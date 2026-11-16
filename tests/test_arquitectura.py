"""
test_arquitectura.py - Las reglas de Vertical Slice Architecture, verificadas en cada corrida.

    python -m pytest tests/test_arquitectura.py -v

Escritas en un README, estas reglas se rompen sin que nadie lo note; acá se chequean leyendo los
imports de cada archivo (con ast, sin ejecutar nada):

  1. Ningún slice importa a otro slice (ni entre features/, ni entre herramientas/, ni cruzado).
  2. shared/ no conoce a nadie: no importa slices, ni el agente, ni main.
  3. Los slices de herramientas no dependen del agente ni de la API (son capacidades sueltas).
  4. Solo main.py conoce a todos los slices HTTP.
  5. El sistema no depende de las entregas archivadas en entregas/.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[1] / "app"


def _imports(archivo: Path) -> set[str]:
    arbol = ast.parse(archivo.read_text(encoding="utf-8"))
    modulos = set()
    for nodo in ast.walk(arbol):
        if isinstance(nodo, ast.ImportFrom) and nodo.module:
            modulos.add(nodo.module)
        elif isinstance(nodo, ast.Import):
            modulos.update(a.name for a in nodo.names)
    return modulos


def _slice_de(archivo: Path) -> str | None:
    """'features/consultar' o 'herramientas/reservas' si el archivo pertenece a un slice."""
    partes = archivo.relative_to(APP).parts
    if len(partes) >= 3 and partes[0] in ("features", "herramientas"):
        return f"{partes[0]}/{partes[1]}"
    return None


def _slice_importado(modulo: str) -> str | None:
    partes = modulo.split(".")
    if len(partes) >= 3 and partes[0] == "app" and partes[1] in ("features", "herramientas"):
        return f"{partes[1]}/{partes[2]}"
    return None


ARCHIVOS = sorted(APP.rglob("*.py"))
SLICES = sorted({s for a in ARCHIVOS if (s := _slice_de(a))})


def test_hay_slices():
    assert {"features/consultar", "features/estado", "features/metricas", "features/health",
            "herramientas/conocimiento", "herramientas/disponibilidad", "herramientas/precio",
            "herramientas/reservas"} <= set(SLICES)


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: str(a.relative_to(APP)))
def test_un_slice_no_importa_a_otro_slice(archivo):
    propio = _slice_de(archivo)
    if propio is None:
        return
    ajenos = {s for m in _imports(archivo) if (s := _slice_importado(m)) and s != propio}
    assert not ajenos, f"{propio} importa a otro slice: {ajenos}"


@pytest.mark.parametrize("archivo", sorted((APP / "shared").rglob("*.py")), ids=lambda a: a.name)
def test_shared_no_conoce_a_nadie(archivo):
    prohibidos = {m for m in _imports(archivo)
                  if m.startswith(("app.features", "app.herramientas", "app.agente", "app.main"))}
    assert not prohibidos, f"shared/{archivo.name} importa {prohibidos}"


@pytest.mark.parametrize("archivo", sorted((APP / "herramientas").rglob("*.py")),
                         ids=lambda a: str(a.relative_to(APP)))
def test_herramientas_no_dependen_del_agente_ni_de_la_api(archivo):
    prohibidos = {m for m in _imports(archivo) if m.startswith(("app.agente", "app.features", "app.main", "fastapi"))}
    assert not prohibidos, f"{archivo.relative_to(APP)} importa {prohibidos}"


def test_solo_main_conoce_todos_los_slices_http():
    for archivo in ARCHIVOS:
        if archivo.name == "main.py" and archivo.parent == APP:
            continue
        if _slice_de(archivo) and _slice_de(archivo).startswith("features/"):
            continue  # cada slice se conoce a sí mismo (ya chequeado arriba que no conozca a otros)
        routers = {m for m in _imports(archivo) if m.startswith("app.features.") and m.endswith(".endpoint")}
        assert not routers, f"{archivo.relative_to(APP)} registra endpoints: {routers}"


@pytest.mark.parametrize("archivo", ARCHIVOS, ids=lambda a: str(a.relative_to(APP)))
def test_el_sistema_no_depende_de_las_entregas_archivadas(archivo):
    viejos = {"db", "schemas", "vector_db", "rag_pipeline", "pipeline_vectorial", "etl_purga", "agente", "api"}
    usados = {m for m in _imports(archivo) if m.split(".")[0] in viejos}
    assert not usados, f"{archivo.relative_to(APP)} importa código archivado: {usados}"
