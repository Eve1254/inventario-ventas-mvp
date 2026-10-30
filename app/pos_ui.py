"""Vista de búsqueda y carrito; delega las reglas en Cart."""

from collections.abc import Callable
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from app.inventory import find_product_by_code, list_products
from app.sales import Cart, process_sale
from app.theme import BLUE
from app.validation import ValidationError, format_price, parse_quantity


class PosFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, db_path: Path, cart: Cart,
                 on_sale_saved: Callable[[], bool | None] | None = None):
        super().__init__(master, padding=(22, 20))
        self.db_path, self.cart = db_path, cart
        self.on_sale_saved = on_sale_saved
        self._processing = False
        self.search_var = tk.StringVar(master=self)
        self.quantity_var = tk.StringVar(master=self, value="1")
        self.total_var = tk.StringVar(master=self, value="0,00")
        self.summary_var = tk.StringVar(master=self)
        self.status_var = tk.StringVar(master=self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)
        ttk.Label(self, text="Punto de venta", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="Venta en preparación · el carrito no reserva stock.", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(4, 18))

        panels = ttk.Frame(self)
        panels.grid(row=2, column=0, sticky="nsew")
        panels.columnconfigure(0, weight=1, uniform="panels")
        panels.columnconfigure(1, weight=1, uniform="panels")
        panels.rowconfigure(0, weight=1)
        self._build_search(panels)
        self._build_cart(panels)
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", wraplength=900).grid(
            row=3, column=0, sticky="w", pady=(14, 0))
        self.refresh_products()
        self.refresh_cart()

    @staticmethod
    def _table(parent, columns):
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=[column[0] for column in columns], show="headings", selectmode="browse")
        for name, label, width, stretch in columns:
            tree.heading(name, text=label, anchor="w")
            tree.column(name, width=width, minwidth=75 if stretch else width, stretch=stretch,
                        anchor="w" if name in ("codigo", "nombre") else "e")
        tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        return frame, tree

    def _build_search(self, panels) -> None:
        left = ttk.Frame(panels, padding=(0, 0, 14, 0))
        left.grid(row=0, column=0, sticky="nsew")
        left.columnconfigure(0, weight=1)
        left.rowconfigure(2, weight=1)
        ttk.Label(left, text="BUSCAR PRODUCTOS", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        search = ttk.Frame(left)
        search.grid(row=1, column=0, sticky="ew", pady=(10, 12))
        search.columnconfigure(0, weight=1)
        self.search_entry = ttk.Entry(search, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda event: self.search_or_add())
        ttk.Button(search, text="Buscar", command=self.refresh_products).grid(row=0, column=1)
        table, self.results_tree = self._table(left, (
            ("codigo", "Código", 80, False), ("nombre", "Producto", 160, True),
            ("precio", "Precio", 100, False), ("stock", "Stock", 55, False)))
        table.grid(row=2, column=0, sticky="nsew")
        self.results_tree.bind("<Double-1>", lambda event: self.add_selected())
        self.results_tree.bind("<Return>", lambda event: self.add_selected())
        self.add_button = ttk.Button(left, text="Agregar al carrito", style="Accent.TButton", command=self.add_selected)
        self.add_button.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        ttk.Label(left, text="Código exacto + Enter: agrega una unidad.\nTambién puedes buscar por nombre.",
                  style="Muted.TLabel").grid(row=4, column=0, sticky="w", pady=(10, 0))

    def _build_cart(self, panels) -> None:
        right = ttk.Frame(panels, padding=(14, 0, 0, 0))
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)
        ttk.Label(right, text="CARRITO", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(right, textvariable=self.summary_var, style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(10, 12))
        table, self.cart_tree = self._table(right, (
            ("nombre", "Producto", 145, True), ("cantidad", "Cant.", 55, False),
            ("precio", "Precio", 100, False), ("subtotal", "Subtotal", 110, False)))
        table.grid(row=2, column=0, sticky="nsew")
        self.cart_tree.bind("<<TreeviewSelect>>", self._cart_selected)

        actions = ttk.Frame(right)
        actions.grid(row=3, column=0, sticky="ew", pady=(12, 8))
        ttk.Label(actions, text="Cantidad").grid(row=0, column=0, padx=(0, 6))
        self.quantity_entry = ttk.Entry(actions, textvariable=self.quantity_var, width=5, font=("Segoe UI", 11))
        self.quantity_entry.grid(row=0, column=1, padx=(0, 6))
        self.quantity_entry.bind("<Return>", lambda event: self.apply_quantity())
        self.quantity_button = ttk.Button(actions, text="Aplicar", command=self.apply_quantity)
        self.quantity_button.grid(row=0, column=2, padx=(0, 6))
        self.remove_button = ttk.Button(actions, text="Quitar", command=self.remove_selected)
        self.remove_button.grid(row=0, column=3)
        self.clear_button = ttk.Button(right, text="Vaciar carrito", command=self.clear_cart)
        self.clear_button.grid(row=4, column=0, sticky="w")
        total = ttk.Frame(right)
        total.grid(row=5, column=0, sticky="ew", pady=(16, 0))
        total.columnconfigure(1, weight=1)
        ttk.Label(total, text="TOTAL", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(total, textvariable=self.total_var, font=("Segoe UI", 24, "bold"),
                  foreground=BLUE).grid(row=0, column=1, sticky="e")
        self.process_button = ttk.Button(right, text="Procesar venta", style="Accent.TButton",
                                         command=self.process_current_sale, state="disabled")
        self.process_button.grid(row=6, column=0, sticky="ew", pady=(12, 0))

    def refresh_products(self, *, notify: bool = True) -> bool:
        try:
            products = list_products(self.db_path, self.search_var.get())
        except (sqlite3.Error, OSError) as error:
            self.status_var.set("No se pudo actualizar la búsqueda; los resultados pueden estar desactualizados.")
            if notify:
                messagebox.showerror("Error de búsqueda", str(error), parent=self)
            return False
        self.results_tree.delete(*self.results_tree.get_children())
        for product in products:
            self.results_tree.insert("", "end", iid=str(product["id"]), values=(
                product["codigo"], product["nombre"], format_price(product["precio"]), product["stock"]))
        if products:
            self.results_tree.selection_set(str(products[0]["id"]))
        self.add_button.state(["!disabled"] if products else ["disabled"])
        self.status_var.set(f"{len(products)} productos encontrados." if products else "No se encontraron productos.")
        return True

    def _change_cart(self, action: Callable[[], None]) -> bool:
        try:
            action()
        except (ValidationError, sqlite3.Error, OSError) as error:
            self.status_var.set(str(error))
            messagebox.showerror("No se pudo cambiar el carrito", str(error), parent=self)
            return False
        self.refresh_cart()
        self.status_var.set("Carrito actualizado. Las existencias no se han descontado.")
        return True

    def search_or_add(self) -> None:
        try:
            product = find_product_by_code(self.search_var.get(), self.db_path)
        except (sqlite3.Error, OSError) as error:
            messagebox.showerror("Error de búsqueda", str(error), parent=self)
            return
        if product is None:
            self.refresh_products()
        elif self._change_cart(lambda: self.cart.add(product["id"])):
            self.search_var.set("")
            self.search_entry.focus_set()

    def add_selected(self) -> None:
        selected = self.results_tree.selection()
        if selected:
            self._change_cart(lambda: self.cart.add(int(selected[0])))

    def refresh_cart(self) -> None:
        selected = self.cart_tree.selection()
        self.cart_tree.delete(*self.cart_tree.get_children())
        for item in self.cart.items:
            self.cart_tree.insert("", "end", iid=str(item.product_id), values=(
                item.name, item.quantity, format_price(item.unit_price), format_price(item.subtotal)))
        if selected and self.cart_tree.exists(selected[0]):
            self.cart_tree.selection_set(selected[0])
        elif self.cart.items:
            self.cart_tree.selection_set(str(self.cart.items[-1].product_id))
        self.total_var.set(format_price(self.cart.total_cents))
        self.summary_var.set(f"{len(self.cart.items)} productos · {self.cart.total_units} unidades")
        self.clear_button.state(["!disabled"] if self.cart.items else ["disabled"])
        self.process_button.state(["!disabled"] if self.cart.items and not self._processing else ["disabled"])
        self._cart_selected()

    def _cart_selected(self, event=None) -> None:
        selected = self.cart_tree.selection()
        enabled = bool(selected)
        for button in (self.quantity_button, self.remove_button):
            button.state(["!disabled"] if enabled else ["disabled"])
        if selected:
            item = next((item for item in self.cart.items if str(item.product_id) == selected[0]), None)
            if item:
                self.quantity_var.set(str(item.quantity))

    def apply_quantity(self) -> None:
        selected = self.cart_tree.selection()
        if selected:
            self._change_cart(lambda: self.cart.set_quantity(int(selected[0]), parse_quantity(self.quantity_var.get())))

    def remove_selected(self) -> None:
        selected = self.cart_tree.selection()
        if selected:
            self._change_cart(lambda: self.cart.remove(int(selected[0])))

    def clear_cart(self) -> None:
        if self.cart.items and messagebox.askyesno("Vaciar carrito", "¿Quieres quitar todos los productos del carrito?",
                                                  parent=self, default="no"):
            self._change_cart(self.cart.clear)

    def process_current_sale(self) -> None:
        if self._processing or not self.cart.items:
            return
        self._processing = True  # Incluye el diálogo modal y evita reentradas.
        self.refresh_cart()
        total = self.cart.total_cents
        try:
            if not messagebox.askyesno("Confirmar venta", f"¿Registrar la venta por {format_price(total)}?\n\nSe descontarán {self.cart.total_units} unidades del inventario.",
                                      parent=self, default="no"):
                return
            try:
                sale_id = process_sale(self.cart)
            except (ValidationError, sqlite3.Error, OSError) as error:
                self.status_var.set("No se registró la venta. El carrito se conserva.")
                messagebox.showerror("No se registró la venta", str(error), parent=self)
                return

            # La venta ya está confirmada: un fallo de lectura posterior NO
            # debe presentarse como si fuera necesario procesarla otra vez.
            self.refresh_cart()
            try:
                products_fresh = self.refresh_products(notify=False)
                views_fresh = self.on_sale_saved() if self.on_sale_saved is not None else True
            except (sqlite3.Error, OSError) as error:
                self.status_var.set(f"Venta #{sale_id} guardada. Actualiza las vistas.")
                messagebox.showwarning("Venta guardada", f"La venta #{sale_id} se guardó, pero no se pudo actualizar la vista.\n\n{error}", parent=self)
                return
            if products_fresh is False or views_fresh is False:
                self.status_var.set(f"Venta #{sale_id} guardada. Actualiza las vistas; pueden mostrar datos anteriores.")
                messagebox.showwarning("Venta guardada", f"La venta #{sale_id} se guardó y el stock se descontó.\n\nNo se pudieron actualizar todas las tablas. Pulsa Actualizar o F5; no repitas la venta.", parent=self)
                return
            self.status_var.set(f"Venta #{sale_id} registrada. Stock actualizado.")
            messagebox.showinfo("Venta registrada", f"Venta #{sale_id}\nTotal: {format_price(total)}\n\nLa venta se guardó y las existencias se descontaron.", parent=self)
        finally:
            self._processing = False
            self.refresh_cart()
