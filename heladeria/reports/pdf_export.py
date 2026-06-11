import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from db import database as db

# ── Paleta ──────────────────────────────────────────────────────────────────
AZUL_OSC  = colors.HexColor("#0f3460")
AZUL_MED  = colors.HexColor("#16213e")
ROJO      = colors.HexColor("#e94560")
VERDE     = colors.HexColor("#2ecc71")
AMARILLO  = colors.HexColor("#f39c12")
GRIS_CLR  = colors.HexColor("#a0a0b0")
GRIS_FILA = colors.HexColor("#f0f4ff")
BLANCO    = colors.white
NEGRO     = colors.HexColor("#1a1a2e")

PAGE_W, PAGE_H = A4


def _estilos():
    base = getSampleStyleSheet()
    estilos = {
        "titulo": ParagraphStyle(
            "titulo", fontSize=22, textColor=BLANCO,
            fontName="Helvetica-Bold", alignment=TA_CENTER, spaceAfter=4,
        ),
        "subtitulo": ParagraphStyle(
            "subtitulo", fontSize=13, textColor=GRIS_CLR,
            fontName="Helvetica", alignment=TA_CENTER, spaceAfter=2,
        ),
        "receta": ParagraphStyle(
            "receta", fontSize=18, textColor=AZUL_OSC,
            fontName="Helvetica-Bold", spaceAfter=2,
        ),
        "fecha": ParagraphStyle(
            "fecha", fontSize=10, textColor=GRIS_CLR,
            fontName="Helvetica", spaceAfter=6,
        ),
        "seccion": ParagraphStyle(
            "seccion", fontSize=12, textColor=AZUL_OSC,
            fontName="Helvetica-Bold", spaceBefore=12, spaceAfter=4,
        ),
        "nota": ParagraphStyle(
            "nota", fontSize=9, textColor=GRIS_CLR,
            fontName="Helvetica-Oblique", alignment=TA_CENTER, spaceBefore=20,
        ),
        "precio_lbl": ParagraphStyle(
            "precio_lbl", fontSize=12, textColor=BLANCO,
            fontName="Helvetica-Bold", alignment=TA_RIGHT,
        ),
        "precio_val": ParagraphStyle(
            "precio_val", fontSize=16, textColor=VERDE,
            fontName="Helvetica-Bold", alignment=TA_RIGHT,
        ),
    }
    return estilos


