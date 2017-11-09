import os
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.rlib.rarithmetic import intmask
from rpython.rlib import jit, jit_libffi, libffi, rdynload, objectmodel
from rpython.rlib.rarithmetic import r_singlefloat
from rpython.tool import leakfinder

from pypy.interpreter.gateway import interp2app
from pypy.interpreter.error import oefmt

from pypy.module._cffi_backend import ctypefunc, ctypeprim, cdataobj, misc
from pypy.module._cffi_backend import newtype
from pypy.module._cppyy import ffitypes

from pypy.module._cppyy.capi.capi_types import C_SCOPE, C_TYPE, C_OBJECT,\
   C_METHOD, C_INDEX, C_INDEX_ARRAY, WLAVC_INDEX, C_FUNC_PTR


backend_library = 'libcppyy_backend.so'

# this is not technically correct, but will do for now
std_string_name = 'std::basic_string<char>'

class _Arg:         # poor man's union
    _immutable_ = True
    def __init__(self, tc, h = 0, l = -1, s = '', p = rffi.cast(rffi.VOIDP, 0)):
        self.tc      = tc
        self._handle = h
        self._long   = l
        self._string = s
        self._voidp  = p

class _ArgH(_Arg):
    _immutable_ = True
    def __init__(self, val):
        _Arg.__init__(self, 'h', h = val)

class _ArgL(_Arg):
    _immutable_ = True
    def __init__(self, val):
        _Arg.__init__(self, 'l', l = val)

class _ArgS(_Arg):
    _immutable_ = True
    def __init__(self, val):
        _Arg.__init__(self, 's', s = val)

class _ArgP(_Arg):
    _immutable_ = True
    def __init__(self, val):
        _Arg.__init__(self, 'p', p = val)

# For the loadable CAPI, the calls start and end in RPython. Therefore, the standard
# _call of W_CTypeFunc, which expects wrapped objects, does not quite work: some
# vars (e.g. void* equivalent) can not be wrapped, and others (such as rfloat) risk
# rounding problems. This W_RCTypeFun then, takes args, instead of args_w. Note that
# rcall() is a new method, so as to not interfere with the base class call and _call
# when rtyping. It is also called directly (see call_capi below).
class W_RCTypeFunc(ctypefunc.W_CTypeFunc):
    @jit.unroll_safe
    def rcall(self, funcaddr, args):
        assert self.cif_descr
        self = jit.promote(self)
        # no checking of len(args) needed, as calls in this context are not dynamic

        # The following code is functionally similar to W_CTypeFunc._call, but its
        # implementation is tailored to the restricted use (include memory handling)
        # of the CAPI calls.
        space = self.space
        cif_descr = self.cif_descr
        size = cif_descr.exchange_size
        raw_string = rffi.cast(rffi.CCHARP, 0)    # only ever have one in the CAPI
        buffer = lltype.malloc(rffi.CCHARP.TO, size, flavor='raw')
        try:
            for i in range(len(args)):
                data = rffi.ptradd(buffer, cif_descr.exchange_args[i])
                obj = args[i]
                argtype = self.fargs[i]
                # the following is clumsy, but the data types used as arguments are
                # very limited, so it'll do for now
                if obj.tc == 'l':
                    assert isinstance(argtype, ctypeprim.W_CTypePrimitiveSigned)
                    misc.write_raw_signed_data(data, rffi.cast(rffi.LONG, obj._long), argtype.size)
                elif obj.tc == 'h':
                    assert isinstance(argtype, ctypeprim.W_CTypePrimitiveUnsigned)
                    misc.write_raw_unsigned_data(data, rffi.cast(rffi.ULONG, obj._handle), argtype.size)
                elif obj.tc == 'p':
                    assert obj._voidp != rffi.cast(rffi.VOIDP, 0)
                    data = rffi.cast(rffi.VOIDPP, data)
                    data[0] = obj._voidp
                else:    # only other use is sring
                    assert obj.tc == 's'
                    n = len(obj._string)
                    assert raw_string == rffi.cast(rffi.CCHARP, 0)
                    # XXX could use rffi.get_nonmovingbuffer_final_null()
                    raw_string = rffi.str2charp(obj._string)
                    data = rffi.cast(rffi.CCHARPP, data)
                    data[0] = raw_string

            jit_libffi.jit_ffi_call(cif_descr,
                                    rffi.cast(rffi.VOIDP, funcaddr),
                                    buffer)

            resultdata = rffi.ptradd(buffer, cif_descr.exchange_result)
            # this wrapping is unnecessary, but the assumption is that given the
            # immediate unwrapping, the round-trip is removed
            w_res = self.ctitem.copy_and_convert_to_object(resultdata)
        finally:
            if raw_string != rffi.cast(rffi.CCHARP, 0):
                rffi.free_charp(raw_string)
            lltype.free(buffer, flavor='raw')
        return w_res

