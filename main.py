"""Punto de entrada: ejecutar con python main.py desde la raíz."""

import logging
from logging.handlers import RotatingFileHandler
import sqlite3
import sys
import tkinter as tk
from tkinter import messagebox

from app.database import DEFAULT_DB_PATH, initialize_database
from app.ui import InventoryApp


def _startup_logger() -> logging.Logger:
    """Diagnóstico local acotado, también disponible en el ejecutable sin consola."""
    logger = logging.Logger("inventario.inicio", level=logging.INFO)
    try:
        DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(DEFAULT_DB_PATH.parent / "inicio.log", maxBytes=65536,
                                      backupCount=1, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s pid=%(process)d %(levelname)s %(message)s"))
        logger.addHandler(handler)
    except OSError:
        logger.addHandler(logging.NullHandler())
    return logger


def main() -> int:
    """Prepara la base de datos y mantiene abierta la ventana."""
    logger = _startup_logger()
    try:
        logger.info("Inicio")
        try:
            root = tk.Tk()
        except tk.TclError as error:
            logger.exception("No se pudo abrir Tkinter")
            if sys.stderr is not None:
                print(f"No se pudo abrir Tkinter: {error}", file=sys.stderr)
            return 1

        root.withdraw()
        try:
            initialize_database(DEFAULT_DB_PATH)
            InventoryApp(root, DEFAULT_DB_PATH)
            root.deiconify()
            root.update_idletasks()
        except (sqlite3.Error, OSError, tk.TclError) as error:
            logger.exception("No se pudo iniciar la aplicación")
            messagebox.showerror("No se pudo iniciar la aplicación",
                                 f"Revisa el acceso a la carpeta de datos:\n{DEFAULT_DB_PATH.parent}\n\nDetalle: {error}", parent=root)
            root.destroy()
            return 1
        logger.info("Interfaz lista")
        root.mainloop()
        logger.info("Cierre")
        return 0
    finally:
        for handler in logger.handlers:
            handler.close()


if __name__ == "__main__":
    raise SystemExit(main())
