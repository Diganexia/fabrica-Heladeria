import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from ui.theme import *
from db import database as db

UNIDADES = ["kg", "gr", "L", "ml", "unidad"]


def _fmt(v):
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ScreenIngredientes(ctk.CTkFrame):
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
            header, text="Materia prima",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nuevo ingrediente",
            fg_color=C_ACCENT, hover_color=C_BTN_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=170, height=36, corner_radius=8,
            command=self._new,
        ).pack(side="right")

        ctk.CTkLabel(
            self, text="Gestioná los ingredientes y sus precios por unidad.",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=30, pady=(2, 14))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=1)
        body.columnconfigure(1, weight=0)
        body.rowconfigure(0, weight=1)

        self._build_table(body)
        self._build_panel(body)

    # ------------------------------------------------------------------ #
    # Tabla con búsqueda                                                   #
    # ------------------------------------------------------------------ #
    def _build_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        # Barra de búsqueda
        search_row = ctk.CTkFrame(frame, fg_color="transparent")
        search_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))

        ctk.CTkLabel(search_row, text="Buscar:",
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(side="left", padx=(4, 6))
        self._var_search = tk.StringVar()
        self._var_search.trace_add("write", lambda *_: self._filter_table())
        ctk.CTkEntry(
            search_row, textvariable=self._var_search,
            placeholder_text="Nombre del ingrediente...",
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=12),
            height=32, corner_radius=6, width=280,
        ).pack(side="left")

        # Treeview
        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Ing.Treeview",
            background=C_CARD, fieldbackground=C_CARD,
            foreground=C_TEXT, rowheight=36,
            font=("Segoe UI", 12), borderwidth=0,
        )
        style.configure("Ing.Treeview.Heading",
            background=C_HEADING_BG, foreground=C_TEXT_LIGHT,
            font=("Segoe UI", 11, "bold"), relief="flat",
        )
        style.map("Ing.Treeview",
            background=[("selected", C_ROW_SEL)],
            foreground=[("selected", C_TEXT)],
        )
        style.layout("Ing.Treeview", [("Ing.Treeview.treearea", {"sticky": "nsew"})])

        cols = ("nombre", "precio", "unidad", "actualizado")
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                  style="Ing.Treeview", selectmode="browse")
        self._tree.heading("nombre",      text="Ingrediente")
        self._tree.heading("precio",      text="Precio")
        self._tree.heading("unidad",      text="Unidad")
        self._tree.heading("actualizado", text="Actualizado")
        self._tree.column("nombre",      width=220, anchor="w")
        self._tree.column("precio",      width=120, anchor="e")
        self._tree.column("unidad",      width=90,  anchor="center")
        self._tree.column("actualizado", width=120, anchor="center")

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
        self._var_precio = tk.StringVar()
        self._var_unidad = tk.StringVar(value=UNIDADES[0])

        self._entry_nombre = self._field(outer, "Nombre", self._var_nombre)
        self._entry_precio = self._field(outer, "Precio ($)", self._var_precio)

        # Solo permite números y coma/punto en el precio
        vcmd = (self.register(lambda P: P == "" or all(c in "0123456789.," for c in P)), "%P")
        self._entry_precio._entry.configure(validate="key", validatecommand=vcmd)

        self._dropdown(outer, "Unidad", self._var_unidad)


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
            parent, variable=var, values=UNIDADES,
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
        self._var_precio.set("")
        self._var_unidad.set(UNIDADES[0])
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="disabled")

    def _set_panel_from_row(self, row):
        self._selected_id = row["id"]
        self._var_nombre.set(row["nombre"])
        self._var_precio.set(str(row["precio"]))
        self._var_unidad.set(row["unidad"])
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
        precio_str = self._var_precio.get().strip().replace(",", ".")
        if not nombre:
            self._lbl_error.configure(text="El nombre no puede estar vacío.")
            return None, None, None
        try:
            precio = float(precio_str)
        except ValueError:
            self._lbl_error.configure(text="El precio debe ser un número válido.")
            return None, None, None
        if precio <= 0:
            self._lbl_error.configure(text="El precio debe ser mayor a cero.")
            return None, None, None
        self._lbl_error.configure(text="")
        return nombre, precio, self._var_unidad.get()

    def _save(self):
        nombre, precio, unidad = self._validate()
        if nombre is None:
            return
        if self._selected_id is None:
            if any(r["nombre"].lower() == nombre.lower() for r in self._all_rows):
                self._lbl_error.configure(text="Ya existe un ingrediente con ese nombre.")
                return
        fecha = datetime.now().strftime("%Y-%m-%d")
        if self._selected_id is None:
            db.add_ingrediente(nombre, precio, unidad, fecha)
            self.app.show_toast(f"'{nombre}' agregado correctamente.")
        else:
            db.update_ingrediente(self._selected_id, nombre, precio, unidad, fecha)
            self.app.show_toast(f"'{nombre}' actualizado.")
        self._cancel()
        self._load_table()
        self.app.refresh_metrics()

    def _delete(self):
        if self._selected_id is None:
            return
        nombre = self._var_nombre.get()
        if not messagebox.askyesno("Eliminar ingrediente",
                                   f"¿Eliminás '{nombre}'?\nSi está en alguna receta no podrá borrarse."):
            return
        try:
            db.delete_ingrediente(self._selected_id)
            self.app.show_toast(f"'{nombre}' eliminado.", kind="info")
            self._cancel()
            self._load_table()
            self.app.refresh_metrics()
        except Exception:
            self._lbl_error.configure(text="No se puede eliminar: está en uso en una o más recetas.")

    # ------------------------------------------------------------------ #
    # Tabla                                                                #
    # ------------------------------------------------------------------ #
    def _load_table(self):
        self._all_rows = list(db.get_ingredientes())
        self._filter_table()

    def _filter_table(self):
        query = self._var_search.get().strip().lower()
        for item in self._tree.get_children():
            self._tree.delete(item)
        rows = [r for r in self._all_rows if query in r["nombre"].lower()] if query else self._all_rows
        for i, row in enumerate(rows):
            tag = "alt" if i % 2 else ""
            self._tree.insert("", "end", iid=str(row["id"]),
                              values=(row["nombre"], _fmt(row["precio"]),
                                      row["unidad"], row["fecha_actualizacion"]),
                              tags=(tag,))

    def on_show(self):
        self._load_table()
        self._set_panel_empty()
