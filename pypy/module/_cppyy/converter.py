import sys

from pypy.interpreter.error import OperationError, oefmt

from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import r_singlefloat, r_longfloat
from rpython.rlib import rfloat, rawrefcount

from pypy.module._rawffi.interp_rawffi import letter2tp
from pypy.module._rawffi.array import W_Array, W_ArrayInstance

from pypy.module._cppyy import helper, capi, ffitypes

# Converter objects are used to translate between RPython and C++. They are
# defined by the type name for which they provide conversion. Uses are for
# function arguments, as well as for read and write access to data members.
# All type conversions are fully checked.
#
# Converter instances are greated by get_converter(<type name>), see below.
# The name given should be qualified in case there is a specialised, exact
# match for the qualified type.


def get_rawobject(space, w_obj, can_be_None=True):
    from pypy.module._cppyy.interp_cppyy import W_CPPClass
    cppinstance = space.interp_w(W_CPPClass, w_obj, can_be_None=can_be_None)
    if cppinstance:
        rawobject = cppinstance.get_rawobject()
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        return rawobject
    return capi.C_NULL_OBJECT

def set_rawobject(space, w_obj, address):
    from pypy.module._cppyy.interp_cppyy import W_CPPClass
    cppinstance = space.interp_w(W_CPPClass, w_obj, can_be_None=True)
    if cppinstance:
        assert lltype.typeOf(cppinstance._rawobject) == capi.C_OBJECT
        cppinstance._rawobject = rffi.cast(capi.C_OBJECT, address)

def get_rawobject_nonnull(space, w_obj):
    from pypy.module._cppyy.interp_cppyy import W_CPPClass
    cppinstance = space.interp_w(W_CPPClass, w_obj, can_be_None=True)
    if cppinstance:
        cppinstance._nullcheck()
        rawobject = cppinstance.get_rawobject()
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        return rawobject
    return capi.C_NULL_OBJECT

def is_nullpointer_specialcase(space, w_obj):
    # 0 and nullptr may serve as "NULL"

    # integer 0
    try:
        return space.int_w(w_obj) == 0
    except Exception:
        pass
    # C++-style nullptr
    from pypy.module._cppyy import interp_cppyy
    return space.is_true(space.is_(w_obj, interp_cppyy.get_nullptr(space)))

def get_rawbuffer(space, w_obj):
    # raw buffer
    try:
        buf = space.getarg_w('s*', w_obj)
        return rffi.cast(rffi.VOIDP, buf.get_raw_address())
    except Exception:
        pass
    # array type
    try:
        arr = space.interp_w(W_ArrayInstance, w_obj, can_be_None=True)
        if arr:
            return rffi.cast(rffi.VOIDP, space.uint_w(arr.getbuffer(space)))
    except Exception:
        pass
    # pre-defined nullptr
    if is_nullpointer_specialcase(space, w_obj):
        return rffi.cast(rffi.VOIDP, 0)
    raise TypeError("not an addressable buffer")


class TypeConverter(object):
    _immutable_fields_ = ['cffi_name', 'uses_local', 'name']

    cffi_name  = None
    uses_local = False
    name       = ""

    def __init__(self, space, extra):
        pass

    def _get_raw_address(self, space, w_obj, offset):
        rawobject = get_rawobject_nonnull(space, w_obj)
        assert lltype.typeOf(rawobject) == capi.C_OBJECT
        if rawobject:
            fieldptr = capi.direct_ptradd(rawobject, offset)
        else:
            fieldptr = rffi.cast(capi.C_OBJECT, offset)
        return fieldptr

    def _is_abstract(self, space):
        raise oefmt(space.w_TypeError,
                    "no converter available for '%s'", self.name)

    def cffi_type(self, space):
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def convert_argument(self, space, w_obj, address, call_local):
        self._is_abstract(space)

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def default_argument_libffi(self, space, address):
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        self._is_abstract(space)

    def to_memory(self, space, w_obj, w_value, offset):
        self._is_abstract(space)

    def finalize_call(self, space, w_obj, call_local):
        pass

    def free_argument(self, space, arg, call_local):
        pass


