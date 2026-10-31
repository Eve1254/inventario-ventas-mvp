"""Conexión y actualización aditiva del esquema local."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
import sqlite3

from app.paths import get_database_path


DEFAULT_DB_PATH = get_database_path()
SCHEMA_VERSION = 1

CREATE_PRODUCTS = """
CREATE TABLE IF NOT EXISTS productos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE
        CHECK (length(trim(codigo)) > 0 AND codigo = trim(codigo)),
    nombre TEXT NOT NULL
        CHECK (length(trim(nombre)) > 0 AND nombre = trim(nombre)),
    precio INTEGER NOT NULL
        CHECK (typeof(precio) = 'integer' AND precio > 0),
    stock INTEGER NOT NULL DEFAULT 0
        CHECK (typeof(stock) = 'integer' AND stock >= 0)
)
"""

CREATE_USERS = """
CREATE TABLE IF NOT EXISTS usuarios (
    id INTEGER PRIMARY KEY,
    usuario TEXT NOT NULL UNIQUE
        CHECK (length(trim(usuario)) > 0 AND usuario = trim(usuario)),
    password TEXT NOT NULL CHECK (length(password) > 0)
)
"""
# La tabla usuarios queda vacía. Cuando se implemente acceso, password
# guardará un hash con sal, nunca una contraseña en texto plano.

CREATE_SALES = """
CREATE TABLE IF NOT EXISTS ventas (
    id INTEGER PRIMARY KEY,
    fecha TEXT NOT NULL,
    total INTEGER NOT NULL CHECK (typeof(total) = 'integer' AND total > 0)
)
"""

CREATE_SALE_DETAILS = """
CREATE TABLE IF NOT EXISTS detalle_venta (
    id INTEGER PRIMARY KEY,
    venta_id INTEGER NOT NULL REFERENCES ventas(id) ON DELETE RESTRICT,
    producto_id INTEGER NOT NULL REFERENCES productos(id) ON DELETE RESTRICT,
    codigo TEXT NOT NULL,
    nombre TEXT NOT NULL,
    cantidad INTEGER NOT NULL CHECK (typeof(cantidad) = 'integer' AND cantidad > 0),
    precio_unitario INTEGER NOT NULL CHECK (typeof(precio_unitario) = 'integer' AND precio_unitario > 0),
    subtotal INTEGER NOT NULL CHECK (typeof(subtotal) = 'integer' AND subtotal > 0),
    CHECK (subtotal = precio_unitario * cantidad),
    UNIQUE (venta_id, producto_id)
)
"""


@contextmanager
def connect_db(db_path: Path = DEFAULT_DB_PATH) -> Iterator[sqlite3.Connection]:
    """Entrega una conexión, confirma o revierte cambios y siempre la cierra."""
    connection = sqlite3.connect(db_path, timeout=5.0, isolation_level="DEFERRED")
    try:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        # El contexto de sqlite3 confirma si todo salió bien y revierte si falló.
        with connection:
            yield connection
    finally:
        # El contexto de sqlite3 NO cierra la conexión; por eso lo hacemos aquí.
        connection.close()


def initialize_database(db_path: Path = DEFAULT_DB_PATH) -> None:
    """Crea la carpeta y las tablas sin borrar información existente."""
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with connect_db(db_path) as connection:
        # El esquema anterior tenía user_version=0. Se añaden tablas, no se
        # reconstruyen ni se borran productos/usuarios existentes.
        connection.execute("BEGIN")
        version = connection.execute("PRAGMA user_version").fetchone()[0]
        if version > SCHEMA_VERSION:
            raise sqlite3.DatabaseError("La base pertenece a una versión más reciente de la aplicación.")
        connection.execute(CREATE_PRODUCTS)
        connection.execute(CREATE_USERS)
        connection.execute(CREATE_SALES)
        connection.execute(CREATE_SALE_DETAILS)
        connection.execute("CREATE INDEX IF NOT EXISTS idx_detalle_producto ON detalle_venta(producto_id)")
        connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
