import { EtiquetaDeRegistro, SUPERFICIE_DO_CARTAO_DE_REGISTRO } from "./CartoesDeRegistro";
import { MensagemDeFalha } from "./MensagemDeFalha";
import { AlertTriangle, Check, Copy, Cpu, Loader2, Pencil, Plus, Radio, Smartphone, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState, type ReactNode } from "react";

import { Link } from "react-router";

import { ErroApi } from "../lib/api";
import { noiteNativaDisponivel } from "../lib/noiteNativa";
import {
  NOME_MAXIMO,
  classificarUltimoEnvio,
  descreverUltimoContato,
  estaAtivo,
  listarDispositivos,
  rotuloDoTipo,
  type TipoDeDispositivo,
  parearDispositivo,
  alterarRecebimento,
  renomearDispositivo,
  revogarDispositivo,
  type Dispositivo,
  type Pareamento,
} from "../lib/dispositivos";
import { INPUT_CLS } from "../lib/ui";

export function MeusDispositivos({ mostrarPareamento = true }: { mostrarPareamento?: boolean }) {
  const [lista, setLista] = useState<Dispositivo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | ErroApi | null>(null);
  const [aguardando, setAguardando] = useState<string | null>(null);
  const [verificando, setVerificando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setLista(await listarDispositivos());
    } catch (e) {
      setErro(e instanceof ErroApi ? e : "Falha ao carregar dispositivos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- UI-33: Busca na API; o carregamento síncrono é o mesmo dos botões de recarregar, que reusam esta função.
    void carregar();
  }, [carregar]);

  const consultaEmAndamento = useRef(false);
  const verificar = useCallback(async (id: string) => {
    if (consultaEmAndamento.current) return;
    consultaEmAndamento.current = true;
    setVerificando(true);
    try {
      const atual = (await listarDispositivos()).find((item) => item.id === id);
      if (atual) setLista((lista) => lista.map((item) => item.id === id ? { ...item, last_seen_at: atual.last_seen_at } : item));
      if (!atual || atual.last_seen_at || atual.revoked_at) {
        setAguardando((esperado) => esperado === id ? null : esperado);
      }
    } catch (e) {
      setErro(e instanceof ErroApi ? e : "Não foi possível verificar o primeiro envio.");
    } finally {
      consultaEmAndamento.current = false;
      setVerificando(false);
    }
  }, []);

  useEffect(() => {
    if (!aguardando) return;
    const intervalo = window.setInterval(() => {
      if (document.visibilityState === "visible") void verificar(aguardando);
    }, 15_000);
    const limite = window.setTimeout(() => window.clearInterval(intervalo), 600_000);
    return () => {
      window.clearInterval(intervalo);
      window.clearTimeout(limite);
    };
  }, [aguardando, verificar]);

  async function revogar(dispositivo: Dispositivo) {
    const confirmado = window.confirm(
      `Revogar "${dispositivo.nome}"?\n\nO código de conexão para de funcionar imediatamente e não pode ` +
        `ser reativado. Os registros já enviados continuam no histórico.`,
    );
    if (!confirmado) return;

    try {
      await revogarDispositivo(dispositivo.id);
      await carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e : "Não foi possível revogar.");
    }
  }

  if (carregando) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground py-6">
        <Loader2 className="w-4 h-4 animate-spin" />
        Carregando dispositivos...
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {erro ? (
        <div role="alert" className="text-sm text-destructive">
          <MensagemDeFalha erro={erro} />
        </div>
      ) : null}

      {lista.length === 0 ? (!erro && (
        <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center">
          <p className="text-sm text-muted-foreground">Nenhum dispositivo pareado</p>
        </div>
      )) : (
        <ul className="space-y-3" aria-label="Dispositivos da conta">
          {lista.map((dispositivo) => (
            <LinhaDoDispositivo
              key={dispositivo.id}
              dispositivo={dispositivo}
              aoAtualizar={carregar}
              verificarEnvio={() => void verificar(dispositivo.id)}
              verificando={verificando}
              aoRevogar={() => revogar(dispositivo)}
              aoAlterarRecebimento={(atualizado) =>
                setLista((atuais) => atuais.map((item) => item.id === atualizado.id ? atualizado : item))
              }
              aoFalhar={setErro}
            />
          ))}
        </ul>
      )}

      <div id="pareamento-dispositivo" hidden={!mostrarPareamento}>
        {mostrarPareamento && <GuiaPareamento aoParear={(aparelho) => {
          setLista((lista) => [aparelho, ...lista.filter((item) => item.id !== aparelho.id)]);
          setAguardando(aparelho.id);
        }} />}
      </div>
    </div>
  );
}

