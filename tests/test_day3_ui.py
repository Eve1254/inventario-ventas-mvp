"""Venta completa, alertas y diálogos CSV con SQLite/Tkinter reales."""

import csv
from pathlib import Path
import sqlite3
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.inventory import create_product, get_product, update_product
from app.sales import Cart, list_sales, process_sale
from app.ui import InventoryApp


class DayThreeWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / "ui.db"
        initialize_database(self.db)
        self.empty = create_product("S0", "Agotado", "1", "0", self.db)
        self.low = create_product("S4", "Bajo", "1", "4", self.db)
        self.available = create_product("S5", "Disponible", "10,50", "5", self.db)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = InventoryApp(self.root, self.db)

    def prepare(self):
        self.app.cart.add(self.available, 2)
        self.app.pos.refresh_cart()

    def test_stock_alert_boundaries_have_text_and_tags(self):
        for product_id, state, tag in [(self.empty, "Agotado", "empty"), (self.low, "Bajo", "low"),
                                       (self.available, "Disponible", None)]:
            row = self.app.tree.item(str(product_id))
            self.assertEqual(row["values"][-1], state)
            if tag:
                self.assertIn(tag, row["tags"])
            else:
                self.assertNotIn("low", row["tags"])
                self.assertNotIn("empty", row["tags"])

    def test_confirmed_sale_updates_all_views_and_button(self):
        self.prepare()
        with patch("app.pos_ui.messagebox.askyesno", return_value=True), patch("app.pos_ui.messagebox.showinfo"):
            self.app.pos.process_button.invoke()
        self.assertEqual(get_product(self.available, self.db)["stock"], 3)
        self.assertEqual(self.app.cart.items, ())
        self.assertEqual(self.app.pos.total_var.get(), "0,00")
        self.assertTrue(self.app.pos.process_button.instate(["disabled"]))
        self.assertIn("low", self.app.tree.item(str(self.available), "tags"))
        self.assertEqual(len(self.app.history.sales_tree.get_children()), 1)
        self.assertEqual(len(self.app.history.details_tree.get_children()), 1)
        self.assertIn("21,00", self.app.history.summary_var.get())

    def test_cancelling_confirmation_does_not_write(self):
        self.prepare()
        with patch("app.pos_ui.messagebox.askyesno", return_value=False):
            self.app.pos.process_button.invoke()
        self.assertEqual(list_sales(self.db), [])
        self.assertEqual(get_product(self.available, self.db)["stock"], 5)
        self.assertEqual(self.app.cart.total_cents, 2100)
        self.assertFalse(self.app.pos._processing)
        self.assertFalse(self.app.pos.process_button.instate(["disabled"]))

    def test_reentrant_activation_during_confirmation_cannot_duplicate_sale(self):
        self.prepare()

        def confirm(*args, **kwargs):
            self.assertTrue(self.app.pos.process_button.instate(["disabled"]))
            self.app.pos.process_current_sale()
            return True

        with patch("app.pos_ui.messagebox.askyesno", side_effect=confirm), patch("app.pos_ui.messagebox.showinfo"):
            self.app.pos.process_current_sale()
            self.app.pos.process_current_sale()  # Vacío después del commit.
        self.assertEqual(len(list_sales(self.db)), 1)
        self.assertEqual(get_product(self.available, self.db)["stock"], 3)

    def test_failed_sale_preserves_cart_and_allows_retry(self):
        self.prepare()
        update_product(self.available, "S5", "Disponible", "10,50", "0", self.db)
        with patch("app.pos_ui.messagebox.askyesno", return_value=True), patch("app.pos_ui.messagebox.showerror"):
            self.app.pos.process_button.invoke()
        self.assertEqual(list_sales(self.db), [])
        self.assertEqual(self.app.cart.total_cents, 2100)
        self.assertFalse(self.app.pos.process_button.instate(["disabled"]))

    def test_refresh_failure_after_commit_never_reports_sale_as_uncommitted(self):
        self.prepare()
        self.app.pos.on_sale_saved = lambda: (_ for _ in ()).throw(sqlite3.OperationalError("fallo de refresco"))
        with patch("app.pos_ui.messagebox.askyesno", return_value=True), \
             patch("app.pos_ui.messagebox.showwarning") as warning, patch("app.pos_ui.messagebox.showerror") as error:
            self.app.pos.process_current_sale()
        self.assertEqual(len(list_sales(self.db)), 1)
        self.assertEqual(self.app.cart.items, ())
        warning.assert_called_once()
        error.assert_not_called()

    def test_export_cancel_creates_nothing_and_export_ignores_inventory_filter(self):
        before = set(self.directory.iterdir())
        with patch("app.export_ui.filedialog.asksaveasfilename", return_value=""):
            self.app.export_button.invoke()
        self.assertEqual(set(self.directory.iterdir()), before)
        self.app.search_var.set("S5")
        self.app.reload_products()
        self.assertEqual(len(self.app.tree.get_children()), 1)
        destination = self.directory / "all.csv"
        with patch("app.export_ui.filedialog.asksaveasfilename", return_value=str(destination)), \
             patch("app.export_ui.messagebox.showinfo"):
            self.app.export_button.invoke()
        with destination.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        self.assertEqual(len(rows), 3)

    def test_history_exports_confirmed_sale_details(self):
        self.prepare()
        with patch("app.pos_ui.messagebox.askyesno", return_value=True), patch("app.pos_ui.messagebox.showinfo"):
            self.app.pos.process_current_sale()
        destination = self.directory / "sales.csv"
        with patch("app.export_ui.filedialog.asksaveasfilename", return_value=str(destination)), \
             patch("app.export_ui.messagebox.showinfo"):
            self.app.history.export_button.invoke()
        with destination.open(encoding="utf-8-sig", newline="") as stream:
            rows = list(csv.DictReader(stream, delimiter=";"))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["subtotal"], "21,00")

    def test_export_to_database_is_reported_without_overwrite(self):
        before = self.db.read_bytes()
        with patch("app.export_ui.filedialog.asksaveasfilename", return_value=str(self.db)), \
             patch("app.export_ui.messagebox.showerror") as error, patch("app.export_ui.messagebox.showinfo") as success:
            self.app.export_button.invoke()
        error.assert_called_once()
        success.assert_not_called()
        self.assertEqual(self.db.read_bytes(), before)

    def test_stale_edit_form_cannot_restore_stock_sold_by_another_connection(self):
        self.app.tree.selection_set(str(self.available))
        dialog = self.app.edit_selected_product()
        other_cart = Cart(self.db)
        other_cart.add(self.available, 4)
        process_sale(other_cart)  # Simula otra ventana mientras el formulario sigue abierto.
        dialog.fields["nombre"].set("Nombre editado después")
        dialog.save_button.invoke()
        self.assertEqual(get_product(self.available, self.db)["stock"], 1)
        self.assertEqual(get_product(self.available, self.db)["nombre"], "Disponible")
        self.assertEqual(len(list_sales(self.db)), 1)
        self.assertTrue(dialog.winfo_exists())
        self.assertTrue(dialog.error_var.get())
        dialog.destroy()

    def test_real_refresh_failures_keep_warning_after_successful_commit(self):
        targets = ("app.pos_ui.list_products", "app.ui.list_products", "app.sales_ui.list_sales")
        for index, target in enumerate(targets):
            with self.subTest(target=target):
                update_product(self.available, "S5", "Disponible", "10,50", "5", self.db)
                self.prepare()
                with patch(target, side_effect=sqlite3.OperationalError("lectura fallida")), \
                     patch("app.pos_ui.messagebox.askyesno", return_value=True), \
                     patch("app.pos_ui.messagebox.showwarning") as warning, \
                     patch("app.pos_ui.messagebox.showerror"), patch("app.pos_ui.messagebox.showinfo") as success:
                    self.app.pos.process_current_sale()
                self.assertEqual(get_product(self.available, self.db)["stock"], 3)
                self.assertEqual(len(list_sales(self.db)), index + 1)
                self.assertEqual(self.app.cart.items, ())
                warning.assert_called_once()
                success.assert_not_called()
                self.assertIn("Actualiza", self.app.pos.status_var.get())


if __name__ == "__main__":
    unittest.main()
