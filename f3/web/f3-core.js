// ---------- utilidades compartidas ----------
(function () {
  const loc = d3.formatLocale({ decimal: ',', thousands: '.', grouping: [3], currency: ['$', ''] });
  const F3 = (window.F3 = window.F3 || {});
  F3.loc = loc;
  F3.n0 = loc.format(',.0f');
  F3.n1 = loc.format(',.1f');
  F3.n2 = loc.format(',.2f');
  F3.pct = loc.format('.0%');
  F3.M = (v) => F3.n0(v / 1e6);
  F3.sel = { aci: 'Dorna Pond', h: 30 };
  F3.ok = (id) => dash.data(id).status === 'ok';
  F3.rows = (id) => (dash.data(id).status === 'ok' ? dash.data(id).data : []);
  F3.colors = () => dash.colors;
  // estado visual de un dibujo cuando la fuente no está lista
  F3.guard = (el, ids, minH) => {
    const st = ids.map((i) => dash.data(i).status);
    if (st.every((s) => s === 'ok')) { el.classList.remove('dash-skeleton'); el.replaceChildren(); return true; }
    if (st.some((s) => s === 'error' || s === 'missing')) {
      el.classList.remove('dash-skeleton');
      el.replaceChildren();
      const p = document.createElement('div'); p.className = 'f3-fail'; p.textContent = 'No se pudo cargar';
      el.appendChild(p);
      return false;
    }
    el.replaceChildren();
    el.classList.add('dash-skeleton');
    return false;
  };
  F3.tip = (el) => {
    let t = el.querySelector(':scope > .f3-tip');
    if (!t) { t = document.createElement('div'); t.className = 'f3-tip'; t.hidden = true; el.appendChild(t); }
    return {
      show(ev, lines) {
        t.replaceChildren();
        lines.forEach((l, i) => { const d = document.createElement('div'); if (i === 0) d.className = 't'; d.textContent = l; t.appendChild(d); });
        t.hidden = false;
        const r = el.getBoundingClientRect();
        let x = ev.clientX - r.left + 12, y = ev.clientY - r.top + 12;
        const w = t.offsetWidth;
        if (x + w > r.width) x = Math.max(0, ev.clientX - r.left - w - 12);
        t.style.left = x + 'px'; t.style.top = y + 'px';
      },
      hide() { t.hidden = true; },
    };
  };
  F3.legend = (el, items) => {
    const lg = document.createElement('div'); lg.className = 'f3-legend';
    items.forEach(([name, color]) => {
      const s = document.createElement('span'); const i = document.createElement('i'); i.style.background = color;
      s.appendChild(i); s.appendChild(document.createTextNode(name)); lg.appendChild(s);
    });
    el.appendChild(lg);
  };
  F3.reduced = !window.matchMedia || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
})();

// ---------- cálculos con fuente visible ----------
dash.calc('kpi', {
  title: 'Indicadores de resumen (M COP)',
  description: 'Totales de las 3 ACI a partir de los CSV del modelo, en millones de COP redondeados.',
  inputs: ['acis', 'opex_comp', 'resumen', 'mc_pct'],
  fn: (acis, opex_comp, resumen, mc_pct) => {
    const tot = (h) => resumen.find((r) => r.aci === 'Total 3 ACI' && +r.horizonte === h) || {};
    const mc = (k) => +((mc_pct.find((r) => r.estadistico === k) || {}).vp_res1092_cop || 0);
    return [{
      capex_m: Math.round(acis.reduce((s, r) => s + +r.capex_cop, 0) / 1e6),
      opex_m: Math.round(opex_comp.reduce((s, r) => s + +r.cop_promedio_anual_3aci, 0) / 1e6),
      vp30_m: Math.round(+tot(30).vp_res1092_cop / 1e6),
      vp50_m: Math.round(+tot(50).vp_res1092_cop / 1e6),
      vp100_m: Math.round(+tot(100).vp_res1092_cop / 1e6),
      vp100_keur: Math.round(+tot(100).vp_res1092_eur / 1e3),
      p10_m: Math.round(mc('P10') / 1e6),
      p90_m: Math.round(mc('P90') / 1e6),
    }];
  },
});

