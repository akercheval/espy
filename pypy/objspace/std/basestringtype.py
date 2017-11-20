from pypy.interpreter.typedef import TypeDef


basestring_typedef = TypeDef("basestring",
    __doc__ =  ("basepalabra no se puede instanciar; "
                "es el base para pal y unicod.")
    )
