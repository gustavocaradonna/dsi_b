"""
El agente ReAct (LangGraph): compone los slices de herramientas y les da memoria.

    prompt.py    reglas de negocio del agente (prompt de sistema) y mensajes fijos
    grafo.py     el grafo ReAct con límite de iteraciones
    memoria.py   checkpointer SQLite por thread_id
    servicio.py  Agente.consultar / Agente.estado: lo que usan los slices HTTP de features/
"""