class ArrayCache(object):
    def __init__(self, space):
        self.space = space
    def __getattr__(self, name):
        if name.startswith('array_'):
            typecode = name[len('array_'):]
            arr = self.space.interp_w(W_Array, letter2tp(self.space, typecode))
            setattr(self, name, arr)
            return arr
        raise AttributeError(name)

    def _freeze_(self):
        return True

class ArrayTypeConverterMixin(object):
    _mixin_ = True
    _immutable_fields_ = ['size']

    def __init__(self, space, array_size):
        if array_size <= 0:
            self.size = sys.maxint
        else:
            self.size = array_size

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        # read access, so no copy needed
        address_value = self._get_raw_address(space, w_obj, offset)
        address = rffi.cast(rffi.ULONG, address_value)
        cache = space.fromcache(ArrayCache)
        arr = getattr(cache, 'array_' + self.typecode)
        return arr.fromaddress(space, address, self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy the full array (uses byte copy for now)
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        buf = space.getarg_w('s*', w_value)
        # TODO: report if too many items given?
        for i in range(min(self.size*self.typesize, buf.getlength())):
            address[i] = buf.getitem(i)


class PtrTypeConverterMixin(object):
    _mixin_ = True
    _immutable_fields_ = ['size']

    def __init__(self, space, array_size):
        self.size = sys.maxint

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument(self, space, w_obj, address, call_local):
        w_tc = space.findattr(w_obj, space.newtext('typecode'))
        if w_tc is not None and space.text_w(w_tc) != self.typecode:
            raise oefmt(space.w_TypeError,
                        "expected %s pointer type, but received %s",
                        self.typecode, space.text_w(w_tc))
        x = rffi.cast(rffi.VOIDPP, address)
        try:
            x[0] = rffi.cast(rffi.VOIDP, get_rawbuffer(space, w_obj))
        except TypeError:
            raise oefmt(space.w_TypeError,
                        "raw buffer interface not supported")
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'o'

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        # read access, so no copy needed
        address_value = self._get_raw_address(space, w_obj, offset)
        address = rffi.cast(rffi.ULONGP, address_value)
        cache = space.fromcache(ArrayCache)
        arr = getattr(cache, 'array_' + self.typecode)
        return arr.fromaddress(space, address[0], self.size)

    def to_memory(self, space, w_obj, w_value, offset):
        # copy only the pointer value
        rawobject = get_rawobject_nonnull(space, w_obj)
        byteptr = rffi.cast(rffi.CCHARPP, capi.direct_ptradd(rawobject, offset))
        buf = space.getarg_w('s*', w_value)
        try:
            byteptr[0] = buf.get_raw_address()
        except ValueError:
            raise oefmt(space.w_TypeError,
                        "raw buffer interface not supported")


class NumericTypeConverterMixin(object):
    _mixin_ = True

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        x = rffi.cast(self.c_ptrtype, address)
        x[0] = self._unwrap_object(space, w_obj)

    def default_argument_libffi(self, space, address):
        x = rffi.cast(self.c_ptrtype, address)
        x[0] = self.default

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = self._get_raw_address(space, w_obj, offset)
        rffiptr = rffi.cast(self.c_ptrtype, address)
        return self._wrap_object(space, rffiptr[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = self._get_raw_address(space, w_obj, offset)
        rffiptr = rffi.cast(self.c_ptrtype, address)
        rffiptr[0] = self._unwrap_object(space, w_value)

class ConstRefNumericTypeConverterMixin(NumericTypeConverterMixin):
    _mixin_ = True
    _immutable_fields_ = ['uses_local']

    uses_local = True

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        assert rffi.sizeof(self.c_type) <= 2*rffi.sizeof(rffi.VOIDP)  # see interp_cppyy.py
        obj = self._unwrap_object(space, w_obj)
        typed_buf = rffi.cast(self.c_ptrtype, call_local)
        typed_buf[0] = obj
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = call_local

class IntTypeConverterMixin(NumericTypeConverterMixin):
    _mixin_ = True

    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(self.c_ptrtype, address)
        x[0] = self._unwrap_object(space, w_obj)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = self.typecode

class FloatTypeConverterMixin(NumericTypeConverterMixin):
    _mixin_ = True

    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(self.c_ptrtype, address)
        x[0] = self._unwrap_object(space, w_obj)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = self.typecode


class VoidConverter(TypeConverter):
    _immutable_fields_ = ['name']

    def __init__(self, space, name):
        self.name = name

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_void

    def convert_argument(self, space, w_obj, address, call_local):
        self._is_abstract(space)


class BoolConverter(ffitypes.typeid(bool), TypeConverter):
    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.LONGP, address)
        x[0] = self._unwrap_object(space, w_obj)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'b'

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.LONGP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        if address[0] == '\x01':
            return space.w_True
        return space.w_False

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        arg = self._unwrap_object(space, w_value)
        if arg:
            address[0] = '\x01'
        else:
            address[0] = '\x00'

class CharConverter(ffitypes.typeid(rffi.CHAR), TypeConverter):
    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.CCHARP, address)
        x[0] = self._unwrap_object(space, w_obj)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'b'

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        x = rffi.cast(self.c_ptrtype, address)
        x[0] = self._unwrap_object(space, w_obj)

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        return space.newbytes(address[0])

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.CCHARP, self._get_raw_address(space, w_obj, offset))
        address[0] = self._unwrap_object(space, w_value)

