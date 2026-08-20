import { useState } from "react";
import {
  BarChart,
  Bar,
  ResponsiveContainer,
  XAxis,
  YAxis,
  Tooltip,
} from "recharts";
import {
  Moon,
  Eye,
  EyeOff,
  Bell,
  User,
  Target,
  Shield,
  Clock,
  TrendingUp,
  ChevronRight,
  Settings,
  LogOut,
  Home,
  Zap,
} from "lucide-react";

type Screen = "login" | "register" | "dashboard" | "settings";

const WEEKLY_DATA = [
  { day: "Seg", hours: 6.5 },
  { day: "Ter", hours: 7.8 },
  { day: "Qua", hours: 5.9 },
  { day: "Qui", hours: 8.2 },
  { day: "Sex", hours: 7.1 },
  { day: "Sáb", hours: 9.0 },
  { day: "Dom", hours: 7.4 },
];

const STAGES = [
  { name: "Profundo", pct: 22, color: "#8b7ff8" },
  { name: "REM", pct: 21, color: "#a78bfa" },
  { name: "Leve", pct: 47, color: "#243260" },
  { name: "Acordado", pct: 10, color: "#1a2448" },
];

const LOG = [
  { date: "Hoje, 19 Ago", bed: "23:15", wake: "07:30", dur: "8h 15m", score: 91 },
  { date: "18 Ago", bed: "00:02", wake: "07:45", dur: "7h 43m", score: 78 },
  { date: "17 Ago", bed: "23:45", wake: "07:00", dur: "7h 15m", score: 82 },
  { date: "16 Ago", bed: "22:30", wake: "06:45", dur: "8h 15m", score: 94 },
];

function scoreColor(s: number) {
  if (s >= 85) return "#8b7ff8";
  if (s >= 70) return "#60a5fa";
  return "#fb923c";
}

// ─── Custom Chart Tooltip ─────────────────────────────────────────

function ChartTooltip({ active, payload, label }: { active?: boolean; payload?: Array<{ value: number }>; label?: string }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-card border border-border rounded-xl px-3 py-2 text-sm shadow-2xl">
      <p className="text-muted-foreground text-xs mb-0.5">{label}</p>
      <p className="text-foreground font-semibold">{payload[0].value}h de sono</p>
    </div>
  );
}

// ─── Toggle Switch ────────────────────────────────────────────────

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={`relative w-11 h-6 rounded-full flex-shrink-0 transition-colors duration-200 ${
        checked ? "bg-primary" : "bg-secondary border border-border"
      }`}
    >
      <span
        className={`absolute top-1 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200 ${
          checked ? "translate-x-6" : "translate-x-1"
        }`}
      />
    </button>
  );
}

// ─── Sidebar ─────────────────────────────────────────────────────

