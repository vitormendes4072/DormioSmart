# ML-13 — protocolo temporal da DREAMT

**06/11/2026, antes de treinar ou avaliar a DREAMT.** As previsões P1–P3
e o adendo de 05/11 conservam os critérios e o braço primário.

## Inspeção executada

No Windows local, Python 3.11.9, os 103 SHA-256 oficiais conferiram.
A leitura de cinco colunas, uma gravação por vez, percorreu 100 CSVs
e 203.531.428 linhas. Cada gravação começa em zero e avança em 1/64 s,
sem lacunas ou timestamps fracionários na unidade de ticks. As três
componentes ACC estão presentes em todas as linhas. Cada par de linhas
na fase par repete exatamente as três componentes. Em unidades de g,
a mediana da norma por gravação variou de 0,973 a 1,034 (mediana das
medianas 1,005, amostragem de uma linha por segundo). A unidade vem do
Metadata.txt e a ordem de grandeza observada é compatível com ela.

Todos os arquivos começam com preparação. A primeira pontuação ocorre
entre 3.849 e 10.771 s (mediana 7.769 s). Em 97 arquivos as transições
se alinham à fase dessa primeira pontuação, módulo 30 s. Em três,
as transições pontuadas ocupam duas fases. Foram 233 transições fora
da fase inicial, com máximo de 120 em uma gravação. As fases observadas
nessas três gravações foram 0/20 s, 20/21 s e 10/20 s. Seis gravações
contêm a marca Missing. A inspeção não calculou métricas de modelos.

## Regras fixadas para a rodada

- Usar somente TIMESTAMP, ACC_X/Y/Z e Sleep_Stage da versão 2.2.0 a
  64 Hz. Recuperar os 32 Hz nativos tomando a primeira linha de cada
  par repetido. Dividir ACC por 64 para obter g. Trabalhar em ticks
  inteiros e validar o alinhamento dos pares.
- Ancorar a grade de 30 s na primeira pontuação após a preparação.
  Exigir uma única fase para as transições consecutivas observadas
  depois da âncora. Excluir as três gravações de fase ambígua por esse
  critério de qualidade. As transições não sustentam uma única grade
  nessas gravações. Uma análise por blocos exigiria outro protocolo.
  Os identificadores das exclusões ficam na evidência local.
- Uma época exige as 1.920 linhas de 64 Hz, em ordem, e aceleração
  finita. Descartar cauda incompleta e qualquer época com lacuna ou
  ACC ausente. Usar W como vigília e N1/N2/N3/R como sono. Preparação,
  Missing e épocas sem rótulo uniforme ficam fora da avaliação.
- Extrair as oito features com a implementação comum, por bloco de
  ACC completo e contínuo. Preservar participante, gravação e índice
  original de época. Contexto e Viterbi usam os segmentos após remover
  as épocas sem rótulo, portanto respeitam as quebras da grade retida.
- Treinar com os 92 participantes Wearanize+ e a configuração
  aec203907e6f, seed 20260910, uma thread nativa. O ML-04 confere os
  hashes de X/y/IDs dos três braços contra a rodada corrigida da ML-17.
  Reutilizar as quatro configurações do ML-04, com pulso primário.
  O limiar e as transições HMM seguem o código corrigido. A
  normalização por participante usa as features de sua gravação.
- Comparar contra a âncora trivial da DREAMT. Reamostrar 2.000 vezes
  por participante, com seed 20260910. Os contrastes pareados usam os
  mesmos participantes em cada comparação. Aplicar os critérios de
  P1–P3 congelados, incluindo o requisito conjunto de P2. Relatar as
  demais células, F1 e as matrizes de confusão como complementos.

Os 97 arquivos restantes compõem a análise primária. Excluir três
gravações limita a inferência à coorte avaliável pelo critério acima.
Os dados, caches e resultados individuais ficam fora do Git.

Fontes consultadas: [PhysioNet v2.2.0](https://physionet.org/content/dreamt/2.2.0/)
e [descrição original, Apêndice B.2](https://proceedings.mlr.press/v248/wang24a.html).