/**
 * O pareamento é só do travesseiro (UI-42). O celular entra na conta sozinho, na
 * primeira noite gravada pela Noite (app) ou pela Coletar (site): escolher
 * "Celular" aqui não pareava nada, só levava a essas telas.
 */
function GuiaPareamento({ aoParear }: { aoParear: (aparelho: Dispositivo) => void }) {
  const noApp = noiteNativaDisponivel();
  const [pareando, setPareando] = useState(false);
  const [novoToken, setNovoToken] = useState<Pareamento | null>(null);
  const [falha, setFalha] = useState<string | ErroApi | null>(null);

  async function parear() {
    setPareando(true);
    setFalha(null);
    try {
      const resultado = await parearDispositivo("", "travesseiro");
      aoParear(resultado.device);
      setNovoToken(resultado);
    } catch (e) {
      setFalha(e instanceof ErroApi ? e : "Não foi possível parear o travesseiro.");
    } finally {
      setPareando(false);
    }
  }

  if (novoToken) return <TokenRecemCriado pareamento={novoToken} aoFechar={() => setNovoToken(null)} />;
  return (
      <section className={`${SUPERFICIE_DO_CARTAO_DE_REGISTRO} space-y-3 p-4`}>
        <h2 className="text-base font-semibold text-foreground">Parear um travesseiro</h2>
        <p className="text-xs text-muted-foreground">O travesseiro recebe um código de conexão próprio, mostrado uma vez só.</p>

        {falha && <div role="alert" className="text-sm text-destructive"><MensagemDeFalha erro={falha} /></div>}
        <button
          onClick={parear}
          disabled={pareando}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-secondary hover:bg-secondary/70 transition text-sm font-semibold text-foreground disabled:opacity-70"
        >
          {pareando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {pareando ? "Preparando..." : "Parear"}
        </button>

        <p className="text-xs text-muted-foreground">
          O celular não precisa de pareamento: ele aparece aqui sozinho depois da primeira noite gravada em{" "}
          <Link to={noApp ? "/noite" : "/coletar"} className="font-semibold text-foreground underline underline-offset-2">
            {noApp ? "Noite" : "Coletar"}
          </Link>
          .
        </p>
      </section>
  );
}

/**
 * O token aparece UMA VEZ.
 *
 * O banco guarda só o hash, então este é o único momento em que o valor
 * existe. O aviso vem antes do campo, e o bloco não fecha sozinho — fechar
 * automaticamente após copiar seria perder o valor de quem se distraiu.
 */
function TokenRecemCriado({
  pareamento,
  aoFechar,
}: {
  pareamento: Pareamento;
  aoFechar: () => void;
}) {
  const [copia, setCopia] = useState<"copiado" | "manual" | null>(null);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(pareamento.token);
      setCopia("copiado");
    } catch {
      // Sem permissão de área de transferência: o valor segue visível para
      // seleção manual, então não é um caminho sem saída.
      setCopia("manual");
    }
  }

  return (
    <div className="space-y-3 rounded-2xl border border-primary/40 bg-primary/5 p-4">
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            Copie agora — este código de conexão não será mostrado de novo
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Não guardamos o código, só uma forma de conferi-lo. Se perder, será preciso parear
            outro dispositivo.
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <code className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-card border border-border text-xs font-mono text-foreground break-all select-all">
          {pareamento.token}
        </code>
        <button
          onClick={copiar}
          aria-label="Copiar código de conexão"
          className="flex-shrink-0 p-2 rounded-lg bg-secondary hover:bg-secondary/70 transition"
        >
          {copia === "copiado" ? (
            <Check className="w-4 h-4 text-primary" />
          ) : (
            <Copy className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      {copia === "manual" && <p role="status">Selecione o código acima e copie manualmente.</p>}
      {copia === "copiado" && <p role="status">Código copiado.</p>}
      <p className="text-xs text-muted-foreground">
        O código precisa ser gravado na placa do travesseiro.
      </p>
      {/* Aberto: sem este passo o travesseiro não conecta. */}
      <details open className="text-xs text-muted-foreground">
        <summary className="cursor-pointer font-semibold">Detalhes técnicos</summary>
        <p className="mt-1">
        Cole em <code className="font-mono">firmware/secrets.h</code>, no campo{" "}
        <code className="font-mono">DEVICE_TOKEN</code>. O <code>secrets.h</code> é ignorado pelo Git e nunca deve
        ser commitado. Depois, grave o firmware na placa seguindo o{" "}
        <a className="underline" href="https://github.com/vitormendes4072/DormioSmart/blob/main/firmware/README.md">
          firmware/README.md
        </a>.
        </p>
      </details>

      <button
        onClick={aoFechar}
        className="text-xs text-primary hover:text-accent transition font-semibold"
      >
        Já copiei, pode ocultar
      </button>
    </div>
  );
}

function LinhaDoDispositivo({
  dispositivo,
  aoAtualizar,
  verificarEnvio,
  verificando,
  aoRevogar,
  aoAlterarRecebimento,
  aoFalhar,
}: {
  dispositivo: Dispositivo;
  aoAtualizar: () => Promise<void>;
  verificarEnvio: () => void;
  verificando: boolean;
  aoRevogar: () => void;
  aoAlterarRecebimento: (dispositivo: Dispositivo) => void;
  aoFalhar: (mensagem: string | ErroApi) => void;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(dispositivo.nome);
  const [salvando, setSalvando] = useState(false);
  const [erroNome, setErroNome] = useState<string | null>(null);
  const idErroNome = useId();
  const ativo = estaAtivo(dispositivo);
  const pausado = dispositivo.receber_leituras === false;
  const estado = !ativo ? "Revogado" : pausado ? "Pausado"
    : classificarUltimoEnvio(dispositivo) === "Enviou recentemente" ? "Conectado" : "Inativo";
  const [alterandoRecebimento, setAlterandoRecebimento] = useState(false);

  async function alternarRecebimento() {
    if (!pausado && !window.confirm(
      "Enquanto pausado, os registros deste aparelho são descartados e não podem ser recuperados.",
    )) return;
    setAlterandoRecebimento(true);
    try {
      aoAlterarRecebimento(await alterarRecebimento(dispositivo.id, pausado));
    } catch (e) {
      aoFalhar(e instanceof ErroApi ? e : "Não foi possível alterar o recebimento.");
    } finally {
      setAlterandoRecebimento(false);
    }
  }

  function fecharEdicao() {
    setEditando(false);
    setNome(dispositivo.nome);
    setErroNome(null);
  }

  async function salvar() {
    if (salvando) return;
    const novoNome = nome.trim();
    if (!novoNome) {
      setErroNome("Informe um nome para o dispositivo.");
      return;
    }
    if (Array.from(novoNome).length > NOME_MAXIMO) {
      setErroNome("O nome tem mais caracteres do que o permitido.");
      return;
    }
    if (novoNome === dispositivo.nome) {
      fecharEdicao();
      return;
    }
    setSalvando(true);
    try {
      await renomearDispositivo(dispositivo.id, novoNome);
      await aoAtualizar();
      setEditando(false);
    } catch (e) {
      aoFalhar(e instanceof ErroApi ? e : "Não foi possível renomear.");
      setNome(dispositivo.nome);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <CartaoDeDispositivo tipo={dispositivo.tipo}>
      <div className="min-w-0 flex-1">
        {editando ? (
          <div className="space-y-2">
            <div className="flex flex-wrap items-center gap-2">
              <input
                autoFocus
                value={nome}
                onChange={(e) => {
                  setNome(e.target.value);
                  setErroNome(null);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter") void salvar();
                  if (e.key === "Escape") fecharEdicao();
                }}
                className={INPUT_CLS + " min-w-0 basis-36 flex-1 py-1.5"}
                aria-label="Nome do dispositivo"
                aria-invalid={erroNome !== null}
                aria-describedby={erroNome ? idErroNome : undefined}
              />
              <button type="button" onClick={salvar} disabled={salvando} aria-label="Salvar nome"
                className="grid size-9 place-items-center rounded-lg hover:bg-secondary">
                {salvando ? (
                  <Loader2 className="size-4 animate-spin text-muted-foreground" aria-hidden />
                ) : (
                  <Check className="size-4 text-primary" aria-hidden />
                )}
              </button>
              <button type="button" onClick={fecharEdicao} aria-label="Cancelar"
                className="grid size-9 place-items-center rounded-lg hover:bg-secondary">
                <X className="size-4 text-muted-foreground" aria-hidden />
              </button>
            </div>
            {erroNome && <p id={idErroNome} role="alert" className="text-xs text-destructive">{erroNome}</p>}
          </div>
        ) : (
          <div className="grid gap-2 sm:flex sm:items-center sm:justify-between">
            <div className="min-w-0 space-y-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <p className="max-w-full truncate text-sm font-semibold text-foreground">{dispositivo.nome}</p>
                <EstadoDoDispositivo estado={estado} />
              </div>
              <p className="text-xs text-muted-foreground">
                {rotuloDoTipo(dispositivo.tipo)}
                {" · "}
                {dispositivo.last_seen_at ? `Último envio ${descreverUltimoContato(dispositivo)}` : "Aguardando primeiro envio"}
              </p>
              {ativo && !dispositivo.last_seen_at && (
                <button type="button" onClick={verificarEnvio} disabled={verificando} className="text-xs font-semibold text-primary">
                  Verificar agora
                </button>
              )}
            </div>

            {ativo && (
              <div className="flex flex-wrap items-center justify-end gap-1">
                {dispositivo.tipo === "travesseiro" && (
                  <button
                    type="button"
                    onClick={alternarRecebimento}
                    disabled={alterandoRecebimento}
                    className="min-h-9 rounded-lg border border-border px-2 text-xs font-semibold text-primary hover:bg-secondary disabled:opacity-50"
                    aria-label={`${pausado ? "Retomar" : "Pausar"} recebimento de ${dispositivo.nome}`}
                  >
                    {pausado ? "Retomar" : "Pausar"}
                  </button>
                )}
                <button type="button" onClick={() => setEditando(true)} aria-label={`Renomear ${dispositivo.nome}`}
                  className="grid size-9 place-items-center rounded-lg hover:bg-secondary">
                  <Pencil className="size-4 text-muted-foreground" aria-hidden />
                </button>
                <button type="button" onClick={aoRevogar} aria-label={`Revogar ${dispositivo.nome}`}
                  className="grid size-9 place-items-center rounded-lg hover:bg-destructive/10">
                  <X className="size-4 text-destructive" aria-hidden />
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </CartaoDeDispositivo>
  );
}

export function CartaoDeDispositivo({ tipo, children }: { tipo?: TipoDeDispositivo; children: ReactNode }) {
  const Icone = tipo === "celular" ? Smartphone : tipo === "travesseiro" ? Radio : Cpu;
  return (
    <li className={`${SUPERFICIE_DO_CARTAO_DE_REGISTRO} flex min-w-0 items-start gap-3 p-4 sm:items-center`}>
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
        <Icone className="size-4" aria-hidden />
      </span>
      {children}
    </li>
  );
}

const TONS_DO_ESTADO = {
  Conectado: "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300",
  Pausado: "bg-amber-500/10 text-amber-800 dark:text-amber-300",
  Inativo: "bg-secondary text-muted-foreground",
  Revogado: "bg-secondary text-muted-foreground",
};

export function EstadoDoDispositivo({ estado }: { estado: keyof typeof TONS_DO_ESTADO }) {
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 ${TONS_DO_ESTADO[estado]}`}>
      <span className="size-1.5 shrink-0 rounded-full bg-current" aria-hidden />
      <EtiquetaDeRegistro cor="text-inherit">{estado}</EtiquetaDeRegistro>
    </span>
  );
}
