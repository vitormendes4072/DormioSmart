import { useEffect, useState } from "react";

import { URL_DO_APK, VERSAO_DO_APP_ANDROID } from "../lib/appAndroid";
import { buscarVersaoPublicada, versaoParaAtualizar } from "../lib/atualizacaoDoApp";
import { noiteNativaDisponivel } from "../lib/noiteNativa";

type Props = {
  /** Só no app Android; injetável nos testes. */
  noApp?: boolean;
  instalada?: string;
  buscar?: () => Promise<string | null>;
};

/**
 * APP-19: a faixa "há uma versão nova do app", no topo das telas depois do login.
 *
 * Pergunta uma vez por abertura do app. Sem resposta, sem faixa: o aviso nunca
 * atrapalha quem está sem internet. O botão abre o download no navegador do
 * celular (link externo, fora do app).
 */
export function AvisoDeAtualizacao({
  noApp = noiteNativaDisponivel(),
  instalada = VERSAO_DO_APP_ANDROID,
  buscar = buscarVersaoPublicada,
}: Props) {
  const [nova, setNova] = useState<string | null>(null);
  const [dispensado, setDispensado] = useState(false);

  useEffect(() => {
    if (!noApp) return;
    let vivo = true;
    void buscar().then((publicada) => {
      if (vivo) setNova(versaoParaAtualizar(instalada, publicada));
    });
    return () => {
      vivo = false;
    };
  }, [noApp, instalada, buscar]);

  if (!noApp || !nova || dispensado) return null;
  return (
    <div
      role="status"
      className="mb-4 flex flex-wrap items-center gap-x-3 gap-y-2 rounded-lg border border-primary/30 bg-primary/5 px-4 py-3 text-sm"
    >
      <p className="min-w-0 flex-1">
        Há uma versão nova do app: <strong>{nova}</strong>. Você está com a {instalada}.
      </p>
      <a
        href={URL_DO_APK}
        target="_blank"
        rel="noreferrer"
        className="rounded-md bg-primary px-3 py-1.5 font-semibold text-primary-foreground"
      >
        Baixar a versão nova
      </a>
      <button type="button" onClick={() => setDispensado(true)} className="px-2 py-1.5 text-muted-foreground">
        Agora não
      </button>
    </div>
  );
}
