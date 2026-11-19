import { useCallback, useEffect, useLayoutEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { Link, useNavigate } from "react-router";

import { useTema } from "../hooks/useTema";
import {
  NOME_MAX,
  emailValido,
  inscreverNaListaDeEspera,
  sugerirEmail,
  type ResultadoDaInscricao,
} from "../lib/listaDeEspera";
import "./ListaDeEspera.css";

/**
 * A lista de espera do lançamento (UI-14).
 *
 * Quem ainda não tem conta deixa o e-mail para ser avisado do lançamento e
 * convidado para os primeiros testes. O desenho foi aprovado pelo autor numa
 * prévia em 17/11 e segue a estética da landing.
 *
 * A ideia que organiza a página: **o movimento vira repouso.** No alto do
 * cartão, um sinal ilustrativo oscila; cada tecla vira um pico, como um corpo
 * que vira na cama. Quando a pessoa entra na lista, a linha se acalma, fica
 * verde e o rótulo passa a "Repouso". A faixa diz que é ilustração: não é
 * medida de nada.
 *
 * O formulário se abre por partes (o resto aparece quando o e-mail está
 * certo), o botão diz o que falta, e a página inteira funciona parada para quem
 * pede menos movimento no sistema.
 */

const PASSOS = ["E-mail", "Confirmações", "Pronto"] as const;
const DICA_DO_SINAL = "Experimente digitar: cada tecla vira um pico, como um corpo que vira na cama.";
const DICA_DO_REPOUSO = "Pronto. Agora é só descansar: avisamos quando chegar a hora.";
const ENDERECO = "https://dormio-smart.vercel.app/lista-de-espera";
const INSTAGRAM = "https://www.instagram.com/dormio.labs/";
const REPOSITORIO = "https://github.com/vitormendes4072/DormioSmart";

function movimentoReduzido(): boolean {
  // Sem `matchMedia` (testes, navegador antigo), a página fica parada: é o modo seguro.
  return typeof window.matchMedia !== "function" || window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** O sinal do travesseiro, ilustrativo. Devolve a função que dá um "chacoalhão". */
function useSinal(caminho: React.RefObject<SVGPathElement | null>, emRepouso: boolean) {
  const estado = useRef({ amostras: new Array<number>(90).fill(0), impulso: 0, calma: 0, fase: 0 });

  useEffect(() => {
    estado.current.calma = emRepouso ? 1 : 0;
    if (emRepouso) estado.current.impulso = 0;
  }, [emRepouso]);

  useEffect(() => {
    const desenhar = () => {
      const { amostras } = estado.current;
      let d = "";
      amostras.forEach((v, i) => {
        const x = (i / (amostras.length - 1)) * 400;
        const y = Math.max(2, Math.min(44, 30 - v * 22));
        d += `${i ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
      });
      caminho.current?.setAttribute("d", d);
    };
    desenhar();
    if (movimentoReduzido() || typeof requestAnimationFrame !== "function") return;
    let quadro = 0;
    const passo = () => {
      const s = estado.current;
      s.fase += 0.06;
      const quieto = 1 - s.calma;
      const ruido = (Math.sin(s.fase * 1.7) + Math.sin(s.fase * 3.1 + 1) * 0.6) * 0.035 * quieto
        + (Math.random() - 0.5) * 0.05 * quieto;
      const pico = s.impulso * (Math.random() > 0.5 ? 1 : -1) * (0.55 + Math.random() * 0.45);
      s.amostras.push(ruido + pico);
      s.amostras.shift();
      s.impulso *= 0.82;
      desenhar();
      quadro = requestAnimationFrame(passo);
    };
    quadro = requestAnimationFrame(passo);
    return () => cancelAnimationFrame(quadro);
  }, [caminho]);

  return useCallback((forca: number) => {
    const s = estado.current;
    s.impulso = Math.min(s.impulso + forca, 1.25);
    s.calma = 0;
  }, []);
}

function mensagemDoResultado(resultado: ResultadoDaInscricao): { tom: "ambar" | "vermelho"; texto: string } | null {
  switch (resultado.tipo) {
    case "lista_cheia":
      return { tom: "ambar", texto: "Recebemos muitas inscrições agora. Tente de novo daqui a pouco." };
    case "texto_mudou":
      return { tom: "ambar", texto: "O texto desta página foi atualizado. Recarregue a página e confira antes de enviar." };
    case "invalido":
      return { tom: "vermelho", texto: "Confira os dados: o servidor não aceitou o pedido." };
    case "indisponivel":
      return { tom: "vermelho", texto: "Não conseguimos registrar agora. Seu e-mail não foi guardado; tente de novo em alguns minutos." };
    default:
      return null;
  }
}

export function ListaDeEspera() {
  const navegar = useNavigate();
  const { aplicado, definirPreferencia } = useTema();
  const temaEscuro = aplicado === "dark";

  const [email, setEmail] = useState("");
  const [nome, setNome] = useState("");
  const [consente, setConsente] = useState(false);
  const [maior, setMaior] = useState(false);
  const [isca, setIsca] = useState("");
  const [abriu, setAbriu] = useState(false);
  const [erroEmail, setErroEmail] = useState("");
  const [tremer, setTremer] = useState(0);
  const [sugestao, setSugestao] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [alerta, setAlerta] = useState<{ tom: "ambar" | "vermelho"; texto: string } | null>(null);
  const [fase, setFase] = useState<"formulario" | "saindo" | "feito">("formulario");
  const [copiado, setCopiado] = useState(false);
  const [emailInscrito, setEmailInscrito] = useState("");
  const [primeiroNome, setPrimeiroNome] = useState("");

  const caminhoDoSinal = useRef<SVGPathElement>(null);
  const cartao = useRef<HTMLDivElement>(null);
  const palco = useRef<HTMLDivElement>(null);
  const cenaFeito = useRef<HTMLDivElement>(null);
  const tituloFeito = useRef<HTMLHeadingElement>(null);
  const campoEmail = useRef<HTMLInputElement>(null);
  const campoNome = useRef<HTMLInputElement>(null);
  const caixaConsente = useRef<HTMLInputElement>(null);
  const botao = useRef<HTMLButtonElement>(null);
  const orbitaUm = useRef<HTMLDivElement>(null);
  const orbitaDois = useRef<HTMLDivElement>(null);

  const feito = fase !== "formulario";
  const chacoalhar = useSinal(caminhoDoSinal, feito);

  const emailOk = emailValido(email);
  const confirmacoes = (consente ? 1 : 0) + (maior ? 1 : 0);
  const pronto = emailOk && confirmacoes === 2;
  const abrirResto = abriu || emailOk;

  const rotuloDoBotao = enviando
    ? "Guardando seu lugar…"
    : !emailOk
      ? "Comece pelo e-mail"
      : confirmacoes === 0
        ? "Marque as duas confirmações"
        : confirmacoes === 1
          ? "Falta uma confirmação"
          : "Entrar na lista de espera";

  const progresso = [
    { p: emailOk ? 1 : Math.min(email.length / 12, 0.85), estado: emailOk ? "ok" : "ativo" },
    { p: confirmacoes / 2, estado: !emailOk ? "" : confirmacoes === 2 ? "ok" : "ativo" },
    { p: pronto ? 1 : 0, estado: pronto ? "ativo" : "" },
  ];

  /** Num notebook, o cartão aberto passa da altura da tela: traz o botão para a vista. */
  const mostrarBotao = useCallback(() => {
    const limite = botao.current?.getBoundingClientRect();
    if (limite && limite.bottom > window.innerHeight - 12) {
      window.scrollBy({ top: limite.bottom - window.innerHeight + 24, behavior: movimentoReduzido() ? "auto" : "smooth" });
    }
  }, []);

  function conferirEmail() {
    if (email.trim() && !emailOk) {
      setErroEmail("Confira o e-mail: ele parece incompleto.");
      setTremer((n) => n + 1);
    }
    setSugestao(sugerirEmail(email));
  }

  function aoTeclar(e: KeyboardEvent<HTMLFormElement>) {
    if (e.key.length === 1) chacoalhar(0.45);
    else if (e.key === "Backspace") chacoalhar(0.25);
  }

  function enterNoEmail(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    if (!emailOk) {
      conferirEmail();
      return;
    }
    setSugestao(sugerirEmail(email));
    setAbriu(true);
    campoNome.current?.focus({ preventScroll: true });
    window.setTimeout(mostrarBotao, movimentoReduzido() ? 0 : 620);
  }

  function enterNoNome(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key !== "Enter") return;
    e.preventDefault();
    caixaConsente.current?.focus();
  }

  function marcar(definir: (v: boolean) => void, valor: boolean) {
    definir(valor);
    chacoalhar(0.9);
    window.setTimeout(mostrarBotao, 0);
  }

  async function enviar(e: FormEvent) {
    e.preventDefault();
    if (!pronto || enviando) return;
    setAlerta(null);
    setEnviando(true);
    const resultado = await inscreverNaListaDeEspera({ email, nome, consentimento: consente, maioridade: maior, site: isca });
    setEnviando(false);
    if (resultado.tipo !== "inscrito") {
      setAlerta(mensagemDoResultado(resultado));
      return;
    }
    setEmailInscrito(email.trim().toLowerCase());
    setPrimeiroNome(nome.trim().split(/\s+/)[0] ?? "");
    if (palco.current) palco.current.style.height = `${palco.current.offsetHeight}px`;
    setFase("saindo");
    window.setTimeout(() => setFase("feito"), movimentoReduzido() ? 0 : 300);
  }

  // A troca de cena: a altura do cartão vai da do formulário à do sucesso, e o foco
  // vai ao título, para o leitor de tela anunciar o resultado.
  useLayoutEffect(() => {
    if (fase !== "feito") return;
    const caixa = palco.current;
    if (caixa && cenaFeito.current) caixa.style.height = `${cenaFeito.current.offsetHeight}px`;
    const fim = window.setTimeout(() => {
      if (caixa) caixa.style.height = "";
      tituloFeito.current?.focus({ preventScroll: true });
      const topo = cartao.current?.getBoundingClientRect().top ?? 0;
      if (topo < 0) cartao.current?.scrollIntoView({ behavior: movimentoReduzido() ? "auto" : "smooth", block: "start" });
    }, movimentoReduzido() ? 0 : 560);
    return () => window.clearTimeout(fim);
  }, [fase]);

  // As órbitas seguem o cursor de leve, só com mouse e com movimento permitido.
  useEffect(() => {
    if (movimentoReduzido() || !window.matchMedia("(pointer: fine)").matches) return;
    const mover = (e: PointerEvent) => {
      const dx = e.clientX / window.innerWidth - 0.5;
      const dy = e.clientY / window.innerHeight - 0.5;
      if (orbitaUm.current) orbitaUm.current.style.transform = `translate(${dx * 16}px, ${dy * 16}px)`;
      if (orbitaDois.current) orbitaDois.current.style.transform = `translate(${dx * -10}px, ${dy * -10}px)`;
    };
    window.addEventListener("pointermove", mover);
    return () => window.removeEventListener("pointermove", mover);
  }, []);

  function irAoCartao(e: React.MouseEvent) {
    e.preventDefault();
    cartao.current?.scrollIntoView({ behavior: movimentoReduzido() ? "auto" : "smooth", block: "start" });
    if (!feito) window.setTimeout(() => campoEmail.current?.focus({ preventScroll: true }), movimentoReduzido() ? 0 : 550);
  }

  async function compartilhar() {
    const dados = {
      title: "Smart Dormio",
      text: "Um sensor no travesseiro que registra o movimento durante o repouso. Entre na lista de espera:",
      url: ENDERECO,
    };
    try {
      if (typeof navigator.share === "function") {
        await navigator.share(dados);
      } else {
        await navigator.clipboard.writeText(ENDERECO);
        setCopiado(true);
        window.setTimeout(() => setCopiado(false), 2200);
      }
    } catch {
      // A pessoa fechou o menu de compartilhar, ou o navegador recusou: nada a fazer.
    }
  }

  return (
    <div className="le">
      <div className="le-wrap">
        <header className="le-nav">
          <Link className="le-logo" to="/" aria-label="Smart Dormio, página inicial">
            <img src="/smart-dormio.svg" alt="Smart Dormio" />
          </Link>
          <div className="le-acoes">
            <button
              type="button"
              className="le-iconbtn"
              aria-label={temaEscuro ? "Ativar tema claro" : "Ativar tema escuro"}
              onClick={() => definirPreferencia(temaEscuro ? "claro" : "escuro")}
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" />
              </svg>
            </button>
            <Link className="le-btn contorno" to="/">Conhecer o projeto</Link>
          </div>
        </header>

        <main>
          <section className="le-hero">
            <div>
              <span className="le-kicker le-sobe" style={{ "--i": 0 } as React.CSSProperties}>
                <span className="le-ponto" />Lista de espera · primeiros usuários
              </span>
              <h1 className="le-sobe" style={{ "--i": 1 } as React.CSSProperties}>
                Seja um dos primeiros<br /><em>a dormir com o Smart Dormio.</em>
              </h1>
              <p className="le-lead le-sobe" style={{ "--i": 2 } as React.CSSProperties}>
                Um sensor dentro do travesseiro registra o movimento durante o repouso, sem nada no pulso
                e sem contato com o corpo. Ele ainda está em desenvolvimento: deixe seu e-mail e avisamos
                quando o travesseiro e o app estiverem prontos para os primeiros usuários.
              </p>
              <a className="le-btn primario grande le-so-celular le-sobe" style={{ "--i": 3 } as React.CSSProperties} href="#lista" onClick={irAoCartao}>
                Quero entrar na lista <span aria-hidden="true">↓</span>
              </a>
              <div className="le-confianca le-sobe" style={{ "--i": 3 } as React.CSSProperties}>
                <span className="le-check" aria-hidden="true">✓</span>
                Um aviso no lançamento e o convite para os primeiros testes. Nada de propaganda, nada repassado a terceiros.
              </div>
              <div className="le-spec le-sobe" style={{ "--i": 4 } as React.CSSProperties} aria-label="Como funciona a lista">
                <div><strong>Só o e-mail</strong><span>O nome é opcional</span></div>
                <div><strong>Só o aviso</strong><span>Lançamento e convite</span></div>
                <div><strong>12 meses</strong><span>Prazo máximo na lista</span></div>
              </div>
              <p className="le-spec-nota le-sobe" style={{ "--i": 5 } as React.CSSProperties}>
                Sem data de lançamento definida: o protótipo ainda passa por testes de bancada e de noite real.
              </p>
            </div>

            <div className="le-visual">
              <div className="le-orbita um" ref={orbitaUm} />
              <div className="le-orbita dois" ref={orbitaDois} />
              <div id="lista" ref={cartao} className={`le-cartao le-sobe${pronto && !feito ? " atento" : ""}`} style={{ "--i": 2 } as React.CSSProperties}>
                <div className="le-cartao-topo">
                  <img src="/smart-dormio.svg" alt="Smart Dormio" />
                  <span className="le-pilula">Lista de espera</span>
                </div>

                <div className={`le-sinal${feito ? " repouso" : ""}`} aria-hidden="true">
                  <div className="le-sinal-topo">
                    <span>Sinal do travesseiro · ilustração</span>
                    <span className="le-sinal-estado"><i />{feito ? "Repouso" : "Movimento"}</span>
                  </div>
                  <svg viewBox="0 0 400 46" preserveAspectRatio="none">
                    <line x1="0" x2="400" y1="14" y2="14" />
                    <path ref={caminhoDoSinal} />
                  </svg>
                  <div className="le-sinal-dica">{feito ? DICA_DO_REPOUSO : DICA_DO_SINAL}</div>
                </div>

                <div className="le-palco" ref={palco}>
                  {fase !== "feito" ? (
                    <div className={`le-cena${fase === "saindo" ? " sai" : ""}`}>
                      <form onSubmit={enviar} onKeyDown={aoTeclar} noValidate>
                        <div className="le-passos" aria-hidden="true">
                          {PASSOS.map((rotulo, i) => (
                            <div key={rotulo} className={`le-passo ${progresso[i].estado}`} style={{ "--p": progresso[i].p } as React.CSSProperties}>
                              <b />{rotulo}
                            </div>
                          ))}
                        </div>
                        <h2>Quero ser avisado</h2>
                        <p className="le-sub">Leva menos de um minuto.</p>

                        <div key={tremer} className={`le-campo${emailOk ? " valido" : ""}${erroEmail ? " invalido" : ""}`}>
                          <input
                            id="le-email"
                            ref={campoEmail}
                            type="email"
                            inputMode="email"
                            autoComplete="email"
                            placeholder=" "
                            enterKeyHint="next"
                            maxLength={254}
                            value={email}
                            aria-invalid={erroEmail ? true : undefined}
                            aria-describedby="le-email-msg"
                            onChange={(e) => {
                              setEmail(e.target.value);
                              setSugestao(null);
                              if (erroEmail && emailValido(e.target.value)) setErroEmail("");
                            }}
                            onBlur={conferirEmail}
                            onKeyDown={enterNoEmail}
                          />
                          <label htmlFor="le-email">Seu e-mail</label>
                          <span className="le-marca" aria-hidden="true">✓</span>
                        </div>
                        <div id="le-email-msg" aria-live="polite">
                          {erroEmail && <p className="le-campo-msg">{erroEmail}</p>}
                          {sugestao && (
                            <p className="le-sugestao">
                              Você quis dizer{" "}
                              <button type="button" onClick={() => { setEmail(sugestao); setSugestao(null); setErroEmail(""); campoEmail.current?.focus(); }}>
                                {sugestao}
                              </button>
                              ?
                            </p>
                          )}
                        </div>
                        {!abrirResto && <p className="le-depois">Depois, o nome (se quiser) e duas confirmações rápidas.</p>}

                        <div className={`le-abre${abrirResto ? " aberto" : ""}`} onFocus={() => window.setTimeout(mostrarBotao, movimentoReduzido() ? 0 : 420)}>
                          <div>
                            <div className="le-campo">
                              <input
                                id="le-nome"
                                ref={campoNome}
                                type="text"
                                autoComplete="given-name"
                                placeholder=" "
                                enterKeyHint="done"
                                maxLength={NOME_MAX}
                                value={nome}
                                onChange={(e) => setNome(e.target.value)}
                                onKeyDown={enterNoNome}
                              />
                              <label htmlFor="le-nome">Como prefere ser chamado <span className="le-opcional">(opcional)</span></label>
                            </div>

                            <div className="le-isca" aria-hidden="true">
                              <label>
                                Site
                                <input type="text" name="site" tabIndex={-1} autoComplete="off" value={isca} onChange={(e) => setIsca(e.target.value)} />
                              </label>
                            </div>

                            <label className="le-toggle">
                              <input ref={caixaConsente} type="checkbox" checked={consente} onChange={(e) => marcar(setConsente, e.target.checked)} />
                              <span className="le-caixa" aria-hidden="true"><svg viewBox="0 0 12 12"><path d="M2 6.5 5 9l5-6" /></svg></span>
                              <span>
                                Concordo que o Smart Dormio guarde meu e-mail (e o nome, se eu informar){" "}
                                <b>só para me avisar do lançamento e me convidar para os primeiros testes</b>. Posso sair da
                                lista quando quiser.
                              </span>
                            </label>
                            <label className="le-toggle">
                              <input type="checkbox" checked={maior} onChange={(e) => marcar(setMaior, e.target.checked)} />
                              <span className="le-caixa" aria-hidden="true"><svg viewBox="0 0 12 12"><path d="M2 6.5 5 9l5-6" /></svg></span>
                              <span>Tenho 18 anos ou mais.</span>
                            </label>
                          </div>
                        </div>

                        <button ref={botao} type="submit" className="le-btn primario grande le-enviar" disabled={!pronto || enviando}>
                          {enviando && <span className="le-giro" aria-hidden="true" />}
                          <span>{rotuloDoBotao}</span>
                          {!enviando && <span aria-hidden="true">↗</span>}
                        </button>
                        {alerta && <p role="alert" className={`le-alerta ${alerta.tom}`}>{alerta.texto}</p>}
                        <p className="le-rodape-cartao">
                          Seus dados não são compartilhados nem usados para outra coisa, e são apagados no máximo 12 meses
                          depois da inscrição. Detalhes na <Link to="/privacidade">política de privacidade</Link>.
                        </p>
                      </form>
                    </div>
                  ) : (
                    <div className="le-cena le-feito entra" ref={cenaFeito}>
                      <div className="le-selo"><svg viewBox="0 0 28 28" aria-hidden="true"><path d="M6 14.5 11.5 20 22 8" /></svg></div>
                      <h2 ref={tituloFeito} tabIndex={-1}>{primeiroNome ? `${primeiroNome}, você está` : "Você está"} na lista.</h2>
                      <p>
                        Vamos escrever para <b style={{ color: "var(--le-text)" }}>{emailInscrito}</b> quando o Smart Dormio estiver
                        pronto para os primeiros usuários. Se o e-mail já estava na lista, nada muda.
                      </p>
                      <p>Mudou de ideia? Peça a remoção pelo contato da <Link className="le-link" to="/privacidade">política de privacidade</Link>.</p>
                      <div className="le-compartilhar">
                        <p>Conhece alguém que ia gostar de acompanhar a própria noite? Mande o link.</p>
                        <button type="button" className="le-btn primario grande" onClick={compartilhar}>
                          {copiado ? "Link copiado" : "Compartilhar o Smart Dormio"} <span aria-hidden="true">↗</span>
                        </button>
                        <a className="le-link" href={INSTAGRAM} target="_blank" rel="noreferrer">Acompanhe o projeto no Instagram, @dormio.labs</a>
                      </div>
                      <button type="button" className="le-btn contorno" onClick={() => navegar("/")}>Voltar à página inicial</button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </section>

          <section className="le-secao">
            <div className="le-limite">
              <div className="le-limite-marca" aria-hidden="true">i</div>
              <div>
                <span className="le-sobrelinha">Transparência sobre as medições</span>
                <p>
                  O Smart Dormio registra indícios de movimento por acelerometria. Ele <b>não</b> faz estadiamento de sono nem
                  diagnóstico clínico, e não é um dispositivo médico.
                </p>
              </div>
            </div>
          </section>
        </main>

        <footer className="le-rodape">
          <div className="le-rodape-marca"><img src="/dormio-labs.svg" alt="Dormio Labs" /><span>Desenvolvido na Dormio Labs</span></div>
          <div className="le-rodape-links">
            <a href={INSTAGRAM} target="_blank" rel="noreferrer">Instagram</a>
            <a href={REPOSITORIO} target="_blank" rel="noreferrer">GitHub</a>
            <Link to="/privacidade">Privacidade</Link>
            <span>© 2026 Smart Dormio · Projeto acadêmico</span>
          </div>
        </footer>
      </div>
    </div>
  );
}
