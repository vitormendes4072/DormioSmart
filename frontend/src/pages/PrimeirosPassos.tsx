import { ArrowLeft, BedSingle, ChevronRight, Loader2, Smartphone, type LucideIcon } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type FormEvent, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router";

import { CampoMetaDiaria } from "../components/CampoMetaDiaria";
import { MarcaDoProduto } from "../components/MarcaDoProduto";
import { TelaDeConsentimento } from "../components/TelaDeConsentimento";
import { TokenRecemCriado } from "../components/TokenRecemCriado";
import { useAuth } from "../contexts/AuthContext";
import { usePerfil } from "../contexts/PerfilContext";
import { useDispositivos } from "../hooks/useDispositivos";
import { usePortaoDoConsentimento } from "../hooks/usePortaoDoConsentimento";
import { usePrimeiroSinal } from "../hooks/usePrimeiroSinal";
import { URL_DO_APK } from "../lib/appAndroid";
import { consentimentoVigente, registrarConsentimento } from "../lib/consentimento";
import { estaAtivo, parearDispositivo, type Pareamento } from "../lib/dispositivos";
import { lerMetaDiaria, preencherMeta } from "../lib/metaDiaria";
import { Noite, noiteNativaDisponivel } from "../lib/noiteNativa";
import { salvarCamposDoPerfil } from "../lib/perfil";
import { guardarJornada, lerJornada, type Jornada, type PassoDaJornada } from "../lib/primeirosPassos";
import qrDoApk from "../assets/qr-app-android.png";

const ROTA = "/primeiros-passos";
const ACAO = "inline-flex min-h-11 items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring disabled:opacity-60";
const PRINCIPAL = ACAO + " bg-primary text-primary-foreground hover:bg-primary/90";
const SECUNDARIA = ACAO + " text-primary hover:bg-secondary";
const ERRO = "text-sm text-destructive";

type Navegacao = {
  jornada?: Jornada;
  voltarPara?: "/configuracoes" | "/dashboard";
  temAnterior?: boolean;
};

const titulos: Record<PassoDaJornada, string> = {
  inicio: "Primeiros passos",
  escolha: "Como você vai registrar?",
  conectar: "Conectar",
  bateria: "Economia de bateria",
  notificacao: "Notificação do registro",
  preparado: "Prepare o celular para a noite",
  codigo: "Grave o código na placa",
  espera: "Aguardando o travesseiro",
  sinal: "Recebemos o primeiro sinal dele",
  meta: "Sua meta de tempo registrado",
  fim: "Tudo pronto para hoje à noite",
};

const numeros: Record<PassoDaJornada, number> = {
  inicio: 1, escolha: 2, conectar: 3, bateria: 3, notificacao: 3, preparado: 3,
  codigo: 3, espera: 3, sinal: 3, meta: 4, fim: 5,
};
const TOTAL_DE_PASSOS = 5;

export function PrimeirosPassos() {
  const conta = useAuth().sessao?.user.id;
  return conta ? <JornadaDaConta key={conta} conta={conta} /> : null;
}

