#!/usr/bin/env python3
"""
Fase 3 — Cuantificación de costos de intervención (ACB Manglares San Andrés)
=============================================================================
Modelo reproducible de CAPEX, OPEX, curva logística de recuperación, flujos de
costos a 30/50/100 años y análisis de sensibilidad (puntual + alterno, tornado
y Monte Carlo).

Todos los valores están en COP constantes de 2026 salvo que se indique.
Cada parámetro lleva su fuente y su estado:
  - "Oficial"     : dato primario/institucional verificado
  - "Proxy"       : derivado de un proyecto comparable (literatura o informe técnico)
  - "Supuesto"    : valor provisional del consultor, a reemplazar con cotización o dato del proyecto
  - "Verificar"   : valor conocido que hay que confirmar en la fuente oficial
  - "Proyecto"    : documento del propio proyecto (Plan de Trabajo / Hoja de Ruta)

Uso:
    python3 modelo_costos_f3.py            # escribe los CSV en ./out
    python3 modelo_costos_f3.py --mc 20000 # cambia el número de iteraciones Monte Carlo

Cuando lleguen los datos reales (áreas de ACI tras el taller F2, cotizaciones
locales, costos MangRes/CORALINA), basta con editar PARAMS y ACIS y volver a
ejecutar.
"""
from __future__ import annotations

import argparse
import copy
import csv
import math
import os
import random
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# 1. PARÁMETROS
# ---------------------------------------------------------------------------
# (valor, unidad, grupo, etiqueta, estado, fuente, url, rango_bajo, rango_alto)
PARAMS: dict[str, dict] = {}


def P(key, valor, unidad, grupo, etiqueta, estado, fuente, url="", lo=None, hi=None, nota=""):
    PARAMS[key] = dict(valor=valor, unidad=unidad, grupo=grupo, etiqueta=etiqueta,
                       estado=estado, fuente=fuente, url=url, lo=lo, hi=hi, nota=nota)


# --- Macro y mano de obra ---------------------------------------------------
P("smmlv", 1_750_905, "COP/mes", "Macro y mano de obra", "Salario mínimo 2026 (SMMLV)", "Oficial",
  "Decreto 1469 de 2025 (MinTrabajo)", "https://www.mintrabajo.gov.co/")
P("aux_transp", 249_095, "COP/mes", "Macro y mano de obra", "Auxilio de transporte 2026", "Oficial",
  "Decreto 1470 de 2025 (MinTrabajo)", "https://www.mintrabajo.gov.co/")
P("factor_prest", 1.52, "×", "Macro y mano de obra", "Factor prestacional (seg. social, prestaciones, parafiscales)",
  "Supuesto", "Estimación del consultor; confirmar con contador o con FORLIANCE", lo=1.45, hi=1.60)
P("prima_jornal", 1.0, "×", "Macro y mano de obra", "Prima de mercado local sobre el jornal mínimo (San Andrés)",
  "Supuesto", "Pendiente cotización local (fila 3.01 de la matriz)", lo=0.95, hi=1.35)
P("trm", 3_300, "COP/USD", "Macro y mano de obra", "Tasa de cambio COP/USD (TRM)", "Verificar",
  "Banco de la República — TRM a la firma del contrato (29-oct-2026)", "https://www.banrep.gov.co/es/estadisticas/trm",
  lo=3_000, hi=3_900)
P("eur", 3_550, "COP/EUR", "Macro y mano de obra", "Tasa de cambio COP/EUR", "Verificar",
  "TRM (BanRep) × tipo EUR/USD del BCE a la firma del contrato", "https://www.ecb.europa.eu/stats/policy_and_exchange_rates/")
P("infl_1", 0.050, "%/año", "Macro y mano de obra", "Inflación año 1 (2027)", "Supuesto",
  "Convergencia desde el IPC de oct-2026 (DANE) hacia la meta", "https://www.dane.gov.co/index.php/estadisticas-por-tema/precios-y-costos/indice-de-precios-al-consumidor-ipc")
