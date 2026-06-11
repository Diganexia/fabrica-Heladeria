import customtkinter as ctk
import tkinter as tk
from ui.theme import *
from db import database as db

FF = FONT_FAMILY


def _fmt(v):
    return f"${v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _fnt(size, bold=False):
    return ctk.CTkFont(family=FF, size=size, weight="bold" if bold else "normal")


class ScreenDashboard(ctk.CTkFrame):
    def __init__(self, parent, app):
        super().__init__(parent, fg_color=C_BG, corner_radius=0)
        self.app = app
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Dashboard", font=_fnt(F_TITLE, True),
                     text_color=C_TEXT).pack(anchor="w", padx=28, pady=(22, 0))
        ctk.CTkLabel(self, text="Resumen general de costos y recetas",
                     font=_fnt(F_SMALL), text_color=C_MUTED).pack(anchor="w", padx=28, pady=(2, 14))

        # ── Fila de cards ────────────────────────────────────────────────
        cards = ctk.CTkFrame(self, fg_color="transparent")
        cards.pack(fill="x", padx=28)

        self._card_rec  = self._stat_card(cards, "Recetas",      "—", C_ACCENT)
        self._card_ing  = self._stat_card(cards, "Ingredientes", "—", "#0891b2")
        self._card_gas  = self._stat_card(cards, "Gastos",       "—", "#7c3aed")
        self._card_gvkg = self._stat_card(cards, "GV / kg",      "—", C_WARN)

        # ── Fila inferior ────────────────────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.pack(fill="both", expand=True, padx=28, pady=(14, 20))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=0)
        bottom.rowconfigure(0, weight=1)

        self._build_recetas_panel(bottom)
        self._build_chart_panel(bottom)

    # ── Tarjeta estadística ──────────────────────────────────────────────
    def _stat_card(self, parent, label, value, color):
        card = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10,
                            border_width=1, border_color=C_BORDER)
        card.pack(side="left", padx=(0, 10), pady=2, ipadx=12, ipady=6)

        bar = ctk.CTkFrame(card, fg_color=color, width=3, corner_radius=2)
        bar.pack(side="left", fill="y", padx=(0, 10), pady=6)

        info = ctk.CTkFrame(card, fg_color="transparent")
        info.pack(side="left")

        ctk.CTkLabel(info, text=label, font=_fnt(F_SMALL), text_color=C_MUTED).pack(anchor="w")
        lbl = ctk.CTkLabel(info, text=value, font=_fnt(22, True), text_color=C_TEXT)
        lbl.pack(anchor="w")
        return lbl

    # ── Panel últimas recetas ─────────────────────────────────────────────
    def _build_recetas_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10,
                             border_width=1, border_color=C_BORDER)
        frame.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        ctk.CTkLabel(frame, text="Últimas recetas", font=_fnt(F_SECTION, True),
                     text_color=C_TEXT).pack(anchor="w", padx=16, pady=(12, 8))

        self._recetas_frame = ctk.CTkScrollableFrame(frame, fg_color="transparent",
                                                     corner_radius=0)
        self._recetas_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    # ── Panel gráfico ─────────────────────────────────────────────────────
    def _build_chart_panel(self, parent):
        frame = ctk.CTkFrame(parent, fg_color=C_CARD, corner_radius=10,
                             border_width=1, border_color=C_BORDER, width=280)
        frame.grid(row=0, column=1, sticky="nsew")
        frame.pack_propagate(False)

        ctk.CTkLabel(frame, text="Distribución de costos",
                     font=_fnt(F_SECTION, True), text_color=C_TEXT).pack(
            anchor="w", padx=16, pady=(12, 2))
        ctk.CTkLabel(frame, text="Promedio de todas las recetas",
                     font=_fnt(F_SMALL), text_color=C_MUTED).pack(
            anchor="w", padx=16, pady=(0, 6))

        self._canvas = tk.Canvas(frame, width=248, height=170,
                                 bg=C_CARD, highlightthickness=0)
        self._canvas.pack()

        self._legend_frame = ctk.CTkFrame(frame, fg_color="transparent")
        self._legend_frame.pack(fill="x", padx=16, pady=(4, 12))

    def _draw_donut(self, mp, gv, ganancia):
        c = self._canvas
        c.delete("all")
        total = mp + gv + ganancia

        if total <= 0:
            c.create_text(124, 85, text="Sin datos aún", fill=C_MUTED,
                          font=(FF, 11))
            for w in self._legend_frame.winfo_children():
                w.destroy()
            return

        segs = [
            (mp,       "#2563eb", "Mat. prima"),
            (gv,       "#d97706", "Gastos var."),
            (ganancia, "#16a34a", "Ganancia"),
        ]
        cx, cy, r = 124, 82, 66
        start = -90.0
        for val, color, _ in segs:
            ext = (val / total) * 360
            if ext > 0.3:
                c.create_arc(cx-r, cy-r, cx+r, cy+r,
                             start=start, extent=ext,
                             fill=color, outline="white", width=2)
            start += ext

        inner = r * 0.55
        c.create_oval(cx-inner, cy-inner, cx+inner, cy+inner,
                      fill=C_CARD, outline=C_CARD)
        c.create_text(cx, cy-7, text=_fmt(total), fill=C_TEXT,
                      font=(FF, 10, "bold"))
        c.create_text(cx, cy+9, text="por kg", fill=C_MUTED, font=(FF, 9))

        for w in self._legend_frame.winfo_children():
            w.destroy()
        for val, color, label in segs:
            pct = val / total * 100
            row = ctk.CTkFrame(self._legend_frame, fg_color="transparent")
            row.pack(fill="x", pady=1)
            ctk.CTkFrame(row, fg_color=color, width=9, height=9,
                         corner_radius=4).pack(side="left", padx=(0, 5))
            ctk.CTkLabel(row, text=f"{label}  {pct:.0f}%",
                         font=_fnt(10), text_color=C_MUTED).pack(side="left")
            ctk.CTkLabel(row, text=_fmt(val),
                         font=_fnt(10, True), text_color=C_TEXT).pack(side="right")

    # ── on_show ───────────────────────────────────────────────────────────
    def on_show(self):
        recetas = db.get_recetas()
        ings    = db.get_ingredientes()
        gastos  = db.get_gastos()
        gv_kg   = db.get_gasto_variable_por_kg()

        self._card_rec.configure(text=str(len(recetas)))
        self._card_ing.configure(text=str(len(ings)))
        self._card_gas.configure(text=str(len(gastos)))
        self._card_gvkg.configure(text=_fmt(gv_kg))

        if recetas:
            tots = [db.calcular_costo_receta(r["id"]) for r in recetas]
            n = len(tots)
            avg_mp  = sum(t["costo_mp_kg"]     for t in tots) / n
            avg_gv  = sum(t["gasto_var_kg"]    for t in tots) / n
            avg_pv  = sum(t["precio_venta_kg"] for t in tots) / n
            self._draw_donut(avg_mp, avg_gv, max(avg_pv - avg_mp - avg_gv, 0))
        else:
            self._draw_donut(0, 0, 0)

        for w in self._recetas_frame.winfo_children():
            w.destroy()

        if not recetas:
            ctk.CTkLabel(self._recetas_frame,
                         text="Todavía no hay recetas cargadas.",
                         font=_fnt(F_BODY), text_color=C_MUTED).pack(anchor="w", pady=8)
            return

        for r in recetas[-6:][::-1]:
            costos = db.calcular_costo_receta(r["id"])
            row = ctk.CTkFrame(self._recetas_frame, fg_color=C_BG, corner_radius=7)
            row.pack(fill="x", pady=2, ipady=4)

            ctk.CTkLabel(row, text=r["nombre"], font=_fnt(F_BODY, True),
                         text_color=C_TEXT).pack(side="left", padx=12)

            badge = ctk.CTkFrame(row, fg_color=C_CHIP_BG, corner_radius=5)
            badge.pack(side="right", padx=12)
            ctk.CTkLabel(badge,
                         text=f"Precio sugerido/kg: {_fmt(costos['precio_venta_kg'])}",
                         font=_fnt(F_SMALL), text_color=C_CHIP_TEXT).pack(padx=8, pady=2)
