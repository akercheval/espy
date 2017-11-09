from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib import jit

from pypy.interpreter.baseobjspace import W_Root
from pypy.interpreter.error import OperationError, oefmt
from pypy.interpreter.function import ClassMethod, Method, StaticMethod
from pypy.interpreter.gateway import interp2app
from pypy.interpreter.typedef import (
    GetSetProperty, TypeDef, interp_attrproperty, interp_attrproperty_w)
from pypy.objspace.std.typeobject import W_TypeObject
from pypy.module.cpyext.api import (
    CONST_STRING, METH_CLASS, METH_COEXIST, METH_KEYWORDS, METH_NOARGS, METH_O,
    METH_STATIC, METH_VARARGS, PyObject, bootstrap_function,
    cpython_api, generic_cpy_call, CANNOT_FAIL, slot_function, cts,
    build_type_checkers)
from pypy.module.cpyext.pyobject import (
    Py_DecRef, from_ref, make_ref, as_pyobj, make_typedescr)

PyMethodDef = cts.gettype('PyMethodDef')
PyCFunction = cts.gettype('PyCFunction')
PyCFunctionKwArgs = cts.gettype('PyCFunctionWithKeywords')
PyCFunctionObject = cts.gettype('PyCFunctionObject*')

@bootstrap_function
def init_methodobject(space):
    make_typedescr(W_PyCFunctionObject.typedef,
                   basestruct=PyCFunctionObject.TO,
                   attach=cfunction_attach,
                   dealloc=cfunction_dealloc)

def cfunction_attach(space, py_obj, w_obj, w_userdata=None):
    assert isinstance(w_obj, W_PyCFunctionObject)
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    py_func.c_m_ml = w_obj.ml
    py_func.c_m_self = make_ref(space, w_obj.w_self)
    py_func.c_m_module = make_ref(space, w_obj.w_module)

@slot_function([PyObject], lltype.Void)
def cfunction_dealloc(space, py_obj):
    py_func = rffi.cast(PyCFunctionObject, py_obj)
    Py_DecRef(space, py_func.c_m_self)
    Py_DecRef(space, py_func.c_m_module)
    from pypy.module.cpyext.object import _dealloc
    _dealloc(space, py_obj)

class W_PyCFunctionObject(W_Root):
    # TODO create a slightly different class depending on the c_ml_flags
    def __init__(self, space, ml, w_self, w_module=None):
        self.ml = ml
        self.name = rffi.charp2str(rffi.cast(rffi.CCHARP,self.ml.c_ml_name))
        self.w_self = w_self
        self.w_module = w_module

    def call(self, space, w_self, w_args, w_kw):
        # Call the C function
        if w_self is None:
            w_self = self.w_self
        flags = rffi.cast(lltype.Signed, self.ml.c_ml_flags)
        flags &= ~(METH_CLASS | METH_STATIC | METH_COEXIST)
        if not flags & METH_KEYWORDS and space.is_true(w_kw):
            raise oefmt(space.w_TypeError,
                        "%s() takes no keyword arguments", self.name)

        func = self.ml.c_ml_meth
        length = space.int_w(space.len(w_args))
        if flags & METH_KEYWORDS:
            func = rffi.cast(PyCFunctionKwArgs, self.ml.c_ml_meth)
            return generic_cpy_call(space, func, w_self, w_args, w_kw)
        elif flags & METH_NOARGS:
            if length == 0:
                return generic_cpy_call(space, func, w_self, None)
            raise oefmt(space.w_TypeError,
                        "%s() takes no arguments", self.name)
        elif flags & METH_O:
            if length != 1:
                raise oefmt(space.w_TypeError,
                            "%s() takes exactly one argument (%d given)",
                            self.name, length)
            w_arg = space.getitem(w_args, space.newint(0))
            return generic_cpy_call(space, func, w_self, w_arg)
        elif flags & METH_VARARGS:
            return generic_cpy_call(space, func, w_self, w_args)
        else: # METH_OLDARGS, the really old style
            size = length
            if size == 1:
                w_arg = space.getitem(w_args, space.newint(0))
            elif size == 0:
                w_arg = None
            else:
                w_arg = w_args
            return generic_cpy_call(space, func, w_self, w_arg)

    def get_doc(self, space):
        doc = self.ml.c_ml_doc
        if doc:
            return space.newtext(rffi.charp2str(rffi.cast(rffi.CCHARP,doc)))
        else:
            return space.w_None

