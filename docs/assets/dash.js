/* Shared dashboard toolkit: small SVG charts, KPI tiles, filters, tooltips, data-table views.
   Plain classic script (no modules, no build) so the pages also work from a static host.
   Every chart is keyboard-operable and has a data-table alternative. All text from data is
   inserted with textContent, never innerHTML. */
(function () {
  'use strict';
  const SVGNS = 'http://www.w3.org/2000/svg';

  function el(tag, attrs, ...kids) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') node.className = v;
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v === true ? '' : v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return node;
  }
  function sv(tag, attrs, ...kids) {
    const node = document.createElementNS(SVGNS, tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') node.setAttribute('class', v);
      else if (k.startsWith('on')) node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    }
    for (const kid of kids.flat()) {
      if (kid === null || kid === undefined || kid === false) continue;
      node.append(kid.nodeType ? kid : document.createTextNode(String(kid)));
    }
    return node;
  }

  /* ---------- formatting ---------- */
  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  const fmt = {
    int: (n) => Math.round(n).toLocaleString('en-GB'),
    dec: (n, d = 1) => n.toLocaleString('en-GB', { minimumFractionDigits: d, maximumFractionDigits: d }),
    pct: (x, d = 1) => (x * 100).toFixed(d) + '%',
    money: (n, cur = '£') => {
      const a = Math.abs(n), s = n < 0 ? '-' : '';
      if (a >= 1e6) return s + cur + (a / 1e6).toFixed(a >= 1e7 ? 1 : 2) + 'M';
      if (a >= 1e4) return s + cur + Math.round(a / 1e3) + 'K';
      if (a >= 1e3) return s + cur + (a / 1e3).toFixed(1) + 'K';
      return s + cur + Math.round(a).toLocaleString('en-GB');
    },
    moneyFull: (n, cur = '£') => cur + Math.round(n).toLocaleString('en-GB'),
    month: (ym) => MONTHS[+ym.slice(5, 7) - 1] + ' ' + ym.slice(0, 4),
    monthShort: (ym) => MONTHS[+ym.slice(5, 7) - 1] + " '" + ym.slice(2, 4),
  };

  function niceTicks(max, count = 4) {
    if (!(max > 0)) return [0, 1];
    const raw = max / count;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
    const ticks = [];
    for (let v = 0; v <= max + step * 0.999; v += step) { ticks.push(+v.toFixed(10)); if (v >= max) break; }
    return ticks;
  }

  /* ---------- tooltip + live region ---------- */
  let tipEl = null, liveEl = null;
  function ensureTip() {
    if (!tipEl) {
      tipEl = el('div', { class: 'tooltip', role: 'presentation' });
      document.body.append(tipEl);
      liveEl = el('div', { class: 'sr-only', 'aria-live': 'polite', id: 'live' });
      document.body.append(liveEl);
    }
  }
  /* content: {title, rows:[{label, value, cls}]} */
  function showTip(content, x, y, announce = false) {
    ensureTip();
    tipEl.replaceChildren();
    if (content.title) tipEl.append(el('div', { class: 'tt-title' }, content.title));
    for (const r of content.rows || []) {
      tipEl.append(el('div', { class: 'tt-row' },
        r.cls ? el('span', { class: 'tt-key ' + r.cls, style: 'border-color:' + (r.cls === 's2' ? 'var(--series-2)' : 'var(--series-1)') }) : null,
        el('b', {}, r.value), el('span', { class: 'lab' }, r.label)));
    }
    tipEl.classList.add('on');
    const pad = 12, rect = tipEl.getBoundingClientRect();
    let left = x + pad, top = y + pad;
    if (left + rect.width > window.innerWidth - 8) left = Math.max(8, x - rect.width - pad);
    if (top + rect.height > window.innerHeight - 8) top = Math.max(8, y - rect.height - pad);
    tipEl.style.left = left + 'px';
    tipEl.style.top = top + 'px';
    if (announce) liveEl.textContent = [content.title, ...(content.rows || []).map((r) => r.label + ' ' + r.value)].join(', ');
  }
  function hideTip() { if (tipEl) tipEl.classList.remove('on'); }
  function announce(text) { ensureTip(); liveEl.textContent = ''; setTimeout(() => { liveEl.textContent = text; }, 30); }

  /* ---------- responsive chart host ---------- */
  function host(container, draw) {
    let spec = null, lastW = 0;
    function render() {
      if (!spec) return;
      const w = Math.floor(container.clientWidth);
      if (w < 40) return;
      lastW = w;
      hideTip();
      draw(container, w, spec);
    }
    const ro = new ResizeObserver(() => { if (Math.floor(container.clientWidth) !== lastW) render(); });
    ro.observe(container);
    return { update(next) { spec = next; render(); } };
  }
  function svgRoot(w, h, label, extra) {
    const svg = sv('svg', Object.assign({ viewBox: `0 0 ${w} ${h}`, width: w, height: h, role: 'group', 'aria-label': label }, extra || {}));
    return svg;
  }
  function hatchDef(id) {
    return sv('defs', {}, sv('pattern', { id, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' },
      sv('rect', { width: 6, height: 6, fill: 'var(--surface)' }),
      sv('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: 'var(--ink-3)', 'stroke-width': 2 })));
  }
  let uid = 0;

  /* ---------- line chart ---------- */
  /* spec: {labels, series:[{name, cls:'s1'|'s2', values}], fmtY, fmtLabel, ariaLabel, selected, onSelect,
            flags (array of bool: low-volume points drawn hollow), marks: [{i, text}] direct annotations,
            area: bool, valueTitle} */
  function lineChart(container) {
    let state = { focus: null };
    return host(container, (box, w, spec) => {
      const n = spec.labels.length;
      const h = Math.max(170, Math.min(260, Math.round(w * 0.42)));
      const m = { l: 46, r: 14, t: 14, b: 26 };
      const iw = w - m.l - m.r, ih = h - m.t - m.b;
      const all = spec.series.flatMap((s) => s.values).filter((v) => v !== null && Number.isFinite(v));
      const maxV = Math.max(...all, 0), minV = Math.min(...all, 0);
      const ticks = niceTicks(maxV);
      const top = ticks[ticks.length - 1] || 1;
      const x = (i) => m.l + (n === 1 ? iw / 2 : (i * iw) / (n - 1));
      const y = (v) => m.t + ih - ((v - Math.min(0, minV)) / (top - Math.min(0, minV))) * ih;
      const svg = svgRoot(w, h, spec.ariaLabel, { tabindex: 0, 'aria-describedby': 'kbd-help' });
      for (const t of ticks) {
        svg.append(sv('line', { class: t === 0 ? 'baseline' : 'gridline', x1: m.l, x2: w - m.r, y1: y(t), y2: y(t) }));
        svg.append(sv('text', { class: 'axis-text', x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end' }, spec.fmtY(t)));
      }
      const every = Math.max(1, Math.ceil(n / Math.max(2, Math.floor(iw / 64))));
      spec.labels.forEach((lab, i) => {
        if (i % every === 0 || i === n - 1) {
          if (i === n - 1 && i % every !== 0 && (n - 1 - Math.floor((n - 1) / every) * every) < every / 2) return;
          svg.append(sv('text', { class: 'axis-text', x: x(i), y: h - 8, 'text-anchor': i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle' }, spec.fmtLabel ? spec.fmtLabel(lab) : lab));
        }
      });
      spec.series.forEach((s, si) => {
        const pts = [];
        s.values.forEach((v, i) => { if (v !== null && Number.isFinite(v)) pts.push([x(i), y(v), i]); });
        if (!pts.length) return;
        const d = pts.map((p, k) => (k ? 'L' : 'M') + p[0].toFixed(1) + ' ' + p[1].toFixed(1)).join('');
        if (spec.area && si === 0) {
          svg.append(sv('path', { class: 'area f1', d: d + `L${pts[pts.length - 1][0]} ${y(0)}L${pts[0][0]} ${y(0)}Z` }));
        }
        svg.append(sv('path', { class: 'line ' + s.cls, d }));
        const last = pts[pts.length - 1];
        svg.append(sv('circle', { class: 'dot ' + (s.cls === 's2' ? 'f2' : 'f1'), cx: last[0], cy: last[1], r: 4 }));
      });
      (spec.flags || []).forEach((flag, i) => {
        const s0 = spec.series[0].values[i];
        if (flag && s0 !== null && Number.isFinite(s0)) {
          svg.append(sv('circle', { cx: x(i), cy: y(s0), r: 4, fill: 'var(--surface)', stroke: 'var(--series-1)', 'stroke-width': 2 }));
        }
      });
      for (const mk of spec.marks || []) {
        const v = spec.series[0].values[mk.i];
        if (v === null || !Number.isFinite(v)) continue;
        const px = x(mk.i), py = y(v);
        const anchor = px > w - 90 ? 'end' : px < 90 ? 'start' : 'middle';
        svg.append(sv('circle', { class: 'dot f1', cx: px, cy: py, r: 4 }));
        svg.append(sv('text', { class: 'note-text', x: px, y: Math.max(12, py - 9), 'text-anchor': anchor }, mk.text));
      }
      const sel = sv('line', { class: 'sel', y1: m.t, y2: m.t + ih, display: 'none' });
      const cross = sv('line', { class: 'crosshair', y1: m.t, y2: m.t + ih, display: 'none' });
      const focusDots = sv('g', {});
      svg.append(sel, cross, focusDots);
      function drawSel() {
        if (spec.selected === null || spec.selected === undefined) { sel.setAttribute('display', 'none'); return; }
        sel.setAttribute('display', 'block');
        sel.setAttribute('x1', x(spec.selected)); sel.setAttribute('x2', x(spec.selected));
      }
      drawSel();
      function content(i) {
        return {
          title: spec.fmtLabel ? spec.fmtLabel(spec.labels[i]) : spec.labels[i],
          rows: spec.series.map((s) => ({ cls: s.cls, label: s.name, value: s.values[i] === null || !Number.isFinite(s.values[i]) ? 'n/a' : (s.fmtValue || spec.fmtY)(s.values[i]) })).concat(spec.extra ? spec.extra(i) : []),
        };
      }
      function showAt(i, clientX, clientY, speak) {
        cross.setAttribute('display', 'block'); cross.setAttribute('x1', x(i)); cross.setAttribute('x2', x(i));
        focusDots.replaceChildren();
        spec.series.forEach((s) => {
          const v = s.values[i];
          if (v !== null && Number.isFinite(v)) focusDots.append(sv('circle', { class: 'dot ' + (s.cls === 's2' ? 'f2' : 'f1'), cx: x(i), cy: y(v), r: 5 }));
        });
        showTip(content(i), clientX, clientY, speak);
      }
      function clear() { cross.setAttribute('display', 'none'); focusDots.replaceChildren(); hideTip(); }
      function nearest(evt) {
        const r = svg.getBoundingClientRect();
        const px = ((evt.clientX - r.left) / r.width) * w;
        return Math.max(0, Math.min(n - 1, Math.round(((px - m.l) / iw) * (n - 1))));
      }
      svg.addEventListener('pointermove', (e) => { const i = nearest(e); state.focus = i; showAt(i, e.clientX, e.clientY, false); });
      svg.addEventListener('pointerleave', clear);
      svg.addEventListener('click', (e) => {
        const i = nearest(e);
        if (spec.onSelect) spec.onSelect(spec.selected === i ? null : i);
      });
      svg.addEventListener('keydown', (e) => {
        let i = state.focus === null || state.focus === undefined ? (n - 1) : state.focus;
        if (e.key === 'ArrowRight') i = Math.min(n - 1, i + 1);
        else if (e.key === 'ArrowLeft') i = Math.max(0, i - 1);
        else if (e.key === 'Home') i = 0;
        else if (e.key === 'End') i = n - 1;
        else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); if (spec.onSelect) spec.onSelect(spec.selected === i ? null : i); return; }
        else if (e.key === 'Escape') { clear(); return; }
        else return;
        e.preventDefault();
        state.focus = i;
        const r = svg.getBoundingClientRect();
        showAt(i, r.left + (x(i) / w) * r.width, r.top + (r.height * 0.3), true);
      });
      svg.addEventListener('blur', clear);
      box.replaceChildren(svg);
    });
  }

  /* ---------- horizontal bar chart (label above each bar) ---------- */
  /* spec: {items:[{id,label,value,n,small,note}], fmt, ariaLabel, selectedId, onSelect, ref:{value,label},
            max, valueFmtN, tipRows:(it)=>rows} */
  function barChart(container) {
    return host(container, (box, w, spec) => {
      const rowH = 42, top = spec.ref ? 18 : 4;
      const h = top + spec.items.length * rowH + 4;
      const valueW = 56;
      const bw = w - valueW - 4;
      const max = spec.max || Math.max(...spec.items.map((d) => d.value), 1e-9) * 1.0;
      const svg = svgRoot(w, h, spec.ariaLabel);
      const hid = 'hatch' + (++uid);
      svg.append(hatchDef(hid));
      const anySel = spec.selectedId !== null && spec.selectedId !== undefined;
      spec.items.forEach((it, idx) => {
        const y0 = top + idx * rowH;
        const bar = Math.max(0, (it.value / max) * bw);
        const isSel = anySel && it.id === spec.selectedId;
        const cls = 'bar f1' + (it.small ? ' small' : anySel && !isSel ? ' muted' : '');
        const note = it.note || (it.n !== undefined ? 'n = ' + fmt.int(it.n) : '');
        const maxChars = Math.max(6, Math.floor((w - note.length * 6.2 - 12) / 6.4));
        const label = it.label.length > maxChars ? it.label.slice(0, maxChars - 1) + '…' : it.label;
        const r = Math.min(4, 6);
        const g = sv('g', { class: 'mark', role: 'button', tabindex: 0, 'aria-pressed': isSel ? 'true' : 'false', 'aria-label': `${it.label}: ${spec.fmt(it.value)}${note ? ', ' + note : ''}${it.small ? ', small group' : ''}` },
          sv('rect', { class: 'ring', x: 0, y: y0, width: w, height: rowH - 4, rx: 6 }),
          sv('text', { class: 'lab-text', x: 2, y: y0 + 14 }, label),
          note ? sv('text', { class: 'note-text', x: w - 2, y: y0 + 14, 'text-anchor': 'end' }, note) : null,
          bar > 0 ? sv('path', { class: cls, fill: it.small ? 'url(#' + hid + ')' : null,
            d: bar <= r ? `M2 ${y0 + 20}h${bar}v12h-${bar}z` : `M2 ${y0 + 20}h${bar - r}a${r} ${r} 0 0 1 ${r} ${r}v${12 - 2 * r}a${r} ${r} 0 0 1 -${r} ${r}h-${bar - r}z` }) : null,
          sv('text', { class: 'val-text', x: 2 + bar + 6, y: y0 + 31 }, spec.fmt(it.value)),
          sv('rect', { class: 'hit', x: 0, y: y0, width: w, height: rowH - 2 }));
        const tip = (e, speak) => showTip({ title: it.label, rows: [{ label: spec.valueLabel || 'value', value: spec.fmt(it.value) }].concat(spec.tipRows ? spec.tipRows(it) : [], it.small ? [{ label: '', value: 'Small group: read with care' }] : []) }, e.x, e.y, speak);
        g.addEventListener('pointermove', (e) => tip({ x: e.clientX, y: e.clientY }, false));
        g.addEventListener('pointerleave', hideTip);
        g.addEventListener('focus', () => { const rc = g.getBoundingClientRect(); tip({ x: rc.left + rc.width * 0.5, y: rc.top }, true); });
        g.addEventListener('blur', hideTip);
        const activate = () => { if (spec.onSelect) spec.onSelect(isSel ? null : it.id); };
        g.addEventListener('click', activate);
        g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); } });
        svg.append(g);
      });
      if (spec.ref) {
        const rx = 2 + (spec.ref.value / max) * bw;
        svg.append(sv('line', { class: 'baseline', x1: rx, x2: rx, y1: top - 4, y2: h - 4, 'stroke-width': 1 }));
        svg.append(sv('text', { class: 'note-text', x: Math.min(rx, w - 4), y: 10, 'text-anchor': rx > w - 120 ? 'end' : 'middle' }, spec.ref.label));
      }
      box.replaceChildren(svg);
    });
  }

  /* ---------- column chart (ordered categories) ---------- */
  function wrap2(label) {
    if (label.length <= 9) return [label];
    const words = label.split(' ');
    if (words.length < 2) return [label];
    let best = 1, diff = 1e9;
    for (let k = 1; k < words.length; k++) {
      const d = Math.abs(words.slice(0, k).join(' ').length - words.slice(k).join(' ').length);
      if (d < diff) { diff = d; best = k; }
    }
    return [words.slice(0, best).join(' '), words.slice(best).join(' ')];
  }
  function columnChart(container) {
    return host(container, (box, w, spec) => {
      const n = spec.items.length;
      const m = { l: 40, r: 8, t: 22, b: 40 };
      const h = 230;
      const iw = w - m.l - m.r, ih = h - m.t - m.b;
      const maxV = Math.max(spec.max || 0, ...spec.items.map((d) => d.value), 1e-9);
      const ticks = niceTicks(maxV, 4);
      const topV = ticks[ticks.length - 1];
      const y = (v) => m.t + ih - (v / topV) * ih;
      const slot = iw / n, bwid = Math.min(24, slot - 8);
      const svg = svgRoot(w, h, spec.ariaLabel);
      const hid = 'hatch' + (++uid);
      svg.append(hatchDef(hid));
      for (const t of ticks) {
        svg.append(sv('line', { class: t === 0 ? 'baseline' : 'gridline', x1: m.l, x2: w - m.r, y1: y(t), y2: y(t) }));
        svg.append(sv('text', { class: 'axis-text', x: m.l - 6, y: y(t) + 4, 'text-anchor': 'end' }, spec.fmtAxis ? spec.fmtAxis(t) : spec.fmt(t)));
      }
      if (spec.ref) {
        svg.append(sv('line', { x1: m.l, x2: w - m.r, y1: y(spec.ref.value), y2: y(spec.ref.value), stroke: 'var(--ink-3)', 'stroke-width': 1, 'stroke-dasharray': '0' }));
        svg.append(sv('text', { class: 'note-text', x: w - m.r, y: y(spec.ref.value) - 4, 'text-anchor': 'end' }, spec.ref.label));
      }
      const anySel = spec.selectedId !== null && spec.selectedId !== undefined;
      spec.items.forEach((it, i) => {
        const cx = m.l + slot * i + slot / 2;
        const bh = Math.max(0, ih - (y(it.value) - m.t));
        const x0 = cx - bwid / 2, y0 = y(it.value), r = Math.min(4, bwid / 2, bh);
        const isSel = anySel && it.id === spec.selectedId;
        const cls = 'bar f1' + (it.small ? ' small' : anySel && !isSel ? ' muted' : '');
        const lines = wrap2(it.label);
        const g = sv('g', { class: 'mark', role: 'button', tabindex: 0, 'aria-pressed': isSel ? 'true' : 'false', 'aria-label': `${it.label}: ${spec.fmt(it.value)}, n = ${fmt.int(it.n)}${it.small ? ', small group' : ''}` },
          sv('rect', { class: 'ring', x: m.l + slot * i + 1, y: m.t - 14, width: slot - 2, height: ih + 14 + 36, rx: 6 }),
          bh > 0 ? sv('path', { class: cls, fill: it.small ? 'url(#' + hid + ')' : null, d: `M${x0} ${y0 + bh}v${-(bh - r)}a${r} ${r} 0 0 1 ${r} ${-r}h${bwid - 2 * r}a${r} ${r} 0 0 1 ${r} ${r}v${bh - r}z` }) : null,
          sv('text', { class: 'val-text', x: cx, y: y0 - 6, 'text-anchor': 'middle' }, spec.fmt(it.value)),
          ...lines.map((ln, k) => sv('text', { class: 'axis-text', x: cx, y: h - 24 + k * 12, 'text-anchor': 'middle' }, ln)),
          sv('text', { class: 'axis-text', x: cx, y: h - 24 + lines.length * 12, 'text-anchor': 'middle' }, it.n !== undefined ? 'n=' + fmt.int(it.n) : ''),
          sv('rect', { class: 'hit', x: m.l + slot * i, y: m.t - 14, width: slot, height: ih + 14 + 40 }));
        const tip = (p, speak) => showTip({ title: it.label, rows: [{ label: spec.valueLabel || 'value', value: spec.fmt(it.value) }, { label: 'n', value: fmt.int(it.n) }].concat(spec.tipRows ? spec.tipRows(it) : []) }, p.x, p.y, speak);
        g.addEventListener('pointermove', (e) => tip({ x: e.clientX, y: e.clientY }, false));
        g.addEventListener('pointerleave', hideTip);
        g.addEventListener('focus', () => { const rc = g.getBoundingClientRect(); tip({ x: rc.left + rc.width / 2, y: rc.top }, true); });
        g.addEventListener('blur', hideTip);
        const activate = () => { if (spec.onSelect) spec.onSelect(isSel ? null : it.id); };
        g.addEventListener('click', activate);
        g.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); activate(); } });
        svg.append(g);
      });
      box.replaceChildren(svg);
    });
  }

  /* ---------- heatmap ---------- */
  /* spec: {rowLabels, colLabels, cells[r][c] = null | {v, n, text}, fmt, domain:[lo,hi], ariaLabel, rowHead,
            colHead, rowLabelW, cellH, tip:(r,c,cell)=>rows} */
  function heatmap(container) {
    return host(container, (box, w, spec) => {
      const rows = spec.rowLabels.length, cols = spec.colLabels.length;
      const lw = spec.rowLabelW || 78, top = 34;
      const cw = (w - lw - 2) / cols, ch = spec.cellH || 22;
      const h = top + rows * ch + 26;
      const [lo, hi] = spec.domain;
      const svg = svgRoot(w, h, spec.ariaLabel, { tabindex: 0, 'aria-describedby': 'kbd-help' });
      if (spec.colHead) svg.append(sv('text', { class: 'note-text', x: lw, y: 10 }, spec.colHead));
      const colEvery = Math.max(1, Math.ceil(26 / cw));
      spec.colLabels.forEach((lab, c) => {
        if (c % colEvery === 0) svg.append(sv('text', { class: 'axis-text', x: lw + c * cw + cw / 2, y: top - 6, 'text-anchor': 'middle' }, lab));
      });
      const cellEls = [];
      spec.rowLabels.forEach((lab, r) => {
        svg.append(sv('text', { class: 'axis-text', x: lw - 6, y: top + r * ch + ch / 2 + 4, 'text-anchor': 'end' }, lab));
        cellEls[r] = [];
        spec.cells[r].forEach((cell, c) => {
          if (cell === null || cell === undefined) { cellEls[r][c] = null; return; }
          const t = cell.v === null ? null : Math.max(0, Math.min(1, (cell.v - lo) / (hi - lo || 1)));
          const bin = t === null ? -1 : Math.min(4, Math.floor(t * 5));
          const rect = sv('rect', { class: 'cell', x: lw + c * cw, y: top + r * ch, width: Math.max(1, cw), height: ch,
            style: 'fill: var(' + (bin < 0 ? '--grid' : '--b' + bin) + ')' });
          svg.append(rect);
          if (bin >= 0 && cw >= 26) {
            svg.append(sv('text', { x: lw + c * cw + cw / 2, y: top + r * ch + ch / 2 + 4, 'text-anchor': 'middle', 'font-size': 10.5, style: 'font-family: var(--font); pointer-events:none; fill: var(--bt' + bin + ')' }, cell.text));
          }
          cellEls[r][c] = rect;
        });
      });
      const ly = top + rows * ch + 10, lf = spec.legendFmt || ((v) => Math.round(v * 100) + '%');
      svg.append(sv('text', { class: 'note-text', x: lw, y: ly + 9 }, lf(lo)));
      for (let b = 0; b < 5; b++) svg.append(sv('rect', { x: lw + 30 + b * 18, y: ly, width: 16, height: 11, rx: 2, style: 'fill: var(--b' + b + ')' }));
      svg.append(sv('text', { class: 'note-text', x: lw + 30 + 5 * 18 + 4, y: ly + 9 }, lf(hi) + ' or more'));
      const ring = sv('rect', { fill: 'none', stroke: 'var(--ink)', 'stroke-width': 2, display: 'none', 'pointer-events': 'none' });
      svg.append(ring);
      function rowsFor(r, c, cell) {
        return spec.tip ? spec.tip(r, c, cell) : [{ label: 'value', value: cell.text }];
      }
      function showCell(r, c, px, py, speak) {
        const cell = spec.cells[r][c];
        if (!cell) { hideTip(); ring.setAttribute('display', 'none'); return; }
        ring.setAttribute('display', 'block');
        ring.setAttribute('x', lw + c * cw); ring.setAttribute('y', top + r * ch);
        ring.setAttribute('width', cw); ring.setAttribute('height', ch);
        showTip({ title: spec.rowLabels[r] + ' / ' + spec.colLabels[c], rows: rowsFor(r, c, cell) }, px, py, speak);
      }
      const at = (e) => {
        const rc = svg.getBoundingClientRect();
        const px = ((e.clientX - rc.left) / rc.width) * w, py = ((e.clientY - rc.top) / rc.height) * h;
        return [Math.floor((py - top) / ch), Math.floor((px - lw) / cw)];
      };
      svg.addEventListener('pointermove', (e) => {
        const [r, c] = at(e);
        if (r < 0 || c < 0 || r >= rows || c >= cols) { hideTip(); ring.setAttribute('display', 'none'); return; }
        showCell(r, c, e.clientX, e.clientY, false);
      });
      svg.addEventListener('pointerleave', () => { hideTip(); ring.setAttribute('display', 'none'); });
      let pos = [0, 0];
      svg.addEventListener('keydown', (e) => {
        let [r, c] = pos;
        if (e.key === 'ArrowRight') c = Math.min(cols - 1, c + 1);
        else if (e.key === 'ArrowLeft') c = Math.max(0, c - 1);
        else if (e.key === 'ArrowDown') r = Math.min(rows - 1, r + 1);
        else if (e.key === 'ArrowUp') r = Math.max(0, r - 1);
        else if (e.key === 'Escape') { hideTip(); ring.setAttribute('display', 'none'); return; }
        else return;
        e.preventDefault();
        pos = [r, c];
        const rc = svg.getBoundingClientRect();
        showCell(r, c, rc.left + ((lw + c * cw + cw / 2) / w) * rc.width, rc.top + ((top + r * ch) / h) * rc.height, true);
      });
      svg.addEventListener('blur', () => { hideTip(); ring.setAttribute('display', 'none'); });
      box.replaceChildren(svg);
    });
  }

  /* ---------- tiles, cards, filters ---------- */
  function tile(parent, { label, hero }) {
    const value = el('div', { class: 'value' }, '-');
    const sub = el('div', { class: 'sub' });
    const root = el('div', { class: 'tile' + (hero ? ' hero' : ''), role: 'group', 'aria-label': label }, el('div', { class: 'label' }, label), value, sub);
    parent.append(root);
    return {
      root,
      set(v, s) {
        value.textContent = v;
        sub.replaceChildren();
        if (s) sub.append(s.nodeType ? s : document.createTextNode(s));
      },
    };
  }
  function delta(text, up, good) {
    return el('span', { class: up === good ? 'delta-up' : 'delta-down' }, (up ? '▲ ' : '▼ ') + text);
  }

  function card(parent, { title, sub, tools, cls, tableName }) {
    const chart = el('div', { class: 'chart' });
    const legend = el('div', { class: 'legend', hidden: true });
    const insight = el('p', { class: 'insight' });
    const subEl = el('p', { class: 'sub' }, sub || '');
    const tableWrap = el('div', { class: 'tablewrap', hidden: true });
    const btn = el('button', { class: 'btn', type: 'button', 'aria-expanded': 'false' }, 'Data table');
    const root = el('section', { class: 'card ' + (cls || ''), 'aria-label': title },
      el('div', { class: 'head' }, el('h2', {}, title), el('div', { class: 'tools' }, ...(tools || []), btn)),
      subEl, legend, chart, insight, tableWrap);
    let tableData = null;
    function paintTable() {
      tableWrap.replaceChildren();
      if (!tableData) return;
      const t = el('table', {}, el('caption', { class: 'sr-only' }, tableName || title),
        el('thead', {}, el('tr', {}, ...tableData.cols.map((c) => el('th', { scope: 'col', class: c.num ? 'num' : '' }, c.label)))),
        el('tbody', {}, ...tableData.rows.map((row) => el('tr', {}, ...tableData.cols.map((c, i) => el('td', { class: c.num ? 'num' : '' }, row[i]))))));
      tableWrap.append(t);
    }
    btn.addEventListener('click', () => {
      const open = tableWrap.hidden;
      tableWrap.hidden = !open;
      btn.setAttribute('aria-expanded', String(open));
      btn.textContent = open ? 'Hide data table' : 'Data table';
      if (open) paintTable();
    });
    parent.append(root);
    return {
      root, chart,
      setSub(t) { subEl.textContent = t; },
      setInsight(t) { insight.textContent = t; },
      setLegend(items) {
        legend.replaceChildren();
        legend.hidden = !items || !items.length;
        for (const it of items || []) legend.append(el('span', {}, el('i', { class: it.cls, style: 'border-color:' + it.color }), it.label));
      },
      setTable(cols, rows) { tableData = { cols, rows }; if (!tableWrap.hidden) paintTable(); },
    };
  }

  function select({ label, options, value, onChange, id }) {
    const sel = el('select', { id: id || null });
    for (const o of options) sel.append(el('option', { value: o.v }, o.l));
    sel.value = value;
    sel.addEventListener('change', () => onChange(sel.value));
    return { root: el('label', {}, label, sel), sel };
  }

  /* ---------- theme toggle ---------- */
  function themeButton() {
    let mode = 'auto';
    try { mode = localStorage.getItem('theme') || 'auto'; } catch (e) { mode = 'auto'; }
    const btn = el('button', { class: 'btn', type: 'button' });
    function apply() {
      if (mode === 'auto') document.documentElement.removeAttribute('data-theme');
      else document.documentElement.setAttribute('data-theme', mode);
      btn.textContent = 'Theme: ' + mode;
      try { localStorage.setItem('theme', mode); } catch (e) { /* storage unavailable */ }
    }
    btn.addEventListener('click', () => { mode = mode === 'auto' ? 'light' : mode === 'light' ? 'dark' : 'auto'; apply(); });
    apply();
    return btn;
  }

  function header({ title, intro, current }) {
    const links = [['index.html', 'Overview'], ['retail.html', 'Retail sales'], ['hr.html', 'HR attrition'], ['marketing.html', 'Marketing']];
    return el('header', { class: 'top' },
      el('div', {}, el('h1', {}, title), el('p', {}, intro)),
      el('nav', { class: 'nav', 'aria-label': 'Dashboards' }, ...links.map(([href, text]) => el('a', Object.assign({ href }, current === href ? { 'aria-current': 'page' } : {}), text)), themeButton()));
  }

  async function loadJSON(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error('Could not load ' + url + ' (' + res.status + ')');
    return res.json();
  }
  function showError(parent, err) {
    parent.replaceChildren(el('div', { class: 'error', role: 'alert' },
      el('b', {}, 'The dashboard data could not be loaded. '),
      'Serve the docs folder over HTTP (for example, run `make serve` and open http://localhost:8000/). Details: ' + err.message));
  }

  window.Dash = { el, sv, fmt, niceTicks, lineChart, barChart, columnChart, heatmap, tile, card, select, delta, header, loadJSON, showError, announce, hideTip };
})();
