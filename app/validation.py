"""Conversión y validaciones compartidas por inventario y punto de venta."""

from decimal import Decimal
import re


MAX_SQLITE_INTEGER = 2**63 - 1


class ValidationError(ValueError):
    """Error que se puede mostrar al usuario y asociar con un campo."""

    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


def parse_price(text: str) -> int:
    """Acepta 10,50 o 10.50; devuelve 1050 sin aproximaciones de float."""
    text = text.strip()
    if not re.fullmatch(r"[0-9]+(?:[.,][0-9]{1,2})?", text):
        raise ValidationError("Escribe un precio válido, por ejemplo 8500,50, sin separadores de miles.", "precio")
    amount = Decimal(text.replace(",", "."))
    if amount <= 0:
        raise ValidationError("El precio debe ser mayor que cero.", "precio")
    if amount > Decimal(MAX_SQLITE_INTEGER) / 100:
        raise ValidationError("El precio supera el valor máximo permitido.", "precio")
    return int(amount * 100)


def _parse_integer(text: str, field: str, label: str, minimum: int) -> int:
    text = text.strip()
    if not re.fullmatch(r"[0-9]+", text):
        raise ValidationError(f"{label} debe ser un número entero sin decimales.", field)
    digits = text.lstrip("0") or "0"
    if len(digits) > 19 or int(digits) > MAX_SQLITE_INTEGER:
        raise ValidationError(f"{label} supera el valor máximo permitido.", field)
    value = int(digits)
    if value < minimum:
        raise ValidationError(f"{label} debe ser mayor o igual a {minimum}.", field)
    return value


def parse_stock(text: str) -> int:
    return _parse_integer(text, "stock", "El stock", 0)


def parse_quantity(text: str) -> int:
    return _parse_integer(text, "cantidad", "La cantidad", 1)


def price_to_input(cents: int) -> str:
    """Texto editable sin separadores de miles, compatible con parse_price."""
    whole, fraction = divmod(cents, 100)
    return f"{whole},{fraction:02d}"


def format_price(cents: int) -> str:
    """Texto para mostrar en tablas y totales, con dos decimales exactos."""
    whole, fraction = divmod(cents, 100)
    thousands = f"{whole:,}".replace(",", ".")
    return f"{thousands},{fraction:02d}"