class W_PyCFunctionObjectNoArgs(W_PyCFunctionObject):
    def call(self, space, w_self, w_args, w_kw):
        # Call the C function
        if w_self is None:
            w_self = self.w_self
        func = self.ml.c_ml_meth
        return generic_cpy_call(space, func, w_self, None)

class W_PyCFunctionObjectSingleObject(W_PyCFunctionObject):
    def call(self, space, w_self, w_o, w_kw):
        if w_self is None:
            w_self = self.w_self
        func = self.ml.c_ml_meth
        return generic_cpy_call(space, func, w_self, w_o)

class W_PyCMethodObject(W_PyCFunctionObject):
    w_self = None
    def __init__(self, space, ml, w_type):
        self.space = space
        self.ml = ml
        self.name = rffi.charp2str(rffi.cast(rffi.CCHARP, ml.c_ml_name))
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_method_repr(self):
        w_objclass = self.w_objclass
        assert isinstance(w_objclass, W_TypeObject)
        return self.space.newtext("<method '%s' of '%s' objects>" % (
            self.name, w_objclass.name))

    def descr_call(self, space, __args__):
        args_w, kw_w = __args__.unpack()
        if len(args_w) < 1:
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%s' of '%s' object needs an argument",
                self.name, w_objclass.name)
        w_instance = args_w[0]
        # XXX: needs a stricter test
        if not space.isinstance_w(w_instance, self.w_objclass):
            w_objclass = self.w_objclass
            assert isinstance(w_objclass, W_TypeObject)
            raise oefmt(space.w_TypeError,
                "descriptor '%s' requires a '%s' object but received a '%T'",
                self.name, w_objclass.name, w_instance)
        w_args = space.newtuple(args_w[1:])
        w_kw = space.newdict()
        for key, w_obj in kw_w.items():
            space.setitem(w_kw, space.newtext(key), w_obj)
        ret = self.call(space, w_instance, w_args, w_kw)
        return ret

# PyPy addition, for Cython
_, _ = build_type_checkers("MethodDescr", W_PyCMethodObject)


@cpython_api([PyObject], rffi.INT_real, error=CANNOT_FAIL)
def PyCFunction_Check(space, w_obj):
    from pypy.interpreter.function import BuiltinFunction
    if w_obj is None:
        return False
    if isinstance(w_obj, W_PyCFunctionObject):
        return True
    return isinstance(w_obj, BuiltinFunction)

class W_PyCClassMethodObject(W_PyCFunctionObject):
    w_self = None
    def __init__(self, space, ml, w_type):
        self.space = space
        self.ml = ml
        self.name = rffi.charp2str(rffi.cast(rffi.CCHARP, ml.c_ml_name))
        self.w_objclass = w_type

    def __repr__(self):
        return self.space.unwrap(self.descr_method_repr())

    def descr_method_repr(self):
        return self.getrepr(self.space,
                            "built-in method '%s' of '%s' object" %
                            (self.name, self.w_objclass.getname(self.space)))



class W_PyCWrapperObject(W_Root):
    def __init__(self, space, pto, method_name, wrapper_func,
                 wrapper_func_kwds, doc, func, offset=None):
        self.space = space
        self.method_name = method_name
        self.wrapper_func = wrapper_func
        self.wrapper_func_kwds = wrapper_func_kwds
        self.doc = doc
        self.func = func
        self.offset = offset
        pyo = rffi.cast(PyObject, pto)
        w_type = from_ref(space, pyo)
        assert isinstance(w_type, W_TypeObject)
        self.w_objclass = w_type

    def call(self, space, w_self, w_args, w_kw):
        func_to_call = self.func
        if self.offset:
            pto = as_pyobj(space, self.w_objclass)
            # make ptr the equivalent of this, using the offsets
            #func_to_call = rffi.cast(rffi.VOIDP, ptr.c_tp_as_number.c_nb_multiply)
            if pto:
                cptr = rffi.cast(rffi.CCHARP, pto)
                for o in self.offset:
                    ptr = rffi.cast(rffi.VOIDPP, rffi.ptradd(cptr, o))[0]
                    cptr = rffi.cast(rffi.CCHARP, ptr)
                func_to_call = rffi.cast(rffi.VOIDP, cptr)
            else:
                # Should never happen, assert to get a traceback
                assert False, "failed to convert w_type %s to PyObject" % str(
                                                              self.w_objclass)
        assert func_to_call
        if self.wrapper_func is None:
            assert self.wrapper_func_kwds is not None
            return self.wrapper_func_kwds(space, w_self, w_args, func_to_call,
                                          w_kw)
        if space.is_true(w_kw):
            raise oefmt(space.w_TypeError,
                        "wrapper %s doesn't take any keyword arguments",
                        self.method_name)
        return self.wrapper_func(space, w_self, w_args, func_to_call)

    def descr_method_repr(self):
        return self.space.newtext("<slot wrapper '%s' of '%s' objects>" %
                                  (self.method_name,
                                   self.w_objclass.name))

