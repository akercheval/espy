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
