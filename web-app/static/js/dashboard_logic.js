/**
 * SmartDormio - Dashboard Logic
 * Responsável por buscar dados da API e atualizar a interface em tempo real.
 */

// 1. Configuração Inicial do Gráfico (Chart.js)
const ctx = document.getElementById('sleepChart').getContext('2d');

// Gradiente para deixar o gráfico bonito (estilo TCC profissional)
const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(99, 102, 241, 0.5)'); // Indigo forte no topo
gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)'); // Transparente na base

const sleepChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [], // Horários (Eixo X)
        datasets: [{
            label: 'Intensidade do Movimento',
            data: [], // Valores do sensor (Eixo Y)
            borderColor: '#818cf8', // Cor da linha (Indigo-400)
            backgroundColor: gradient,
            borderWidth: 2,
            pointRadius: 0, // Remove as bolinhas para o gráfico ficar liso
            pointHoverRadius: 4,
            fill: true,
            tension: 0.4 // Suaviza a linha (Curva de Bezier)
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false, // Desativa animação para não ficar "pulando" no realtime
        interaction: {
            mode: 'index',
            intersect: false,
        },
        scales: {
            x: {
                grid: { display: false, color: '#334155' },
                ticks: { color: '#94a3b8', maxTicksLimit: 8 }
            },
            y: {
                beginAtZero: true,
                grid: { color: '#1e293b' }, // Linhas de grade sutis
                ticks: { color: '#94a3b8' }
            }
        },
        plugins: {
            legend: { display: false },
            tooltip: {
                backgroundColor: 'rgba(15, 23, 42, 0.9)',
                titleColor: '#e2e8f0',
                bodyColor: '#cbd5e1',
                borderColor: '#334155',
                borderWidth: 1
            }
        }
    }
});

// 2. Função Principal de Atualização
async function updateDashboard() {
    try {
        // Busca os dados na sua API Flask
        const response = await fetch('/api/sleep-history');
        
        if (!response.ok) throw new Error("Falha na comunicação com a API");
        
        const data = await response.json();

        // Se não houver dados, não faz nada
        if (data.length === 0) return;

        // --- ATUALIZAÇÃO DOS CARDS (Último dado recebido) ---
        const latest = data[0]; // O primeiro item é o mais recente

        // Temperatura
        const temp = latest.temp ? latest.temp.toFixed(1) : "--";
        document.getElementById('temp-val').innerText = `${temp}°C`;

        // Movimento
        const mov = latest.movimento_total ? latest.movimento_total.toFixed(2) : "0.00";
        document.getElementById('mov-val').innerText = mov;

        // Status
        const status = latest.status || "Aguardando...";
        const statusEl = document.getElementById('status-val');
        statusEl.innerText = status;
        
        // Muda a cor do status dinamicamente
        if (status === "Movimento Detectado!") {
            statusEl.className = "text-3xl font-bold text-amber-400 animate-pulse";
        } else {
            statusEl.className = "text-3xl font-bold text-indigo-400";
        }

        // Hora da última atualização
        const lastTime = new Date(latest.created_at).toLocaleTimeString('pt-BR');
        document.getElementById('time-val').innerText = lastTime;

        // --- ATUALIZAÇÃO DO GRÁFICO (Série Histórica) ---
        // A API traz do mais novo para o mais velho, mas o gráfico precisa do inverso
        // Usamos .slice() para criar uma cópia e não inverter o array original
        const history = data.slice().reverse(); 

        sleepChart.data.labels = history.map(d => {
            return new Date(d.created_at).toLocaleTimeString('pt-BR', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            });
        });
        
        sleepChart.data.datasets[0].data = history.map(d => d.movimento_total);
        sleepChart.update();

        // --- ATUALIZAÇÃO DA TABELA DE LOGS (Opcional) ---
        updateTable(data);

    } catch (error) {
        console.error("Erro no Dashboard:", error);
        document.getElementById('status-badge').innerText = "Erro de Conexão";
        document.getElementById('status-badge').classList.replace('text-green-400', 'text-red-400');
    }
}

// 3. Função Auxiliar para a Tabela
function updateTable(data) {
    const tbody = document.getElementById('log-table-body');
    tbody.innerHTML = ''; // Limpa a tabela

    // Pega apenas os 5 últimos para não poluir
    data.slice(0, 5).forEach(row => {
        const tr = document.createElement('tr');
        tr.className = "border-b border-slate-800 hover:bg-slate-800/50 transition";
        
        const time = new Date(row.created_at).toLocaleTimeString('pt-BR');
        const mov = row.movimento_total ? row.movimento_total.toFixed(2) : "0.00";
        const temp = row.temp ? row.temp.toFixed(1) : "--";

        tr.innerHTML = `
            <td class="px-6 py-4">${time}</td>
            <td class="px-6 py-4 font-mono text-indigo-300">${mov}</td>
            <td class="px-6 py-4">${temp}°C</td>
            <td class="px-6 py-4 text-xs text-slate-400">${row.status || '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// 4. Inicia o Ciclo de Atualização (Polling)
// Atualiza assim que carrega
updateDashboard();

// E depois repete a cada 2 segundos (2000ms)
setInterval(updateDashboard, 2000);