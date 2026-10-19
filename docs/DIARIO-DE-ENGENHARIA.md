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

> **Fechada em 2026-10-16.** O risco em aberto desta entrada — "nada disto foi
> executado" — foi resolvido na entrada seguinte, e os três jobs reprovaram. A
> análise acima estava certa; as três implementações dela, não.

---

# 2026-10-16 — `CI-03`/`CI-04`/`CI-05` executados: os três jobs reprovaram, cada um pelo seu motivo

**O problema, como foi entendido no início.** A entrada anterior (30/09) deixou um risco
declarado em aberto: três jobs de CI escritos sem uma única execução, porque o shell da sessão
caiu com o disco cheio antes da validação. Além disso, dois commits ficaram por fazer com os
arquivos já em disco. O enunciado desta sessão era, portanto, de dívida: commitar e validar.

**Hipótese de trabalho.** A hipótese era explícita e está escrita na entrada de 30/09 — a
análise que motivou os três jobs *é verificável por leitura*, em particular a do `CI-05`, que é
consequência de o git enviar objetos commitados e nada mais. Donde se seguia, tacitamente, que a
execução seria confirmação: rodar, ver verde, tirar o 🟠. Os arquivos tinham sido lidos e
revisados em 30/09.

**O que foi testado, e como.** Execução local dos três jobs, passo por passo, mais controle
positivo em cada um — provocar de propósito o defeito que o job deve pegar e confirmar que
acusa. Antes, `git log`, `git status` e os `mtime` dos arquivos, para conferir se duas semanas
tinham mudado algo (não tinham: nada no repositório foi tocado desde 30/09 03:20).

**Resultado medido. Os três reprovaram, e nenhum pelo motivo que se esperaria.**

| Job | O que a execução achou |
|---|---|
| `documentos` (`CI-05`) | **O verificador se acusava a si mesmo.** Reprovou com três referências pendentes, e as três eram prosa: `docs/FOO.md` e `docs/sub/FOO.md` estão no comentário do próprio `PADRAO_REFERENCIA`, para explicar o que o regex casa, e `docs/ORFAO-DE-TESTE.md` está no backlog, dentro do procedimento de validação **deste mesmo script**. Job vermelho desde o primeiro push. |
| `firmware` (`CI-03`) | **A lista tinha dois dos quatro sketches versionados**, e na primeira vez que os outros dois foram compilados os **dois** tinham string com quebra de linha literal no meio — o defeito exato que o alvo nasceu para pegar, o mesmo do `envio-continuo.ino` de 22/09. Mais dois no `diagnostico-i2c.ino`: chave sobrando fechando `setup()` no meio, e `%lu` para um `uint32_t` (no ESP32, `unsigned int`), que faz o `printf` ler 8 bytes de um argumento de 4. |
| `ml` (`CI-04`) | **A suíte passou inteira** — 107 testes em 8,75 s, 12 de 12 sabotagens detectadas pelo verificador por mutação, ponto cego registrado confirmado. **A guarda é que estava quebrada:** o piso era 70, de 22/09, e a suíte tem 107 — ela toleraria perder 37 testes, um terço da cobertura, sem reprovar. |

Quatro defeitos de firmware que nunca compilaram, um verificador que não podia passar e uma
guarda que não guardava um terço do que anuncia. Nenhum deles é erro de digitação: cada um é um
**alcance** menor do que o declarado.

**Adaptação.** Em cada caso, a correção de superfície veio acompanhada de uma de fundo, porque a
de superfície repetiria o defeito na próxima vez:

1. `CI-05` — `EXEMPLOS_EM_PROSA`, isenção estreita e **impressa a cada execução**, porque
   isenção silenciosa é como uma verificação deixa de verificar sem ninguém notar. Vale **só
   para a verificação (2)**: na (1) o nome não tem isenção, senão o próprio procedimento de
   validação (criar o órfão, confirmar que acusa) ficaria incapaz de falhar — que é o defeito
   que o `DATA-07d` achou no vetor dourado, na mesma forma.
2. `CI-03` — a lista de sketches **deixou de ser escrita à mão**: sai de `$(wildcard)`, com
   guarda para o caso de não casar nada. Lista manual é alcance que silenciosamente para de
   acompanhar a pasta, e foi assim que dois sketches ficaram semanas sem compilar.
3. `CI-04` — piso em 107, com o motivo e a obrigação de atualizar escritos ao lado. A guarda é
   necessária ali por um detalhe que vale registrar: o passo roda o pytest com `|| true`, então
   o exit 2 da coleta sumiria — quem acusa é a contagem.

A suíte completa foi rodada depois, e achou **um quinto defeito, fora do CI**: o backend
declarava contrato `2.5.0` com o `DATA-CONTRACT.md` em `2.5.1` desde 30/09. O
`test_informa_a_versao_do_contrato_de_dados` não fixa a versão num literal — lê do documento,
exatamente para que a divergência não fosse possível em silêncio. Funcionou: acusou na primeira
execução da suíte do backend depois de 30/09, que foi hoje. O teste estava certo e disponível
por duas semanas sem ninguém rodar, o que é o argumento do CI em uma frase.

Estado final das quatro suítes: núcleo C++ **341 verificações, 0 falhas**; `make sintaxe`
**4/4**; `ml/` **107 passam**; backend **240 passam** (eram 239 + 1 falha); frontend **338
passam** em 22 arquivos, com `tsc --noEmit` e `vite build` limpos.

**Risco em aberto.**

- **Nenhum destes jobs rodou num runner do GitHub.** Rodaram todos localmente, e o
  `chore/GIT-01-normalizar-fim-de-linha` não foi enviado. O que o runner tem e o local não é
  justamente o `actions/checkout` — o ponto central da análise do `CI-05` — além das versões de
  `setup-python`/`setup-node` e do cache do pip. Enquanto isso não rodar lá, a frase honesta é
  "validado localmente", não "o CI passa".
- **`web-app/tests/rls/` não rodou: 125 testes pulados.** Exige um Postgres de verdade, e o
  sandbox não tem root para instalar um (`apt-get` bloqueado). É o job `rls`, com matriz de
  versão, e continua sem execução de referência — a mesma situação em que os três acima
  estavam, e que esta entrada mostra não ser inofensiva.
- **Os 15 arquivos de frontend de 29/09 continuam não commitados, e agora há um agravante:** os
  338 testes do frontend e o `tsc` passaram **sobre a árvore de trabalho**, isto é, *com* essas
  alterações. Não é medição do estado commitado, e o número não deve ser citado como se fosse.
- **`caracterizacao.ino` entrou neste commit só pela metade, de propósito.** O arquivo tinha uma
  edição de cabeçalho pendente de outra sessão (`FW-06`); só o hunk do `printf` foi commitado. A
  edição da outra sessão continua em disco, sem commit.
- **O `/tmp` não foi o culpado de 30/09.** A suspeita registrada era que a suíte do `ml/` teria
  enchido o disco; medido, ela roda em 8,75 s e não escreve em `/tmp` (92 KB durante toda a
  execução). O custo está em instalar `scipy` + `scikit-learn`, ~160 MB de build. A causa
  provável do travamento de 30/09 é essa, não os testes — mas é inferência, não medição: o
  ambiente daquela sessão não existe mais para conferir.
- **O `.git/_lixo_sandbox/` cresceu** (88 → ~95 itens): locks órfãos que o sandbox não pode
  apagar, mais os arquivos de teste desta sessão. Ainda é o `GIT-03`, ainda ⚪, ainda precisa de
  um terminal na máquina.

**Procedência.** Commits `7a96e6a` (diário), `6312267` (os três jobs como estavam),
`7feeef9` (CI-03/CI-05 corrigidos), `6359912` (guarda do CI-04), `fa34897` (contrato 2.5.1);
`docs/BACKLOG-COMPLETO.md`, nota ✅ ao final de "Infraestrutura e qualidade";
`firmware/nucleo/Makefile`, comentário acima de `SKETCHES`;
`scripts/conferir_docs_versionados.py`, `EXEMPLOS_EM_PROSA`.

---

# 2026-10-16 (ii) — `CI-06`: o push que não saiu, e o que a tentativa revelou sobre o Actions

**O problema, como foi entendido no início.** A entrada anterior fechou os três jobs com um risco
declarado: validados localmente, nenhum num runner. Com autorização para empurrar a branch, o
enunciado era simples — `git push origin chore/GIT-01-normalizar-fim-de-linha`, sem merge e sem
PR, para que o CI rodasse de verdade.

**Hipótese de trabalho.** Que o push fosse o último passo e que o resto do trabalho fosse ler o
resultado do Actions. Implícito nisso: que o ambiente que lê o repositório também pode escrever
nele.

**O que foi testado, e como.** Primeiro as conferências pré-push: `git remote -v`,
`git ls-remote --heads origin`, o cruzamento entre os arquivos pendentes e os arquivos que a
branch carrega, e varredura de segredos — por **nome** de arquivo e por **conteúdo**, nos 363
blobs distintos de todos os 48 commits de `develop..HEAD`, não só nos 6 desta sessão. Depois,
`git push --dry-run`.

**Resultado medido.** As conferências passaram, e o push **não saiu**:

```
fatal: could not read Username for 'https://github.com': No such device or address
```

Não há credencial de escrita no ambiente — nenhum `credential.helper`, nenhum
`~/.git-credentials`, nenhum `GH_TOKEN`, `gh` ausente. A leitura anônima do repositório público
funciona (foi assim que o `ls-remote` respondeu); a escrita não, e **não há como obtê-la daqui**
sem manipular credencial em texto claro, o que não se faz. A hipótese tácita estava errada: ler e
escrever o remoto não são a mesma permissão.

O que as conferências mediram, que fica registrado por ser verificação feita e não suposta:

