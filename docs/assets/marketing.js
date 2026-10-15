/* Marketing campaign dashboard (Bank Marketing, bank-additional-full, 41,176 clients).
   All numbers are computed in the browser from data/marketing.json. The year of each month is
   inferred from row order (the source file has month only); see docs/metrics-dictionary.md. */
(async function () {
  'use strict';
  const { el, fmt } = Dash;
  document.getElementById('hdr').replaceWith(Dash.header({
    title: 'Marketing campaigns',
    intro: 'Phone campaigns of a Portuguese bank, May 2008 to November 2010. Conversion = the client subscribed to a term deposit.',
    current: 'marketing.html',
  }));
  const app = document.getElementById('app');
  let D;
  try { D = await Dash.loadJSON('data/marketing.json'); } catch (err) { Dash.showError(app, err); return; }

  const n = D.y.length, months = D.months, nM = months.length, dims = D.dims;
  const MIN_N = 50, MIN_MONTH = 100, MIN_CELL = 30, MAX_ATT = 6;
  const LABEL = { job: 'Job', age: 'Age band', education: 'Education', channel: 'Contact channel', prior: 'Outcome of earlier campaign', housing: 'Housing loan', loan: 'Personal loan' };
  const FILTER_DIMS = ['channel', 'age', 'job', 'prior'];
  const DRIVERS = ['prior', 'job', 'age', 'education', 'channel', 'housing', 'loan'];
  const ORDERED = ['age'];
  const att = D.att.map((a) => Math.min(a, MAX_ATT));
  const state = { f: {}, from: 0, to: nM - 1, month: null, driver: 'prior' };
  const overall = D.y.reduce((a, b) => a + b, 0) / n;

  app.replaceChildren(); app.removeAttribute('aria-busy');
  const filtersEl = el('div', { class: 'filters', role: 'group', 'aria-label': 'Filters' });
  const chipsEl = el('div', { class: 'chips', 'aria-live': 'polite' });
  const tilesEl = el('div', { class: 'tiles' });
  const gridA = el('div', { class: 'grid two' });
  const gridB = el('div', { class: 'grid two' });
  const foot = el('div', { class: 'footnote' },
    el('p', {}, 'Definitions: conversion rate = converted clients / clients contacted; contacts per conversion = contact attempts (sum of the "campaign" column) / converted clients. See docs/metrics-dictionary.md. There is no cost data, so there is no cost-per-acquisition KPI.'),
    el('p', {}, 'Source: Bank Marketing (bank-additional-full), UCI Machine Learning Repository, CC BY 4.0 (Moro, Rita and Cortez, 2014). 12 exact duplicate rows were removed. The file gives month and weekday only; the year is inferred from row order (the UCI documentation says rows are ordered by date). The call-duration column is not used because it is only known after the call. Months with fewer than ' + MIN_MONTH + ' clients are drawn as hollow markers.'));
  const seen = new Set(D.m);
  const gaps = months.filter((m, i) => !seen.has(i)).map((m) => fmt.month(m));
  foot.append(el('p', {}, 'Months with no records in the file (shown as zero clients and a gap in the rate): ' + (gaps.length ? gaps.join(', ') : 'none') + '.'));
  app.append(filtersEl, chipsEl, tilesEl, gridA, gridB, foot);

  const monthOpts = months.map((m, i) => ({ v: String(i), l: fmt.month(m) }));
  const fFrom = Dash.select({ label: 'From month', options: monthOpts, value: '0', onChange: (v) => { state.from = +v; if (state.to < state.from) state.to = state.from; clampMonth(); update(); } });
  const fTo = Dash.select({ label: 'To month', options: monthOpts, value: String(nM - 1), onChange: (v) => { state.to = +v; if (state.from > state.to) state.from = state.to; clampMonth(); update(); } });
  filtersEl.append(fFrom.root, fTo.root);
  const selects = {};
  for (const key of FILTER_DIMS) {
    selects[key] = Dash.select({ label: LABEL[key], options: [{ v: '-1', l: 'All' }, ...dims[key].levels.map((l, i) => ({ v: String(i), l }))], value: '-1', onChange: (v) => setFilter(key, +v < 0 ? null : +v) });
    filtersEl.append(selects[key].root);
  }
  const reset = el('button', { class: 'btn', type: 'button' }, 'Reset filters');
  reset.addEventListener('click', () => { Object.assign(state, { f: {}, from: 0, to: nM - 1, month: null }); update(); });
  filtersEl.append(reset);
  function clampMonth() { if (state.month !== null && (state.month < state.from || state.month > state.to)) state.month = null; }
  function setFilter(key, level) { if (level === null) delete state.f[key]; else state.f[key] = level; update(); }

  const tRate = Dash.tile(tilesEl, { label: 'Conversion rate', hero: true });
  const tClients = Dash.tile(tilesEl, { label: 'Clients contacted' });
  const tConv = Dash.tile(tilesEl, { label: 'Conversions' });
  const tAtt = Dash.tile(tilesEl, { label: 'Contact attempts' });
  const tCpc = Dash.tile(tilesEl, { label: 'Contacts per conversion' });

  const cClients = Dash.card(gridA, { title: 'Clients contacted per month', sub: 'Click a month to drill into it.', tableName: 'Clients contacted by month' });
  const cRate = Dash.card(gridA, { title: 'Conversion rate by month', sub: 'Share of contacted clients who converted. Hollow markers: fewer than ' + MIN_MONTH + ' clients that month.', tableName: 'Conversion rate by month' });
  const driverSel = Dash.select({ label: 'Break down by', options: DRIVERS.map((k) => ({ v: k, l: LABEL[k] })), value: state.driver, onChange: (v) => { state.driver = v; update(); } });
  driverSel.root.style.flexDirection = 'row'; driverSel.root.style.alignItems = 'center'; driverSel.root.style.gap = '6px';
  const cDriver = Dash.card(gridB, { title: 'Conversion by segment', sub: '', tools: [driverSel.root], tableName: 'Conversion by segment' });
  const cAtt = Dash.card(gridB, { title: 'Conversion by number of contacts', sub: 'Contact attempts made to the client in this campaign (6 means 6 or more).', tableName: 'Conversion by contact attempts' });
  const cHeat = Dash.card(app, { title: 'Earlier-campaign outcome by number of contacts', sub: 'Conversion rate per cell; cells under ' + MIN_CELL + ' clients are greyed out.', tableName: 'Outcome by contacts' });
  app.insertBefore(cHeat.root, foot);
  const clientsChart = Dash.lineChart(cClients.chart), rateChart = Dash.lineChart(cRate.chart);
  const driverChart = Dash.barChart(cDriver.chart), attChart = Dash.columnChart(cAtt.chart), heat = Dash.heatmap(cHeat.chart);

  const okDims = (i, skip) => { for (const k in state.f) { if (skip && skip.includes(k)) continue; if (dims[k].codes[i] !== state.f[k]) return false; } return true; };

  function update() {
    const clients = new Array(nM).fill(0), conv = new Array(nM).fill(0);
    let cl = 0, cv = 0, tries = 0;
    for (let i = 0; i < n; i++) {
      if (!okDims(i)) continue;
      const m = D.m[i];
      clients[m]++; conv[m] += D.y[i];
      if (m >= state.from && m <= state.to) { cl++; cv += D.y[i]; tries += D.att[i]; }
    }
    const rate = cl ? cv / cl : null;
    tRate.set(rate === null ? 'n/a' : fmt.pct(rate), cl ? 'Overall in the dataset: ' + fmt.pct(overall) : 'No clients match');
    tClients.set(fmt.int(cl), 'Rows in scope');
    tConv.set(fmt.int(cv), 'Subscribed (y = yes)');
    tAtt.set(fmt.int(tries), 'Sum of the campaign column');
    tCpc.set(cv ? fmt.dec(tries / cv, 1) : 'n/a', 'Attempts / conversions');

    for (const k of FILTER_DIMS) selects[k].sel.value = state.f[k] === undefined ? '-1' : String(state.f[k]);
    fFrom.sel.value = String(state.from); fTo.sel.value = String(state.to);
    driverSel.sel.value = state.driver;
    chipsEl.replaceChildren();
    const chips = Object.keys(state.f).map((k) => [LABEL[k] + ': ' + dims[k].levels[state.f[k]], () => setFilter(k, null)]);
    if (state.month !== null) chips.push(['Drill-down month: ' + fmt.month(months[state.month]), () => { state.month = null; update(); }]);
    if (chips.length) {
      chipsEl.append('Active drill-downs:');
      for (const [text, fn] of chips) {
        const b = el('button', { type: 'button', 'aria-label': 'Remove ' + text }, '×');
        b.addEventListener('click', fn);
        chipsEl.append(el('span', { class: 'chip' }, text, b));
      }
    }

    /* monthly trend */
    const idx = []; for (let m = state.from; m <= state.to; m++) idx.push(m);
    const labels = idx.map((m) => months[m]);
    const rates = idx.map((m) => (clients[m] ? conv[m] / clients[m] : null));
    const low = idx.map((m) => clients[m] < MIN_MONTH);
    const selIdx = state.month === null ? null : state.month - state.from;
    const onSelect = (i) => { state.month = i === null ? null : idx[i]; update(); };
    clientsChart.update({ labels, fmtLabel: fmt.monthShort, series: [{ name: 'Clients contacted', cls: 's1', values: idx.map((m) => clients[m]) }], fmtY: (v) => fmt.int(v), flags: low, selected: selIdx, onSelect, ariaLabel: 'Line chart of clients contacted per month' });
    const solid = rates.map((r, i) => [r, i]).filter((p) => p[0] !== null && !low[p[1]]);
    const marks = solid.length ? [{ i: solid.reduce((b, p) => (p[0] > b[0] ? p : b))[1], text: 'Highest' }] : [];
    rateChart.update({ labels, fmtLabel: fmt.monthShort, series: [{ name: 'Conversion rate', cls: 's1', values: rates }], fmtY: (v) => fmt.pct(v, 0), flags: low, marks, selected: selIdx, onSelect, ariaLabel: 'Line chart of conversion rate by month',
      extra: (i) => [{ label: 'clients', value: fmt.int(clients[idx[i]]) }] });
    const peak = idx.reduce((b, m) => (clients[m] > clients[b] ? m : b), idx[0]);
    cClients.setInsight('Busiest month: ' + fmt.month(months[peak]) + ' with ' + fmt.int(clients[peak]) + ' clients.');
    cRate.setInsight(solid.length ? 'Highest rate among months with at least ' + MIN_MONTH + ' clients: ' + fmt.month(labels[solid.reduce((b, p) => (p[0] > b[0] ? p : b))[1]]) + ' at ' + fmt.pct(solid.reduce((b, p) => (p[0] > b[0] ? p : b))[0]) + '. Months differ in who was called, so this is not a like-for-like trend.' : 'No month in range has at least ' + MIN_MONTH + ' clients.');
    cClients.setTable([{ label: 'Month' }, { label: 'Clients', num: true }], idx.map((m) => [months[m], fmt.int(clients[m])]));
    cRate.setTable([{ label: 'Month' }, { label: 'Clients', num: true }, { label: 'Conversions', num: true }, { label: 'Conversion rate', num: true }], idx.map((m) => [months[m], fmt.int(clients[m]), fmt.int(conv[m]), clients[m] ? fmt.pct(conv[m] / clients[m]) : 'n/a']));

    /* drill scope = selected month or range, plus dimension filters */
    const dFrom = state.month === null ? state.from : state.month, dTo = state.month === null ? state.to : state.month;
    const scopeText = state.month === null ? fmt.month(months[state.from]) + ' to ' + fmt.month(months[state.to]) : fmt.month(months[state.month]);
    const inScope = (i, skip) => D.m[i] >= dFrom && D.m[i] <= dTo && okDims(i, skip);

    const dk = state.driver, lv = dims[dk].levels;
    const cnt = new Array(lv.length).fill(0), cvv = new Array(lv.length).fill(0);
    for (let i = 0; i < n; i++) { if (!inScope(i, [dk])) continue; const c = dims[dk].codes[i]; cnt[c]++; cvv[c] += D.y[i]; }
    let g = lv.map((l, c) => ({ id: c, label: l, n: cnt[c], conv: cvv[c], value: cnt[c] ? cvv[c] / cnt[c] : 0, small: cnt[c] < MIN_N })).filter((d) => d.n > 0);
    if (!ORDERED.includes(dk) && dk !== 'prior') g = g.sort((a, b) => b.value - a.value);
    driverChart.update({ items: g, fmt: (v) => fmt.pct(v), selectedId: state.f[dk] === undefined ? null : state.f[dk], onSelect: (id) => setFilter(dk, id), ref: { value: overall, label: 'Whole dataset ' + fmt.pct(overall) }, max: Math.max(0.5, ...g.map((d) => d.value)), ariaLabel: 'Bar chart of conversion rate by ' + LABEL[dk], valueLabel: 'conversion rate', tipRows: (it) => [{ label: 'converted / clients', value: fmt.int(it.conv) + ' / ' + fmt.int(it.n) }] });
    cDriver.setSub('Conversion rate by ' + LABEL[dk].toLowerCase() + ', ' + scopeText + ', other filters applied. Click a bar to filter. Hatched bars have fewer than ' + MIN_N + ' clients.');
    cDriver.setTable([{ label: LABEL[dk] }, { label: 'Clients', num: true }, { label: 'Converted', num: true }, { label: 'Conversion rate', num: true }], g.map((d) => [d.label, fmt.int(d.n), fmt.int(d.conv), fmt.pct(d.value)]));
    const big = g.filter((d) => !d.small);
    if (big.length > 1) {
      const hi = big.reduce((a, b) => (b.value > a.value ? b : a)), lo = big.reduce((a, b) => (b.value < a.value ? b : a));
      cDriver.setInsight('Among groups with at least ' + MIN_N + ' clients: highest ' + hi.label + ' (' + fmt.pct(hi.value) + ', n = ' + fmt.int(hi.n) + '), lowest ' + lo.label + ' (' + fmt.pct(lo.value) + ', n = ' + fmt.int(lo.n) + '). Groups were not randomly assigned, so these are associations.');
    } else cDriver.setInsight('Too few clients to compare groups in this scope.');

    /* attempts */
    const ac = new Array(MAX_ATT).fill(0), av = new Array(MAX_ATT).fill(0);
    const cells = dims.prior.levels.map(() => Array.from({ length: MAX_ATT }, () => [0, 0]));
    for (let i = 0; i < n; i++) {
      if (!inScope(i, ['prior'])) continue; // the heat map shows every earlier-campaign outcome
      const pr = dims.prior.codes[i], a = att[i] - 1;
      cells[pr][a][0]++; cells[pr][a][1] += D.y[i];
      if (state.f.prior === undefined || state.f.prior === pr) { ac[a]++; av[a] += D.y[i]; }
    }
    const aItems = ac.map((k, a) => ({ id: a, label: a === MAX_ATT - 1 ? MAX_ATT + '+' : String(a + 1), n: k, value: k ? av[a] / k : 0, small: k < MIN_N }));
    attChart.update({ items: aItems, fmt: (v) => fmt.pct(v, 0), fmtAxis: (v) => Math.round(v * 100) + '%', max: 0.3, ariaLabel: 'Column chart of conversion rate by number of contact attempts', valueLabel: 'conversion rate', ref: { value: overall, label: 'Dataset ' + fmt.pct(overall, 0) } });
    cAtt.setTable([{ label: 'Contact attempts' }, { label: 'Clients', num: true }, { label: 'Conversion rate', num: true }], aItems.map((d) => [d.label, fmt.int(d.n), d.n ? fmt.pct(d.value) : 'n/a']));
    const a1 = aItems[0], a6 = aItems[MAX_ATT - 1];
    cAtt.setInsight(a1.n >= MIN_N && a6.n >= MIN_N ? 'Clients contacted once converted at ' + fmt.pct(a1.value) + '; clients contacted ' + MAX_ATT + ' or more times at ' + fmt.pct(a6.value) + '. Clients who were hard to reach get more contacts, so this does not show that extra calls lower conversion.' : 'Too few clients in this scope.');
    const hc = cells.map((row) => row.map(([k, c]) => ({ v: k >= MIN_CELL ? c / k : null, n: k, conv: c, text: k >= MIN_CELL ? String(Math.round((c / k) * 100)) : '' })));
    heat.update({ rowLabels: dims.prior.levels, colLabels: Array.from({ length: MAX_ATT }, (_, a) => (a === MAX_ATT - 1 ? MAX_ATT + '+' : String(a + 1))), cells: hc, domain: [0, 0.7], rowLabelW: 128, cellH: 36, colHead: 'Contact attempts in this campaign (cells show % converted)', ariaLabel: 'Heatmap of conversion rate by earlier-campaign outcome and contact attempts',
      tip: (r, c, cell) => (cell.v === null ? [{ label: '', value: 'Not shown: under ' + MIN_CELL + ' clients' }, { label: 'clients', value: fmt.int(cell.n) }] : [{ label: 'conversion rate', value: fmt.pct(cell.v) }, { label: 'converted / clients', value: fmt.int(cell.conv) + ' / ' + fmt.int(cell.n) }]) });
    const hr = []; hc.forEach((row, r) => row.forEach((cell, c) => hr.push([dims.prior.levels[r], c === MAX_ATT - 1 ? MAX_ATT + '+' : String(c + 1), fmt.int(cell.n), cell.v === null ? 'under ' + MIN_CELL : fmt.pct(cell.v)])));
    cHeat.setTable([{ label: 'Earlier outcome' }, { label: 'Contacts' }, { label: 'Clients', num: true }, { label: 'Conversion rate', num: true }], hr);
    const first = hc[dims.prior.levels.indexOf('Prior: yes')][0];
    cHeat.setInsight(first && first.v !== null ? 'Clients whose earlier campaign succeeded and who were contacted once converted at ' + fmt.pct(first.v) + ' (n = ' + fmt.int(first.n) + ').' : '');
    window.__mkKpis = { cl, cv, tries, rate };
    Dash.announce('Dashboard updated: conversion rate ' + (rate === null ? 'n/a' : fmt.pct(rate)) + ' across ' + fmt.int(cl) + ' clients.');
  }
  update();
})();
