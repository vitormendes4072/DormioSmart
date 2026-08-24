import { AlertTriangle, Check, Copy, Cpu, Loader2, Pencil, Plus, X } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { ErroApi } from "../lib/api";
import {
  NOME_MAXIMO,
  descreverUltimoContato,
  estaAtivo,
  listarDispositivos,
  TIPOS,
  type TipoDeDispositivo,
  parearDispositivo,
  renomearDispositivo,
  revogarDispositivo,
  type Dispositivo,
  type Pareamento,
} from "../lib/dispositivos";
import { INPUT_CLS } from "../lib/ui";

export function MeusDispositivos() {
  const [lista, setLista] = useState<Dispositivo[]>([]);
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [pareando, setPareando] = useState(false);
  // O tipo escolhido no pareamento (DATA-05). Padrao travesseiro: e o
  // dispositivo do projeto, e o celular e instrumento de referencia.
  const [tipo, setTipo] = useState<TipoDeDispositivo>("travesseiro");
  const [novoToken, setNovoToken] = useState<Pareamento | null>(null);

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

  async function parear() {
    setPareando(true);
    setErro(null);
    try {
      const resultado = await parearDispositivo("", tipo);
      setNovoToken(resultado);
      await carregar();
    } catch (e) {
      setErro(e instanceof ErroApi ? e.message : "Não foi possível parear.");
    } finally {
      setPareando(false);
    }
  }

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
      {novoToken ? (
        <TokenRecemCriado pareamento={novoToken} aoFechar={() => setNovoToken(null)} />
      ) : null}

      {erro ? (
        <p role="alert" className="text-sm text-destructive">
          {erro}
        </p>
      ) : null}

      {lista.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border px-4 py-6 text-center">
          <p className="text-sm text-muted-foreground">Nenhum dispositivo pareado</p>
        </div>
      ) : (
        <ul className="space-y-2">
          {lista.map((dispositivo) => (
            <LinhaDoDispositivo
              key={dispositivo.id}
              dispositivo={dispositivo}
              aoAtualizar={carregar}
              aoRevogar={() => revogar(dispositivo)}
              aoFalhar={setErro}
            />
          ))}
        </ul>
      )}

      <fieldset className="space-y-2" disabled={pareando}>
        <legend className="text-xs uppercase tracking-wider text-muted-foreground">
          Tipo do instrumento
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

      <button
        onClick={parear}
        disabled={pareando}
        className="w-full flex items-center justify-center gap-2 px-4 py-3 rounded-xl bg-secondary hover:bg-secondary/70 transition text-sm font-semibold text-foreground disabled:opacity-70"
      >
        {pareando ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
        {pareando ? "Gerando token..." : "Parear novo dispositivo"}
      </button>
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
  const [copiado, setCopiado] = useState(false);

  async function copiar() {
    try {
      await navigator.clipboard.writeText(pareamento.token);
      setCopiado(true);
    } catch {
      // Sem permissão de área de transferência: o valor segue visível para
      // seleção manual, então não é um caminho sem saída.
      setCopiado(false);
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
        <code className="flex-1 min-w-0 px-3 py-2 rounded-lg bg-card border border-border text-xs font-mono text-foreground break-all">
          {pareamento.token}
        </code>
        <button
          onClick={copiar}
          aria-label="Copiar token"
          className="flex-shrink-0 p-2 rounded-lg bg-secondary hover:bg-secondary/70 transition"
        >
          {copiado ? (
            <Check className="w-4 h-4 text-primary" />
          ) : (
            <Copy className="w-4 h-4 text-muted-foreground" />
          )}
        </button>
      </div>

      <p className="text-xs text-muted-foreground">
        Cole em <code className="font-mono">firmware/secrets.h</code>, no campo{" "}
        <code className="font-mono">DEVICE_TOKEN</code>.
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
  aoRevogar,
  aoFalhar,
}: {
  dispositivo: Dispositivo;
  aoAtualizar: () => Promise<void>;
  aoRevogar: () => void;
  aoFalhar: (mensagem: string) => void;
}) {
  const [editando, setEditando] = useState(false);
  const [nome, setNome] = useState(dispositivo.nome);
  const [salvando, setSalvando] = useState(false);
  const ativo = estaAtivo(dispositivo);

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
    <li
      className={`flex items-center gap-3 rounded-xl border border-border px-4 py-3 ${
        ativo ? "" : "opacity-60"
      }`}
    >
      <Cpu className={`w-4 h-4 flex-shrink-0 ${ativo ? "text-primary" : "text-muted-foreground"}`} />

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
              {ativo ? descreverUltimoContato(dispositivo) : "revogado"}
            </p>
          </>
        )}
      </div>

      {ativo && !editando ? (
        <div className="flex items-center gap-1 flex-shrink-0">
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
    </li>
  );
}