| Conferência | Resultado |
|---|---|
| Remoto | `https://github.com/vitormendes4072/DormioSmart.git`, o esperado |
| A branch existe no remoto? | **Não.** Só `develop` (`f044fd2`) e `main` (`198b32e`), ambos idênticos aos refs locais — nada divergente, nada a reescrever |
| O gatilho cobre a branch? | Sim: `chore/**` está em `on.push.branches` desde `ba9f31a` (21/08) |
| As ações `@v6` resolvem? | Sim — `checkout`, `setup-python` e `setup-node` têm as tags v1…v7; o pin em v6 é de `a6c2315` (03/06), deliberado |
| Os 15 pendentes estão fora dos commits? | Sim. E a contagem exata é **13 de frontend + 1 de firmware + 1 JSON do ml**, não 15 de frontend — o número herdado de 30/09 estava mal atribuído |
| A branch carrega algum frontend? | Três arquivos, de `916e210` (UI-10, 29/09) — commit deliberado de outra sessão, **interseção vazia** com os 13 pendentes |
| Segredos | Nada. Nenhum `.env`/`secrets.h`/`.pem` versionado em commit nenhum; nenhum JWT (`eyJ…`), chave AWS, token do GitHub ou PEM. Os únicos achados de alto sinal são placeholders: `sb_secret_abc123` (fixture que testa a *recusa* de chave secreta), `SUPABASE_JWT_SECRET='...'` e `'o-segredo-do-projeto'` (documentação) |

**Adaptação — e é o achado que paga a tentativa frustrada.** Sem poder empurrar, fui ler o
histórico do Actions pela API pública, e ele desmonta uma premissa que esta sessão vinha
repetindo. **A última execução do CI é a #131, de 2026-09-10**, em `develop`, com sucesso. Não há
nenhuma depois. E o `ci.yml` que existia em `develop` naquela data tinha **dois** jobs:

```
jobs em develop (o que a #131 rodou):  test, frontend
jobs na branch hoje:                   test, rls, frontend, ml, firmware, documentos
```

Portanto **quatro dos seis jobs nunca rodaram num runner** — não três. O quarto é o `rls`, que
entrou em `d4011a1` (28/09), dezoito dias depois da última execução. A categoria "escrito, não
executado" sempre teve um item a mais do que o backlog contava, e o item a mais é justamente o
que carrega a afirmação de segurança do trabalho (`SEC-05`, isolamento entre usuários).

Com uma distinção que precisa ser feita com cuidado, porque é fácil exagerar na direção
alarmante: **os 125 testes de RLS não são código nunca executado.** A entrada de 28/09 registra
execução local contra Postgres de verdade, com verificação por mutação, e o código de
`web-app/tests/rls/` não mudou desde `3e38c9f` (106 funções de teste, 125 casos coletados com
parametrização). O que nunca aconteceu é outra coisa, mais estreita e ainda assim relevante:

1. O **job** `rls` nunca rodou — ou seja, a guarda contra pulo silencioso, que é o que impede o
   job de ficar verde sem verificar nada, nunca foi exercitada no lugar onde ela precisa
   funcionar. Os três cenários dela foram exercitados à mão em 28/09, o que é bom e não é o
   mesmo.
2. O **Postgres 16 nunca foi exercitado.** O harness foi desenvolvido e verificado na 14. A
   matriz `['14','16']` existe exatamente porque RLS e privilégio mudam entre majors — a 15
   mudou dono e privilégios do schema `public` — e a perna da 16 é, hoje, uma hipótese.

**Risco em aberto.**

- **O push continua pendente, e é bloqueio de ambiente, não de decisão.** Os 6 commits estão no
  clone local do Vitor e em nenhum outro lugar. Enquanto não saírem, o CI não roda e nada nesta
  entrada ou na anterior pode ser chamado de "o CI passa".
- **Nada do que a entrada anterior chamou de "validado localmente" mudou de status aqui.** Esta
  entrada não acrescentou uma única execução de job; acrescentou o conhecimento de que a dívida
  é maior do que se pensava.
- **A perna da Postgres 16 é a próxima coisa a olhar quando o push sair**, antes dos três jobs
  novos. Se a 16 reprovar, o achado é de segurança e vale mais que qualquer selo verde — e o
  `fail-fast: false` foi posto ali justamente para que esse diagnóstico apareça inteiro.
- **`DATA-03` segue aberto** e aparece de novo aqui por tabela: a `002_backfill_dono_dos_dados.sql`
  está mergeada desde agosto e não foi rodada no Supabase. É a mesma classe de coisa — escrito,
  mergeado, não executado — e é a terceira vez que ela aparece neste diário.

