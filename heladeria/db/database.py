import sqlite3
import sys
import os


def _get_db_path():
    if getattr(sys, "frozen", False):
        # Ejecutando como .exe — guardar en AppData para que sea persistente
        app_data = os.path.join(os.environ.get("APPDATA", os.path.expanduser("~")), "Heladeria")
        os.makedirs(app_data, exist_ok=True)
        return os.path.join(app_data, "heladeria.db")
    return os.path.join(os.path.dirname(__file__), "heladeria.db")


DB_PATH = _get_db_path()


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_connection() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS ingredientes (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre              TEXT    NOT NULL,
                precio              REAL    NOT NULL,
                unidad              TEXT    NOT NULL,
                fecha_actualizacion TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gastos (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL,
                monto          REAL    NOT NULL,
                periodo        TEXT    NOT NULL DEFAULT 'mensual',
                produccion_kg  REAL    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS recetas (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre         TEXT    NOT NULL,
                rinde_kg       REAL    NOT NULL,
                margen_pct     REAL    NOT NULL DEFAULT 40.0,
                fecha_creacion TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS receta_ingredientes (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                receta_id       INTEGER NOT NULL REFERENCES recetas(id)     ON DELETE CASCADE,
                ingrediente_id  INTEGER NOT NULL REFERENCES ingredientes(id) ON DELETE RESTRICT,
                cantidad        REAL    NOT NULL
            );
        """)


# ---------- Ingredientes ----------

def get_ingredientes():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM ingredientes ORDER BY nombre").fetchall()


def add_ingrediente(nombre, precio, unidad, fecha):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ingredientes (nombre, precio, unidad, fecha_actualizacion) VALUES (?, ?, ?, ?)",
            (nombre, precio, unidad, fecha),
        )


def update_ingrediente(id_, nombre, precio, unidad, fecha):
    with get_connection() as conn:
        conn.execute(
            "UPDATE ingredientes SET nombre=?, precio=?, unidad=?, fecha_actualizacion=? WHERE id=?",
            (nombre, precio, unidad, fecha, id_),
        )


def delete_ingrediente(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM ingredientes WHERE id=?", (id_,))


# ---------- Gastos ----------

def get_gastos():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM gastos ORDER BY nombre").fetchall()


def add_gasto(nombre, monto, periodo, produccion_kg):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gastos (nombre, monto, periodo, produccion_kg) VALUES (?, ?, ?, ?)",
            (nombre, monto, periodo, produccion_kg),
        )


def update_gasto(id_, nombre, monto, periodo, produccion_kg):
    with get_connection() as conn:
        conn.execute(
            "UPDATE gastos SET nombre=?, monto=?, periodo=?, produccion_kg=? WHERE id=?",
            (nombre, monto, periodo, produccion_kg, id_),
        )


def delete_gasto(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id=?", (id_,))


def get_gasto_variable_por_kg():
    """Suma todos los gastos y los divide por los kg de producción del período."""
    with get_connection() as conn:
        rows = conn.execute("SELECT monto, produccion_kg FROM gastos").fetchall()
    if not rows:
        return 0.0
    total_gastos = sum(r["monto"] for r in rows)
    # Usa el promedio ponderado de produccion_kg entre todos los registros
    total_kg = sum(r["produccion_kg"] for r in rows)
    if total_kg == 0:
        return 0.0
    return total_gastos / total_kg


# ---------- Recetas ----------

def get_recetas():
    with get_connection() as conn:
        return conn.execute("SELECT * FROM recetas ORDER BY nombre").fetchall()


def add_receta(nombre, rinde_kg, margen_pct, fecha):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO recetas (nombre, rinde_kg, margen_pct, fecha_creacion) VALUES (?, ?, ?, ?)",
            (nombre, rinde_kg, margen_pct, fecha),
        )
        return cur.lastrowid


def update_receta(id_, nombre, rinde_kg, margen_pct):
    with get_connection() as conn:
        conn.execute(
            "UPDATE recetas SET nombre=?, rinde_kg=?, margen_pct=? WHERE id=?",
            (nombre, rinde_kg, margen_pct, id_),
        )


def delete_receta(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM recetas WHERE id=?", (id_,))


# ---------- Receta ingredientes ----------

def get_receta_ingredientes(receta_id):
    with get_connection() as conn:
        return conn.execute(
            """
            SELECT ri.id, ri.ingrediente_id, ri.cantidad, i.nombre, i.precio, i.unidad
            FROM receta_ingredientes ri
            JOIN ingredientes i ON i.id = ri.ingrediente_id
            WHERE ri.receta_id = ?
            ORDER BY i.nombre
            """,
            (receta_id,),
        ).fetchall()


def set_receta_ingredientes(receta_id, items):
    """items: lista de (ingrediente_id, cantidad)"""
    with get_connection() as conn:
        conn.execute("DELETE FROM receta_ingredientes WHERE receta_id=?", (receta_id,))
        conn.executemany(
            "INSERT INTO receta_ingredientes (receta_id, ingrediente_id, cantidad) VALUES (?, ?, ?)",
            [(receta_id, ing_id, cant) for ing_id, cant in items],
        )


# ---------- Cálculo de costo ----------

def calcular_costo_receta(receta_id):
    with get_connection() as conn:
        receta = conn.execute("SELECT rinde_kg, margen_pct FROM recetas WHERE id=?", (receta_id,)).fetchone()
    if not receta or receta["rinde_kg"] == 0:
        return {"costo_mp_kg": 0, "gasto_var_kg": 0, "costo_total_kg": 0, "precio_venta_kg": 0}

    ings = get_receta_ingredientes(receta_id)
    costo_mp = sum(r["cantidad"] * r["precio"] for r in ings)
    costo_mp_kg = costo_mp / receta["rinde_kg"]

    gasto_var_kg = get_gasto_variable_por_kg()
    costo_total_kg = costo_mp_kg + gasto_var_kg

    margen = receta["margen_pct"] / 100
    precio_venta_kg = costo_total_kg / (1 - margen) if margen < 1 else 0

    return {
        "costo_mp_kg": round(costo_mp_kg, 2),
        "gasto_var_kg": round(gasto_var_kg, 2),
        "costo_total_kg": round(costo_total_kg, 2),
        "precio_venta_kg": round(precio_venta_kg, 2),
    }