P("infl_2", 0.040, "%/año", "Macro y mano de obra", "Inflación año 2 (2028)", "Supuesto", "Convergencia hacia la meta del Banco de la República")
P("infl_lp", 0.030, "%/año", "Macro y mano de obra", "Inflación de largo plazo", "Oficial",
  "Meta de inflación del Banco de la República (3 %)", "https://www.banrep.gov.co/es/politica-monetaria")
P("tsd_0_5", 0.095, "%/año real", "Descuento", "TSD ambiental años 0–5", "Oficial",
  "DNP, Resolución 1092 de 2022, art. 2", "https://dnp.gov.co/publicaciones/Revista-Juridica/Paginas/Adopci%C3%B3n-de-la-Tasa-Social-de-Descuento-para-la-evaluaci%C3%B3n-de-proyectos-de-inversi%C3%B3n.aspx")
P("tsd_6_25", 0.064, "%/año real", "Descuento", "TSD ambiental años 6–25", "Oficial", "DNP, Resolución 1092 de 2022, art. 2")
P("tsd_26", 0.035, "%/año real", "Descuento", "TSD ambiental años 26+", "Oficial", "DNP, Resolución 1092 de 2022, art. 2")
P("tsd_hr", 0.05, "%/año real", "Descuento", "Tasa de la Hoja de Ruta (comparación)", "Proyecto",
  "Hoja de Ruta ACB (S1) — no coincide con la Res. 1092/2022; FORLIANCE pide seguir la Res. 1092")

# --- Enriquecimiento vegetal ----------------------------------------------
P("densidad", 1_600, "ind/ha", "Enriquecimiento vegetal", "Densidad de siembra (2,5 × 2,5 m)", "Supuesto",
  "Diseño provisional; ajustar a la ficha de cada ACI", lo=1_100, hi=2_500)
P("rend_siembra", 0.05, "jornal/plántula", "Enriquecimiento vegetal", "Rendimiento recolección + siembra", "Proxy",
  "CATIE (2025), Planes de intervención Cuerval, Timbiquí: 40 jornales para 800 plántulas",
  "https://www.ctc-n.org/file-download/download/private/45937", lo=0.035, hi=0.07)
P("insumo_plantula", 1_500, "COP/plántula", "Enriquecimiento vegetal", "Insumos de vivero por plántula (bolsa, sustrato)", "Supuesto",
  "Pendiente costos de viveros MangRes / PNN Old Providence", lo=800, hi=3_000)
P("prep_sitio", 15, "jornal/ha", "Enriquecimiento vegetal", "Preparación del sitio", "Supuesto", "Estimación del consultor", lo=8, hi=25)

# --- Rehabilitación hidrológica --------------------------------------------
P("rh_jornales", 90, "jornal/ha", "Rehabilitación hidrológica", "Limpieza/apertura manual de caños", "Supuesto",
  "Pendiente costos de RH de INVEMAR (Cispatá, 2017) y CORALINA", lo=60, hi=150)
P("rh_equipo", 6_000_000, "COP/ha", "Rehabilitación hidrológica", "Equipo menor (motobomba, excavación puntual)", "Supuesto",
  "Pendiente cotización local", lo=3_000_000, hi=12_000_000)

# --- Residuos sólidos ------------------------------------------------------
P("res_t_ha", 5, "t/ha", "Residuos sólidos", "Residuos acumulados por hectárea", "Supuesto",
  "Pendiente CORALINA / capa DisposicionResiduosSAI (Gobernación)", lo=2, hi=10)
P("res_jornal_t", 4, "jornal/t", "Residuos sólidos", "Jornales de recolección por tonelada", "Supuesto", "Estimación del consultor", lo=2.5, hi=6)
P("res_disp_t", 350_000, "COP/t", "Residuos sólidos", "Transporte y disposición final por tonelada", "Supuesto",
  "Pendiente tarifa del relleno de San Andrés", lo=200_000, hi=600_000)

