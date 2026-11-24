// ---------- gráficos ----------
(function () {
  const F3 = window.F3;
  const W = (el) => Math.max(280, el.clientWidth || 600);

  // margen izquierdo según la etiqueta más ancha
  function measure(svg, labels) {
    const t = svg.append('text').attr('class', 'tmp');
    let m = 0;
    labels.forEach((l) => { t.text(l); m = Math.max(m, t.node().getComputedTextLength() || l.length * 6.5); });
    t.remove();
    return m;
  }
  function base(el, h, label) {
    const svg = d3.select(el).append('svg').attr('width', '100%').attr('height', h).attr('role', 'img').attr('aria-label', label);
    return svg;
  }

  // ---- barras horizontales apiladas: rows=[{label, parts:{k:v}}]
  function hstack(el, rows, keys, opt) {
    const C = F3.colors();
    const w = W(el);
    const rowH = opt.rowH || 34;
    const h = rows.length * rowH + 30;
    const svg = base(el, h, opt.aria);
    const ml = Math.min(w * 0.4, measure(svg, rows.map((r) => r.label)) + 10);
    const mr = 70;
    const totals = rows.map((r) => keys.reduce((s, k) => s + (r.parts[k] || 0), 0));
    const x = d3.scaleLinear().domain([0, d3.max(totals) || 1]).nice().range([ml, w - mr]);
    const y = d3.scaleBand().domain(rows.map((r) => r.label)).range([0, h - 24]).padding(0.28);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((w - ml) / 110))).tickSize(-(h - 24)).tickFormat(opt.tick || F3.M));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    const tip = F3.tip(el);
    rows.forEach((r, i) => {
      let x0 = 0;
      keys.forEach((k, j) => {
        const val = r.parts[k] || 0;
        if (!val) return;
        svg.append('rect').attr('x', x(x0)).attr('y', y(r.label)).attr('height', y.bandwidth()).attr('width', Math.max(0, x(x0 + val) - x(x0)))
          .style('fill', C[j % C.length])
          .on('mousemove', (ev) => tip.show(ev, [r.label, `${k}: ${(opt.fmt || F3.M)(val)} ${opt.unit || ''}`]))
          .on('mouseleave', tip.hide);
        x0 += val;
      });
      svg.append('text').attr('class', 'vlabel').attr('x', x(totals[i]) + 6).attr('y', y(r.label) + y.bandwidth() / 2).attr('dy', '0.35em').text((opt.fmt || F3.M)(totals[i]));
    });
    if (keys.length > 1) F3.legend(el, keys.map((k, j) => [k, C[j % C.length]]));
  }

  // ---- barras verticales apiladas por año
  function vstack(el, data, keys, opt) {
    const C = F3.colors();
    const w = W(el);
    const h = opt.h || 300;
    const svg = base(el, h, opt.aria);
    const maxV = d3.max(data, (d) => Math.max(keys.reduce((s, k) => s + (d[k] || 0), 0), opt.line ? d[opt.line] || 0 : 0)) || 1;
    const y = d3.scaleLinear().domain([0, maxV]).nice().range([h - 26, 8]);
    const ml = measure(svg, y.ticks(5).map(opt.tick || F3.n0)) + 12;
    const x = d3.scaleBand().domain(data.map((d) => d.anio)).range([ml, w - 8]).padding(0.15);
    const every = Math.ceil(data.length / Math.max(4, Math.floor((w - ml) / 45)));
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(w - ml - 8)).tickFormat(opt.tick || F3.n0));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).tickValues(data.map((d) => d.anio).filter((a, i) => i % every === 0)).tickSizeOuter(0));
    const tip = F3.tip(el);
    data.forEach((d) => {
      let y0 = 0;
      keys.forEach((k, j) => {
        const val = d[k] || 0;
        if (!val) return;
        svg.append('rect').attr('x', x(d.anio)).attr('width', x.bandwidth()).attr('y', y(y0 + val)).attr('height', Math.max(0, y(y0) - y(y0 + val)))
          .style('fill', C[j % C.length])
          .on('mousemove', (ev) => tip.show(ev, [`Año ${d.anio}`].concat(keys.map((kk) => `${kk}: ${(opt.fmt || F3.n1)(d[kk] || 0)} ${opt.unit || ''}`)).concat(opt.line ? [`${opt.lineName}: ${(opt.fmt || F3.n1)(d[opt.line])} ${opt.unit || ''}`] : [])))
          .on('mouseleave', tip.hide);
        y0 += val;
      });
    });
    const items = keys.map((k, j) => [k, C[j % C.length]]);
    if (opt.line) {
      const lc = C[keys.length % C.length];
      svg.append('path').datum(data).attr('fill', 'none').style('stroke', lc).attr('stroke-width', 2)
        .attr('d', d3.line().x((d) => x(d.anio) + x.bandwidth() / 2).y((d) => y(d[opt.line])));
      items.push([opt.lineName, lc]);
    }
    F3.legend(el, items);
  }

  // ---- líneas
  function lines(el, data, series, opt) {
    const C = F3.colors();
    const w = W(el);
    const h = opt.h || 320;
    const svg = base(el, h, opt.aria);
    const y = d3.scaleLinear().domain(opt.ydom || [0, d3.max(data, (d) => d3.max(series, (s) => d[s.k]))]).nice().range([h - 26, 8]);
    const ml = measure(svg, y.ticks(5).map(opt.tick || F3.n2)) + 12;
    const x = d3.scaleLinear().domain(d3.extent(data, (d) => d.x)).range([ml, w - 12]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(w - ml - 12)).tickFormat(opt.tick || F3.n2));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).ticks(Math.max(4, Math.floor((w - ml) / 60))).tickFormat(d3.format('d')));
    (opt.marks || []).forEach((m) => {
      svg.append('line').attr('x1', x(m)).attr('x2', x(m)).attr('y1', 8).attr('y2', h - 26).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '3 3');
      svg.append('text').attr('x', x(m) + 4).attr('y', 18).text('t=' + m);
    });
    series.forEach((s, j) => {
      svg.append('path').datum(data).attr('fill', 'none').style('stroke', C[j % C.length]).attr('stroke-width', 2)
        .attr('stroke-dasharray', s.dash || null)
        .attr('d', d3.line().x((d) => x(d.x)).y((d) => y(d[s.k])));
    });
    const tip = F3.tip(el);
    const dot = svg.append('line').style('stroke', 'var(--cds-chart-reference)').attr('y1', 8).attr('y2', h - 26).attr('opacity', 0);
    svg.append('rect').attr('x', ml).attr('y', 0).attr('width', w - ml - 12).attr('height', h - 26).attr('fill', 'transparent')
      .on('mousemove', (ev) => {
        const [mx] = d3.pointer(ev);
        const xv = x.invert(mx);
        const d = data.reduce((a, b) => (Math.abs(b.x - xv) < Math.abs(a.x - xv) ? b : a));
        dot.attr('x1', x(d.x)).attr('x2', x(d.x)).attr('opacity', 1);
        tip.show(ev, [`${opt.xname || 'Año'} ${d.x}`].concat(series.map((s) => `${s.name}: ${(opt.fmt || F3.n2)(d[s.k])}`)));
      })
      .on('mouseleave', () => { dot.attr('opacity', 0); tip.hide(); });
    F3.legend(el, series.map((s, j) => [s.name, C[j % C.length]]));
  }

  // ======== dibujos ========
  dash.draw('estado-chart', (el) => {
    if (!F3.guard(el, ['estado'])) return;
    const d = dash.data('estado').data || [];
    const order = ['Encontrado fuera', 'Proxy', 'Verificar', 'Supuesto', 'Solicitar', 'Falta (F2)'];
    const rows = d.slice().sort((a, b) => order.indexOf(a.estado) - order.indexOf(b.estado)).map((r) => ({ label: r.estado, parts: { Datos: r.n } }));
    hstack(el, rows, ['Datos'], { aria: 'Número de insumos por estado de disponibilidad', fmt: F3.n0, tick: d3.format('d'), unit: 'datos', rowH: 30 });
  });

  dash.draw('bench-chart', (el) => {
    if (!F3.guard(el, ['benchmark'])) return;
    const rows = F3.rows('benchmark').map((r) => ({ label: r.referencia.replace(' (CAPEX + OPEX 3 años)', ''), parts: { 'USD/ha': +r.usd_ha } }));
    hstack(el, rows, ['USD/ha'], { aria: 'Costo por hectárea del modelo frente a referencias', fmt: F3.n0, tick: F3.n0, unit: 'USD/ha', rowH: 30 });
  });

  dash.draw('capex-chart', (el) => {
    if (!F3.guard(el, ['capex'])) return;
    const d = F3.rows('capex');
    const keys = Array.from(new Set(d.map((r) => r.categoria)));
    const acis = Array.from(new Set(d.map((r) => r.aci)));
    const rows = acis.map((a) => ({ label: a, parts: Object.fromEntries(d.filter((r) => r.aci === a).map((r) => [r.categoria, +r.cop])) }));
    hstack(el, rows, keys, { aria: 'CAPEX por ACI y categoría, millones de COP', unit: 'M COP', rowH: 46 });
  });

  dash.draw('capexint-chart', (el) => {
    if (!F3.guard(el, ['capex_int'])) return;
    const d = F3.rows('capex_int');
    const keys = Array.from(new Set(d.map((r) => r.intervencion)));
    const acis = Array.from(new Set(d.map((r) => r.aci)));
    const rows = acis.map((a) => ({ label: a, parts: Object.fromEntries(d.filter((r) => r.aci === a).map((r) => [r.intervencion, +r.cop])) }));
    hstack(el, rows, keys, { aria: 'Costo directo por intervención, millones de COP', unit: 'M COP', rowH: 40 });
  });

  dash.draw('opex-chart', (el) => {
    if (!F3.guard(el, ['opex_anual'])) return;
    el.replaceChildren();
    const d = F3.rows('opex_anual').filter((r) => r.aci === F3.sel.aci);
    const keys = Array.from(new Set(d.map((r) => r.componente)));
    const by = d3.group(d, (r) => +r.anio);
    const data = Array.from(by, ([anio, v]) => Object.assign({ anio }, Object.fromEntries(v.map((r) => [r.componente, +r.cop / 1e6])))).sort((a, b) => a.anio - b.anio);
    vstack(el, data, keys, { aria: 'OPEX anual por componente para ' + F3.sel.aci, unit: 'M COP', h: 300 });
  });

  dash.draw('opexcomp-chart', (el) => {
    if (!F3.guard(el, ['opex_comp'])) return;
    const rows = F3.rows('opex_comp').map((r) => ({ label: r.componente, parts: { 'Promedio anual': +r.cop_promedio_anual_3aci } })).sort((a, b) => b.parts['Promedio anual'] - a.parts['Promedio anual']);
    hstack(el, rows, ['Promedio anual'], { aria: 'OPEX promedio anual por componente', unit: 'M COP/año', rowH: 30 });
  });

  dash.draw('reinv-chart', (el) => {
    if (!F3.guard(el, ['reinversiones'])) return;
    el.replaceChildren();
    const C = F3.colors();
    const d = F3.rows('reinversiones');
    const evs = Array.from(new Set(d.map((r) => r.evento)));
    const w = W(el), h = evs.length * 34 + 30;
    const svg = base(el, h, 'Calendario de reinversiones por año');
    const ml = Math.min(w * 0.45, measure(svg, evs) + 10);
    const x = d3.scaleLinear().domain([0, 100]).range([ml, w - 10]);
    const y = d3.scaleBand().domain(evs).range([0, h - 24]).padding(0.3);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 24})`).call(d3.axisBottom(x).ticks(Math.max(4, Math.floor((w - ml) / 60))).tickSize(-(h - 24)));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    const tip = F3.tip(el);
    d.forEach((r) => {
      svg.append('circle').attr('cx', x(+r.anio)).attr('cy', y(r.evento) + y.bandwidth() / 2).attr('r', 4)
        .style('fill', C[evs.indexOf(r.evento) % C.length])
        .on('mousemove', (ev) => tip.show(ev, [`Año ${r.anio}`, r.evento])).on('mouseleave', tip.hide);
    });
  });

  dash.draw('curva-chart', (el) => {
    if (!F3.guard(el, ['curva'])) return;
    const data = F3.rows('curva').map((r) => ({ x: +r.anio, a: +r.cobertura_vegetal, b: +r.estructura_proteccion, c: +r.estructura_alterno_lento }));
    lines(el, data, [
      { k: 'a', name: 'Cobertura vegetal' },
      { k: 'b', name: 'Estructura arbórea (protección)' },
      { k: 'c', name: 'Estructura · alterno lento', dash: '5 4' },
    ], { aria: 'Curvas logísticas de recuperación del manglar, años 0 a 50', ydom: [0, 1], marks: [10, 20, 30], h: 340 });
  });

  dash.draw('flujos-chart', (el) => {
    if (!F3.guard(el, ['flujos_total'])) return;
    el.replaceChildren();
    const d = (dash.data('flujos_total').data || []).filter((r) => r.anio <= F3.sel.h)
      .map((r) => ({ anio: r.anio, CAPEX: r.capex_m, OPEX: r.opex_m, nom: r.nominal_m }));
    vstack(el, d, ['CAPEX', 'OPEX'], { aria: `Flujo anual de costos a ${F3.sel.h} años, millones de COP`, unit: 'M COP', h: 340, line: 'nom', lineName: 'Total nominal' });
  });

  dash.draw('tornado-chart', (el) => {
    if (!F3.guard(el, ['tornado'])) return;
    el.replaceChildren();
    const C = F3.colors();
    const d = F3.rows('tornado').map((r) => ({ p: r.parametro, lo: +r.delta_bajo_cop / 1e6, hi: +r.delta_alto_cop / 1e6, vlo: r.valor_bajo, vhi: r.valor_alto }));
    const w = W(el), h = d.length * 30 + 34;
    const svg = base(el, h, 'Tornado de sensibilidad del VP de costos a 50 años');
    const ml = Math.min(w * 0.48, measure(svg, d.map((r) => r.p)) + 10);
    const ext = d3.max(d, (r) => Math.max(Math.abs(r.lo), Math.abs(r.hi))) || 1;
    const x = d3.scaleLinear().domain([-ext, ext]).nice().range([ml, w - 12]);
    const y = d3.scaleBand().domain(d.map((r) => r.p)).range([0, h - 26]).padding(0.25);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((w - ml) / 90))).tickSize(-(h - 26)).tickFormat((v) => (v > 0 ? '+' : '') + F3.n0(v)));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 0).attr('y2', h - 26).style('stroke', 'var(--cds-chart-reference)');
    const tip = F3.tip(el);
    d.forEach((r) => {
      [['lo', r.lo, r.vlo, C[0]], ['hi', r.hi, r.vhi, C[1 % C.length]]].forEach(([k, v, pv, col]) => {
        svg.append('rect').attr('x', x(Math.min(0, v))).attr('width', Math.abs(x(v) - x(0))).attr('y', y(r.p)).attr('height', y.bandwidth())
          .style('fill', col)
          .on('mousemove', (ev) => tip.show(ev, [r.p, `Valor ${k === 'lo' ? 'bajo' : 'alto'}: ${pv}`, `Cambio en el VP: ${(v > 0 ? '+' : '') + F3.n0(v)} M COP`]))
          .on('mouseleave', tip.hide);
      });
    });
    F3.legend(el, [['Valor bajo del parámetro', C[0]], ['Valor alto del parámetro', C[1 % C.length]]]);
  });

  dash.draw('esc-chart', (el) => {
    if (!F3.guard(el, ['escenarios'])) return;
    const d = F3.rows('escenarios');
    const keys = Array.from(new Set(d.map((r) => r.escenario)));
    const hs = Array.from(new Set(d.map((r) => r.horizonte)));
    el.replaceChildren();
    const C = F3.colors();
    const w = W(el), h = 260;
    const svg = base(el, h, 'VP de costos en escenario puntual y alterno por horizonte');
    const maxV = d3.max(d, (r) => +r.vp_res1092_cop / 1e6);
    const y = d3.scaleLinear().domain([0, maxV]).nice().range([h - 26, 14]);
    const ml = measure(svg, y.ticks(5).map(F3.n0)) + 12;
    const x0 = d3.scaleBand().domain(hs).range([ml, w - 8]).padding(0.25);
    const x1 = d3.scaleBand().domain(keys).range([0, x0.bandwidth()]).padding(0.08);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(w - ml - 8)).tickFormat(F3.n0));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x0).tickFormat((v) => v + ' años').tickSizeOuter(0));
    const tip = F3.tip(el);
    d.forEach((r) => {
      const v = +r.vp_res1092_cop / 1e6;
      const xx = x0(r.horizonte) + x1(r.escenario);
      svg.append('rect').attr('x', xx).attr('width', x1.bandwidth()).attr('y', y(v)).attr('height', y(0) - y(v))
        .style('fill', C[keys.indexOf(r.escenario) % C.length])
        .on('mousemove', (ev) => tip.show(ev, [`${r.escenario} · ${r.horizonte} años`, `VP: ${F3.n0(v)} M COP`])).on('mouseleave', tip.hide);
      svg.append('text').attr('class', 'vlabel').attr('x', xx + x1.bandwidth() / 2).attr('y', y(v) - 4).attr('text-anchor', 'middle').text(F3.n0(v));
    });
    F3.legend(el, keys.map((k, j) => [k, C[j % C.length]]));
  });

  dash.draw('mc-chart', (el) => {
    if (!F3.guard(el, ['mc_hist', 'mc_pct'])) return;
    el.replaceChildren();
    const C = F3.colors();
    const d = F3.rows('mc_hist').map((r) => ({ a: +r.desde_cop / 1e6, b: +r.hasta_cop / 1e6, n: +r.frecuencia }));
    const pc = Object.fromEntries(F3.rows('mc_pct').map((r) => [r.estadistico, +r.vp_res1092_cop / 1e6]));
    const w = W(el), h = 260;
    const svg = base(el, h, 'Distribución Monte Carlo del VP de costos a 50 años');
    const y = d3.scaleLinear().domain([0, d3.max(d, (r) => r.n)]).nice().range([h - 26, 22]);
    const ml = measure(svg, y.ticks(4).map(F3.n0)) + 12;
    const x = d3.scaleLinear().domain([Math.min(d[0].a, pc.Puntual), d[d.length - 1].b]).range([ml, w - 12]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(4).tickSize(-(w - ml - 12)).tickFormat(F3.n0));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((w - ml) / 80))).tickFormat(F3.n0));
    const tip = F3.tip(el);
    d.forEach((r) => {
      svg.append('rect').attr('x', x(r.a)).attr('width', Math.max(0, x(r.b) - x(r.a) - 1)).attr('y', y(r.n)).attr('height', y(0) - y(r.n))
        .style('fill', C[0])
        .on('mousemove', (ev) => tip.show(ev, [`${F3.n0(r.a)}–${F3.n0(r.b)} M COP`, `${F3.n0(r.n)} iteraciones`])).on('mouseleave', tip.hide);
    });
    [['P10', pc.P10], ['P50', pc.P50], ['P90', pc.P90], ['Puntual', pc.Puntual]].forEach(([k, v], i) => {
      if (v == null) return;
      svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', 14).attr('y2', h - 26)
        .style('stroke', k === 'Puntual' ? C[1 % C.length] : 'var(--cds-chart-reference)').attr('stroke-dasharray', k === 'Puntual' ? null : '4 3').attr('stroke-width', k === 'Puntual' ? 2 : 1);
      svg.append('text').attr('x', x(v) + 3).attr('y', 10 + (i % 2) * 10).text(`${k} ${F3.n0(v)}`);
    });
    F3.legend(el, [['Frecuencia (M COP en el eje)', C[0]], ['Estimación puntual', C[1 % C.length]]]);
  });
})();
