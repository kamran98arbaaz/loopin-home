async function highlightIfRecent() {
  try {
    const response = await fetch('/api/latest-update-time');
    const data = await response.json();
    const latestTimestamp = data.latest_timestamp;

    if (!latestTimestamp) return;

    const latestTime = new Date(latestTimestamp);
    const now = new Date();
    const diffHours = (now - latestTime) / (1000 * 60 * 60);

    const tile = document.getElementById('showUpdatesTile');
    if (diffHours <= 24) {
      tile.classList.add('highlight');
    } else {
      tile.classList.remove('highlight');
    }
  } catch (err) {
    console.error("Failed to check for recent updates:", err);
  }
}

window.addEventListener('DOMContentLoaded', highlightIfRecent);
