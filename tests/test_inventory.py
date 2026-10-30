"""Pruebas de consulta y datos de ejemplo sin tocar la base del usuario."""

from pathlib import Path
import tempfile
import unittest

from app.database import connect_db, initialize_database
from app.demo import seed_demo_products
from app.inventory import list_products


class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "inventario.db"
        initialize_database(self.db_path)

    def test_empty_inventory(self):
        self.assertEqual(list_products(self.db_path), [])

    def test_reads_committed_products_sorted_with_accents(self):
        with connect_db(self.db_path) as connection:
            connection.executemany(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                [("P2", "Café", 1050, 4), ("P1", "Arroz", 2000, 12)],
            )
        rows = list_products(self.db_path)
        self.assertEqual([row["nombre"] for row in rows], ["Arroz", "Café"])
        self.assertEqual((rows[1]["codigo"], rows[1]["precio"], rows[1]["stock"]), ("P2", 1050, 4))

    def test_demo_load_does_not_duplicate_or_overwrite_existing_products(self):
        self.assertEqual(seed_demo_products(self.db_path), 5)
        with connect_db(self.db_path) as connection:
            connection.execute(
                "UPDATE productos SET nombre = ?, precio = ?, stock = ? WHERE codigo = ?",
                ("Café editado", 777, 2, "P001"),
            )
        self.assertEqual(seed_demo_products(self.db_path), 0)
        rows = list_products(self.db_path)
        self.assertEqual(len(rows), 5)
        edited = next(row for row in rows if row["codigo"] == "P001")
        self.assertEqual((edited["nombre"], edited["precio"], edited["stock"]), ("Café editado", 777, 2))


if __name__ == "__main__":
    unittest.main()