# --- Logística e insumos generales ----------------------------------------
P("bote_usd_ha", 700, "USD/ha", "Logística e insumos", "Embarcación y combustible por campaña", "Proxy",
  "CATIE (2025): USD 800–1.000 por sitio de 1–1,8 ha", "https://www.ctc-n.org/file-download/download/private/45937", lo=400, hi=1_200)
P("herr_usd_ha", 200, "USD/ha", "Logística e insumos", "Herramientas, materiales y EPP", "Proxy",
  "CATIE (2025): USD 200–300 por sitio", "https://www.ctc-n.org/file-download/download/private/45937", lo=120, hi=350)

# --- Estudios, permisos, equipos, supervisión (por ACI) --------------------
P("estudios_aci", 45_000_000, "COP/ACI", "Estudios, permisos y supervisión", "Estudios técnicos (topografía, hidrología, diagnóstico)", "Supuesto",
  "Pendiente cotización; categoría exigida por los TdR", lo=25_000_000, hi=80_000_000)
P("permisos_aci", 20_000_000, "COP/ACI", "Estudios, permisos y supervisión", "Permisos, trámites y socialización comunitaria", "Supuesto",
  "Pendiente tarifas de evaluación de CORALINA", lo=10_000_000, hi=35_000_000)
P("equipos_usd_aci", 3_500, "USD/ACI", "Estudios, permisos y supervisión", "Equipos de monitoreo (sensores de nivel, miras)", "Supuesto",
  "Precio de lista de registradores de nivel; cotizar", lo=2_000, hi=6_000)
P("superv_mes", 9_000_000, "COP/mes", "Estudios, permisos y supervisión", "Honorario profesional de supervisión técnica", "Supuesto",
  "Pendiente tablas de honorarios de Patrimonio Natural / FORLIANCE (fila 3.03)", lo=6_000_000, hi=13_000_000)
P("superv_fte", 0.3, "FTE", "Estudios, permisos y supervisión", "Dedicación de supervisión por ACI", "Supuesto", "Estimación del consultor", lo=0.2, hi=0.5)
P("superv_meses", 24, "meses", "Estudios, permisos y supervisión", "Duración de la fase de implementación", "Supuesto", "Años 1–2 del flujo")
P("contingencia", 0.25, "% s/CAPEX", "Estudios, permisos y supervisión", "Contingencia por logística insular", "Supuesto",
  "FORLIANCE pide un rango sustentado; pendiente comparar contratos SECOP II isla vs. continente", lo=0.15, hi=0.40)

# --- OPEX ------------------------------------------------------------------
P("marras_1", 0.30, "fracción", "OPEX", "Replante de marras año 1", "Supuesto", "Ajustar con supervivencia observada en MangRes", lo=0.15, hi=0.50)
P("marras_2", 0.15, "fracción", "OPEX", "Replante de marras año 2", "Supuesto", "Ajustar con supervivencia observada en MangRes", lo=0.05, hi=0.30)
P("mant_ini", 12, "jornal/ha·año", "OPEX", "Mantenimiento años 1–3 (limpieza, control de invasoras)", "Proxy",
  "CATIE (2025): cuadrillas de mantenimiento a 6, 12, 18, 24 y 30 meses", "https://www.ctc-n.org/file-download/download/private/45937", lo=8, hi=20)
P("mant_lp", 4, "jornal/ha·año", "OPEX", "Mantenimiento año 4 en adelante", "Supuesto", "Estimación del consultor", lo=2, hi=8)
P("rh_relimpieza", 0.30, "fracción del CAPEX RH", "OPEX", "Re-limpieza de caños cada 5 años", "Supuesto", "Estimación del consultor", lo=0.15, hi=0.50)
P("monit_camp", 30_000_000, "COP/campaña·ACI", "OPEX", "Campaña de monitoreo científico (biomasa, carbono, agua)", "Proxy",
  "CATIE (2025): USD 6.000/año evaluación de indicadores + USD 3.000 informes", "https://www.ctc-n.org/file-download/download/private/45937", lo=18_000_000, hi=45_000_000)
