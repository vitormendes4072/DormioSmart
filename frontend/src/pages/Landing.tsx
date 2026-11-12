import { ArrowRight, BarChart3, BedDouble, Check, Github, Instagram, Moon, Radio, Sun, X } from "lucide-react";
import { Link, useSearchParams } from "react-router";

import { Moldura, RotuloDeSecao } from "../components/Blueprint";
import { MarcaDoProduto } from "../components/MarcaDoProduto";
import { Revelar } from "../components/Revelar";
import { TracadoDeMovimento } from "../components/TracadoDeMovimento";
import { useAuth } from "../contexts/AuthContext";
import { useTema } from "../hooks/useTema";
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
 *
 * ✏️ 03/11 (UI-23): a página ainda descrevia a arquitetura abandonada em 30/10
 * (Deep Sleep acordando por movimento, um envio a cada evento) e dava como
 * pendente a validação por dados públicos, fechada em 18/09. Os textos foram
 * refeitos contra o `ARQ-01` e o backlog, e `Landing.test.tsx` reprova os
 * termos da arquitetura antiga.
 *
 * O movimento da página (UI-15) é deliberadamente contido: entrada suave dos
 * blocos ao aparecerem, elevação de 1px nos botões, e um único elemento
 * animado de forma contínua — o traçado de aceleração do hero, que existe
 * para mostrar o critério de movimento em vez de descrevê-lo. Tudo desliga
 * sob `prefers-reduced-motion`.
 */

const REPOSITORIO = "https://github.com/vitormendes4072/DormioSmart";
const INSTAGRAM = "https://www.instagram.com/dormio.labs/";

/* A elevação no hover é de 1px — o suficiente para o botão responder ao
   cursor, longe de chamar atenção para si. No `:active` ele volta ao lugar,
   que é o gesto de afundar sob o clique. */
const BOTAO_BASE =
  "group inline-flex items-center gap-2 px-6 py-3 rounded-xl font-semibold " +
  "transition-all duration-200 hover:-translate-y-0.5 active:translate-y-0";
const BOTAO_PRIMARIO =
  `${BOTAO_BASE} bg-primary text-primary-foreground hover:bg-primary/90 ` +
  "hover:shadow-lg hover:shadow-primary/25";
const BOTAO_SECUNDARIO =
  `${BOTAO_BASE} border border-border text-foreground hover:bg-secondary hover:border-primary/40`;

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
      "ESP32 e MPU6050 embarcados no travesseiro captam aceleração sem contato com o corpo. O microcontrolador fica em sono leve e lê em rajadas a memória interna do sensor, a 50 Hz, resumindo cada 30 s de movimento.",
  },
  {
    icone: Radio,
    titulo: "Envio via Wi-Fi",
    texto:
      "A cada 10 minutos, o dispositivo envia em lote o que acumulou, por HTTPS e com um token próprio; sem rede, guarda na memória flash e envia depois. O backend valida cada leitura antes de gravar.",
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
  { pronto: true, texto: "Coleta pelo acelerômetro do celular, no navegador" },
  { pronto: true, texto: "Modelo de sono × vigília validado em dados públicos de acelerometria" },
  { pronto: true, texto: "Firmware da arquitetura de captação testado no computador (ainda não na placa)" },
  { pronto: false, texto: "Teste de bancada: o sinal separa movimento de repouso?" },
];

const FASE_2 = [
  "Montagem física no travesseiro",
  "Firmware rodando na placa: leitura da FIFO e fila na flash",
  "Bateria, autonomia e segurança térmica",
  "Captação de uma noite real",
  "Calibrar o modelo com a noite captada",
];

