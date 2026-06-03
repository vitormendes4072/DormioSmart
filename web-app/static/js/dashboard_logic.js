/**
 * SmartDormio - Dashboard Logic
 * Busca os dados da API e atualiza a interface.
 *
 * Métrica exibida: INTENSIDADE DO MOVIMENTO = |magnitude - gravidade|.
 * Em repouso, a magnitude do vetor de aceleração fica próxima da gravidade
 * (~9,81 m/s²), então a intensidade ≈ 0; durante um evento de movimento, a
 * magnitude se afasta e a intensidade cresce. Isso torna "evento vs. repouso"
 * legível (picos = movimento) e alinha com o índice de atividade da metodologia.
 */

const GRAVIDADE = 9.81; // m/s² — referência de repouso
const STATUS_MOVIMENTO = "Movimento Detectado!";
const COR_MOVIMENTO = "#f59e0b"; // amber-500
const COR_REPOUSO = "#818cf8";   // indigo-400

// Converte um registro do banco na intensidade do movimento (desvio do repouso).
function intensidade(registro) {
    if (registro == null || registro.movimento_total == null) return null;
    return Math.abs(registro.movimento_total - GRAVIDADE);
}

// Status de cada ponto do gráfico, na mesma ordem dos dados (para colorir os segmentos).
let statusHistorico = [];

const ctx = document.getElementById('sleepChart').getContext('2d');

const gradient = ctx.createLinearGradient(0, 0, 0, 400);
gradient.addColorStop(0, 'rgba(99, 102, 241, 0.4)');
gradient.addColorStop(1, 'rgba(99, 102, 241, 0.0)');

const sleepChart = new Chart(ctx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            label: 'Intensidade do Movimento (m/s²)',
            data: [],
            borderColor: COR_REPOUSO,
            backgroundColor: gradient,
            borderWidth: 2,
            pointRadius: 0,
            pointHoverRadius: 4,
            fill: true,
            tension: 0.3,
            // Colore cada segmento conforme o status registrado naquele ponto:
            // âmbar quando é evento de movimento, indigo quando é repouso.
            segment: {
                borderColor: (c) =>
                    statusHistorico[c.p1DataIndex] === STATUS_MOVIMENTO
                        ? COR_MOVIMENTO
                        : COR_REPOUSO
            }
        }]
    },
    options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
            x: {
                grid: { display: false, color: '#334155' },
                ticks: { color: '#94a3b8', maxTicksLimit: 8 }
            },
            y: {
                beginAtZero: true,
                title: { display: true, text: 'Intensidade (m/s²)', color: '#64748b' },
                grid: { color: '#1e293b' },
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
                borderWidth: 1,
                callbacks: {
                    label: (item) => `Intensidade: ${item.parsed.y.toFixed(2)} m/s²`,
                    afterLabel: (item) => statusHistorico[item.dataIndex] || ''
                }
            }
        }
    }
});

async function updateDashboard() {
    try {
        const response = await fetch('/api/sleep-history');
        if (!response.ok) throw new Error("Falha na comunicação com a API");

        const data = await response.json();
        if (data.length === 0) return;

        // --- CARDS (último dado) ---
        const latest = data[0];

        const temp = latest.temp != null ? latest.temp.toFixed(1) : "--";
        document.getElementById('temp-val').innerText = `${temp}°C`;

        const intLatest = intensidade(latest);
        document.getElementById('mov-val').innerText =
            intLatest != null ? intLatest.toFixed(2) : "--";

        const status = latest.status || "Aguardando...";
        const statusEl = document.getElementById('status-val');
        statusEl.innerText = status;
        statusEl.className = status === STATUS_MOVIMENTO
            ? "text-3xl font-bold text-amber-400 animate-pulse"
            : "text-3xl font-bold text-indigo-400";

        document.getElementById('time-val').innerText =
            new Date(latest.created_at).toLocaleTimeString('pt-BR');

        // --- GRÁFICO (série histórica, do mais antigo ao mais recente) ---
        const history = data.slice().reverse();
        statusHistorico = history.map(d => d.status);

        sleepChart.data.labels = history.map(d =>
            new Date(d.created_at).toLocaleTimeString('pt-BR', {
                hour: '2-digit', minute: '2-digit', second: '2-digit'
            })
        );
        sleepChart.data.datasets[0].data = history.map(intensidade);
        sleepChart.update();

        // --- RESUMO: nº de eventos de movimento na janela exibida ---
        const eventos = history.filter(d => d.status === STATUS_MOVIMENTO).length;
        const elCount = document.getElementById('event-count');
        if (elCount) elCount.innerText = `${eventos} ${eventos === 1 ? 'evento' : 'eventos'}`;

        updateTable(data);

    } catch (error) {
        console.error("Erro no Dashboard:", error);
        const badge = document.getElementById('status-badge');
        if (badge) {
            badge.innerText = "Erro de Conexão";
            badge.classList.replace('text-green-400', 'text-red-400');
        }
    }
}

function updateTable(data) {
    const tbody = document.getElementById('log-table-body');
    tbody.innerHTML = '';

    data.slice(0, 5).forEach(row => {
        const tr = document.createElement('tr');
        tr.className = "border-b border-slate-800 hover:bg-slate-800/50 transition";

        const time = new Date(row.created_at).toLocaleTimeString('pt-BR');
        const intRow = intensidade(row);
        const intStr = intRow != null ? intRow.toFixed(2) : "--";
        const temp = row.temp != null ? row.temp.toFixed(1) : "--";
        const ehMovimento = row.status === STATUS_MOVIMENTO;
        const corStatus = ehMovimento ? "text-amber-400" : "text-slate-400";

        tr.innerHTML = `
            <td class="px-6 py-4">${time}</td>
            <td class="px-6 py-4 font-mono text-indigo-300">${intStr}</td>
            <td class="px-6 py-4">${temp}°C</td>
            <td class="px-6 py-4 text-xs ${corStatus}">${row.status || '-'}</td>
        `;
        tbody.appendChild(tr);
    });
}

// Polling: atualiza ao carregar e a cada 2s.
updateDashboard();
setInterval(updateDashboard, 2000);
