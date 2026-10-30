"""Carga opcional: ejecutar desde la raíz con python -m app.demo."""

from pathlib import Path
import sqlite3
import sys

from app.database import DEFAULT_DB_PATH, connect_db, initialize_database


# Precio en centavos: 850000 representa 8.500,00 en la pantalla.
DEMO_PRODUCTS = (
    ("P001", "Café molido 250 g", 850000, 12),
    ("P002", "Arroz 1 kg", 420000, 20),
    ("P003", "Aceite 1 L", 1250000, 8),
    ("P004", "Leche 1 L", 380000, 4),
    ("P005", "Pan integral", 650000, 0),
)


def seed_demo_products(db_path: Path = DEFAULT_DB_PATH) -> int:
    """Agrega ejemplos sin duplicar códigos ni sobrescribir productos."""
    initialize_database(db_path)
    with connect_db(db_path) as connection:
        cursor = connection.executemany(
            """
            INSERT INTO productos (codigo, nombre, precio, stock)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(codigo) DO NOTHING
            """,
            DEMO_PRODUCTS,
        )
        return cursor.rowcount


if __name__ == "__main__":
    try:
        inserted = seed_demo_products()
    except (sqlite3.Error, OSError) as error:
        print(f"No se pudieron cargar los ejemplos: {error}", file=sys.stderr)
        raise SystemExit(1)
    print(f"Productos de ejemplo agregados: {inserted}")
    print(f"Base de datos: {DEFAULT_DB_PATH}")