class State(object):
    def __init__(self, space):
        self.backend = None
        self.capi_calls = {}

        nt = newtype     # module from _cffi_backend
        state = space.fromcache(ffitypes.State)   # factored out common types

        # TODO: the following need to match up with the globally defined C_XYZ low-level
        # types (see capi/__init__.py), but by using strings here, that isn't guaranteed
        c_opaque_ptr = state.c_ulong
 
        c_scope       = c_opaque_ptr
        c_type        = c_scope
        c_object      = c_opaque_ptr
        c_method      = c_opaque_ptr
        c_index       = state.c_long
        c_index_array = state.c_voidp

        c_void    = state.c_void
        c_char    = state.c_char
        c_uchar   = state.c_uchar
        c_short   = state.c_short
        c_int     = state.c_int
        c_long    = state.c_long
        c_llong   = state.c_llong
        c_ullong  = state.c_ullong
        c_float   = state.c_float
        c_double  = state.c_double
        c_ldouble = state.c_ldouble

        c_ccharp = state.c_ccharp
        c_voidp  = state.c_voidp

        c_size_t = nt.new_primitive_type(space, 'size_t')
        c_ptrdiff_t = nt.new_primitive_type(space, 'ptrdiff_t')

        self.capi_call_ifaces = {
            # name to opaque C++ scope representation
            'num_scopes'               : ([c_scope],                  c_int),
            'scope_name'               : ([c_scope, c_int],           c_ccharp),

            'resolve_name'             : ([c_ccharp],                 c_ccharp),
            'get_scope'                : ([c_ccharp],                 c_scope),
            'actual_class'             : ([c_type, c_object],         c_type),

            # memory management
            'allocate'                 : ([c_type],                   c_object),
            'deallocate'               : ([c_type, c_object],         c_void),
            'destruct'                 : ([c_type, c_object],         c_void),

            # method/function dispatching
            'call_v'       : ([c_method, c_object, c_int, c_voidp],   c_void),
            'call_b'       : ([c_method, c_object, c_int, c_voidp],   c_uchar),
            'call_c'       : ([c_method, c_object, c_int, c_voidp],   c_char),

            'call_h'       : ([c_method, c_object, c_int, c_voidp],   c_short),
            'call_i'       : ([c_method, c_object, c_int, c_voidp],   c_int),
            'call_l'       : ([c_method, c_object, c_int, c_voidp],   c_long),
            'call_ll'      : ([c_method, c_object, c_int, c_voidp],   c_llong),
            'call_f'       : ([c_method, c_object, c_int, c_voidp],   c_float),
            'call_d'       : ([c_method, c_object, c_int, c_voidp],   c_double),
            'call_ld'      : ([c_method, c_object, c_int, c_voidp],   c_ldouble),

            'call_r'       : ([c_method, c_object, c_int, c_voidp],   c_voidp),
            # call_s actually takes an size_t* as last parameter, but this will do
            'call_s'       : ([c_method, c_object, c_int, c_voidp, c_voidp],    c_ccharp),

            'constructor'  : ([c_method, c_object, c_int, c_voidp],   c_object),
            'call_o'       : ([c_method, c_object, c_int, c_voidp, c_type],     c_object),

            'get_function_address'     : ([c_scope, c_index],         c_voidp), # TODO: verify

            # handling of function argument buffer
            'allocate_function_args'   : ([c_int],                    c_voidp),
            'deallocate_function_args' : ([c_voidp],                  c_void),
            'function_arg_sizeof'      : ([],                         c_size_t),
            'function_arg_typeoffset'  : ([],                         c_size_t),

            # scope reflection information
            'is_namespace'             : ([c_scope],                  c_int),
            'is_template'              : ([c_ccharp],                 c_int),
            'is_abstract'              : ([c_type],                   c_int),
            'is_enum'                  : ([c_ccharp],                 c_int),

            # type/class reflection information
            'final_name'               : ([c_type],                   c_ccharp),
            'scoped_final_name'        : ([c_type],                   c_ccharp),
            'has_complex_hierarchy'    : ([c_type],                   c_int),
            'num_bases'                : ([c_type],                   c_int),
            'base_name'                : ([c_type, c_int],            c_ccharp),
            'is_subtype'               : ([c_type, c_type],           c_int),

            'base_offset'              : ([c_type, c_type, c_object, c_int],    c_ptrdiff_t),

            # method/function reflection information
            'num_methods'              : ([c_scope],                  c_int),
            'method_index_at'          : ([c_scope, c_int],           c_index),
            'method_indices_from_name' : ([c_scope, c_ccharp],        c_index_array),

            'method_name'              : ([c_scope, c_index],         c_ccharp),
            'method_result_type'       : ([c_scope, c_index],         c_ccharp),
            'method_num_args'          : ([c_scope, c_index],         c_int),
            'method_req_args'          : ([c_scope, c_index],         c_int),
            'method_arg_type'          : ([c_scope, c_index, c_int],  c_ccharp),
            'method_arg_default'       : ([c_scope, c_index, c_int],  c_ccharp),
            'method_signature'         : ([c_scope, c_index, c_int],  c_ccharp),
            'method_prototype'         : ([c_scope, c_index, c_int],  c_ccharp),

            'method_is_template'       : ([c_scope, c_index],         c_int),
            'method_num_template_args' : ([c_scope, c_index],         c_int),
            'method_template_arg_name' : ([c_scope, c_index, c_index],          c_ccharp),

            'get_method'               : ([c_scope, c_index],         c_method),
            'get_global_operator'      : ([c_scope, c_scope, c_scope, c_ccharp],   c_index),

            # method properties
            'is_constructor'           : ([c_type, c_index],          c_int),
            'is_staticmethod'          : ([c_type, c_index],          c_int),

            # data member reflection information
            'num_datamembers'          : ([c_scope],                  c_int),
            'datamember_name'          : ([c_scope, c_int],           c_ccharp),
            'datamember_type'          : ([c_scope, c_int],           c_ccharp),
            'datamember_offset'        : ([c_scope, c_int],           c_ptrdiff_t),

            'datamember_index'         : ([c_scope, c_ccharp],        c_int),

            # data member properties
            'is_publicdata'            : ([c_scope, c_int],           c_int),
            'is_staticdata'            : ([c_scope, c_int],           c_int),

            # misc helpers
            'strtoll'                  : ([c_ccharp],                 c_llong),
            'strtoull'                 : ([c_ccharp],                 c_ullong),
            'free'                     : ([c_voidp],                  c_void),

            'charp2stdstring'          : ([c_ccharp, c_size_t],       c_object),
            #stdstring2charp  actually takes an size_t* as last parameter, but this will do
            'stdstring2charp'          : ([c_object, c_voidp],        c_ccharp),
            'stdstring2stdstring'      : ([c_object],                 c_object),

            'stdvector_valuetype'      : ([c_ccharp],                 c_ccharp),
            'stdvector_valuesize'      : ([c_ccharp],                 c_size_t),

        }

        # size/offset are backend-specific but fixed after load
        self.c_sizeof_farg = 0
        self.c_offset_farg = 0


