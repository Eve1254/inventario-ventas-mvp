"""Paleta compartida: azul, negro y blanco, con tintes de azul."""

import tkinter as tk
from tkinter import ttk

BLUE = "#1456d8"
DARK_BLUE = "#103d99"
PALE_BLUE = "#e8f0ff"
BLACK = "#000000"
WHITE = "#ffffff"


def configure_theme(root: tk.Tk) -> None:
    root.configure(background=WHITE)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=WHITE, foreground=BLACK, font=("Segoe UI", 11),
                    bordercolor=PALE_BLUE, lightcolor=WHITE, darkcolor=WHITE,
                    focuscolor=BLUE, troughcolor=WHITE, selectbackground=BLUE, selectforeground=WHITE)
    style.configure("TFrame", background=WHITE)
    style.configure("TLabel", background=WHITE, foreground=BLACK)
    style.configure("Title.TLabel", font=("Segoe UI", 26, "bold"))
    style.configure("Muted.TLabel", foreground=BLACK, font=("Segoe UI", 10))
    style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"))
    style.configure("Metric.TLabel", foreground=BLUE, font=("Segoe UI", 16, "bold"))
    style.configure("TButton", font=("Segoe UI", 10), padding=(10, 7), bordercolor=BLUE)
    style.map("TButton", background=[("disabled", PALE_BLUE), ("pressed", BLACK), ("active", BLUE)],
              foreground=[("disabled", DARK_BLUE), ("pressed", WHITE), ("active", WHITE)])
    style.configure("Accent.TButton", background=BLUE, foreground=WHITE,
                    font=("Segoe UI", 11, "bold"), padding=(18, 11), borderwidth=0)
    style.map("Accent.TButton", background=[("disabled", PALE_BLUE), ("pressed", BLACK), ("active", DARK_BLUE)],
              foreground=[("disabled", DARK_BLUE), ("!disabled", WHITE)])
    style.configure("TEntry", fieldbackground=WHITE, foreground=BLACK, insertcolor=BLACK, bordercolor=BLUE)
    style.map("TEntry", fieldbackground=[("disabled", PALE_BLUE)],
              bordercolor=[("focus", BLUE)], lightcolor=[("focus", BLUE)], darkcolor=[("focus", BLUE)])
    style.configure("TNotebook", background=WHITE, borderwidth=0)
    style.configure("TNotebook.Tab", background=WHITE, foreground=BLACK, padding=(20, 10))
    style.map("TNotebook.Tab", background=[("selected", BLUE), ("active", PALE_BLUE)],
              foreground=[("selected", WHITE), ("active", BLACK)])
    style.configure("Treeview", background=WHITE, fieldbackground=WHITE, foreground=BLACK,
                    font=("Segoe UI", 11), rowheight=40, borderwidth=0)
    style.configure("Treeview.Heading", background=BLACK, foreground=WHITE,
                    font=("Segoe UI", 10, "bold"), padding=(12, 12), relief="flat")
    style.map("Treeview.Heading", background=[("active", DARK_BLUE)], foreground=[("active", WHITE)])
    style.map("Treeview", background=[("selected", BLUE)], foreground=[("selected", WHITE)])
    style.configure("TScrollbar", background=PALE_BLUE, arrowcolor=BLACK)
    style.map("TScrollbar", background=[("pressed", DARK_BLUE), ("active", BLUE)],
              arrowcolor=[("pressed", WHITE), ("active", WHITE)])
