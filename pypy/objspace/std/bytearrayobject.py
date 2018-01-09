"""The builtin bytearray implementation"""

from rpython.rlib.objectmodel import (
    import_from_mixin, newlist_hint, resizelist_hint, specialize)
from rpython.rlib.rstring import StringBuilder, ByteListBuilder
from rpython.rlib.debug import check_list_of_chars, check_nonneg
from rpython.rtyper.lltypesystem import rffi
from rpython.rlib.rgc import (resizable_list_supporting_raw_ptr,
                              nonmoving_raw_ptr_for_resizable_list)
from rpython.rlib import jit
from rpython.rlib.buffer import (GCBuffer,
                                 get_gc_data_for_list_of_chars,
                                 get_gc_data_offset_for_list_of_chars)
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.interpreter.buffer import SimpleView
from pypy.objspace.std.sliceobject import W_SliceObject, unwrap_start_stop
from pypy.objspace.std.stringmethods import StringMethods, _get_buffer
from pypy.objspace.std.stringmethods import _descr_getslice_slowpath
from pypy.objspace.std.bytesobject import W_BytesObject
from pypy.objspace.std.util import get_positive_index


class W_BytearrayObject(W_Root):
    import_from_mixin(StringMethods)
    _KIND1 = "bytearray"
    _KIND2 = "bytearray"

    def __init__(self, data):
        check_list_of_chars(data)
        self._data = resizable_list_supporting_raw_ptr(data)
        self._offset = 0
        # NOTE: the bytearray data is in 'self._data[self._offset:]'
        check_nonneg(self._offset)
        _tweak_for_tests(self)

    def getdata(self):
        if self._offset > 0:
            self._data = self._data[self._offset:]
            self._offset = 0
        return self._data

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%s)" % (self.__class__.__name__,
                           ''.join(self._data[self._offset:]))

    def buffer_w(self, space, flags):
        return SimpleView(BytearrayBuffer(self))

    def readbuf_w(self, space):
        return BytearrayBuffer(self, readonly=True)

    def writebuf_w(self, space):
        return BytearrayBuffer(self)

    def charbuf_w(self, space):
        return ''.join(self.getdata())

    def bytearray_list_of_chars_w(self, space):
        return self.getdata()

    def nonmovable_carray(self, space):
        return BytearrayBuffer(self).get_raw_address()

    def _new(self, value):
        if value is self._data:
            value = value[:]
        return W_BytearrayObject(value)

    def _new_from_buffer(self, buffer):
        return W_BytearrayObject([buffer[i] for i in range(len(buffer))])

    def _new_from_list(self, value):
        return W_BytearrayObject(value)

    def _empty(self):
        return W_BytearrayObject([])

    def _len(self):
        return len(self._data) - self._offset

    def _fixindex(self, space, index, errmsg="índice del bytematriz fuera del rango"):
        # for getitem/setitem/delitem of a single char
        if index >= 0:
            index += self._offset
            if index >= len(self._data):
                raise OperationError(space.w_IndexError, space.newtext(errmsg))
        else:
            index += len(self._data)    # count from the end
            if index < self._offset:
                raise OperationError(space.w_IndexError, space.newtext(errmsg))
        check_nonneg(index)
        return index

    def _getitem_result(self, space, index):
        character = self._data[self._fixindex(space, index)]
        return space.newint(ord(character))

    def _val(self, space):
        return self.getdata()

    @staticmethod
    def _use_rstr_ops(space, w_other):
        return False

    @staticmethod
    def _op_val(space, w_other, strict=None):
        # bytearray does not enforce the strict restriction (on strip at least)
        return space.buffer_w(w_other, space.BUF_SIMPLE).as_str()

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    def _multi_chr(self, char):
        return [char]

    @staticmethod
    def _builder(size=100):
        return ByteListBuilder(size)

    def _newlist_unwrapped(self, space, res):
        return space.newlist([W_BytearrayObject(i) for i in res])

    def _isupper(self, ch):
        return ch.isupper()

    def _islower(self, ch):
        return ch.islower()

    def _istitle(self, ch):
        return ch.isupper()

    def _isspace(self, ch):
        return ch.isspace()

    def _isalpha(self, ch):
        return ch.isalpha()

    def _isalnum(self, ch):
        return ch.isalnum()

    def _isdigit(self, ch):
        return ch.isdigit()

    _iscased = _isalpha

    def _islinebreak(self, ch):
        return (ch == '\n') or (ch == '\r')

    def _upper(self, ch):
        if ch.islower():
            o = ord(ch) - 32
            return chr(o)
        else:
            return ch

    def _lower(self, ch):
        if ch.isupper():
            o = ord(ch) + 32
            return chr(o)
        else:
            return ch

    _title = _upper

    def _join_return_one(self, space, w_obj):
        return False

    def _join_check_item(self, space, w_obj):
        if (space.isinstance_w(w_obj, space.w_bytes) or
            space.isinstance_w(w_obj, space.w_bytearray)):
            return 0
        return 1

    def ord(self, space):
        length = self._len()
        if length != 1:
            raise oefmt(space.w_TypeError,
                        "ord() anticipaba un carácter, pero palabra de tamaño %d "
                        "encontrada", length)
        return space.newint(ord(self._data[self._offset]))

    @staticmethod
    def descr_new(space, w_bytearraytype, __args__):
        return new_bytearray(space, w_bytearraytype, [])

    def descr_reduce(self, space):
        assert isinstance(self, W_BytearrayObject)
        w_dict = self.getdict(space)
        if w_dict is None:
            w_dict = space.w_None
        return space.newtuple([
            space.type(self), space.newtuple([
                space.newunicode(''.join(self.getdata()).decode('latin-1')),
                space.newtext('latin-1')]),
            w_dict])

    @staticmethod
    def descr_fromhex(space, w_bytearraytype, w_hexstring):
        hexstring = space.text_w(w_hexstring)
        data = _hexstring_to_array(space, hexstring)
        # in CPython bytearray.fromhex is a staticmethod, so
        # we ignore w_type and always return a bytearray
        return new_bytearray(space, space.w_bytearray, data)

    @unwrap_spec(encoding='text_or_none', errors='text_or_none')
    def descr_init(self, space, w_source=None, encoding=None, errors=None):
        if w_source is None:
            w_source = space.newbytes('')
        if encoding is not None:
            from pypy.objspace.std.unicodeobject import encode_object
            # if w_source is an integer this correctly raises a
            # TypeError the CPython error message is: "encoding or
            # errors without a string argument" ours is: "expected
            # unicode, got int object"
            w_source = encode_object(space, w_source, encoding, errors)

        # Is it an int?
        try:
            count = space.int_w(w_source)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
        else:
            if count < 0:
                raise oefmt(space.w_ValueError, "bytematriz total negativo")
            self._data = resizable_list_supporting_raw_ptr(['\0'] * count)
            self._offset = 0
            return

        data = makebytearraydata_w(space, w_source)
        self._data = resizable_list_supporting_raw_ptr(data)
        self._offset = 0
        _tweak_for_tests(self)

    def descr_repr(self, space):
        s, start, end, _ = self._convert_idx_params(space, None, None)

        # Good default if there are no replacements.
        buf = StringBuilder(len("bytematriz(b'')") + (end - start))

        buf.append("bytematriz(b")
        quote = "'"
        for i in range(start, end):
            c = s[i]
            if c == '"':
                quote = "'"
                break
            elif c == "'":
                quote = '"'
        buf.append(quote)

        for i in range(start, end):
            c = s[i]

            if c == '\\' or c == "'":
                buf.append('\\')
                buf.append(c)
            elif c == '\t':
                buf.append('\\t')
            elif c == '\r':
                buf.append('\\r')
            elif c == '\n':
                buf.append('\\n')
            elif not '\x20' <= c < '\x7f':
                n = ord(c)
                buf.append('\\x')
                buf.append("0123456789abcdef"[n >> 4])
                buf.append("0123456789abcdef"[n & 0xF])
            else:
                buf.append(c)

        buf.append(quote)
        buf.append(")")

        return space.newtext(buf.build())

    def descr_str(self, space):
        return space.newtext(''.join(self.getdata()))

    def descr_eq(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return space.newbool(self.getdata() == w_other.getdata())

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise

        value = self._val(space)
        buffer_len = buffer.getlength()

        if len(value) != buffer_len:
            return space.newbool(False)

        min_length = min(len(value), buffer_len)
        return space.newbool(_memcmp(value, buffer, min_length) == 0)

    def descr_ne(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return space.newbool(self.getdata() != w_other.getdata())

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise

        value = self._val(space)
        buffer_len = buffer.getlength()

        if len(value) != buffer_len:
            return space.newbool(True)

        min_length = min(len(value), buffer_len)
        return space.newbool(_memcmp(value, buffer, min_length) != 0)

    def _comparison_helper(self, space, w_other):
        value = self._val(space)

        if isinstance(w_other, W_BytearrayObject):
            other = w_other.getdata()
            other_len = len(other)
            cmp = _memcmp(value, other, min(len(value), len(other)))
        elif isinstance(w_other, W_BytesObject):
            other = self._op_val(space, w_other)
            other_len = len(other)
            cmp = _memcmp(value, other, min(len(value), len(other)))
        else:
            try:
                buffer = _get_buffer(space, w_other)
            except OperationError as e:
                if e.match(space, space.w_TypeError):
                    return False, 0, 0
                raise
            other_len = len(buffer)
            cmp = _memcmp(value, buffer, min(len(value), len(buffer)))

        return True, cmp, other_len

    def descr_lt(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp < 0 or (cmp == 0 and self._len() < other_len))

    def descr_le(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp < 0 or (cmp == 0 and self._len() <= other_len))

    def descr_gt(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp > 0 or (cmp == 0 and self._len() > other_len))

    def descr_ge(self, space, w_other):
        success, cmp, other_len = self._comparison_helper(space, w_other)
        if not success:
            return space.w_NotImplemented
        return space.newbool(cmp > 0 or (cmp == 0 and self._len() >= other_len))

    def descr_iter(self, space):
        return space.newseqiter(self)

    def descr_inplace_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self._data += w_other.getdata()
            return self

        if isinstance(w_other, W_BytesObject):
            self._inplace_add(self._op_val(space, w_other))
        else:
            self._inplace_add(_get_buffer(space, w_other))
        return self

    @specialize.argtype(1)
    def _inplace_add(self, other):
        for i in range(len(other)):
            self._data.append(other[i])

    def descr_inplace_mul(self, space, w_times):
        try:
            times = space.getindex_w(w_times, space.w_OverflowError)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        data = self.getdata()
        data *= times
        return self

    def descr_setitem(self, space, w_index, w_other):
        if isinstance(w_index, W_SliceObject):
            sequence2 = makebytearraydata_w(space, w_other)
            oldsize = self._len()
            start, stop, step, slicelength = w_index.indices4(space, oldsize)
            if start == 0 and step == 1 and len(sequence2) <= slicelength:
                self._delete_from_start(slicelength - len(sequence2))
                slicelength = len(sequence2)
                if slicelength == 0:
                    return
            data = self._data
            start += self._offset
            _setitem_slice_helper(space, data, start, step,
                                  slicelength, sequence2, empty_elem='\x00')
        else:
            idx = space.getindex_w(w_index, space.w_IndexError,
                                   "índice de bytematriz")
            newvalue = space.byte_w(w_other)
            self._data[self._fixindex(space, idx)] = newvalue

    def descr_delitem(self, space, w_idx):
        if isinstance(w_idx, W_SliceObject):
            start, stop, step, slicelength = w_idx.indices4(space, self._len())
            if start == 0 and step == 1:
                self._delete_from_start(slicelength)
            else:
                _delitem_slice_helper(space, self._data,
                                      start + self._offset, step, slicelength)
        else:
            idx = space.getindex_w(w_idx, space.w_IndexError,
                                   "índice de bytematriz")
            idx = self._fixindex(space, idx)
            if idx == self._offset:    # fast path for del x[0] or del[-len]
                self._delete_from_start(1)
            else:
                del self._data[idx]

    def _delete_from_start(self, n):
        assert n >= 0
        self._offset += n
        jit.conditional_call(self._offset > len(self._data) / 2,
                             _shrink_after_delete_from_start, self)

    def descr_append(self, space, w_item):
        self._data.append(space.byte_w(w_item))

    def descr_extend(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            self._data += w_other.getdata()
        else:
            self._inplace_add(makebytearraydata_w(space, w_other))

    def descr_insert(self, space, w_idx, w_other):
        where = space.int_w(w_idx)
        data = self.getdata()
        index = get_positive_index(where, len(data))
        val = space.byte_w(w_other)
        data.insert(index, val)

    @unwrap_spec(w_idx=WrappedDefault(-1))
    def descr_pop(self, space, w_idx):
        index = space.int_w(w_idx)
        if self._len() == 0:
            raise oefmt(space.w_IndexError, "pop de bytematriz vacía")
        index = self._fixindex(space, index, "índice del pop fuera del rango")
        result = self._data.pop(index)
        return space.newint(ord(result))

    def descr_remove(self, space, w_char):
        char = space.int_w(space.index(w_char))
        _data = self._data
        for index in range(self._offset, len(_data)):
            if ord(_data[index]) == char:
                del _data[index]
                return
        raise oefmt(space.w_ValueError, "valor no encontrado en bytematriz")

    _StringMethods_descr_contains = descr_contains
    def descr_contains(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_int):
            char = space.int_w(w_sub)
            return _descr_contains_bytearray(self.getdata(), space, char)

        return self._StringMethods_descr_contains(space, w_sub)

    def descr_add(self, space, w_other):
        if isinstance(w_other, W_BytearrayObject):
            return self._new(self.getdata() + w_other.getdata())

        if isinstance(w_other, W_BytesObject):
            return self._add(self._op_val(space, w_other))

        try:
            buffer = _get_buffer(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return self._add(buffer)

    @specialize.argtype(1)
    def _add(self, other):
        return self._new(self.getdata() + [other[i] for i in range(len(other))])

    def descr_reverse(self, space):
        self.getdata().reverse()

    def descr_alloc(self, space):
        return space.newint(len(self._data) + 1)   # includes the _offset part

    def _convert_idx_params(self, space, w_start, w_end):
        # optimization: this version doesn't force getdata()
        start, end = unwrap_start_stop(space, self._len(), w_start, w_end)
        ofs = self._offset
        return (self._data, start + ofs, end + ofs, ofs)

    def descr_getitem(self, space, w_index):
        # optimization: this version doesn't force getdata()
        if isinstance(w_index, W_SliceObject):
            start, stop, step, sl = w_index.indices4(space, self._len())
            if sl == 0:
                return self._empty()
            elif step == 1:
                assert start >= 0 and stop >= 0
                ofs = self._offset
                return self._new(self._data[start + ofs : stop + ofs])
            else:
                start += self._offset
                ret = _descr_getslice_slowpath(self._data, start, step, sl)
                return self._new_from_list(ret)

        index = space.getindex_w(w_index, space.w_IndexError, self._KIND1)
        return self._getitem_result(space, index)


# ____________________________________________________________
# helpers for slow paths, moved out because they contain loops

def _make_data(s):
    return [s[i] for i in range(len(s))]


def _descr_contains_bytearray(data, space, char):
    if not 0 <= char < 256:
        raise oefmt(space.w_ValueError, "byte tiene que estar en rango(0, 256)")
    for c in data:
        if ord(c) == char:
            return space.w_True
    return space.w_False

# ____________________________________________________________


def new_bytearray(space, w_bytearraytype, data):
    w_obj = space.allocate_instance(W_BytearrayObject, w_bytearraytype)
    W_BytearrayObject.__init__(w_obj, data)
    return w_obj


def makebytearraydata_w(space, w_source):
    # String-like argument
    try:
        buf = space.buffer_w(w_source, space.BUF_FULL_RO)
    except OperationError as e:
        if not e.match(space, space.w_TypeError):
            raise
    else:
        return list(buf.as_str())
    return _from_byte_sequence(space, w_source)

def _get_printable_location(w_type):
    return ('bytearray_from_byte_sequence [w_type=%s]' %
            w_type.getname(w_type.space))

_byteseq_jitdriver = jit.JitDriver(
    name='bytearray_from_byte_sequence',
    greens=['w_type'],
    reds=['w_iter', 'data'],
    get_printable_location=_get_printable_location)

def _from_byte_sequence(space, w_source):
    # Split off in a separate function for the JIT's benefit
    # and add a jitdriver with the type of w_iter as the green key
    w_iter = space.iter(w_source)
    length_hint = space.length_hint(w_source, 0)
    data = newlist_hint(length_hint)
    #
    _from_byte_sequence_loop(space, w_iter, data)
    #
    extended = len(data)
    if extended < length_hint:
        resizelist_hint(data, extended)
    return data

def _from_byte_sequence_loop(space, w_iter, data):
    w_type = space.type(w_iter)
    while True:
        _byteseq_jitdriver.jit_merge_point(w_type=w_type,
                                           w_iter=w_iter,
                                           data=data)
        try:
            w_item = space.next(w_iter)
        except OperationError as e:
            if not e.match(space, space.w_StopIteration):
                raise
            break
        data.append(space.byte_w(w_item))


def _hex_digit_to_int(d):
    val = ord(d)
    if 47 < val < 58:
        return val - 48
    if 64 < val < 71:
        return val - 55
    if 96 < val < 103:
        return val - 87
    return -1

NON_HEX_MSG = "número no-hexadecimal encontrado en dehex() arg en posición %d"

def _hexstring_to_array(space, s):
    data = []
    length = len(s)
    i = 0
    while True:
        while i < length and s[i] == ' ':
            i += 1
        if i >= length:
            break
        if i + 1 == length:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i)

        top = _hex_digit_to_int(s[i])
        if top == -1:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i)
        bot = _hex_digit_to_int(s[i + 1])
        if bot == -1:
            raise oefmt(space.w_ValueError, NON_HEX_MSG, i + 1)
        data.append(chr(top * 16 + bot))
        i += 2
    return data


class BytearrayDocstrings:
    """bytematriz(iterable_de_ents) -> bytematriz
    bytematriz(palabra, codificación[, errores]) -> bytematriz
    bytematriz(bytes_o_bytematriz) -> copia mutable de bytes_o_bytematriz
    bytematriz(vista_memoria) -> bytematriz

    Construir un objeto bytematriz mutable de:
        - un iterable que produce enteros en el rango(256)
        - una palabra codificada usando la codificación especificada
        - un objeto de bytes o bytematriz
        - cualquier objecto que implementa el API del búfer

    bytematriz(ent) -> bytematriz.

    Construir un cero-iniciada bytematriz del tamaño dado.

    """

    def __add__():
        """x.__mas__(y) <==> x+y"""

    def __alloc__():
        """B.__asign__() -> int

        Vuelve el numero actual de bytes asignados.
        """

    def __contains__():
        """x.__contiene__(y) <==> y in x"""

    def __delitem__():
        """x.__elimartic__(y) <==> del x[y]"""

    def __eq__():
        """x.__ig__(y) <==> x==y"""

    def __ge__():
        """x.__mai__(y) <==> x>=y"""

    def __getattribute__():
        """x.__sacaatributo__('nombre') <==> x.nombre"""

    def __getitem__():
        """x.__sacaartic__(y) <==> x[y]"""

    def __gt__():
        """x.__maq__(y) <==> x>y"""

    def __iadd__():
        """x.__imas__(y) <==> x+=y"""

    def __imul__():
        """x.__imul__(y) <==> x*=y"""

    def __init__():
        """x.__inic__(...) inicializa x; vea ayuda(tipo(x)) para firma"""

    def __iter__():
        """x.__iter__() <==> iter(x)"""

    def __le__():
        """x.__mei__(y) <==> x<=y"""

    def __len__():
        """x.__tam__() <==> tam(x)"""

    def __lt__():
        """x.__meq__(y) <==> x<y"""

    def __mul__():
        """x.__mul__(n) <==> x*n"""

    def __ne__():
        """x.__ni__(y) <==> x!=y"""

    def __reduce__():
        """Vuelve información de estado para envinagración."""

    def __repr__():
        """x.__repr__() <==> repr(x)"""

    def __rmul__():
        """x.__dmul__(n) <==> n*x"""

    def __setitem__():
        """x.__ponartic__(i, y) <==> x[i]=y"""

    def __sizeof__():
        """B.__tamde__() -> int

        Vuelve el tamaño de B en memoria, en bytes
        """

    def __str__():
        """x.__pal__() <==> pal(x)"""

    def append():
        """B.adjuntar(int) -> None

        Adjunta un solo artículo al fin de B.
        """

    def capitalize():
        """B.mayuscular() -> copia de B

        Vuelve una copia de B con solo su carácter primera puesta en mayúscula
        (ASCII) y el resto puesta en minúscula.
        """

    def center():
        """B.centro(ancho[, llenacarác]) -> copia de B

        Vuelve B al centro de una palabra de tamaño ancho. Renneno está hecho
        usando la carácter especificada (estándar es un espacio).
        """

    def count():
        """B.total(sub[, empieza[, fin]]) -> ent

        Vuelve el número de casos no-sobreponiendos de subsección sub en bytes
        B[empieza:fin]. Argumentos opcionales empieza y fin son interpretados en
        notación de cortar.
        """

    def decode():
        """B.decodificar(codificación=Nada, errores='estricta') -> unicod

        Decodifica B usando el codec registrado para codificación. codificación
        se estandardiza ala codificación estándar. errores puede ser dado para
        poner otra manera de manejar errores. El estándar es 'estricta' que
        significa que errores de codificación llaman UnicodeDecodeError. Otros
        valores posibles son 'ignorar' y 'reemplazar', tanto como cualquiera
        otro nombre registrado con codecs.registrar_error que funciona con
        UnicodeDecodeError.
        """

    def endswith():
        """B.terminacon(sufijo[, empieza[, fin]]) -> bool

        Vuelve Cierto si B termina con el sufijo especificado, Falso si no.
        Con opcional empieza, prueba B empezando en este posición.
        Con opcional fin, pare comparando B en este posición.
        sufijo también puede ser un tuple de palabras para probar.
        """

    def expandtabs():
        """B.expandtabs([tabtam]) -> copia de B

        Vuelve una copia de B donde todas las carácteres tab son expandidas
        usando espacios. Si tabtam no es dado, tamaño de 8 carácteres es
        suponido.
        """

    def extend():
        """B.extender(iterable_de_ents) -> Nada

        Adjunta todos los elementos del iterador o secuencia al final de B.
        """

    def find():
        """B.encontrar(sub[, empieza[, fin]]) -> ent

        Vuelve el índice más bajo en B donde subsección sub se puede encontar,
        para que sub esté contenida entre B[empieza:fin]. Opcional argumentos
        empieza y fin son interpretados como en notación cortar.

        Vuelve -1 si fracasa.
        """

    def fromhex():
        r"""bytearray.fromhex(string) -> bytearray (static method)

        Create a bytearray object from a string of hexadecimal numbers.
        Spaces between two numbers are accepted.
        Example: bytearray.fromhex('B9 01EF') -> bytearray(b'\xb9\x01\xef').
        """

    def index():
        """B.indice(sub[, empieza[, fin]]) -> ent

        Como B.encontrar() pero llama ValueError cuando no se puede encontrar
        la subsección.
        """

    def insert():
        """B.insertar(índice, ent) -> Nada

        Insertar un solo artículo en el bytematríz antes del índice dado.
        """

    def isalnum():
        """B.esalnum() -> bool

        Vuelve Cierto si todos los carácteres en B son alfanuméricos y
        hay por lo menos un carácter en B, Falso si no.
        """

    def isalpha():
        """B.esalfa() -> bool

        Vuelve Cierto si todos los carácteres en B son alfabeticos y
        hay por lo menos un carácter en B, Falso si no.
        """

    def isdigit():
        """B.esdig() -> bool

        Vuelve Cierto si todos los carácteres en B son números decimales,
        y hay por lo menos un carácter en B, Falso si no.
        """

    def islower():
        """B.esminusc() -> bool

        Vuelve Cierto si todos los carácteres en B son minúsculos y hay
        por lo menos un carácter en B, Falso si no.
        """

    def isspace():
        """B.esespac() -> bool

        Vuelve Cierto si todos los carácteres en B son espacio blanco
        y hay por lo menos un carácter en B, Falso si no.
        """

    ## XXX check this - AK
    def istitle():
        """B.estitulo() -> bool

        Vuelve Cierto si B es en forma título y hay por lo menos un carácter
        en B, i.e. carácteres en mayúscula solo pueden seguir carácteres en
        minúscula, y carácteres en minúscula solo siguen mayusculas. Falso si
        no.
        """

    def isupper():
        """B.esmayusc() -> bool

        Vuelve Cierto si todos los carácteres en B son mayúsculas y hay por
        lo menus un carácter en B, Falso si no.
        """

    def join():
        """B.juntar(iterable_de_bytes) -> bytematriz

        Conectar cualquier número de objetos pal/bytematriz, con B
        entre cada pareja. Vuelve el resultado como nuevo bytematriz.
        """

    def ljust():
        """B.ijust(ancho[, llenacarác]) -> copia de B

        Vuelve B justificado a la izquiera en una palabra de tamaño ancho.
        Relleno está hecho con el carácter especificado (estándar es un
        espacio).
        """

    def lower():
        """B.minusc() -> copia de B

        Vuelve una copia de B con todos los carácteres ASCII convertidos a
        minúscula.
        """

    def lstrip():
        """B.idecapar([bytes]) -> bytematriz

        Decapa bytes contenidos al frente del argumento y volver el resulto
        como nuevo bytematriz. Si el argumento está omitido, decapar espacio
        blanco ASCII al frente.
        """

    def partition():
        """B.particion(sep) -> (cabeza, sep, cola)

        Buscar el separador sep en B. Vuelve el parte antes de ello, ello
        mismo y el parte después de ello. Si el separador no se puede encontrar,
        vuelve B y dos bytematrizes vacíos.
        """

    def pop():
        """B.pop([índice]) -> ent

        Quitar y volver un solo artículo de B. Si no índice está dado,
        saca el valor final.
        """

    def remove():
        """B.quitar(ent) -> Nada

        Quitar la ocurrencia primera de un valor en B.
        """

    def replace():
        """B.reemplazar(vieja, nueva[, num]) -> bytematriz

        Vuelve una copia de B con todas ocurrencias de subsección
        vieja reemplazadas con nueva. Si el argumento opcional num
        está dado, solo las primeras num ocurrencias son reemplazadas.
        """

    def reverse():
        """B.invertir() -> None

        Invertir el orden de los valores de B en su lugar.
        """

    def rfind():
        """B.dencontrar(sub[, empieza[, fin]]) -> ent

        Vuelve el índice más alto en B donde subsección sub se puede
        encontrar, para que sub se contenga entre B[empieza,fin]. Argumentos
        opcionales empieza y fin son interpretados como en notación cortar.

        Vuelve -1 si fracasa.
        """

    def rindex():
        """B.dindice(sub[, empieza[, fin]]) -> ent

        Como B.encontrar() pero llama ValueError cuando la subsección no
        está encontrada.
        """

    def rjust():
        """B.djust(ancho[, llenacarác]) -> copia de B

        Vuelve B justificada a la derecha en una palabra de tamaño ancho.
        Relleno está hecho con el llenacarác especificado (estándar es un
        espacio).
        """

    def rpartition():
        """B.dparticion(sep) -> (cabeza, sep, cola)

        Buscar el separador sep en B, empezando al fin de B, y vuelve
        el parte antes de ello, ello mismo y el parte despúes de ello.
        Si no se puede encontrar sep, vuelve dos bytematrizes vacíos.
        """

    def rsplit():
        """B.dquebrar(sep=Nada, maxquebar=-1) -> lista de bytematrizes

        Volver una ista de las secciones en B, usando sep como delimitador,
        empezando al final de B y siguendo al frente.
        Si sep no está dado, B está quebrado en carácteres ASCII espacio
        blanco (espacio, tab, volver, lineanueva, salto de página, tab
        vertical).
        Si maxquebrar está dado, al máximo maxquebrar quebraciones están
        hechos.
        """

    def rstrip():
        """B.ddecapar([bytes]) -> bytematriz

        Decapar bytes en la cola del argumento y volver el resultado como
        newva bytematriz.
        Si el argumento está omitido, decapar espacio blanco ASCII en la
        cola.
        """

    def split():
        """B.quebrar(sep=Nada, maxsquebrar=-1) -> lista de bytematrizes

        Volver una ista de las secciones en B, usando sep como delimitador.
        Si sep no está dado, B está quebrado en carácteres ASCII espacio
        blanco (espacio, tab, volver, lineanueva, salto de página, tab
        vertical).
        Si maxquebrar está dado, al máximo maxquebrar quebraciones están
        hechos.
        """

    def splitlines():
        """B.quebrarlineas(guardarcolas=False) -> lista de líneas

        Volver una lista de las líneas en B, rompiendo en límites de las
        líneas. Rompes de línea no son incluidos en el resultado a menos
        que guardarcolas está dado y es Cierto.
        """

    def startswith():
        """B.empcon(prefijo[, empieza[, fin]]) -> bool

        Vuelve Cierto si B empieza con el prefijo especificado, Falso si no.
        Con empieza opcional, prueba B empezando en esta posición.
        Con fin opcional, pare comparando B en esta posición.
        prefijo también puede ser un tuple de palabras para probar.
        """

    def strip():
        """B.decapar([bytes]) -> bytematriz

        Decapa bytes al frente y al fin del argumento y volver el resultado
        como nueva bytematriz.
        Si el argumento está omitido, decapar espacio blanco ASCII.
        """

    def swapcase():
        """B.minmayusc() -> copia de B

        Vuelve una copia de B con todos los carácteres mayúsculos convertidos
        a minúsculo, y vice versa.
        """

    def title():
        """B.titulo() -> copia de B

        Vuelve una versión de B puesto como titulo, i.e. palabras de ASCII
        empiezan con mayúscula, y el resto de los carácteres son minusculos.
        """

    def translate():
        """B.traducir(mesa[, elimcarács]) -> bytematriz

        Vuelve una copia de B donde todos los carácteres que ocurren
        en el argumento opcional elimcarács son quitados, y el resto
        de los carácteres han sido aplicados en la mesa de traducción,
        que tiene que ser un objeto bytes de tamaño 256.
        """

    def upper():
        """B.mayusc() -> copia de B

        Vuelve una copia de B con todos carácteres ASCII convertidos a
        mayúsculo.
        """

    def zfill():
        """B.cllenar(ancho) -> copia de B

        Rellenar una palabra numérica B con ceros a la izquierda, para
        llenar un campo del ancho especificado. B nunca está truncado.
        """


W_BytearrayObject.typedef = TypeDef(
    "bytematriz", None, None, "read-write",
    __doc__ = BytearrayDocstrings.__doc__,
    __nuevo__ = interp2app(W_BytearrayObject.descr_new),
    __new__ = interp2app(W_BytearrayObject.descr_new),
    __hash__ = None,
    __reducir__ = interp2app(W_BytearrayObject.descr_reduce,
                            doc=BytearrayDocstrings.__reduce__.__doc__),
    __reduce__ = interp2app(W_BytearrayObject.descr_reduce,
                            doc=BytearrayDocstrings.__reduce__.__doc__),
    dehex = interp2app(W_BytearrayObject.descr_fromhex, as_classmethod=True,
                         doc=BytearrayDocstrings.fromhex.__doc__),
    fromhex = interp2app(W_BytearrayObject.descr_fromhex, as_classmethod=True,
                         doc=BytearrayDocstrings.fromhex.__doc__),
    __repr__ = interp2app(W_BytearrayObject.descr_repr,
                          doc=BytearrayDocstrings.__repr__.__doc__),
    __pal__ = interp2app(W_BytearrayObject.descr_str,
                         doc=BytearrayDocstrings.__str__.__doc__),
    __str__ = interp2app(W_BytearrayObject.descr_str,
                         doc=BytearrayDocstrings.__str__.__doc__),
    __ig__ = interp2app(W_BytearrayObject.descr_eq,
                        doc=BytearrayDocstrings.__eq__.__doc__),
    __eq__ = interp2app(W_BytearrayObject.descr_eq,
                        doc=BytearrayDocstrings.__eq__.__doc__),
    __ni__ = interp2app(W_BytearrayObject.descr_ne,
                        doc=BytearrayDocstrings.__ne__.__doc__),
    __ne__ = interp2app(W_BytearrayObject.descr_ne,
                        doc=BytearrayDocstrings.__ne__.__doc__),
    __meq__ = interp2app(W_BytearrayObject.descr_lt,
                        doc=BytearrayDocstrings.__lt__.__doc__),
    __lt__ = interp2app(W_BytearrayObject.descr_lt,
                        doc=BytearrayDocstrings.__lt__.__doc__),
    __mei__ = interp2app(W_BytearrayObject.descr_le,
                        doc=BytearrayDocstrings.__le__.__doc__),
    __le__ = interp2app(W_BytearrayObject.descr_le,
                        doc=BytearrayDocstrings.__le__.__doc__),
    __maq__ = interp2app(W_BytearrayObject.descr_gt,
                        doc=BytearrayDocstrings.__gt__.__doc__),
    __gt__ = interp2app(W_BytearrayObject.descr_gt,
                        doc=BytearrayDocstrings.__gt__.__doc__),
    __mai__ = interp2app(W_BytearrayObject.descr_ge,
                        doc=BytearrayDocstrings.__ge__.__doc__),
    __ge__ = interp2app(W_BytearrayObject.descr_ge,
                        doc=BytearrayDocstrings.__ge__.__doc__),
    __iter__ = interp2app(W_BytearrayObject.descr_iter,
                         doc=BytearrayDocstrings.__iter__.__doc__),
    __tam__ = interp2app(W_BytearrayObject.descr_len,
                         doc=BytearrayDocstrings.__len__.__doc__),
    __len__ = interp2app(W_BytearrayObject.descr_len,
                         doc=BytearrayDocstrings.__len__.__doc__),
    __contiene__ = interp2app(W_BytearrayObject.descr_contains,
                              doc=BytearrayDocstrings.__contains__.__doc__),
    __contains__ = interp2app(W_BytearrayObject.descr_contains,
                              doc=BytearrayDocstrings.__contains__.__doc__),
    __mas__ = interp2app(W_BytearrayObject.descr_add,
                         doc=BytearrayDocstrings.__add__.__doc__),
    __add__ = interp2app(W_BytearrayObject.descr_add,
                         doc=BytearrayDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_BytearrayObject.descr_mul,
                         doc=BytearrayDocstrings.__mul__.__doc__),
    __dmul__ = interp2app(W_BytearrayObject.descr_mul,
                          doc=BytearrayDocstrings.__rmul__.__doc__),
    __rmul__ = interp2app(W_BytearrayObject.descr_mul,
                          doc=BytearrayDocstrings.__rmul__.__doc__),
    __sacaartic__ = interp2app(W_BytearrayObject.descr_getitem,
                             doc=BytearrayDocstrings.__getitem__.__doc__),
    __getitem__ = interp2app(W_BytearrayObject.descr_getitem,
                             doc=BytearrayDocstrings.__getitem__.__doc__),
    mayuscular = interp2app(W_BytearrayObject.descr_capitalize,
                            doc=BytearrayDocstrings.capitalize.__doc__),
    capitalize = interp2app(W_BytearrayObject.descr_capitalize,
                            doc=BytearrayDocstrings.capitalize.__doc__),
    centro = interp2app(W_BytearrayObject.descr_center,
                        doc=BytearrayDocstrings.center.__doc__),
    center = interp2app(W_BytearrayObject.descr_center,
                        doc=BytearrayDocstrings.center.__doc__),
    total = interp2app(W_BytearrayObject.descr_count,
                       doc=BytearrayDocstrings.count.__doc__),
    count = interp2app(W_BytearrayObject.descr_count,
                       doc=BytearrayDocstrings.count.__doc__),
    decodificar = interp2app(W_BytearrayObject.descr_decode,
                        doc=BytearrayDocstrings.decode.__doc__),
    decode = interp2app(W_BytearrayObject.descr_decode,
                        doc=BytearrayDocstrings.decode.__doc__),
    expandtabs = interp2app(W_BytearrayObject.descr_expandtabs,
                            doc=BytearrayDocstrings.expandtabs.__doc__),
    encontrar = interp2app(W_BytearrayObject.descr_find,
                      doc=BytearrayDocstrings.find.__doc__),
    find = interp2app(W_BytearrayObject.descr_find,
                      doc=BytearrayDocstrings.find.__doc__),
    dencontrar = interp2app(W_BytearrayObject.descr_rfind,
                       doc=BytearrayDocstrings.rfind.__doc__),
    rfind = interp2app(W_BytearrayObject.descr_rfind,
                       doc=BytearrayDocstrings.rfind.__doc__),
    indice = interp2app(W_BytearrayObject.descr_index,
                       doc=BytearrayDocstrings.index.__doc__),
    index = interp2app(W_BytearrayObject.descr_index,
                       doc=BytearrayDocstrings.index.__doc__),
    dindice = interp2app(W_BytearrayObject.descr_rindex,
                        doc=BytearrayDocstrings.rindex.__doc__),
    rindex = interp2app(W_BytearrayObject.descr_rindex,
                        doc=BytearrayDocstrings.rindex.__doc__),
    esalnum = interp2app(W_BytearrayObject.descr_isalnum,
                         doc=BytearrayDocstrings.isalnum.__doc__),
    isalnum = interp2app(W_BytearrayObject.descr_isalnum,
                         doc=BytearrayDocstrings.isalnum.__doc__),
    esalfa = interp2app(W_BytearrayObject.descr_isalpha,
                         doc=BytearrayDocstrings.isalpha.__doc__),
    isalpha = interp2app(W_BytearrayObject.descr_isalpha,
                         doc=BytearrayDocstrings.isalpha.__doc__),
    esdig = interp2app(W_BytearrayObject.descr_isdigit,
                         doc=BytearrayDocstrings.isdigit.__doc__),
    isdigit = interp2app(W_BytearrayObject.descr_isdigit,
                         doc=BytearrayDocstrings.isdigit.__doc__),
    esminusc = interp2app(W_BytearrayObject.descr_islower,
                         doc=BytearrayDocstrings.islower.__doc__),
    islower = interp2app(W_BytearrayObject.descr_islower,
                         doc=BytearrayDocstrings.islower.__doc__),
    esespac = interp2app(W_BytearrayObject.descr_isspace,
                         doc=BytearrayDocstrings.isspace.__doc__),
    isspace = interp2app(W_BytearrayObject.descr_isspace,
                         doc=BytearrayDocstrings.isspace.__doc__),
    estitulo = interp2app(W_BytearrayObject.descr_istitle,
                         doc=BytearrayDocstrings.istitle.__doc__),
    istitle = interp2app(W_BytearrayObject.descr_istitle,
                         doc=BytearrayDocstrings.istitle.__doc__),
    esmayusc = interp2app(W_BytearrayObject.descr_isupper,
                         doc=BytearrayDocstrings.isupper.__doc__),
    isupper = interp2app(W_BytearrayObject.descr_isupper,
                         doc=BytearrayDocstrings.isupper.__doc__),
    juntar = interp2app(W_BytearrayObject.descr_join,
                      doc=BytearrayDocstrings.join.__doc__),
    join = interp2app(W_BytearrayObject.descr_join,
                      doc=BytearrayDocstrings.join.__doc__),
    ijust = interp2app(W_BytearrayObject.descr_ljust,
                       doc=BytearrayDocstrings.ljust.__doc__),
    ljust = interp2app(W_BytearrayObject.descr_ljust,
                       doc=BytearrayDocstrings.ljust.__doc__),
    djust = interp2app(W_BytearrayObject.descr_rjust,
                       doc=BytearrayDocstrings.rjust.__doc__),
    rjust = interp2app(W_BytearrayObject.descr_rjust,
                       doc=BytearrayDocstrings.rjust.__doc__),
    minusc = interp2app(W_BytearrayObject.descr_lower,
                       doc=BytearrayDocstrings.lower.__doc__),
    lower = interp2app(W_BytearrayObject.descr_lower,
                       doc=BytearrayDocstrings.lower.__doc__),
    particion = interp2app(W_BytearrayObject.descr_partition,
                           doc=BytearrayDocstrings.partition.__doc__),
    partition = interp2app(W_BytearrayObject.descr_partition,
                           doc=BytearrayDocstrings.partition.__doc__),
    dparticion = interp2app(W_BytearrayObject.descr_rpartition,
                            doc=BytearrayDocstrings.rpartition.__doc__),
    rpartition = interp2app(W_BytearrayObject.descr_rpartition,
                            doc=BytearrayDocstrings.rpartition.__doc__),
    reemplazar = interp2app(W_BytearrayObject.descr_replace,
                         doc=BytearrayDocstrings.replace.__doc__),
    replace = interp2app(W_BytearrayObject.descr_replace,
                         doc=BytearrayDocstrings.replace.__doc__),
    quebrar = interp2app(W_BytearrayObject.descr_split,
                       doc=BytearrayDocstrings.split.__doc__),
    split = interp2app(W_BytearrayObject.descr_split,
                       doc=BytearrayDocstrings.split.__doc__),
    dquebrar = interp2app(W_BytearrayObject.descr_rsplit,
                        doc=BytearrayDocstrings.rsplit.__doc__),
    rsplit = interp2app(W_BytearrayObject.descr_rsplit,
                        doc=BytearrayDocstrings.rsplit.__doc__),
    quebrarlineas = interp2app(W_BytearrayObject.descr_splitlines,
                            doc=BytearrayDocstrings.splitlines.__doc__),
    splitlines = interp2app(W_BytearrayObject.descr_splitlines,
                            doc=BytearrayDocstrings.splitlines.__doc__),
    empcon = interp2app(W_BytearrayObject.descr_startswith,
                            doc=BytearrayDocstrings.startswith.__doc__),
    startswith = interp2app(W_BytearrayObject.descr_startswith,
                            doc=BytearrayDocstrings.startswith.__doc__),
    terminacon = interp2app(W_BytearrayObject.descr_endswith,
                          doc=BytearrayDocstrings.endswith.__doc__),
    decapar = interp2app(W_BytearrayObject.descr_strip,
                       doc=BytearrayDocstrings.strip.__doc__),
    strip = interp2app(W_BytearrayObject.descr_strip,
                       doc=BytearrayDocstrings.strip.__doc__),
    idecapar = interp2app(W_BytearrayObject.descr_lstrip,
                        doc=BytearrayDocstrings.lstrip.__doc__),
    lstrip = interp2app(W_BytearrayObject.descr_lstrip,
                        doc=BytearrayDocstrings.lstrip.__doc__),
    ddecapar = interp2app(W_BytearrayObject.descr_rstrip,
                        doc=BytearrayDocstrings.rstrip.__doc__),
    rstrip = interp2app(W_BytearrayObject.descr_rstrip,
                        doc=BytearrayDocstrings.rstrip.__doc__),
    minmayusc = interp2app(W_BytearrayObject.descr_swapcase,
                          doc=BytearrayDocstrings.swapcase.__doc__),
    swapcase = interp2app(W_BytearrayObject.descr_swapcase,
                          doc=BytearrayDocstrings.swapcase.__doc__),
    titulo = interp2app(W_BytearrayObject.descr_title,
                       doc=BytearrayDocstrings.title.__doc__),
    title = interp2app(W_BytearrayObject.descr_title,
                       doc=BytearrayDocstrings.title.__doc__),
    traducir = interp2app(W_BytearrayObject.descr_translate,
                           doc=BytearrayDocstrings.translate.__doc__),
    translate = interp2app(W_BytearrayObject.descr_translate,
                           doc=BytearrayDocstrings.translate.__doc__),
    mayusc = interp2app(W_BytearrayObject.descr_upper,
                       doc=BytearrayDocstrings.upper.__doc__),
    upper = interp2app(W_BytearrayObject.descr_upper,
                       doc=BytearrayDocstrings.upper.__doc__),
    cllenar = interp2app(W_BytearrayObject.descr_zfill,
                       doc=BytearrayDocstrings.zfill.__doc__),
    zfill = interp2app(W_BytearrayObject.descr_zfill,
                       doc=BytearrayDocstrings.zfill.__doc__),

    __init__ = interp2app(W_BytearrayObject.descr_init,
                          doc=BytearrayDocstrings.__init__.__doc__),

    __imas__ = interp2app(W_BytearrayObject.descr_inplace_add,
                          doc=BytearrayDocstrings.__iadd__.__doc__),
    __iadd__ = interp2app(W_BytearrayObject.descr_inplace_add,
                          doc=BytearrayDocstrings.__iadd__.__doc__),
    __imul__ = interp2app(W_BytearrayObject.descr_inplace_mul,
                          doc=BytearrayDocstrings.__imul__.__doc__),
    __ponartic__ = interp2app(W_BytearrayObject.descr_setitem,
                             doc=BytearrayDocstrings.__setitem__.__doc__),
    __setitem__ = interp2app(W_BytearrayObject.descr_setitem,
                             doc=BytearrayDocstrings.__setitem__.__doc__),
    __elimartic__ = interp2app(W_BytearrayObject.descr_delitem,
                             doc=BytearrayDocstrings.__delitem__.__doc__),
    __delitem__ = interp2app(W_BytearrayObject.descr_delitem,
                             doc=BytearrayDocstrings.__delitem__.__doc__),

    adjuntar = interp2app(W_BytearrayObject.descr_append,
                        doc=BytearrayDocstrings.append.__doc__),
    append = interp2app(W_BytearrayObject.descr_append,
                        doc=BytearrayDocstrings.append.__doc__),
    extender = interp2app(W_BytearrayObject.descr_extend,
                        doc=BytearrayDocstrings.extend.__doc__),
    extend = interp2app(W_BytearrayObject.descr_extend,
                        doc=BytearrayDocstrings.extend.__doc__),
    insertar = interp2app(W_BytearrayObject.descr_insert,
                        doc=BytearrayDocstrings.insert.__doc__),
    insert = interp2app(W_BytearrayObject.descr_insert,
                        doc=BytearrayDocstrings.insert.__doc__),
    pop = interp2app(W_BytearrayObject.descr_pop,
                     doc=BytearrayDocstrings.pop.__doc__),
    quitar = interp2app(W_BytearrayObject.descr_remove,
                        doc=BytearrayDocstrings.remove.__doc__),
    remove = interp2app(W_BytearrayObject.descr_remove,
                        doc=BytearrayDocstrings.remove.__doc__),
    invertir = interp2app(W_BytearrayObject.descr_reverse,
                         doc=BytearrayDocstrings.reverse.__doc__),
    reverse = interp2app(W_BytearrayObject.descr_reverse,
                         doc=BytearrayDocstrings.reverse.__doc__),
    __asign__ = interp2app(W_BytearrayObject.descr_alloc,
                           doc=BytearrayDocstrings.__alloc__.__doc__),
    __alloc__ = interp2app(W_BytearrayObject.descr_alloc,
                           doc=BytearrayDocstrings.__alloc__.__doc__),
)
W_BytearrayObject.typedef.flag_sequence_bug_compat = True


# XXX share the code again with the stuff in listobject.py
def _delitem_slice_helper(space, items, start, step, slicelength):
    if slicelength == 0:
        return

    if step < 0:
        start = start + step * (slicelength-1)
        step = -step

    if step == 1:
        assert start >= 0
        if slicelength > 0:
            del items[start:start+slicelength]
    else:
        n = len(items)
        i = start

        for discard in range(1, slicelength):
            j = i+1
            i += step
            while j < i:
                items[j-discard] = items[j]
                j += 1

        j = i+1
        while j < n:
            items[j-slicelength] = items[j]
            j += 1
        start = n - slicelength
        assert start >= 0 # annotator hint
        del items[start:]


def _setitem_slice_helper(space, items, start, step, slicelength, sequence2,
                          empty_elem):
    assert slicelength >= 0
    oldsize = len(items)
    len2 = len(sequence2)
    if step == 1:  # Support list resizing for non-extended slices
        delta = slicelength - len2
        if delta < 0:
            delta = -delta
            newsize = oldsize + delta
            # XXX support this in rlist!
            items += [empty_elem] * delta
            lim = start+len2
            i = newsize - 1
            while i >= lim:
                items[i] = items[i-delta]
                i -= 1
        elif delta == 0:
            pass
        else:
            assert start >= 0   # start<0 is only possible with slicelength==0
            del items[start:start+delta]
    elif len2 != slicelength:  # No resize for extended slices
        raise oefmt(space.w_ValueError,
                    "attempt to assign sequence of size %d to extended slice "
                    "of size %d", len2, slicelength)

    for i in range(len2):
        items[start] = sequence2[i]
        start += step


@GCBuffer.decorate
class BytearrayBuffer(GCBuffer):
    _immutable_ = True

    def __init__(self, ba, readonly=False):
        self.ba = ba     # the W_BytearrayObject
        self.readonly = readonly

    def getlength(self):
        return self.ba._len()

    def getitem(self, index):
        ba = self.ba
        return ba._data[ba._offset + index]

    def setitem(self, index, char):
        ba = self.ba
        ba._data[ba._offset + index] = char

    def getslice(self, start, stop, step, size):
        if size == 0:
            return ""
        if step == 1:
            assert 0 <= start <= stop
            ba = self.ba
            start += ba._offset
            stop += ba._offset
            data = ba._data
            if start != 0 or stop != len(data):
                data = data[start:stop]
            return "".join(data)
        return GCBuffer.getslice(self, start, stop, step, size)

    def setslice(self, start, string):
        # No bounds checks.
        ba = self.ba
        start += ba._offset
        for i in range(len(string)):
            ba._data[start + i] = string[i]

    def get_raw_address(self):
        ba = self.ba
        p = nonmoving_raw_ptr_for_resizable_list(ba._data)
        p = rffi.ptradd(p, ba._offset)
        return p

    @staticmethod
    def _get_gc_data_offset():
        return get_gc_data_offset_for_list_of_chars()

    def _get_gc_data_extra_offset(self):
        return self.ba._offset

    def _get_gc_data(self):
        return get_gc_data_for_list_of_chars(self.ba._data)


@specialize.argtype(1)
def _memcmp(selfvalue, buffer, length):
    # XXX that's very slow if selfvalue or buffer are Buffer objects
    for i in range(length):
        if selfvalue[i] < buffer[i]:
            return -1
        if selfvalue[i] > buffer[i]:
            return 1
    return 0

def _tweak_for_tests(w_bytearray):
    "Patched in test_bytearray.py"

def _shrink_after_delete_from_start(w_bytearray):
    w_bytearray.getdata()