def load_backend(space):
    state = space.fromcache(State)
    if state.backend is None:
        from pypy.module._cffi_backend.libraryobj import W_Library
        dldflags = rdynload.RTLD_LOCAL | rdynload.RTLD_LAZY
        if os.environ.get('CPPYY_BACKEND_LIBRARY'):
            libname = os.environ['CPPYY_BACKEND_LIBRARY']
            state.backend = W_Library(space, libname, dldflags)
        else:
            # try usual lookups
            state.backend = W_Library(space, backend_library, dldflags)

        if state.backend:
            # fix constants
            state.c_sizeof_farg = _cdata_to_size_t(
                space, call_capi(space, 'function_arg_sizeof', []))
            state.c_offset_farg = _cdata_to_size_t(
                space, call_capi(space, 'function_arg_typeoffset', []))

def verify_backend(space):
    try:
        load_backend(space)
    except Exception:
        if objectmodel.we_are_translated():
            raise oefmt(space.w_ImportError,
                        "missing reflection library %s", backend_library)
        return False
    return True

def call_capi(space, name, args):
    state = space.fromcache(State)
    try:
        c_call = state.capi_calls[name]
    except KeyError:
        if state.backend is None:
            load_backend(space)
        iface = state.capi_call_ifaces[name]
        cfunc = W_RCTypeFunc(space, iface[0], iface[1], False)
        c_call = state.backend.load_function(cfunc, 'cppyy_'+name)
        # TODO: there must be a better way to trick the leakfinder ...
        if not objectmodel.we_are_translated():
            leakfinder.remember_free(c_call.ctype.cif_descr._obj0)
        state.capi_calls[name] = c_call
    with c_call as ptr:
        return c_call.ctype.rcall(ptr, args)

