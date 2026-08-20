import { AlertTriangle, Loader2, Radio } from "lucide-react";

/**
 * Os tres estados que dado real tem e dado ficticio nao tinha.
 *
 * Vazio e erro sao coisas diferentes e precisam ser ditas de forma diferente:
 * "o dispositivo ainda nao enviou nada" nao e a mesma situacao que "nao
 * conseguimos falar com o servidor", e tratar as duas como tela vazia faria o
 * usuario esperar por um dado que nunca vem.
 */

export function Carregando({ mensagem = "Carregando leituras..." }: { mensagem?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
      <Loader2 className="w-6 h-6 animate-spin" />
      <p className="text-sm">{mensagem}</p>
    </div>
  );
}

export function SemLeituras() {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-4">
      <div className="w-12 h-12 rounded-2xl bg-secondary flex items-center justify-center">
        <Radio className="w-6 h-6 text-muted-foreground" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">Nenhuma leitura registrada</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">
          O dispositivo ainda não enviou dados. Verifique se ele está ligado, conectado à
          rede e pareado a esta conta.
        </p>
      </div>
    </div>
  );
}

export function FalhaAoCarregar({
  mensagem,
  aoTentarNovamente,
}: {
  mensagem: string;
  aoTentarNovamente: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center gap-3 py-16 text-center px-4">
      <div className="w-12 h-12 rounded-2xl bg-destructive/10 flex items-center justify-center">
        <AlertTriangle className="w-6 h-6 text-destructive" />
      </div>
      <div>
        <p className="text-sm font-medium text-foreground">Não foi possível carregar</p>
        <p className="text-sm text-muted-foreground mt-1 max-w-sm">{mensagem}</p>
      </div>
      <button
        onClick={aoTentarNovamente}
        className="mt-1 px-4 py-2 rounded-xl text-sm font-semibold bg-secondary text-foreground hover:bg-secondary/70 transition"
      >
        Tentar novamente
      </button>
    </div>
  );
}
