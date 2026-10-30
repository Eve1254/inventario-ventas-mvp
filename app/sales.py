"""Carrito, confirmación transaccional y consulta de ventas."""

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from app.database import DEFAULT_DB_PATH, connect_db
from app.inventory import get_product
from app.validation import MAX_SQLITE_INTEGER, ValidationError


@dataclass(frozen=True)
class CartItem:
    product_id: int
    code: str
    name: str
    unit_price: int
    quantity: int

    @property
    def subtotal(self) -> int:
        return self.unit_price * self.quantity


class Cart:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self._items: dict[int, CartItem] = {}

    @property
    def items(self) -> tuple[CartItem, ...]:
        # No exponemos un diccionario mutable que pueda saltarse las reglas.
        return tuple(self._items.values())

    @property
    def total_cents(self) -> int:
        return sum(item.subtotal for item in self._items.values())

    @property
    def total_units(self) -> int:
        return sum(item.quantity for item in self._items.values())

    @staticmethod
    def _validate_quantity(quantity: int) -> None:
        if type(quantity) is not int or not 1 <= quantity <= MAX_SQLITE_INTEGER:
            raise ValidationError("La cantidad debe ser un entero positivo dentro del rango permitido.", "cantidad")

    def _checked_item(self, product_id: int, quantity: int) -> CartItem:
        self._validate_quantity(quantity)
        product = get_product(product_id, self.db_path)
        if product is None:
            raise ValidationError("El producto ya no existe. Quítalo del carrito y actualiza la búsqueda.")
        previous = self._items.get(product_id)
        if previous and (previous.unit_price != product["precio"] or previous.code != product["codigo"]):
            raise ValidationError("El precio o código cambió. Quita el producto y vuelve a agregarlo para revisar el total.")
        if quantity > product["stock"]:
            raise ValidationError(f"Stock insuficiente para {product['nombre']}. Disponibles: {product['stock']}.", "cantidad")
        return CartItem(product_id, product["codigo"], product["nombre"], product["precio"], quantity)

    def add(self, product_id: int, quantity: int = 1) -> None:
        self._validate_quantity(quantity)
        previous = self._items.get(product_id)
        accumulated = quantity + (previous.quantity if previous else 0)
        item = self._checked_item(product_id, accumulated)
        self._items[product_id] = item

    def set_quantity(self, product_id: int, quantity: int) -> None:
        if product_id not in self._items:
            raise ValidationError("Selecciona un producto del carrito.")
        item = self._checked_item(product_id, quantity)
        self._items[product_id] = item

    def remove(self, product_id: int) -> None:
        if product_id not in self._items:
            raise ValidationError("El producto ya no está en el carrito.")
        del self._items[product_id]

    def clear(self) -> None:
        self._items.clear()


def process_sale(cart: Cart) -> int:
    """Guarda venta y stock juntos; conserva el carrito si falla incluso el commit."""
    items = cart.items  # Instantánea inmutable, ya agrupada por ID por Cart.
    if not items:
        raise ValidationError("Agrega al menos un producto antes de procesar la venta.")
    for item in items:
        Cart._validate_quantity(item.quantity)
        if type(item.unit_price) is not int or not 1 <= item.unit_price <= MAX_SQLITE_INTEGER:
            raise ValidationError("El carrito contiene un precio inválido. Vuelve a agregar el producto.")
    total = sum(item.subtotal for item in items)
    if total > MAX_SQLITE_INTEGER:
        raise ValidationError("El total de la venta supera el valor máximo permitido.")

    try:
        with connect_db(cart.db_path) as connection:
            # Reservamos la escritura ANTES de consultar stock. Otra venta
            # debe esperar y después leerá las existencias ya actualizadas.
            connection.execute("BEGIN IMMEDIATE")
            checked = []
            for item in items:
                product = connection.execute("SELECT * FROM productos WHERE id = ?", (item.product_id,)).fetchone()
                if product is None:
                    raise ValidationError(f"El producto {item.code} ya no existe. Quítalo del carrito.")
                if product["precio"] != item.unit_price or product["codigo"] != item.code:
                    raise ValidationError(f"El precio o código de {item.name} cambió. Quita y vuelve a agregar el producto para revisar el total.")
                if product["stock"] < item.quantity:
                    raise ValidationError(f"Stock insuficiente para {product['nombre']}. Disponibles: {product['stock']}.")
                checked.append((item, product))

            timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
            sale_id = connection.execute("INSERT INTO ventas (fecha, total) VALUES (?, ?)",
                                         (timestamp, total)).lastrowid
            for item, product in checked:
                updated = connection.execute(
                    "UPDATE productos SET stock = stock - ? WHERE id = ? AND stock >= ?",
                    (item.quantity, item.product_id, item.quantity),
                )
                if updated.rowcount != 1:
                    raise ValidationError("Las existencias cambiaron. Actualiza el carrito e intenta nuevamente.")
                connection.execute(
                    """INSERT INTO detalle_venta
                       (venta_id, producto_id, codigo, nombre, cantidad, precio_unitario, subtotal)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (sale_id, item.product_id, product["codigo"], product["nombre"],
                     item.quantity, item.unit_price, item.subtotal),
                )
            # connect_db confirma aquí al salir; cualquier excepción revierte
            # la cabecera, TODOS los detalles y TODOS los descuentos de stock.
    except sqlite3.OperationalError as error:
        if error.sqlite_errorcode & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise ValidationError("La base está ocupada. No se guardó la venta; espera un momento y vuelve a intentarlo.") from error
        raise

    # Solo después de salir del contexto sabemos que el COMMIT terminó bien.
    cart.clear()
    return sale_id


def list_sales(db_path: Path = DEFAULT_DB_PATH) -> list[sqlite3.Row]:
    with connect_db(db_path) as connection:
        return connection.execute("SELECT id, fecha, total FROM ventas ORDER BY id DESC").fetchall()


def get_sale_details(sale_id: int, db_path: Path = DEFAULT_DB_PATH) -> list[sqlite3.Row]:
    with connect_db(db_path) as connection:
        return connection.execute("SELECT * FROM detalle_venta WHERE venta_id = ? ORDER BY id", (sale_id,)).fetchall()


def format_sale_date(iso_text: str) -> str:
    """Almacenamos zona explícita; mostramos la hora local del equipo."""
    return datetime.fromisoformat(iso_text).astimezone().strftime("%d/%m/%Y %H:%M:%S")
