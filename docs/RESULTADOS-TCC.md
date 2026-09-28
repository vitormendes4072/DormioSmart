# Resultados — texto pronto para o TCC (`DOC-08`)

> **Como usar este arquivo.** O que está entre as linhas `── TEXTO ──` é redigido em tom
> acadêmico e pode ser colado no documento com ajustes mínimos de numeração e de referência.
> O que está fora delas são **notas para você**, não para o texto final. A convenção é a
> mesma de `docs/LIMITACOES-TCC.md`, e os dois textos são feitos para conviver: este
> apresenta os resultados, aquele declara os limites com que devem ser lidos.
>
> **Fundamentação:** diferentemente do `LIMITACOES-TCC.md`, cujos números vêm em boa parte
> da literatura, **todo número deste arquivo foi medido neste trabalho** e sai de
> `ml/experimentos/saida/*.json`. A procedência de cada um, com a chave do JSON e o comando
> que o reproduz, está em **"Procedência de cada número"**, ao final. Nada aqui foi escrito
> de memória.
>
> **Sugestão de posição:** capítulo próprio de Resultados, antes da seção de Limitações.
> A ordem importa: a seção Y.1 estabelece contra o que tudo será lido, e sem ela os números
> das seções seguintes não têm referência.
>
> ⚠️ **Convenção de notação adotada no texto.** Intervalos entre colchetes são **IC 95% de
> bootstrap sobre sujeitos** (2 000 reamostragens, semente 20260910), com o **participante**
> como unidade de reamostragem. Diferenças entre configurações são reportadas como **IC 95%
> de bootstrap pareado da diferença** sobre os mesmos participantes, e nunca como
> sobreposição de intervalos individuais — os dois critérios estão implementados lado a lado
> no código, e o texto reporta o pareado. Onde não há intervalo, é porque a medição não
> produziu um (ver Y.1 e a nota de procedência).

---

## Nota de enquadramento (leia antes de colar)

Três decisões de apresentação estão embutidas no texto abaixo e conviria não desfazê-las na
hora de colar:

1. **A acurácia nunca aparece sozinha.** Sempre que há acurácia, há especificidade e kappa ao
   lado, e o classificador trivial na linha de cima. Essa é a consequência direta do §0.2 do
   `ML-DATASETS-E-PLANO.md`.
2. **O número que vale é o externo.** As seções Y.3 a Y.5 são validação interna; a Y.6 é
   externa e reduz o desempenho. O texto declara isso como a estimativa defensável, e não
   como ressalva final.
3. **O achado da Y.6 é metodológico e vale independentemente do desempenho do protótipo.**
   Se o TCC tiver seção de contribuições, é de lá que se referencia a Y.6.

---

── TEXTO ────────────────────────────────────────────────────────────────────

## Y. Resultados

Este capítulo apresenta os resultados obtidos na tarefa de discriminação entre sono e vigília
a partir de aceleração bruta. A exposição segue a ordem em que os experimentos foram
conduzidos, que é também a ordem em que cada resultado condiciona o seguinte: estabelecem-se
primeiro os classificadores de referência (Y.1), mede-se em seguida o desempenho em base
pública com rotulagem polissonográfica (Y.2), quantifica-se o efeito da posição do sensor
(Y.3) e a assimetria da transferência entre posições (Y.4), avaliam-se modificações do
procedimento (Y.5), verifica-se a reprodução dos ganhos em coorte independente (Y.6) e
mede-se, por fim, o efeito da lateralidade do sensor (Y.7).

Todas as métricas reportadas são de **época a época**, com épocas de 30 s — a resolução dos
rótulos polissonográficos das bases empregadas. A validação interna é por
*leave-one-subject-out*, com o participante como unidade de agrupamento, de modo que nenhum
participante presente no teste participa do ajuste do modelo. A agregação das métricas é
**por participante**, não por época: a média reportada é a média entre participantes, e o
intervalo de confiança de 95% provém de bootstrap sobre participantes. Essa escolha é
deliberada — agregar por época trataria as centenas de épocas de uma mesma noite como
observações independentes, o que estreitaria artificialmente os intervalos.

As grandezas reportadas são a **acurácia**, a **especificidade** (fração de épocas de vigília
corretamente identificadas), a **sensibilidade** (fração de épocas de sono corretamente
identificadas) e o **coeficiente kappa de Cohen**. Pelas razões expostas na seção de
metodologia e retomadas em Y.1, a especificidade e o kappa são as grandezas sobre as quais as
conclusões se apoiam; a acurácia é reportada por comparabilidade com a literatura, não como
evidência.

### Y.1 Classificadores de referência

#### Y.1.1 O classificador trivial

O primeiro resultado medido não é um modelo, e sim um **classificador trivial** que atribui a
totalidade das épocas à classe "sono", ignorando por completo o sinal do acelerômetro. Sua
função é fornecer o piso contra o qual qualquer outro resultado deve ser lido.

Esse classificador apresenta, por construção, sensibilidade de 1,000, especificidade de 0,000
e coeficiente kappa de 0,000, e apresenta **acurácia igual à prevalência de sono da base em
que é medido**. Nas três bases empregadas neste trabalho, essa acurácia foi de 0,703
[0,616 a 0,776] nos 27 participantes da coorte de Newcastle e de 0,895 [0,877 a 0,912] nos 92
participantes da base Wearanize+. A magnitude desses valores é o argumento central da seção:
**um classificador que não realiza medição alguma alcança, nessas bases, acurácia de 70% e de
90%**, respectivamente.

Registra-se que o coeficiente kappa é a única das quatro métricas que o classificador trivial
não consegue inflar — ele vale exatamente zero, por construção, em qualquer prevalência —, e é
essa propriedade que justifica sua adoção como métrica principal.

#### Y.1.2 Os algoritmos clássicos de actigrafia e a degeneração com escala arbitrária

Foram implementados os algoritmos de Cole-Kripke e de Sadeh, referências consolidadas na
literatura de actigrafia. Duas diferenças em relação à formulação original são declaradas
explicitamente, por afetarem a interpretação dos valores:

**Primeira diferença — o substituto de contagem.** Ambos os algoritmos operam sobre
*activity counts*, que são a saída de um algoritmo proprietário não publicado, e não uma
grandeza física. Não existe função pública que converta aceleração em contagens de Actiwatch.
O que se implementou, portanto, foi um **substituto documentado** — filtragem passa-banda de
0,25 a 3 Hz, retificação e integração por época. Os resultados a seguir devem ser lidos como
"Cole-Kripke aplicado a um substituto de contagem", e não como o algoritmo original.
**Segunda diferença:** os algoritmos rodam sobre épocas de 30 s, e não sobre os 60 s da
formulação original.

**A degeneração com escala arbitrária.** Aplicados ao substituto de contagem com escala
arbitrária, isto é, sem calibração alguma do fator de escala, **os dois algoritmos degeneram
exatamente para o classificador trivial**: na coorte de Newcastle, ambos produziram acurácia
de 0,697, sensibilidade de 1,000, especificidade de 0,000 e kappa de 0,000 — os mesmos quatro
valores do classificador que ignora o sensor, e não valores próximos a eles. Nenhuma época foi
classificada como vigília.

Esse resultado é registrado por ser, ele próprio, evidência de uma afirmação relevante: os
limiares publicados por Cole-Kripke e por Sadeh foram ajustados à escala de contagem de um
fabricante específico, e **não transferem para uma escala derivada de aceleração bruta**. A
degeneração não é falha de implementação — é a manifestação, em métrica, de que contagens
proprietárias não se reproduzem a partir da grandeza física. Trata-se de constatação com
consequência prática direta: qualquer trabalho que pretenda aplicar esses algoritmos a
aceleração bruta precisa calibrar a escala, e a calibração é etapa do método, não detalhe de
implementação.

A calibração adotada é de **um único parâmetro** — o fator de escala do substituto de
contagem —, estimada **exclusivamente nos participantes de treino de cada dobra**, com os
limiares publicados mantidos intactos. Com a escala assim calibrada, os dois algoritmos
deixam de degenerar e passam a discriminar, conforme a Y.2.

