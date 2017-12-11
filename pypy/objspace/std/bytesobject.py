"""The builtin str implementation"""

from rpython.rlib import jit
from rpython.rlib.jit import we_are_jitted
from rpython.rlib.objectmodel import (
    compute_hash, compute_unique_id, import_from_mixin)
from rpython.rlib.buffer import StringBuffer
from rpython.rlib.rstring import StringBuilder, replace

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import SimpleView
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import (
    WrappedDefault, interp2app, interpindirect2app, unwrap_spec)
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std import newformat
from pypy.objspace.std.basestringtype import basestring_typedef
from pypy.objspace.std.formatting import mod_format
from pypy.objspace.std.stringmethods import StringMethods
from pypy.objspace.std.unicodeobject import (
    decode_object, unicode_from_encoded_object,
    unicode_from_string, getdefaultencoding)
from pypy.objspace.std.util import IDTAG_SPECIAL, IDTAG_SHIFT


class W_AbstractBytesObject(W_Root):
    __slots__ = ()

    def is_w(self, space, w_other):
        if not isinstance(w_other, W_AbstractBytesObject):
            return False
        if self is w_other:
            return True
        if self.user_overridden_class or w_other.user_overridden_class:
            return False
        s1 = space.bytes_w(self)
        s2 = space.bytes_w(w_other)
        if len(s2) > 1:
            return s1 is s2
        else:            # strings of len <= 1 are unique-ified
            return s1 == s2

    def immutable_unique_id(self, space):
        if self.user_overridden_class:
            return None
        s = space.bytes_w(self)
        if len(s) > 1:
            uid = compute_unique_id(s)
        else:            # strings of len <= 1 are unique-ified
            if len(s) == 1:
                base = ord(s[0])     # base values 0-255
            else:
                base = 256           # empty string: base value 256
            uid = (base << IDTAG_SHIFT) | IDTAG_SPECIAL
        return space.newint(uid)

    def unicode_w(self, space):
        # Use the default encoding.
        encoding = getdefaultencoding(space)
        return space.unicode_w(decode_object(space, self, encoding, None))

    def descr_add(self, space, w_other):
        """x.__mas__(y) <==> x+y"""

    def descr_contains(self, space, w_sub):
        """x.__contiene__(y) <==> y in x"""

    def descr_eq(self, space, w_other):
        """x.__ig__(y) <==> x==y"""

    def descr__format__(self, space, w_format_spec):
        """S.__formato__(formato_espec) -> palabra

        Vuelve una versión formateada de S, describido por formato_espec.
        """

    def descr_ge(self, space, w_other):
        """x.__mai__(y) <==> x>=y"""

    def descr_getitem(self, space, w_index):
        """x.__sacaartic__(y) <==> x[y]"""

    def descr_getnewargs(self, space):
        ""

    def descr_getslice(self, space, w_start, w_stop):
        """x.__sacaparte__(i, j) <==> x[i:j]

        Uso de índices negativos no es apoyado.
        """

    def descr_gt(self, space, w_other):
        """x.__maq__(y) <==> x>y"""

    def descr_hash(self, space):
        """x.__hash__() <==> hash(x)"""

    def descr_le(self, space, w_other):
        """x.__mei__(y) <==> x<=y"""

    def descr_len(self, space):
        """x.__tam__() <==> tam(x)"""

    def descr_lt(self, space, w_other):
        """x.__meq__(y) <==> x<y"""

    def descr_mod(self, space, w_values):
        """x.__mod__(y) <==> x%y"""

    def descr_mul(self, space, w_times):
        """x.__mul__(n) <==> x*n"""

    def descr_ne(self, space, w_other):
        """x.__ni__(y) <==> x!=y"""

    def descr_repr(self, space):
        """x.__repr__() <==> repr(x)"""

    def descr_rmod(self, space, w_values):
        """x.__dmod__(y) <==> y%x"""

    def descr_rmul(self, space, w_times):
        """x.__dmul__(n) <==> n*x"""

    def descr_str(self, space):
        """x.__pal__() <==> pal(x)"""

    def descr_capitalize(self, space):
        """S.mayuscular() -> palabra

        Vuelve una versión de S puesta en mayusculas, i.e. poner el carácter
        primero en mayúsculo y el resto en minusculo.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_center(self, space, width, w_fillchar):
        """S.centro(ancho[, llenacarác]) -> palabra

        Vuelve S en el centro de una palabra de tamaño ancho. Relleno está
        hecho con la llenacarác especificada (estándar es un espacio).
        """

    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        """S.total(sub[, empieza[, fin]]) -> ent

        Vuelve el numero de casos no sobreponiendos del sub-palabra sub en
        palabra S[empieza:fin]. Argumentos opcionales empieza y fin son
        interpretados como en notación cortar.
        """

    def descr_decode(self, space, w_encoding=None, w_errors=None):
        """S.decodificar(codificación=Nada, errores='estricto') -> objeto

        Decodificar S usando el codec registrado para codificación. Errores se
        pueden pasar a una esquema de encargación de errores diferente. El
        estándar es 'estricto', es decir que los errores llaman
        UnicodeDecodeError. Otros valores posibles son 'ignorar' y 'reemplazar'
        y cualquier otro nombre registrado con codecs.register_error que puede
        llamar UnicodeDecodeErrors.
        """

    def descr_encode(self, space, w_encoding=None, w_errors=None):
        """S.codificar(codificación=Nada, errores='estricto') -> objeto

        Codificar S usando el codec para codificación. Errores se pueden
        pasar a una esquema de encargación de errores diferente. El estándar
        es 'estricto', es decir que los errores llaman UnicodeEncodeError.
        Otros valores posibles son 'ignorar', 'reemplazar' y 'xmlcharrefreplace'
        y cualquier otro nombre registrado con codecs.register_error que puede
        llamar UnicodeEncodeErrors.
        """

    def descr_endswith(self, space, w_suffix, w_start=None, w_end=None):
        """S.terminacon(sufijo[, empieza[, fin]]) -> bool

        Vuelve Cierto si S termina con el sufijo especificado, Falso si no.
        Con empieza opcional, prueba S al inicio de esa posición.
        Con fin opcional, pare comparando S en esa posición.
        sufijo también puede ser un tuple de palabrase para probar.
        """

    @unwrap_spec(tabsize=int)
    def descr_expandtabs(self, space, tabsize=8):
        """S.expandtabs([tabtamaño]) -> palabra

        Vuelve una copia de S donde todos los tabs son expandidos usando
        espacios. Si tabtamaño no está dado, un tamaño de 8 carácteres está
        asumido.
        """

    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        """S.encontrar(sub[, empieza[, fin]]) -> ent

        Vuelve la índice más baja en S donde la sub-palabra sub
        está encontrada, para que sub esté contenido entre S[empieza:fin].
        Vuelve -1 si fracasa.
        """

    def descr_format(self, space, __args__):
        """S.formato(*args, **kwargs) -> palabra

        Vuelve una versión de S formateado, usando substituciones de args y
        kwargs. Las substituciones son identificados con llaves ('{' y '}').
        """

    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        """S.indice(sub[, empieza[, fin]]) -> ent

        Como S.encontrar() pero llama ValueError cuando el sub-palabra no
        se puede encontrar.
        """

    def descr_isalnum(self, space):
        """S.esalnum() -> bool

        Vuelve Cierto si todos los carácteres en S son alfanuméricos
        y hay por lo menos un carácter en S, Falso si no.
        """

    def descr_isalpha(self, space):
        """S.esalfa() -> bool

        Vuelve Cierto si todos los carácteres en S son alfabéticos y hay
        por lo menos un carácter en S, Falso si no.
        """

    def descr_isdigit(self, space):
        """S.esdec() -> bool

        Vuelve Cierto si todos los carácteres en S son dígitos y hay por
        lo menus un carácter en S, Falso si no.
        """

    def descr_islower(self, space):
        """S.esminusc() -> bool

        Vuelve Cierto si todos los carácteres en S están en minúscula y
        hay por lo menos un carácter en S, Falso si no.
        """

    def descr_isspace(self, space):
        """S.esespac() -> bool

        Vuelve Cierto si todos los carácteres en S son espacio blanco y
        hay por lo menos un carácter en S, Falso si no.
        """

    def descr_istitle(self, space):
        """S.estitulo() -> bool

        Vuelve Cierto si S está en formato de título y hay por lo menos
        un carácter en S, Falso si no.
        """

    def descr_isupper(self, space):
        """S.esmayusc() -> bool

        Vuelve Cierto si todos los carácteres en S son en mayúsculo y hay
        por lo menos un carácter en S, Falso si no.
        """

    def descr_join(self, space, w_list):
        """S.juntar(iterable) -> palabra

        Vuelve una palabra que es la juntación de las palabras en el
        iterable. El separador entre elementos es S.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_ljust(self, space, width, w_fillchar):
        """S.ijust(ancho[, lleneacarác]) -> palabra

        Vuelve S justificado a la izquierda en una palabra de tamaño
        ancho. Relleno está hecho con el carácter especificado (estándar
        es un espacio).
        """

    def descr_lower(self, space):
        """S.minusc() -> palabra

        Vuelve una copia de la palabra S convertido a minúscula.
        """

    def descr_lstrip(self, space, w_chars=None):
        """S.idecapar([carács]) -> palabra o unicod

        Vuelve una copia de la palabra S con espacio blanco al frente quitado.
        Si carács está dado y no es Nada, quita carácteres en carács en lugar
        de espacio blanco. Si carács es unicod, S será convertido a unicode
        antes de decapar.
        """

    def descr_partition(self, space, w_sub):
        """S.particion(sep) -> (cabeza, sep, cola)

        Busca el separador sep en S, y volver la parte antes de ello, el
        separador, y el parte después de ello. Si sep no está encontrado,
        volver S y dos palabras vacías.
        """

    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        """S.reemplazar(viejo, nuevo[, total]) -> palabra

        Vuelve una copia de la palabra S con todas occurencias de la
        sub-palabra viejo reemplazadas por nuevo. Si el argumento
        opcional total está dado, solamente las primeras total occurencias
        son reemplazadas.
        """

    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        """S.dencontrar(sub[, empieza[, fin]]) -> ent

        Vuelve la índice más alta en S donde sub-palabra sub está
        encontrada, para que sub esté contenida en S[empieza:fin].
        Vuelve -1 si fracasa.
        """

    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        """S.dindice(sub[, empieza[, fin]]) -> ent

        Como S.dencontrar() pero llama ValueError cuando la sub-palabra
        no está encontrada.
        """

    @unwrap_spec(width=int, w_fillchar=WrappedDefault(' '))
    def descr_rjust(self, space, width, w_fillchar):
        """S.djust(ancho[, llenacarác]) -> palabra

        Vuelve S justificado a la derecha en una palabra de tamaño
        ancho. Relleno está hecho con el carácter especificado (estándar
        es un espacio).
        """

    def descr_rpartition(self, space, w_sub):
        """S.dparticion(sep) -> (cabeza, sep, cola)

        Busca el separador sep en S, empezando al fin de S, y volver la
        parte antes de ello, el separador, y el parte después de ello.
        Si sep no está encontrado, volver S y dos palabras vacías.
        """

    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        """S.dquebrar(sep=Nada, maxquebrar=-1) -> lista de palabras

        Volver una lista de las secciones en S, usando sep como delimitador,
        empezando al final de S y siguendo al frente.
        Si sep no está dado o es Nada, cualquier espacio blanco es un
        separador.
        Si maxquebrar está dado, al máximo maxquebrar quebraciones están
        hechos.
        """

    def descr_rstrip(self, space, w_chars=None):
        """S.ddecapar([carács]) -> palabra o unicod

        Vuelve una copia de la palabra S con espacio blanco al final quitado.
        Si carács está dado y no es Nada, quita carácteres en carács en lugar
        de espacio blanco. Si carács es unicod, S será convertido a unicode
        antes de decapar.
        """

    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        """S.quebrar(sep=Nada, maxquebrar=-1) -> lista de palabras

        Volver una lista de las secciones en S, usando sep como delimitador.
        Si sep no está dado o es Nada, cualquier espacio blanco es un
        separador.
        Si maxquebrar está dado, al máximo maxquebrar quebraciones están
        hechos.
        """

    @unwrap_spec(keepends=bool)
    def descr_splitlines(self, space, keepends=False):
        """S.quebrarlineas(guardacolas=Falso) -> lista de palabras

        Volver una lista de las líneas en S, rompiendo en límites de las
        líneas. Rompes de línea no son incluidos en el resultado a menos
        que guardarcolas está dado y es Cierto.
        """

    def descr_startswith(self, space, w_prefix, w_start=None, w_end=None):
        """S.empcon(prefijo[, empieza[, fin]]) -> bool

        Vuelve Cierto si S empieza con el prefijo especificado, Falso si no.
        Con empieza opcional, prueba S empezando en esta posición.
        Con fin opcional, pare comparando S en esta posición.
        prefijo también puede ser un tuple de palabras para probar.
        """

    def descr_strip(self, space, w_chars=None):
        """S.decapar([carács]) -> palabra o unicod

        Vuelve una copia de la palabra S con espacio blanco al inicio y al
        final quitado.
        Si carács está dado y no es Nada, quita carácteres in carács.
        Si carács es unicod, S será convertido a unicod antes de decapar.
        """

    def descr_swapcase(self, space):
        """S.minmayusc() -> palabra

        Vuelve una copia de S con todos los carácteres mayúsculos convertidos
        a minúsculo, y vice versa.
        """

    def descr_title(self, space):
        """S.titulo() -> palabra

        Vuelve una versión de S puesto como título, i.e. palabras que empiezan
        con mayúsculos, y todos otros carácteres están in minúsculo.
        """

    @unwrap_spec(w_deletechars=WrappedDefault(''))
    def descr_translate(self, space, w_table, w_deletechars):
        """S.traducir(mesa[, elimcarács]) -> palabra

        Vuelve una copia de B donde todos los carácteres que ocurren
        en el argumento opcional elimcarács son quitados, y el resto
        de los carácteres han sido aplicados en la mesa de traducción,
        que tiene que ser un objeto bytes de tamaño 256. Si el argumento
        mesa es Nada, no traducción está aplicado y la operación simplemente
        quita los carácteres en elimcarács.
        """

    def descr_upper(self, space):
        """S.mayusc() -> palabra

        Vuelve una copia de S con todos carácteres puesto en mayúsculo.
        """

    @unwrap_spec(width=int)
    def descr_zfill(self, space, width):
        """S.cllenar(ancho) -> palabra

        Rellenar una palabra numérica S con ceros a la izquierda, para
        llenar un campo del ancho especificado. S nunca está truncado.
        """

