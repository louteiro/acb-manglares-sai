#!/usr/bin/env python3
"""
Tablas de seguimiento de la Fase 4 (ACB Manglares San Andrés): necesidades de
datos, hitos del camino crítico, vías de batimetría, matriz de elección del
modelo, rugosidad por clase LULC y parámetros de vegetación.

Estado de los datos (a 22 nov 2026):
  Tenemos · Encontrado fuera · Solicitado · Solicitar · Generar · Falta
Edita las listas y ejecuta: python3 tablas_f4.py  (escribe en ./out)
"""
import csv
import os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")

NEC = [
    # id, actividad, fila matriz, dato, estado, lo que hay, siguiente paso, a quién, fecha límite, url
    ("D01", "4.1", "4.01/4.02", "Batimetría CIOH 2015–2017 (vía a)", "Solicitado",
     "Monohaz en someras y multihaz en profundas; la usa Rey et al. (2021). Pedida por transparencia el 19 nov 2026 (formulario DIMAR M5-FOR-146)",
     "Seguimiento del plazo legal de respuesta; si llega antes del 29 ene sustituye a la SDB", "DIMAR-CIOH (vía FORLIANCE)", "2027-01-29", "https://www.dimar.mil.co/"),
    ("D02", "4.1", "4.01", "Batimetría propia de INVEMAR (vía b)", "Solicitado",
     "INVEMAR la mencionó el 10 nov; no pasó el control de calidad del CIOH. Pedida por email el 11 nov 2026",
     "Si llega, evaluar su calidad con las sondas de la carta antes de usarla", "INVEMAR (Gabriela, FORLIANCE)", "2027-01-29", "https://siam.invemar.org.co/"),
    ("D03", "4.1", "4.02", "Carta náutica CIOH 201 (sondas e isóbatas)", "Solicitar",
     "Base de la vía c (paso B.1)", "Conseguir la carta electrónica (S-57) o la de papel escaneada y digitalizar sondas", "DIMAR-CIOH", "2026-12-15", "https://cecoldodigital.dimar.mil.co/"),
    ("D04", "4.1", "nuevo", "ICESat-2 ATL03 / ATL24 (puntos de profundidad)", "Encontrado fuera",
     "Perfiles de fotones y producto batimétrico ATL24 de libre acceso", "Descargar los pasos sobre SAI con SlideRule y filtrar por calidad", "Consultor", "2026-12-31", "https://nsidc.org/data/atl24"),
    ("D05", "4.1", "nuevo", "Escenas Sentinel-2 L1C sin nubes ni brillo solar", "Encontrado fuera",
     "Copernicus Data Space; corrección atmosférica con ACOLITE", "Seleccionar 3–5 escenas de aguas claras", "Consultor", "2026-12-31", "https://dataspace.copernicus.eu/"),
    ("D06", "4.1", "4.03", "Batimetría regional (dominio exterior)", "Encontrado fuera",
     "GEBCO (también es la capa Batimetría del geoportal SAI) y SRTM15+", "Recortar el dominio exterior", "Consultor", "2027-02-28", "https://download.gebco.net/"),
    ("D07", "4.1", "4.04", "MDE terrestre de 5 m (curvas de nivel IGAC)", "Tenemos",
     "Generado a partir de las curvas del geoportal (400 entidades)", "Mejorar si llega un MDT mejor antes del HB.1", "Consultor", "", "https://geoportal.sanandres.gov.co/server/rest/services/CartografiaBaseSAI/MapServer/0"),
    ("D08", "4.1", "4.04", "MDT de 2 m (2020) o LiDAR 5 m de Rey et al.", "Solicitar",
     "Existe según la ficha ANM (Univ. Distrital, 2025) y Rey et al. (2021)", "Carta de FORLIANCE a CORALINA y Gobernación; pedir también a INVEMAR cualquier MDT parcial", "CORALINA / Gobernación (vía FORLIANCE)", "2027-02-28", ""),
    ("D09", "4.3", "4.05", "Línea de costa (Límite de Isla 1:800)", "Tenemos",
     "Descargada con las capas del geoportal", "Revisar contra la ortofoto 2025 en las ACI", "Consultor", "", "https://geoportal.sanandres.gov.co/server/rest/services/CartografiaBaseSAI/MapServer/3"),
    ("D10", "4.1", "nuevo", "Cota del suelo bajo el manglar", "Generar",
     "El MDE y los modelos satelitales pueden dar la cota del dosel, no la del suelo", "Corregir con ICESat-2 ATL08 (terreno bajo el dosel), cotas de parcelas y piezómetros de INVEMAR, CORALINA y MangRes si las tienen, y zonación–marea", "Consultor", "2027-02-28", "https://nsidc.org/data/atl08"),
    ("D11", "4.4", "4.06", "Marea observada (mareógrafo de San Andrés)", "Encontrado fuera",
     "PSMSL 2116 / UHSLC 737 en abierto; serie DIMAR pendiente", "Descargar y pedir a DIMAR la serie horaria de nov 2020; alternativa TPXO/FES2014", "DIMAR (vía FORLIANCE)", "2027-03-30", "https://psmsl.org/data/obtaining/stations/2116.php"),
    ("D12", "4.5", "4.07", "Niveles extremos para Tr 10, 25, 50 y 100 años", "Encontrado fuera",
     "COAST-RP y GTSM (globales, con ciclones); en el tablero hay marcadores provisionales", "Extraer el punto más cercano a SAI y contrastar con Rey et al. (2021)", "Consultor", "2027-01-31", "https://data.4tu.nl/datasets/4e291b8f-a37e-4378-8ca6-954a44fdc8fb"),
    ("D13", "4.5", "4.07", "Niveles 10/25/50 años con los 1.078 ciclones de Rey y Ruiz-Salcines", "Solicitar",
     "Solo publicados los de 100 y 500 años (Velásquez-Calderón et al., 2026)", "Pedir a los autores (correo a Wilmar Rey enviado el 8 nov sobre batimetría)", "W. Rey / P. Ruiz-Salcines", "2027-02-28", "https://doi.org/10.1016/j.ocecoaman.2026.108404"),
    ("D14", "4.4", "4.08", "Oleaje (Hs, Tp, dirección) de fondo", "Encontrado fuera",
     "ERA5 y reanálisis de oleaje de Copernicus Marine", "Descargar 1980–2025 en el contorno del dominio", "Consultor", "2027-02-28", "https://cds.climate.copernicus.eu/datasets/reanalysis-era5-single-levels"),
    ("D15", "4.4", "1.12", "Trayectoria de Iota (best track)", "Tenemos",
     "Tabla 1 del informe del NHC, ya incorporada en este tablero; IBTrACS como contraste", "Usar el best track para el campo de viento de la calibración", "Consultor", "", "https://www.nhc.noaa.gov/data/tcr/AL312020_Iota.pdf"),
    ("D16", "4.5", "4.09", "Ciclones sintéticos (eventos de 50–100 años)", "Encontrado fuera",
     "STORM (Bloemendaal et al., 2020)", "Seleccionar los eventos de diseño por Tr", "Consultor", "2027-03-31", "https://data.4tu.nl/articles/dataset/STORM_IBTrACS_present_climate_synthetic_tropical_cyclone_tracks/12706085"),
    ("D17", "4.2", "nuevo", "Mallas SWAN de las cartas 200 y 201 (Ortiz Royero et al., 2015)", "Solicitar",
     "Mallas de 140 m y 40 m; batimetría de plataforma de 2005", "Escribir a J. C. Ortiz Royero (Universidad del Norte)", "Universidad del Norte", "2027-01-31", ""),
    ("D18", "4.3", "1.07", "LULC t = 0 y futuros (6 clases, 10 m, EPSG:32617)", "Generar",
     "Vector CLIMARES20 2008 descargado; t = 0 en la F1 y t = 10/20/30 en la F3 (actividad 3.4)", "Cerrar la leyenda con Antonio (FORLIANCE)", "Consultor", "2027-01-08", "https://gis.invemar.org.co/arcgis/rest/services/CLIMARES20/CLIMARES20_TM_Caso_SAI_Providencia/MapServer"),
    ("D19", "4.3", "1.08", "Arrecifes, pastos marinos y fondos (rugosidad del fondo)", "Tenemos",
     "AmbientalSAI (áreas coralinas, pastos, comunidades marinas) descargado", "Contrastar con Allen Coral Atlas y asignar Manning", "Consultor", "", "https://allencoralatlas.org/atlas/"),
    ("D20", "4.3", "1.05", "Parcelas de estructura del manglar (densidad, DAP, altura)", "Tenemos",
     "BDD_SAI de INVEMAR, recibida el 17 nov 2026: 2.993 árboles en 8 estaciones de San Andrés (2021–2025), con especie, DAP y altura; sin altura de raíces fúlcreas ni diccionario de códigos de estado", "Derivar densidad, diámetro y altura por ACI; altura de raíces con Ohira et al. (2013); preguntar a INVEMAR los códigos ME, PA y NE", "INVEMAR (Línea RAE)", "", ""),
    ("D21", "4.3", "4.10", "Coeficiente de arrastre y tasas de atenuación de Rhizophora", "Encontrado fuera",
     "Kelty et al. (2022): C_D = 0,6 + 3·10⁴/Re; Lopez-Arias et al. (2024): datos de campo en R. mangle", "Usar como rango a priori y calibrar", "Consultor", "", "https://doi.org/10.3389/fmars.2021.780946"),
    ("D22", "4.3", "4.10", "Altura de dosel y biomasa del manglar (Simard et al., 2019)", "Encontrado fuera",
     "Producto global de 30 m (ORNL DAAC)", "Descargar para SAI; solo como contraste", "Consultor", "", "https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1665"),
    ("D23", "4.4", "1.20", "Daños de Iota por edificación (UNOSAT)", "Tenemos",
     "Descargados el 9 nov 2026: en San Andrés, 31 estructuras dañadas y 221 potencialmente dañadas; en Providencia, 1.100", "Validación de extensión; en San Andrés es un conteo mínimo (sin máscara de nubes), así que la calibración se apoya en Providencia", "Consultor", "", "https://data.amerigeoss.org/dataset/damage-assessment-in-san-andres-island-providencia-and-santa-catalina-department-colombia"),
    ("D24", "4.4", "4.11", "Mapa de daños ARIA (Sentinel-1, 22 nov 2020)", "Encontrado fuera",
     "Servicio rotulado Eta 2020", "Confirmar que cubre el Archipiélago", "Consultor", "", "https://maps.disasters.nasa.gov/ags04/rest/services/hurricane_eta_2020/aria_dpm_sentinel1_20201122/ImageServer"),
    ("D25", "4.4", "nuevo", "Daño al manglar y cotas de inundación observadas tras Iota (INVEMAR)", "Solicitado",
     "Pedidos a INVEMAR el 10 nov 2026 (parcelas de 2021 y expedición posterior a Iota)", "Seguimiento con INVEMAR; sin ellos, solo UNOSAT", "INVEMAR (vía FORLIANCE)", "2027-03-31", ""),
    ("D26", "4.6", "nuevo", "Atenuación de la marea de tormenta por manglar", "Encontrado fuera",
     "Zhang et al. (2012): 20–50 cm/km; Krauss et al. (2009): 4,2–9,4 cm/km", "Rango para el cribado; el valor local sale de las corridas", "Consultor", "", "https://doi.org/10.1016/j.ecss.2012.02.021"),
    ("D27", "4.5", "1.10", "ANM local (IPCC AR6 + GNSS SAN0)", "Tenemos",
     "Tabla de la ficha ANM: +8/+17/+26 cm en t = 10/20/30", "Validar la velocidad vertical de SAN0 con el SGC", "Consultor", "", "https://sealevel.nasa.gov/ipcc-ar6-sea-level-projection-tool"),
    ("D28", "4.2", "2.04", "Tres ACI aprobadas con sus escenarios (H2.3)", "Falta",
     "Candidatas del tablero: Old Point / Bahía Hooker, Cove Sea Side (El Cove) y Smith Channel, todas con parcelas INVEMAR. La capa sectores_SAI prioriza 9 sectores en San Andrés", "Lista corta con INVEMAR (H2.0, 11 dic 2026), ACI propuestas (H2.2, 4 ene 2027), Taller 1 y aprobación escrita", "FORLIANCE / CORALINA", "2027-01-29", ""),
    ("D29", "4.5", "nuevo", "Recursos de cómputo para ADCIRC+SWAN", "Falta",
     "XBeach cabe en equipo local; ADCIRC+SWAN pide clúster", "Decidir en la nota de elección del modelo (4.2)", "Consultor / FORLIANCE", "2027-03-31", ""),
]

