"""The builtin unicode implementation"""

from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin,
    enforceargs)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.mutbuffer import MutableStringBuffer
from rpython.rlib.rstring import StringBuilder, UnicodeBuilder
from rpython.rlib.runicode import (
    make_unicode_escape_function, str_decode_ascii, str_decode_utf_8,
    unicode_encode_ascii, unicode_encode_utf_8, fast_str_decode_ascii)

from pypy.interpreter import unicodehelper
from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.module.unicodedata import unicodedb
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT

__all__ = ['W_UnicodeObject', 'wrapunicode', 'plain_str2unicode',
           'encode_object', 'decode_object', 'unicode_from_object',
           'unicode_from_string', 'unicode_to_decimal_w']


class W_UnicodeObject(W_Root):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_value']

    @enforceargs(uni=unicode)
    def __init__(self, unistr):
        assert isinstance(unistr, unicode)
        self._value = unistr

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        # for testing
        return self._value

    def create_if_subclassed(self):
        if type(self) is W_UnicodeObject:
            return self
        return W_UnicodeObject(self._value)

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_UnicodeObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        s1 = space.unicode_w(self)
        s2 = space.unicode_w(w_other)
        if len(s2) > 1:
            return s1 is s2
        else:            # strings of len <= 1 are unique-ified
            return s1 == s2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        s = space.unicode_w(self)
        if len(s) > 1:
            uid = compute_unique_id(s)
        else:            # strings of len <= 1 are unique-ified
            if len(s) == 1:
                base = ~ord(s[0])      # negative base values
            else:
                base = 257       # empty unicode string: base value 257
            uid = (base << IDTAG_SHIFT) | IDTAG_SPECIAL
        return space.newint(uid)

    def str_w(self, space):
        return space.text_w(space.str(self))

    def unicode_w(self, space):
        return self._value

    def readbuf_w(self, space):
        from rpython.rlib.rstruct.unichar import pack_unichar, UNICODE_SIZE
        buf = MutableStringBuffer(len(self._value) * UNICODE_SIZE)
        pos = 0
        for unich in self._value:
            pack_unichar(unich, buf, pos)
            pos += UNICODE_SIZE
        return StringBuffer(buf.finish())

    def writebuf_w(self, space):
        raise oefmt(space.w_TypeError,
                    "no puede usar unicod como búfer modificable")

    charbuf_w = str_w

    def listview_unicode(self):
        return _create_list_from_unicode(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            raise oefmt(space.w_TypeError,
                         "ord() anticipó un carácter, pero palabra de tamaño %d "
                         "encontrado", len(self._value))
        return space.newint(ord(self._value[0]))

    def _new(self, value):
        return W_UnicodeObject(value)

    def _new_from_list(self, value):
        return W_UnicodeObject(u''.join(value))

    def _empty(self):
        return W_UnicodeObject.EMPTY

    def _len(self):
        return len(self._value)

    _val = unicode_w

    @staticmethod
    def _use_rstr_ops(space, w_other):
        # Always return true because we always need to copy the other
        # operand(s) before we can do comparisons
        return True

    @staticmethod
    def _op_val(space, w_other, strict=None):
        if isinstance(w_other, W_UnicodeObject):
            return w_other._value
        if space.isinstance_w(w_other, space.w_bytes):
            return unicode_from_string(space, w_other)._value
        if strict:
            raise oefmt(space.w_TypeError,
                "%s arg tiene que ser Nada, unicod o pal", strict)
        return unicode_from_encoded_object(
            space, w_other, None, "strict")._value

    def _chr(self, char):
        assert len(char) == 1
        return unicode(char)[0]

    _builder = UnicodeBuilder

    def _isupper(self, ch):
        return unicodedb.isupper(ord(ch))

    def _islower(self, ch):
        return unicodedb.islower(ord(ch))

    def _isnumeric(self, ch):
        return unicodedb.isnumeric(ord(ch))

    def _istitle(self, ch):
        return unicodedb.isupper(ord(ch)) or unicodedb.istitle(ord(ch))

    def _isspace(self, ch):
        return unicodedb.isspace(ord(ch))

    def _isalpha(self, ch):
        return unicodedb.isalpha(ord(ch))

    def _isalnum(self, ch):
        return unicodedb.isalnum(ord(ch))

    def _isdigit(self, ch):
        return unicodedb.isdigit(ord(ch))

    def _isdecimal(self, ch):
        return unicodedb.isdecimal(ord(ch))

    def _iscased(self, ch):
        return unicodedb.iscased(ord(ch))

    def _islinebreak(self, ch):
        return unicodedb.islinebreak(ord(ch))

    def _upper(self, ch):
        return unichr(unicodedb.toupper(ord(ch)))

    def _lower(self, ch):
        return unichr(unicodedb.tolower(ord(ch)))

    def _title(self, ch):
        return unichr(unicodedb.totitle(ord(ch)))

    def _newlist_unwrapped(self, space, lst):
        return space.newlist_unicode(lst)

    @staticmethod
    @unwrap_spec(w_string=WrappedDefault(""))
    def descr_new(space, w_unicodetype, w_string, w_encoding=None,
                  w_errors=None):
        # NB. the default value of w_obj is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = w_string

        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        # convoluted logic for the case when unicode subclass has a __unicode__
        # method, we need to call this method
        is_precisely_unicode = space.is_w(space.type(w_obj), space.w_unicode)
        if (is_precisely_unicode or
            (space.isinstance_w(w_obj, space.w_unicode) and
             space.findattr(w_obj, space.newtext('__unicode__')) is None)):
            if encoding is not None or errors is not None:
                raise oefmt(space.w_TypeError,
                            "decodificar Unicod no es apoyado")
            if (is_precisely_unicode and
                space.is_w(w_unicodetype, space.w_unicode)):
                return w_obj
            w_value = w_obj
        else:
            if encoding is None and errors is None:
                w_value = unicode_from_object(space, w_obj)
            else:
                w_value = unicode_from_encoded_object(space, w_obj,
                                                      encoding, errors)
            if space.is_w(w_unicodetype, space.w_unicode):
                return w_value

        assert isinstance(w_value, W_UnicodeObject)
        w_newobj = space.allocate_instance(W_UnicodeObject, w_unicodetype)
        W_UnicodeObject.__init__(w_newobj, w_value._value)
        return w_newobj

    def descr_repr(self, space):
        chars = self._value
        size = len(chars)
        s = _repr_function(chars, size, "strict")
        return space.newtext(s)

    def descr_str(self, space):
        return encode_object(space, self, None, None)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        x -= (x == -1) # convert -1 to -2 without creating a bridge
        return space.newint(x)

    def descr_eq(self, space, w_other):
        try:
            res = self._val(space) == self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicod comparasión igual fracasó de convertir ambos "
                       "argumentos a Unocod - interpretándolos como ser "
                       "desiguales")
                space.warn(space.newtext(msg), space.w_UnicodeWarning)
                return space.w_False
            raise
        return space.newbool(res)

    def descr_ne(self, space, w_other):
        try:
            res = self._val(space) != self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            if (e.match(space, space.w_UnicodeDecodeError) or
                e.match(space, space.w_UnicodeEncodeError)):
                msg = ("Unicod comparasión desigual fracasó de convertir ambos "
                       "argumentos a Unocod - interpretándolos como ser "
                       "desiguales")
                space.warn(space.newtext(msg), space.w_UnicodeWarning)
                return space.w_True
            raise
        return space.newbool(res)

    def descr_lt(self, space, w_other):
        try:
            res = self._val(space) < self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_le(self, space, w_other):
        try:
            res = self._val(space) <= self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_gt(self, space, w_other):
        try:
            res = self._val(space) > self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_ge(self, space, w_other):
        try:
            res = self._val(space) >= self._op_val(space, w_other)
        except OperationError as e:
            if e.match(space, space.w_TypeError):
                return space.w_NotImplemented
            raise
        return space.newbool(res)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=True)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_unicode):
            w_format_spec = space.call_function(space.w_unicode, w_format_spec)
        spec = space.unicode_w(w_format_spec)
        formatter = newformat.unicode_formatter(space, spec)
        self2 = unicode_from_object(space, self)
        assert isinstance(self2, W_UnicodeObject)
        return formatter.format_string(self2._value)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=True)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=True)

    def descr_translate(self, space, w_table):
        selfvalue = self._value
        w_sys = space.getbuiltinmodule('sys')
        maxunicode = space.int_w(space.getattr(w_sys,
                                               space.newtext("maxunicode")))
        result = []
        for unichar in selfvalue:
            try:
                w_newval = space.getitem(w_table, space.newint(ord(unichar)))
            except OperationError as e:
                if e.match(space, space.w_LookupError):
                    result.append(unichar)
                else:
                    raise
            else:
                if space.is_w(w_newval, space.w_None):
                    continue
                elif space.isinstance_w(w_newval, space.w_int):
                    newval = space.int_w(w_newval)
                    if newval < 0 or newval > maxunicode:
                        raise oefmt(space.w_TypeError,
                                    "mapar carácteres tiene que ser en rango(%s)",
                                    hex(maxunicode + 1))
                    result.append(unichr(newval))
                elif space.isinstance_w(w_newval, space.w_unicode):
                    result.append(space.unicode_w(w_newval))
                else:
                    raise oefmt(space.w_TypeError,
                                "mapar carácteres tiene que volver entero, Nada "
                                "o unicod")
        return W_UnicodeObject(u''.join(result))

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        encoding, errors = _get_encoding_and_errors(space, w_encoding,
                                                    w_errors)
        return encode_object(space, self, encoding, errors)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_unicode(w_list)
        if l is not None:
            if len(l) == 1:
                return space.newunicode(l[0])
            return space.newunicode(self._val(space).join(l))
        return self._StringMethods_descr_join(space, w_list)

    def _join_return_one(self, space, w_obj):
        return space.is_w(space.type(w_obj), space.w_unicode)

    def _join_check_item(self, space, w_obj):
        if (space.isinstance_w(w_obj, space.w_bytes) or
            space.isinstance_w(w_obj, space.w_unicode)):
            return 0
        return 1

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.unicode_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import unicode_template_formatter
        tformat = unicode_template_formatter(space, space.unicode_w(self))
        return tformat.formatter_field_name_split()

    def descr_isdecimal(self, space):
        return self._is_generic(space, '_isdecimal')

    def descr_isnumeric(self, space):
        return self._is_generic(space, '_isnumeric')

    def descr_islower(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.isupper(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.islower(ord(uchar)):
                cased = True
        return space.newbool(cased)

    def descr_isupper(self, space):
        cased = False
        for uchar in self._value:
            if (unicodedb.islower(ord(uchar)) or
                unicodedb.istitle(ord(uchar))):
                return space.w_False
            if not cased and unicodedb.isupper(ord(uchar)):
                cased = True
        return space.newbool(cased)

    _starts_ends_unicode = True


def wrapunicode(space, uni):
    return W_UnicodeObject(uni)


def plain_str2unicode(space, s):
    try:
        return unicode(s)
    except UnicodeDecodeError:
        for i in range(len(s)):
            if ord(s[i]) > 127:
                raise OperationError(
                    space.w_UnicodeDecodeError,
                    space.newtuple([
                    space.newtext('ascii'),
                    space.newbytes(s),
                    space.newint(i),
                    space.newint(i+1),
                    space.newtext("ordinal no en rango(128)")]))
        assert False, "unreachable"


# stuff imported from bytesobject for interoperability


# ____________________________________________________________

def getdefaultencoding(space):
    return space.sys.defaultencoding


def _get_encoding_and_errors(space, w_encoding, w_errors):
    encoding = None if w_encoding is None else space.text_w(w_encoding)
    errors = None if w_errors is None else space.text_w(w_errors)
    return encoding, errors


def encode_object(space, w_object, encoding, errors):
    if encoding is None:
        # Get the encoder functions as a wrapped object.
        # This lookup is cached.
        w_encoder = space.sys.get_w_default_encoder()
    else:
        if errors is None or errors == 'strict':
            if encoding == 'ascii':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.newbytes(unicode_encode_ascii(
                        u, len(u), None, errorhandler=eh))
            if encoding == 'utf-8':
                u = space.unicode_w(w_object)
                eh = unicodehelper.encode_error_handler(space)
                return space.newbytes(unicode_encode_utf_8(
                        u, len(u), None, errorhandler=eh,
                        allow_surrogates=True))
        from pypy.module._codecs.interp_codecs import lookup_codec
        w_encoder = space.getitem(lookup_codec(space, encoding), space.newint(0))
    if errors is None:
        w_errors = space.newtext('strict')
    else:
        w_errors = space.newtext(errors)
    w_restuple = space.call_function(w_encoder, w_object, w_errors)
    w_retval = space.getitem(w_restuple, space.newint(0))
    if not space.isinstance_w(w_retval, space.w_bytes):
        raise oefmt(space.w_TypeError,
                    "codificador no volvió un objeto palabra (tipo '%T')",
                    w_retval)
    return w_retval


def decode_object(space, w_obj, encoding, errors):
    if encoding is None:
        encoding = getdefaultencoding(space)
    if errors is None or errors == 'strict':
        if encoding == 'ascii':
            # XXX error handling
            s = space.charbuf_w(w_obj)
            try:
                u = fast_str_decode_ascii(s)
            except ValueError:
                eh = unicodehelper.decode_error_handler(space)
                u = str_decode_ascii(     # try again, to get the error right
                    s, len(s), None, final=True, errorhandler=eh)[0]
            return space.newunicode(u)
        if encoding == 'utf-8':
            s = space.charbuf_w(w_obj)
            eh = unicodehelper.decode_error_handler(space)
            return space.newunicode(str_decode_utf_8(
                    s, len(s), None, final=True, errorhandler=eh,
                    allow_surrogates=True)[0])
    w_codecs = space.getbuiltinmodule("_codecs")
    w_decode = space.getattr(w_codecs, space.newtext("decode"))
    if errors is None:
        w_retval = space.call_function(w_decode, w_obj, space.newtext(encoding))
    else:
        w_retval = space.call_function(w_decode, w_obj, space.newtext(encoding),
                                       space.newtext(errors))
    return w_retval

def unicode_from_encoded_object(space, w_obj, encoding, errors):
    # explicitly block bytearray on 2.7
    from .bytearrayobject import W_BytearrayObject
    if isinstance(w_obj, W_BytearrayObject):
        raise oefmt(space.w_TypeError, "decodificar bytematríz no está apoyado")

    w_retval = decode_object(space, w_obj, encoding, errors)
    if not space.isinstance_w(w_retval, space.w_unicode):
        raise oefmt(space.w_TypeError,
                    "decodificador no volvió un objeto unicod (tipo '%T')",
                    w_retval)
    assert isinstance(w_retval, W_UnicodeObject)
    return w_retval


def unicode_from_object(space, w_obj):
    if space.is_w(space.type(w_obj), space.w_unicode):
        return w_obj
    elif space.is_w(space.type(w_obj), space.w_bytes):
        w_res = w_obj
    else:
        w_unicode_method = space.lookup(w_obj, "__unicode__")
        # obscure workaround: for the next two lines see
        # test_unicode_conversion_with__str__
        if w_unicode_method is None:
            if space.isinstance_w(w_obj, space.w_unicode):
                return space.newunicode(space.unicode_w(w_obj))
            w_unicode_method = space.lookup(w_obj, "__str__")
        if w_unicode_method is not None:
            w_res = space.get_and_call_function(w_unicode_method, w_obj)
        else:
            w_res = space.str(w_obj)
        if space.isinstance_w(w_res, space.w_unicode):
            return w_res
    return unicode_from_encoded_object(space, w_res, None, "strict")


def unicode_from_string(space, w_bytes):
    # this is a performance and bootstrapping hack
    encoding = getdefaultencoding(space)
    if encoding != 'ascii':
        return unicode_from_encoded_object(space, w_bytes, encoding, "strict")
    s = space.bytes_w(w_bytes)
    try:
        return W_UnicodeObject(s.decode("ascii"))
    except UnicodeDecodeError:
        # raising UnicodeDecodeError is messy, "please crash for me"
        return unicode_from_encoded_object(space, w_bytes, "ascii", "strict")


class UnicodeDocstrings:
    """unicod(objeto='') -> objeto unicod
    unicod(palabra[, codificación[, errores]]) -> objeto unicod

    Crear un objeto unicod nuevo de la palabra codificada dada.
    El estándar de codificación es la codificación estándar de palabras.
    errores pueden ser 'estricto', 'reemplazar' o 'ignorar' y el estándar es
    'estricto'.

    """

    def __add__():
        """x.__mas__(y) <==> x+y"""

    def __contains__():
        """x.__contiene__(y) <==> y en x"""

    def __eq__():
        """x.__ig__(y) <==> x==y"""

    def __format__():
        """S.__formato__(espec_formato) -> unicod

        Volver una versión formateado de S, describido por espec_formato.
        """

    def __ge__():
        """x.__mai__(y) <==> x>=y"""

    def __getattribute__():
        """x.__sacaatributo__('nombre') <==> x.nombre"""

    def __getitem__():
        """x.__sacaartic__(y) <==> x[y]"""

    def __getnewargs__():
        ""

    def __getslice__():
        """x.__sacaparte__(i, j) <==> x[i:j]

        Uso de índices negativos no es apoyado.
        """

    def __gt__():
        """x.__maq__(y) <==> x>y"""

    def __hash__():
        """x.__hash__() <==> hash(x)"""

    def __le__():
        """x.__mei__(y) <==> x<=y"""

    def __len__():
        """x.__tam__() <==> len(x)"""

    def __lt__():
        """x.__meq__(y) <==> x<y"""

    def __mod__():
        """x.__mod__(y) <==> x%y"""

    def __rmod__():
        """x.__dmod__(y) <==> y%x"""

    def __mul__():
        """x.__mul__(n) <==> x*n"""

    def __ne__():
        """x.__ni__(y) <==> x!=y"""

    def __repr__():
        """x.__repr__() <==> repr(x)"""

    def __rmod__():
        """x.__dmod__(y) <==> y%x"""

    def __rmul__():
        """x.__dmul__(n) <==> n*x"""

    def __sizeof__():
        """S.__tamde__() -> tamaño de S en memoria, en bytes"""

    def __str__():
        """x.__pal__() <==> pal(x)"""

    def capitalize():
        """S.mayuscular() -> unicod

        Volver una versión mayúscula de S, i.e. el carácter primero es en
        mayúsculo y el resto en minúsculo.
        """
    def center():
        """S.centro(ancho[, llenacarác]) -> unicod

        Volver S en el centro de una palabra unicod de tamaño ancho. Relleno
        es hecho con el llenacarác especificado (estándar es un espacio).
        """

    def count():
        """S.total(sub[, empieza[, fin]]) -> ent

        Volver el número de casos de la sub-palabra sub no sobrepuestos en
        palabra unicod S[empieza:fin]. Argumentos opcionales empieza y fin
        son interpretados como en notación cortar.
        """

    def decode():
        """S.decodificar(codificación=Nada, errores='estricto') ->
        palabra o unicod

        Decodificar S usando el codec registrado para codificación.
        errores puede ser 'estricto', es decir los errores llaman UnicodeDecodeError.
        Otros valores posibles son 'ignorar' y 'reemplazar', tanto como
        cualquier otro nombre registrado con codecs.register_error que puede
        llamar UnicodeDecodeErrors.
        """

    def encode():
        """S.codificar(codificación=Nada, errores='estricto') ->
        palabra o unicod

        Codificar S usando el codec registrado para codificación.
        errores puede ser 'estricto', es decir los errores llaman UnicodeDecodeError.
        Otros valores posibles son 'ignorar' y 'reemplazar', tanto como
        cualquier otro nombre registrado con codecs.register_error que puede
        llamar UnicodeDecodeErrors.
        """

    def endswith():
        """S.terminacon(sufijo[, empieza[, fin]]) -> bool

        Volver Cierto si S termina con el sufijo especificado, Falso si no.
        Con empieza opcional, probar S empezando en esa posición.
        Con fin opcional, termina comparando S en esa posición.
        sufijo también puede ser un tuple de palabras para probar.
        """

    def expandtabs():
        """S.expandtabs([tabtamaño]) -> unicod

        Volver una copia de S donde todos carácteres tab son expandidos
        usando espacios. Si tabtamaño no está dado, un tamaño de 8
        carácteres está usado.
        """

    def find():
        """S.encontrar(sub[, empieza[, fin]]) -> ent

        Volver la índice más baja en S donde sub-palabra sub está
        encontrada, para que sub esté contenido en S[empieza:fin].
        Argumentos opcionales empieza y fin son interpretados como
        en notación cortar.

        Volver -1 si fracasa.
        """

    def format():
        """S.formato(*args, **kwargs) -> unicod

        Volver una versión formateado de S, usando substituciones de args y
        kwargs. Las substituciones son identificados por llaves ('{' y '}').
        """

    def index():
        """S.indice(sub[, empieza[, fin]]) -> ent

        Como S.encontrar() pero llamar ValueError cuando la sub-palabra no
        está encontradaa.
        """

    def isalnum():
        """S.esalnum() -> bool

        Volver Cierto si todos carácateres en S son alfanuméricas y
        hay por lo menos un carácter en S, Falso si no.
        """

    def isalpha():
        """S.esalfa() -> bool

        Volver Cierto si todos carácateres en S son alfabéticas y
        hay por lo menos un carácter en S, Falso si no.
        """

    def isdecimal():
        """S.esdecimal() -> bool

        Volver Cierto si hay solamente carácteres decimales en S,
        Falso si no.
        """

    def isdigit():
        """S.esdig() -> bool

        Volver Cierto si todos carácateres en S son dígitos y
        hay por lo menos un carácter en S, Falso si no.
        """

    def islower():
        """S.esminusc() -> bool

        Volver Cierto si todos carácateres en S son en minúsculo y
        hay por lo menos un carácter en S, Falso si no.
        """

    def isnumeric():
        """S.esnumerico() -> bool

        Volver Cierto si todos carácateres en S son numéricos, Falso si no.
        """

    def isspace():
        """S.esespac() -> bool

        Volver Cierto si todos carácateres en S son espacio blanco y
        hay por lo menos un carácter en S, Falso si no.
        """

    def istitle():
        """S.estitulo() -> bool

        Volver Cierto si S está puesto en formato titulo y hay por lo menos
        un carácter en S, i.e. carácteres mayúsculos solo pueden seguir
        carácteres sin caso y minúsculos solo carácteres con caso.
        Volver Falso si no.
        """

    def isupper():
        """S.esmayusc() -> bool

        Volver Cierto si todos carácteres en S están en mayúsculo y hay por
        lo menos un carácter con caso en S, Falso si no.
        """

    def join():
        """S.juntar(iterable) -> unicod

        Volver una palabra que es la combinación de las palabras en el
        iterable. El separador entre los elementos es S.
        """

    def ljust():
        """S.ijust(ancho[, llenacarac]) -> ent

        Volver S justificado a la izquierda en una palabra unicod de tamaño
        ancho. Relleno está hecho con llenecarac (estándar es un espacio).
        """

    def lower():
        """S.minusc() -> unicod

        Volver una copia de la palabra S convertida a minúscula.
        """

    def lstrip():
        """S.idecapar([caracs]) -> unicod

        Volver una copia de la palabra S con espacio blanco al frente
        quitado. Si caracs está dado y no es Nada, quitar carácteres en
        caracs en lugar de espacio blano. Si caracs es una palabra, no será
        convertida a unicod antes de decapar.
        """

    def partition():
        """S.particion(sep) -> (cabeza, sep, cola)

        Buscar el separador sep en S, y quitar el parte antes de él, él mismo
        y el parte después de él. Si el separador no está encontrado, volver
        S y dos palabras vacías.
        """

    def replace():
        """S.reemplazar(vieja, nueva[, total]) -> unicod

        Volver una copia de S con todos casos de sub-palabra vieja
        reemplazada por nueva. Sel argumento opcional total está
        dado, solo los primeros total caso son reemplazados.
        """

    def rfind():
        """S.dencontrar(sub[, empieza[, fin]]) -> ent

        Volver la índice más alta en S donde sub-palabra sub está
        encontradao, para que sub esté contenida entre S[empieza:fin].
        Argumentos opcionales empieza y fin son interpretados como
        en notación cortar.

        Volver -1 si fracasa.
        """

    def rindex():
        """S.dindice(sub[, empieza[, fin]]) -> ent

        Como S.dencontrar() pero llamar ValueError cuando la sub-palabra no
        está encontrada.
        """

    def rjust():
        """S.ijust(ancho[, llenacarac]) -> unicod

        Volver S justificado a la derecha en una palabra unicod de tamaño ancho.
        Relleno es hecho con llenacarac (estándar es un espacio).
        """

    def rpartition():
        """S.dparticion(sep) -> (cabeza, sep, cola)

        Buscar el separador sep en S, empezando al final de S, y volver la parte
        antes de él, él mismo y la parte después de él. Si el separador no está
        encontrado, volver dos palabras vacías y S.
        """

    def rsplit():
        """S.dquebrar(sep=Nada, maxquebrar=-1) -> lista de palabras

        Volver una lista de las palabras en S, usando sep como la palabra
        delimitadora, empezando al final de la palabra y moviendo al frente.
        Si maxquebrar está dado, a lo máximo maxquebrar quebraciónes están
        hechos. Si sep no está especificada, cuaquiera palabra de espacio blanco
        es un separador.
        """

    def rstrip():
        """S.ddecapar([caracs]) -> unicode

        Volver una copia de la palabra S con espacio blanco al final
        quitado. Si caracs está dado y no es Nada, quitar carácteres en
        caracs en lugar de espacio blano. Si caracs es una palabra, no será
        convertida a unicod antes de decapar.
        """

    def split():
        """S.split(sep=None, maxsplit=-1) -> list of strings

        Volver una lista de las palabras en S, usando sep como la palabra
        delimitadora.
        Si maxquebrar está dado, a lo máximo maxquebrar quebraciónes están
        hechos. Si sep no está especificada, cuaquiera palabra de espacio blanco
        es un separador y palabras vaciás están quitadas del resultado.
        """

    def splitlines():
        """S.quebrarlineas(guardarcolas=False) -> lista de palabras

        Volver una lista de las líneas en S, rompiendo en límites de las
        líneas. Rompes de línea no son incluidos en el resultado a menos
        que guardarcolas está dado y es Cierto.
        """

    def startswith():
        """S.empcon(prefijo[, empieza[, fin]]) -> bool

        Vuelve Cierto si S empieza con el prefijo especificado, Falso si no.
        Con empieza opcional, prueba S empezando en esta posición.
        Con fin opcional, pare comparando S en esta posición.
        prefijo también puede ser un tuple de palabras para probar.
        """

    def strip():
        """S.decapar([cacars]) -> unicod

        Volver una copia de la palabra S con espacio blanco al frente y al
        final quitado.
        Si caracs está dado y no es Nada, quitar carácteres en caracs en lugar
        de espacio blaco.
        Si carács es una palabra, no será convertida a unicod antes de
        decapar.
        """

    def swapcase():
        """S.minmayusc() -> unicod

        Volver una copia de S con todos los carácteres mayúsculos convertidos
        a minúsculo, y vice versa.
        """

    def title():
        """S.titulo() -> unicod

        Volver una versión de S puesto como titulo, i.e. palabras empiezan
        con carácteres en caso titulo, todos otros carácteres en minúsculo.
        """

    def translate():
        """S.traducir(mesa) -> unicod

        Volver una copia de la palabra S, donde todos carácteres han sido
        mapados en la mesa de traducción dada, que tiene que ser una mapa de
        ordinales unicod a ordinales unicod, palabras unicod o Nada.
        Carácters sin mapa no cambian. Carácteres mapados a Nada son quitados.
        """

    def upper():
        """S.mayusc() -> unicod

        Volver una copia de S convertido a mayúsculo.
        """

    def zfill():
        """S.cllenar(ancho) -> unicod

        Rellenar una palabra numérica S con ceros a la izquiera, para llenar
        un campo de ancho especificado. S nunca está truncado.
        """


W_UnicodeObject.typedef = TypeDef(
    "unicode", basestring_typedef,
    __nuevo__ = interp2app(W_UnicodeObject.descr_new),
    __new__ = interp2app(W_UnicodeObject.descr_new),
    __doc__ = UnicodeDocstrings.__doc__,

    __repr__ = interp2app(W_UnicodeObject.descr_repr,
                          doc=UnicodeDocstrings.__repr__.__doc__),
    __pal__ = interp2app(W_UnicodeObject.descr_str,
                         doc=UnicodeDocstrings.__str__.__doc__),
    __str__ = interp2app(W_UnicodeObject.descr_str,
                         doc=UnicodeDocstrings.__str__.__doc__),
    __hash__ = interp2app(W_UnicodeObject.descr_hash,
                          doc=UnicodeDocstrings.__hash__.__doc__),

    __ig__ = interp2app(W_UnicodeObject.descr_eq,
                        doc=UnicodeDocstrings.__eq__.__doc__),
    __eq__ = interp2app(W_UnicodeObject.descr_eq,
                        doc=UnicodeDocstrings.__eq__.__doc__),
    __ni__ = interp2app(W_UnicodeObject.descr_ne,
                        doc=UnicodeDocstrings.__ne__.__doc__),
    __ne__ = interp2app(W_UnicodeObject.descr_ne,
                        doc=UnicodeDocstrings.__ne__.__doc__),
    __meq__ = interp2app(W_UnicodeObject.descr_lt,
                        doc=UnicodeDocstrings.__lt__.__doc__),
    __lt__ = interp2app(W_UnicodeObject.descr_lt,
                        doc=UnicodeDocstrings.__lt__.__doc__),
    __mei__ = interp2app(W_UnicodeObject.descr_le,
                        doc=UnicodeDocstrings.__le__.__doc__),
    __le__ = interp2app(W_UnicodeObject.descr_le,
                        doc=UnicodeDocstrings.__le__.__doc__),
    __maq__ = interp2app(W_UnicodeObject.descr_gt,
                        doc=UnicodeDocstrings.__gt__.__doc__),
    __gt__ = interp2app(W_UnicodeObject.descr_gt,
                        doc=UnicodeDocstrings.__gt__.__doc__),
    __mai__ = interp2app(W_UnicodeObject.descr_ge,
                        doc=UnicodeDocstrings.__ge__.__doc__),
    __ge__ = interp2app(W_UnicodeObject.descr_ge,
                        doc=UnicodeDocstrings.__ge__.__doc__),

    __tam__ = interp2app(W_UnicodeObject.descr_len,
                         doc=UnicodeDocstrings.__len__.__doc__),
    __len__ = interp2app(W_UnicodeObject.descr_len,
                         doc=UnicodeDocstrings.__len__.__doc__),
    __contiene__ = interp2app(W_UnicodeObject.descr_contains,
                              doc=UnicodeDocstrings.__contains__.__doc__),
    __contains__ = interp2app(W_UnicodeObject.descr_contains,
                              doc=UnicodeDocstrings.__contains__.__doc__),

    __mas__ = interp2app(W_UnicodeObject.descr_add,
                         doc=UnicodeDocstrings.__add__.__doc__),
    __add__ = interp2app(W_UnicodeObject.descr_add,
                         doc=UnicodeDocstrings.__add__.__doc__),
    __mul__ = interp2app(W_UnicodeObject.descr_mul,
                         doc=UnicodeDocstrings.__mul__.__doc__),
    __dmul__ = interp2app(W_UnicodeObject.descr_mul,
                          doc=UnicodeDocstrings.__rmul__.__doc__),
    __rmul__ = interp2app(W_UnicodeObject.descr_mul,
                          doc=UnicodeDocstrings.__rmul__.__doc__),

    __sacaartic__ = interp2app(W_UnicodeObject.descr_getitem,
                             doc=UnicodeDocstrings.__getitem__.__doc__),
    __getitem__ = interp2app(W_UnicodeObject.descr_getitem,
                             doc=UnicodeDocstrings.__getitem__.__doc__),
    __sacaparte__ = interp2app(W_UnicodeObject.descr_getslice,
                              doc=UnicodeDocstrings.__getslice__.__doc__),
    __getslice__ = interp2app(W_UnicodeObject.descr_getslice,
                              doc=UnicodeDocstrings.__getslice__.__doc__),

    mayuscular = interp2app(W_UnicodeObject.descr_capitalize,
                            doc=UnicodeDocstrings.capitalize.__doc__),
    capitalize = interp2app(W_UnicodeObject.descr_capitalize,
                            doc=UnicodeDocstrings.capitalize.__doc__),
    centro = interp2app(W_UnicodeObject.descr_center,
                        doc=UnicodeDocstrings.center.__doc__),
    center = interp2app(W_UnicodeObject.descr_center,
                        doc=UnicodeDocstrings.center.__doc__),
    total = interp2app(W_UnicodeObject.descr_count,
                       doc=UnicodeDocstrings.count.__doc__),
    count = interp2app(W_UnicodeObject.descr_count,
                       doc=UnicodeDocstrings.count.__doc__),
    decodificar = interp2app(W_UnicodeObject.descr_decode,
                        doc=UnicodeDocstrings.decode.__doc__),
    decode = interp2app(W_UnicodeObject.descr_decode,
                        doc=UnicodeDocstrings.decode.__doc__),
    codificar = interp2app(W_UnicodeObject.descr_encode,
                        doc=UnicodeDocstrings.encode.__doc__),
    encode = interp2app(W_UnicodeObject.descr_encode,
                        doc=UnicodeDocstrings.encode.__doc__),
    expandtabs = interp2app(W_UnicodeObject.descr_expandtabs,
                            doc=UnicodeDocstrings.expandtabs.__doc__),
    encontrar = interp2app(W_UnicodeObject.descr_find,
                      doc=UnicodeDocstrings.find.__doc__),
    find = interp2app(W_UnicodeObject.descr_find,
                      doc=UnicodeDocstrings.find.__doc__),
    decontrar = interp2app(W_UnicodeObject.descr_rfind,
                       doc=UnicodeDocstrings.rfind.__doc__),
    rfind = interp2app(W_UnicodeObject.descr_rfind,
                       doc=UnicodeDocstrings.rfind.__doc__),
    indice = interp2app(W_UnicodeObject.descr_index,
                       doc=UnicodeDocstrings.index.__doc__),
    index = interp2app(W_UnicodeObject.descr_index,
                       doc=UnicodeDocstrings.index.__doc__),
    dincide = interp2app(W_UnicodeObject.descr_rindex,
                        doc=UnicodeDocstrings.rindex.__doc__),
    rindex = interp2app(W_UnicodeObject.descr_rindex,
                        doc=UnicodeDocstrings.rindex.__doc__),
    esalnum = interp2app(W_UnicodeObject.descr_isalnum,
                         doc=UnicodeDocstrings.isalnum.__doc__),
    isalnum = interp2app(W_UnicodeObject.descr_isalnum,
                         doc=UnicodeDocstrings.isalnum.__doc__),
    esalfa = interp2app(W_UnicodeObject.descr_isalpha,
                         doc=UnicodeDocstrings.isalpha.__doc__),
    isalpha = interp2app(W_UnicodeObject.descr_isalpha,
                         doc=UnicodeDocstrings.isalpha.__doc__),
    esdecimal = interp2app(W_UnicodeObject.descr_isdecimal,
                           doc=UnicodeDocstrings.isdecimal.__doc__),
    isdecimal = interp2app(W_UnicodeObject.descr_isdecimal,
                           doc=UnicodeDocstrings.isdecimal.__doc__),
    esdig = interp2app(W_UnicodeObject.descr_isdigit,
                         doc=UnicodeDocstrings.isdigit.__doc__),
    isdigit = interp2app(W_UnicodeObject.descr_isdigit,
                         doc=UnicodeDocstrings.isdigit.__doc__),
    esminusc = interp2app(W_UnicodeObject.descr_islower,
                         doc=UnicodeDocstrings.islower.__doc__),
    islower = interp2app(W_UnicodeObject.descr_islower,
                         doc=UnicodeDocstrings.islower.__doc__),
    esnumerico = interp2app(W_UnicodeObject.descr_isnumeric,
                           doc=UnicodeDocstrings.isnumeric.__doc__),
    isnumeric = interp2app(W_UnicodeObject.descr_isnumeric,
                           doc=UnicodeDocstrings.isnumeric.__doc__),
    esespac = interp2app(W_UnicodeObject.descr_isspace,
                         doc=UnicodeDocstrings.isspace.__doc__),
    isspace = interp2app(W_UnicodeObject.descr_isspace,
                         doc=UnicodeDocstrings.isspace.__doc__),
    estitulo = interp2app(W_UnicodeObject.descr_istitle,
                         doc=UnicodeDocstrings.istitle.__doc__),
    istitle = interp2app(W_UnicodeObject.descr_istitle,
                         doc=UnicodeDocstrings.istitle.__doc__),
    esmayusc = interp2app(W_UnicodeObject.descr_isupper,
                         doc=UnicodeDocstrings.isupper.__doc__),
    isupper = interp2app(W_UnicodeObject.descr_isupper,
                         doc=UnicodeDocstrings.isupper.__doc__),
    juntar = interp2app(W_UnicodeObject.descr_join,
                      doc=UnicodeDocstrings.join.__doc__),
    join = interp2app(W_UnicodeObject.descr_join,
                      doc=UnicodeDocstrings.join.__doc__),
    ijust = interp2app(W_UnicodeObject.descr_ljust,
                       doc=UnicodeDocstrings.ljust.__doc__),
    ljust = interp2app(W_UnicodeObject.descr_ljust,
                       doc=UnicodeDocstrings.ljust.__doc__),
    djust = interp2app(W_UnicodeObject.descr_rjust,
                       doc=UnicodeDocstrings.rjust.__doc__),
    rjust = interp2app(W_UnicodeObject.descr_rjust,
                       doc=UnicodeDocstrings.rjust.__doc__),
    minusr = interp2app(W_UnicodeObject.descr_lower,
                       doc=UnicodeDocstrings.lower.__doc__),
    lower = interp2app(W_UnicodeObject.descr_lower,
                       doc=UnicodeDocstrings.lower.__doc__),
    particion = interp2app(W_UnicodeObject.descr_partition,
                           doc=UnicodeDocstrings.partition.__doc__),
    partition = interp2app(W_UnicodeObject.descr_partition,
                           doc=UnicodeDocstrings.partition.__doc__),
    dparticion = interp2app(W_UnicodeObject.descr_rpartition,
                            doc=UnicodeDocstrings.rpartition.__doc__),
    rpartition = interp2app(W_UnicodeObject.descr_rpartition,
                            doc=UnicodeDocstrings.rpartition.__doc__),
    reemplazar = interp2app(W_UnicodeObject.descr_replace,
                         doc=UnicodeDocstrings.replace.__doc__),
    replace = interp2app(W_UnicodeObject.descr_replace,
                         doc=UnicodeDocstrings.replace.__doc__),
    quebrar = interp2app(W_UnicodeObject.descr_split,
                       doc=UnicodeDocstrings.split.__doc__),
    split = interp2app(W_UnicodeObject.descr_split,
                       doc=UnicodeDocstrings.split.__doc__),
    dquebrar = interp2app(W_UnicodeObject.descr_rsplit,
                        doc=UnicodeDocstrings.rsplit.__doc__),
    rsplit = interp2app(W_UnicodeObject.descr_rsplit,
                        doc=UnicodeDocstrings.rsplit.__doc__),
    quebrarlineas = interp2app(W_UnicodeObject.descr_splitlines,
                            doc=UnicodeDocstrings.splitlines.__doc__),
    splitlines = interp2app(W_UnicodeObject.descr_splitlines,
                            doc=UnicodeDocstrings.splitlines.__doc__),
    empcon = interp2app(W_UnicodeObject.descr_startswith,
                            doc=UnicodeDocstrings.startswith.__doc__),
    startswith = interp2app(W_UnicodeObject.descr_startswith,
                            doc=UnicodeDocstrings.startswith.__doc__),
    terminacon = interp2app(W_UnicodeObject.descr_endswith,
                          doc=UnicodeDocstrings.endswith.__doc__),
    endswith = interp2app(W_UnicodeObject.descr_endswith,
                          doc=UnicodeDocstrings.endswith.__doc__),
    decapar = interp2app(W_UnicodeObject.descr_strip,
                       doc=UnicodeDocstrings.strip.__doc__),
    strip = interp2app(W_UnicodeObject.descr_strip,
                       doc=UnicodeDocstrings.strip.__doc__),
    idecapar = interp2app(W_UnicodeObject.descr_lstrip,
                        doc=UnicodeDocstrings.lstrip.__doc__),
    lstrip = interp2app(W_UnicodeObject.descr_lstrip,
                        doc=UnicodeDocstrings.lstrip.__doc__),
    ddecapar = interp2app(W_UnicodeObject.descr_rstrip,
                        doc=UnicodeDocstrings.rstrip.__doc__),
    rstrip = interp2app(W_UnicodeObject.descr_rstrip,
                        doc=UnicodeDocstrings.rstrip.__doc__),
    minmayusc = interp2app(W_UnicodeObject.descr_swapcase,
                          doc=UnicodeDocstrings.swapcase.__doc__),
    swapcase = interp2app(W_UnicodeObject.descr_swapcase,
                          doc=UnicodeDocstrings.swapcase.__doc__),
    titulo = interp2app(W_UnicodeObject.descr_title,
                       doc=UnicodeDocstrings.title.__doc__),
    title = interp2app(W_UnicodeObject.descr_title,
                       doc=UnicodeDocstrings.title.__doc__),
    traducir = interp2app(W_UnicodeObject.descr_translate,
                           doc=UnicodeDocstrings.translate.__doc__),
    translate = interp2app(W_UnicodeObject.descr_translate,
                           doc=UnicodeDocstrings.translate.__doc__),
    mayusc = interp2app(W_UnicodeObject.descr_upper,
                       doc=UnicodeDocstrings.upper.__doc__),
    upper = interp2app(W_UnicodeObject.descr_upper,
                       doc=UnicodeDocstrings.upper.__doc__),
    cllenar = interp2app(W_UnicodeObject.descr_zfill,
                       doc=UnicodeDocstrings.zfill.__doc__),
    zfill = interp2app(W_UnicodeObject.descr_zfill,
                       doc=UnicodeDocstrings.zfill.__doc__),

    formato = interp2app(W_UnicodeObject.descr_format,
                        doc=UnicodeDocstrings.format.__doc__),
    format = interp2app(W_UnicodeObject.descr_format,
                        doc=UnicodeDocstrings.format.__doc__),
    __formato__ = interp2app(W_UnicodeObject.descr__format__,
                            doc=UnicodeDocstrings.__format__.__doc__),
    __format__ = interp2app(W_UnicodeObject.descr__format__,
                            doc=UnicodeDocstrings.__format__.__doc__),
    __mod__ = interp2app(W_UnicodeObject.descr_mod,
                         doc=UnicodeDocstrings.__mod__.__doc__),
    __dmod__ = interp2app(W_UnicodeObject.descr_rmod,
                         doc=UnicodeDocstrings.__rmod__.__doc__),
    __rmod__ = interp2app(W_UnicodeObject.descr_rmod,
                         doc=UnicodeDocstrings.__rmod__.__doc__),
    __sacanuevosargs__ = interp2app(W_UnicodeObject.descr_getnewargs,
                                doc=UnicodeDocstrings.__getnewargs__.__doc__),
    __getnewargs__ = interp2app(W_UnicodeObject.descr_getnewargs,
                                doc=UnicodeDocstrings.__getnewargs__.__doc__),
    _formatter_parser = interp2app(W_UnicodeObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_UnicodeObject.descr_formatter_field_name_split),
)
W_UnicodeObject.typedef.flag_sequence_bug_compat = True


def _create_list_from_unicode(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_unicode
    return [s for s in value]


W_UnicodeObject.EMPTY = W_UnicodeObject(u'')


# Helper for converting int/long
def unicode_to_decimal_w(space, w_unistr):
    if not isinstance(w_unistr, W_UnicodeObject):
        raise oefmt(space.w_TypeError, "anticipó unicod, recibió '%T'", w_unistr)
    unistr = w_unistr._value
    result = ['\0'] * len(unistr)
    digits = ['0', '1', '2', '3', '4',
              '5', '6', '7', '8', '9']
    for i in xrange(len(unistr)):
        uchr = ord(unistr[i])
        if unicodedb.isspace(uchr):
            result[i] = ' '
            continue
        try:
            result[i] = digits[unicodedb.decimal(uchr)]
        except KeyError:
            if 0 < uchr < 256:
                result[i] = chr(uchr)
            else:
                w_encoding = space.newtext('decimal')
                w_start = space.newint(i)
                w_end = space.newint(i+1)
                w_reason = space.newtext('palabra decimal unicod no válida')
                raise OperationError(space.w_UnicodeEncodeError,
                                     space.newtuple([w_encoding, w_unistr,
                                                     w_start, w_end,
                                                     w_reason]))
    return ''.join(result)


_repr_function, _ = make_unicode_escape_function(
    pass_printable=False, unicode_output=False, quotes=True, prefix='u')