function JornadaDaConta({ conta }: { conta: string }) {
  const local = useLocation();
  const navegar = useNavigate();
  const navegacao = local.state as Navegacao | null;
  const [salva] = useState<Jornada>(() => lerJornada(conta) ?? { passo: "inicio" });
  const jornada = navegacao?.jornada ?? salva;
  const [pareamento, setPareamento] = useState<Pareamento | null>(null);
  const noApp = noiteNativaDisponivel();
  const sairPara = navegacao?.voltarPara ?? "/dashboard";
  const titulo = useRef<HTMLHeadingElement>(null);
  const passo = jornada.passo === "codigo" && !pareamento ? "espera" : jornada.passo;
  const caminho = jornada.caminho;
  const aparelho = jornada.aparelho;
  const temAnterior = navegacao?.temAnterior;

  useEffect(() => {
    titulo.current?.focus();
  }, [passo]);

  useEffect(() => {
    guardarJornada(conta, { passo, caminho, aparelho });
  }, [conta, passo, caminho, aparelho]);

  const ir = useCallback((destino: PassoDaJornada, alteracoes?: Partial<Jornada>, substituir = false) => {
    navegar(ROTA, {
      replace: substituir,
      state: {
        jornada: { caminho, aparelho, ...alteracoes, passo: destino },
        voltarPara: sairPara,
        temAnterior: substituir ? temAnterior : true,
      } satisfies Navegacao,
    });
  }, [aparelho, caminho, navegar, sairPara, temAnterior]);

  const sair = useCallback((destino: string, retomar = passo) => {
    guardarJornada(conta, { caminho, aparelho, passo: retomar === "codigo" ? "espera" : retomar });
    navegar(destino, { replace: true });
  }, [aparelho, caminho, conta, navegar, passo]);

  const voltar = useCallback(() => {
    if (temAnterior) {
      navegar(-1);
      return;
    }
    const anteriores: Partial<Record<PassoDaJornada, PassoDaJornada>> = {
      escolha: "inicio", conectar: "escolha", bateria: "conectar", notificacao: "bateria",
      preparado: "notificacao", espera: "conectar", sinal: "conectar",
      meta: caminho === "travesseiro" && aparelho ? "espera" : noApp ? "preparado" : "conectar", fim: "meta",
    };
    const anterior = anteriores[passo];
    if (anterior) ir(anterior, undefined, true);
    else sair(sairPara);
  }, [aparelho, caminho, ir, navegar, noApp, passo, sair, sairPara, temAnterior]);

  useEffect(() => {
    if (!noApp) return;
    function voltarNoAndroid() {
      const dialogo = document.querySelector('[role="dialog"][aria-modal="true"]');
      if (dialogo?.contains(document.activeElement)) {
        document.activeElement?.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      } else {
        voltar();
      }
    }
    window.addEventListener("dormio-voltar-na-jornada", voltarNoAndroid);
    return () => window.removeEventListener("dormio-voltar-na-jornada", voltarNoAndroid);
  }, [noApp, voltar]);

  const avancarAposSinal = useCallback(() => ir("sinal", undefined, true), [ir]);
  const paraMeta = useCallback(() => ir("meta"), [ir]);
  const tituloAtual = passo === "conectar"
    ? caminho === "travesseiro" ? "Conecte o travesseiro" : noApp ? "Prepare o registro pelo celular" : "Abra o Smart Dormio no celular"
    : titulos[passo];

  let conteudo: ReactNode;
  switch (passo) {
    case "inicio":
      conteudo = <>
        <p>O Smart Dormio registra os movimentos enquanto você descansa, pelo travesseiro ou pelo celular, e mostra quanto tempo foi registrado.</p>
        <p>Não é diagnóstico e não mede o sono.</p>
        <button className={PRINCIPAL} onClick={() => ir("escolha")}>Começar</button>
      </>;
      break;
    case "escolha":
      conteudo = (
        <div className="grid gap-3">
          <OpcaoDeRegistro id="celular" titulo="Celular" descricao="App para Android, sobre o colchão"
            icone={Smartphone} aoEscolher={() => ir("conectar", { caminho: "celular" })} />
          <OpcaoDeRegistro id="travesseiro" titulo="Travesseiro" descricao="O sensor dentro da fronha"
            icone={BedSingle} aoEscolher={() => ir("conectar", { caminho: "travesseiro" })} />
        </div>
      );
      break;
    case "conectar":
      if (caminho === "travesseiro") {
        conteudo = <ConectarTravesseiro aparelho={aparelho}
          aoVerCodigo={pareamento ? () => ir("codigo", { aparelho: pareamento.device.id }) : undefined}
          aoParear={(novo) => {
            setPareamento(novo);
            ir("codigo", { aparelho: novo.device.id });
          }}
          aoAguardar={(id) => ir("espera", { aparelho: id })}
          aoAdiar={() => sair("/dashboard")} />;
      } else if (noApp) {
        conteudo = <ConsentimentoDaJornada continuar={() => ir("bateria")} adiar={paraMeta} />;
      } else {
        conteudo = <>
          <p>Aponte a câmera do celular para o QR code ou abra o link no telefone.</p>
          <img src={qrDoApk} width={192} height={192} className="size-48 rounded-lg bg-white" alt="QR code para baixar o app para Android" />
          <div className="flex flex-wrap gap-2">
            <a className={PRINCIPAL} href={URL_DO_APK}>Baixar o app para Android</a>
            <button className={SECUNDARIA} onClick={paraMeta}>Já instalei</button>
            <button className={SECUNDARIA} onClick={() => sair("/coletar", "meta")}>Testar no navegador (sessão curta)</button>
          </div>
        </>;
      }
      break;
    case "bateria":
    case "notificacao":
      conteudo = <PermissaoDaNoite key={passo} tipo={passo} continuar={() => ir(passo === "bateria" ? "notificacao" : "preparado")} />;
      break;
    case "preparado":
      conteudo = <>
        <p>Em Noite, escolha onde o celular vai ficar e inicie o registro quando for descansar.</p>
        <div className="flex flex-wrap gap-2">
          <button className={PRINCIPAL} onClick={() => sair("/noite", "meta")}>Começar a Noite</button>
          <button className={SECUNDARIA} onClick={paraMeta}>Continuar depois</button>
        </div>
      </>;
      break;
    case "codigo":
      conteudo = pareamento && <>
        <TokenRecemCriado pareamento={pareamento} rotuloAoFechar="Já copiei, aguardar sinal"
          aoFechar={() => { setPareamento(null); ir("espera", undefined, true); }} />
        <button className={SECUNDARIA} onClick={() => sair("/dashboard")}>Continuar depois</button>
      </>;
      break;
    case "espera":
      conteudo = aparelho && <AguardarTravesseiro key={aparelho} aparelho={aparelho} aoReceber={avancarAposSinal}
        aoReparear={() => ir("conectar", { aparelho: undefined }, true)}
        aoAdiar={() => sair("/dashboard")} />;
      break;
    case "sinal":
      conteudo = <>
        <p>O travesseiro já se comunicou com a sua conta.</p>
        <button className={PRINCIPAL} onClick={paraMeta}>Continuar</button>
      </>;
      break;
    case "meta":
      conteudo = <MetaDaJornada continuar={() => ir("fim")} />;
      break;
    case "fim":
      conteudo = <>
        <p>{caminho === "travesseiro"
          ? "Deixe o travesseiro ligado ao descansar."
          : noApp
            ? <>Abra <Link to="/noite" className="inline-flex min-h-11 items-center text-primary underline">Noite</Link> no celular e comece o registro quando for descansar.</>
            : "Entre no app com o mesmo e-mail desta conta. Depois, abra Noite e comece o registro quando for descansar."}</p>
        <p>Amanhã, o Início mostra quanto tempo foi registrado na sessão.</p>
        <button className={PRINCIPAL} onClick={() => sair("/dashboard")}>Ir para o Início</button>
      </>;
  }

  return (
    <main className="min-h-dvh bg-background px-5 py-6 text-foreground sm:grid sm:place-items-center sm:px-8 sm:py-12">
      <div className="mx-auto w-full max-w-xl space-y-7 sm:min-h-[32rem] sm:space-y-8 sm:rounded-[1.75rem] sm:border sm:border-border sm:bg-card sm:p-10 sm:shadow-sm">
        <header className="space-y-5">
          <MarcaDoProduto className="h-8 sm:h-9" />
          <nav aria-label="Primeiros passos" className="flex items-center justify-between gap-3">
            <button className={SECUNDARIA + " -ml-3 gap-2 px-3"} onClick={voltar}><ArrowLeft size={16} aria-hidden /> Voltar</button>
            <p className="text-sm font-medium tabular-nums text-muted-foreground">Passo {numeros[passo]} de {TOTAL_DE_PASSOS}</p>
          </nav>
          <div role="progressbar" aria-label="Progresso dos primeiros passos" aria-valuemin={0}
            aria-valuemax={TOTAL_DE_PASSOS} aria-valuenow={numeros[passo]} className="h-1.5 overflow-hidden rounded-full bg-secondary">
            <div className="h-full rounded-full bg-primary" style={{ width: `${numeros[passo] / TOTAL_DE_PASSOS * 100}%` }} />
          </div>
        </header>
        <section aria-labelledby="titulo-da-jornada" className="space-y-4">
          <h1 id="titulo-da-jornada" ref={titulo} tabIndex={-1}
            className="text-3xl font-extrabold tracking-tight outline-none sm:text-4xl">{tituloAtual}</h1>
          <div className="space-y-4 text-sm leading-relaxed text-muted-foreground sm:text-base">{conteudo}</div>
        </section>
      </div>
    </main>
  );
}