def _fmt(v):
    """Formatea como moneda argentina."""
    return f"$ {v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _tabla_ingredientes(items, rinde_kg, estilos):
    """items: lista de (ing_id, nombre, unidad, precio, cantidad)"""
    encabezado = ["Ingrediente", "Unidad", "Cantidad", "Precio / u", "Subtotal"]
    filas = [encabezado]

    for _, nombre, unidad, precio, cantidad in items:
        subtotal = precio * cantidad
        filas.append([
            nombre,
            unidad,
            f"{cantidad:g}",
            _fmt(precio),
            _fmt(subtotal),
        ])

    # Fila de total de MP
    costo_mp = sum(p * c for _, _, _, p, c in items)
    filas.append(["", "", "", "Total MP (receta)", _fmt(costo_mp)])
    filas.append(["", "", "", f"Costo MP / kg  (÷ {rinde_kg:g} kg)", _fmt(costo_mp / rinde_kg) if rinde_kg else "—"])

    col_widths = [6.5*cm, 1.8*cm, 2.2*cm, 4.5*cm, 3.5*cm]

    t = Table(filas, colWidths=col_widths, repeatRows=1)
    n = len(filas)
    t.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND",   (0, 0), (-1, 0), AZUL_OSC),
        ("TEXTCOLOR",    (0, 0), (-1, 0), BLANCO),
        ("FONTNAME",     (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",     (0, 0), (-1, 0), 10),
        ("ALIGN",        (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING",(0, 0), (-1, 0), 7),
        ("TOPPADDING",   (0, 0), (-1, 0), 7),
        # Datos
        ("FONTNAME",     (0, 1), (-1, n-3), "Helvetica"),
        ("FONTSIZE",     (0, 1), (-1, n-3), 9),
        ("ALIGN",        (2, 1), (-1, n-3), "RIGHT"),
        ("ALIGN",        (0, 1), (1, n-3), "LEFT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, n-3), [BLANCO, GRIS_FILA]),
        ("BOTTOMPADDING",(0, 1), (-1, n-3), 5),
        ("TOPPADDING",   (0, 1), (-1, n-3), 5),
        # Filas de totales
        ("FONTNAME",     (0, n-2), (-1, n-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0, n-2), (-1, n-1), 9),
        ("ALIGN",        (3, n-2), (-1, n-1), "RIGHT"),
        ("BACKGROUND",   (0, n-2), (-1, n-1), colors.HexColor("#e8eeff")),
        ("SPAN",         (0, n-2), (2, n-2)),
        ("SPAN",         (0, n-1), (2, n-1)),
        # Bordes
        ("GRID",         (0, 0), (-1, n-1), 0.4, colors.HexColor("#d0d8f0")),
        ("LINEBELOW",    (0, 0), (-1, 0), 1, AZUL_OSC),
    ]))
    return t


def _tabla_costos(costo_mp_kg, gv_kg, costo_total_kg, margen_pct, precio_venta_kg):
    filas = [
        ["Concepto",              "Valor / kg"],
        ["Costo materia prima",   _fmt(costo_mp_kg)],
        ["Gasto variable",        _fmt(gv_kg)],
        ["Costo total",           _fmt(costo_total_kg)],
        [f"Margen aplicado",      f"{margen_pct:.1f}% sobre precio de venta"],
        ["PRECIO DE VENTA",       _fmt(precio_venta_kg)],
    ]
    col_widths = [9*cm, 9.5*cm]
    t = Table(filas, colWidths=col_widths)
    n = len(filas)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), AZUL_MED),
        ("TEXTCOLOR",     (0, 0), (-1, 0), BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0), 10),
        ("ALIGN",         (0, 0), (-1, 0), "CENTER"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
        ("TOPPADDING",    (0, 0), (-1, 0), 7),
        ("FONTNAME",      (0, 1), (-1, n-2), "Helvetica"),
        ("FONTSIZE",      (0, 1), (-1, n-2), 10),
        ("ALIGN",         (1, 1), (1, n-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0, 1), (-1, n-2), [BLANCO, GRIS_FILA]),
        ("BOTTOMPADDING", (0, 1), (-1, n-2), 6),
        ("TOPPADDING",    (0, 1), (-1, n-2), 6),
        # Fila precio de venta
        ("BACKGROUND",    (0, n-1), (-1, n-1), AZUL_OSC),
        ("TEXTCOLOR",     (0, n-1), (-1, n-1), VERDE),
        ("FONTNAME",      (0, n-1), (-1, n-1), "Helvetica-Bold"),
        ("FONTSIZE",      (0, n-1), (-1, n-1), 13),
        ("BOTTOMPADDING", (0, n-1), (-1, n-1), 10),
        ("TOPPADDING",    (0, n-1), (-1, n-1), 10),
        ("GRID",          (0, 0), (-1, n-1), 0.4, colors.HexColor("#d0d8f0")),
        ("LINEBELOW",     (0, 0), (-1, 0), 1, AZUL_MED),
    ]))
    return t