dash.calc('estado', {
  title: 'Datos por estado',
  description: 'Número de insumos de la Fase 3 en cada estado de disponibilidad.',
  inputs: ['necesidades'],
  fn: (necesidades) => {
    const m = d3.rollup(necesidades, (v) => v.length, (r) => r.estado);
    return Array.from(m, ([estado, n]) => ({ estado, n }));
  },
});

dash.calc('flujos_total', {
  title: 'Flujo anual de costos, 3 ACI (M COP)',
  description: 'Suma por año de CAPEX, OPEX y total nominal de las tres ACI.',
  inputs: ['flujos'],
  fn: (flujos) => {
    const m = d3.rollup(flujos, (v) => ({
      capex_m: Math.round(d3.sum(v, (r) => +r.capex_cop) / 1e5) / 10,
      opex_m: Math.round(d3.sum(v, (r) => +r.opex_cop) / 1e5) / 10,
      nominal_m: Math.round(d3.sum(v, (r) => +r.total_nominal_cop) / 1e5) / 10,
    }), (r) => +r.anio);
    return Array.from(m, ([anio, o]) => ({ anio, ...o })).sort((a, b) => a.anio - b.anio);
  },
});

dash.calc('resumen_m', {
  title: 'Resumen por horizonte (M COP)',
  description: 'Sumas y valores presentes por ACI y horizonte, en millones de COP.',
  inputs: ['resumen'],
  fn: (resumen) => resumen.map((r) => ({
    clave: r.aci + ' · ' + r.horizonte,
    aci: r.aci,
    horizonte: +r.horizonte,
    constante_m: Math.round(+r.suma_constante_cop / 1e6),
    nominal_m: Math.round(+r.suma_nominal_cop / 1e6),
    vp1092_m: Math.round(+r.vp_res1092_cop / 1e6),
    vp5_m: Math.round(+r.vp_5pct_cop / 1e6),
  })),
});

// ---------- pestañas ----------
(function () {
  const ids = ['resumen', 'datos', 'parametros', 'capex', 'opex', 'curva', 'flujos', 'sensibilidad', 'metodo'];
  function open(id) {
    if (!ids.includes(id)) id = 'resumen';
    document.querySelectorAll('.f3-page').forEach((s) => { s.hidden = s.id !== id; });
    document.querySelectorAll('.f3-tab').forEach((b) => {
      const on = b.getAttribute('data-tab') === id;
      b.classList.toggle('is-on', on);
      b.setAttribute('aria-selected', on ? 'true' : 'false');
    });
  }
  document.querySelectorAll('.f3-tab').forEach((b) => {
    b.addEventListener('click', () => { const id = b.getAttribute('data-tab'); open(id); dash.setLink(id); });
  });
  open((location.hash || '').replace('#', '') || 'resumen');
  document.querySelectorAll('#sel-aci').forEach((s) => s.addEventListener('change', () => { window.F3.sel.aci = s.value; dash.draw('opex-chart'); }));
  document.querySelectorAll('#sel-h').forEach((s) => s.addEventListener('change', () => { window.F3.sel.h = +s.value; dash.draw('flujos-chart'); }));
})();

// ---------- KPI ----------
[['kpi-capex', 'capex_m'], ['kpi-capex-t', 'capex_m'], ['kpi-opex', 'opex_m'], ['kpi-vp30', 'vp30_m'], ['kpi-vp50', 'vp50_m'],
 ['kpi-vp50-t', 'vp50_m'], ['kpi-vp100', 'vp100_m'], ['kpi-eur100', 'vp100_keur'], ['kpi-p10', 'p10_m'], ['kpi-p90', 'p90_m']].forEach(([name, f]) => {
  dash.draw(name, (el) => {
    const k = dash.data('kpi');
    if (k.status !== 'ok' || !k.data || !k.data[0]) { el.textContent = '—'; return; }
    el.textContent = window.F3.n0(k.data[0][f]);
  });
});
dash.draw('mc-n', (el) => {
  const r = window.F3.rows('mc_pct').find((x) => x.estadistico === 'Iteraciones');
  el.textContent = r ? window.F3.n0(+r.vp_res1092_cop) : '—';
});

