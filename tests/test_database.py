"""Comprueba persistencia e integridad con SQLite real."""

import os
from pathlib import Path
import sqlite3
import tempfile
import unittest

from app.database import DEFAULT_DB_PATH, connect_db, initialize_database


class DatabaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.db_path = Path(self.temp.name) / "datos" / "inventario.db"
        initialize_database(self.db_path)

    def test_creates_required_tables_without_automatic_data(self):
        with connect_db(self.db_path) as connection:
            tables = {
                row["name"] for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                )
            }
            self.assertTrue({"productos", "usuarios"}.issubset(tables))
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM productos").fetchone()[0], 0)
            self.assertEqual(connection.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0], 0)
            self.assertEqual(connection.execute("PRAGMA foreign_keys").fetchone()[0], 1)

    def test_reinitializing_preserves_committed_products(self):
        with connect_db(self.db_path) as connection:
            connection.execute(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                ("CAFE-01", "Café", 1050, 10),
            )
        initialize_database(self.db_path)
        with connect_db(self.db_path) as connection:
            row = connection.execute("SELECT * FROM productos").fetchone()
            self.assertEqual((row["codigo"], row["nombre"], row["precio"], row["stock"]),
                             ("CAFE-01", "Café", 1050, 10))

    def test_rejects_duplicate_product_codes(self):
        with connect_db(self.db_path) as connection:
            connection.execute(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                ("P001", "Arroz", 3000, 10),
            )
        with self.assertRaises(sqlite3.IntegrityError), connect_db(self.db_path) as connection:
            connection.execute(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                ("P001", "Otro arroz", 4000, 3),
            )

    def test_rejects_invalid_product_fields(self):
        invalid_rows = [
            ("", "Arroz", 100, 1),
            ("   ", "Arroz", 100, 1),
            (" P1 ", "Arroz", 100, 1),
            ("P1", "", 100, 1),
            ("P1", "   ", 100, 1),
            ("P1", "Arroz", 0, 1),
            ("P1", "Arroz", -1, 1),
            ("P1", "Arroz", 10.5, 1),
            ("P1", "Arroz", "caro", 1),
            ("P1", "Arroz", 100, -1),
            ("P1", "Arroz", 100, 1.5),
            ("P1", "Arroz", 100, "muchos"),
            (None, "Arroz", 100, 1),
            ("P1", None, 100, 1),
            ("P1", "Arroz", None, 1),
            ("P1", "Arroz", 100, None),
        ]
        for values in invalid_rows:
            with self.subTest(values=values):
                with self.assertRaises(sqlite3.IntegrityError), connect_db(self.db_path) as connection:
                    connection.execute(
                        "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                        values,
                    )

    def test_zero_stock_is_valid(self):
        with connect_db(self.db_path) as connection:
            connection.execute(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                ("P0", "Agotado", 1, 0),
            )
        with connect_db(self.db_path) as connection:
            self.assertEqual(connection.execute("SELECT stock FROM productos").fetchone()[0], 0)

    def test_user_name_is_unique_and_required(self):
        with connect_db(self.db_path) as connection:
            connection.execute(
                "INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                ("prueba", "hash_ficticio_solo_para_prueba"),
            )
        for username, password in [("prueba", "otro_hash"), ("", "hash"), ("   ", "hash"), ("otro", "")]:
            with self.subTest(username=username):
                with self.assertRaises(sqlite3.IntegrityError), connect_db(self.db_path) as connection:
                    connection.execute(
                        "INSERT INTO usuarios (usuario, password) VALUES (?, ?)",
                        (username, password),
                    )

    def test_failure_rolls_back_and_closes_connection(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with connect_db(self.db_path) as connection:
                connection.execute(
                    "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                    ("P1", "Primero", 100, 1),
                )
                connection.execute(
                    "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)",
                    ("P1", "Duplicado", 200, 2),
                )
        with self.assertRaises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")
        with connect_db(self.db_path) as reopened:
            self.assertEqual(reopened.execute("SELECT COUNT(*) FROM productos").fetchone()[0], 0)

    def test_default_path_is_relative_to_project(self):
        previous = Path.cwd()
        try:
            os.chdir(self.temp.name)
            expected = Path(__file__).resolve().parents[1] / "data" / "inventario.db"
            self.assertEqual(DEFAULT_DB_PATH, expected)
            self.assertTrue(DEFAULT_DB_PATH.is_absolute())
        finally:
            os.chdir(previous)


if __name__ == "__main__":
    unittest.main()
