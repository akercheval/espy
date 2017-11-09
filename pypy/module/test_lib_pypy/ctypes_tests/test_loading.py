import py
from ctypes import *
import sys
import os, StringIO
from ctypes.util import find_library
from ctypes.test import is_resource_enabled

libc_name = None
if os.name == "nt":
    libc_name = "msvcrt"
elif os.name == "ce":
    libc_name = "coredll"
elif sys.platform == "cygwin":
    libc_name = "cygwin1.dll"
else:
    libc_name = find_library("c")

if True or is_resource_enabled("printing"):
    print >> sys.stderr, "\tfind_library('c') -> ", find_library('c')
    print >> sys.stderr, "\tfind_library('m') -> ", find_library('m')

class TestLoader:

    unknowndll = "xxrandomnamexx"

    if libc_name is not None:
        def test_load(self):
            CDLL(libc_name)
            CDLL(os.path.basename(libc_name))
            raises(OSError, CDLL, self.unknowndll)

    if libc_name is not None and os.path.basename(libc_name) == "libc.so.6":
        def test_load_version(self):
            cdll.LoadLibrary("libc.so.6")
            # linux uses version, libc 9 should not exist
            raises(OSError, cdll.LoadLibrary, "libc.so.9")
            raises(OSError, cdll.LoadLibrary, self.unknowndll)

    def test_find(self):
        for name in ("c", "m"):
            lib = find_library(name)
            if lib:
                cdll.LoadLibrary(lib)
                CDLL(lib)

    def test__handle(self):
        lib = find_library("c")
        if lib:
            cdll = CDLL(lib)
            assert type(cdll._handle) in (int, long)

    if os.name in ("nt", "ce"):
        def test_load_library(self):
            if is_resource_enabled("printing"):
                print find_library("kernel32")
                print find_library("user32")

            if os.name == "nt":
                windll.kernel32.GetModuleHandleW
                windll["kernel32"].GetModuleHandleW
                windll.LoadLibrary("kernel32").GetModuleHandleW
                WinDLL("kernel32").GetModuleHandleW
            elif os.name == "ce":
                windll.coredll.GetModuleHandleW
                windll["coredll"].GetModuleHandleW
                windll.LoadLibrary("coredll").GetModuleHandleW
                WinDLL("coredll").GetModuleHandleW

        def test_load_ordinal_functions(self):
            import conftest
            _ctypes_test = str(conftest.sofile)
            dll = CDLL(_ctypes_test)
            # We load the same function both via ordinal and name
            func_ord = dll[2]
            func_name = dll.GetString
            # addressof gets the address where the function pointer is stored
            a_ord = addressof(func_ord)
            a_name = addressof(func_name)
            f_ord_addr = c_void_p.from_address(a_ord).value
            f_name_addr = c_void_p.from_address(a_name).value
            assert hex(f_ord_addr) == hex(f_name_addr)

            raises(AttributeError, dll.__getitem__, 1234)

if __name__ == "__main__":
    unittest.main()