P("guardas", 1.0, "FTE/ACI", "OPEX", "Guardabosques comunitarios (2 personas a medio tiempo)", "Supuesto",
  "Esquema de monitoreo comunitario del Plan de Trabajo", lo=0.5, hi=1.5)
P("gobernanza", 15_000_000, "COP/año·ACI", "OPEX", "Gobernanza, comunicación y gestión de permisos", "Supuesto", "Estimación del consultor", lo=8_000_000, hi=25_000_000)
P("reposicion_eq", 10, "años", "OPEX", "Reposición de equipos de monitoreo", "Supuesto", "Vida útil típica de registradores", lo=7, hi=15)

# --- Curva logística de recuperación ---------------------------------------
P("c0", 0.20, "fracción", "Curva de recuperación", "Condición inicial (fracción del manglar de referencia)", "Supuesto",
  "Manglar degradado; calibrar con LULC F1 y parcelas MangRes")
P("cmax", 0.95, "fracción", "Curva de recuperación", "Condición máxima alcanzable", "Supuesto",
  "Su et al. (2021): el manglar restaurado rinde por debajo del natural", "https://doi.org/10.1038/s41467-021-25349-1")
P("t50_veg", 6, "años", "Curva de recuperación", "Punto medio — cobertura vegetal", "Proxy",
  "Osland et al. (2020): equivalencia de vegetación juvenil en < 15 años", "https://pmc.ncbi.nlm.nih.gov/articles/pmid/31991504", lo=4, hi=9)
P("k_veg", 0.45, "1/año", "Curva de recuperación", "Pendiente — cobertura vegetal", "Proxy", "Calibrado para alcanzar ~0,9 a los 12–15 años", lo=0.30, hi=0.60)
P("t50_est", 14, "años", "Curva de recuperación", "Punto medio — estructura arbórea (protección)", "Proxy",
  "Osland et al. (2020): diámetro de árboles adultos equivalente a ~25 años", "https://pmc.ncbi.nlm.nih.gov/articles/pmid/31991504", lo=10, hi=20)
P("k_est", 0.22, "1/año", "Curva de recuperación", "Pendiente — estructura arbórea", "Proxy", "Calibrado para alcanzar ~0,9 a los 25 años", lo=0.15, hi=0.30)

# ---------------------------------------------------------------------------
# 2. ÁREAS CRÍTICAS DE INTERVENCIÓN (ACI) — candidatas pre-taller
# ---------------------------------------------------------------------------
# Fracciones = parte del área de la ACI donde se aplica cada intervención.
# Todo provisional hasta el acta de selección de F2 (taller dic 2026 – ene 2027).
ACIS = [
    dict(aci="Dorna Pond", perfil="Turismo / residuos", ha=10, f_enr=0.50, f_rh=0.30, f_res=0.80),
    dict(aci="Cove Sea Side", perfil="Exposición costera / siembra", ha=10, f_enr=0.80, f_rh=0.20, f_res=0.40),
    dict(aci="Smith Channel", perfil="Hidrología / conectividad", ha=10, f_enr=0.40, f_rh=0.90, f_res=0.30),
]

HORIZONTES = [30, 50, 100]
T_MAX = 100


# ---------------------------------------------------------------------------
# 3. MODELO
# ---------------------------------------------------------------------------
def v(p, k):
    return p[k]["valor"]


def jornal(p):
    """Costo de un jornal (COP/día) con prestaciones y auxilio de transporte."""
    return (v(p, "smmlv") * v(p, "factor_prest") + v(p, "aux_transp")) / 30 * v(p, "prima_jornal")


def costo_plantula(p):
    return v(p, "rend_siembra") * jornal(p) + v(p, "insumo_plantula")


