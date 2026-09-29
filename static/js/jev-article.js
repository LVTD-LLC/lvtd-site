// Animate each chart once on entry. Labels and final data never depend on JS.
;(() => {
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)')
  if (motion.matches || !('IntersectionObserver' in window)) return
  const observer = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue
      entry.target.classList.add('jr-enter')
      observer.unobserve(entry.target)
    }
  }, { threshold: 0.2 })
  document.querySelectorAll('[data-jr-animate]').forEach(chart => observer.observe(chart))
  motion.addEventListener('change', () => {
    if (!motion.matches) return
    observer.disconnect()
    document.querySelectorAll('.jr-enter').forEach(chart => chart.classList.remove('jr-enter'))
  })
})()
