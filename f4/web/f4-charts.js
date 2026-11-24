// ---------- gráficos ----------
(function () {
  const F4 = window.F4;
  const W = (el) => Math.max(280, el.clientWidth || 600);
  function measure(svg, labels) {
    const t = svg.append('text').attr('class', 'tmp');
    let m = 0;
    labels.forEach((l) => { t.text(l); m = Math.max(m, t.node().getComputedTextLength() || String(l).length * 6.5); });
    t.remove();
    return m;
  }
  const base = (el, h, label) => d3.select(el).append('svg').attr('width', '100%').attr('height', h).attr('role', 'img').attr('aria-label', label);

  // barras horizontales simples: rows=[{label, v, color?}]
  function hbars(el, rows, opt) {
    const C = F4.colors();
    const w = W(el), rowH = opt.rowH || 30, h = rows.length * rowH + 30;
    const svg = base(el, h, opt.aria);
    const ml = Math.min(w * 0.45, measure(svg, rows.map((r) => r.label)) + 10);
    const x = d3.scaleLinear().domain([0, d3.max(rows, (r) => r.v) || 1]).nice().range([ml, w - 50]);
    const y = d3.scaleBand().domain(rows.map((r) => r.label)).range([0, h - 24]).padding(0.28);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 24})`).call(d3.axisBottom(x).ticks(Math.max(2, Math.floor((w - ml) / 90))).tickSize(-(h - 24)).tickFormat(opt.tick || F4.n0));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    const tip = F4.tip(el);
    rows.forEach((r, i) => {
      svg.append('rect').attr('x', x(0)).attr('y', y(r.label)).attr('height', y.bandwidth()).attr('width', Math.max(0, x(r.v) - x(0)))
        .style('fill', r.color || C[0])
        .on('mousemove', (ev) => tip.show(ev, [r.label, `${(opt.fmt || F4.n0)(r.v)} ${opt.unit || ''}`])).on('mouseleave', tip.hide);
      svg.append('text').attr('class', 'vlabel').attr('x', x(r.v) + 6).attr('y', y(r.label) + y.bandwidth() / 2).attr('dy', '0.35em').text((opt.fmt || F4.n0)(r.v));
    });
  }

  // barras verticales agrupadas: groups (eje x), keys (series), get(g,k)
  function gbars(el, groups, keys, get, opt) {
    const C = F4.colors();
    const w = W(el), h = opt.h || 280;
    const svg = base(el, h, opt.aria);
    const maxV = d3.max(groups, (g) => d3.max(keys, (k) => get(g, k) || 0)) || 1;
    const y = d3.scaleLinear().domain([0, maxV]).nice().range([h - 26, 16]);
    const ml = measure(svg, y.ticks(5).map(opt.tick || F4.n1)) + 12;
    const x0 = d3.scaleBand().domain(groups).range([ml, w - 8]).padding(0.22);
    const x1 = d3.scaleBand().domain(keys).range([0, x0.bandwidth()]).padding(0.08);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(w - ml - 8)).tickFormat(opt.tick || F4.n1));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x0).tickFormat(opt.xfmt || ((d) => d)).tickSizeOuter(0));
    const tip = F4.tip(el);
    groups.forEach((g) => keys.forEach((k, j) => {
      const val = get(g, k);
      if (val == null || isNaN(val)) return;
      const xx = x0(g) + x1(k);
      svg.append('rect').attr('x', xx).attr('width', x1.bandwidth()).attr('y', y(val)).attr('height', Math.max(0, y(0) - y(val)))
        .style('fill', C[j % C.length])
        .on('mousemove', (ev) => tip.show(ev, [`${(opt.xfmt || ((d) => d))(g)} · ${k}`, `${(opt.fmt || F4.n1)(val)} ${opt.unit || ''}`])).on('mouseleave', tip.hide);
      if (x1.bandwidth() > 22) svg.append('text').attr('class', 'vlabel').attr('x', xx + x1.bandwidth() / 2).attr('y', y(val) - 4).attr('text-anchor', 'middle').text((opt.fmt || F4.n1)(val));
    }));
    F4.legend(el, keys.map((k, j) => [k, C[j % C.length]]));
  }

  // líneas: data=[{x,...}], series=[{k,name,dash}]
  function lines(el, data, series, opt) {
    const C = F4.colors();
    const w = W(el), h = opt.h || 300;
    const svg = base(el, h, opt.aria);
    const ymax = opt.ymax != null ? opt.ymax : d3.max(data, (d) => d3.max(series, (s) => d[s.k])) * 1.05;
    const y = d3.scaleLinear().domain([opt.ymin || 0, Math.max(ymax, ...(opt.hlines || []).map((l) => l.v * 1.08))]).nice().range([h - 28, 10]);
    const ml = measure(svg, y.ticks(5).map(opt.tick || F4.n2)) + 12;
    const x = d3.scaleLinear().domain(d3.extent(data, (d) => d.x)).range([ml, w - 14]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(5).tickSize(-(w - ml - 14)).tickFormat(opt.tick || F4.n2));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 28})`).call(d3.axisBottom(x).ticks(Math.max(4, Math.floor((w - ml) / 70))).tickFormat(opt.xtick || d3.format('d')));
    (opt.hlines || []).forEach((l) => {
      svg.append('line').attr('x1', ml).attr('x2', w - 14).attr('y1', y(l.v)).attr('y2', y(l.v)).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '4 3');
      svg.append('text').attr('x', w - 16).attr('y', y(l.v) - 4).attr('text-anchor', 'end').text(l.label);
    });
    (opt.marks || []).forEach((m) => {
      svg.append('line').attr('x1', x(m)).attr('x2', x(m)).attr('y1', 10).attr('y2', h - 28).style('stroke', 'var(--cds-chart-reference)').attr('stroke-dasharray', '3 3');
      svg.append('text').attr('x', x(m) + 4).attr('y', 20).text((opt.markLabel || ((v) => 't=' + v))(m));
    });
    series.forEach((s, j) => {
      svg.append('path').datum(data.filter((d) => d[s.k] != null)).attr('fill', 'none').style('stroke', s.color || C[j % C.length]).attr('stroke-width', 2)
        .attr('stroke-dasharray', s.dash || null).attr('d', d3.line().x((d) => x(d.x)).y((d) => y(d[s.k])));
    });
    const tip = F4.tip(el);
    const guide = svg.append('line').style('stroke', 'var(--cds-chart-reference)').attr('y1', 10).attr('y2', h - 28).attr('opacity', 0);
    svg.append('rect').attr('x', ml).attr('y', 0).attr('width', Math.max(0, w - ml - 14)).attr('height', h - 28).attr('fill', 'transparent')
      .on('mousemove', (ev) => {
        const [mx] = d3.pointer(ev);
        const xv = x.invert(mx);
        const d = data.reduce((a, b) => (Math.abs(b.x - xv) < Math.abs(a.x - xv) ? b : a));
        guide.attr('x1', x(d.x)).attr('x2', x(d.x)).attr('opacity', 1);
        tip.show(ev, [(opt.xlabel || ((v) => `x = ${v}`))(d)].concat(series.map((s) => `${s.name}: ${(opt.fmt || F4.n2)(d[s.k])} ${opt.unit || ''}`)));
      })
      .on('mouseleave', () => { guide.attr('opacity', 0); tip.hide(); });
    F4.legend(el, series.map((s, j) => [s.name, s.color || C[j % C.length]]));
  }

  // cronograma: rows=[{label, a, b, tipo, estado}]
  function gantt(el, rows, opt) {
    const C = F4.colors();
    const w = W(el), rowH = 28, h = rows.length * rowH + 34;
    const svg = base(el, h, opt.aria);
    const ml = Math.min(w * 0.42, measure(svg, rows.map((r) => r.label)) + 12);
    const x = d3.scaleUtc().domain([d3.min(rows, (r) => r.a), d3.max(rows, (r) => r.b)]).nice().range([ml, w - 14]);
    const y = d3.scaleBand().domain(rows.map((r) => r.label)).range([0, h - 26]).padding(0.3);
    const mes = d3.utcFormat('%b %Y');
    const es = { Jan: 'ene', Feb: 'feb', Mar: 'mar', Apr: 'abr', May: 'may', Jun: 'jun', Jul: 'jul', Aug: 'ago', Sep: 'sep', Oct: 'oct', Nov: 'nov', Dec: 'dic' };
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 26})`)
      .call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((w - ml) / 80))).tickSize(-(h - 26)).tickFormat((d) => mes(d).replace(/^[A-Za-z]{3}/, (m) => es[m] || m)));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    const tip = F4.tip(el);
    const col = (r) => (r.estado === 'En curso' || r.estado === 'Solicitado' ? C[1 % C.length] : C[0]);
    rows.forEach((r) => {
      const cy = y(r.label) + y.bandwidth() / 2;
      const lines = [r.label, r.a.getTime() === r.b.getTime() ? F4.fmtD(r.a) : `${F4.fmtD(r.a)} → ${F4.fmtD(r.b)}`, `Estado: ${r.estado}`].concat(r.extra ? [r.extra] : []);
      let mark;
      if (r.a.getTime() === r.b.getTime()) {
        const s = Math.min(8, y.bandwidth() / 2 + 2);
        mark = svg.append('path').attr('d', `M${x(r.a)},${cy - s}L${x(r.a) + s},${cy}L${x(r.a)},${cy + s}L${x(r.a) - s},${cy}Z`).style('fill', 'var(--color-fg)');
      } else {
        mark = svg.append('rect').attr('x', x(r.a)).attr('width', Math.max(3, x(r.b) - x(r.a))).attr('y', y(r.label)).attr('height', y.bandwidth()).attr('rx', 3).style('fill', col(r));
      }
      mark.on('mousemove', (ev) => tip.show(ev, lines)).on('mouseleave', tip.hide);
    });
    if (opt.hoy) {
      const xh = x(opt.hoy);
      svg.append('line').attr('x1', xh).attr('x2', xh).attr('y1', 0).attr('y2', h - 26).style('stroke', 'var(--cds-chart-status-critical)').attr('stroke-dasharray', '4 3');
      svg.append('text').attr('x', xh + 4).attr('y', 10).text(opt.hoyLabel);
    }
    F4.legend(el, [['Actividad', C[0]], ['En curso / solicitado', C[1 % C.length]], ['Hito (rombo)', 'var(--color-fg)']]);
  }

  const FECHA_TABLERO = F4.parseD('2026-11-22'); // fecha de los estados de este tablero

  // ======== dibujos ========
  dash.draw('estado-chart', (el) => {
    if (!F4.guard(el, ['estado'])) return;
    const order = ['Tenemos', 'Encontrado fuera', 'Generar', 'Solicitado', 'Solicitar', 'Falta'];
    const C = F4.colors();
    const colr = { Tenemos: 'var(--color-ok)', 'Encontrado fuera': 'var(--color-ok)', Generar: 'var(--color-warn)', Solicitado: 'var(--color-warn)', Solicitar: 'var(--color-bad)', Falta: 'var(--color-bad)' };
    const rows = (dash.data('estado').data || []).slice().sort((a, b) => order.indexOf(a.estado) - order.indexOf(b.estado)).map((r) => ({ label: r.estado, v: r.n, color: colr[r.estado] || C[0] }));
    hbars(el, rows, { aria: 'Número de datos de la F4 por estado', unit: 'datos', tick: d3.format('d') });
  });

  dash.draw('gantt-chart', (el) => {
    if (!F4.guard(el, ['hitos'])) return;
    const rows = F4.rows('hitos').map((r) => ({ label: r.nombre, a: F4.parseD(r.inicio), b: F4.parseD(r.fin), estado: r.estado, extra: 'Depende de: ' + r.depende }));
    gantt(el, rows, { aria: 'Cronograma de la Fase 4 con el camino crítico', hoy: FECHA_TABLERO, hoyLabel: '22 nov 2026' });
  });

  dash.draw('bati-chart', (el) => {
    if (!F4.guard(el, ['batimetria'])) return;
    const rows = F4.rows('batimetria').map((r) => ({ label: r.paso, a: F4.parseD(r.inicio), b: F4.parseD(r.fin), estado: r.estado, extra: r.herramientas }));
    gantt(el, rows, { aria: 'Vías y pasos de la batimetría hasta el hito HB.1', hoy: FECHA_TABLERO, hoyLabel: '22 nov 2026' });
  });

  dash.draw('difres-chart', (el) => {
    if (!F4.guard(el, ['diferencial'])) return;
    const d = F4.rows('diferencial').filter((r) => +r.corte === 30);
    const acis = Array.from(new Set(d.map((r) => r.aci)));
    const trs = ['Tr 10', 'Tr 25', 'Tr 50', 'Tr 100'];
    gbars(el, acis, trs, (a, k) => { const r = d.find((x) => x.aci === a && 'Tr ' + x.tr === k); return r ? +r.dif_ola_cm : null; },
      { aria: 'Reducción de la altura de ola por la intervención en t = 30, por ACI y periodo de retorno', unit: 'cm', h: 280 });
  });

  dash.draw('matriz-chart', (el) => {
    if (!F4.guard(el, ['matriz_tot'])) return;
    const d = (dash.data('matriz_tot').data || []);
    const casos = Array.from(new Set(d.map((r) => r.caso)));
    const ops = Array.from(new Set(d.map((r) => r.opcion)));
    gbars(el, casos, ops, (c, o) => { const r = d.find((x) => x.caso === c && x.opcion === o); return r ? r.total : null; },
      { aria: 'Puntaje ponderado de cada opción de modelo según la batimetría disponible', unit: 'puntos (máx. 5)', fmt: F4.n2, tick: F4.n1, h: 260 });
  });

  dash.draw('iota-chart', (el) => {
    if (!F4.guard(el, ['iota_viento', 'calibracion'])) return;
    const C = F4.colors();
    const data = F4.rows('iota_viento').map((r) => ({ x: +r.hora, f: r.fecha, a: +r.v10min_sai_kt, b: +r.v1min_pva_kt }));
    const obs = F4.rows('calibracion').find((r) => r.id === 'C1');
    lines(el, data, [
      { k: 'b', name: 'Providencia · viento 1 min (modelo)' },
      { k: 'a', name: 'San Andrés · viento 10 min (modelo)' },
    ], {
      aria: 'Viento paramétrico de Holland durante Iota en San Andrés y Providencia', h: 320, tick: F4.n0, fmt: F4.n1, unit: 'kt',
      xtick: (v) => (v % 24 === 0 ? `${16 + v / 24} nov` : `${((v % 24) + 24) % 24}h`), xlabel: (d) => d.f,
      hlines: [{ v: 64, label: 'Umbral de huracán (64 kt)' }].concat(obs ? [{ v: +obs.observado, label: `Observado en el aeropuerto de SAI (${F4.n0(+obs.observado)} kt, 10 min)` }] : []),
    });
  });

  dash.draw('forz-chart', (el) => {
    if (!F4.guard(el, ['forzamiento'])) return;
    const d = F4.rows('forzamiento');
    gbars(el, d.map((r) => 'Tr ' + r.tr), ['t = 0', 't = 30', 't = 100'], (g, k) => {
      const r = d.find((x) => 'Tr ' + x.tr === g);
      return r ? +r[{ 't = 0': 'nivel_t0_m', 't = 30': 'nivel_t30_m', 't = 100': 'nivel_t100_m' }[k]] : null;
    }, { aria: 'Nivel del mar de las corridas por periodo de retorno y horizonte de ANM', unit: 'm', fmt: F4.n2, tick: F4.n1, h: 260 });
  });

  dash.draw('cond-chart', (el) => {
    if (!F4.guard(el, ['condicion'])) return;
    const data = F4.rows('condicion').map((r) => ({ x: +r.anio, a: +r.base, b: +r.intervencion }));
    lines(el, data, [{ k: 'a', name: 'Escenario Base' }, { k: 'b', name: 'Escenario de Intervención' }],
      { aria: 'Condición del manglar en cada escenario, años 0 a 50', ymax: 1, marks: [10, 20, 30], h: 280, xlabel: (d) => `Año ${d.x}` });
  });

  dash.draw('perfil-chart', (el) => {
    if (!F4.guard(el, ['perfil'])) return;
    const S = F4.sel;
    const d = F4.rows('perfil').filter((r) => r.aci === S.aciPerfil && +r.tr === S.trPerfil);
    const by = d3.group(d, (r) => +r.x_m);
    const data = Array.from(by, ([x, v]) => ({ x, a: +(v.find((r) => r.escenario === 'Base') || {}).H_m, b: +(v.find((r) => r.escenario === 'Intervención') || {}).H_m })).sort((p, q) => p.x - q.x);
    lines(el, data, [{ k: 'a', name: 'Escenario Base' }, { k: 'b', name: 'Escenario de Intervención' }],
      { aria: `Altura de ola a lo ancho de la franja de manglar en ${S.aciPerfil}, Tr ${S.trPerfil}, t = 30`, h: 280, unit: 'm', xlabel: (p) => `${p.x} m desde el borde` });
  });

  dash.draw('dif-chart', (el) => {
    if (!F4.guard(el, ['diferencial'])) return;
    const d = F4.rows('diferencial').filter((r) => r.aci === F4.sel.aciDif);
    gbars(el, ['Tr 10', 'Tr 25', 'Tr 50', 'Tr 100'], ['t = 10', 't = 20', 't = 30', 't = 50', 't = 100'], (g, k) => {
      const r = d.find((x) => 'Tr ' + x.tr === g && 't = ' + x.corte === k);
      return r ? +r.dif_ola_cm : null;
    }, { aria: `Reducción de la altura de ola por la intervención en ${F4.sel.aciDif}, por Tr y corte`, unit: 'cm', h: 280 });
  });

  dash.draw('prot-chart', (el) => {
    if (!F4.guard(el, ['proteccion'])) return;
    const d = F4.rows('proteccion');
    const acis = Array.from(new Set(d.map((r) => r.aci)));
    gbars(el, acis, ['Tr 10', 'Tr 25', 'Tr 50', 'Tr 100'], (a, k) => { const r = d.find((x) => x.aci === a && 'Tr ' + x.tr === k); return r ? +r.prot_ola_cm : null; },
      { aria: 'Reducción de la altura de ola del manglar actual frente al dominio sin manglar, t = 0, por ACI y periodo de retorno', unit: 'cm', h: 260 });
  });

  dash.draw('tornado-chart', (el) => {
    if (!F4.guard(el, ['tornado'])) return;
    const C = F4.colors();
    const d = F4.rows('tornado').map((r) => ({ p: r.parametro, lo: +r.delta_bajo_cm, hi: +r.delta_alto_cm, vlo: r.valor_bajo, vhi: r.valor_alto }));
    const w = W(el), h = d.length * 30 + 34;
    const svg = base(el, h, 'Tornado de sensibilidad del diferencial de ola');
    const ml = Math.min(w * 0.5, measure(svg, d.map((r) => r.p)) + 10);
    const ext = d3.max(d, (r) => Math.max(Math.abs(r.lo), Math.abs(r.hi))) || 1;
    const x = d3.scaleLinear().domain([-ext, ext]).nice().range([ml, w - 12]);
    const y = d3.scaleBand().domain(d.map((r) => r.p)).range([0, h - 26]).padding(0.25);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((w - ml) / 80))).tickSize(-(h - 26)).tickFormat((v) => (v > 0 ? '+' : '') + F4.n0(v)));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).tickSize(0)).call((g) => g.select('.domain').remove());
    svg.append('line').attr('x1', x(0)).attr('x2', x(0)).attr('y1', 0).attr('y2', h - 26).style('stroke', 'var(--cds-chart-reference)');
    const tip = F4.tip(el);
    d.forEach((r) => {
      [['bajo', r.lo, r.vlo, C[0]], ['alto', r.hi, r.vhi, C[1 % C.length]]].forEach(([k, v, pv, col]) => {
        svg.append('rect').attr('x', x(Math.min(0, v))).attr('width', Math.abs(x(v) - x(0))).attr('y', y(r.p)).attr('height', y.bandwidth()).style('fill', col)
          .on('mousemove', (ev) => tip.show(ev, [r.p, `Valor ${k}: ${pv}`, `Cambio: ${(v > 0 ? '+' : '') + F4.n1(v)} cm`])).on('mouseleave', tip.hide);
      });
    });
    F4.legend(el, [['Valor bajo del parámetro', C[0]], ['Valor alto del parámetro', C[1 % C.length]]]);
  });

  dash.draw('mc-chart', (el) => {
    if (!F4.guard(el, ['mc_hist', 'mc_pct'])) return;
    const C = F4.colors();
    const d = F4.rows('mc_hist').map((r) => ({ a: +r.desde_cm, b: +r.hasta_cm, n: +r.frecuencia }));
    const pc = Object.fromEntries(F4.rows('mc_pct').map((r) => [r.estadistico, +r.dif_ola_cm]));
    const w = W(el), h = 260;
    const svg = base(el, h, 'Distribución Monte Carlo del diferencial de ola');
    const y = d3.scaleLinear().domain([0, d3.max(d, (r) => r.n)]).nice().range([h - 26, 24]);
    const ml = measure(svg, y.ticks(4).map(F4.n0)) + 12;
    const x = d3.scaleLinear().domain([d[0].a, d[d.length - 1].b]).range([ml, w - 12]);
    svg.append('g').attr('class', 'grid').attr('transform', `translate(${ml},0)`).call(d3.axisLeft(y).ticks(4).tickSize(-(w - ml - 12)).tickFormat(F4.n0));
    svg.append('g').attr('class', 'axis').attr('transform', `translate(0,${h - 26})`).call(d3.axisBottom(x).ticks(Math.max(3, Math.floor((w - ml) / 70))).tickFormat(F4.n0));
    const tip = F4.tip(el);
    d.forEach((r) => {
      svg.append('rect').attr('x', x(r.a)).attr('width', Math.max(0, x(r.b) - x(r.a) - 1)).attr('y', y(r.n)).attr('height', y(0) - y(r.n)).style('fill', C[0])
        .on('mousemove', (ev) => tip.show(ev, [`${F4.n1(r.a)}–${F4.n1(r.b)} cm`, `${F4.n0(r.n)} iteraciones`])).on('mouseleave', tip.hide);
    });
    [['P10', pc.P10], ['P50', pc.P50], ['P90', pc.P90], ['Puntual', pc.Puntual]].forEach(([k, v], i) => {
      if (v == null) return;
      svg.append('line').attr('x1', x(v)).attr('x2', x(v)).attr('y1', 16).attr('y2', h - 26)
        .style('stroke', k === 'Puntual' ? C[1 % C.length] : 'var(--cds-chart-reference)').attr('stroke-dasharray', k === 'Puntual' ? null : '4 3').attr('stroke-width', k === 'Puntual' ? 2 : 1);
      svg.append('text').attr('x', x(v) + 3).attr('y', 10 + (i % 2) * 11).text(`${k} ${F4.n1(v)}`);
    });
    F4.legend(el, [['Iteraciones (cm en el eje)', C[0]], ['Estimación puntual', C[1 % C.length]]]);
  });
})();