def capex_aci(p, a):
    """CAPEX por categoría de los TdR para una ACI (COP 2026)."""
    J = jornal(p)
    ha = a["ha"]
    ha_enr, ha_rh, ha_res = ha * a["f_enr"], ha * a["f_rh"], ha * a["f_res"]
    n_pl = ha_enr * v(p, "densidad")

    mano = (n_pl * v(p, "rend_siembra") + ha_enr * v(p, "prep_sitio")
            + ha_rh * v(p, "rh_jornales") + ha_res * v(p, "res_t_ha") * v(p, "res_jornal_t")) * J
    insumos = (n_pl * v(p, "insumo_plantula") + ha_rh * v(p, "rh_equipo")
               + ha_res * v(p, "res_t_ha") * v(p, "res_disp_t")
               + ha * (v(p, "bote_usd_ha") + v(p, "herr_usd_ha")) * v(p, "trm"))
    estudios = v(p, "estudios_aci")
    permisos = v(p, "permisos_aci")
    equipos = v(p, "equipos_usd_aci") * v(p, "trm")
    superv = v(p, "superv_mes") * v(p, "superv_fte") * v(p, "superv_meses")
    base = mano + insumos + estudios + permisos + equipos + superv
    cont = base * v(p, "contingencia")
    out = {
        "Mano de obra": mano,
        "Insumos y materiales": insumos,
        "Estudios técnicos": estudios,
        "Permisos y socialización": permisos,
        "Equipos de monitoreo": equipos,
        "Supervisión técnica": superv,
        "Contingencia insular": cont,
    }
    # desglose por intervención (sin costos fijos por ACI)
    por_int = {
        "Enriquecimiento vegetal": (n_pl * v(p, "rend_siembra") + ha_enr * v(p, "prep_sitio")) * J + n_pl * v(p, "insumo_plantula"),
        "Rehabilitación hidrológica": ha_rh * (v(p, "rh_jornales") * J + v(p, "rh_equipo")),
        "Residuos sólidos": ha_res * v(p, "res_t_ha") * (v(p, "res_jornal_t") * J + v(p, "res_disp_t")),
    }
    return out, por_int, dict(n_pl=n_pl, ha_enr=ha_enr, ha_rh=ha_rh, ha_res=ha_res)


def opex_aci(p, a, t):
    """OPEX del año t (t ≥ 1) por componente (COP 2026)."""
    J = jornal(p)
    ha = a["ha"]
    _, por_int, q = capex_aci(p, a)
    comp = {}
    # mantenimiento: marras + limpieza
    marras = 0.0
    if t == 1:
        marras = v(p, "marras_1") * q["n_pl"] * costo_plantula(p)
    elif t == 2:
        marras = v(p, "marras_2") * q["n_pl"] * costo_plantula(p)
    limpieza = ha * (v(p, "mant_ini") if t <= 3 else v(p, "mant_lp")) * J
    comp["Mantenimiento"] = marras + limpieza
    # re-limpieza hidrológica (reinversión cada 5 años)
    comp["Reinversión hidrológica"] = por_int["Rehabilitación hidrológica"] * v(p, "rh_relimpieza") if t % 5 == 0 else 0.0
    # monitoreo científico: bianual hasta el año 30, luego quinquenal
    camp = (t <= 30 and t % 2 == 0) or (t > 30 and t % 5 == 0)
    comp["Monitoreo científico"] = v(p, "monit_camp") if camp else 0.0
    # monitoreo comunitario (guardabosques)
    comp["Monitoreo comunitario"] = v(p, "guardas") * 12 * (v(p, "smmlv") * v(p, "factor_prest") + v(p, "aux_transp"))
    comp["Gobernanza y gestión"] = v(p, "gobernanza")
    rep = int(round(v(p, "reposicion_eq")))
    comp["Reposición de equipos"] = v(p, "equipos_usd_aci") * v(p, "trm") if (t % rep == 0) else 0.0
    return comp


def capex_calendario(t):
    """Fracción del CAPEX por año: estudios/permisos/equipos en año 0, obras 70 % año 1 y 30 % año 2."""
    return {0: "fijos", 1: 0.70, 2: 0.30}.get(t)