#### Y.1.3 A identidade entre acurácia, sensibilidade e especificidade

A relevância do classificador trivial não se restringe a este trabalho, e pode ser
demonstrada sobre valores já publicados por meio de uma identidade aritmética exata. Sendo
`p` a fração de épocas de sono de um registro, a acurácia de um classificador binário
satisfaz

> acurácia = p · sensibilidade + (1 − p) · especificidade

de onde se isola a prevalência implicada pelos valores publicados por um estudo:

> p = (acurácia − especificidade) / (sensibilidade − especificidade)

Como a acurácia do classificador trivial é igual a `p`, a identidade permite recuperar, a
partir de sensibilidade, especificidade e acurácia publicadas, **a acurácia que o
classificador trivial teria alcançado naquele mesmo estudo**. Aplicada a dois trabalhos da
literatura que publicam as três grandezas conjuntamente, ela produz:

| Estudo | `p` implicado | Acurácia do trivial | Acurácia publicada | Diferença |
|---|:---:|:---:|:---:|:---:|
| LI; HALAKI; CHOW (2025) — actígrafo de grau clínico | 0,878 | **0,878** | 0,873 | −0,5 pt |
| WALCH et al. (2019) — movimento, frequência cardíaca e proxy circadiano | 0,910 | **0,910** | 0,900 | −1,0 pt |

Nos dois casos, o classificador que ignora o sensor apresenta acurácia **ligeiramente
superior** à do método publicado. São dois estudos independentes, com populações, aparelhos e
modalidades de sensor distintas, e o resultado é o mesmo.

> **Registra-se que esta derivação é deste trabalho.** Nenhum dos dois artigos citados
> apresenta essa comparação; o que deles se utiliza são apenas os três valores publicados. A
> identidade empregada é aritmética exata, e não aproximação ou estimativa.

Cabe a ressalva de que a constatação **não** implica que a actigrafia seja inútil: o
classificador trivial não produz tempo acordado após o início do sono, latência, número de
despertares nem fragmentação, que são precisamente as saídas de interesse clínico. O que a
identidade estabelece é a **inadequação da acurácia como métrica de síntese** neste domínio.
É por essa razão que todos os resultados a seguir são apresentados com especificidade e kappa
ao lado, e com o classificador trivial medido na própria coorte.

### Y.2 Primeira medição em base com rotulagem polissonográfica

A primeira medição sobre dado real empregou a coorte de Newcastle, com acelerometria de punho
por GENEActiv a 85,70 Hz e rotulagem polissonográfica manual. Após o descarte de um
participante cuja janela de gravação do acelerômetro não intersecta a janela de pontuação
polissonográfica — inconsistência rastreável ao cabeçalho do próprio arquivo original, e não
erro de leitura —, a medição compreendeu **27 participantes e 59 825 épocas**, com
**prevalência de sono de 0,697**.

| Configuração | Acurácia | Sensibilidade | Especificidade | Kappa |
|---|---:|---:|---:|---:|
| Trivial "sempre dormindo" | 0,697 | 1,000 | 0,000 | 0,000 |
| Cole-Kripke, escala arbitrária | 0,697 | 1,000 | 0,000 | 0,000 |
| Sadeh, escala arbitrária | 0,697 | 1,000 | 0,000 | 0,000 |
| Cole-Kripke, escala calibrada | 0,727 | 0,827 | 0,499 | 0,335 |
| Sadeh, escala calibrada | 0,763 | 0,871 | 0,516 | 0,408 |
| Regressão logística | 0,738 | 0,841 | 0,501 | 0,355 |
| Regressão logística com suavização | 0,739 | 0,841 | 0,504 | 0,359 |

Três leituras se extraem da tabela.

**A primeira** é a degeneração já discutida em Y.1.2, aqui visível nas duas linhas de escala
arbitrária: elas reproduzem o classificador trivial em todas as quatro métricas.

**A segunda** é que a diferença de acurácia entre o melhor modelo e o classificador trivial é
de aproximadamente quatro pontos percentuais, enquanto a diferença de especificidade é de
cerca de cinquenta pontos e a de kappa é de 0,408. A acurácia é, portanto, a métrica que menos
distingue as configurações, o que confirma empiricamente o argumento de Y.1.3.

**A terceira** é que o algoritmo de Sadeh, com escala calibrada, supera a regressão logística
nas três métricas nesta coorte — kappa de 0,408 contra 0,355 e especificidade de 0,516 contra
0,501. A regressão logística empregada nesta medição utiliza contexto de ±2 épocas, ao passo
que o algoritmo de Sadeh opera sobre uma janela de aproximadamente onze minutos. Essa
observação motivou o experimento relatado em Y.5, cujo resultado a confirma.

Registra-se que as métricas desta tabela são agregadas sobre o conjunto das épocas, sem
intervalo de confiança de bootstrap — a agregação por participante, com o intervalo
correspondente, foi introduzida a partir do experimento de transferência entre posições, e é
adotada em todas as seções seguintes. Registra-se ainda que o total de 59 825 épocas
corresponde às gravações disponíveis dos 27 participantes, que incluem ambos os punhos onde há
registro bilateral; o agrupamento do *leave-one-subject-out* é o participante, de modo que os
dois punhos de um mesmo participante permanecem sempre do mesmo lado da partição.

### Y.3 Transferência entre posições de sensor, e o controle de qualidade do sensor

A questão de pesquisa deste trabalho exige quantificar quanto se perde ao substituir um sensor
vestido por um sensor apoiado no travesseiro. Não existe base pública que reúna acelerometria
captada em travesseiro com rotulagem validada por polissonografia; o que existe, e foi
empregado, é uma base com **registros simultâneos de múltiplas posições no mesmo
participante**, sob a mesma noite e a mesma pontuação polissonográfica.

O experimento foi conduzido na coleção aberta Wearanize+, sobre os **92 participantes** que
dispõem simultaneamente de registro de cabeça e de punho, com prevalência de sono de
**0,895**. Treinou-se um modelo em cada posição e avaliou-se em cada posição, produzindo uma
matriz de transferência.

**O controle de qualidade do sensor.** Uma matriz construída apenas com as duas posições
originais confundiria duas variáveis distintas: o sensor da cabeça registra a 256 Hz com 12
bits, e o sensor de punho registra a 32 Hz com 8 bits, isto é, com grade de quantização
aproximadamente dezesseis vezes mais grosseira. Um decréscimo de desempenho medido entre essas
duas células não poderia ser atribuído à posição nem à qualidade do sensor isoladamente. O
experimento foi conduzido, por essa razão, em **três braços**: a cabeça em qualidade original,
o **mesmo sinal de cabeça degradado para a grade do sensor de punho** — 32 Hz e 8 bits — e o
punho em qualidade original. A comparação entre o primeiro e o segundo braço isola o custo da
**qualidade do sensor**, com a posição constante; a comparação entre o segundo e o terceiro
isola o custo da **posição**, com a qualidade constante.

As nove células da matriz compartilham as mesmas 92 dobras: em cada dobra, um participante é
deixado de fora, treina-se um modelo por braço com os 91 restantes e cada modelo é avaliado
nos três braços do participante excluído. A única coisa que varia de uma célula para outra é
qual sinal treinou o modelo e qual sinal o avaliou, nunca o particionamento.

Coeficiente kappa por célula, com IC 95%:

| Treino ↓ / Teste → | Cabeça | Cabeça degradada | Punho |
|---|---:|---:|---:|
| **Cabeça** | **0,398** [0,365 a 0,431] | 0,067 [0,054 a 0,082] | 0,046 [0,037 a 0,055] |
| **Cabeça degradada** | 0,422 [0,388 a 0,456] | **0,327** [0,299 a 0,358] | 0,328 [0,296 a 0,360] |
| **Punho** | 0,378 [0,347 a 0,411] | 0,376 [0,347 a 0,406] | **0,377** [0,347 a 0,408] |

Os classificadores de referência medidos sobre os mesmos 92 participantes situam-se em kappa
de 0,000 para o trivial e entre 0,435 [0,405 a 0,465] e 0,462 [0,428 a 0,494] para o algoritmo
de Sadeh com escala calibrada, conforme o braço.

