#!/usr/bin/env python3
"""
Fase 4 — Modelado del beneficio biofísico (ACB Manglares San Andrés)
=====================================================================
Modelo de CRIBADO en Python estándar (sin dependencias) que acompaña al
modelo hidrodinámico de la F4 mientras no exista la topobatimetría (HB.1).
No sustituye a ADCIRC+SWAN / XBeach: sirve para

  1. ordenar las necesidades de datos de cada actividad (4.1–4.7);
  2. fijar el forzamiento común (ANM + niveles por Tr) y la matriz de corridas;
  3. comprobar el campo de viento paramétrico (Holland, 1980) con Iota (2020)
     antes de montar el modelo (actividad 4.4);
  4. estimar el orden de magnitud del diferencial Base–Intervención en
     altura de ola y nivel de inundación por ACI, Tr y corte (actividad 4.6),
     con su sensibilidad, para detectar qué parámetros conviene medir primero.

Estados de cada parámetro (igual que en modelo_costos_f3.py):
  - "Oficial"   : dato primario/institucional verificado
  - "Proyecto"  : decidido en el Plan de Trabajo (E1) o en otra fase
  - "Proxy"     : valor de literatura científica para un caso comparable
  - "Supuesto"  : valor provisional del consultor, a reemplazar
  - "Verificar" : valor conocido que hay que confirmar en la fuente

Uso:
    python3 modelo_beneficio_f4.py               # escribe los CSV en ./out
    python3 modelo_beneficio_f4.py --mc 20000    # cambia las iteraciones Monte Carlo

Cuando lleguen los niveles extremos (COAST-RP / Rey et al.), las parcelas de
estructura del manglar y las ACI aprobadas (H2.3), edita PARAMS y ACIS y vuelve
a ejecutar.
"""
from __future__ import annotations

import argparse
import copy
import csv
import math
import os
import random

# ---------------------------------------------------------------------------
# 1. PARÁMETROS
# ---------------------------------------------------------------------------
PARAMS: dict[str, dict] = {}


def P(key, valor, unidad, grupo, etiqueta, estado, fuente, url="", lo=None, hi=None):
    PARAMS[key] = dict(valor=valor, unidad=unidad, grupo=grupo, etiqueta=etiqueta,
                       estado=estado, fuente=fuente, url=url, lo=lo, hi=hi)


URL_KELTY = "https://doi.org/10.3389/fmars.2021.780946"
URL_LOPEZ = "https://doi.org/10.3389/fmars.2024.1383368"
URL_ZHANG = "https://doi.org/10.1016/j.ecss.2012.02.021"
URL_NHC = "https://www.nhc.noaa.gov/data/tcr/AL312020_Iota.pdf"
URL_COASTRP = "https://data.4tu.nl/datasets/4e291b8f-a37e-4378-8ca6-954a44fdc8fb"

# --- Forzamiento: nivel del mar extremo en el frente del manglar ------------
for tr, val in [(10, 0.6), (25, 0.9), (50, 1.2), (100, 1.5)]:
    P(f"eta_{tr}", val, "m s.n.m.m.", "Forzamiento", f"Nivel extremo (marea + marea de tormenta + setup), Tr {tr}",
      "Supuesto", "Marcador provisional hasta COAST-RP / niveles 10–100 de Rey y Ruiz-Salcines (solicitados); "
      "Velásquez-Calderón et al. (2026): ninguna zona > 2 m de lámina a 100 años", URL_COASTRP,
      lo=round(val * 0.6, 2), hi=round(val * 1.4, 2))
for t, cm in [(10, 8), (20, 17), (30, 26), (50, 45), (100, 97)]:
    P(f"anm_{t}", cm / 100, "m", "Forzamiento", f"ANM t = {t} (SSP2-4.5 mediana + GNSS SAN0)", "Proyecto",
      "E1 Plan de Trabajo, sección 5.2 (ficha de antecedentes ANM)")
P("gamma", 0.5, "H/h", "Forzamiento", "Índice de rotura en fondo somero (ola limitada por profundidad)", "Proxy",
  "Rango habitual 0,4–0,6 en planicies someras; calibrar con XBeach", lo=0.4, hi=0.6)
