import os
import sys


def _set_tcl_tk_env():
    if not getattr(sys, 'frozen', False):
        return

    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))

    tcl_dir = os.path.join(base_dir, 'tcl', 'tcl8.6')
    tk_dir = os.path.join(base_dir, 'tcl', 'tk8.6')
    if not os.path.exists(tk_dir):
        tk_dir = os.path.join(base_dir, 'tk', 'tk8.6')

    if os.path.exists(tcl_dir):
        os.environ['TCL_LIBRARY'] = tcl_dir
        os.environ['TK_LIBRARY'] = tk_dir
        os.environ['TCL_ROOT'] = os.path.dirname(tcl_dir)
        os.environ['TK_ROOT'] = os.path.dirname(tk_dir)


_set_tcl_tk_env()
