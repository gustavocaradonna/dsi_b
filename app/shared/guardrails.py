"""
guardrails.py - Validadores de entrada y salida del agente (TP Final, Parte D).

Entrada (antes de gastar un token de LLM):
    validar_longitud           mensaje vacio o de mas de MAX_CARACTERES -> bloqueo
    validar_prompt_injection   intentos de pisar las instrucciones del sistema -> bloqueo

Salida (antes de devolver la respuesta al cliente):
    enmascarar_datos_personales  DNI, telefono, email y tarjeta -> [DNI], [TELEFONO], ...

Son deterministas (regex, sin LLM) a proposito: son la primera linea de defensa, tienen que ser
baratos, rapidos y testeables con asserts exactos (security_tests.py). El guardrail semantico ya
esta en el prompt del agente (responder solo con lo que devuelven las herramientas).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

MAX_CARACTERES = 1000


@dataclass
class ResultadoValidacion:
    permitido: bool
    motivo: str | None = None  # codigo estable, se usa en /metricas y en los logs
    detalle: str | None = None  # texto para el cliente
    tactica: str | None = None  # que regla salto: va al log, nunca al cliente


def _normalizar(texto: str) -> str:
    """Minusculas y sin tildes: 'Ignorá' y 'ignora' tienen que caer en la misma regla."""
    sin_tildes = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in sin_tildes if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", sin_tildes.lower())


# --------------------------------------------------------------------------
# Entrada 1 - longitud
# --------------------------------------------------------------------------


def validar_longitud(mensaje: str, maximo: int = MAX_CARACTERES) -> ResultadoValidacion:
    """Un mensaje vacio no tiene nada que responder; uno enorme es casi siempre un pegado
    accidental o un intento de inundar el contexto (y cada caracter se paga en tokens)."""
    if not mensaje or not mensaje.strip():
        return ResultadoValidacion(False, "mensaje_vacio", "El mensaje está vacío.")
    if len(mensaje) > maximo:
        return ResultadoValidacion(
            False,
            "mensaje_demasiado_largo",
            f"El mensaje tiene {len(mensaje)} caracteres; el máximo es {maximo}. "
            "Probá escribir la consulta más corta.",
        )
    return ResultadoValidacion(True)


# --------------------------------------------------------------------------
# Entrada 2 - prompt injection
# --------------------------------------------------------------------------

# Patrones sobre el texto normalizado (sin tildes, minusculas). Cada uno apunta a una tactica
# conocida, no a palabras sueltas: "instrucciones" solo no bloquea ("¿qué instrucciones de uso
# trae la amoladora?" es una consulta legitima).
PATRONES_INJECTION: list[tuple[str, str]] = [
    (r"\b(ignora|ignore|olvida|olvidate de|descarta|saltea|omiti|forget|disregard)\b.{0,40}"
     r"\b(instrucciones|reglas|indicaciones|prompt|instructions|rules|directivas)\b", "pisar_instrucciones"),
    (r"\b(system prompt|prompt del sistema|mensaje del sistema|tus instrucciones (internas|originales|de sistema))\b",
     "extraer_prompt"),
    (r"\b(revela|mostra|mostrame|decime|dame|imprimi|repeti|reveal|print|show)\b.{0,30}"
     r"\b(tu|tus|el|las)\b.{0,15}\b(prompt|instrucciones|reglas internas|configuracion)\b", "extraer_prompt"),
    (r"\b(ahora sos|a partir de ahora sos|actua como|actuar como|hace de cuenta que sos|you are now|act as|pretend to be)\b",
     "cambio_de_rol"),
    (r"\b(modo desarrollador|developer mode|jailbreak|dan mode|modo dan|sin restricciones|without restrictions)\b",
     "jailbreak"),
    (r"<\s*/?\s*(system|assistant|instrucciones)\s*>|\[\s*(system|inst)\s*\]|###\s*(system|instruction)", "etiquetas_de_rol"),
]
_REGEX_INJECTION = [(re.compile(p), motivo) for p, motivo in PATRONES_INJECTION]


def validar_prompt_injection(mensaje: str) -> ResultadoValidacion:
    texto = _normalizar(mensaje)
    for regex, tactica in _REGEX_INJECTION:
        if regex.search(texto):
            return ResultadoValidacion(
                False,
                "prompt_injection",
                "No puedo procesar ese mensaje. Si tenés una consulta sobre alquiler de herramientas, "
                "escribila de nuevo y te ayudo.",
                tactica,
            )
    return ResultadoValidacion(True)


VALIDADORES_ENTRADA = (validar_longitud, validar_prompt_injection)


def validar_entrada(mensaje: str) -> ResultadoValidacion:
    """Corre los validadores en orden; el primero que bloquea gana (longitud antes que regex:
    no tiene sentido correr expresiones regulares sobre 50.000 caracteres)."""
    for validador in VALIDADORES_ENTRADA:
        resultado = validador(mensaje)
        if not resultado.permitido:
            return resultado
    return ResultadoValidacion(True)


# --------------------------------------------------------------------------
# Salida - enmascarado de datos personales
# --------------------------------------------------------------------------

_EMAIL = re.compile(r"\b[\w.+-]+@[\w-]+(\.[\w-]+)+\b")
# DNI argentino: 7 u 8 digitos, con o sin puntos (12.345.678 / 12345678). Con \b para no morder
# numeros mas largos (esos los evalua el patron de telefono o de tarjeta).
# Los bordes aceptan un punto final de oracion ("...mi DNI 30123456.") pero no un punto seguido de
# digito, que es parte del numero (30.123.456). Sin esto, el punto final hacia retroceder la regex
# y el dato quedaba sin enmascarar (lo encontro security_tests.py).
_DNI = re.compile(r"(?<!\d)(?<!\d\.)(\d{1,2}\.\d{3}\.\d{3}|\d{7,8})(?!\d)(?!\.\d)")
# Candidatos a telefono o tarjeta: secuencias de digitos con espacios, guiones o + en el medio.
_SECUENCIA_NUMERICA = re.compile(r"(?<![\w.])\+?\d[\d \-]{8,}\d(?!\w)(?!\.\d)")
_FECHA = re.compile(r"^\d{4}-\d{2}-\d{2}$|^\d{2}-\d{2}-\d{4}$")


@dataclass
class ResultadoEnmascarado:
    texto: str
    reemplazos: dict[str, int] = field(default_factory=dict)

    @property
    def enmascarado(self) -> bool:
        return bool(self.reemplazos)


def _luhn_valido(digitos: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digitos)):
        n = int(d)
        if i % 2 == 1:
            n = n * 2 - 9 if n > 4 else n * 2
        total += n
    return total % 10 == 0


def enmascarar_datos_personales(texto: str) -> ResultadoEnmascarado:
    """Reemplaza datos personales por etiquetas. Pensado para la salida: el agente puede haber
    recibido el telefono del cliente para crear una reserva, pero la respuesta (y lo que queda en
    logs y en la memoria visible por /estado) no tiene por que repetirlo."""
    reemplazos: dict[str, int] = {}

    def contar(etiqueta: str) -> str:
        reemplazos[etiqueta] = reemplazos.get(etiqueta, 0) + 1
        return f"[{etiqueta}]"

    texto = _EMAIL.sub(lambda m: contar("EMAIL"), texto)

    def clasificar_secuencia(m: re.Match) -> str:
        candidato = m.group(0)
        if _FECHA.match(candidato.strip()):
            return candidato  # 2026-11-20 no es un telefono
        digitos = re.sub(r"\D", "", candidato)
        if 13 <= len(digitos) <= 19 and _luhn_valido(digitos):
            return contar("TARJETA")
        if 10 <= len(digitos) <= 15:
            return contar("TELEFONO")
        return candidato

    texto = _SECUENCIA_NUMERICA.sub(clasificar_secuencia, texto)
    texto = _DNI.sub(lambda m: contar("DNI"), texto)
    return ResultadoEnmascarado(texto, reemplazos)
