## TODO

* Don't break the help() function. It doesn't work right now, and it's not 
  totally clear why.

* Allow for accents in type definitions: Right now, for example, the "index" 
    function of the list type, which should be called "índice" is called
    "indice" because the pypy compiler freaks out when it finds an accent.
* There are some files and things I've skipped:
  * `pypy/objspace/std/dictproxyobject.py` - I've never heard of this and don't 
        know what it does
  * There's an XXX in dictmultiobject `_add_indirections` function where
        internal function names are created as raw strings. I didn't change it
        because I'm not entirely sure whether it's necessary to, but it might be.
  * `kwargsdict.py` hasn't been changed - again, not sure what it does and it's 
        not at all the same format as the other files in the `/std/` directory


#### Builtins and their functionality:

| English       |  Spanish       |  Working?
| --------------|----------------|----------
| abs()         |  abs()         |  Yes
| all()         |  todo()        |  Yes
| any()         |  cualq()       |  Yes
| ascii()       |  ascii()       |  Not defined even in normal pypy
| bin()         |  bin()         |  Yes
| bool()        |  bool()	     |  Yes
| bytearray()   |  bytematriz()  |  Yes but (1, 2)
| bytes()       |  bytes()	     |  Yes
| callable()    |  llamable()    |  Yes
| chr()	        |  carac()       |  Yes
| classmethod() |  metclase()    |  Yes
| compile()     |  compilar()    |  Yes
| complex()     |  complejo()    |  Yes but (1)
| delattr()     |  elimatr()     |  Yes
| dict()        |  dicc()        |  Yes
| dir()         |  dir()         |  Yes
| divmod()      |  divmod()      |  Yes
| enumerate()   |  enumerar()    |  Yes
| eval()        |  eval()        |  Yes
| exec()        |  ejec()        |  **No**, but probably won't include
| filter()      |  filtrar()     |  Yes
| float()       |  flot()        |  Yes
| format()      |  formato()     |  Yes
| frozenset()   |                |  *not found yet*
| getattr()     |  sacaatr()     |  Yes
| globals()     |  globales()    |  Yes
| hasattr()     |  tieneatr()    |  Yes
| hash()        |  hash()        |  Yes
| hex()         |  hex()         |  Yes
| id()          |  id()          |  Yes
| input()       |  entrada()     |  Yes
| int()         |  ent()         |  Yes
| isinstance()  |  esinstancia() |  Yes
| issubclass()  |  essubclase()  |  Yes
| len()         |  tam()         |  Yes
| list()        |  lista()       |  Yes
| locals()      |  locales()     |  Yes
| map()         |  mapa()        |  Yes
| max()         |  max()         |  Yes
| memoryview()  |                |   *not found yet*
| min()         |  min()         |  Yes
| next()        |  sig()         |  Yes
| object()      |  objeto()      |  Yes
| oct()         |  oct()         |  Yes
| open()        |  abrir()       |  Yes
| ord()         |  ord()         |  Yes
| pow()         |  pot()         |  Yes
| print()       |  imprimir()    |  Yes
| property()    |  propiedad()   |  Yes
| range()       |  rango()       |  Yes
| repr()        |  repr()        |  Yes
| reversed()    |  invertido()   |  Yes
| round()       |  redond()      |  Yes
| set()         |  set()         |  Yes
| setattr()     |  ponatr()      |  Yes
| slice()       |  cortar()      |  Yes
| sorted()      |  ordenado()    |  Yes
| staticmethod()|  metestat()    |  Yes
| str()         |  pal()         |  Yes
| sum()         |  suma()        |  Yes
| super()       |  padre()       |  Yes
| tuple()       |  tuple()       |  Yes
| type()        |  tipo()        |  Yes
| vars()        |  vars()        |  Yes
| zip()         |  zip()         |  Yes
| __import__()  |  __importar__()|  Yes

1. Spanish keyword works, English one doesn't.

#### Etc

| English         | Spanish       |   Working?
| ----------------| --------------| ----------
| True            | Cierto        |   Yes
| False           | Falso         |   Yes
| None            | Nada          |   Yes
| if              | si            |   Yes 
| else            | si_no         |   Yes 
| elif            | sino          |   Yes 
| not             | no            |   Yes
| in              | en            |   Yes
| pass            | pasa          |   Yes
| continue        | continuar     |   Yes
| break           | romper        |   Yes
| class           | clase         |   Yes
| def             | def           |   Yes
| for             | para          |   Yes
| while           | mientras      |   Yes
| return          | volver        |   Yes
| try             | probar        |   Yes
| except          | excepto       |   Yes
| raise           | levantar      |   Yes
| self            | mismo         |   Yes
| and             | y             |   Yes
| or              | o             |   Yes
| help            | ayuda         |   Yes, but function doesn't work
| copyright       | copyright     |   Yes
| credits         | atrib         |   Yes
| license         | licencia      |   Yes

#### Highlighting:
Is included as a sample for vim in the file `python.vim`