HITOS = [
    # id, nombre, inicio, fin, tipo, depende, estado
    ("4.1", "4.1 Batimetría (vías a/b/c, pasos B.1–B.5)", "2026-12-01", "2027-03-26", "actividad", "—", "En curso"),
    ("H2.0", "H2.0 Lista corta acordada con INVEMAR", "2026-12-11", "2026-12-11", "hito", "Respuesta de INVEMAR (actividad 2.3)", "Pendiente"),
    ("H2.2", "H2.2 Pesos fijados y ACI propuestas", "2027-01-04", "2027-01-04", "hito", "H2.0, encuesta de pesos", "Pendiente"),
    ("H2.3", "H2.3 Tres ACI aprobadas", "2027-01-29", "2027-01-29", "hito", "Taller 1", "Pendiente"),
    ("CORTE", "Fecha de corte: datos oficiales sustituyen a la SDB", "2027-01-29", "2027-01-29", "hito", "D01, D02", "Pendiente"),
    ("4.2", "4.2 Elección del modelo", "2027-02-01", "2027-03-31", "actividad", "H2.3, batimetría v0", "Pendiente"),
    ("4.3", "4.3 Malla, rugosidad y vegetación", "2027-02-28", "2027-04-30", "actividad", "Batimetría v0", "Pendiente"),
    ("HB.1", "HB.1 Topobatimetría v1 aceptada", "2027-03-26", "2027-03-26", "hito", "B.1–B.4", "Pendiente"),
    ("4.4", "4.4 Calibración con Iota", "2027-04-01", "2027-05-07", "actividad", "HB.1", "Pendiente"),
    ("H4.1", "H4.1 Modelo calibrado con Iota", "2027-05-07", "2027-05-07", "hito", "HB.1", "Pendiente"),
    ("4.5", "4.5 Corridas de escenarios", "2027-05-08", "2027-06-11", "actividad", "H4.1", "Pendiente"),
    ("4.6", "4.6 Beneficio biofísico", "2027-05-20", "2027-06-15", "actividad", "4.5", "Pendiente"),
    ("4.7", "4.7 Redacción del E3", "2027-06-01", "2027-06-25", "actividad", "4.6", "Pendiente"),
    ("E3", "E3 Informe Fases 3 y 4", "2027-06-25", "2027-06-25", "hito", "H4.1", "Pendiente"),
]

