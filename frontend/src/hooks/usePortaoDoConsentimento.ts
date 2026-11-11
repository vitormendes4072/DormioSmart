import { useCallback, useState } from "react";

/**
 * O portão do consentimento (LGPD-12): roda a ação se a pessoa já consentiu, e
 * senão abre a tela e só a roda depois do "Concordo".
 *
 * `vigente` e `registrar` vêm de fora (o perfil e a rota), para que o portão seja
 * testável sem rede e o mesmo no app e no navegador.
 */
export function usePortaoDoConsentimento(consentimento?: {
  vigente: boolean;
  registrar: () => Promise<void>;
}) {
  const [pendente, setPendente] = useState<(() => unknown) | null>(null);
  const [erro, setErro] = useState<string | null>(null);

  const pedir = useCallback(
    (acao: () => unknown) => {
      // Sem `consentimento` (testes antigos, telas fora do portão) a ação roda:
      // a garantia de verdade é a do banco, não esta tela.
      if (!consentimento || consentimento.vigente) {
        void acao();
        return;
      }
      setErro(null);
      setPendente(() => acao);
    },
    [consentimento],
  );

  const concordar = useCallback(async () => {
    if (!consentimento || !pendente) return;
    try {
      await consentimento.registrar();
    } catch {
      setErro("Não foi possível registrar o consentimento. Tente de novo.");
      return;
    }
    const acao = pendente;
    setPendente(null);
    await acao();
  }, [consentimento, pendente]);

  const recusar = useCallback(() => {
    setPendente(null);
    setErro(null);
  }, []);

  return { telaAberta: pendente !== null, erro, pedir, concordar, recusar };
}
