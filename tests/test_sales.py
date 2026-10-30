"""Pruebas de transacciones, migración e historial con SQLite real."""

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import sqlite3
import tempfile
from threading import Barrier
import unittest
from unittest.mock import patch

from app.database import CREATE_PRODUCTS, CREATE_USERS, connect_db, initialize_database
from app.inventory import create_product, delete_product, get_product, update_product
from app.sales import Cart, get_sale_details, list_sales, process_sale
from app.validation import ValidationError


class SaleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "sales.db"
        initialize_database(self.db)
        self.first = create_product("P1", "Café", "10,50", "10", self.db)
        self.second = create_product("P2", "Pan", "0,10", "5", self.db)
        self.cart = Cart(self.db)

    def assert_no_sale(self):
        self.assertEqual(list_sales(self.db), [])
        with connect_db(self.db) as connection:
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM detalle_venta").fetchone()[0], 0)

    def test_additive_migration_preserves_old_schema_data_and_repeated_initialization(self):
        legacy = Path(self.temp.name) / "legacy.db"
        with connect_db(legacy) as connection:
            connection.execute(CREATE_PRODUCTS)
            connection.execute(CREATE_USERS)
            connection.execute("INSERT INTO productos VALUES (7, 'ANT', 'Anterior', 1050, 12)")
            connection.execute("INSERT INTO usuarios VALUES (3, 'usuario', 'hash_de_prueba')")
        initialize_database(legacy)
        initialize_database(legacy)
        self.assertEqual(tuple(get_product(7, legacy)), (7, "ANT", "Anterior", 1050, 12))
        with connect_db(legacy) as connection:
            self.assertEqual(connection.execute("SELECT usuario FROM usuarios").fetchone()[0], "usuario")
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 1)
        self.assertEqual(list_sales(legacy), [])

    def test_newer_schema_is_not_silently_downgraded(self):
        with connect_db(self.db) as connection:
            connection.execute("PRAGMA user_version = 999")
        with self.assertRaises(sqlite3.DatabaseError):
            initialize_database(self.db)
        with connect_db(self.db) as connection:
            self.assertEqual(connection.execute("PRAGMA user_version").fetchone()[0], 999)

    def test_sale_persists_header_lines_and_stock_then_clears_cart(self):
        self.cart.add(self.first, 2)
        self.cart.add(self.second, 3)
        sale_id = process_sale(self.cart)
        sales = list_sales(self.db)
        self.assertEqual(len(sales), 1)
        self.assertEqual((sales[0]["id"], sales[0]["total"]), (sale_id, 2130))
        self.assertIsNotNone(datetime.fromisoformat(sales[0]["fecha"]).utcoffset())
        details = get_sale_details(sale_id, self.db)
        self.assertEqual([(d["cantidad"], d["precio_unitario"], d["subtotal"]) for d in details],
                         [(2, 1050, 2100), (3, 10, 30)])
        self.assertEqual(get_product(self.first, self.db)["stock"], 8)
        self.assertEqual(get_product(self.second, self.db)["stock"], 2)
        self.assertEqual(self.cart.items, ())
        with self.assertRaises(ValidationError):
            process_sale(self.cart)
        self.assertEqual(len(list_sales(self.db)), 1)

    def test_empty_cart_is_rejected(self):
        with self.assertRaises(ValidationError):
            process_sale(self.cart)
        self.assert_no_sale()

    def test_stale_stock_rejects_whole_sale_and_preserves_cart(self):
        self.cart.add(self.first, 2)
        self.cart.add(self.second, 4)
        before = self.cart.items
        update_product(self.second, "P2", "Pan", "0,10", "1", self.db)
        with self.assertRaises(ValidationError):
            process_sale(self.cart)
        self.assert_no_sale()
        self.assertEqual(self.cart.items, before)
        self.assertEqual(get_product(self.first, self.db)["stock"], 10)

    def test_changed_price_or_code_and_deleted_product_reject_sale(self):
        self.cart.add(self.first)
        for code, price in [("P1", "20"), ("OTRO", "10,50")]:
            update_product(self.first, code, "Café", price, "10", self.db)
            with self.subTest(code=code, price=price), self.assertRaises(ValidationError):
                process_sale(self.cart)
            self.assert_no_sale()
            self.assertEqual(self.cart.total_cents, 1050)
        delete_product(self.first, self.db)
        with self.assertRaises(ValidationError):
            process_sale(self.cart)
        self.assert_no_sale()

    def test_failure_on_second_detail_rolls_back_stock_header_and_first_detail(self):
        self.cart.add(self.first, 2)
        self.cart.add(self.second, 3)
        before = self.cart.items
        with connect_db(self.db) as connection:
            connection.execute(f"""CREATE TRIGGER fail_second BEFORE INSERT ON detalle_venta
                WHEN NEW.producto_id = {self.second}
                BEGIN SELECT RAISE(ABORT, 'fallo de prueba en segundo detalle'); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            process_sale(self.cart)
        self.assert_no_sale()
        self.assertEqual(get_product(self.first, self.db)["stock"], 10)
        self.assertEqual(get_product(self.second, self.db)["stock"], 5)
        self.assertEqual(self.cart.items, before)

    def test_commit_failure_also_rolls_back_and_preserves_cart(self):
        self.cart.add(self.first, 2)
        with connect_db(self.db) as connection:
            connection.execute("CREATE TABLE deferred_guard (venta_id INTEGER REFERENCES ventas(id) DEFERRABLE INITIALLY DEFERRED)")
            connection.execute("""CREATE TRIGGER fail_commit AFTER INSERT ON detalle_venta
                BEGIN INSERT INTO deferred_guard VALUES (-1); END""")
        with self.assertRaises(sqlite3.IntegrityError):
            process_sale(self.cart)
        self.assert_no_sale()
        self.assertEqual(get_product(self.first, self.db)["stock"], 10)
        self.assertEqual(self.cart.total_cents, 2100)

    def test_locked_database_is_reported_without_changes(self):
        self.cart.add(self.first)

        @contextmanager
        def impatient_connection(path):
            # Conserva SQLite real, acorta solo la espera para esta prueba.
            with connect_db(path) as connection:
                connection.execute("PRAGMA busy_timeout = 1")
                yield connection

        with connect_db(self.db) as locked:
            locked.execute("BEGIN IMMEDIATE")
            with patch("app.sales.connect_db", impatient_connection), self.assertRaises(ValidationError):
                process_sale(self.cart)
        self.assert_no_sale()
        self.assertEqual(self.cart.total_cents, 1050)
        self.assertEqual(get_product(self.first, self.db)["stock"], 10)

    def test_concurrent_carts_cannot_oversell(self):
        carts = [Cart(self.db), Cart(self.db)]
        for cart in carts:
            cart.add(self.second, 4)
        start = Barrier(2)

        def attempt(cart):
            start.wait(timeout=5)
            try:
                return process_sale(cart)
            except ValidationError:
                return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, carts))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(get_product(self.second, self.db)["stock"], 1)
        self.assertEqual(len(list_sales(self.db)), 1)
        self.assertEqual(sorted(cart.total_units for cart in carts), [0, 4])

    def test_history_keeps_snapshots_and_prevents_product_deletion(self):
        self.cart.add(self.first)
        sale_id = process_sale(self.cart)
        update_product(self.first, "NUEVO", "Nuevo nombre", "99", "9", self.db)
        detail = get_sale_details(sale_id, self.db)[0]
        self.assertEqual((detail["codigo"], detail["nombre"], detail["precio_unitario"]), ("P1", "Café", 1050))
        with self.assertRaises(ValidationError):
            delete_product(self.first, self.db)
        self.assertIsNotNone(get_product(self.first, self.db))

    def test_out_of_range_total_is_rejected_before_writing(self):
        huge = create_product("MAX", "Límite", "92233720368547758.07", "2", self.db)
        self.cart.add(huge, 2)
        with self.assertRaises(ValidationError):
            process_sale(self.cart)
        self.assert_no_sale()
        self.assertEqual(get_product(huge, self.db)["stock"], 2)


if __name__ == "__main__":
    unittest.main()