function OpcaoDeRegistro({ id, titulo, descricao, icone: Icone, aoEscolher }: {
  id: string;
  titulo: string;
  descricao: string;
  icone: LucideIcon;
  aoEscolher: () => void;
}) {
  return (
    <button type="button" aria-labelledby={id + "-titulo"} aria-describedby={id + "-descricao"} onClick={aoEscolher}
      className="grid min-h-20 w-full grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 rounded-xl border border-border bg-card p-3 text-left hover:border-primary hover:bg-secondary focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring sm:px-4">
      <span className="grid size-11 place-items-center rounded-lg bg-primary/10 text-primary"><Icone size={21} aria-hidden /></span>
      <span>
        <span id={id + "-titulo"} className="block text-base font-bold text-foreground">{titulo}</span>
        <span id={id + "-descricao"} className="block text-sm leading-snug text-muted-foreground">{descricao}</span>
      </span>
      <ChevronRight size={18} aria-hidden className="text-primary" />
    </button>
  );
}

function ConectarTravesseiro({ aparelho, aoVerCodigo, aoParear, aoAguardar, aoAdiar }: {
  aparelho?: string;
  aoVerCodigo?: () => void;
  aoParear: (novo: Pareamento) => void;
  aoAguardar: (id: string) => void;
  aoAdiar: () => void;
}) {
  const { dispositivos, estado } = useDispositivos();
  const existente = aparelho ?? dispositivos.find((d) => d.tipo === "travesseiro" && estaAtivo(d))?.id;
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(false);
  const montado = useRef(false);

  useEffect(() => {
    montado.current = true;
    return () => { montado.current = false; };
  }, []);

  async function parear(outro: boolean) {
    if (!outro && aoVerCodigo) {
      aoVerCodigo();
      return;
    }
    if (!outro && existente) {
      aoAguardar(existente);
      return;
    }
    setOcupado(true);
    setErro(false);
    try {
      const novo = await parearDispositivo("", "travesseiro");
      if (montado.current) aoParear(novo);
    } catch {
      setErro(true);
    } finally {
      setOcupado(false);
    }
  }

  return <>
    <p>{existente ? "Vamos conferir se o travesseiro já enviou o primeiro sinal." : "Gere um código de conexão para gravar na placa do travesseiro. Ele aparece uma vez só."}</p>
    {erro && <p role="alert" className={ERRO}>Não foi possível parear o travesseiro. Tente novamente.</p>}
    <div className="flex flex-wrap gap-2">
      <button className={PRINCIPAL} disabled={ocupado || estado === "carregando"} onClick={() => void parear(false)}>
        {ocupado ? "Gerando…" : aoVerCodigo ? "Ver código de conexão" : existente ? "Verificar conexão" : "Gerar código de conexão"}
      </button>
      {existente && !aoVerCodigo && <button className={SECUNDARIA} disabled={ocupado} onClick={() => void parear(true)}>Gerar outro código</button>}
      <button className={SECUNDARIA} disabled={ocupado} onClick={aoAdiar}>Continuar depois</button>
    </div>
  </>;
}

