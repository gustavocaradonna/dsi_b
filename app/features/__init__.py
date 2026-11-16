"""
Slices HTTP: un caso de uso = una carpeta, con su endpoint, sus modelos y su lógica.

    consultar/   POST /consultar          guardrails -> agente -> enmascarado -> métricas
    estado/      GET  /estado/{thread_id} historial desde la memoria, enmascarado
    metricas/    GET  /metricas           métricas del proceso
    health/      GET  /health             estado del servicio
"""
