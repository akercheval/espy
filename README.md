# espy

### pypy, in Spanish!

In this directory I will be modifying the pypy source code to operate using 
Spanish, in everything from the keywords to the error messages. This will
be different from the python version of [sí](https://github.com/akercheval/si),
because while sí is a preprocessor that changes the language from English to 
Spanish (and vice-versa), espy will be, at its core, in Spanish. 

This is part of my senior honors thesis at Tufts University, but naturally the
code will be open-source. I'll upload a version of the thesis to this repository
in May 2018, once it's published.

### To use:
If you have a 64-bit machine, you should be able to use the pre-built executable 
binary called `pypy-c` with a good ol' `./pypy-c`. If that doesn't work:

Clone the repository and run [`sh build`](https://github.com/akercheval/espy/blob/master/build),
and then walk away from your computer for somewhere around an hour and 15 
minutes. Seriously! The build process, according to 
[pypy's docs](https://pypy.org/download.html#building-from-source) will use 5 
and 3 GB of RAM on 64- and 32-bit systems, respectively.

Once the build is complete, there will be an executable file called `pypy-c` in
the repo's main directory. There's Espy!

Most of the keywords and their respective translations into Spanish can be found
in [`TODO.md`](https://github.com/akercheval/espy/blob/master/TODO.md), or you 
can run `python3 pickler.py` in the main directory to run an interactive lookup
tool.

### Syntax highlighting:
I've included a file called [`python.vim`](https://github.com/akercheval/espy/blob/master/python.vim)
that you can put wherever your syntax files are held (for vim), and it will
highlight the new Spanish words appropriately. I'm working on getting another
editor's highlighting to work as well, probably Atom, Sublime, or Brackets, but 
they are proving to be a bit trickier than vim is.

### Known issues
* Translating errors (so that, for example, `ValueError` is of type `ValorError`
  causes a very odd breakdown in the interpreter that raises an `IndentationError`
  every time it should leave space for a new line. So, right now, the final link
  between app-level errors and implementation-level errors (the kind of thing that
  would let `except: ValorError` catch both `ValueError` and `ValorError`) is
  incomplete.
* Somewhere down the line, the `help()` function got hopelessly destroyed, and I
  have yet to figure out why or how to fix it. 