**A decomposição do custo.** Lidas pelas diagonais, que são o desempenho de cada braço na
posição em que foi treinado, as duas comparações controladas produzem:

- **custo da qualidade do sensor:** kappa decresce de 0,398 [0,365 a 0,431] na cabeça original
  para 0,327 [0,299 a 0,358] na cabeça degradada, isto é, **0,071** atribuível à degradação da
  grade de aquisição, com a posição mantida constante;
- **custo da posição:** kappa decresce de 0,377 [0,347 a 0,407] no punho para 0,327
  [0,299 a 0,358] na cabeça degradada, isto é, **0,050** atribuível à posição, com a qualidade
  de aquisição mantida constante.

A leitura que se extrai é que, nesta base e nesta tarefa, **o custo de mover o sensor do punho
para a cabeça é da ordem de 0,05 em kappa, e é menor que o custo de degradar a grade de
aquisição**, que é da ordem de 0,07. A direção do efeito de posição é a antecipada na seção de
limitações a partir da literatura de posicionamento — a cabeça apresenta desempenho inferior ao
punho —, e a magnitude é modesta. Registra-se, contudo, que a posição de cabeça desta base é um
sensor **acoplado à cabeça**, não apoiado no travesseiro: o experimento quantifica o custo da
posição anatômica, e não o custo do acoplamento mecânico através de um travesseiro, que
permanece não medido.

### Y.4 A assimetria da transferência, e a ablação de duas hipóteses

A matriz da seção Y.3 apresenta uma assimetria que não é explicável pelo custo de posição, e
que constitui o resultado original deste trabalho.

**A assimetria.** O modelo treinado no punho transfere para as três posições sem decréscimo
distinguível: kappa de 0,377, 0,376 e 0,378, com intervalos de confiança amplamente
sobrepostos. O modelo treinado na cabeça, ao contrário, **colapsa** ao ser avaliado nas outras
duas: o kappa decresce de 0,398 [0,365 a 0,431] na própria posição para 0,067
[0,054 a 0,082] na cabeça degradada e para 0,046 [0,037 a 0,055] no punho — decréscimos de
0,332 e 0,352 em kappa, isto é, de 83,3% e 88,5% do valor na diagonal. A
transferência entre posições, portanto, **não é simétrica**: uma direção atravessa e a outra
não.

Duas hipóteses concorrentes explicariam o colapso, e a distinção entre elas tem consequência
prática oposta. Pela primeira, **hipótese de escala**, o colapso é de normalização: o modelo
treinado na cabeça aprende a operar sobre a faixa de valores das características daquele
sensor, e ao receber valores de outra faixa desloca a fronteira de decisão sem que informação
alguma tenha sido perdida; sendo esse o caso, o colapso é recuperável sem acesso a rótulo do
domínio de destino. Pela segunda, **hipótese de informação**, as características extraídas de
uma posição não contêm a informação necessária para discriminar sono e vigília na outra;
sendo esse o caso, o colapso não é recuperável por normalização alguma. As duas foram
submetidas a ablação.

As ablações a seguir constituem execução independente do mesmo delineamento, e dispõem de sua
própria matriz de referência; os valores dessa matriz reproduzem os da seção Y.3 até a terceira
casa decimal — 0,401 contra 0,398 na diagonal de cabeça, 0,331 contra 0,327 na cabeça degradada
e 0,377 em ambas no punho. As frações de recuperação relatadas abaixo são calculadas
integralmente dentro da execução da ablação, de modo a não misturar as duas rodadas.

**Ablação 1 — reajuste do normalizador no domínio de destino.** Refazer o normalizador de
características sobre o domínio de teste, mantendo o modelo e os rótulos de treino
inalterados, recupera o kappa da transferência cabeça → punho de 0,047 [0,037 a 0,056] para
**0,322** [0,292 a 0,353], o que corresponde a **77,6%** da lacuna entre a célula colapsada e
a diagonal de origem. Na transferência cabeça → cabeça degradada, a recuperação é de 0,067
[0,054 a 0,083] para 0,183 [0,160 a 0,208], isto é, **34,5%** da lacuna.

**Ablação 2 — normalização por participante.** Normalizar as características por participante
— procedimento que **não utiliza rótulo algum do domínio de destino** e, portanto, não
constitui vazamento — recupera a transferência cabeça → punho para **0,298**
[0,260 a 0,338], correspondentes a **71,0%** da lacuna, e a transferência cabeça → cabeça
degradada para 0,206 [0,175 a 0,241], correspondentes a **41,5%**. Por ser recuperação
comparável à da ablação 1 sem acesso ao domínio de destino, essa normalização foi adotada como
representação de base em todos os experimentos subsequentes.

**Ablação 3 — modelo sem normalizador.** As duas ablações acima estabelecem que a escala
responde por parte substancial do colapso, mas não permitem concluir que responda pela sua
totalidade. Para isolar o residual, a matriz foi refeita com **floresta aleatória**, modelo
que não possui etapa de normalização das características. Nessa configuração, a transferência
a partir da cabeça continua a apresentar decréscimo: o kappa decresce de 0,488
[0,447 a 0,527] na diagonal para 0,257 [0,226 a 0,294] no punho e 0,302 [0,266 a 0,338] na
cabeça degradada, isto é, decréscimos de **0,230 e 0,186** em kappa. Registra-se que a
regressão logística com o normalizador simplesmente removido **não** reproduz esse
comportamento — ela permanece colapsada, com kappa de 0,072 [0,058 a 0,086] no punho —, o que
indica que a insensibilidade da floresta aleatória a deslocamentos de escala é propriedade do
particionamento recursivo, e não consequência de se ter retirado uma etapa do fluxo.

**A conclusão, e ela é composta.** O efeito é **misto**, e os dois componentes foram
quantificados separadamente:

1. **Componente de escala**, responsável por **71% a 78%** da lacuna na transferência
   cabeça → punho, recuperável por normalização por participante, sem rótulo do destino.
2. **Componente residual**, da ordem de **0,19 a 0,23 em kappa**, que subsiste em um modelo
   sem normalizador e é, portanto, atribuível a diferença genuína entre os domínios.

Não se afirma, por conseguinte, que a assimetria seja um achado sobre a informação contida em
cada posição, nem que seja um artefato de normalização. Ela é as duas coisas, em proporções
medidas, e a proporção depende do par de posições: a componente de escala responde por cerca
de três quartos da lacuna na transferência para o punho e por cerca de dois quintos na
transferência para a cabeça degradada.

**Uma medição auxiliar** corrobora a existência do componente residual. A divergência
padronizada das distribuições de características entre os braços é de 1,353 entre cabeça e
cabeça degradada, 1,066 entre cabeça e punho e 0,668 entre cabeça degradada e punho, dominada,
nos três pares, pela taxa de cruzamentos por zero — 1,860, 1,108 e 0,483, respectivamente.
Isto é, a característica que mais divergiu entre os braços é a que depende mais diretamente da
taxa de amostragem e da grade de quantização, o que é consistente com o custo de qualidade de
sensor medido em Y.3.

### Y.5 Modificações avaliadas sobre a configuração de base

Sobre a configuração de base — características normalizadas por participante, regressão
logística com ponderação de classes e contexto de ±2 épocas —, avaliaram-se cinco
modificações, em validação interna *leave-one-subject-out* sobre os mesmos 92 participantes e
nos três braços. Cada modificação é reportada contra a base do próprio braço, com IC 95% de
bootstrap pareado da diferença. Adota-se o critério de que **diferença cujo intervalo contém
zero não é contada como ganho**.

Configuração de base, por braço:

| Braço | Kappa | Especificidade |
|---|---:|---:|
| Cabeça | 0,383 [0,348 a 0,418] | 0,724 [0,690 a 0,758] |
| Cabeça degradada | 0,325 [0,292 a 0,359] | 0,700 [0,666 a 0,734] |
| Punho | 0,356 [0,325 a 0,388] | 0,682 [0,647 a 0,717] |

Modificações, no braço de cabeça:

