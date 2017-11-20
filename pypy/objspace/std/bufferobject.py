"""Implementation of the 'buffer' type"""
import operator

from rpython.rlib.buffer import Buffer, SubBuffer
from rpython.rlib.objectmodel import compute_hash

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.buffer import SimpleView, BufferInterfaceNotFound
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef


class W_Buffer(W_Root):
    """The 'buffer' type: a wrapper around an interp-level buffer"""

    def __init__(self, buf):
        assert isinstance(buf, Buffer)
        self.buf = buf

    def buffer_w(self, space, flags):
        space.check_buf_flags(flags, self.buf.readonly)
        return SimpleView(self.buf)

    def readbuf_w(self, space):
        return self.buf

    def writebuf_w(self, space):
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "búfer es solo-leer")
        return self.buf

    def charbuf_w(self, space):
        return self.buf.as_str()

    def descr_getbuffer(self, space, w_flags):
        space.check_buf_flags(space.int_w(w_flags), self.buf.readonly)
        return self

    @staticmethod
    @unwrap_spec(offset=int, size=int)
    def descr_new_buffer(space, w_subtype, w_object, offset=0, size=-1):
        try:
            buf = w_object.readbuf_w(space)
        except BufferInterfaceNotFound:
            raise oefmt(space.w_TypeError, "anticipó un objecto búfer leíble")
        if offset == 0 and size == -1:
            return W_Buffer(buf)
        # handle buffer slices
        if offset < 0:
            raise oefmt(space.w_ValueError, "offset tiene que ser cero o positivo")
        if size < -1:
            raise oefmt(space.w_ValueError, "tamaño tiene que ser cero o positivo")
        buf = SubBuffer(buf, offset, size)
        return W_Buffer(buf)

    def descr_len(self, space):
        return space.newint(self.buf.getlength())

    def descr_getitem(self, space, w_index):
        start, stop, step, size = space.decode_index4(w_index,
                                                      self.buf.getlength())
        if step == 0:  # index only
            return space.newbytes(self.buf.getitem(start))
        res = self.buf.getslice(start, stop, step, size)
        return space.newbytes(res)

    def descr_setitem(self, space, w_index, w_obj):
        if self.buf.readonly:
            raise oefmt(space.w_TypeError, "búfer es solo-leer")
        start, stop, step, size = space.decode_index4(w_index,
                                                      self.buf.getlength())
        value = space.readbuf_w(w_obj)
        if step == 0:  # index only
            if value.getlength() != 1:
                raise oefmt(space.w_TypeError,
                            "operando derecho tiene que ser un solo byte")
            self.buf.setitem(start, value.getitem(0))
        else:
            if value.getlength() != size:
                raise oefmt(space.w_TypeError,
                            "tamaño del operando derecho tiene que ser el mismo que el tamaño del parte cortado")
            if step == 1:
                self.buf.setslice(start, value.as_str())
            else:
                for i in range(size):
                    self.buf.setitem(start + i * step, value.getitem(i))

    def descr_str(self, space):
        return space.newbytes(self.buf.as_str())

    @unwrap_spec(other='bufferstr')
    def descr_add(self, space, other):
        return space.newbytes(self.buf.as_str() + other)

    def _make_descr__cmp(name):
        def descr__cmp(self, space, w_other):
            if not isinstance(w_other, W_Buffer):
                return space.w_NotImplemented
            # xxx not the most efficient implementation
            str1 = self.buf.as_str()
            str2 = w_other.buf.as_str()
            return space.newbool(getattr(operator, name)(str1, str2))
        descr__cmp.func_name = name
        return descr__cmp

    descr_eq = _make_descr__cmp('eq')
    descr_ne = _make_descr__cmp('ne')
    descr_lt = _make_descr__cmp('lt')
    descr_le = _make_descr__cmp('le')
    descr_gt = _make_descr__cmp('gt')
    descr_ge = _make_descr__cmp('ge')

    def descr_hash(self, space):
        x = compute_hash(self.buf.as_str())
        x -= (x == -1) # convert -1 to -2 without creating a bridge
        return space.newint(x)

    def descr_mul(self, space, w_times):
        # xxx not the most efficient implementation
        w_string = space.newbytes(self.buf.as_str())
        # use the __mul__ method instead of space.mul() so that we
        # return NotImplemented instead of raising a TypeError
        return space.call_method(w_string, '__mul__', w_times)

    def descr_repr(self, space):
        if self.buf.readonly:
            info = 'read-only buffer'
        else:
            info = 'read-write buffer'
        addrstring = self.getaddrstring(space)

        return space.newtext("<%s para 0x%s, tamaño %d>" %
                             (info, addrstring, self.buf.getlength()))

    def descr_pypy_raw_address(self, space):
        from rpython.rtyper.lltypesystem import lltype, rffi
        try:
            ptr = self.buf.get_raw_address()
        except ValueError:
            # report the error using the RPython-level internal repr of self.buf
            msg = ("no puede encontrar la dirección subyacente del búfer que "
                   "es internalmente %r" % (self.buf,))
            raise OperationError(space.w_ValueError, space.newtext(msg))
        return space.newint(rffi.cast(lltype.Signed, ptr))

