"""
schemas.py - El contrato de datos en codigo (C.1).

Traduce el System Prompt y el JSON de B.5 a un modelo Pydantic V2.
La regla del sistema: el LLM interpreta, Pydantic es la aduana.
Todo lo que no cumple este contrato NO llega al backend.

Dominio: AlquiHerramientas (alquiler de herramientas por WhatsApp).
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

# Valores exactos de la Matriz de Intenciones (B.3).
# Este Literal es la unica fuente de verdad: lo usan el System Prompt,
# el JSON Schema que se le manda a Gemini y la tabla de resultados del lote.
Intencion = Literal[
    "consultar_disponibilidad",
    "consultar_precio",
    "solicitar_reserva",
    "fuera_de_alcance",
]

# Catalogo minimo de herramientas del local ficticio.
# No es la Base de Conocimiento (eso llega con RAG en la Unidad 3):
# es apenas el vocabulario controlado que normaliza el texto libre.
CATALOGO_ALIAS: dict[str, str] = {
    "taladro": "taladro",
    "taladro percutor": "taladro",
    "perforadora": "taladro",
    "hidrolavadora": "hidrolavadora",
    "hidro": "hidrolavadora",
    "lijadora": "lijadora",
    "lijadora orbital": "lijadora",
    "amoladora": "amoladora",
    "sierra": "sierra_circular",
    "sierra circular": "sierra_circular",
    "andamio": "andamio",
    "martillo demoledor": "martillo_demoledor",
    "hormigonera": "hormigonera",
    "mezcladora": "hormigonera",
}


def _normalizar_texto(valor: str) -> str:
    """Minusculas, sin tildes, sin espacios de mas. Determinista, no LLM."""
    sin_tildes = "".join(
        c for c in unicodedata.normalize("NFD", valor) if unicodedata.category(c) != "Mn"
    )
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


class SolicitudAlquiler(BaseModel):
    """Salida estructurada del LLM para un mensaje de WhatsApp."""

    # --- Nucleo de la extraccion ---
    intencion: Intencion = Field(
        description="Intencion detectada. Si no encaja en ninguna, fuera_de_alcance."
    )
    herramienta: Optional[str] = Field(
        default=None,
        description="Herramienta normalizada al catalogo. null si no se menciona.",
    )
    cantidad: int = Field(
        default=1, ge=1, le=10, description="Unidades pedidas. Por defecto 1."
    )

    # --- Ventana temporal del alquiler ---
    fecha_inicio: Optional[date] = Field(
        default=None,
        description="Fecha de retiro en formato YYYY-MM-DD. null si no se dice.",
    )
    fecha_fin: Optional[date] = Field(
        default=None,
        description="Fecha de devolucion en formato YYYY-MM-DD. null si no se dice.",
    )

    # --- Identificacion del cliente ---
    telefono_cliente: Optional[str] = Field(
        default=None,
        description="Telefono del remitente, normalizado a E.164 argentino.",
    )

    # --- Metadatos de control ---
    confianza: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Confianza del modelo en la extraccion."
    )
    requiere_humano: bool = Field(
        default=False,
        description="True si el mensaje es ambiguo, hostil o esta fuera del alcance.",
    )
    texto_original: Optional[str] = Field(
        default=None,
        description="Mensaje crudo, para auditoria en la tabla interacciones.",
    )

    # ------------------------------------------------------------------
    # Validadores con logica real (C.1)
    # ------------------------------------------------------------------

    @field_validator("herramienta", mode="before")
    @classmethod
    def normalizar_herramienta(cls, v):
        """Normaliza al vocabulario del catalogo. Lo que no existe, se rechaza."""
        if v is None:
            return None
        if not isinstance(v, str):
            raise ValueError("herramienta debe ser texto o null")
        texto = _normalizar_texto(v)
        if not texto or texto in {"null", "none", "n/a"}:
            return None
        if texto in CATALOGO_ALIAS:
            return CATALOGO_ALIAS[texto]
        # Coincidencia parcial: "un taladro percutor grande" -> taladro
        for alias, canonico in CATALOGO_ALIAS.items():
            if re.search(r"\b" + re.escape(alias) + r"\b", texto):
                return canonico
        raise ValueError(
            "herramienta '" + str(v) + "' no existe en el catalogo de AlquiHerramientas"
        )

    @field_validator("fecha_inicio", "fecha_fin", mode="before")
    @classmethod
    def rechazar_fechas_relativas(cls, v):
        """El LLM debe resolver la fecha o devolver null. 'el sabado' no es una fecha."""
        if v is None or isinstance(v, date):
            return v
        if not isinstance(v, str):
            raise ValueError("la fecha debe ser un string YYYY-MM-DD o null")
        texto = v.strip()
        if not texto or texto.lower() in {"null", "none", "n/a"}:
            return None
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", texto):
            raise ValueError(
                "fecha '" + texto + "' no esta en formato YYYY-MM-DD "
                "(no se aceptan fechas relativas)"
            )
        return texto

    @field_validator("telefono_cliente", mode="before")
    @classmethod
    def normalizar_telefono(cls, v):
        """Deja solo digitos y normaliza a E.164 argentino (+549...)."""
        if v is None:
            return None
        digitos = re.sub(r"\D", "", str(v))
        if not digitos:
            return None
        if digitos.startswith("54"):
            nacional = digitos[2:]
        elif digitos.startswith("0"):
            nacional = digitos.lstrip("0")
        else:
            nacional = digitos
        if nacional.startswith("9"):
            nacional = nacional[1:]
        if not 10 <= len(nacional) <= 11:
            raise ValueError(
                "telefono '" + str(v) + "' no tiene una cantidad valida de digitos"
            )
        return "+549" + nacional

    # ------------------------------------------------------------------
    # Reglas que cruzan campos
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def validar_coherencia(self) -> "SolicitudAlquiler":
        # Una reserva escribe en la base: sin herramienta ni fecha no se ejecuta.
        if self.intencion == "solicitar_reserva":
            if self.herramienta is None:
                raise ValueError("solicitar_reserva requiere herramienta identificada")
            if self.fecha_inicio is None:
                raise ValueError("solicitar_reserva requiere fecha_inicio")
        if self.fecha_inicio and self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin no puede ser anterior a fecha_inicio")
        # Baja confianza nunca se ejecuta sola: escala a un humano.
        if self.confianza < 0.6 and not self.requiere_humano:
            raise ValueError("confianza < 0.6 obliga a requiere_humano = true")
        return self

    @property
    def dias_alquiler(self) -> Optional[int]:
        """Dias facturables. El precio final lo calcula el SQL, no el LLM."""
        if self.fecha_inicio and self.fecha_fin:
            return (self.fecha_fin - self.fecha_inicio).days + 1
        return None


# JSON Schema que se le entrega a Gemini como response_schema.
# Es deliberadamente mas permisivo que el modelo Pydantic: el LLM garantiza
# la FORMA, Pydantic garantiza las REGLAS DE NEGOCIO. Si fueran identicos,
# nunca podriamos observar un ValidationError.
RESPONSE_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "intencion": {
            "type": "string",
            "enum": [
                "consultar_disponibilidad",
                "consultar_precio",
                "solicitar_reserva",
                "fuera_de_alcance",
            ],
        },
        "herramienta": {"type": "string", "nullable": True},
        "cantidad": {"type": "integer"},
        "fecha_inicio": {"type": "string", "nullable": True},
        "fecha_fin": {"type": "string", "nullable": True},
        "telefono_cliente": {"type": "string", "nullable": True},
        "confianza": {"type": "number"},
        "requiere_humano": {"type": "boolean"},
    },
    "required": ["intencion", "cantidad", "confianza", "requiere_humano"],
}
