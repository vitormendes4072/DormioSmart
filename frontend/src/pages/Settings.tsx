import { Bell, ChevronRight, Shield, Target, User } from "lucide-react";
import { useState } from "react";

import { Toggle } from "../components/Toggle";
import { INPUT_CLS, LABEL_CLS } from "../lib/ui";

/**
 * ATENCAO: "Metas de Sono" e os quatro interruptores de notificacao vieram do
 * prototipo e nao tem nada por tras — nenhum deles produz efeito. O corte
 * desses blocos e o UI-07, junto da entrada de "Meus dispositivos" (AUTH-05).
 * O UI-02 tratou apenas de estrutura, rotas e responsividade.
 */
export function Settings() {
  const [notificacoes, setNotificacoes] = useState(true);
  const [lembreteDormir, setLembreteDormir] = useState(true);
  const [alarmeDespertar, setAlarmeDespertar] = useState(false);
  const [relatorioSemanal, setRelatorioSemanal] = useState(true);
  const [metaSono, setMetaSono] = useState(8);

  const interruptores = [
    {
      label: "Notificações gerais",
      desc: "Receba atualizações e dicas do app",
      value: notificacoes,
      set: setNotificacoes,
    },
    {
      label: "Lembrete de dormir",
      desc: "Alerta 30 minutos antes da meta",
      value: lembreteDormir,
      set: setLembreteDormir,
    },
    {
      label: "Alarme de despertar",
      desc: "Acorde no momento ideal do ciclo",
      value: alarmeDespertar,
      set: setAlarmeDespertar,
    },
    {
      label: "Relatório semanal",
      desc: "Resumo toda segunda-feira",
      value: relatorioSemanal,
      set: setRelatorioSemanal,
    },
  ];

  return (
    <div className="max-w-2xl space-y-5">
      <div className="mb-8">
        <h1 className="text-xl sm:text-2xl font-semibold text-foreground">Configurações</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Personalize sua experiência de repouso
        </p>
      </div>

      <section className="bg-card border border-border rounded-2xl p-4 sm:p-6">
        <div className="flex items-center gap-2 mb-5">
          <User className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Perfil</h2>
        </div>
        <div className="flex items-center gap-4 mb-5 flex-wrap">
          <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
            <User className="w-7 h-7 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="font-semibold text-foreground truncate">Rafael Silva</p>
            <p className="text-sm text-muted-foreground truncate">rafael@email.com</p>
          </div>
          <button className="ml-auto text-xs text-primary hover:text-accent transition font-semibold">
            Editar foto
          </button>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={LABEL_CLS} htmlFor="perfil-nome">
              Nome
            </label>
            <input id="perfil-nome" type="text" defaultValue="Rafael Silva" className={INPUT_CLS} />
          </div>
          <div>
            <label className={LABEL_CLS} htmlFor="perfil-idade">
              Idade
            </label>
            <input id="perfil-idade" type="number" defaultValue="28" className={INPUT_CLS} />
          </div>
        </div>
      </section>

      <section className="bg-card border border-border rounded-2xl p-4 sm:p-6">
        <div className="flex items-center gap-2 mb-5">
          <Target className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Metas de Sono</h2>
        </div>

        <div className="space-y-5">
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm text-foreground" htmlFor="meta-sono">
                Meta de horas diárias
              </label>
              <span className="text-sm font-bold text-primary">{metaSono}h</span>
            </div>
            <input
              id="meta-sono"
              type="range"
              min={5}
              max={12}
              value={metaSono}
              onChange={(e) => setMetaSono(Number(e.target.value))}
              className="w-full h-1.5 rounded-full"
              style={{ accentColor: "#8b7ff8" }}
            />
            <div className="flex justify-between text-xs text-muted-foreground mt-1">
              <span>5h</span>
              <span>12h</span>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className={LABEL_CLS} htmlFor="hora-dormir">
                Hora de dormir
              </label>
              <input id="hora-dormir" type="time" defaultValue="23:00" className={INPUT_CLS} />
            </div>
            <div>
              <label className={LABEL_CLS} htmlFor="hora-acordar">
                Hora de acordar
              </label>
              <input id="hora-acordar" type="time" defaultValue="07:00" className={INPUT_CLS} />
            </div>
          </div>
        </div>
      </section>

      <section className="bg-card border border-border rounded-2xl p-4 sm:p-6">
        <div className="flex items-center gap-2 mb-5">
          <Bell className="w-4 h-4 text-primary" />
          <h2 className="text-sm font-semibold text-foreground">Notificações</h2>
        </div>

        <div className="space-y-5">
          {interruptores.map(({ label, desc, value, set }) => (
            <div key={label} className="flex items-center justify-between gap-4">
              <div className="min-w-0">
                <p className="text-sm font-medium text-foreground">{label}</p>
                <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
              </div>
              <Toggle checked={value} onChange={set} />
            </div>
          ))}
        </div>
      </section>

      <section className="bg-card border border-border rounded-2xl overflow-hidden">
        <div className="px-4 sm:px-6 pt-6 pb-3">
          <div className="flex items-center gap-2">
            <Shield className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Conta e Privacidade</h2>
          </div>
        </div>
        {["Alterar senha", "Exportar meus dados", "Política de privacidade", "Termos de uso"].map(
          (label) => (
            <button
              key={label}
              className="w-full flex items-center justify-between px-4 sm:px-6 py-3.5 hover:bg-secondary transition border-t border-border text-left"
            >
              <span className="text-sm text-foreground">{label}</span>
              <ChevronRight className="w-4 h-4 text-muted-foreground flex-shrink-0" />
            </button>
          ),
        )}
      </section>

      <button className="w-full py-3 rounded-2xl text-sm font-medium text-red-400 bg-red-500/10 border border-red-500/15 hover:bg-red-500/15 transition">
        Excluir conta
      </button>
    </div>
  );
}
