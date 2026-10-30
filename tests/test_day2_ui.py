"""Recorridos de formularios y carrito con Tkinter y SQLite reales."""

from pathlib import Path
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.inventory import create_product, get_product, list_products
from app.ui import InventoryApp


class DayTwoWindowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "ui.db"
        initialize_database(self.db)
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = InventoryApp(self.root, self.db)

    def fill(self, dialog, code="P1", name="Café", price="8500,50", stock="5"):
        for field, value in zip(("codigo", "nombre", "precio", "stock"), (code, name, price, stock)):
            dialog.fields[field].set(value)

    def select_inventory(self, product_id):
        self.app.reload_products()
        self.app.tree.selection_set(str(product_id))
        self.app.tree.focus(str(product_id))

    def test_create_and_edit_dialog_persist_and_refresh_inventory(self):
        dialog = self.app.new_product()
        self.fill(dialog)
        dialog.save_button.invoke()
        product = list_products(self.db)[0]
        self.assertEqual(product["precio"], 850050)
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.select_inventory(product["id"])
        edit = self.app.edit_selected_product()
        self.assertEqual(edit.fields["precio"].get(), "8500,50")
        edit.fields["nombre"].set("Café editado")
        edit.fields["stock"].set("0")
        edit.save_button.invoke()
        self.assertEqual(get_product(product["id"], self.db)["nombre"], "Café editado")
        self.assertEqual(get_product(product["id"], self.db)["stock"], 0)

    def test_invalid_form_stays_open_and_cancel_does_not_write(self):
        dialog = self.app.new_product()
        self.fill(dialog, price="1,000.00")
        dialog.save_button.invoke()
        self.assertTrue(dialog.winfo_exists())
        self.assertTrue(dialog.error_var.get())
        self.assertEqual(list_products(self.db), [])
        dialog.cancel_button.invoke()
        self.assertEqual(list_products(self.db), [])

    def test_enter_on_cancel_never_writes_new_or_edited_product(self):
        self.root.deiconify()
        dialog = self.app.new_product()
        self.fill(dialog)
        self.root.update()
        dialog.cancel_button.focus_force()
        self.root.update()
        dialog.cancel_button.event_generate("<Return>")
        self.root.update()
        self.assertEqual(list_products(self.db), [])

        product_id = create_product("P1", "Nombre original", "10,50", "5", self.db)
        self.select_inventory(product_id)
        edit = self.app.edit_selected_product()
        edit.fields["nombre"].set("Cambio cancelado")
        self.root.update()
        edit.cancel_button.focus_force()
        self.root.update()
        edit.cancel_button.event_generate("<Return>")
        self.root.update()
        self.assertEqual(get_product(product_id, self.db)["nombre"], "Nombre original")

    def test_enter_in_input_saves_one_product(self):
        self.root.deiconify()
        dialog = self.app.new_product()
        self.fill(dialog)
        self.root.update()
        dialog.entries["stock"].focus_force()
        self.root.update()
        dialog.entries["stock"].event_generate("<Return>")
        self.root.update()
        products = list_products(self.db)
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["codigo"], "P1")

    def test_delete_requires_confirmation_and_refuses_product_in_cart(self):
        product_id = create_product("P1", "Café", "1", "5", self.db)
        self.select_inventory(product_id)
        with patch("app.ui.messagebox.askyesno", return_value=False):
            self.app.delete_selected_product()
        self.assertIsNotNone(get_product(product_id, self.db))
        self.app.cart.add(product_id)
        with patch("app.ui.messagebox.showerror"):
            self.app.delete_selected_product()
        self.assertIsNotNone(get_product(product_id, self.db))
        self.app.cart.clear()
        with patch("app.ui.messagebox.askyesno", return_value=True):
            self.app.delete_selected_product()
        self.assertIsNone(get_product(product_id, self.db))
        self.assertEqual(len(self.app.tree.get_children()), 0)

    def test_pos_search_scan_quantity_and_tabs_keep_one_cart(self):
        product_id = create_product("P1", "Café", "0,10", "5", self.db)
        pos = self.app.pos
        pos.search_var.set("CAFÉ")
        pos.refresh_products()
        self.assertEqual(len(pos.results_tree.get_children()), 1)
        for _ in range(2):
            pos.search_var.set("p1")
            pos.search_or_add()
        self.assertEqual(len(pos.cart_tree.get_children()), 1)
        self.assertEqual(pos.total_var.get(), "0,20")
        pos.cart_tree.selection_set(str(product_id))
        pos.quantity_var.set("3")
        pos.apply_quantity()
        self.assertEqual(pos.total_var.get(), "0,30")
        self.app.notebook.select(self.app.inventory_tab)
        self.root.update()
        self.app.notebook.select(pos)
        self.root.update()
        self.assertEqual(self.app.cart.total_cents, 30)
        self.assertEqual(get_product(product_id, self.db)["stock"], 5)
        self.assertEqual(len(pos.cart_tree.get_children()), 1)

    def test_pos_stock_error_clear_cancel_and_remove(self):
        product_id = create_product("P1", "Café", "10", "1", self.db)
        pos = self.app.pos
        pos.search_var.set("P1")
        pos.search_or_add()
        with patch("app.pos_ui.messagebox.showerror"):
            pos.search_var.set("P1")
            pos.search_or_add()
        self.assertEqual(self.app.cart.total_cents, 1000)
        self.assertEqual(pos.total_var.get(), "10,00")
        with patch("app.pos_ui.messagebox.askyesno", return_value=False):
            pos.clear_cart()
        self.assertEqual(self.app.cart.total_cents, 1000)
        pos.cart_tree.selection_set(str(product_id))
        pos.remove_selected()
        self.assertEqual(pos.total_var.get(), "0,00")
        pos.search_var.set("P1")
        pos.search_or_add()
        with patch("app.pos_ui.messagebox.askyesno", return_value=True):
            pos.clear_cart()
        self.assertEqual(self.app.cart.items, ())
        self.assertEqual(len(pos.cart_tree.get_children()), 0)

    def test_closing_can_be_cancelled_when_cart_is_pending(self):
        product_id = create_product("P1", "Café", "1", "1", self.db)
        self.app.cart.add(product_id)
        with patch("app.ui.messagebox.askyesno", return_value=False):
            self.app.close_application()
        self.assertTrue(self.root.winfo_exists())
        self.assertEqual(self.app.cart.total_cents, 100)


if __name__ == "__main__":
    unittest.main()
