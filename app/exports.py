"""CSV con BOM, campos seguros y reemplazo completo del archivo de destino."""

from collections.abc import Iterable
import csv
import os
from pathlib import Path
import tempfile

from app.database import DEFAULT_DB_PATH, connect_db
from app.inventory import list_products
from app.validation import ValidationError, price_to_input


def _safe_text(value: str) -> str:
    """Neutraliza inicios de fórmula; el apóstrofo se conserva en el CSV."""
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def _check_destination(destination: Path, db_path: Path) -> None:
    protected = [Path(str(db_path) + suffix) for suffix in ("", "-wal", "-shm", "-journal")]
    for path in protected:
        if destination.resolve() == path.resolve() or (
            destination.exists() and path.exists() and os.path.samefile(destination, path)
        ):
            raise ValidationError("Elige un archivo CSV distinto de la base de datos y sus archivos auxiliares.")


def _write_csv(destination: Path, headers: tuple[str, ...], rows: Iterable[tuple]) -> int:
    temporary = None
    try:
        # El temporal debe estar en el mismo directorio para poder reemplazar
        # el destino al finalizar. Si falla la escritura, el anterior queda intacto.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8-sig", newline="", dir=destination.parent,
                                         prefix=f".{destination.name}.", suffix=".tmp", delete=False) as output:
            temporary = Path(output.name)
            writer = csv.writer(output, delimiter=";")
            writer.writerow(headers)
            count = 0
            for row in rows:
                writer.writerow(row)
                count += 1
        os.replace(temporary, destination)
        return count
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def export_inventory(destination: Path, db_path: Path = DEFAULT_DB_PATH) -> int:
    destination, db_path = Path(destination), Path(db_path)
    _check_destination(destination, db_path)
    products = list_products(db_path)  # Siempre TODO el catálogo, sin filtro de UI.
    rows = ((_safe_text(p["codigo"]), _safe_text(p["nombre"]), price_to_input(p["precio"]), p["stock"])
            for p in products)
    return _write_csv(destination, ("codigo", "nombre", "precio", "stock"), rows)


def export_sales(destination: Path, db_path: Path = DEFAULT_DB_PATH) -> int:
    destination, db_path = Path(destination), Path(db_path)
    _check_destination(destination, db_path)
    with connect_db(db_path) as connection:
        details = connection.execute("""
            SELECT d.venta_id, v.fecha, d.codigo, d.nombre, d.cantidad, d.precio_unitario, d.subtotal
            FROM detalle_venta AS d JOIN ventas AS v ON v.id = d.venta_id
            ORDER BY v.id, d.id
        """).fetchall()
    rows = ((d["venta_id"], d["fecha"], _safe_text(d["codigo"]), _safe_text(d["nombre"]),
             d["cantidad"], price_to_input(d["precio_unitario"]), price_to_input(d["subtotal"])) for d in details)
    return _write_csv(destination, ("venta_id", "fecha", "codigo", "nombre", "cantidad", "precio_unitario", "subtotal"), rows)
