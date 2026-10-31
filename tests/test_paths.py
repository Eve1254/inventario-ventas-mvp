"""Los datos del ejecutable sobreviven a la sustitución del programa."""

import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from app.database import connect_db, initialize_database
from app.paths import get_database_path


class DataPathTests(unittest.TestCase):
    def test_source_keeps_existing_project_database(self):
        with patch.object(sys, "frozen", False, create=True):
            expected = Path(__file__).resolve().parents[1] / "data" / "inventario.db"
            self.assertEqual(get_database_path(), expected)

    def test_frozen_uses_user_data_not_bundle_or_working_directory(self):
        with tempfile.TemporaryDirectory(prefix="datos con espacios ") as directory:
            local = Path(directory) / "perfil ágil"
            with patch.object(sys, "frozen", True, create=True), patch.dict(os.environ, {"LOCALAPPDATA": str(local)}):
                path = get_database_path()
                self.assertEqual(path, local / "InventarioVentas" / "inventario.db")
                initialize_database(path)
                with connect_db(path) as connection:
                    connection.execute("INSERT INTO productos(codigo,nombre,precio,stock) VALUES ('P1','Café',1050,3)")
                # Un nuevo arranque reutiliza los datos, aunque el programa cambie de carpeta.
                with patch.object(sys, "_MEIPASS", str(Path(directory) / "nueva version"), create=True):
                    initialize_database(get_database_path())
                    with connect_db(get_database_path()) as connection:
                        row = connection.execute("SELECT codigo,precio,stock FROM productos").fetchone()
                        self.assertEqual(tuple(row), ("P1", 1050, 3))

    def test_frozen_missing_or_relative_appdata_uses_home_not_current_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            for value in (None, "", "relative/path"):
                with self.subTest(value=value), patch.object(sys, "frozen", True, create=True), patch.dict(os.environ, {}, clear=True), patch("app.paths.Path.home", return_value=home):
                    if value is not None:
                        os.environ["LOCALAPPDATA"] = value
                    self.assertEqual(get_database_path(), home / "AppData" / "Local" / "InventarioVentas" / "inventario.db")
