import customtkinter as ctk
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from ui.theme import *
from db import database as db

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
         "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]


def _fmt(v):
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ScreenPeriodos(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.app = app
        self._selected_periodo = None
        self._periodos = []
        self._gastos_detalle = []
        self._build()

    # ------------------------------------------------------------------ #
    # Layout                                                               #
    # ------------------------------------------------------------------ #
    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(16, 0))

        ctk.CTkLabel(
            header, text="Períodos",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=C_TEXT,
        ).pack(side="left")

        self._btn_export = ctk.CTkButton(
            header, text="Exportar PDF",
            fg_color="#7c3aed", hover_color="#6d28d9",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            width=150, height=36, corner_radius=8,
            state="disabled",
            command=self._export_pdf,
        )
        self._btn_export.pack(side="right")

        ctk.CTkLabel(
            self,
            text="Historial mensual de gastos variables. Seleccioná un período para ver el detalle.",
            font=ctk.CTkFont(family="Segoe UI", size=12), text_color=C_MUTED,
        ).pack(anchor="w", padx=30, pady=(2, 12))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        body.columnconfigure(0, weight=3)
        body.columnconfigure(1, weight=2)
        body.rowconfigure(0, weight=1)

        self._build_periodos_table(body)
        self._build_detail_panel(body)

    # ------------------------------------------------------------------ #
    # Tabla de períodos (izquierda)                                        #
    # ------------------------------------------------------------------ #
    def _build_periodos_table(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(0, weight=1)

        ctk.CTkLabel(
            frame, text="Historial de períodos",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=C_TEXT,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(12, 6))

        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.grid(row=1, column=0, sticky="nsew", padx=6, pady=(0, 6))

        style = ttk.Style()
        style.configure("PerHist.Treeview",
            background=C_CARD, fieldbackground=C_CARD,
            foreground=C_TEXT, rowheight=36,
            font=("Segoe UI", 12), borderwidth=0,
        )
        style.configure("PerHist.Treeview.Heading",
            background=C_HEADING_BG, foreground=C_TEXT_LIGHT,
            font=("Segoe UI", 11, "bold"), relief="flat",
        )
        style.map("PerHist.Treeview",
            background=[("selected", C_ROW_SEL)],
            foreground=[("selected", C_TEXT)],
        )
        style.layout("PerHist.Treeview", [("PerHist.Treeview.treearea", {"sticky": "nsew"})])

        cols = ("periodo", "kg_prod", "total_gastos", "gv_kg")
        self._tree_per = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                       style="PerHist.Treeview", selectmode="browse")
        self._tree_per.heading("periodo",      text="Período")
        self._tree_per.heading("kg_prod",      text="Kg producidos")
        self._tree_per.heading("total_gastos", text="Total gastos")
        self._tree_per.heading("gv_kg",        text="GV / kg")
        self._tree_per.column("periodo",      width=130, anchor="w")
        self._tree_per.column("kg_prod",      width=120, anchor="e")
        self._tree_per.column("total_gastos", width=130, anchor="e")
        self._tree_per.column("gv_kg",        width=110, anchor="e")

        sb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree_per.yview)
        self._tree_per.configure(yscrollcommand=sb.set)
        self._tree_per.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")

        self._tree_per.tag_configure("alt", background=C_ROW_ALT)
        self._tree_per.bind("<<TreeviewSelect>>", self._on_periodo_select)

    # ------------------------------------------------------------------ #
    # Panel de detalle (derecha)                                           #
    # ------------------------------------------------------------------ #
    def _build_detail_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=12,
                             border_width=1, border_color=C_BORDER)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.rowconfigure(2, weight=1)
        frame.columnconfigure(0, weight=1)

        self._lbl_det_titulo = ctk.CTkLabel(
            frame, text="Seleccioná un período",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color=C_TEXT,
        )
        self._lbl_det_titulo.grid(row=0, column=0, sticky="w", padx=14, pady=(14, 2))

        self._lbl_det_sub = ctk.CTkLabel(
            frame, text="",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=C_MUTED,
        )
        self._lbl_det_sub.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 8))

        tree_frame = ctk.CTkFrame(frame, fg_color="transparent")
        tree_frame.grid(row=2, column=0, sticky="nsew", padx=6, pady=(0, 8))

        style = ttk.Style()
        style.configure("PerDet.Treeview",
            background=C_CARD, fieldbackground=C_CARD,
            foreground=C_TEXT, rowheight=34,
            font=("Segoe UI", 12), borderwidth=0,
        )
        style.configure("PerDet.Treeview.Heading",
            background=C_HEADING_BG, foreground=C_TEXT_LIGHT,
            font=("Segoe UI", 11, "bold"), relief="flat",
        )
        style.map("PerDet.Treeview",
            background=[("selected", C_ROW_SEL)],
            foreground=[("selected", C_TEXT)],
        )
        style.layout("PerDet.Treeview", [("PerDet.Treeview.treearea", {"sticky": "nsew"})])

        cols = ("concepto", "monto")
        self._tree_det = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                       style="PerDet.Treeview", selectmode="none")
        self._tree_det.heading("concepto", text="Concepto")
        self._tree_det.heading("monto",    text="Monto")
        self._tree_det.column("concepto", width=200, anchor="w")
        self._tree_det.column("monto",    width=130, anchor="e")

        sb2 = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree_det.yview)
        self._tree_det.configure(yscrollcommand=sb2.set)
        self._tree_det.pack(side="left", fill="both", expand=True)
        sb2.pack(side="right", fill="y")

        self._tree_det.tag_configure("alt", background=C_ROW_ALT)
        self._tree_det.tag_configure("total_row",
            background=C_HEADING_BG,
            foreground=C_TEXT_LIGHT,
            font=("Segoe UI", 12, "bold"),
        )

        # Card GV/kg
        self._card_gv = ctk.CTkFrame(frame, fg_color="#1e3a5f", corner_radius=8)
        self._card_gv.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

        inner_gv = ctk.CTkFrame(self._card_gv, fg_color="transparent")
        inner_gv.pack(fill="x", padx=14, pady=10)

        ctk.CTkLabel(inner_gv, text="GV / kg este período",
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color="#c7d8f5").pack(side="left")

        self._lbl_gv_val = ctk.CTkLabel(inner_gv, text="—",
                                          font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                                          text_color="#fbbf24")
        self._lbl_gv_val.pack(side="right")

    # ------------------------------------------------------------------ #
    # Eventos                                                              #
    # ------------------------------------------------------------------ #
    def _on_periodo_select(self, _=None):
        sel = self._tree_per.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._selected_periodo = self._periodos[idx]
        self._load_detail()
        self._btn_export.configure(state="normal")

    # ------------------------------------------------------------------ #
    # Carga de datos                                                       #
    # ------------------------------------------------------------------ #
    def _load_periodos(self):
        self._periodos = list(db.get_periodos_gastos())
        for item in self._tree_per.get_children():
            self._tree_per.delete(item)
        for i, p in enumerate(self._periodos):
            gastos = db.get_gastos_by_periodo(p["id"])
            total = sum(g["monto"] for g in gastos)
            gv_kg = total / p["kg_prod"] if p["kg_prod"] else 0
            mes_nombre = MESES[p["mes"] - 1]
            tag = "alt" if i % 2 else ""
            self._tree_per.insert("", "end", iid=str(i),
                                  values=(
                                      f"{mes_nombre} {p['anio']}",
                                      f"{p['kg_prod']:g} kg",
                                      _fmt(total),
                                      _fmt(gv_kg),
                                  ),
                                  tags=(tag,))

    def _load_detail(self):
        p = self._selected_periodo
        if not p:
            return
        mes_nombre = MESES[p["mes"] - 1]
        self._lbl_det_titulo.configure(text=f"{mes_nombre} {p['anio']}")

        self._gastos_detalle = list(db.get_gastos_by_periodo(p["id"]))
        total = sum(g["monto"] for g in self._gastos_detalle)
        gv_kg = total / p["kg_prod"] if p["kg_prod"] else 0

        self._lbl_det_sub.configure(
            text=f"{p['kg_prod']:g} kg producidos · {len(self._gastos_detalle)} concepto(s)"
        )
        self._lbl_gv_val.configure(text=_fmt(gv_kg))

        for item in self._tree_det.get_children():
            self._tree_det.delete(item)
        for i, g in enumerate(self._gastos_detalle):
            tag = "alt" if i % 2 else ""
            self._tree_det.insert("", "end",
                                   values=(g["nombre"], _fmt(g["monto"])),
                                   tags=(tag,))
        self._tree_det.insert("", "end",
                               values=("TOTAL", _fmt(total)),
                               tags=("total_row",))

    # ------------------------------------------------------------------ #
    # Exportar PDF                                                         #
    # ------------------------------------------------------------------ #
    def _export_pdf(self):
        if not self._selected_periodo:
            return
        p = self._selected_periodo
        mes_nombre = MESES[p["mes"] - 1]
        default_name = f"Gastos_{mes_nombre}_{p['anio']}.pdf"
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=default_name,
            title="Guardar PDF del período",
        )
        if not ruta:
            return
        try:
            from reports.pdf_export import generar_pdf_periodo
            generar_pdf_periodo(p["id"], ruta)
            self.app.show_toast(f"PDF guardado: {os.path.basename(ruta)}")
            os.startfile(ruta)
        except Exception as e:
            messagebox.showerror("Error al generar PDF", str(e))

    # ------------------------------------------------------------------ #
    # on_show                                                              #
    # ------------------------------------------------------------------ #
    def on_show(self):
        self._selected_periodo = None
        self._btn_export.configure(state="disabled")
        self._lbl_det_titulo.configure(text="Seleccioná un período")
        self._lbl_det_sub.configure(text="")
        self._lbl_gv_val.configure(text="—")
        for item in self._tree_det.get_children():
            self._tree_det.delete(item)
        self._load_periodos()
