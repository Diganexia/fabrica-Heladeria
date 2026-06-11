import customtkinter as ctk
from ui.theme import *
from db import database as db

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

NAV_ITEMS = [
    ("Dashboard",        "screen_dashboard"),
    ("Materia prima",    "screen_ingredientes"),
    ("Gastos variables", "screen_gastos"),
    ("Recetas",          "screen_recetas"),
]


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Fábrica de Helados — Calculadora de costos")
        self.geometry("1140x700")
        self.minsize(960, 600)
        self.configure(fg_color=C_BG)

        self._screens = {}
        self._active_btn = None
        self._toast_job = None

        self._build_topbar()
        self._build_body()
        self._build_toast()
        self._bind_global_keys()
        self.navigate("screen_dashboard")
        self.refresh_metrics()

    # ------------------------------------------------------------------ #
    # Top bar                                                              #
    # ------------------------------------------------------------------ #
    def _build_topbar(self):
        bar = ctk.CTkFrame(self, fg_color=C_TOPBAR, height=58, corner_radius=0)
        bar.pack(side="top", fill="x")
        bar.pack_propagate(False)

        ctk.CTkLabel(
            bar, text="Fábrica de Helados",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color=C_TEXT_LIGHT,
        ).pack(side="left", padx=22)

        metrics = ctk.CTkFrame(bar, fg_color="transparent")
        metrics.pack(side="right", padx=18)

        self._lbl_mp    = self._chip(metrics, "MP / kg",    "$0,00")
        self._lbl_gv    = self._chip(metrics, "GV / kg",    "$0,00")
        self._lbl_total = self._chip(metrics, "Costo / kg", "$0,00")
        self._lbl_pv    = self._chip(metrics, "Venta / kg", "$0,00", accent=True)

    def _chip(self, parent, label, value, accent=False):
        bg = C_ACCENT if accent else "#2a4a7f"
        frame = ctk.CTkFrame(parent, fg_color=bg, corner_radius=8)
        frame.pack(side="left", padx=5, pady=9)
        ctk.CTkLabel(frame, text=label,
                     font=ctk.CTkFont(family="Segoe UI", size=10),
                     text_color="#c7d8f5").pack(padx=12, pady=(5, 0))
        lbl = ctk.CTkLabel(frame, text=value,
                           font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                           text_color=C_TEXT_LIGHT)
        lbl.pack(padx=12, pady=(0, 5))
        return lbl

    # ------------------------------------------------------------------ #
    # Sidebar + contenido                                                  #
    # ------------------------------------------------------------------ #
    def _build_body(self):
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)

        self._sidebar = ctk.CTkFrame(body, fg_color=C_SIDEBAR, width=210, corner_radius=0)
        self._sidebar.pack(side="left", fill="y")
        self._sidebar.pack_propagate(False)

        self._content = ctk.CTkFrame(body, fg_color=C_BG, corner_radius=0)
        self._content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()

    def _build_sidebar(self):
        ctk.CTkLabel(
            self._sidebar, text="NAVEGACIÓN",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#7a9cc8",
        ).pack(pady=(22, 6), padx=16, anchor="w")

        self._nav_buttons = {}
        for label, key in NAV_ITEMS:
            btn = ctk.CTkButton(
                self._sidebar, text=label, anchor="w",
                fg_color="transparent", hover_color="#2a4a7f",
                text_color="#c7d8f5",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                height=42, corner_radius=8,
                command=lambda k=key: self.navigate(k),
            )
            btn.pack(fill="x", padx=10, pady=2)
            self._nav_buttons[key] = btn

        ctk.CTkLabel(
            self._sidebar, text="v1.0",
            font=ctk.CTkFont(size=10), text_color="#7a9cc8",
        ).pack(side="bottom", pady=14)

    # ------------------------------------------------------------------ #
    # Toast                                                                #
    # ------------------------------------------------------------------ #
    def _build_toast(self):
        self._toast = ctk.CTkFrame(
            self, fg_color=C_SUCCESS, corner_radius=10,
            border_width=0,
        )
        self._toast_lbl = ctk.CTkLabel(
            self._toast, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=C_TEXT_LIGHT,
        )
        self._toast_lbl.pack(padx=20, pady=10)
        # El toast no se muestra hasta que se llame a show_toast()

    def show_toast(self, message: str, kind: str = "success"):
        colors_map = {"success": C_SUCCESS, "error": C_DANGER, "info": C_ACCENT}
        self._toast.configure(fg_color=colors_map.get(kind, C_SUCCESS))
        self._toast_lbl.configure(text=message)
        self._toast.place(relx=1.0, rely=1.0, x=-20, y=-20, anchor="se")
        self._toast.lift()
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(2500, self._hide_toast)

    def _hide_toast(self):
        self._toast.place_forget()
        self._toast_job = None

    # ------------------------------------------------------------------ #
    # Navegación                                                           #
    # ------------------------------------------------------------------ #
    def navigate(self, key: str):
        for child in self._content.winfo_children():
            child.pack_forget()

        if self._active_btn:
            self._active_btn.configure(fg_color="transparent", text_color="#c7d8f5",
                                       font=ctk.CTkFont(family="Segoe UI", size=13))
        btn = self._nav_buttons.get(key)
        if btn:
            btn.configure(fg_color=C_BTN_SEL, text_color=C_TEXT_LIGHT,
                          font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"))
            self._active_btn = btn

        if key not in self._screens:
            mod = __import__(f"ui.{key}", fromlist=[key])
            cls_name = "".join(p.capitalize() for p in key.split("_"))
            cls = getattr(mod, cls_name)
            self._screens[key] = cls(self._content, app=self)

        self._screens[key].pack(fill="both", expand=True)
        if hasattr(self._screens[key], "on_show"):
            self._screens[key].on_show()

    # ------------------------------------------------------------------ #
    # Atajos globales                                                      #
    # ------------------------------------------------------------------ #
    def _bind_global_keys(self):
        keys = list(self._nav_buttons.keys()) if hasattr(self, "_nav_buttons") else []
        shortcuts = [("<Control-Key-1>", "screen_dashboard"),
                     ("<Control-Key-2>", "screen_ingredientes"),
                     ("<Control-Key-3>", "screen_gastos"),
                     ("<Control-Key-4>", "screen_recetas")]
        for keybind, screen in shortcuts:
            self.bind_all(keybind, lambda e, s=screen: self.navigate(s))

    # ------------------------------------------------------------------ #
    # Métricas                                                             #
    # ------------------------------------------------------------------ #
    def refresh_metrics(self):
        gv = db.get_gasto_variable_por_kg()
        recetas = db.get_recetas()
        if recetas:
            totales = [db.calcular_costo_receta(r["id"]) for r in recetas]
            mp    = sum(t["costo_mp_kg"]     for t in totales) / len(totales)
            total = sum(t["costo_total_kg"]  for t in totales) / len(totales)
            pv    = sum(t["precio_venta_kg"] for t in totales) / len(totales)
        else:
            mp = total = pv = 0.0

        def f(v):
            return f"${v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

        self._lbl_mp.configure(text=f(mp))
        self._lbl_gv.configure(text=f(gv))
        self._lbl_total.configure(text=f(total))
        self._lbl_pv.configure(text=f(pv))
