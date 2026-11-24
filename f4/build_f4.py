#!/usr/bin/env python3
"""
Construye beneficio-f4.html (página autónoma para GitHub Pages) a partir de:
  - los CSV que escribe modelo_beneficio_f4.py en f4/out/
  - la plantilla web (f4/web/index.html, f4-core.js, f4-charts.js, f4.css)

Uso (desde la raíz del repo):
    python3 f4/modelo_beneficio_f4.py
    python3 f4/tablas_f4.py
    python3 f4/build_f4.py
"""
import csv
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(HERE, "out")
WEB = os.path.join(HERE, "web")

DATASETS = {
    "parametros": "parametros.csv", "necesidades": "necesidades_datos.csv", "hitos": "hitos.csv",
    "batimetria": "batimetria.csv", "matriz": "matriz_modelo.csv", "rugosidad": "rugosidad.csv",
    "vegetacion": "vegetacion.csv", "anm": "anm.csv", "forzamiento": "forzamiento.csv", "corridas": "corridas.csv",
    "condicion": "condicion.csv", "beneficio": "beneficio.csv", "diferencial": "diferencial.csv", "perfil": "perfil.csv",
    "proteccion": "proteccion_actual.csv", "tornado": "tornado.csv", "mc_pct": "montecarlo.csv",
    "mc_hist": "montecarlo_hist.csv", "iota_track": "iota_track.csv", "iota_viento": "iota_viento.csv",
    "calibracion": "calibracion.csv", "resumen": "resumen.csv",
}


def read(name):
    with open(os.path.join(WEB, name), encoding="utf-8") as f:
        return f.read()


def load_data():
    data = {}
    for k, fn in DATASETS.items():
        with open(os.path.join(OUT, fn), encoding="utf-8") as f:
            data[k] = list(csv.DictReader(f))
    return data


# Equivalencias de los tokens de diseño del tablero de Claude (claro / oscuro)
TOKENS = """
:root{
  --font-anthropic-sans: Inter, system-ui, -apple-system, "Segoe UI", sans-serif;
  --font-anthropic-serif: Georgia, "Times New Roman", serif;
  --color-fg:#14231f; --color-fg-muted:#5b6b66; --color-bg:#f6f8f7; --color-panel:#ffffff; --color-border-line:#dfe6e3;
  --color-ok:#1f7a4d; --color-warn:#9a6700; --color-bad:#b3261e;
  --cds-font-size-caption:12.5px; --cds-font-size-body:14.5px; --cds-font-size-heading:18px; --cds-font-size-title:28px;
  --cds-font-weight-medium:600;
  --cds-gap-xs:4px; --cds-gap-sm:8px; --cds-gap-md:12px; --cds-gap-lg:20px; --cds-gap-xl:32px;
  --cds-pad-xs:4px; --cds-pad-sm:8px; --cds-pad-md:12px; --cds-pad-lg:18px; --cds-pad-xl:28px;
  --cds-radius:10px;
  --cds-chart-grid:#e8eeeb; --cds-chart-axis:#c9d3cf; --cds-chart-reference:#7d8c87; --cds-chart-muted:#b8c4c0;
  --cds-text-secondary:#5b6b66;
  --cds-surface-popover:#ffffff; --cds-border:#dfe6e3; --cds-shadow-popover:0 4px 14px rgba(0,0,0,.12);
  --s1:#1f6f5c; --s2:#d08a2c; --s3:#3b6ea8; --s4:#b54a4a; --s5:#7a5ea8; --s6:#4f9a8a; --s7:#8a8f3c; --s8:#c06a9a;
}
@media (prefers-color-scheme: dark){
  :root{
    --color-fg:#e6eeeb; --color-fg-muted:#9fb0aa; --color-bg:#0f1715; --color-panel:#16211e; --color-border-line:#26342f;
    --color-ok:#5cc28f; --color-warn:#e0b450; --color-bad:#f08a80;
    --cds-chart-grid:#22302b; --cds-chart-axis:#36463f; --cds-chart-reference:#8fa19a; --cds-text-secondary:#9fb0aa;
    --cds-surface-popover:#1c2a26; --cds-border:#2f3f39; --cds-shadow-popover:0 4px 14px rgba(0,0,0,.5);
    --s1:#4fb394; --s2:#e6a54d; --s3:#6f9fd6; --s4:#e07b7b; --s5:#a68ad6; --s6:#7cc4b4; --s7:#bcc26a; --s8:#e09ac2;
  }
}
*{box-sizing:border-box}
body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:var(--font-anthropic-sans);font-size:var(--cds-font-size-body);line-height:1.5}
#dash-root{max-width:1180px;margin:0 auto;padding:28px 20px 64px}
.f4-back{display:inline-block;font-size:var(--cds-font-size-caption);color:var(--color-fg-muted);text-decoration:none;margin-bottom:var(--cds-gap-md)}
.f4-back:hover{color:var(--color-fg)}
.dash-select{font:inherit;font-size:var(--cds-font-size-caption);color:var(--color-fg);background-color:var(--color-panel);border:1px solid var(--color-border-line);border-radius:8px;padding:6px 10px}
[hidden]{display:none!important}
.f4-foot{margin-top:var(--cds-gap-xl);font-size:var(--cds-font-size-caption);color:var(--color-fg-muted)}
"""

