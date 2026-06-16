import sqlite3
import sys
import os


def _get_db_path():
    if getattr(sys, "frozen", False):
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

            CREATE TABLE IF NOT EXISTS periodos_gastos (
                id      INTEGER PRIMARY KEY AUTOINCREMENT,
                anio    INTEGER NOT NULL,
                mes     INTEGER NOT NULL,
                kg_prod REAL    NOT NULL,
                UNIQUE(anio, mes)
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
    _migrate_gastos()


def _migrate_gastos():
    """Migrates old gastos schema (with produccion_kg) to new period-based schema."""
    with get_connection() as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info(gastos)").fetchall()]

    if not cols:
        with get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS gastos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo_id INTEGER NOT NULL REFERENCES periodos_gastos(id) ON DELETE CASCADE,
                    nombre     TEXT    NOT NULL,
                    monto      REAL    NOT NULL
                )
            """)
    elif "produccion_kg" in cols:
        # Old schema detected — drop and recreate (data is incompatible with new model)
        with get_connection() as conn:
            conn.executescript("""
                DROP TABLE IF EXISTS gastos;
                CREATE TABLE gastos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    periodo_id INTEGER NOT NULL REFERENCES periodos_gastos(id) ON DELETE CASCADE,
                    nombre     TEXT    NOT NULL,
                    monto      REAL    NOT NULL
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


# ---------- Períodos de gastos ----------

def get_periodos_gastos():
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM periodos_gastos ORDER BY anio DESC, mes DESC"
        ).fetchall()


def get_periodo_by_mes_anio(mes, anio):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM periodos_gastos WHERE mes=? AND anio=?", (mes, anio)
        ).fetchone()


def upsert_periodo(mes, anio, kg_prod):
    """Creates or updates a period. Returns its id."""
    with get_connection() as conn:
        existing = conn.execute(
            "SELECT id FROM periodos_gastos WHERE mes=? AND anio=?", (mes, anio)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE periodos_gastos SET kg_prod=? WHERE id=?", (kg_prod, existing["id"])
            )
            return existing["id"]
        cur = conn.execute(
            "INSERT INTO periodos_gastos (mes, anio, kg_prod) VALUES (?, ?, ?)",
            (mes, anio, kg_prod)
        )
        return cur.lastrowid


def delete_periodo(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM periodos_gastos WHERE id=?", (id_,))


# ---------- Gastos ----------

def get_gastos():
    """Returns all gastos across all periods (used for count in dashboard)."""
    with get_connection() as conn:
        return conn.execute("SELECT * FROM gastos ORDER BY nombre").fetchall()


def get_gastos_by_periodo(periodo_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM gastos WHERE periodo_id=? ORDER BY nombre", (periodo_id,)
        ).fetchall()


def add_gasto(periodo_id, nombre, monto):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO gastos (periodo_id, nombre, monto) VALUES (?, ?, ?)",
            (periodo_id, nombre, monto)
        )


def update_gasto(id_, nombre, monto):
    with get_connection() as conn:
        conn.execute(
            "UPDATE gastos SET nombre=?, monto=? WHERE id=?",
            (nombre, monto, id_)
        )


def delete_gasto(id_):
    with get_connection() as conn:
        conn.execute("DELETE FROM gastos WHERE id=?", (id_,))


def get_gasto_variable_por_kg():
    """Historical weighted average: sum(all montos) / sum(all kg). Used in recipe cost."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT pg.kg_prod, COALESCE(SUM(g.monto), 0) AS total_gastos
            FROM periodos_gastos pg
            LEFT JOIN gastos g ON g.periodo_id = pg.id
            GROUP BY pg.id
        """).fetchall()
    if not rows:
        return 0.0
    total_montos = sum(r["total_gastos"] for r in rows)
    total_kg = sum(r["kg_prod"] for r in rows)
    return total_montos / total_kg if total_kg else 0.0


def get_gasto_variable_periodo(periodo_id):
    """Cost per kg for a specific period (for display on gastos screen)."""
    with get_connection() as conn:
        periodo = conn.execute(
            "SELECT kg_prod FROM periodos_gastos WHERE id=?", (periodo_id,)
        ).fetchone()
        if not periodo or periodo["kg_prod"] == 0:
            return 0.0
        total = conn.execute(
            "SELECT COALESCE(SUM(monto), 0) AS total FROM gastos WHERE periodo_id=?",
            (periodo_id,)
        ).fetchone()
    return total["total"] / periodo["kg_prod"]


def get_gasto_variable_historico():
    """Returns weighted avg and period count across all months."""
    with get_connection() as conn:
        rows = conn.execute("""
            SELECT pg.kg_prod, COALESCE(SUM(g.monto), 0) AS total_gastos
            FROM periodos_gastos pg
            LEFT JOIN gastos g ON g.periodo_id = pg.id
            GROUP BY pg.id
        """).fetchall()
    if not rows:
        return {"promedio_kg": 0.0, "n_periodos": 0}
    total_montos = sum(r["total_gastos"] for r in rows)
    total_kg = sum(r["kg_prod"] for r in rows)
    promedio = total_montos / total_kg if total_kg else 0.0
    return {"promedio_kg": promedio, "n_periodos": len(rows)}


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
        receta = conn.execute(
            "SELECT rinde_kg, margen_pct FROM recetas WHERE id=?", (receta_id,)
        ).fetchone()
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