class FloatConverter(ffitypes.typeid(rffi.FLOAT), FloatTypeConverterMixin, TypeConverter):
    _immutable_fields_ = ['default']

    def __init__(self, space, default):
        if default:
            fval = float(rfloat.rstring_to_float(default))
        else:
            fval = float(0.)
        self.default = r_singlefloat(fval)

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = self._get_raw_address(space, w_obj, offset)
        rffiptr = rffi.cast(self.c_ptrtype, address)
        return self._wrap_object(space, rffiptr[0])

class ConstFloatRefConverter(FloatConverter):
    _immutable_fields_ = ['typecode']
    typecode = 'f'

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

class DoubleConverter(ffitypes.typeid(rffi.DOUBLE), FloatTypeConverterMixin, TypeConverter):
    _immutable_fields_ = ['default']

    def __init__(self, space, default):
        if default:
            self.default = rffi.cast(self.c_type, rfloat.rstring_to_float(default))
        else:
            self.default = rffi.cast(self.c_type, 0.)

class ConstDoubleRefConverter(ConstRefNumericTypeConverterMixin, DoubleConverter):
    _immutable_fields_ = ['typecode']
    typecode = 'd'

class LongDoubleConverter(ffitypes.typeid(rffi.LONGDOUBLE), FloatTypeConverterMixin, TypeConverter):
    _immutable_fields_ = ['default']

    def __init__(self, space, default):
        if default:
            fval = float(rfloat.rstring_to_float(default))
        else:
            fval = float(0.)
        self.default = r_longfloat(fval)

class ConstLongDoubleRefConverter(ConstRefNumericTypeConverterMixin, LongDoubleConverter):
    _immutable_fields_ = ['typecode']
    typecode = 'g'


class CStringConverter(TypeConverter):
    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.LONGP, address)
        arg = space.text_w(w_obj)
        x[0] = rffi.cast(rffi.LONG, rffi.str2charp(arg))
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'o'

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = self._get_raw_address(space, w_obj, offset)
        charpptr = rffi.cast(rffi.CCHARPP, address)
        return space.newbytes(rffi.charp2str(charpptr[0]))

    def free_argument(self, space, arg, call_local):
        lltype.free(rffi.cast(rffi.CCHARPP, arg)[0], flavor='raw')

