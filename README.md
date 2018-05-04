# espy

### pypy, in Spanish!

In this directory I will be modifying the pypy source code to operate using 
Spanish, in everything from the keywords to the error messages. This will
be different from the python version of [sí](https://github.com/akercheval/si),
because while sí is a preprocessor that changes the language from English to 
Spanish (and vice-versa), espy will be, at its core, in Spanish. 

This is part of my senior honors thesis at Tufts University, and naturally the
code will be open-source. You can read a copy of my thesis [here](https://github.com/akercheval/espy/blob/master/Thesis%20-%20Adam%20Kercheval.pdf)

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

All the keywords and their respective translations can be found [here](https://docs.google.com/spreadsheets/d/1Sub2El7knpA1Z5R4iM2PimXfTPOX2M2vCwZrLQ5C3yU/edit?usp=sharing).
You can also run `python3 pickler.py` in the main directory for an interactive lookup
tool.

### Syntax highlighting:
I've included a file called [`python.vim`](https://github.com/akercheval/espy/blob/master/python.vim)
that you can put wherever your syntax files are held (for vim), and it will
highlight the new Spanish words appropriately. I'm working on getting another
editor's highlighting to work as well, probably Atom, Sublime, or Brackets, but 
they are proving to be a bit trickier than vim is.

