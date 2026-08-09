# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules


shared_datas = collect_data_files("customtkinter") + [("web_api/static", "web_api/static")]
shared_hidden_imports = collect_submodules("keyring.backends")
excluded_packages = [
    "matplotlib",
    "numpy",
    "pandas",
    "pytest",
    "pip_audit",
    "scipy",
    "selenium",
]

gui_analysis = Analysis(
    ["run.py"],
    pathex=[],
    binaries=[],
    datas=shared_datas,
    hiddenimports=shared_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_packages,
    noarchive=False,
)
gui_pyz = PYZ(gui_analysis.pure)
gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="NLvoorelkaar-Reachout",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
gui_bundle = COLLECT(
    gui_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    strip=False,
    upx=False,
    name="NLvoorelkaar-Reachout",
)

operator_analysis = Analysis(
    ["nlve_operator.py"],
    pathex=[],
    binaries=[],
    datas=shared_datas,
    hiddenimports=shared_hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_packages,
    noarchive=False,
)
operator_pyz = PYZ(operator_analysis.pure)
operator_exe = EXE(
    operator_pyz,
    operator_analysis.scripts,
    [],
    exclude_binaries=True,
    name="NLVE-Operator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
)
operator_bundle = COLLECT(
    operator_exe,
    operator_analysis.binaries,
    operator_analysis.datas,
    strip=False,
    upx=False,
    name="NLVE-Operator",
)
