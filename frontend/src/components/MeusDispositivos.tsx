import { AlertTriangle, Check, Copy, Cpu, Loader2, Pencil, Plus, Radio, Smartphone, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";

import { Link } from "react-router";

import { ErroApi } from "../lib/api";
import {
  NOME_MAXIMO,
  descreverUltimoContato,
  estaAtivo,
  listarDispositivos,
  TIPOS,
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
  const [erro, setErro] = useState<string | null>(null);
  const [aguardando, setAguardando] = useState<string | null>(null);
  const [verificando, setVerificando] = useState(false);

  const carregar = useCallback(async () => {
    setCarregando(true);
    setErro(null);
    try {
      setLista(await listarDispositivos());
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Falha ao carregar dispositivos.");
    } finally {
      setCarregando(false);
    }
  }, []);

  useEffect(() => {
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
      setErro(e instanceof ErroApi ? e.message : "Não foi possível verificar o primeiro envio.");
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
      `Revogar "${dispositivo.nome}"?\n\nO token para de funcionar imediatamente e não pode ` +
        `ser reativado. As leituras já enviadas continuam no histórico.`,
    );
    if (!confirmado) return;

    try {
      await revogarDispositivo(dispositivo.id);
      await carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível revogar.");
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
        <p role="alert" className="text-sm text-destructive">
          {erro}
        </p>
      ) : null}

      {lista.length === 0 ? (!erro && (
        <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center">
          <p className="text-sm text-muted-foreground">Nenhum dispositivo pareado</p>
        </div>
      )) : (
        <ul className="space-y-2">
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

function GuiaPareamento({ aoParear }: { aoParear: (aparelho: Dispositivo) => void }) {
  const [tipo, setTipo] = useState<TipoDeDispositivo>("travesseiro");
  const [pareando, setPareando] = useState(false);
  const [novoToken, setNovoToken] = useState<Pareamento | null>(null);
  const [falha, setFalha] = useState(false);

  async function parear() {
    setPareando(true);
    setFalha(false);
    try {
      const resultado = await parearDispositivo("", "travesseiro");
      aoParear(resultado.device);
      setNovoToken(resultado);
    } catch {
      setFalha(true);
    } finally {
      setPareando(false);
    }
  }

  if (novoToken) return <TokenRecemCriado pareamento={novoToken} aoFechar={() => setNovoToken(null)} />;
  return (
      <div className="space-y-3 rounded-xl border border-border bg-card p-4">
        <p className="text-sm font-semibold text-foreground">Parear novo dispositivo</p>

        {falha && <p role="alert">Não foi possível parear o travesseiro.</p>}
        <fieldset className="space-y-2" disabled={pareando}>
          <legend className="text-xs uppercase tracking-wider text-muted-foreground mb-2">
            O novo dispositivo será um
          </legend>
          {TIPOS.map(({ valor, rotulo, ajuda }) => (
            <label
              key={valor}
              className="flex items-start gap-3 rounded-xl border border-border p-3 cursor-pointer transition-colors hover:border-primary/40 has-[:checked]:border-primary/60 has-[:checked]:bg-secondary/50"
            >
              <input
                type="radio"
                name="tipo-do-dispositivo"
                value={valor}
                checked={tipo === valor}
                onChange={() => setTipo(valor)}
                className="mt-0.5 accent-[var(--primary)]"
              />
              <span className="min-w-0">
                <span className="block text-sm font-medium text-foreground">{rotulo}</span>
                <span className="block text-xs text-muted-foreground">{ajuda}</span>
              </span>
            </label>
          ))}
        </fieldset>

        {tipo === "celular" ? (
          <Link to="/coletar" className="inline-block rounded-xl bg-secondary px-4 py-3 text-sm font-semibold">
            Ir para Coletar
          </Link>
        ) : (
        <button
          onClick={parear}
          disabled={pareando}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-secondary hover:bg-secondary/70 transition text-sm font-semibold text-foreground disabled:opacity-70"
        >
          {pareando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
          {pareando ? "Preparando..." : "Parear"}
        </button>
        )}
      </div>
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
    <div className="rounded-xl border border-primary/40 bg-primary/5 p-4 space-y-3">
      <div className="flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-primary flex-shrink-0 mt-0.5" />
        <div className="min-w-0">
          <p className="text-sm font-semibold text-foreground">
            Copie agora — este token não será mostrado de novo
          </p>
          <p className="text-xs text-muted-foreground mt-0.5">
            Guardamos apenas um resumo criptográfico dele. Se perder, será preciso parear
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
          aria-label="Copiar token"
          className="flex-shrink-0 p-2 rounded-lg bg-secondary hover:bg-secondary/70 transition"
        >
          {copia === "copiado" ? (
            <Check className="w-4 h-4 text-primary" />
          ) : (
            <Copy className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      {copia === "manual" && <p role="status">Selecione o token acima e copie manualmente.</p>}
      {copia === "copiado" && <p role="status">Token copiado.</p>}
      <p className="text-xs text-muted-foreground">
        Cole em <code className="font-mono">firmware/secrets.h</code>, no campo{" "}
        <code className="font-mono">DEVICE_TOKEN</code>. O <code>secrets.h</code> é ignorado pelo Git e nunca deve
        ser commitado. Depois, grave o firmware na placa seguindo o{" "}
        <a className="underline" href="https://github.com/vitormendes4072/DormioSmart/blob/main/firmware/README.md">
          firmware/README.md
        </a>.
      </p>

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
  aoFalhar: (mensagem: string) => void;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(dispositivo.nome);
  const [salvando, setSalvando] = useState(false);
  const ativo = estaAtivo(dispositivo);
  const pausado = dispositivo.receber_leituras === false;
  const [alterandoRecebimento, setAlterandoRecebimento] = useState(false);

  async function alternarRecebimento() {
    if (!pausado && !window.confirm(
      "Enquanto pausado, as leituras deste aparelho são descartadas e não podem ser recuperadas.",
    )) return;
    setAlterandoRecebimento(true);
    try {
      aoAlterarRecebimento(await alterarRecebimento(dispositivo.id, pausado));
    } catch (e) {
      aoFalhar(e instanceof ErroApi ? e.message : "Não foi possível alterar o recebimento.");
    } finally {
      setAlterandoRecebimento(false);
    }
  }

  async function salvar() {
    if (!nome.trim() || nome === dispositivo.nome) {
      setEditando(false);
      setNome(dispositivo.nome);
      return;
    }
    setSalvando(true);
    try {
      await renomearDispositivo(dispositivo.id, nome);
      await aoAtualizar();
      setEditando(false);
    } catch (e) {
      aoFalhar(e instanceof ErroApi ? e.message : "Não foi possível renomear.");
      setNome(dispositivo.nome);
    } finally {
      setSalvando(false);
    }
  }

  return (
    <CartaoDeDispositivo tipo={dispositivo.tipo}>
      <div className="flex-1 min-w-0">
        {editando ? (
          <div className="flex items-center gap-2">
            <input
              autoFocus
              value={nome}
              maxLength={NOME_MAXIMO}
              onChange={(e) => setNome(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") void salvar();
                if (e.key === "Escape") {
                  setNome(dispositivo.nome);
                  setEditando(false);
                }
              }}
              className={INPUT_CLS + " py-1.5"}
              aria-label="Nome do dispositivo"
            />
            <button onClick={salvar} disabled={salvando} aria-label="Salvar nome">
              {salvando ? (
                <Loader2 className="w-4 h-4 animate-spin text-muted-foreground" />
              ) : (
                <Check className="w-4 h-4 text-primary" />
              )}
            </button>
            <button
              onClick={() => {
                setNome(dispositivo.nome);
                setEditando(false);
              }}
              aria-label="Cancelar"
            >
              <X className="w-4 h-4 text-muted-foreground" />
            </button>
          </div>
        ) : (
          <>
            <p className="text-sm font-medium text-foreground truncate">{dispositivo.nome}</p>
            <p className="text-xs text-muted-foreground">
              {/* O TIPO na propria linha. Sem ele, nada distinguia um
                  travesseiro de um celular a nao ser o nome — que e escolha
                  livre do usuario e nao classifica nada. */}
              {rotuloDoTipo(dispositivo.tipo)}
              {" · "}
              {dispositivo.last_seen_at ? `Último envio ${descreverUltimoContato(dispositivo)}` : "Aguardando primeiro envio"}
            </p>
            <EstadoDoDispositivo ativo={ativo}>{ativo ? "Credencial ativa" : "Revogado"}</EstadoDoDispositivo>
            {ativo && !dispositivo.last_seen_at && (
              <button type="button" onClick={verificarEnvio} disabled={verificando} className="text-xs font-semibold text-primary">
                Verificar agora
              </button>
            )}
            {ativo && pausado && <p className="text-sm font-semibold text-destructive">Pausado</p>}
          </>
        )}
      </div>

      {ativo && !editando ? (
        <div className="flex flex-wrap items-center justify-end gap-1">
          {dispositivo.tipo === "travesseiro" && (
            <button
              type="button"
              onClick={alternarRecebimento}
              disabled={alterandoRecebimento}
              className="rounded-lg px-2 py-1 text-xs font-semibold text-primary hover:bg-secondary disabled:opacity-50"
              aria-label={`${pausado ? "Retomar" : "Pausar"} recebimento de ${dispositivo.nome}`}
            >
              {pausado ? "Retomar" : "Pausar"}
            </button>
          )}
          <button
            onClick={() => setEditando(true)}
            aria-label={`Renomear ${dispositivo.nome}`}
            className="p-2 rounded-lg hover:bg-secondary transition"
          >
            <Pencil className="w-3.5 h-3.5 text-muted-foreground" />
          </button>
          <button
            onClick={aoRevogar}
            aria-label={`Revogar ${dispositivo.nome}`}
            className="p-2 rounded-lg hover:bg-destructive/10 transition"
          >
            <X className="w-3.5 h-3.5 text-destructive" />
          </button>
        </div>
      ) : null}
    </CartaoDeDispositivo>
  );
}

export function CartaoDeDispositivo({ tipo, children }: { tipo?: TipoDeDispositivo; children: ReactNode }) {
  const Icone = tipo === "celular" ? Smartphone : tipo === "travesseiro" ? Radio : Cpu;
  return (
    <li className="flex min-h-24 items-center gap-3 rounded-[14px] border border-border bg-card p-4 shadow-sm">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
        <Icone className="size-4" aria-hidden />
      </span>
      {children}
    </li>
  );
}

export function EstadoDoDispositivo({ ativo, children }: { ativo: boolean; children: ReactNode }) {
  return (
    <span className={`mt-2 inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-semibold ${ativo
      ? "bg-emerald-500/10 text-emerald-800 dark:text-emerald-300"
      : "bg-amber-500/10 text-amber-800 dark:text-amber-300"}`}>
      <span className="size-1.5 rounded-full bg-current" aria-hidden />
      {children}
    </span>
  );
}