@jit.dont_look_inside
def cwrapper_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCWrapperObject, w_self)
    args_w, kw_w = __args__.unpack()
    w_args = space.newtuple(args_w[1:])
    w_self = args_w[0]
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.newtext(key), w_obj)
    return self.call(space, w_self, w_args, w_kw)

def cfunction_descr_call_noargs(space, w_self):
    # special case for calling with flags METH_NOARGS
    self = space.interp_w(W_PyCFunctionObjectNoArgs, w_self)
    return self.call(space, None, None, None)

def cfunction_descr_call_single_object(space, w_self, w_o):
    # special case for calling with flags METH_O
    self = space.interp_w(W_PyCFunctionObjectSingleObject, w_self)
    return self.call(space, None, w_o, None)

@jit.dont_look_inside
def cfunction_descr_call(space, w_self, __args__):
    # specialize depending on the W_PyCFunctionObject
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    # XXX __args__.unpack is slow
    w_args = space.newtuple(args_w)
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.newtext(key), w_obj)
    ret = self.call(space, None, w_args, w_kw)
    return ret

@jit.dont_look_inside
def cclassmethod_descr_call(space, w_self, __args__):
    self = space.interp_w(W_PyCFunctionObject, w_self)
    args_w, kw_w = __args__.unpack()
    if len(args_w) < 1:
        raise oefmt(space.w_TypeError,
            "descriptor '%s' of '%s' object needs an argument",
            self.name, self.w_objclass.getname(space))
    w_instance = args_w[0] # XXX typecheck missing
    w_args = space.newtuple(args_w[1:])
    w_kw = space.newdict()
    for key, w_obj in kw_w.items():
        space.setitem(w_kw, space.newtext(key), w_obj)
    ret = self.call(space, w_instance, w_args, w_kw)
    return ret

def cmethod_descr_get(space, w_function, w_obj, w_cls=None):
    asking_for_bound = (space.is_none(w_cls) or
                        not space.is_w(w_obj, space.w_None) or
                        space.is_w(w_cls, space.type(space.w_None)))
    if asking_for_bound:
        return Method(space, w_function, w_obj, w_cls)
    else:
        return w_function

def cclassmethod_descr_get(space, w_function, w_obj, w_cls=None):
    if not w_cls:
        w_cls = space.type(w_obj)
    return Method(space, w_function, w_cls, space.w_None)


W_PyCFunctionObject.typedef = TypeDef(
    'builtin_function_or_method',
    __call__ = interp2app(cfunction_descr_call),
    __doc__ = GetSetProperty(W_PyCFunctionObject.get_doc),
    __module__ = interp_attrproperty_w('w_module', cls=W_PyCFunctionObject),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObject,
        wrapfn="newtext_or_none"),
    )
W_PyCFunctionObject.typedef.acceptable_as_base_class = False

W_PyCFunctionObjectNoArgs.typedef = TypeDef(
    'builtin_function_or_method', W_PyCFunctionObject.typedef,
    __call__ = interp2app(cfunction_descr_call_noargs),
    __doc__ = GetSetProperty(W_PyCFunctionObjectNoArgs.get_doc),
    __module__ = interp_attrproperty_w('w_module', cls=W_PyCFunctionObjectNoArgs),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObjectNoArgs,
        wrapfn="newtext_or_none"),
    )
W_PyCFunctionObjectNoArgs.typedef.acceptable_as_base_class = False

W_PyCFunctionObjectSingleObject.typedef = TypeDef(
    'builtin_function_or_method', W_PyCFunctionObject.typedef,
    __call__ = interp2app(cfunction_descr_call_single_object),
    __doc__ = GetSetProperty(W_PyCFunctionObjectSingleObject.get_doc),
    __module__ = interp_attrproperty_w('w_module', cls=W_PyCFunctionObjectSingleObject),
    __name__ = interp_attrproperty('name', cls=W_PyCFunctionObjectSingleObject,
        wrapfn="newtext_or_none"),
    )
