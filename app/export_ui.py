"""Diálogo común para exportar inventario o detalle de ventas."""

from pathlib import Path
import sqlite3
from tkinter import filedialog, messagebox
from typing import Literal

from app.exports import export_inventory, export_sales
from app.validation import ValidationError


def export_csv_dialog(parent, db_path: Path, kind: Literal["inventory", "sales"]) -> Path | None:
    label, exporter = {"inventory": ("inventario", export_inventory), "sales": ("ventas", export_sales)}[kind]
    chosen = filedialog.asksaveasfilename(
        parent=parent, title=f"Exportar {label} a CSV", initialfile=f"{label}.csv",
        defaultextension=".csv", filetypes=[("Archivo CSV", "*.csv")], confirmoverwrite=True,
    )
    if not chosen:
        return None
    destination = Path(chosen)
    try:
        count = exporter(destination, db_path)
    except (ValidationError, sqlite3.Error, OSError) as error:
        messagebox.showerror("No se pudo exportar", f"No se completó la exportación.\n\nDetalle: {error}", parent=parent)
        return None
    messagebox.showinfo("Exportación completada", f"{count} registros exportados a:\n{destination}\n\nCSV UTF-8; separador: punto y coma (;).", parent=parent)
    return destination
