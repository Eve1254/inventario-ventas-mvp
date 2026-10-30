"""CRUD de productos, independiente de la interfaz gráfica."""

from pathlib import Path
import sqlite3

from app.database import DEFAULT_DB_PATH, connect_db
from app.validation import ValidationError, parse_price, parse_stock


def stock_status(stock: int) -> str:
    if stock == 0:
        return "Agotado"
    return "Bajo" if stock < 5 else "Disponible"


def list_products(db_path: Path = DEFAULT_DB_PATH, query: str = "") -> list[sqlite3.Row]:
    """Lee el catálogo y filtra literalmente por código/nombre, con Unicode."""
    with connect_db(db_path) as connection:
        products = connection.execute(
            """
            SELECT id, codigo, nombre, precio, stock
            FROM productos
            ORDER BY nombre COLLATE NOCASE, id
            """
        ).fetchall()
    query = query.strip().casefold()
    return [product for product in products
            if query in product["codigo"].casefold() or query in product["nombre"].casefold()]


def get_product(product_id: int, db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Row | None:
    with connect_db(db_path) as connection:
        return connection.execute("SELECT * FROM productos WHERE id = ?", (product_id,)).fetchone()


def find_product_by_code(code: str, db_path: Path = DEFAULT_DB_PATH) -> sqlite3.Row | None:
    with connect_db(db_path) as connection:
        return connection.execute(
            "SELECT * FROM productos WHERE codigo = ?", (code.strip().upper(),)
        ).fetchone()


def validate_product(code: str, name: str, price_text: str, stock_text: str) -> tuple[str, str, int, int]:
    """Reglas compartidas por formularios e importaciones; no escribe datos."""
    code, name = code.strip().upper(), name.strip()
    if not code:
        raise ValidationError("El código es obligatorio.", "codigo")
    if not name:
        raise ValidationError("El nombre es obligatorio.", "nombre")
    return code, name, parse_price(price_text), parse_stock(stock_text)


def _save_error(error: sqlite3.IntegrityError) -> ValidationError:
    if error.sqlite_errorcode == sqlite3.SQLITE_CONSTRAINT_UNIQUE:
        return ValidationError("Ya existe un producto con ese código.", "codigo")
    return ValidationError("Los datos no cumplen las reglas del inventario.")


def create_product(code: str, name: str, price_text: str, stock_text: str,
                   db_path: Path = DEFAULT_DB_PATH) -> int:
    values = validate_product(code, name, price_text, stock_text)
    try:
        with connect_db(db_path) as connection:
            cursor = connection.execute(
                "INSERT INTO productos (codigo, nombre, precio, stock) VALUES (?, ?, ?, ?)", values
            )
            return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        raise _save_error(error) from error


def update_product(product_id: int, code: str, name: str, price_text: str, stock_text: str,
                   db_path: Path = DEFAULT_DB_PATH, *, expected: sqlite3.Row | None = None) -> None:
    values = validate_product(code, name, price_text, stock_text)
    query = "UPDATE productos SET codigo = ?, nombre = ?, precio = ?, stock = ? WHERE id = ?"
    parameters = (*values, product_id)
    if expected is not None:
        # Comparar y escribir en UNA sentencia evita que un formulario antiguo
        # restaure stock vendido o sobrescriba una edición de otra conexión.
        query += " AND codigo = ? AND nombre = ? AND precio = ? AND stock = ?"
        parameters += tuple(expected[field] for field in ("codigo", "nombre", "precio", "stock"))
    try:
        with connect_db(db_path) as connection:
            cursor = connection.execute(query, parameters)
            if cursor.rowcount == 0:
                if expected is not None and connection.execute("SELECT 1 FROM productos WHERE id = ?", (product_id,)).fetchone():
                    raise ValidationError("El producto cambió desde que abriste el formulario. Cancela y vuelve a abrirlo para revisar los datos actuales.")
                raise ValidationError("El producto ya no existe. Actualiza el inventario.")
    except sqlite3.IntegrityError as error:
        raise _save_error(error) from error


def delete_product(product_id: int, db_path: Path = DEFAULT_DB_PATH) -> None:
    try:
        with connect_db(db_path) as connection:
            cursor = connection.execute("DELETE FROM productos WHERE id = ?", (product_id,))
            if cursor.rowcount == 0:
                raise ValidationError("El producto ya no existe. Actualiza el inventario.")
    except sqlite3.IntegrityError as error:
        raise ValidationError("No se puede eliminar: el producto tiene registros asociados.") from error
