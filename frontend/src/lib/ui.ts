/** Classes repetidas entre formulários. Ficavam duplicadas em cada tela do
 *  protótipo; centralizadas aqui para que um ajuste visual valha em todas. */
export const INPUT_CLS =
  "w-full px-3.5 py-2.5 bg-secondary text-foreground placeholder:text-muted-foreground/40 " +
  "border border-border rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-primary/30 transition";

export const LABEL_CLS =
  "text-xs font-medium text-muted-foreground mb-1.5 block uppercase tracking-wider";

export const BOTAO_PRIMARIO_CLS =
  "w-full py-3 bg-primary text-primary-foreground rounded-xl text-sm font-semibold " +
  "hover:bg-primary/90 transition active:scale-[0.98]";

/** Nome do produto. Existe como constante para não voltar a espalhar string
 *  de marca pelo código — o protótipo do Figma dizia "Dormix" em 3 lugares. */
export const NOME_PRODUTO = "Dormio Smart";
