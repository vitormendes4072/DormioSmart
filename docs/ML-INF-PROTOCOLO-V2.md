# ML-INF v2 — protocolo prévio ao treino

Usar o braço `cabeca`, `qualidade="original"`, e a configuração
`item9_ctx11` do ML-04 após a correção temporal da ML-17. A variante original
é reamostrada a 32 Hz sem a quantização e a saturação adicionais do braço E4.
Manter as oito features canônicas e a regressão logística balanceada do
ML-04 com a mesma semente, parâmetros padrão e `max_iter=2000`. Uma thread
nativa. A saída sem HMM é `LogisticRegression.predict`. O corte do modelo
binário é logit estritamente positivo, com empate em vigília.

## Unidade e cobertura

Uma época válida tem as oito features numéricas e finitas, na ordem canônica.
Na entrada do modelo, o `d_angulo` ausente apenas na primeira época ou
depois de lacuna do servidor é representado por zero. Épocas com feature
inválida ficam fora da normalização e da janela, preservando a descontinuidade
temporal. No histórico, as features e os filtros de cobertura publicados são
preservados e conferidos pela mesma condição de finitude.

O mínimo operacional é 23 épocas válidas por gravação, equivalentes a
11 min 30 s e ao tamanho de uma janela ±11. Abaixo disso, a inferência
recusa a noite e informa a contagem observada e a exigida. O piso vale para
a gravação inteira. Um segmento curto é aceito dentro de uma noite elegível.
Noites históricas abaixo do piso seriam identificadas separadamente e
preservadas na reprodução histórica se a normalização publicada for definida.

Calcular média e desvio de cada feature dentro de cada gravação, antes do
contexto. Usar desvio amostral (`ddof=1`) e substituir desvios menores que
`1e-9` por 1. O LOSO agrupa todas as gravações da pessoa na mesma dobra.
O contexto replica as épocas das pontas de cada segmento e segue a ordem
das colunas produzida por `empilhar_contexto`.

## Reprodução e paridade

Ajustar a v2 no treino congelado da ML-17. Comparar o JSON exportado com
o modelo ajustado e com os resultados publicados da Newcastle esquerda,
Walch principal, Walch todos e DREAMT. Usar as mesmas populações, features,
segmentos, métricas e semente de bootstrap. Comparar o LOSO e as coortes
externas com sempre sono. Registrar a v1 lado a lado onde houver avaliação
na mesma população. Nenhuma coorte externa orienta ajuste.

Gerar duas noites sintéticas de oito horas com o simulador C2, semente 7,
uma contínua e uma com uma época removida no meio. Passar os payloads por
`derivar_noite`. Comparar com o ML usando os mesmos vetores de gravidade.
O servidor usa uma referência angular por noite e quebra na primeira época
e acima de 45 s para `d_angulo`. O ML histórico usa a sequência que cada
carregador entrega e o índice original para segmentar o contexto. Exercitar
em teste os pontos onde as regras divergem, incluindo 45 s exatos.

Exportar o modelo sem parâmetros de escala globais, com a lista explícita
de colunas, procedência, atribuição CC BY 4.0 e os parâmetros de inferência.
Os dourados fixam os payloads, features do servidor, segmentos, probabilidades
do scikit-learn com tolerância absoluta de `1e-12` e classes exatas.
Incluir casos sintéticos de logit dos dois lados do corte e um empate exato.
Predições, rótulos e notas de coortes ficam locais.