**Procedência.** `git push --dry-run` (saída citada acima); `git ls-remote --heads origin`;
API pública do GitHub, `/actions/runs` (`total_count: 131`, run `#131`,
`head_sha f044fd2`, `created_at 2026-09-10`, `conclusion success`);
`git show develop:.github/workflows/ci.yml` contra `.github/workflows/ci.yml`;
`.github/workflows/ci.yml`, job `rls` (matriz, serviço e a etapa "Conferir que os testes de RLS
não foram pulados"); entrada de 2026-09-28 (`SEC-05`) deste diário.

---

# 2026-10-17 — `DATA-07b`: as features em C++, e a paridade que finalmente tem dois lados

**O problema, como foi entendido no início.** O `DATA-07c` fechou deixando um registro
explícito: *"a paridade continua garantida de um lado só: enquanto o firmware não consumir o
JSON, o dourado é uma especificação que ninguém leu"*. O item era escrever o lado que lê — o
filtro Butterworth ida-e-volta em C++, a acumulação das seis features por época, e um alvo de
teste que prove a paridade contra o `vetor_dourado.json`.

**Hipótese de trabalho.** A referência `features_estilo_firmware` (em
`ml/testes/test_vetor_dourado.py`) já é laço escalar, sem numpy, escrita justamente para ser
transcrita. Então o trabalho seria transcrever, e o risco estaria concentrado no resíduo de
borda do filtro — a única divergência de estimador declarada.

**O que foi testado, e como.**

Quatro módulos novos, e três instrumentos sobre eles:

- `firmware/nucleo/filtro.{h,cpp}` — biquad Butterworth de 2ª ordem pela forma fechada
  (prewarp por tangente + bilinear, Q = 1/√2), duas passagens com estado inicializado em
  regime permanente. **Roda no lugar, sem vetor de rascunho:** na forma direta I as entradas
  passadas ficam em locais, não no vetor, então sobrescrever a própria posição é seguro — 3,8 KB
  por época a menos.
- `firmware/nucleo/caracteristicas.{h,cpp}` — as 6 features intra-época e `ĝ`, mais o ponto
  fixo de 16 bits (`VetorDeFeatures`, 18 B, com `static_assert` próprio).
- `firmware/nucleo/testes/leitor_json.{h,cpp}` — leitor *pull* mínimo, sem alocação e sem
  exceções, com autoteste de 24 verificações **incluindo os casos que ele deve recusar**.
- `firmware/nucleo/testes/testes_dourado.cpp` — o alvo de paridade. `make dourado`.
- `firmware/nucleo/testes/verificar_paridade_por_mutacao.sh` — quem testa o teste. `make mutacao`.

Execução: `make` (341 + 157 verificações), `make mutacao` (15 casos), `make sintaxe`
(4 sketches), `make capacidade`, e `pytest testes/` no `ml/` (107) mais
`verificar_vetor_dourado_por_mutacao.py` (12/12 + 1 cego).

**Resultado medido.**

A paridade fechou nos cinco casos, com folga em todas as seis réguas:

| régua | pior dos 5 casos | tolerância | uso |
|---|---:|---:|---:|
| ENMO (abs, g) | 2,433e−08 | 1e−07 | 24,3 % |
| `zcr` (abs) | 0,000e+00 | 0 | exato |
| `mag_din_media` (rel) | 0,570 % | 4 % | 14,3 % |
| `p_frac` (amostras) | 1,00 | 2,5 | 40,0 % |
| `ĝ` (componente) | 2,755e−04 | 5e−03 | 5,5 % |
| `ĝ` (ângulo, grau) | 0,0178 | 0,25 | 7,1 % |

**O resultado que importa mais que o "passou" é este:** medindo a divergência da *referência em
Python* contra o scipy nas mesmas 5 sementes, dá **`mag_din` 0,570 %, `p_frac` 1,00 amostra,
`ĝ` 0,0178 grau** — os mesmos números, dígito por dígito. Ou seja: para as três grandezas que
dependem do filtro, **o C++ não acrescenta divergência nenhuma**. Toda a divergência observada
é o resíduo de borda do `filtfilt` reflexivo contra o biquad causal ida-e-volta, que já estava
medido e declarado. O resíduo de borda, que era a parte incerta do item, se comportou
exatamente como o `DATA-07c` previu — e ficou **no fundo da faixa prevista** (p50 0,017 grau de
200 sementes), porque as 5 sementes do dourado são de movimento pequeno.

O ENMO é a exceção: o C++ diverge 2,43e−08 g onde o Python puro diverge 2,43e−17 g. São nove
ordens de grandeza, e a causa é uma decisão de projeto — a janela guarda as amostras em
`float32`, não em `double`. Isso consome **24 % do orçamento de paridade do ENMO** e economiza
11,5 KB. O número está medido e o teste o reporta a cada execução; quem quiser apertar a
tolerância do ENMO sabe o preço.

Verificação por mutação do lado C++: **11 de 11 sabotadores detectados**, 3 pontos cegos
declarados confirmados cegos.

**Adaptação.** Cinco coisas deram errado, e quatro mudaram o código.

**(a) `features.h` sequestrou o `<features.h>` da glibc, e nada compilava.** O primeiro nome do
módulo foi `features.h`. Com o `-I.` do Makefile, todo cabeçalho de sistema que faz
`#include <features.h>` — ou seja praticamente todos — passou a incluir o meu. O erro era
`missing binary operator before token "("` **dentro de `/usr/include/`**, apontando para a
biblioteca padrão, sem mencionar o arquivo culpado; e atingia até `filtro.cpp`, que não o
inclui. *Corrigido:* renomeado para `caracteristicas.h`, que além de não colidir segue o padrão
de nomes da casa (`epoca`, `cadencia`, `relogio`, `payload`) — seguir o padrão teria evitado o
problema de graça.

**(b) Os coeficientes em `float32` enviesavam o estimador, e o teste pegou.** O ganho em
corrente contínua de um passa-baixa tem de ser exatamente 1. Saiu **1,0000120**. A causa é
cancelamento catastrófico na própria expressão: `1 + a1 + a2 = 1 − 1,93060643 + 0,93293473 =
0,0023283`, uma soma que perde quase três ordens de grandeza, então 1e−7 de erro por
coeficiente vira 4,3e−5 no ganho. Em termos físicos: a gravidade estimada sai escalada por
1,000012, o que injeta 1,2e−5 g em `‖a − ĝ‖` de forma **sistemática** — viés de estimador, não
ruído, e portanto não se cancela no somatório. *Corrigido:* coeficientes em `double`, a custo
**zero** — o laço interno já acumulava em `double`, então eles eram `float` truncado promovido a
`double` em toda multiplicação, o pior dos dois mundos. O ganho DC passou a fechar em 1e−16 e
um sinal constante de 1 g atravessa o filtro com desvio **0,000e+00**. A tentação era afrouxar a
tolerância de 1e−5; o teste estava certo e o estimador estava errado.

**(c) Os coeficientes de referência que eu escrevi no teste estavam errados.** Foram escritos de
memória (`b0 ≈ 5,37e−4`, `a1 ≈ −1,93338`) e o valor real é `b0 = 5,8207613e−4`,
`a1 = −1,9306064`. Conferido contra `scipy.signal.butter` de verdade (scipy 1.15.3): a forma
fechada do módulo e o scipy concordam em **2,2e−19** nos cinco coeficientes. Fica registrado
porque é o modo de falha mais fácil de não notar — um valor de referência inventado faz o teste
reprovar código correto, e a reação natural é mexer no código.

**(d) A asserção `inclinacao_rel == 0` reprovou, e estava mais fina que a física.** O dourado
traz `inclinacao_rel = 8,53774e−07` no seed 4. Não é defeito do arquivo: é o piso de
condicionamento do `arccos`, que o lado Python já havia medido e registrado — com uma época só
`ĝ_ref` é o próprio `ĝ`, o produto interno é 1, e ali `dθ/dc = −1/√(1−c²)` explode, transformando
1 ulp em ~6e−7 grau. *Corrigido:* régua de 1e−5 grau, a **mesma** que
`test_angulo_entre_vetores_paralelos_nao_e_nan` usa do outro lado.

**(e) Meu próprio harness de mutação tinha contaminação entre rodadas.** A primeira versão
restaurava só `caracteristicas.cpp` entre sabotagens, deixando `filtro.cpp` sabotado da rodada
anterior. Resultado: a sabotagem "`ĝ` com viés de 1e−4" apareceu como **detectada**, e a
detecção era resíduo da sabotagem do corte do filtro. É o mesmo defeito que o `DATA-07c` achou
no instrumento do Python, com outra roupa — instrumento que mede a si mesmo errado. *Corrigido:*
árvore nova (`mktemp -d`) por sabotagem, e a exigência de que cada trecho case **exatamente uma
vez**, com erro alto quando não casa (um sabotador morto se lê como ponto cego).

**Decisão de projeto: as features ficaram FORA do `Epoca`.** O `Epoca` é o registro que o buffer
funde quando degrada resolução, e das sete grandezas deste módulo **quatro fundem exato e três
não**: `mag_din_media` (o `filtfilt` sobre 60 s não é a concatenação de dois de 30 s), `zcr` (os
cruzamentos são contados contra a média da própria janela) e `ĝ` (guardamos só a direção
unitária; a magnitude, que seria o peso da média ponderada, foi descartada). Embuti-las no
registro que funde criaria três números que a degradação corromperia em silêncio, dentro de
todas as faixas do contrato — exatamente o defeito que o `DATA-07` existe para evitar.

**Recálculo da autonomia, que é consequência da decisão acima.** `sizeof(Epoca)` continua 32 B e
o `static_assert` de `epoca.cpp` continua travado. O pareamento com `VetorDeFeatures` (18 B) dá
50 B, que alinham em **52 B** — contra os **40 B** do layout D do estudo do buffer. Os 10 B de
diferença são os 5 floats de pico que o layout D quantiza e esta mudança não tocou.

| registro | bytes | 32 KiB | 1,5 MiB |
|---|---:|---:|---:|
| A. hoje, sem features | 32 | 8,53 h | 409,6 h |
| D. estudo (picos quantizados) | 40 | 6,83 h | 327,7 h |
| **implementado** | **52** | **5,25 h** | **252,1 h** |

⚠️ **E a consequência não é só margem.** Com 32 B uma noite de 8 h cabia inteira em resolução
cheia, sem degradar uma vez. Com 52 B cobre 5,25 h, então numa noite sem rede a degradação
**passa a ser acionada** — cerca de 2,75 h precisam ser fundidas. E época degradada **não tem
features**, pelo motivo do parágrafo anterior: o início da noite chegaria ao servidor com
`total`/`status` e **sem** `f`. Não é perda silenciosa (a época viaja marcada `EPOCA_DEGRADADA` e
`f` é opcional no contrato), mas é perda de **cobertura de features** que o layout D reduziria.
É o argumento mais forte a favor de quantizar os picos, e está registrado como tal — não foi
feito junto porque mexe na precisão **transmitida** (`ax/ay/az/total`) e na checagem de coerência
da seção 5.1, e juntar as duas mudanças tornaria impossível dizer qual delas quebrou o quê.
**Dívida assumida, com o motivo: `DATA-07e`.**

⚠️ **E a saída de fundo já estava desenhada desde 29/09, sem nunca ter virado item.** O estudo
do buffer (`docs/DECISAO-BUFFER-E-FEATURES.md`, Saída 1, item 3 da ordem de implementação)
recomenda **flash como registro durável e RAM como cache de escrita**, com os números medidos:
**1,5 MiB** na partição de dados do esquema padrão (não os 4 MiB do chip — ~1,2 MB vão para OTA),
**39 321 épocas de 40 B = 327 h ≈ 13,7 dias** em resolução plena sem degradar uma vez; desgaste
de **3 741 anos** com nivelamento (374 com endurance pessimista), e energia entre **0,0026 % e
0,013 %** dos 23,9 mA do `CALC-01` Z.4.4 — contra 3,33 mA médios de **uma** transmissão por
época, isto é, mais de mil vezes menos. A recomendação estava no corpo de um documento e em
nenhuma lista de trabalho. **Virou `FW-08`.** Resolvido o `FW-08`, a degradação deixa de ser
acionada numa noite de 8 h e a pressão sobre o `DATA-07e` cai — mas os dois continuam valendo,
porque o `DATA-07e` também reduz o tráfego e o `FW-08` depende do `ARQ-01`.

**Achado de RAM que o estudo do buffer não tinha como prever.** `sizeof(AcumuladorDeFeatures)` =
**19 208 B (18,8 KiB)**, ou 59 % do orçamento de heap "conservador" de 32 KiB. O estudo
dimensionou o **armazenamento** das features e não tinha implementação para orçar o **cálculo**.
O custo é imposto pela matemática, não por conveniência: o filtro é de fase zero, a passagem de
volta lê a janela do fim para o começo, então a gravidade na amostra 0 depende da amostra 959 —
**não existe forma O(1) em streaming**. Qualquer acumulador incremental seria um filtro causal,
isto é, outro estimador, com divergência não declarada. A alternativa de guardar a janela em
`int16` (economia de 9,6 KB) foi recusada: injetaria quantização *dentro* do cálculo e moveria o
piso de paridade do ENMO de 1e−7 para a ordem de 1e−3 g.

**Dois pontos cegos do lado C++, um deles novo e estrutural.**

`C1` é o já conhecido: `p_frac` com `>=` em vez de `>`. Copiado por leitura da seção 2.6 do
contrato ("fração de amostras com ‖a − ĝ‖ **acima** do limiar"), com a nota no código apontando
para o registro. Não é teste, é procedência.

`C2` é **novo**: `ĝ` normalizado antes de promediar — média de direções em vez de direção da
média. O lado Python detecta (ele compara byte a byte com o arquivo, régua de igualdade exata);
o lado C++ não, e **não se resolve estendendo o dourado**. Medido:

| amplitude | piso de borda | sabotagem |
|---:|---:|---:|
| 0,02 g | 0,0213° | 0,0004° |
| 0,20 g | 0,1857° | 0,0400° |
| 0,40 g | 0,3683° | 0,1406° |
| 0,60 g | 0,5507° | 0,2793° |
| 1,20 g | 1,0963° | 0,8184° |

A sabotagem só cruzaria os 0,25 grau com amplitude ~0,6 g — e nessa amplitude o **piso legítimo
já vale 0,55 grau**, o dobro. Em toda a faixa o piso é ~2× a sabotagem, e os dois escalam juntos
porque são governados pela mesma grandeza: a variação de ‖ĝ_filtrado‖ ao longo da época. Então
acrescentar um caso de movimento grande ao dourado **pioraria** a situação — faria o piso
estourar a tolerância e reprovar firmware correto. A assimetria é inerente à fronteira: entre
duas implementações só existe régua de tolerância, e uma tolerância derivada de um piso físico
não pode ser mais fina que esse piso.

**Este é um limite quantificado e inerente, não uma pendência** — não há trabalho que o feche, e
retomá-lo como tarefa seria gastar esforço para piorar o instrumento. Registrado como tal em
`docs/BACKLOG-COMPLETO.md` (`PARID-C2`, marcado ⛔ e fora da contagem de itens abertos) e, por
ser material de defesa, em `docs/LIMITACOES-TCC.md` X.4, na forma do limite geral: **verificação
por paridade entre duas implementações independentes tem piso de detecção, e esse piso é
mensurável.**

**Nenhuma tolerância foi afrouxada.** As duas que se mexeram foram apertadas ou alinhadas com a
régua já existente do outro lado: o ganho DC foi de 1e−5 para 1e−12 (corrigindo o estimador), e
a das angulares passou de igualdade exata para os 1e−5 grau que o Python já usava.

**Risco em aberto.**

- **A cadência atual é 0,1 Hz, e as features precisam de 32 Hz na grade do dourado — com
  piso de amostragem de ≥ 42 Hz.** `INTERVALO_AMOSTRA_MS = 10000` no `envio-continuo.ino` dá
  **3 amostras por época**. O contrato mede 54 % de divergência em 8 amostras. Ou seja: **todo
  este item é código correto que o dispositivo ainda não tem insumo para alimentar**, e
  `fechar()` recusa a época em vez de emitir um vetor plausível e errado. Até o `FW-05` fixar a
  taxa, o caminho de features é inerte. Isso não estava escrito em lugar nenhum antes desta
  entrada.
  ⚠️ **E subir a taxa não é ajuste de parâmetro.** Os 42 Hz de Nyquist do filtro de 21 Hz
  atravessam os **40 Hz** do modo de baixo consumo do MPU6050 — desigualdade estrita já
  estabelecida no `CALC-01` Z.4.3 e na entrada de 10/09 deste diário —, o que obriga o modo
  normal a 500 µA (**4,5×** na corrente do transdutor) e **elimina a arquitetura de despertar
  por movimento**, porque o WoM exige baixo consumo e as épocas se sucedem sem janela ociosa em
  que dormir. A cadência, portanto, **escolhe entre o vetor de features e o Deep Sleep com
  WoM**. Virou item próprio: **`ARQ-01`**. As duas metades do problema existiam separadas desde
  setembro e nada as ligava.
- 🛑 **Consequência prática, e é a que custa caro se for ignorada: captar uma noite agora
  produz dado que o modelo não consome.** Cadência de 0,1 Hz + acumulador que recusa a época +
  `montar_payload` sem `f` = **noite registrada, zero features**. Não é perda silenciosa — a
  época viaja honesta, com `total`/`status`, e `f` é opcional no contrato — mas é uma noite que
  terá de ser recaptada. Registrado onde quem for captar lê: no aviso do `VAL-01` em
  `docs/BACKLOG-COMPLETO.md`, no caminho crítico do mesmo arquivo e no `ROADMAP.md`.
- **Nada disto rodou numa placa.** Os 18,8 KiB de janela, os ~29 000 MACs em `double` por época e
  o tempo de parede do fechamento são `sizeof` e aritmética no host. Os 8 pinos do MPU6050
  continuam sem solda.
- **Os itens (d) e (e) do `DATA-07b` continuam abertos:** a persistência no backend e a
  derivação das duas features angulares no servidor. Esta entrada fecha (a), (b) e (c).
- **O `C2` fica como ponto cego permanente deste alvo**, mitigado só por leitura do código e pelo
  fato de o lado Python continuar detectando.
- **O payload não emite `f`.** `montar_payload` não ganhou os campos `f`, `g` e `fs`: o contrato
  os declara opcionais e a emissão depende da decisão de época truncada, que esta entrada
  resolve no acumulador mas não no payload. O contrato v2.5.1 continua "declarado, não
  implementado" do lado do transporte.

**Procedência.** `firmware/nucleo/filtro.{h,cpp}`, `caracteristicas.{h,cpp}`,
`testes/leitor_json.{h,cpp}`, `testes/testes_dourado.cpp`,
`testes/verificar_paridade_por_mutacao.sh`, `Makefile` (alvos `dourado` e `mutacao`);
`capacidade.cpp` (seções "AUTONOMIA COM AS FEATURES" e "CUSTO DE RAM DO ACUMULADOR");
`ml/testes/vetor_dourado.json` (tolerâncias lidas do arquivo, não copiadas);
`ml/testes/test_vetor_dourado.py` (`features_estilo_firmware`, bloco de tolerâncias);
`docs/DATA-CONTRACT.md` seção 2.6; `docs/DECISAO-BUFFER-E-FEATURES.md` ("O registro: 40 bytes").

---

# 2026-10-17 (ii) — `DOC-10`/`GIT-05`: auditoria de registro, e o eixo que faltava

**O problema, como foi entendido no início.** Auditar se cinco achados já conhecidos estavam
registrados de forma **acionável** — não se estavam escritos, mas se alguém sem contexto os
encontraria e saberia o que fazer. Os cinco: o caminho de features inerte, a consequência disso
para a captação, a autonomia de 5,25 h com a saída em flash já desenhada, o ponto cego
permanente da paridade, e a dívida de não quantizar os picos.

**Hipótese de trabalho.** O trabalho seria de conferência, e o grosso já estaria registrado — a
entrada de 17/10 (i) é longa e cobre os cinco. Esperava-se achar uma ou duas lacunas de
formulação.

**O que foi testado, e como.** Leitura dos três arquivos de registro (`DIARIO`,
`BACKLOG-COMPLETO`, `LIMITACOES-TCC`) contra `DECISAO-BUFFER-E-FEATURES.md` e
`CALCULOS-TCC.md`, mais `grep` por cada termo-chave em `docs/`.

**Resultado medido.** **Quatro dos cinco estavam no diário e nenhum dos cinco estava acionável
no backlog**, que é a lista que alguém abre para decidir o que fazer. O mais objetivo:

> `grep -rniE 'flash|LittleFS' docs/BACKLOG-COMPLETO.md docs/DIARIO-DE-ENGENHARIA.md` → **vazio.**

O estudo do buffer dimensionou flash em 29/09 — 1,5 MiB, 13,7 dias, desgaste de 3 741 anos,
energia em centésimos de por cento — e a recomendação viveu **18 dias** no corpo de um documento
sem nunca virar item. O `FW-05` pedia "≥ 42 Hz" como requisito simples, sem dizer que atravessar
os 40 Hz custa uma arquitetura. O `VAL-01` convidava a captar uma noite sem avisar que ela
sairia sem feature nenhuma. O `DATA-07c` dizia "1 ponto cego registrado", e era o do lado
Python, não o `C2`.

**Adaptação.** Cinco itens novos (`ARQ-01`, `FW-08`, `DATA-07e`, `PARID-C2` — este ⛔, fora da
contagem — e `GIT-05`), o aviso de captação em quatro lugares, e o limite de paridade escrito
como material de defesa em `LIMITACOES-TCC.md` X.4.

**E um achado que não estava sendo procurado, que é o próprio objeto do item `GIT-05`.** Ao
escrever o aviso de captação no `ROADMAP.md`, `git status` não o acusou: **o `ROADMAP.md` está
no `.gitignore`.** Um aviso ali não chega a um clone. A varredura completa — todo arquivo
rastreado contra `git check-ignore` — achou **oito** arquivos ignorados que arquivos rastreados
mandam ler, e o `ROADMAP.md` é citado por **8 deles**, inclusive `frontend/src/lib/metricas.ts`.
O aviso foi para o `README.md`, que é versionado.

O `CI-05` **não acusa isso, e não por defeito**: sua verificação (2) trata *ignorado como
decisão, não esquecimento*, e a distinção está certa. O que faltava é que ignorar é decisão
sobre **distribuição** e não diz nada sobre o **ponteiro** que ficou no texto. Entrou a
verificação **(3)** em `scripts/conferir_docs_versionados.py`, validada por controle positivo
nas duas direções (ponteiro novo → reprova; árvore limpa → OK, inclusive com `CI=true`).
⚠️ **Ela nasceu com os oito dentro da isenção `PONTEIROS_ACEITOS`, cada um com motivo escrito e
impresso a cada execução** — então **hoje não cobre nenhum dos oito; pega o nono.** Está dito
assim no script, no `ci.yml` e no backlog, porque uma verificação que estreia com todas as
violações atuais isentas é exatamente §1 de novo se não se disser isso.

**O documento que saiu da auditoria.** O padrão de todos os cinco achados é o mesmo, e já tinha
nome: análise correta que não chega onde a decisão é tomada. Daí `docs/LICOES-APRENDIDAS.md`
(`DOC-10`) — o mesmo material deste diário pelo outro eixo, **por padrão de falha**. Oito
padrões, regra de entrada explícita (duas ocorrências reais, ou uma com custo medido), cada um
com prevenção em forma verificável, e um checklist de sete perguntas. O diário responde *o que
aconteceu*; o novo responde *já pisamos nessa pedra?*, que é a pergunta que se faz antes.

**Risco em aberto.**

- **Nada do que esta entrada registra foi executado.** `ARQ-01` depende de medição em placa,
  `FW-08` e `DATA-07e` dependem dele. O repositório passou a descrever corretamente um problema
  que continua inteiro.
- **A (3) é catraca, não cobertura**, e o trabalho do `GIT-05` é reduzir os oito — arquivo por
  arquivo, versionando ou parando de citar. Só o `HISTORICO.md` é ponteiro legítimo: o diário o
  cita justamente para dizer que ele não serve de procedência.
- ✏️ **Uma afirmação minha desta sessão saiu sem conferência e foi corrigida no mesmo dia:** eu
  escrevi que o `README.md` "manda ler" `METODOLOGIA.md`, `HARDWARE.md` e `DATASET.md`;
  conferido, ele os lista **pelo nome, sem caminho**, na árvore de "Estrutura". O efeito sobre
  quem clona é o mesmo, a afirmação não era. É §3 do próprio documento novo, cometido enquanto
  ele era escrito, e fica registrado por isso.
- **O `CI-06` continua valendo:** nenhum destes jobs rodou em runner, e agora são quatro mais
  uma verificação nova.

**Procedência.** `docs/LICOES-APRENDIDAS.md`; `docs/BACKLOG-COMPLETO.md` (`ARQ-01`, `FW-08`,
`DATA-07e`, `PARID-C2`, `GIT-05`, `DOC-10`); `docs/LIMITACOES-TCC.md` X.4 e a nota "O que entrou
em 2026-10-17"; `scripts/conferir_docs_versionados.py` (cabeçalho, `PONTEIROS_ACEITOS`,
`conferir_ponteiros`); `.github/workflows/ci.yml`, job `documentos`; `README.md`, seção
"Status".

