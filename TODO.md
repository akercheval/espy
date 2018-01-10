## TODO

* Don't break the help() function: for example, help(list) makes no sense in 
    espy. I think that this is because I put the Spanish references to functions
    below their English counterparts in W_ListObject.typedef, but I'm not sure.
* Remove all the unnecessary stuff pypy throws up when the interpreter starts,
    and translate it to Spanish.
* Traceback translations, found in `pypy/interpreter/error.py`
* Translate error names
  * 1/9 I did two things to see which works: I changed what I believe is the 
    `__name__` attribute of `ValueError` to `ValorError` in 
    `pypy/module/exceptions/interp_exceptions.py`, and I mapped the string
    `IndiceError` to `IndexError`'s typedef in `pypy/module/exceptions/__init__.py`
* Translate object method names: for example, I've never seen the definition of 
  `list.append` yet and as such haven't translated it.
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
| help()        |                |  *not found yet*
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
| object()      |  objeto()      |  **No**
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
| set()         |  set()         |  Yes (but only because name is same)
| setattr()     |  ponatr()      |  Yes
| slice()       |  cortar()      |  **No**
| sorted()      |  ordenado()    |  Yes
| staticmethod()|  metestat()    |  Yes
| str()         |  pal()         |  **No**
| sum()         |  suma()        |  Yes
| super()       |  padre()       |  Yes
| tuple()       |  tuple()       |  Yes
| type()        |  tipo()        |  **No**
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
| help            | ayuda         |   **Not found**
| copyright       | copyright     |   N/A (same word)
| credits         | atrib         |   **Not found**
| license         | licencia      |   **Not found**
