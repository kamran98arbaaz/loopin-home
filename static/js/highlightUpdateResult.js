// highlightUpdateResult.js
// Highlights the update item if the URL hash matches an update id

document.addEventListener('DOMContentLoaded', function() {
  const hash = window.location.hash;
  if (hash && hash.startsWith('#update-')) {
    const el = document.querySelector(hash);
    if (el) {
      el.classList.add('search-highlight');
      setTimeout(() => {
        el.classList.remove('search-highlight');
      }, 1200);
      el.scrollIntoView({behavior: 'smooth', block: 'center'});
    }
  }
});
