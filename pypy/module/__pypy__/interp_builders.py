from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import oefmt
from pypy.interpreter.gateway import interp2app, unwrap_spec
from pypy.interpreter.typedef import TypeDef
from rpython.rlib.rstring import UnicodeBuilder, StringBuilder
from rpython.tool.sourcetools import func_with_new_name


def create_builder(name, strtype, builder_cls, newmethod):
    if strtype is str:
        unwrap = 'bytes'
    else:
        unwrap = unicode
    class W_Builder(W_Root):
        def __init__(self, space, size):
            if size < 0:
                self.builder = builder_cls()
            else:
                self.builder = builder_cls(size)

        @unwrap_spec(size=int)
        def descr__new__(space, w_subtype, size=-1):
            return W_Builder(space, size)

        @unwrap_spec(s=unwrap)
        def descr_append(self, space, s):
            self.builder.append(s)

        @unwrap_spec(s=unwrap, start=int, end=int)
        def descr_append_slice(self, space, s, start, end):
            if not 0 <= start <= end <= len(s):
                raise oefmt(space.w_ValueError, "bad start/stop")
            self.builder.append_slice(s, start, end)

        def descr_build(self, space):
            w_s = getattr(space, newmethod)(self.builder.build())
            # after build(), we can continue to append more strings
            # to the same builder.  This is supported since
            # 2ff5087aca28 in RPython.
            return w_s

        def descr_len(self, space):
            if self.builder is None:
                raise oefmt(space.w_ValueError, "no length of built builder")
            return space.newint(self.builder.getlength())

    W_Builder.__name__ = "W_%s" % name
    W_Builder.typedef = TypeDef(name,
        __new__ = interp2app(func_with_new_name(
                                    W_Builder.descr__new__.im_func,
                                    '%s_new' % (name,))),
        append = interp2app(W_Builder.descr_append),
        append_slice = interp2app(W_Builder.descr_append_slice),
        build = interp2app(W_Builder.descr_build),
        __len__ = interp2app(W_Builder.descr_len),
    )
    W_Builder.typedef.acceptable_as_base_class = False
    return W_Builder

W_StringBuilder = create_builder("StringBuilder", str, StringBuilder, "newbytes")
W_UnicodeBuilder = create_builder("UnicodeBuilder", unicode, UnicodeBuilder, "newunicode")
