"""Ventana principal: inventario y punto de venta en pestañas."""

from datetime import datetime
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from app.database import DEFAULT_DB_PATH
from app.charts_ui import ChartsFrame
from app.export_ui import export_csv_dialog
from app.import_ui import ImportFrame
from app.inventory import delete_product, get_product, list_products, stock_status
from app.pos_ui import PosFrame
from app.product_dialog import ProductDialog
from app.sales import Cart
from app.sales_ui import SalesFrame
from app.theme import BLACK, PALE_BLUE, WHITE, configure_theme
from app.validation import ValidationError, format_price


class InventoryApp:
    """La ventana presenta datos; las consultas viven en inventory.py."""

    def __init__(self, root: tk.Tk, db_path: Path = DEFAULT_DB_PATH):
        self.root = root
        self.db_path = db_path
        self.status_var = tk.StringVar(master=root)
        self.summary_var = tk.StringVar(master=root)
        self.search_var = tk.StringVar(master=root)
        self.cart = Cart(db_path)

        root.title("Inventario y Ventas")
        root.geometry("1120x760")
        root.minsize(1020, 680)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        configure_theme(root)
        self._build_header()
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=1, column=0, sticky="nsew")
        self._build_inventory()
        self.pos = PosFrame(self.notebook, db_path, self.cart, self._after_sale_saved)
        self.notebook.add(self.pos, text="Punto de venta")
        self.history = SalesFrame(self.notebook, db_path)
        self.notebook.add(self.history, text="Ventas")
        self.charts = ChartsFrame(self.notebook, db_path)
        self.notebook.add(self.charts, text="Gráficos")
        self.importer = ImportFrame(self.notebook, db_path, self._after_import_loaded)
        self.notebook.add(self.importer, text="Importar CSV")
        self.notebook.bind("<<NotebookTabChanged>>", lambda event: self.refresh_current_tab())
        root.bind("<F5>", lambda event: self.refresh_current_tab(reload_import=True))
        root.protocol("WM_DELETE_WINDOW", self.close_application)
        self.reload_products()

    def _build_header(self) -> None:
        header = tk.Frame(self.root, background=BLACK, padx=28, pady=20)
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(0, weight=1)
        tk.Label(header, text="INVENTARIO / VENTAS", background=BLACK, foreground=WHITE,
                 font=("Segoe UI", 13, "bold")).grid(row=0, column=0, sticky="w")
        tk.Label(header, text="Datos guardados en este equipo", background=BLACK,
                 foreground=WHITE, font=("Segoe UI", 10)).grid(row=0, column=1, sticky="e")

    def _build_inventory(self) -> None:
        content = ttk.Frame(self.notebook, padding=(28, 22, 28, 18))
        self.inventory_tab = content
        self.notebook.add(content, text="Inventario")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(4, weight=1)

        heading = ttk.Frame(content)
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Inventario", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.new_button = ttk.Button(heading, text="Nuevo producto", style="Accent.TButton", command=self.new_product)
        self.new_button.grid(row=0, column=1, padx=(0, 10))
        self.refresh_button = ttk.Button(heading, text="Actualizar inventario",
                                         command=self.reload_products)
        self.refresh_button.grid(row=0, column=2, sticky="e")
        ttk.Label(content, text="Administra tus productos y existencias.", style="Muted.TLabel").grid(
            row=1, column=0, sticky="w", pady=(6, 20))

        toolbar = ttk.Frame(content)
        toolbar.grid(row=2, column=0, sticky="ew", pady=(0, 18))
        toolbar.columnconfigure(1, weight=1)
        ttk.Label(toolbar, text="Código o nombre").grid(row=0, column=0, padx=(0, 10))
        self.search_entry = ttk.Entry(toolbar, textvariable=self.search_var, font=("Segoe UI", 11))
        self.search_entry.grid(row=0, column=1, sticky="ew", padx=(0, 8))
        self.search_entry.bind("<Return>", lambda event: self.reload_products())
        ttk.Button(toolbar, text="Buscar", command=self.reload_products).grid(row=0, column=2, padx=(0, 16))
        self.edit_button = ttk.Button(toolbar, text="Editar", command=self.edit_selected_product, state="disabled")
        self.edit_button.grid(row=0, column=3, padx=(0, 8))
        self.delete_button = ttk.Button(toolbar, text="Eliminar", command=self.delete_selected_product, state="disabled")
        self.delete_button.grid(row=0, column=4)
        self.export_button = ttk.Button(toolbar, text="Exportar CSV",
                                        command=lambda: export_csv_dialog(self.root, self.db_path, "inventory"))
        self.export_button.grid(row=0, column=5, padx=(8, 0))

        summary = ttk.Frame(content)
        summary.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        summary.columnconfigure(0, weight=1)
        ttk.Label(summary, text="CATÁLOGO DE PRODUCTOS", style="Section.TLabel").grid(
            row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.summary_var, style="Muted.TLabel").grid(
            row=0, column=1, sticky="e")

        table_frame = ttk.Frame(content)
        table_frame.grid(row=4, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        columns = ("id", "codigo", "nombre", "precio", "stock", "estado")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        column_settings = (
            ("id", "ID", 55, "center", False),
            ("codigo", "Código", 115, "w", False),
            ("nombre", "Nombre del producto", 300, "w", True),
            ("precio", "Precio", 145, "e", False),
            ("stock", "Stock", 85, "center", False),
            ("estado", "Estado", 110, "w", False),
        )
        for name, label, width, anchor, stretch in column_settings:
            self.tree.heading(name, text=label, anchor=anchor)
            self.tree.column(name, width=width, minwidth=width if not stretch else 160,
                             anchor=anchor, stretch=stretch)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        horizontal = ttk.Scrollbar(table_frame, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=horizontal.set)
        self.tree.tag_configure("alternate", background=WHITE)
        self.tree.tag_configure("low", background=PALE_BLUE, foreground=BLACK)
        self.tree.tag_configure("empty", background=BLACK, foreground=WHITE)
        self.tree.bind("<<TreeviewSelect>>", lambda event: self._inventory_selected())
        self.tree.bind("<Double-1>", lambda event: self.edit_selected_product())

        self.empty_label = tk.Label(self.tree, text="Aún no hay productos registrados.",
                                    background=WHITE, foreground=BLACK, font=("Segoe UI", 12))

        footer = ttk.Frame(content)
        footer.grid(row=5, column=0, sticky="ew", pady=(14, 0))
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status_var, style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(footer, text="F5 · Actualizar", style="Muted.TLabel").grid(row=0, column=1, sticky="e")

    def reload_products(self, *, notify: bool = True) -> bool:
        """Consulta SQLite antes de reemplazar lo visible para conservarlo si falla."""
        try:
            products = list_products(self.db_path, self.search_var.get())
        except (sqlite3.Error, OSError) as error:
            self.status_var.set("No se pudo actualizar. Los datos visibles pueden estar desactualizados.")
            if notify:
                messagebox.showerror("No se pudo leer el inventario",
                                     f"Intenta actualizar de nuevo.\n\nDetalle: {error}", parent=self.root)
            return False

        current_items = self.tree.get_children()
        if current_items:
            self.tree.delete(*current_items)
        for index, product in enumerate(products):
            tag = "empty" if product["stock"] == 0 else "low" if product["stock"] < 5 else "alternate" if index % 2 else ""
            self.tree.insert("", "end", iid=str(product["id"]), values=(
                product["id"], product["codigo"], product["nombre"],
                format_price(product["precio"]), product["stock"], stock_status(product["stock"]),
            ), tags=(tag,) if tag else ())

        if products:
            self.empty_label.place_forget()
        else:
            self.empty_label.configure(text="No hay coincidencias." if self.search_var.get().strip()
                                       else "Aún no hay productos registrados.")
            self.empty_label.place(relx=0.5, rely=0.45, anchor="center")

        units = sum(product["stock"] for product in products)
        low = sum(product["stock"] < 5 for product in products)
        self.summary_var.set(f"{len(products)} productos · {units} unidades · {low} con stock < 5")
        self.status_var.set(f"Última lectura: {datetime.now().astimezone():%H:%M:%S}")
        self._inventory_selected()
        return True

    def _inventory_selected(self) -> None:
        selected = bool(self.tree.selection())
        for button in (self.edit_button, self.delete_button):
            button.state(["!disabled"] if selected else ["disabled"])

    def _after_product_saved(self) -> None:
        self.search_var.set("")
        self.reload_products()
        self.pos.refresh_products()
        self.pos.refresh_cart()
        self.charts.refresh()

    def new_product(self) -> ProductDialog:
        return ProductDialog(self.root, self.db_path, self._after_product_saved)

    def edit_selected_product(self) -> ProductDialog | None:
        selected = self.tree.selection()
        if not selected:
            return None
        try:
            product = get_product(int(selected[0]), self.db_path)
            if product is None:
                raise ValidationError("El producto ya no existe. Actualiza el inventario.")
        except (ValidationError, sqlite3.Error, OSError) as error:
            messagebox.showerror("No se pudo editar", str(error), parent=self.root)
            return None
        return ProductDialog(self.root, self.db_path, self._after_product_saved, product)

    def delete_selected_product(self) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        product_id = int(selected[0])
        try:
            if any(item.product_id == product_id for item in self.cart.items):
                raise ValidationError("Quita este producto del carrito antes de eliminarlo del inventario.")
            product = get_product(product_id, self.db_path)
            if product is None:
                raise ValidationError("El producto ya no existe. Actualiza el inventario.")
            if not messagebox.askyesno("Eliminar producto", f"¿Eliminar {product['codigo']} — {product['nombre']}?\n\nEsta acción no se puede deshacer.",
                                      parent=self.root, default="no"):
                return
            delete_product(product_id, self.db_path)
        except (ValidationError, sqlite3.Error, OSError) as error:
            messagebox.showerror("No se pudo eliminar", str(error), parent=self.root)
            return
        self._after_product_saved()

    def refresh_current_tab(self, *, reload_import: bool = False) -> None:
        if self.notebook.select() == str(self.inventory_tab):
            self.reload_products()
        elif self.notebook.select() == str(self.pos):
            self.pos.refresh_products()
            self.pos.refresh_cart()
        elif self.notebook.select() == str(self.history):
            self.history.refresh_sales()
        elif self.notebook.select() == str(self.charts):
            self.charts.refresh()
        elif reload_import:
            self.importer.revalidate()

    def _after_import_loaded(self) -> bool:
        self.search_var.set("")
        inventory_fresh = self.reload_products(notify=False)
        products_fresh = self.pos.refresh_products(notify=False)
        self.pos.refresh_cart()
        charts_fresh = self.charts.refresh(notify=False)
        return inventory_fresh and products_fresh and charts_fresh

    def _after_sale_saved(self) -> bool:
        inventory_fresh = self.reload_products(notify=False)
        history_fresh = self.history.refresh_sales(notify=False)
        charts_fresh = self.charts.refresh(notify=False)
        return inventory_fresh and history_fresh and charts_fresh

    def close_application(self) -> None:
        if self.pos._processing or self.importer._loading:
            return
        if self.cart.items and not messagebox.askyesno(
            "Carrito pendiente", "El carrito es temporal. ¿Quieres salir y descartarlo?", parent=self.root, default="no"
        ):
            return
        self.root.destroy()