P("z_suelo", 0.3, "m s.n.m.m.", "Forzamiento", "Cota del suelo del manglar en el frente de la ACI", "Supuesto",
  "Corregir con ICESat-2 ATL08 (terreno bajo el dosel), cotas de parcelas y piezómetros y zonación–marea (E1, actividad 4.1)", lo=0.1, hi=0.5)
P("sigma_z", 0.5, "m", "Forzamiento", "Error vertical de la topobatimetría (±σ, corridas de Tr 100)", "Supuesto",
  "Se sustituye por el σ de la validación B.4 (hito HB.1)", lo=0.25, hi=1.0)

# --- Vegetación -------------------------------------------------------------
P("beta_ref", 0.010, "1/m", "Vegetación", "Coeficiente de decaimiento de ola en Rhizophora sana (H/H₀ = 1/(1+βx))", "Proxy",
  "Kelty et al. (2022): 0,004–0,010 m⁻¹ baja densidad y 0,008–0,021 m⁻¹ alta densidad; "
  "Lopez-Arias et al. (2024), campo R. mangle: 0,001–0,01 m⁻¹", URL_KELTY, lo=0.004, hi=0.021)
P("h_raiz", 1.5, "m", "Vegetación", "Altura de la zona de raíces fúlcreas", "Supuesto",
  "Ohira et al. (2013) la relaciona con el DAP; medir en parcelas MangRes/INVEMAR", lo=1.0, hi=2.0)
P("phi_tronco", 0.25, "fracción", "Vegetación", "Eficacia relativa de la columna sobre las raíces (troncos)", "Supuesto",
  "Maza et al. (2019): la atenuación depende del área frontal, que cae con la profundidad", lo=0.10, hi=0.40)
P("s_mangle", 35, "cm/km", "Vegetación", "Atenuación de la marea de tormenta en manglar sano", "Proxy",
  "Zhang et al. (2012): 20–50 cm/km (Wilma); Krauss et al. (2009): 4,2–9,4 cm/km", URL_ZHANG, lo=9.4, hi=50)
P("s_desnudo", 8, "cm/km", "Vegetación", "Atenuación sin manglar (terreno abierto)", "Proxy",
  "Zhang et al. (2012): 6–10 cm/km sin manglar", URL_ZHANG, lo=6, hi=10)

# --- Escenarios (acoplados con la F3) --------------------------------------
P("c0", 0.20, "fracción", "Escenarios", "Condición inicial del manglar en la ACI", "Proyecto",
  "Mismo valor que modelo_costos_f3.py (curva de recuperación)")
P("cmax", 0.95, "fracción", "Escenarios", "Condición máxima alcanzable (Intervención)", "Proyecto",
  "modelo_costos_f3.py; Su et al. (2021)")
P("t50_est", 14, "años", "Escenarios", "Punto medio de la curva de estructura arbórea", "Proyecto",
  "modelo_costos_f3.py; Osland et al. (2020)", lo=10, hi=20)
P("k_est", 0.22, "1/año", "Escenarios", "Pendiente de la curva de estructura arbórea", "Proyecto",
  "modelo_costos_f3.py", lo=0.15, hi=0.30)
P("perdida_base", 0.01, "1/año", "Escenarios", "Tasa de pérdida crónica del Escenario Base", "Proyecto",
  "E1 sección 11.6: ≤ 1 %/año hasta tener la serie propia (actividad 1.3)", lo=0.005, hi=0.02)

# --- Viento paramétrico (Iota) ---------------------------------------------
P("pn", 1010, "hPa", "Viento Iota", "Presión ambiental", "Supuesto", "Valor típico del Caribe en noviembre", lo=1008, hi=1012)
P("rmw", 8 * 1.852, "km", "Viento Iota", "Radio de vientos máximos (8 n mi)", "Oficial",
  "NHC TCR Iota: RMW ≈ 8 n mi en el pico", URL_NHC, lo=8 * 1.852, hi=15 * 1.852)
P("k_sup", 0.90, "×", "Viento Iota", "Reducción de viento de gradiente a superficie (1 min)", "Supuesto",
  "Valor habitual sobre el mar; calibrar", lo=0.80, hi=0.95)
P("f_10min", 0.93, "×", "Viento Iota", "Conversión 1 min → 10 min en mar abierto", "Proxy",
  "Harper et al. (2010), guía OMM de conversión de promedios de viento", lo=0.88, hi=0.95)