def _cdata_to_cobject(space, w_cdata):
    return rffi.cast(C_OBJECT, space.uint_w(w_cdata))

def _cdata_to_size_t(space, w_cdata):
    return rffi.cast(rffi.SIZE_T, space.uint_w(w_cdata))

def _cdata_to_ptrdiff_t(space, w_cdata):
    return rffi.cast(rffi.LONG, space.int_w(w_cdata))

def _cdata_to_ptr(space, w_cdata): # TODO: this is both a hack and dreadfully slow
    w_cdata = space.interp_w(cdataobj.W_CData, w_cdata, can_be_None=False)
    ptr = w_cdata.unsafe_escaping_ptr()
    return rffi.cast(rffi.VOIDP, ptr)

def _cdata_to_ccharp(space, w_cdata):
    ptr = _cdata_to_ptr(space, w_cdata)      # see above ... something better?
    return rffi.cast(rffi.CCHARP, ptr)

# name to opaque C++ scope representation ------------------------------------
def c_num_scopes(space, cppscope):
    return space.int_w(call_capi(space, 'num_scopes', [_ArgH(cppscope.handle)]))
def c_scope_name(space, cppscope, iscope):
    args = [_ArgH(cppscope.handle), _ArgL(iscope)]
    return charp2str_free(space, call_capi(space, 'scope_name', args))

def c_resolve_name(space, name):
    return charp2str_free(space, call_capi(space, 'resolve_name', [_ArgS(name)]))
def c_get_scope_opaque(space, name):
    return rffi.cast(C_SCOPE, space.uint_w(call_capi(space, 'get_scope', [_ArgS(name)])))
def c_actual_class(space, cppclass, cppobj):
    args = [_ArgH(cppclass.handle), _ArgH(cppobj)]
    return rffi.cast(C_TYPE, space.uint_w(call_capi(space, 'actual_class', args)))

# memory management ----------------------------------------------------------
def c_allocate(space, cppclass):
    return _cdata_to_cobject(space, call_capi(space, 'allocate', [_ArgH(cppclass.handle)]))
def c_deallocate(space, cppclass, cppobject):
    call_capi(space, 'deallocate', [_ArgH(cppclass.handle), _ArgH(cppobject)])
def c_destruct(space, cppclass, cppobject):
    call_capi(space, 'destruct', [_ArgH(cppclass.handle), _ArgH(cppobject)])

# method/function dispatching ------------------------------------------------
def c_call_v(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    call_capi(space, 'call_v', args)
def c_call_b(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.UCHAR, space.c_uint_w(call_capi(space, 'call_b', args)))
def c_call_c(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.CHAR, space.text_w(call_capi(space, 'call_c', args))[0])
def c_call_h(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.SHORT, space.int_w(call_capi(space, 'call_h', args)))
def c_call_i(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.INT, space.c_int_w(call_capi(space, 'call_i', args)))
def c_call_l(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.LONG, space.int_w(call_capi(space, 'call_l', args)))
def c_call_ll(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.LONGLONG, space.r_longlong_w(call_capi(space, 'call_ll', args)))
def c_call_f(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.FLOAT, r_singlefloat(space.float_w(call_capi(space, 'call_f', args))))
def c_call_d(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.DOUBLE, space.float_w(call_capi(space, 'call_d', args)))
def c_call_ld(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return rffi.cast(rffi.LONGDOUBLE, space.float_w(call_capi(space, 'call_ld', args)))

def c_call_r(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return _cdata_to_ptr(space, call_capi(space, 'call_r', args))
def c_call_s(space, cppmethod, cppobject, nargs, cargs):
    length = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
    try:
        w_cstr = call_capi(space, 'call_s',
            [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs),
             _ArgP(rffi.cast(rffi.VOIDP, length))])
        cstr_len = intmask(length[0])
    finally:
        lltype.free(length, flavor='raw')
    return _cdata_to_ccharp(space, w_cstr), cstr_len

def c_constructor(space, cppmethod, cppobject, nargs, cargs):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs)]
    return _cdata_to_cobject(space, call_capi(space, 'constructor', args))