// ---------- tablas ----------
function f3Row(tbody, key, cells) {
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
function f3Badge(text) {
  const s = document.createElement('span');
  const t = String(text || '');
  let c = 'mut';
  if (/^Oficial|^Encontrado|^Proyecto/.test(t)) c = 'ok';
  else if (/^Proxy|^Verificar/.test(t)) c = 'warn';
  else if (/^Supuesto|^Solicitar|^Falta/.test(t)) c = 'bad';
  s.className = 'f3-badge ' + c; s.textContent = t; return s;
}
function f3Link(url, label) {
  if (!url || !/^https:\/\//.test(url)) { const s = document.createElement('span'); s.textContent = label || '—'; return s; }
  const a = document.createElement('a'); a.href = url; a.target = '_blank'; a.rel = 'noopener'; a.textContent = label || 'enlace'; return a;
}
window.F3.badge = f3Badge;

dash.draw('tabla-datos', (tb) => {
  tb.replaceChildren();
  window.F3.rows('necesidades').forEach((r) => f3Row(tb, r.id, [
    { t: r.id }, { t: r.dato, cls: 'wide' }, { node: f3Badge(r.estado) }, { t: r.lo_que_hay, cls: 'wide' },
    { t: r.siguiente_paso, cls: 'wide' }, { t: r.a_quien }, { node: f3Link(r.url, 'abrir') },
  ]));
});

dash.draw('tabla-param', (tb) => {
  tb.replaceChildren();
  const F3 = window.F3;
  const fmtv = (v, u) => {
    if (v == null || v === '') return '';
    const x = +v;
    if (/^%/.test(u) || /% s\//.test(u)) return F3.n1(x * 100) + ' %';
    if (Math.abs(x) >= 1000) return F3.n0(x);
    return F3.loc.format(',~r')(x);
  };
  F3.rows('parametros').forEach((r) => f3Row(tb, r.id, [
    { t: r.grupo }, { t: r.parametro, cls: 'wide' }, { t: fmtv(r.valor, r.unidad), cls: 'num' }, { t: r.unidad },
    { t: fmtv(r.rango_bajo, r.unidad), cls: 'num' }, { t: fmtv(r.rango_alto, r.unidad), cls: 'num' },
    { node: f3Badge(r.estado) }, { node: f3Link(r.url, r.fuente), cls: 'wide' },
  ]));
});

dash.draw('tabla-acis', (tb) => {
  tb.replaceChildren();
  const F3 = window.F3;
  F3.rows('acis').forEach((r) => f3Row(tb, r.aci, [
    { t: r.aci }, { t: r.perfil }, { t: F3.n0(+r.ha_provisional), cls: 'num' },
    { t: F3.pct(+r.frac_enriquecimiento), cls: 'num' }, { t: F3.pct(+r.frac_hidrologica), cls: 'num' }, { t: F3.pct(+r.frac_residuos), cls: 'num' },
    { t: F3.n0(+r.capex_cop_ha), cls: 'num' }, { t: F3.n0(+r.capex_usd_ha), cls: 'num' },
  ]));
});

dash.draw('tabla-curva', (tb) => {
  tb.replaceChildren();
  const F3 = window.F3;
  F3.rows('curva').filter((r) => [0, 10, 20, 30, 50].includes(+r.anio)).forEach((r) => f3Row(tb, r.anio, [
    { t: r.anio, cls: 'num' }, { t: F3.n2(+r.cobertura_vegetal), cls: 'num' }, { t: F3.n2(+r.estructura_proteccion), cls: 'num' }, { t: F3.n2(+r.estructura_alterno_lento), cls: 'num' },
  ]));
});

dash.draw('tabla-resumen', (tb) => {
  tb.replaceChildren();
  const F3 = window.F3;
  const d = dash.data('resumen_m');
  (d.status === 'ok' && d.data ? d.data : []).forEach((r) => {
    f3Row(tb, r.clave, [
      { t: r.aci }, { t: r.horizonte + ' años', cls: 'num' }, { t: F3.n0(r.constante_m), cls: 'num' }, { t: F3.n0(r.nominal_m), cls: 'num' },
      { t: F3.n0(r.vp1092_m), cls: 'num' }, { t: F3.n0(r.vp5_m), cls: 'num' },
    ]);
    if (r.aci === 'Total 3 ACI') tb.lastChild.className = 'tot';
  });
});
