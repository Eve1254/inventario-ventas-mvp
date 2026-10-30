"""Refresco y dibujo de los gráficos con Tk y SQLite reales."""

from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import tkinter as tk
import unittest
from unittest.mock import patch

from app.database import connect_db, initialize_database
from app.inventory import create_product, get_product
from app.ui import InventoryApp


class ChartWindowTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.db = Path(temp.name) / "charts.db"
        initialize_database(self.db)
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.app = InventoryApp(self.root, self.db)

    def show_charts(self):
        self.app.notebook.select(self.app.charts)
        self.root.update()

    def test_empty_charts_identify_no_data_without_inventing_bars(self):
        self.show_charts()
        canvas = self.app.charts.stock_canvas
        text = [canvas.itemcget(item, "text") for item in canvas.find_withtag("label")]
        self.assertTrue(any("Sin productos" in value for value in text))
        self.assertEqual(canvas.find_withtag("bar"), ())
        self.assertEqual(self.app.charts.sales_canvas.find_withtag("bar"), ())

    def test_stock_bars_are_proportional_and_refresh_after_external_change(self):
        first = create_product("A", "Tres unidades", "1", "3", self.db)
        create_product("B", "Seis unidades", "1", "6", self.db)
        self.show_charts()
        canvas = self.app.charts.stock_canvas
        coordinates = [canvas.coords(item) for item in canvas.find_withtag("bar")]
        lengths = [right - left for left, top, right, bottom in coordinates]
        self.assertAlmostEqual(lengths[0] / lengths[1], 0.5)
        with connect_db(self.db) as connection:
            connection.execute("UPDATE productos SET stock=0 WHERE id=?", (first,))
        self.app.charts.refresh_button.invoke()
        self.assertEqual(self.app.charts.data.stock[0].units, 0)
        self.assertEqual(len(canvas.find_withtag("bar")), 1)

    def test_sale_and_product_form_refresh_chart_data(self):
        product = create_product("A", "Producto", "10,50", "6", self.db)
        self.app._after_product_saved()
        self.assertEqual(self.app.charts.data.stock[0].units, 6)
        self.app.cart.add(product, 3)
        with patch("app.pos_ui.messagebox.askyesno", return_value=True), patch("app.pos_ui.messagebox.showinfo"):
            self.app.pos.process_current_sale()
        self.assertEqual(self.app.charts.data.stock[0].units, 3)
        self.assertEqual(self.app.charts.data.sales_total_cents, 3150)
        self.assertEqual(self.app.charts.data.sales_count, 1)

    def test_failed_read_preserves_previous_chart_and_marks_it_stale(self):
        create_product("A", "Producto", "1", "6", self.db)
        self.show_charts()
        before = self.app.charts.data
        with connect_db(self.db) as connection:
            connection.execute("ALTER TABLE ventas RENAME TO ventas_oculta")
        self.assertFalse(self.app.charts.refresh(notify=False))
        self.assertEqual(self.app.charts.data, before)
        self.assertIn("desactualizados", self.app.charts.status_var.get())

    def test_chart_read_failure_after_commit_does_not_repeat_or_undo_sale(self):
        product = create_product("A", "Producto", "10,50", "6", self.db)
        self.app.cart.add(product, 3)
        with patch("app.charts_ui.load_chart_data", side_effect=sqlite3.OperationalError("lectura fallida")), \
             patch("app.pos_ui.messagebox.askyesno", return_value=True), \
             patch("app.pos_ui.messagebox.showwarning"), patch("app.pos_ui.messagebox.showinfo"):
            self.app.pos.process_current_sale()
        self.assertEqual(get_product(product, self.db)["stock"], 3)
        self.assertEqual(self.app.cart.items, ())
        self.assertIn("Actualiza", self.app.pos.status_var.get())


if __name__ == "__main__":
    unittest.main()