BATI = [
    # id, paso, descripcion, inicio, fin, estado, herramientas
    ("a", "Vía a · DIMAR-CIOH", "Batimetría CIOH 2015–2017 (monohaz + multihaz), pedida por transparencia el 19 nov 2026. Vía preferente por sus parámetros de calidad", "2026-11-19", "2027-01-29", "Solicitado", "Solicitud por transparencia"),
    ("b", "Vía b · INVEMAR", "Batimetría propia de INVEMAR, sin control de calidad del CIOH", "2026-11-11", "2027-01-29", "Solicitado", "Email; evaluación con sondas de la carta"),
    ("B.1", "B.1 Compilación", "Sondas e isóbatas de la carta CIOH 201, perfiles ICESat-2 ATL03, GEBCO/SRTM15+ en el dominio exterior", "2026-12-01", "2026-12-31", "Por empezar", "GDAL, SlideRule, QGIS"),
    ("B.2", "B.2 Batimetría derivada de satélite", "Cociente de bandas calibrado con ICESat-2 y sondas, y red U-Net con los mismos puntos", "2026-12-01", "2027-02-28", "Por empezar", "ACOLITE, scikit-learn, LightGBM, PyTorch"),
    ("B.3", "B.3 Unión con el MDE", "Unión con el MDE de 5 m y el Límite de Isla 1:800 en una referencia vertical común (nivel medio local); cota del suelo bajo el manglar corregida con ICESat-2 ATL08", "2027-02-01", "2027-03-20", "Por empezar", "GDAL, pyTMD (FES2014/TPXO)"),
    ("B.4", "B.4 Validación e incertidumbre", "Validación cruzada con sondas reservadas; error por rango de profundidad y mapa de σ", "2027-02-01", "2027-03-20", "Por empezar", "Python"),
    ("B.5", "B.5 Aceptación (HB.1)", "Cubre las tres ACI sin huecos, error documentado, revisión del equipo de inteligencia espacial de FORLIANCE", "2027-03-26", "2027-03-26", "Por empezar", "Revisión Antonio (FORLIANCE)"),
]