P("alfa_tras", 0.5, "×", "Viento Iota", "Fracción de la velocidad de traslación sumada al viento", "Supuesto",
  "Asimetría simple; el lado sur (izquierdo) de un ciclón que va al oeste recibe menos viento", lo=0.0, hi=0.7)
P("rho_aire", 1.15, "kg/m³", "Viento Iota", "Densidad del aire", "Supuesto", "Valor estándar tropical")

# ---------------------------------------------------------------------------
# 2. ACI candidatas pre-taller (sitios con parcelas INVEMAR; anchos de franja supuestos)
# ---------------------------------------------------------------------------
ACIS = [
    dict(aci="Old Point / Bahía Hooker", ancho_m=250),
    dict(aci="Cove Sea Side", ancho_m=200),
    dict(aci="Smith Channel", ancho_m=150),
]
TRS = [10, 25, 50, 100]
CORTES = [10, 20, 30, 50, 100]  # 50 y 100: cobertura de t = 30 congelada (E1, actividad 4.5)

LUGARES = {
    "San Andrés (aeropuerto)": (12.583, -81.711),
    "Providencia": (13.350, -81.370),
}

# Best track de Iota (NHC TCR, tabla 1) — fecha (día, hora UTC), lat, lon, hPa, kt
IOTA = [
    (15, 12, 13.1, -78.0, 982, 70), (15, 18, 13.2, -78.9, 974, 75),
    (16, 0, 13.2, -79.8, 961, 90), (16, 6, 13.4, -80.7, 935, 120),
    (16, 12, 13.5, -81.5, 917, 135), (16, 18, 13.5, -82.3, 918, 130),
    (17, 0, 13.6, -83.0, 918, 130), (17, 6, 13.7, -83.8, 935, 110),
]
KT = 0.514444


def v(p, k):
    return p[k]["valor"]


# ---------------------------------------------------------------------------
# 3. MODELOS
# ---------------------------------------------------------------------------
def logistica(t, c0, cmax, t50, k):
    return c0 + (cmax - c0) / (1 + math.exp(-k * (t - t50)))


def condicion(p, t, esc):
    if esc == "Sin manglar":
        return 0.0
    if esc == "Actual":
        return v(p, "c0")
    t = min(t, 30)  # de t = 30 a 50/100 se mantiene la cobertura de t = 30
    if esc == "Base":
        return v(p, "c0") * math.exp(-v(p, "perdida_base") * t)
    # se resta el valor en t=0 para que ambos escenarios partan de c0
    l0 = logistica(0, v(p, "c0"), v(p, "cmax"), v(p, "t50_est"), v(p, "k_est"))
    lt = logistica(t, v(p, "c0"), v(p, "cmax"), v(p, "t50_est"), v(p, "k_est"))
    return min(v(p, "cmax"), v(p, "c0") + (lt - l0) * (v(p, "cmax") - v(p, "c0")) / (v(p, "cmax") - l0))


def f_prof(p, h):
    """Fracción de eficacia del área frontal según la lámina de agua."""
    hr = v(p, "h_raiz")
    if h <= hr:
        return 1.0
    return (hr + v(p, "phi_tronco") * (h - hr)) / h


def ola(p, aci, tr, t, esc, dz=0.0):
    """Altura de ola al fondo de la franja (Mendez y Losada, 2004, forma hiperbólica)."""
    anm = 0.0 if t == 0 else v(p, f"anm_{t}")
    h = max(0.05, v(p, f"eta_{tr}") + anm - v(p, "z_suelo") + dz)
    H0 = v(p, "gamma") * h
    c = condicion(p, t, esc)
    beta = v(p, "beta_ref") * c * f_prof(p, h)
    W = aci["ancho_m"]
    Hb = H0 / (1 + beta * W)
    deta = (v(p, "s_mangle") * c + v(p, "s_desnudo") * (1 - c)) * W / 1000  # cm
    return dict(h=h, H0=H0, cond=c, beta=beta, Hb=Hb, deta=deta)


def diferencial(p, aci, tr, t):
    b, i = ola(p, aci, tr, t, "Base"), ola(p, aci, tr, t, "Intervención")
    return (b["Hb"] - i["Hb"]) * 100, i["deta"] - b["deta"]


