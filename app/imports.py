"""ETL acotado: extraer CSV, transformar/validar y cargar nuevos productos."""

from collections import Counter
import csv
from dataclasses import dataclass, replace
import io
import json
import os
from pathlib import Path
import sqlite3
from typing import Literal

from app.database import DEFAULT_DB_PATH, connect_db
from app.exports import _check_destination, _safe_text, _write_csv
from app.inventory import validate_product
from app.validation import ValidationError, price_to_input

HEADERS = ("codigo", "nombre", "precio", "stock")
MAX_FILE_BYTES = 2 * 1024 * 1024
MAX_ROWS = 2000
STATUS_LABELS = {"new": "Nuevo", "existing": "Existente", "error": "Error", "loaded": "Cargado"}


@dataclass(frozen=True)
class ImportRow:
    line: int
    raw: tuple[str, ...]
    values: tuple[str, str, int, int] | None
    status: Literal["new", "existing", "error", "loaded"]
    message: str


@dataclass(frozen=True)
class ImportPreview:
    source: Path
    rows: tuple[ImportRow, ...]

    @property
    def new_count(self) -> int:
        return sum(row.status == "new" for row in self.rows)

    @property
    def error_count(self) -> int:
        return sum(row.status == "error" for row in self.rows)

    @property
    def existing_count(self) -> int:
        return sum(row.status == "existing" for row in self.rows)

    @property
    def can_load(self) -> bool:
        return self.new_count > 0 and self.error_count == 0


def _existing_codes(connection: sqlite3.Connection) -> set[str]:
    # Incluye códigos heredados escritos por otros scripts sin normalización.
    return {row[0].strip().upper() for row in connection.execute("SELECT codigo FROM productos")}


def preview_import(source: Path, db_path: Path = DEFAULT_DB_PATH) -> ImportPreview:
    source = Path(source).resolve()
    with source.open("rb") as stream:
        payload = stream.read(MAX_FILE_BYTES + 1)
    if len(payload) > MAX_FILE_BYTES:
        raise ValidationError("El CSV supera 2 MiB. Divide el archivo en lotes más pequeños.")
    try:
        content = payload.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValidationError("Guarda el archivo como CSV UTF-8 y vuelve a abrirlo.") from error
    reader = csv.reader(io.StringIO(content, newline=""), delimiter=";", strict=True)
    rows = []
    try:
        header = next(reader, [])
        normalized = [field.strip().casefold() for field in header]
        if len(normalized) != 4 or set(normalized) != set(HEADERS):
            raise ValidationError("Encabezados requeridos: codigo;nombre;precio;stock. Usa punto y coma (;).")
        positions = [normalized.index(field) for field in HEADERS]
        while True:
            line = reader.line_num + 1
            record = next(reader, None)
            if record is None:
                break
            if not record or (len(record) == 1 and not record[0].strip()):
                continue
            if len(rows) >= MAX_ROWS:
                raise ValidationError("El CSV supera 2000 filas. Divide el archivo en lotes más pequeños.")
            if len(record) != 4:
                rows.append(ImportRow(line, tuple(record), None, "error", "La fila debe tener exactamente cuatro columnas."))
                continue
            raw = tuple(record[position] for position in positions)
            try:
                values = validate_product(*raw)
            except ValidationError as error:
                rows.append(ImportRow(line, raw, None, "error", str(error)))
            else:
                rows.append(ImportRow(line, raw, values, "new", "Datos válidos; código normalizado y precio convertido a centavos."))
    except csv.Error as error:
        raise ValidationError(f"CSV mal formado cerca de la línea {reader.line_num}: {error}") from error

    counts = Counter(row.raw[0].strip().upper() for row in rows if len(row.raw) == 4 and row.raw[0].strip())
    with connect_db(db_path) as connection:
        existing = _existing_codes(connection)
    checked = []
    for row in rows:
        if len(row.raw) == 4 and counts[row.raw[0].strip().upper()] > 1:
            row = replace(row, status="error", message="Código repetido en el archivo después de normalizarlo; corrige todas sus filas.")
        elif row.values is not None and row.values[0] in existing:
            row = replace(row, status="existing", message="El código ya existe. Se omite; conserva nombre, precio y stock actuales.")
        checked.append(row)
    return ImportPreview(source, tuple(checked))


def load_import(preview: ImportPreview, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Inserta exactamente las filas nuevas revisadas, en una sola transacción."""
    if preview.error_count:
        raise ValidationError("Corrige los errores del CSV y vuelve a abrirlo. No se cargó ninguna fila.")
    new_rows = [row for row in preview.rows if row.status == "new"]
    if not new_rows:
        raise ValidationError("No hay productos nuevos para cargar.")
    # Defender también la entrada de esta API; la interfaz conserva tipos inmutables.
    values = []
    for row in new_rows:
        if row.values is None:
            raise ValidationError("La vista previa no es válida. Vuelve a abrir el archivo.")
        code, name, price, stock = row.values
        values.append(validate_product(code, name, price_to_input(price), str(stock)))
    if len({value[0] for value in values}) != len(values):
        raise ValidationError("Hay códigos repetidos en el lote.")
    try:
        with connect_db(db_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = _existing_codes(connection)
            if any(value[0] in existing for value in values):
                raise ValidationError("El catálogo cambió desde la vista previa. Vuelve a abrir el CSV para revisar los códigos; no se cargó ninguna fila.")
            connection.executemany(
                "INSERT INTO productos(codigo,nombre,precio,stock) VALUES (?,?,?,?)", values
            )
    except sqlite3.OperationalError as error:
        if error.sqlite_errorcode & 255 in (sqlite3.SQLITE_BUSY, sqlite3.SQLITE_LOCKED):
            raise ValidationError("La base está ocupada. No se cargaron productos; espera y vuelve a intentar.") from error
        raise
    return len(values)  # El COMMIT ya terminó correctamente.


def check_import_destination(destination: Path, db_path: Path, source: Path | None = None) -> None:
    destination = Path(destination)
    _check_destination(destination, Path(db_path))
    if source is not None and (destination.resolve() == source.resolve() or (
        destination.exists() and source.exists() and os.path.samefile(destination, source)
    )):
        raise ValidationError("Elige un destino distinto del CSV de entrada para conservar el archivo original.")


def export_import_report(preview: ImportPreview, destination: Path, db_path: Path = DEFAULT_DB_PATH) -> int:
    destination = Path(destination)
    check_import_destination(destination, db_path, preview.source)
    rows = []
    for row in preview.rows:
        code, name, price, stock = row.values if row.values is not None else ("", "", None, "")
        rows.append((row.line, STATUS_LABELS[row.status], json.dumps(row.raw, ensure_ascii=False),
                     _safe_text(code), _safe_text(name), price_to_input(price) if price is not None else "",
                     stock, _safe_text(row.message)))
    return _write_csv(destination, ("fila", "estado", "valores_originales", "codigo_normalizado",
                                   "nombre_normalizado", "precio", "stock", "detalle"), rows)


def write_product_template(destination: Path, db_path: Path = DEFAULT_DB_PATH, *, source: Path | None = None) -> int:
    destination = Path(destination)
    check_import_destination(destination, db_path, source)
    return _write_csv(destination, HEADERS, ())