# Matriz de elección del modelo (actividad 4.2). Puntajes 1–5, provisionales del consultor.
MATRIZ = [
    # criterio, peso, caso, ADCIRC+SWAN, XBeach, anidado, nota
    ("Tolerancia a la batimetría disponible", 0.30, "Solo SDB y carta", 4, 2, 3, "XBeach exige nearshore ≤ 5–10 m; ADCIRC con malla variable lo tolera mejor"),
    ("Tolerancia a la batimetría disponible", 0.30, "Con batimetría CIOH", 4, 4, 4, "Con sondajes oficiales ambos son viables"),
    ("Mecanismo dominante (marea de tormenta E–NE / oleaje SE)", 0.30, "Solo SDB y carta", 3, 3, 5, "Si las ACI combinan ambos mecanismos, el anidamiento los cubre"),
    ("Mecanismo dominante (marea de tormenta E–NE / oleaje SE)", 0.30, "Con batimetría CIOH", 3, 3, 5, ""),
    ("Escala (isla y contorno frente a ACI de pocos km)", 0.20, "Solo SDB y carta", 4, 3, 5, "ADCIRC+SWAN da el contorno; XBeach el detalle con vegetación"),
    ("Escala (isla y contorno frente a ACI de pocos km)", 0.20, "Con batimetría CIOH", 4, 3, 5, ""),
    ("Cómputo y plazo (16 corridas por ACI)", 0.20, "Solo SDB y carta", 2, 4, 2, "ADCIRC+SWAN pide clúster; XBeach a 2–5 m cabe en equipo local"),
    ("Cómputo y plazo (16 corridas por ACI)", 0.20, "Con batimetría CIOH", 2, 4, 2, ""),
]

