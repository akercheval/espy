
all: pypy-c cffi_imports

PYPY_EXECUTABLE := $(shell which pypy)
URAM := $(shell python -c "import sys; print 4.5 if sys.maxint>1<<32 else 2.5")

ifeq ($(PYPY_EXECUTABLE),)
RUNINTERP = python
else
RUNINTERP = $(PYPY_EXECUTABLE)
endif

.PHONY: pypy-c cffi_imports

pypy-c:
	@echo
	@echo "===================================================================="
ifeq ($(PYPY_EXECUTABLE),)
	@echo "Building a regular (jitting) version of PyPy, using CPython."
	@echo "This takes around 2 hours and $(URAM) GB of RAM."
	@echo "Note that pre-installing a PyPy binary would reduce this time"
	@echo "and produce basically the same result."
else
	@echo "Building a regular (jitting) version of PyPy, using"
	@echo "$(PYPY_EXECUTABLE) to run the translation itself."
	@echo "This takes up to 1 hour and $(URAM) GB of RAM."
endif
	@echo
	@echo "For more control (e.g. to use multiple CPU cores during part of"
	@echo "the process) you need to run \`\`rpython/bin/rpython'' directly."
	@echo "For more information see \`\`http://pypy.org/download.html''."
	@echo "===================================================================="
	@echo
	@sleep 5
	cd pypy/goal && $(RUNINTERP) ../../rpython/bin/rpython -Ojit targetpypystandalone.py

# Note: the -jN option, or MAKEFLAGS=-jN, are not usable.  They are
# replaced with an opaque --jobserver option by the time this Makefile
# runs.  We cannot get their original value either:
# http://lists.gnu.org/archive/html/help-make/2010-08/msg00106.html

cffi_imports: pypy-c
	PYTHONPATH=. pypy/goal/pypy-c pypy/tool/build_cffi_imports.py || /bin/true