def metrica(p):
    """Diferencial medio de altura de ola (cm) en Tr 100, t = 30, 3 ACI."""
    return sum(diferencial(p, a, 100, 30)[0] for a in ACIS) / len(ACIS)


# --- viento de Holland (1980) ------------------------------------------------
def hav(lat1, lon1, lat2, lon2):
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return math.degrees(math.atan2(y, x)) % 360


def track_hourly():
    pts = []
    for (d0, h0, la0, lo0, p0, w0), (d1, h1, la1, lo1, p1, w1) in zip(IOTA[:-1], IOTA[1:]):
        t0 = (d0 - 16) * 24 + h0
        t1 = (d1 - 16) * 24 + h1
        for k in range(t1 - t0):
            f = k / (t1 - t0)
            pts.append((t0 + k, la0 + f * (la1 - la0), lo0 + f * (lo1 - lo0), p0 + f * (p1 - p0), w0 + f * (w1 - w0)))
    d, h, la, lo, pc, w = IOTA[-1]
    pts.append(((d - 16) * 24 + h, la, lo, pc, w))
    return pts


def holland(p, r_km, pc, vmax_kt, lat):
    dp = (v(p, "pn") - pc) * 100
    vg = vmax_kt * KT / v(p, "k_sup")
    B = min(2.5, max(1.0, v(p, "rho_aire") * math.e * vg ** 2 / dp))
    R = v(p, "rmw")
    x = (R / max(r_km, 0.1)) ** B
    f = 2 * 7.292e-5 * math.sin(math.radians(lat))
    r = r_km * 1000
    vgr = math.sqrt(B * dp / v(p, "rho_aire") * x * math.exp(-x) + (r * f / 2) ** 2) - r * f / 2
    return vgr * v(p, "k_sup"), B  # m/s, 1 min en superficie (simétrico)


def viento_iota(p):
    pts = track_hourly()
    rows = []
    for i, (t, la, lo, pc, w) in enumerate(pts):
        j0, j1 = max(0, i - 1), min(len(pts) - 1, i + 1)
        dist = hav(pts[j0][1], pts[j0][2], pts[j1][1], pts[j1][2])
        vt = dist * 1000 / ((pts[j1][0] - pts[j0][0]) * 3600)
        rumbo = bearing(pts[j0][1], pts[j0][2], pts[j1][1], pts[j1][2])
        row = dict(hora=t, lat=la, lon=lo, pc=pc, vmax=w, vt=vt)
        for nombre, (pla, plo) in LUGARES.items():
            r = hav(la, lo, pla, plo)
            vs, B = holland(p, r, pc, w, la)
            # ángulo entre el rumbo del ciclón y la dirección del viento ciclónico en el punto
            az = bearing(la, lo, pla, plo)
            ang = math.radians((az + 90) - rumbo)  # viento tangencial antihorario (HN)
            v1 = max(0.0, vs + v(p, "alfa_tras") * vt * math.cos(ang))
            row[nombre] = (r, v1 / KT, v1 * v(p, "f_10min") / KT, B)
        rows.append(row)
    return rows