class CStringConverterWithSize(CStringConverter):
    _immutable_fields_ = ['size']

    def __init__(self, space, extra):
        self.size = extra

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = self._get_raw_address(space, w_obj, offset)
        charpptr = rffi.cast(rffi.CCHARP, address)
        strsize = self.size
        if charpptr[self.size-1] == '\0':
            strsize = self.size-1  # rffi will add \0 back
        return space.newbytes(rffi.charpsize2str(charpptr, strsize))


class VoidPtrConverter(TypeConverter):
    def _unwrap_object(self, space, w_obj):
        try:
            obj = get_rawbuffer(space, w_obj)
        except TypeError:
            obj = rffi.cast(rffi.VOIDP, get_rawobject(space, w_obj, False))
        return obj

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = self._unwrap_object(space, w_obj)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'o'

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = self._unwrap_object(space, w_obj)

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        # returned as a long value for the address (INTPTR_T is not proper
        # per se, but rffi does not come with a PTRDIFF_T)
        address = self._get_raw_address(space, w_obj, offset)
        ptrval = rffi.cast(rffi.ULONG, rffi.cast(rffi.VOIDPP, address)[0])
        if ptrval == 0:
            from pypy.module._cppyy import interp_cppyy
            return interp_cppyy.get_nullptr(space)
        arr = space.interp_w(W_Array, letter2tp(space, 'P'))
        return arr.fromaddress(space, ptrval, sys.maxint)

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.VOIDPP, self._get_raw_address(space, w_obj, offset))
        if is_nullpointer_specialcase(space, w_value):
            address[0] = rffi.cast(rffi.VOIDP, 0)
        else:
            address[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_value))

class VoidPtrPtrConverter(TypeConverter):
    _immutable_fields_ = ['uses_local', 'typecode']

    uses_local = True
    typecode = 'a'

    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.VOIDPP, address)
        ba = rffi.cast(rffi.CCHARP, address)
        try:
            x[0] = get_rawbuffer(space, w_obj)
        except TypeError:
            r = rffi.cast(rffi.VOIDPP, call_local)
            r[0] = rffi.cast(rffi.VOIDP, get_rawobject(space, w_obj))
            x[0] = rffi.cast(rffi.VOIDP, call_local)
        ba[capi.c_function_arg_typeoffset(space)] = self.typecode

    def finalize_call(self, space, w_obj, call_local):
        r = rffi.cast(rffi.VOIDPP, call_local)
        try:
            set_rawobject(space, w_obj, r[0])
        except OperationError:
            pass             # no set on buffer/array/None

class VoidPtrRefConverter(VoidPtrPtrConverter):
    _immutable_fields_ = ['uses_local', 'typecode']
    uses_local = True
    typecode   = 'V'

class InstanceRefConverter(TypeConverter):
    _immutable_fields_ = ['typecode', 'clsdecl']
    typecode    = 'V'

    def __init__(self, space, clsdecl):
        from pypy.module._cppyy.interp_cppyy import W_CPPClassDecl
        assert isinstance(clsdecl, W_CPPClassDecl)
        self.clsdecl = clsdecl

    def _unwrap_object(self, space, w_obj):
        from pypy.module._cppyy.interp_cppyy import W_CPPClass
        if isinstance(w_obj, W_CPPClass):
            from pypy.module._cppyy.interp_cppyy import INSTANCE_FLAGS_IS_R_VALUE
            if w_obj.flags & INSTANCE_FLAGS_IS_R_VALUE:
                # reject moves as all are explicit
                raise ValueError("lvalue expected")
            if capi.c_is_subtype(space, w_obj.clsdecl, self.clsdecl):
                rawobject = w_obj.get_rawobject()
                offset = capi.c_base_offset(space, w_obj.clsdecl, self.clsdecl, rawobject, 1)
                obj_address = capi.direct_ptradd(rawobject, offset)
                return rffi.cast(capi.C_OBJECT, obj_address)
        raise oefmt(space.w_TypeError,
                    "cannot pass %T as %s", w_obj, self.clsdecl.name)

    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_obj))
        address = rffi.cast(capi.C_OBJECT, address)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = self.typecode

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_obj))