def flujos_aci(p, a):
    cap, por_int, _ = capex_aci(p, a)
    fijos = cap["Estudios técnicos"] + cap["Permisos y socialización"] + cap["Equipos de monitoreo"]
    fijos *= (1 + v(p, "contingencia"))
    variable = sum(cap.values()) - fijos
    rows = []
    for t in range(0, T_MAX + 1):
        c = fijos if t == 0 else (variable * capex_calendario(t) if t in (1, 2) else 0.0)
        o = sum(opex_aci(p, a, t).values()) if t >= 1 else 0.0
        rows.append((t, c, o))
    return rows


def inflacion(p, t):
    if t == 1:
        return v(p, "infl_1")
    if t == 2:
        return v(p, "infl_2")
    return v(p, "infl_lp")


def tsd(p, t):
    if t <= 5:
        return v(p, "tsd_0_5")
    if t <= 25:
        return v(p, "tsd_6_25")
    return v(p, "tsd_26")


def factores(p):
    """Índice de precios y factores de descuento (Res. 1092 escalonada y 5 % constante)."""
    idx, df1092, df5 = [1.0], [1.0], [1.0]
    for t in range(1, T_MAX + 1):
        idx.append(idx[-1] * (1 + inflacion(p, t)))
        df1092.append(df1092[-1] / (1 + tsd(p, t)))
        df5.append(df5[-1] / (1 + v(p, "tsd_hr")))
    return idx, df1092, df5


def vp_total(p, horizonte=50):
    _, df, _ = factores(p)
    tot = 0.0
    for a in ACIS:
        for t, c, o in flujos_aci(p, a):
            if t <= horizonte:
                tot += (c + o) * df[t]
    return tot


def logistica(t, c0, cmax, t50, k):
    return c0 + (cmax - c0) / (1 + math.exp(-k * (t - t50)))


# ---------------------------------------------------------------------------
# 4. SALIDAS
# ---------------------------------------------------------------------------
def write_csv(path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)


