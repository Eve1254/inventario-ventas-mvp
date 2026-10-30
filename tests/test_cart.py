"""El carrito calcula y valida; nunca descuenta stock."""

from pathlib import Path
import tempfile
import unittest

from app.database import initialize_database
from app.inventory import create_product, delete_product, get_product, update_product
from app.sales import Cart
from app.validation import ValidationError


class CartTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db = Path(self.temp.name) / "cart.db"
        initialize_database(self.db)
        self.product_id = create_product("P1", "Prueba", "0,10", "5", self.db)
        self.cart = Cart(self.db)

    def test_repeated_product_merges_and_money_is_exact_without_changing_stock(self):
        self.assertEqual(self.cart.total_cents, 0)
        self.cart.add(self.product_id)
        self.cart.add(self.product_id, 2)
        self.assertEqual(len(self.cart.items), 1)
        self.assertEqual(self.cart.items[0].quantity, 3)
        self.assertEqual(self.cart.items[0].subtotal, 30)
        self.assertEqual(self.cart.total_cents, 30)
        self.assertEqual(get_product(self.product_id, self.db)["stock"], 5)

    def test_update_remove_and_clear_recalculate_total(self):
        second = create_product("P2", "Segundo", "10,50", "10", self.db)
        self.cart.add(self.product_id, 2)
        self.cart.add(second, 2)
        self.assertEqual(self.cart.total_cents, 2120)
        self.cart.set_quantity(second, 3)
        self.assertEqual(self.cart.total_cents, 3170)
        self.assertEqual(self.cart.total_units, 5)
        self.cart.remove(self.product_id)
        self.assertEqual(self.cart.total_cents, 3150)
        self.cart.clear()
        self.assertEqual(self.cart.items, ())
        self.assertEqual(self.cart.total_cents, 0)

    def test_rejects_accumulated_stock_excess_without_changing_cart(self):
        self.cart.add(self.product_id, 4)
        before = self.cart.items
        with self.assertRaises(ValidationError):
            self.cart.add(self.product_id, 2)
        self.assertEqual(self.cart.items, before)
        with self.assertRaises(ValidationError):
            self.cart.set_quantity(self.product_id, 6)
        self.assertEqual(self.cart.items, before)

    def test_rejects_invalid_quantities_and_zero_stock(self):
        for quantity in [0, -1, 1.5, True, "2", 9223372036854775808]:
            with self.subTest(quantity=quantity), self.assertRaises(ValidationError):
                self.cart.add(self.product_id, quantity)
        update_product(self.product_id, "P1", "Prueba", "0,10", "0", self.db)
        with self.assertRaises(ValidationError):
            self.cart.add(self.product_id)
        self.assertEqual(self.cart.items, ())

    def test_rechecks_stock_and_allows_reducing_quantity_to_available_stock(self):
        self.cart.add(self.product_id, 4)
        update_product(self.product_id, "P1", "Prueba", "0,10", "2", self.db)
        with self.assertRaises(ValidationError):
            self.cart.add(self.product_id)
        self.cart.set_quantity(self.product_id, 2)
        self.assertEqual(self.cart.total_cents, 20)

    def test_changed_price_requires_removal_before_readding(self):
        self.cart.add(self.product_id)
        update_product(self.product_id, "P1", "Prueba", "0,20", "5", self.db)
        with self.assertRaises(ValidationError):
            self.cart.add(self.product_id)
        with self.assertRaises(ValidationError):
            self.cart.set_quantity(self.product_id, 2)
        self.assertEqual(self.cart.total_cents, 10)
        self.cart.remove(self.product_id)
        self.cart.add(self.product_id)
        self.assertEqual(self.cart.total_cents, 20)

    def test_deleted_product_and_missing_cart_lines_are_reported(self):
        self.cart.add(self.product_id)
        delete_product(self.product_id, self.db)
        with self.assertRaises(ValidationError):
            self.cart.add(self.product_id)
        self.assertEqual(self.cart.total_cents, 10)
        self.cart.remove(self.product_id)
        with self.assertRaises(ValidationError):
            self.cart.set_quantity(self.product_id, 1)
        with self.assertRaises(ValidationError):
            self.cart.remove(self.product_id)


if __name__ == "__main__":
    unittest.main()
