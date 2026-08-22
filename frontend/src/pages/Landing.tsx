import { ArrowRight, BarChart3, BedDouble, Check, Github, Instagram, Radio, X } from "lucide-react";
import { Link } from "react-router";

import { LinhaDeCota, Moldura, RotuloDeSecao } from "../components/Blueprint";
import { MarcaDoProduto } from "../components/MarcaDoProduto";
import { useAuth } from "../contexts/AuthContext";
import { NOME_PRODUTO } from "../lib/ui";

/**
 * Página pública (UI-11).
 *
 * É o endereço que vai no devlog, no perfil e no texto do TCC — quem chega
 * pelo link precisa entender o projeto antes de ver um formulário de login.
 *
 * O texto veio da landing Jinja anterior (`web-app/templates/index.html`),
 * com uma correção de honestidade: a versão antiga afirmava "✅ Firmware
 * validado no Wokwi", e o firmware mudou no FW-05 sem nunca ter sido
 * compilado. O teste de bancada (VIA-01) também não aconteceu. As duas
 * coisas aparecem agora como pendentes, não como concluídas.
 */

const REPOSITORIO = "https://github.com/vitormendes4072/DormioSmart";
const INSTAGRAM = "https://www.instagram.com/dormio.labs/";

const REGISTRA = [
  "Eventos de movimento durante o repouso",
  "Intensidade e horário de cada evento",
  "Períodos contínuos sem movimento",
  "Temperatura do próprio chip do sensor",
];

const NAO_REGISTRA = [
  "Estágios do sono (REM, profundo, leve)",
  "Diagnóstico clínico de qualquer natureza",
  "Apneia, ronco ou frequência cardíaca",
  "Temperatura do ambiente do quarto",
];

const ETAPAS = [
  {
    icone: BedDouble,
    titulo: "Sensor no travesseiro",
    texto:
      "ESP32 e MPU6050 embarcados no travesseiro captam aceleração sem contato com o corpo. O microcontrolador dorme em Deep Sleep e acorda ao detectar movimento.",
  },
  {
    icone: Radio,
    titulo: "Envio via Wi-Fi",
    texto:
      "A cada evento, o dispositivo transmite um pacote JSON por HTTPS, autenticado com um token próprio. O backend valida a leitura antes de persistir.",
  },
  {
    icone: BarChart3,
    titulo: "Visualização",
    texto:
      "O painel mostra a intensidade do movimento ao longo da captação, a contagem de eventos e o maior intervalo contínuo em repouso.",
  },
];

const FASE_1 = [
  { pronto: true, texto: "API com ingestão autenticada e persistência" },
  { pronto: true, texto: "Validação de entrada antes de gravar" },
  { pronto: true, texto: "Contas de usuário com isolamento por dono (RLS)" },
  { pronto: true, texto: "Painel de movimento em produção" },
  { pronto: true, texto: "Integração contínua com testes automatizados" },
  { pronto: false, texto: "Teste de bancada: o sinal separa movimento de repouso?" },
];

const FASE_2 = [
  "Montagem física no travesseiro",
  "Wake-on-Motion real pela interrupção do MPU6050",
  "Bateria, autonomia e segurança térmica",
  "Captação de uma noite real",
  "Validação contra dataset público de acelerometria",
];

