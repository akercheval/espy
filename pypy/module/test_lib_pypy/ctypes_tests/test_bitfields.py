import py
from ctypes import *
from support import BaseCTypesTestChecker
import os

import ctypes

signed_int_types = (c_byte, c_short, c_int, c_long, c_longlong)
unsigned_int_types = (c_ubyte, c_ushort, c_uint, c_ulong, c_ulonglong)
int_types = unsigned_int_types + signed_int_types


def setup_module(mod):
    import conftest
    _ctypes_test = str(conftest.sofile)
    func = CDLL(_ctypes_test).unpack_bitfields
    func.argtypes = POINTER(BITS), c_char
    mod.func = func


class BITS(Structure):
    _fields_ = [("A", c_int, 1),
                ("B", c_int, 2),
                ("C", c_int, 3),
                ("D", c_int, 4),
                ("E", c_int, 5),
                ("F", c_int, 6),
                ("G", c_int, 7),
                ("H", c_int, 8),
                ("I", c_int, 9),

                ("M", c_short, 1),
                ("N", c_short, 2),
                ("O", c_short, 3),
                ("P", c_short, 4),
                ("Q", c_short, 5),
                ("R", c_short, 6),
                ("S", c_short, 7)]


class TestC:
    def test_ints(self):
        for i in range(512):
            for name in "ABCDEFGHI":
                b = BITS()
                setattr(b, name, i)
                assert (name, i, getattr(b, name)) == (name, i, func(byref(b), name))

    def test_shorts(self):
        for i in range(256):
            for name in "MNOPQRS":
                b = BITS()
                setattr(b, name, i)
                assert (name, i, getattr(b, name)) == (name, i, func(byref(b), name))


