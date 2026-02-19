// charts.js
const ctx = document.getElementById('sleepChart').getContext('2d');
const sleepChart = new Chart(ctx, { /* ...mesma config anterior... */ });

async function updateDashboard() {
    const res = await fetch('/api/sleep-history');
    const data = await res.json();
    if (data.length > 0) {
        // Lógica de atualização aqui
    }
}

setInterval(updateDashboard, 5000);