RUG = [
    # clase, n, lo, hi, estado, fuente
    ("Manglar maduro", 0.14, 0.10, 0.20, "Proxy", "Rango de valores para bosque inundable en modelos de marea de tormenta; sustituir por el término de arrastre en XBeach"),
    ("Manglar degradado", 0.08, 0.05, 0.12, "Supuesto", "Interpolado entre manglar maduro y área deforestada"),
    ("Manglar en recuperación", 0.10, 0.06, 0.14, "Supuesto", "Sigue la curva de condición de la F3"),
    ("Área deforestada", 0.035, 0.025, 0.05, "Proxy", "Valor habitual para suelo desnudo o herbáceo"),
    ("Agua y zonas inundables", 0.02, 0.015, 0.025, "Proxy", "Valor habitual para aguas abiertas"),
    ("Infraestructura", 0.12, 0.08, 0.15, "Proxy", "Valor habitual para zona urbana densa"),
    ("Arrecife (fondo)", 0.04, 0.03, 0.06, "Supuesto", "Fondo rugoso; calibrar con Iota"),
    ("Pastos marinos (fondo)", 0.03, 0.025, 0.035, "Supuesto", "Fondo vegetado sumergido"),
]

VEG = [
    # parametro, valor, unidad, estado, fuente, uso, url
    ("Densidad de árboles", "450 (Smith Channel), 167–464 (El Cove), 2.070 (Bahía Hooker)", "árboles/ha", "Tenemos", "BDD_SAI INVEMAR, árboles vivos con DAP ≥ 2,5 cm (2023–2025)", "Área frontal por unidad de volumen", ""),
    ("DAP medio", "37,7 (Smith Channel), 16,9–23,2 (El Cove), 10,0 (Bahía Hooker)", "cm", "Tenemos", "BDD_SAI INVEMAR (2023–2025)", "Con Ohira et al. (2013) da número, altura y diámetro de raíces", ""),
    ("Altura de los árboles", "En la BDD, por resumir", "m", "Tenemos", "BDD_SAI INVEMAR", "Altura de la vegetación en XBeach/SWAN", ""),
    ("Altura de la zona de raíces fúlcreas", "1,5 (supuesto)", "m", "Supuesto", "Ohira et al. (2013), a partir del DAP de las parcelas", "Corte del área frontal en profundidad", ""),
    ("Coeficiente de arrastre C_D", "0,6 + 3·10⁴/Re_DAP", "—", "Proxy", "Kelty et al. (2022), Rhizophora a escala de prototipo", "Término de vegetación de XBeach/SWAN", "https://doi.org/10.3389/fmars.2021.780946"),
    ("Tasa de atenuación de ola (campo, R. mangle)", "0,001–0,01", "1/m", "Proxy", "Lopez-Arias et al. (2024): −34 % de altura a 63 m", "Rango de validación", "https://doi.org/10.3389/fmars.2024.1383368"),
    ("Tasa de atenuación de ola (laboratorio)", "0,004–0,021", "1/m", "Proxy", "Kelty et al. (2022), baja y alta densidad", "β del modelo de cribado", "https://doi.org/10.3389/fmars.2021.780946"),
    ("Atenuación de la marea de tormenta", "9,4–50", "cm/km", "Proxy", "Krauss et al. (2009); Zhang et al. (2012)", "Atenuación de nivel del cribado", "https://doi.org/10.1016/j.ecss.2012.02.021"),
    ("Altura del dosel", "Por descargar", "m", "Encontrado fuera", "Simard et al. (2019), ORNL DAAC", "Contraste de la estructura", "https://daac.ornl.gov/cgi-bin/dsviewer.pl?ds_id=1665"),
]


def w(name, header, rows):
    with open(os.path.join(OUT, name), "w", newline="", encoding="utf-8") as f:
        c = csv.writer(f)
        c.writerow(header)
        c.writerows(rows)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    w("necesidades_datos.csv", ["id", "actividad", "fila_matriz", "dato", "estado", "lo_que_hay", "siguiente_paso", "a_quien", "fecha_limite", "url"], NEC)
    w("hitos.csv", ["id", "nombre", "inicio", "fin", "tipo", "depende", "estado"], HITOS)
    w("batimetria.csv", ["id", "paso", "descripcion", "inicio", "fin", "estado", "herramientas"], BATI)
    w("matriz_modelo.csv", ["criterio", "peso", "caso", "adcirc_swan", "xbeach", "anidado", "nota"], MATRIZ)
    w("rugosidad.csv", ["clase", "manning_n", "rango_bajo", "rango_alto", "estado", "fuente"], RUG)
    w("vegetacion.csv", ["parametro", "valor", "unidad", "estado", "fuente", "uso", "url"], VEG)
    print(f"{len(NEC)} datos · {len(HITOS)} hitos · CSV en {OUT}")