function LandingLeve() {
  const { sessao } = useAuth();
  const { aplicado, definirPreferencia } = useTema();
  const temaEscuro = aplicado === "dark";

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-4 py-4 sm:px-6">
          <MarcaDoProduto className="h-7 sm:h-8" />
          <nav aria-label="Seções da página" className="hidden gap-6 text-sm text-muted-foreground md:flex">
            <a className="hover:text-foreground" href="#como-funciona">Como funciona</a>
            <a className="hover:text-foreground" href="#tecnologia">Tecnologia</a>
          </nav>
          <div className="flex items-center gap-3 text-sm">
            <button
              type="button"
              aria-label={temaEscuro ? "Ativar tema claro" : "Ativar tema escuro"}
              onClick={() => definirPreferencia(temaEscuro ? "claro" : "escuro")}
              className="inline-flex size-10 items-center justify-center rounded-lg border border-border hover:bg-secondary"
            >
              {temaEscuro ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
            </button>
            {sessao ? (
              <Link to="/dashboard" className="font-semibold text-primary">Ir para o painel</Link>
            ) : (
              <>
                <Link to="/login" className="font-semibold text-foreground">Entrar</Link>
                <Link to="/cadastro" className="hidden rounded-lg bg-primary px-3 py-2 font-semibold text-primary-foreground sm:inline-flex">
                  Criar conta
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main>
        <section aria-labelledby="titulo-landing" className="border-b border-border bg-gradient-to-br from-primary/10 via-background to-background">
          <div className="mx-auto grid max-w-6xl items-center gap-10 px-4 py-12 sm:px-6 lg:grid-cols-[1fr_1fr] lg:gap-14 lg:py-24">
            <Revelar>
              <p className="font-mono text-xs uppercase tracking-widest text-primary">Smart Dormio · Protótipo acadêmico</p>
              <h1 id="titulo-landing" className="mt-4 text-4xl font-semibold tracking-tight text-foreground sm:text-5xl">
                Acompanhe os movimentos <span className="text-primary">durante o repouso.</span>
              </h1>
              <p className="mt-5 max-w-lg text-base leading-relaxed text-muted-foreground sm:text-lg">
                Um sensor no travesseiro registra variações de movimento durante o repouso,
                sem contato com o corpo.
              </p>
              <div className="mt-7 flex flex-wrap gap-3">
                <a href="#demonstracao" className={BOTAO_PRIMARIO}>
                  Ver exemplo de medição <ArrowRight className="size-4" aria-hidden />
                </a>
                <a href="#como-funciona" className={BOTAO_SECUNDARIO}>Como funciona</a>
              </div>
            </Revelar>

            <Revelar atraso={110} className="min-w-0">
              <div id="demonstracao" className="scroll-mt-6 rounded-2xl border border-border bg-card p-4 shadow-lg shadow-primary/10 sm:p-6">
                <p className="text-xs font-semibold uppercase tracking-wider text-primary">Demonstração</p>
                <h2 className="mb-4 mt-2 text-xl font-semibold text-foreground">Movimento durante o repouso</h2>
                <TracadoDeMovimento />
                <p className="mt-3 text-sm text-muted-foreground">
                  O traçado ilustra como um pico de aceleração cruza o limiar de movimento.
                </p>
              </div>
            </Revelar>
          </div>
        </section>

        <div className="mx-auto max-w-5xl space-y-16 px-4 py-12 sm:px-6 sm:py-16">
          {/* ── Escopo ─────────────────────────────────────────────── */}
          <section>
            <Revelar>
              <RotuloDeSecao numero="01" texto="Escopo declarado" />
              <h2 className="text-2xl font-semibold text-foreground">
                O que o aparelho faz — e o que não faz
              </h2>
              <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
                O sensor é um acelerômetro. Ele mede movimento, e apenas isso. Tudo que exigiria
                outro tipo de medição está fora, de propósito.
              </p>
            </Revelar>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <Moldura atraso={0}>
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

              <Moldura atraso={110}>
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
          <section id="como-funciona">
            <Revelar>
              <RotuloDeSecao numero="02" texto="Fluxo de dados" />
              <h2 className="text-2xl font-semibold text-foreground">Como funciona</h2>
            </Revelar>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              {ETAPAS.map(({ icone: Icone, titulo, texto }, i) => (
                <Moldura key={titulo} atraso={i * 110}>
                  <span className="font-mono text-xs text-primary tracking-widest">
                    {String(i + 1).padStart(2, "0")}
                  </span>
                  <Icone className="w-5 h-5 text-primary mt-3 transition-transform duration-300 group-hover:scale-110" />
                  <h3 className="mt-3 text-sm font-semibold text-foreground">{titulo}</h3>
                  <p className="mt-2 text-sm text-muted-foreground">{texto}</p>
                </Moldura>
              ))}
            </div>

            {/* Um brilho percorre a linha no sentido do dado. A cor do texto
                continua declarada aqui: é ela que aparece se o navegador não
                suportar `background-clip: text`, ou sob redução de movimento. */}
            <div className="mt-4 overflow-x-auto">
              <p className="fluxo-animado font-mono text-xs text-muted-foreground whitespace-nowrap py-3">
                MPU6050 ──I2C──▸ ESP32 ──HTTPS──▸ API ──▸ Banco ──▸ Painel
              </p>
            </div>
          </section>

          {/* ── Status ─────────────────────────────────────────────── */}
          <section id="tecnologia">
            <Revelar>
              <RotuloDeSecao numero="03" texto="Estado do projeto" />
              <h2 className="text-2xl font-semibold text-foreground">Onde está hoje</h2>
            </Revelar>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <Moldura atraso={0}>
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

              <Moldura atraso={110}>
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
          <section className="flex flex-wrap items-center justify-between gap-5 rounded-2xl border border-border bg-secondary/40 p-6 sm:p-8">
            <div>
              <h2 className="text-2xl font-semibold text-foreground">Conheça o Smart Dormio</h2>
              <p className="mt-2 text-sm text-muted-foreground">Explore um exemplo de medição ou acesse o painel com sua conta.</p>
            </div>
            <div className="flex flex-wrap gap-3">
              <a href="#demonstracao" className={BOTAO_PRIMARIO}>Ver exemplo</a>
              <Link to={sessao ? "/dashboard" : "/cadastro"} className={BOTAO_SECUNDARIO}>
                {sessao ? "Abrir painel" : "Criar conta"}
              </Link>
            </div>
          </section>
        </div>
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
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-accent transition-colors duration-200 font-semibold"
            >
              <Instagram className="w-3.5 h-3.5" />
              @dormio.labs
            </a>
            <a
              href={REPOSITORIO}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 text-xs text-primary hover:text-accent transition-colors duration-200 font-semibold"
            >
              <Github className="w-3.5 h-3.5" />
              Código aberto
            </a>
            <Link
              to="/privacidade"
              className="text-xs text-primary hover:text-accent transition-colors duration-200 font-semibold"
            >
              Privacidade
            </Link>
          </div>
          </div>
        </div>
      </footer>
    </div>
  );
}


/** A apresentação completa usa o HTML do protótipo em um documento isolado. */
export function Landing() {
  const { sessao } = useAuth();
  const [parametros] = useSearchParams();

  if (parametros.get("apresentacao") === "leve") return <LandingLeve />;

  return (
    <iframe
      title="Smart Dormio — página inicial"
      src={sessao ? "/landing-prototipo.html?sessao=1" : "/landing-prototipo.html"}
      sandbox="allow-scripts allow-top-navigation-by-user-activation allow-popups allow-popups-to-escape-sandbox allow-downloads"
      className="block h-dvh w-full border-0"
    />
  );
}
