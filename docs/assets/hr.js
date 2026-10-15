/* HR attrition dashboard (Saudi Employee Attrition survey, 1,191 respondents).
   All numbers are computed in the browser from data/hr.json. The survey has no dates, so the
   "cohort-style" view is attrition by tenure band, not a time trend. */
(async function () {
  'use strict';
  const { el, fmt } = Dash;
  document.getElementById('hdr').replaceWith(Dash.header({
    title: 'HR attrition',
    intro: 'Public survey of 1,191 private-sector employees in Saudi Arabia. Attrition rate by sector, satisfaction, tenure, pay and more.',
    current: 'hr.html',
  }));
  const app = document.getElementById('app');
  let D;
  try { D = await Dash.loadJSON('data/hr.json'); } catch (err) { Dash.showError(app, err); return; }

  const n = D.left.length, dims = D.dims, MIN_N = 20;
  const LABEL = {
    sector: 'Sector', gender: 'Gender', age: 'Age band', degree: 'Degree', salary: 'Monthly salary', tenure: 'Tenure at last organisation',
    job_satisfaction: 'Job satisfaction', job_support: 'Job support', work_life_balance: 'Work-life balance', training: 'Training programmes (3 years)',
    overtime_pay: 'Overtime pay', recognition: 'Recognition', fair_promotion: 'Got a deserved promotion', job_stability: 'Job stability', distance: 'Distance to work',
  };
  const FILTER_DIMS = ['sector', 'gender', 'age', 'salary', 'tenure'];
  const DRIVERS = ['sector', 'job_satisfaction', 'tenure', 'training', 'salary', 'age', 'gender', 'degree', 'job_support', 'work_life_balance', 'overtime_pay', 'recognition', 'fair_promotion', 'job_stability', 'distance'];
  const state = { f: {}, driver: 'job_satisfaction' };
  const overall = D.left.reduce((a, b) => a + b, 0) / n;

  app.replaceChildren(); app.removeAttribute('aria-busy');
  const filtersEl = el('div', { class: 'filters', role: 'group', 'aria-label': 'Filters' });
  const chipsEl = el('div', { class: 'chips', 'aria-live': 'polite' });
  const tilesEl = el('div', { class: 'tiles' });
  const gridA = el('div', { class: 'grid two' });
  const gridB = el('div', { class: 'grid' });
  const foot = el('div', { class: 'footnote' },
    el('p', {}, 'Definition: attrition rate = respondents coded Attrition = Yes in the source / respondents. See docs/metrics-dictionary.md.'),
    el('p', {}, 'This is a convenience-sample survey (Alqahtani, Almagrabi and Alharbi, Mendeley Data, CC BY 4.0), so rates describe the respondents, not Saudi employees in general, and differences between groups are associations, not causes. Groups under ' + MIN_N + ' respondents are hatched. The survey has no dates, so there is no time trend; tenure bands play the role of a cohort view.'));
  app.append(filtersEl, chipsEl, tilesEl, gridA, gridB, foot);

  const selects = {};
  for (const key of FILTER_DIMS) {
    const opts = [{ v: '-1', l: 'All' }, ...dims[key].levels.map((l, i) => ({ v: String(i), l }))];
    selects[key] = Dash.select({ label: LABEL[key], options: opts, value: '-1', onChange: (v) => { setFilter(key, +v < 0 ? null : +v); } });
    filtersEl.append(selects[key].root);
  }
  const reset = el('button', { class: 'btn', type: 'button' }, 'Reset filters');
  reset.addEventListener('click', () => { state.f = {}; update(); });
  filtersEl.append(reset);
  function setFilter(key, level) { if (level === null) delete state.f[key]; else state.f[key] = level; update(); }

  const tRate = Dash.tile(tilesEl, { label: 'Attrition rate', hero: true });
  const tN = Dash.tile(tilesEl, { label: 'Respondents' });
  const tLeft = Dash.tile(tilesEl, { label: 'Left the organisation' });
  const tGap = Dash.tile(tilesEl, { label: 'Gap vs all respondents' });

  const driverSel = Dash.select({ label: 'Break down by', options: DRIVERS.map((k) => ({ v: k, l: LABEL[k] })), value: state.driver, onChange: (v) => { state.driver = v; update(); } });
  driverSel.root.style.flexDirection = 'row'; driverSel.root.style.alignItems = 'center'; driverSel.root.style.gap = '6px';
  const cDriver = Dash.card(gridA, { title: 'Attrition rate by driver', sub: 'Click a bar to filter the dashboard to that group.', tools: [driverSel.root], tableName: 'Attrition rate by driver' });
  const cTenure = Dash.card(gridA, { title: 'Attrition by tenure (cohort-style view)', sub: 'Years at the last organisation. Click a column to filter.', tableName: 'Attrition by tenure' });
  const cHeat = Dash.card(gridB, { title: 'Job satisfaction by tenure', sub: 'Attrition rate per cell. Cells under ' + MIN_N + ' respondents are greyed out. The satisfaction and tenure filters are not applied to this view.', tableName: 'Satisfaction by tenure' });
  const driverChart = Dash.barChart(cDriver.chart);
  const tenureChart = Dash.columnChart(cTenure.chart);
  const heatChart = Dash.heatmap(cHeat.chart);

  const rowOk = (i, skip) => { for (const k in state.f) { if (skip && skip.includes(k)) continue; if (dims[k].codes[i] !== state.f[k]) return false; } return true; };
  function group(key, skip) {
    const lv = dims[key].levels, cnt = new Array(lv.length).fill(0), left = new Array(lv.length).fill(0);
    for (let i = 0; i < n; i++) { if (!rowOk(i, skip)) continue; const c = dims[key].codes[i]; cnt[c]++; left[c] += D.left[i]; }
    return lv.map((l, c) => ({ id: c, label: l, n: cnt[c], leavers: left[c], value: cnt[c] ? left[c] / cnt[c] : 0, small: cnt[c] < MIN_N }));
  }

  function update() {
    let cnt = 0, left = 0;
    for (let i = 0; i < n; i++) if (rowOk(i)) { cnt++; left += D.left[i]; }
    const rate = cnt ? left / cnt : null;
    tRate.set(rate === null ? 'n/a' : fmt.pct(rate), cnt ? 'Left / respondents = ' + fmt.int(left) + ' / ' + fmt.int(cnt) : 'No respondents match');
    tN.set(fmt.int(cnt), 'of ' + fmt.int(n) + ' in the survey');
    tLeft.set(fmt.int(left), 'Attrition = Yes');
    if (rate === null) tGap.set('n/a', '');
    else {
      const gap = (rate - overall) * 100;
      if (Math.abs(gap) < 0.05) tGap.set('0.0 pp', 'Same as all respondents (' + fmt.pct(overall) + ')');
      else tGap.set((gap >= 0 ? '+' : '') + gap.toFixed(1) + ' pp', Dash.delta(Math.abs(gap).toFixed(1) + ' pp ' + (gap >= 0 ? 'above' : 'below') + ' all respondents (' + fmt.pct(overall) + ')', gap >= 0, false));
    }
    for (const k of FILTER_DIMS) selects[k].sel.value = state.f[k] === undefined ? '-1' : String(state.f[k]);
    driverSel.sel.value = state.driver;
    chipsEl.replaceChildren();
    const keys = Object.keys(state.f);
    if (keys.length) {
      chipsEl.append('Active filters:');
      for (const k of keys) {
        const text = LABEL[k] + ': ' + dims[k].levels[state.f[k]];
        const b = el('button', { type: 'button', 'aria-label': 'Remove filter ' + text }, '×');
        b.addEventListener('click', () => setFilter(k, null));
        chipsEl.append(el('span', { class: 'chip' }, text, b));
      }
    }

    /* driver bars */
    const dk = state.driver;
    const g = group(dk, [dk]);
    const sorted = ['salary', 'age', 'tenure', 'job_satisfaction', 'job_support', 'work_life_balance', 'training', 'distance'].includes(dk) ? g : [...g].sort((a, b) => b.value - a.value);
    const sel = state.f[dk] === undefined ? null : state.f[dk];
    driverChart.update({
      items: sorted.map((d) => ({ id: d.id, label: d.label, value: d.value, n: d.n, small: d.small, leavers: d.leavers })), fmt: (v) => fmt.pct(v), selectedId: sel,
      ref: { value: overall, label: 'All respondents ' + fmt.pct(overall) }, max: Math.max(0.8, ...sorted.map((d) => d.value)),
      onSelect: (id) => setFilter(dk, id), ariaLabel: 'Bar chart of attrition rate by ' + LABEL[dk], valueLabel: 'attrition rate', tipRows: (it) => [{ label: 'left / respondents', value: it.leavers + ' / ' + it.n }],
    });
    cDriver.setSub('Attrition rate by ' + LABEL[dk].toLowerCase() + ', with the other filters applied. Click a bar to filter the dashboard to that group.');
    cDriver.setTable([{ label: LABEL[dk] }, { label: 'Respondents', num: true }, { label: 'Left', num: true }, { label: 'Attrition rate', num: true }], sorted.map((d) => [d.label, fmt.int(d.n), fmt.int(d.leavers), d.n ? fmt.pct(d.value) : 'n/a']));
    const big = g.filter((d) => !d.small);
    if (big.length > 1) {
      const hi = big.reduce((a, b) => (b.value > a.value ? b : a)), lo = big.reduce((a, b) => (b.value < a.value ? b : a));
      cDriver.setInsight('Among groups of at least ' + MIN_N + ' respondents: highest ' + hi.label + ' (' + fmt.pct(hi.value) + ', n = ' + hi.n + '), lowest ' + lo.label + ' (' + fmt.pct(lo.value) + ', n = ' + lo.n + '). This is an association in survey data, not a cause.');
    } else cDriver.setInsight('Too few respondents to compare groups under the current filters.');

    /* tenure columns */
    const gt = group('tenure', ['tenure']);
    tenureChart.update({
      items: gt.map((d) => ({ id: d.id, label: d.label.replace(' years', ' yrs'), value: d.value, n: d.n, small: d.small, leavers: d.leavers })), fmt: (v) => fmt.pct(v, 0), fmtAxis: (v) => Math.round(v * 100) + '%', max: 0.8,
      selectedId: state.f.tenure === undefined ? null : state.f.tenure, onSelect: (id) => setFilter('tenure', id), ariaLabel: 'Column chart of attrition rate by tenure band', valueLabel: 'attrition rate',
      ref: { value: overall, label: 'All ' + fmt.pct(overall, 0) }, tipRows: (it) => [{ label: 'left / respondents', value: it.leavers + ' / ' + it.n }],
    });
    cTenure.setTable([{ label: 'Tenure' }, { label: 'Respondents', num: true }, { label: 'Left', num: true }, { label: 'Attrition rate', num: true }], gt.map((d) => [d.label, fmt.int(d.n), fmt.int(d.leavers), d.n ? fmt.pct(d.value) : 'n/a']));
    const first = gt[0], rest = gt.filter((d, i) => i > 0 && !d.small);
    cTenure.setInsight(first.n >= MIN_N && rest.length ? 'Under 5 years: ' + fmt.pct(first.value) + ' (n = ' + first.n + '). Longer-tenure groups with at least ' + MIN_N + ' respondents range from ' + fmt.pct(Math.min(...rest.map((d) => d.value))) + ' to ' + fmt.pct(Math.max(...rest.map((d) => d.value))) + '.' : 'Too few respondents for this comparison under the current filters.');

    /* heatmap: satisfaction x tenure */
    const sat = dims.job_satisfaction, ten = dims.tenure;
    const cc = sat.levels.map(() => ten.levels.map(() => [0, 0]));
    for (let i = 0; i < n; i++) { if (!rowOk(i, ['job_satisfaction', 'tenure'])) continue; const c = cc[sat.codes[i]][ten.codes[i]]; c[0]++; c[1] += D.left[i]; }
    const cells = cc.map((row) => row.map(([k, l]) => ({ v: k >= MIN_N ? l / k : null, n: k, left: l, text: k >= MIN_N ? String(Math.round((l / k) * 100)) : '' })));
    heatChart.update({
      rowLabels: sat.levels, colLabels: ten.levels.map((t) => t.replace('Less than 5 years', '<5').replace(' years', '').replace('+', '+')), cells, domain: [0, 0.8], rowLabelW: 96, cellH: 40,
      colHead: 'Years at last organisation (cells show % who left)', ariaLabel: 'Heatmap of attrition rate by job satisfaction and tenure',
      tip: (r, c, cell) => (cell.v === null ? [{ label: '', value: 'Not shown: under ' + MIN_N + ' respondents' }, { label: 'respondents', value: String(cell.n) }] : [{ label: 'attrition rate', value: fmt.pct(cell.v) }, { label: 'left / respondents', value: cell.left + ' / ' + cell.n }]),
    });
    const tRows = []; cells.forEach((row, r) => row.forEach((cell, c) => tRows.push([sat.levels[r], ten.levels[c], fmt.int(cell.n), fmt.int(cell.left), cell.v === null ? 'under ' + MIN_N : fmt.pct(cell.v)])));
    cHeat.setTable([{ label: 'Job satisfaction' }, { label: 'Tenure' }, { label: 'Respondents', num: true }, { label: 'Left', num: true }, { label: 'Attrition rate', num: true }], tRows);
    const shown = cells.flat().filter((c) => c.v !== null);
    cHeat.setInsight(shown.length ? 'Cells shown: ' + shown.length + ' of ' + cells.flat().length + '. Highest: ' + fmt.pct(Math.max(...shown.map((c) => c.v)), 0) + '; lowest: ' + fmt.pct(Math.min(...shown.map((c) => c.v)), 0) + '.' : 'Every cell is under ' + MIN_N + ' respondents with the current filters.');
    window.__hrKpis = { cnt, left, rate };
    Dash.announce('Dashboard updated: attrition rate ' + (rate === null ? 'n/a' : fmt.pct(rate)) + ' across ' + cnt + ' respondents.');
  }
  update();
})();
