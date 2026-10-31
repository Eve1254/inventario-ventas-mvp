# Construir desde Windows con scripts/build_windows.py.
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / "main.py")],
    pathex=[str(root)],
    binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, [], exclude_binaries=True,
    name="InventarioVentas", debug=False, bootloader_ignore_signals=False,
    strip=False, upx=False, console=False,
    version=str(root / "packaging" / "version_info.txt"),
)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="InventarioVentas")