function AguardarTravesseiro({ aparelho, aoReceber, aoReparear, aoAdiar }: {
  aparelho: string;
  aoReceber: () => void;
  aoReparear: () => void;
  aoAdiar: () => void;
}) {
  const { resultado, pausado, tentarNovamente } = usePrimeiroSinal(aparelho);
  const [estadoMontado, setEstadoMontado] = useState(false);
  useEffect(() => {
    // A região de estado precisa existir antes de receber a primeira mensagem.
    const depoisDaMontagem = window.setTimeout(() => setEstadoMontado(true), 0);
    return () => window.clearTimeout(depoisDaMontagem);
  }, []);

  useEffect(() => {
    if (resultado === "sinal") aoReceber();
  }, [resultado, aoReceber]);

  return <>
    <p>Depois de gravar o código, ligue o travesseiro. Esta tela avança assim que o aparelho enviar o primeiro sinal.</p>
    <p role="status" aria-live="polite" className={resultado === "aguardando" ? "flex items-center gap-2 text-sm font-medium text-primary" : ERRO}>
      {resultado === "aguardando" && estadoMontado && <>
        <Loader2 size={16} aria-hidden className="shrink-0 motion-safe:animate-spin" style={pausado ? { animationPlayState: "paused" } : undefined} />
        Procurando o travesseiro…
      </>}
      {resultado === "erro" && "Não foi possível consultar o travesseiro. Vamos tentar novamente."}
      {resultado === "ausente" && "Este travesseiro não está mais disponível na conta."}
    </p>
    <div className="flex flex-wrap gap-2">
      {resultado === "erro" && <button className={PRINCIPAL} onClick={tentarNovamente}>Tentar novamente</button>}
      {resultado === "ausente" && <button className={PRINCIPAL} onClick={aoReparear}>Parear novamente</button>}
      {resultado !== "ausente" && <button className={SECUNDARIA} onClick={aoReparear}>Perdi o código</button>}
      <button className={SECUNDARIA} onClick={aoAdiar}>Continuar depois</button>
    </div>
  </>;
}

