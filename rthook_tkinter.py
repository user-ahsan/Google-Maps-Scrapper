import os
import sys

# Functions to set environment variables for Tcl/Tk
def _set_tcl_tk_env():
    # Only run if frozen (bundled)
    if not getattr(sys, 'frozen', False):
        return

    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # These paths must match where we put them in scraper.spec
    # In scraper.spec we did: ('assets/tcl/tcl8.6', 'tcl/tcl8.6') 
    # so they end up at <base_dir>/tcl/tcl8.6
    
    tcl_dir = os.path.join(base_dir, 'tcl', 'tcl8.6')
    tk_dir = os.path.join(base_dir, 'tk', 'tk8.6')

    if os.path.exists(tcl_dir):
        os.environ['TCL_LIBRARY'] = tcl_dir
        os.environ['TK_LIBRARY'] = tk_dir
        # Standard env vars for some distros
        os.environ['TCL_ROOT'] = os.path.dirname(tcl_dir)
        os.environ['TK_ROOT'] = os.path.dirname(tk_dir)

_set_tcl_tk_env()
