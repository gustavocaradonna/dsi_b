"""Fábrica del modelo de lenguaje. La usan el agente y el juez de relevancia del slice de conocimiento."""

from __future__ import annotations

from app.shared import config


def crear_llm():
    from langchain_google_genai import ChatGoogleGenerativeAI

    config.verificar_api_key()
    return ChatGoogleGenerativeAI(
        model=config.GEMINI_MODEL,
        temperature=config.GEMINI_TEMPERATURE,
        max_retries=6,  # el free tier devuelve 429/503 con ráfagas; reintenta con backoff
    )