class InstanceMoveConverter(InstanceRefConverter):
    def _unwrap_object(self, space, w_obj):
        # moving is same as by-ref, but have to check that move is allowed
        from pypy.module._cppyy.interp_cppyy import W_CPPClass, INSTANCE_FLAGS_IS_R_VALUE
        if isinstance(w_obj, W_CPPClass):
            if w_obj.flags & INSTANCE_FLAGS_IS_R_VALUE:
                w_obj.flags &= ~INSTANCE_FLAGS_IS_R_VALUE
                return InstanceRefConverter._unwrap_object(self, space, w_obj)
        raise oefmt(space.w_ValueError, "object is not an rvalue")


class InstanceConverter(InstanceRefConverter):

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible       # TODO: by-value is a jit_libffi special case

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = rffi.cast(capi.C_OBJECT, self._get_raw_address(space, w_obj, offset))
        from pypy.module._cppyy import interp_cppyy
        return interp_cppyy.wrap_cppinstance(space, address, self.clsdecl, do_cast=False)

    def to_memory(self, space, w_obj, w_value, offset):
        self._is_abstract(space)


class InstancePtrConverter(InstanceRefConverter):
    typecode    = 'o'

    def _unwrap_object(self, space, w_obj):
        try:
            return InstanceRefConverter._unwrap_object(self, space, w_obj)
        except OperationError as e:
            # if not instance, allow certain special cases
            if is_nullpointer_specialcase(space, w_obj):
                return capi.C_NULL_OBJECT
            raise e

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = rffi.cast(capi.C_OBJECT, self._get_raw_address(space, w_obj, offset))
        from pypy.module._cppyy import interp_cppyy
        return interp_cppyy.wrap_cppinstance(space, address, self.clsdecl, do_cast=False)

    def to_memory(self, space, w_obj, w_value, offset):
        address = rffi.cast(rffi.VOIDPP, self._get_raw_address(space, w_obj, offset))
        address[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_value))

class InstancePtrPtrConverter(InstancePtrConverter):
    _immutable_fields_ = ['uses_local']

    uses_local = True

    def convert_argument(self, space, w_obj, address, call_local):
        r = rffi.cast(rffi.VOIDPP, call_local)
        r[0] = rffi.cast(rffi.VOIDP, self._unwrap_object(space, w_obj))
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, call_local)
        address = rffi.cast(capi.C_OBJECT, address)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'o'

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        # TODO: finalize_call not yet called for fast call (see interp_cppyy.py)
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

    def finalize_call(self, space, w_obj, call_local):
        from pypy.module._cppyy.interp_cppyy import W_CPPClass
        assert isinstance(w_obj, W_CPPClass)
        r = rffi.cast(rffi.VOIDPP, call_local)
        w_obj._rawobject = rffi.cast(capi.C_OBJECT, r[0])

    def from_memory(self, space, w_obj, w_pycppclass, offset):
        address = rffi.cast(capi.C_OBJECT, self._get_raw_address(space, w_obj, offset))
        from pypy.module._cppyy import interp_cppyy
        return interp_cppyy.wrap_cppinstance(
            space, address, self.clsdecl, do_cast=False, is_ref=True)

