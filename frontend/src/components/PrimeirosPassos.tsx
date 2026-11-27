import { useEffect, useRef } from "react";
import { Link } from "react-router";

import { URL_DO_APK } from "../lib/appAndroid";
import { usePerfil } from "../contexts/PerfilContext";
import { minutosDaMeta } from "../lib/metaDiaria";
import { idadeDoPerfil } from "../lib/perfil";
import { PerguntasDoGuia } from "./PerguntasDoGuia";

const ACAO = "inline-flex min-h-11 items-center rounded-lg px-3 py-2 text-sm font-semibold focus-visible:outline-2 focus-visible:outline-ring";
const PRIMARIA = ACAO + " bg-primary text-primary-foreground hover:bg-primary/90";
const SECUNDARIA = ACAO + " text-primary hover:bg-secondary";

export function PrimeirosPassos({ temAparelho, consentiu, situacaoConhecida, noApp, dispensar }: {
  temAparelho: boolean;
  consentiu: boolean;
  situacaoConhecida: boolean;
  noApp: boolean;
  dispensar: () => void;
}) {
  const titulo = useRef<HTMLHeadingElement>(null);
  const { perfil } = usePerfil();
  const opcionaisPreenchidos = idadeDoPerfil(perfil) !== null && minutosDaMeta(perfil?.meta_diaria_min) !== null;
  const passos = [
    { texto: "Conta criada", feito: true },
    { texto: "Aparelho conectado", feito: temAparelho },
    { texto: "Consentimento dado", feito: consentiu },
    { texto: "Primeira sessão registrada", feito: false },
  ];
  const feitos = passos.filter(({ feito }) => feito).length;

  useEffect(() => {
    titulo.current?.focus();
  }, []);

  return (
    <section id="primeiros-passos" aria-labelledby="titulo-primeiros-passos" className="scroll-mt-4 space-y-4 rounded-2xl border border-border bg-card p-4 shadow-sm sm:p-5">
      <h2 id="titulo-primeiros-passos" ref={titulo} tabIndex={-1} className="text-lg font-extrabold outline-none">Primeiros passos</h2>
      <p className="text-sm text-muted-foreground">
        O Smart Dormio registra os movimentos durante o repouso, pelo travesseiro ou pelo celular. Ele mostra quanto tempo foi registrado e quando houve movimento. Não mede o sono e não é diagnóstico.
      </p>
      <div className="grid gap-3 sm:grid-cols-2">
        <div className="space-y-2 rounded-xl border border-border p-3">
          <h3 className="text-sm font-bold">Travesseiro</h3>
          <Link to="/dispositivos?parear=1" className={PRIMARIA}>Parear o travesseiro</Link>
        </div>
        <div className="space-y-2 rounded-xl border border-border p-3">
          <h3 className="text-sm font-bold">Celular</h3>
          {noApp ? (
            <Link to="/noite" className={PRIMARIA}>Começar uma Noite</Link>
          ) : (
            <div className="flex flex-wrap gap-1">
              <a href={URL_DO_APK} className={PRIMARIA}>Baixar o app para Android</a>
              <Link to="/coletar" className={SECUNDARIA}>Testar no navegador (sessão curta)</Link>
            </div>
          )}
        </div>
      </div>
      {situacaoConhecida && (
        <div className="space-y-1">
          <p id="progresso-primeiros-passos" className="text-xs font-semibold">{feitos} de {passos.length} passos feitos</p>
          <div role="progressbar" aria-labelledby="progresso-primeiros-passos"
            aria-valuemin={0} aria-valuemax={passos.length} aria-valuenow={feitos}
            className="h-2 overflow-hidden rounded-full bg-secondary">
            <div className="h-full bg-primary" style={{ width: `${100 * feitos / passos.length}%` }} />
          </div>
        </div>
      )}
      <ol className="list-decimal space-y-1 pl-5 text-sm">
        {passos.map(({ texto, feito }) => (
          <li key={texto}>{texto}{situacaoConhecida && <span className="ml-2 text-xs text-muted-foreground">· {feito ? "feito" : "a fazer"}</span>}</li>
        ))}
        <li>Idade e meta (opcional){situacaoConhecida && <span className="ml-2 text-xs text-muted-foreground">· {opcionaisPreenchidos ? "feito" : "a fazer"}</span>}</li>
      </ol>
      <PerguntasDoGuia habilitado={situacaoConhecida} />
      <button type="button" onClick={dispensar} className={SECUNDARIA}>Dispensar</button>
    </section>
  );
}
