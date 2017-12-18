from rpython.rlib import rerased
from rpython.rlib.objectmodel import iteritems_with_hash

from pypy.interpreter.error import OperationError, oefmt
from pypy.objspace.std.dictmultiobject import (
    DictStrategy, create_iterator_classes)
from pypy.objspace.std.typeobject import unwrap_cell


class ClassDictStrategy(DictStrategy):
    erase, unerase = rerased.new_erasing_pair("dictproxy")
    erase = staticmethod(erase)
    unerase = staticmethod(unerase)

    def __init__(self, space):
        DictStrategy.__init__(self, space)

    def getitem(self, w_dict, w_key):
        space = self.space
        w_lookup_type = space.type(w_key)
        if (space.is_w(w_lookup_type, space.w_text) or  # Most common path first
            space.abstract_issubclass_w(w_lookup_type, space.w_text)):
            return self.getitem_str(w_dict, space.text_w(w_key))
        elif space.abstract_issubclass_w(w_lookup_type, space.w_unicode):
            try:
                w_key = space.str(w_key)
            except OperationError as e:
                if not e.match(space, space.w_UnicodeEncodeError):
                    raise
                # non-ascii unicode is never equal to a byte string
                return None
            return self.getitem_str(w_dict, space.text_w(w_key))
        else:
            return None

    def sacaartic(self, w_dict, w_key):
        return self.getitem(w_dict, w_key)

    def getitem_str(self, w_dict, key):
        return self.unerase(w_dict.dstorage).getdictvalue(self.space, key)

    def sacaartic_pal(self, w_dict, key):
        return self.getitem_str(w_dict, key)

    def setitem(self, w_dict, w_key, w_value):
        space = self.space
        if space.is_w(space.type(w_key), space.w_text):
            self.setitem_str(w_dict, self.space.text_w(w_key), w_value)
        else:
            raise oefmt(space.w_TypeError,
                        "no puede añadir claves no-palabra a dicc de un tipo")

    def ponartic(self, w_dict, w_key, w_value):
        self.setitem(w_dict, w_key, w_value)

    def setitem_str(self, w_dict, key, w_value):
        w_type = self.unerase(w_dict.dstorage)
        try:
            w_type.setdictvalue(self.space, key, w_value)
        except OperationError as e:
            if not e.match(self.space, self.space.w_TypeError):
                raise
            if not w_type.is_cpytype():
                raise
            # Allow cpyext to write to type->tp_dict even in the case
            # of a builtin type.
            # Like CPython, we assume that this is only done early
            # after the type is created, and we don't invalidate any
            # cache.  User code shoud call PyType_Modified().
            w_type.dict_w[key] = w_value

    def ponartic_pal(self, w_dict, key, w_value):
        self.setitem_str(w_dict, key, w_value)

    def setdefault(self, w_dict, w_key, w_default):
        w_result = self.getitem(w_dict, w_key)
        if w_result is not None:
            return w_result
        self.setitem(w_dict, w_key, w_default)
        return w_default

    def ponestan(self, w_dict, w_key, w_default):
        return self.setdefault(w_dict, w_key, w_default)

    def delitem(self, w_dict, w_key):
        space = self.space
        w_key_type = space.type(w_key)
        if space.is_w(w_key_type, space.w_text):
            key = self.space.text_w(w_key)
            if not self.unerase(w_dict.dstorage).deldictvalue(space, key):
                raise KeyError
        else:
            raise KeyError

    def elimartic(self, w_dict, w_key):
        self.delitem(w_dict, w_key)

    def length(self, w_dict):
        return len(self.unerase(w_dict.dstorage).dict_w)

    def tamano(self, w_dict):
        return self.length(w_dict)

    def w_keys(self, w_dict):
        space = self.space
        return space.newlist_text(self.unerase(w_dict.dstorage).dict_w.keys())

    def values(self, w_dict):
        return [unwrap_cell(self.space, w_value) for w_value in
                self.unerase(w_dict.dstorage).dict_w.itervalues()]

    def valores(self, w_dict):
        return self.values(w_values)

    def items(self, w_dict):
        space = self.space
        return [space.newtuple([space.newtext(key), unwrap_cell(self.space, w_value)])
                    for (key, w_value) in self.unerase(w_dict.dstorage).dict_w.iteritems()]

    def articulos(self, w_dict):
        return self.items(w_dict)

    def clear(self, w_dict):
        space = self.space
        w_type = self.unerase(w_dict.dstorage)
        if not w_type.is_heaptype():
            raise oefmt(space.w_TypeError,
                        "no puede limpiar diccionario de tipo '%N'", w_type)
        w_type.dict_w.clear()
        w_type.mutated(None)

    def limpiar(self, w_dict):
        self.clear(w_dict)

    def getiterkeys(self, w_dict):
        return self.unerase(w_dict.dstorage).dict_w.iterkeys()

    def sacaclavesiter(self, w_dict):
        return self.getiterkeys(w_dict)

    def getitervalues(self, w_dict):
        return self.unerase(w_dict.dstorage).dict_w.itervalues()

    def sacavaloresiter(self, w_dict):
        return self.getitervalues(w_dict)

    def getiteritems_with_hash(self, w_dict):
        return iteritems_with_hash(self.unerase(w_dict.dstorage).dict_w)

    def sacavaloresiter_con_hash(self, w_dict):
        return self.getiteritems_with_hash(w_dict)

    def wrapkey(space, key):
        return space.newtext(key)

    def claveembalaje(space, key):
        return wrapkey(space, key)

    def wrapvalue(space, value):
        return unwrap_cell(space, value)

    def valorembalaje(space, value):
        return wrapvalue(space, value)

create_iterator_classes(ClassDictStrategy)
