# ACB Manglares San Andrés — Visores HTML

Visores de trabajo de la consultoría de Análisis Costo-Beneficio (ACB) de proyectos de Adaptación basada en Ecosistemas en manglares del Archipiélago de San Andrés, Providencia y Santa Catalina.

Web: https://louteiro.github.io/acb-manglares-sai/

## Fase 3 — Costos de intervención

- Visor: `costos-f3.html`
- Código en `f3/`: `modelo_costos_f3.py` (modelo de costos, Python estándar), `necesidades_datos.py` (matriz de datos), `build_f3.py` (genera la página a partir de `f3/out/*.csv` y la plantilla de `f3/web/`).
- Para regenerar: `python3 f3/modelo_costos_f3.py && python3 f3/necesidades_datos.py && python3 f3/build_f3.py`

## Fase 4 — Beneficio biofísico

- Visor: `beneficio-f4.html`
- Código en `f4/`: `modelo_beneficio_f4.py` (forzamiento, matriz de corridas, viento de Iota y cribado del beneficio, Python estándar), `tablas_f4.py` (necesidades de datos, hitos, batimetría, matriz de modelo, rugosidad y vegetación), `build_f4.py` (genera la página a partir de `f4/out/*.csv` y la plantilla de `f4/web/`).
- Para regenerar: `python3 f4/modelo_beneficio_f4.py && python3 f4/tablas_f4.py && python3 f4/build_f4.py`

## Fase 5 — Valoración económica

- Visor: `valoracion-f5.html` (página autocontenida de seguimiento de las actividades 5.1–5.4; el avance se guarda en el navegador y se puede exportar a JSON).