W_PyCFunctionObjectSingleObject.typedef.acceptable_as_base_class = False

W_PyCMethodObject.typedef = TypeDef(
    'method_descriptor',
    __get__ = interp2app(cmethod_descr_get),
    __call__ = interp2app(W_PyCMethodObject.descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCMethodObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCMethodObject),
    __repr__ = interp2app(W_PyCMethodObject.descr_method_repr),
    )
W_PyCMethodObject.typedef.acceptable_as_base_class = False

W_PyCClassMethodObject.typedef = TypeDef(
    'classmethod',
    __get__ = interp2app(cclassmethod_descr_get),
    __call__ = interp2app(cclassmethod_descr_call),
    __name__ = interp_attrproperty('name', cls=W_PyCClassMethodObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass',
                                         cls=W_PyCClassMethodObject),
    __repr__ = interp2app(W_PyCClassMethodObject.descr_method_repr),
    )
W_PyCClassMethodObject.typedef.acceptable_as_base_class = False


W_PyCWrapperObject.typedef = TypeDef(
    'wrapper_descriptor',
    __call__ = interp2app(cwrapper_descr_call),
    __get__ = interp2app(cmethod_descr_get),
    __name__ = interp_attrproperty('method_name', cls=W_PyCWrapperObject,
        wrapfn="newtext_or_none"),
    __doc__ = interp_attrproperty('doc', cls=W_PyCWrapperObject,
        wrapfn="newtext_or_none"),
    __objclass__ = interp_attrproperty_w('w_objclass', cls=W_PyCWrapperObject),
    __repr__ = interp2app(W_PyCWrapperObject.descr_method_repr),
    # XXX missing: __getattribute__
    )
W_PyCWrapperObject.typedef.acceptable_as_base_class = False


@cpython_api([lltype.Ptr(PyMethodDef), PyObject, PyObject], PyObject)
def PyCFunction_NewEx(space, ml, w_self, w_name):
    return W_PyCFunctionObject(space, ml, w_self, w_name)

@cts.decl("PyCFunction PyCFunction_GetFunction(PyObject *)")
def PyCFunction_GetFunction(space, w_obj):
    try:
        cfunction = space.interp_w(W_PyCFunctionObject, w_obj)
    except OperationError as e:
        if e.match(space, space.w_TypeError):
            raise oefmt(space.w_SystemError,
                        "bad argument to internal function")
        raise
    return cfunction.ml.c_ml_meth

@cpython_api([PyObject], PyObject)
def PyStaticMethod_New(space, w_func):
    return StaticMethod(w_func)

@cpython_api([PyObject], PyObject)
def PyClassMethod_New(space, w_func):
    return ClassMethod(w_func)

@cts.decl("""
    PyObject *
    PyDescr_NewClassMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewMethod(space, w_type, method):
    return W_PyCMethodObject(space, method, w_type)

@cts.decl("""
    PyObject *
    PyDescr_NewClassMethod(PyTypeObject *type, PyMethodDef *method)""")
def PyDescr_NewClassMethod(space, w_type, method):
    return W_PyCClassMethodObject(space, method, w_type)

@cpython_api([lltype.Ptr(PyMethodDef), PyObject, CONST_STRING], PyObject)
def Py_FindMethod(space, table, w_obj, name_ptr):
    """Return a bound method object for an extension type implemented in
    C.  This can be useful in the implementation of a tp_getattro or
    tp_getattr handler that does not use the PyObject_GenericGetAttr()
    function.
    """
    # XXX handle __doc__

    name = rffi.charp2str(name_ptr)
    methods = rffi.cast(rffi.CArrayPtr(PyMethodDef), table)
    method_list_w = []

    if methods:
        i = -1
        while True:
            i = i + 1
            method = methods[i]
            if not method.c_ml_name:
                break
            if name == "__methods__":
                method_list_w.append(
                    space.newtext(rffi.charp2str(rffi.cast(rffi.CCHARP, method.c_ml_name))))
            elif rffi.charp2str(rffi.cast(rffi.CCHARP, method.c_ml_name)) == name: # XXX expensive copy
                return W_PyCFunctionObject(space, method, w_obj)
    if name == "__methods__":
        return space.newlist(method_list_w)
    raise OperationError(space.w_AttributeError, space.newtext(name))
