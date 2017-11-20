"""The builtin bool implementation"""

import operator

from rpython.rlib.rarithmetic import r_uint
from rpython.tool.sourcetools import func_renamer, func_with_new_name

from pypy.interpreter.gateway import WrappedDefault, interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from pypy.objspace.std.intobject import W_AbstractIntObject, W_IntObject


class W_BoolObject(W_IntObject):

    def __init__(self, boolval):
        self.intval = int(not not boolval)

    def __nonzero__(self):
        raise Exception("no puede hacer esto; tiene que usar space.is_true()")

    def __repr__(self):
        """representation for debugging purposes"""
        return "%s(%s)" % (self.__class__.__name__, bool(self.intval))

    def is_w(self, space, w_other):
        return self is w_other

    def immutable_unique_id(self, space):
        return None

    def unwrap(self, space):
        return bool(self.intval)

    def uint_w(self, space):
        return r_uint(self.intval)

    def int(self, space):
        return space.newint(self.intval)

    @staticmethod
    @unwrap_spec(w_obj=WrappedDefault(False))
    def descr_new(space, w_booltype, w_obj):
        """T.__new__(S, ...) -> a new object with type S, a subtype of T"""
        space.w_bool.check_user_subclass(w_booltype)
        return space.newbool(space.is_true(w_obj))

    def descr_repr(self, space):
        return space.newtext('Cierto' if self.intval else 'Falso')
    descr_str = func_with_new_name(descr_repr, 'descr_str')

    def descr_nonzero(self, space):
        return self

    def _make_bitwise_binop(opname):
        descr_name = 'descr_' + opname
        int_op = getattr(W_IntObject, descr_name)
        op = getattr(operator,
                     opname + '_' if opname in ('and', 'or') else opname)

        @func_renamer(descr_name)
        def descr_binop(self, space, w_other):
            if not isinstance(w_other, W_BoolObject):
                return int_op(self, space, w_other)
            a = bool(self.intval)
            b = bool(w_other.intval)
            return space.newbool(op(a, b))

        @func_renamer('descr_r' + opname)
        def descr_rbinop(self, space, w_other):
            return descr_binop(self, space, w_other)

        return descr_binop, descr_rbinop

    descr_and, descr_rand = _make_bitwise_binop('and')
    descr_or, descr_ror = _make_bitwise_binop('or')
    descr_xor, descr_rxor = _make_bitwise_binop('xor')


W_BoolObject.w_Falso = W_BoolObject(False)
W_BoolObject.w_False = W_BoolObject(False)
W_BoolObject.w_Cierto = W_BoolObject(True)
W_BoolObject.w_True = W_BoolObject(True)


W_BoolObject.typedef = TypeDef("bool", W_IntObject.typedef,
    __doc__ = """bool(x) -> bool

Vuelve Cierto cuando el argumento x es cierto, Falso si no.
Los prehechos Cierto y Falso son las únicas instancias de la clase bool.
La clase bool es un sub-clase de la clase ent, y no se puede ser sub-clasificada.""",
    __nuevo__ = interp2app(W_BoolObject.descr_new),
    __new__ = interp2app(W_BoolObject.descr_new),
    __repr__ = interp2app(W_BoolObject.descr_repr,
                          doc=W_AbstractIntObject.descr_repr.__doc__),
    __pal__ = interp2app(W_BoolObject.descr_str,
                         doc=W_AbstractIntObject.descr_str.__doc__),
    __str__ = interp2app(W_BoolObject.descr_str,
                         doc=W_AbstractIntObject.descr_str.__doc__),
    __nocero__ = interp2app(W_BoolObject.descr_nonzero,
                             doc=W_AbstractIntObject.descr_nonzero.__doc__),
    __nonzero__ = interp2app(W_BoolObject.descr_nonzero,
                             doc=W_AbstractIntObject.descr_nonzero.__doc__),

    __y__ = interp2app(W_BoolObject.descr_and,
                         doc=W_AbstractIntObject.descr_and.__doc__),
    __and__ = interp2app(W_BoolObject.descr_and,
                         doc=W_AbstractIntObject.descr_and.__doc__),
    __dy__ = interp2app(W_BoolObject.descr_rand,
                          doc=W_AbstractIntObject.descr_rand.__doc__),
    __rand__ = interp2app(W_BoolObject.descr_rand,
                          doc=W_AbstractIntObject.descr_rand.__doc__),
    __o__ = interp2app(W_BoolObject.descr_or,
                        doc=W_AbstractIntObject.descr_or.__doc__),
    __or__ = interp2app(W_BoolObject.descr_or,
                        doc=W_AbstractIntObject.descr_or.__doc__),
    __do__ = interp2app(W_BoolObject.descr_ror,
                         doc=W_AbstractIntObject.descr_ror.__doc__),
    __ror__ = interp2app(W_BoolObject.descr_ror,
                         doc=W_AbstractIntObject.descr_ror.__doc__),
    __oex__ = interp2app(W_BoolObject.descr_xor,
                         doc=W_AbstractIntObject.descr_xor.__doc__),
    __xor__ = interp2app(W_BoolObject.descr_xor,
                         doc=W_AbstractIntObject.descr_xor.__doc__),
    __doex__ = interp2app(W_BoolObject.descr_rxor,
                          doc=W_AbstractIntObject.descr_rxor.__doc__),
    __rxor__ = interp2app(W_BoolObject.descr_rxor,
                          doc=W_AbstractIntObject.descr_rxor.__doc__),
    )
W_BoolObject.typedef.acceptable_as_base_class = False
