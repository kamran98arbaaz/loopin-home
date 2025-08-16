// static/js/home.js

document.addEventListener('DOMContentLoaded', () => {
  const sopBtn = document.getElementById('tile-sop');
  const lessonsBtn = document.getElementById('tile-lessons');
  const sopPanel = document.getElementById('panel-sop');
  const lessonsPanel = document.getElementById('panel-lessons');
  const closeSop = document.getElementById('close-sop');
  const closeLessons = document.getElementById('close-lessons');

  function openPanel(panel, btn) {
    panel.classList.remove('hidden');
    panel.setAttribute('aria-hidden', 'false');
    btn.setAttribute('aria-expanded', 'true');
    panel.scrollIntoView({ behavior: 'smooth' });
  }

  function closePanel(panel, btn) {
    panel.classList.add('hidden');
    panel.setAttribute('aria-hidden', 'true');
    btn.setAttribute('aria-expanded', 'false');
    btn.focus();
  }

  sopBtn.addEventListener('click', () => {
    closePanel(lessonsPanel, lessonsBtn);
    openPanel(sopPanel, sopBtn);
  });

  lessonsBtn.addEventListener('click', () => {
    closePanel(sopPanel, sopBtn);
    openPanel(lessonsPanel, lessonsBtn);
  });

  closeSop.addEventListener('click', () => closePanel(sopPanel, sopBtn));
  closeLessons.addEventListener('click', () => closePanel(lessonsPanel, lessonsBtn));

  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      if (!sopPanel.classList.contains('hidden')) closePanel(sopPanel, sopBtn);
      if (!lessonsPanel.classList.contains('hidden')) closePanel(lessonsPanel, lessonsBtn);
    }
  });
});
