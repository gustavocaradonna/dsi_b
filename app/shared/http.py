"""
Infraestructura HTTP transversal: respuestas con charset, normalización del cuerpo y manejadores de
error. La registra main.py; ningún slice la necesita importar.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.shared.observabilidad import log_evento

MAX_BYTES_CUERPO = 64 * 1024


class JSONUTF8(JSONResponse):
    """Declara el charset: PowerShell 5.1 (Invoke-RestMethod) asume Latin-1 si falta y muestra
    "Â¡Hola! SÃ­" en vez de "¡Hola! Sí" (lo detectó la prueba de instalación limpia)."""

    media_type = "application/json; charset=utf-8"


class NormalizarCuerpo:
    """Middleware ASGI para los POST:
    - corta cuerpos de más de 64 KB con 413 antes de leerlos enteros (el guardrail de longitud del
      mensaje viene después; esto protege al servidor, no al LLM);
    - si el cuerpo no es UTF-8 válido, lo reinterpreta como cp1252. Es lo que manda curl en Windows
      con tildes o con "¿" (lo detectó la prueba de instalación limpia)."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http" or scope["method"] != "POST":
            return await self.app(scope, receive, send)
        cuerpo, mas = b"", True
        while mas:
            mensaje = await receive()
            cuerpo += mensaje.get("body", b"")
            mas = mensaje.get("more_body", False)
            if len(cuerpo) > MAX_BYTES_CUERPO:
                log_evento("cuerpo_rechazado", logging.WARNING, motivo="cuerpo_demasiado_grande", bytes=len(cuerpo))
                await send({"type": "http.response.start", "status": 413,
                            "headers": [(b"content-type", b"application/json; charset=utf-8")]})
                await send({"type": "http.response.body",
                            "body": b'{"detail": {"motivo": "cuerpo_demasiado_grande"}}'})
                return
        try:
            cuerpo.decode("utf-8")
        except UnicodeDecodeError:
            cuerpo = cuerpo.decode("cp1252", errors="replace").encode("utf-8")
            log_evento("cuerpo_recodificado", origen="cp1252")
        entregado = False

        async def receive_normalizado():
            nonlocal entregado
            if not entregado:
                entregado = True
                return {"type": "http.request", "body": cuerpo, "more_body": False}
            return await receive()

        await self.app(scope, receive_normalizado, send)


def registrar(app: FastAPI) -> None:
    app.add_middleware(NormalizarCuerpo)

    @app.exception_handler(HTTPException)
    async def error_http(request, exc: HTTPException) -> JSONUTF8:
        return JSONUTF8({"detail": exc.detail}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def error_validacion(request, exc: RequestValidationError) -> JSONUTF8:
        return JSONUTF8({"detail": jsonable_encoder(exc.errors())}, status_code=422)