class StdStringConverter(InstanceConverter):

    def __init__(self, space, extra):
        from pypy.module._cppyy import interp_cppyy
        cppclass = interp_cppyy.scope_byname(space, capi.std_string_name)
        InstanceConverter.__init__(self, space, cppclass)

    def _unwrap_object(self, space, w_obj):
        from pypy.module._cppyy.interp_cppyy import W_CPPClass
        if isinstance(w_obj, W_CPPClass):
            arg = InstanceConverter._unwrap_object(self, space, w_obj)
            return capi.c_stdstring2stdstring(space, arg)
        else:
            return capi.c_charp2stdstring(space, space.text_w(w_obj), space.len_w(w_obj))

    def to_memory(self, space, w_obj, w_value, offset):
        try:
            address = rffi.cast(capi.C_OBJECT, self._get_raw_address(space, w_obj, offset))
            assign = self.clsdecl.get_overload("__assign__")
            from pypy.module._cppyy import interp_cppyy
            assign.call(
                interp_cppyy.wrap_cppinstance(space, address, self.clsdecl, do_cast=False), [w_value])
        except Exception:
            InstanceConverter.to_memory(self, space, w_obj, w_value, offset)

    def free_argument(self, space, arg, call_local):
        capi.c_destruct(space, self.clsdecl, rffi.cast(capi.C_OBJECT, rffi.cast(rffi.VOIDPP, arg)[0]))

class StdStringRefConverter(InstancePtrConverter):
    _immutable_fields_ = ['cppclass', 'typecode']

    typecode    = 'V'

    def __init__(self, space, extra):
        from pypy.module._cppyy import interp_cppyy
        cppclass = interp_cppyy.scope_byname(space, capi.std_string_name)
        InstancePtrConverter.__init__(self, space, cppclass)


class PyObjectConverter(TypeConverter):
    def cffi_type(self, space):
        state = space.fromcache(ffitypes.State)
        return state.c_voidp

    def convert_argument(self, space, w_obj, address, call_local):
        if hasattr(space, "fake"):
            raise NotImplementedError
        space.getbuiltinmodule("cpyext")
        from pypy.module.cpyext.pyobject import make_ref
        ref = make_ref(space, w_obj)
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, ref)
        ba = rffi.cast(rffi.CCHARP, address)
        ba[capi.c_function_arg_typeoffset(space)] = 'a'

    def convert_argument_libffi(self, space, w_obj, address, call_local):
        # TODO: free_argument not yet called for fast call (see interp_cppyy.py)
        from pypy.module._cppyy.interp_cppyy import FastCallNotPossible
        raise FastCallNotPossible

        # proposed implementation:
        """if hasattr(space, "fake"):
            raise NotImplementedError
        space.getbuiltinmodule("cpyext")
        from pypy.module.cpyext.pyobject import make_ref
        ref = make_ref(space, w_obj)
        x = rffi.cast(rffi.VOIDPP, address)
        x[0] = rffi.cast(rffi.VOIDP, ref)"""

    def free_argument(self, space, arg, call_local):
        if hasattr(space, "fake"):
            raise NotImplementedError
        space.getbuiltinmodule("cpyext")
        from pypy.module.cpyext.pyobject import Py_DecRef, PyObject
        Py_DecRef(space, rffi.cast(PyObject, rffi.cast(rffi.VOIDPP, arg)[0]))


class MacroConverter(TypeConverter):
    def from_memory(self, space, w_obj, w_pycppclass, offset):
        # TODO: get the actual type info from somewhere ...
        address = self._get_raw_address(space, w_obj, offset)
        longptr = rffi.cast(rffi.LONGP, address)
        return space.newlong(longptr[0])


