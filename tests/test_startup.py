"""El diagnóstico distingue una interfaz lista de un fallo de inicialización."""

import os
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

import main


class StartupTests(unittest.TestCase):
    def test_success_records_readiness_after_real_window_initializes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventario.db"
            root = tk.Tk()
            root.withdraw()
            root.after(100, root.destroy)
            with patch.object(main, "DEFAULT_DB_PATH", path), patch.object(main.tk, "Tk", return_value=root):
                self.assertEqual(main.main(), 0)
            log = (path.parent / "inicio.log").read_text(encoding="utf-8")
            self.assertIn(f"pid={os.getpid()} INFO Interfaz lista", log)
            self.assertTrue(path.exists())

    def test_ui_failure_records_error_without_readiness(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "inventario.db"
            with patch.object(main, "DEFAULT_DB_PATH", path), patch.object(main, "InventoryApp", side_effect=OSError("fallo de prueba")), patch.object(main.messagebox, "showerror"):
                self.assertEqual(main.main(), 1)
            log = (path.parent / "inicio.log").read_text(encoding="utf-8")
            self.assertIn("ERROR No se pudo iniciar la aplicación", log)
            self.assertNotIn("INFO Interfaz lista", log)
