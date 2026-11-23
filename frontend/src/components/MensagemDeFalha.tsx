import { ErroApi } from "../lib/api";

export function DetalhesDaFalha({ texto }: { texto?: string }) {
  if (!texto) return null;
  return (
    <details className="mt-2">
      <summary className="cursor-pointer">Detalhes técnicos</summary>
      <p className="mt-1 whitespace-pre-wrap [overflow-wrap:anywhere]">{texto}</p>
    </details>
  );
}

export function MensagemDeFalha({ erro }: { erro: string | Error }) {
  return typeof erro === "string" ? erro : (
    <>
      {erro.message}
      <DetalhesDaFalha texto={erro instanceof ErroApi ? erro.detalhe : undefined} />
    </>
  );
}
