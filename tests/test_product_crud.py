"""Reglas del CRUD sobre bases temporales reales."""

from pathlib import Path
import tempfile
import unittest

from app.database import connect_db, initialize_database
from app.inventory import (create_product, delete_product, find_product_by_code,
                           get_product, list_products, update_product)
from app.validation import ValidationError, parse_price, parse_quantity, parse_stock, price_to_input


class ValidationTests(unittest.TestCase):
    def test_decimal_input_is_exact_and_has_no_thousands_separator(self):
        for text, cents in [("0,10", 10), ("10.50", 1050), (" 8500,5 ", 850050),
                            ("12", 1200), ("92233720368547758.07", 9223372036854775807)]:
            with self.subTest(text=text):
                self.assertEqual(parse_price(text), cents)
        self.assertEqual(price_to_input(850050), "8500,50")

    def test_rejects_invalid_prices(self):
        for text in ["", "0", "-1", "1.234", "1,000.00", "NaN", "Infinity", "1e3",
                     "92233720368547758.08", "9" * 100, "hola"]:
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_price(text)

    def test_stock_and_cart_quantity_have_different_zero_rules(self):
        self.assertEqual(parse_stock(" 0 "), 0)
        self.assertEqual(parse_stock("0012"), 12)
        self.assertEqual(parse_quantity("2"), 2)
        for text in ["", "-1", "1.5", "1,5", "1e2", "NaN", "9223372036854775808"]:
            with self.subTest(text=text), self.assertRaises(ValidationError):
                parse_stock(text)
        with self.assertRaises(ValidationError):
            parse_quantity("0")


class ProductCrudTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "inventory.db"
        initialize_database(self.db)

    def create(self, code="P001", name="Café", price="10,50", stock="5"):
        return create_product(code, name, price, stock, self.db)

    def test_create_normalizes_and_persists_all_fields(self):
        product_id = self.create(" p001 ", " Café molido ", "10.50", "12")
        row = get_product(product_id, self.db)
        self.assertEqual(tuple(row), (product_id, "P001", "Café molido", 1050, 12))
        self.assertEqual(find_product_by_code(" p001 ", self.db)["id"], product_id)

    def test_invalid_input_does_not_create_a_product(self):
        for values in [(" ", "Café", "1", "0"), ("P1", "\t", "1", "0"),
                       ("P1", "Café", "-1", "0"), ("P1", "Café", "1", "-1")]:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                create_product(*values, self.db)
        self.assertEqual(list_products(self.db), [])

    def test_duplicate_code_is_rejected_after_normalization(self):
        self.create()
        with self.assertRaises(ValidationError) as caught:
            self.create(" p001 ")
        self.assertEqual(caught.exception.field, "codigo")
        self.assertEqual(len(list_products(self.db)), 1)

    def test_update_changes_only_selected_product_and_duplicate_rolls_back(self):
        first = self.create()
        second = self.create("P002", "Arroz")
        update_product(first, "P003", "Café nuevo", "20,01", "0", self.db)
        self.assertEqual(tuple(get_product(first, self.db)), (first, "P003", "Café nuevo", 2001, 0))
        with self.assertRaises(ValidationError):
            update_product(first, "p002", "Cambio inválido", "100", "9", self.db)
        self.assertEqual(get_product(first, self.db)["nombre"], "Café nuevo")
        self.assertEqual(get_product(second, self.db)["nombre"], "Arroz")

    def test_delete_removes_only_selected_product_and_missing_id_is_reported(self):
        first = self.create()
        second = self.create("P002")
        delete_product(first, self.db)
        self.assertIsNone(get_product(first, self.db))
        self.assertIsNotNone(get_product(second, self.db))
        with self.assertRaises(ValidationError):
            delete_product(first, self.db)
        with self.assertRaises(ValidationError):
            update_product(first, "P003", "Ausente", "1", "1", self.db)

    def test_reference_prevents_deletion(self):
        product_id = self.create()
        with connect_db(self.db) as connection:
            # Anticipa la restricción que tendrá detalle_venta en el Día 3.
            connection.execute("CREATE TABLE referencia (producto_id INTEGER REFERENCES productos(id))")
            connection.execute("INSERT INTO referencia VALUES (?)", (product_id,))
        with self.assertRaises(ValidationError):
            delete_product(product_id, self.db)
        self.assertIsNotNone(get_product(product_id, self.db))

    def test_search_is_literal_case_insensitive_and_keeps_sql_as_data(self):
        self.create(name="Café 100% 'especial'")
        malicious = "Arroz'); DROP TABLE productos; --"
        self.create("P002", malicious)
        self.assertEqual(len(list_products(self.db, "CAFÉ")), 1)
        self.assertEqual(len(list_products(self.db, "%")), 1)
        self.assertEqual(list_products(self.db, "no existe"), [])
        self.assertEqual(find_product_by_code("p002", self.db)["nombre"], malicious)
        self.assertEqual(len(list_products(self.db)), 2)


if __name__ == "__main__":
    unittest.main()
