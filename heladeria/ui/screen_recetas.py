import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog
import os
from datetime import datetime
from ui.theme import *
from db import database as db
from reports.pdf_export import generar_pdf

C_SELECTED = C_CHIP_BG


def fmt_ars(v):
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ScreenRecetas(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.app = app

        # Estado del editor
        self._receta_id   = None        # None = nueva
        self._items       = []          # [(ingrediente_id, nombre, unidad, precio, cantidad)]
        self._ing_map     = {}          # nombre → row completo (para lookup rápido)

        self._build()

    # ------------------------------------------------------------------ #
    # Layout principal                                                     #
    # ------------------------------------------------------------------ #
    def _build(self):
        # Encabezado
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(24, 0))

        ctk.CTkLabel(
            header, text="Recetas",
            font=ctk.CTkFont(size=22, weight="bold"), text_color=C_TEXT,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="+ Nueva receta",
            fg_color=C_ACCENT, hover_color="#c73652",
            font=ctk.CTkFont(size=13, weight="bold"),
            width=150, height=36, corner_radius=8,
            command=self._nueva_receta,
        ).pack(side="right")

        ctk.CTkLabel(
            self, text="Armá recetas, calculá costos en tiempo real y definí el precio de venta.",
            font=ctk.CTkFont(size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=30, pady=(2, 14))

        # Cuerpo: lista izquierda + editor derecho
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=0)
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        self._build_lista(body)
        self._build_editor(body)

    # ------------------------------------------------------------------ #
    # Lista de recetas (columna izquierda)                                 #
    # ------------------------------------------------------------------ #
    def _build_lista(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10, width=220)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        frame.pack_propagate(False)

        ctk.CTkLabel(
            frame, text="Recetas guardadas",
            font=ctk.CTkFont(size=13, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self._lista_scroll = ctk.CTkScrollableFrame(
            frame, fg_color="transparent", corner_radius=0,
        )
        self._lista_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 8))

    def _refresh_lista(self):
        for w in self._lista_scroll.winfo_children():
            w.destroy()

        recetas = db.get_recetas()
        if not recetas:
            ctk.CTkLabel(
                self._lista_scroll, text="Sin recetas",
                font=ctk.CTkFont(size=12), text_color=C_MUTED,
            ).pack(pady=10)
            return

        for r in recetas:
            is_sel = (r["id"] == self._receta_id)
            btn = ctk.CTkButton(
                self._lista_scroll,
                text=r["nombre"],
                anchor="w",
                fg_color=C_SELECTED if is_sel else "transparent",
                hover_color=C_CHIP_BG,
                text_color=C_TEXT if is_sel else C_MUTED,
                font=ctk.CTkFont(size=12, weight="bold" if is_sel else "normal"),
                height=36, corner_radius=6,
                command=lambda rid=r["id"]: self._cargar_receta(rid),
            )
            btn.pack(fill="x", pady=2)

    # ------------------------------------------------------------------ #
    # Editor (columna derecha)                                             #
    # ------------------------------------------------------------------ #
    def _build_editor(self, parent):
        self._editor = ctk.CTkScrollableFrame(
            parent, fg_color=C_CARD, corner_radius=10,
        )
        self._editor.grid(row=0, column=1, sticky="nsew")

        # — Datos generales —
        datos = ctk.CTkFrame(self._editor, fg_color="transparent")
        datos.pack(fill="x", padx=20, pady=(16, 0))
        datos.columnconfigure(0, weight=1)
        datos.columnconfigure(1, weight=0)
        datos.columnconfigure(2, weight=0)

        self._var_nombre  = tk.StringVar()
        self._var_rinde   = tk.StringVar()
        self._var_margen  = tk.StringVar(value="40")

        self._entry_field(datos, "Nombre de la receta", self._var_nombre, col=0, colspan=3)
        self._entry_field(datos, "Rinde (kg)",          self._var_rinde,  col=0, row=1)
        self._entry_field(datos, "Margen de ganancia (%)", self._var_margen, col=1, row=1, pad_left=10)

        # Bind para recálculo en tiempo real
        for var in (self._var_rinde, self._var_margen):
            var.trace_add("write", lambda *_: self._recalcular())

        # — Separador —
        ctk.CTkFrame(self._editor, fg_color="#2a3a6e", height=1).pack(
            fill="x", padx=20, pady=(14, 10)
        )

        # — Agregar ingrediente —
        ctk.CTkLabel(
            self._editor, text="Ingredientes",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(0, 6))

        add_row = ctk.CTkFrame(self._editor, fg_color="transparent")
        add_row.pack(fill="x", padx=20, pady=(0, 8))

        self._var_ing_sel  = tk.StringVar()
        self._var_cantidad = tk.StringVar()

        self._om_ing = ctk.CTkOptionMenu(
            add_row, variable=self._var_ing_sel,
            values=["(sin ingredientes)"],
            fg_color=C_INPUT_BG, button_color=C_BORDER,
            button_hover_color=C_ACCENT, text_color=C_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=12), corner_radius=6, height=36, width=220,
        )
        self._om_ing.pack(side="left", padx=(0, 8))

        ctk.CTkLabel(add_row, text="Cantidad:", text_color=C_MUTED,
                     font=ctk.CTkFont(family="Segoe UI", size=12)).pack(side="left")
        self._entry_cantidad = ctk.CTkEntry(
            add_row, textvariable=self._var_cantidad,
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36, corner_radius=6, width=90,
        )
        self._entry_cantidad.pack(side="left", padx=(4, 8))
        self._entry_cantidad._entry.bind("<Return>", lambda e: self._agregar_ingrediente())

        ctk.CTkButton(
            add_row, text="+ Agregar",
            fg_color=C_ACCENT, hover_color=C_BTN_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=12), height=36, width=100, corner_radius=6,
            command=self._agregar_ingrediente,
        ).pack(side="left")

        self._lbl_ing_error = ctk.CTkLabel(
            self._editor, text="", text_color=C_DANGER,
            font=ctk.CTkFont(family="Segoe UI", size=11),
        )
        self._lbl_ing_error.pack(anchor="w", padx=20)

        # — Tabla de ingredientes de la receta —
        self._tabla_frame = ctk.CTkFrame(self._editor, fg_color="transparent")
        self._tabla_frame.pack(fill="x", padx=20, pady=(0, 8))

        # — Separador —
        ctk.CTkFrame(self._editor, fg_color="#2a3a6e", height=1).pack(
            fill="x", padx=20, pady=(4, 10)
        )

        # — Resumen de costos —
        ctk.CTkLabel(
            self._editor, text="Resumen de costos",
            font=ctk.CTkFont(size=14, weight="bold"), text_color=C_TEXT,
        ).pack(anchor="w", padx=20, pady=(0, 8))

        self._resumen = ctk.CTkFrame(self._editor, fg_color=C_CARD, corner_radius=10,
                                     border_width=1, border_color=C_BORDER)
        self._resumen.pack(fill="x", padx=20, pady=(0, 14))
        self._build_resumen()

        # — Error general y botones —
        self._lbl_error = ctk.CTkLabel(
            self._editor, text="", text_color=C_DANGER,
            font=ctk.CTkFont(family="Segoe UI", size=11), wraplength=500,
        )
        self._lbl_error.pack(anchor="w", padx=20)

        btns = ctk.CTkFrame(self._editor, fg_color="transparent")
        btns.pack(fill="x", padx=20, pady=(8, 16))

        self._btn_save = ctk.CTkButton(
            btns, text="Guardar receta",
            fg_color=C_SUCCESS, hover_color="#15803d",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40, corner_radius=8, command=self._guardar,
        )
        self._btn_save.pack(side="left", padx=(0, 10))

        self._btn_delete = ctk.CTkButton(
            btns, text="Eliminar receta",
            fg_color=C_DANGER, hover_color="#b91c1c",
            font=ctk.CTkFont(family="Segoe UI", size=13), height=40, corner_radius=8,
            command=self._eliminar, state="disabled",
        )
        self._btn_delete.pack(side="left", padx=(0, 10))

        self._btn_pdf = ctk.CTkButton(
            btns, text="Exportar PDF",
            fg_color="#7c3aed", hover_color="#6d28d9",
            font=ctk.CTkFont(family="Segoe UI", size=13), height=40, corner_radius=8,
            command=self._exportar_pdf, state="disabled",
        )
        self._btn_pdf.pack(side="left")

    def _entry_field(self, parent, label, var, col, row=0, colspan=1, pad_left=0):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=col, columnspan=colspan,
                   sticky="ew", padx=(pad_left, 0), pady=(0, 8))
        ctk.CTkLabel(frame, text=label, font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=C_MUTED).pack(anchor="w")
        e = ctk.CTkEntry(
            frame, textvariable=var,
            fg_color=C_INPUT_BG, border_color=C_BORDER,
            text_color=C_TEXT, font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36, corner_radius=6,
        )
        e.pack(fill="x")
        e._entry.bind("<Return>", lambda ev: self._guardar())
        return e

    # ------------------------------------------------------------------ #
    # Resumen de costos                                                    #
    # ------------------------------------------------------------------ #
    def _build_resumen(self):
        resumen_rows = [
            ("Costo materia prima / kg",     "_lbl_mp",    C_TEXT),
            ("Gasto variable / kg",           "_lbl_gv",    C_TEXT),
            ("Costo total / kg",              "_lbl_total", C_WARN),
            ("Precio de venta sugerido / kg", "_lbl_pv",    C_SUCCESS),
        ]
        for i, (label, attr, color) in enumerate(resumen_rows):
            r = ctk.CTkFrame(self._resumen, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=(8 if i == 0 else 2, 8 if i == 3 else 0))
            ctk.CTkLabel(r, text=label, font=ctk.CTkFont(family="Segoe UI", size=12),
                         text_color=C_MUTED).pack(side="left")
            lbl = ctk.CTkLabel(r, text="$ —",
                               font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                               text_color=color)
            lbl.pack(side="right")
            setattr(self, attr, lbl)

        r = ctk.CTkFrame(self._resumen, fg_color="transparent")
        r.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(r, text="Margen aplicado", font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=C_MUTED).pack(side="left")
        self._lbl_margen_info = ctk.CTkLabel(
            r, text="—", font=ctk.CTkFont(family="Segoe UI", size=11), text_color=C_MUTED,
        )
        self._lbl_margen_info.pack(side="right")

    # ------------------------------------------------------------------ #
    # Tabla de ingredientes de la receta                                   #
    # ------------------------------------------------------------------ #
    def _refresh_tabla_items(self):
        for w in self._tabla_frame.winfo_children():
            w.destroy()

        if not self._items:
            ctk.CTkLabel(
                self._tabla_frame,
                text="Todavía no agregaste ingredientes.",
                font=ctk.CTkFont(size=12), text_color=C_MUTED,
            ).pack(anchor="w", pady=4)
            return

        # Encabezado
        hdr = ctk.CTkFrame(self._tabla_frame, fg_color=C_HEADING_BG, corner_radius=6)
        hdr.pack(fill="x", pady=(0, 2))
        for txt, w in [("Ingrediente", 200), ("Cant.", 70), ("$/u", 100), ("Subtotal", 110), ("", 36)]:
            ctk.CTkLabel(hdr, text=txt, width=w,
                         font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                         text_color=C_TEXT_LIGHT, anchor="w").pack(side="left", padx=6, pady=4)

        # Filas
        for idx, (ing_id, nombre, unidad, precio, cantidad) in enumerate(self._items):
            subtotal = precio * cantidad
            bg = C_ROW_ALT if idx % 2 else C_CARD
            row = ctk.CTkFrame(self._tabla_frame, fg_color=bg, corner_radius=4)
            row.pack(fill="x", pady=1)

            ctk.CTkLabel(row, text=f"{nombre} ({unidad})", width=200,
                         font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_TEXT,
                         anchor="w").pack(side="left", padx=6, pady=4)
            ctk.CTkLabel(row, text=str(cantidad), width=70,
                         font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_TEXT,
                         anchor="w").pack(side="left", padx=6)
            ctk.CTkLabel(row, text=fmt_ars(precio), width=100,
                         font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
                         anchor="e").pack(side="left", padx=6)
            ctk.CTkLabel(row, text=fmt_ars(subtotal), width=110,
                         font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                         text_color=C_TEXT, anchor="e").pack(side="left", padx=6)
            ctk.CTkButton(
                row, text="✕", width=30, height=26,
                fg_color=C_DANGER, hover_color="#b91c1c",
                font=ctk.CTkFont(family="Segoe UI", size=11), corner_radius=4,
                command=lambda i=idx: self._quitar_ingrediente(i),
            ).pack(side="left", padx=4)

    # ------------------------------------------------------------------ #
    # Cálculo en tiempo real                                               #
    # ------------------------------------------------------------------ #
    def _recalcular(self):
        try:
            rinde = float(self._var_rinde.get().replace(",", "."))
        except ValueError:
            rinde = 0

        try:
            margen = float(self._var_margen.get().replace(",", "."))
        except ValueError:
            margen = 0

        if rinde > 0 and self._items:
            costo_mp = sum(p * c for _, _, _, p, c in self._items)
            costo_mp_kg = costo_mp / rinde
        else:
            costo_mp_kg = 0.0

        gv_kg = db.get_gasto_variable_por_kg()
        total_kg = costo_mp_kg + gv_kg
        m = margen / 100
        pv_kg = total_kg / (1 - m) if 0 < m < 1 else (0.0 if m >= 1 else total_kg)

        self._lbl_mp.configure(text=fmt_ars(costo_mp_kg))
        self._lbl_gv.configure(text=fmt_ars(gv_kg))
        self._lbl_total.configure(text=fmt_ars(total_kg))
        self._lbl_pv.configure(text=fmt_ars(pv_kg))
        self._lbl_margen_info.configure(text=f"{margen:.1f}% sobre precio de venta")

    # ------------------------------------------------------------------ #
    # Acciones ingredientes                                                #
    # ------------------------------------------------------------------ #
    def _agregar_ingrediente(self):
        nombre_sel = self._var_ing_sel.get()
        if nombre_sel not in self._ing_map:
            self._lbl_ing_error.configure(text="Seleccioná un ingrediente.")
            return

        cant_str = self._var_cantidad.get().strip().replace(",", ".")
        try:
            cantidad = float(cant_str)
        except ValueError:
            self._lbl_ing_error.configure(text="La cantidad debe ser un número.")
            return
        if cantidad <= 0:
            self._lbl_ing_error.configure(text="La cantidad debe ser mayor a cero.")
            return

        self._lbl_ing_error.configure(text="")
        row = self._ing_map[nombre_sel]
        self._items.append((row["id"], row["nombre"], row["unidad"], row["precio"], cantidad))
        self._var_cantidad.set("")
        self._refresh_tabla_items()
        self._recalcular()

    def _quitar_ingrediente(self, idx):
        self._items.pop(idx)
        self._refresh_tabla_items()
        self._recalcular()

    # ------------------------------------------------------------------ #
    # Cargar / limpiar editor                                              #
    # ------------------------------------------------------------------ #
    def _nueva_receta(self):
        self._receta_id = None
        self._items = []
        self._var_nombre.set("")
        self._var_rinde.set("")
        self._var_margen.set("40")
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="disabled")
        self._btn_pdf.configure(state="disabled")
        self._refresh_tabla_items()
        self._recalcular()
        self._refresh_lista()

    def _cargar_receta(self, receta_id):
        self._receta_id = receta_id
        r = next((x for x in db.get_recetas() if x["id"] == receta_id), None)
        if not r:
            return

        self._var_nombre.set(r["nombre"])
        self._var_rinde.set(str(r["rinde_kg"]))
        self._var_margen.set(str(r["margen_pct"]))

        ings = db.get_receta_ingredientes(receta_id)
        self._items = [
            (row["ingrediente_id"], row["nombre"], row["unidad"], row["precio"], row["cantidad"])
            for row in ings
        ]
        self._lbl_error.configure(text="")
        self._btn_delete.configure(state="normal")
        self._btn_pdf.configure(state="normal")
        self._refresh_tabla_items()
        self._recalcular()
        self._refresh_lista()

    def _refresh_ing_dropdown(self):
        ings = db.get_ingredientes()
        self._ing_map = {r["nombre"]: r for r in ings}
        nombres = list(self._ing_map.keys()) if self._ing_map else ["(sin ingredientes)"]
        self._om_ing.configure(values=nombres)
        if nombres:
            self._var_ing_sel.set(nombres[0])

    # ------------------------------------------------------------------ #
    # Validación                                                           #
    # ------------------------------------------------------------------ #
    def _validar(self):
        nombre = self._var_nombre.get().strip()
        if not nombre:
            self._lbl_error.configure(text="El nombre de la receta no puede estar vacío.")
            return False

        try:
            rinde = float(self._var_rinde.get().replace(",", "."))
            if rinde <= 0:
                raise ValueError
        except ValueError:
            self._lbl_error.configure(text="El rendimiento debe ser un número mayor a cero.")
            return False

        try:
            margen = float(self._var_margen.get().replace(",", "."))
            if not (0 <= margen < 100):
                raise ValueError
        except ValueError:
            self._lbl_error.configure(text="El margen debe ser un número entre 0 y 99.")
            return False

        if not self._items:
            self._lbl_error.configure(text="Agregá al menos un ingrediente.")
            return False

        self._lbl_error.configure(text="")
        return True

    # ------------------------------------------------------------------ #
    # Guardar / eliminar                                                   #
    # ------------------------------------------------------------------ #
    def _guardar(self):
        if not self._validar():
            return

        nombre  = self._var_nombre.get().strip()
        rinde   = float(self._var_rinde.get().replace(",", "."))
        margen  = float(self._var_margen.get().replace(",", "."))
        fecha   = datetime.now().strftime("%Y-%m-%d")
        ing_ids = [(ing_id, cant) for ing_id, _, _, _, cant in self._items]

        if self._receta_id is None:
            if any(r["nombre"].lower() == nombre.lower() for r in db.get_recetas()):
                self._lbl_error.configure(text="Ya existe una receta con ese nombre.")
                return
            rid = db.add_receta(nombre, rinde, margen, fecha)
        else:
            rid = self._receta_id
            db.update_receta(rid, nombre, rinde, margen)

        db.set_receta_ingredientes(rid, ing_ids)
        self._receta_id = rid
        self._btn_delete.configure(state="normal")
        self._btn_pdf.configure(state="normal")
        self._refresh_lista()
        self.app.refresh_metrics()
        self.app.show_toast(f"Receta '{nombre}' guardada.")

    def _eliminar(self):
        if self._receta_id is None:
            return
        nombre = self._var_nombre.get()
        if not messagebox.askyesno("Eliminar receta", f"¿Eliminás '{nombre}'?"):
            return
        db.delete_receta(self._receta_id)
        self.app.show_toast(f"Receta '{nombre}' eliminada.", kind="info")
        self._nueva_receta()
        self.app.refresh_metrics()

    # ------------------------------------------------------------------ #
    # on_show                                                              #
    # ------------------------------------------------------------------ #
    def _exportar_pdf(self):
        if self._receta_id is None:
            return
        nombre = self._var_nombre.get().strip() or "receta"
        nombre_archivo = nombre.replace(" ", "_").lower() + ".pdf"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=nombre_archivo,
            title="Guardar PDF",
        )
        if not ruta:
            return
        try:
            generar_pdf(self._receta_id, ruta)
            if messagebox.askyesno(
                "PDF generado",
                f"PDF guardado en:\n{ruta}\n\n¿Querés abrirlo ahora?",
            ):
                os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error al generar PDF", str(e))

    def on_show(self):
        self._refresh_ing_dropdown()
        self._refresh_lista()
        self._recalcular()
