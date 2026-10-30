"""Integración con Tkinter real y una base SQLite temporal."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from app.database import connect_db, initialize_database
from app.demo import seed_demo_products
from app.ui import InventoryApp, format_price


class PriceDisplayTests(unittest.TestCase):
    def test_displays_exact_prices_without_float_rounding(self):
        for cents, expected in [(1, "0,01"), (30, "0,30"), (1050, "10,50"),
                                (850000, "8.500,00"), (9999999999999999, "99.999.999.999.999,99")]:
            with self.subTest(cents=cents):
                self.assertEqual(format_price(cents), expected)


class InventoryWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "inventario.db"
        initialize_database(self.db_path)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)

    def test_empty_window_then_refresh_reads_committed_data(self):
        app = InventoryApp(self.root, self.db_path)
        self.assertEqual(len(app.tree.get_children()), 0)
        self.assertEqual(app.empty_label.winfo_manager(), "place")

        seed_demo_products(self.db_path)
        app.refresh_button.invoke()
        rows = [tuple(map(str, app.tree.item(item, "values"))) for item in app.tree.get_children()]
        self.assertEqual(len(rows), 5)
        coffee = next(row for row in rows if row[1] == "P001")
        # El Día 3 agrega Estado al final; las columnas originales se conservan.
        self.assertEqual(coffee[2:5], ("Café molido 250 g", "8.500,00", "12"))
        self.assertEqual(app.empty_label.winfo_manager(), "")

        # Otro proceso/conexión cambia el inventario: actualizar debe releerlo.
        with connect_db(self.db_path) as connection:
            connection.execute("UPDATE productos SET stock = ? WHERE codigo = ?", (7, "P001"))
        app.refresh_button.invoke()
        rows = [tuple(map(str, app.tree.item(item, "values"))) for item in app.tree.get_children()]
        coffee = next(row for row in rows if row[1] == "P001")
        self.assertEqual(coffee[4], "7")
        self.assertEqual(len(rows), 5)  # La actualización no duplica filas.

    def test_read_failure_preserves_previous_rows_and_reports_error(self):
        seed_demo_products(self.db_path)
        app = InventoryApp(self.root, self.db_path)
        before = [app.tree.item(item, "values") for item in app.tree.get_children()]
        previous_status = app.status_var.get()
        with connect_db(self.db_path) as connection:
            connection.execute("DROP TABLE productos")  # Solo la base temporal.
        # Se sustituye únicamente el diálogo modal para no bloquear la prueba.
        with patch("app.ui.messagebox.showerror") as notification:
            app.refresh_button.invoke()
        after = [app.tree.item(item, "values") for item in app.tree.get_children()]
        self.assertEqual(after, before)
        self.assertNotEqual(app.status_var.get(), previous_status)
        notification.assert_called_once()


if __name__ == "__main__":
    unittest.main()
