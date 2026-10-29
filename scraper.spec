# -*- mode: python ; coding: utf-8 -*-
import os
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files, copy_metadata

block_cipher = None

# --- DETECT PYTHON RUNTIME FOR TCL/TK ---
PYTHON_HOME = getattr(sys, 'base_prefix', sys.prefix)
if not os.path.exists(os.path.join(PYTHON_HOME, 'DLLs', 'tcl86t.dll')):
    candidates = [
        r"C:\Users\ahsan\AppData\Local\Python\pythoncore-3.14-64",
        r"C:\Users\ahsan\AppData\Local\Programs\Python\Python313",
        r"C:\Users\ahsan\AppData\Local\Programs\Python\Python312",
    ]
    for c in candidates:
        if os.path.exists(os.path.join(c, 'DLLs', 'tcl86t.dll')):
            PYTHON_HOME = c
            break

# --- COLLECT DEPENDENCIES ---
datas = []
binaries = []
hiddenimports = [
    'playwright',
    'customtkinter',
    'fake_useragent',
    'gspread',
    'oauth2client',
    'oauth2client.service_account',
    'PIL._tkinter_finder',
    'tkinter',
    'tkinter.filedialog',
    'tkinter.messagebox',
    'main_gui_wrapper',
    'src.config_manager',
    'src.controller',
    'src.db',
    'src.job_manager',
    'src.leads_scraping',
    'src.logger',
    'src.resource_utils',
    'src.security_utils',
    'src.selector_manager',
    'src.sheets_utils',
    'pandas',
    'openpyxl',
    'dotenv',
    'tenacity'
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
if os.path.exists('input.txt'):
    datas.append(('input.txt', '.'))
if os.path.exists('credentials.json'):
    datas.append(('credentials.json', '.'))
if os.path.exists('config.json'):
    datas.append(('config.json', '.'))
if os.path.exists('assets'):
    datas.append(('assets', 'assets'))
if os.path.exists('test'):
    datas.append(('test', 'test'))

# 5. Metadata
try:
    datas.extend(copy_metadata('google-api-python-client'))
except Exception:
    pass

# --- MANUAL TKINTER COLLECTION ---
for dll_name in ['tcl86t.dll', 'tk86t.dll', '_tkinter.pyd']:
    dll_path = os.path.join(PYTHON_HOME, 'DLLs', dll_name)
    if os.path.exists(dll_path):
        binaries.append((dll_path, '.'))

tk_pkg = os.path.join(PYTHON_HOME, 'Lib', 'tkinter')
if os.path.exists(tk_pkg):
    datas.append((tk_pkg, 'tkinter'))

tcl_src = os.path.join(PYTHON_HOME, 'tcl')
if os.path.exists(tcl_src):
    datas.append((tcl_src, 'tcl'))

# Deduplicate
hiddenimports = list(set(hiddenimports))
unique_datas = []
seen_datas = set()
for src, dst in datas:
    key = (src, dst)
    if key not in seen_datas:
        seen_datas.add(key)
        unique_datas.append((src, dst))
datas = unique_datas

runtime_hooks = []
if os.path.exists('rthook_tkinter.py'):
    runtime_hooks.append('rthook_tkinter.py')

analysis = Analysis(
    ['gui_app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
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
    name='GoogleMapsScraper_v2.0',
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
