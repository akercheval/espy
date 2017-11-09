import py
from support import BaseCTypesTestChecker
from ctypes import *

def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    mod.dll = CDLL(_ctypes_test)

class TestSlices(BaseCTypesTestChecker):
    def test_getslice_cint(self):
        a = (c_int * 100)(*xrange(1100, 1200))
        b = range(1100, 1200)
        assert a[0:2] == b[0:2]
        assert len(a) == len(b)
        assert a[5:7] == b[5:7]
        assert a[-1] == b[-1]
        assert a[:] == b[:]

        a[0:5] = range(5, 10)
        assert a[0:5] == range(5, 10)

    def test_setslice_cint(self):
        a = (c_int * 100)(*xrange(1100, 1200))
        b = range(1100, 1200)

        a[32:47] = range(32, 47)
        assert a[32:47] == range(32, 47)

        from operator import setslice

        # TypeError: int expected instead of str instance
        raises(TypeError, setslice, a, 0, 5, "abcde")
        # TypeError: int expected instead of str instance
        raises(TypeError, setslice, a, 0, 5, ["a", "b", "c", "d", "e"])
        # TypeError: int expected instead of float instance
        raises(TypeError, setslice, a, 0, 5, [1, 2, 3, 4, 3.14])
        # ValueError: Can only assign sequence of same size
        raises(ValueError, setslice, a, 0, 5, range(32))

    def test_char_ptr(self):
        s = "abcdefghijklmnopqrstuvwxyz"

        dll.my_strdup.restype = POINTER(c_char)
        dll.my_free.restype = None
        res = dll.my_strdup(s)
        assert res[:len(s)] == s

        import operator
        raises(TypeError, operator.setslice,
                          res, 0, 5, u"abcde")
        dll.my_free(res)

        dll.my_strdup.restype = POINTER(c_byte)
        res = dll.my_strdup(s)
        assert res[:len(s)] == range(ord("a"), ord("z")+1)
        dll.my_free(res)

    def test_char_ptr_with_free(self):
        s = "abcdefghijklmnopqrstuvwxyz"

        class allocated_c_char_p(c_char_p):
            pass

        dll.my_free.restype = None
        def errcheck(result, func, args):
            retval = result.value
            dll.my_free(result)
            return retval

        dll.my_strdup.restype = allocated_c_char_p
        dll.my_strdup.errcheck = errcheck
        try:
            res = dll.my_strdup(s)
            assert res == s
        finally:
            del dll.my_strdup.errcheck


    def test_char_array(self):
        s = "abcdefghijklmnopqrstuvwxyz\0"

        p = (c_char * 27)(*s)
        assert p[:] == s


    try:
        c_wchar
    except NameError:
        pass
    else:
        def test_wchar_ptr(self):
            s = u"abcdefghijklmnopqrstuvwxyz\0"

            dll.my_wcsdup.restype = POINTER(c_wchar)
            dll.my_wcsdup.argtypes = POINTER(c_wchar),
            dll.my_free.restype = None
            res = dll.my_wcsdup(s)
            assert res[:len(s)] == s

            import operator
            raises(TypeError, operator.setslice,
                              res, 0, 5, u"abcde")
            dll.my_free(res)

            if sizeof(c_wchar) == sizeof(c_short):
                dll.my_wcsdup.restype = POINTER(c_short)
            elif sizeof(c_wchar) == sizeof(c_int):
                dll.my_wcsdup.restype = POINTER(c_int)
            elif sizeof(c_wchar) == sizeof(c_long):
                dll.my_wcsdup.restype = POINTER(c_long)
            else:
                return
            res = dll.my_wcsdup(s)
            assert res[:len(s)-1] == range(ord("a"), ord("z")+1)
            dll.my_free(res)