_converters = {}         # builtin and custom types
_a_converters = {}       # array and ptr versions of above
def get_converter(space, _name, default):
    # The matching of the name to a converter should follow:
    #   1) full, exact match
    #       1a) const-removed match
    #   2) match of decorated, unqualified type
    #   3) accept ref as pointer (for the stubs, const& can be
    #       by value, but that does not work for the ffi path)
    #   4) generalized cases (covers basically all user classes)
    #   5) void* or void converter (which fails on use)

    name = capi.c_resolve_name(space, _name)

    #   1) full, exact match
    try:
        return _converters[name](space, default)
    except KeyError:
        pass

    #   1a) const-removed match
    try:
        return _converters[helper.remove_const(name)](space, default)
    except KeyError:
        pass

    #   2) match of decorated, unqualified type
    compound = helper.compound(name)
    clean_name = capi.c_resolve_name(space, helper.clean_type(name))
    try:
        # array_index may be negative to indicate no size or no size found
        array_size = helper.array_size(_name)     # uses original arg
        return _a_converters[clean_name+compound](space, array_size)
    except KeyError:
        pass

    #   3) TODO: accept ref as pointer

    #   4) generalized cases (covers basically all user classes)
    from pypy.module._cppyy import interp_cppyy
    scope_decl = interp_cppyy.scope_byname(space, clean_name)
    if scope_decl:
        # type check for the benefit of the annotator
        from pypy.module._cppyy.interp_cppyy import W_CPPClassDecl
        clsdecl = space.interp_w(W_CPPClassDecl, scope_decl, can_be_None=False)
        if compound == "*":
            return InstancePtrConverter(space, clsdecl)
        elif compound == "&":
            return InstanceRefConverter(space, clsdecl)
        elif compound == "&&":
            return InstanceMoveConverter(space, clsdecl)
        elif compound == "**":
            return InstancePtrPtrConverter(space, clsdecl)
        elif compound == "":
            return InstanceConverter(space, clsdecl)
    elif capi.c_is_enum(space, clean_name):
        return _converters['unsigned'](space, default)

    #   5) void* or void converter (which fails on use)
    if 0 <= compound.find('*'):
        return VoidPtrConverter(space, default)  # "user knows best"

    # return a void converter here, so that the class can be build even
    # when some types are unknown
    return VoidConverter(space, name)            # fails on use


_converters["bool"]                     = BoolConverter
_converters["char"]                     = CharConverter
_converters["float"]                    = FloatConverter
_converters["const float&"]             = ConstFloatRefConverter
_converters["double"]                   = DoubleConverter
_converters["const double&"]            = ConstDoubleRefConverter
#_converters["long double"]              = LongDoubleConverter
#_converters["const long double&"]       = ConstLongDoubleRefConverter
_converters["const char*"]              = CStringConverter
_converters["void*"]                    = VoidPtrConverter
_converters["void**"]                   = VoidPtrPtrConverter
_converters["void*&"]                   = VoidPtrRefConverter

# special cases (note: 'string' aliases added below)
_converters["std::basic_string<char>"]           = StdStringConverter
_converters["const std::basic_string<char>&"]    = StdStringConverter     # TODO: shouldn't copy
_converters["std::basic_string<char>&"]          = StdStringRefConverter

_converters["PyObject*"]                         = PyObjectConverter

_converters["#define"]                           = MacroConverter