| Modificação | Kappa | Δ kappa (pareado) | Especificidade | Δ especificidade (pareado) |
|---|---:|---|---:|---|
| Retirada da ponderação de classes | 0,417 [0,386 a 0,450] | +0,034 [−0,005 a +0,073] | 0,379 [0,344 a 0,415] | **−0,345** [−0,368 a −0,322] |
| Limiar de decisão de Youden | 0,333 [0,296 a 0,370] | −0,050 [−0,060 a −0,040] | 0,792 [0,760 a 0,822] | +0,068 [+0,056 a +0,080] |
| Mediana móvel de 5 épocas | 0,399 [0,363 a 0,435] | +0,016 [+0,012 a +0,020] | 0,734 [0,699 a 0,768] | +0,010 [+0,006 a +0,014] |
| **Modelo oculto de Markov de 2 estados** | **0,507** [0,463 a 0,548] | **+0,123** [+0,105 a +0,142] | 0,727 [0,685 a 0,767] | +0,003 [−0,015 a +0,022] |
| **Contexto ampliado para ±11 épocas** | 0,458 [0,418 a 0,499] | **+0,075** [+0,060 a +0,090] | **0,825** [0,791 a 0,856] | **+0,101** [+0,083 a +0,118] |

As duas últimas linhas reproduzem-se nos três braços, e a reprodução é parte do resultado:

| Braço | Δ kappa (Markov) | Δ kappa (±11) | Δ especificidade (±11) |
|---|---|---|---|
| Cabeça | +0,123 [+0,105 a +0,142] | +0,075 [+0,060 a +0,090] | +0,101 [+0,083 a +0,118] |
| Cabeça degradada | +0,122 [+0,101 a +0,145] | +0,082 [+0,066 a +0,099] | +0,106 [+0,088 a +0,126] |
| Punho | +0,123 [+0,105 a +0,142] | +0,058 [+0,041 a +0,075] | +0,119 [+0,099 a +0,139] |

Quatro leituras.

**A imposição de estrutura temporal rende, mas apenas na formulação em que o custo de
transição é estimado dos dados.** A mediana móvel de cinco épocas — suavização de janela fixa
— produz ganho de kappa de +0,016 [+0,012 a +0,020] no braço de cabeça, e não superior a
+0,016 em nenhum braço. O modelo oculto de Markov de dois estados, com a matriz de transição
contada nos rótulos dos participantes de treino de cada dobra, produz +0,123
[+0,105 a +0,142]. A diferença entre os dois procedimentos está em que o segundo estima o
custo de trocar de estado a partir dos dados, em vez de arbitrá-lo por uma janela fixa.

**A ampliação da janela de contexto é a única modificação que melhora kappa e especificidade
simultaneamente.** Passar o contexto de ±2 para ±11 épocas — aproximadamente onze minutos —
produz ganho de kappa de +0,075 [+0,060 a +0,090] e de especificidade de +0,101
[+0,083 a +0,118] no braço de cabeça, com reprodução nos outros dois. O resultado confirma a
suspeita registrada em Y.2: o algoritmo de Sadeh superava a regressão logística naquela
medição porque dispunha de uma janela temporal aproximadamente cinco vezes mais longa, e não
por propriedade do algoritmo em si. Sendo a especificidade a métrica crítica neste domínio,
esta é a modificação de maior relevância prática entre as avaliadas.

**Duas das modificações não constituem melhorias, e foram medidas como contrafactuais.** A
retirada da ponderação de classes existe para quantificar o que a ponderação compra:
retirá-la reduz a especificidade em 0,345 [0,322 a 0,368] e não produz ganho de kappa fora do
intervalo. O limiar de Youden troca uma métrica pela outra — ganha 0,068 [0,056 a 0,080] de
especificidade e perde 0,050 [0,040 a 0,060] de kappa —, sem melhorar ambas.

**A escolha do critério de significância altera o veredito em um caso.** Dois critérios foram
computados em paralelo: a exigência de que os IC 95% individuais das duas configurações não se
sobreponham, e o IC 95% de bootstrap pareado da diferença sobre os mesmos 92 participantes.
Como os braços rodam sobre os mesmos participantes e a variância entre participantes é
elevada — desvio-padrão de aproximadamente 0,16 em kappa — e comum às duas configurações,
exigir intervalos disjuntos descartaria como ruído efeitos que a comparação pareada reproduz
em quase todos os participantes. O veredito adotado neste trabalho é o **pareado**; o critério
conservador é reportado como piso. O ganho de kappa do contexto ampliado no braço de cabeça é
o caso em que os dois critérios divergem: +0,075 [+0,060 a +0,090] pelo pareado, mas com
intervalos individuais sobrepostos.

### Y.6 Validação em coorte independente

Todos os resultados até aqui são de validação interna. O *leave-one-subject-out* controla o
vazamento de informação entre participantes, mas não controla as demais fontes de
homogeneidade de uma mesma coorte: aparelho, protocolo de aquisição, critérios de pontuação,
laboratório e perfil da população permanecem constantes. Para medir o que resta do desempenho
quando essas fontes também variam, conduziu-se validação externa.

**Protocolo.** O modelo foi ajustado na totalidade dos 92 participantes da base de
desenvolvimento, de uma vez, e aplicado a **27 participantes** da coorte de Newcastle —
adquirida com acelerômetro de outro fabricante, em outro centro e com outra equipe de
pontuação —, **sem reajuste algum**: sem reestimação do normalizador no domínio de teste, sem
recalibração do limiar de decisão e sem qualquer acesso aos rótulos da coorte externa anterior
à medição. O braço de teste reportado é o punho esquerdo, com 30 440 épocas e prevalência de
sono de 0,699.

| Treino | Configuração | Kappa | Especificidade |
|---|---|---:|---:|
| — | **Trivial, medido no Newcastle** | **0,000** | **0,000** |
| Punho | Base (±2) | 0,265 [0,191 a 0,346] | 0,412 [0,347 a 0,483] |
| Punho | Com modelo de Markov | 0,301 [0,218 a 0,383] | 0,375 [0,312 a 0,445] |
| Punho | **Contexto ±11** | **0,334** [0,254 a 0,416] | **0,507** [0,442 a 0,576] |
| Punho | Contexto ±11 e Markov | 0,338 [0,258 a 0,416] | 0,466 [0,405 a 0,532] |
| Cabeça | Base (±2) | 0,239 [0,163 a 0,317] | 0,357 [0,296 a 0,427] |
| Cabeça | Contexto ±11 | 0,301 [0,217 a 0,384] | 0,438 [0,369 a 0,516] |

**Todas as configurações permanecem acima do classificador trivial medido na própria coorte**,
com o IC 95% de kappa integralmente acima de zero. O método, portanto, generaliza para coorte
não observada — o que não estava garantido.

**A magnitude da degradação.** Na melhor configuração, o coeficiente kappa decresce de
**0,414** [0,373 a 0,453], obtido em validação interna, para **0,334** [0,254 a 0,416] na
coorte externa, e a especificidade decresce de **0,802** [0,768 a 0,831] para **0,507**
[0,442 a 0,576]. A perda concentra-se, portanto, na métrica identificada como crítica neste
domínio: aproximadamente trinta pontos percentuais de especificidade não sobrevivem à troca de
coorte. Considera-se, por consequência, que **o desempenho externo, e não o interno, constitui
a estimativa defensável do comportamento esperado do método em população não observada**.

Registra-se que os coeficientes kappa das duas condições **não são diretamente comparáveis
entre si**, uma vez que o kappa depende da prevalência da classe majoritária, que é de 0,699
na coorte externa e de 0,895 na base de desenvolvimento. Por essa razão, a leitura adotada não
é a comparação absoluta entre os dois valores, e sim a comparação de cada um contra o
classificador trivial medido **na própria coorte**, que por construção apresenta kappa nulo.

**O resultado metodológico.** A validação externa produziu um resultado que condiciona todo o
procedimento de seleção de modelo adotado neste trabalho, e que se julga a contribuição mais
relevante do capítulo. Comparando-se as configurações **entre si**, nos mesmos 27
participantes, com IC 95% de bootstrap pareado da diferença:

