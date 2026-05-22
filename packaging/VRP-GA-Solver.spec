# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files


def find_project_root() -> Path:
    candidates = [Path.cwd().resolve()]

    if "__file__" in globals():
        candidates.append(Path(__file__).resolve().parent.parent)

    if "SPECPATH" in globals():
        spec_path = Path(SPECPATH).resolve()
        candidates.extend([spec_path, spec_path.parent, spec_path.parent.parent])

    seen = set()
    for candidate in candidates:
        candidate = candidate.resolve()
        if candidate in seen:
            continue
        seen.add(candidate)
        if (candidate / "VRP_GA_2_APP" / "main.py").is_file():
            return candidate

    checked = "\n".join(f"  - {path}" for path in seen)
    raise FileNotFoundError(
        "Could not locate project root containing VRP_GA_2_APP/main.py.\n"
        f"Checked:\n{checked}"
    )


project_root = find_project_root()
app_root = project_root / "VRP_GA_2_APP"

datas = []
datas += collect_data_files("folium")
datas += collect_data_files("branca")

a = Analysis(
    [str(app_root / "main.py")],
    pathex=[str(app_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "IPython"],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="VRP-GA-Solver",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="VRP-GA-Solver",
)