def generar_pdf(receta_id: int, ruta_destino: str) -> str:
    """
    Genera el PDF para la receta indicada y lo guarda en ruta_destino.
    Retorna la ruta del archivo generado.
    """
    # Datos
    receta = next((r for r in db.get_recetas() if r["id"] == receta_id), None)
    if not receta:
        raise ValueError(f"Receta id={receta_id} no encontrada.")

    ings    = db.get_receta_ingredientes(receta_id)
    items   = [(r["ingrediente_id"], r["nombre"], r["unidad"], r["precio"], r["cantidad"]) for r in ings]
    costos  = db.calcular_costo_receta(receta_id)
    gastos  = db.get_gastos()

    rinde      = receta["rinde_kg"]
    margen_pct = receta["margen_pct"]
    fecha_hoy  = datetime.now().strftime("%d/%m/%Y %H:%M")

    estilos = _estilos()
    doc = SimpleDocTemplate(
        ruta_destino,
        pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm,
        title=f"Receta — {receta['nombre']}",
        author="Fábrica de Helados",
    )

    story = []

    # ── Encabezado con fondo ──────────────────────────────────────────────
    header_data = [[
        Paragraph("Fábrica de Helados", estilos["titulo"]),
        Paragraph("Calculadora de costos de producción", estilos["subtitulo"]),
    ]]
    header_tbl = Table([[
        Paragraph("FÁBRICA DE HELADOS", estilos["titulo"]),
    ]], colWidths=[18.5*cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_OSC),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
        ("TOPPADDING",    (0, 0), (-1, -1), 14),
        ("ROUNDEDCORNERS", [6]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 0.3*cm))

    sub_tbl = Table([[
        Paragraph("Calculadora de costos de producción", estilos["subtitulo"]),
    ]], colWidths=[18.5*cm])
    sub_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), AZUL_MED),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ]))
    story.append(sub_tbl)
    story.append(Spacer(1, 0.5*cm))

    # ── Nombre de la receta + fecha ───────────────────────────────────────
    story.append(Paragraph(receta["nombre"], estilos["receta"]))
    story.append(Paragraph(
        f"Fecha de generación: {fecha_hoy}  ·  Rinde: {rinde:g} kg  ·  Margen: {margen_pct:.1f}%",
        estilos["fecha"],
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=AZUL_OSC, spaceAfter=8))

    # ── Ingredientes ─────────────────────────────────────────────────────
    story.append(Paragraph("Ingredientes", estilos["seccion"]))
    if items:
        story.append(_tabla_ingredientes(items, rinde, estilos))
    else:
        story.append(Paragraph("Sin ingredientes cargados.", estilos["fecha"]))

    story.append(Spacer(1, 0.5*cm))

    # ── Desglose de gastos variables ─────────────────────────────────────
    story.append(Paragraph("Gastos variables del período", estilos["seccion"]))
    if gastos:
        gasto_filas = [["Concepto", "Monto", "Período", "Producción (kg)", "$ / kg"]]
        for g in gastos:
            gv = g["monto"] / g["produccion_kg"] if g["produccion_kg"] else 0
            gasto_filas.append([
                g["nombre"],
                _fmt(g["monto"]),
                g["periodo"],
                f"{g['produccion_kg']:,.0f} kg".replace(",", "."),
                _fmt(gv),
            ])
        total_gv = db.get_gasto_variable_por_kg()
        gasto_filas.append(["", "", "", "Total GV / kg", _fmt(total_gv)])

        gasto_tbl = Table(gasto_filas, colWidths=[5*cm, 3.2*cm, 2.2*cm, 3.8*cm, 3.2*cm], repeatRows=1)
        ng = len(gasto_filas)
        gasto_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), AZUL_MED),
            ("TEXTCOLOR",     (0, 0), (-1, 0), BLANCO),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, 0), 9),
            ("ALIGN",         (1, 0), (-1, 0), "RIGHT"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
            ("TOPPADDING",    (0, 0), (-1, 0), 6),
            ("FONTNAME",      (0, 1), (-1, ng-2), "Helvetica"),
            ("FONTSIZE",      (0, 1), (-1, ng-2), 9),
            ("ALIGN",         (1, 1), (-1, ng-1), "RIGHT"),
            ("ROWBACKGROUNDS",(0, 1), (-1, ng-2), [BLANCO, GRIS_FILA]),
            ("BOTTOMPADDING", (0, 1), (-1, ng-1), 5),
            ("TOPPADDING",    (0, 1), (-1, ng-1), 5),
            ("FONTNAME",      (0, ng-1), (-1, ng-1), "Helvetica-Bold"),
            ("BACKGROUND",    (0, ng-1), (-1, ng-1), colors.HexColor("#e8eeff")),
            ("SPAN",          (0, ng-1), (2, ng-1)),
            ("GRID",          (0, 0), (-1, ng-1), 0.4, colors.HexColor("#d0d8f0")),
            ("LINEBELOW",     (0, 0), (-1, 0), 1, AZUL_MED),
        ]))
        story.append(gasto_tbl)
    else:
        story.append(Paragraph("Sin gastos variables cargados.", estilos["fecha"]))

    story.append(Spacer(1, 0.5*cm))

    # ── Resumen de costos ─────────────────────────────────────────────────
    story.append(Paragraph("Resumen de costos", estilos["seccion"]))
    story.append(_tabla_costos(
        costos["costo_mp_kg"],
        costos["gasto_var_kg"],
        costos["costo_total_kg"],
        margen_pct,
        costos["precio_venta_kg"],
    ))

    # ── Pie de página ─────────────────────────────────────────────────────
    story.append(Paragraph(
        f"Generado el {fecha_hoy} · Fábrica de Helados — Sistema de costeo",
        estilos["nota"],
    ))

    doc.build(story)
    return ruta_destino