def r0(x):
    return int(round(x))


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
              [[k, d["grupo"], d["etiqueta"], d["valor"], d["unidad"],
                "" if d["lo"] is None else d["lo"], "" if d["hi"] is None else d["hi"],
                d["estado"], d["fuente"], d["url"]] for k, d in p.items()])

    # 4.2 ACIs y CAPEX
    capex_rows, int_rows, aci_rows = [], [], []
    for a in ACIS:
        cap, por_int, q = capex_aci(p, a)
        for cat, val in cap.items():
            capex_rows.append([a["aci"], cat, r0(val)])
        for it, val in por_int.items():
            int_rows.append([a["aci"], it, r0(val)])
        tot = sum(cap.values())
        o3 = sum(sum(opex_aci(p, a, t).values()) for t in (1, 2, 3))
        aci_rows.append([a["aci"], a["perfil"], a["ha"], a["f_enr"], a["f_rh"], a["f_res"], r0(q["n_pl"]),
                         r0(tot), r0(tot / a["ha"]), round(tot / a["ha"] / v(p, "trm")),
                         round((tot + o3) / a["ha"] / v(p, "trm")), round(tot / v(p, "eur"))])
    write_csv(O("capex.csv"), ["aci", "categoria", "cop"], capex_rows)
    write_csv(O("capex_intervencion.csv"), ["aci", "intervencion", "cop"], int_rows)
    write_csv(O("acis.csv"), ["aci", "perfil", "ha_provisional", "frac_enriquecimiento", "frac_hidrologica",
                              "frac_residuos", "plantulas", "capex_cop", "capex_cop_ha", "capex_usd_ha",
                              "capex_opex3_usd_ha", "capex_eur"], aci_rows)

    # 4.3 OPEX por componente (años 1–30, para el gráfico) y promedio anual
    opex_rows = []
    for a in ACIS:
        for t in range(1, 31):
            for comp, val in opex_aci(p, a, t).items():
                opex_rows.append([a["aci"], t, comp, r0(val)])
    write_csv(O("opex_anual.csv"), ["aci", "anio", "componente", "cop"], opex_rows)

    opex_tot = {}
    for a in ACIS:
        for t in range(1, 31):
            for comp, val in opex_aci(p, a, t).items():
                opex_tot[comp] = opex_tot.get(comp, 0) + val
    write_csv(O("opex_componentes.csv"), ["componente", "cop_promedio_anual_3aci"],
              [[k, r0(val / 30)] for k, val in opex_tot.items()])

    # calendario de reinversiones (años 1–100)
    rein = []
    a0 = ACIS[0]
    for t in range(1, T_MAX + 1):
        c = opex_aci(p, a0, t)
        ev = []
        if c["Reinversión hidrológica"] > 0:
            ev.append("Re-limpieza de caños")
        if c["Monitoreo científico"] > 0:
            ev.append("Campaña de monitoreo científico")
        if c["Reposición de equipos"] > 0:
            ev.append("Reposición de equipos")
        if t in (1, 2):
            ev.append("Replante de marras")
        for e in ev:
            rein.append([t, e])
    write_csv(O("reinversiones.csv"), ["anio", "evento"], rein)

    # 4.4 curva logística
    curva = []
    for t in range(0, 51):
        curva.append([t,
                      round(logistica(t, v(p, "c0"), v(p, "cmax"), v(p, "t50_veg"), v(p, "k_veg")), 4),
                      round(logistica(t, v(p, "c0"), v(p, "cmax"), v(p, "t50_est"), v(p, "k_est")), 4),
                      round(logistica(t, v(p, "c0"), v(p, "cmax"), v(p, "t50_est") * 1.4, v(p, "k_est") * 0.8), 4)])
    write_csv(O("curva_recuperacion.csv"), ["anio", "cobertura_vegetal", "estructura_proteccion", "estructura_alterno_lento"], curva)

    # 4.5 flujos anuales
    idx, df1092, df5 = factores(p)
    fl_rows = []
    for a in ACIS:
        for t, c, o in flujos_aci(p, a):
            tot = c + o
            fl_rows.append([a["aci"], t, 2026 + t, r0(c), r0(o), r0(tot), r0(tot * idx[t]),
                            round(df1092[t], 6), r0(tot * df1092[t]), r0(tot * df5[t])])
    write_csv(O("flujos.csv"), ["aci", "anio", "anio_calendario", "capex_cop", "opex_cop", "total_constante_cop",
                                "total_nominal_cop", "factor_desc_res1092", "vp_res1092_cop", "vp_5pct_cop"], fl_rows)

    # resumen por horizonte
    res = []
    for a in ACIS:
        fl = [r for r in fl_rows if r[0] == a["aci"]]
        for h in HORIZONTES:
            sel = [r for r in fl if r[1] <= h]
            res.append([a["aci"], h, sum(r[5] for r in sel), sum(r[6] for r in sel),
                        sum(r[8] for r in sel), sum(r[9] for r in sel), round(sum(r[8] for r in sel) / v(p, "eur"))])
    for h in HORIZONTES:
        sel = [r for r in res if r[1] == h]
        res.append(["Total 3 ACI", h] + [sum(r[i] for r in sel) for i in range(2, 7)])
    write_csv(O("resumen_horizontes.csv"), ["aci", "horizonte", "suma_constante_cop", "suma_nominal_cop",
                                            "vp_res1092_cop", "vp_5pct_cop", "vp_res1092_eur"], res)

    # 4.6 sensibilidad — tornado sobre VP 50 años (Res. 1092)
    base = vp_total(p, 50)
    torn = []
    for k, d in p.items():
        if d["lo"] is None:
            continue
        lo_p, hi_p = copy.deepcopy(p), copy.deepcopy(p)
        lo_p[k]["valor"], hi_p[k]["valor"] = d["lo"], d["hi"]
        vl, vh = vp_total(lo_p, 50), vp_total(hi_p, 50)
        if abs(vh - vl) < 1:
            continue
        torn.append([d["etiqueta"], d["lo"], d["hi"], r0(vl - base), r0(vh - base), r0(abs(vh - vl))])
    torn.sort(key=lambda r: -r[5])
    write_csv(O("tornado.csv"), ["parametro", "valor_bajo", "valor_alto", "delta_bajo_cop", "delta_alto_cop", "amplitud_cop"], torn[:12])

    # escenario puntual vs alterno (TdR: estimación puntual + escenario alterno)
    alt = copy.deepcopy(p)
    for k in ["contingencia", "prima_jornal", "marras_1", "marras_2", "monit_camp", "rh_jornales", "res_t_ha", "insumo_plantula", "trm"]:
        alt[k]["valor"] = alt[k]["hi"]
    esc = []
    for h in HORIZONTES:
        esc.append(["Puntual", h, r0(vp_total(p, h))])
        esc.append(["Alterno (costos altos)", h, r0(vp_total(alt, h))])
    write_csv(O("escenarios.csv"), ["escenario", "horizonte", "vp_res1092_cop"], esc)

    # Monte Carlo — triangular(lo, modo, hi) en todos los parámetros con rango
    rng = random.Random(args.seed)
    keys = [k for k, d in p.items() if d["lo"] is not None and not k.startswith(("t50", "k_"))]
    sims = []
    for _ in range(args.mc):
        q = copy.deepcopy(p)
        for k in keys:
            d = p[k]
            lo, hi, mo = d["lo"], d["hi"], d["valor"]
            mo = min(max(mo, lo), hi)
            q[k]["valor"] = rng.triangular(lo, hi, mo)
        sims.append(vp_total(q, 50))
    sims.sort()
    pct = lambda x: sims[min(len(sims) - 1, int(x * len(sims)))]
    write_csv(O("montecarlo_percentiles.csv"), ["estadistico", "vp_res1092_cop"],
              [["P10", r0(pct(0.10))], ["P50", r0(pct(0.50))], ["P90", r0(pct(0.90))],
               ["Media", r0(sum(sims) / len(sims))], ["Puntual", r0(base)], ["Iteraciones", len(sims)]])
    nb = 30
    lo_, hi_ = sims[0], sims[-1]
    w = (hi_ - lo_) / nb
    bins = [0] * nb
    for s in sims:
        bins[min(nb - 1, int((s - lo_) / w))] += 1
    write_csv(O("montecarlo_hist.csv"), ["desde_cop", "hasta_cop", "frecuencia"],
              [[r0(lo_ + i * w), r0(lo_ + (i + 1) * w), bins[i]] for i in range(nb)])

    # 4.7 referencias de costo por hectárea (USD/ha)
    bench = [
        ["Goto et al. 2025 — mediana global", 8_143, "Implementación, 249 proyectos en 25 países (USD int. 2022)", "https://doi.org/10.1016/j.oneear.2025.101342"],
        ["Goto et al. 2025 — media global", 9_739, "Restaurar 1,1 Mha: USD 10.730 M (USD int. 2022)", "https://doi.org/10.1016/j.oneear.2025.101342"],
        ["CATIE 2025 — Cuerval (Timbiquí) bajo", 18_640, "Total 3 años con monitoreo, sitio de 1,4 ha", "https://www.ctc-n.org/file-download/download/private/45937"],
        ["CATIE 2025 — Cuerval (Timbiquí) alto", 25_600, "Total 3 años con monitoreo, sitio de 1 ha", "https://www.ctc-n.org/file-download/download/private/45937"],
    ]
    for r in aci_rows:
        bench.append([f"Este modelo — {r[0]} (CAPEX + OPEX 3 años)", r[10], "Estimación preliminar, 10 ha provisionales", ""])
    write_csv(O("benchmark.csv"), ["referencia", "usd_ha", "nota", "url"], bench)

    print(f"Jornal: {jornal(p):,.0f} COP/día")
    print(f"VP 50 años (Res. 1092), 3 ACI: {base/1e6:,.0f} M COP")
    print(f"Monte Carlo P10/P50/P90: {pct(.1)/1e6:,.0f} / {pct(.5)/1e6:,.0f} / {pct(.9)/1e6:,.0f} M COP")
    print(f"CSV escritos en {args.out}")


if __name__ == "__main__":
    main()
