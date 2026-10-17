# Diário de engenharia — Smart Dormio

> **Reconstruído retroativamente em 2026-09-30**, a partir do histórico do git, dos
> documentos em `docs/`, dos JSONs em `ml/experimentos/saida/`, dos scripts de conferência e
> das suítes de teste. Daqui para frente é registro corrente: toda teoria, teste, resultado e
> adaptação entra aqui no dia em que acontece.

Este arquivo existe para virar o **capítulo de desenvolvimento** do TCC. Por isso cada entrada
traz número e procedência: o que está escrito aqui ou sai de um JSON versionado, ou de um teste
que roda, ou de uma linha de código que dá para abrir. Onde a fonte não bastou, a entrada está
marcada **PARCIAL** e diz o que falta.

## Como ler

Cada entrada tem sete campos fixos, sempre na mesma ordem:

| Campo | O que registra |
|---|---|
| **O problema, como foi entendido no início** | O enunciado de partida — inclusive quando ele estava errado |
| **Hipótese de trabalho** | O que se esperava que fosse verdade, antes de medir |
| **O que foi testado, e como** | O procedimento, com o comando ou o arquivo |
| **Resultado medido** | O número, com a unidade e o N |
| **Adaptação** | O que mudou quando o resultado contrariou a hipótese — vazio quando não contrariou |
| **Risco em aberto** | O que continua não resolvido depois da entrada |
| **Procedência** | Onde reconferir |

**O valor está sobretudo no que deu errado.** Uma boa parte das entradas abaixo é de premissa
que caiu ao ser verificada — e várias delas eram premissas que *já estavam escritas na
documentação do projeto como se fossem fato*. Estão registradas com o mesmo cuidado que os
acertos, porque é delas que sai o argumento metodológico do trabalho.

## Sobre as datas

As datas vêm de três fontes, em ordem de confiança:

1. **O que o próprio documento afirma** (`DATA-07c ✅ (30/09)`, "medição de 2026-09-21") — é o
   que se usa quando existe.
2. **O carimbo dos JSONs de experimento** (`ml03b_ablacao_..._20260915T223235Z.json`) — data de
   execução, não de redação.
3. **O reflog** (`.git/logs/HEAD`) — data em que o commit entrou *neste clone*. Vários commits
   entraram em lote, então a data do git às vezes é posterior ao trabalho que ela registra.

Onde as três divergem, a entrada diz qual foi usada.

---

# 2026-04-29 — abertura do repositório

**PARCIAL.** O clone inicial está no reflog (`a5a3307`, 2026-04-29), mas o trabalho anterior a
ele não está no repositório. Falta: o levantamento do problema, a escolha do ESP32 + MPU6050 e
a decisão de usar travesseiro em vez de punho — todos anteriores ao versionamento. Reconstruir
isso depende de material fora do git.

---

# 2026-05-31 — `DEC-01` / `FUND-01`: escolher a base de dados antes de ter dado

**O problema, como foi entendido no início.** Um trabalho de detecção de sono precisa de
rótulo de referência, e o projeto não tinha nenhum. A pergunta de partida era qual base pública
usar.

**Hipótese de trabalho.** Haveria uma base de acelerometria com polissonografia pontuada e
acesso aberto, e o acesso seria a parte fácil.

**O que foi testado, e como.** Levantamento das bases públicas com PSG e acelerometria
simultâneas, registrado em `docs/DATASET.md` (não versionado — material interno) e ampliado
depois em `docs/ML-DATASETS-E-PLANO.md`.

**Resultado medido.** As bases com a combinação exigida ou pedem *Data Use Agreement*, ou não
têm o acelerômetro na posição de interesse. O acesso passou a ser risco de projeto, não
detalhe.

**Adaptação.** O `DEC-01` ficou registrado como dependência de terceiro (`SCI-01`), e o
trabalho seguiu por caminhos que não dependiam dele.

**Risco em aberto.** Nesta data, o caminho crítico do trabalho dependia de uma assinatura de
terceiro. Só foi removido em 22/09 (entrada própria).

**Procedência.** `docs/ML-DATASETS-E-PLANO.md`; commits `0785d40` e `4fb38b6`.

---

# 2026-06-03 — `FIX-02`: o `POST` que respondia 201 sem gravar

**O problema, como foi entendido no início.** A ingestão respondia `201 Created` e o dashboard
continuava vazio.

**Hipótese de trabalho.** Problema de leitura — o dado estaria gravado e a consulta não o
trazia.

**O que foi testado, e como.** Inspeção do caminho de escrita no backend.

**Resultado medido.** A resposta `201` era emitida antes de o resultado da escrita ser
verificado: a falha do Supabase não virava erro HTTP. O dispositivo recebia confirmação de um
dado que não existia.

**Adaptação.** A resposta passou a depender do resultado da escrita. É a primeira ocorrência
registrada do padrão que se repete em todo o projeto — *confirmação emitida antes da
verificação* —, e que reaparece no `UI-10` (exclusão de conta) e no `APP-10` (estado de envio).

**Risco em aberto.** Nenhum específico; o padrão geral continua sendo o modo de falha mais
frequente do projeto.

**Procedência.** Reflog, merge `bugfix/FIX-02-post-201-falso` (2026-06-03).

---

# 2026-08-20 — `DATA-02`: o critério de movimento era assimétrico

**O problema, como foi entendido no início.** O firmware classificava movimento por limiar
sobre a magnitude bruta da aceleração:

```cpp
status = (total > 11.0 || total < 8.0) ? "Movimento Detectado!" : "Dormindo";
```

O enunciado de partida era *ajustar os dois limites*.

**Hipótese de trabalho.** Os dois limites representavam a mesma sensibilidade em torno de
1 g — um acima, um abaixo.

**O que foi testado, e como.** Aritmética sobre os próprios números do código, contra
`g = 9,81 m/s²`.

**Resultado medido.** O limite superior dispara a `11,0 − 9,81 = 1,19 m/s²` de desvio. O
inferior só dispara a `9,81 − 8,0 = 1,81 m/s²`. **A regra era 52% menos sensível para baixo do
que para cima** — e nada no código dizia que isso era intencional, porque não era.

**Adaptação.** O critério passou a ser simétrico, `|‖a‖ − 9,81| > 1,2 m/s²`, preservando a
sensibilidade do lado que já era o mais sensível. O valor foi declarado **provisório** no
contrato de dados desde então.

**Risco em aberto.** O 1,2 herdou a autoridade de ter sido escrito num contrato, e a nota de
"provisório" foi lida cada vez menos. A entrada de 2026-09-29 (`CALC-03`) mostra o que isso
custou.

**Procedência.** `docs/DATA-CONTRACT.md` §2.2 e "Histórico — a assimetria corrigida em 1.1.0";
merge `feature/DATA-02-criterio-movimento`.

---

# 2026-08-25 — `Etapa 0`: o sensor lido por contato de jumper

**O problema, como foi entendido no início.** O módulo MPU6050 veio com os pinos não soldados.
A pergunta era se dava para adiantar a caracterização com contato por jumper enquanto o ferro
de solda não aparecia.

**Hipótese de trabalho.** O contato seria pior, e produziria ruído maior — mas dado utilizável,
com margem declarada.

**O que foi testado, e como.** Leitura das seis poses de caracterização com o sketch de
`firmware/caracterizacao/`.

**Resultado medido.** Não foi ruído maior, foi leitura sem significado: registradores zerados,
`‖a‖ = 56,5 m/s²` **com a placa parada** (5,8 g em repouso), temperatura de `−11,6 °C`, e ruído
**30× o normal**. O viés de Z saiu `−1,06 m/s²` — **89% do limiar de movimento inteiro, só de
viés de um eixo**.

