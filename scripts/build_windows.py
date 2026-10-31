"""Construye la distribución Windows; nunca lee ni copia la base del usuario."""

import argparse
import hashlib
from importlib.metadata import distribution
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iscc", type=Path, help="Ruta a ISCC.exe para generar también el instalador")
    args = parser.parse_args()
    if os.name != "nt" or struct.calcsize("P") != 8:
        parser.error("La versión Windows x64 debe construirse con Python de 64 bits en Windows.")
    if args.iscc is not None and not args.iscc.is_file():
        parser.error("No existe el compilador indicado con --iscc.")
    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    if len(version.split(".")) != 3 or not all(part.isdigit() for part in version.split(".")):
        parser.error("VERSION debe tener formato mayor.menor.parche.")
    output = (ROOT / "dist" / "windows").resolve()
    work = (ROOT / "build" / "pyinstaller").resolve()
    # PyInstaller puede reemplazar sus salidas: limitar siempre estos destinos al proyecto.
    for path in (output, work):
        if not path.is_relative_to(ROOT):
            parser.error("Las salidas de construcción deben permanecer dentro del proyecto.")
    subprocess.run([sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean", "--log-level", "WARN",
                    "--distpath", str(output), "--workpath", str(work),
                    str(ROOT / "packaging" / "InventarioVentas.spec")], cwd=ROOT, check=True)
    bundle = output / "InventarioVentas"
    shutil.copytree(ROOT / "examples", bundle / "examples", dirs_exist_ok=True)
    shutil.copyfile(ROOT / "docs" / "aplicacion_windows.md", bundle / "LEEME.txt")
    shutil.copyfile(ROOT / "VERSION", bundle / "VERSION.txt")
    licenses = bundle / "Licencias"
    licenses.mkdir(exist_ok=True)
    shutil.copyfile(Path(sys.base_prefix) / "LICENSE.txt", licenses / "Python.txt")
    shutil.copyfile(Path(sys.base_prefix) / "tcl" / "tk8.6" / "license.terms", licenses / "Tcl-Tk.txt")
    for entry in distribution("pyinstaller").files or ():
        if entry.name == "COPYING.txt":
            shutil.copyfile(distribution("pyinstaller").locate_file(entry), licenses / "PyInstaller.txt")
            break
    else:
        raise RuntimeError("No se encontró el aviso de licencia de PyInstaller.")
    forbidden = [path for path in bundle.rglob("*") if path.is_file() and
                 (path.suffix.lower() in {".db", ".sqlite", ".sqlite3"} or path.name.startswith(".env"))]
    if forbidden:
        raise RuntimeError("El paquete contiene datos locales o configuración privada; se cancela la distribución.")
    release = ROOT / "dist" / "releases" / ("v" + version)
    release.mkdir(parents=True, exist_ok=True)
    archive = release / f"InventarioVentas-{version}-Windows-x64.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as stream:
        for path in sorted(bundle.rglob("*")):
            if path.is_file():
                stream.write(path, path.relative_to(output))
    artifacts = [archive]
    if args.iscc:
        subprocess.run([str(args.iscc.resolve()), "/Q", f"/DAppVersion={version}", f"/DSourceDir={bundle}",
                        f"/DReleaseDir={release}", str(ROOT / "packaging" / "windows.iss")], check=True)
        artifacts.append(release / f"InventarioVentas-{version}-Windows-x64-Setup.exe")
    checksums = release / "SHA256SUMS.txt"
    checksums.write_text("".join(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                                 for path in artifacts), encoding="utf-8")
    for path in [*artifacts, checksums]:
        print(f"{path} ({path.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
