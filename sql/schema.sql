-- =====================================================================
-- AlquiHerramientas - Esquema de base de datos (B.5.b)
-- Motor de referencia: PostgreSQL (compatible con SQLite salvo tipos)
--
-- Principio de diseno: la base es la AUTORIDAD. El LLM interpreta el
-- mensaje, pero disponibilidad, precio y confirmacion de reserva se
-- resuelven aca, con SQL determinista.
-- =====================================================================

-- ---------------------------------------------------------------------
-- Entidad principal del dominio: el parque de herramientas en alquiler.
-- ---------------------------------------------------------------------
CREATE TABLE herramientas (
    id                SERIAL PRIMARY KEY,
    codigo            VARCHAR(20)  NOT NULL UNIQUE,   -- coincide con el Literal normalizado
    nombre            VARCHAR(80)  NOT NULL,          -- "Taladro percutor Bosch GSB 550"
    categoria         VARCHAR(40)  NOT NULL,
    stock_total       INTEGER      NOT NULL CHECK (stock_total >= 0),
    precio_dia        NUMERIC(10,2) NOT NULL CHECK (precio_dia > 0),
    deposito_garantia NUMERIC(10,2) NOT NULL DEFAULT 0,
    requiere_dni      BOOLEAN      NOT NULL DEFAULT TRUE,
    activo            BOOLEAN      NOT NULL DEFAULT TRUE
);

-- ---------------------------------------------------------------------
-- Clientes. El telefono de WhatsApp es la clave natural del canal.
-- ---------------------------------------------------------------------
CREATE TABLE clientes (
    id            SERIAL PRIMARY KEY,
    telefono      VARCHAR(20) NOT NULL UNIQUE,        -- E.164, normalizado por Pydantic
    nombre        VARCHAR(80),
    dni           VARCHAR(15),
    creado_en     TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ---------------------------------------------------------------------
-- Reservas: la unica tabla que el sistema ESCRIBE por pedido del cliente.
-- Por eso solicitar_reserva es la intencion de riesgo ALTO.
-- ---------------------------------------------------------------------
CREATE TABLE reservas (
    id             SERIAL PRIMARY KEY,
    cliente_id     INTEGER NOT NULL REFERENCES clientes(id),
    herramienta_id INTEGER NOT NULL REFERENCES herramientas(id),
    cantidad       INTEGER NOT NULL CHECK (cantidad BETWEEN 1 AND 10),
    fecha_inicio   DATE    NOT NULL,
    fecha_fin      DATE    NOT NULL,
    estado         VARCHAR(20) NOT NULL DEFAULT 'pendiente'
                   CHECK (estado IN ('pendiente','confirmada','entregada','devuelta','cancelada')),
    precio_total   NUMERIC(10,2),                     -- lo calcula el backend, nunca el LLM
    creado_en      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT rango_valido CHECK (fecha_fin >= fecha_inicio)
);

CREATE INDEX idx_reservas_disponibilidad
    ON reservas (herramienta_id, fecha_inicio, fecha_fin)
    WHERE estado IN ('pendiente','confirmada','entregada');

-- ---------------------------------------------------------------------
-- Interacciones: la traza de lo que el LLM entendio en cada mensaje.
-- Es la tabla que permite auditar al modelo y medir el Performance del PEAS.
-- ---------------------------------------------------------------------
CREATE TABLE interacciones (
    id                 SERIAL PRIMARY KEY,
    telefono           VARCHAR(20) NOT NULL,
    canal              VARCHAR(20) NOT NULL DEFAULT 'whatsapp',
    texto_libre        TEXT        NOT NULL,          -- mensaje crudo del cliente
    intencion_detectada VARCHAR(30),                  -- valores del Literal de schemas.py
    parametros_json    JSONB,                         -- el JSON completo que devolvio el LLM
    contrato_valido    BOOLEAN     NOT NULL,          -- paso o no paso Pydantic
    error_validacion   TEXT,                          -- motivo del rechazo, si fallo
    confianza          NUMERIC(3,2),
    requiere_humano    BOOLEAN     NOT NULL DEFAULT FALSE,
    respuesta_enviada  TEXT,
    reserva_id         INTEGER REFERENCES reservas(id),
    modelo             VARCHAR(40),                   -- gemini-2.5-flash
    latencia_ms        INTEGER,
    creado_en          TIMESTAMP   NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_interacciones_intencion ON interacciones (intencion_detectada, creado_en);
CREATE INDEX idx_interacciones_fallidas  ON interacciones (contrato_valido) WHERE NOT contrato_valido;

-- ---------------------------------------------------------------------
-- Consulta de disponibilidad: la respuesta REAL que el LLM no puede inventar.
-- ---------------------------------------------------------------------
-- SELECT h.nombre,
--        h.stock_total - COALESCE(SUM(r.cantidad), 0) AS disponibles,
--        h.precio_dia
-- FROM herramientas h
-- LEFT JOIN reservas r
--        ON r.herramienta_id = h.id
--       AND r.estado IN ('pendiente','confirmada','entregada')
--       AND r.fecha_inicio <= :fecha_fin
--       AND r.fecha_fin    >= :fecha_inicio
-- WHERE h.codigo = :herramienta AND h.activo
-- GROUP BY h.id;
