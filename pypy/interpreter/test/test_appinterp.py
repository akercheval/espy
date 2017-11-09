
import py
from pypy.interpreter.gateway import appdef, ApplevelClass, applevel_temp
from pypy.interpreter.error import OperationError

def test_execwith_novars(space): 
    val = space.appexec([], """ 
    (): 
        return 42 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_withvars(space): 
    val = space.appexec([space.wrap(7)], """
    (x): 
        y = 6 * x 
        return y 
    """) 
    assert space.eq_w(val, space.wrap(42))

def test_execwith_compile_error(space): 
    excinfo = py.test.raises(OperationError, space.appexec, [], """
    (): 
        y y 
    """)
    # NOTE: the following test only works because excinfo.value is not
    # normalized so far
    assert str(excinfo.value.get_w_value(space)).find('y y') != -1 

def test_simple_applevel(space):
    app = appdef("""app(x,y): 
        return x + y
    """)
    assert app.func_name == 'app'
    w_result = app(space, space.wrap(41), space.wrap(1))
    assert space.eq_w(w_result, space.wrap(42))

def test_applevel_with_one_default(space):
    app = appdef("""app(x,y=1): 
        return x + y
    """)
    assert app.func_name == 'app'
    w_result = app(space, space.wrap(41)) 
    assert space.eq_w(w_result, space.wrap(42))

def test_applevel_with_two_defaults(space):
    app = appdef("""app(x=1,y=2): 
        return x + y
    """)
    w_result = app(space, space.wrap(41), space.wrap(1))
    assert space.eq_w(w_result, space.wrap(42))

    w_result = app(space, space.wrap(15))
    assert space.eq_w(w_result, space.wrap(17))

    w_result = app(space)
    assert space.eq_w(w_result, space.wrap(3))


def test_applevel_noargs(space):
    app = appdef("""app(): 
        return 42 
    """)
    assert app.func_name == 'app'
    w_result = app(space) 
    assert space.eq_w(w_result, space.wrap(42))

def somefunc(arg2=42): 
    return arg2 

def test_app2interp_somefunc(space): 
    app = appdef(somefunc) 
    w_result = app(space) 
    assert space.eq_w(w_result, space.wrap(42))

def test_applevel_functions(space, applevel_temp = applevel_temp):
    app = applevel_temp('''
        def f(x, y):
            return x-y
        def g(x, y):
            return f(y, x)
    ''')
    g = app.interphook('g')
    w_res = g(space, space.wrap(10), space.wrap(1))
    assert space.eq_w(w_res, space.wrap(-9))

def test_applevel_class(space, applevel_temp = applevel_temp):
    app = applevel_temp('''
        class C(object):
            clsattr = 42 
            def __init__(self, x=13): 
                self.attr = x 
    ''')
    C = app.interphook('C')
    c = C(space, space.wrap(17)) 
    w_attr = space.getattr(c, space.wrap('clsattr'))
    assert space.eq_w(w_attr, space.wrap(42))
    w_clsattr = space.getattr(c, space.wrap('attr'))
    assert space.eq_w(w_clsattr, space.wrap(17))

def app_test_something_at_app_level(): 
    x = 2
    assert x/2 == 1

class AppTestMethods: 
    def test_some_app_test_method(self): 
        assert 2 == 2

class TestMixedModule: 
    def test_accesses(self): 
        space = self.space
        import demomixedmod 
        w_module = demomixedmod.Module(space, space.wrap('mixedmodule'))
        space.appexec([w_module], """
            (module): 
                assert module.value is None 
                assert module.__doc__ == 'mixedmodule doc'

                assert module.somefunc is module.somefunc 
                result = module.somefunc() 
                assert result == True 

                assert module.someappfunc is module.someappfunc 
                appresult = module.someappfunc(41) 
                assert appresult == 42 

                assert module.__dict__ is module.__dict__
                for name in ('somefunc', 'someappfunc', '__doc__', '__name__'): 
                    assert name in module.__dict__
        """)
        assert space.is_true(w_module.call('somefunc'))

    def test_whacking_at_loaders(self):
        """Some MixedModules change 'self.loaders' in __init__(), but doing
        so they incorrectly mutated a class attribute.  'loaders' is now a
        per-instance attribute, holding a fresh copy of the dictionary.
        """
        from pypy.interpreter.mixedmodule import MixedModule
        from pypy.tool.pytest.objspace import maketestobjspace

        class MyModule(MixedModule):
            interpleveldefs = {}
            appleveldefs = {}
            def __init__(self, space, w_name):
                def loader(myspace):
                    assert myspace is space
                    return myspace.wrap("hello")
                MixedModule.__init__(self, space, w_name)
                self.loaders["hi"] = loader

        space1 = self.space
        w_mymod1 = MyModule(space1, space1.wrap('mymod'))

        space2 = maketestobjspace()
        w_mymod2 = MyModule(space2, space2.wrap('mymod'))

        w_str = space1.getattr(w_mymod1, space1.wrap("hi"))
        assert space1.str_w(w_str) == "hello"

class TestMixedModuleUnfreeze:
    spaceconfig = dict(usemodules=('_ssl', '_socket'))

    def test_random_stuff_can_unfreeze(self):
        # When a module contains an "import" statement in applevel code, the
        # imported module is initialized, possibly after it has been already
        # frozen.

        # This is important when the module startup() function does something
        # at runtime, like setting os.environ (posix module) or initializing
        # the winsock library (_socket module)
        w_socket = self.space.builtin_modules['_socket']
        w_ssl = self.space.builtin_modules['_ssl']

        # Uncomment this line for a workaround
        # space.getattr(w_ssl, space.wrap('SSLError'))

        w_socket._cleanup_()
        assert w_socket.startup_called == False
        w_ssl._cleanup_() # w_ssl.appleveldefs['SSLError'] imports _socket
        assert w_socket.startup_called == False

