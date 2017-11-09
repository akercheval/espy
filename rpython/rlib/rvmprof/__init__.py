from rpython.rlib.objectmodel import specialize
from rpython.rlib.rvmprof.rvmprof import _get_vmprof, VMProfError
from rpython.rlib.rvmprof.rvmprof import vmprof_execute_code, MAX_FUNC_NAME
from rpython.rlib.rvmprof.rvmprof import _was_registered
from rpython.rlib.rvmprof.cintf import VMProfPlatformUnsupported
from rpython.rtyper.lltypesystem import rffi, lltype

#
# See README.txt.
#

#vmprof_execute_code(): implemented directly in rvmprof.py

def register_code_object_class(CodeClass, full_name_func):
    _get_vmprof().register_code_object_class(CodeClass, full_name_func)

@specialize.argtype(0)
def register_code(code, name):
    _get_vmprof().register_code(code, name)

@specialize.call_location()
def get_unique_id(code):
    """Return the internal unique ID of a code object.  Can only be
    called after register_code().  Call this in the jitdriver's
    method 'get_unique_id(*greenkey)'.  This always returns 0 if we
    didn't call register_code_object_class() on the class.
    """
    assert code is not None
    if _was_registered(code.__class__):
        # '0' can occur here too, if the code object was prebuilt,
        # or if register_code() was not called for another reason.
        return code._vmprof_unique_id
    return 0

def enable(fileno, interval, memory=0, native=0, real_time=0):
    _get_vmprof().enable(fileno, interval, memory, native, real_time)

def disable():
    _get_vmprof().disable()

def is_enabled():
    vmp = _get_vmprof()
    return vmp.is_enabled

def get_profile_path(space):
    vmp = _get_vmprof()
    if not vmp.is_enabled:
        return None

    with rffi.scoped_alloc_buffer(4096) as buf:
        length = vmp.cintf.vmprof_get_profile_path(buf.raw, buf.size) 
        if length == -1:
            return ""
        return buf.str(length)

    return None

def stop_sampling(space):
    fd = _get_vmprof().cintf.vmprof_stop_sampling()
    return rffi.cast(lltype.Signed, fd)

def start_sampling(space):
    _get_vmprof().cintf.vmprof_start_sampling()
