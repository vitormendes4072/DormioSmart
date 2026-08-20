import { Bell, ChevronRight, Clock, TrendingUp, Zap } from "lucide-react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { ChartTooltip } from "../components/ChartTooltip";
import { DADOS_SEMANAIS, ESTAGIOS, HISTORICO, corDaPontuacao } from "../data/mock";

/**
 * ATENCAO: esta tela ainda exibe os dados ficticios do prototipo, incluindo
 * estagios de sono e "pontuacao" — metricas que o dispositivo NAO mede. A
 * substituicao por dados reais de movimento e o UI-04/UI-05/UI-06. O UI-02
 * mexeu apenas em estrutura, rotas e responsividade, para manter o diff
 * revisavel.
 */
export function Dashboard() {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="text-xs text-muted-foreground uppercase tracking-wider">
            Terça, 19 de Agosto de 2026
          </p>
          <h1 className="text-xl sm:text-2xl font-semibold text-foreground mt-1">
            Boa noite, Rafael
          </h1>
        </div>
        <button
          aria-label="Notificações"
          className="relative w-9 h-9 flex-shrink-0 bg-card border border-border rounded-xl flex items-center justify-center hover:bg-secondary transition"
        >
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-primary rounded-full" />
        </button>
      </div>

      {/* 2 colunas no celular, 4 a partir de lg */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
        <div className="col-span-2 lg:col-span-1 bg-card border border-border rounded-2xl p-5 flex flex-col">
          <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
            Pontuação
          </p>
          <div className="mt-4 flex items-end gap-1">
            <span className="text-5xl font-bold text-primary leading-none">91</span>
            <span className="text-lg text-muted-foreground mb-0.5">/100</span>
          </div>
          <div className="mt-4">
            <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
              <div className="h-full bg-primary rounded-full" style={{ width: "91%" }} />
            </div>
            <p className="text-xs text-muted-foreground mt-1.5">Excelente sono</p>
          </div>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Duração
            </p>
            <Clock className="w-4 h-4 text-blue-400 flex-shrink-0" />
          </div>
          <p className="text-2xl font-bold text-foreground">8h 15m</p>
          <p className="text-xs text-muted-foreground mt-1">Meta: 8h</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Eficiência
            </p>
            <TrendingUp className="w-4 h-4 text-green-400 flex-shrink-0" />
          </div>
          <p className="text-2xl font-bold text-foreground">94%</p>
          <p className="text-xs text-muted-foreground mt-1">+3% vs semana ant.</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-5">
          <div className="flex items-center justify-between mb-4">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
              Profundo
            </p>
            <Zap className="w-4 h-4 text-accent flex-shrink-0" />
          </div>
          <p className="text-2xl font-bold text-foreground">1h 49m</p>
          <p className="text-xs text-muted-foreground mt-1">22% do total</p>
        </div>
      </div>

      <div className="bg-card border border-border rounded-2xl p-4 sm:p-6">
        <div className="flex items-start justify-between gap-4 mb-5 flex-wrap">
          <div>
            <h3 className="text-sm font-semibold text-foreground">Sono Semanal</h3>
            <p className="text-xs text-muted-foreground mt-0.5">
              Últimos 7 dias · Média: 7h 27m
            </p>
          </div>
          <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="w-3 h-3 rounded-sm bg-primary inline-block" />
            Horas dormidas
          </span>
        </div>
        <div className="h-44 sm:h-52">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart
              data={DADOS_SEMANAIS}
              barSize={30}
              margin={{ top: 4, right: 4, left: -10, bottom: 0 }}
            >
              <XAxis
                dataKey="day"
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#6b7a99", fontSize: 12, fontFamily: "Outfit" }}
              />
              <YAxis
                axisLine={false}
                tickLine={false}
                tick={{ fill: "#6b7a99", fontSize: 12, fontFamily: "Outfit" }}
                domain={[0, 10]}
                tickFormatter={(v) => v + "h"}
              />
              <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(139, 127, 248, 0.06)" }} />
              <Bar dataKey="hours" fill="#8b7ff8" radius={[6, 6, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Empilha no celular; 2/5 + 3/5 a partir de lg */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
        <div className="lg:col-span-2 bg-card border border-border rounded-2xl p-4 sm:p-6">
          <h3 className="text-sm font-semibold text-foreground">Fases do Sono</h3>
          <p className="text-xs text-muted-foreground mt-0.5 mb-5">Ontem à noite</p>

          <div className="space-y-3.5">
            {ESTAGIOS.map(({ name, pct, color }) => (
              <div key={name}>
                <div className="flex justify-between text-xs mb-1.5">
                  <span className="text-muted-foreground">{name}</span>
                  <span className="text-foreground font-semibold">{pct}%</span>
                </div>
                <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{ width: pct + "%", backgroundColor: color }}
                  />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-5 pt-5 border-t border-border grid grid-cols-2 gap-3">
            <div className="text-center">
              <p className="text-xl font-bold text-foreground">23:15</p>
              <p className="text-xs text-muted-foreground mt-0.5">Dormiu</p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-foreground">07:30</p>
              <p className="text-xs text-muted-foreground mt-0.5">Acordou</p>
            </div>
          </div>
        </div>

        <div className="lg:col-span-3 bg-card border border-border rounded-2xl p-4 sm:p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-foreground">Histórico de Sono</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Últimas entradas</p>
            </div>
            <button className="text-xs text-primary hover:text-accent transition font-semibold flex-shrink-0">
              Ver tudo
            </button>
          </div>

          <div className="space-y-0.5">
            {HISTORICO.map(({ date, bed, wake, dur, score }) => (
              <div
                key={date}
                className="flex items-center justify-between gap-3 py-3.5 border-b border-border last:border-0 group cursor-pointer"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-foreground truncate">{date}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {bed} – {wake} · {dur}
                  </p>
                </div>
                <div className="flex items-center gap-3 flex-shrink-0">
                  <div className="text-right">
                    <p className="text-sm font-bold" style={{ color: corDaPontuacao(score) }}>
                      {score}
                    </p>
                    <p className="text-xs text-muted-foreground">score</p>
                  </div>
                  <ChevronRight className="w-4 h-4 text-muted-foreground group-hover:text-foreground transition" />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