class W_BytesObject(W_AbstractBytesObject):
    import_from_mixin(StringMethods)
    _immutable_fields_ = ['_value']

    def __init__(self, str):
        assert str is not None
        self._value = str

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%r)" % (self.__class__.__name__, self._value)

    def unwrap(self, space):
        return self._value

    def str_w(self, space):
        return self._value

    def buffer_w(self, space, flags):
        space.check_buf_flags(flags, True)
        return SimpleView(StringBuffer(self._value))

    def readbuf_w(self, space):
        return StringBuffer(self._value)

    def writebuf_w(self, space):
        raise oefmt(space.w_TypeError,
                    "No puede usar palabra como búfer modificable")

    def descr_getbuffer(self, space, w_flags):
        #from pypy.objspace.std.bufferobject import W_Buffer
        #return W_Buffer(StringBuffer(self._value))
        return self

    charbuf_w = str_w

    def listview_bytes(self):
        return _create_list_from_bytes(self._value)

    def ord(self, space):
        if len(self._value) != 1:
            raise oefmt(space.w_TypeError,
                        "ord() anticipó un carácter, pero palabra de tamaño %d "
                        "encontrada", len(self._value))
        return space.newint(ord(self._value[0]))

    def _new(self, value):
        return W_BytesObject(value)

    def _new_from_list(self, value):
        return W_BytesObject(''.join(value))

    def _empty(self):
        return W_BytesObject.EMPTY

    def _len(self):
        return len(self._value)

    _val = str_w

    @staticmethod
    def _use_rstr_ops(space, w_other):
        from pypy.objspace.std.unicodeobject import W_UnicodeObject
        return (isinstance(w_other, W_BytesObject) or
                isinstance(w_other, W_UnicodeObject))

    @staticmethod
    def _op_val(space, w_other, strict=None):
        if strict and not space.isinstance_w(w_other, space.w_bytes):
            raise oefmt(space.w_TypeError,
                "%s arg tiene que ser Nada, pal o unicod", strict)
        try:
            return space.bytes_w(w_other)
        except OperationError as e:
            if not e.match(space, space.w_TypeError):
                raise
        return space.charbuf_w(w_other)

    def _chr(self, char):
        assert len(char) == 1
        return str(char)[0]

    _builder = StringBuilder

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

    def _newlist_unwrapped(self, space, lst):
        return space.newlist_bytes(lst)

    @staticmethod
    @unwrap_spec(w_object=WrappedDefault(""))
    def descr_new(space, w_stringtype, w_object):
        # NB. the default value of w_object is really a *wrapped* empty string:
        #     there is gateway magic at work
        w_obj = space.str(w_object)
        if space.is_w(w_stringtype, space.w_bytes):
            return w_obj  # XXX might be reworked when space.str() typechecks
        value = space.bytes_w(w_obj)
        w_obj = space.allocate_instance(W_BytesObject, w_stringtype)
        W_BytesObject.__init__(w_obj, value)
        return w_obj

    def descr_repr(self, space):
        s = self._value
        quote = "'"
        if quote in s and '"' not in s:
            quote = '"'
        return space.newtext(string_escape_encode(s, quote))

    def descr_str(self, space):
        if type(self) is W_BytesObject:
            return self
        return W_BytesObject(self._value)

    def descr_hash(self, space):
        x = compute_hash(self._value)
        x -= (x == -1) # convert -1 to -2 without creating a bridge
        return space.newint(x)

    def descr_format(self, space, __args__):
        return newformat.format_method(space, self, __args__, is_unicode=False)

    def descr__format__(self, space, w_format_spec):
        if not space.isinstance_w(w_format_spec, space.w_bytes):
            w_format_spec = space.str(w_format_spec)
        spec = space.bytes_w(w_format_spec)
        formatter = newformat.str_formatter(space, spec)
        return formatter.format_string(self._value)

    def descr_mod(self, space, w_values):
        return mod_format(space, self, w_values, do_unicode=False)

    def descr_rmod(self, space, w_values):
        return mod_format(space, w_values, self, do_unicode=False)

    def descr_eq(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value == w_other._value)

    def descr_ne(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value != w_other._value)

    def descr_lt(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value < w_other._value)

    def descr_le(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value <= w_other._value)

    def descr_gt(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value > w_other._value)

    def descr_ge(self, space, w_other):
        if not isinstance(w_other, W_BytesObject):
            return space.w_NotImplemented
        return space.newbool(self._value >= w_other._value)

    # auto-conversion fun

    _StringMethods_descr_add = descr_add
    def descr_add(self, space, w_other):
        if space.isinstance_w(w_other, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return self_as_unicode.descr_add(space, w_other)
        elif space.isinstance_w(w_other, space.w_bytearray):
            # XXX: eliminate double-copy
            from .bytearrayobject import W_BytearrayObject, _make_data
            self_as_bytearray = W_BytearrayObject(_make_data(self._value))
            return space.add(self_as_bytearray, w_other)
        return self._StringMethods_descr_add(space, w_other)

    _StringMethods__startswith = _startswith
    def _startswith(self, space, value, w_prefix, start, end):
        if space.isinstance_w(w_prefix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return self_as_unicode._startswith(space, self_as_unicode._value,
                                               w_prefix, start, end)
        return self._StringMethods__startswith(space, value, w_prefix, start,
                                               end)

    _StringMethods__endswith = _endswith
    def _endswith(self, space, value, w_suffix, start, end):
        if space.isinstance_w(w_suffix, space.w_unicode):
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return self_as_unicode._endswith(space, self_as_unicode._value,
                                             w_suffix, start, end)
        return self._StringMethods__endswith(space, value, w_suffix, start,
                                             end)

    _StringMethods_descr_contains = descr_contains
    def descr_contains(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            from pypy.objspace.std.unicodeobject import W_UnicodeObject
            assert isinstance(w_sub, W_UnicodeObject)
            self_as_unicode = unicode_from_encoded_object(space, self, None,
                                                          None)
            return space.newbool(
                self_as_unicode._value.find(w_sub._value) >= 0)
        return self._StringMethods_descr_contains(space, w_sub)

    _StringMethods_descr_replace = descr_replace
    @unwrap_spec(count=int)
    def descr_replace(self, space, w_old, w_new, count=-1):
        old_is_unicode = space.isinstance_w(w_old, space.w_unicode)
        new_is_unicode = space.isinstance_w(w_new, space.w_unicode)
        if old_is_unicode or new_is_unicode:
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_replace(space, w_old, w_new, count)
        return self._StringMethods_descr_replace(space, w_old, w_new, count)

    _StringMethods_descr_join = descr_join
    def descr_join(self, space, w_list):
        l = space.listview_bytes(w_list)
        if l is not None:
            if len(l) == 1:
                return space.newbytes(l[0])
            return space.newbytes(self._val(space).join(l))
        return self._StringMethods_descr_join(space, w_list)

    _StringMethods_descr_split = descr_split
    @unwrap_spec(maxsplit=int)
    def descr_split(self, space, w_sep=None, maxsplit=-1):
        if w_sep is not None and space.isinstance_w(w_sep, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_split(space, w_sep, maxsplit)
        return self._StringMethods_descr_split(space, w_sep, maxsplit)

    _StringMethods_descr_rsplit = descr_rsplit
    @unwrap_spec(maxsplit=int)
    def descr_rsplit(self, space, w_sep=None, maxsplit=-1):
        if w_sep is not None and space.isinstance_w(w_sep, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rsplit(space, w_sep, maxsplit)
        return self._StringMethods_descr_rsplit(space, w_sep, maxsplit)

    _StringMethods_descr_strip = descr_strip
    def descr_strip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_strip(space, w_chars)
        return self._StringMethods_descr_strip(space, w_chars)

    _StringMethods_descr_lstrip = descr_lstrip
    def descr_lstrip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_lstrip(space, w_chars)
        return self._StringMethods_descr_lstrip(space, w_chars)

    _StringMethods_descr_rstrip = descr_rstrip
    def descr_rstrip(self, space, w_chars=None):
        if w_chars is not None and space.isinstance_w(w_chars, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rstrip(space, w_chars)
        return self._StringMethods_descr_rstrip(space, w_chars)

    _StringMethods_descr_count = descr_count
    def descr_count(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_count(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_count(space, w_sub, w_start, w_end)

    _StringMethods_descr_find = descr_find
    def descr_find(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_find(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_find(space, w_sub, w_start, w_end)

    _StringMethods_descr_rfind = descr_rfind
    def descr_rfind(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rfind(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_rfind(space, w_sub, w_start, w_end)

    _StringMethods_descr_index = descr_index
    def descr_index(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_index(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_index(space, w_sub, w_start, w_end)

    _StringMethods_descr_rindex = descr_rindex
    def descr_rindex(self, space, w_sub, w_start=None, w_end=None):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rindex(space, w_sub, w_start, w_end)
        return self._StringMethods_descr_rindex(space, w_sub, w_start, w_end)

    _StringMethods_descr_partition = descr_partition
    def descr_partition(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_partition(space, w_sub)
        return self._StringMethods_descr_partition(space, w_sub)

    _StringMethods_descr_rpartition = descr_rpartition
    def descr_rpartition(self, space, w_sub):
        if space.isinstance_w(w_sub, space.w_unicode):
            self_as_uni = unicode_from_encoded_object(space, self, None, None)
            return self_as_uni.descr_rpartition(space, w_sub)
        return self._StringMethods_descr_rpartition(space, w_sub)

    def _join_return_one(self, space, w_obj):
        return (space.is_w(space.type(w_obj), space.w_bytes) or
                space.is_w(space.type(w_obj), space.w_unicode))

    def _join_check_item(self, space, w_obj):
        if space.isinstance_w(w_obj, space.w_bytes):
            return 0
        if space.isinstance_w(w_obj, space.w_unicode):
            return 2
        return 1

    def _join_autoconvert(self, space, list_w):
        # we need to rebuild w_list here, because the original
        # w_list might be an iterable which we already consumed
        w_list = space.newlist(list_w)
        w_u = space.call_function(space.w_unicode, self)
        return space.call_method(w_u, "join", w_list)

    def descr_lower(self, space):
        return W_BytesObject(self._value.lower())

    def descr_upper(self, space):
        return W_BytesObject(self._value.upper())

    def descr_formatter_parser(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.bytes_w(self))
        return tformat.formatter_parser()

    def descr_formatter_field_name_split(self, space):
        from pypy.objspace.std.newformat import str_template_formatter
        tformat = str_template_formatter(space, space.bytes_w(self))
        return tformat.formatter_field_name_split()


def _create_list_from_bytes(value):
    # need this helper function to allow the jit to look inside and inline
    # listview_bytes
    return [s for s in value]

W_BytesObject.EMPTY = W_BytesObject('')


W_BytesObject.typedef = TypeDef(
    "str", basestring_typedef, None, "read",
    __new__ = interp2app(W_BytesObject.descr_new),
    __doc__ = """pal(objeto='') -> palabra

    Vuelve una representación palabra del objeto. Si el argumento es
    una palabra, lo que vuelve es el objeto mismo.
    """,

    __repr__ = interpindirect2app(W_AbstractBytesObject.descr_repr),
    __pal__ = interpindirect2app(W_AbstractBytesObject.descr_str),
    __str__ = interpindirect2app(W_AbstractBytesObject.descr_str),
    __hash__ = interpindirect2app(W_AbstractBytesObject.descr_hash),

    __ig__ = interpindirect2app(W_AbstractBytesObject.descr_eq),
    __eq__ = interpindirect2app(W_AbstractBytesObject.descr_eq),
    __ni__ = interpindirect2app(W_AbstractBytesObject.descr_ne),
    __ne__ = interpindirect2app(W_AbstractBytesObject.descr_ne),
    __meq__ = interpindirect2app(W_AbstractBytesObject.descr_lt),
    __lt__ = interpindirect2app(W_AbstractBytesObject.descr_lt),
    __mei__ = interpindirect2app(W_AbstractBytesObject.descr_le),
    __le__ = interpindirect2app(W_AbstractBytesObject.descr_le),
    __maq__ = interpindirect2app(W_AbstractBytesObject.descr_gt),
    __gt__ = interpindirect2app(W_AbstractBytesObject.descr_gt),
    __mai__ = interpindirect2app(W_AbstractBytesObject.descr_ge),
    __ge__ = interpindirect2app(W_AbstractBytesObject.descr_ge),

    __tam__ = interpindirect2app(W_AbstractBytesObject.descr_len),
    __len__ = interpindirect2app(W_AbstractBytesObject.descr_len),
    __contiene__ = interpindirect2app(W_AbstractBytesObject.descr_contains),
    __contains__ = interpindirect2app(W_AbstractBytesObject.descr_contains),

    __mas__ = interpindirect2app(W_AbstractBytesObject.descr_add),
    __add__ = interpindirect2app(W_AbstractBytesObject.descr_add),
    __mul__ = interpindirect2app(W_AbstractBytesObject.descr_mul),
    __dmul__ = interpindirect2app(W_AbstractBytesObject.descr_rmul),
    __rmul__ = interpindirect2app(W_AbstractBytesObject.descr_rmul),

    __sacaartic__ = interpindirect2app(W_AbstractBytesObject.descr_getitem),
    __getitem__ = interpindirect2app(W_AbstractBytesObject.descr_getitem),
    __sacaparte__ = interpindirect2app(W_AbstractBytesObject.descr_getslice),
    __getslice__ = interpindirect2app(W_AbstractBytesObject.descr_getslice),

    mayuscular = interpindirect2app(W_AbstractBytesObject.descr_capitalize),
    capitalize = interpindirect2app(W_AbstractBytesObject.descr_capitalize),
    centro = interpindirect2app(W_AbstractBytesObject.descr_center),
    center = interpindirect2app(W_AbstractBytesObject.descr_center),
    total = interpindirect2app(W_AbstractBytesObject.descr_count),
    count = interpindirect2app(W_AbstractBytesObject.descr_count),
    decodificar = interpindirect2app(W_AbstractBytesObject.descr_decode),
    decode = interpindirect2app(W_AbstractBytesObject.descr_decode),
    codificar = interpindirect2app(W_AbstractBytesObject.descr_encode),
    encode = interpindirect2app(W_AbstractBytesObject.descr_encode),
    expandtabs = interpindirect2app(W_AbstractBytesObject.descr_expandtabs),
    encontrar = interpindirect2app(W_AbstractBytesObject.descr_find),
    find = interpindirect2app(W_AbstractBytesObject.descr_find),
    dencontrar = interpindirect2app(W_AbstractBytesObject.descr_rfind),
    rfind = interpindirect2app(W_AbstractBytesObject.descr_rfind),
    indice = interpindirect2app(W_AbstractBytesObject.descr_index),
    index = interpindirect2app(W_AbstractBytesObject.descr_index),
    dindice = interpindirect2app(W_AbstractBytesObject.descr_rindex),
    rindex = interpindirect2app(W_AbstractBytesObject.descr_rindex),
    esalnum = interpindirect2app(W_AbstractBytesObject.descr_isalnum),
    isalnum = interpindirect2app(W_AbstractBytesObject.descr_isalnum),
    esalfa = interpindirect2app(W_AbstractBytesObject.descr_isalpha),
    isalpha = interpindirect2app(W_AbstractBytesObject.descr_isalpha),
    esdig = interpindirect2app(W_AbstractBytesObject.descr_isdigit),
    isdigit = interpindirect2app(W_AbstractBytesObject.descr_isdigit),
    esminusc = interpindirect2app(W_AbstractBytesObject.descr_islower),
    islower = interpindirect2app(W_AbstractBytesObject.descr_islower),
    esespac = interpindirect2app(W_AbstractBytesObject.descr_isspace),
    isspace = interpindirect2app(W_AbstractBytesObject.descr_isspace),
    estitulo = interpindirect2app(W_AbstractBytesObject.descr_istitle),
    istitle = interpindirect2app(W_AbstractBytesObject.descr_istitle),
    esmayusc = interpindirect2app(W_AbstractBytesObject.descr_isupper),
    isupper = interpindirect2app(W_AbstractBytesObject.descr_isupper),
    juntar = interpindirect2app(W_AbstractBytesObject.descr_join),
    join = interpindirect2app(W_AbstractBytesObject.descr_join),
    ijust = interpindirect2app(W_AbstractBytesObject.descr_ljust),
    ljust = interpindirect2app(W_AbstractBytesObject.descr_ljust),
    djust = interpindirect2app(W_AbstractBytesObject.descr_rjust),
    rjust = interpindirect2app(W_AbstractBytesObject.descr_rjust),
    minusc = interpindirect2app(W_AbstractBytesObject.descr_lower),
    lower = interpindirect2app(W_AbstractBytesObject.descr_lower),
    particion = interpindirect2app(W_AbstractBytesObject.descr_partition),
    partition = interpindirect2app(W_AbstractBytesObject.descr_partition),
    dparticion = interpindirect2app(W_AbstractBytesObject.descr_rpartition),
    rpartition = interpindirect2app(W_AbstractBytesObject.descr_rpartition),
    reemplazar = interpindirect2app(W_AbstractBytesObject.descr_replace),
    replace = interpindirect2app(W_AbstractBytesObject.descr_replace),
    quebrar = interpindirect2app(W_AbstractBytesObject.descr_split),
    split = interpindirect2app(W_AbstractBytesObject.descr_split),
    dquebrar = interpindirect2app(W_AbstractBytesObject.descr_rsplit),
    rsplit = interpindirect2app(W_AbstractBytesObject.descr_rsplit),
    quebrarlineas = interpindirect2app(W_AbstractBytesObject.descr_splitlines),
    splitlines = interpindirect2app(W_AbstractBytesObject.descr_splitlines),
    empcon = interpindirect2app(W_AbstractBytesObject.descr_startswith),
    startswith = interpindirect2app(W_AbstractBytesObject.descr_startswith),
    terminacon = interpindirect2app(W_AbstractBytesObject.descr_endswith),
    endswith = interpindirect2app(W_AbstractBytesObject.descr_endswith),
    decapar = interpindirect2app(W_AbstractBytesObject.descr_strip),
    strip = interpindirect2app(W_AbstractBytesObject.descr_strip),
    idecapar = interpindirect2app(W_AbstractBytesObject.descr_lstrip),
    lstrip = interpindirect2app(W_AbstractBytesObject.descr_lstrip),
    ddecapar = interpindirect2app(W_AbstractBytesObject.descr_rstrip),
    rstrip = interpindirect2app(W_AbstractBytesObject.descr_rstrip),
    minmayusc = interpindirect2app(W_AbstractBytesObject.descr_swapcase),
    swapcase = interpindirect2app(W_AbstractBytesObject.descr_swapcase),
    titulo = interpindirect2app(W_AbstractBytesObject.descr_title),
    title = interpindirect2app(W_AbstractBytesObject.descr_title),
    traducir = interpindirect2app(W_AbstractBytesObject.descr_translate),
    translate = interpindirect2app(W_AbstractBytesObject.descr_translate),
    mayusc = interpindirect2app(W_AbstractBytesObject.descr_upper),
    upper = interpindirect2app(W_AbstractBytesObject.descr_upper),
    cllenar = interpindirect2app(W_AbstractBytesObject.descr_zfill),
    zfill = interpindirect2app(W_AbstractBytesObject.descr_zfill),
    __bufer__ = interp2app(W_BytesObject.descr_getbuffer),
    __buffer__ = interp2app(W_BytesObject.descr_getbuffer),

    formato = interpindirect2app(W_BytesObject.descr_format),
    format = interpindirect2app(W_BytesObject.descr_format),
    __formato__ = interpindirect2app(W_BytesObject.descr__format__),
    __format__ = interpindirect2app(W_BytesObject.descr__format__),
    __mod__ = interpindirect2app(W_BytesObject.descr_mod),
    __dmod__ = interpindirect2app(W_BytesObject.descr_rmod),
    __rmod__ = interpindirect2app(W_BytesObject.descr_rmod),
    __sacanuevosargs__ = interpindirect2app(
        W_AbstractBytesObject.descr_getnewargs),
    __getnewargs__ = interpindirect2app(
        W_AbstractBytesObject.descr_getnewargs),
    _formatter_parser = interp2app(W_BytesObject.descr_formatter_parser),
    _formatter_field_name_split =
        interp2app(W_BytesObject.descr_formatter_field_name_split),
)
W_BytesObject.typedef.flag_sequence_bug_compat = True


@jit.elidable
def string_escape_encode(s, quote):
    buf = StringBuilder(len(s) + 2)

    buf.append(quote)
    startslice = 0

    for i in range(len(s)):
        c = s[i]
        use_bs_char = False # character quoted by backspace

        if c == '\\' or c == quote:
            bs_char = c
            use_bs_char = True
        elif c == '\t':
            bs_char = 't'
            use_bs_char = True
        elif c == '\r':
            bs_char = 'r'
            use_bs_char = True
        elif c == '\n':
            bs_char = 'n'
            use_bs_char = True
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\x')
            buf.append("0123456789abcdef"[n >> 4])
            buf.append("0123456789abcdef"[n & 0xF])

        if use_bs_char:
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\')
            buf.append(bs_char)

    if len(s) != startslice:
        buf.append_slice(s, startslice, len(s))

    buf.append(quote)

    return buf.build()