function ConsentimentoDaJornada({ continuar, adiar }: { continuar: () => void; adiar: () => void }) {
  const { perfil, recarregar, carregando, erro } = usePerfil();
  const vigente = consentimentoVigente(perfil);
  const portao = usePortaoDoConsentimento({
    vigente,
    registrar: async () => {
      await registrarConsentimento();
      await recarregar();
    },
  });
  return <>
    <p>{vigente ? "O consentimento para o registro já está vigente nesta conta." : "Antes de preparar o registro, leia como os dados serão usados."}</p>
    {erro && <p role="status" className={ERRO}>Não foi possível conferir os dados da conta.</p>}
    <div className="flex flex-wrap gap-2">
      <button className={PRINCIPAL} disabled={carregando} onClick={() => portao.pedir(continuar)}>
        {vigente ? "Continuar" : "Ver consentimento"}
      </button>
      <button className={SECUNDARIA} onClick={adiar}>Continuar depois</button>
    </div>
    {portao.telaAberta && <TelaDeConsentimento aoConcordar={portao.concordar} aoRecusar={portao.recusar} erro={portao.erro} />}
  </>;
}

function PermissaoDaNoite({ tipo, continuar }: { tipo: "bateria" | "notificacao"; continuar: () => void }) {
  const bateria = tipo === "bateria";
  const [permitido, setPermitido] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState(false);
  useEffect(() => {
    let ativo = true;
    function conferir() {
      if (document.hidden) return;
      const leitura = bateria ? Noite.estado().then((dados) => dados.isentoDeBateria) : Noite.lembrete().then((dados) => dados.notificacoes);
      void leitura.then((liberado) => { if (ativo) setPermitido(liberado); }, () => {});
    }
    conferir();
    document.addEventListener("visibilitychange", conferir);
    window.addEventListener("focus", conferir);
    return () => {
      ativo = false;
      document.removeEventListener("visibilitychange", conferir);
      window.removeEventListener("focus", conferir);
    };
  }, [bateria]);

  async function pedir() {
    setOcupado(true);
    setErro(false);
    try {
      const liberado = bateria
        ? (await Noite.pedirIsencaoDeBateria()).isentoDeBateria
        : (await Noite.pedirNotificacoes()).notificacoes;
      if (liberado) continuar();
      else if (!bateria) setErro(true);
    } catch {
      setErro(true);
    } finally {
      setOcupado(false);
    }
  }

  return <>
    <p>{bateria ? "Permita que o Smart Dormio continue registrando com a tela apagada." : "A notificação do Android indica quando há um registro em andamento."}</p>
    {erro && <p role="status" className={ERRO}>A permissão ainda está desativada. Você pode tentar novamente ou continuar depois.</p>}
    <div className="flex flex-wrap gap-2">
      <button className={PRINCIPAL} disabled={ocupado} onClick={permitido ? continuar : () => void pedir()}>
        {permitido ? "Continuar" : bateria ? "Permitir uso em segundo plano" : "Permitir notificação"}
      </button>
      {!permitido && <button className={SECUNDARIA} disabled={ocupado} onClick={continuar}>Continuar depois</button>}
    </div>
  </>;
}

function MetaDaJornada({ continuar }: { continuar: () => void }) {
  const { perfil, recarregar, carregando } = usePerfil();
  const salva = preencherMeta(perfil?.meta_diaria_min);
  const [edicao, setEdicao] = useState<string>();
  const [ocupado, setOcupado] = useState(false);
  const [erro, setErro] = useState<string>();
  const valor = edicao ?? salva;

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    const meta = lerMetaDiaria(valor);
    if (!meta.ok) {
      setErro(meta.motivo);
      return;
    }
    if (valor.trim() === salva) {
      continuar();
      return;
    }
    setOcupado(true);
    setErro(undefined);
    try {
      await salvarCamposDoPerfil({ meta_diaria_min: meta.valor });
      await recarregar();
      continuar();
    } catch {
      setErro("Não foi possível salvar a meta. Tente novamente.");
    } finally {
      setOcupado(false);
    }
  }

  return <form className="space-y-4" onSubmit={(evento) => void salvar(evento)}>
    <CampoMetaDiaria valor={valor} alterar={setEdicao} />
    {erro && <p role="alert" className={ERRO}>{erro}</p>}
    <div className="flex flex-wrap gap-2">
      <button className={PRINCIPAL} type="submit" disabled={ocupado || carregando}>
        {ocupado ? "Salvando…" : "Salvar meta"}
      </button>
      <button className={SECUNDARIA} type="button" disabled={ocupado} onClick={continuar}>
        {salva ? "Manter minha meta" : "Definir depois"}
      </button>
    </div>
  </form>;
}
