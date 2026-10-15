/* Retail sales dashboard (Online Retail II). All numbers are computed in the browser from
   data/retail.json using the definitions in docs/metrics-dictionary.md. */
(async function () {
  'use strict';
  const { el, fmt } = Dash;
  document.getElementById('hdr').replaceWith(Dash.header({
    title: 'Retail sales',
    intro: 'UK online gift retailer, December 2009 to 9 December 2011. Revenue, returns, orders, customers and cohort retention, in GBP.',
    current: 'retail.html',
  }));
  const app = document.getElementById('app');
  let D;
  try { D = await Dash.loadJSON('data/retail.json'); } catch (err) { Dash.showError(app, err); return; }

  const months = D.months, nM = months.length, countries = D.countries, inv = D.invoices, N = inv.m.length;
  const lastMonth = nM - 1;
  const nCust = Math.max(...inv.cu) + 1;
  const MIN_COHORT = 20, MAX_K = 12;
  const state = { country: -1, from: 0, to: nM - 1, who: 'all', month: null };

  /* ---------- layout ---------- */
  app.replaceChildren();
  app.removeAttribute('aria-busy');
  const filtersEl = el('div', { class: 'filters', role: 'group', 'aria-label': 'Filters' });
  const chipsEl = el('div', { class: 'chips', 'aria-live': 'polite' });
  const tilesEl = el('div', { class: 'tiles' });
  const gridA = el('div', { class: 'grid' });
  const gridB = el('div', { class: 'grid two' });
  const gridC = el('div', { class: 'grid two' });
  const gridD = el('div', { class: 'grid' });
  const foot = el('div', { class: 'footnote' },
    el('p', {}, 'Definitions: see docs/metrics-dictionary.md. Gross revenue = sales lines (quantity x unit price) on non-cancelled invoices; returns = cancellation invoices; net = gross minus returns. No cost data exists in the source, so there is no margin KPI.'),
    el('p', {}, 'Source: Online Retail II, UCI Machine Learning Repository, CC BY 4.0 (Chen, 2012). 22% of invoice lines have no customer id; they count as revenue and orders ("guest") but not as customers.'));
  app.append(filtersEl, chipsEl, tilesEl, gridA, gridB, gridC, gridD, foot);

  const countryOpts = [{ v: '-1', l: 'All countries' }, ...countries.map((c, i) => ({ v: String(i), l: c }))];
  const monthOpts = months.map((m, i) => ({ v: String(i), l: fmt.month(m) }));
  const fCountry = Dash.select({ label: 'Country', options: countryOpts, value: '-1', onChange: (v) => { state.country = +v; update(); } });
  const fFrom = Dash.select({ label: 'From month', options: monthOpts, value: '0', onChange: (v) => { state.from = +v; if (state.to < state.from) state.to = state.from; clampMonth(); update(); } });
  const fTo = Dash.select({ label: 'To month', options: monthOpts, value: String(nM - 1), onChange: (v) => { state.to = +v; if (state.from > state.to) state.from = state.to; clampMonth(); update(); } });
  const fWho = Dash.select({ label: 'Customers', options: [{ v: 'all', l: 'All orders' }, { v: 'id', l: 'Identified customers' }, { v: 'guest', l: 'Guest orders (no id)' }], value: 'all', onChange: (v) => { state.who = v; update(); } });
  const reset = el('button', { class: 'btn', type: 'button' }, 'Reset filters');
  reset.addEventListener('click', () => { Object.assign(state, { country: -1, from: 0, to: nM - 1, who: 'all', month: null }); update(); });
  filtersEl.append(fCountry.root, fFrom.root, fTo.root, fWho.root, reset);
  function clampMonth() { if (state.month !== null && (state.month < state.from || state.month > state.to)) state.month = null; }

  /* ---------- tiles ---------- */
  const tNet = Dash.tile(tilesEl, { label: 'Net revenue', hero: true });
  const tGross = Dash.tile(tilesEl, { label: 'Gross revenue' });
  const tRet = Dash.tile(tilesEl, { label: 'Returns value' });
  const tOrders = Dash.tile(tilesEl, { label: 'Orders' });
  const tAov = Dash.tile(tilesEl, { label: 'Average order value' });
  const tCust = Dash.tile(tilesEl, { label: 'Customers (identified)' });
  const tRep = Dash.tile(tilesEl, { label: 'Repeat-customer rate' });

  /* ---------- cards ---------- */
  const cTrend = Dash.card(gridA, { title: 'Net revenue by month', sub: 'Click a month (or press Enter on it) to drill into its countries and products.', tableName: 'Net revenue by month' });
  const cOrders = Dash.card(gridB, { title: 'Orders per month', sub: 'Distinct non-cancelled invoices.', tableName: 'Orders by month' });
  const cAov = Dash.card(gridB, { title: 'Average order value', sub: 'Gross revenue divided by orders, per month.', tableName: 'Average order value by month' });
  const cCountry = Dash.card(gridC, { title: 'Net revenue by country', sub: 'Click a country to filter the whole dashboard.', tableName: 'Net revenue by country' });
  const cProd = Dash.card(gridC, { title: 'Top products', sub: '', tableName: 'Top products' });
  const cCohort = Dash.card(gridD, { title: 'Customer retention by first-order month', sub: 'Share of each cohort that ordered again k months after its first order. Cohort = month of a customer\'s first order in the current country and customer-type scope; month range does not apply.', tableName: 'Cohort retention' });
  const trendChart = Dash.lineChart(cTrend.chart);
  const ordersChart = Dash.lineChart(cOrders.chart);
  const aovChart = Dash.lineChart(cAov.chart);
  const countryChart = Dash.barChart(cCountry.chart);
  const prodChart = Dash.barChart(cProd.chart);
  const cohortChart = Dash.heatmap(cCohort.chart);

  const shortLab = (i) => fmt.monthShort(months[i]);
  const inScope = (i) => (state.country < 0 || inv.c[i] === state.country) &&
    (state.who === 'all' || (state.who === 'id' ? inv.cu[i] >= 0 : inv.cu[i] < 0));

  function update() {
    const monthly = { gross: new Array(nM).fill(0), ret: new Array(nM).fill(0), orders: new Array(nM).fill(0) };
    const byCountry = new Array(countries.length).fill(0);
    const ordersByCust = new Int32Array(nCust);
    const act = new Int32Array(nCust), first = new Int32Array(nCust).fill(-1);
    const drillFrom = state.month === null ? state.from : state.month, drillTo = state.month === null ? state.to : state.month;
    for (let i = 0; i < N; i++) {
      const m = inv.m[i], isRet = inv.k[i] === 1, v = inv.v[i];
      // country bar ignores the country filter (so the reader can switch) but obeys customer type + range/drill
      const whoOk = state.who === 'all' || (state.who === 'id' ? inv.cu[i] >= 0 : inv.cu[i] < 0);
      if (whoOk && m >= drillFrom && m <= drillTo) byCountry[inv.c[i]] += isRet ? -v : v;
      if (!inScope(i)) continue;
      if (isRet) monthly.ret[m] += v;
      else {
        monthly.gross[m] += v; monthly.orders[m] += 1;
        const cu = inv.cu[i];
        if (cu >= 0) {
          act[cu] |= (1 << m);
          if (first[cu] < 0 || m < first[cu]) first[cu] = m;
          if (m >= state.from && m <= state.to) ordersByCust[cu] += 1;
        }
      }
    }
    const idx = []; for (let m = state.from; m <= state.to; m++) idx.push(m);
    const sum = (arr) => idx.reduce((a, m) => a + arr[m], 0);
    const gross = sum(monthly.gross), ret = sum(monthly.ret), orders = sum(monthly.orders), net = gross - ret;
    let custs = 0, rep = 0;
    for (let c = 0; c < nCust; c++) { if (ordersByCust[c] > 0) { custs++; if (ordersByCust[c] >= 2) rep++; } }

    /* tiles */
    tNet.set(fmt.money(net), fmt.moneyFull(net) + ' GBP');
    tGross.set(fmt.money(gross), 'Sales lines on non-cancelled invoices');
    tRet.set(fmt.money(ret), gross > 0 ? fmt.pct(ret / gross) + ' of gross revenue' : 'n/a');
    tOrders.set(fmt.int(orders), 'Distinct invoices');
    tAov.set(orders > 0 ? fmt.money(gross / orders, '£') : 'n/a', 'Gross revenue / orders');
    tCust.set(state.who === 'guest' ? 'n/a' : fmt.int(custs), 'Distinct, with at least one order in range');
    tRep.set(custs > 0 ? fmt.pct(rep / custs) : 'n/a', 'Customers with 2 or more orders in range');

    /* filter chips */
    chipsEl.replaceChildren();
    const chips = [];
    if (state.country >= 0) chips.push(['Country: ' + countries[state.country], () => { state.country = -1; update(); }]);
    if (state.month !== null) chips.push(['Drill-down month: ' + fmt.month(months[state.month]), () => { state.month = null; update(); }]);
    if (chips.length) {
      chipsEl.append('Active drill-downs:');
      for (const [text, fn] of chips) {
        const b = el('button', { type: 'button', 'aria-label': 'Remove ' + text }, '×');
        b.addEventListener('click', fn);
        chipsEl.append(el('span', { class: 'chip' }, text, b));
      }
    }
    fCountry.sel.value = String(state.country); fFrom.sel.value = String(state.from); fTo.sel.value = String(state.to); fWho.sel.value = state.who;

    /* trend */
    const labels = idx.map((m) => months[m]);
    const netSeries = idx.map((m) => monthly.gross[m] - monthly.ret[m]);
    const selIdx = state.month === null ? null : state.month - state.from;
    const partial = idx.map((m) => m === lastMonth);
    const peak = netSeries.reduce((b, v, i) => (v > netSeries[b] ? i : b), 0);
    const marks = [{ i: peak, text: 'Peak ' + fmt.money(netSeries[peak]) }];
    const onSelect = (i) => { state.month = i === null ? null : idx[i]; update(); };
    trendChart.update({ labels, fmtLabel: fmt.monthShort, series: [{ name: 'Net revenue', cls: 's1', values: netSeries }], fmtY: (v) => fmt.money(v), area: true, flags: partial, marks, selected: selIdx, onSelect, ariaLabel: 'Line chart of net revenue by month' });
    const hasPartial = idx.includes(lastMonth);
    cTrend.setInsight('Peak month: ' + fmt.month(labels[peak]) + ' at ' + fmt.moneyFull(netSeries[peak]) + '.' + (hasPartial ? ' The last month (December 2011) is partial: the data ends on 9 December (hollow marker).' : ''));
    cTrend.setTable([{ label: 'Month' }, { label: 'Gross revenue (GBP)', num: true }, { label: 'Returns (GBP)', num: true }, { label: 'Net revenue (GBP)', num: true }],
      idx.map((m) => [months[m], fmt.int(monthly.gross[m]), fmt.int(monthly.ret[m]), fmt.int(monthly.gross[m] - monthly.ret[m])]));
    const ords = idx.map((m) => monthly.orders[m]);
    const aovs = idx.map((m) => (monthly.orders[m] > 0 ? monthly.gross[m] / monthly.orders[m] : null));
    ordersChart.update({ labels, fmtLabel: fmt.monthShort, series: [{ name: 'Orders', cls: 's1', values: ords }], fmtY: (v) => fmt.int(v), flags: partial, selected: selIdx, onSelect, ariaLabel: 'Line chart of orders per month' });
    aovChart.update({ labels, fmtLabel: fmt.monthShort, series: [{ name: 'Average order value', cls: 's1', values: aovs }], fmtY: (v) => fmt.money(v), flags: partial, selected: selIdx, onSelect, ariaLabel: 'Line chart of average order value by month' });
    cOrders.setTable([{ label: 'Month' }, { label: 'Orders', num: true }], idx.map((m) => [months[m], fmt.int(monthly.orders[m])]));
    cAov.setTable([{ label: 'Month' }, { label: 'AOV (GBP)', num: true }], idx.map((m, k) => [months[m], aovs[k] === null ? 'n/a' : aovs[k].toFixed(2)]));
    const ordPeak = ords.reduce((b, v, i) => (v > ords[b] ? i : b), 0);
    cOrders.setInsight('Most orders: ' + fmt.month(labels[ordPeak]) + ' (' + fmt.int(ords[ordPeak]) + ').');
    const aovVals = aovs.map((v, i) => [v, i]).filter((p) => p[0] !== null);
    if (aovVals.length) { const hi = aovVals.reduce((b, p) => (p[0] > b[0] ? p : b)); cAov.setInsight('Highest: ' + fmt.month(labels[hi[1]]) + ' at £' + hi[0].toFixed(2) + '.' + (idx[hi[1]] === lastMonth ? ' (December 2011 is a partial month.)' : '')); } else cAov.setInsight('');

    /* countries */
    const scopeText = state.month === null ? fmt.month(months[state.from]) + ' to ' + fmt.month(months[state.to]) : fmt.month(months[state.month]);
    cCountry.setSub('Net revenue, ' + scopeText + '. Click a country to filter the whole dashboard.');
    const cItems = countries.map((c, i) => ({ id: i, label: c, value: Math.max(0, byCountry[i]), raw: byCountry[i] })).sort((a, b) => b.raw - a.raw);
    const totalC = cItems.reduce((a, d) => a + d.raw, 0);
    countryChart.update({ items: cItems, fmt: (v) => fmt.money(v), selectedId: state.country >= 0 ? state.country : null, onSelect: (id) => { state.country = id === null ? -1 : id; update(); }, ariaLabel: 'Bar chart of net revenue by country', valueLabel: 'net revenue', tipRows: (it) => [{ label: 'share of total', value: totalC > 0 ? fmt.pct(it.raw / totalC) : 'n/a' }] });
    cCountry.setTable([{ label: 'Country' }, { label: 'Net revenue (GBP)', num: true }, { label: 'Share', num: true }], cItems.map((d) => [d.label, fmt.int(d.raw), totalC > 0 ? fmt.pct(d.raw / totalC) : 'n/a']));
    const ukShare = totalC > 0 ? byCountry[countries.indexOf('United Kingdom')] / totalC : null;
    cCountry.setInsight(ukShare === null ? '' : 'United Kingdom share of net revenue in this scope: ' + fmt.pct(ukShare) + '.');

    /* products */
    const pAgg = new Map();
    for (const [p, m, c, rev, units] of D.products.rows) {
      if (m < drillFrom || m > drillTo) continue;
      if (state.country >= 0 && c !== state.country) continue;
      const cur = pAgg.get(p) || { rev: 0, units: 0 };
      cur.rev += rev; cur.units += units; pAgg.set(p, cur);
    }
    const pItems = [...pAgg.entries()].map(([p, a]) => ({ id: p, label: D.products.items[p][1], code: D.products.items[p][0], value: a.rev, units: a.units }))
      .sort((a, b) => b.value - a.value).slice(0, 8);
    cProd.setSub('Gross sales revenue, ' + scopeText + (state.country >= 0 ? ', ' + countries[state.country] : '') + '. Ranked among the 100 best-selling products overall' + (state.who !== 'all' ? '; this panel ignores the customer filter' : '') + '. Returns are not attributed to products.');
    prodChart.update({ items: pItems.map((d) => Object.assign({}, d, { note: d.code })), fmt: (v) => fmt.money(v), ariaLabel: 'Bar chart of top products by gross revenue', valueLabel: 'gross revenue', tipRows: (it) => [{ label: 'units sold', value: fmt.int(it.units) }, { label: 'stock code', value: it.code }] });
    cProd.setTable([{ label: 'Stock code' }, { label: 'Product' }, { label: 'Gross revenue (GBP)', num: true }, { label: 'Units', num: true }], pItems.map((d) => [d.code, d.label, fmt.int(d.value), fmt.int(d.units)]));
    cProd.setInsight(pItems.length ? 'Top product: ' + pItems[0].label + ' (' + fmt.moneyFull(pItems[0].value) + ').' : 'No sales in this scope.');

    /* cohorts */
    const size = new Array(nM).fill(0), back = Array.from({ length: nM }, () => new Array(MAX_K + 1).fill(0));
    for (let c = 0; c < nCust; c++) {
      const f = first[c]; if (f < 0) continue;
      size[f]++;
      for (let k = 0; k <= MAX_K && f + k < nM; k++) if ((act[c] >> (f + k)) & 1) back[f][k]++;
    }
    const rowIdx = []; for (let c = 0; c < nM; c++) if (size[c] > 0) rowIdx.push(c);
    const cells = rowIdx.map((c) => Array.from({ length: MAX_K + 1 }, (_, k) => {
      if (c + k > lastMonth) return null;
      if (size[c] < MIN_COHORT || c + k === lastMonth) return { v: null, n: size[c], text: '', partial: c + k === lastMonth };
      return { v: back[c][k] / size[c], n: size[c], active: back[c][k], text: String(Math.round((back[c][k] / size[c]) * 100)) };
    }));
    cohortChart.update({
      rowLabels: rowIdx.map((c) => fmt.monthShort(months[c])), colLabels: Array.from({ length: MAX_K + 1 }, (_, k) => String(k)),
      cells, domain: [0, 0.6], rowLabelW: 56, cellH: 20, colHead: 'Months since first order (cells show % of cohort active)',
      ariaLabel: 'Heatmap of customer retention by first-order month and months since first order',
      tip: (r, c, cell) => (cell.v === null
        ? [{ label: '', value: cell.partial ? 'Not shown: partial month (data ends 9 Dec 2011)' : 'Not shown: cohort under ' + MIN_COHORT + ' customers' }, { label: 'cohort size', value: fmt.int(cell.n) }]
        : [{ label: 'retained', value: fmt.pct(cell.v) }, { label: 'active customers', value: fmt.int(cell.active) }, { label: 'cohort size', value: fmt.int(cell.n) }]),
    });
    const m1 = cells.map((r) => r[1]).filter((x) => x && x.v !== null).map((x) => x.v);
    cCohort.setInsight(m1.length ? 'Average month-1 retention across the ' + m1.length + ' cohorts shown: ' + fmt.pct(m1.reduce((a, b) => a + b, 0) / m1.length) + '. The last diagonal (December 2011) is excluded because the month is partial.' : (state.who === 'guest' ? 'Guest orders have no customer id, so there are no cohorts.' : 'No cohorts of at least ' + MIN_COHORT + ' customers in this scope.'));
    const tRows = [];
    rowIdx.forEach((c, r) => cells[r].forEach((cell, k) => { if (cell && cell.v !== null) tRows.push([months[c], String(k), fmt.int(cell.n), fmt.pct(cell.v)]); }));
    cCohort.setTable([{ label: 'Cohort month' }, { label: 'Months since', num: true }, { label: 'Cohort size', num: true }, { label: 'Retention', num: true }], tRows);

    window.__retailKpis = { gross, ret, net, orders, custs, rep, aov: orders ? gross / orders : null };
    Dash.announce('Dashboard updated: net revenue ' + fmt.moneyFull(net) + ', ' + fmt.int(orders) + ' orders.');
  }
  update();
})();
