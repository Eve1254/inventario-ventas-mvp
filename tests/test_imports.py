"""ETL real con archivos y SQLite temporales; el catálogo no se sobrescribe."""

import csv
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from app.database import connect_db, initialize_database
from app.imports import preview_import, load_import, export_import_report, write_product_template
from app.inventory import create_product, get_product, list_products
from app.sales import Cart, process_sale
from app.validation import ValidationError


class ImportTests(unittest.TestCase):
    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.folder = Path(temp.name)
        self.db = self.folder / "inventory.db"
        initialize_database(self.db)
        self.source = self.folder / "products.csv"

    def source_text(self, text, encoding="utf-8-sig"):
        self.source.write_text(text, encoding=encoding, newline="")
        return preview_import(self.source, self.db)

    def test_preview_normalizes_reordered_headers_without_writing(self):
        preview = self.source_text(' Stock ;NOMBRE;Precio;codigo\n006; Café ;10.50; p001 \n')
        self.assertEqual(preview.rows[0].values, ("P001", "Café", 1050, 6))
        self.assertEqual(preview.rows[0].line, 2)
        self.assertEqual(preview.new_count, 1)
        self.assertEqual(list_products(self.db), [])

    def test_invalid_rows_and_all_normalized_duplicates_block_the_batch(self):
        preview = self.source_text('codigo;nombre;precio;stock\np1;Uno;1;2\n P1 ;Otro;2;3\nP2;Dos;0;2\nP3;Tres;3;-1\nP4;Cuatro;4;5\n')
        self.assertEqual([row.status for row in preview.rows], ["error", "error", "error", "error", "new"])
        self.assertEqual(preview.error_count, 4)
        with self.assertRaises(ValidationError):
            load_import(preview, self.db)
        self.assertEqual(list_products(self.db), [])

    def test_row_width_errors_are_reported_and_blank_physical_lines_ignored(self):
        preview = self.source_text('codigo;nombre;precio;stock\n\nA;A;1\nB;B;1;2;extra\nC;C;2;3\n')
        self.assertEqual([row.line for row in preview.rows], [3, 4, 5])
        self.assertEqual([row.status for row in preview.rows], ["error", "error", "new"])

    def test_quotes_semicolons_multiline_and_initial_zeros_are_preserved(self):
        preview = self.source_text('codigo;nombre;precio;stock\n001;"Café; edición\nespecial";0,10;3\n002;Pan;1;2\n', encoding="utf-8")
        self.assertEqual(preview.rows[0].values, ("001", "Café; edición\nespecial", 10, 3))
        self.assertEqual(preview.rows[1].line, 4)

    def test_bad_file_structure_encoding_and_limits_reject_without_writes(self):
        for text in ('', 'codigo,nombre,precio,stock\n', 'codigo;codigo;precio;stock\n',
                     'codigo;nombre;precio;stock\nA;"sin cerrar;1;1'):
            with self.subTest(text=text), self.assertRaises(ValidationError):
                self.source_text(text)
        self.source.write_bytes(b'codigo;nombre;precio;stock\nA;Caf\xe9;1;1')
        with self.assertRaises(ValidationError):
            preview_import(self.source, self.db)
        self.source.write_bytes(b'x' * (2 * 1024 * 1024 + 1))
        with self.assertRaises(ValidationError):
            preview_import(self.source, self.db)
        with self.assertRaises(ValidationError):
            self.source_text('codigo;nombre;precio;stock\n' + '\n'.join(f'P{i};P;1;1' for i in range(2001)))
        self.assertEqual(list_products(self.db), [])

    def test_header_only_has_no_loadable_products(self):
        preview = self.source_text('codigo;nombre;precio;stock\n')
        self.assertEqual(preview.rows, ())
        with self.assertRaises(ValidationError):
            load_import(preview, self.db)

    def test_existing_codes_are_skipped_and_repeat_never_restores_sold_stock(self):
        preview = self.source_text('codigo;nombre;precio;stock\nA;Original;10,50;6\n')
        self.assertEqual(load_import(preview, self.db), 1)
        product = list_products(self.db)[0]
        cart = Cart(self.db)
        cart.add(product['id'], 3)
        process_sale(cart)
        repeat = self.source_text('codigo;nombre;precio;stock\na;Otro nombre;99;600\nB;Nuevo;1;1\n')
        self.assertEqual([row.status for row in repeat.rows], ['existing', 'new'])
        self.assertEqual(load_import(repeat, self.db), 1)
        stored = get_product(product['id'], self.db)
        self.assertEqual((stored['nombre'], stored['precio'], stored['stock']), ('Original', 1050, 3))
        self.assertEqual(preview_import(self.source, self.db).new_count, 0)

    def test_loading_uses_reviewed_snapshot_even_if_source_is_changed(self):
        preview = self.source_text('codigo;nombre;precio;stock\nA;Revisado;1,25;2\n')
        self.source.write_text('archivo cambiado', encoding='utf-8')
        load_import(preview, self.db)
        self.assertEqual(list_products(self.db)[0]['nombre'], 'Revisado')

    def test_new_code_inserted_after_preview_rejects_all_without_overwriting(self):
        preview = self.source_text('codigo;nombre;precio;stock\nA;A;1;1\nB;B;2;2\n')
        create_product('B', 'Otra ventana', '9', '9', self.db)
        with self.assertRaises(ValidationError):
            load_import(preview, self.db)
        self.assertEqual([(p['codigo'], p['stock']) for p in list_products(self.db)], [('B', 9)])

    def test_second_insert_failure_rolls_back_first_product(self):
        preview = self.source_text('codigo;nombre;precio;stock\nA;A;1;1\nB;B;2;2\n')
        with connect_db(self.db) as connection:
            connection.execute("CREATE TRIGGER reject_b BEFORE INSERT ON productos WHEN NEW.codigo='B' BEGIN SELECT RAISE(ABORT, 'fallo segundo'); END")
        with self.assertRaises(sqlite3.IntegrityError):
            load_import(preview, self.db)
        self.assertEqual(list_products(self.db), [])

    def test_locked_database_does_not_load_any_product(self):
        preview = self.source_text('codigo;nombre;precio;stock\nA;A;1;1\n')
        with connect_db(self.db) as other:
            other.execute('BEGIN IMMEDIATE')
            original = sqlite3.connect
            def quick(*args, **kwargs):
                kwargs['timeout'] = 0.001
                return original(*args, **kwargs)
            with patch('app.database.sqlite3.connect', side_effect=quick), self.assertRaises(ValidationError):
                load_import(preview, self.db)
        self.assertEqual(list_products(self.db), [])

    def test_report_is_safe_and_protects_source_database_and_existing_target(self):
        preview = self.source_text('codigo;nombre;precio;stock\n=A;=1+1;1;2\n')
        target = self.folder / 'report.csv'
        self.assertEqual(export_import_report(preview, target, self.db), 1)
        with target.open(encoding='utf-8-sig', newline='') as stream:
            row = next(csv.DictReader(stream, delimiter=';'))
        self.assertEqual(row['codigo_normalizado'], "'=A")
        self.assertEqual(row['nombre_normalizado'], "'=1+1")
        for destination in (self.db, self.source, Path(str(self.db) + '-wal')):
            with self.subTest(destination=destination), self.assertRaises(ValidationError):
                export_import_report(preview, destination, self.db)
        before = target.read_bytes()
        with patch('app.exports.os.replace', side_effect=PermissionError('ocupado')), self.assertRaises(PermissionError):
            export_import_report(preview, target, self.db)
        self.assertEqual(target.read_bytes(), before)

    def test_template_is_compatible_and_cannot_replace_database(self):
        template = self.folder / 'template.csv'
        write_product_template(template, self.db)
        self.assertEqual(preview_import(template, self.db).rows, ())
        with self.assertRaises(ValidationError):
            write_product_template(self.db, self.db)


if __name__ == '__main__':
    unittest.main()
