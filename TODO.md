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
abs()           abs()
all()           todo()
any()           cualq()
ascii()         ascii()
bin()           bin()
bool()          bool()	
bytearray()     bytematriz()
bytes()         bytes()	
callable()      llamable()
chr()	        carac()
classmethod()   metclase()
compile()       compilar()
complex()                       *not found yet*
delattr()       elimatr()
dict()          dicc()
dir()           dir()
divmod()        divmod()
enumerate()     enumerar()
eval()          eval()
exec()          ejec()
filter()        filtrar()
float()         flot() 
format()        formato()
frozenset()                     *not found yet*
getattr()       sacaatr()
globals()       globales()
hasattr()       tieneatr()
hash()          hash()
help()                          *not found yet*
hex()           hex()
id()            id()
input()         entrada()
int()           ent()
isinstance()    esinstancia()
issubclass()    essubclase()
print()         imprimir()
len()           tam()
list()          lista()
locals()        locales()
map()           mapa()
max()           max()
memoryview()                     *not found yet*
min()           min()
next()          sig()
object()        objeto()
oct()           oct()
open()          abrir()
ord()           ord()
pow()           pot()
print()         imprimir()
property()      propiedad()
range()         rango()
repr()          repr()
reversed()      invertido()
round()         redond()
set()           set()
setattr()       ponatr()
slice()         cortar()
sorted()        ordenado()
staticmethod()  metestat()
str()           pal()
sum()           suma()
super()         padre()
tuple()         tuple()
type()          tipo()
vars()          vars()
zip()           zip()
__import__()    __importar__()


#### Etc (unless noted otherwise, not found yet)

English         Spanish         Working?
----------------------------------------
True            Cierto          Yes
False           Falso           Yes
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