**Adaptação.** A caracterização foi invalidada, e a solda passou a ser declarada como
dependência que **trava as camadas L1 e L2 inteiras** — não como tarefa de conveniência.
Entrou também uma guarda de leitura zerada no sketch (`bugfix/CALC-02-guarda-de-leitura-zerada`,
2026-09-14), para que a próxima leitura ruim falhe em vez de virar número.

**Risco em aberto.** O viés de `−1,06 m/s²` é o número mais desconfortável do projeto: se ele
se confirmar com solda, um único eixo mal calibrado consome 89% do orçamento de detecção. O
`CAL-01` ainda não foi refeito, e o `CAL-02` obriga a refazê-lo de novo depois do `FW-06`
(entrada seguinte) — o número atual não transfere.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, `Etapa 0` e `CAL-01`; `firmware/caracterizacao/`.

---

# 2026-09-10 — `FW-06`: o filtro estava em 260 Hz, e isso mudou o ruído de base

**O problema, como foi entendido no início.** Escolher a largura de banda do filtro
passa-baixa do MPU6050. O sketch usava o padrão, 260 Hz.

**Hipótese de trabalho.** Banda mais larga custa mais ruído, e a escolha seria um compromisso
a arbitrar.

**O que foi testado, e como.** Cálculo sobre a densidade espectral do sensor, com
`σ = e_n·√B`, e depois transposto para `scripts/calculos_tcc.py`.

**Resultado medido.** O ruído cresce com `√B`: passar de 21 Hz para 260 Hz multiplica σ por
**3,52**, e o piso do ENMO médio é proporcional a σ, então o fator se transfere integralmente.
Na banda de 21 Hz, `σ = 1,833 mg`.

**Adaptação.** O filtro foi para 21 Hz. E uma consequência que não estava prevista: **o limiar
de movimento é definido sobre o ruído de base, e o ruído de base mudou** — o que invalidou a
caracterização de 25/08 duas vezes (contato ruim *e* banda diferente). Virou o item `CAL-02`.

**Risco em aberto.** 21 Hz implica amostragem mínima de 42 Hz por Nyquist, e o modo de baixo
consumo do acelerômetro vai só até 40 Hz a 110 µA. **A desigualdade é estrita:** a cadeia de
processamento obriga o modo normal, a 500 µA — fator **4,5×** na corrente do transdutor. É um
custo do teorema da amostragem, não uma escolha de implementação.

**Procedência.** `docs/CALCULOS-TCC.md` Z.1 e Z.2.2; `scripts/calculos_tcc.py`.

---

# 2026-09-14 — `ML-01`: as features herdadas não eram invariantes a rotação

**O problema, como foi entendido no início.** Escrever o conjunto de características por
época. O ponto de partida era o vocabulário clássico da actigrafia: `angulo_z` e a *signal
magnitude area* (SMA, norma L1).

**Hipótese de trabalho.** Features clássicas de actigrafia de punho servem para o travesseiro —
o que muda é a escala, não a definição.

**O que foi testado, e como.** Aplicação de rotação `R` arbitrária ao sinal e medição da
variação de cada feature. Testes em `ml/testes/` e na suíte do vetor dourado
(`test_sequencias_tambem_sao_invariantes_a_rotacao`).

**Resultado medido.** Num travesseiro a orientação é arbitrária **e muda durante a noite**, e
as duas features herdadas dependem dela: `angulo_z` depende de qual eixo é "z"; a norma L1 sobre
gravidade bruta **varia até 73% só por causa da montagem**, e mesmo restrita à componente
dinâmica variou ~6%.

**Adaptação.** `angulo_z` saiu; entraram `inclinacao_rel` (ângulo contra a gravidade de
referência *da própria gravação*) e `d_angulo` (reorientação entre épocas), ambos invariantes
por construção: `(Rĝ_a)·(Rĝ_b) = ĝ_a·ĝ_b`. A SMA L1 saiu; entrou `mag_din_media` (norma L2).
Um defeito residual foi corrigido no mesmo dia: `direcao_referencia` **também não era
invariante** na primeira escrita (commit `11eb4b7`).

**Risco em aberto.** `mag_din_media` **não pode ser citada como *signal magnitude area* no
TCC** — é outra norma, e chamar pelo nome clássico seria atribuir ao trabalho uma comparação
com a literatura que ele não faz. Registrado como advertência em `ml/README.md`.

**Procedência.** `ml/README.md` "Decisões técnicas" 1 e 2; `ml/src/features.py`; commits
`38ae2a5` e `11eb4b7`.

---

# 2026-09-14 — `DADOS-02`: as dez armadilhas de formato, e a que valia fator 4

**O problema, como foi entendido no início.** Escrever os carregadores das duas bases a partir
da documentação delas.

**Hipótese de trabalho.** A documentação do dataset descreve o dataset.

**O que foi testado, e como.** Auditoria dos **arquivos reais** — EDF, `channels.tsv`, `.bin` do
GENEActiv —, com um teste por armadilha em `ml/testes/test_wearanize.py`.

**Resultado medido.** Dez divergências entre o declarado e o gravado. As que mais custariam:

| # | O que a documentação diz | O que o arquivo tem | Se passar batido |
|:-:|---|---|---|
| 1 | `PSG_Manual_scor1` no `.tsv` | `PSG_Manual_Scor1` no EDF | Casamento sensível a maiúscula acha o acelerômetro e **perde o rótulo** — sintoma não é exceção, é **zero época** |
| 2 | Empatica em `g/16` (coleção restrita, v1.0) | **`g/64`** | **Fator 4 de erro** no braço "treina" do `ML-03`, silencioso |
| 4 | `scor2` para os 100 sujeitos | EDF só tem em **96** | O teto inter-avaliador é N=96, não 100 |
| 5 | — | nº de canais varia de **38 a 61** por sujeito | Indexar canal por posição fixa quebra |

**Adaptação.** Todo acesso passou a ser por nome, nunca por posição. O carregador **aborta** se
encontrar a declaração `g/16`, em vez de converter pelo fator que achar. E a regra de método
ficou escrita no backlog para o próximo carregador (`ML-06b`): *escreva contra a documentação,
mas não confie até rodar.*

**Risco em aberto.** O carregador do Walch et al. (`ML-06b`) será escrito contra documentação,
sem o arquivo em mãos — pelo mesmo caminho que produziu estas dez.

**Procedência.** `ml/README.md` §5; `ml/src/carregar/wearanize.py`; `ml/testes/test_wearanize.py`.

---

# 2026-09-14 — `ML-02`: o classificador trivial é competitivo, e κ mostra por quê

**O problema, como foi entendido no início.** Estabelecer *baselines* antes de treinar
qualquer modelo.

**Hipótese de trabalho.** Acurácia serviria como métrica de leitura, e os algoritmos clássicos
(Cole-Kripke, Sadeh) serviriam como piso de comparação.

**O que foi testado, e como.** Baselines em sintético, Wearanize+ (cabeça e pulso) e Newcastle,
incluindo o trivial "sempre dormindo". Além disso, a identidade
`acurácia = p·sensibilidade + (1−p)·especificidade` aplicada a dois trabalhos da literatura que
publicam as três grandezas.

**Resultado medido.** O trivial é **competitivo em acurácia** — porque a prevalência de sono
numa noite de PSG é alta — e tem **κ exatamente 0**. Aplicada à literatura, a identidade
recupera a acurácia que o trivial teria alcançado *naquele mesmo estudo*, e a diferença contra
a acurácia publicada é pequena em dois trabalhos.

**Adaptação.** Acurácia deixou de ser métrica de decisão; κ de Cohen passou a ser a métrica
primária em todo o trabalho. E Cole-Kripke/Sadeh **não puderam** ser usados como publicados:
exigem *activity counts* de Actiwatch, e não há função pública que converta aceleração em
counts. Entrou um substituto documentado (passa-banda 0,25–3 Hz, retificado, integrado).