W_Buffer.typedef = TypeDef(
    "buffer", None, None, "read-write",
    __doc__ = """\
buffer(object [, offset[, size]])
búfer(objeto [, offset[, tamaño]])

Crear un nuevo objeto búfer que refiere al objecto dado.
El búfer referirá a un parte del objeto propósito desde la
empieza del objecto (o al offset especificado). El parte extenderá
al final del objeto propósito (o con el tamaño especificado).
""",
    __nuevo__ = interp2app(W_Buffer.descr_new_buffer),
    __new__ = interp2app(W_Buffer.descr_new_buffer),
    __tam__ = interp2app(W_Buffer.descr_len),
    __len__ = interp2app(W_Buffer.descr_len),
    __sacaartic__ = interp2app(W_Buffer.descr_getitem),
    __getitem__ = interp2app(W_Buffer.descr_getitem),
    __ponartic__ = interp2app(W_Buffer.descr_setitem),
    __setitem__ = interp2app(W_Buffer.descr_setitem),
    __pal__ = interp2app(W_Buffer.descr_str),
    __str__ = interp2app(W_Buffer.descr_str),
    __mas__ = interp2app(W_Buffer.descr_add),
    __add__ = interp2app(W_Buffer.descr_add),
    __ig__ = interp2app(W_Buffer.descr_eq),
    __eq__ = interp2app(W_Buffer.descr_eq),
    __ni__ = interp2app(W_Buffer.descr_ne),
    __ne__ = interp2app(W_Buffer.descr_ne),
    __meq__ = interp2app(W_Buffer.descr_lt),
    __lt__ = interp2app(W_Buffer.descr_lt),
    __mei__ = interp2app(W_Buffer.descr_le),
    __le__ = interp2app(W_Buffer.descr_le),
    __maq__ = interp2app(W_Buffer.descr_gt),
    __gt__ = interp2app(W_Buffer.descr_gt),
    __mai__ = interp2app(W_Buffer.descr_ge),
    __ge__ = interp2app(W_Buffer.descr_ge),
    __hash__ = interp2app(W_Buffer.descr_hash),
    __mul__ = interp2app(W_Buffer.descr_mul),
    __dmul__ = interp2app(W_Buffer.descr_mul),
    __rmul__ = interp2app(W_Buffer.descr_mul),
    __repr__ = interp2app(W_Buffer.descr_repr),
    __bufer__ = interp2app(W_Buffer.descr_getbuffer),
    __buffer__ = interp2app(W_Buffer.descr_getbuffer),
    _pypy_raw_address = interp2app(W_Buffer.descr_pypy_raw_address),
)
W_Buffer.typedef.acceptable_as_base_class = False
