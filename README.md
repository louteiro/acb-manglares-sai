# ACB Manglares San Andrés — Visores HTML

Visores de trabajo de la consultoría de Análisis Costo-Beneficio (ACB) de proyectos de Adaptación basada en Ecosistemas en manglares del Archipiélago de San Andrés, Providencia y Santa Catalina.

Web: https://louteiro.github.io/acb-manglares-sai/

## Fase 3 — Costos de intervención

- Visor: `costos-f3.html`
- Código en `f3/`: `modelo_costos_f3.py` (modelo de costos, Python estándar), `necesidades_datos.py` (matriz de datos), `build_f3.py` (genera la página a partir de `f3/out/*.csv` y la plantilla de `f3/web/`).
- Para regenerar: `python3 f3/modelo_costos_f3.py && python3 f3/necesidades_datos.py && python3 f3/build_f3.py`