# Sustituto mínimo del entorno del tablero (dash.data, dash.calc, dash.draw...)
SHIM = r"""
(function(){
  const RAW = window.__F4_DATA__;
  const calcs = {}, cache = {}, draws = {};
  const dash = window.dash = {
    colors: ['var(--s1)','var(--s2)','var(--s3)','var(--s4)','var(--s5)','var(--s6)','var(--s7)','var(--s8)'],
    data(id){
      if (RAW[id]) return {status:'ok', data:RAW[id], columns:Object.keys(RAW[id][0]||{})};
      if (calcs[id]){
        if (!(id in cache)) cache[id] = calcs[id].fn.apply(null, calcs[id].inputs.map((i)=>dash.data(i).data));
        return {status:'ok', data:cache[id]};
      }
      return {status:'missing', data:[]};
    },
    calc(id, spec){ calcs[id] = spec; },
    loader(){},
    onData(fn){ fn(); },
    draw(name, fn){
      if (fn) { draws[name] = fn; return; }
      run(name);
    },
    setLink(id){ try { history.replaceState(null, '', '#' + id); } catch(e){} runAll(); },
    params(){ return {}; }, setParams(){}, resetParams(){}, refresh(){},
  };
  function visible(el){ return !el.closest('[hidden]'); }
  function run(name){
    const fn = draws[name]; if (!fn) return;
    document.querySelectorAll('[data-draw="'+name+'"]').forEach((el)=>{ if (visible(el)) { try { fn(el); } catch(e){ console.error(name, e); } } });
  }
  function runAll(){ Object.keys(draws).forEach(run); }
  window.__F4_RUN__ = runAll;
  let t; window.addEventListener('resize', ()=>{ clearTimeout(t); t = setTimeout(runAll, 150); });
})();
"""


def main():
    html = read("index.html")
    css = read("f4.css")
    core = read("f4-core.js")
    charts = read("f4-charts.js")
    data = load_data()

    html = html.replace('<meta name="dash-one-writer">\n', "")
    html = html.replace('<link rel="stylesheet" href="f4.css">\n', "")
    html = re.sub(r'<script src="f4-(core|charts)\.js"></script>\n?', "", html)
    old = "ejecuta los dos scripts y sustituye los CSV en Fuentes."
    assert old in html
    html = html.replace(old, "ejecuta <code>python3 f4/modelo_beneficio_f4.py</code>, <code>python3 f4/tablas_f4.py</code> y "
                        "<code>python3 f4/build_f4.py</code> para regenerar esta página. El código y los CSV están en la carpeta "
                        "<code>f4/</code> del repositorio.")
    html = html.replace('<header id="cabecera">',
                        '<header id="cabecera">\n    <a class="f4-back" href="index.html">← Visores del proyecto</a>')

    data_js = "window.__F4_DATA__ = " + json.dumps(data, ensure_ascii=False, separators=(",", ":")) + ";"

    page = f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>F4 — Beneficio biofísico · ACB Manglares San Andrés</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap">
<style>{TOKENS}
{css}</style>
<script src="https://cdn.jsdelivr.net/npm/d3@7"></script>
</head>
<body>
<div id="dash-root">
{html}
<p class="f4-foot">Modelo de cribado generado con <code>f4/modelo_beneficio_f4.py</code> (estados de los datos a 22 nov 2026). Luis Rodríguez Outeiro · 2026</p>
</div>
<script>{data_js}</script>
<script>{SHIM}</script>
<script>{core}</script>
<script>{charts}</script>
<script>window.__F4_RUN__();</script>
</body>
</html>
"""
    dest = os.path.join(ROOT, "beneficio-f4.html")
    with open(dest, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Escrito {dest} ({len(page)/1024:.0f} KB)")


if __name__ == "__main__":
    main()
