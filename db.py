"""
db.py - La base es la autoridad (paso 3 y registro del flujo de B.6).

Version ejecutable, en SQLite, del esquema de sql/schema.sql (B.5.b, Postgres).
El LLM ya interpreto el mensaje y Pydantic ya valido el contrato (schemas.py);
esto es lo unico que puede decir si hay stock, cuanto sale y si una reserva
se puede tomar. Ningun dato de negocio sale de aca sin pasar por SQL.

Uso tipico:
    conn = conectar()
    resultado = consultar_disponibilidad(conn, "hidrolavadora", fecha_inicio, fecha_fin, 1)
"""

from __future__ import annotations

import sqlite3
from datetime import date
from typing import Optional

RUTA_DB_DEFAULT = "alquiherramientas.db"

# Catalogo semilla: un renglon por cada valor canonico de CATALOGO_ALIAS en schemas.py.
# Es el mismo vocabulario controlado -- si un codigo no esta aca, no existe para el negocio.
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

ESTADOS_QUE_OCUPAN_STOCK = ("pendiente", "confirmada", "entregada")


def conectar(ruta: str = RUTA_DB_DEFAULT) -> sqlite3.Connection:
    """Abre (y si hace falta, inicializa) la base. Una conexion por proceso alcanza."""
    conn = sqlite3.connect(ruta)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    _init_db(conn)
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Crea las tablas si no existen y siembra el catalogo. Idempotente."""
    conn.executescript(
        """
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

        CREATE TABLE IF NOT EXISTS interacciones (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            telefono            TEXT,
            canal               TEXT NOT NULL DEFAULT 'whatsapp',
            texto_libre         TEXT NOT NULL,
            intencion_detectada TEXT,
            parametros_json     TEXT,
            contrato_valido     INTEGER NOT NULL,
            error_validacion    TEXT,
            confianza           REAL,
            requiere_humano     INTEGER NOT NULL DEFAULT 0,
            respuesta_enviada   TEXT,
            reserva_id          INTEGER REFERENCES reservas(id),
            modelo              TEXT,
            creado_en           TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    ya_sembrado = conn.execute("SELECT COUNT(*) FROM herramientas").fetchone()[0]
    if not ya_sembrado:
        conn.executemany(
            """
            INSERT INTO herramientas
                (codigo, nombre, categoria, stock_total, precio_dia, deposito_garantia, requiere_dni)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            CATALOGO_SEMILLA,
        )
    conn.commit()


def _obtener_herramienta(conn: sqlite3.Connection, codigo: str) -> Optional[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM herramientas WHERE codigo = ? AND activo = 1", (codigo,)
    ).fetchone()


def _stock_ocupado(
    conn: sqlite3.Connection, herramienta_id: int, fecha_inicio: str, fecha_fin: str
) -> int:
    """Suma la cantidad reservada que solapa la ventana pedida. Nunca la calcula el LLM."""
    placeholders = ",".join("?" * len(ESTADOS_QUE_OCUPAN_STOCK))
    fila = conn.execute(
        f"""
        SELECT COALESCE(SUM(cantidad), 0) AS ocupado
        FROM reservas
        WHERE herramienta_id = ?
          AND estado IN ({placeholders})
          AND fecha_inicio <= ?
          AND fecha_fin    >= ?
        """,
        (herramienta_id, *ESTADOS_QUE_OCUPAN_STOCK, fecha_fin, fecha_inicio),
    ).fetchone()
    return fila["ocupado"]


def consultar_disponibilidad(
    conn: sqlite3.Connection,
    herramienta: str,
    fecha_inicio: Optional[date],
    fecha_fin: Optional[date],
    cantidad: int = 1,
) -> dict:
    """Paso 3 del flujo (B.6) para consultar_disponibilidad. Resultado verificado, no opinado."""
    h = _obtener_herramienta(conn, herramienta)
    if h is None:
        return {"encontrado": False, "herramienta": herramienta}

    # Sin fecha no hay ventana que chequear: informamos el stock total como referencia.
    ini = (fecha_inicio or date.today()).isoformat()
    fin = (fecha_fin or fecha_inicio or date.today()).isoformat()
    ocupado = _stock_ocupado(conn, h["id"], ini, fin)
    libres = h["stock_total"] - ocupado

    return {
        "encontrado": True,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "stock_total": h["stock_total"],
        "disponibles": max(libres, 0),
        "disponible": libres >= cantidad,
        "precio_dia": h["precio_dia"],
        "fecha_inicio": ini,
        "fecha_fin": fin,
    }


def consultar_precio(
    conn: sqlite3.Connection, herramienta: str, dias_alquiler: Optional[int]
) -> dict:
    """Paso 3 del flujo (B.6) para consultar_precio. El total lo calcula el codigo, no el LLM."""
    h = _obtener_herramienta(conn, herramienta)
    if h is None:
        return {"encontrado": False, "herramienta": herramienta}

    dias = dias_alquiler or 1
    return {
        "encontrado": True,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "precio_dia": h["precio_dia"],
        "deposito_garantia": h["deposito_garantia"],
        "dias_alquiler": dias,
        "precio_total": round(h["precio_dia"] * dias, 2),
    }


def _upsert_cliente(conn: sqlite3.Connection, telefono: str) -> int:
    conn.execute(
        "INSERT INTO clientes (telefono) VALUES (?) ON CONFLICT(telefono) DO NOTHING",
        (telefono,),
    )
    fila = conn.execute("SELECT id FROM clientes WHERE telefono = ?", (telefono,)).fetchone()
    return fila["id"]


def crear_reserva(
    conn: sqlite3.Connection,
    telefono: str,
    herramienta: str,
    cantidad: int,
    fecha_inicio: date,
    fecha_fin: date,
) -> dict:
    """Paso 3 del flujo (B.6) para solicitar_reserva. Escribe SOLO si hay stock real."""
    disponibilidad = consultar_disponibilidad(conn, herramienta, fecha_inicio, fecha_fin, cantidad)
    if not disponibilidad["encontrado"]:
        return {"reservado": False, "motivo": "herramienta_no_encontrada", **disponibilidad}
    if not disponibilidad["disponible"]:
        return {"reservado": False, "motivo": "sin_stock", **disponibilidad}

    h = _obtener_herramienta(conn, herramienta)
    cliente_id = _upsert_cliente(conn, telefono)
    dias = (fecha_fin - fecha_inicio).days + 1
    precio_total = round(h["precio_dia"] * dias, 2)

    cursor = conn.execute(
        """
        INSERT INTO reservas
            (cliente_id, herramienta_id, cantidad, fecha_inicio, fecha_fin, estado, precio_total)
        VALUES (?, ?, ?, ?, ?, 'pendiente', ?)
        """,
        (cliente_id, h["id"], cantidad, fecha_inicio.isoformat(), fecha_fin.isoformat(), precio_total),
    )
    conn.commit()
    return {
        "reservado": True,
        "reserva_id": cursor.lastrowid,
        "herramienta": herramienta,
        "nombre": h["nombre"],
        "cantidad": cantidad,
        "fecha_inicio": fecha_inicio.isoformat(),
        "fecha_fin": fecha_fin.isoformat(),
        "estado": "pendiente",
        "precio_total": precio_total,
        "deposito_garantia": h["deposito_garantia"],
    }


def registrar_interaccion(
    conn: sqlite3.Connection,
    telefono: Optional[str],
    texto_libre: str,
    intencion_detectada: Optional[str],
    parametros_json: Optional[str],
    contrato_valido: bool,
    error_validacion: Optional[str],
    confianza: Optional[float],
    requiere_humano: bool,
    respuesta_enviada: Optional[str],
    reserva_id: Optional[int],
    modelo: Optional[str],
) -> int:
    """Traza cada mensaje procesado. Alimenta las metricas de Performance del PEAS (A.3)."""
    cursor = conn.execute(
        """
        INSERT INTO interacciones
            (telefono, texto_libre, intencion_detectada, parametros_json, contrato_valido,
             error_validacion, confianza, requiere_humano, respuesta_enviada, reserva_id, modelo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            telefono,
            texto_libre,
            intencion_detectada,
            parametros_json,
            int(contrato_valido),
            error_validacion,
            confianza,
            int(requiere_humano),
            respuesta_enviada,
            reserva_id,
            modelo,
        ),
    )
    conn.commit()
    return cursor.lastrowid