def c_call_o(space, cppmethod, cppobject, nargs, cargs, cppclass):
    args = [_ArgH(cppmethod), _ArgH(cppobject), _ArgL(nargs), _ArgP(cargs), _ArgH(cppclass.handle)]
    return _cdata_to_cobject(space, call_capi(space, 'call_o', args))

def c_get_function_address(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return rffi.cast(C_FUNC_PTR,
        _cdata_to_ptr(space, call_capi(space, 'get_function_address', args)))

# handling of function argument buffer ---------------------------------------
def c_allocate_function_args(space, size):
    return _cdata_to_ptr(space, call_capi(space, 'allocate_function_args', [_ArgL(size)]))
def c_deallocate_function_args(space, cargs):
    call_capi(space, 'deallocate_function_args', [_ArgP(cargs)])
def c_function_arg_sizeof(space):
    state = space.fromcache(State)
    return state.c_sizeof_farg
def c_function_arg_typeoffset(space):
    state = space.fromcache(State)
    return state.c_offset_farg

# scope reflection information -----------------------------------------------
def c_is_namespace(space, scope):
    return space.bool_w(call_capi(space, 'is_namespace', [_ArgH(scope)]))
def c_is_template(space, name):
    return space.bool_w(call_capi(space, 'is_template', [_ArgS(name)]))
def c_is_abstract(space, cpptype):
    return space.bool_w(call_capi(space, 'is_abstract', [_ArgH(cpptype)]))
def c_is_enum(space, name):
    return space.bool_w(call_capi(space, 'is_enum', [_ArgS(name)]))

# type/class reflection information ------------------------------------------
def c_final_name(space, cpptype):
    return charp2str_free(space, call_capi(space, 'final_name', [_ArgH(cpptype)]))
def c_scoped_final_name(space, cpptype):
    return charp2str_free(space, call_capi(space, 'scoped_final_name', [_ArgH(cpptype)]))
def c_has_complex_hierarchy(space, handle):
    return space.bool_w(call_capi(space, 'has_complex_hierarchy', [_ArgH(handle)]))
def c_num_bases(space, cppclass):
    return space.int_w(call_capi(space, 'num_bases', [_ArgH(cppclass.handle)]))
def c_base_name(space, cppclass, base_index):
    args = [_ArgH(cppclass.handle), _ArgL(base_index)]
    return charp2str_free(space, call_capi(space, 'base_name', args))
def c_is_subtype(space, derived, base):
    jit.promote(base)
    if derived == base:
        return bool(1)
    return space.bool_w(call_capi(space, 'is_subtype', [_ArgH(derived.handle), _ArgH(base.handle)]))

def _c_base_offset(space, derived_h, base_h, address, direction):
    args = [_ArgH(derived_h), _ArgH(base_h), _ArgH(address), _ArgL(direction)]
    return _cdata_to_ptrdiff_t(space, call_capi(space, 'base_offset', args))
def c_base_offset(space, derived, base, address, direction):
    if derived == base:
        return rffi.cast(rffi.LONG, 0)
    return _c_base_offset(space, derived.handle, base.handle, address, direction)
def c_base_offset1(space, derived_h, base, address, direction):
    return _c_base_offset(space, derived_h, base.handle, address, direction)

# method/function reflection information -------------------------------------
def c_num_methods(space, cppscope):
    args = [_ArgH(cppscope.handle)]
    return space.int_w(call_capi(space, 'num_methods', args))
def c_method_index_at(space, cppscope, imethod):
    args = [_ArgH(cppscope.handle), _ArgL(imethod)]
    return space.int_w(call_capi(space, 'method_index_at', args))
def c_method_indices_from_name(space, cppscope, name):
    args = [_ArgH(cppscope.handle), _ArgS(name)]
    indices = rffi.cast(C_INDEX_ARRAY,
                        _cdata_to_ptr(space, call_capi(space, 'method_indices_from_name', args)))
    if not indices:
        return []
    py_indices = []
    i = 0
    index = indices[i]
    while index != -1:
        i += 1
        py_indices.append(index)
        index = indices[i]
    c_free(space, rffi.cast(rffi.VOIDP, indices))   # c_free defined below
    return py_indices

def c_method_name(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return charp2str_free(space, call_capi(space, 'method_name', args))
def c_method_result_type(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return charp2str_free(space, call_capi(space, 'method_result_type', args))
def c_method_num_args(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return space.int_w(call_capi(space, 'method_num_args', args))
def c_method_req_args(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return space.int_w(call_capi(space, 'method_req_args', args))
def c_method_arg_type(space, cppscope, index, arg_index):
    args = [_ArgH(cppscope.handle), _ArgL(index), _ArgL(arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_type', args))
def c_method_arg_default(space, cppscope, index, arg_index):
    args = [_ArgH(cppscope.handle), _ArgL(index), _ArgL(arg_index)]
    return charp2str_free(space, call_capi(space, 'method_arg_default', args))
def c_method_signature(space, cppscope, index, show_formalargs=True):
    args = [_ArgH(cppscope.handle), _ArgL(index), _ArgL(show_formalargs)]
    return charp2str_free(space, call_capi(space, 'method_signature', args))
def c_method_prototype(space, cppscope, index, show_formalargs=True):
    args = [_ArgH(cppscope.handle), _ArgL(index), _ArgL(show_formalargs)]
    return charp2str_free(space, call_capi(space, 'method_prototype', args))

def c_method_is_template(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return space.bool_w(call_capi(space, 'method_is_template', args))
def _c_method_num_template_args(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return space.int_w(call_capi(space, 'method_num_template_args', args)) 
def c_template_args(space, cppscope, index):
    nargs = _c_method_num_template_args(space, cppscope, index)
    arg1 = _ArgH(cppscope.handle)
    arg2 = _ArgL(index)
    args = [c_resolve_name(space, charp2str_free(space,
                call_capi(space, 'method_template_arg_name', [arg1, arg2, _ArgL(iarg)]))
            ) for iarg in range(nargs)]
    return args

def c_get_method(space, cppscope, index):
    args = [_ArgH(cppscope.handle), _ArgL(index)]
    return rffi.cast(C_METHOD, space.uint_w(call_capi(space, 'get_method', args)))
def c_get_global_operator(space, nss, lc, rc, op):
    if nss is not None:
        args = [_ArgH(nss.handle), _ArgH(lc.handle), _ArgH(rc.handle), _ArgS(op)]
        return rffi.cast(WLAVC_INDEX, space.int_w(call_capi(space, 'get_global_operator', args)))
    return rffi.cast(WLAVC_INDEX, -1)

# method properties ----------------------------------------------------------
def c_is_constructor(space, cppclass, index):
    args = [_ArgH(cppclass.handle), _ArgL(index)]
    return space.bool_w(call_capi(space, 'is_constructor', args))
def c_is_staticmethod(space, cppclass, index):
    args = [_ArgH(cppclass.handle), _ArgL(index)]
    return space.bool_w(call_capi(space, 'is_staticmethod', args))

# data member reflection information -----------------------------------------
def c_num_datamembers(space, cppscope):
    return space.int_w(call_capi(space, 'num_datamembers', [_ArgH(cppscope.handle)]))
def c_datamember_name(space, cppscope, datamember_index):
    args = [_ArgH(cppscope.handle), _ArgL(datamember_index)]
    return charp2str_free(space, call_capi(space, 'datamember_name', args))
def c_datamember_type(space, cppscope, datamember_index):
    args = [_ArgH(cppscope.handle), _ArgL(datamember_index)]
    return  charp2str_free(space, call_capi(space, 'datamember_type', args))
def c_datamember_offset(space, cppscope, datamember_index):
    args = [_ArgH(cppscope.handle), _ArgL(datamember_index)]
    return _cdata_to_ptrdiff_t(space, call_capi(space, 'datamember_offset', args))

def c_datamember_index(space, cppscope, name):
    args = [_ArgH(cppscope.handle), _ArgS(name)]
    return space.int_w(call_capi(space, 'datamember_index', args))

# data member properties -----------------------------------------------------
def c_is_publicdata(space, cppscope, datamember_index):
    args = [_ArgH(cppscope.handle), _ArgL(datamember_index)]
    return space.bool_w(call_capi(space, 'is_publicdata', args))
def c_is_staticdata(space, cppscope, datamember_index):
    args = [_ArgH(cppscope.handle), _ArgL(datamember_index)]
    return space.bool_w(call_capi(space, 'is_staticdata', args))

# misc helpers ---------------------------------------------------------------
def c_strtoll(space, svalue):
    return space.r_longlong_w(call_capi(space, 'strtoll', [_ArgS(svalue)]))
def c_strtoull(space, svalue):
    return space.r_ulonglong_w(call_capi(space, 'strtoull', [_ArgS(svalue)]))
def c_free(space, voidp):
    call_capi(space, 'free', [_ArgP(voidp)])

def charp2str_free(space, cdata):
    charp = rffi.cast(rffi.CCHARP, _cdata_to_ptr(space, cdata))
    pystr = rffi.charp2str(charp)
    c_free(space, rffi.cast(rffi.VOIDP, charp))
    return pystr

def c_charp2stdstring(space, svalue, sz):
    return _cdata_to_cobject(space, call_capi(space, 'charp2stdstring',
        [_ArgS(svalue), _ArgH(rffi.cast(rffi.ULONG, sz))]))
def c_stdstring2charp(space, cppstr):
    sz = lltype.malloc(rffi.SIZE_TP.TO, 1, flavor='raw')
    try:
        w_cstr = call_capi(space, 'stdstring2charp',
            [_ArgH(cppstr), _ArgP(rffi.cast(rffi.VOIDP, sz))])
        cstr_len = intmask(sz[0])
    finally:
        lltype.free(sz, flavor='raw')
    return rffi.charpsize2str(_cdata_to_ccharp(space, w_cstr), cstr_len)
def c_stdstring2stdstring(space, cppobject):
    return _cdata_to_cobject(space, call_capi(space, 'stdstring2stdstring', [_ArgH(cppobject)]))

def c_stdvector_valuetype(space, pystr):
    return charp2str_free(space, call_capi(space, 'stdvector_valuetype', [_ArgS(pystr)]))

def c_stdvector_valuetype(space, pystr):
    return charp2str_free(space, call_capi(space, 'stdvector_valuetype', [_ArgS(pystr)]))
def c_stdvector_valuesize(space, pystr):
    return _cdata_to_size_t(space, call_capi(space, 'stdvector_valuesize', [_ArgS(pystr)]))


# TODO: factor these out ...
# pythonizations
def stdstring_c_str(space, w_self):
    """Return a python string taking into account \0"""

    from pypy.module._cppyy import interp_cppyy
    cppstr = space.interp_w(interp_cppyy.W_CPPClass, w_self, can_be_None=False)
    return space.newtext(c_stdstring2charp(space, cppstr._rawobject))

# setup pythonizations for later use at run-time
_pythonizations = {}
def register_pythonizations(space):
    "NOT_RPYTHON"

    allfuncs = [

        ### std::string
        stdstring_c_str,

    ]

    for f in allfuncs:
        _pythonizations[f.__name__] = interp2app(f).spacebind(space)

def _method_alias(space, w_pycppclass, m1, m2):
    space.setattr(w_pycppclass, space.newtext(m1),
                  space.getattr(w_pycppclass, space.newtext(m2)))

def pythonize(space, name, w_pycppclass):
    if name == "string":
        space.setattr(w_pycppclass, space.newtext("c_str"), _pythonizations["stdstring_c_str"])
        _method_alias(space, w_pycppclass, "_cppyy_as_builtin", "c_str")
        _method_alias(space, w_pycppclass, "__str__",           "c_str")
