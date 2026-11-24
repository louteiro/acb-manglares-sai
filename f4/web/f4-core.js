// ---------- utilidades compartidas ----------
(function () {
  const loc = d3.formatLocale({ decimal: ',', thousands: '.', grouping: [3], currency: ['$', ''] });
  const F4 = (window.F4 = window.F4 || {});
  F4.loc = loc;
  F4.n0 = loc.format(',.0f');
  F4.n1 = loc.format(',.1f');
  F4.n2 = loc.format(',.2f');
  F4.n3 = loc.format(',.3f');
  F4.sel = { aciPerfil: 'Old Point / Bahía Hooker', trPerfil: 100, aciDif: 'Old Point / Bahía Hooker', aciCorr: 'Old Point / Bahía Hooker', caso: 'Solo SDB y carta' };
  F4.rows = (id) => (dash.data(id).status === 'ok' ? dash.data(id).data || [] : []);
  F4.colors = () => dash.colors;
  F4.parseD = d3.utcParse('%Y-%m-%d');
  F4.fmtD = (d) => {
    const m = ['ene', 'feb', 'mar', 'abr', 'may', 'jun', 'jul', 'ago', 'sep', 'oct', 'nov', 'dic'];
    return `${d.getUTCDate()} ${m[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
  };
  F4.guard = (el, ids) => {
    const st = ids.map((i) => dash.data(i).status);
    if (st.every((s) => s === 'ok')) { el.classList.remove('dash-skeleton'); el.replaceChildren(); return true; }
    if (st.some((s) => s === 'error' || s === 'missing')) {
      el.classList.remove('dash-skeleton');
      el.replaceChildren();
      const p = document.createElement('div'); p.className = 'f4-fail'; p.textContent = 'No se pudo cargar';
      el.appendChild(p);
      return false;
    }
    el.replaceChildren();
    el.classList.add('dash-skeleton');
    return false;
  };
  F4.tip = (el) => {
    let t = el.querySelector(':scope > .f4-tip');
    if (!t) { t = document.createElement('div'); t.className = 'f4-tip'; t.hidden = true; el.appendChild(t); }
    return {
      show(ev, lines) {
        t.replaceChildren();
        lines.forEach((l, i) => { const d = document.createElement('div'); if (i === 0) d.className = 't'; d.textContent = l; t.appendChild(d); });
        t.hidden = false;
        const r = el.getBoundingClientRect();
        let x = ev.clientX - r.left + 12;
        const y = ev.clientY - r.top + 12;
        const w = t.offsetWidth;
        if (x + w > r.width) x = Math.max(0, ev.clientX - r.left - w - 12);
        t.style.left = x + 'px'; t.style.top = y + 'px';
      },
      hide() { t.hidden = true; },
    };
  };
  F4.legend = (el, items) => {
    const lg = document.createElement('div'); lg.className = 'f4-legend';
    items.forEach(([name, color]) => {
      const s = document.createElement('span'); const i = document.createElement('i'); i.style.background = color;
      s.appendChild(i); s.appendChild(document.createTextNode(name)); lg.appendChild(s);
    });
    el.appendChild(lg);
  };
})();

// ---------- cálculos con fuente visible ----------
dash.calc('kpi', {
  title: 'Indicadores de resumen',
  description: 'Diferencial de ola y de nivel (Tr 100, t = 30), número de corridas, viento de Iota modelado y estado de los datos.',
  inputs: ['resumen', 'necesidades'],
  fn: (resumen, necesidades) => {
    const g = (k) => +((resumen.find((r) => r.indicador === k) || {}).valor || 0);
    const listos = necesidades.filter((r) => r.estado === 'Tenemos' || r.estado === 'Encontrado fuera').length;
    return [{
      dif_ola_cm: g('dif_ola_tr100_t30_medio'),
      dif_ola_max_cm: g('dif_ola_tr100_t30_max'),
      dif_nivel_cm: g('dif_nivel_tr100_t30_medio'),
      corridas: g('corridas_total'),
      v10_sai_kt: g('v10_sai_modelo'),
      n_datos: necesidades.length,
      n_listos: listos,
      n_pend: necesidades.length - listos,
    }];
  },
});

dash.calc('estado', {
  title: 'Datos de la F4 por estado',
  description: 'Número de insumos de la Fase 4 en cada estado de disponibilidad.',
  inputs: ['necesidades'],
  fn: (necesidades) => Array.from(d3.rollup(necesidades, (v) => v.length, (r) => r.estado), ([estado, n]) => ({ estado, n })),
});

dash.calc('matriz_tot', {
  title: 'Puntaje ponderado de cada modelo',
  description: 'Suma de peso × puntaje (1–5) por opción de modelo y caso de batimetría.',
  inputs: ['matriz'],
  fn: (matriz) => {
    const out = [];
    d3.group(matriz, (r) => r.caso).forEach((rows, caso) => {
      [['adcirc_swan', 'ADCIRC+SWAN'], ['xbeach', 'XBeach'], ['anidado', 'ADCIRC+SWAN → XBeach']].forEach(([k, opcion]) => {
        out.push({ clave: caso + '|' + opcion, caso, opcion, total: Math.round(d3.sum(rows, (r) => +r.peso * +r[k]) * 100) / 100 });
      });
    });
    return out;
  },
});

// ---------- pestañas ----------
(function () {
  const ids = ['resumen', 'datos', 'parametros', 'batimetria', 'modelo', 'malla', 'iota', 'corridas', 'beneficio', 'sensibilidad', 'metodo'];
  function open(id) {
    if (!ids.includes(id)) id = 'resumen';
    document.querySelectorAll('.f4-page').forEach((s) => { s.hidden = s.id !== id; });
    document.querySelectorAll('.f4-tab').forEach((b) => {
      const on = b.getAttribute('data-tab') === id;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.f4-tab').forEach((b) => {
    b.addEventListener('click', () => { const id = b.getAttribute('data-tab'); open(id); dash.setLink(id); });
  });
  open((location.hash || '').replace('#', '') || 'resumen');
  const S = window.F4.sel;
  const bind = (id, key, num, draws) => document.querySelectorAll('#' + id).forEach((s) => s.addEventListener('change', () => {
    S[key] = num ? +s.value : s.value; draws.forEach((d) => dash.draw(d));
  }));
  bind('sel-aci-perfil', 'aciPerfil', false, ['perfil-chart']);
  bind('sel-tr-perfil', 'trPerfil', true, ['perfil-chart']);
  bind('sel-aci-dif', 'aciDif', false, ['dif-chart', 'tabla-beneficio']);
  bind('sel-aci-corr', 'aciCorr', false, ['tabla-corridas']);
  bind('sel-caso', 'caso', false, ['matriz-chart', 'tabla-matriz']);
})();

// ---------- KPI ----------
[['kpi-dif', 'dif_ola_cm', 1], ['kpi-dif-t', 'dif_ola_cm', 1], ['kpi-difmax', 'dif_ola_max_cm', 1], ['kpi-nivel', 'dif_nivel_cm', 1],
 ['kpi-nivel-t', 'dif_nivel_cm', 1], ['kpi-corr', 'corridas', 0], ['kpi-v10', 'v10_sai_kt', 1], ['kpi-ndatos', 'n_datos', 0],
 ['kpi-ndatos-t', 'n_datos', 0], ['kpi-listos', 'n_listos', 0], ['kpi-listos-t', 'n_listos', 0], ['kpi-pend', 'n_pend', 0]].forEach(([name, f, dec]) => {
  dash.draw(name, (el) => {
    const k = dash.data('kpi');
    if (k.status !== 'ok' || !k.data || !k.data[0]) { el.textContent = '—'; return; }
    el.textContent = dec ? window.F4.n1(k.data[0][f]) : window.F4.n0(k.data[0][f]);
  });
});
[['mc-p10', 'P10'], ['mc-p90', 'P90'], ['mc-p10-b', 'P10'], ['mc-p90-b', 'P90']].forEach(([name, k]) => {
  dash.draw(name, (el) => {
    const r = window.F4.rows('mc_pct').find((x) => x.estadistico === k);
    el.textContent = r ? window.F4.n1(+r.dif_ola_cm) : '—';
  });
});
dash.draw('mc-n', (el) => {
  const r = window.F4.rows('mc_pct').find((x) => x.estadistico === 'Iteraciones');
  el.textContent = r ? window.F4.n0(+r.dif_ola_cm) : '—';
});

// ---------- tablas ----------
function f4Row(tbody, key, cells) {
  const tr = document.createElement('tr');
  tr.setAttribute('data-key', encodeURIComponent(key));
  cells.forEach((c) => {
    const td = document.createElement('td');
    if (c.cls) td.className = c.cls;
    if (c.node) td.appendChild(c.node); else td.textContent = c.t == null ? '' : c.t;
    tr.appendChild(td);
  });
  tbody.appendChild(tr);
}
function f4Badge(text) {
  const s = document.createElement('span');
  const t = String(text || '');
  let c = 'mut';
  if (/^(Oficial|Tenemos|Encontrado|Proyecto|En curso)/.test(t)) c = 'ok';
  else if (/^(Proxy|Verificar|Solicitado|Generar)/.test(t)) c = 'warn';
  else if (/^(Supuesto|Solicitar|Falta)/.test(t)) c = 'bad';
  s.className = 'f4-badge ' + c; s.textContent = t; return s;
}
function f4Link(url, label) {
  if (!url || !/^https:\/\//.test(url)) { const s = document.createElement('span'); s.textContent = label || '—'; return s; }
  const a = document.createElement('a'); a.href = url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = label || 'enlace'; return a;
}
window.F4.badge = f4Badge;

dash.draw('tabla-datos', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  const order = ['Falta', 'Solicitar', 'Solicitado', 'Generar', 'Encontrado fuera', 'Tenemos'];
  F4.rows('necesidades').slice().sort((a, b) => order.indexOf(a.estado) - order.indexOf(b.estado) || a.id.localeCompare(b.id)).forEach((r) => f4Row(tb, r.id, [
    { t: r.id }, { t: r.actividad }, { t: r.dato, cls: 'wide' }, { node: f4Badge(r.estado) }, { t: r.lo_que_hay, cls: 'wide' },
    { t: r.siguiente_paso, cls: 'wide' }, { t: r.a_quien }, { t: r.fecha_limite ? F4.fmtD(F4.parseD(r.fecha_limite)) : '—', cls: 'num' }, { node: f4Link(r.url, 'abrir') },
  ]));
});

dash.draw('tabla-param', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  const fv = (x) => (x == null || x === '' ? '' : F4.loc.format(',~r')(+x));
  F4.rows('parametros').forEach((r) => f4Row(tb, r.id, [
    { t: r.grupo }, { t: r.parametro, cls: 'wide' }, { t: fv(r.valor), cls: 'num' }, { t: r.unidad },
    { t: fv(r.rango_bajo), cls: 'num' }, { t: fv(r.rango_alto), cls: 'num' }, { node: f4Badge(r.estado) }, { node: f4Link(r.url, r.fuente), cls: 'wide' },
  ]));
});

dash.draw('tabla-bati', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('batimetria').forEach((r) => f4Row(tb, r.id, [
    { t: r.paso }, { t: r.descripcion, cls: 'wide' }, { t: F4.fmtD(F4.parseD(r.inicio)), cls: 'num' }, { t: F4.fmtD(F4.parseD(r.fin)), cls: 'num' },
    { node: f4Badge(r.estado) }, { t: r.herramientas },
  ]));
});

dash.draw('tabla-matriz', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('matriz').filter((r) => r.caso === F4.sel.caso).forEach((r) => f4Row(tb, r.criterio + '|' + r.caso, [
    { t: r.criterio, cls: 'wide' }, { t: F4.n2(+r.peso), cls: 'num' }, { t: r.adcirc_swan, cls: 'num' }, { t: r.xbeach, cls: 'num' }, { t: r.anidado, cls: 'num' }, { t: r.nota, cls: 'wide' },
  ]));
});

dash.draw('tabla-rug', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('rugosidad').forEach((r) => f4Row(tb, r.clase, [
    { t: r.clase }, { t: F4.n3(+r.manning_n), cls: 'num' }, { t: F4.n3(+r.rango_bajo) + '–' + F4.n3(+r.rango_alto), cls: 'num' }, { node: f4Badge(r.estado) }, { t: r.fuente, cls: 'wide' },
  ]));
});

dash.draw('tabla-veg', (tb) => {
  tb.replaceChildren();
  window.F4.rows('vegetacion').forEach((r) => f4Row(tb, r.parametro, [
    { t: r.parametro }, { t: r.valor, cls: 'num' }, { t: r.unidad }, { node: f4Badge(r.estado) }, { node: f4Link(r.url, r.fuente), cls: 'wide' }, { t: r.uso, cls: 'wide' },
  ]));
});

dash.draw('tabla-track', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('iota_track').forEach((r) => f4Row(tb, r.fecha, [
    { t: r.fecha }, { t: F4.n1(+r.lat), cls: 'num' }, { t: F4.n1(+r.lon), cls: 'num' }, { t: F4.n0(+r.presion_hpa), cls: 'num' }, { t: F4.n0(+r.viento_kt), cls: 'num' },
    { t: F4.n0(+r.dist_sai_km), cls: 'num' }, { t: F4.n0(+r.dist_pva_km), cls: 'num' },
  ]));
});

dash.draw('tabla-calib', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('calibracion').forEach((r) => f4Row(tb, r.id, [
    { t: r.indicador, cls: 'wide' }, { t: F4.n1(+r.observado), cls: 'num' }, { t: r.modelo_cribado === '' || r.modelo_cribado == null ? 'Modelo hidrodinámico' : F4.n1(+r.modelo_cribado), cls: 'num' },
    { t: r.unidad }, { node: f4Link(r.url, r.fuente), cls: 'wide' },
  ]));
});

dash.draw('tabla-forz', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('forzamiento').forEach((r) => f4Row(tb, r.tr, [
    { t: 'Tr ' + r.tr }, { t: F4.n2(+r.nivel_t0_m), cls: 'num' }, { t: F4.n2(+r.nivel_t10_m), cls: 'num' }, { t: F4.n2(+r.nivel_t20_m), cls: 'num' },
    { t: F4.n2(+r.nivel_t30_m), cls: 'num' }, { t: F4.n2(+r.nivel_t50_m), cls: 'num' }, { t: F4.n2(+r.nivel_t100_m), cls: 'num' },
  ]));
});

dash.draw('tabla-corridas', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('corridas').filter((r) => r.aci === F4.sel.aciCorr).forEach((r) => f4Row(tb, r.id, [
    { t: r.id }, { t: r.tr, cls: 'num' }, { t: r.escenario }, { t: r.anm }, { t: F4.n2(+r.nivel_m), cls: 'num' }, { t: r.lulc }, { t: r.tipo }, { node: f4Badge(r.estado) },
  ]));
});

dash.draw('tabla-beneficio', (tb) => {
  tb.replaceChildren();
  const F4 = window.F4;
  F4.rows('beneficio').filter((r) => r.aci === F4.sel.aciDif && +r.corte === 30).forEach((r) => f4Row(tb, r.clave, [
    { t: 'Tr ' + r.tr }, { t: r.escenario }, { t: F4.n2(+r.condicion), cls: 'num' }, { t: F4.n2(+r.lamina_m), cls: 'num' }, { t: F4.n2(+r.H0_m), cls: 'num' },
    { t: F4.n2(+r.H_fondo_m), cls: 'num' }, { t: F4.n1(+r.reduccion_ola_pct) + ' %', cls: 'num' }, { t: F4.n1(+r.atenuacion_nivel_cm), cls: 'num' },
  ]));
});
