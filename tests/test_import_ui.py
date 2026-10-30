"""Vista previa sin escritura y carga revisada con Tk/SQLite reales."""

from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import tkinter as tk
import unittest
from unittest.mock import patch

from app.database import initialize_database
from app.inventory import list_products
from app.ui import InventoryApp


class ImportWindowTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.directory = Path(temp.name)
        self.db = self.directory / 'db.sqlite'
        initialize_database(self.db)
        self.source = self.directory / 'products.csv'
        self.source.write_text('codigo;nombre;precio;stock\n p01 ;Café;10,50;6\n', encoding='utf-8')
        self.root = tk.Tk()
        self.root.withdraw()
        self.addCleanup(self.root.destroy)
        self.app = InventoryApp(self.root, self.db)

    def open_source(self):
        with patch('app.import_ui.filedialog.askopenfilename', return_value=str(self.source)):
            self.app.importer.open_csv()

    def test_open_previews_and_cancel_confirmation_writes_nothing(self):
        self.open_source()
        view = self.app.importer
        self.assertEqual(view.preview.new_count, 1)
        self.assertFalse(view.load_button.instate(['disabled']))
        self.assertEqual(list_products(self.db), [])
        with patch('app.import_ui.messagebox.askyesno', return_value=False):
            view.load_preview()
        self.assertEqual(list_products(self.db), [])
        self.assertEqual(view.preview.new_count, 1)

    def test_cancel_file_picker_preserves_reviewed_preview(self):
        self.open_source()
        before = self.app.importer.preview
        with patch('app.import_ui.filedialog.askopenfilename', return_value=''):
            self.app.importer.open_csv()
        self.assertEqual(self.app.importer.preview, before)

    def test_load_refreshes_inventory_and_charts_then_disables_repeat(self):
        self.open_source()
        with patch('app.import_ui.messagebox.askyesno', return_value=True), patch('app.import_ui.messagebox.showinfo'):
            self.app.importer.load_button.invoke()
            self.app.importer.load_preview()
        self.assertEqual(len(list_products(self.db)), 1)
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.assertEqual(self.app.charts.data.product_count, 1)
        self.assertEqual(self.app.importer.preview.rows[0].status, 'loaded')
        self.assertTrue(self.app.importer.load_button.instate(['disabled']))

    def test_invalid_rows_disable_load_and_do_not_write(self):
        self.source.write_text('codigo;nombre;precio;stock\nP;Mal;0;-1\n', encoding='utf-8')
        self.open_source()
        self.assertEqual(self.app.importer.preview.error_count, 1)
        self.assertTrue(self.app.importer.load_button.instate(['disabled']))
        self.app.importer.load_preview()
        self.assertEqual(list_products(self.db), [])

    def test_invalid_file_after_valid_cannot_load_old_preview(self):
        self.open_source()
        self.source.write_text('archivo inválido', encoding='utf-8')
        with patch('app.import_ui.messagebox.showerror'):
            self.open_source()
        self.assertIsNone(self.app.importer.preview)
        self.assertTrue(self.app.importer.load_button.instate(['disabled']))
        self.assertEqual(self.app.importer.tree.get_children(), ())

    def test_reentrant_confirmation_cannot_load_twice(self):
        self.open_source()
        def confirm(*args, **kwargs):
            self.app.importer.load_preview()
            return True
        with patch('app.import_ui.messagebox.askyesno', side_effect=confirm), patch('app.import_ui.messagebox.showinfo'):
            self.app.importer.load_preview()
        self.assertEqual(len(list_products(self.db)), 1)
        self.assertFalse(self.app.importer._loading)

    def test_postcommit_refresh_error_keeps_loaded_state_and_warns(self):
        self.open_source()
        with patch('app.charts_ui.load_chart_data', side_effect=sqlite3.OperationalError('lectura fallida')), \
             patch('app.import_ui.messagebox.askyesno', return_value=True), \
             patch('app.import_ui.messagebox.showwarning'), patch('app.import_ui.messagebox.showinfo'):
            self.app.importer.load_preview()
        self.assertEqual(len(list_products(self.db)), 1)
        self.assertEqual(self.app.importer.preview.rows[0].status, 'loaded')
        self.assertTrue(self.app.importer.load_button.instate(['disabled']))
        self.assertIn('guardada', self.app.importer.status_var.get())
        self.assertIn('Actualizar', self.app.importer.status_var.get())

    def test_save_template_and_report_cannot_replace_input(self):
        self.open_source()
        before = self.source.read_bytes()
        with patch('app.import_ui.filedialog.asksaveasfilename', return_value=str(self.source)), \
             patch('app.import_ui.messagebox.showerror'):
            self.app.importer.save_template()
            self.app.importer.save_report()
        self.assertEqual(self.source.read_bytes(), before)

    def test_malformed_row_detail_preserves_all_physical_columns_without_mislabeling(self):
        self.source.write_text('stock;nombre;precio;codigo\n2;Producto;1;A;EXTRA\n', encoding='utf-8')
        self.open_source()
        detail = self.app.importer.detail.get('1.0', 'end')
        self.assertIn("columna 1: '2'", detail)
        self.assertIn("columna 5: 'EXTRA'", detail)
        self.assertNotIn("codigo: '2'", detail)


if __name__ == '__main__':
    unittest.main()
