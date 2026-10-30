"""Gráficos de barras sin dependencias externas; SQLite es su fuente real."""

from datetime import datetime
from pathlib import Path
import sqlite3
import tkinter as tk
from tkinter import font as tkfont, messagebox, ttk

from app.charts import ChartData, load_chart_data
from app.theme import BLACK, BLUE, WHITE
from app.validation import format_price


class ChartsFrame(ttk.Frame):
    def __init__(self, master: ttk.Notebook, db_path: Path):
        super().__init__(master, padding=(28, 20))
        self.db_path = db_path
        self.data: ChartData | None = None
        self.status_var = tk.StringVar(master=self)
        self.period_var = tk.StringVar(master=self)
        self.product_var = tk.StringVar(master=self, value="—")
        self.low_var = tk.StringVar(master=self, value="—")
        self.total_var = tk.StringVar(master=self, value="—")
        self.chart_font = tkfont.Font(root=self, family="Segoe UI", size=10)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        heading = ttk.Frame(self)
        heading.grid(row=0, column=0, sticky="ew")
        heading.columnconfigure(0, weight=1)
        ttk.Label(heading, text="Gráficos", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        self.refresh_button = ttk.Button(heading, text="Actualizar gráficos", command=self.refresh)
        self.refresh_button.grid(row=0, column=1, sticky="e")
        ttk.Label(self, text="Existencias actuales y ventas confirmadas · hora local del equipo",
                  style="Muted.TLabel").grid(row=1, column=0, sticky="w", pady=(4, 14))

        metrics = ttk.Frame(self)
        metrics.grid(row=2, column=0, sticky="ew", pady=(0, 20))
        for column, (label, variable) in enumerate((
            ("PRODUCTOS", self.product_var), ("CON STOCK MENOR A 5", self.low_var),
            ("VENTAS · ÚLTIMOS 7 DÍAS", self.total_var),
        )):
            metrics.columnconfigure(column, weight=1, uniform="metric")
            box = ttk.Frame(metrics)
            box.grid(row=0, column=column, sticky="nw")
            ttk.Label(box, text=label, style="Section.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(box, textvariable=variable, style="Metric.TLabel", wraplength=300).grid(row=1, column=0, sticky="w")

        panels = ttk.Frame(self)
        panels.grid(row=3, column=0, sticky="nsew")
        panels.rowconfigure(0, weight=1)
        for column in range(2):
            panels.columnconfigure(column, weight=1, uniform="chart")
        self.stock_canvas = self._panel(panels, 0, "Existencias por producto", "10 con menor stock · unidades")
        self.sales_canvas = self._panel(panels, 1, "Ventas por día", self.period_var)
        ttk.Label(self, textvariable=self.status_var, style="Muted.TLabel", wraplength=940).grid(
            row=4, column=0, sticky="w", pady=(12, 0))
        self.refresh()

    def _panel(self, parent, column, title, subtitle) -> tk.Canvas:
        panel = ttk.Frame(parent, padding=(0 if column == 0 else 12, 0, 12 if column == 0 else 0, 0))
        panel.grid(row=0, column=column, sticky="nsew")
        panel.columnconfigure(0, weight=1)
        panel.rowconfigure(2, weight=1)
        ttk.Label(panel, text=title, style="Section.TLabel").grid(row=0, column=0, sticky="w")
        options = {"textvariable": subtitle} if isinstance(subtitle, tk.StringVar) else {"text": subtitle}
        ttk.Label(panel, style="Muted.TLabel", **options).grid(row=1, column=0, sticky="w", pady=(4, 10))
        canvas = tk.Canvas(panel, background=WHITE, highlightthickness=0, width=200, height=340)
        canvas.grid(row=2, column=0, sticky="nsew")
        canvas.bind("<Configure>", lambda event: self._redraw())
        return canvas

    def refresh(self, *, notify: bool = True) -> bool:
        try:
            data = load_chart_data(self.db_path)
        except (sqlite3.Error, OSError, ValueError, OverflowError) as error:
            self.status_var.set("No se pudo actualizar. Los gráficos visibles pueden estar desactualizados. Pulsa F5.")
            if notify:
                messagebox.showerror("No se pudieron leer los gráficos", str(error), parent=self)
            return False
        # No reemplazar una mitad de la vista si la otra lectura falló.
        self.data = data
        self.product_var.set(str(data.product_count))
        self.low_var.set(str(data.low_stock_count))
        self.total_var.set(format_price(data.sales_total_cents))
        self.period_var.set(f"{data.sales[0].day:%d/%m/%Y} – {data.sales[-1].day:%d/%m/%Y} · importe")
        self.status_var.set(f"{data.unit_count} unidades en catálogo · {data.sales_count} ventas en el período · Actualizado {datetime.now():%H:%M:%S}")
        self._redraw()
        return True

    def _fit_label(self, text: str, width: int) -> str:
        text = " ".join(text.split())
        if self.chart_font.measure(text) <= width:
            return text
        while text and self.chart_font.measure(text + "…") > width:
            text = text[:-1]
        return text + "…"

    def _bars(self, canvas: tk.Canvas, labels: list[str], values: list[int], display: list[str], *, empty: str) -> None:
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 40 or height < 40:
            return  # Configure vuelve a dibujar cuando la pestaña recibe espacio.
        if not labels:
            canvas.create_text(12, 30, text=empty, anchor="w", fill=BLACK, font=self.chart_font, tags="label")
            return
        value_width = max(self.chart_font.measure(value) for value in display) + 16
        label_width = min(170, int(width * 0.36))
        start = label_width + 8
        end = max(start + 1, width - value_width - 8)
        maximum = max(values) or 1
        top, bottom = 26, height - 12
        step = (bottom - top) / len(labels)
        bar_height = min(22, step * 0.62)
        canvas.create_line(start, top - 10, start, bottom, fill=BLACK)
        canvas.create_text(start, 8, text="0", fill=BLACK, font=self.chart_font, tags="label")
        for index, (label, value, amount) in enumerate(zip(labels, values, display)):
            y = top + step * (index + 0.5)
            canvas.create_text(0, y, text=self._fit_label(label, label_width), anchor="w",
                               fill=BLACK, font=self.chart_font, tags="label")
            # Solo las coordenadas usan float; importes y etiquetas son enteros exactos.
            if value:
                canvas.create_rectangle(start, y - bar_height / 2,
                                        start + (end - start) * (value / maximum), y + bar_height / 2,
                                        fill=BLUE, outline="", tags="bar")
            canvas.create_text(width - 8, y, text=amount, anchor="e", fill=BLACK,
                               font=self.chart_font, tags="value")

    def _redraw(self) -> None:
        if self.data is None:
            return
        self._bars(self.stock_canvas, [f"{point.code} · {point.name}" for point in self.data.stock],
                   [point.units for point in self.data.stock], [str(point.units) for point in self.data.stock],
                   empty="Sin productos registrados")
        self._bars(self.sales_canvas, [f"{point.day:%d/%m}" for point in self.data.sales],
                   [point.total_cents for point in self.data.sales],
                   [format_price(point.total_cents) for point in self.data.sales], empty="Sin ventas")
