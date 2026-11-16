"""
AlquiHerramientas — agente en producción (TP Final), organizado con Vertical Slice Architecture.

    app/
    ├── main.py            composición: arma la API registrando cada slice
    ├── features/          slices HTTP: un caso de uso = una carpeta (endpoint + modelos + lógica)
    ├── herramientas/      slices del agente: una capacidad = una carpeta (tool + su acceso a datos)
    ├── agente/            el agente ReAct que compone los slices de herramientas
    └── shared/            solo lo transversal: config, LLM, SQL, logs/métricas, guardrails, HTTP

Regla de dependencias: un slice puede usar shared/ (y features/ puede usar agente/), pero ningún
slice importa a otro slice. Para cambiar una funcionalidad se toca una sola carpeta.
"""
