"""Punto de entrada: ejecutar con python main.py desde la raíz."""

import sqlite3
import sys
import tkinter as tk
from tkinter import messagebox

from app.database import initialize_database
from app.ui import InventoryApp


def main() -> int:
    """Prepara la base de datos y mantiene abierta la ventana."""
    try:
        root = tk.Tk()
    except tk.TclError as error:
        print(f"No se pudo abrir Tkinter: {error}", file=sys.stderr)
        return 1

    root.withdraw()
    try:
        initialize_database()
        InventoryApp(root)
    except (sqlite3.Error, OSError) as error:
        messagebox.showerror("No se pudo iniciar la aplicación",
                             f"Revisa el acceso a la carpeta data.\n\nDetalle: {error}", parent=root)
        root.destroy()
        return 1

    root.deiconify()
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
