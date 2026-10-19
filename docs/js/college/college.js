/* College pages: shared table rendering (search, filters, sort, paging).
   Data comes from /static-football-rankings/data/college/*.json written by
   python_scripts/college/generate_college_site.py */
const COLLEGE_BASE = '/static-football-rankings';
const COLLEGE_DATA = COLLEGE_BASE + '/data/college/';

async function collegeLoad(file) {
  const r = await fetch(COLLEGE_DATA + file, { cache: 'no-cache' });
  if (!r.ok) throw new Error(file + ': ' + r.status);
  return r.json();
}

function collegeFmt(v, kind) {
  if (v === null || v === undefined || v === '') return '';
  if (kind === 'num1') return Number(v).toFixed(1);
  if (kind === 'num2') return Number(v).toFixed(2);
  if (kind === 'pct') return Number(v).toFixed(3).replace(/^0/, '');
  return String(v);
}

function collegeProgramLink(name, slug) {
  if (!slug) return document.createTextNode(name);
  const a = document.createElement('a');
  a.href = COLLEGE_BASE + '/pages/public/college/program.html?team=' + encodeURIComponent(slug);
  a.textContent = name;
  return a;
}

function collegeCoachLink(name, id) {
  if (id === null || id === undefined || id === '') return document.createTextNode(name || '');
  const a = document.createElement('a');
  a.href = COLLEGE_BASE + '/pages/public/college/coach.html?id=' + encodeURIComponent(id);
  a.textContent = name;
  return a;
}

function collegeCoachLinks(td, list) {
  list.forEach((c, i) => {
    if (i) td.appendChild(document.createTextNode(' / '));
    td.appendChild(collegeCoachLink(c[0], c[1]));
  });
}

/* opts: { data: [...rows], columns: [{key,label,fmt,link,num,sortKey}], tableId, pageSize,
           searchKeys: [...], filters: [{id, key, type:'select'|'min', label, default}],
           defaultSort: {key, dir} , countId } */
function collegeTable(opts) {
  const state = { sort: opts.defaultSort || null, page: 1, q: '' };
  const tbl = document.getElementById(opts.tableId);
  const pageSize = opts.pageSize || 100;
  const thead = tbl.querySelector('thead'), tbody = tbl.querySelector('tbody');
  const tr = document.createElement('tr');
  opts.columns.forEach(c => {
    const th = document.createElement('th');
    th.textContent = c.label;
    th.style.cursor = 'pointer';
    th.title = 'Sort';
    th.addEventListener('click', () => {
      const k = c.sortKey || c.key;
      state.sort = (state.sort && state.sort.key === k) ? { key: k, dir: -state.sort.dir }
                 : { key: k, dir: c.num ? -1 : 1 };
      state.page = 1; draw();
    });
    tr.appendChild(th);
  });
  thead.innerHTML = ''; thead.appendChild(tr);

  (opts.filters || []).forEach(f => {
    const el = document.getElementById(f.id);
    if (!el) return;
    if (f.type === 'select') {
      const vals = [...new Set(opts.data.map(r => r[f.key]).filter(v => v !== null && v !== ''))].sort();
      el.innerHTML = '<option value="">All</option>' + vals.map(v => `<option>${v}</option>`).join('');
      if (f.default) el.value = f.default;
    } else if (f.default !== undefined) { el.value = f.default; }
    el.addEventListener('input', () => { state.page = 1; draw(); });
  });
  const search = document.getElementById(opts.searchId || 'tableSearch');
  if (search) search.addEventListener('input', () => { state.q = search.value.toLowerCase(); state.page = 1; draw(); });

  function rows() {
    let r = opts.data;
    (opts.filters || []).forEach(f => {
      const el = document.getElementById(f.id); if (!el || el.value === '') return;
      if (f.type === 'select') r = r.filter(x => String(x[f.key]) === el.value);
      else if (f.type === 'min') { const m = Number(el.value); r = r.filter(x => (x[f.key] || 0) >= m); }
      else if (f.type === 'max') { const m = Number(el.value); r = r.filter(x => x[f.key] !== null && x[f.key] <= m); }
    });
    if (state.q) r = r.filter(x => (opts.searchKeys || ['team']).some(k => String(x[k] || '').toLowerCase().includes(state.q)));
    if (state.sort) {
      const { key, dir } = state.sort;
      r = [...r].sort((a, b) => {
        const va = a[key], vb = b[key];
        if (va === vb) return 0;
        if (va === null || va === undefined || va === '') return 1;
        if (vb === null || vb === undefined || vb === '') return -1;
        return (va > vb ? 1 : -1) * dir;
      });
    }
    return r;
  }

  function draw() {
    const r = rows();
    const pages = Math.max(1, Math.ceil(r.length / pageSize));
    state.page = Math.min(state.page, pages);
    const slice = r.slice((state.page - 1) * pageSize, state.page * pageSize);
    tbody.innerHTML = '';
    slice.forEach(x => {
      const row = document.createElement('tr');
      opts.columns.forEach(c => {
        const td = document.createElement('td');
        if (c.link) td.appendChild(collegeProgramLink(x[c.key], x[c.link]));
        else if (c.coachLinks && x[c.coachLinks] && x[c.coachLinks].length) collegeCoachLinks(td, x[c.coachLinks]);
        else if (c.coachId) td.appendChild(collegeCoachLink(x[c.key], x[c.coachId]));
        else td.textContent = collegeFmt(x[c.key], c.fmt);
        if (c.num) td.className = 'text-end';
        if (c.wrap) td.classList.add('wrap');
        row.appendChild(td);
      });
      if (opts.onRow) { row.style.cursor = 'pointer'; row.addEventListener('click', e => { if (e.target.tagName !== 'A') opts.onRow(x); }); }
      tbody.appendChild(row);
    });
    const cnt = document.getElementById(opts.countId || 'rowCount');
    if (cnt) cnt.textContent = r.length.toLocaleString();
    const pg = document.getElementById(opts.pagerId || 'pager');
    if (pg) {
      pg.innerHTML = '';
      if (pages > 1) {
        const mk = (label, p, dis) => {
          const li = document.createElement('li'); li.className = 'page-item' + (dis ? ' disabled' : '') + (p === state.page ? ' active' : '');
          const a = document.createElement('a'); a.className = 'page-link'; a.href = '#'; a.textContent = label;
          a.addEventListener('click', e => { e.preventDefault(); if (!dis) { state.page = p; draw(); } });
          li.appendChild(a); pg.appendChild(li);
        };
        mk('«', state.page - 1, state.page === 1);
        const lo = Math.max(1, state.page - 3), hi = Math.min(pages, state.page + 3);
        for (let p = lo; p <= hi; p++) mk(String(p), p, false);
        mk('»', state.page + 1, state.page === pages);
      }
    }
  }
  draw();
  return { redraw: draw };
}

function collegeStamp(meta) {
  const el = document.getElementById('lastUpdated');
  if (el && meta && meta.generated) el.textContent = meta.generated;
  const n = document.getElementById('ratingNote');
  if (n && meta && meta.note) n.textContent = meta.note;
}
