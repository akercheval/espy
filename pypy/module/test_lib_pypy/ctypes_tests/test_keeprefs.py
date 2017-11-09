import py
from ctypes import *

class TestSimple:
    def test_cint(self):
        x = c_int()
        assert x._objects == None
        x.value = 42
        assert x._objects == None
        x = c_int(99)
        assert x._objects == None

    def test_ccharp(self):
        py.test.skip("we make copies of strings")
        x = c_char_p()
        assert x._objects == None
        x.value = "abc"
        assert x._objects == "abc"
        x = c_char_p("spam")
        assert x._objects == "spam"

class TestStructure:
    def test_cint_struct(self):
        class X(Structure):
            _fields_ = [("a", c_int),
                        ("b", c_int)]

        x = X()
        assert x._objects == None
        x.a = 42
        x.b = 99
        assert x._objects == None

    def test_ccharp_struct(self):
        py.test.skip("we make copies of strings")        
        class X(Structure):
            _fields_ = [("a", c_char_p),
                        ("b", c_char_p)]
        x = X()
        assert x._objects == None

        x.a = "spam"
        x.b = "foo"
        assert x._objects == {"0": "spam", "1": "foo"}

    def test_struct_struct(self):
        class POINT(Structure):
            _fields_ = [("x", c_int), ("y", c_int)]
        class RECT(Structure):
            _fields_ = [("ul", POINT), ("lr", POINT)]

        r = RECT()
        r.ul.x = 0
        r.ul.y = 1
        r.lr.x = 2
        r.lr.y = 3
        assert r._objects == None

        r = RECT()
        pt = POINT(1, 2)
        r.ul = pt
        assert r._objects == {'0': {}}
        r.ul.x = 22
        r.ul.y = 44
        assert r._objects == {'0': {}}
        r.lr = POINT()
        assert r._objects == {'0': {}, '1': {}}

class TestArray:
    def test_cint_array(self):
        INTARR = c_int * 3

        ia = INTARR()
        assert ia._objects == None
        ia[0] = 1
        ia[1] = 2
        ia[2] = 3
        assert ia._objects == None

        class X(Structure):
            _fields_ = [("x", c_int),
                        ("a", INTARR)]

        x = X()
        x.x = 1000
        x.a[0] = 42
        x.a[1] = 96
        assert x._objects == None
        x.a = ia
        assert x._objects == {'1': {}}

class TestPointer:
    def test_p_cint(self):
        i = c_int(42)
        x = pointer(i)
        assert x._objects == {'1': i}

class TestDeletePointer:
    def X_test(self):
        class X(Structure):
            _fields_ = [("p", POINTER(c_char_p))]
        x = X()
        i = c_char_p("abc def")
        from sys import getrefcount as grc
        print "2?", grc(i)
        x.p = pointer(i)
        print "3?", grc(i)
        for i in range(320):
            c_int(99)
            x.p[0]
        print x.p[0]
##        del x
##        print "2?", grc(i)
##        del i
        import gc
        gc.collect()
        for i in range(320):
            c_int(99)
            x.p[0]
        print x.p[0]
        print x.p.contents
##        print x._objects

        x.p[0] = "spam spam"
##        print x.p[0]
        print "+" * 42
        print x._objects

class TestPointerToStructure:
    def test(self):
        class POINT(Structure):
            _fields_ = [("x", c_int), ("y", c_int)]
        class RECT(Structure):
            _fields_ = [("a", POINTER(POINT)),
                        ("b", POINTER(POINT))]
        r = RECT()
        p1 = POINT(1, 2)

        r.a = pointer(p1)
        r.b = pointer(p1)
##        from pprint import pprint as pp
##        pp(p1._objects)
##        pp(r._objects)

        r.a[0].x = 42
        r.a[0].y = 99

        # to avoid leaking when tests are run several times
        # clean up the types left in the cache.
        from ctypes import _pointer_type_cache
        del _pointer_type_cache[POINT]