| Treino | Modificação sobre a base | Δ kappa | Δ especificidade |
|---|---|---|---|
| Punho | Modelo de Markov | +0,036 [+0,008 a +0,067] | **−0,037** [−0,058 a −0,014] |
| Punho | Contexto ±11 | **+0,069** [+0,039 a +0,102] | **+0,095** [+0,065 a +0,130] |
| Cabeça | Modelo de Markov | +0,008 [−0,011 a +0,028] | **−0,050** [−0,073 a −0,029] |
| Cabeça | Contexto ±11 | **+0,062** [+0,040 a +0,086] | **+0,081** [+0,057 a +0,108] |
| Cabeça degradada | Modelo de Markov | +0,027 [+0,003 a +0,055] | **−0,037** [−0,062 a −0,010] |
| Cabeça degradada | Contexto ±11 | **+0,063** [+0,031 a +0,095] | **+0,087** [+0,059 a +0,116] |

Em validação interna, o modelo de Markov apresentava-se nitidamente superior, com ganho de
kappa de +0,123 [+0,105 a +0,142] — aproximadamente o dobro do obtido pela ampliação do
contexto. Em coorte independente, essa vantagem praticamente desaparece: resta +0,036
[+0,008 a +0,067] no melhor braço, com **perda de especificidade distinguível de zero nos três
braços**, entre −0,037 e −0,050. A ampliação do contexto, ao contrário, preserva magnitude e
direção do efeito, com ganho de kappa entre +0,062 e +0,069 e de especificidade entre +0,081 e
+0,095, conforme o braço.

A explicação é atribuível ao objeto que cada modificação aprende. A matriz de transição do
modelo de Markov é estimada sobre a estrutura temporal de sono e vigília da coorte de
desenvolvimento e, por isso, incorpora a prevalência dessa coorte; transposta para população
com prevalência substancialmente distinta — 0,699 contra 0,895 —, a mesma matriz passa a
penalizar indevidamente as transições para vigília, o que se manifesta precisamente como perda
de especificidade. A janela de contexto ampliada, por sua vez, não codifica prevalência
alguma: ela altera apenas a escala temporal sobre a qual as características são computadas, e
essa escala é propriedade do fenômeno fisiológico, não da coorte.

Deriva-se daí a conclusão metodológica: **procedimentos de seleção de modelo apoiados
exclusivamente em validação cruzada interna são insuficientes neste domínio**. Neste trabalho,
especificamente, a validação interna teria selecionado a modificação cujo ganho não se
reproduz fora da coorte de origem, e **apenas a validação externa permitiu distinguir o ganho
atribuível ao método do ganho atribuível à coorte**. Essa conclusão é independente do
desempenho absoluto do dispositivo: vale qualquer que seja o valor de kappa obtido.

**Uma única coorte externa.** A validação externa apoiou-se em uma coorte independente apenas.
Estava prevista a utilização de uma segunda base, com acelerometria de punho obtida por
dispositivo de consumo e rotulagem polissonográfica, o que permitiria distinguir o que, na
degradação observada, é atribuível à troca de coorte em geral e o que é atribuível às
particularidades daquela coorte específica. Essa segunda validação **não foi executada**, por
indisponibilidade de acesso ao repositório que hospeda a base no ambiente de execução
empregado; não há, portanto, resultado desfavorável a relatar, e sim procedimento não
realizado. Com uma única coorte externa, a magnitude da degradação relatada deve ser lida como
estimativa pontual, e não como medida da variabilidade esperada entre coortes.

### Y.7 Efeito da lateralidade do sensor

A coorte externa dispõe de registros simultâneos dos dois punhos do mesmo participante, o que
permite isolar o efeito do lado do corpo sobre o desempenho. O censo é de 27 participantes com
registro do punho esquerdo, 26 com registro do punho direito e 26 com ambos — um participante
não possui registro do punho direito, razão pela qual a comparação pareada fecha em 26.

A comparação foi conduzida **intraparticipante**, nos 26 com registro bilateral: cada
participante é seu próprio controle, uma vez que a noite, a rotulagem polissonográfica e o
modelo são os mesmos, variando apenas o lado em que o acelerômetro foi acoplado. Essa
formulação remove da conta a variância entre participantes, que é a maior fonte de ruído nesta
medição — desvio-padrão de aproximadamente 0,2 em kappa.

Na configuração de melhor desempenho, nos 26 participantes com registro bilateral:

| Métrica | Esquerdo | Direito | Δ (esquerdo − direito) |
|---|---:|---:|---|
| Kappa | 0,335 | 0,326 | +0,009 [−0,014 a +0,031] |
| Especificidade | 0,510 | 0,519 | −0,009 [−0,038 a +0,017] |

Nas **vinte e quatro comparações** realizadas — três braços de treino, quatro configurações e
duas métricas —, **todos os intervalos de confiança de 95% contiveram o valor nulo**, e a
maior diferença absoluta observada foi de 0,027 em kappa. O lado do corpo, portanto, não
produziu efeito distinguível de zero em nenhuma das configurações avaliadas.

Esse resultado é interpretado como evidência favorável às decisões de representação adotadas
na seção de extração de características: o conjunto de atributos foi deliberadamente
construído com grandezas invariantes a rotação — inclinação relativa à gravidade de referência
da própria gravação e norma euclidiana da componente dinâmica, em substituição a atributos
dependentes de eixo —, e a insensibilidade ao lado do corpo é consequência previsível dessa
invariância. Trata-se de verificação relevante para este trabalho em particular, no qual o
sensor é alojado em um travesseiro e sua orientação é, por natureza, arbitrária e variável ao
longo da noite.

Registra-se que **a ausência de efeito detectável não equivale à demonstração de ausência de
efeito**: com 26 participantes, efeitos de magnitude inferior a aproximadamente 0,03 em kappa
não seriam distinguíveis do ruído amostral pelo delineamento empregado.

Registra-se ainda, por rigor, que as 53 gravações **não** foram tratadas como 53 observações
independentes. Os dois punhos de um mesmo participante correspondem à mesma noite, ao mesmo
sono e à mesma pontuação polissonográfica, medidos de dois lugares; a unidade de agrupamento
é o participante. O empilhamento das 52 gravações pareadas como observações independentes
estreitaria o intervalo de confiança de kappa em aproximadamente 30% — de 0,163 de largura, na
estimativa com o participante como unidade, para 0,114 — sem que qualquer evidência nova
tivesse entrado na conta.

### Y.8 Síntese dos resultados

Reunindo o que foi medido:

1. Um classificador que ignora o sensor alcança acurácia de 0,703 [0,616 a 0,776] e de 0,895
   [0,877 a 0,912] nas duas bases empregadas, com kappa nulo em ambas. A acurácia não é
   métrica informativa neste domínio, e a identidade derivada em Y.1.3 mostra que a
   constatação se estende a resultados publicados na literatura.
2. Os algoritmos clássicos de actigrafia, aplicados a um substituto de contagem sem calibração
   de escala, degeneram exatamente para esse classificador trivial — evidência de que
   contagens proprietárias não se reproduzem a partir de aceleração bruta.
3. O custo de mover o sensor do punho para a cabeça é de 0,050 em kappa, com a qualidade de
   aquisição controlada, e é menor que o custo de degradar a grade de aquisição, de 0,071.
4. A transferência entre posições é assimétrica: do punho atravessa, da cabeça colapsa. O
   colapso decompõe-se em uma componente de escala, responsável por 71% a 78% da lacuna e
   recuperável sem rótulo do destino, e uma componente residual da ordem de 0,19 a 0,23 em
   kappa, atribuível a diferença genuína entre os domínios.
5. Entre as modificações avaliadas, a ampliação da janela de contexto para aproximadamente
   onze minutos é a única que melhora kappa e especificidade simultaneamente, e é a única cujo
   ganho se reproduz em coorte independente.
6. O desempenho em coorte independente é kappa de 0,334 [0,254 a 0,416] e especificidade de
   0,507 [0,442 a 0,576], acima do classificador trivial da própria coorte e substancialmente
   inferior ao desempenho interno. É esta a estimativa que se adota como defensável.