# add basic (builtin) converters
def _build_basic_converters():
    "NOT_RPYTHON"
    # signed types (use strtoll in setting of default in __init__)
    type_info = (
        (rffi.SHORT,      ("short", "short int"),          'h'),
        (rffi.INT,        ("int", "internal_enum_type_t"), 'i'),
    )

    # constref converters exist only b/c the stubs take constref by value, whereas
    # libffi takes them by pointer (hence it needs the fast-path in testing); note
    # that this is list is not complete, as some classes are specialized

    for c_type, names, c_tc in type_info:
        class BasicConverter(ffitypes.typeid(c_type), IntTypeConverterMixin, TypeConverter):
            _immutable_ = True
            typecode = c_tc
            def __init__(self, space, default):
                self.default = rffi.cast(self.c_type, capi.c_strtoll(space, default))
        class ConstRefConverter(ConstRefNumericTypeConverterMixin, BasicConverter):
            _immutable_ = True
        for name in names:
            _converters[name] = BasicConverter
            _converters["const "+name+"&"] = ConstRefConverter

    type_info = (
        (rffi.LONG,       ("long", "long int"),                        'l'),
        (rffi.LONGLONG,   ("long long", "long long int", "Long64_t"),  'q'),
    )

    for c_type, names, c_tc in type_info:
        class BasicConverter(ffitypes.typeid(c_type), IntTypeConverterMixin, TypeConverter):
            _immutable_ = True
            typecode = c_tc
            def __init__(self, space, default):
                self.default = rffi.cast(self.c_type, capi.c_strtoll(space, default))
        class ConstRefConverter(ConstRefNumericTypeConverterMixin, BasicConverter):
            _immutable_ = True
        for name in names:
            _converters[name] = BasicConverter
            _converters["const "+name+"&"] = ConstRefConverter

    # unsigned integer types (use strtoull in setting of default in __init__)
    type_info = (
        (rffi.USHORT,     ("unsigned short", "unsigned short int"),                            'H'),
        (rffi.UINT,       ("unsigned", "unsigned int"),                                        'I'),
        (rffi.ULONG,      ("unsigned long", "unsigned long int"),                              'L'),
        (rffi.ULONGLONG,  ("unsigned long long", "unsigned long long int", "ULong64_t"),       'Q'),
    )

    for c_type, names, c_tc in type_info:
        class BasicConverter(ffitypes.typeid(c_type), IntTypeConverterMixin, TypeConverter):
            _immutable_ = True
            typecode = c_tc
            def __init__(self, space, default):
                self.default = rffi.cast(self.c_type, capi.c_strtoull(space, default))
        class ConstRefConverter(ConstRefNumericTypeConverterMixin, BasicConverter):
            _immutable_ = True
        for name in names:
            _converters[name] = BasicConverter
            _converters["const "+name+"&"] = ConstRefConverter

_build_basic_converters()

# create the array and pointer converters; all real work is in the mixins
def _build_array_converters():
    "NOT_RPYTHON"
    array_info = (
        ('b', rffi.sizeof(rffi.UCHAR),      ("bool",)),    # is debatable, but works ...
        ('h', rffi.sizeof(rffi.SHORT),      ("short int", "short")),
        ('H', rffi.sizeof(rffi.USHORT),     ("unsigned short int", "unsigned short")),
        ('i', rffi.sizeof(rffi.INT),        ("int",)),
        ('I', rffi.sizeof(rffi.UINT),       ("unsigned int", "unsigned")),
        ('l', rffi.sizeof(rffi.LONG),       ("long int", "long")),
        ('L', rffi.sizeof(rffi.ULONG),      ("unsigned long int", "unsigned long")),
        ('q', rffi.sizeof(rffi.LONGLONG),   ("long long", "long long int", "Long64_t")),
        ('Q', rffi.sizeof(rffi.ULONGLONG),  ("unsigned long long", "unsigned long long int", "ULong64_t")),
        ('f', rffi.sizeof(rffi.FLOAT),      ("float",)),
        ('d', rffi.sizeof(rffi.DOUBLE),     ("double",)),
#        ('g', rffi.sizeof(rffi.LONGDOUBLE), ("long double",)),
    )

    for tcode, tsize, names in array_info:
        class ArrayConverter(ArrayTypeConverterMixin, TypeConverter):
            typecode = tcode
            typesize = tsize
        class PtrConverter(PtrTypeConverterMixin, TypeConverter):
            typecode = tcode
            typesize = tsize
        for name in names:
            _a_converters[name+'[]'] = ArrayConverter
            _a_converters[name+'*']  = PtrConverter

    # special case, const char* w/ size and w/o '\0'
    _a_converters["const char[]"] = CStringConverterWithSize

_build_array_converters()

# add another set of aliased names
def _add_aliased_converters():
    "NOT_RPYTHON"
    aliases = (
        ("char",                            "unsigned char"), # TODO: check
        ("char",                            "signed char"),   # TODO: check
        ("const char*",                     "char*"),

        ("std::basic_string<char>",         "string"),
        ("const std::basic_string<char>&",  "const string&"),
        ("std::basic_string<char>&",        "string&"),

        ("PyObject*",                       "_object*"),
    )
 
    for c_type, alias in aliases:
        _converters[alias] = _converters[c_type]
_add_aliased_converters()
