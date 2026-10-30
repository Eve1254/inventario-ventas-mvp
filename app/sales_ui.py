"""Historial de ventas confirmadas, detalle y exportación."""

from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import messagebox, ttk

from app.export_ui import export_csv_dialog
from app.sales import format_sale_date, get_sale_details, list_sales
from app.validation import format_price


class SalesFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, db_path: Path):
        super().__init__(master, padding=(28, 22, 28, 18))
        self.db_path = db_path
        self.summary_var = tk.StringVar(master=self)
        self.status_var = tk.StringVar(master=self)
        self.detail_var = tk.StringVar(master=self, value="DETALLE DE LA VENTA")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)
        self.rowconfigure(5, weight=1)

        heading = ttk.Frame(self)
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Ventas", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(heading, text="Actualizar", command=self.refresh_sales).grid(row=0, column=1, padx=(0, 10))
        self.export_button = ttk.Button(heading, text="Exportar CSV", style="Accent.TButton",
                                        command=lambda: export_csv_dialog(self, self.db_path, "sales"))
        self.export_button.grid(row=0, column=2)
        ttk.Label(self, text="Ventas confirmadas y productos vendidos. Fechas en la hora local del equipo.",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(6, 14))
        ttk.Label(self, textvariable=self.summary_var, style="Section.TLabel").grid(
            row=2, column=0, sticky="w", pady=(0, 10))
        table, self.sales_tree = self._table(self, (
            ("id", "Venta", 90), ("fecha", "Fecha y hora", 300), ("total", "Total", 180)))
        table.grid(row=3, column=0, sticky="nsew")
        self.sales_tree.bind("<<TreeviewSelect>>", lambda event: self.show_details())
        ttk.Label(self, textvariable=self.detail_var, style="Section.TLabel").grid(
            row=4, column=0, sticky="w", pady=(16, 10))
        table, self.details_tree = self._table(self, (
            ("codigo", "Código", 100), ("nombre", "Producto", 260), ("cantidad", "Cantidad", 90),
            ("precio_unitario", "Precio unitario", 150), ("subtotal", "Subtotal", 150)))
        table.grid(row=5, column=0, sticky="nsew")
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel").grid(
            row=6, column=0, sticky="w", pady=(12, 0))
        self.refresh_sales()

    @staticmethod
    def _table(parent, columns):
        frame = ttk.Frame(parent)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(0, weight=1)
        tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings", selectmode="browse", height=4)
        for name, label, width in columns:
            tree.heading(name, text=label, anchor="w")
            tree.column(name, width=width, minwidth=80, anchor="e" if name in ("total", "subtotal", "cantidad", "precio_unitario") else "w")
        tree.grid(row=0, column=0, sticky="nsew")
        scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        scroll.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        tree.configure(yscrollcommand=scroll.set, xscrollcommand=horizontal.set)
        return frame, tree

    def refresh_sales(self, *, notify: bool = True) -> bool:
        try:
            sales = list_sales(self.db_path)
        except (sqlite3.Error, OSError) as error:
            self.status_var.set("No se pudo actualizar el historial. Los datos visibles pueden estar desactualizados.")
            if notify:
                messagebox.showerror("Error de historial", str(error), parent=self)
            return False
        selected = self.sales_tree.selection()
        self.sales_tree.delete(*self.sales_tree.get_children())
        for sale in sales:
            self.sales_tree.insert("", "end", iid=str(sale["id"]), values=(
                sale["id"], format_sale_date(sale["fecha"]), format_price(sale["total"])))
        total = sum(sale["total"] for sale in sales)
        self.summary_var.set(f"{len(sales)} ventas · Total vendido: {format_price(total)}")
        self.status_var.set("Selecciona una venta para consultar sus productos." if sales else "Todavía no hay ventas registradas.")
        if selected and self.sales_tree.exists(selected[0]):
            self.sales_tree.selection_set(selected[0])
        elif sales:
            self.sales_tree.selection_set(str(sales[0]["id"]))
        return self.show_details(notify=notify)

    def show_details(self, *, notify: bool = True) -> bool:
        selected = self.sales_tree.selection()
        if not selected:
            self.details_tree.delete(*self.details_tree.get_children())
            self.detail_var.set("DETALLE DE LA VENTA")
            return True
        try:
            details = get_sale_details(int(selected[0]), self.db_path)
        except (sqlite3.Error, OSError) as error:
            self.details_tree.delete(*self.details_tree.get_children())
            self.detail_var.set("No se pudo cargar el detalle de la venta seleccionada.")
            if notify:
                messagebox.showerror("Error de detalle", str(error), parent=self)
            return False
        self.details_tree.delete(*self.details_tree.get_children())
        for detail in details:
            self.details_tree.insert("", "end", values=(detail["codigo"], detail["nombre"], detail["cantidad"],
                                    format_price(detail["precio_unitario"]), format_price(detail["subtotal"])))
        self.detail_var.set(f"DETALLE DE LA VENTA #{selected[0]}")
        return True