7. O lado do corpo em que o sensor é acoplado não produziu efeito distinguível de zero em
   nenhuma das vinte e quatro comparações realizadas.

O que permanece **não medido**, e é declarado como tal: o comportamento do dispositivo
desenvolvido neste trabalho em placa, uma vez que a validação em hardware depende de etapa não
concluída; o custo do acoplamento mecânico através de um travesseiro, distinto do custo da
posição anatômica medido em Y.3; a segunda coorte externa prevista; e o teto de concordância
entre pontuadores humanos da base de desenvolvimento, que forneceria a referência superior
contra a qual os decréscimos de kappa deveriam ser lidos. Nenhum desses procedimentos foi
executado com resultado desfavorável — nenhum foi executado.

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Procedência de cada número

Notas para você, não para o texto. Cada valor citado acima está abaixo com o arquivo JSON, a
chave e o comando que o reproduz. Todos os arquivos estão versionados em
`ml/experimentos/saida/`. Os comandos de conferência **não reprocessam dado** — leem o JSON e
recalculam apenas as comparações pareadas:

```bash
cd ml
pip install -r requirements.txt
python -m experimentos.ml03b_otimizacoes    --item resumo    # Y.5 (interno, N=92)
python -m experimentos.ml04_validacao_externa --comparar     # Y.6 (externo, n=27)
python -m experimentos.ml04_validacao_externa --lados        # Y.7 (lado, n=26)
```

> ⚠️ **O `--lados` regrava o JSON.** Ele sobrescreve
> `ml04b_efeito_do_lado_aec203907e6f.json`, e a **única** diferença em relação à versão
> commitada é o campo `utc`. Isso foi verificado por `git diff` nesta sessão: 1 linha alterada,
> em 125 KB de números. É a evidência mais direta de reprodutibilidade que o repositório tem —
> mas se você rodar e não quiser o ruído no `git status`, restaure só aquele campo (o mount
> não permite `git checkout`, que tenta remover o arquivo).

### Y.1 — classificadores de referência

| Número no texto | Arquivo | Chave |
|---|---|---|
| trivial no Newcastle: ac 0,703 [0,616 a 0,776], κ 0,000, espec. 0,000 | `ml04_validacao_externa_aec203907e6f_esquerdo.json` | `trivial_no_newcastle.media/.ic95_baixo/.ic95_alto` |
| trivial no Wearanize+: ac 0,895 [0,877 a 0,912] | `ml03_transferencia_aec203907e6f_20260915T020658Z.json` | `baselines_por_braco.cabeca.trivial` (idêntico nos três braços) |
| degeneração com escala arbitrária: 0,697 / 1,000 / 0,000 / 0,000 | `ml02_newcastle_aec203907e6f_20260914T052628Z.json` | `resultados.1a_cole_kripke_escala_arbitraria`, `.1b_sadeh_escala_arbitraria` — **valores idênticos, bit a bit, a `.0_sempre_dormindo`** |
| identidade `p = (ac − espec)/(sens − espec)`; Li 0,878; Walch 0,910 | *derivação nossa* | entradas em `docs/ML-DATASETS-E-PLANO.md` §0.1; a conta está no §0.2 e no `ml/README.md` |

**Sobre a identidade.** Confira você mesmo antes de colar: Li — (0,873 − 0,331)/(0,948 −
0,331) = 0,8784. Walch — (0,900 − 0,596)/(0,930 − 0,596) = 0,9102. **Marcado como derivação
nossa no texto, e precisa continuar marcado** — é o tipo de conta que a banca pode querer
refazer, e atribuí-la aos autores dos artigos seria atribuir-lhes conclusão que eles não
tiram.

**Sobre a degeneração.** O texto afirma que os valores são *exatamente* os do trivial, não
próximos. Isso é verificável: nos três JSONs de `ml02_*` as três chaves têm os mesmos `vp`,
`vn`, `fp`, `fn`. É uma afirmação forte e ela se sustenta — mas note que `f1_vigilia` sai
`NaN` nessas linhas (divisão por zero, nenhuma época predita como vigília), e **`NaN` em JSON
não é JSON válido em sentido estrito**. Se algum dia esses arquivos passarem por um parser
mais rigoroso que o do Python, é aí que vai quebrar.

### Y.2 — Newcastle

| Número no texto | Arquivo | Chave |
|---|---|---|
| 27 participantes, 59 825 épocas, prevalência 0,697 | `ml02_newcastle_aec203907e6f_20260914T052628Z.json` | `n_sujeitos`, `n_epocas`, `prevalencia_sono` |
| toda a tabela de Y.2 (7 linhas × 4 métricas) | idem | `resultados.*.{acuracia,sensibilidade,especificidade,kappa}` |

⚠️ **Duas coisas a saber antes de colar a tabela.**

**1. As 59 825 épocas são 53 gravações, não 27.** `carregar_newcastle()` sem filtro carrega
todos os `.bin`, isto é, os dois punhos de quem tem os dois. A conta fecha exatamente:
30 440 (esquerdo, 27) + 29 385 (direito, 26) = 59 825, e esses dois números estão em
`ml04_validacao_externa_*` e no `--lados`. **Não há vazamento** — o LOSO agrupa por
participante, então os dois punhos de alguém caem sempre do mesmo lado da partição. Mas a
prevalência de 0,697 é sobre as 53 gravações, enquanto a de 0,699 citada em Y.6 é sobre as 27
do punho esquerdo. Os dois números estão certos e **não são o mesmo número**. O texto declara
isso no último parágrafo de Y.2; se você encurtar aquele parágrafo, o `n` da tabela fica
ambíguo.

**2. Y.2 é a única seção sem intervalo de confiança.** O `ml02_baselines.py` agrega sobre o
conjunto das épocas e não roda bootstrap; a agregação por participante entrou a partir do
`ML-03`. O texto declara a ausência em vez de a esconder. **Não invente intervalo para essa
tabela** — se a banca pedir, o caminho é rodar o `ml02` com agregação por sujeito, que não
existe hoje.

### Y.3 — matriz de transferência

Tudo em `ml03_transferencia_aec203907e6f_20260915T020658Z.json`:

| Número no texto | Chave |
|---|---|
| N = 92, prevalência 0,895 | `n_sujeitos`, `prevalencia_sono.cabeca` (0,89538; o trivial agregado por sujeito dá 0,89545 — os dois arredondam para 0,895) |
| as 9 células de κ com IC | `matriz.<treino>-><teste>.media.kappa`, `.ic95_baixo.kappa`, `.ic95_alto.kappa` |
| Sadeh calibrado, 0,435 a 0,462 conforme o braço | `baselines_por_braco.<braço>.sadeh_calibrado_loso` (cabeça 0,4461; cabeça-E4 0,4346; punho 0,4621) |
| quedas de 83,3% e 88,5% do valor na diagonal | 0,3318/0,3983 e 0,3524/0,3983, da mesma matriz |
| **custo de sensor +0,071** | `matriz.cabeca->cabeca` (0,3983) − `matriz.cabeca_e4->cabeca_e4` (0,3274) = **0,0709** |
| **custo de posição +0,050** | `matriz.pulso->pulso` (0,3772) − `matriz.cabeca_e4->cabeca_e4` (0,3274) = **0,0498** |
| 256 Hz / 12 bits e 32 Hz / 8 bits; degradação para a grade do E4 | *docstring* de `experimentos/ml03_transferencia.py`, e `ml/README.md` §4 |

⚠️ **O `ml03b_ablacao_*.json` tem uma chave `referencia` com a mesma matriz, e os valores
diferem na terceira casa** — 0,4012 / 0,3313 / 0,3770 contra 0,3983 / 0,3274 / 0,3772. Os
dois experimentos são rodadas independentes do mesmo desenho. **O texto de Y.3 usa o
`ml03_transferencia`, e é o que faz os custos fecharem em 0,071 e 0,050 exatos.** Se você
recalcular a partir da `referencia` do ablação, sai 0,070 e 0,046 — perto, mas não o que está
escrito. Cite um arquivo só, por seção, e declare qual.

