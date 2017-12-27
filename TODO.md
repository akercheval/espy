## TODO

* Change python's internal reference to a class without breaking everything 
    (i.e. alias "lista" to "list"). Changing "list" to "lista" in listobject.py
    really messes things up, but it means that when espy is running, the command
    `type([])` returns "list", not "lista". 
* Don't break the help() function: for example, help(list) makes no sense in 
    espy. I think that this is because I put the Spanish references to functions
    below their English counterparts in W_ListObject.typedef, but I'm not sure.
* Add new builtin functions every time espy runs. There could be some sort of 
    [global somewhere]("https://stackoverflow.com/questions/29798592/overwriting-built-in-function-in-python"),
    but I'm not sure how that would work or where it would be go. Alternately, 
    this codeblock shows how to overwrite some builtins, but I'm not sure how 
    temporary it is (and also it doesn't seem to work with print()):
    ```
        >>>> import __builtin__ as builtin
        >>>> builtin.tam = builtin.len
        >>>> tam([1, 2, 3])
        3
    ```
* Allow for accents in type definitions: Right now, for example, the "index" 
    function of the list type, which should be called "índice" is called
    "indice" because the pypy compiler freaks out when it finds an accent.
* There are some files and things I've skipped:
..* `pypy/objspace/std/dictproxyobject.py` - I've never heard of this and don't 
        know what it does
..* There's an XXX in dictmultiobject `_add_indirections` function where
        internal function names are created as raw strings. I didn't change it
        because I'm not entirely sure whether it's necessary to, but it might be.
..* `kwargsdict.py` hasn't been changed - again, not sure what it does and it's 
        not at all the same format as the other files in the `/std/` directory


#### Builtins and their functionality:

English         Spanish         Working?
----------------------------------------
abs()           abs()           Yes
all()           todo()          Yes
any()           cualq()         Yes
ascii()         ascii()         Not defined even in normal pypy
bin()           bin()           Yes
bool()          bool()	        Yes
bytearray()     bytematriz()    **No**
bytes()         bytes()	        Yes
callable()      llamable()      Yes
chr()	        carac()         Yes
classmethod()   metclase()      Yes
compile()       compilar()      Yes
complex()                       *not found yet*
delattr()       elimatr()       Yes
dict()          dicc()          **No**
dir()           dir()           Yes
divmod()        divmod()        Yes
enumerate()     enumerar()      Yes
eval()          eval()          Yes
exec()          ejec()          **No**
filter()        filtrar()       Yes
float()         flot()          **No**
format()        formato()       Yes
frozenset()                     *not found yet*
getattr()       sacaatr()       Yes
globals()       globales()      Yes
hasattr()       tieneatr()      Yes
hash()          hash()          Yes
help()                          *not found yet*
hex()           hex()           Yes
id()            id()            Yes
input()         entrada()       Yes
int()           ent()           **No**
isinstance()    esinstancia()   Yes
issubclass()    essubclase()    Yes
len()           tam()           Yes
list()          lista()         **No**
locals()        locales()       Yes
map()           mapa()          Yes
max()           max()           Yes
memoryview()                     *not found yet*
min()           min()           Yes
next()          sig()           Yes
object()        objeto()        **No**
oct()           oct()           Yes
open()          abrir()         Yes
ord()           ord()           Yes
pow()           pot()           Yes
print()         imprimir()      Yes
property()      propiedad()     Yes
range()         rango()         Yes
repr()          repr()          Yes
reversed()      invertido()     Yes
round()         redond()        Yes
set()           set()           Yes (but only because name is same)
setattr()       ponatr()        Yes
slice()         cortar()        **No**
sorted()        ordenado()      Yes
staticmethod()  metestat()      Yes
str()           pal()           **No**
sum()           suma()          Yes
super()         padre()         Yes
tuple()         tuple()         Yes (but only because name is same)
type()          tipo()          **No**
vars()          vars()          Yes
zip()           zip()           Yes
__import__()    __importar__()  Yes (but 'importar' doesn't)

#### Etc (unless noted otherwise, not found yet)
These are probably located in pypy/interpreter

English         Spanish         Working?
----------------------------------------
True            Cierto          Yes
False           Falso           Yes
None            Nada            Yes
if              si              
else            si_no 
elif            sino
not             no
in              en
pass            pasa
continue        continuar
break           romper
class           clase
def             def
for             para
while           mientras
do              hacer
return          volver
try             probar
except          excepto
self            mismo
and             y
or              o