function Sidebar({ screen, onGo }: { screen: Screen; onGo: (s: Screen) => void }) {
  const navItems = [
    { id: "dashboard" as Screen, label: "Início", icon: Home },
    { id: "settings" as Screen, label: "Configurações", icon: Settings },
  ];

  return (
    <aside className="w-56 flex-shrink-0 bg-card border-r border-border flex flex-col h-screen sticky top-0">
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-primary/20 flex items-center justify-center">
            <Moon className="w-5 h-5 text-primary" />
          </div>
          <span className="font-semibold text-foreground text-lg tracking-tight">Dormix</span>
        </div>
      </div>

      <nav className="flex-1 p-4 space-y-0.5">
        {navItems.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => onGo(id)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-150 ${
              screen === id
                ? "bg-primary/15 text-primary"
                : "text-muted-foreground hover:text-foreground hover:bg-secondary"
            }`}
          >
            <Icon className="w-4 h-4" />
            {label}
          </button>
        ))}
      </nav>

      <div className="p-4 border-t border-border space-y-3">
        <div className="flex items-center gap-3 px-1">
          <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
            <User className="w-4 h-4 text-primary" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-medium text-foreground truncate">Rafael Silva</p>
            <p className="text-xs text-muted-foreground truncate">rafael@email.com</p>
          </div>
        </div>
        <button
          onClick={() => onGo("login")}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-xl text-sm text-muted-foreground hover:text-foreground hover:bg-secondary transition-all duration-150"
        >
          <LogOut className="w-4 h-4" />
          Sair
        </button>
      </div>
    </aside>
  );
}

// ─── Login ────────────────────────────────────────────────────────

function LoginScreen({ onLogin, onGo }: { onLogin: () => void; onGo: (s: Screen) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[500px] h-[500px] rounded-full bg-primary/8 blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 right-0 w-72 h-72 rounded-full bg-accent/5 blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/20 border border-primary/20 mb-4">
            <Moon className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Dormix</h1>
          <p className="text-sm text-muted-foreground mt-1">Seu guia para um sono de qualidade</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-7 space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Bem-vindo de volta</h2>
            <p className="text-sm text-muted-foreground mt-0.5">Entre na sua conta</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider">
                E-mail
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="rafael@email.com"
                className="w-full px-3.5 py-2.5 bg-secondary text-foreground placeholder:text-muted-foreground/40 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition"
              />
            </div>

            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider">
                Senha
              </label>
              <div className="relative">
                <input
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full px-3.5 py-2.5 pr-10 bg-secondary text-foreground placeholder:text-muted-foreground/40 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition"
                />
                <button
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              <button className="text-xs text-primary hover:text-accent transition mt-1.5 block ml-auto">
                Esqueci minha senha
              </button>
            </div>
          </div>

          <button
            onClick={onLogin}
            className="w-full py-3 bg-primary text-primary-foreground rounded-xl text-sm font-semibold hover:bg-primary/90 transition active:scale-[0.98]"
          >
            Entrar
          </button>

          <p className="text-center text-sm text-muted-foreground">
            Não tem uma conta?{" "}
            <button
              onClick={() => onGo("register")}
              className="text-primary hover:text-accent transition font-semibold"
            >
              Cadastre-se
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Register ─────────────────────────────────────────────────────

function RegisterScreen({ onRegister, onGo }: { onRegister: () => void; onGo: (s: Screen) => void }) {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPass, setShowPass] = useState(false);

  const inputCls =
    "w-full px-3.5 py-2.5 bg-secondary text-foreground placeholder:text-muted-foreground/40 border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition";
  const labelCls = "text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider";

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-4 relative overflow-hidden">
      <div className="absolute top-1/4 right-1/4 w-96 h-96 rounded-full bg-primary/7 blur-3xl pointer-events-none" />
      <div className="absolute bottom-1/4 left-1/4 w-64 h-64 rounded-full bg-accent/5 blur-3xl pointer-events-none" />

      <div className="relative w-full max-w-sm">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-primary/20 border border-primary/20 mb-4">
            <Moon className="w-7 h-7 text-primary" />
          </div>
          <h1 className="text-2xl font-semibold text-foreground tracking-tight">Dormix</h1>
          <p className="text-sm text-muted-foreground mt-1">Comece a melhorar seu sono hoje</p>
        </div>

        <div className="bg-card border border-border rounded-2xl p-7 space-y-5">
          <div>
            <h2 className="text-lg font-semibold text-foreground">Criar conta</h2>
            <p className="text-sm text-muted-foreground mt-0.5">Preencha seus dados abaixo</p>
          </div>

          <div className="space-y-4">
            <div>
              <label className={labelCls}>Nome completo</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Rafael Silva"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>E-mail</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="rafael@email.com"
                className={inputCls}
              />
            </div>
            <div>
              <label className={labelCls}>Senha</label>
              <div className="relative">
                <input
                  type={showPass ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Mínimo 8 caracteres"
                  className={inputCls + " pr-10"}
                />
                <button
                  onClick={() => setShowPass(!showPass)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
                >
                  {showPass ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>
          </div>

          <button
            onClick={onRegister}
            className="w-full py-3 bg-primary text-primary-foreground rounded-xl text-sm font-semibold hover:bg-primary/90 transition active:scale-[0.98]"
          >
            Criar conta
          </button>

          <p className="text-center text-sm text-muted-foreground">
            Já tem uma conta?{" "}
            <button
              onClick={() => onGo("login")}
              className="text-primary hover:text-accent transition font-semibold"
            >
              Entrar
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}

// ─── Dashboard ───────────────────────────────────────────────────

function Dashboard({ onGo }: { onGo: (s: Screen) => void }) {
  return (
    <div className="flex bg-background min-h-screen">
      <Sidebar screen="dashboard" onGo={onGo} />

      <main className="flex-1 overflow-y-auto p-8 space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <p className="text-xs text-muted-foreground uppercase tracking-wider">Terça, 19 de Agosto de 2026</p>
            <h1 className="text-2xl font-semibold text-foreground mt-1">Boa noite, Rafael</h1>
          </div>
          <button className="relative w-9 h-9 bg-card border border-border rounded-xl flex items-center justify-center hover:bg-secondary transition">
            <Bell className="w-4 h-4 text-muted-foreground" />
            <span className="absolute top-2 right-2 w-1.5 h-1.5 bg-primary rounded-full" />
          </button>
        </div>

        {/* Stat cards */}
        <div className="grid grid-cols-4 gap-4">
          {/* Sleep Score */}
          <div className="col-span-1 bg-card border border-border rounded-2xl p-5 flex flex-col">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Pontuação</p>
            <div className="mt-4 flex items-end gap-1">
              <span className="text-5xl font-bold text-primary leading-none">91</span>
              <span className="text-lg text-muted-foreground mb-0.5">/100</span>
            </div>
            <div className="mt-4">
              <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                <div className="h-full bg-primary rounded-full transition-all" style={{ width: "91%" }} />
              </div>
              <p className="text-xs text-muted-foreground mt-1.5">Excelente sono</p>
            </div>
          </div>

          {/* Duration */}
          <div className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Duração</p>
              <Clock className="w-4 h-4 text-blue-400" />
            </div>
            <p className="text-2xl font-bold text-foreground">8h 15m</p>
            <p className="text-xs text-muted-foreground mt-1">Meta: 8h</p>
          </div>

          {/* Efficiency */}
          <div className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Eficiência</p>
              <TrendingUp className="w-4 h-4 text-green-400" />
            </div>
            <p className="text-2xl font-bold text-foreground">94%</p>
            <p className="text-xs text-muted-foreground mt-1">+3% vs semana ant.</p>
          </div>

          {/* Deep Sleep */}
          <div className="bg-card border border-border rounded-2xl p-5">
            <div className="flex items-center justify-between mb-4">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">Profundo</p>
              <Zap className="w-4 h-4 text-accent" />
            </div>
            <p className="text-2xl font-bold text-foreground">1h 49m</p>
            <p className="text-xs text-muted-foreground mt-1">22% do total</p>
          </div>
        </div>

        {/* Weekly Chart */}
        <div className="bg-card border border-border rounded-2xl p-6">
          <div className="flex items-start justify-between mb-5">
            <div>
              <h3 className="text-sm font-semibold text-foreground">Sono Semanal</h3>
              <p className="text-xs text-muted-foreground mt-0.5">Últimos 7 dias · Média: 7h 27m</p>
            </div>
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded-sm bg-primary inline-block" />
                Horas dormidas
              </span>
            </div>
          </div>
          <div className="h-52">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={WEEKLY_DATA} barSize={30} margin={{ top: 4, right: 4, left: -10, bottom: 0 }}>
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
                  tickFormatter={(v) => `${v}h`}
                />
                <Tooltip content={<ChartTooltip />} cursor={{ fill: "rgba(139, 127, 248, 0.06)" }} />
                <Bar dataKey="hours" fill="#8b7ff8" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Bottom row */}
        <div className="grid grid-cols-5 gap-4">
          {/* Sleep Stages */}
          <div className="col-span-2 bg-card border border-border rounded-2xl p-6">
            <h3 className="text-sm font-semibold text-foreground">Fases do Sono</h3>
            <p className="text-xs text-muted-foreground mt-0.5 mb-5">Ontem à noite</p>

            <div className="space-y-3.5">
              {STAGES.map(({ name, pct, color }) => (
                <div key={name}>
                  <div className="flex justify-between text-xs mb-1.5">
                    <span className="text-muted-foreground">{name}</span>
                    <span className="text-foreground font-semibold">{pct}%</span>
                  </div>
                  <div className="h-1.5 bg-secondary rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: `${pct}%`,
                        backgroundColor: color,
                        opacity: color === "#243260" || color === "#1a2448" ? 1 : 1,
                      }}
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

          {/* Recent Log */}
          <div className="col-span-3 bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center justify-between mb-5">
              <div>
                <h3 className="text-sm font-semibold text-foreground">Histórico de Sono</h3>
                <p className="text-xs text-muted-foreground mt-0.5">Últimas entradas</p>
              </div>
              <button className="text-xs text-primary hover:text-accent transition font-semibold">
                Ver tudo
              </button>
            </div>

            <div className="space-y-0.5">
              {LOG.map(({ date, bed, wake, dur, score }) => (
                <div
                  key={date}
                  className="flex items-center justify-between py-3.5 border-b border-border last:border-0 group cursor-pointer"
                >
                  <div>
                    <p className="text-sm font-medium text-foreground">{date}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      {bed} – {wake} · {dur}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="text-right">
                      <p className="text-sm font-bold" style={{ color: scoreColor(score) }}>
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
      </main>
    </div>
  );
}

// ─── Settings ────────────────────────────────────────────────────

function SettingsScreen({ onGo }: { onGo: (s: Screen) => void }) {
  const [notifs, setNotifs] = useState(true);
  const [bedReminder, setBedReminder] = useState(true);
  const [wakeAlarm, setWakeAlarm] = useState(false);
  const [weeklyReport, setWeeklyReport] = useState(true);
  const [sleepGoal, setSleepGoal] = useState(8);

  const inputCls =
    "w-full px-3.5 py-2.5 bg-secondary text-foreground border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition";
  const labelCls = "text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider";

  return (
    <div className="flex bg-background min-h-screen">
      <Sidebar screen="settings" onGo={onGo} />

      <main className="flex-1 overflow-y-auto p-8">
        <div className="max-w-2xl space-y-5">
          <div className="mb-8">
            <h1 className="text-2xl font-semibold text-foreground">Configurações</h1>
            <p className="text-sm text-muted-foreground mt-0.5">Personalize sua experiência de sono</p>
          </div>

          {/* Profile */}
          <section className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <User className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Perfil</h2>
            </div>
            <div className="flex items-center gap-4 mb-5">
              <div className="w-14 h-14 rounded-full bg-primary/20 flex items-center justify-center flex-shrink-0">
                <User className="w-7 h-7 text-primary" />
              </div>
              <div>
                <p className="font-semibold text-foreground">Rafael Silva</p>
                <p className="text-sm text-muted-foreground">rafael@email.com</p>
              </div>
              <button className="ml-auto text-xs text-primary hover:text-accent transition font-semibold">
                Editar foto
              </button>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className={labelCls}>Nome</label>
                <input type="text" defaultValue="Rafael Silva" className={inputCls} />
              </div>
              <div>
                <label className={labelCls}>Idade</label>
                <input type="number" defaultValue="28" className={inputCls} />
              </div>
            </div>
          </section>

          {/* Sleep Goals */}
          <section className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <Target className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Metas de Sono</h2>
            </div>

            <div className="space-y-5">
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm text-foreground">Meta de horas diárias</label>
                  <span className="text-sm font-bold text-primary">{sleepGoal}h</span>
                </div>
                <input
                  type="range"
                  min={5}
                  max={12}
                  value={sleepGoal}
                  onChange={(e) => setSleepGoal(Number(e.target.value))}
                  className="w-full accent-primary h-1.5 rounded-full"
                  style={{ accentColor: "#8b7ff8" }}
                />
                <div className="flex justify-between text-xs text-muted-foreground mt-1">
                  <span>5h</span>
                  <span>12h</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className={labelCls}>Hora de dormir</label>
                  <input type="time" defaultValue="23:00" className={inputCls} />
                </div>
                <div>
                  <label className={labelCls}>Hora de acordar</label>
                  <input type="time" defaultValue="07:00" className={inputCls} />
                </div>
              </div>
            </div>
          </section>

          {/* Notifications */}
          <section className="bg-card border border-border rounded-2xl p-6">
            <div className="flex items-center gap-2 mb-5">
              <Bell className="w-4 h-4 text-primary" />
              <h2 className="text-sm font-semibold text-foreground">Notificações</h2>
            </div>

            <div className="space-y-5">
              {[
                {
                  label: "Notificações gerais",
                  desc: "Receba atualizações e dicas do app",
                  value: notifs,
                  set: setNotifs,
                },
                {
                  label: "Lembrete de dormir",
                  desc: "Alerta 30 minutos antes da meta",
                  value: bedReminder,
                  set: setBedReminder,
                },
                {
                  label: "Alarme de despertar",
                  desc: "Acorde no momento ideal do ciclo",
                  value: wakeAlarm,
                  set: setWakeAlarm,
                },
                {
                  label: "Relatório semanal",
                  desc: "Resumo toda segunda-feira",
                  value: weeklyReport,
                  set: setWeeklyReport,
                },
              ].map(({ label, desc, value, set }) => (
                <div key={label} className="flex items-center justify-between gap-4">
                  <div>
                    <p className="text-sm font-medium text-foreground">{label}</p>
                    <p className="text-xs text-muted-foreground mt-0.5">{desc}</p>
                  </div>
                  <Toggle checked={value} onChange={set} />
                </div>
              ))}
            </div>
          </section>

          {/* Account */}
          <section className="bg-card border border-border rounded-2xl overflow-hidden">
            <div className="px-6 pt-6 pb-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-primary" />
                <h2 className="text-sm font-semibold text-foreground">Conta e Privacidade</h2>
              </div>
            </div>
            {["Alterar senha", "Exportar meus dados", "Política de privacidade", "Termos de uso"].map((label) => (
              <button
                key={label}
                className="w-full flex items-center justify-between px-6 py-3.5 hover:bg-secondary transition border-t border-border text-left"
              >
                <span className="text-sm text-foreground">{label}</span>
                <ChevronRight className="w-4 h-4 text-muted-foreground" />
              </button>
            ))}
          </section>

          <button className="w-full py-3 rounded-2xl text-sm font-medium text-red-400 bg-red-500/10 border border-red-500/15 hover:bg-red-500/15 transition">
            Excluir conta
          </button>
        </div>
      </main>
    </div>
  );
}

// ─── Root ─────────────────────────────────────────────────────────

export default function App() {
  const [screen, setScreen] = useState<Screen>("login");

  if (screen === "login") {
    return <LoginScreen onLogin={() => setScreen("dashboard")} onGo={setScreen} />;
  }
  if (screen === "register") {
    return <RegisterScreen onRegister={() => setScreen("dashboard")} onGo={setScreen} />;
  }
  if (screen === "dashboard") {
    return <Dashboard onGo={setScreen} />;
  }
  if (screen === "settings") {
    return <SettingsScreen onGo={setScreen} />;
  }
  return null;
}