### Y.4 — assimetria e ablação

Tudo em `ml03b_ablacao_aec203907e6f_20260915T223235Z.json`. Todas as frações abaixo são
calculadas contra a diagonal de origem `referencia.cabeca->cabeca` = 0,4012:

| Número no texto | Chave / conta |
|---|---|
| colapso: 0,067 e 0,046; quedas de 0,332 e 0,352 (85% e 88%) | `ml03_transferencia` → `matriz.cabeca->cabeca_e4` (0,0665) e `.cabeca->pulso` (0,0459), contra a diagonal 0,3983 |
| reajuste do normalizador recupera cabeça → punho a 0,322, **77,6%** | `item1_rescaler_teste.cabeca->pulso` (0,3219); (0,3219 − 0,0467)/(0,4012 − 0,0467) |
| … e cabeça → cabeça-E4 a 0,183, **34,5%** | `item1_rescaler_teste.cabeca->cabeca_e4` (0,1827); (0,1827 − 0,0675)/(0,4012 − 0,0675). No texto o ponto de partida aparece como 0,067 [0,054 a 0,083], que é o arredondamento de 0,06747 |
| normalização por participante: 0,298 (**71,0%**) e 0,206 (**41,5%**) | `item5_normalizacao_por_sujeito.cabeca->pulso` (0,2983) e `.cabeca->cabeca_e4` (0,2061) |
| floresta aleatória: 0,488 na diagonal; 0,257 e 0,302; **Δκ 0,230 e 0,186** | `item3_random_forest.cabeca->cabeca` (0,4875), `.cabeca->pulso` (0,2574), `.cabeca->cabeca_e4` (0,3017) |
| logística sem normalizador continua colapsada: 0,072 no punho | `item2_sem_scaler.cabeca->pulso` (0,0720) |
| divergência multivariada 1,353 / 1,066 / 0,668 | `item4_divergencia.distancia_multivariada` |
| `zcr` domina: 1,860 / 1,108 / 0,483 | `item4_divergencia.por_feature.<par>.zcr` |

🔧 **Três ressalvas, e a primeira é a que mais importa para a banca.**

