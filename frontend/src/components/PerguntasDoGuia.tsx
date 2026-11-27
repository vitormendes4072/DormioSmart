import { useId, useState, type FormEvent } from "react";

import { usePerfil } from "../contexts/PerfilContext";
import { aplicabilidadeDaIdade } from "../lib/aplicabilidade";
import { lerMetaDiaria, preencherMeta } from "../lib/metaDiaria";
import { idadeDoPerfil, lerIdade, salvarCamposDoPerfil } from "../lib/perfil";
import { CampoMetaDiaria } from "./CampoMetaDiaria";

export function PerguntasDoGuia({ habilitado }: { habilitado: boolean }) {
  const { perfil, recarregar } = usePerfil();
  const id = useId();
  const idadeSalva = idadeDoPerfil(perfil);
  const metaSalva = preencherMeta(perfil?.meta_diaria_min);
  const [idade, setIdade] = useState(idadeSalva === null ? "" : String(idadeSalva));
  const [meta, setMeta] = useState(metaSalva);
  const [abertas, setAbertas] = useState(false);
  const [adiadas, setAdiadas] = useState(false);
  const [salvando, setSalvando] = useState(false);
  const [erro, setErro] = useState<string>();
  const [aviso, setAviso] = useState<string>();

  function abrir() {
    setIdade(idadeSalva === null ? "" : String(idadeSalva));
    setMeta(metaSalva);
    setAbertas(true);
  }

  async function salvar(evento: FormEvent<HTMLFormElement>) {
    evento.preventDefault();
    if (salvando) return;
    const lida = lerIdade(idade);
    const metaLida = lerMetaDiaria(meta);
    if (!lida.ok) return setErro(lida.motivo);
    if (meta.trim() !== metaSalva && !metaLida.ok) return setErro(metaLida.motivo);
    const campos: Parameters<typeof salvarCamposDoPerfil>[0] = {};
    if (lida.valor !== idadeSalva) campos.idade = lida.valor;
    if (meta.trim() !== metaSalva && metaLida.ok) campos.meta_diaria_min = metaLida.valor;
    setErro(undefined);
    setSalvando(true);
    try {
      if (Object.keys(campos).length) {
        const dados = await salvarCamposDoPerfil(campos);
        setAviso(aplicabilidadeDaIdade(idadeDoPerfil(dados))?.aviso ?? "Dados atualizados.");
        setAbertas(false);
        await recarregar();
      }
      setAbertas(false);
    } catch {
      setErro("Não foi possível salvar. Tente novamente.");
    } finally {
      setSalvando(false);
    }
  }

  if (adiadas || (!habilitado && !aviso)) return null;

  return (
    <div className="mt-2 space-y-2 rounded-xl border border-border p-3">
      <h3 className="text-sm font-bold">Opcional: idade e meta</h3>
      {aviso && <p role="status" className="text-xs text-muted-foreground">{aviso}</p>}
      {abertas ? (
        <form className="space-y-3" onSubmit={salvar}>
          <div className="space-y-1.5">
            <label htmlFor={id} className="block text-xs text-muted-foreground">Idade (opcional)</label>
            <input id={id} inputMode="numeric" value={idade} onChange={(e) => setIdade(e.target.value)}
              className="min-h-11 w-full rounded-lg border border-border bg-input-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring" />
          </div>
          <CampoMetaDiaria valor={meta} alterar={setMeta} />
          {erro && <p role="alert" className="text-sm text-destructive">{erro}</p>}
          <div className="flex flex-wrap gap-2">
            <button type="submit" disabled={salvando} className="min-h-11 rounded-lg bg-primary px-3 font-semibold text-primary-foreground">
              {salvando ? "Salvando…" : "Salvar respostas"}
            </button>
            <button type="button" disabled={salvando} onClick={() => { setAbertas(false); setAdiadas(true); }} className="min-h-11 px-3 text-primary">
              Agora não
            </button>
          </div>
        </form>
      ) : (
        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={abrir} disabled={!habilitado} className="min-h-11 px-3 font-semibold text-primary">Responder</button>
          <button type="button" onClick={() => setAdiadas(true)} className="min-h-11 px-3 text-primary">Agora não</button>
        </div>
      )}
    </div>
  );
}
