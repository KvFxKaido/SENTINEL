# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec for SENTINEL Agent.

Build with:
    pyinstaller sentinel.spec

Output in dist/sentinel/
"""

import os
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Collect tiktoken data files (encoding definitions)
tiktoken_datas = collect_data_files('tiktoken')

a = Analysis(
    ['src/interface/cli.py'],
    pathex=[],
    binaries=[],
    datas=[
        # Prompts - keep editable in dist folder
        ('prompts', 'prompts'),
        # Tiktoken encoding data
        *tiktoken_datas,
    ],
    hiddenimports=[
        'tiktoken_ext.openai_public',
        'tiktoken_ext',
        # Rich markup
        'rich.markup',
        'rich.console',
        'rich.panel',
        'rich.table',
        # Prompt toolkit
        'prompt_toolkit',
        # Pydantic
        'pydantic',
        # Optional memvid - won't break if missing
        'memvid',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude dev/test stuff
        'pytest',
        'black',
        'mypy',
        'ruff',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='sentinel',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # CLI app needs console
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # Add icon path here if you have one: 'assets/icon.ico'
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='sentinel',
)
