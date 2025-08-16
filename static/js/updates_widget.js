(function(){
  async function fetchUpdates(){
    try{
      const res = await fetch('/api/updates?per_page=5');
      if(!res.ok) throw new Error('fetch failed');
      const j = await res.json();
      const list = document.getElementById('updates-list');
      if(!j.items || j.items.length === 0){
        list.innerHTML = '<p class="text-sm text-gray-500">No updates yet.</p>';
        return;
      }
      const items = j.items.map(u => {
        const time = u.timestamp ? `<time class="text-xs text-gray-400">${u.timestamp}</time>` : '';
        return `<div class="py-2 border-b last:border-b-0"><div class="flex justify-between"><div><strong>${u.process}</strong> — ${u.name}</div>${time}</div><div class="mt-1 text-sm text-gray-700">${u.message}</div></div>`;
      }).join('');
      list.innerHTML = items;
    }catch(e){
      const list = document.getElementById('updates-list');
      list.innerHTML = '<p class="text-sm text-red-500">Failed to load updates</p>';
    }
  }

  // Initial fetch
  if(document.getElementById('updates-widget')){
    fetchUpdates();
    // refresh every 30s
    setInterval(fetchUpdates, 30000);
  }
})();