export function Landing() {
  const { sessao } = useAuth();

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-4 flex items-center justify-between gap-4">
          <MarcaDoProduto className="h-7 sm:h-8" />
          {/* Quem já tem sessão é usuário: o painel merece destaque.
              Visitante sem conta não tem o que fazer lá dentro — nenhum
              dispositivo existe para parear — então o login fica discreto,
              onde quem procura encontra, sem ser a chamada da página. */}
          {sessao ? (
            <Link
              to="/dashboard"
              className="flex-shrink-0 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-sm font-semibold hover:bg-primary/90 transition"
            >
              Ir para o painel
            </Link>
          ) : (
            <Link
              to="/login"
              className="flex-shrink-0 text-sm font-medium text-muted-foreground hover:text-foreground transition"
            >
              Entrar
            </Link>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 sm:px-6 py-12 sm:py-16 space-y-16">
        {/* ── Hero ───────────────────────────────────────────────── */}
        <section>
          <p className="font-mono text-xs text-muted-foreground tracking-widest uppercase">
            TCC · Engenharia da Computação · 2026
          </p>
          <h1 className="mt-4 text-3xl sm:text-5xl font-semibold text-foreground tracking-tight">
            Monitoramento de movimento
            <span className="block text-primary">durante o repouso</span>
          </h1>
          <p className="mt-5 text-base sm:text-lg text-muted-foreground max-w-2xl">
            Um dispositivo embarcado de baixo consumo, instalado dentro do travesseiro, que
            registra eventos de movimento durante o repouso — sem nada em contato com o corpo.
          </p>

          {/* A chamada principal muda conforme quem está olhando.
              Sem sessão, oferecer "entrar no painel" seria prometer um painel
              que nasce vazio: não existe dispositivo para parear além do
              protótipo do autor. O que essa pessoa pode de fato fazer é
              acompanhar o desenvolvimento. */}
          <div className="mt-8 flex flex-wrap gap-3">
            {sessao ? (
              <Link
                to="/dashboard"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition"
              >
                Abrir o painel
                <ArrowRight className="w-4 h-4" />
              </Link>
            ) : (
              <a
                href={INSTAGRAM}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-2 px-6 py-3 rounded-xl bg-primary text-primary-foreground font-semibold hover:bg-primary/90 transition"
              >
                <Instagram className="w-4 h-4" />
                Acompanhar o desenvolvimento
              </a>
            )}
            <a
              href={REPOSITORIO}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-border text-foreground font-semibold hover:bg-secondary transition"
            >
              <Github className="w-4 h-4" />
              Ver no GitHub
            </a>
          </div>
        </section>

        <LinhaDeCota />

        {/* ── Escopo ─────────────────────────────────────────────── */}
        <section>
          <RotuloDeSecao numero="01" texto="Escopo declarado" />
          <h2 className="text-2xl font-semibold text-foreground">
            O que o aparelho faz — e o que não faz
          </h2>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            O sensor é um acelerômetro. Ele mede movimento, e apenas isso. Tudo que exigiria
            outro tipo de medição está fora, de propósito.
          </p>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Moldura>
              <h3 className="text-sm font-semibold text-foreground mb-4">Registra</h3>
              <ul className="space-y-2.5">
                {REGISTRA.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    <Check className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </Moldura>

            <Moldura>
              <h3 className="text-sm font-semibold text-foreground mb-4">Não registra</h3>
              <ul className="space-y-2.5">
                {NAO_REGISTRA.map((item) => (
                  <li key={item} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    <X className="w-4 h-4 text-destructive flex-shrink-0 mt-0.5" />
                    {item}
                  </li>
                ))}
              </ul>
            </Moldura>
          </div>
        </section>

        {/* ── Como funciona ──────────────────────────────────────── */}
        <section>
          <RotuloDeSecao numero="02" texto="Fluxo de dados" />
          <h2 className="text-2xl font-semibold text-foreground">Como funciona</h2>

          <div className="mt-6 grid gap-4 sm:grid-cols-3">
            {ETAPAS.map(({ icone: Icone, titulo, texto }, i) => (
              <Moldura key={titulo}>
                <span className="font-mono text-xs text-primary tracking-widest">
                  {String(i + 1).padStart(2, "0")}
                </span>
                <Icone className="w-5 h-5 text-primary mt-3" />
                <h3 className="mt-3 text-sm font-semibold text-foreground">{titulo}</h3>
                <p className="mt-2 text-sm text-muted-foreground">{texto}</p>
              </Moldura>
            ))}
          </div>

          <div className="mt-4 overflow-x-auto">
            <p className="font-mono text-xs text-muted-foreground whitespace-nowrap py-3">
              MPU6050 ──I2C──▸ ESP32 ──HTTPS──▸ API ──▸ Banco ──▸ Painel
            </p>
          </div>
        </section>

        {/* ── Status ─────────────────────────────────────────────── */}
        <section>
          <RotuloDeSecao numero="03" texto="Estado do projeto" />
          <h2 className="text-2xl font-semibold text-foreground">Onde está hoje</h2>

          <div className="mt-6 grid gap-4 sm:grid-cols-2">
            <Moldura>
              <h3 className="text-sm font-semibold text-foreground">Fase 1 — Software</h3>
              <ul className="mt-4 space-y-2.5">
                {FASE_1.map(({ pronto, texto }) => (
                  <li key={texto} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    {pronto ? (
                      <Check className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
                    ) : (
                      <span className="w-4 h-4 flex-shrink-0 mt-0.5 font-mono text-xs text-muted-foreground">
                        ○
                      </span>
                    )}
                    {texto}
                  </li>
                ))}
              </ul>
            </Moldura>

            <Moldura>
              <h3 className="text-sm font-semibold text-foreground">Fase 2 — Protótipo físico</h3>
              <ul className="mt-4 space-y-2.5">
                {FASE_2.map((texto) => (
                  <li key={texto} className="flex items-start gap-2.5 text-sm text-muted-foreground">
                    <span className="w-4 h-4 flex-shrink-0 mt-0.5 font-mono text-xs">○</span>
                    {texto}
                  </li>
                ))}
              </ul>
            </Moldura>
          </div>

          <p className="mt-4 text-xs text-muted-foreground">
            Itens sem marca ainda não foram feitos. O trabalho é documentado publicamente,
            inclusive o que não funcionou.
          </p>
        </section>
      </main>

      <footer className="border-t border-border">
        <div className="mx-auto max-w-5xl px-4 sm:px-6 py-8 space-y-6">
          {/* Assinatura da Dormio Labs.
              A Labs é o laboratório; o Smart Dormio é o produto. Por isso a
              marca da Labs aparece como assinatura no rodapé, e não no
              cabeçalho — quem entra está usando o produto, não o laboratório.

              A cor está fixa dentro do próprio SVG, de propósito. Carregado via
              <img>, `currentColor` não herda nada da página e resolveria para
              preto. E cor de marca não deve mudar com o tema: é identidade,
              não decoração. O arquivo tem um único `fill`, então recolorir
              continua sendo uma troca de uma linha se um dia for inlinado. */}
          <div className="flex items-center gap-3">
            <span className="text-xs text-muted-foreground">um projeto da</span>
            {/* A marca da Labs leva ao perfil dela — é onde o trabalho é
                documentado publicamente. Clicar no logo de uma organização e
                chegar até ela é o comportamento esperado. */}
            <a
              href={INSTAGRAM}
              target="_blank"
              rel="noreferrer"
              aria-label="Dormio Labs no Instagram"
              className="transition hover:opacity-70"
            >
              <img src="/dormio-labs.svg" alt="Dormio Labs" className="h-5 w-auto" />
            </a>
          </div>

          <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground">
            {NOME_PRODUTO} — registra indícios de movimento por acelerometria. Não realiza
            estadiamento de sono nem diagnóstico clínico.
          </p>
          <div className="flex items-center gap-4">
            <a
              href={INSTAGRAM}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-accent transition font-semibold"
            >
              <Instagram className="w-3.5 h-3.5" />
              @dormio.labs
            </a>
            <a
              href={REPOSITORIO}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-accent transition font-semibold"
            >
              <Github className="w-3.5 h-3.5" />
              Código aberto
            </a>
          </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
