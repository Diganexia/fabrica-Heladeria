import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from ui.theme import *
from db import database as db

PERIODOS = ["mensual", "diario"]


def _fmt(v):
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ScreenGastos(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.app = app
        self._selected_id = None
        self._all_rows = []
        self._build()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #
    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(24, 0))

        ctk.CTkLabel(
            header, text="Gastos variables",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nuevo gasto",
            fg_color=C_ACCENT, hover_color=C_BTN_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=150, height=36, corner_radius=8,
            command=self._new,
        ).pack(side="right")

        ctk.CTkLabel(
            self,
            text="Luz, gas, empleados y otros gastos del período. Se prorratean sobre los kg producidos.",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=30, pady=(2, 14))

        self._build_summary()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        self._build_table(body)
        self._build_panel(body)

    # ------------------------------------------------------------------ #
    # Card resumen                                                         #
    # ------------------------------------------------------------------ #
    def _build_summary(self):
        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=12,
                            border_width=1, border_color=C_BORDER)
        card.pack(fill="x", padx=30, pady=(0, 14))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=20, pady=12)

        ctk.CTkLabel(
            inner, text="Gasto variable total por kg producido:",
            font=ctk.CTkFont(family="Segoe UI", size=13), text_color=C_MUTED,
        ).pack(side="left")

        self._lbl_gv_kg = ctk.CTkLabel(
            inner, text="$0,00",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=C_WARN,
        )
        self._lbl_gv_kg.pack(side="left", padx=12)

        ctk.CTkLabel(
            inner, text="= Σ gastos ÷ kg producidos",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=C_MUTED,
        ).pack(side="left")

    # ------------------------------------------------------------------ #
    # Tabla con búsqueda                                                   #
    # ------------------------------------------------------------------ #
    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        search_row = ctk.CTkFrame(frame, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        ctk.CTkLabel(search_row, text="Buscar:",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(side="left", padx=(4, 6))
        self._var_search = tk.StringVar()
        self._var_search.trace_add("write", lambda *_: self._filter_table())
        ctk.CTkEntry(
            search_row, textvariable=self._var_search,
            placeholder_text="Concepto...",
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=12),
            height=32, corner_radius=6, width=280,
        ).pack(side="left")

        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        style = ttk.Style()
        style.configure("Gas.Treeview",
            background=C_CARD, fieldbackground=C_CARD,
            foreground=C_TEXT, rowheight=36,
            font=("Segoe UI", 12), borderwidth=0,
        )
        style.configure("Gas.Treeview.Heading",
            background=C_HEADING_BG, foreground=C_TEXT_LIGHT,
            font=("Segoe UI", 11, "bold"), relief="flat",
        )
        style.map("Gas.Treeview",
            background=[("selected", C_ROW_SEL)],
            foreground=[("selected", C_TEXT)],
        )
        style.layout("Gas.Treeview", [("Gas.Treeview.treearea", {"sticky": "nsew"})])

        cols = ("nombre", "monto", "periodo", "produccion_kg", "gv_kg")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Gas.Treeview", selectmode="browse")
        self._tree.heading("nombre",        text="Concepto")
        self._tree.heading("monto",         text="Monto")
        self._tree.heading("periodo",       text="Período")
        self._tree.heading("produccion_kg", text="Producción (kg)")
        self._tree.heading("gv_kg",         text="$ / kg")
        self._tree.column("nombre",        width=180, anchor="w")
        self._tree.column("monto",         width=120, anchor="e")
        self._tree.column("periodo",       width=90,  anchor="center")
        self._tree.column("produccion_kg", width=140, anchor="e")
        self._tree.column("gv_kg",         width=100, anchor="e")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tree.tag_configure("alt", background=C_ROW_ALT)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    # ------------------------------------------------------------------ #
    # Panel formulario                                                     #
    # ------------------------------------------------------------------ #
    def _build_panel(self, parent):
        self._panel = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                                   border_width=1, border_color=C_BORDER, width=280)
        self._panel.grid(row=0, column=1, sticky="nsew")
        self._panel.pack_propagate(False)

        ctk.CTkLabel(
            self._panel, text="Detalle",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(18, 12))

        self._var_nombre     = tk.StringVar()
        self._var_monto      = tk.StringVar()
        self._var_periodo    = tk.StringVar(value=PERIODOS[0])
        self._var_produccion = tk.StringVar()

        self._entry_nombre = self._field(self._panel, "Concepto",       self._var_nombre)
        self._entry_monto  = self._field(self._panel, "Monto ($)",      self._var_monto)
        self._dropdown(self._panel, "Período",                          self._var_periodo)
        self._entry_prod   = self._field(self._panel, "Producción (kg)", self._var_produccion)

        ctk.CTkLabel(
            self._panel, text="Kg producidos en el período indicado.",
            font=ctk.CTkFont(family="Segoe UI", size=10), text_color=C_MUTED,
        ).pack(anchor="w", padx=20)

        self._lbl_error = ctk.CTkLabel(
            self._panel, text="", text_color=C_DANGER,
            font=ctk.CTkFont(family="Segoe UI", size=11), wraplength=240,
        )
        self._lbl_error.pack(anchor="w", padx=20, pady=(6, 0))

        btns = ctk.CTkFrame(self._panel, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(12, 0))

        self._btn_save = ctk.CTkButton(
            btns, text="Guardar",
            fg_color=C_SUCCESS, hover_color="#15803d",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=38, corner_radius=8, command=self._save,
        )
        self._btn_save.pack(fill="x", pady=(0, 6))

        self._btn_delete = ctk.CTkButton(
            btns, text="Eliminar",
            fg_color=C_DANGER, hover_color="#b91c1c",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=38, corner_radius=8, command=self._delete, state="disabled",
        )
        self._btn_delete.pack(fill="x", pady=(0, 6))

        ctk.CTkButton(
            btns, text="Cancelar",
            fg_color=C_INPUT_BG, hover_color=C_BORDER, text_color=C_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=38, corner_radius=8, command=self._cancel,
        ).pack(fill="x")

    def _field(self, parent, label, var):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(anchor="w", padx=20, pady=(8, 0))
        e = ctk.CTkEntry(
            parent, textvariable=var,
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36, corner_radius=6,
        )
        e.pack(fill="x", padx=20, pady=(2, 0))
        e._entry.bind("<Return>", lambda ev: self._save())
        e._entry.bind("<Escape>", lambda ev: self._cancel())
        return e

    def _dropdown(self, parent, label, var):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(anchor="w", padx=20, pady=(8, 0))
        ctk.CTkOptionMenu(
            parent, variable=var, values=PERIODOS,
            fg_color=C_INPUT_BG, button_color=C_BORDER,
            button_hover_color=C_ACCENT, text_color=C_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=6, height=36,
        ).pack(fill="x", padx=20, pady=(2, 0))

    # ------------------------------------------------------------------ #
    # Estado del panel                                                     #
    # ------------------------------------------------------------------ #
    def _set_panel_empty(self):
        self._selected_id = None
        self._var_nombre.set("")
        self._var_monto.set("")
        self._var_periodo.set(PERIODOS[0])
        self._var_produccion.set("")
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="disabled")

    def _set_panel_from_row(self, row):
        self._selected_id = row["id"]
        self._var_nombre.set(row["nombre"])
        self._var_monto.set(str(row["monto"]))
        self._var_periodo.set(row["periodo"])
        self._var_produccion.set(str(row["produccion_kg"]))
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="normal")

    # ------------------------------------------------------------------ #
    # Eventos                                                              #
    # ------------------------------------------------------------------ #
    def _on_select(self, _=None):
        sel = self._tree.selection()
        if not sel:
            return
        row = next((r for r in self._all_rows if str(r["id"]) == sel[0]), None)
        if row:
            self._set_panel_from_row(row)

    def _new(self):
        self._tree.selection_remove(self._tree.selection())
        self._set_panel_empty()
        self._entry_nombre.focus()

    def _cancel(self):
        self._tree.selection_remove(self._tree.selection())
        self._set_panel_empty()

    # ------------------------------------------------------------------ #
    # Validación y CRUD                                                    #
    # ------------------------------------------------------------------ #
    def _validate(self):
        nombre = self._var_nombre.get().strip()
        monto_str = self._var_monto.get().strip().replace(",", ".")
        prod_str  = self._var_produccion.get().strip().replace(",", ".")
        if not nombre:
            self._lbl_error.configure(text="El concepto no puede estar vacío.")
            return None, None, None, None
        try:
            monto = float(monto_str)
            if monto <= 0:
                raise ValueError
        except ValueError:
            self._lbl_error.configure(text="El monto debe ser un número mayor a cero.")
            return None, None, None, None
        try:
            produccion = float(prod_str)
            if produccion <= 0:
                raise ValueError
        except ValueError:
            self._lbl_error.configure(text="La producción debe ser un número mayor a cero.")
            return None, None, None, None
        self._lbl_error.configure(text="")
        return nombre, monto, self._var_periodo.get(), produccion

    def _save(self):
        nombre, monto, periodo, produccion = self._validate()
        if nombre is None:
            return
        if self._selected_id is None:
            db.add_gasto(nombre, monto, periodo, produccion)
            self.app.show_toast(f"'{nombre}' agregado correctamente.")
        else:
            db.update_gasto(self._selected_id, nombre, monto, periodo, produccion)
            self.app.show_toast(f"'{nombre}' actualizado.")
        self._cancel()
        self._load_table()
        self.app.refresh_metrics()

    def _delete(self):
        if self._selected_id is None:
            return
        nombre = self._var_nombre.get()
        if not messagebox.askyesno("Eliminar gasto", f"¿Eliminás '{nombre}'?"):
            return
        db.delete_gasto(self._selected_id)
        self.app.show_toast(f"'{nombre}' eliminado.", kind="info")
        self._cancel()
        self._load_table()
        self.app.refresh_metrics()

    # ------------------------------------------------------------------ #
    # Tabla                                                                #
    # ------------------------------------------------------------------ #
    def _load_table(self):
        self._all_rows = list(db.get_gastos())
        self._filter_table()
        gv = db.get_gasto_variable_por_kg()
        self._lbl_gv_kg.configure(text=_fmt(gv))

    def _filter_table(self):
        query = self._var_search.get().strip().lower()
        for item in self._tree.get_children():
            self._tree.delete(item)
        rows = [r for r in self._all_rows if query in r["nombre"].lower()] if query else self._all_rows
        for i, row in enumerate(rows):
            gv_kg = row["monto"] / row["produccion_kg"] if row["produccion_kg"] else 0
            tag = "alt" if i % 2 else ""
            self._tree.insert("", "end", iid=str(row["id"]),
                              values=(row["nombre"], _fmt(row["monto"]), row["periodo"],
                                      f"{row['produccion_kg']:,.0f} kg".replace(",", "."),
                                      _fmt(gv_kg)),
                              tags=(tag,))

    def on_show(self):
        self._load_table()
        self._set_panel_empty()
