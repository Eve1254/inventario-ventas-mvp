"""CSV de datos confirmados, con archivos y bases temporales."""

import csv
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from app.database import connect_db, initialize_database
from app.exports import export_inventory, export_sales
from app.inventory import create_product, update_product
from app.sales import Cart, process_sale
from app.validation import ValidationError


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.db = self.directory / "inventory.db"
        initialize_database(self.db)

    def read(self, path):
        return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8-sig")), delimiter=";"))

    def test_empty_exports_still_have_headers(self):
        for exporter, filename, expected in [(export_inventory, "inventory.csv", "codigo;nombre;precio;stock"),
                                             (export_sales, "sales.csv", "venta_id;fecha;codigo;nombre;cantidad;precio_unitario;subtotal")]:
            with self.subTest(filename=filename):
                path = self.directory / filename
                self.assertEqual(exporter(path, self.db), 0)
                self.assertTrue(path.read_bytes().startswith(b"\xef\xbb\xbf"))
                self.assertEqual(path.read_text(encoding="utf-8-sig").strip(), expected)
                self.assertEqual(self.read(path), [])

    def test_inventory_preserves_accents_quotes_delimiters_and_exact_prices(self):
        name = 'Café; "especial", edición'
        create_product("P001", name, "8500,50", "4", self.db)
        path = self.directory / "inventory.csv"
        self.assertEqual(export_inventory(path, self.db), 1)
        self.assertEqual(self.read(path), [{"codigo": "P001", "nombre": name, "precio": "8500,50", "stock": "4"}])

    def test_formula_like_text_is_neutralized(self):
        for index, name in enumerate(["=1+1", "+SUM(1)", "-2+3", "@SUM(1)"]):
            create_product(f"=P{index}", name, "1", "1", self.db)
        # Datos anteriores importados por otro script pueden contener controles.
        with connect_db(self.db) as connection:
            connection.execute("INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                               ("=CONTROL", "\t =1+1", 100, 1))
        path = self.directory / "safe.csv"
        export_inventory(path, self.db)
        for row in self.read(path):
            self.assertTrue(row["codigo"].startswith("'="))
            self.assertTrue(row["nombre"].startswith("'"))

    def test_sales_export_uses_snapshots_without_repeating_header_total(self):
        first = create_product("P1", "Café", "10,50", "5", self.db)
        second = create_product("P2", "Pan", "0,10", "5", self.db)
        cart = Cart(self.db)
        cart.add(first, 2)
        cart.add(second, 3)
        sale_id = process_sale(cart)
        update_product(first, "NUEVO", "Otro nombre", "99", "3", self.db)
        path = self.directory / "sales.csv"
        self.assertEqual(export_sales(path, self.db), 2)
        rows = self.read(path)
        self.assertEqual(rows[0]["venta_id"], str(sale_id))
        self.assertEqual((rows[0]["codigo"], rows[0]["nombre"], rows[0]["precio_unitario"]), ("P1", "Café", "10,50"))
        self.assertEqual([row["subtotal"] for row in rows], ["21,00", "0,30"])
        self.assertNotIn("total", rows[0])

    def test_cannot_export_over_database_or_its_sidecars(self):
        original = self.db.read_bytes()
        for path in [self.db, Path(str(self.db) + "-wal"), Path(str(self.db) + "-shm"), Path(str(self.db) + "-journal")]:
            with self.subTest(path=path), self.assertRaises(ValidationError):
                export_inventory(path, self.db)
        self.assertEqual(self.db.read_bytes(), original)

    def test_cannot_export_over_hardlink_to_database(self):
        alias = self.directory / "alias.csv"
        os.link(self.db, alias)
        with self.assertRaises(ValidationError):
            export_sales(alias, self.db)
        self.assertEqual(alias.read_bytes(), self.db.read_bytes())

    def test_failed_replacement_preserves_existing_file_and_removes_temporary(self):
        target = self.directory / "previous.csv"
        target.write_text("contenido anterior", encoding="utf-8")
        original_files = set(self.directory.iterdir())
        with patch("app.exports.os.replace", side_effect=PermissionError("archivo ocupado")):
            with self.assertRaises(PermissionError):
                export_inventory(target, self.db)
        self.assertEqual(target.read_text(encoding="utf-8"), "contenido anterior")
        self.assertEqual(set(self.directory.iterdir()), original_files)

    def test_missing_destination_directory_is_reported(self):
        with self.assertRaises(OSError):
            export_inventory(self.directory / "missing" / "out.csv", self.db)


if __name__ == "__main__":
    unittest.main()
