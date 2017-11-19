import pickle
def pickler():
    trans = {}
    action = input("Load or save? (l/s) ")
    if action == 'l':
        try:
            trans = load_obj("trans")
        except FileNotFoundError:
            print("No trans object exists yet.")
            quit()
        eng = input("Word in English: ")
        if eng in trans:
            print("Spanish translation:", trans[eng])
        else:
            print("A Spanish translation for", eng, "doesn't exist yet!")
    elif action == 's':
        eng = input("Word in English: ")
        spn = input("Word in Spanish: ")
        try:
            trans = load_obj("trans")
        except (FileNotFoundError, EOFError):
            trans = {}
        if eng not in trans:
            trans[eng] = spn
            save_obj(trans, "trans")
            print(eng, "saved as", spn)
        else:
            print("There's already a word translating " + eng + ": " + trans[eng] + ".")
            overwrite = input("Do you want to overwrite it? (y/n) ")
            if overwrite == 'y':
                trans[eng] = spn
                save_obj(trans, "trans")
                print(eng, "saved as", spn)

    cont = input("Another? (y/n) ")
    if cont == "y":
        pickler()


def save_obj(obj, name ):
    with open('obj/'+ name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name ):
    with open('obj/' + name + '.pkl', 'rb') as f:
        return pickle.load(f)

pickler()
