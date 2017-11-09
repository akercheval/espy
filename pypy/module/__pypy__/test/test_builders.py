class AppTestBuilders(object):
    spaceconfig = dict(usemodules=['__pypy__'])

    def test_simple(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder()
        b.append(u"abc")
        b.append(u"123")
        b.append(u"1")
        s = b.build()
        assert s == u"abc1231"
        assert b.build() == s
        b.append(u"123")
        assert b.build() == s + u"123"

    def test_preallocate(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder(10)
        b.append(u"abc")
        b.append(u"123")
        s = b.build()
        assert s == u"abc123"

    def test_append_slice(self):
        from __pypy__.builders import UnicodeBuilder
        b = UnicodeBuilder()
        b.append_slice(u"abcdefgh", 2, 5)
        raises(ValueError, b.append_slice, u"1", 2, 1)
        s = b.build()
        assert s == u"cde"
        b.append_slice(u"abc", 1, 2)
        assert b.build() == u"cdeb"

    def test_stringbuilder(self):
        from __pypy__.builders import StringBuilder
        b = StringBuilder()
        b.append("abc")
        b.append("123")
        assert len(b) == 6
        b.append("you and me")
        s = b.build()
        assert len(b) == 16
        assert s == "abc123you and me"
        assert b.build() == s
