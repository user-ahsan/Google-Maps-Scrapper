# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata
import sys
import os

block_cipher = None

# --- CONSTANTS ---
# Using the found Python 3.13 path for Tcl/Tk because they were missing in venv or broken
PYTHON_HOME = r"C:\Users\ahsan\AppData\Local\Programs\Python\Python313"

# --- COLLECT DEPENDENCIES ---
datas = []
binaries = []
hiddenimports = [
    'playwright', 
    'customtkinter', 
    'fake_useragent', 
    'gspread', 
    'oauth2client',
    'PIL._tkinter_finder', 
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox'
]

# 1. Playwright
p_datas, p_binaries, p_hidden = collect_all('playwright')
datas.extend(p_datas)
binaries.extend(p_binaries)
hiddenimports.extend(p_hidden)

# 2. CustomTkinter
c_datas, c_binaries, c_hidden = collect_all('customtkinter')
datas.extend(c_datas)
binaries.extend(c_binaries)
hiddenimports.extend(c_hidden)

# 3. FakeUserAgent
f_datas = collect_data_files('fake_useragent')
datas.extend(f_datas)

# 4. Local Source Files
datas.append(('src', 'src'))
datas.append(('input.txt', '.'))
datas.append(('credentials.json', '.'))
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))

datas.append(('assets/selectors.json', 'assets'))

# 5. Metadata
try:
    datas.extend(copy_metadata('google-api-python-client'))
except Exception:
    pass

# --- MANUAL TKINTER COLLECTION ---
# Force include the detected Tcl/Tk files
# 1. DLLs
binaries.append((os.path.join(PYTHON_HOME, 'DLLs', 'tcl86t.dll'), '.'))
binaries.append((os.path.join(PYTHON_HOME, 'DLLs', 'tk86t.dll'), '.'))
binaries.append((os.path.join(PYTHON_HOME, 'DLLs', '_tkinter.pyd'), '.'))

# 2. Python Package
datas.append((os.path.join(PYTHON_HOME, 'Lib', 'tkinter'), 'tkinter'))

# 3. Tcl/Tk Data Sources (Tcl Library)
# We map the 'tcl' folder to 'tcl' and 'lib' to ensure it's found
tcl_src = os.path.join(PYTHON_HOME, 'tcl')
if os.path.exists(tcl_src):
    datas.append((tcl_src, 'tcl'))
    # Some windows python installs have it differently, but this matched our search.

# Clean up duplicates
hiddenimports = list(set(hiddenimports))

analysis = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(analysis.pure, analysis.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    analysis.scripts,
    analysis.binaries,
    analysis.zipfiles,
    analysis.datas,
    [],
    name='GoogleMapsScraper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico' if os.path.exists('assets/icon.ico') else None
)

