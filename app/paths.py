"""Ubicación persistente de los datos, separada del ejecutable instalado."""

import os
from pathlib import Path
import sys


def get_database_path() -> Path:
    if not getattr(sys, "frozen", False):
        return Path(__file__).resolve().parent.parent / "data" / "inventario.db"
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if not local.is_absolute():
        local = Path.home() / "AppData" / "Local"
    return local / "InventarioVentas" / "inventario.db"
