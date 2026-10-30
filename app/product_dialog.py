"""Un solo formulario modal para crear y editar productos."""

from collections.abc import Callable
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import ttk

from app.inventory import create_product, update_product
from app.theme import BLACK
from app.validation import ValidationError, price_to_input


class ProductDialog(tk.Toplevel):
    def __init__(self, master: tk.Tk, db_path: Path, on_saved: Callable[[], None],
                 product: sqlite3.Row | None = None):
        super().__init__(master)
        self.db_path = db_path
        self.on_saved = on_saved
        self.product_id = product["id"] if product is not None else None
        self.original_product = product
        self.title("Editar producto" if product is not None else "Nuevo producto")
        self.transient(master)
        self.resizable(False, False)
        self.error_var = tk.StringVar(master=self)
        initial = {"codigo": "", "nombre": "", "precio": "", "stock": "0"}
        if product is not None:
            initial = {"codigo": product["codigo"], "nombre": product["nombre"],
                       "precio": price_to_input(product["precio"]), "stock": str(product["stock"])}
        self.fields = {key: tk.StringVar(master=self, value=value) for key, value in initial.items()}
        self.entries: dict[str, ttk.Entry] = {}

        content = ttk.Frame(self, padding=24)
        content.grid(sticky="nsew")
        content.columnconfigure(0, weight=1)
        ttk.Label(content, text=self.title(), font=("Segoe UI", 19, "bold")).grid(
            row=0, column=0, sticky="w", pady=(0, 16))
        labels = (("codigo", "Código único"), ("nombre", "Nombre del producto"),
                  ("precio", "Precio unitario"), ("stock", "Stock disponible"))
        for index, (field, label) in enumerate(labels):
            ttk.Label(content, text=label).grid(row=1 + index * 2, column=0, sticky="w", pady=(8, 4))
            entry = ttk.Entry(content, textvariable=self.fields[field], width=42, font=("Segoe UI", 11))
            entry.grid(row=2 + index * 2, column=0, sticky="ew")
            self.entries[field] = entry
        ttk.Label(content, text="Precio: 8500,50 o 8500.50, sin separadores de miles.\nStock: unidades enteras; puede ser cero.",
                  style="Muted.TLabel").grid(row=9, column=0, sticky="w", pady=(12, 0))
        ttk.Label(content, textvariable=self.error_var, foreground=BLACK, wraplength=440).grid(
            row=10, column=0, sticky="w", pady=(12, 8))

        actions = ttk.Frame(content)
        actions.grid(row=11, column=0, sticky="e")
        self.cancel_button = ttk.Button(actions, text="Cancelar", command=self.destroy)
        self.cancel_button.grid(row=0, column=0, padx=(0, 10))
        self.save_button = ttk.Button(actions, text="Guardar producto", style="Accent.TButton", command=self.save)
        self.save_button.grid(row=0, column=1)
        self.bind("<Escape>", lambda event: self.destroy())
        self.bind("<Return>", self._on_return)
        self.update_idletasks()
        x = max(0, master.winfo_rootx() + (master.winfo_width() - self.winfo_reqwidth()) // 2)
        y = max(0, master.winfo_rooty() + (master.winfo_height() - self.winfo_reqheight()) // 2)
        self.geometry(f"+{x}+{y}")
        self.grab_set()
        self.entries["codigo"].focus_set()

    def _on_return(self, event) -> str:
        # El botón enfocado conserva su significado también con el teclado.
        if event.widget is self.cancel_button:
            self.destroy()
        else:
            self.save()
        return "break"

    def save(self) -> None:
        self.save_button.state(["disabled"])
        values = tuple(self.fields[field].get() for field in ("codigo", "nombre", "precio", "stock"))
        try:
            if self.product_id is None:
                create_product(*values, self.db_path)
            else:
                update_product(self.product_id, *values, self.db_path, expected=self.original_product)
        except ValidationError as error:
            self.error_var.set(str(error))
            if error.field in self.entries:
                self.entries[error.field].focus_set()
            self.save_button.state(["!disabled"])
            return
        except (sqlite3.Error, OSError) as error:
            self.error_var.set(f"No se pudo guardar. Intenta nuevamente. Detalle: {error}")
            self.save_button.state(["!disabled"])
            return
        self.destroy()
        self.on_saved()