---

# 2026-10-17 (iii) — os 15 arquivos pendentes, lidos: a tela que não existia e a premissa que não se sustentava

**O problema, como foi entendido no início.** Havia 15 arquivos modificados e não commitados em
disco desde 29/09 — 13 de frontend (`DASH-12`/`DASH-13` e adjacências), 1 de firmware e 1 JSON
do `ml/`. Todas as sessões seguintes foram instruídas a não tocá-los, e este diário e o
`docs/LICOES-APRENDIDAS.md` registram, nas respectivas seções de lacuna, que eles **não foram
lidos**. O enunciado era: ler o diff inteiro, decidir o que completar e o que descartar, e não
commitar trabalho alheio no escuro só para limpar a árvore. Em seguida, o `UI-11`.

**Hipótese de trabalho.** Duas, e as duas eram razoáveis. A primeira: que fosse trabalho pela
metade, de valor incerto, possivelmente em conflito com o que veio depois (contrato v2.5.1,
migrações `006` e `007`, as features em C++ do `DATA-07b`) — daí a instrução de preferir relatar
a commitar. A segunda, implícita no backlog: que o `UI-11` fosse barato *porque* a policy de
`update` em `profiles` já existia desde a migração `001`, faltando só a interface.

**O que foi testado, e como.** O diff inteiro, lido arquivo por arquivo, não por estatística.
Depois, para cada afirmação que o diff fazia sobre o resto do repositório, a conferência no
artefato: `grep` por `captured_at` em `web-app/`, por `profiles` em todo código de produção, por
`\bidade\b`, e busca de uso de cada símbolo novo e de cada símbolo que ele substituía. `cmp`
byte a byte do JSON contra `git show HEAD:`. `tsc --noEmit`, `vitest run` e `vite build` em cada
estado intermediário, antes de cada um dos quatro commits. `make sintaxe` no firmware.