class TestBitField:
    def test_longlong(self):
        class X(Structure):
            _fields_ = [("a", c_longlong, 1),
                        ("b", c_longlong, 62),
                        ("c", c_longlong, 1)]

        assert sizeof(X) == sizeof(c_longlong)
        x = X()
        x.a, x.b, x.c = -1, 7, -1
        assert (x.a, x.b, x.c) == (-1, 7, -1)

        x = X()
        x.a, x.b, x.c = -1, -7, -1
        assert (x.a, x.b, x.c) == (-1, -7, -1)

    def test_ulonglong(self):
        class X(Structure):
            _fields_ = [("a", c_ulonglong, 1),
                        ("b", c_ulonglong, 62),
                        ("c", c_ulonglong, 1)]

        assert sizeof(X) == sizeof(c_longlong)
        x = X()
        assert (x.a, x.b, x.c) == (0, 0, 0)
        x.a, x.b, x.c = 7, 2305843009213693953, 7
        assert (x.a, x.b, x.c) == (1, 2305843009213693953, 1)

    def test_signed(self):
        for c_typ in signed_int_types:
            class X(Structure):
                _fields_ = [("dummy", c_typ),
                            ("a", c_typ, 3),
                            ("b", c_typ, 3),
                            ("c", c_typ, 1)]
            assert sizeof(X) == sizeof(c_typ)*2

            x = X()
            assert (c_typ, x.a, x.b, x.c) == (c_typ, 0, 0, 0)
            x.a = -1
            assert (c_typ, x.a, x.b, x.c) == (c_typ, -1, 0, 0)
            x.a, x.b = 0, -1
            assert (c_typ, x.a, x.b, x.c) == (c_typ, 0, -1, 0)

    def test_unsigned(self):
        for c_typ in unsigned_int_types:
            class X(Structure):
                _fields_ = [("a", c_typ, 3),
                            ("b", c_typ, 3),
                            ("c", c_typ, 1)]
            assert sizeof(X) == sizeof(c_typ)

            x = X()
            assert (c_typ, x.a, x.b, x.c) == (c_typ, 0, 0, 0)
            x.a = -1
            assert (c_typ, x.a, x.b, x.c) == (c_typ, 7, 0, 0)
            x.a, x.b = 0, -1
            assert (c_typ, x.a, x.b, x.c) == (c_typ, 0, 7, 0)

    def fail_fields(self, *fields):
        return self.get_except(type(Structure), "X", (),
                               {"_fields_": fields})

    def test_nonint_types(self):
        # bit fields are not allowed on non-integer types.
        result = self.fail_fields(("a", c_char_p, 1))
        assert result == (TypeError, 'bit fields not allowed for type c_char_p')

        result = self.fail_fields(("a", c_void_p, 1))
        assert result == (TypeError, 'bit fields not allowed for type c_void_p')

        if c_int != c_long:
            result = self.fail_fields(("a", POINTER(c_int), 1))
            assert result == (TypeError, 'bit fields not allowed for type LP_c_int')

        result = self.fail_fields(("a", c_char, 1))
        assert result == (TypeError, 'bit fields not allowed for type c_char')

        try:
            c_wchar
        except NameError:
            pass
        else:
            result = self.fail_fields(("a", c_wchar, 1))
            assert result == (TypeError, 'bit fields not allowed for type c_wchar')

        class Dummy(Structure):
            _fields_ = []

        result = self.fail_fields(("a", Dummy, 1))
        assert result == (TypeError, 'bit fields not allowed for type Dummy')

    def test_single_bitfield_size(self):
        for c_typ in int_types:
            result = self.fail_fields(("a", c_typ, -1))
            assert result == (ValueError, 'number of bits invalid for bit field')

            result = self.fail_fields(("a", c_typ, 0))
            assert result == (ValueError, 'number of bits invalid for bit field')

            class X(Structure):
                _fields_ = [("a", c_typ, 1)]
            assert sizeof(X) == sizeof(c_typ)

            class X(Structure):
                _fields_ = [("a", c_typ, sizeof(c_typ)*8)]
            assert sizeof(X) == sizeof(c_typ)

            result = self.fail_fields(("a", c_typ, sizeof(c_typ)*8 + 1))
            assert result == (ValueError, 'number of bits invalid for bit field')

    def test_multi_bitfields_size(self):
        class X(Structure):
            _fields_ = [("a", c_short, 1),
                        ("b", c_short, 14),
                        ("c", c_short, 1)]
        assert sizeof(X) == sizeof(c_short)

        class X(Structure):
            _fields_ = [("a", c_short, 1),
                        ("a1", c_short),
                        ("b", c_short, 14),
                        ("c", c_short, 1)]
        assert sizeof(X) == sizeof(c_short)*3
        assert X.a.offset == 0
        assert X.a1.offset == sizeof(c_short)
        assert X.b.offset == sizeof(c_short)*2
        assert X.c.offset == sizeof(c_short)*2

        class X(Structure):
            _fields_ = [("a", c_short, 3),
                        ("b", c_short, 14),
                        ("c", c_short, 14)]
        assert sizeof(X) == sizeof(c_short)*3
        assert X.a.offset == sizeof(c_short)*0
        assert X.b.offset == sizeof(c_short)*1
        assert X.c.offset == sizeof(c_short)*2

    def get_except(self, func, *args, **kw):
        try:
            func(*args, **kw)
        except Exception as detail:
            import traceback
            traceback.print_exc()
            return detail.__class__, str(detail)

    def test_mixed_1(self):
        class X(Structure):
            _fields_ = [("a", c_byte, 4),
                        ("b", c_int, 4)]
        if os.name in ("nt", "ce"):
            assert sizeof(X) == sizeof(c_int)*2
        else:
            assert sizeof(X) == sizeof(c_int)

    def test_mixed_2(self):
        class X(Structure):
            _fields_ = [("a", c_byte, 4),
                        ("b", c_int, 32)]
        assert sizeof(X) == sizeof(c_int)*2

    def test_mixed_3(self):
        class X(Structure):
            _fields_ = [("a", c_byte, 4),
                        ("b", c_ubyte, 4)]
        assert sizeof(X) == sizeof(c_byte)

    def test_anon_bitfields(self):
        # anonymous bit-fields gave a strange error message
        class X(Structure):
            _fields_ = [("a", c_byte, 4),
                        ("b", c_ubyte, 4)]
        class Y(Structure):
            _anonymous_ = ["_"]
            _fields_ = [("_", X)]

    def test_set_fields_attr(self):
        class A(Structure):
            pass
        A._fields_ = [("a", c_byte),
                      ("b", c_ubyte)]

    def test_set_fields_attr_bitfields(self):
        class A(Structure):
            pass
        A._fields_ = [("a", POINTER(A)),
                      ("b", c_ubyte, 4)]

    def test_set_fields_cycle_fails(self):
        class A(Structure):
            pass
        import pytest
        pytest.raises(AttributeError, """
            A._fields_ = [("a", A)]
                      """)