**Risco em aberto.** O substituto **não é Cole-Kripke**. No texto tem de aparecer como
*"Cole-Kripke aplicado a um substituto de contagem"*, com a segunda diferença também declarada
(rodam em épocas de 30 s, não nos 60 s originais). É o tipo de atalho de redação que uma banca
cobra.

**Procedência.** `docs/RESULTADOS-TCC.md` §0 e a tabela da identidade;
`ml/experimentos/saida/ml02_*.json`; `ml/README.md` "Decisões técnicas" 3.

---

# 2026-09-14/15 — `ML-03`: a transferência entre posições é assimétrica

**O problema, como foi entendido no início.** Quanto se perde ao treinar numa posição de sensor
e aplicar em outra. É a pergunta original do trabalho: o travesseiro fica na cabeça, e a
literatura de actigrafia é de punho.

**Hipótese de trabalho.** A transferência seria **simétrica** e moderadamente ruim nas duas
direções — perda de informação por posição.

**O que foi testado, e como.** Matriz 3×3 de transferência (cabeça, cabeça degradada, pulso),
com **o mesmo N nas nove células**, N = 92, validação *leave-one-subject-out*.

**Resultado medido.** Fortemente assimétrica.

| Treino → teste | κ |
|---|---:|
| pulso → qualquer posição | ≈ 0,38 |
| cabeça → cabeça (diagonal de origem) | 0,398 – 0,401 |
| cabeça → pulso | **0,046** |
| cabeça → cabeça degradada (E4) | **0,067** |

Queda de 0,332 e 0,352 — **85% e 88%** da diagonal de origem.

**Adaptação.** A hipótese de simetria caiu, e o achado virou o resultado original do trabalho.
A pergunta seguinte deixou de ser "quanto se perde" e passou a ser "o que exatamente é perdido",
o que gerou o `ML-03b`.

**Risco em aberto.** A direção que interessa ao produto (treinar com dado de cabeça) é
justamente a que colapsa.

**Procedência.** `ml/experimentos/saida/ml03_transferencia_aec203907e6f_20260915T020658Z.json`;
`docs/RESULTADOS-TCC.md` §Y.3.

---

# 2026-09-15 — `ML-03b`: o colapso é escala, não informação — mas só num par de posições

**O problema, como foi entendido no início.** Entender o colapso de `cabeça → pulso`. Duas
hipóteses concorrentes: **H1**, a informação não existe no sinal de cabeça; **H2**, a informação
existe e a representação está deslocada.

**Hipótese de trabalho.** Se fosse H2 (escala), refazer o normalizador no domínio de destino
recuperaria boa parte do κ. Se fosse H1, nenhuma normalização recuperaria nada.

**O que foi testado, e como.** Cinco ablações sobre a mesma matriz, com intervalos de confiança
por *bootstrap*. A execução tem matriz de referência própria, que reproduz a do `ML-03` até a
terceira decimal (0,401 contra 0,398 na diagonal de cabeça), de modo a não misturar as rodadas.

**Resultado medido.**

| Ablação | cabeça → pulso | % da lacuna | cabeça → cabeça-E4 | % da lacuna |
|---|---:|---:|---:|---:|
| 1 — reajuste do normalizador no destino | 0,047 → **0,322** | **77,6%** | 0,067 → 0,183 | **34,5%** |
| 5 — normalização por participante | 0,047 → **0,298** | **71,0%** | 0,067 → 0,206 | **41,5%** |
| 3 — floresta aleatória (sem normalizador) | 0,257 | — | 0,302 | — |
| 2 — logística sem normalizador | 0,072 | — | — | — |

Divergência multivariada entre domínios: 1,353 / 1,066 / 0,668, e **`zcr` domina** (1,860 /
1,108 / 0,483).

**Adaptação.** H2 confirmada, e a normalização **por participante** — que não usa rótulo algum
do domínio de destino, e portanto não é vazamento — virou a representação de base de todos os
experimentos seguintes, no lugar da ablação 1, que tem acesso ao destino.