**1. O "70% a 80%" é a faixa de um par de posições, não da matriz.** Os 71,0% e 77,6% são
ambos da transferência **cabeça → punho**. Na transferência cabeça → cabeça-E4 a recuperação
é de 34,5% e 41,5% — metade. O texto de Y.4 diz isso explicitamente ("cerca de três quartos
[…] e cerca de dois quintos"), e **aquela frase não é enfeite**: sem ela, a faixa "71% a 78%"
parece valer para a matriz inteira, e não vale. Se a banca perguntar "recupera 78% de quê?",
a resposta tem de estar no texto, não na sua cabeça.

**2. As frações são contra a diagonal de origem, e essa é uma escolha.** Poder-se-ia medir a
recuperação contra a diagonal de **destino** — o teto que um modelo treinado no destino
alcança —, e daí sairia 83,3% para cabeça → punho, não 77,6%. As duas contas são defensáveis;
a adotada é mais conservadora, porque a diagonal de origem é maior que a de destino neste par.
**Declare a escolha se alguém perguntar por que 77,6% e não 83,3%.**

**3. A floresta aleatória não é "o modelo sem normalizador".** Ela é *insensível a
deslocamento monotônico de escala* por construção — o corte é um limiar por característica.
Retirar o `StandardScaler` da logística **não** produz o mesmo efeito, e o JSON prova
(`item2_sem_scaler` continua em 0,072). O texto de Y.4 declara essa distinção, e ela é o que
impede a leitura errada de que "basta tirar o normalizador". Δκ de 0,19–0,23 num modelo que
ignora escala é o argumento de que existe componente residual; a logística sem scaler **não**
é argumento de nada, e está no texto só para bloquear a interpretação preguiçosa.

Registre também que `parcial: true` está gravado no JSON do ablação. Ele se refere à execução
retomável por dobra (`experimentos/_retomada.py`) e **não** a N reduzido: as cinco chaves de
item têm `n_sujeitos: 92` e `n_valido: 92` nas três métricas. Se a banca notar a flag, é isso
que se responde.

### Y.5 — otimizações (validação interna, N = 92)

Tudo em `ml03b_otimizacoes_aec203907e6f_92suj.json`, reproduzido por
`python -m experimentos.ml03b_otimizacoes --item resumo`:

| Item no JSON | O que é no texto | κ (cabeça) | Δκ pareado |
|---|---|---|---|
| `itens.baseline` | configuração de base | 0,383 [0,348 a 0,418] | — |
| `itens.6` | retirada da ponderação de classes | 0,417 | +0,034 [−0,005 a +0,073] · Δespec. **−0,345** |
| `itens.7` | limiar de Youden | 0,333 | −0,050 [−0,060 a −0,040] · Δespec. +0,068 |
| `itens.8` | mediana móvel de 5 | 0,399 | +0,016 [+0,012 a +0,020] |
| `itens.8b` | **modelo oculto de Markov** | 0,507 [0,463 a 0,548] | **+0,123 [+0,105 a +0,142]** |
| `itens.9` | **contexto ±11** | 0,458 [0,418 a 0,499] | **+0,075 [+0,060 a +0,090]** · Δespec. **+0,101 [+0,083 a +0,118]** |

Os Δ **não estão no JSON** — o JSON guarda `por_sujeito` por item, e o `--resumo` calcula o
bootstrap pareado da diferença na hora. Reproduzido nesta sessão, valor a valor, contra o que
está escrito no texto.

⚠️ **A tabela de Y.5 é do braço de cabeça; a de Y.6 é do braço de punho.** Não são
comparáveis linha a linha, e o κ interno de 0,414 citado em Y.6 é `itens.9.pulso`, não
`itens.9.cabeca` (0,458). Se você fundir as duas tabelas para economizar espaço, este é o erro
que vai entrar.

⚠️ **O item 6 é contrafactual e está escrito como tal.** `class_weight="balanced"` **está** na
configuração de base; o item 6 mede o que acontece ao retirá-lo. Ler a linha como "uma
melhoria que não deu certo" inverte o sentido: ela mede o que a base já compra. Mesma coisa
para o item 7.

⚠️ **O item 8 "não sai do ruído" pelo critério conservador, mas o pareado o dá como ganho
real** (+0,016 [+0,012 a +0,020], IC não contém zero). O texto diz "produz ganho de +0,016",
sem chamá-lo de nulo — de propósito. O `ml/README.md` o descreve como "não sai do ruído", o
que vem do critério de IC disjuntos. **Os dois documentos não se contradizem, mas usam
critérios diferentes**, e como o texto do TCC declara em Y.5 que o veredito é o pareado, é a
redação daqui que vale. Se você copiar a frase do README para o TCC, cria inconsistência
interna.

### Y.6 — validação externa (n = 27)

Tudo em `ml04_validacao_externa_aec203907e6f_esquerdo.json`, reproduzido por
`python -m experimentos.ml04_validacao_externa --comparar`:

| Número no texto | Chave |
|---|---|
| treino 92, teste 27, sem reajuste | `treino.n_sujeitos`, `teste.n_sujeitos`, `treino.reajuste_no_teste: "nenhum"` |
| 30 440 épocas, prevalência 0,699, punho esquerdo | `teste.n_epocas`, `teste.prevalencia_sono`, `teste.punho` |
| toda a tabela de κ e especificidade externa | `resultados.<braço>.<config>.media/.ic95_*` |
| **κ 0,334 [0,254 a 0,416] e espec. 0,507 [0,442 a 0,576]** | `resultados.pulso.item9_ctx11` |
| **κ interno 0,414 [0,373 a 0,453] e espec. 0,802 [0,768 a 0,831]** | `ml03b_otimizacoes_*.json` → `itens.9.pulso` |
| os 6 Δ pareados entre configurações | saída do `--comparar` (calculada do `por_sujeito`, não gravada) |

**O par 0,802 → 0,507 é o número honesto do trabalho, e vem de dois arquivos diferentes.**
Interno do `ml03b_otimizacoes`, externo do `ml04`. Já está assim no `LIMITACOES-TCC.md` §X.4,
e as duas seções precisam continuar dizendo o mesmo número — se uma mudar, a outra muda.

**Sobre a incomparabilidade dos κ.** Prevalência 0,699 externa contra 0,896 interna, ambas
verificáveis nos JSONs (`teste.prevalencia_sono` e `prevalencia_sono.cabeca`). O
`LIMITACOES-TCC.md` §X.4 diz "aproximadamente 0,85" para a interna; o valor medido é 0,8954.
**Vale alinhar os dois documentos** — 0,85 não está errado como ordem de grandeza, mas 0,895 é
o que está no JSON, e ter dois números para a mesma quantidade em duas seções do mesmo TCC é o
tipo de coisa que a banca encontra.

**Sobre o Walch.** Segunda coorte externa prevista, PhysioNet `sleep-accel`, 31 participantes.
**Não foi executada:** falta o dado *e* o carregador (`ml/src/carregar/walch.py` não existe) —
o repositório não é alcançável do ambiente de execução. O texto de Y.6 declara "não foi
executada", e essa redação é deliberada. Não a troque por nada que sugira tentativa
malsucedida.

### Y.7 — lateralidade (n = 26 pareado)

Tudo em `ml04b_efeito_do_lado_aec203907e6f.json`, reproduzido por
`python -m experimentos.ml04_validacao_externa --lados`:

| Número no texto | Origem |
|---|---|
| censo 27 / 26 / 26; `ncl010` sem punho direito | saída do `--lados`, primeiras linhas |
| κ esq. 0,335, dir. 0,326, Δ +0,009 [−0,014 a +0,031] | `resultados.pulso.item9_ctx11.c_efeito_do_lado_intra_sujeito.kappa` → `media_a`, `media_b`, `delta_medio`, `ic95_*` |
| espec. esq. 0,510, dir. 0,519, Δ −0,009 [−0,038 a +0,017] | idem, `.especificidade` |
| 24 comparações, todos os IC contêm zero, máx. 0,027 em κ | 3 braços × 4 configs × 2 métricas; varredura feita nesta sessão: `significativo: false` em todas as 24. A maior em κ é `cabeca.item9b_ctx11_hmm` (−0,0267 → 0,027) |
| IC de 0,163 para 0,114 de largura (~30% mais estreito) | 0,163 = largura de `pulso.item9_ctx11.a_esquerdo_isolado` em κ (0,41642 − 0,25379); 0,114 = largura de `d_INCORRETO_empilhado.kappa` (0,38614 − 0,27246) |

⚠️ **`d_INCORRETO_empilhado` existe de propósito e não vai para tabela.** É o que sairia se as
52 gravações pareadas fossem empilhadas como independentes. Está no JSON para documentar o
tamanho do viés (próximo do fator 1/√2 esperado de dobrar o N artificialmente). O texto cita a
largura do intervalo, nunca o valor do Δ. **Se alguém copiar esse Δ para uma tabela, o
resultado fica errado e parece mais forte.**

⚠️ **O `LIMITACOES-TCC.md` §X.3 traz este mesmo Δκ como `+0,009 (IC 95%: −0,015 a +0,031)`.** O
valor no JSON é −0,014499, que arredonda para **−0,014**, e é o que está escrito aqui. Não é erro
de medição, é arredondamento discordante de um número na terceira casa — mas são dois números
diferentes para a mesma quantidade em duas seções do mesmo TCC. **Alinhe os dois antes de
entregar**, e o valor certo é −0,014.

⚠️ **Y.7 diz 0,335 e 0,510; Y.6 diz 0,334 e 0,507.** É o mesmo braço e a mesma configuração, e
os valores diferem porque Y.6 é sobre os **27** participantes com punho esquerdo e Y.7 é sobre
os **26** que têm os dois. A diferença é um participante. **Os dois estão certos** — mas se
você colar as duas seções sem os `n`, vira erro aparente de transcrição.

---

## Checklist antes de colar no documento

- [ ] Ajustar `Y` para o número do capítulo, e conferir as referências internas a `Y.1`–`Y.8`.
- [ ] Substituir "a seção de metodologia", "a seção de limitações" e "a seção de extração de
      características" pelos números de seção reais do TCC.
- [ ] **Alinhar com o `LIMITACOES-TCC.md`.** As seções X.3 (lateralidade) e X.4 (degradação
      entre coortes, ganho que atravessa coorte) **repetem números deste capítulo**. Se um
      número mudar aqui, muda lá. Os pontos de contato são: κ 0,414 → 0,334 · espec. 0,802 →
      0,507 · Δκ HMM interno +0,123 e externo +0,036 · Δκ janela externo +0,069 · Δespec.
      janela externo +0,095 · lateralidade +0,009 e −0,009 · prevalência 0,699 e 0,895. Há
      **duas divergências já identificadas** entre os dois documentos, ambas descritas na nota
      de procedência: o IC do Δκ de lateralidade (−0,014 aqui, −0,015 lá) e a prevalência
      interna (0,895 aqui, "aproximadamente 0,85" lá).
- [ ] **Decidir se Y.6 e X.4 coexistem, ou se X.4 passa a referenciar Y.6.** Hoje o mesmo
      argumento metodológico está redigido nos dois — aqui como resultado, lá como limitação.
      Dizer duas vezes não é erro, mas repetir com redação levemente diferente é pior que
      repetir igual. **Recomendação:** manter o argumento completo em Y.6, e em X.4 deixar só
      a limitação (uma coorte só) com remissão a Y.6.
- [ ] Converter as citações de Y.1.3 (LI; HALAKI; CHOW; WALCH et al.) para o padrão do TCC, se
      não for autor-data. Autoria, ano, veículo e DOI já conferidos — ver `LIMITACOES-TCC.md`.
- [ ] **Ler os dois artigos de Y.1.3 antes de citá-los.** Os três valores de cada um entram na
      derivação; referência conferida não é artigo lido, e a derivação depende de os três
      números serem da mesma população e do mesmo protocolo. **Confirme isso no texto dos
      artigos.**
- [ ] Verificar se a seção de metodologia já define kappa de Cohen, bootstrap pareado e
      *leave-one-subject-out*. O capítulo os usa sem redefinir.
- [ ] Conferir se o resumo e as considerações finais citam o número **externo** (0,334 / 0,507)
      e não o interno. Este é o erro mais provável de todos, porque o número interno é melhor.
- [ ] Decidir se as sete tabelas ficam todas no corpo ou se as de Y.5 vão para apêndice. São
      muitas tabelas seguidas; a de Y.3 (matriz 3×3) e a de Y.6 (externa) são as que não podem
      sair do corpo.

## O que este capítulo deliberadamente não faz

- **Não reporta dado sintético.** O `ml02_sintetico_*.json` existe e tem números bons
  (κ 0,636, espec. 0,798), e é **gerador de teste de pipeline**, não medição. Nada dele entra
  no TCC. Se entrar em alguma versão, tem de vir rotulado como sintético na mesma frase.
- **Não reporta os pilotos do Wearanize+.** `ml02_wearanize_cabeca_*` (N = 10) e
  `ml02_wearanize_pulso_*` (N = 7) foram execuções de verificação antes do N = 92. Os
  resultados definitivos da mesma base são os de Y.3 a Y.5, com N = 92 e IC. Citar os pilotos
  ao lado só criaria dois números para a mesma coisa.
- **Não apresenta o teto de concordância entre pontuadores.** A base tem dois pontuadores
  humanos em 96 participantes, e esse teto seria a referência superior natural para ler os Δκ.
  **Não foi medido** — e é a lacuna mais barata de fechar que sobrou neste capítulo: o dado
  está em disco, o carregador aceita `pontuador=2`, e são duas chamadas de `carregar()` mais
  um kappa. Se sobrar um dia antes da entrega, é aqui que ele rende mais.
- **Não afirma nada sobre o protótipo em placa.** Nenhum número deste capítulo foi medido no
  dispositivo. Todo ele é sobre bases públicas de acelerometria com rotulagem
  polissonográfica, e a seção Y.8 declara isso.
