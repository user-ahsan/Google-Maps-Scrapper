try:
    import tkinter
    print("Tkinter is working!")
    print(f"Tkinter version: {tkinter.TkVersion}")
    import _tkinter
    print(f"_tkinter path: {_tkinter.__file__}")
except ImportError as e:
    print(f"Tkinter ERROR: {e}")
except Exception as e:
    print(f"Other ERROR: {e}")
