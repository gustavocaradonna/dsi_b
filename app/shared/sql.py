"""
Base SQL de negocio (SQLite): conexión, esquema, catálogo semilla y las dos lecturas que comparten
varios slices (herramienta activa por código y stock ocupado en una ventana).

Viene de db.py de la Entrega 1 (entregas/entrega_1/db.py). Cada consulta propia de un caso de uso
vive en su slice (herramientas/<slice>/consultas.py), no acá: esto es solo la infraestructura.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal, Optional

from app.shared import config

# Un renglón por herramienta del catálogo: si un código no está acá, no existe para el negocio.
CATALOGO_SEMILLA = [
    # codigo, nombre, categoria, stock_total, precio_dia, deposito_garantia, requiere_dni
    ("taladro", "Taladro percutor Bosch GSB 550", "electrico", 6, 3500.00, 15000.00, True),
    ("hidrolavadora", "Hidrolavadora Karcher K4", "limpieza", 4, 12000.00, 30000.00, True),
    ("lijadora", "Lijadora orbital Makita BO3710", "electrico", 5, 2800.00, 10000.00, True),
    ("amoladora", "Amoladora angular Dewalt 4 1/2", "electrico", 5, 2500.00, 10000.00, True),
    ("sierra_circular", "Sierra circular Makita 5007N", "electrico", 3, 4200.00, 18000.00, True),
    ("andamio", "Modulo de andamio tubular 1.5m", "estructura", 20, 1800.00, 20000.00, True),
    ("martillo_demoledor", "Martillo demoledor Bosch GSH 5", "electrico", 2, 9500.00, 40000.00, True),
    ("hormigonera", "Hormigonera electrica 150L", "obra", 3, 8000.00, 35000.00, True),
]
CodigoHerramienta = Literal[tuple(codigo for codigo, *_ in CATALOGO_SEMILLA)]  # type: ignore[valid-type]

ESTADOS_QUE_OCUPAN_STOCK = ("pendiente", "confirmada", "entregada")

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS herramientas (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo            TEXT NOT NULL UNIQUE,
    nombre            TEXT NOT NULL,
    categoria         TEXT NOT NULL,
    stock_total       INTEGER NOT NULL CHECK (stock_total >= 0),
    precio_dia        REAL NOT NULL CHECK (precio_dia > 0),
    deposito_garantia REAL NOT NULL DEFAULT 0,
    requiere_dni      INTEGER NOT NULL DEFAULT 1,
    activo            INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS clientes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    telefono   TEXT NOT NULL UNIQUE,
    nombre     TEXT,
    dni        TEXT,
    creado_en  TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reservas (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    cliente_id     INTEGER NOT NULL REFERENCES clientes(id),
    herramienta_id INTEGER NOT NULL REFERENCES herramientas(id),
    cantidad       INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 10),
    fecha_inicio   TEXT NOT NULL,
    fecha_fin      TEXT NOT NULL,
    estado         TEXT NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','confirmada','entregada','devuelta','cancelada')),
    precio_total   REAL,
    creado_en      TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (fecha_fin >= fecha_inicio)
);
"""


def conectar(ruta: Path | str | None = None) -> sqlite3.Connection:
    """Abre la base (y si no existe, la crea y siembra el catálogo). Idempotente."""
    config.asegurar_directorios()
    conn = sqlite3.connect(str(ruta or config.RUTA_DB_NEGOCIO))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(_ESQUEMA)
    if not conn.execute("SELECT COUNT(*) FROM herramientas").fetchone()[0]:
        conn.executemany(
            "INSERT INTO herramientas (codigo, nombre, categoria, stock_total, precio_dia, deposito_garantia, requiere_dni)"
            " VALUES (?, ?, ?, ?, ?, ?, ?)",
            CATALOGO_SEMILLA,
        )
    conn.commit()
    return conn


def obtener_herramienta(conn: sqlite3.Connection, codigo: str) -> Optional[sqlite3.Row]:
    return conn.execute("SELECT * FROM herramientas WHERE codigo = ? AND activo = 1", (codigo,)).fetchone()


def stock_ocupado(conn: sqlite3.Connection, herramienta_id: int, fecha_inicio: str, fecha_fin: str) -> int:
    """Unidades reservadas que se solapan con la ventana pedida. Nunca lo calcula el LLM."""
    marcadores = ",".join("?" * len(ESTADOS_QUE_OCUPAN_STOCK))
    fila = conn.execute(
        f"""
        SELECT COALESCE(SUM(cantidad), 0) AS ocupado
        FROM reservas
        WHERE herramienta_id = ? AND estado IN ({marcadores}) AND fecha_inicio <= ? AND fecha_fin >= ?
        """,
        (herramienta_id, *ESTADOS_QUE_OCUPAN_STOCK, fecha_fin, fecha_inicio),
    ).fetchone()
    return fila["ocupado"]
