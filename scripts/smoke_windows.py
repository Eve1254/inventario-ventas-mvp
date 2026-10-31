"""Prueba artefactos reales con un perfil aislado; conserva evidencia en build/smoke."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
import uuid
import winreg
import zipfile


ROOT = Path(__file__).resolve().parents[1]
UNINSTALL_KEY = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{948B7B28-820F-4F45-85C4-687006BB98A1}_is1"


def launch(executable: Path, profile: Path, cwd: Path) -> None:
    environment = os.environ.copy()
    environment["LOCALAPPDATA"] = str(profile)
    environment["PATH"] = str(Path(os.environ["SystemRoot"]) / "System32")
    environment.pop("PYTHONHOME", None)
    environment.pop("PYTHONPATH", None)
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    database = profile / "InventarioVentas" / "inventario.db"
    startup_log = database.parent / "inicio.log"
    process = subprocess.Popen([str(executable)], env=environment, cwd=cwd, startupinfo=startup)
    try:
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            if process.poll() is not None:
                raise RuntimeError(f"El ejecutable terminó al iniciar: {process.returncode}")
            if database.exists():
                try:
                    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
                        count = connection.execute("SELECT count(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
                    ready = startup_log.read_text(encoding="utf-8") if startup_log.exists() else ""
                    if count >= 4 and f"pid={process.pid} INFO Interfaz lista" in ready:
                        break
                except sqlite3.Error:
                    pass
            time.sleep(0.2)
        else:
            raise RuntimeError("El ejecutable no confirmó la inicialización de su interfaz en el perfil aislado.")
        time.sleep(2)
        if process.poll() is not None:
            raise RuntimeError("El ejecutable se cerró después de inicializar SQLite.")
    finally:
        # Solo se termina el proceso creado por esta prueba, sin operaciones pendientes.
        if process.poll() is None:
            process.terminate()
        process.wait(timeout=10)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--installer", type=Path, required=True)
    args = parser.parse_args()
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, UNINSTALL_KEY, 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY):
            parser.error("Ya hay una instalación del producto: ejecuta esta prueba en otro usuario o equipo.")
    except FileNotFoundError:
        pass
    work = (ROOT / "build" / "smoke" / uuid.uuid4().hex).resolve()
    if not work.is_relative_to(ROOT / "build"):
        raise RuntimeError("La carpeta de prueba debe permanecer dentro de build.")
    work.mkdir(parents=True)
    extracted = work / "carpeta con espacios y acentos á"
    with zipfile.ZipFile(args.zip) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("El ZIP no supera la comprobación CRC.")
        for name in archive.namelist():
            if not (extracted / name).resolve().is_relative_to(extracted.resolve()):
                raise RuntimeError("El ZIP contiene una ruta fuera de su carpeta.")
        archive.extractall(extracted)
    portable = extracted / "InventarioVentas" / "InventarioVentas.exe"
    profile = work / "perfil de prueba á"
    launch(portable, profile, work)
    database = profile / "InventarioVentas" / "inventario.db"
    with sqlite3.connect(database) as connection:
        assert connection.execute("SELECT COUNT(*) FROM productos").fetchone()[0] == 0
        connection.execute("INSERT INTO productos(codigo,nombre,precio,stock) VALUES ('PRUEBA','Café',1050,3)")
    launch(portable, profile, work)
    install = work / "programa instalado"
    installer = args.installer.resolve()
    command = [str(installer), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/SP-", "/NOICONS", "/TASKS=", f"/DIR={install}"]
    startup = subprocess.STARTUPINFO()
    startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startup.wShowWindow = subprocess.SW_HIDE
    subprocess.run(command, check=True, timeout=60, startupinfo=startup)
    installed_exe = install / "InventarioVentas.exe"
    assert hashlib.sha256(installed_exe.read_bytes()).digest() == hashlib.sha256(portable.read_bytes()).digest()
    launch(installed_exe, profile, work)
    subprocess.run(command, check=True, timeout=60, startupinfo=startup)
    launch(installed_exe, profile, work)
    # El destino se comprobó dentro de build antes de ejecutar la desinstalación.
    assert install.resolve().is_relative_to(work)
    subprocess.run([str(install / "unins000.exe"), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                   check=True, timeout=60, startupinfo=startup)
    assert not installed_exe.exists()
    with sqlite3.connect(database.as_uri() + "?mode=ro", uri=True) as connection:
        assert connection.execute("SELECT codigo,precio,stock FROM productos").fetchall() == [("PRUEBA", 1050, 3)]
    result = {"zip_crc": "ok", "portable_start_and_restart": "ok", "path_without_python": "ok",
              "install_reinstall_uninstall": "ok", "database_preserved": "ok",
              "work": str(work), "visual_inspection": "not_performed"}
    (work / "resultado.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=True))


if __name__ == "__main__":
    main()
