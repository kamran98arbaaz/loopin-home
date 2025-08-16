let lastKnownUpdate = null;
const SOUND_URL = "/static/sounds/notification.mp3"; // Replace with your actual sound path

async function checkForNewUpdate() {
  try {
    const response = await fetch('/api/latest-update-time');
    const data = await response.json();
    const latestTimestamp = data.latest_timestamp;

    if (!latestTimestamp) return;

    if (lastKnownUpdate === null) {
      // First time page load – set baseline
      lastKnownUpdate = latestTimestamp;
      return;
    }

    if (latestTimestamp !== lastKnownUpdate) {
      lastKnownUpdate = latestTimestamp;

      // 🔊 Play notification sound
      const audio = new Audio(SOUND_URL);
      audio.play();

      // 🍞 Show toast message
      showToast("🔔 New update posted!");

    }
  } catch (error) {
    console.error('Error fetching latest update time:', error);
  }
}

function showToast(message) {
  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.innerText = message;
  document.body.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('show');
  }, 100);

  setTimeout(() => {
    toast.classList.remove('show');
    setTimeout(() => document.body.removeChild(toast), 500);
  }, 4000);
}

// Run check every 15 seconds
setInterval(checkForNewUpdate, 15000);
window.addEventListener('DOMContentLoaded', checkForNewUpdate);
