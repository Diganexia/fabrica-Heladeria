import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ui.theme import *
from db import database as db

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _fmt(v):
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _only_numeric(P):
    return P == "" or all(c in "0123456789.," for c in P)


class ScreenGastos(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.app = app
        self._selected_id = None
        self._all_rows = []
        self._current_periodo_id = None
        self._build()

    # ------------------------------------------------------------------ #
    # Layout principal                                                     #
    # ------------------------------------------------------------------ #
    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(16, 0))

        ctk.CTkLabel(
            header, text="Gastos variables",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")

        self._btn_nuevo = ctk.CTkButton(
            header, text="+ Nuevo gasto",
            fg_color=C_ACCENT, hover_color=C_BTN_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=150, height=36, corner_radius=8,
            command=self._new,
        )
        self._btn_nuevo.pack(side="right")

        ctk.CTkLabel(
            self,
            text="Registrá los gastos del mes (luz, gas, empleados, etc.) junto con los kg producidos.",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=30, pady=(2, 6))

        self._build_period_bar()
        self._build_summary()

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        self._build_table(body)
        self._build_panel(body)

    # ------------------------------------------------------------------ #
    # Barra de período                                                     #
    # ------------------------------------------------------------------ #
    def _build_period_bar(self):
        bar = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=12,
                           border_width=1, border_color=C_BORDER, height=58)
        bar.pack(fill="x", padx=30, pady=(0, 8))
        bar.pack_propagate(False)

        inner = ctk.CTkFrame(bar, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=8)

        ctk.CTkLabel(
            inner, text="Período:",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left", padx=(0, 8))

        self._var_mes = tk.StringVar(value=MESES[datetime.now().month - 1])
        ctk.CTkOptionMenu(
            inner, variable=self._var_mes, values=MESES,
            fg_color=C_INPUT_BG, button_color=C_BORDER,
            button_hover_color=C_ACCENT, text_color=C_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            corner_radius=6, height=34, width=130,
            command=lambda _: self._on_periodo_change(),
        ).pack(side="left", padx=(0, 6))

        self._var_anio = tk.StringVar(value=str(datetime.now().year))
        vcmd_year = (self.register(lambda P: P == "" or P.isdigit()), "%P")
        anio_entry = ctk.CTkEntry(
            inner, textvariable=self._var_anio,
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=13),
            height=34, corner_radius=6, width=70,
        )
        anio_entry.pack(side="left", padx=(0, 16))
        anio_entry._entry.configure(validate="key", validatecommand=vcmd_year)
        anio_entry._entry.bind("<Return>", lambda _: self._on_periodo_change())
        anio_entry._entry.bind("<FocusOut>", lambda _: self._on_periodo_change())

        ctk.CTkLabel(
            inner, text="|",
            font=ctk.CTkFont(family="Segoe UI", size=18),
            text_color=C_BORDER,
        ).pack(side="left", padx=(0, 16))

        ctk.CTkLabel(
            inner, text="Kg producidos este mes:",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=C_TEXT,
        ).pack(side="left", padx=(0, 8))

        vcmd_num = (self.register(_only_numeric), "%P")
        self._var_kg = tk.StringVar()
        self._entry_kg = ctk.CTkEntry(
            inner, textvariable=self._var_kg,
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=13),
            height=34, corner_radius=6, width=110,
        )
        self._entry_kg.pack(side="left", padx=(0, 10))
        self._entry_kg._entry.configure(validate="key", validatecommand=vcmd_num)
        self._entry_kg._entry.bind("<Return>", lambda _: self._save_periodo())

        ctk.CTkButton(
            inner, text="Guardar período",
            fg_color=C_ACCENT, hover_color=C_BTN_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=34, corner_radius=6, width=140,
            command=self._save_periodo,
        ).pack(side="left", padx=(0, 12))

        self._lbl_periodo_status = ctk.CTkLabel(
            inner, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=C_MUTED,
        )
        self._lbl_periodo_status.pack(side="left")

    # ------------------------------------------------------------------ #
    # Card resumen (una sola línea horizontal)                            #
    # ------------------------------------------------------------------ #
    def _build_summary(self):
        card = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=12,
                            border_width=1, border_color=C_BORDER, height=56)
        card.pack(fill="x", padx=30, pady=(0, 10))
        card.pack_propagate(False)

        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=10)

        ctk.CTkLabel(
            row, text="Este mes:",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(side="left", padx=(0, 6))

        self._lbl_periodo_costo = ctk.CTkLabel(
            row, text="—",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=C_WARN,
        )
        self._lbl_periodo_costo.pack(side="left")

        ctk.CTkLabel(
            row, text=" / kg",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(side="left", padx=(2, 18))

        ctk.CTkFrame(row, fg_color=C_BORDER, width=1, corner_radius=0).pack(
            side="left", fill="y", padx=6
        )

        ctk.CTkLabel(
            row, text="Promedio histórico (recetas):",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(side="left", padx=(10, 6))

        self._lbl_hist_costo = ctk.CTkLabel(
            row, text="—",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color=C_TEXT,
        )
        self._lbl_hist_costo.pack(side="left")

        ctk.CTkLabel(
            row, text=" / kg",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(side="left", padx=(2, 10))

        self._lbl_hist_meses = ctk.CTkLabel(
            row, text="",
            font=ctk.CTkFont(family="Segoe UI", size=11), text_color=C_MUTED,
        )
        self._lbl_hist_meses.pack(side="left")

    # ------------------------------------------------------------------ #
    # Tabla                                                                #
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

        cols = ("nombre", "monto")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Gas.Treeview", selectmode="browse")
        self._tree.heading("nombre", text="Concepto")
        self._tree.heading("monto",  text="Monto")
        self._tree.column("nombre", width=300, anchor="w")
        self._tree.column("monto",  width=160, anchor="e")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tree.tag_configure("alt", background=C_ROW_ALT)
        self._tree.bind("<<TreeviewSelect>>", self._on_select)

    # ------------------------------------------------------------------ #
    # Panel formulario (botones fijos abajo, campos scrolleables)         #
    # ------------------------------------------------------------------ #
    def _build_panel(self, parent):
        outer = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER, width=280)
        outer.grid(row=0, column=1, sticky="nsew")
        outer.pack_propagate(False)

        # Botones fijos al fondo — se packean PRIMERO para que siempre sean visibles
        btns = ctk.CTkFrame(outer, fg_color="transparent")
        btns.pack(side="bottom", fill="x", padx=20, pady=(0, 12))

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

        self._lbl_error = ctk.CTkLabel(
            outer, text="", text_color=C_DANGER,
            font=ctk.CTkFont(family="Segoe UI", size=11), wraplength=240,
        )
        self._lbl_error.pack(side="bottom", anchor="w", padx=20, pady=(0, 4))

        # Título y campos (se packean desde arriba; si la ventana es muy chica
        # los campos se cortan, pero los botones de abajo siempre se ven)
        ctk.CTkLabel(
            outer, text="Detalle",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(18, 4))

        self._var_nombre = tk.StringVar()
        self._var_monto  = tk.StringVar()

        vcmd_num = (self.register(_only_numeric), "%P")

        self._entry_nombre = self._field(outer, "Concepto", self._var_nombre)
        self._entry_monto  = self._field(outer, "Monto ($)", self._var_monto)
        self._entry_monto._entry.configure(validate="key", validatecommand=vcmd_num)

    def _field(self, parent, label, var):
        ctk.CTkLabel(parent, text=label,
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(anchor="w", padx=20, pady=(10, 0))
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

    # ------------------------------------------------------------------ #
    # Lógica de período                                                    #
    # ------------------------------------------------------------------ #
    def _on_periodo_change(self, _=None):
        mes_nombre = self._var_mes.get()
        mes = MESES.index(mes_nombre) + 1
        try:
            anio = int(self._var_anio.get())
        except ValueError:
            return

        periodo = db.get_periodo_by_mes_anio(mes, anio)
        if periodo:
            self._current_periodo_id = periodo["id"]
            kg = periodo["kg_prod"]
            self._var_kg.set(str(int(kg)) if kg == int(kg) else str(kg))
            self._lbl_periodo_status.configure(text="Período cargado", text_color=C_SUCCESS)
        else:
            self._current_periodo_id = None
            self._var_kg.set("")
            self._lbl_periodo_status.configure(text="Sin datos — ingresá los kg y guardá", text_color=C_MUTED)

        self._load_table()
        self._update_summary()

    def _save_periodo(self):
        mes_nombre = self._var_mes.get()
        mes = MESES.index(mes_nombre) + 1
        try:
            anio = int(self._var_anio.get())
            if not (2000 <= anio <= 2099):
                raise ValueError
        except ValueError:
            self.app.show_toast("El año debe ser un número entre 2000 y 2099.", kind="error")
            return

        kg_str = self._var_kg.get().strip().replace(",", ".")
        try:
            kg = float(kg_str)
            if kg <= 0:
                raise ValueError
        except ValueError:
            self.app.show_toast("Los kg producidos deben ser un número mayor a cero.", kind="error")
            return

        self._current_periodo_id = db.upsert_periodo(mes, anio, kg)
        self._lbl_periodo_status.configure(
            text=f"Guardado: {mes_nombre} {anio}", text_color=C_SUCCESS
        )
        self._load_table()
        self._update_summary()
        self.app.refresh_metrics()
        self.app.show_toast(f"Período {mes_nombre} {anio} guardado.")

    # ------------------------------------------------------------------ #
    # Estado del panel                                                     #
    # ------------------------------------------------------------------ #
    def _set_panel_empty(self):
        self._selected_id = None
        self._var_nombre.set("")
        self._var_monto.set("")
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="disabled")

    def _set_panel_from_row(self, row):
        self._selected_id = row["id"]
        self._var_nombre.set(row["nombre"])
        self._var_monto.set(str(row["monto"]))
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
        if self._current_periodo_id is None:
            self._lbl_error.configure(text="Primero guardá el período con los kg producidos.")
            return None, None
        nombre = self._var_nombre.get().strip()
        monto_str = self._var_monto.get().strip().replace(",", ".")
        if not nombre:
            self._lbl_error.configure(text="El concepto no puede estar vacío.")
            return None, None
        try:
            monto = float(monto_str)
            if monto <= 0:
                raise ValueError
        except ValueError:
            self._lbl_error.configure(text="El monto debe ser un número mayor a cero.")
            return None, None
        self._lbl_error.configure(text="")
        return nombre, monto

    def _save(self):
        nombre, monto = self._validate()
        if nombre is None:
            return
        if self._selected_id is None:
            db.add_gasto(self._current_periodo_id, nombre, monto)
            self.app.show_toast(f"'{nombre}' agregado.")
        else:
            db.update_gasto(self._selected_id, nombre, monto)
            self.app.show_toast(f"'{nombre}' actualizado.")
        self._cancel()
        self._load_table()
        self._update_summary()
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
        self._update_summary()
        self.app.refresh_metrics()

    # ------------------------------------------------------------------ #
    # Tabla y resumen                                                      #
    # ------------------------------------------------------------------ #
    def _load_table(self):
        if self._current_periodo_id:
            self._all_rows = list(db.get_gastos_by_periodo(self._current_periodo_id))
        else:
            self._all_rows = []
        self._filter_table()

    def _filter_table(self):
        query = self._var_search.get().strip().lower()
        for item in self._tree.get_children():
            self._tree.delete(item)
        rows = [r for r in self._all_rows if query in r["nombre"].lower()] if query else self._all_rows
        for i, row in enumerate(rows):
            tag = "alt" if i % 2 else ""
            self._tree.insert("", "end", iid=str(row["id"]),
                              values=(row["nombre"], _fmt(row["monto"])),
                              tags=(tag,))

    def _update_summary(self):
        if self._current_periodo_id:
            costo = db.get_gasto_variable_periodo(self._current_periodo_id)
            self._lbl_periodo_costo.configure(text=_fmt(costo) + " / kg")
        else:
            self._lbl_periodo_costo.configure(text="—")

        hist = db.get_gasto_variable_historico()
        n = hist["n_periodos"]
        if n:
            self._lbl_hist_costo.configure(text=_fmt(hist["promedio_kg"]) + " / kg")
            self._lbl_hist_meses.configure(
                text=f"basado en {n} {'mes' if n == 1 else 'meses'}"
            )
        else:
            self._lbl_hist_costo.configure(text="—")
            self._lbl_hist_meses.configure(text="")

    def on_show(self):
        self._set_panel_empty()
        self._on_periodo_change()