**Resultado medido. O diff não era trabalho pela metade — era a metade que faltava de trabalho
que o projeto dava por concluído.**

| Achado | O que a conferência mostrou |
|---|---|
| **`DASH-12` e `DASH-13` estavam feitos só do lado do servidor.** | O backend está commitado e testado desde 10/09 (`captured_at` no `select` de `database.py`, `LIMITE_PADRAO = 20` e `LIMITE_MAXIMO = 2000` em `consulta.py`, cobertura em `test_leitura_por_dispositivo.py`). O cliente, não. Na árvore versionada, `LeituraSono` não tinha `captured_at`, `instanteDaLeitura` não existia, e nem o painel nem a exportação mandavam `limite`. **O `ROADMAP.md` declara os dois "✅ corrigido em 2026-09-10", com descrição detalhada do que mudou.** O painel versionado descrevia 20 linhas — dez minutos de celular — pela hora de chegada. |
| **A tela de exclusão de conta estava inalcançável.** | `ExcluirConta.tsx` foi commitado em 29/09 (`916e210`) com 23 testes, e **nenhum arquivo versionado o importava.** As três linhas que o montam em `Settings.tsx` estavam entre os 15 pendentes, presas porque os *hunks* não se separavam do `DASH-13`. |
| **Três documentos afirmavam que aquela tela existia.** | O backlog (`UI-10 ✅`), o `docs/LGPD-ELIMINACAO.md` ("a interface existe desde 29/09") e a `docs/POLITICA-DE-PRIVACIDADE.md` §6.4, que **dizia ao titular onde clicar** para exercer o art. 18, VI. |
| **Havia trabalho do `DASH-08` que ninguém mencionou.** | `descreverDispositivo`, `descreverRecorte`, `tiposPresentes` e `serieMisturaTipos`. O `ROADMAP.md` lista o `DASH-08` como feito em 10/09 porque `MeusDispositivos` mostra o tipo na lista de aparelhos; o painel não mostrava. |
| **`serieMisturaTipos` era decisão escrita e não aplicada.** | Documentada, com três testes, e **ligada em lugar nenhum**: o `AvisoDeMistura` reescrevia a condição inline e o `Dashboard` decidia tudo por `serieMisturaInstrumentos`. |
| **A premissa do `UI-11` não se sustentava.** | **Nenhum código de produção toca `public.profiles`** — as únicas referências do repositório estão em `web-app/tests/rls/`. O nome que a tela exibe vem de `auth.users.raw_user_meta_data`; `profiles.nome` é cópia tirada uma vez pelo trigger `handle_new_user` (migração `001`, linha 125) e lida por nada. Não há rota de perfil no backend. |
| **O 15º arquivo não era uma mudança.** | O JSON do `ml03b` tem 7 346 CR no disco e o histórico o guarda em LF; com o `text=auto` desta branch, o conteúdo normalizado é **idêntico** ao de `HEAD`. O que estava desatualizado era a **entrada de índice**, não o arquivo. Um `git add` a refrescou e ele saiu do `status` sozinho, sem entrar em commit nenhum, mantendo os CRLF no disco. |

Dos "15 arquivos pendentes" citados aqui e nas lições desde 29/09, portanto, **14 eram trabalho
e 1 era contabilidade do índice.** A contagem estava certa; a leitura dela, não.

**Adaptação.** A hipótese de que seria trabalho duvidoso caiu na primeira leitura: o conteúdo
estava correto, coerente com o que veio depois, e com os comentários mais cuidadosos do
frontend. O que estava errado era o **registro de projeto**, não o código — e isso inverteu o
risco do enunciado. Não commitar deixaria de ser prudência e passaria a ser manter três
documentos mentindo sobre um direito do titular.

Quatro commits, separados por item e com os *hunks* desembaraçados à mão (`Dashboard.tsx` e
`Settings.tsx` carregavam pedaços de três itens cada): `a586b0b` (`DASH-12`/`DASH-13`),
`fea1c48` (`DASH-08`), `22a9268` (montagem do `UI-10` e correção de duas das três afirmações) e
`f58f52c` (`FW-06`). Em seguida `c80c2b8` (as duas ocorrências novas nas lições e a terceira
afirmação falsa), `216fda7` (backlog) e o do `UI-11`.

Três decisões que mudaram o trabalho original, cada uma declarada no commit:

1. **`serieMisturaTipos` foi ligada, mas não como porta de entrada do aviso.** Quem decide se o
   aviso *aparece* continua sendo `serieMisturaInstrumentos` (há mais de um aparelho); quem
   decide se ele *nomeia as classes* passou a ser `serieMisturaTipos` (há mais de uma classe).
   Trocar um pelo outro faria o aviso desaparecer com dois travesseiros, que é comportamento com
   teste próprio afirmando-o. Apareceu na leitura uma assimetria que vale registrar: a
   justificativa escrita de `serieMisturaInstrumentos` fala de *"um travesseiro e um celular"*,
   mas a implementação é só `dispositivos.length > 1` — o alcance do código é mais largo que o
   do comentário.
2. **O `UI-11` foi feito pelo Supabase Auth, não por `profiles`.** Implementado conforme a
   especificação, ele teria entregado uma tela em que a pessoa clica "salvar", recebe "dados
   atualizados", e o nome continua o mesmo.
3. **`profiles` não foi sincronizada de passagem.** Virou o `PERFIL-01`, com três saídas e o
   custo de cada uma. O motivo é o mesmo que o `DATA-07e` registrou para não quantizar os picos
   junto: duas mudanças de uma vez tornam impossível dizer qual quebrou o quê.

E uma verificação nova, `frontend/src/alcance.test.ts`, que é a correção de fundo do achado do
`UI-10`: percorre os `import` relativos a partir de `main.tsx` e reprova quando um módulo de
`src/` fica fora do grafo. **Nada no repositório podia pegar aquele defeito** — `tsc` não
reclama de módulo não importado, o `vite build` poda o que não entra no grafo e segue verde, e
os 23 testes do item são de `lib/`, então passavam com o componente desmontado.

**O que o método pegou, e que a leitura não pegaria.** Três coisas, as três porque alguma
verificação foi feita em vez de assumida:

- A **primeira tentativa de sabotar** o `perfil.ts` não casou (indentação errada no padrão de
  busca) e a suíte passou — o que eu teria lido como "ponto cego detectado". É o §4 das lições
  em miniatura, *"um sabotador morto se lê como ponto cego"*, e o mesmo defeito que o harness de
  mutação do C++ teve nesta mesma data, pela manhã. Daí a conferência de que cada trecho
  sabotado casa **exatamente uma vez** ter entrado no procedimento antes de qualquer conclusão.
  Refeito: de 4 sabotagens, 3 detectadas e 1 **provadamente equivalente** (trocava
  `nomeAlterado` por `true` num retorno alcançável só quando o nome mudou, onde ele já vale
  `true`) — mutante equivalente, não cego.
- Eu **reportei duas afirmações falsas e eram três.** Procurei no `docs/LGPD-ELIMINACAO.md` a
  tabela de citações da Lei, cuja coluna é *"Confere?"* — ela afirma que a **citação** do artigo
  está correta, não que o direito esteja implementado —, concluí que o arquivo estava certo e
  segui. A afirmação falsa estava trinta linhas abaixo, na lista de notas: *"✅ A interface
  existe desde 29/09"*. **Conferi o lugar errado do arquivo certo**, que é o §5 aplicado a mim
  mesmo. Detalhe que vale guardar: logo abaixo dela estava a linha *"Falta a parte de interface:
  hoje a eliminação existe como rota, e só"*, marcada como obsoleta e mantida "para o histórico
  ficar legível" — **a linha dita obsoleta estava mais certa que a que a substituiu**, por
  dezoito dias.
- **Eu corrompi este arquivo e o `git status` foi quem disse.** Ao inserir esta entrada, o
  heredoc que escrevia o texto num arquivo temporário falhou por permissão (`/tmp` deste
  ambiente tem arquivo de outro dono), o script seguinte leu um `/tmp/entrada.md`
  **pré-existente e alheio**, e 208 linhas de conteúdo não relacionado entraram no diário —
  duplicando a entrada de `DATA-07b`. Apareceu em `git diff --numstat` como `208 0`, que é um
  número impossível para uma inserção de entrada única. Revertido por
  `git show HEAD:… > …` (o `git checkout --` não consegue, porque não pode desvincular arquivo
  no diretório montado) e reescrito com ferramenta de arquivo. **A lição é de método e não de
  conteúdo:** script que lê arquivo temporário precisa falhar quando o arquivo não é o que ele
  acabou de escrever — `set -euo pipefail` no heredoc teria interrompido antes, e conferir o
  `numstat` antes de commitar foi o que pegou.

**Risco em aberto.**

