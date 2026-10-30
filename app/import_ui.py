"""Vista previa ETL y confirmación explícita de una carga de productos."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from app.imports import (HEADERS, STATUS_LABELS, ImportPreview, export_import_report,
                         load_import, preview_import, write_product_template)
from app.theme import BLACK, BLUE, PALE_BLUE, WHITE
from app.validation import ValidationError, price_to_input


class ImportFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, db_path: Path, on_loaded: Callable[[], bool]):
        super().__init__(master, padding=(28, 18))
        self.db_path, self.on_loaded = db_path, on_loaded
        self.preview: ImportPreview | None = None
        self.source_path: Path | None = None
        self._loading = False
        self.file_var = tk.StringVar(master=self, value="Ningún archivo seleccionado")
        self.summary_var = tk.StringVar(master=self, value="Abre un CSV para revisar sus filas antes de cargar.")
        self.status_var = tk.StringVar(master=self)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(5, weight=1)

        ttk.Label(self, text="Importar productos", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(self, text="1 · Extraer CSV  →  2 · Validar y normalizar  →  3 · Cargar nuevos",
                  foreground=BLUE).grid(row=1, column=0, sticky="w", pady=(4, 8))
        ttk.Label(self, text="CSV UTF-8 con ; · columnas: codigo, nombre, precio, stock · máximo 2 MiB / 2000 filas\n"
                            "Los códigos existentes se omiten y conservan sus datos. Corrige todas las filas con error antes de cargar.",
                  style="Muted.TLabel").grid(row=2, column=0, sticky="w", pady=(0, 12))
        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="ew", pady=(0, 10))
        self.open_button = ttk.Button(actions, text="Abrir CSV", command=self.open_csv)
        self.open_button.grid(row=0, column=0, padx=(0, 8))
        self.template_button = ttk.Button(actions, text="Guardar plantilla", command=self.save_template)
        self.template_button.grid(row=0, column=1, padx=(0, 8))
        self.report_button = ttk.Button(actions, text="Exportar informe", command=self.save_report)
        self.report_button.grid(row=0, column=2, padx=(0, 8))
        self.load_button = ttk.Button(actions, text="Cargar nuevos productos", style="Accent.TButton", command=self.load_preview)
        self.load_button.grid(row=0, column=3)
        summary = ttk.Frame(self)
        summary.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(summary, textvariable=self.file_var, style="Section.TLabel", wraplength=920).grid(row=0, column=0, sticky="w")
        ttk.Label(summary, textvariable=self.summary_var, style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 0))

        table = ttk.Frame(self)
        table.grid(row=5, column=0, sticky="nsew")
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        columns = ("line", "status", "code", "name", "price", "stock", "detail")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse", height=4)
        for column, title, width in zip(columns, ("Fila", "Estado", "Código", "Nombre", "Precio", "Stock", "Detalle"),
                                         (55, 90, 110, 180, 100, 70, 290)):
            self.tree.heading(column, text=title, anchor="w")
            self.tree.column(column, width=width, minwidth=width, stretch=column in ("name", "detail"))
        self.tree.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(table, orient="horizontal", command=self.tree.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.tree.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.tree.tag_configure("error", background=BLACK, foreground=WHITE)
        self.tree.tag_configure("new", background=PALE_BLUE, foreground=BLACK)
        self.tree.tag_configure("loaded", background=PALE_BLUE, foreground=BLACK)
        self.tree.bind("<<TreeviewSelect>>", lambda event: self._show_row())

        self.detail = tk.Text(self, height=4, width=1, wrap="word", state="disabled",
                              background=WHITE, foreground=BLACK, font=("Segoe UI", 10),
                              highlightbackground=PALE_BLUE, highlightcolor=BLUE, highlightthickness=1,
                              selectbackground=BLUE, selectforeground=WHITE)
        self.detail.grid(row=6, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", wraplength=920).grid(
            row=7, column=0, sticky="w", pady=(10, 0))
        self._sync_buttons()

    def _sync_buttons(self) -> None:
        for button in (self.open_button, self.template_button):
            button.state(["disabled"] if self._loading else ["!disabled"])
        self.report_button.state(["!disabled"] if self.preview is not None and not self._loading else ["disabled"])
        self.load_button.state(["!disabled"] if self.preview is not None and self.preview.can_load and not self._loading else ["disabled"])

    def open_csv(self) -> None:
        if self._loading:
            return
        source = filedialog.askopenfilename(parent=self, title="Seleccionar productos CSV",
                                             filetypes=[("Archivo CSV", "*.csv")])
        if source:
            self.source_path = Path(source).resolve()
            self.revalidate()

    def revalidate(self) -> None:
        if self._loading or self.source_path is None:
            return
        self.preview = None  # Un archivo nuevo inválido nunca deja cargable el anterior.
        self.file_var.set(self.source_path.name)
        self._render()
        try:
            self.preview = preview_import(self.source_path, self.db_path)
        except (ValidationError, sqlite3.Error, OSError) as error:
            self.status_var.set(f"Archivo no validado: {error}")
            messagebox.showerror("No se pudo revisar el CSV", str(error), parent=self)
        else:
            self.status_var.set("Vista previa sin cambios en la base. Revisa las filas y confirma la carga de nuevos productos.")
        self._render()

    def _render(self) -> None:
        self.tree.delete(*self.tree.get_children())
        if self.preview is None:
            self.summary_var.set("Sin vista previa válida")
        else:
            loaded = sum(row.status == "loaded" for row in self.preview.rows)
            self.summary_var.set(f"{len(self.preview.rows)} filas · {self.preview.new_count} nuevos · "
                                 f"{self.preview.existing_count} existentes · {self.preview.error_count} errores · {loaded} cargados")
            for index, row in enumerate(self.preview.rows):
                code, name, price, stock = row.values if row.values is not None else ("", "", None, "")
                self.tree.insert("", "end", iid=str(index), values=(row.line, STATUS_LABELS[row.status], code,
                    name, price_to_input(price) if price is not None else "", stock, row.message), tags=(row.status,))
            errors = [index for index, row in enumerate(self.preview.rows) if row.status == "error"]
            if self.preview.rows:
                self.tree.selection_set(str(errors[0] if errors else 0))
        self._show_row()
        self._sync_buttons()

    def _show_row(self) -> None:
        selected = self.tree.selection()
        text = "Selecciona una fila para ver los valores originales y el resultado."
        if selected and self.preview is not None:
            row = self.preview.rows[int(selected[0])]
            # Solo las filas de ancho válido están en el orden canónico HEADERS.
            # En filas mal formadas conservamos TODAS las columnas físicas.
            labels = HEADERS if len(row.raw) == len(HEADERS) else tuple(
                f"columna {index + 1}" for index in range(len(row.raw)))
            originals = " | ".join(f"{key}: {value!r}" for key, value in zip(labels, row.raw))
            text = f"Fila {row.line} · {STATUS_LABELS[row.status]}\nOriginal: {originals}\n{row.message}"
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", text)
        self.detail.configure(state="disabled")

    def load_preview(self) -> None:
        if self._loading or self.preview is None or not self.preview.can_load:
            return
        self._loading = True
        self._sync_buttons()
        try:
            if not messagebox.askyesno("Confirmar importación", f"¿Cargar {self.preview.new_count} productos nuevos?\n\n"
                                       "Los códigos existentes se omiten. Se cargan los valores de esta vista previa.",
                                       parent=self, default="no"):
                return
            try:
                count = load_import(self.preview, self.db_path)
            except (ValidationError, sqlite3.Error, OSError) as error:
                self.status_var.set(f"No se cargaron productos. {error}")
                messagebox.showerror("Carga no realizada", str(error), parent=self)
                return
            # Marcar aplicada ANTES de refrescar otras vistas o mostrar diálogos.
            self.preview = replace(self.preview, rows=tuple(
                replace(row, status="loaded", message="Producto cargado correctamente.") if row.status == "new" else row
                for row in self.preview.rows))
            self._render()
            try:
                fresh = self.on_loaded()
            except (sqlite3.Error, OSError):
                fresh = False
            if fresh is False:
                self.status_var.set(f"Importación guardada: {count} productos. Pulsa Actualizar en las vistas; no repitas la carga.")
                messagebox.showwarning("Importación guardada", self.status_var.get(), parent=self)
            else:
                self.status_var.set(f"Importación guardada: {count} productos. Inventario, POS y gráficos actualizados.")
                messagebox.showinfo("Importación completada", self.status_var.get(), parent=self)
        finally:
            self._loading = False
            self._sync_buttons()

    def _save(self, report: bool) -> None:
        if self._loading or (report and self.preview is None):
            return
        chosen = filedialog.asksaveasfilename(parent=self, title="Guardar informe" if report else "Guardar plantilla",
            initialfile="informe_importacion.csv" if report else "plantilla_productos.csv", defaultextension=".csv",
            filetypes=[("Archivo CSV", "*.csv")], confirmoverwrite=True)
        if not chosen:
            return
        try:
            if report:
                export_import_report(self.preview, Path(chosen), self.db_path)
            else:
                write_product_template(Path(chosen), self.db_path, source=self.source_path)
        except (ValidationError, sqlite3.Error, OSError) as error:
            messagebox.showerror("No se pudo guardar el CSV", str(error), parent=self)
            return
        messagebox.showinfo("CSV guardado", f"Archivo guardado en:\n{chosen}\n\nUTF-8; separador: punto y coma (;).", parent=self)

    def save_template(self) -> None:
        self._save(False)

    def save_report(self) -> None:
        self._save(True)