**E a correção que importa mais:** a leitura fácil desse resultado é *"recupera 70% a 80%"*, e
ela está errada. **Os 71,0% e os 77,6% são ambos de `cabeça → pulso`.** Em
`cabeça → cabeça-E4` a recuperação é **metade** — 34,5% e 41,5%. A faixa é de **um par de
posições, não da matriz**, e o texto de Y.4 teve de dizer isso com essas palavras ("cerca de
três quartos […] e cerca de dois quintos"). Sem a frase, o número parece valer para a matriz
inteira e não vale.

**Risco em aberto.** Duas ressalvas que ficam para a banca. **(i)** As frações são medidas
contra a diagonal de **origem**; contra a de **destino** sairia 83,3% em vez de 77,6% — as duas
contas são defensáveis, a adotada é a conservadora, e a escolha tem de ser declarada. **(ii)** A
floresta aleatória **não é "o modelo sem normalizador"**: ela é insensível a deslocamento
monotônico de escala por construção, então o Δκ dela não isola o residual de H1 tão limpamente
quanto o nome da ablação sugere.

**Procedência.** `ml/experimentos/saida/ml03b_ablacao_aec203907e6f_20260915T223235Z.json`;
`docs/RESULTADOS-TCC.md` §Y.4 e a nota de procedência com as três ressalvas.

---

# 2026-09-17/18 — `ML-03b` itens 6–9: as quatro otimizações, e uma que não saiu do ruído

**O problema, como foi entendido no início.** Melhorar o classificador dentro da coorte de
desenvolvimento.

**Hipótese de trabalho.** As quatro modificações candidatas (peso de classe, limiar de Youden,
suavização temporal, janela de contexto) dariam ganhos de tamanhos parecidos, e a validação
interna diria qual escolher.

**O que foi testado, e como.** LOSO, N = 92, com **bootstrap pareado da diferença** sobre os
mesmos sujeitos.

**Resultado medido.**

| Item | Modificação | Efeito medido |
|:-:|---|---|
| 6 | `class_weight="balanced"` | **+34 pontos de especificidade** (contrafactual) |
| 7 | limiar de Youden | troca κ por especificidade — não é ganho, é escolha de operação |
| 8 | mediana móvel | **não sai do ruído** |
| 8b | HMM de 2 estados | **Δκ = +0,123** [+0,105, +0,142] |
| 9 | contexto de ±11 épocas | Δκ = +0,075 e Δespecificidade = +0,101 |

**Adaptação.** A mediana móvel foi descartada. O HMM apareceu como o melhor candidato — quase o
dobro do ganho do item 9 — e teria sido escolhido se a decisão parasse aqui. **Parou não.** Ver
a entrada seguinte.

**Risco em aberto.** O item 7 continua sendo uma escolha de ponto de operação que ninguém
tomou: `κ` e especificidade não se otimizam juntas, e qual delas o produto prioriza é decisão
de escopo, não de modelagem.

**Procedência.** `ml/experimentos/saida/ml03b_otimizacoes_aec203907e6f_92suj.json`;
`docs/RESULTADOS-TCC.md` §Y.5.

---

# 2026-09-18 — `ML-04`: o ganho que parecia grande não atravessou a coorte

**O problema, como foi entendido no início.** Confirmar em coorte independente o que a
validação interna havia medido. O LOSO controla vazamento entre participantes, mas não controla
aparelho, protocolo, critério de pontuação, laboratório nem perfil da população — tudo isso
permanece constante dentro de uma coorte.

**Hipótese de trabalho.** Haveria degradação, e ela seria **uniforme**: todas as configurações
cairiam junto, e a ordem entre elas se preservaria. Sob essa hipótese, a validação interna é
suficiente para *escolher* o modelo, mesmo que insuficiente para *estimar* o desempenho.

**O que foi testado, e como.** Modelo ajustado nos **92** participantes de desenvolvimento de
uma vez e aplicado a **27** de coorte independente (Newcastle 2015): outro fabricante de
acelerômetro, outro centro, outra equipe de pontuação. **Sem reajuste de nada** — sem
reestimação de normalizador no destino, sem recalibração de limiar, sem acesso a rótulo da
coorte externa antes da medição.

**Resultado medido.** A degradação global:

| Métrica | Interna (N=92) | Externa (n=27) |
|---|---:|---:|
| κ de Cohen | 0,414 | **0,334** [0,254; 0,416] |
| Especificidade | 0,802 | **0,507** |

E a hipótese de uniformidade caiu:

| Modificação | Δκ interna | Δκ externa | Δespecificidade externa |
|---|---:|---:|---:|
| HMM de 2 estados | **+0,123** [+0,105; +0,142] | **+0,036** [+0,008; +0,067] | **−0,037** [−0,058; −0,014] |
| Contexto ±11 épocas | +0,075 | **+0,069** [+0,039; +0,102] | **+0,095** [+0,065; +0,130] |

O ganho do HMM praticamente desapareceu **e** veio com perda de especificidade estatisticamente
distinguível. O da janela de contexto preservou magnitude e direção.

**Adaptação.** A explicação é o que cada modificação aprende: a matriz de transição do HMM é
estimada sobre a **prevalência** de sono e vigília da coorte de treino, e aplicada a uma
população de prevalência distinta passa a penalizar indevidamente as transições para vigília. A
janela de contexto não codifica prevalência alguma — só muda a escala temporal sobre a qual as
features são computadas, e essa escala é propriedade do fenômeno, não da coorte.

Daí a limitação metodológica que o trabalho declara, e que é o achado mais forte dele:
**seleção de modelo apoiada só em validação cruzada interna é insuficiente neste domínio.**
Neste trabalho, especificamente, a validação interna **teria escolhido a modificação errada**.

**Risco em aberto.** **Uma única** coorte externa. A segunda (Walch et al. 2019, PhysioNet
`sleep-accel`, 31 sujeitos) não foi baixada — o repositório não é alcançável do ambiente de
execução (`ML-06a`). Com uma coorte só, a degradação relatada é **estimativa pontual, não
medida de variabilidade**: não dá para separar o que é "trocar de coorte em geral" do que é
"as particularidades desta coorte". Está declarado como procedimento **não executado**, e não
como procedimento executado com resultado desfavorável. Também não há teto inter-avaliador para
o Newcastle — aquela coleção não publica segunda pontuação.

**Procedência.** `ml/experimentos/saida/ml04_validacao_externa_aec203907e6f_esquerdo.json`;
`docs/LIMITACOES-TCC.md` "Degradação do desempenho entre coortes independentes" e
"Ganho que atravessa coorte"; `docs/RESULTADOS-TCC.md` §X.4.

---

# 2026-09-18 — `GIT-01`: vinte mil linhas de nada escondendo o diff

**O problema, como foi entendido no início.** `git status` acusava 144 arquivos modificados e
o diff era ilegível.

**Hipótese de trabalho.** Alguma ferramenta havia reformatado o repositório.

**O que foi testado, e como.** `git diff --ignore-cr-at-eol`.

**Resultado medido.** Devolveu **vazio**. Os 144 arquivos tinham **20.243 inserções e 20.243
remoções** — o mesmo número dos dois lados — e nenhuma mudança de conteúdo: editar no Windows
salvava CRLF no disco enquanto o histórico guardava LF.

**Adaptação.** `.gitattributes` com `* text=auto`, tipos declarados explicitamente para o caso
de o heurístico hesitar, `*.sh text eol=lf` (com CRLF o interpretador lê `#!/bin/bash\r` e não
encontra o programa) e binários marcados `binary` — uma única conversão corrompe o arquivo.

**Risco em aberto.** O problema real não era a feiura do diff: era que um ajuste de três linhas
ficava indistinguível de vinte mil linhas de nada, e **revisão que não se consegue fazer não se
faz**. Quantos diffs passaram sem revisão nesse período não é recuperável.

**Procedência.** `.gitattributes`, cabeçalho; commit `f188ec9`.

---

# 2026-09-21 — `ML-04b`: o lado do corpo não importa, e isso não prova o que parece

**O problema, como foi entendido no início.** A base externa tem registro simultâneo dos dois
punhos do mesmo participante. Isso permite isolar o efeito do lado.

**Hipótese de trabalho.** Se as features são invariantes a rotação e a montagem (decisão de
2026-09-14), o lado **não deve** produzir efeito detectável. É um teste da escolha de features,
não do modelo.

**O que foi testado, e como.** Comparação **intraparticipante** nos 26 com registro bilateral —
cada participante é seu próprio controle: mesma noite, mesma rotulagem de PSG, mesmo modelo,
variando só o lado. Participante como unidade de agrupamento.

**Resultado medido.** Na melhor configuração, Δκ = **+0,009** (IC 95%: −0,014 a +0,031) e
Δespecificidade = **−0,009** (−0,038 a +0,017). Nas vinte e quatro comparações, **todos os 24
IC 95% contêm zero**.

**Adaptação.** Nenhuma — o resultado confirmou a hipótese, o que é o caso raro neste diário.

**Risco em aberto.** E a ressalva é o valor da entrada: **com 26 participantes, efeito menor
que ~0,03 em κ não seria distinguível do ruído.** Ausência de efeito detectável não é
demonstração de ausência de efeito, e o texto não pode dizer "o lado não importa" sem o poder
do teste ao lado.

**Procedência.** `ml/experimentos/saida/ml04b_efeito_do_lado_aec203907e6f.json`;
`docs/LIMITACOES-TCC.md` "Lateralidade do sensor"; `ml/experimentos/_lados.py`.

---

# 2026-09-22 — `GIT-04`: três documentos passaram semanas fora do git

**O problema, como foi entendido no início.** Nenhum — o problema não estava sendo procurado.
Apareceu ao conferir o repositório contra o disco.

**Hipótese de trabalho.** O que está em `docs/` está versionado, exceto o que o `.gitignore`
exclui de propósito.

**O que foi testado, e como.** Comparação de `git ls-files docs/` com o conteúdo da pasta.

**Resultado medido.** **Três documentos nunca commitados**: `BACKLOG-COMPLETO.md`,
`ML-DATASETS-E-PLANO.md` e `SINTESE-PESQUISA-E-CAMINHOS.md`. O segundo é a **fundamentação que
os READMEs mandam ler** — um clone feito no dia anterior não a traria junto, e quem clonasse
encontraria READMEs apontando para um arquivo inexistente.

**Adaptação.** Versionados na mesma revisão. A prevenção ficou registrada como `CI-05`.

**Risco em aberto.** Nada impedia que acontecesse de novo — e o `CI-05`, como foi especificado
naquele momento, **não impediria**. Ver a entrada de 2026-09-30.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, `GIT-04` em "Concluído".

---

# 2026-09-22 — `HW-05`: a medição esperava pela rede, e a série saía com aparência normal

**O problema, como foi entendido no início.** Perda de dado quando a rede cai. O enunciado de
partida era *acrescentar buffer*.

**Hipótese de trabalho.** O prejuízo de uma queda de rede é a lacuna na série.

**O que foi testado, e como.** Leitura do caminho de execução do `envio-continuo.ino`, e depois
reimplementação do núcleo em C++ puro com suíte no host (`g++`), incluindo duas noites simuladas
de 8 h.

**Resultado medido.** `conectarWiFi()` era chamada **dentro do laço de amostragem**, e gastava
até **20 s** em `delay(500)`. Com intervalo de 10 s, uma queda de rede fazia cada ciclo levar
**20–30 s** — e a série **continuava saindo, com aparência normal, com a base de tempo
derivada**.

Para actigrafia, cuja unidade *é* a época fixa de 30 s, isso é pior que lacuna: **a lacuna a
análise vê; a deriva, não.** A perda de dado era o problema menor.

**Adaptação.** Quatro regras, e a arquitetura saiu delas:

1. **Nada na medição espera por conectividade.** Saíram os três travamentos: `while (!Serial)`,
   `while(1)` no `mpu.begin()` falho, e a conexão síncrona no laço.
2. **Perda de cadência vira campo no dado.** `EPOCA_INCOMPLETA` e `EPOCA_VAZIA`, e a época
   vazia **ocupa lugar no buffer** — custa 32 bytes dizer "aqui não houve medida", e sem isso a
   análise veria duas épocas encostadas e concluiria que a noite foi medida sem falha.
3. **O buffer é de épocas, não de amostras** — o que permite *degradar resolução* quando enche,
   em vez de descartar. Perde-se resolução, não cobertura. A degradação é **exata**, não
   aproximada: o método é `pico-da-magnitude`, e máximo é associativo.
4. **A grade é absoluta:** `t0 + k·período`, nunca `última + período`. Na segunda forma todo
   atraso de execução entra permanentemente na base de tempo e nunca mais sai.

Capacidade **medida**, não estimada (`make capacidade`), com registro de 32 B travado por
`static_assert`: 128 épocas em 4 KB de RTC = **1,07 h** em resolução cheia e **65,6 h**
degradado; 1024 épocas em 32 KB de heap = **8,53 h** e 543 h.

**A suíte pegou quatro bugs, um sério.** O fechamento de época era preguiçoso e `amostrar`
recusava amostra de um slot futuro por não ter como fechar o anterior: **uma amostra em cada
três** — as dos instantes 30 000, 60 000, 90 000 ms — desaparecia, e **toda época saía marcada
`INCOMPLETA` com a medição perfeita**. Na placa isso apareceria depois de uma noite de coleta;
no host apareceu em 3 ms. Os outros: `fundir` consultava `a->vazia()` *depois* de mesclar as
flags, então época com dado fundida com lacuna saía marcada como lacuna; e duas expectativas de
teste que estavam erradas — não o código.

**Risco em aberto.** Drenar 8 h de buffer são **960 POSTs**, um handshake TLS novo cada — número
medido em `capacidade.cpp`, não estimado. Daí o teto de 2 min no backoff (sem teto o aparelho
não perceberia a rede voltando; com teto curto gastaria rádio para falhar) e o item `API-03`,
endpoint de lote. Seriam 1,2 milhão de POSTs se o buffer fosse de amostras quando o `FW-05`
subir a amostragem para ≥ 42 Hz — **é a agregação, não o buffer, que torna a drenagem
possível.**

**Procedência.** `firmware/nucleo/README.md`; `firmware/nucleo/testes/testes.cpp`
(341 verificações); `docs/BACKLOG-COMPLETO.md`, `HW-05`.

---

# 2026-09-22 — um dos sketches nunca compilou, e nada no repositório tentava compilar

**O problema, como foi entendido no início.** Nenhum. O `envio-continuo.ino` era tratado como
código em funcionamento, e o backlog discutia melhorias nele.

**Hipótese de trabalho.** Código versionado num repositório com CI é código que ao menos
compila.

**O que foi testado, e como.** Ao montar o alvo `make sintaxe` — `g++ -fsyntax-only` sobre os
`.ino` com stubs mínimos do Arduino — o sketch versionado foi compilado pela primeira vez.

**Resultado medido.** O `envio-continuo.ino` tinha **duas strings com quebra de linha literal
no meio**. **Não compilava em máquina nenhuma.** E ficou assim porque nada no repositório
tentava compilar: o CI olhava Python e frontend, e o firmware só era exercitado
manualmente no Wokwi — onde o arquivo aberto era o da máquina de quem editava, não o versionado.

**Adaptação.** O alvo `make sintaxe` entrou no `firmware/nucleo/Makefile`. Ele gera um
`secrets.h` falso em `bin/` e o põe **por último** no caminho de include, para rodar em qualquer
clone sem exigir credencial — e para que um `secrets.h` de verdade, se houver, vença.

Uma causa mais funda ficou registrada na mesma revisão: `sketch.ino` e `envio-continuo.ino`
tinham chegado a **critérios de movimento diferentes** antes do `FW-06`, porque o núcleo era
duplicado em cada sketch e as cópias divergiram na primeira correção. Daí a unidade de tradução
única (`nucleo_amalgama.cpp`).

**Risco em aberto.** Até 2026-09-30, **`make sintaxe` continuava sendo chamado só à mão**, e
`firmware/caracterizacao/caracterizacao.ino` **não está na lista que ele compila** — é
exatamente a classe de arquivo que produziu este achado. O job de CI escrito em 30/09 chama
`make sintaxe`, mas não acrescentou o `caracterizacao.ino` à lista, porque a sessão que o
escreveu não tinha shell para verificar se ele compila (ver a última entrada).

**Procedência.** `firmware/nucleo/Makefile`, alvo `sintaxe`, comentário de cabeçalho;
`firmware/nucleo/testes/stubs-arduino/Arduino.h`; `firmware/nucleo/README.md` § final.

---

# 2026-09-22 — `FW-07`: o sketch de produto tira uma amostra por boot

**O problema, como foi entendido no início.** O `sketch.ino` precisava de correção defensiva
nos travamentos — era o enunciado do `HW-05` para ele.

**Hipótese de trabalho.** Tirados os travamentos, o sketch de produto serviria para captação
noturna.

**O que foi testado, e como.** Leitura da máquina de estados do sketch.

**Resultado medido.** Ele tira **uma amostra por boot** e dorme. **Não registraria uma noite
nem com rede perfeita** — não tem amostragem periódica nenhuma. O problema não era
robustez, era ausência de estrutura.

**Adaptação.** Em 22/09 ele recebeu **só** a correção dos travamentos, e o conserto de verdade
foi separado como `FW-07`: reorganizá-lo em torno do núcleo, com buffer no RTC
(`RTC_DATA_ATTR`, 128 épocas — o heap não sobrevive ao Deep Sleep) e ciclo acordar → medir →
agregar → dormir. O núcleo já existe e está testado; o que falta é a máquina de estados do sono.

**Risco em aberto.** O `FW-07` está aberto e é 🔴. Enquanto estiver, o "firmware de produto" do
trabalho é o `envio-continuo.ino`, que não dorme.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, `FW-07`; commit `54504f6`.

---

# 2026-09-28 — `SEC-05`: uma suíte de segurança que nunca falhou não provou nada

**O problema, como foi entendido no início.** Cobrir o isolamento entre usuários (RLS do
Postgres) com testes.

**Hipótese de trabalho.** Testes contra Supabase mockado cobririam a regra.

**O que foi testado, e como.** A hipótese caiu de saída: **mock não exercita policy nenhuma**.
A suíte foi reescrita contra Postgres de verdade — 105 testes adversariais em `profiles`,
`devices` e `sleep_data` por todo comando, mais invariantes de catálogo (tabela nova sem RLS,
`using (true)`, policy para `anon`). E depois submetida a **verificação por mutação**: o esquema
é sabotado de N maneiras, uma por vez, e se exige que a suíte acuse cada uma.

**Resultado medido.** 18 sabotadores no registro do item, 25 no job do CI — **todos
detectados**. E a mutação achou um defeito no próprio instrumento: um teste que olhava **só a
primeira linha** do resultado passava por acidente; foi corrigido por causa da sabotagem, não
por revisão.

**Adaptação.** Três decisões de infraestrutura saíram daqui, e as três são sobre o mesmo
risco — **verde que não verificou nada**:

1. **Matriz de versão do Postgres (14 e 16).** RLS e privilégio mudam de comportamento entre
   majors — a 15 mudou o dono e os privilégios do schema `public`. O harness foi verificado na
   14; a 16 é a que se usaria hoje. `fail-fast: false`, porque saber que passa na 14 e falha na
   16 é metade do diagnóstico.
2. **Guarda contra pulo silencioso.** `pytest.skip` **não falha o job**. Se a variável de
   ambiente sumisse, se o serviço não subisse, se o `psycopg2` deixasse de instalar, os testes
   de RLS seriam **pulados** e o CI ficaria **verde, anunciando cobertura de segurança que não
   rodou**. Os três cenários foram exercitados à mão. Pulo silencioso é pior que falha, porque
   ninguém investiga o verde.
3. **`--ignore` em vez de deixar pular.** Pulo aparece como "s" no relatório e vira ruído que se
   aprende a ignorar.

**Risco em aberto.** A migração `002_backfill_dono_dos_dados.sql` está escrita e mergeada desde
agosto e **não foi rodada no Supabase** (`DATA-03`): sem ela o dashboard de uma conta nova nasce
vazio. É um comando, e depende de acesso que a execução não tem.

**Procedência.** `web-app/tests/rls/`, `verificar_por_mutacao.py`; `.github/workflows/ci.yml`,
job `rls` e a etapa "Conferir que os testes de RLS não foram pulados";
`docs/BACKLOG-COMPLETO.md`, `SEC-05`.

---

# 2026-09-28 — `ML-05`: a faixa de leitura não é [0; 1], é [0; 0,61]

**O problema, como foi entendido no início.** Os Δκ medidos nos experimentos precisavam de uma
referência superior. Contra 1,0 um κ de 0,41 parece ruim.

**Hipótese de trabalho.** A concordância entre dois pontuadores humanos daria um teto alto —
próximo de 1 —, e a distância até ele mediria o quanto falta ao modelo.

**O que foi testado, e como.** As duas pontuações manuais do Wearanize+ comparadas entre si, na
**mesma redução binária** que o pipeline aplica.

**Resultado medido.** κ = **0,607** [0,569; 0,643] nos **96** sujeitos com as duas pontuações, e
**0,612** [0,572; 0,650] nos **90** que também estão nos 92 da base de desenvolvimento — este é
o divisor certo. **A faixa de leitura dos Δκ é [0; 0,61], não [0; 1].**

Achado de brinde, e desconfortável: o pontuador 2 marca **7,8 pontos percentuais** mais de
vigília que o pontuador 1, e **a especificidade humana vale 0,958 ou 0,520 conforme qual dos
dois se toma como referência.** A especificidade externa do modelo (0,507) deixa de parecer um
número isolado.

**Adaptação.** O capítulo de resultados foi reescrito contra esse teto. Foi a lacuna barata que
faltava para fechar o `DOC-08`.

**Risco em aberto.** **Não há teto para o Newcastle** — a coleção não publica segunda pontuação.
O número externo do trabalho é o único sem referência superior própria, e é justamente o que o
trabalho declara como número honesto.

**Procedência.** `ml/experimentos/saida/ml05_teto_interavaliador_aec203907e6f.json`;
`docs/RESULTADOS-TCC.md`; `docs/BACKLOG-COMPLETO.md`, `ML-05`.

---

# 2026-09-29 — `CALC-03`: o limiar de 1,2 m/s² não foi derivado do ruído, e a derivação não o gera

**O problema, como foi entendido no início.** Transpor para o texto a derivação do limiar de
atividade na forma clássica `g ± k·σ`. O backlog dizia que o item já estava "boa parte
resolvido" pelo `ML-01` e que virou *transpor, não decidir*.

**Hipótese de trabalho.** O limiar de 1,2 m/s² em uso é um limiar do tipo `g ± k·σ`, com algum
`k` razoável — a forma do critério (`|‖a‖ − g| > limiar`) tem exatamente essa aparência.

**O que foi testado, e como.** Uma divisão. Com `σ = 1,833 mg = 0,0180 m/s²` na banda de 21 Hz
(`scripts/calculos_tcc.py`, o mesmo σ que o `FW-06` usou):

> k = 1,2 / 0,0180 ≈ **67 σ**

**Resultado medido.** **67 desvios-padrão.** Um limiar de detecção derivado de ruído opera
tipicamente entre **3 σ e 5 σ** — o compromisso entre falso positivo e sensibilidade. Um limiar
a 67 σ **não pertence a essa família**: ele não foi derivado do ruído, e a derivação `g ± k·σ`
não o gera nem o explica. Escrever a derivação assim mesmo produziria um valor entre **0,054 e
0,090 m/s²** — de **treze a vinte e duas vezes menor** que o em uso.

**Adaptação.** O item foi **recortado**, não cumprido: a seção Z.2.3 do `CALCULOS-TCC.md`
**demonstra por que a derivação não produz número útil**, em vez de produzir um número que
pareceria derivado e não seria. Uma derivação escrita com `k = 67` implícito seria pior que a
ausência dela — daria ao 1,2 uma procedência que ele não tem.

De onde o 1,2 vem de verdade está na entrada de 2026-08-20: da correção da assimetria, herdado
de `11,0 − 9,81 = 1,19`. É um número de engenharia, não de estatística, e agora está escrito
assim.

**Risco em aberto.** O limiar continua em uso, continua marcado como provisório, e a calibração
empírica (`VIA-01`) depende da solda. Pior: ele é **constante compartilhada** — o celular
(`APP-01`) é classificado pela mesma régua nascida do travesseiro, com outro acoplamento
mecânico e outro sensor (`DATA-06`). E o viés de Z medido em 25/08, `−1,06 m/s²`, é 89% dele.

**Procedência.** `docs/CALCULOS-TCC.md` Z.2.3 e a nota 🔧 1;
`scripts/calculos_tcc.py`; `docs/DATA-CONTRACT.md` §2.2.

---

# 2026-09-29 — `DATA-07`: a feature angular não era diferença entre épocas, por geometria

**O problema, como foi entendido no início.** Decidir o que o dispositivo guarda no buffer para
que o servidor reconstrua as 8 features. Guardar amostra bruta não cabe; guardar as 8 features
por época custaria bytes, e duas delas (`inclinacao_rel` e `d_angulo`) pareciam redundantes.

**Hipótese de trabalho.** `d_angulo` é a **diferença de `inclinacao_rel` entre épocas
vizinhas**. Se for, não precisa ser guardada: sai da outra por subtração, e o registro
encolhe.

**O que foi testado, e como.** Duas coisas. Primeiro a álgebra — as duas features são
`arccos` de produtos internos de vetores unitários:

```
inclinacao_rel[t] = arccos( ĝ_t · ĝ_ref )     ĝ_ref = mediana geométrica da NOITE INTEIRA
d_angulo[t]       = arccos( ĝ_t · ĝ_{t−1} )
```

Depois a medição da aproximação sobre dado real, em `ml/testes/test_redundancia_angular.py` e
`scripts/estudo_buffer.py`.

**Resultado medido.** São ângulos **numa esfera**, e entre eles não vale uma igualdade: vale a
**desigualdade triangular esférica**

> |θ_t − θ_{t−1}| ≤ d_angulo ≤ θ_t + θ_{t−1}

que deixa **um grau de liberdade** que só `ĝ` fecha. Medido em **87 795 épocas**: a aproximação
erra **0,01 grau na mediana** e **149 graus no pior caso** — e o erro está **concentrado nas
viradas**, que é tudo aquilo para o que a feature existe. A mediana boa era a armadilha: ela
tornava a hipótese plausível exatamente onde nada acontece.

**Adaptação.** O dispositivo guarda **`ĝ` (gravidade unitária)** por época, e as duas features
angulares são derivadas **no servidor**, sobre a noite completa, pelo mesmo código que produziu
os resultados do ML. A reconstrução é exata.

Isso resolveu junto um problema que não estava sendo procurado: `ĝ_ref` é a mediana geométrica
(Weiszfeld) da gravação **inteira**, e **um dispositivo que drena em tempo real não pode
conhecê-la** — ao enviar a época 12, as épocas 13 a 960 não existem. A proposta que havia em
`features.py` era um "acumulador direcional com aquecimento", que é um **estimador diferente**,
não uma aproximação com tolerância: divergiria do Python em silêncio. Guardando `ĝ`, a `ĝ_ref` é
calculada na drenagem com o mesmo Weiszfeld, e a divergência deixa de ser possível.

**Risco em aberto.** O contrato v2.5.0 declara o formato; **a implementação em C++ não existe**
(`DATA-07b`). E há uma decisão pendente: se o dispositivo emite `f` de época truncada — ver a
entrada seguinte, item (c).

**Procedência.** `docs/DECISAO-BUFFER-E-FEATURES.md` §6; `docs/DATA-CONTRACT.md` §2.6;
`ml/testes/test_redundancia_angular.py`; `scripts/estudo_buffer.py` §6.

---

# 2026-09-29 — `DATA-07b`: "o item virou transcrever" estava errado

**O problema, como foi entendido no início.** O `DATA-07` original afirmava que o item havia
saído de *"a definir"* para *"transcrever"* — as features estariam definidas, e faltaria passar
para C++.

**Hipótese de trabalho.** Existe um lado C++ das features, ainda que incompleto.

**O que foi testado, e como.** Um `grep`:

```
grep -rniE "enmo|zcr|p_frac|inclinacao|d_angulo|mag_din" firmware/
```

**Resultado medido.** **Vazio.** As 8 features existem **só em Python**. O que o projeto chamava
de "lado C++" era uma referência **escrita em Python** dentro de `test_vetor_dourado.py`
(`features_estilo_firmware`) — útil como especificação, e nenhuma linha de firmware.

**Adaptação.** O item foi reescrito com as cinco partes que faltam de verdade: (a) o biquad
Butterworth de 2ª ordem ida-e-volta em C++, com inicialização em regime permanente; (b)
acumulação por época das 6 features + `ĝ` no registro de 40 B; (c) alvo de teste em C++ que leia
o `vetor_dourado.json` — 437 KB, e **não há parser JSON no núcleo**, que é `-fno-exceptions
-fno-rtti` de propósito; (d) migração e mudança na ingestão para persistir; (e) derivação das
features inter-época no servidor. Peso reclassificado para comparável ao `FW-07`.

**Risco em aberto.** É o item aberto de maior peso do projeto junto com o `FW-07`, e foi
subestimado por seis dias porque ninguém rodou o `grep`.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, `DATA-07b`; `ml/testes/test_vetor_dourado.py`.

---

# 2026-09-30 — `DATA-07c`/`07d`: o vetor dourado gravava a própria referência

**O problema, como foi entendido no início.** O vetor dourado é o instrumento que impede as
duas implementações da mesma feature (Python e C++) de divergirem em silêncio. Ele existia com
5 casos e a suíte passava.

**Hipótese de trabalho.** Uma suíte de paridade que passa é uma suíte que verifica paridade.

**O que foi testado, e como.** **Verificação por mutação** do próprio instrumento
(`ml/testes/verificar_vetor_dourado_por_mutacao.py`): sabota `src/features.py` de doze maneiras,
uma por vez, numa cópia da árvore em `/tmp`, e exige que a suíte **acuse** cada uma — com o
teste nomeado em `exige` entre os que caem, para que ela não acuse por acidente. As classes de
sabotagem: erro de sinal, ordem de operações, condição de borda, filtro sem inicialização,
estimador trocado, unidade, e regressão já vivida.

**Resultado medido.** 12/12 sabotagens detectadas e 1 ponto cego registrado — **depois** de
corrigir três defeitos do instrumento, que é o que esta entrada registra:

**(a) O dourado se regravava sozinho.** `test_gravar_vetor_dourado` **gravava** o arquivo de
referência e conferia que ele **existia**. Isso nunca falha. Qualquer mudança na definição de
uma feature reescrevia o dourado e a suíte seguia verde: **o arquivo perseguia o código em vez
de prendê-lo.** Um vetor dourado que se regrava sozinho não é vetor dourado, é log.
*Corrigido:* agora ele **confere**, e regravar exige dizer que se quer regravar
(`DORMIO_REGRAVAR_DOURADO=1`) e explicar no commit o que mudou de definição.

**(b) A tolerância exigia mais do que um firmware correto pode entregar.** Estava em
`rel = 1e−6`. Medido em **60 sementes** com a fórmula em float32 — que é o que o ESP32 calcula:
`enmo_media` diverge **1,10e−6** relativo e `enmo_max` **3,51e−6**. **A tolerância reprovaria
firmware correto.** A causa é **cancelamento catastrófico** em `‖a‖ − 1` com `‖a‖ ≈ 1`: o float32
tem ~1,2e−7 g de resolução em 1 g, e é essa resolução que limita, não a do resultado. Trocar o
acumulador para double **não resolve** — medido, 1,101e−6 contra 1,097e−6 — porque o erro entra
no `sqrt` **por amostra**, não na soma. *Corrigido:* tolerância **absoluta**, `1e−7 g` = 1 ULP
de float32 em 1 g, que fica 6 400× abaixo do piso de ruído do ENMO no MPU6050 (0,64 mg).

**(c) Época incompleta não tem paridade nenhuma.** O ramo degenerado de `estimar_gravidade`
(n ≤ 9) não existe na referência estilo-firmware, e ali a divergência vai a **54%**. Mesmo
passando desse ramo: n = 64 diverge **3%** e n = 300, **0,8%**.

E o ponto cego original, que era o mais silencioso dos quatro: os 5 casos eram **todos de época
única**, então `inclinacao_rel` e `d_angulo` valiam **0 em todos os cinco** — **as duas features
de definição mais delicada não tinham referência nenhuma**, e o instrumento que devia pegar a
divergência era cego exatamente ali. Zero também é trivialmente invariante a rotação, então o
teste de invariância delas passava sem testar nada.

**Adaptação.** O dourado virou **dois arquivos**, um por fronteira da v2.5.0:
`vetor_dourado.json` (dispositivo, Python↔C++, 6 features + `ĝ`, 437 KB, com amostra bruta) e
`vetor_dourado_sequencias.json` (servidor, derivação a partir do `ĝ` guardado, **23 KB e nenhuma
amostra bruta** — as duas features são função só de `ĝ`, então cobri-las não custa sinal). 8
sequências: mudança de postura, virada brusca de 140°, deriva coerente sub-grau, retorno exato à
orientação, faixa cobrindo todos os bins do estudo do buffer, duas épocas, uma época, e lacuna
temporal. As tolerâncias passaram a ser **derivadas entre piso medido e teto de decisão**, e
`test_as_tolerancias_ainda_cercam_o_piso` **re-mede o piso a cada execução** — uma tolerância
medida uma vez e depois só comentada envelhece.

**Risco em aberto.** **O contrato precisa dizer que o dispositivo não emite `f` de época
truncada**, e não diz ainda — decisão pendente no `DATA-07b`, item (b). E a paridade continua
garantida **de um lado só**: enquanto o firmware não consumir o JSON, o dourado é uma
especificação que ninguém leu.

**Procedência.** `ml/testes/test_vetor_dourado.py` (cabeçalho, bloco de tolerâncias,
`test_dourado_do_dispositivo_confere_com_o_arquivo`);
`ml/testes/verificar_vetor_dourado_por_mutacao.py`; `docs/BACKLOG-COMPLETO.md`, `DATA-07c` e
`DATA-07d`.

---

# 2026-09-29/30 — `REF-01` e `LGPD-01`: o que a conferência na fonte achou

**O problema, como foi entendido no início.** As referências bibliográficas e as citações de
artigos da LGPD estavam escritas nos documentos e seriam conferidas por formalidade.

**Hipótese de trabalho.** Citação escrita por quem leu o material está certa; a conferência
acharia erros de formatação.

**O que foi testado, e como.** Conferência de **11 fontes na fonte** (`REF-01`), e das citações
da LGPD contra o texto no Planalto.

**Resultado medido.** Nas referências: **1 autoria falsa** (`Rocha et al.` → **Li, Halaki &
Chow**), **1 tendência não significativa apresentada como achado**, **1 número virado
indevidamente em requisito técnico** e **2 citações não localizadas**. Nenhuma referência
permanece sem autoria conferida.

Na LGPD, dois erros de inciso e artigo, com naturezas diferentes:

- **art. 18, V → VI.** O inciso V trata de *portabilidade a outro fornecedor*; a *eliminação dos
  dados tratados com consentimento* é o **VI**. A troca estava em `LGPD-ELIMINACAO.md`,
  `DATA-CONTRACT.md` §6.2, `routes.py`, na migração `006` e no `BACKLOG-COMPLETO.md` — **cinco
  lugares, propagada por cópia.**
- **art. 13, §4º → art. 12.** A citação do art. 13 §4º *existe e é onde a pseudonimização é
  definida*, mas o artigo inteiro trata de *estudos em saúde pública*, então citá-lo sozinho para
  sustentar "dado pseudonimizado continua sendo dado pessoal" é frouxo. Conferido no Planalto, o
  §4º abre com *"Para os efeitos deste artigo"* — **a própria lei circunscreve a definição ao
  art. 13**, o que torna a objeção textual, e não apenas contextual.

**Adaptação.** O argumento passou a ser apoiado no **art. 12**, que retira do escopo da lei
apenas o dado **anonimizado** — de onde se segue, por contraste, que o pseudonimizado permanece
dentro. A formulação foi estendida aos três documentos e ao cabeçalho da migração `006`, que
ainda repetiam a antiga, e uma **varredura completa** conferiu que nenhuma outra citação de
artigo da LGPD no repositório está incorreta.

**Risco em aberto.** `DOC-06b`: **referência conferida ≠ artigo lido.** As 11 têm autoria
correta; quantas foram lidas além do resumo não está registrado, e é o que o item cobra. E na
LGPD, duas decisões que não dão para inferir do repositório: quem é o **controlador** e qual a
**base legal** — consentimento (art. 7º, I) ou pesquisa (art. 7º, IV) —, que muda a política
inteira.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, `REF-01`; `docs/POLITICA-DE-PRIVACIDADE.md`,
seção de notas; `docs/SINTESE-PESQUISA-E-CAMINHOS.md`; commit `fab1d95`.

---

# 2026-09-30 — `CI-03`/`CI-04`/`CI-05`: a prevenção especificada não podia reprovar

**O problema, como foi entendido no início.** Três itens de integração contínua em aberto. O
`CI-05` estava especificado assim, com estimativa: *"Um job que falhe quando há arquivo não
rastreado em `docs/` custa três linhas e fecha a classe de problema."*

**Hipótese de trabalho.** A especificação era correta e o trabalho era de transcrição — as três
linhas seriam `git ls-files --others --exclude-standard -- docs/` dentro de um job.

**O que foi testado, e como.** Não uma execução: um raciocínio sobre o que o `actions/checkout`
monta. O git envia **objetos commitados e nada mais**. A árvore de trabalho de um runner é
construída a partir do commit.

**Resultado medido.** **Num runner não existe arquivo não rastreado em `docs/`** — não porque o
repositório esteja limpo, mas porque o arquivo não rastreado nunca sai da máquina de quem o
escreveu. O comando devolveria vazio **sempre**, o job passaria **sempre**, e o resultado seria
um selo verde que não verificou nada. A prevenção pedida, posta onde foi pedida, seria
**decorativa** — contra uma classe de problema que o `GIT-04` já demonstrou ser real.

Os outros dois também mudaram de natureza ao serem executados, na direção oposta — ficaram mais
baratos. O `CI-03` pedia `arduino-cli compile`, uma toolchain de 300 MB; o repositório **já
tinha** a verificação desde 22/09 (`make sintaxe`, `g++ -fsyntax-only` com stubs), e faltava
só chamá-la. O `CI-04` parecia exigir os ~46 GB de dado; não exige — `ml/dados/` só tem
`.gitkeep` versionado e a suíte gera sinal sintético, porque o que ela verifica é a **definição**
das features, não a medição.

**Adaptação.** O `CI-05` foi reimplementado com **duas** verificações de alcance declarado, em
`scripts/conferir_docs_versionados.py`:

1. **Órfão na árvore** — existe em `docs/`, não rastreado, não ignorado. É o estado exato do
   `GIT-04`. Só detectável na máquina de quem edita, e o script **diz isso** quando roda com
   `CI` no ambiente, em vez de reportar "✓ nenhum" e deixar parecer verificação.
2. **Referência pendente** — caminho `docs/*.md` citado por arquivo **rastreado**, ausente do
   git **e** do `.gitignore`. **Esta roda e reprova no CI**, porque tanto a citação quanto a
   ausência viajam no commit. É a forma pela qual o `GIT-04` causava dano: o
   `ML-DATASETS-E-PLANO.md` era a fundamentação que os READMEs mandavam ler, e o clone não a
   trazia.

A distinção que o script usa é a única que importa: **ignorado é decisão, não rastreado e não
ignorado é esquecimento.** Tirar um documento do versionamento exige dizê-lo no `.gitignore`, e
aí a linha fica no diff, onde alguém a lê. Isso preserva as exclusões deliberadas
(`docs/METODOLOGIA.md`, `docs/DATASET.md`, `docs/HARDWARE.md`, `docs/fontes/`, `docs/devlog/`),
que são citadas por arquivos rastreados e devem continuar sendo.

**Risco em aberto — e é o maior desta entrada. Nada disto foi executado.** O ambiente da sessão
perdeu o shell (disco cheio no sandbox) antes da validação, e o único procedimento que o `CI-05`
pedia explicitamente — **criar um documento em `docs/` sem versionar e confirmar que a
verificação acusa** — **não foi feito**. A suíte do `ml/` também não rodou até o fim nesta
sessão: foi iniciada duas vezes e interrompida por tempo, então os 70 testes e o verificador por
mutação entraram no CI sem uma execução verde de referência. `firmware/caracterizacao/caracterizacao.ino`
continua fora da lista do `make sintaxe`, pela mesma razão.

É registro de **procedimento não executado**, não de procedimento executado com resultado
favorável — a mesma distinção que o `LIMITACOES-TCC.md` faz sobre a segunda coorte externa. E é
a ironia que fecha a entrada: um item sobre prevenção decorativa entregue sem a verificação que
o distinguiria de decoração.

**Procedência.** `scripts/conferir_docs_versionados.py`, cabeçalho;
`.github/workflows/ci.yml`, jobs `ml`, `firmware` e `documentos`;
`docs/BACKLOG-COMPLETO.md`, nota 🟠 ao final da seção "Infraestrutura e qualidade".

---

# O que este diário não cobre

Registrado para que a ausência não passe por completude.

| Lacuna | Por quê |
|---|---|
| Tudo antes de 2026-04-29 | Anterior ao versionamento. Escolha do ESP32 + MPU6050, do travesseiro em vez do punho, e o enunciado inicial do problema não estão no git. |
| Grande parte de junho a agosto | O `HISTORICO.md` cobre o período, mas **não é versionado** (está no `.gitignore`), então não pode ser citado como procedência num capítulo de TCC. As entradas desse intervalo aqui saem de reflog e de código, e por isso são poucas. |
| As suítes do backend e do frontend | Os números de 10/09 (221 pytest, 315 vitest) são os últimos medidos; a revisão de 22/09 **não as reexecutou**. |
| O frontend de 29/09 | Há 15 arquivos modificados e não commitados em `frontend/` de outra sessão de trabalho. Não estão neste diário porque não estão no histórico, e não foram lidos. |
| Toda a camada L1 e L2 | Nada foi medido no dispositivo físico. Os 8 pinos do MPU6050 não estão soldados. Todo número de hardware neste arquivo é **calculado ou simulado**, com uma exceção — a leitura de 25/08, que é medição de um sensor mal conectado e serve só para dizer que não serve. |