# ---------------------------------------------------------------------------
# 4. SALIDAS
# ---------------------------------------------------------------------------
def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def hora_txt(h):
    d = 16 + h // 24
    return f"{int(d)} nov {int(h % 24):02d}:00 UTC"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "out"))
    ap.add_argument("--mc", type=int, default=10_000)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    p = PARAMS
    O = lambda n: os.path.join(args.out, n)

    # 4.1 parámetros
    write_csv(O("parametros.csv"),
              ["id", "grupo", "parametro", "valor", "unidad", "rango_bajo", "rango_alto", "estado", "fuente", "url"],
              [[k, d["grupo"], d["etiqueta"], round(d["valor"], 4), d["unidad"],
                "" if d["lo"] is None else round(d["lo"], 4), "" if d["hi"] is None else round(d["hi"], 4),
                d["estado"], d["fuente"], d["url"]] for k, d in p.items()])

    # 4.2 forzamiento: nivel de corrida por Tr y horizonte de ANM
    forz = []
    for tr in TRS:
        row = [tr, round(v(p, f"eta_{tr}"), 2)]
        for t in (10, 20, 30, 50, 100):
            row.append(round(v(p, f"eta_{tr}") + v(p, f"anm_{t}"), 2))
        forz.append(row)
    write_csv(O("forzamiento.csv"), ["tr", "nivel_t0_m", "nivel_t10_m", "nivel_t20_m", "nivel_t30_m", "nivel_t50_m", "nivel_t100_m"], forz)
    write_csv(O("anm.csv"), ["t", "anio", "anm_central_cm", "anm_estres_cm"],
              [[0, 2026, 0, 0], [10, 2036, 8, 10], [20, 2046, 17, 22], [30, 2056, 26, 38], [50, 2076, 45, ""], [100, 2126, 97, ""]])

    # 4.3 matriz de corridas (actividad 4.5 del E1, versión 19 nov 2026)
    corr = []
    nonlocal_n = [0]

    def add(a, tr, esc, hz, nivel, lulc, tipo):
        nonlocal_n[0] += 1
        corr.append([f"R{nonlocal_n[0]:02d}", a["aci"], tr, esc, f"t={hz}", round(nivel, 2), lulc, tipo, "Pendiente (tras H4.1)"])
    for a in ACIS:
        for tr in TRS:  # t = 0: papel protector del manglar actual
            for esc, lulc in (("Actual", "LULC actual"), ("Sin manglar", "Mismo dominio sin manglar")):
                add(a, tr, esc, 0, v(p, f"eta_{tr}"), lulc, "Papel protector actual")
        for tr in TRS:  # t = 30: beneficio de la intervención
            for esc in ("Base", "Intervención"):
                add(a, tr, esc, 30, v(p, f"eta_{tr}") + v(p, "anm_30"), f"{esc} t=30", "Beneficio de la intervención")
        for esc in ("Base", "Intervención"):  # estrés de la extrapolación
            add(a, 100, esc, 100, v(p, "eta_100") + v(p, "anm_100"), f"{esc} t=30 (cobertura congelada)", "Estrés t = 100")
        for esc in ("Base", "Intervención"):
            for sg in ("+σ", "−σ"):
                add(a, 100, esc, 30, v(p, "eta_100") + v(p, "anm_30"), f"{esc} t=30", f"Batimetría {sg}")
    write_csv(O("corridas.csv"), ["id", "aci", "tr", "escenario", "anm", "nivel_m", "lulc", "tipo", "estado"], corr)

    # papel protector del manglar actual (t = 0): sin manglar − actual
    prot = []
    for a in ACIS:
        for tr in TRS:
            s0, c0_ = ola(p, a, tr, 0, "Sin manglar"), ola(p, a, tr, 0, "Actual")
            prot.append([f"{a['aci']}|{tr}", a["aci"], tr, round((s0["Hb"] - c0_["Hb"]) * 100, 1), round(c0_["deta"] - s0["deta"], 1)])
    write_csv(O("proteccion_actual.csv"), ["clave", "aci", "tr", "prot_ola_cm", "prot_nivel_cm"], prot)

    # 4.4 condición del manglar
    write_csv(O("condicion.csv"), ["anio", "base", "intervencion"],
              [[t, round(condicion(p, t, "Base"), 4), round(condicion(p, t, "Intervención"), 4)] for t in range(0, 51)])

    # 4.5 beneficio por ACI, Tr, corte y escenario
    ben, dif = [], []
    for a in ACIS:
        for tr in TRS:
            for t in CORTES:
                for esc in ("Base", "Intervención"):
                    o = ola(p, a, tr, t, esc)
                    ben.append([f"{a['aci']}|{tr}|{t}|{esc}", a["aci"], tr, t, esc, round(o["cond"], 3), round(o["h"], 2),
                                round(o["H0"], 2), round(o["beta"], 5), round(o["Hb"], 3),
                                round(100 * (1 - o["Hb"] / o["H0"]), 1), round(o["deta"], 1)])
                dH, de = diferencial(p, a, tr, t)
                b = ola(p, a, tr, t, "Base")
                dif.append([f"{a['aci']}|{tr}|{t}", a["aci"], tr, t, round(dH, 1), round(100 * dH / 100 / b["H0"], 1), round(de, 1)])
    write_csv(O("beneficio.csv"), ["clave", "aci", "tr", "corte", "escenario", "condicion", "lamina_m", "H0_m", "beta_1m",
                                   "H_fondo_m", "reduccion_ola_pct", "atenuacion_nivel_cm"], ben)
    write_csv(O("diferencial.csv"), ["clave", "aci", "tr", "corte", "dif_ola_cm", "dif_ola_pct_H0", "dif_nivel_cm"], dif)

    # 4.6 perfiles H(x) en Tr 10 y Tr 100, t = 30
    perf = []
    for a in ACIS:
        for tr in (10, 100):
            for esc in ("Base", "Intervención"):
                o = ola(p, a, tr, 30, esc)
                for x in range(0, a["ancho_m"] + 1, 5):
                    perf.append([a["aci"], tr, esc, x, round(o["H0"] / (1 + o["beta"] * x), 3)])
    write_csv(O("perfil.csv"), ["aci", "tr", "escenario", "x_m", "H_m"], perf)

    # 4.7 sensibilidad: tornado y Monte Carlo sobre el diferencial medio de ola (Tr 100, t = 30)
    base = metrica(p)
    torn = []
    for k, d in p.items():
        if d["lo"] is None or d["grupo"] == "Viento Iota":
            continue
        lo_p, hi_p = copy.deepcopy(p), copy.deepcopy(p)
        lo_p[k]["valor"], hi_p[k]["valor"] = d["lo"], d["hi"]
        vl, vh = metrica(lo_p), metrica(hi_p)
        if abs(vh - vl) < 0.05:
            continue
        torn.append([d["etiqueta"], d["lo"], d["hi"], round(vl - base, 2), round(vh - base, 2), round(abs(vh - vl), 2)])
    # error vertical ±σ (corridas de batimetría)
    sig = v(p, "sigma_z")
    vs = []
    for dz in (-sig, sig):
        vs.append(sum((ola(p, a, 100, 30, "Base", dz)["Hb"] - ola(p, a, 100, 30, "Intervención", dz)["Hb"]) * 100 for a in ACIS) / 3)
    torn.append(["Error vertical de la topobatimetría (±σ)", -sig, sig, round(vs[0] - base, 2), round(vs[1] - base, 2), round(abs(vs[1] - vs[0]), 2)])
    torn.sort(key=lambda r: -r[5])
    write_csv(O("tornado.csv"), ["parametro", "valor_bajo", "valor_alto", "delta_bajo_cm", "delta_alto_cm", "amplitud_cm"], torn[:12])

    rng = random.Random(args.seed)
    keys = [k for k, d in p.items() if d["lo"] is not None and d["grupo"] != "Viento Iota"]
    sims = []
    for _ in range(args.mc):
        q = copy.deepcopy(p)
        for k in keys:
            d = p[k]
            q[k]["valor"] = rng.triangular(d["lo"], d["hi"], min(max(d["valor"], d["lo"]), d["hi"]))
        sims.append(metrica(q))
    sims.sort()
    pct = lambda x: sims[min(len(sims) - 1, int(x * len(sims)))]
    write_csv(O("montecarlo.csv"), ["estadistico", "dif_ola_cm"],
              [["P10", round(pct(.1), 2)], ["P50", round(pct(.5), 2)], ["P90", round(pct(.9), 2)],
               ["Media", round(sum(sims) / len(sims), 2)], ["Puntual", round(base, 2)], ["Iteraciones", len(sims)]])
    nb = 30
    lo_, hi_ = sims[0], sims[-1]
    w = (hi_ - lo_) / nb or 1
    bins = [0] * nb
    for s in sims:
        bins[min(nb - 1, int((s - lo_) / w))] += 1
    write_csv(O("montecarlo_hist.csv"), ["desde_cm", "hasta_cm", "frecuencia"],
              [[round(lo_ + i * w, 2), round(lo_ + (i + 1) * w, 2), bins[i]] for i in range(nb)])

    # 4.8 Iota: trayectoria y viento paramétrico
    write_csv(O("iota_track.csv"), ["fecha", "lat", "lon", "presion_hpa", "viento_kt", "dist_sai_km", "dist_pva_km"],
              [[f"{d} nov {h:02d}:00", la, lo, pc, w,
                round(hav(la, lo, *LUGARES["San Andrés (aeropuerto)"])), round(hav(la, lo, *LUGARES["Providencia"]))]
               for d, h, la, lo, pc, w in IOTA])
    vi = viento_iota(p)
    sai, pva = "San Andrés (aeropuerto)", "Providencia"
    rows = []
    for r in vi:
        if -6 <= r["hora"] <= 24:
            rows.append([r["hora"], hora_txt(r["hora"]), round(r[sai][0]), round(r[sai][2], 1), round(r[pva][0]), round(r[pva][1], 1), round(r[pva][3], 2)])
    write_csv(O("iota_viento.csv"), ["hora", "fecha", "dist_sai_km", "v10min_sai_kt", "dist_pva_km", "v1min_pva_kt", "B_holland"], rows)

    max_sai = max(vi, key=lambda r: r[sai][2])
    max_pva = max(vi, key=lambda r: r[pva][1])
    horas_h = sum(1 for r in vi if r[pva][1] >= 64)
    min_d = min(vi, key=lambda r: r[pva][0])
    calib = [
        ["C1", "Viento medio 10 min máximo, aeropuerto de San Andrés", 33, round(max_sai[sai][2], 1), "kt",
         f"NHC TCR (16 nov 13:00 UTC) · modelo {hora_txt(max_sai['hora'])}", URL_NHC],
        ["C2", "Viento sostenido 1 min máximo en Providencia", 115, round(max_pva[pva][1], 1), "kt",
         "NHC TCR: al menos 115 kt (SFMR); sin observación en superficie", URL_NHC],
        ["C3", "Horas con viento huracanado (≥ 64 kt) en Providencia", 7, horas_h, "h",
         "NHC TCR: ~7 h (07:00–14:00 UTC)", URL_NHC],
        ["C4", "Distancia mínima del centro a Providencia", round(5 * 1.852, 1), round(min_d[pva][0], 1), "km",
         "NHC TCR: el ojo pasó a menos de 5 n mi al norte (~10:45 UTC); trayectoria interpolada cada hora", URL_NHC],
        ["C5", "Marea de tormenta en San Andrés sobre la marea normal", 3.0, "", "m",
         "NHC TCR: «casi 3 m»; contrastar con el mareógrafo (PSMSL 2116 / UHSLC 737) y con DIMAR — objetivo del modelo hidrodinámico", URL_NHC],
        ["C6", "Lámina de inundación observada en Providencia", 2.2, "", "m",
         "Revisión documental del proyecto: 2–2,4 m; validación de extensión con UNOSAT y ARIA", ""],
        ["C7", "Estructuras dañadas en San Andrés (UNOSAT, conteo mínimo)", 31, "", "estructuras",
         "UNOSAT, descargado el 9 nov 2026: 31 dañadas y 221 potencialmente dañadas; sin máscara de nubes", "https://data.amerigeoss.org/dataset/damage-assessment-in-san-andres-island-providencia-and-santa-catalina-department-colombia"],
    ]
    write_csv(O("calibracion.csv"), ["id", "indicador", "observado", "modelo_cribado", "unidad", "fuente", "url"], calib)

    # 4.9 resumen para los KPI
    d100 = [r for r in dif if r[2] == 100 and r[3] == 30]
    write_csv(O("resumen.csv"), ["indicador", "valor", "unidad"], [
        ["dif_ola_tr100_t30_medio", round(base, 1), "cm"],
        ["dif_ola_tr100_t30_max", max(r[4] for r in d100), "cm"],
        ["dif_nivel_tr100_t30_medio", round(sum(r[6] for r in d100) / len(d100), 1), "cm"],
        ["corridas_total", len(corr), "corridas"],
        ["v10_sai_modelo", round(max_sai[sai][2], 1), "kt"],
    ])

    print(f"Diferencial medio de ola Tr100 t=30: {base:.1f} cm · MC P10/P50/P90 {pct(.1):.1f}/{pct(.5):.1f}/{pct(.9):.1f}")
    print(f"Iota: viento 10 min máx en SAI {max_sai[sai][2]:.1f} kt (obs. 33) · Providencia 1 min {max_pva[pva][1]:.0f} kt · {horas_h} h ≥ 64 kt")
    print(f"Corridas: {len(corr)} · CSV en {args.out}")


if __name__ == "__main__":
    main()