- **O ponto cego do `UI-11` é declarado e não está fechado.** O dublê de `updateUser` exercita a
  orquestração do módulo — ordem das chamadas, propagação de `nomeAlterado`, leitura pessimista
  da resposta —, e **não prova nada sobre o comportamento real do Supabase**: não prova que a
  troca de e-mail exige confirmação, nem quantos e-mails ela dispara. A diferença em relação ao
  §4 (a suíte de RLS contra Supabase mockado) é o que está sendo afirmado: ali o trabalho
  afirmava isolamento entre usuários e a prova era um mock; aqui o que está sob teste é a
  decisão do próprio arquivo sobre o que fazer com cada forma de resposta. Fecha com um projeto
  Supabase de teste e uma troca ponta a ponta — registrado no `UI-11`.
- **O `alcance.test.ts` é catraca, não cobertura.** Prova que existe caminho de `import`;
  **não** prova que o componente é renderizado, nem que há rota que leve a ele. Componente
  importado e nunca usado no JSX passa. A outra metade é o `UI-17`, e exige
  `@testing-library/react`.
- **Nada disto rodou em runner.** Vale o `CI-06`: agora são quatro jobs mais duas verificações
  sem execução em runner, e a branch continua sem push — sem credencial de escrita no ambiente.
- **`profiles` ficou com duas naturezas e nenhuma decidida.** As colunas são mortas, mas a
  tabela **não é inerte**: carrega a policy de `delete`, o `delete from public.profiles` de
  `apagar_minha_conta()`, o campo `perfil_apagado` do recibo, a frase "o perfil" que o `UI-10`
  mostra ao titular, e parte dos 105 testes de RLS. Enquanto o `PERFIL-01` não decidir,
  `profiles.nome` é cópia que pode divergir do nome real. Carrega o item; não é observação
  solta.
- **O `ROADMAP.md` continua declarando `DASH-12`, `DASH-13` e `DASH-08` como feitos em 10/09.**
  Agora a afirmação é verdadeira, mas a data não: a do cliente é 17/10. O arquivo não é
  versionado (`GIT-05`), então a correção dele não entra em commit — e é justamente por não ser
  versionado que ele pôde carregar um `✅` errado por seis semanas sem que nenhuma verificação o
  alcançasse.
- **O `.git/_lixo_sandbox/` cresceu de novo.** Cada comando que escreve no índice deixa um
  `index.lock` ou `HEAD.lock` que o sandbox não consegue remover, e o lock órfão quebra o
  comando seguinte — foi preciso limpá-los antes de cada `git add` e cada `git commit`. Ainda é
  o `GIT-03`, ainda ⚪, ainda precisa de um terminal na máquina. Observação de método que custou
  duas tentativas: **`GIT_OPTIONAL_LOCKS=0` faz `git add` não gravar nada em silêncio** — serve
  para leitura, e usá-lo em escrita produz um `git commit` que responde "no changes added to
  commit".

**Procedência.** Commits `a586b0b`, `fea1c48`, `22a9268`, `f58f52c`, `c80c2b8`, `216fda7` e o do
`UI-11`; `frontend/src/lib/perfil.ts` (cabeçalho), `frontend/src/alcance.test.ts` (cabeçalho e
isenções), `frontend/src/lib/perfil.test.ts` (ponto cego declarado); `docs/BACKLOG-COMPLETO.md`
(`UI-11`, `PERFIL-01`, `UI-16`, `UI-17`, `LGPD-04`, item 6 do "Estado do projeto", procedência
de execução); `docs/LICOES-APRENDIDAS.md` §5 ocorrência 4 e §6 ocorrência 4;
`docs/LGPD-ELIMINACAO.md` e `docs/POLITICA-DE-PRIVACIDADE.md` §6.4, notas de correção de 17/10;
`web-app/migrations/001_multiusuario.sql` linha 125 e `006_direito_de_eliminacao.sql` linhas 151
e 169.

---

---

# 2026-10-17 (iv) — `profiles` vira fonte de verdade, e a suíte de segurança provou cobrir menos do que anunciava

**O problema, como foi entendido no início.** O `PERFIL-01` tinha três saídas escritas e
custo medido para cada uma, e a decisão foi tomada: **tornar `public.profiles` a fonte de
verdade do perfil, e usar a coluna `idade`** em vez de removê-la. O enunciado chamou isso
de "saída (B)"; no backlog, a saída que torna `profiles` canônica é a **(A)** — a (B) é a
oposta, e nela `idade` sairia por migração. Seguiu-se a descrição em prosa, que é
inequívoca e cujas duas metades só são consistentes entre si na (A). Registrado no
backlog e em `docs/DECISAO-FONTE-DO-PERFIL.md` §0, porque "saída (B)" vai aparecer de novo
numa releitura e não pode significar duas coisas.

**Hipótese de trabalho.** Duas, e as duas eram razoáveis. A primeira, vinda do próprio
item: que o maior custo da saída fosse o segundo modo de falha — *"gravou no Auth, falhou
em `profiles`, e agora os dois divergem e nada diz qual vale"* —, de modo que o trabalho
difícil seria escolher uma regra de sincronização. A segunda, implícita: que a suíte de
RLS, com 125 testes e 25 sabotagens detectadas, já cobrisse `profiles` o suficiente, e que
o trabalho de teste fosse só acrescentar o caminho novo.

**O que foi testado, e como.** Antes de escrever código: o diff do que existia, lido
arquivo por arquivo, e `grep` por `user_metadata`, por `profiles` e por `idade` em todo
código de produção. A pasta `migrations/` aberta inteira, incluindo o que não é migração —
e foi aí que o `DIAGNOSTICO-perfil-nao-criado.sql` apareceu, que é o arquivo que mudou o
desenho. Depois: 46 testes de rota com dublê, 21 de RLS contra **Postgres real**, 32 de
frontend, `tsc --noEmit`, `vite build`, o verificador por mutação do RLS a cada mudança de
esquema, e `conferir_docs_versionados.py`. Oito controles positivos, cada um nomeando o
teste que deveria cair.

**Resultado medido. A duplicidade não precisava de regra de sincronização — precisava
deixar de existir. E a suíte de segurança cobria menos do que o nome dos testes dizia.**

| Achado | O que a conferência mostrou |
|---|---|
| **O modo de falha previsto pelo item é eliminável por desenho.** | Divergência entre duas cópias só é **ambiguidade** quando as duas são **lidas**. Com leitor único (`profiles`) e destino único por campo (nome e idade pela rota; e-mail pelo Auth, porque é credencial), nenhum campo tem dois destinos — e `nome` não pode divergir de si mesmo. Não há tie-break porque não há empate. O que sobra do metadado não é um segundo valor em disputa: é **resíduo**, e resíduo é problema de LGPD (art. 18, III e art. 6º, III), não de corretude. |
| **`profiles` pode não ter linha para um usuário que existe.** | `migrations/DIAGNOSTICO-perfil-nao-criado.sql` existe porque **já aconteceu**: o gatilho `handle_new_user` não existia no projeto, e o arquivo tem um reparo manual embaixo de *"ZERO LINHAS AQUI = causa confirmada"*. Enquanto a tabela era inerte isso era detalhe de esquema. Com ela canônica, linha ausente passa a ser **nome em branco na tela de quem digitou o nome no cadastro**. |
| **`create function` concede `EXECUTE` a `PUBLIC` por padrão no PostgreSQL.** | A migração `008`, ao criar `tocar_updated_at()`, **ampliava** o que o papel `dormio_ingestao` pode executar — o papel que a `005` existe para manter com `EXECUTE` em exatamente três funções e nenhum privilégio de tabela. Quem acusou foi `test_o_papel_executa_exatamente_tres_funcoes`, na primeira execução da migração, nomeando a função nova. É o teste cujo docstring diz *"enumera o que ele PODE, para que ampliar apareça no diff"*. |
| **`test_ana_nao_cria_profile_para_o_bruno` barrava pela chave estrangeira, não pela policy.** | Ele inseria com um uuid **inventado** (`cccccccc-…`), para não colidir com a chave primária da linha que o gatilho cria. Uuid inventado não existe em `auth.users`: o comando morria em `profiles_id_fkey` e **nunca chegava ao RLS**. Medido: com `profiles_insert_own` escancarada (`with check (true)`), **ele continua passando** — só os dois testes estruturais caem. |
| **Dois barramentos em série escondem um ao outro.** | O `upsert` que a rota emite, contra uma vítima que **já tem** linha, cai no ramo de `update`: quem recusa é a policy de `update`, e a de `insert` escancarada passa despercebida. Um teste chamado "a Ana não faz upsert no perfil do Bruno" anuncia cobertura das duas e cobre uma. |
| **Policy de `UPDATE` sem `with check` não é mais frouxa no PostgreSQL.** | Sem `with check`, o `using` é usado **também** como verificação da linha resultante. Removê-lo não abre a transferência de linha para outro dono, e **nenhum teste de acesso pode cair** — quem detecta é o teste estrutural. Era premissa minha, não conferida, e o verificador por mutação a derrubou. |
| **Três documentos afirmavam estado que o artefato contradiz, e um deles mudava comportamento.** | A §6.3 da política dizia *"não há tela para alterar nome e e-mail"* enquanto a tela do `UI-11` existia desde a manhã — o commit `2316b06` não tocou a política. O `DIAG-04` era o **quarto** documento com a afirmação desatualizada sobre a tela do `UI-10` (a entrada (iii) reporta três). E o `CLAUDE.md` dizia *"ainda não há suíte de testes nem CI"* e *"health check ainda não existe"*, as duas falsas havia semanas. |

**Adaptação.** Três, e cada uma mudou o desenho em vez de só o código:

1. **O `GET /api/me/perfil` escreve.** Quando falta a linha, ele a cria, semeada pelo nome
   do metadado — a mesma semeadura que o gatilho faz, no único momento em que ela ainda faz
   sentido. A alternativa (a tela cair para o metadado quando falta a linha) foi recusada:
   criaria o segundo leitor de volta, **sob condição**, e invariante com cláusula de exceção
   é o que apodrece primeiro. `GET` com efeito colateral é ruim; `GET` **idempotente** com
   efeito colateral é aceitável, e está dito no docstring da rota, porque um `GET` que
   escreve sem avisar é armadilha para quem ler depois.
