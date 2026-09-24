(() => {
  const input = document.querySelector('#steering-search');
  const entries = [...document.querySelectorAll('.steering-entry')];
  const groups = [...document.querySelectorAll('.steering-group')];
  const count = document.querySelector('#steering-count');
  const filter = () => {
    const query = input.value.trim().toLowerCase();
    let visible = 0;
    entries.forEach(entry => {
      entry.hidden = !entry.textContent.toLowerCase().includes(query);
      if (!entry.hidden) visible++;
    });
    groups.forEach(group => { group.hidden = ![...group.querySelectorAll('.steering-entry')].some(entry => !entry.hidden); });
    count.textContent = query ? `Showing ${visible} of ${entries.length} file patterns.` : `Showing all ${entries.length} file patterns.`;
    document.querySelector('#steering-empty').hidden = visible !== 0;
  };
  document.querySelector('#steering-filter').hidden = false;
  input.addEventListener('input', filter);
  document.querySelector('.steering-index').addEventListener('click', event => {
    if (event.target.closest('a[href^="#"]')) { input.value = ''; filter(); }
  });
})();
