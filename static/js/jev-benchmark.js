(() => {
  document.querySelectorAll('[data-ranking]').forEach((section) => {
    const body = section.querySelector('tbody');
    const rows = Array.from(body.rows);
    const toggle = section.querySelector('[data-expand]');
    const sort = section.querySelector('[data-sort]');
    let expanded = false;
    function render() {
      const key = sort.value;
      rows.sort((a, b) => {
        const av = a.dataset[key], bv = b.dataset[key];
        if (av === '') return bv === '' ? 0 : 1;
        if (bv === '') return -1;
        return (Number(av) - Number(bv)) * (key === 'cost' ? 1 : -1);
      });
      rows.forEach((row, index) => {
        body.appendChild(row);
        row.hidden = !expanded && index >= 5;
      });
      if (toggle) {
        toggle.textContent = expanded ? 'Show top 5' : `Show all ${rows.length} models`;
        toggle.setAttribute('aria-expanded', String(expanded));
      }
      section.querySelector('.bench-table-tools > span').firstChild.textContent = expanded ? 'All ' : 'Top 5 ';
    }
    sort.addEventListener('change', render);
    if (toggle) toggle.addEventListener('click', () => { expanded = !expanded; render(); });
  });
  const readout = document.querySelector('[data-chart-readout]');
  document.querySelectorAll('[data-point]').forEach((point) => {
    const describe = () => { readout.textContent = point.getAttribute('aria-label'); };
    point.addEventListener('focus', describe);
    point.addEventListener('pointerenter', describe);
    point.addEventListener('click', describe);
    point.addEventListener('keydown', (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); describe(); } });
  });
})();