2. **A limpeza do resíduo acontece no navegador, e não pode transformar a correção em
   erro.** `updateUser` age sobre a **sessão** de quem chama, e o cliente do Flask só
   autentica o PostgREST — fazer isso no servidor exigiria a API de administração, isto é,
   papel privilegiado, recusado pelo `SEC-06`. Então ela vai no cliente, **depois** de o
   `PATCH` ter sucedido, e `residuoLimpo` é campo próprio do resultado: o que foi verificado
   é afirmado, o que não foi não é. Dois testes afirmam que falha e exceção na limpeza
   deixam o desfecho em "salvo", porque a correção **aconteceu**.
3. **A finalidade da `idade` teve de ser implementada, não só declarada.** "Cadastral" seria
   a finalidade mais fácil de escrever e a menos defensável: um dado coletado para existir
   no cadastro não sobrevive ao art. 6º, III, e é literalmente o que o `LGPD-04` descrevia.
   "Estratifica a análise do sono" soaria melhor e seria **finalidade declarada que o código
   não cumpre** — o §6 na forma mais barata de cometê-lo, porque um parágrafo de política de
   privacidade não tem como ficar vermelho. A finalidade escolhida é a que dá para cumprir
   hoje: dizer ao titular se a idade dele está na faixa das coortes de validação que o
   trabalho cita (`frontend/src/lib/aplicabilidade.ts`). Ela **não entra em cálculo nenhum**,
   e isso está dito na política, no `comment on column` da migração e no cabeçalho do módulo
   — nos três lugares de propósito.

Quatro commits: `778ec27` (backend, migração, testes de rota e de RLS, documento de
decisão), `ad3114a` (frontend), `fb2f18f` (política, `LGPD-ELIMINACAO`, `DIAG-04`) e o deste
registro.

**O que o método pegou, e que a leitura não pegaria.** Quatro coisas, as quatro porque
alguma verificação foi feita em vez de assumida:

- **O `exige` do sabotador novo apontava para um teste que não podia detectá-lo.** Preenchido
  por leitura, parecia certo. O verificador reprovou dizendo que a sabotagem foi detectada
  **por outros** testes — que é o campo existindo *"para que a suíte não acuse por
  acidente"*, funcionando contra quem o escreveu. Foi esse `REGRESSAO: 2 de 30` que levou aos
  achados 4, 5 e 6 da tabela acima. Sem o campo, as duas sabotagens apareceriam como
  "detectadas" e os três defeitos continuariam lá.
- **O `conferir_docs_versionados.py` reprovou por minha causa.** Escrevi
  o caminho do `DIAG-04` abreviado com reticências no meio do nome do arquivo, no documento
  de decisão: a verificação (2) lê isso como citação de arquivo que um clone não traz, e sai
  != 0. **E eu repeti o mesmo erro ao escrever este parágrafo**, abreviando o caminho de novo
  para descrevê-lo — o script reprovou a segunda vez também, e por isso esta frase não traz o
  caminho abreviado. Pequeno, e é a verificação (2) fazendo exatamente o que ela existe para
  fazer, duas vezes em dez minutos, contra a mesma pessoa.
- **O `ID` do item novo colidia com um item fechado.** Criei `ML-07` para a finalidade futura
  da idade; já existe `ML-07` ✅ ("infraestrutura de execução retomável"), e `ML-08` também
  está tomado. Renomeado para `LGPD-06` em todos os lugares que já o citavam — backlog,
  documento de decisão, migração e cabeçalho do módulo. Achado por `grep` de conferência
  depois de escrever, não por lembrança.
- **A suposição sobre `contar_afetadas` estava errada, e o banco disse qual.** O teste de "a
  Ana não muda o próprio `id` para o do Bruno" foi escrito esperando **zero linhas
  afetadas**, por analogia com os outros testes de negativa de `profiles`. Reprovou com
  *"new row violates row-level security policy"*. A diferença é qual metade da policy barra:
  `using` que esconde a linha afeta zero em silêncio; `with check` que reprova a linha
  **resultante** levanta exceção. A asserção foi corrigida para o que o banco faz, e o
  porquê ficou no docstring.

**Risco em aberto.**

- **A migração `008` não foi aplicada.** Virou `PERFIL-02`, L3, com as quatro verificações do
  rodapé — inclusive a terceira, que testa o **gatilho** e não a existência dele. A rota
  funciona sem ela; o que falta é `profiles.updated_at` parar de mentir sobre linhas
  corrigidas hoje, e o teto de tamanho do nome para o caminho que **não passa pelo Flask**
  (`authenticated` tem `GRANT` de `UPDATE` em `profiles`, e o navegador fala direto com o
  PostgREST pela chave `anon`, que é pública por design). **Enquanto ela não rodar, nada no
  repositório pode afirmar que o esquema de produção é o que o `DIAG-04` desenha.**
- **Nada prova que o `<PerfilProvider>` está montado.** Medido por controle positivo:
  removido o provider do `main.tsx`, o `alcance.test.ts` **passa** — o módulo continua no
  grafo pelos imports de `Sidebar` e `EditarPerfil`. É a metade que falta do `UI-17`, e é a
  mesma classe de defeito que deixou o `UI-10` inalcançável por dezoito dias. Mitigado, não
  resolvido: `usePerfil` **levanta** em vez de devolver valor neutro, de modo que a ausência
  quebre a primeira renderização de forma ruidosa em vez de subir o aplicativo mostrando
  nome em branco para quem tem nome — §7, o desfecho pior dos dois.
- **O ponto cego do `UI-11` continua aberto, e agora carrega uma afirmação a mais.** Os
  dublês exercitam a orquestração do nosso código, não o Supabase: **não está provado que
  `updateUser({data:{nome:null}})` apaga a chave** em projeto real. Se não apagar, o resíduo
  fica — e o que o código garante é só que isso não contamina o relato da correção. Fecha com
  o mesmo projeto Supabase de teste.
- **O campo de idade e o aviso de aplicabilidade não têm teste de renderização.** A lógica
  inteira está em `lib/`, com teste, exatamente porque o `vitest` roda em ambiente `node` e
  não há testing-library (`UI-17`). Ninguém, nem teste nem pessoa, viu a tela nova.
- **Os três blocos mermaid do `DIAG-04` foram validados por parser, nunca por renderização.**
  Validados com `mermaid@11` + `jsdom` (os três parseiam); **ninguém olhou as figuras.**
  Parser não acusa seta apontando para o nó errado.
- **A correção do `CLAUDE.md` está num arquivo gitignorado.** Não entra em commit, não chega
  a um clone, e nenhuma verificação a alcança. É o `GIT-05`, e é a ocorrência 6 do §1 das
  lições acontecendo de novo — agora com o arquivo que governa as sessões de trabalho.
  Registrado como `DOC-11`, fechado "pela metade" de propósito.
- **Nada disto rodou em runner.** Continua valendo o `CI-06`. A branch segue sem push, sem
  credencial de escrita no ambiente. **Mas uma ressalva antiga caiu:** os testes de RLS, que
  o diário registrava como "não rodou (125 pulados — exige Postgres de verdade)", **rodaram**
  — Postgres real levantado no ambiente desta sessão, 146 passando, 30/30 sabotagens
  detectadas. É a primeira vez que este diário pode citar os números de RLS como **medidos na
  mesma sessão** em que o esquema mudou.
- **O `.git/_lixo_sandbox/` cresceu de novo** (`GIT-03`), e com um detalhe novo: além do
  `index.lock`, cada `git add`/`git commit` deixou `.git/objects/*/tmp_obj_*` que o sandbox
  não consegue remover. Os commits saíram; os avisos de `unable to unlink` são ruído, não
  falha. Continua valendo a observação de método: **`GIT_OPTIONAL_LOCKS=0` serve para leitura
  e faz `git add` não gravar nada em silêncio.**

**Procedência.** Commits `778ec27`, `ad3114a`, `fb2f18f` e o deste registro;
`docs/DECISAO-FONTE-DO-PERFIL.md` (a decisão inteira, incluindo a correção de rótulo da
saída); `web-app/perfil.py`, `web-app/routes.py` (as duas rotas de perfil),
`web-app/database.py` (`nome_do_metadado`), `web-app/migrations/008_perfil_como_fonte_de_verdade.sql`
(o `revoke` e o porquê dele); `web-app/tests/test_perfil.py`,
`web-app/tests/rls/test_rls_perfil.py`, `web-app/tests/rls/conftest.py` (a usuária `CAROL` e
o motivo de ela existir), `web-app/tests/rls/test_rls_isolamento.py`,
`web-app/tests/rls/verificar_por_mutacao.py` (cinco sabotadores novos e os comentários de
`perfil_insert_permissivo` e `perfil_update_sem_with_check`);
`frontend/src/lib/perfil.ts`, `frontend/src/lib/aplicabilidade.ts`,
`frontend/src/contexts/PerfilContext.tsx`, `frontend/src/fonteDoNomeDoPerfil.test.ts`,
`frontend/src/components/EditarPerfil.tsx`, `frontend/src/components/Sidebar.tsx`;
`docs/POLITICA-DE-PRIVACIDADE.md` (§2.1, §2.4, §3, §6.3, §6.5, §9 e lacunas),
`docs/LGPD-ELIMINACAO.md` (nota de 17/10), `docs/diagramas/DIAG-04-modelo-de-dados-e-seguranca.md`,
`docs/BACKLOG-COMPLETO.md` (`PERFIL-01` ✅, `LGPD-04` ✅, `PERFIL-02`, `LGPD-05`, `LGPD-06`,
`DOC-11`, `DIAG-04`, contagem), `docs/LICOES-APRENDIDAS.md` (§1 ocorrências 7 e 8, §4
ocorrência 5, §6 ocorrências 5 e 6, índice reordenado, §9).

---

# 2026-10-19 — a gravação do perfil apagaria o nome do titular, e foi a especificação que disse

> **Continuação direta da entrada de 17/10 (iv).** O `PERFIL-01` estava fechado, com suíte
> verde e quatro commits. Esta entrada existe porque a revisão final de uma suposição que
> havia ficado declarada **confirmou o defeito** em vez de dissipá-lo.

