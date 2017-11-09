# coding: latin-1
import ctypes
import py
from support import BaseCTypesTestChecker

try:
    ctypes.c_wchar
except AttributeError:
    pass
else:
    def setup_module(mod):
        import conftest
        dll = ctypes.CDLL(str(conftest.sofile))
        mod.wcslen = dll.my_wcslen
        mod.wcslen.argtypes = [ctypes.c_wchar_p]
        mod.func = dll._testfunc_p_p

    def teardown_module(mod):
        del mod.func
        del mod.wcslen

    class TestUnicode(BaseCTypesTestChecker):
        def setup_method(self, method):
            self.prev_conv_mode = ctypes.set_conversion_mode("ascii", "strict")

        def teardown_method(self, method):
            ctypes.set_conversion_mode(*self.prev_conv_mode)

        def test_ascii_strict(self):
            ctypes.set_conversion_mode("ascii", "strict")
            # no conversions take place with unicode arguments
            assert wcslen(u"abc") == 3
            assert wcslen(u"ab\u2070") == 3
            # string args are converted
            assert wcslen("abc") == 3
            py.test.raises(ctypes.ArgumentError, wcslen, "ab�")

        def test_ascii_replace(self):
            ctypes.set_conversion_mode("ascii", "replace")
            assert wcslen(u"abc") == 3
            assert wcslen(u"ab\u2070") == 3
            assert wcslen("abc") == 3
            assert wcslen("ab�") == 3

        def test_ascii_ignore(self):
            ctypes.set_conversion_mode("ascii", "ignore")
            assert wcslen(u"abc") == 3
            assert wcslen(u"ab\u2070") == 3
            # ignore error mode skips non-ascii characters
            assert wcslen("abc") == 3
            assert wcslen("����") == 0

        def test_latin1_strict(self):
            ctypes.set_conversion_mode("latin-1", "strict")
            assert wcslen(u"abc") == 3
            assert wcslen(u"ab\u2070") == 3
            assert wcslen("abc") == 3
            assert wcslen("����") == 4

        def test_buffers(self):
            ctypes.set_conversion_mode("ascii", "strict")
            buf = ctypes.create_unicode_buffer("abc")
            assert len(buf) == 3+1

            ctypes.set_conversion_mode("ascii", "replace")
            buf = ctypes.create_unicode_buffer("ab���")
            assert buf[:] == u"ab\uFFFD\uFFFD\uFFFD\0"

            ctypes.set_conversion_mode("ascii", "ignore")
            buf = ctypes.create_unicode_buffer("ab���")
            # is that correct? not sure.  But with 'ignore', you get what you pay for..
            assert buf[:] == u"ab\0\0\0\0"

    class TestString(TestUnicode):
        def setup_method(self, method):
            self.prev_conv_mode = ctypes.set_conversion_mode("ascii", "strict")
            func.argtypes = [ctypes.c_char_p]
            func.restype = ctypes.c_char_p

        def teardown_method(self, method):
            ctypes.set_conversion_mode(*self.prev_conv_mode)
            func.argtypes = None
            func.restype = ctypes.c_int

        def test_ascii_replace(self):
            ctypes.set_conversion_mode("ascii", "strict")
            assert func("abc") == "abc"
            assert func(u"abc") == "abc"
            raises(ctypes.ArgumentError, func, u"ab�")

        def test_ascii_ignore(self):
            ctypes.set_conversion_mode("ascii", "ignore")
            assert func("abc") == "abc"
            assert func(u"abc") == "abc"
            assert func(u"����") == ""

        def test_ascii_replace_2(self):
            ctypes.set_conversion_mode("ascii", "replace")
            assert func("abc") == "abc"
            assert func(u"abc") == "abc"
            assert func(u"����") == "????"

        def test_buffers(self):
            ctypes.set_conversion_mode("ascii", "strict")
            buf = ctypes.create_string_buffer(u"abc")
            assert len(buf) == 3+1

            ctypes.set_conversion_mode("ascii", "replace")
            buf = ctypes.create_string_buffer(u"ab���")
            assert buf[:] == "ab???\0"

            ctypes.set_conversion_mode("ascii", "ignore")
            buf = ctypes.create_string_buffer(u"ab���")
            # is that correct? not sure.  But with 'ignore', you get what you pay for..
            assert buf[:] == "ab\0\0\0\0"