**O problema, como foi entendido no início.** A gravação do perfil (`PATCH /api/me/perfil`)
usava `upsert` do cliente Supabase, e o `PATCH` é **parcial** de propósito: `{"idade": 30}`
deve mexer na idade e não tocar no nome. A pergunta ficou registrada como suposição ao fechar
o item: *o `upsert` do PostgREST, com um corpo que não traz `nome`, mexe no nome?*

**Hipótese de trabalho.** Que não mexia. E ela tinha apoio: a docstring do método no cliente
Python diz que o comportamento de campo ausente *"só se aplica a upsert em lote"*. Lida com
atenção, ela encerra a análise.

**O que foi testado, e como.** A docstring **não é a fonte** desse comportamento, e foi isso
que mudou o resultado. Duas leituras, em duas camadas:

1. `postgrest.base_request_builder.pre_upsert`, no pacote instalado — para saber **o que o
   cliente envia**.
2. A documentação do PostgREST v12.2, seções *Tables and Views → Upsert* e *Prefer Header →
   Missing* — para saber **o que o servidor faz com aquilo**.

**Resultado medido. O risco estava confirmado, e o defeito era perda silenciosa de dado
pessoal.** A especificação do PostgREST, literal:

> *"When doing `POST` and `PATCH` requests, **any missing columns in the payload will be
> inserted as `null` value by default**. To use the `DEFAULT` column value instead, use the
> `Prefer: missing=default` header."*

E o upsert é um `POST`. Do lado do cliente, `pre_upsert` só acrescenta `missing=default`
quando `default_to_null=False` — e o padrão é `True`, isto é, **o header não vai**. A cadeia
fecha inteira:

| Elo | O que acontece |
|---|---|
| A tela manda | `PATCH /api/me/perfil` com `{"idade": 30}` |
| A rota chama | `client.table("profiles").upsert({"id": <jwt>, "idade": 30})` |
| O cliente envia | `POST /profiles`, `Prefer: return=representation,resolution=merge-duplicates` — **sem** `missing=default` |
| O PostgREST aplica | coluna ausente do corpo = `null` |
| O banco grava | **`nome` do titular apagado** |
| A pessoa vê | `200`, e a mensagem *"Dados atualizados."* |

Corrigir a idade apagaria o nome. **Na tela que existe para cumprir o art. 18, III** — o
direito de corrigir dado inexato —, o mecanismo de correção destruiria o dado vizinho. É o §7
das lições (degradação silenciosa: o dado fica errado-com-cara-de-certo) com o §6 em cima
(confirmação emitida antes da verificação), e **nenhum teste deste repositório poderia
pegá-lo**: os testes de rota usam dublê do nosso cliente, e o PostgREST roda no Supabase.

**Adaptação.** A correção **não** foi passar `default_to_null=False`. Isso faria a coluna
ausente cair no `DEFAULT` em vez de `null` — e o default de `profiles.nome` é nulo, então
**daria no mesmo**. O header resolve o caso de coluna com default útil; não é o nosso.

A gravação passou a ser **duas instruções**, `update` e, só se ele afetar zero linhas,
`insert`:

- `update` leva **exatamente** as colunas do corpo. Semântica de SQL, não de serviço de
  terceiro.
- `insert` cobre a linha ausente, que é o caso do `DIAGNOSTICO-perfil-nao-criado.sql`. Sem
  ele, zero linhas afetadas — que não é erro para o Postgres — faria a correção do titular
  responder `200` sem ter gravado nada.
- Ordem: `update` primeiro, porque o caso comum é a linha existir. `insert` primeiro erraria
  por chave duplicada em toda correção.

**E o ganho maior é de testabilidade, não de corretude:** com `upsert`, a propriedade "um
`PATCH` de um campo não toca os outros" **não tinha onde ser testada** neste repositório. Com
SQL, tem — e agora está presa contra Postgres real, nos dois sentidos
(`test_alterar_so_a_idade_nao_apaga_o_nome` e o simétrico), mais seis testes de unidade da
ordem das duas instruções.

Os testes de `upsert` **alheio** continuam no arquivo de RLS, e por outro motivo: aquele é o
comando que um atacante pode mandar direto ao PostgREST com a chave `anon`, e o que se afirma
ali é que ele é **recusado**.

**O que o método pegou, e que a leitura não pegaria.** Um só achado, e é sobre leitura:

- **Eu li o artefato certo e respondi a pergunta errada.** A docstring do cliente descreve o
  parâmetro `columns` (que o `pre_upsert` só preenche para lote); a pergunta era sobre
  `missing`, que é do servidor. Não foi descuido de não conferir — foi conferir **a camada
  errada**, com a atenção toda. Virou a ocorrência 5 do §5 das lições, e as duas regras que
  saíram dela são: *comportamento de serviço se confere na especificação do serviço, não na
  biblioteca que fala com ele*; e *onde não der para conferir, prefira o desenho que não
  precisa da resposta*.

**Risco em aberto.**

- **A versão do PostgREST do projeto não foi conferida.** A especificação lida é a **v12.2**;
  o Supabase roda uma versão própria, que varia por projeto. A preferência `missing` existe
  desde a v11, e o comportamento padrão (`null`) é o antigo — então o defeito valeria para
  qualquer versão plausível. **Mas isso deixou de importar**, e é o ponto do desenho novo: o
  código não depende mais da resposta.
- **O desfecho de concorrência mudou de forma, não de tamanho.** Duas correções simultâneas
  sobre uma linha ausente podem ambas cair no `insert`, e uma falha por chave duplicada →
  `503`. Antes, com `upsert`, a segunda venceria em silêncio. Para um protótipo de um usuário
  é teórico; está registrado porque *"teórico"* não é o mesmo que *"tratado"*.
- **Tudo o que a entrada de 17/10 (iv) deixou aberto continua aberto**, com uma linha a
  menos: o ponto cego do `UI-11` (o dublê de `updateUser` não prova o comportamento do
  Supabase) **cresceu** — agora ele é a única parte do caminho de escrita cujo comportamento
  de serviço de terceiro ainda não foi conferido em especificação nenhuma. A limpeza de
  resíduo (`data: { nome: null }`) depende de como o GoTrue trata um valor nulo em
  `raw_user_meta_data`, e isso não foi lido. **Diferença importante:** ali a falha é inerte —
  o resíduo fica, ninguém lê, e `residuoLimpo` já relata o desfecho sem mentir.
- **A migração `008` continua não aplicada** (`PERFIL-02`).
- **Nada rodou em runner** (`CI-06`), e a branch segue sem push.

**Procedência.** Documentação do PostgREST v12.2 — *Tables and Views → Upsert* e *Prefer
Header → Missing* (`https://docs.postgrest.org/en/v12/references/api/preferences.html`);
`postgrest.base_request_builder.pre_upsert` do pacote instalado;
`web-app/perfil.py` (cabeçalho de `gravar`, com a cadeia inteira e a alternativa descartada);
`web-app/tests/test_perfil.py` (seis testes da ordem `update`/`insert`);
`web-app/tests/rls/test_rls_perfil.py` (`test_alterar_so_a_idade_nao_apaga_o_nome`, o
simétrico, e o insert do caminho de reparo); `docs/DECISAO-FONTE-DO-PERFIL.md` §6;
`docs/diagramas/DIAG-04-modelo-de-dados-e-seguranca.md` (caminho 4 e a nota do `PATCH`);
`docs/LICOES-APRENDIDAS.md` §5 ocorrência 5 e as regras 6 e 7.

# O que este diário não cobre

Registrado para que a ausência não passe por completude.

| Lacuna | Por quê |
|---|---|
| Tudo antes de 2026-04-29 | Anterior ao versionamento. Escolha do ESP32 + MPU6050, do travesseiro em vez do punho, e o enunciado inicial do problema não estão no git. |
| Grande parte de junho a agosto | O `HISTORICO.md` cobre o período, mas **não é versionado** (está no `.gitignore`), então não pode ser citado como procedência num capítulo de TCC. As entradas desse intervalo aqui saem de reflog e de código, e por isso são poucas. |
| ~~As suítes do backend e do frontend~~ | **Coberto em 16/10:** backend 240 passam, frontend 338 passam em 22 arquivos, `tsc --noEmit` e `vite build` limpos. Substitui os números de 10/09 (221 pytest, 315 vitest). Com duas ressalvas: `web-app/tests/rls/` **não rodou** (125 pulados — exige Postgres de verdade), e os 338 do frontend foram medidos **sobre a árvore de trabalho**, não sobre o estado commitado — ver a linha abaixo. ✏️ **17/10:** a segunda ressalva caiu com os 15 arquivos commitados — o frontend passa a 376 testes em 24 arquivos, medidos sobre a árvore versionada, e os dois números coincidem porque não há mais pendência. A ressalva do `rls` continua valendo. O backend **não foi reexecutado em 17/10**: os 240 seguem sendo de 16/10, e nada do trabalho de 17/10 toca `web-app/` fora de documentação. |
| ~~O frontend de 29/09~~ | ✏️ **Lacuna fechada em 17/10 — ver a entrada (iii) daquela data.** Os 15 arquivos foram lidos e commitados em quatro commits (`a586b0b`, `fea1c48`, `22a9268`, `f58f52c`). Eram a metade de cliente do `DASH-12`/`DASH-13`, trabalho não catalogado do `DASH-08`, a montagem do `UI-10` e uma correção de cabeçalho do `FW-06` — **14 de trabalho e 1 que não era mudança nenhuma**, só entrada de índice desatualizada. Os números do frontend passam a medir a árvore versionada: **376 testes**, `tsc` limpo. |
| Execução em runner de verdade | Os jobs de CI validados em 16/10 rodaram **localmente**. Nenhum rodou num runner do GitHub, e o `chore/GIT-01-normalizar-fim-de-linha` não foi enviado. A diferença não é cosmética: o `actions/checkout` é o ponto central da análise do `CI-05`. |
| Toda a camada L1 e L2 | Nada foi medido no dispositivo físico. Os 8 pinos do MPU6050 não estão soldados. Todo número de hardware neste arquivo é **calculado ou simulado**, com uma exceção — a leitura de 25/08, que é medição de um sensor mal conectado e serve só para dizer que não serve. |
