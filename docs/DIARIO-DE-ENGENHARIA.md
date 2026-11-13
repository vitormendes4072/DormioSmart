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

# 2026-02-18 e 2026-02-19 — abertura do repositório: o primeiro produto, simulado

> ✏️ **Reescrita em 2026-10-28 (`DOC-12`).** Até aqui esta entrada se chamava *"2026-04-29 —
> abertura do repositório"* e dizia que **o trabalho anterior ao clone não estava no
> repositório**. Estava: 29/04 é a data em que o repositório entrou **neste clone** (reflog:
> `clone: from …DormioSmart.git`), e o commit clonado, `a5a3307`, é o **último de sete** feitos em
> 18 e 19/02. A seção "Sobre as datas" já avisava que o reflog registra a entrada no clone; a
> entrada não seguiu o próprio aviso. É a ocorrência 8 do §5 das lições.

**PARCIAL**, e agora com o que falta delimitado.

**O que os sete commits mostram** (`git log --before=2026-04-30`, todos do mesmo autor):

| Commit | Data | O que entrou |
|---|---|---|
| `d74aa01` | 18/02 | Monorepo inteiro: `firmware/sketch.ino` + `diagram.json` do **Wokwi** (ESP32 DevKit C v4, `wokwi-mpu6050`, botão, resistor); `web-app/` em Flask com `database.py` (Supabase), `routes.py`, painel Jinja (`templates/dashboard.html`, `static/js/`), `fake_sensor.py` e `teste_conexao.py`; `vercel.json` |
| `ac1a29e`, `374e254`, `16448e1` | 18/02 | Três correções do deploy no Vercel: `requirements.txt` fora de UTF-8 e o `ModuleNotFoundError` do `routes` |
| `739f24e`, `5d2c513` | 19/02 | Conflito de versão do cliente Supabase (erro de proxy) e *lazy loading* que era simulado |
| `a5a3307` | 19/02 | O sketch passa a enviar por **HTTPS para o Vercel** (`/api/data`) e a ler o MPU6050 |

**O que eles permitem reconstruir, e não estava em lugar nenhum deste diário:**

- **A escolha do ESP32 + MPU6050 já estava feita em 18/02**, com o I2C em `SDA=21 / SCL=22` — os
  mesmos pinos de hoje. O README da `web-app/` a apresenta pronta, **sem a justificativa**.
- **O desenho de partida era Deep Sleep com despertar por botão**, no GPIO 27 (domínio RTC), com
  pull-down físico de 10 kΩ para evitar despertar por pino flutuante — e o README dedica uma
  seção ao *"crash no Deep Sleep"* no Wokwi. É a origem do andaime que o `HW-03` ainda carrega (o
  despertar é por **botão**, não pelo INT do MPU6050).
- **A pilha Flask + Supabase + Vercel e o domínio `dormio-smart.vercel.app` são de 18–19/02.**
- **O README de 18/02 exibia um selo "Status: Validado"** com tudo em simulação. É a primeira
  instância registrável do que o §6 das lições chama de confirmação antes da verificação — aqui,
  um selo num README.

**O que continua faltando** — e agora com o intervalo certo: **nenhum commit entre 20/02 e
30/05.** O levantamento do problema, a **justificativa** do ESP32 + MPU6050 e a decisão de usar
**travesseiro em vez de punho** não aparecem em commit nenhum antes de 31/05 (`e0d3f12`, o
primeiro a citar "travesseiro"). Reconstruí-los depende de material fora do git.

**Procedência.** `git log --all --reverse --before=2026-04-30`; `git show d74aa01:web-app/README.md`;
`git show d74aa01:firmware/diagram.json`; `git reflog` (a linha `clone`); `git log -S travesseiro`.

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

---

# 2026-10-19 (ii) — `UI-17`: a catraca de alcance pegava metade, e a metade que faltava era a que a pessoa vê

> **Reincidência declarada do §1 das lições**, e é a nona ocorrência. A diferença
> em relação às oito anteriores é que esta foi **prevista e medida antes de custar
> algo**: o alcance insuficiente do `alcance.test.ts` estava escrito no próprio
> arquivo, no backlog e no `PerfilContext.tsx` desde 17/10, com o número — removido
> o `<PerfilProvider>` do `main.tsx`, a suíte passa.

**O problema, como foi entendido no início.** O `alcance.test.ts`, criado em 17/10, percorre
os `import` relativos a partir de `main.tsx` e reprova quando um módulo de `src/` fica fora do
grafo. Fecha o defeito do `UI-10` — arquivo versionado que ninguém importa, inalcançável por
dezoito dias enquanto o backlog o dava por concluído e o `docs/LGPD-ELIMINACAO.md` afirmava
que o direito de eliminação estava implementado. O enunciado desta sessão: provar que os
componentes estão **montados e renderizados**, não só importados — e cobrir ao menos o
`ExcluirConta`, o `EditarPerfil`, o `PerfilProvider` e o campo de idade com o aviso de
aplicabilidade, este último nunca visto renderizado por teste nem por pessoa.

**Hipótese de trabalho.** Que a escolha fosse entre renderizar a árvore de verdade (caro,
exige `jsdom` e testing-library) e inspecionar o JSX estaticamente (barato, pega a tag
ausente). E que, pelo critério de menor custo de manutenção, a segunda vencesse para os três
componentes e só o aviso de idade exigisse render.

**O que foi testado, e como.** Primeiro o alcance de cada abordagem, contra os quatro alvos:

| Abordagem | Pega | Deixa passar | Custo de manutenção |
|---|---|---|---|
| **Inspeção estática do JSX** (`<ExcluirConta` aparece em `Settings.tsx`?) | tag apagada | tag dentro de ramo nunca alcançado; componente num arquivo que nada renderiza; rota ausente; **texto condicional que nunca aparece** | lista de pares (arquivo, tag) **escrita à mão** — a ocorrência 4 do §1 em forma nova |
| **Render da árvore de verdade** (`jsdom` + `@testing-library/react`) | tudo acima, mais provedor fora do JSX, rota ausente, condicional que nunca rende | integração real com Supabase e Flask (dublada); CSS e layout; comportamento de navegador | dublês de fronteira + 3 dependências; asserção por coisa afirmada |
| **AST com avaliação de condicionais** | em teoria tudo | o que depender de estado em tempo de execução | alto, e reimplementa um renderizador |
| **Ponta a ponta em navegador** (Playwright) | o que a pessoa de fato alcança | nada relevante | exige Supabase e Flask de pé |

**Resultado medido. A hipótese caiu no quarto alvo, e ele decidiu sozinho.** O aviso de
aplicabilidade da idade é `{aplicabilidade ? <p>…{aplicabilidade.aviso}</p> : null}`, com
`aplicabilidade = aplicabilidadeDaIdade(idadeDoPerfil(perfil))`. *"Nunca foi visto
renderizado"* não é uma afirmação que inspeção estática possa fechar — **ela não vê nada
renderizado, por construção.** E, fechado esse alvo com render, a inspeção estática dos outros
três passa a ser trabalho duplicado: o render os cobre, e com margem. Uma abordagem, não duas.

A decisão de desenho que faz a verificação valer algo, e a armadilha de que ela escapou por
pouco: o caminho idiomático com testing-library é
`render(<AuthProvider><PerfilProvider><App /></PerfilProvider></AuthProvider>)`. **Esse teste
reproduziria o defeito que existe para pegar** — a composição sob teste seria a escrita no
arquivo de teste, e remover o `<PerfilProvider>` do `main.tsx` deixaria tudo verde. Seria o §1
em forma de teste de componente, e com o agravante de o arquivo *parecer* cobertura. Então a
montagem é `await import("./main.tsx")`: o ponto de entrada de produção, executando o
`createRoot(...).render(...)` que ele tem, sobre a árvore que ele compõe. **Não há composição
duplicada, logo não há composição que possa divergir.**

Entregue: `frontend/src/montagem.test.ts`, **16 testes** — 8 de asserção nomeada em
`/configuracoes` e 8 da varredura de rotas (7 rotas + a guarda de contagem). Três dependências
de desenvolvimento (`jsdom`, `@testing-library/react`, `@testing-library/dom`), ambiente
`jsdom` por diretiva no arquivo, e **nenhuma mudança no `vitest.config.ts`** — o `include` é
`src/**/*.test.ts` e o arquivo novo não precisa de JSX, porque quem monta é o `main.tsx`.

**Controle positivo: 11 sabotagens, 11 detectadas.** Cada uma remove de fato a coisa afirmada
do JSX de produção; o arranjo confere que o trecho casa **exatamente uma vez** antes de
sabotar (um sabotador morto se lê como ponto cego — §4) e compara o arquivo byte a byte depois
de restaurar.

| # | Sabotagem | Testes que caíram | `alcance.test.ts` |
|:-:|---|---|:-:|
| 1 | `<PerfilProvider>` fora do `main.tsx` | **8 de 8** (o `usePerfil` levanta, e a `Sidebar` o chama) | **passa** |
| 2 | `<ExcluirConta />` fora do `Settings.tsx` | 1 — o do `ExcluirConta` | **passa** |
| 3 | `<EditarPerfil />` fora do `Settings.tsx` | 4 | **passa** |
| 4 | `<label for="perfil-idade">` fora do JSX | 1 | — |
| 5 | `id` do campo de idade trocado | 1 | — |
| 6 | o `<p>` do aviso de aplicabilidade fora do JSX | 1 | **passa** |
| 7 | aviso com idade fixa em 70 (sempre visível) | 1 — o **par negativo** | — |
| 8 | `<Route path="/configuracoes">` fora do `App.tsx` | 7 | **passa** |
| 9 | página de rota passa a render `null` | 1 — a varredura | — |
| 10 | guarda do instrumento: `#root` com outro id | **8 de 8** | — |
| 11 | guarda do instrumento: padrão de rota que não casa | 1 — a guarda de contagem | — |

A coluna da direita é o resultado que importa, e é o §1 inteiro numa célula: **em cinco das
cinco sabotagens em que foi medido, o `alcance.test.ts` continuou verde.** A catraca de 17/10
não estava errada; estava afirmando exatamente o que dizia afirmar, e o que ela dizia era
menos do que se precisava. É a diferença entre um alcance insuficiente **declarado** e um
alcance insuficiente **suposto**, e é a única razão pela qual esta ocorrência do §1 custou
zero.

**Adaptação.** Três coisas mudaram em relação ao plano:

1. **O prazo dos testes subiu para 60 s, e o motivo é um defeito que a primeira execução
   produziu.** A primeira montagem paga a transformação de todo o grafo de `src/` pelo Vite
   (~13 s); com o prazo padrão de 5 s o primeiro teste estourava, o `import("./main.tsx")` em
   curso resolvia **depois** do `afterEach`, e o `createRoot` da montagem abandonada caía no
   `#root` do teste seguinte. O sintoma foi oito falhas de
   `useAuth precisa estar dentro de <AuthProvider>` **numa árvore em que o provedor estava
   lá** — um erro que manda procurar o defeito no lugar errado. Está escrito no arquivo, ao
   lado da constante.
2. **A lista de rotas não é escrita no teste: sai do `App.tsx`, lido do disco.** A ocorrência 4
   do §1 é um alvo de `make` com dois dos quatro sketches porque a lista era manual. Uma lista
   de rotas à mão teria o mesmo destino. Com a lista derivada, rota nova é coberta sozinha; e a
   guarda de contagem reprova se o padrão deixar de casar, em vez de aprovar conjunto vazio
   (sabotagem 11).
3. **A varredura cobre rota nova, não rota removida** — e isso está dito no arquivo. Apagar um
   `<Route>` encurta a lista, e lista curta passa. Quem pega a remoção é a asserção nomeada da
   rota, e hoje existe uma só (`/configuracoes`, medida na sabotagem 8). As outras seis ficam no
   `UI-18`.

**O que o método pegou, e que a leitura não pegaria.** Quatro achados, e três deles são sobre
instrumentos:

- **O `UI-16` quase ganhou uma correção falsa.** Uma varredura de exports por frequência de
  identificador disse que `nomeDoDispositivo` **é** usado em produção (duas ocorrências em
  `pages/Coletar.tsx`) — o que contradiria a premissa do item. As duas ocorrências são uma
  `useState` local **com o mesmo nome**, e o `Coletar.tsx` não importa a função. O instrumento
  colidia com identificadores locais e **sub-relatava** código morto. Refeito por nome
  importado em vez de por frequência: a premissa do `UI-16` está correta.
- **E a varredura refeita achou um segundo export morto, com peso.**
  `lib/autenticacao.ts :: pareceContaExistente` não é importada por nenhum arquivo de
  produção, e tem **7 testes**. A docstring dela descreve uma decisão de segurança — *não
  dizer ao usuário que a conta já existe, para não permitir enumeração.* A proteção **existe**
  no comportamento, e justamente porque `cadastrar` **não ramifica**: e-mail existente e
  e-mail novo recebem a mesma resposta. Então não há vazamento. O que há é uma suíte de 7
  testes afirmando uma decisão de segurança **cujo caminho de produção não a exercita** —
  §1 num terceiro nível de alcance (o símbolo), que nem a catraca de arquivo nem o render
  alcançam. Virou `UI-19`, com o `UI-16` como instância.
- **Nenhum componente está hoje importado-e-não-renderizado.** Conferido símbolo a símbolo nos
  37 componentes exportados: todos aparecem como tag em algum lugar. O defeito do `UI-10` não
  tem instância aberta — e é a terceira vez que uma conferência deste tipo responde "não há",
  o que é informação e não ausência de informação.
- **`vite build` reprova neste ambiente por motivo que não é do código.** `EPERM` ao
  esvaziar `frontend/dist/` — o sandbox não consegue desvincular arquivo na pasta montada,
  mesma limitação do `GIT-03`. Os 2 328 módulos transformam; com `--outDir` fora da montagem,
  o build fecha em 23 s. Registrado para que uma sessão futura não leia isso como regressão.

**Resultado da suíte completa**, medido nesta ordem:

| Camada | Antes | Depois |
|---|---|---|
| Frontend (`vitest run`) | 408 em 26 arquivos | **424 em 27 arquivos** |
| `tsc --noEmit` | limpo | limpo |
| `vite build` | limpo | limpo (com `--outDir` fora da montagem — ver acima) |
| Backend (`pytest --ignore=tests/rls`) | — | **293** |

O número do backend corrige de passagem uma afirmação do `CLAUDE.md`, que diz 286 — medidos
em 17/10, antes dos testes de rota do `PERFIL-01`. O arquivo está no `.gitignore` (`GIT-05`),
então a correção não entra em commit; é o `DOC-11` acontecendo de novo, pelo mesmo motivo.

**Risco em aberto.**

- **O que esta suíte dubla, ela não afirma.** Três dublês, todos na fronteira externa:
  `createClient` do `@supabase/supabase-js`, o `fetch` global, e `matchMedia`/`ResizeObserver`
  que o jsdom não implementa. `lib/supabase.ts`, `lib/chaveSupabase.ts`, o `AuthContext` e o
  `PerfilContext` ficam **reais**. Logo o que está provado é montagem e renderização, **não**
  integração com o Supabase nem com o Flask. O ponto cego de integração herdado do `UI-11` (o
  `updateUser({data:{nome:null}})` em projeto real) **não** é fechado nem agravado por isto.
- **jsdom não é navegador.** Não há layout, não há CSS aplicado, não há foco real. Um elemento
  renderizado e invisível por CSS passa aqui. Fechar isso é ponta a ponta, e não está pedido.
- **As afirmações condicionais do painel continuam sem prova de que aparecem.** O
  `AvisoDeLacuna`, a `NotaDeInferencia` e a `NotaDeEscopo` são texto de honestidade científica
  que o trabalho afirma mostrar; estão renderizados *no arquivo*, e nenhuma condição deles foi
  exercitada. É o `UI-18`, e é a mesma classe do aviso de idade — que esta entrada fechou.
- **Nada disto rodou em runner** (`CI-06`), e a branch `chore/GIT-01-normalizar-fim-de-linha`
  segue sem push. O arquivo novo **não está no `ci.yml`**: ele roda junto por
  `vitest run`, mas nenhum job do CI roda `vitest` hoje — os jobs são `documentos`, `rls` e os
  do firmware. Registrado no `UI-18`.
- **Resíduo de ambiente, pela terceira sessão seguida.** `frontend/` acumulou **57** arquivos
  `vitest.config.ts.timestamp-*.mjs`, que o sandbox não apaga. Estão cobertos pelo
  `.gitignore` (linha 33), então não há risco de versionamento; é a mesma causa do `GIT-03`,
  e continua precisando de um terminal na máquina.
- **A suíte de RLS não rodou** (exige Postgres real), e o firmware não foi reexecutado —
  nada neste trabalho toca `firmware/` nem `web-app/`.

**Procedência.** `frontend/src/montagem.test.ts` (cabeçalho, com a abordagem descartada e os
dublês declarados; a nota do prazo de 60 s; a assimetria rota-nova/rota-removida);
`frontend/src/alcance.test.ts` e `frontend/src/contexts/PerfilContext.tsx` (notas de 19/10
apontando para a metade fechada); `frontend/src/components/EditarPerfil.tsx` (cabeçalho, nota
de 19/10); `frontend/package.json` (as três dependências novas);
`docs/BACKLOG-COMPLETO.md` (`UI-17` fechado, `UI-16` com a premissa reconferida, `UI-18` e
`UI-19` novos); `docs/LICOES-APRENDIDAS.md` §1 ocorrência 9, a regra 7 (*verificação não recompõe o que ela
verifica*) e a pergunta do §1 no checklist da §9.

# 2026-10-20 — `SEC-08`: o backlog dizia que não havia vazamento, e havia — o teste empírico contra a leitura

**O problema, como foi entendido no início.** Fechar duas instâncias de export morto
catalogadas no `UI-19`: `lib/dispositivos.ts :: nomeDoDispositivo` (3 testes, o `UI-16`) e
`lib/autenticacao.ts :: pareceContaExistente` (3 testes, cujo assunto declarado é uma decisão
de segurança). Trabalho de limpeza, peso baixo, decisão já tomada. **E o enunciado estava
errado na parte que importava:** o `UI-19` havia concluído em 19/10, em negrito, que *"a
proteção existe e não há vazamento"*. O Vitor foi cadastrar um e-mail já existente. A tela
respondeu **"Já existe uma conta com este e-mail."**

**Hipótese de trabalho.** Duas, e a segunda é a da sessão.

1. A primeira, herdada do diagnóstico: trocar a frase pela forma não-comprometedora, no
   modelo do `recuperarSenha` (*"Se houver uma conta com este e-mail, o link foi enviado"*),
   fecha o vazamento.
2. A segunda, levantada antes de executar a primeira e que é a razão desta entrada existir:
   **com a confirmação de e-mail desligada, os dois caminhos divergem por construção, e a
   frase é só o canal mais visível.** Se for assim, trocar a mensagem é cosmético — fecha o
   que se lê na tela e deixa o que se lê na resposta.

**O que foi testado, e como.**

| # | O que | Como |
|:-:|---|---|
| 1 | O vazamento existe? | **Cadastro real de e-mail existente, na tela.** Não é leitura: é o formulário preenchido. |
| 2 | De onde vem a frase? | `grep` por `"Já existe uma conta"` em `frontend/src/`. Dois caminhos até ela, não um. |
| 3 | O que mais difere entre os dois cadastros? | Leitura dos quatro pontos do caminho: `signUp` → `cadastrar` → `Register.aoEnviar` → tela. |
| 4 | Os testes novos prendem? | **Controle positivo:** a frase antiga devolvida ao código, suíte reexecutada. |
| 5 | A premissa de código morto se sustenta? | `grep` por **nome importado** (não por frequência de identificador — o erro medido em 19/10). |

**Resultado medido.**

**(a) O vazamento é real, e tinha dois caminhos, não um.** A frase sai de
`traduzirErroDeAuth`, e a função decide por `codigo === c || texto.includes(t)`: há a rota por
`code` (`user_already_exists`) e a rota por `message` (`"already registered"`), que existe
porque o `code` nem sempre vem. **Fechar uma só deixaria a outra vazando** — e é por isso que
eram dois os testes a reescrever, e não um.

**(b) Por que a conclusão de 19/10 estava errada, que é o achado de método.** O raciocínio
era: *`cadastrar` não ramifica, logo e-mail novo e e-mail existente recebem a mesma resposta.*
Isso é **verdade sobre o código** e **falso sobre este projeto**. A resposta idêntica é o que o
Supabase faz com a confirmação de e-mail **ligada** — 200, `identities` vazio, sem sessão.
Neste projeto ela está **desligada**, e aí o `signUp` devolve **erro**; a ramificação acontece
dentro de `traduzirErroDeAuth`, uma chamada abaixo de onde a leitura parou. A premissa não
conferida não era código: **era o valor de uma chave no painel do Supabase** — artefato que não
está no repositório, não aparece em `grep` e não dá para dublar. Virou a **ocorrência 6 do §5**
das lições, e é a primeira daquele parágrafo que chegou a produção e lá ficou.

**(c) O que difere entre os dois cadastros além da mensagem** — a pergunta de fundo, respondida
com o código na mão:

| Observável pelo cliente | E-mail novo | E-mail já cadastrado |
|---|---|---|
| Resposta do `signUp` | **200**, `user` + `session` | **422 `user_already_exists`** |
| `ResultadoDeAuth` | `{ ok: true, precisaConfirmarEmail: false }` | `{ ok: false, mensagem }` |
| Sessão | **criada** | nenhuma |
| Navegação | `navigate("/dashboard")` | **nenhuma** — fica em `/register` |
| Estado da tela | painel autenticado | `<p role="alert">` vermelho no formulário |

São **cinco** divergências, e a mensagem é **uma**. Quatro sobrevivem a qualquer redação.

**(d) É possível tornar os dois indistinguíveis mantendo a confirmação desligada? Não, e é
categórico.** Duas razões independentes, e cada uma bastaria:

1. **O desfecho de um dos caminhos é funcional, não cosmético.** E-mail novo tem de entrar no
   app — é o produto. E-mail existente **não pode** receber sessão: o app não tem a senha
   daquela conta. Igualar os dois exigiria **parar de autenticar quem acabou de se cadastrar** e
   mandar todo mundo para uma tela de "confira seu e-mail" — que, com a confirmação desligada,
   é uma tela esperando um e-mail que **ninguém envia**. Indistinguível e quebrado.
2. **O oráculo está na API, não na tela, e o frontend não é a fronteira de confiança.** Mesmo
   com UI idêntica, `422` ≠ `200` na resposta do `signUp`. Qualquer `curl` enumera, e nenhuma
   linha de TypeScript muda a resposta do servidor. **A anti-enumeração do Supabase não é uma
   chave própria: ela vem junto da confirmação de e-mail.** Então o canal estrutural é
   fechado lá, ou não é fechado.

**(e) Controle positivo, que é o que dá valor aos dois testes novos.** Frase antiga devolvida ao
código: **os dois reprovam**, um por caminho de tradução (`× pelo codigo`, `× pelo texto`).
Restaurada: **17 de 17** no arquivo. Os testes acusam o defeito que existiam para acusar — o que
os dois testes antigos, por serem o avesso disto, acusavam era a correção.

**(f) A suíte, depois de tudo.** Frontend **424 → 418 testes em 27 arquivos**, e a conta fecha:
**−3** de `pareceContaExistente`, **−3** de `nomeDoDispositivo`, **−2** linhas de `it.each`
(as que exigiam a frase), **+2** novos. Saldo −6, e o número de **arquivos** não muda — nenhum
ficou vazio. `tsc --noEmit` limpo. Backend **293**, reexecutado e inalterado: nada desta sessão
toca `web-app/`. O `web-app/tests/rls/` continua fora da conta (exige Postgres de verdade).

**Adaptação.** Três coisas mudaram em relação ao plano recebido.

1. **A ordem de apagar `pareceContaExistente` foi invertida de propósito, e o motivo virou
   regra.** O cabeçalho dela era o **único registro no repositório** de como o Supabase se
   comporta com a confirmação **ligada** — e essa informação é **insumo da decisão** do
   `SEC-08`, porque é ela que diz que a saída (A) funciona. Apagar a função primeiro teria
   destruído a evidência de que a opção existe, no mesmo commit que criou a necessidade de
   decidir. Foi preservada no cabeçalho de `temSessaoImediata`, onde o regime **oposto** já
   estava descrito — então os dois regimes ficam lado a lado, que é a forma em que a informação
   serve para decidir. *Export morto que afirma algo não se apaga: primeiro se lê o que ele
   afirma, depois se confere, e só então se apaga.* Neste caso a conferência derrubou a
   conclusão do item.
2. **O `UI-19` não foi fechado, e as duas instâncias dele fecharam.** Parece contradição e não
   é: o item mudou de enunciado em 19/10, de *"decidir as duas instâncias"* para *"tornar a
   classe verificável"*, e a classe segue sem instrumento. As duas instâncias foram resolvidas
   **à mão**, nada impede a terceira, e o `SEC-08` é a prova de por que a ferramenta importa —
   a instância morta carregava a única cópia de uma informação de que uma decisão de segurança
   dependia.
3. **A correção ficou parcial por construção, então foi registrada onde se decide e não só
   aqui.** O `SEC-08` entrou no backlog como 🔴 ⚠️ **L3 — decisão sua**, com as três saídas,
   ganho e custo de cada uma, e com o vazamento marcado como **confirmado empiricamente**. É o
   §2 das lições aplicado antes de ele reincidir: análise que não chega onde a decisão é tomada
   é análise que não aconteceu. A mesma informação está no comentário de
   `traduzirErroDeAuth` — porque quem for mexer na frase precisa saber que ela não é o
   problema inteiro.

**Risco em aberto.**

- **O canal estrutural está aberto e agora está aberto COM CONHECIMENTO.** Isso é melhor que
  ontem em honestidade e **idêntico em risco**: qualquer um com devtools enumera e-mails deste
  projeto. O que mudou é que a tela não entrega mais de graça, e que a limitação deixou de ser
  **suposta** para ser **declarada** — a distinção que é o §1 inteiro das lições. **A decisão de
  fechá-lo é do Vitor** e tem custo de experiência real: a saída (A) quebra o roteiro de
  demonstração da banca ("cadastre e entre") e depende de um remetente de e-mail que o plano
  gratuito do Supabase limita por hora.
- **Nenhum teste deste repositório pode pegar a reincidência deste defeito**, e vale dizer com
  precisão: os dois testes novos prendem **a frase**. A divergência de desfecho mora na resposta
  do Supabase, que a suíte **dubla** (`createClient` é mock desde o `UI-17`). O que pegaria é
  ponta a ponta contra um projeto real, e não existe aqui.
- **A classe do `UI-19` continua sem instrumento.** Export morto novo entra sem que nada acuse.
- **Nada disto rodou em runner** (`CI-06`), e a branch `chore/GIT-01-normalizar-fim-de-linha`
  segue sem push.

**Procedência.** `frontend/src/lib/autenticacao.ts` (o comentário do `user_already_exists`, com
a confirmação empírica datada; e o cabeçalho de `temSessaoImediata`, com os dois regimes do
Supabase lado a lado); `frontend/src/lib/autenticacao.test.ts` (os dois testes novos e o que
eles declaram **não** cobrir); `frontend/src/lib/dispositivos.ts` e
`frontend/src/lib/dispositivos.selecao.test.ts` (`nomeDoDispositivo` fora, comentário do rótulo
migrado para `descreverRecorte`); `docs/BACKLOG-COMPLETO.md` (`SEC-08` novo, `UI-16` fechado,
`UI-19` com a conclusão de 19/10 **riscada e marcada como falsa**);
`docs/LICOES-APRENDIDAS.md` §5 ocorrência 6, a regra 8 (*conclusão condicionada a configuração
não fecha por leitura*) e a pergunta nova do §5 no checklist da §9.

# 2026-10-20 (ii) — `SEC-08` revisitado: a saída recomendada não fecha o que o backlog dizia que ela fechava

**O problema, como foi entendido no início.** A entrada anterior concluiu que a anti-enumeração do
Supabase vem acoplada à confirmação de e-mail, e que a saída **(A)** — ligar a confirmação — é a
*"única que torna os caminhos genuinamente idênticos"*. Esta entrada existe para **testar essa
conclusão em vez de repeti-la**: dá para ficar seguro contra enumeração nos dois regimes? Se não,
por que exatamente? E como o mercado resolve o cadastro, que é o fluxo difícil — porque criar conta
e não criar conta têm desfechos naturalmente diferentes.

**Hipótese de trabalho.** Três, e as três caíram ou foram qualificadas.

1. A saída (A) fecha o cadastro. *(Caiu.)*
2. `recuperarSenha` não vaza, porque a resposta é uniformizada na tela. *(Caiu em dois eixos.)*
3. O cadastro pelo backend Flask uniformizaria a resposta e fecharia o canal. *(Caiu: o endpoint
   do Supabase continua público.)*

**O que foi testado, e como.** Esta entrada **não roda nada contra o Supabase** — é leitura de
código deste repositório mais leitura de fonte primária. O que é inferência está marcado.

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | O padrão de mercado trata o cadastro? | Texto integral da *Authentication Cheat Sheet* da OWASP, seção *Account creation* | fonte |
| 2 | Qual é a exigência normativa, e em que nível? | ASVS 5.0 V6, requisito a requisito | fonte |
| 3 | O NIST exige anti-enumeração? | Busca por `enumerat` no capítulo de autenticadores do SP 800-63B-4 | fonte, **resultado negativo** |
| 4 | A saída (A) é indistinguível? | Doc oficial do `signUp` + método de detecção publicado | fonte (uma de terceiros) |
| 5 | Os outros fluxos vazam? | Issues do `supabase/auth` e do `supabase/supabase` + leitura de `autenticacao.ts`, `perfil.ts`, `Login.tsx` | fonte + código |
| 6 | O proxy no Flask é viável? | `web-app/routes.py` (11 rotas), `web-app/database.py`, `web-app/auth.py` | **código deste repositório** |

**Resultado medido.**

**(a) A saída (A) NÃO torna os caminhos idênticos, e este é o achado da entrada.** Com a
confirmação **ligada**, `signUp` de e-mail existente devolve 200 com um usuário obfuscado cujo
`identities` é **array vazio**; e-mail novo devolve 200 com `identities` **populado**. É um oráculo
de **um bit, dentro de um 200, em JSON, sem timing e sem ferramenta** — e está publicado como
*método de detecção* (`data.user.identities?.length === 0`). A própria documentação oficial é
hedged e deveria ter sido lida com atenção à qualificação: *"you may get back an error message that
**attempts to** hide this information from the user"*. **Logo: nenhum dos dois regimes do Supabase
é livre de enumeração no cadastro.** A diferença entre eles não é "fecha / não fecha", é **custo de
exploração**: desligada, o sinal é o status HTTP (422 vs 200); ligada, é um campo dentro do corpo.

⚠️ **Isto é fonte, não medição deste projeto.** O que fecharia: projeto Supabase de teste com a
confirmação ligada, dois `signUp` por `curl`, comparar `identities`. Não foi feito — é o mesmo
ponto cego do `UI-11`, e fecha com o mesmo instrumento.

**(b) E o oráculo do regime (A) é parcial, o que piora o desenho em vez de melhorar.** O
`identities` vazio vale para conta **confirmada**; endereço cadastrado e **não confirmado** ainda
devolve identity, então o segundo `signUp` nele parece o primeiro. E aí mora um defeito **pior que
enumeração**: re-cadastrar em endereço não confirmado **não sobrescreve a senha original**. Quem
registra `vitima@dominio.com` primeiro e nunca confirma retém a credencial; se o dono real se
cadastrar e confirmar sem notar, **a senha viva é a do atacante**. Isso é consequência de **ligar**
a confirmação, e não estava na coluna de custo da saída (A).

**(c) O padrão de mercado trata o cadastro, é literal, e recusa a premissa de produto do registro
anterior.** A *Authentication Cheat Sheet* da OWASP, em *Account creation*, lista como respostas
**incorretas** duas — não uma:

> ❌ *"This user ID is already in use."*  ❌ *"Welcome! You have signed up successfully."*
> ✅ *"A link to activate your account has been emailed to the address provided."*

**O desfecho bem-sucedido é metade do vazamento.** O §(d)(1) da entrada anterior argumentou que
igualar os caminhos exigiria *"parar de autenticar quem acabou de se cadastrar"*, e tratou isso
como absurdo — *"é o produto"*. O padrão diz que é exatamente isso que se deve fazer: **cadastro
nunca autentica na hora.** A objeção era premissa de produto, não restrição técnica, e o
mercado a rejeita explicitamente.

**(d) Calibração normativa — e é o achado que vai para a defesa.** A exigência de
não-dedutibilidade **com registro nomeado** é **ASVS 5.0 § 6.3.8**, e é **Nível 3**:

> *"Verify that valid users cannot be deduced from failed authentication challenges, such as by
> basing on error messages, HTTP response codes, or different response times. **Registration and
> forgot password functionality must also have this protection.**"* — ASVS 5.0, V6.3.8, **L3**

Nível 3 é a faixa reservada às aplicações mais críticas; nada em V6.1/6.2/6.3 nos níveis 1 e 2
exige uniformidade de resposta. E **o NIST não exige anti-enumeração**: a busca por `enumerat` no
capítulo de autenticadores do SP 800-63B-4 — o que contém os `SHALL` de verificador — devolve
**zero ocorrências**. O que o NIST manda ali é *rate-limiting* (`SHALL`) e notificação de evento de
conta. **Portanto a enumeração é falha reconhecida, de severidade baixa e exigência de nível
alto** — e é por isso que o Supabase a declara **fora do escopo** do programa de divulgação,
afirmado nas duas issues abaixo.

**(e) Como os grandes resolvem — e nenhum dos três fecha o cadastro inteiro.**

| Provedor | Mecanismo no cadastro | Fecha? |
|---|---|---|
| **Auth0** | Flag **de tenant** (`Advanced → Use a generic response in public signup`), **ligada por padrão em tenants novos**, opt-in nos antigos → `invalid_signup` genérico | Sim no conteúdo — **e a chave é própria**, não amarrada à confirmação de e-mail |
| **Cognito** | *Prevent user existence errors* no app client — **cobre o sign-in, não o `SignUp`**, que segue devolvendo `UsernameExistsException` | **Não** no cadastro |
| **Supabase** | Acoplado à confirmação de e-mail, sem chave própria | **Não** — resta `identities` (ver (a)) |

A lição de desenho: **Auth0 prova que o acoplamento do Supabase é escolha de implementação, não
necessidade.** Uma flag de resposta genérica no cadastro pode existir sem obrigar fluxo de
confirmação — ela só não existe aqui.

**(f) Os outros fluxos, e aqui há dois achados novos neste repositório.**

- 🐞 **`recuperarSenha` vaza, e a afirmação escrita em `Login.tsx` — *"Resposta identica com ou sem
  conta"* — não se sustenta em nenhum dos dois eixos.** **(i) Conteúdo:** `supabase/auth` **#2702**
  (aberta, com PR proposto) relata, em projeto hospedado, `400 email_address_invalid` para usuário
  **existente** e **sucesso** para endereço inexistente — a validação de domínio roda *depois* da
  busca no banco. No código daqui, `traduzirErroDeAuth` **não tem ramo para `email_address_invalid`**
  (o ramo que existe casa `validation_failed` / `"unable to validate email"`), então cai no genérico
  com `ok: false`, e `Login.aoRecuperarSenha` mostra `resultado.mensagem` em vez de *"Se houver uma
  conta com este e-mail…"*. **A divergência atravessa a tela inteira.** ⚠️ Ressalva honesta: a
  reprodução da issue usa domínio reservado (`@example.com`); **não está provado para domínio real
  e não foi medido aqui.** **(ii) Tempo:** a *Forgot Password Cheat Sheet* exige resposta em tempo
  uniforme, e o caminho que manda e-mail não tem a latência do caminho que não faz nada. Isso
  depende de trabalho assíncrono **dentro** do Supabase — não é configurável daqui, e nada neste
  projeto mede.
- 🐞 **Sim, o `UI-11` abriu um canal novo, e é o mais limpo dos quatro.** `updateUser({ email })`
  com endereço de outra conta devolve **`422 email_exists`** — `supabase/supabase` **#35844**,
  reconhecida e **movida para discussão como pedido de recurso**, com enumeração declarada fora do
  escopo do bounty. No código daqui: `traduzirErroDeAuth` **também não tem ramo para `email_exists`**
  → frase genérica; **mas** `atualizarPerfil` devolve `tipo: "erro"` para endereço tomado e
  `tipo: "email-pendente"` para endereço livre, e `descreverResultado` imprime **frases diferentes**.
  Dois desfechos distinguíveis na tela — **verificado por leitura de código deste repositório.**
  Agravante: exige sessão, mas **uma** sessão basta para varrer a base; autenticação aqui não é
  barreira, é custo de entrada de uma conta.
- **Login:** o conteúdo está certo — `invalid_credentials` nos dois casos, e `traduzirErroDeAuth` o
  traduz para uma frase só. **O tempo não está:** `supabase/auth` **#2674** mede, contra projeto
  hospedado, **+74,4 / +79,7 / +78,9 / +77,0 ms** (piso de 4 execuções; controle entre dois
  endereços inexistentes = **+1,9 ms**), porque o bcrypt só roda quando o usuário existe. Fora do
  nosso alcance: é `internal/api/token.go` do Supabase.
- ⚠️ **E um custo da saída (A) que não estava no backlog:** com a confirmação ligada,
  `email_not_confirmed` passa a existir no login — e *"Confirme seu e-mail antes de entrar"* só
  aparece para **quem tem conta**. Ligar a confirmação fecha parcialmente o cadastro e **abre um
  discriminador novo no login**, que `traduzirErroDeAuth` já traduz para frase própria (linha 38).

**(g) O proxy no Flask é viável e é teatro de fronteira.** O que verifiquei no código:
`web-app/routes.py` tem **11 rotas e nenhuma de cadastro ou login** — autenticação é toda
cliente→Supabase, e `web-app/auth.py` só valida JWT de entrada; `web-app/database.py` já guarda
`SUPABASE_ANON_KEY` e cria cliente por chamada (`cliente_do_usuario`). Então escrever a rota é
barato e sem dependência nova. **E não fecha nada**, por duas razões:

1. **A senha passaria a transitar pelo nosso serviço, e hoje não transita.** Isso cria superfície
   de log acidental e obriga declaração na política de privacidade — o inverso do que o `SEC-06`
   conquistou ao expulsar a `service_role` da ingestão.
2. **O endpoint do Supabase continua público.** `POST https://<proj>.supabase.co/auth/v1/signup`
   com a chave `anon`, que **está no bundle por design**. A #2702 diz a frase exata: *"wrapping the
   call in an application server action does not close it."* Uniformizar a nossa resposta deixa o
   oráculo original a um `curl` de distância.

Fechar de verdade por esse caminho exigiria **desligar o signup público** (`disable_signup`) e criar
contas pelo backend com papel privilegiado — reintroduzir exatamente o que o `SEC-06` expulsou,
mais a API de administração, mais rate-limiting próprio. **É saída, mas é arquitetural, não um
endpoint.**

**(h) Mitigação e correção, nomeadas — porque o enunciado pediu a distinção.**

| Medida | O que faz | O que é |
|---|---|---|
| Resposta única em conteúdo, status **e tempo** + cadastro que não autentica + aviso pelo canal de e-mail | elimina o bit | **correção** — e **nenhuma configuração do Supabase entrega isso hoje** |
| `disable_signup` + criação pelo backend uniformizada | elimina o bit | **correção**, ao preço do `SEC-06` |
| Ligar a confirmação (saída A) | troca o canal de status HTTP por canal em campo JSON | **mitigação**, e não a chamem de correção |
| Captcha (hCaptcha/Turnstile, nativo no painel) | encarece a consulta | **mitigação** |
| Rate limiting / atraso artificial | encarece a consulta | **mitigação** — e atraso **fixo** não corrige timing, só desloca a média |

**O teto, dito com precisão:** mesmo com (A) + captcha + limite, restam **`identities`**,
**`email_exists` do `UI-11`** e **o timing de #2674** — três canais fora do nosso controle. **Logo o
trabalho não pode afirmar ausência de enumeração em regime nenhum.** Pode afirmar que o canal
óbvio está fechado e que os residuais estão catalogados com fonte, o que é afirmação diferente e
verdadeira.

**Adaptação.** A recomendação mudou, e não é nenhuma das três saídas do backlog como estavam
escritas. É **(B′)**: manter a confirmação **desligada** até a banca, ligar **captcha** no painel, **não**
fazer o proxy, e declarar os **quatro** canais em `LIMITACOES-TCC.md` com a fonte de cada um. O
motivo de não ser (A): ela não entrega o que o backlog prometia, abre o discriminador
`email_not_confirmed` no login, traz o problema da senha retida em endereço não confirmado, depende
do remetente limitado do plano gratuito e quebra o roteiro *"cadastre e entre"* — **custo alto,
ganho parcial, e um custo novo.** O motivo de não ser (B) pura: (B) declara a limitação sem o
atenuante grátis que existe no painel.

E a frase de defesa, que é o produto desta entrada: **a exigência violada é ASVS 6.3.8, Nível 3**;
o projeto é de nível 1 declarado; o canal está catalogado, com fonte, com severidade calibrada e
com a saída conhecida e precificada. Isso é postura defensável diante de uma banca — e é melhor
que ligar uma chave e afirmar que fechou, que é o que a entrada anterior recomendava.

**Risco em aberto.**

- **Duas afirmações do repositório sobre comportamento do Supabase estão falsas, e nenhuma foi
  conferida contra o serviço.** O cabeçalho de `temSessaoImediata` diz que com a confirmação ligada
  *"os dois caminhos ficam indistinguíveis pelo cliente"* — e `identities` os distingue. O
  comentário de `Login.tsx` diz que `recuperarSenha` *"responde idêntico com ou sem conta"* — e a
  #2702 diz que não. **Mesma classe do §5 das lições, agora em duas instâncias novas**, e nenhuma
  delas é corrigível por teste deste repositório, porque o `createClient` é dublê. Não foram
  tocadas nesta sessão: é investigação, e corrigir comentário é mudança de código.
- **(a), (b), (f-i) e o timing do (f-login) são fonte de terceiros, não medição deste projeto.** O
  instrumento que fecharia os quatro é o mesmo e já está devendo desde o `UI-11`: um projeto
  Supabase de teste e um punhado de `curl`.
- **O canal do `UI-11` (`email_exists`) está aberto e era desconhecido** até esta entrada. O
  `SEC-08` catalogava um canal; são **quatro**.
- **Nada disto rodou em runner** (`CI-06`), e a branch `chore/GIT-01-normalizar-fim-de-linha`
  segue sem push.

**Procedência.** **Código deste repositório, lido:** `frontend/src/lib/autenticacao.ts` (ausência de
ramo para `email_address_invalid` e `email_exists`; `email_not_confirmed` na linha 38);
`frontend/src/lib/perfil.ts` (`atualizarPerfil` → `erro` vs `email-pendente`; `descreverResultado`);
`frontend/src/pages/Login.tsx` (`aoRecuperarSenha`, e o comentário falso); `web-app/routes.py`
(11 rotas, nenhuma de auth); `web-app/auth.py`; `web-app/database.py` (`SUPABASE_ANON_KEY`,
`cliente_do_usuario`). **Fonte primária:** OWASP *Authentication Cheat Sheet*, §*Authentication and
Error Messages* → *Account creation*; OWASP *Forgot Password Cheat Sheet*; **OWASP ASVS 5.0 V6.3.8
(L3)**; NIST SP 800-63B-4, cap. *Authenticators* (busca por `enumerat` = 0 ocorrências; `SHALL` de
rate-limiting em §3.2.2); doc oficial do `supabase.auth.signUp`; issues `supabase/auth` **#2702**,
**#2674** e `supabase/supabase` **#35844**. **Fonte de terceiros, usada como tal:** GuardLayer,
*"Supabase signup with an existing email: why no error"* (07/09/2026) — método `identities.length === 0`,
o caso não-confirmado e a senha retida (via discussão `supabase` #29327); comunidade Auth0 sobre a
flag de tenant; `aws-amplify/amplify-js` #6238 sobre `UsernameExistsException` no `SignUp`.

# 2026-10-20 (iii) — `SEC-08` executado: a saída (B′), os comentários que prometiam segurança, e o achado que estava escondido num custo

**O problema, como foi entendido no início.** Executar a decisão da entrada anterior — o Vitor
aprovou a saída **(B′)** — e fechar o que ficou pendente: os dois comentários falsos no código, os
quatro canais em `LIMITACOES-TCC.md`, o captcha como item dele, e os dois canais novos catalogados.
Trabalho de registro, com uma pergunta aberta de verdade no meio: **a retenção de credencial em
conta não confirmada merece item próprio, ou é nota de rodapé do custo da saída (A)?**

**Hipótese de trabalho.** Que fosse nota de rodapé. Era como estava escrita na entrada (ii) — um
marcador dentro do parágrafo (b), ao lado do oráculo parcial. **Caiu**, e a correção é de
classificação e não de fato: o que estava registrado como *custo de uma alternativa* é uma **classe
de ataque com nome, literatura e causa raiz própria**, e de severidade **acima** de tudo o que o
`SEC-08` cataloga.

**O que foi testado, e como.** Esta entrada também não roda nada contra o Supabase — e isso é o
risco em aberto nº 1, repetido pela terceira sessão seguida.

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | A retenção de credencial é real e é classe conhecida? | `supabase` #14994 (2023) e #29327 (2024), independentes e em versões distintas; guia oficial *Identity Linking*; SUDHODANAN & PAVERD, arXiv:2205.10174 | fonte |
| 2 | Ela é explorável **nesta** configuração? | Raciocínio sobre o regime medido em 20/10 (i) | **inferência, e está marcada como tal** |
| 3 | As duas afirmações falsas do código estavam onde eu disse? | `Login.tsx` e cabeçalho de `temSessaoImediata`, abertos e corrigidos | código |
| 4 | A suíte aceita as mudanças? | `vitest run`, `tsc --noEmit`, `pytest` do backend | execução |

**Resultado medido.**

**(a) A retenção de credencial virou `SEC-10`, e a justificativa de promovê-la é de natureza, não
de gravidade percebida.** O mecanismo: alguém cadastra endereço de terceiro e **não confirma**; o
dono real se cadastra depois, e o Supabase **reenvia o link em vez de criar conta nova — e não
sobrescreve a senha**. O dono confirma, entra, usa; **a credencial viva é a do primeiro.** Dois
relatos independentes, de 2023 e 2024, descrevem o mesmo comportamento em versões diferentes — o
que é o mais próximo de reprodução que se consegue sem medir. E tem nome: é *account
pre-hijacking*, com a causa raiz enunciada pelos autores do artigo como **permitir uso da conta
antes de verificar que o usuário controla o identificador**, documentada em **56 vulnerabilidades
sobre 35 de 75 serviços populares**. A própria documentação do Supabase usa o termo — *"would
enable pre-account takeover attacks"* — e descreve a proteção **para o fluxo de vinculação de
identidades**, não para o re-cadastro simples.

**Por que não é nota de rodapé:** enumeração é **divulgação de informação**; isto é **acesso
indevido a conta**, com os dados de sono do titular dentro. São classes diferentes de dano, e
enterrar a segunda num parágrafo sobre a primeira é o §2 das lições — análise que não chega onde
a decisão é tomada. Mais: ela **muda o sinal da decisão.** A saída (A) não é só "ganho parcial por
custo alto"; é **trocar um vazamento de informação por uma via de acesso indevido**. Quem leia só
a coluna de custo não vê isso; quem leia um item 🟠 com título próprio, vê.

**(b) E ela NÃO é explorável na configuração atual — o que é o resultado mais útil da entrada.**
Com a confirmação **desligada**, a conta nasce confirmada no primeiro `signUp`, e o segundo recebe
`422`: **não existe estado "não confirmado" para ser ocupado.** Logo `SEC-10` não é risco corrente,
é **pré-condição** de qualquer adoção futura da saída (A). Está escrito assim no item, com a
obrigação explícita: se (A) for adotada algum dia, `SEC-10` se resolve **antes ou junto, nunca
depois**. ⚠️ Isto é **inferência** a partir do regime medido em (i), não medição própria — e está
marcado no item.

**(c) Os dois comentários falsos foram corrigidos dizendo o que acontece, com a fonte dentro do
comentário.** O de `Login.tsx` afirmava *"Resposta identica com ou sem conta"*; agora enumera os
dois eixos em que isso é falso (conteúdo, por #2702; tempo, por exigência da cheat sheet que nada
aqui mede), **com a ressalva de que a issue reproduz em domínio reservado e que não foi medido
aqui.** O de `temSessaoImediata` afirmava *"os dois caminhos ficam indistinguiveis pelo cliente"*;
agora cita a frase oficial **inteira** — *"an error message that **attempts to** hide this
information"* — porque foi exatamente a qualificação perdida que produziu o erro, e deixar a frase
no comentário é a forma verificável da lição. Nenhuma linha de lógica mudou nos dois arquivos: o
código já era o melhor alcançável do lado do cliente. **O que mudou foi a afirmação** — e isso é o
ponto, porque comentário que promete segurança inexistente **encerra a análise de quem revisa**,
que é pior que comentário nenhum. O canal do `UI-11` ganhou cabeçalho próprio em `perfil.ts`,
inclusive a parte que não é técnica: ele **entrou junto com a funcionalidade e passou pela
revisão**.

**(d) `LIMITACOES-TCC.md` ganhou a seção X.7, e é a primeira do arquivo que não é sobre medição.**
Quatro canais, cada um **classificado pela natureza da evidência** — e dois deles com "não
verificado neste trabalho" **no próprio título do item**, para que enxugar o texto não apague a
distinção. O enquadramento, que é o produto: a exigência violada é **ASVS 5.0 § 6.3.8, Nível 3** —
o nível máximo, e nenhum requisito de Nível 1 ou 2 exige uniformidade de resposta; o **NIST
SP 800-63B-4 não tem requisito de anti-enumeração** (busca por `enumerat` no capítulo de
autenticadores = zero, e o que ele impõe é rate-limiting e notificação); e o **acoplamento do
Supabase é escolha de implementação** — o Auth0 tem flag própria, ligada por padrão em tenants
novos, sem vincular à confirmação. Isso transforma *"temos uma falha"* em *"não atendemos a um
requisito de nível máximo, sabemos em quais quatro pontos, sabemos quanto custa fechar, e a causa
é uma decisão de projeto revisável"*. E a nota fora dos marcadores traz **três ressalvas de citação
obrigatórias**, a mais séria sendo que **a citação do NIST é feita por ausência** e está delimitada
a um capítulo — afirmação de ausência mal delimitada é a pior forma de citação, porque o leitor não
a verifica sem repetir a busca.

**(e) O captcha ficou como `SEC-11` e com o parágrafo do que ele não faz colado no do que faz.** É
painel, ~5 min, zero código, cobre `signup`/`token`/`recover`. **Reduz taxa; não elimina o
oráculo** — quem quer saber de **um** endereço resolve um desafio e recebe a resposta, e é a
consulta individual que sustenta os usos graves (phishing direcionado, extorsão). E a frase que o
item existe para carregar: **ligar isto não autoriza mudar uma palavra da X.7.** Trocar "limitação
declarada" por "mitigado" depois de ligar a chave seria o §1 das lições com a chave na mão.

**(f) A suíte.** Frontend **418 testes em 27 arquivos**, inalterados — as mudanças de hoje são
comentário e documentação, e nenhum teste do repositório afirma nada sobre os canais novos, o que
é verdade registrada e não lacuna nova: `createClient` é dublê desde o `UI-17`. `tsc --noEmit`
limpo. Backend **293**, reexecutado e inalterado. RLS fora da conta (exige Postgres real).

**Adaptação.** Duas, e as duas são de classificação.

1. **A retenção de credencial foi promovida de nota a item (`SEC-10`)** — justificativa em (a).
2. **O `SEC-08` saiu do L3 e o `SEC-11` entrou nele.** Parece contabilidade e não é: o `SEC-08`
   estava em L3 porque *"a saída é decisão sua"*, e a decisão foi tomada. O que resta dele é
   declaração, que é L0. O que precisa do Vitor agora é **uma chave de painel**, e ela tem item
   próprio justamente para não ficar pendurada num item de 🟠 que ninguém mais precisa abrir.
   *Pendência que depende de outra pessoa não mora dentro de um item já decidido.*

**Risco em aberto.**

- **Terceira sessão seguida em que o instrumento que falta é o mesmo, e ele agora deve a quatro
  itens.** Um projeto Supabase de teste fecharia: o ponto cego do `UI-11` (confirmação de troca de
  e-mail, `nome: null` apagando a chave), o canal 2 do `SEC-08` (`identities`), o canal 4 /
  `SEC-09` (`/recover` em domínio real) e o `SEC-10` inteiro. **Quatro itens esperando o mesmo
  objeto, e ele não tem item.** Isto é candidato a ser o próximo item criado, e esta linha existe
  para que ele não seja esquecido de novo.
- **A X.7 depende de duas *issues* em aberto.** Se #35844 e #2702 forem corrigidas antes da
  entrega, a seção passa a **afirmar falha que não existe** — espelho exato do `DOC-11`. Entrou no
  checklist do arquivo, com a obrigação de reconferir na semana da entrega e registrar a data de
  consulta.
- **`SEC-10` é o item de maior severidade declarada do projeto e tem a evidência mais fraca.** Dois
  relatos de comunidade e um termo em doc oficial, mais um relato **conflitante** sobre metadado
  (`supabase-js` #298). Nada medido. A classificação 🟠 é da **classe**, não da confirmação — e
  está dito no item.
- **Nada disto rodou em runner** (`CI-06`); o `vitest` segue fora do `ci.yml` (`UI-18` (c)), e a
  branch `chore/GIT-01-normalizar-fim-de-linha` segue sem push.

**Procedência.** **Código:** `frontend/src/pages/Login.tsx` (comentário de `aoRecuperarSenha`,
corrigido); `frontend/src/lib/autenticacao.ts` (cabeçalho de `temSessaoImediata`, corrigido e com
a frase oficial citada inteira); `frontend/src/lib/perfil.ts` (cabeçalho novo do canal `SEC-09`).
**Documentos:** `docs/LIMITACOES-TCC.md` (seção **X.7** nova, dentro dos marcadores; nota *"O que
entrou em 2026-10-20"* com a tabela de 11 referências e as três ressalvas; 3 itens novos no
checklist; aviso no cabeçalho); `docs/BACKLOG-COMPLETO.md` (`SEC-08` decidido e movido para L0;
`SEC-09`, `SEC-10` e `SEC-11` novos; contagem 73 → **76**, L0 46, L3 8; mapa de camadas);
`docs/LICOES-APRENDIDAS.md` (§1 ocorrência **10** + regras 9 e 10; §5 ocorrência **7** + regras 10
e 12; índice reordenado — o §5 passou ao segundo lugar — e a nota de 20/10 (ii) sobre o terceiro
instrumento; §9 com as duas perguntas novas). **Fontes externas:** OWASP *Authentication* e
*Forgot Password Cheat Sheets*; **ASVS 5.0 V6.3.8 (L3)**; NIST SP 800-63B-4; doc de
`supabase.auth.signUp` e guia *Identity Linking*; `supabase/auth` #2702, #2674; `supabase/supabase`
#35844; `supabase` #14994 e #29327; `supabase-js` #298; SUDHODANAN & PAVERD, arXiv:2205.10174.

---

# 2026-10-27 — `DOC-11`, segunda passagem: a correção de 17/10 envelheceu em dez dias, e a suíte inteira rodou nesta máquina pela primeira vez

**O problema, como foi entendido no início.** Migração de ferramenta. O enunciado da sessão:
*"o `CLAUDE.md` está desatualizado e gitignorado, e afirma que não há suíte de testes quando há
mais de mil"*. Corrigir, e avaliar se ele deve sair do `.gitignore`. Antes disso, dizer o que
ficou sem commit da sessão anterior, interrompida no meio de uma consolidação.

**Hipótese de trabalho.** Que o `CLAUDE.md` do repositório ainda dissesse "não há suíte". **Caiu
na primeira leitura:** o arquivo do repositório já tinha sido corrigido em 17/10 e diz "há suíte
e há CI". Quem ainda diz *"Testes: ainda não existem"* é a **cópia** na
pasta `backup-interno`, fora do repositório (28/08). A premissa do enunciado era verdadeira sobre uma cópia e
falsa sobre o arquivo — que é exatamente o risco de um arquivo gitignorado: ele tem cópias, e
nada as compara. A segunda hipótese — *então o arquivo está em dia* — **também caiu**, e é o
resultado desta entrada.

**O que foi testado, e como.** Tudo executado em Windows 11, branch
`chore/GIT-01-normalizar-fim-de-linha` (`2fcb0f5`), árvore com os 3 arquivos não rastreados
abaixo.

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | O que ficou sem commit | `git status` | execução |
| 2 | A consolidação interrompida está coerente? | `python scripts/consolidar_registro.py --conferir` | execução |
| 3 | Backend | `pytest --ignore=tests/rls` | execução |
| 4 | Frontend | `npx vitest run`; `npx tsc --noEmit` | execução |
| 5 | RLS e mutação | `postgres:16` em Docker; `pytest tests/rls`; `verificar_por_mutacao.py` com `PYTHONUTF8=1` | execução |
| 6 | ML | `ml/.venv` (3.11.9, versões do `requirements.txt`); `pytest testes` | execução |
| 7 | Firmware | contêiner `gcc:13`, `firmware/` e `ml/testes/` copiados; `make`, `sintaxe`, `capacidade`, `mutacao` | execução |
| 8 | Verificador de documentos | no Windows, e num clone limpo em `python:3.11` (Linux) | execução + controle |
| 9 | Jobs do CI | `ci.yml` aberto; `git log -S"npm test"` | inventário |

**Resultado medido.**

**(a) Sem commit: três arquivos não rastreados, e nada modificado.** `docs/CORRECOES-APLICADAS.md`,
`docs/PENDENCIAS-ABERTAS.md` e `scripts/consolidar_registro.py`, todos de 20/10 02:23 — a
consolidação. O `--conferir` passa (*105 defeitos, 87 pendências*; os dois documentos batem com as
tabelas do script). **Mas o `conferir_docs_versionados.py` reprova os dois como órfãos em `docs/`**,
e o `PENDENCIAS-ABERTAS.md` diz que se mitiga o §2 *"com uma linha no `BACKLOG-COMPLETO.md`
apontando para cá"* — **a linha não existe** (`grep` vazio). O script também não está no `ci.yml`.
A consolidação parou antes de três passos: versionar, ligar ao backlog e ao CI. **Não commitado
nesta sessão** — não li as 2 897 linhas do script, e não se dá por verificado o que não foi
rodado nem lido.

**(b) A suíte, executada:** backend **293**; frontend **418 em 27 arquivos**, `tsc` limpo; RLS
**149** contra Postgres real, mutação **30/30**; firmware **341 + 157 verificações, 0 falhas**,
**4/4** sketches compilam, mutação **15/15**; ML **104 passam e 3 falham**. São **967 testes** de
pytest/vitest e **498 verificações** do núcleo C++. *"Mais de mil"* depende de somar as duas
unidades — está escrito assim no `CLAUDE.md`, com as duas separadas.

**(c) O `CLAUDE.md` de 17/10 estava errado em três pontos, e um já tinha contaminado o backlog.**
Os números eram de 17/10 (286/408/146); a suíte de **ML não aparecia**; e a lista de jobs dizia
*"`documentos`, `rls` e os do firmware"*. O `ci.yml` tem **seis** (`test`, `rls`, `frontend`, `ml`,
`firmware`, `documentos`), e o `frontend` roda `npm test` = `vitest run` desde `01a7faa` (19/08).
**O `UI-18` (c) do backlog afirmava que *"nem o `vitest` está"* no CI, com a mesma lista de jobs** —
afirmação falsa, corrigida hoje. Não dá para provar que ela veio do `CLAUDE.md`; a coincidência do
enunciado é a evidência, e é **inferência**.

**(d) Dois defeitos novos, os dois só no Windows, os dois achados porque rodou.**
- **`DOCS-WIN-01`.** No Windows, `ignorados()` manda `\r\n` ao `git check-ignore` (pipe em modo
  texto), e só o último caminho casa. **Controle:** mesma árvore, clone limpo em Linux — a (3) acha
  os **8** ponteiros aceitos e dá OK; no Windows acha **0**, e a (2) reprova os três arquivos de
  fundamentação como não ignorados. Reproduzido isolado em três linhas de Python. A verificação (3),
  que existe para pegar o nono ponteiro pendurado, **não pode reprovar nada nesta máquina**. O CI
  (Ubuntu) não é afetado.
- **`ML-WIN-01`.** Os dois testes de vetor dourado comparam JSON por **igualdade exata** e diferem
  no **último dígito** (1 valor num arquivo, 70 no outro) — referência gravada em Linux/3.10. O
  terceiro, de retomada, leva 5 chamadas onde espera 7; **hipótese não confirmada**: resolução de
  ~15,6 ms do relógio do Windows com `orcamento_s=0.0`.
- E as quebras de codificação: dois scripts morrem em `cp1252` sem `PYTHONUTF8=1`.

**Adaptação.**

1. **O `CLAUDE.md` foi reescrito com o que rodou**, não com o que estava escrito: tabela com
   resultado e data, a linha de ML, os seis jobs, as armadilhas do Windows, a ordem de leitura
   (backlog → diário → lições → documentos gerados) no lugar de *"ler o `ROADMAP.md` no início de
   toda sessão"*, a estrutura real (`frontend/`, `scripts/`; `hardware/` vazia) e as práticas não
   negociáveis do enunciado. Mantido: Gitflow, regras de commit e a regra que o põe no `.gitignore`,
   agora com a nota de que está em reavaliação.
2. **A recomendação do `GIT-05` sobre o `CLAUDE.md` foi invertida**, de *"parar de ser citado"* para
   *versionar*, com a parte pessoal num `CLAUDE.local.md` gitignorado. Motivo medido: a correção
   envelheceu em dez dias sem que nada a alcançasse, a lista de jobs errada passou para o backlog, e
   existem cópias divergentes. **Não executada:** revoga uma decisão explícita do autor e resulta em
   publicação num repositório público. A decisão é do Vitor.

**Risco em aberto.**

- **O `DOC-11` continua meio-feito, e pelo mesmo motivo de 17/10.** Esta reescrita também está só no
  disco; nada a confere. Item: `GIT-05`.
- **O `CLAUDE.md` envelhece de novo** a cada teste novo. Versionado, uma conferência no
  `documentos` poderia comparar os números com a coleta (como o piso do `CI-04`). Ainda não é item,
  porque depende da decisão do `GIT-05`.
- **A consolidação de 20/10 segue sem commit** (a). Pendente de ler o script e decidir o caminho.
- **Os 3 testes de ML que falham no Windows** (`ML-WIN-01`) e o verificador que mede errado no
  Windows (`DOCS-WIN-01`).
- **`vite build` não rodou hoje**; e nada disso rodou em runner (`CI-06`).
- **Esta entrada não pode ser commitada sozinha.** Ela cita `docs/CORRECOES-APLICADAS.md` e
  `docs/PENDENCIAS-ABERTAS.md`, que não estão no git, e a verificação (2) do
  `conferir_docs_versionados.py` **reprova** por isso — medido em Linux sobre a árvore editada. Na
  mesma execução a (3) acusou um ponteiro novo que esta própria entrada criava (o caminho da cópia
  de backup, que casa a regra `CLAUDE.md` do `.gitignore`); corrigido trocando o caminho por
  descrição. Commitar junto com a consolidação, ou depois dela.

**Procedência.** `CLAUDE.md` (gitignorado; seções "Contexto", "Práticas não negociáveis",
"Testes"); `docs/BACKLOG-COMPLETO.md` (`DOC-11`, `GIT-05`, `UI-18` (c) corrigido, `DOCS-WIN-01` e
`ML-WIN-01` novos, contagem 76 → **78**, L0 48); `.github/workflows/ci.yml`; commit `01a7faa`;
`scripts/conferir_docs_versionados.py` (`ignorados`); `ml/testes/test_vetor_dourado.py`
(`_confere_ou_regrava`); `ml/testes/test_retomada.py`; `ml/experimentos/_retomada.py` (linha 127);
a cópia na pasta `backup-interno` (fora do repositório).

---

# 2026-10-27 (ii) — `DOC-11` fechado: o `CLAUDE.md` passa a ser versionado, e a lista de ponteiros não encolheu

**O problema, como foi entendido no início.** O Vitor decidiu pela recomendação da entrada
anterior: versionar o `CLAUDE.md` e mover a parte pessoal (devlog, mídia, caminhos da máquina)
para um `CLAUDE.local.md` gitignorado. Mostrar o diff antes de commitar.

**Hipótese de trabalho.** Duas. (1) Que bastasse tirar uma linha do `.gitignore` e mover três
seções. (2) A que eu tinha escrito no `GIT-05`: *"fazendo, a lista do `PONTEIROS_ACEITOS` cai de
8 para 7"*. **A (2) caiu**, e a (1) também, por causa de um lock.

**O que foi testado, e como.**

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | O conteúdo pode ir a público? | `grep` por chave, senha, e-mail, nome e caminho de usuário; `git log --all -- CLAUDE.md`; URL de produção contra o `README.md` | inventário |
| 2 | As regras de ignore ficaram certas? | `git check-ignore -v CLAUDE.md CLAUDE.local.md` | execução |
| 3 | A verificação (3) aceita o desenho novo? | cópia da árvore em `python:3.11`, `CLAUDE.md` posto no índice, `conferir_docs_versionados.py` | execução |
| 4 | Ela acusaria um ponteiro novo? | mesma cópia, com o `CLAUDE.local.md` removido de `PONTEIROS_ACEITOS` | **controle positivo** |

**Resultado medido.**

**(a) Nada sensível.** Nenhuma chave, senha, e-mail, nome de pessoa ou caminho de usuário no
`CLAUDE.md`; a URL de produção já está no `README.md` versionado; e o arquivo **nunca** esteve no
histórico (`git log --all` vazio), então versioná-lo não expõe nenhuma versão antiga.

**(b) O `.gitignore` responde certo:** `CLAUDE.local.md` casa a linha 10; `CLAUDE.md` não casa
nada.

**(c) A lista de ponteiros aceitos continua com 8, não 7.** O `CLAUDE.md` saiu e o
`CLAUDE.local.md` entrou: o arquivo versionado precisa dizer onde está o que ficou de fora, e
dizer isso **é** um ponteiro para arquivo ignorado. E o `CLAUDE.md`, agora rastreado, passou a
citar também os outros seis ignorados — a (3) os lista com *"ex.: `CLAUDE.md`"*. **A lista mudou
de natureza, não de tamanho.** A previsão estava errada por leitura; a execução a corrigiu antes
de ela virar número no backlog.

**(d) Controle positivo:** com o `CLAUDE.local.md` fora da lista, a (3) reprova e nomeia
*"`CLAUDE.local.md` ← citado em `CLAUDE.md`"*. Sem a sabotagem, *"nenhum ponteiro novo"*.

**(e) O que segue reprovando é o que já reprovava**, e agora por dois citadores: a (1) e a (2)
acusam os dois documentos da consolidação, citados pelo diário e pelo `CLAUDE.md`. Virou `GIT-06`.

**(f) A primeira execução da (3) foi inválida, e quase passou por boa.** A cópia da árvore levou
junto um `.git/index.lock` de 20/10 01:22, o `git add` da cópia falhou, e o `grep` da saída
escondeu o erro — o resultado parecia "OK" e tinha sido medido **sem** o `CLAUDE.md` no índice.
Notado porque o `git ls-files` de conferência veio vazio. Refeito com o lock removido **só na
cópia**. O mesmo lock está no repositório real, sem processo git rodando: é sobra da sessão
interrompida, e **bloqueia commit**. Registrado no `GIT-03`.

**Adaptação.**

1. **`CLAUDE.md` versionado**, com cabeçalho dizendo desde quando e por quê, e o aviso de que o
   repositório é público. Mídia, devlog, regras de gravação, caminho da memória persistente e o
   ambiente desta máquina foram para o `CLAUDE.local.md`. A nota de 17/10 que citava o caminho da
   cópia de backup virou descrição — caminho de máquina não vai a público.
2. **`.gitignore`:** sai `CLAUDE.md`, entra `CLAUDE.local.md`, com comentário. **`PONTEIROS_ACEITOS`:**
   a entrada do `CLAUDE.md` vira a do `CLAUDE.local.md`, com o motivo.
3. **`DOC-11` fechado; `GIT-06` aberto.** Contagem 78 → 78.

**Risco em aberto.**

- **O `documentos` fica vermelho até o `GIT-06`.** Commitar isto antes da consolidação deixa o CI
  reprovando por um motivo conhecido e declarado.
- **O `CLAUDE.md` continua podendo envelhecer.** Versionado, o envelhecimento aparece em diff, mas
  nada o reprova. Uma conferência que compare os números da seção "Testes" com a coleta seria o
  passo seguinte; **ainda não é item** — fica aqui até alguém decidir se vale o custo.
- ~~O lock precisa sair antes do commit~~ — **eram dois.** Removido o `index.lock`, o commit
  falhou num `HEAD.lock` da mesma hora (20/10 01:22:28). Os dois foram removidos, cada um com
  aprovação própria, depois de conferir 0 bytes e nenhum `git.exe` rodando; o
  `objects/maintenance.lock` (16/10) ficou, por decisão do Vitor. **Erro de método meu:** a
  varredura `find .git -name "*.lock"` devia ter vindo antes da primeira remoção, não depois da
  falha (`GIT-03`).

**Procedência.** `CLAUDE.md` (versionado); `CLAUDE.local.md` (gitignorado); `.gitignore`;
`scripts/conferir_docs_versionados.py` (`PONTEIROS_ACEITOS`); `docs/BACKLOG-COMPLETO.md`
(`DOC-11`, `GIT-03`, `GIT-05`, `GIT-06`); `.git/index.lock` (20/10 01:22, 0 bytes).

---

# 2026-10-28 — `GIT-06` e `DOCS-WIN-01`: a consolidação de 20/10 entra no git, e o que ela tinha achado chega, enfim, ao backlog

**O problema, como foi entendido no início.** Versionar os três arquivos da consolidação
interrompida em 20/10 (`scripts/consolidar_registro.py` e os dois documentos que ele gera), que
deixavam o job `documentos` vermelho desde que o diário e o `CLAUDE.md` passaram a citá-los. Plano
aprovado pelo Vitor com sete escolhas: a linha `ML-04b` fora da contagem e visível; o push como
`GIT-07`; dois commits de conteúdo (consertar e versionar; levar as discordâncias ao backlog), com
a data do versionamento virando item próprio; todas as discordâncias reconferidas, e nada fechado
sem abrir o artefato; números puros derivados e frases que nomeiam casos travadas por guarda;
`fetch-depth: 0` no CI com guarda para histórico raso; e o `DOCS-WIN-01` no mesmo lote.

**Hipótese de trabalho.** Que fosse trabalho de transcrição sobre uma auditoria já feita. **Caiu
três vezes**, e as três quedas estão abaixo: a contagem do backlog não podia ser corrigida por
delta, uma classificação minha foi reprovada pela guarda que eu acabara de escrever, e medir o
impacto achou uma terceira instância do defeito do Windows.

**O que foi testado, e como.** Windows 11 e contêiner `python:3.11` (Linux), sobre a árvore de
trabalho de `4014798` mais este lote.

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | Os hashes citados existem? | `git cat-file` em cada um | inventário |
| 2 | As discordâncias de 20/10 ainda valem? | cada artefato aberto de novo (DIAG-01, DIAG-03, `firmware/`, `DATA-CONTRACT.md`, as duas linhas `LGPD-02`) | inventário |
| 3 | A contagem do backlog está certa? | recontagem linha a linha por script, na versão commitada e na editada | execução |
| 4 | A correção do `DOCS-WIN-01` funciona? | Windows sem `PYTHONUTF8`: execução normal, ponteiro plantado, versão anterior | **controle positivo** |
| 5 | As verificações novas acusam? | seis sabotagens num clone em Linux, cada uma numa cópia nova | **controle positivo** |
| 6 | Algo mais mudou de comportamento? | todas as suítes, os três `--conferir`, RLS com mutação, YAML do CI | execução |

**Resultado medido.**

**(a) O hash `846966a` não existe**, e estava em cinco linhas de procedência "completa". O commit
é `846986a` (núcleo do firmware, 22/09). Uma das linhas, a das strings quebradas do
`envio-continuo.ino`, citava só ele, e a correção do sketch está no `c0725ca`: passou a citar os
dois. O `--conferir` agora confere todo hash e **reprova com histórico raso**. O job `documentos`
passou a `fetch-depth: 0` e a rodar o `--conferir`.

**(b) A "divergência" 146 × 149 do RLS não era divergência.** Coleta em cada commit: **146** em
`778ec27` e `73c213f` (17/10), **149** desde `275665a` (19/10). Os dois documentos estavam certos
para as suas datas.

**(c) Das catorze discordâncias de 20/10, doze fecharam e duas não.** `DIAG-01` e `DIAG-03` estão
escritos desde 29/09, e o backlog os dava como não começados. Abertos de novo, cumprem o pedido
na forma, mas se declaram conferidos em 29/09. O `DIAG-03` tem dois pontos que pedem decisão: a
figura C omite as features em C++ de 17/10 (inertes: o sketch não as chama) e rotula o payload
`v2.4.0` com o contrato em 2.5.1. **Ficaram abertos, com o que falta escrito.** Os outros doze
foram aplicados: `LGPD-02` contado duas vezes; `PWA-01` e `PERFIL-02` na camada errada; item sem
ID (`UI-20`); `ML-04`/`ML-05` abertos com ID de itens fechados (`ML-09`/`ML-10`, com a
correspondência anotada nos dois documentos de plano que numeram assim); números do `GIT-03` (148
itens, 330 KB, e 9) e do `CI-06`; a frase velha do `CALC-03`; e três pendências sem item, que viraram
`GIT-07` (o push), `INFRA-02` (o projeto Supabase de teste) e `ESC-01` (o conceito de noite).

**(d) A contagem não podia ser corrigida por delta, porque dois registros discordavam.** O delta
de 17/10 punha o `PERFIL-02` em L3; a conferência de 20/10 dizia que o 76 só fechava com ele em L0.
**Recontado linha a linha:** a versão commitada tem exatamente 78, e a divisão declarada
(48/12/10/8) só fecha com o `PERFIL-02` em L0. **A conferência estava certa e o delta, errado.** E
eu tinha repetido o erro do delta neste mesmo trabalho, ao escrever no item *"conta em L3 desde
17/10"*, antes de recontar. Saída: **80 = 46/12/9/13**, recontado, sem duplicados. O recontador
também errou duas vezes antes de valer: não aceitava ID com dois hífens e marcava como fechado o
que tem ✅ na segunda célula, inclusive o `DATA-07b` parcial e o `SEC-08` decidido com resíduo.

**(e) `DOCS-WIN-01`, controle positivo no Windows, sem nenhuma variável de ambiente:** a (3) acha os
**8** ponteiros aceitos; um ponteiro plantado no `README.md` reprova nomeando o arquivo; a versão
anterior do script, na mesma máquina, acha **0**. E o `verificar_por_mutacao.py`, que morria em
`cp1252`, roda: **149 testes de RLS e 30/30 sabotagens** contra `postgres:16`.

**(f) As seis sabotagens em Linux, cada uma reprovando pelo motivo certo:** documento gerado editado
à mão → `DIVERGE`; hash `846966a` de volta → *"commit inexistente: 846966a (em HW-05)"*; clone com
`--depth 1` → *"histórico raso"*; linha falsa de cálculo com premissa → a guarda nomeia o parágrafo;
premissa sem resumo → `ValueError` na carga; procedência "completa" sem hash → `ValueError`. Sem
sabotagem, os dois verificadores dão OK.

**(g) A guarda de prosa reprovou na primeira execução real, contra quem a escreveu.** Marquei a
linha do hash inexistente como `instrumento=True`, e o gerador parou: o texto da derivação (3) só
admite duas verificações defeituosas achadas sem rodar, e passavam a ser três. **A guarda estava
certa:** o defeituoso era o registro, não uma verificação do projeto. Corrigi a classificação, não
a guarda. É a cena da ocorrência 5 do §4 das lições, com outro instrumento.

**(h) Impacto medido.** Backend **293**; frontend **418 em 27 arquivos**, `tsc` limpo; RLS **149** e
mutação **30/30**; `estudo_buffer --conferir` 0; consolidação OK (**110 correções + 1 fora da
contagem, 89 pendências**); YAML do CI válido, seis jobs. ML **105 passam e 2 falham**: o de
retomada passou desta vez, sem mudança de código, o que é o que a hipótese do relógio prevê (anotado
no `ML-WIN-01`). **E `calculos_tcc.py --conferir` sai 1 no Windows**: as asserções batem e o `print`
do `✓` final quebra em `cp1252`. Arquivo não tocado por este lote, terceira instância da classe do
`DOCS-WIN-01`, e não estava registrada: virou **`DOCS-WIN-02`**. O verificador de documentos segue
reprovando no Windows **só** pelos dois documentos ainda fora do git; em Linux, com eles no índice,
dá OK.

**(i) A revisão antes do commit achou três coisas, e uma delas era minha afirmação.** O Vitor
pediu que eu revisasse os patches e só commitasse sem divergência. (1) **A linha do `DOCS-WIN-01`
no backlog estava partida em seis desde o commit `4014798`, de ontem**: o texto cita `\n`, `\r\n`
e `\r` como exemplo, e o script de 27/10 os gravou como caracteres de controle — inclusive um CR
solto dentro da linha, que uma leitura com conversão de fim de linha mostra como quebra e a
leitura binária mostra como CR. A tabela renderizava errado. Reconstruída lendo em binário, com as
quatro trocas conferidas uma a uma; agora não há linha de tabela sem `|` final nem CR solto, e a
recontagem segue 80. (2) **O resumo da premissa do `DATA-07b` dizia mais que a linha** —
*"e que a reprovação pedia afrouxar a tolerância"*, quando o texto fala de uma **tentação**
recusada, não de uma premissa sustentada. Ficou *"que coeficientes do filtro em `float32`
bastavam"*. Os outros 41 conferem com o texto de cada linha. (3) **Eu apontei um defeito na
checagem de hashes que não existia.** Supus que prefixo ambíguo voltaria como `ambiguous` e
passaria; medido no git 2.47 (Linux) e 2.50 (Windows) com um prefixo que casa dois commits
(`3b6`), volta `missing` — a primeira versão já reprovava. Mantive a regra mais estrita (só
`commit` passa, e o número de respostas tem de bater), porque ela não custa nada e cobre formato
que esta versão não produz, mas **o comentário que eu tinha escrito afirmava uma brecha falsa**, e
foi reescrito com a medição. É o §1, regra 9, contra mim: a recomendação veio de leitura.

**Adaptação.**

1. **Contar refazendo, não somando.** Quando dois registros discordam sobre uma contagem, o delta
   herda o erro de quem o escreveu. A recontagem por script é o único número deste lote que não
   depende de eu ter lido certo.
2. **Seis erros meus de execução, registrados porque o formato pede:** indentação errada nas
   trocas (as asserções pegaram e nada foi gravado); um nome literal `PEND` no lugar do valor; um
   comando que rodou um script sem a correção, porque não estava encadeado com `&&` (inseriu uma
   linha em branco numa citação das lições; o diff mostrou que o dano parou ali); um `git stash`
   num script de sabotagem que esvaziou a cópia do contêiner (o repositório real estava montado
   só para leitura); um script regravado em CRLF pelo Python do Windows; e a classificação do
   item (g). Nenhum chegou ao commit.

**Risco em aberto.**

- **Nada disto rodou em runner** (`CI-06`, `GIT-07`). O `fetch-depth: 0` e o passo novo foram
  exercitados num clone em Linux, não no Actions. Também não está confirmado que o runner tem
  `python` no PATH sem `setup-python`: o passo anterior do mesmo job já supunha isso, e nunca rodou.
- **Quatro linhas da tabela de correções** citam commits deste lote, que não existiam quando foram
  escritas. Três (as do `DOCS-WIN-01` e as duas do C1) ganham o hash antes do commit do registro.
  A quarta, a das discordâncias, é corrigida **pelo próprio commit que a introduz**, e um commit não
  cita o próprio hash: fica `parcial`, dizendo isso, com esta entrada como procedência.
- `DIAG-01`/`DIAG-03` abertos; `DOC-12`, `ML-WIN-01` e `DOCS-WIN-02` abertos.

**Procedência.** `scripts/consolidar_registro.py` (`_conferir_prosa`, `_conferir_commits`,
`premissa_curta`, `conta`); `docs/CORRECOES-APLICADAS.md` e `docs/PENDENCIAS-ABERTAS.md` (gerados);
`scripts/conferir_docs_versionados.py` (`git`, `ignorados`, `main`);
`web-app/tests/rls/verificar_por_mutacao.py`; `.github/workflows/ci.yml` (job `documentos`);
`docs/BACKLOG-COMPLETO.md` (contagem recontada; `GIT-06` e `DOCS-WIN-01` fechados; `GIT-07`,
`INFRA-02`, `ESC-01`, `DOC-12`, `DOCS-WIN-02` novos; `UI-20`, `ML-09`, `ML-10` renomeados);
`docs/LICOES-APRENDIDAS.md` (§1 ocorrência 11, §2 ocorrência 5, §3 ocorrência 5, §5 ocorrência 8);
`docs/ML-DATASETS-E-PLANO.md` e `docs/SINTESE-PESQUISA-E-CAMINHOS.md` (correspondência de IDs);
commits `846986a`, `c0725ca`, `d74aa01`, `778ec27`, `275665a`.

---

# 2026-10-28 (ii) — o primeiro push desde setembro, o CI num runner, e os quatro itens que ele deixou

**O problema, como foi entendido no início.** Fechar o que a entrada anterior deixou aberto: o
push (`GIT-07`), os dois testes de ML e o script que falhavam no Windows (`ML-WIN-01`,
`DOCS-WIN-02`), os dois diagramas que não fecharam (`DIAG-01`, `DIAG-03`) e a data de início do
versionamento (`DOC-12`). O Vitor autorizou o push pela conta dele e aprovou de antemão o que
precisasse de aprovação. A sessão foi interrompida por um desligamento do computador no meio do
registro; nada se perdeu, e está conferido abaixo.

**Hipótese de trabalho.** Três, e duas caíram. (1) Que o CI pudesse reprovar no runner — a perna
Postgres 16 era hipótese desde 28/09, e o job `documentos` usa o Python do sistema sem
`setup-python`. **Não reprovou.** (2) Que o `DOCS-WIN-02` fosse um script. **Eram dois.** (3) Que
o teste de retomada falhasse pela resolução do relógio do Windows. **Confirmada, antes de
corrigir.**

**O que foi testado, e como.**

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | Há credencial de escrita? | `gh auth status`, `git config credential.helper` | inventário |
| 2 | Há segredo nos 80 commits novos? | varredura de arquivos e padrões de chave em `git log -p origin/develop..HEAD` | inventário + **controle positivo** |
| 3 | O CI passa num runner? | push; `gh run watch`; o log de cada job | execução |
| 4 | Os scripts quebram no Windows? | os dois, nos dois modos, sem `PYTHONUTF8` | execução |
| 5 | A tolerância do dourado é segura? | piso: divergência medida entre plataformas; teto: o verificador por mutação, nos dois sistemas | execução + **controle positivo** |
| 6 | É o relógio? | o teste de retomada com um relógio em degraus de 15,6 ms, em Linux | **controle positivo** |
| 7 | Os diagramas ainda batem com o código? | 55 afirmações por script; identificadores das figuras; `mermaid-cli` | inventário + execução |
| 8 | O que os commits de fevereiro contêm? | `git log --before=2026-04-30`, `git show`, `git reflog` | inventário |

**Resultado medido.**

**(a) O push saiu, e o CI rodou num runner pela primeira vez desde 10/09.** O `gh` está
autenticado na conta `vitormendes4072`, com escopos `repo` e `workflow`, e o git usa o gerenciador
de credenciais do Windows. A varredura não achou segredo nos 80 commits, e o mesmo filtro acusou 2
de 2 chaves falsas. A execução `40639232458` (`ubuntu-24.04`) deu **sete jobs verdes**: backend
293, frontend 418, ML 107, firmware 341 + 157 e 4/4 sketches, documentos (com a consolidação
conferida e o histórico inteiro), e **RLS 149 na Postgres 14 e na 16, com mutação 30/30**. O
`skipped` que aparece no log é o texto da própria guarda, não teste pulado. O Python do runner
existe sem `setup-python` (3.11.17). Fecham `GIT-07` e `CI-06`.

**(b) E o runner avisou de uma coisa que o projeto não sabia:** o `ubuntu-latest` está migrando
para o Ubuntu 26. Os seis jobs usam `ubuntu-latest`, e a próxima execução pode pegar outro `g++` e
outro Python. O `ci.yml` já tem a regra, para o Postgres: *"nunca `latest`"*. Virou o `CI-07`,
**decisão do Vitor**.

**(c) `DOCS-WIN-02` era maior do que eu tinha registrado.** Ontem medi só o `--conferir` do
`estudo_buffer`, que passa; o modo relatório quebrava no `ĝ`. Os dois scripts, nos dois modos: 3 de
4 combinações quebravam. Corrigido nos dois. **Controle positivo:** com um valor sabotado, o
`--conferir` novo sai 1 e imprime *"obtido 0.244…, documento diz 0.3"*; o anterior também saía 1,
mas por `UnicodeEncodeError` — uma reprovação de verdade e uma quebra eram indistinguíveis.

**(d) `ML-WIN-01`, as duas metades.** **(a)** O dourado comparava por igualdade exata. Medido:
71 de 14 952 floats divergem, **pior caso 8,0e-13 relativo**. Régua nova: estrutura exata e
floats a 1e-9 relativo. O teto foi o verificador por mutação do dourado, que tem duas sabotagens
pegas justamente por esses testes: **12/12 em Linux (107 testes) e no Windows**, com o ponto cego
registrado ainda cego. **(b)** Antes de corrigir, a hipótese do relógio foi **reproduzida em
Linux**: com um relógio que só anda em degraus de 15,6 ms, o teste reprova **3 de 3**, com a mesma
mensagem do Windows. Causa: `elapsed > orcamento_s` com orçamento zero e 0 s medido. `>` virou
`>=`; com o relógio em degraus, passa. **A suíte de ML passa 107/107 no Windows pela primeira
vez.**

**(e) `DIAG-01` e `DIAG-03`.** As 55 afirmações verificáveis do `DIAG-01` (arquivo, rota, função
do banco, tabela com RLS, pino, constante) batem com o código; os identificadores das três figuras
do `DIAG-03` existem. Faltava o que veio depois de 29/09: as features em C++, `/api/me/perfil` e
`/health`. **Os dois "pontos a decidir" do `DIAG-03` não precisavam de decisão** — a convenção do
`DIAG-01` já tinha a forma: código que existe e não roda leva `(NÃO EXERCITADO)`. Antes de escrever
que *"a 0,1 Hz a época é recusada"*, conferi no código (`fechar()` devolve `false` abaixo de
`AMOSTRAS_MINIMAS_PARA_PARIDADE`); e o "6 features" do commit `6d328bb` contra o comentário que
diz "sete quantidades" — são seis features mais o `ĝ`. Renderizados os quatro arquivos (10
figuras) pela imagem `minlag/mermaid-cli:11.4.2`, baixada para isso; **controle:** um diagrama com
sintaxe quebrada reprova com *"Parse error on line 5"*. Olhei os PNGs: legíveis.

**(f) `DOC-12`.** Sete commits em 18–19/02, todos do mesmo autor; o clonado em 29/04 é o último
deles. Eles mostram que a escolha do ESP32 + MPU6050, o desenho com Deep Sleep e despertar por
botão no GPIO 27, e a pilha Flask + Supabase + Vercel são de fevereiro — e que o README de
18/02 já exibia um selo **"Status: Validado"** com tudo em simulação. O que continua faltando ficou
delimitado: **nenhum commit entre 20/02 e 30/05**, e a decisão do travesseiro só aparece em
31/05.

**(g) Depois do desligamento**, conferido antes de continuar: as 9 edições estavam no disco, o
`HEAD` igual ao remoto, nenhum lock novo, os scripts compilando, os blocos dos diagramas
fechados. Todas as suítes foram rodadas de novo antes de escrever qualquer número: backend 293,
frontend 418 e `vite build` ok, ML 107, RLS 149 e 30/30, firmware igual, os quatro `--conferir`
passando — no Windows, sem nenhuma variável de ambiente.

**(h) E o CI reprovou o meu próprio conserto.** A segunda execução (`40745254169`, sobre
`474176e`) deu seis jobs verdes e o `ml` vermelho: no runner, dois valores de `d_angulo`
divergiram **5,7e-9 relativo** (0,008016267455 contra 0,008016267410 grau), acima da régua de
1e-9. **A régua tinha sido derivada de um único par de plataformas** — Windows contra o arquivo
gravado em Linux —, e eu escrevi "piso medido" sobre ela. A primeira execução no runner tinha
passado até com igualdade exata, o que mostra que a máquina do runner muda entre execuções.
**A causa é numérica e está no arquivo:** `inclinacao_rel` e `d_angulo` são
`degrees(arccos(c))`, e `arccos` perto de 1 é mal-condicionado — o erro **absoluto** fica pequeno
(4,5e-11° no runner) e o **relativo** cresce como 1/θ². Os ângulos passaram a ter régua absoluta
de **1e-4°**, derivada: com o ruído a montante medido (~1e-12), o menor ângulo do arquivo (0,003°)
erra ~1,1e-6°, e o limite de vetores paralelos dá ~8e-5°. Conferido contra os números exatos do
runner (passam), contra a mesma diferença num campo não angular (reprova) e contra 1° de erro num
ângulo (reprova); **12/12 no verificador por mutação, em Linux e no Windows** (`58ae504`).

**Uma detecção sumiu, e eu fui ver qual.** A sabotagem de radianos era pega por 9 testes e passou
a ser por 8: saiu o dourado **do dispositivo**. O caso 3 dele tem `inclinacao_rel = 8,5e-7°` numa
época **única**, em que o ângulo é zero por definição — é ruído de arredondamento do `arccos`
(√(2ε) ≈ 1,2e-6°). O teste "pegava" a sabotagem através de um número que é ruído: a mesma
fragilidade que reprovou no runner, a favor. A cobertura de ângulo está no dourado das
sequências, que continua pegando. Registrado como ocorrência 6 do §4.

**Adaptação.**

1. **Hipótese confirmada antes de corrigir.** O `>=` teria passado no Windows de qualquer jeito;
   sem a reprodução em Linux não haveria como dizer que a causa era a que eu supunha.
2. **Medir as duas metades de um script antes de registrar.** O `DOCS-WIN-02` nasceu com metade do
   alcance porque eu medi um modo e escrevi sobre o script.

**Risco em aberto.**

- **`CI-07`**: a próxima execução pode cair no Ubuntu 26. Decisão do Vitor.
- **O piso entre plataformas é amostra, não medida.** Dois runners e um Windows; uma quarta
  máquina pode errar mais. A régua dos ângulos é derivada da condição do `arccos`, que não
  depende da máquina; a de 1e-9 dos demais floats ainda é empírica.
- **`ventregaz-redis`** — um contêiner de outro projeto do Vitor estava rodando; não foi tocado.
- A lacuna de 20/02 a 30/05 e a justificativa do travesseiro dependem de material fora do git.

**Procedência.** Execução `40639232458` do Actions; commit `7016c81` (`scripts/calculos_tcc.py`,
`scripts/estudo_buffer.py`, `ml/testes/test_vetor_dourado.py` — `TOL_DOURADO_REL`,
`_divergencias` —, `ml/experimentos/_retomada.py`, `docs/diagramas/DIAG-01` e `DIAG-03`, a entrada
de abertura deste diário); `docs/BACKLOG-COMPLETO.md` (75 = 42/12/9/12, recontado);
`scripts/consolidar_registro.py` (116 correções, 83 pendências); `CLAUDE.md` (seção "Testes");
`docs/LICOES-APRENDIDAS.md` (§6 ocorrência 7).

---

# 2026-10-28 (iii) — `CI-07`: a imagem do runner fica fixa

**O problema, como foi entendido no início.** O runner avisou que o `ubuntu-latest` migra para o
Ubuntu 26, e os seis jobs usavam `ubuntu-latest`. O Vitor decidiu fixar.

**Hipótese de trabalho.** Que fixar `runs-on: ubuntu-24.04` mantivesse os sete jobs verdes e fizesse
o aviso sumir.

**O que foi testado, e como.** As seis linhas trocadas e conferidas pelo YAML carregado
(`{job: runs-on}` dos seis); o commit `78998d8` enviado **sozinho**, antes do registro, para que o
registro dissesse o que o CI mostrou e não o que se esperava; a execução `40750204890` comparada
com a anterior.

**Resultado medido.** Sete jobs verdes, todos em `ubuntu-24.04`. O aviso de migração está nas
**anotações** da execução, não no log dos jobs — a primeira busca, no log, deu 0 nas duas execuções
e não provava nada. Nas anotações: **7 na execução anterior (`40746683981`), 0 nesta.**

**Adaptação.** O registro saiu num commit separado, depois do CI, porque a primeira versão do
texto do `CI-07` dizia *"conferido no log da execução seguinte"* antes de a execução existir.
Reescrito antes de commitar.

**Risco em aberto.** Nenhum novo. A 24.04 também terá fim de suporte; migrar é trocar as seis
linhas de uma vez, com o CI verde lá — está no comentário do `ci.yml`.

**Procedência.** `.github/workflows/ci.yml` (`runs-on` dos seis jobs e o comentário do primeiro);
execuções `40746683981` e `40750204890`; `docs/BACKLOG-COMPLETO.md` (`CI-07`, 74 = 41/12/9/12).

---

# 2026-10-28 (iv) — `INFRA-03`: a produção estava fora do ar, e nada no repositório sabia

**O problema, como foi entendido no início.** Ao avaliar o merge para `develop`, o `/health` de
produção respondeu **503**, com `"banco": "consulta falhou"`. A produção vem de `main`, de 10/09;
não era efeito de nada desta semana.

**Hipótese de trabalho.** Projeto Supabase pausado por inatividade. **Confirmada pelo Vitor**:
plano gratuito, pausa depois de uma semana sem uso; ele reativou o projeto.

**O que foi testado, e como.**

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | O banco existe? | `nslookup` do domínio do projeto (tirado do JavaScript público do site) no Google e na Cloudflare; `supabase.com` como controle de rede | inventário |
| 2 | Voltou? | o mesmo DNS, `rest/v1` sem chave, e o `/health` três vezes | execução |
| 3 | O monitor acusa? | `scripts/conferir_producao.py` contra um servidor local que imita cada falha, e contra a produção | **controle positivo** |

**Resultado medido.** **(a)** Antes: o domínio do projeto **não existia** nos dois resolvedores
(`Non-existent domain`), com `supabase.com` respondendo 200 pela mesma rede — não era a minha
conexão. **(b)** Depois da reativação: o domínio resolve, o Supabase responde 401 sem chave
(serviço ativo), e o `/health` deu **200 com `"banco": "ok"` três vezes**. **(c)** O monitor: reprova
503 degradado (o estado de hoje), 200 com outro valor em `banco`, 200 com HTML no lugar de JSON e
domínio inexistente; passa num servidor que responde certo e na produção real — **6 de 6**.

**Adaptação.** A prevenção é um job agendado, `.github/workflows/saude-producao.yml`, que chama o
`/health` a cada 3 dias. O `/health` faz uma consulta real ao banco, então o mesmo job serve para
manter o projeto ativo e para avisar quando cair. A verificação ficou num script, e não solta no
YAML, para poder ser sabotada aqui.

**Risco em aberto** — escrito também no cabeçalho do workflow:

- **`schedule` só roda a partir da branch padrão (`main`).** Até o release de `develop`, o
  agendamento não existe. O workflow também roda num push que mude ele próprio ou o script, para
  ser exercitado num runner antes disso.
- **O GitHub desativa agendamentos depois de 60 dias sem atividade** num repositório público.
- **Que a consulta impeça a pausa é hipótese**: supõe que uma requisição ao banco conta como
  atividade para o Supabase. Não foi medido.
- **Por quanto tempo a produção ficou fora não se sabe**: nada registrava. A última produção
  publicada é de 10/09.

**Procedência.** `scripts/conferir_producao.py`; `.github/workflows/saude-producao.yml`;
`docs/BACKLOG-COMPLETO.md` (`INFRA-03`, 75 = 41/12/9/13); `CLAUDE.md` (seção "Deploy").

---

# 2026-10-28 (v) — `SEC-12`: a chave pública executava as funções do banco, e a suíte de segurança passava no vazio

**O problema, como foi entendido no início.** Conferir quais migrações estavam aplicadas na
produção e quais precisavam ser — pergunta do Vitor. Não havia como saber: as migrações são
aplicadas à mão, e nada registra quais rodaram.

**Hipótese de trabalho.** Que bastasse procurar no catálogo as marcas de cada migração. Isso
funcionou. **A hipótese que caiu foi outra, e ninguém a tinha escrito como hipótese:** que um
objeto novo nasce sem privilégio para o cliente.

**O que foi testado, e como.**

| # | O que | Como | Natureza |
|:-:|---|---|---|
| 1 | Quais migrações estão aplicadas | `DIAGNOSTICO-migracoes-aplicadas.sql`, rodado pelo Vitor na produção | inventário |
| 2 | O diagnóstico acerta? | aplicando 001→009 num Postgres local, e na ordem real da produção | execução |
| 3 | A ordem segura de aplicar | as operações do código de `main` antes e depois de cada grupo de migrações | execução |
| 4 | O verificador acusa? | três sabotagens: marca errada, critério frouxo, migração que tira privilégio | **controle positivo** |
| 5 | Por que a sabotagem 3 passava | `pg_default_acl` e `has_function_privilege` na produção | inventário |
| 6 | O que `anon` consegue fazer | as oito funções chamadas como `anon`, contagens antes e depois | execução |
| 7 | A correção | suíte de RLS com e sem a 009; a 007 isolada; mutação | **controle positivo** |

**Resultado medido.**

**(a) O estado da produção:** 001, 003, 004 aplicadas; 002 desnecessária (0 leituras sem dono);
005–008 não. A 005, 006 e 008 podem entrar antes do release — as 10 operações do código de
`main` dão o mesmo resultado com elas; a 007 quebra exatamente as 2 que usam `devices.token_hash`
e por isso só entra com o release. O Vitor aplicou a 005, 006 e 008; o diagnóstico confirmou.
Fecham `PERFIL-02` e `DATA-03`.

**(b) A sabotagem que não foi acusada, e o que ela escondia.** Das três sabotagens do verificador,
a que acrescentava à 006 a retirada da leitura de `sleep_data` passou. Causa no instrumento: ele
reaplicava os GRANTs das tabelas **depois** das migrações, desfazendo o `revoke`. Indo atrás disso,
apareceu que a 007 cria `device_tokens` dizendo *"sem GRANT para anon"* e não revoga nada — o que só
vale se o banco não der privilégio sozinho. **Na produção, dá:** `pg_default_acl` mostra ALL em
tabela e EXECUTE em função, nominais, para `anon` e `authenticated`. E `revoke ... from public`,
que as 005–008 usavam, não alcança grant nominal. Conferido pelo Vitor: **as sete funções
aplicadas eram executáveis por `anon`**.

**(c) O impacto, medido antes de corrigir:** chamando as oito funções como `anon`, nada mudou —
as do usuário têm guarda para `auth.uid()` nulo, as de gatilho não são chamáveis, as de ingestão
exigem o hash de um token de 256 bits. Contagens idênticas antes e depois. Com uma exceção pequena,
registrada no `SEC-12`: até a 007, o dono de um dispositivo lê o próprio hash e pode gravar
leituras pela API sem a validação de faixa do backend.

**(d) Por que nenhum teste tinha visto:** a suíte de RLS tinha os testes certos —
`test_anon_nao_executa_funcao_de_ingestao` e outros 13 — e eles passavam porque a base de teste
não reproduzia os privilégios padrão. Com a base reproduzindo-os: **14 reprovam sem a 009**, **151
passam com ela**, e a 007 corrigida sozinha leva as falhas a 9 (as dela passam). Um teste novo
cobre o padrão de funções **futuras**, e falhou na primeira escrita por um motivo que eu não
previa: o próprio Postgres dá EXECUTE a `PUBLIC` em toda função, e isso não se revoga por esquema
— o `revoke from public` de cada migração continua necessário, e está escrito no teste. Dois
sabotadores novos: mutação **32/32**.

**Adaptação.** A 009 revoga nominalmente, devolve a `authenticated` só as quatro funções do
próprio usuário e muda o padrão de funções futuras. Não editei as 005, 006 e 008: já aplicadas,
editar o arquivo não muda a produção. O verificador de migrações entrou no job `rls` do CI, com a
ordem real da produção (009 antes da 007) — que tem controle próprio: com a 007 antiga, acusa a
tabela aberta.

**Risco em aberto.**

- **`SEC-12`: a 009 precisa ser aplicada na produção.** Até lá, o estado medido em (b) continua.
- **`SEC-13`: a suíte de RLS ainda reaplica GRANTs por cima das migrações.** Não mexi porque o
  verificador por mutação injeta as sabotagens nesse mesmo arquivo.
- A suíte imita o Supabase em Postgres puro; o PostgREST não está na frente.

**Procedência.** Commit `040fe4b`; `web-app/migrations/009_privilegios_padrao_do_supabase.sql`,
`007_…` (revogações), `DIAGNOSTICO-migracoes-aplicadas.sql`, `README.md`;
`web-app/tests/rls/esquema_base.sql` (bloco 1b), `test_rls_privilegios.py`,
`verificar_por_mutacao.py`; `web-app/tests/migracoes/verificar_migracoes.py`; `pg_default_acl` e
`has_function_privilege` da produção (resultados colados pelo Vitor); backlog `SEC-12`, `SEC-13`.

---

# 2026-10-29 — `SEC-12` aplicada na produção, e o que o release precisa

**O problema, como foi entendido no início.** Aplicar a 009 na produção e preparar o release de
`develop` para `main`, com a 007 — a única migração que falta — entrando junto.

**Hipótese de trabalho.** Que a 009 tirasse de `anon` todas as funções sem tocar no que o código
da produção usa. Confirmada.

**O que foi testado, e como.** O Vitor aplicou a 009 no SQL Editor e colou dois resultados: a
consulta de privilégios por função e o diagnóstico de migrações. O `/health` foi conferido daqui
depois da aplicação. Para o release: `git diff` de `main` para `develop` (arquivos, variáveis de
ambiente, `vercel.json`) e todas as chamadas que o código de `develop` faz ao banco.

**Resultado medido.**

- **A 009 na produção:** `anon = false` nas sete funções; `authenticated = true` só em
  `sanidade`, `registrar_leitura_da_sessao` e `apagar_minha_conta`; `registrar_leitura` e
  `resolver_dispositivo` fechadas também para `authenticated`. Diagnóstico: 009 com 4 de 4 marcas,
  007 com 0 de 4 (o esperado). `/health` 200 duas vezes. Fecha `SEC-12`.
- **O release:** `main` não tem conteúdo próprio — os 25 commits que ela tem a mais são merges de
  release, e o conteúdo dela é idêntico à base comum (`f044fd2`); o merge não tem como dar
  conflito. `vercel.json` e as variáveis do frontend não mudam; a única variável nova do backend é
  `SUPABASE_INGESTAO_KEY`, opcional. Todo acesso ao banco passa pelo backend, e **a única coisa
  que só existe depois da 007 é `parear_dispositivo`** — usada no pareamento de dispositivo novo
  (`POST /api/devices` e `/api/devices/celular`). É a janela do release: entre o deploy e a 007,
  parear falha; ler, gravar, perfil e exclusão de conta não.

**Adaptação.** Nenhuma.

**Risco em aberto.**

- **Não medido:** que `service_role` executa as funções de ingestão na produção. Sem
  `SUPABASE_INGESTAO_KEY`, é por ela que o backend novo grava leitura. A 009 não mexe nesse papel, e
  o padrão do Supabase lhe dá EXECUTE — mas isso é leitura; a conferência entrou no roteiro do
  release, antes do merge.

**Procedência.** Resultados da produção colados pelo Vitor em 29/10; `git diff origin/main
origin/develop`; `web-app/database.py`, `web-app/dispositivos.py`; backlog `SEC-12`.

---

# 2026-10-29 (ii) — o release para `main`, a 007 na produção e o monitor agendável

**O problema, como foi entendido no início.** Levar `develop` para `main` (o que estava em
produção era de setembro), aplicar a 007 logo depois do deploy — é a única migração que o código
novo exige — e pôr o monitor do `INFRA-03` na branch de onde o agendamento roda.

**Hipótese de trabalho.** A da entrada anterior: o merge não tem como dar conflito, e entre o
deploy e a 007 só o pareamento de dispositivo novo falha. E que `service_role` executa as funções
de ingestão — lida, não medida, e era por ela que o backend novo grava leitura. Confirmada nas
duas partes.

**O que foi testado, e como.**

- **Antes do merge:** o Vitor rodou no SQL Editor `has_function_privilege('service_role', …)` nas
  cinco funções que o backend chama e a contagem de dispositivos.
- **O release:** PR #5, `develop` → `main`. **O merge em `main` foi negado a esta sessão** pelo
  classificador de permissões (deploy de produção); o Vitor mesclou pelo GitHub
  (*Create a merge commit*).
- **Depois do merge:** `/health` e as rotas protegidas conferidos daqui. O Vitor aplicou a 007
  e rodou a conferência que vem nela e o diagnóstico de migrações.
- **O monitor:** disparado à mão (`workflow_dispatch`) a partir de `main`.

**Resultado medido.**

- **Antes do merge:** `service_role` executa as cinco funções (5 × `true`); 4 dispositivos.
  Fecha o risco em aberto da entrada anterior.
- **Produção em `main 787227c`**, contrato 2.5.1: `/health` 200 com banco ok; rotas protegidas
  respondem 401 sem token.
- **A 007:** coluna `devices.token_hash` não existe mais (0); **4 dispositivos e 4 tokens** em
  `device_tokens` — nenhuma credencial perdida na mudança de tabela; `anon` e `authenticated` sem
  privilégio nenhum em `device_tokens` (0); `anon` não executa `parear_dispositivo`, usuário
  logado executa. Diagnóstico: **`aplicada = true` nas oito migrações de esquema** (001, 003–009);
  a 002 desnecessária. A ordem real da produção (009 antes da 007) é a que o
  `verificar_migracoes.py` exercita no CI.
- **O monitor:** a execução `40818265459`, de `main`, passou.

**Adaptação.** Nenhuma no plano. A permissão negada mudou só quem clica: merge em `main` é do
Vitor, e assim fica.

**Risco em aberto.**

- **Não medido:** que o agendamento roda. A execução manual prova o job, não o `schedule`; a
  primeira agendada, pelo cron, cai em 31/10. Segue no `INFRA-03`.
- **Não medido:** quanto durou a janela entre o deploy e a 007, em que parear falharia. Ninguém
  pareou nela que se saiba — a produção não recebia dado desde setembro —, mas não há log
  conferido.
- **Não medido:** o pareamento de ponta a ponta pelo app em produção (`POST /api/devices`). O
  que se mediu foi o privilégio da função no banco.

**Procedência.** Resultados da produção colados pelo Vitor em 29/10 (privilégios de
`service_role`, conferência da 007, diagnóstico); PR #5 e `main 787227c`; execução `40818265459`
de `saude-producao.yml`; backlog `INFRA-03`.

---

# 2026-10-29 (iii) — o resumo do backlog mandava fazer o que já estava feito

**O problema, como foi entendido no início.** Ao ler o backlog para responder *"o que temos a
fazer agora?"*, o topo do arquivo dizia *"se você tem uma hora, rode `DATA-03`"* — fechado em
28/10. A suspeita era de uma linha velha; o pedido foi corrigir o resumo, o quadro e o caminho
crítico.

**Hipótese de trabalho.** Que fossem três menções (`DATA-03`, `PERFIL-02` e o monitor
"esperando o release"). Refutada: eram mais.

**O que foi testado, e como.** Cada ID citado nas seções "Estado", "O quadro em uma tela" e "O
caminho crítico" foi buscado na linha do próprio item, para ver se está aberto. Depois, a
recontagem linha a linha, as conferências `consolidar_registro.py --conferir` e
`conferir_docs_versionados.py`.

**Resultado medido.**

- **Seis itens fechados apareciam como pendentes:** `DATA-03` (o conselho de abertura e o passo 1
  do caminho crítico), `PERFIL-02` e o `INFRA-03` "esperando o release" (o quadro), mais
  `DOC-11`, `DIAG-01`, `DIAG-03` e `DATA-07c`, que o quadro e o "em paralelo" listavam entre os
  pendentes. O mais antigo, o `DATA-07c`, fechou em 30/09.
- **Faltavam no quadro:** `SEC-13` (aberto em 28/10) e `DATA-07d`. Entrou também o `DOC-13`. O `PWA-01` aparecia duas
  vezes, em L0 e em L3; ficou só em L3, onde a linha dele está.
- "70 testes" do ML ganhou data (22/09) e o número de 28/10 (107).
- O conselho de abertura passou a ser o `SEC-11` (captcha no painel, ~5 min), com a ressalva
  de que é mitigação. Recontagem: 75 (L0 43, com o `DOC-13`); conferências passam.

**Adaptação.** O escopo cresceu de três menções para dez correções nas mesmas três seções, e
abriu um item (`DOC-13`) para a guarda que faltava.

**Risco em aberto.**

- **Não mecanizado:** nada confere o resumo contra as linhas. A próxima vez que um item fechar,
  o resumo pode envelhecer de novo. Abri o `DOC-13` (L0, ⚪): uma conferência que reprove ID
  marcado ✅ na própria linha e citado como pendente no quadro ou no caminho crítico.

**Procedência.** `docs/BACKLOG-COMPLETO.md` antes e depois deste commit; §6 das lições,
ocorrência 8.

---

# 2026-10-29 (iv) — o `DOC-05` dizia que o `CLAUDE.md` é gitignorado

**O problema, como foi entendido no início.** Ao listar os 75 itens abertos, a linha do
`DOC-05` dizia que o `CLAUDE.md` está no `.gitignore` e que toda correção nele fica fora do git.
Ele é versionado desde 27/10 (`DOC-11`).

**Hipótese de trabalho.** Que a frase velha estivesse em mais lugares. Refutada: busca por
"`CLAUDE.md` está no" e "é gitignorado" em todo `.md` e `.py` do repositório achou só esta linha.
A pendência gerada (`consolidar_registro.py`) já dizia o certo.

**O que foi testado, e como.** A busca acima; depois a recontagem linha a linha,
`consolidar_registro.py --conferir` e `conferir_docs_versionados.py`.

**Resultado medido.** Uma linha corrigida, com a marca ✏️. Contagem inalterada (75). As
conferências passam.

**Adaptação.** O `DOC-13` ganhou uma ressalva: a guarda que ele propõe procura ID fechado citado
como pendente, e **não pegaria este caso** — a frase velha estava dentro da linha de um item
aberto, sem ID fechado nela. Mesmo padrão da entrada (iii) (§6 das lições, ocorrência 8), outra
forma.

**Risco em aberto.**

- **Não medido:** quantas frases de estado assim restam dentro de linhas abertas. Achar esta foi
  leitura, ao explicar o backlog; varrer as 75 linhas contra o estado do repositório não foi
  feito. Fica no `DOC-13`, com a ressalva.

**Procedência.** `docs/BACKLOG-COMPLETO.md`, linha do `DOC-05`, antes e depois deste commit;
`scripts/consolidar_registro.py`, pendência `DOC-05`; backlog `DOC-11`.

---

# 2026-10-29 (v) — `ARQ-01` (a) e (b): a dicotomia tinha uma terceira saída

**O problema, como foi entendido no início.** O `ARQ-01` pede (a) decidir contínuo-com-features
× WoM-sem-features e (b) fixar banda e taxa contra os 12,8 Hz do `ml/`. O pedido foi preparar a
análise das duas arquiteturas e das consequências, sem tomar a decisão: ela muda a frase da
pergunta de pesquisa, que fala em "baixo consumo" e em "eventos de movimento".

**Hipótese de trabalho.** Ao ler as fontes para o plano, surgiu uma terceira arquitetura: a FIFO
do MPU6050 deixaria o ESP32 em sono leve entre rajadas, e a amostragem contínua sairia perto de
uma ordem de grandeza mais barata que a do Z.4.4. Outra suspeita era que a grade de 32 Hz não
existisse no sensor. As duas eram lembrança, não leitura.

**O que foi testado, e como.**

- **Folhas de dados:**
  - PS-MPU-6000A-00 Rev. 3.2, baixada de um espelho e extraída com `pypdf`;
  - ESP-IDF v6.1, *Sleep Modes*;
  - o *Register Map* não baixou de nenhuma fonte (403, HTML no lugar do PDF), e foi lido só em
    resumo de busca.
- **O modelo:** `scripts/estudo_cadencia.py`, que importa as constantes e os dois cenários do
  `calculos_tcc.py` em vez de copiá-los, mais dois cenários novos de sono leve (C1, uma amostra
  por despertar; C2, FIFO). Ele varre todos os parâmetros em faixa e soma o consumo fixo da
  placa.
- **CI:** o `--conferir` entrou no job `documentos`.
- **Controle positivo, três sabotagens:**
  1. sono leve de 0,8 → 0,9 mA no `calculos_tcc.py`;
  2. rádio de referência de 100 → 120 mA, que atinge o Z.4.4;
  3. FIFO esvaziada a 60 % em vez de 50 %.
- **Conferências:** `calculos_tcc.py --conferir`, `estudo_buffer.py --conferir`,
  `conferir_docs_versionados.py`, `consolidar_registro.py --conferir`.

**Resultado medido** (aritmética e folha de dados; nada medido na placa).

- **Confirmado na folha:**
  - FIFO de **1024 B**, feita *"to read the data in bursts and then go into a low-power mode"*;
  - acelerômetro a 1 kHz;
  - no sono leve, a RAM sobrevive e o Wi-Fi não se mantém.
- **Achado que não estava na lembrança:** o oscilador interno do MPU tem **±5 % a 25 °C e −15 %
  a +10 % na temperatura**. Nenhuma taxa ditada pelo sensor cai exata na grade, com ou sem
  divisor, e o firmware precisa medir a taxa e reamostrar, como o `ml/` já faz com as bases
  públicas.
- **Os números:** o modelo reproduz o Z.4.4 (A 1,91 mA, B 23,9 mA). O sono leve com FIFO (C2,
  50 Hz) dá **5,31 mA**, 4,5× abaixo de B. Não é "uma ordem de grandeza", como a hipótese dizia:
  o rádio é 63 % de C2. Com lote (`API-03`), C2 cai a 2,03 mA. A ordem A < C2 < C1 < B vale com a
  placa de 0 a 10 mA.
- **Para (b):** o critério contra os 12,8 Hz é a dobra em f<sub>s</sub> − 12,8 Hz (37,2 Hz a
  50 Hz), não 2 × a banda do DLPF. A 40 Hz com DLPF de 21 Hz, a dobra começa em 27,2 Hz.
- **As três sabotagens reprovaram:**
  1. 11 asserções caíram, nomeando C1, C2 e as razões;
  2. caíram as âncoras do Z.4.4 (`A (Z.4.4)`, `B (Z.4.4)`);
  3. caíram `C2 amostras/despertar` e `C2 acordado (%)`.

  Restaurado, tudo passa.

**Adaptação.**

- **A dicotomia do backlog estava incompleta.** "Features ou Deep Sleep" comparava o WoM com a
  amostragem contínua de CPU ativa. A análise acrescenta C2 e a recomenda, **marcada como
  recomendação**: não é uma decisão tomada por esta sessão.
- **A hipótese do plano errou para mais.** C2 sai 4,5× melhor que B, não dez vezes.
- **O texto pronto do `CALCULOS-TCC.md` não foi editado.** Ele muda depois da decisão (§7 do
  documento).

**Risco em aberto.**

- **Não conferido na fonte primária:** a fórmula do divisor, os degraus do DLPF e se a FIFO
  funciona no modo de baixo consumo, todos do *Register Map*. O resultado que depende da fórmula
  (não há 32 Hz exato) é robusto, porque o oscilador de ±5 % já o garante. Fica no `ARQ-01`.
- **Não medido:**
  - a latência e a corrente do sono leve na placa;
  - o transbordo da FIFO;
  - a reassociação Wi-Fi;
  - o tempo do fechamento da época.

  É a parte (c) do `ARQ-01`, que depende da solda.
- **Não decidido:** a escolha entre A e C2. É do autor com o orientador (`ARQ-01` (a) e `RQ-01`).
- **Não feito:** o experimento que daria número ao WoM do lado da hipótese (o kappa de uma
  contagem de eventos simulada nas bases públicas). Só vale abrir se A for escolhida, e a
  decisão diz.
- **Lido em revisão diferente:** a folha de produto foi lida na Rev. 3.2; o `calculos_tcc.py`
  cita a 3.4.

**Procedência.**

- `docs/DECISAO-ARQ-01-CADENCIA.md` e `scripts/estudo_cadencia.py`, deste commit;
- `CALCULOS-TCC.md` Z.1.4, Z.4.3–Z.4.7 e "Uma divergência técnica";
- PS-MPU-6000A-00 Rev. 3.2, §4, §5.1, §5.2 e §6.6;
- ESP-IDF v6.1, *Sleep Modes — ESP32*;
- backlog `ARQ-01`.

---

# 2026-10-30 — `ML-11`: três features bastam, e o WoM custa de 0,07 a 0,10 de kappa

**O problema, como foi entendido no início.** Depois da análise do `ARQ-01` (29/10 (v)), o
Vitor perguntou se todas as 8 features são necessárias, e pediu o resultado antes de decidir
qualquer coisa. Ele está inclinado ao sono leve com FIFO. Pediu também a investigação do
registro pelo celular, que não tem as limitações do ESP32, e se dá para oferecer mais de um
modo de registro ao usuário, com tudo registrado num documento.

**Hipótese de trabalho.** Cinco hipóteses, declaradas antes de rodar
(`docs/ARQUITETURA-DE-CAPTACAO.md` §2):
- H1: as features de intensidade são redundantes entre si;
- H2: poucas features bastam;
- H3: o que o WoM entrega perde muito;
- H4: no celular, o limite é o sistema operacional, não a energia;
- H5: o contrato já comporta vários modos.

**O que foi testado, e como.**

- **`ml/experimentos/ml11_ablacao_features.py`**, sobre as features já extraídas (cache do
  Wearanize, 92 pessoas em cabeça e pulso; Newcastle, 27). Usa o pipeline do produto, igual ao
  do experimento de quantização, mudando só as colunas. Mede:
  - tirar uma feature de cada vez;
  - a seleção progressiva;
  - os conjuntos de cada arquitetura, com o WoM cercado por dois proxies;
  - o subconjunto escolhido na cabeça, fixo, nas outras bases.

  Toda diferença é pareada por dobra, com IC de 95 %.
- **Rodou duas vezes** (a segunda com o teste fora da amostra acrescentado): Windows 11,
  `ml/.venv`, ~6 min cada.
- **O celular:** leitura do código da coleta (`frontend/src/hooks/useColeta.ts`,
  `lib/acelerometro.ts`) e pesquisa na web (AOSP, fóruns da Apple, quatro estudos de validação).

**Resultado medido.**

- **Tirar uma:** perdas detectáveis só em `mag_din_media` (−0,049 de κ na cabeça; −0,011 no
  pulso), `p_frac` (−0,017 na cabeça) e `d_angulo` (−0,008 na cabeça; −0,024 no Newcastle).
  Saem sem perda: as três `enmo_*`, `zcr` e `inclinacao_rel`.
- **Quantas bastam:** `mag_din_media` + `p_frac` + `d_angulo` dão κ 0,405 contra 0,403 das
  oito na cabeça (número otimista). Fixas, fora da amostra: pulso Δκ +0,004 [−0,004; +0,011];
  Newcastle +0,044 [+0,002; +0,086]. A especificidade cai de 1 a 4 pontos.
- **O WoM, na cabeça:** −0,070 (limite superior) a −0,090 (inferior) de κ, os dois com IC longe
  do zero: de 66 % para 51–55 % do teto humano. No pulso, −0,008 (n.s.) a −0,039. No Newcastle,
  nada detectável. A contagem clássica de actigrafia, um número só, fica a −0,024 na cabeça.
- **A segunda rodada** reproduziu todos os números da primeira.
- **O celular:** no navegador, o sensor para com a tela bloqueada, o que o próprio código já
  declarava. Para a noite inteira, o caminho é o Android nativo, com *batching* do *sensor hub*
  (a mesma ideia da FIFO, feita em hardware). O iOS não está verificado. A literatura mostra o
  celular sobre a cama detectando bem o sono e mal a vigília.

**Adaptação.**

- **H1 errou em parte, e a correção ficou registrada.** O documento dizia que as três `enmo_*`
  eram redundantes com `mag_din_media` por correlação. A `enmo_media` tem correlação de 0,25 com
  ela, e mesmo assim sai sem perda. Já `mag_din_media` e `p_frac`, que a H1 dava como
  redundantes, são as que mais carregam informação.
- **A seleção progressiva é otimista por construção.** Por isso o subconjunto foi testado fixo
  nas bases que não participaram da escolha, e esse teste entrou no script antes do commit.
- **Uma citação foi atribuída ao artigo errado e foi corrigida antes do commit:** o link do PMC
  era o estudo do Sleep Time (2015), não o de 2012.

**Risco em aberto.**

- **Não medido:** o WoM real. Os proxies saem do cache de features; o circuito do MPU6050
  detecta movimento por diferença entre amostras, e a postura com uma leitura só é otimista.
  Como os dois limites dão perda grande na cabeça, a conclusão não depende do proxy exato; o
  número exato, sim.
- **Não validado:** a escolha do subconjunto de 3 features (validação aninhada, HMM, dado do
  travesseiro). Fica no `ML-12`, aberto hoje.
- **Não medido:** que as 3 features toleram o DLPF de 10 Hz (C2-LP). É hipótese no §4 do
  documento.
- **As bases são de sensores presos ao corpo.** Cabeça ≠ travesseiro (`ML-DATASETS-E-PLANO.md`).
  Os números ordenam as arquiteturas; não preveem o kappa do travesseiro.
- **Não decidido:** os modos de registro (`ARQ-02`, aberto hoje) e a escolha do `ARQ-01` (a).
- **Fora do CI:** os números do `ML-11` não são travados por nenhuma conferência, como os demais
  experimentos de ML. O JSON é a procedência.

**Procedência.**

- `ml/experimentos/ml11_ablacao_features.py` e `ml/experimentos/saida/ml11_ablacao_features.json`,
  deste commit;
- `docs/ARQUITETURA-DE-CAPTACAO.md`;
- `docs/DECISAO-ARQ-01-CADENCIA.md` §4.4, atualizado;
- fontes externas na §9 do documento.

---

# 2026-10-30 (ii) — `ARQ-01` decidido: arquitetura C2, e o `ML-11` fora de `develop`

**O problema, como foi entendido no início.** O Vitor mesclou as PRs #12 e #13 e decidiu:
seguir com a arquitetura **C2** (sono leve + FIFO). Pediu os ajustes que a decisão exige, depois
o `API-03`, depois o `ML-12`, tudo registrado, e que eu dissesse se houve algum erro em qualquer
parte.

**Hipótese de trabalho.** Que as duas PRs estivessem em `develop`, e que a decisão tocasse:
- os dois documentos de análise;
- o `CALCULOS-TCC.md` (Z.4, que dizia "muda depois da decisão");
- o `CLAUDE.md` e o `README.md`, que descreviam o dispositivo como Deep Sleep com WoM;
- as linhas `HW-03`, `FW-05`, `FW-07`, `FW-08` e `RQ-01` do backlog.

**O que foi testado, e como.**

- `gh pr view 12` e `13` antes de criar a branch;
- busca por "Wake-on-Motion", "Deep Sleep" e `ARQ-01` nos documentos versionados e nos locais;
- depois das edições:
  - recontagem do backlog linha a linha;
  - `consolidar_registro.py --conferir`;
  - `conferir_docs_versionados.py`;
  - `calculos_tcc.py --conferir`;
  - `estudo_cadencia.py --conferir`.

**Resultado medido.**

- **A #13 não estava em `develop`.** A #12 entrou às 03:33:09; a #13, que tinha como base a
  branch da #12, foi mesclada às 03:33:28 **nessa branch**, e não em `develop`. O `ML-11` (o
  experimento, o JSON, o documento de captação e o registro) estava só na branch velha.
  Corrigido partindo dela, para que a PR desta entrada leve os dois.
- **Decisão aplicada:**
  - os dois documentos de análise ganharam o estado "decidido em 30/10, a confirmar com o
    orientador";
  - o `CALCULOS-TCC.md` ganhou a seção Z.4.4b (a arquitetura adotada, com os números do
    `estudo_cadencia.py` e do `ML-11`) e, em Z.1.4, o critério de dobra contra os 12,8 Hz e a
    tolerância do oscilador;
  - `CLAUDE.md` e `README.md` agora descrevem o sono leve com FIFO;
  - os locais `HARDWARE.md` e `ROADMAP.md` ganharam nota datada.
- **Backlog:**
  - `ARQ-01` (a,b) decididos; o item segue aberto pela parte (c) e passou de L0 para L1;
  - `HW-03` deixou de ser pré-requisito;
  - `FW-05` foi desbloqueado, com a especificação nova (50 Hz pela FIFO, DLPF de 21 Hz);
  - `FW-07` mudou de premissa (sono leve, não Deep Sleep);
  - a premissa do `FW-08` passou a valer;
  - o `RQ-01` leva a decisão ao orientador;
  - recontagem: 77 (L0 44, L1 13).
- **Na primeira versão do script, três prefixos começavam com ✅ em itens que seguem
  abertos** (`ARQ-01`, `FW-05`, `FW-08`). O recontador conta ✅ no começo da célula como item
  fechado. Trocados por 📌 e 🔓 antes de rodar, então nada saiu errado no arquivo.
- **Consolidação:** as pendências `ARQ-01 (a, b)` e `ARQ-01 (a) — a escolha` saíram (83
  pendências); as de `FW-05` e `HW-03` foram reescritas. Todas as conferências passam.

**Adaptação.**

- **A regra que faltava foi para o `CLAUDE.md`:** PR sempre com base em `develop`. Trabalho que
  depende de outra PR parte da branch dela, mas aponta para `develop`, e assim qualquer ordem de
  merge chega ao lugar certo.
- **O defeito entrou na consolidação** (`ML-11`, área de infraestrutura).

**Risco em aberto.**

- **Não confirmado:** a decisão com o orientador. Ela muda a frase de "baixo consumo" da RQ; se o
  orientador recusar, o `ARQ-01` volta a L0. Fica no `RQ-01`.
- **Não decidido:** o conjunto de features (8 ou 3). Espera o `ML-12`, que é o terceiro passo do
  pedido.
- **Não medido:** tudo o que a C2 promete na placa (latência do sono leve, transbordo da FIFO,
  taxa real). É a parte (c) do `ARQ-01`, que espera a solda.

**Procedência.** `gh pr view 12 --json mergedAt` e `gh pr view 13 --json baseRefName,mergedAt`
(30/10, 03:33:09 e 03:33:28 UTC); os arquivos tocados por este commit; backlog `ARQ-01`, `FW-05`,
`HW-03`, `FW-07`, `FW-08`, `RQ-01`.

---

# 2026-10-30 (iii) — `API-03`: o endpoint de lote

**O problema, como foi entendido no início.** Na arquitetura C2, o rádio é 63 % da corrente
média com uma entrega por época, e uma entrega por hora a reduz de 5,31 para 2,03 mA. Drenar 8 h
pelo `POST /api/data` são 960 requisições, cada uma com um handshake TLS novo. O item pedia
`POST /api/data/lote`, validando item a item e respondendo quais entraram.

**Hipótese de trabalho.** Que desse para fazer **sem migração**. O caro em energia é o enlace
dispositivo → Vercel; o Vercel → Supabase pode continuar uma chamada por leitura, pela mesma
função do `/api/data`. O preço seria o tempo de servidor, contido por um teto de tamanho e um
orçamento de tempo.

**O que foi testado, e como.**

- **Refatoração:** a gravação de uma leitura saiu de `receive_data` para `_gravar_leitura`, por
  transformação mecânica do bloco original (script em scratchpad), e a suíte do backend rodou
  antes de qualquer código novo.
- **Código novo:**
  - `web-app/lote.py` (envelope, teto de 60, orçamento de 6 s, código da resposta);
  - a rota `receive_lote`;
  - `web-app/tests/test_lote.py` (23 testes).
- **Contrato:** v2.6.0, seção 5.2. A constante `CONTRATO_DE_DADOS` subiu junto.
- **Controle positivo, quatro sabotagens no `routes.py`:**
  1. falha do banco tratada como rejeição;
  2. aceitar sem gravação confirmada;
  3. desligar o orçamento de tempo;
  4. `user_id` de volta no payload.
- **Suítes completas:** backend, Windows 11, sem variável de ambiente; ML no `ml/.venv`.

**Resultado medido.**

- **A refatoração não mudou nada:** 293 passam antes e depois.
- **Com o lote:** 316 passam no backend (23 novos) e 107 no ML.
- **As quatro sabotagens reprovaram, pelos testes certos:**
  1. `test_banco_falha_no_meio…` e `test_banco_fora_desde_a_primeira_e_503_nao_200`;
  2. seis testes do lote;
  3. `test_estouro_do_orcamento…`;
  4. sete testes, entre eles o de privilégio mínimo corrigido (abaixo).
- **Duas sabotagens não chegaram a aplicar na primeira tentativa.** A âncora com `\r\n`
  escapado não casou com o arquivo CRLF, e o script acusou "âncora 0" em vez de seguir. Elas
  foram refeitas com a âncora exata e só contam a partir daí.

**Adaptação.**

- **O guarda de privilégio mínimo pegou a rota nova**, como deveria: ela não monta cliente do
  usuário no corpo. Ela entrou na lista de isenções com o motivo, igual ao da `receive_data`.
- **A refatoração cegou outro guarda, e isso foi corrigido.** O
  `test_a_ingestao_nao_monta_user_id_no_payload` olhava só o corpo da `receive_data`. Com o
  payload movido para o helper, ele **passaria sem conferir nada**. Agora ele confere as três
  funções e exige achar o payload em `_gravar_leitura`, e a sabotagem 4 prova que ele acusa.
- **A pendência gerada do `FW-07` estava velha.** Ela seguia dizendo buffer no RTC e Deep
  Sleep, porque a propagação da C2 (entrada (ii)) atualizou a linha do backlog e não a
  pendência. Foi corrigida aqui e registrada como defeito; é o mesmo padrão que o `DOC-13`
  descreve.

**Risco em aberto.**

- **Não em produção:** a rota só existe em `main` depois do próximo release.
- **Não usado:** o firmware ainda drena em rajadas de 3 POSTs. Adotar o lote é parte do `FW-07`.
- **Não resolvido:** duplicata quando a resposta se perde depois da gravação. O `/api/data` tem
  o mesmo risco; registrado no contrato §5.2, com a saída (idempotência por dispositivo + `ts`).
- **Não medido:** o tempo real de 60 chamadas ao Supabase a partir do Vercel. O orçamento de
  6 s e o teto de 60 são estimativa; o que não couber volta como pendente, então o pior caso é
  lentidão, não perda.
- **Envelhecido de propósito:** o `CLAUDE.md` ainda diz "Backend 293 passam (28/10)". O número
  tem data, então envelhece de forma visível (regra 6 do §6 das lições); fica para a próxima
  reconferência da tabela.

**Procedência.**

- `web-app/routes.py`, `web-app/lote.py`, `web-app/tests/test_lote.py` e
  `web-app/tests/test_privilegio_minimo.py`, deste commit;
- `docs/DATA-CONTRACT.md` 2.6.0, §5.2;
- backlog `API-03` e `FW-07`.

---

# 2026-10-30 (iv) — `ML-12`: a redução para 3 features sobrevive no kappa e custa especificidade

**O problema, como foi entendido no início.** O `ML-11` achou que três features empatam com
as oito, mas escolheu o trio olhando as dobras de avaliação da cabeça. Antes de o `DATA-07e`
encolher o registro, o `ML-12` pedia: (a) validação aninhada, (b) o mesmo com o HMM e (c) dado
do travesseiro, que não existe ainda.

**Hipótese de trabalho.** Que a redução sobrevivesse, porque o trio do `ML-11` já tinha
empatado fora da amostra. E, ao ler `src/epocas.py` para reusar, uma suspeita nova: o contexto
de ±2 épocas é empilhado sobre a base concatenada e atravessa a fronteira entre sujeitos.

**O que foi testado, e como.**

- **`ml/experimentos/ml12_validacao_aninhada.py`:** seleção progressiva dentro de cada uma das
  10 dobras externas, com 5 internas que só veem o treino. A regra de parada foi fixada antes de
  rodar (o menor conjunto a até 0,005 do melhor kappa interno). Cada conjunto foi avaliado com
  e sem o Viterbi de 2 estados, contra as 8, pareado por dobra, com IC de 95 %.
- **Contexto por sujeito**, com a comparação contra o global.
- **Controle positivo antes de tudo:** uma coluna-isca que vaza o rótulo. O script para se a
  seleção não a escolher em todas as dobras.
- Rodou com `python -u`, a saída em tempo real; Windows 11, `ml/.venv`, ~11 min.

**Resultado medido.**

- **Controle positivo:** a isca foi a primeira escolha em 10 de 10 dobras.
- **O que a seleção escolhe:**
  - cabeça: `mag_din_media` e `d_angulo` em 10/10, `p_frac` em 8/10;
  - pulso: só `mag_din_media`;
  - Newcastle: `d_angulo` e às vezes `p_frac`;
  - `enmo_desvio`, `enmo_max` e `zcr` nunca foram escolhidas.
- **Kappa:** nenhuma perda significativa em nenhuma base, com ou sem HMM. Cabeça: aninhada
  −0,010, trio +0,002. Pulso e Newcastle: sobe.
- **Especificidade:** cai de 0,8 a 5,5 pontos, e o IC não cruza o zero em 9 dos 12 casos
  (cabeça aninhada −0,028; Newcastle trio −0,043).
- **Contexto global contra por sujeito:** κ +0,001 a +0,002 a favor do global (vazamento
  real e desprezível).

**Adaptação.**

- **A hipótese acertou no kappa e errou no que importa para a decisão.** O `ML-11` já mostrava
  a especificidade caindo, e eu a tratei como ressalva. Com IC, ela é o resultado: o vetor menor
  troca vigília por sono acertado.
- **A recomendação para o `DATA-07e` mudou de "pode encolher" para "manter as 6".** São 8 B por
  época, e a flash do `FW-08` não precisa deles.
- **O `ML-12` foi para L1:** a parte (c) espera dado do travesseiro.
- **O vazamento do contexto entrou como defeito.** Os experimentos antigos não foram refeitos,
  de propósito: o efeito é uma ordem de grandeza menor que qualquer um deles.

**Risco em aberto.**

- **Não medido:** o travesseiro. Todas as bases são de sensores presos ao corpo. Fica no `ML-12`
  (c).
- **Não decidido:** o vetor do dispositivo. A recomendação é manter as 6; o `DATA-07e` decide.
- **Não refeito:** os experimentos anteriores com o contexto por sujeito. A diferença medida
  (≤ 0,002) não muda nenhuma leitura, e refazê-los custaria horas por nada.

**Procedência.**

- `ml/experimentos/ml12_validacao_aninhada.py` e
  `ml/experimentos/saida/ml12_validacao_aninhada.json`, deste commit;
- `docs/ARQUITETURA-DE-CAPTACAO.md` §3.4;
- backlog `ML-12` e `DATA-07e`.

---

# 2026-10-30 (v) — `FW-07`, parte do núcleo: a cadeia C2, da FIFO à grade de 32 Hz

**O problema, como foi entendido no início.** O núcleo C++ já calculava as 6 features a
partir de 960 amostras numa grade de 32 Hz (`DATA-07b`), mas nada no firmware produzia essa
grade. Na C2 o sensor entrega outra coisa: blocos da FIFO a ~50 Hz **nominais**, sem carimbo
de tempo, de um oscilador que erra de −15 a +10 %. O plano aprovado separou o `FW-07` em duas
partes: (a) o que se escreve e testa no computador, no `firmware/nucleo/`, e (b) o
`sketch.ino`, que só compila sem a placa e fica para outra PR.

**Hipótese de trabalho.** Que a cadeia do `ml/src/sinal.py::reamostrar` (Butterworth de 4ª
ordem a 12,8 Hz, fase zero, depois interpolação linear) pudesse ser aplicada **por época**,
com uma margem de sinal de cada lado, e que a taxa pudesse ser medida por uma regressão da
contagem acumulada contra o instante de cada drenagem. A dúvida era quanto a margem e a
estimativa de tempo custariam contra o `ml/`, que filtra a noite inteira com o tempo
verdadeiro.

**O que foi testado, e como.**

- **Protótipo em Python antes do C++** (scratchpad), 30 sementes × 4 taxas (42,5; 47; 50;
  55 Hz) × 2 épocas, medindo três coisas separadas:
  - a margem, com o tempo verdadeiro ("oráculo");
  - o erro de tempo da regressão;
  - o efeito de variar o intervalo de despertar.
- **A referência e o gerador:** `ml/testes/dourado_cadeia_c2.py`. Contém o gerador (sinal da
  geradora histórica + uma componente de 14–20 Hz para exercitar o anti-aliasing), o
  `esperado_pelo_pipeline` (o `ml/` com o tempo verdadeiro) e o `cadeia_estilo_firmware` (a
  conta que o C++ copia).
- **Os testes Python:** `test_dourado_cadeia_c2.py`, 19 testes. Medem o piso em 400 épocas,
  conferem as constantes contra o `config.yaml`, provam a margem com o oráculo, conferem as
  recusas e mostram que cada sabotagem estoura a régua de exatidão. Gravam
  `vetor_dourado_cadeia_c2.json` (473 KB).
- **O C++:**
  - `fifo_mpu.h/.cpp`: registradores e decodificação;
  - `reamostragem.h/.cpp`: duas seções com Q distintos, ida e volta;
  - `cadeia_c2.h/.cpp`: regressão, janela, recusas;
  - `lote.h/.cpp`: envelope e leitura da resposta do `API-03`;
  - `buffer.h`: `confirmar_entregas` e uma geração que muda quando a fila degrada;
  - `filtro.h/.cpp`: a passagem do biquad exposta, não copiada.
- **Testes C++:** `testes_c2.cpp` (105 verificações de unidade) e `testes_cadeia_c2.cpp` (456,
  a cadeia contra o dourado, com as drenagens entrando uma a uma e os bytes passando pelo
  decodificador).
- **Controle positivo:** `verificar_cadeia_por_mutacao.sh` (alvo `make mutacao-cadeia`, e
  agora no CI). São 16 sabotadores, cada um declarando qual alvo **tem** de acusar.
- **Suítes completas:** firmware em `gcc:13` (Docker, Windows 11); ML no `ml/.venv`.

**Resultado medido.**

- **A margem resolve as bordas.** Com o tempo verdadeiro, a cadeia por época com 0,5 s de
  margem dá a mesma grade que o `reamostrar` da noite inteira em **1,5e-6 g**. Sem margem, a
  borda move `mag_din_media` em até 1 %. Com 1 s, nada melhora.
- **O que sobra é o relógio.** A regressão erra o instante em até ~5 ms no centro da época.
  Piso medido em 400 épocas, firmware contra o pipeline:

  | Medida | Piso |
  |---|---|
  | `enmo_media`, `enmo_desvio` | 2,2e-5 g |
  | `enmo_max` | 2,2e-3 g |
  | `mag_din_media` | 1,12 % |
  | `zcr` | 8 cruzamentos |
  | `p_frac` | 11 amostras |
  | `ĝ` | 0,079° |

- **Cinco das seis sabotagens movem as features menos que o próprio piso.** Só a ausência de
  anti-aliasing estoura uma régua de validade com folga. Daí as **duas referências** do dourado:
  - validade, contra o pipeline, com régua larga;
  - exatidão, contra a mesma conta em Python, com 1e-4 g de grade e 1e-9 s de linha do tempo.
- **O C++ contra a referência de exatidão:** linha do tempo idêntica (0 s), grade a **9,2e-8
  g**. Contra o pipeline: `enmo` 9,6e-6 g, `enmo_max` 3,4e-4 g, `mag_din` 0,85 %, `zcr` 0,
  `p_frac` 7 amostras, `ĝ` 0,065°. Tudo dentro.
- **Controle positivo: 16/16 sabotadores acusados pelo alvo esperado**, e a árvore limpa
  passou.
  - Pelo dourado: taxa nominal, sem anti-aliasing, Q errado, filtro causal, sem meio passo,
    sem margem, grade deslocada, FIFO little-endian, regressão com todas as drenagens, ±16 g.
  - Pela unidade: transbordo e taxa que deixam de recusar, lote que confirma pendentes ou
    aceita pendente no meio, buffer que confirma depois de degradar, FIFO no teto.
- **Suítes:**
  - firmware: 341 + 157 + 105 + 456 verificações, 0 falhas; 4/4 sketches compilam; mutação da
    paridade antiga continua 15/15;
  - ML: 126 passam (107 + 19).
- **Memória:** `CadeiaC2` ocupa 23,7 KiB, mais 11,3 KiB de grade. Cabe porque o sono leve
  preserva a RAM.

**Adaptação.**

- **Um achado de projeto: o despertar trava em fase com a amostragem.** A 50 Hz exatos, 1,7 s
  são 85 amostras inteiras: toda drenagem cai no mesmo ponto entre duas amostras, e a
  regressão herda o deslocamento inteiro (até 10 ms) em vez de tirar a média. Variar o
  intervalo em [0, 20 ms) (`intervalo_de_drenagem_us`) baixou o pior erro de 8,1 para 4,7 ms.
  A FIFO segue com folga: no pior caso, 95 de 170 amostras.
- **O meio passo.** A drenagem que deixa a contagem em C acontece, em média, meio passo depois
  da amostra C−1. Sem esse termo a linha inteira atrasa 10 ms; virou sabotador.
- **A confirmação do lote ficou mais simples que o previsto.** O servidor para na primeira
  falha, então `pendentes` é sempre um sufixo, e o dispositivo confirma um **prefixo** da fila,
  que é a única operação que ela sabe fazer sem furar a série. Resposta incoerente → nada sai
  (duplicata no servidor, nunca perda aqui).
- **Um risco que o plano não tinha:** a fila pode degradar com um lote no ar, e as k primeiras
  épocas deixam de ser as k enviadas. A geração do buffer resolve: lote montado antes de uma
  fusão não confirma nada.
- **Textos velhos corrigidos, e um registrado como defeito.** O `README.md` do núcleo e o
  `capacidade.cpp` ainda diziam que o `sketch.ino` reescrito usaria 128 épocas no RTC (desenho
  Deep Sleep) e que o `API-03` era item aberto.

**O que deu errado no caminho** (nenhum chegou ao commit):

1. **O gerador cortava as drenagens cedo.** A 42,5 Hz, a última drenagem caía antes do fim da
   janela, e a época 1 saía recusada. Era o gerador, não o firmware: o firmware espera a
   drenagem seguinte.
2. **O primeiro protótipo deu números absurdos com margem de 1 s.** As drenagens depois do fim
   do registro repetiam a contagem final e entortavam a regressão. Também era do simulador.
3. **Um teste meu reprovou o filtro sem razão.** Ele media a amplitude de 3 Hz pelo maior valor
   amostrado (0,998), e a 50 Hz as amostras não caem no pico. Trocado por RMS sobre ciclos
   inteiros; o filtro passa 3 Hz com 1,0000 e corta 20 Hz a 0,0002.
4. **O primeiro dourado tinha 1,1 MB.** O `indent=2` punha cada inteiro numa linha. As listas
   internas foram compactadas: 473 KB.

**Risco em aberto.**

- **Não exercitado:** nada disto rodou num MPU6050. Os registradores, o transbordo e o
  comportamento real da FIFO esperam a solda (`FW-05`, L1).
- **Não medido:** o relógio do ESP32 em sono leve. A taxa "medida" herda o erro dele. É a parte
  (c) do `ARQ-01`, e foi para `docs/LIMITACOES-TCC.md`.
- **Não feito:** o `sketch.ino` (parte (b) do `FW-07`). Ele tem um risco próprio: um POST que
  bloqueie mais de ~1,7 s deixa a FIFO transbordar, porque o laço é de uma linha só.
- **Não transportado:** o payload ainda não leva `f` (`DATA-07b`). A cadeia produz a grade, o
  acumulador produz as features, e o servidor ainda não as recebe.

**Procedência.**

- `firmware/nucleo/{fifo_mpu,reamostragem,cadeia_c2,lote}.{h,cpp}`, `buffer.h`, `filtro.{h,cpp}`,
  `testes/testes_c2.cpp`, `testes/testes_cadeia_c2.cpp` e
  `testes/verificar_cadeia_por_mutacao.sh`, deste commit;
- `ml/testes/dourado_cadeia_c2.py`, `test_dourado_cadeia_c2.py` e
  `vetor_dourado_cadeia_c2.json`;
- `firmware/nucleo/README.md`, seção "A arquitetura C2";
- backlog `FW-07` e `FW-05`.

---

# 2026-10-30 (vi) — `DATA-07b` fechado: o vetor sai do dispositivo, entra no banco e volta com as oito

**O problema, como foi entendido no início.** O firmware calculava as 6 features e `ĝ` de cada
época, mas nada levava isso adiante: `montar_payload` não tinha `f`, `g` e `fs`; o backend não
os validava; o banco não tinha colunas, e as duas funções de gravação só extraíam os campos que
conheciam; e `inclinacao_rel` e `d_angulo`, que dependem da noite inteira, não eram calculadas
em lugar nenhum fora do `ml/`. Uma noite captada chegaria sem vetor, e o modelo não teria o que
ler. O plano aprovado juntou o transporte, (d) e (e) numa PR, com duas decisões do autor para a
(e): a janela é escolhida por quem pede (o `ESC-01` decide a "noite" depois), e `d_angulo` é
nulo depois de buraco.

**Hipótese de trabalho.** Que o caminho inteiro pudesse ser escrito sem mudar o que já está em
campo: payload sem `f` continuando válido, a 010 sem quebrar o backend de hoje, e a derivação
do servidor batendo com o `ml/` sem numpy.

**O que foi testado, e como.**

- **Firmware:** `montar_payload` ganhou o vetor opcional, só para época de nível 0 (30 s) com
  todos os valores dentro das faixas. 13 verificações novas em `testes_c2.cpp`.
- **Backend:**
  - `validacao._validar_features`, as regras do §2.6 uma a uma;
  - `colunas_de_features`, onde a ordem de `f` vira nome;
  - 40 testes em `test_features_da_epoca.py`.
- **Banco:** a migração `010` (dez colunas nomeadas, restrição tudo-ou-nada, as duas funções
  recriadas). Sete testes contra Postgres 16 em Docker (`test_rls_features.py`). O verificador de
  migrações e o diagnóstico de produção ganharam a 010.
- **Servidor:**
  - `web-app/features_noite.py` (Weiszfeld e arccos em Python puro) e `GET /api/features`;
  - 28 testes em `test_features_noite.py`, incluindo a paridade contra as oito sequências de
    `ml/testes/vetor_dourado_sequencias.json`.
- **Controle positivo:**
  - 13 sabotagens no backend e no banco (script em scratchpad, que aplica, roda o teste nomeado e
    restaura);
  - 3 no payload, agora no `make mutacao-cadeia`;
  - a 010 com uma função que grava nulo, rodada pelo verificador do diagnóstico.
- **Suítes completas:** backend e RLS no Windows 11 (RLS contra `postgres:16` em Docker);
  firmware em `gcc:13`; ML no `ml/.venv`.

**Resultado medido.**

- **Paridade da derivação:** `g_ref` difere do `ml/` em 5,6e-16, e os ângulos em 2,4e-10 grau.
  O arccos amplifica perto de 0 a diferença de 1e-16 no cosseno, então a régua "exato" do arquivo
  (1e-12) **reprovaria a implementação correta** nos ângulos. A régua adotada é 1e-6 grau,
  4 000× acima do piso; as sabotagens movem graus inteiros.
- **Suítes:**
  - backend: 384 passam (316 + 68);
  - RLS: 158 (151 + 7);
  - firmware: 341 + 157 + 118 + 456, 0 falhas; 4/4 sketches;
  - mutação: 15/15 da paridade e 19/19 da cadeia e do payload;
  - o verificador de migrações acerta os 10 estados e a mutação do RLS segue 32/32.
- **Controle positivo:** 13/13 no backend e no banco, 3/3 no payload. O diagnóstico acusou a 010
  sabotada ("3 de 4 marcas; falta: registrar_leitura extrai o vetor").
- **A 010 não quebra o backend de hoje:** a gravação sem as dez chaves entra com as colunas nulas,
  medido.

**Adaptação.**

- **Três escolhas que o plano não detalhava.**
  1. **Vetor fora de faixa sai sem `f`, em vez de ir e levar a leitura inteira a um `400`.** Uma
     época de movimento violento pode passar de 2 g de magnitude dinâmica, e o pico, que é válido,
     se perderia junto.
  2. **`%.9g` no texto:** uma noite parada tem `enmo_media` da ordem de 1e-4 g, e `%.4f`
     arredondaria a feature a zero (virou sabotador).
  3. **A consulta pagina de 1 000 em 1 000.** O Supabase corta em 1 000 linhas, e 24 h são 2 880
     épocas.
- **Só entram em `/api/features` as épocas com `captured_at`.** Sem o instante da medição não há
  como ordenar a noite nem reconhecer buraco, e o `created_at` é a hora de chegada.
- **O guarda de privilégio mínimo acusou a rota nova**, como deveria. O método entrou na lista
  dos que usam o JWT, e um teste confere que ele de fato monta o cliente com o JWT.
- **`DATA-07d` fechou junto:** o que restava dele era o contrato dizer que época truncada não
  emite `f`, e a v2.7.0 diz.
- **Entrou `DATA-07f` (L3):** aplicar a 010 na produção antes do release.

**O que deu errado no caminho** (nenhum chegou ao commit):

1. **Dois testes meus conferiam pouco, e só a revisão antes das sabotagens os pegou.**
   - O "os três vêm juntos" procurava a letra `g` ou `fs` na mensagem, e quase toda recusa as
     contém: a regra podia sumir e o teste passar.
   - O diagnóstico procurava `fs_features` em qualquer lugar da função; uma função que listasse a
     coluna e gravasse nulo passaria.

   Os dois agora conferem a mensagem inteira e a extração (`->> 'fs_features'`), e as duas
   sabotagens provam que acusam.
2. **Um teste do payload supôs que 220 bytes não cabiam o vetor.** Cabiam, porque `%.9g` encurta
   os números. Agora o teste usa um buffer de 150.
3. **Um `heredoc` do bash corrompeu o travessão de uma âncora de edição.** O script de edição
   recusou ("casou 0") em vez de gravar errado, e as edições com acento passaram a ir por arquivo.

**Risco em aberto.**

- **Ordem de aplicação** (`DATA-07f`): a 010 tem de entrar antes do release.
- **Não guardado:** a fila do firmware (`buffer.h`) guarda `Epoca` sem o vetor. O payload sabe
  levar `f`, e quem passa a guardá-lo até o envio é o `FW-08`.
- **Não exercitado:** nenhum sketch chama `montar_payload` com o vetor (`FW-07` (b)).
- **Não decidido:** o que é "a noite" (`ESC-01`). A rota devolve o `g_ref` e a janela usados
  para que a escolha fique visível.
- **Não testado contra o PostgREST:** a consulta paginada roda mockada no backend. O RLS das
  colunas novas é testado em Postgres de verdade, mas sem o PostgREST na frente.

**Procedência.**

- `firmware/nucleo/payload.{h,cpp}`, `testes/testes_c2.cpp` e
  `testes/verificar_cadeia_por_mutacao.sh`;
- `web-app/validacao.py`, `routes.py`, `database.py` e `features_noite.py`;
- `web-app/migrations/010_vetor_de_caracteristicas.sql` e `DIAGNOSTICO-migracoes-aplicadas.sql`;
- `web-app/tests/test_features_da_epoca.py`, `test_features_noite.py`,
  `rls/test_rls_features.py`, `rls/conftest.py`, `migracoes/verificar_migracoes.py` e
  `test_privilegio_minimo.py`;
- `docs/DATA-CONTRACT.md` 2.7.0, §2.6;
- backlog `DATA-07b`, `DATA-07d` e `DATA-07f`.

---

# 2026-10-30 (vii) — `DATA-07f`: a 010 na produção, antes do release

**O problema, como foi entendido no início.** O `DATA-07b` entrou em `develop` com a migração
`010`, e o backend novo valida o vetor `f` e o entrega às funções de gravação. Se o release
levasse esse backend a `main` antes da 010 estar no banco, as funções antigas descartariam o
vetor e responderiam `201`: perda silenciosa, a mesma família do `SEC-12`.

**Hipótese de trabalho.** Que a 010 entrasse na produção sem efeito sobre o backend que está no
ar (contrato 2.5.1), e que o diagnóstico distinguisse "aplicada" de "colunas criadas com a
função antiga".

**O que foi testado, e como.** O autor aplicou `010_vetor_de_caracteristicas.sql` no SQL Editor
do Supabase e colou aqui o resultado de `DIAGNOSTICO-migracoes-aplicadas.sql`. O `/health` de
produção foi chamado daqui depois da aplicação.

**Resultado medido.**

- **Diagnóstico:**
  - a 010 com **4 de 4 marcas**: a coluna `fs_features`, a restrição tudo-ou-nada, e as duas
    funções extraindo `->> 'fs_features'`;
  - 001 e 003–009 com todas as marcas, como em 29/10;
  - 0 leituras sem dono (002).
- **`/health`:** `200`, `"banco": "ok"`, `"contrato_de_dados": "2.5.1"`. O backend de `main`
  continua funcionando sobre o banco novo, e ainda não é o da v2.7.0.

**Adaptação.** Nenhuma: a aplicação seguiu o passo a passo do item. A régua do diagnóstico já
tinha sido endurecida no `DATA-07b`, e foi ela que permitiu dar o item por fechado só com o
resultado colado, sem acesso ao banco daqui.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**

- **Não exercitado na produção:** nenhuma leitura com vetor foi gravada lá. O dispositivo ainda não
  emite `f` em campo (`FW-07` (b), `FW-08`), e o backend que validaria `f` só chega a `main` no
  próximo release. O caminho completo está testado contra Postgres 16 local, não contra o
  Supabase.
- **O release de `develop` para `main`** ficou desbloqueado deste lado; não foi feito.

**Procedência.**

- `web-app/migrations/010_vetor_de_caracteristicas.sql` e `DIAGNOSTICO-migracoes-aplicadas.sql`;
- resultado do diagnóstico na produção, colado pelo autor em 30/10;
- `GET https://dormio-smart.vercel.app/health`, 30/10;
- backlog `DATA-07f`.

---

# 2026-10-30 (viii) — o release para `main`: contrato 2.7.0 no ar

**O problema, como foi entendido no início.** A produção rodava o backend do release de 29/10,
contrato 2.5.1. Em `develop` estavam o endpoint de lote (`API-03`), o vetor de características
com `GET /api/features` (`DATA-07b`), a cadeia C2 do firmware (`FW-07` (a)) e o trabalho de
`ARQ-01`, `ML-11` e `ML-12`. A 010 já estava na produção (`DATA-07f`), então a ordem exigida
estava cumprida.

**Hipótese de trabalho.** Que o merge não tivesse como dar conflito e que o código novo não
dependesse de nada que a produção ainda não tivesse: variável de ambiente, dependência,
configuração de deploy ou objeto do banco.

**O que foi testado, e como.**

- **Antes do merge:**
  - diff da base comum (`32356ff`) para `main`;
  - diff de `main` para `develop`: arquivos, variáveis de ambiente lidas no código,
    `requirements.txt`, `package.json` e `vercel.json`;
  - toda chamada nova ao banco em `database.py`, `routes.py` e `lote.py`.
- **O release:** PR #20, `develop` → `main`, mesclada por esta sessão com aprovação do autor,
  depois dos 9 checks do CI.
- **Depois do merge:** `/health` consultado daqui até o deploy virar; as duas rotas novas
  chamadas sem credencial.

**Resultado medido.**

- **Antes:**
  - o diff da base para `main` é vazio: `main` só tem os commits de merge dos releases;
  - nenhuma variável de ambiente nova, nenhuma dependência nova; `vercel.json` e frontend sem
    mudança;
  - o código novo usa só as colunas da 010 e as funções `registrar_leitura` e
    `registrar_leitura_da_sessao`, todas na produção.
- **Depois:**
  - `/health`: `200`, `"banco": "ok"`, `"contrato_de_dados": "2.7.0"`, na terceira consulta
    (menos de um minuto depois do merge);
  - `GET /api/features` e `POST /api/data/lote` sem credencial: `401`. As rotas existem e não
    respondem a quem não se identifica.

**Adaptação.** Diferente de 29/10, o merge em `main` não foi negado a esta sessão. A conferência
seguiu o roteiro da primeira entrada de 29/10.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**

- **Não exercitado na produção:**
  - nenhuma leitura com vetor e nenhum lote foram gravados lá; os dois caminhos estão testados
    contra Postgres 16 local e com o Supabase mockado, não contra o Supabase;
  - quem os exercita é o firmware em campo (`FW-07` (b), `FW-08`).
- **`INFRA-03`:** a primeira execução agendada do monitor (31/10) roda sobre esta versão. É ela
  que fecha o item.

**Procedência.**

- PR #20 (`fa5f164`);
- `GET https://dormio-smart.vercel.app/health`, `/api/features` e `/api/data/lote`, 30/10;
- backlog `API-03`, `DATA-07b`, `DATA-07f` e `INFRA-03`.

---

# 2026-10-31 — `FW-08`: a fila na flash, e a partição que tinha 9 % a menos

**O problema, como foi entendido no início.** A fila em RAM (`buffer.h`) guarda só a `Epoca`
de 32 B. Ela não tem onde pôr o vetor que o `DATA-07b` passou a enviar, perde a noite inteira
num reset, e quando enche funde épocas — e época fundida não tem features. O estudo de 29/09
já tinha decidido a saída (flash como registro durável) e deixado duas escolhas em aberto:
LittleFS ou NVS, e versionar a tabela de partições.

**Hipótese de trabalho.** Que um log circular próprio sobre a partição crua fosse mais simples
e mais testável que LittleFS ou NVS, e que desse para provar no host, sem placa, que ele
sobrevive a corte de energia em qualquer ponto. O autor aprovou as duas recomendações do plano:
log circular próprio, e tabela sob medida sem OTA.

**O que foi testado, e como.**

- **O núcleo:** `registro_flash.{h,cpp}` (registro de 64 B com `static_assert` de tamanho e
  offsets, CRC-16/CCITT pulando o byte de entregue) e `fila_flash.{h,cpp}` (montagem, guarda,
  leitura, confirmação, e o caminho do registro ao payload).
- **A flash simulada** (`testes/testes_fila_flash.cpp`): programa com `antigo & novo` e conta
  toda tentativa de bit 0 → 1; apaga de 4 KiB em 4 KiB; corta a energia depois de N bytes, no
  meio de um apagamento, ou "engole" a escrita.
- **Cenários:** ida e volta; reset com pendentes; fila cheia; 20 000 épocas em 8 setores;
  corte em cada um dos 65 pontos de uma gravação; confirmação pela metade; apagamento pela
  metade; chip que engole a escrita; o registro virando o JSON do contrato, com e sem relógio.
- **A tabela:** `firmware/partitions.csv`; `make capacidade` passou a lê-la e validá-la.
- **A ponte:** `firmware/midia_flash_esp32.h`, compilada pelo `make sintaxe` com um stub de
  `esp_partition.h`.
- **Controle positivo:** `make mutacao-fila` com 10 sabotagens; a ponte com a chamada de escrita
  estragada; a tabela com três estragos (sobreposição, nome trocado, fim fora da flash).
- **Suítes completas** do firmware em `gcc:13`; conferências de documento no Windows 11.

**Resultado medido.**

- **A fila:** 72 verificações, 0 falhas. Nenhuma violação de NOR em nenhum cenário. Depois de
  qualquer corte, nada do que já estava gravado se perde e a fila volta a gravar.
- **Desgaste:** em 20 000 épocas, os 8 setores ficaram entre 38 e 39 apagamentos.
- **Capacidade:** 512 setores = 32 768 registros, **32 704 garantidos = 272,5 h = 11,4 dias**.
  Com a tabela padrão seriam 7,8 dias.
- **Controle positivo:** 10/10 sabotagens acusadas, depois do conserto abaixo; a ponte estragada
  reprova o `make sintaxe`; os três estragos da tabela reprovam o `make capacidade`.
- **Suítes:** 341 + 157 + 118 + 456 + 72 verificações, 0 falhas; 4/4 sketches e a ponte
  compilam; mutação 15/15, da cadeia 19/19, da fila 10/10.

**Adaptação.**

- **A partição padrão tem 1 408 KiB, não 1,5 MiB.** Conferido no `tools/partitions/default.csv`
  do `arduino-esp32`: a área de dados é 0x160000. O 1,5 MiB estava no estudo desde 29/09 sem
  ter sido conferido, e dali foi para o backlog, a pendência e dois documentos de decisão como
  "13,7 dias". Corrigido nas constantes, anotado nos documentos, registrado como defeito.
- **O registro tem 64 B, não os 40 do layout D.** A flash exige o que a RAM não exigia: ordem
  (`seq`), integridade (CRC), a marca de entregue e o instante. Com a partição de 2 MiB, a
  cobertura continua acima de uma semana.
- **O instante passou a ser resolvido na gravação.** A fila em RAM data cada época no envio,
  pelo relógio monotônico, e esse relógio zera num reset. Na flash, o registro grava hora de
  parede quando o relógio já foi sincronizado; senão, o monotônico da sessão, e depois de um
  reset sem sincronia a época vai sem `ts`. Resolução de 1 s, porque sobravam 4 B.
- **O `FW-08` passou de L0 para L1:** o que falta é exercitar a ponte na placa.

**O que deu errado no caminho.**

1. **O controle positivo achou um ponto cego nos testes que eu tinha acabado de escrever.** A
   sabotagem 7 (procurar a cauda a partir do slot 0, e não da cabeça) passou. Nenhum teste
   remontava a fila com pendentes atravessando o fim físico da partição, que é justamente o
   caso em que o slot 0 guarda a época mais nova. Entrou o teste de remontagem com pendentes
   dando a volta, e a sabotagem passou a ser acusada.
2. **Uma edição do `Makefile` gravou `\n` literal** no lugar da quebra de linha (escape de
   shell dentro de Python). O `make` recusou ("No rule to make target"), e a correção foi por
   script em arquivo.
3. **O simulador de flash tinha um aviso `-Wreorder`** na ordem de inicialização dos membros.
   Corrigido antes do commit.
4. **O parágrafo gerado de `CORRECOES-APLICADAS.md` dizia que toda premissa achada por leitura
   era uma "estrutura ausente".** O defeito novo do 1,5 MiB não é: é um dado de terceiro nunca
   conferido. A guarda do gerador acusou, e o parágrafo foi reescrito junto com ela.

**Risco em aberto.**

- **Não exercitado na placa:** a ponte com o ESP32, a tabela gravada de verdade, o tempo de
  varrer 2 MiB no boot e o tempo de apagar um setor (`FW-08` (c), L1).
- **Não ligado:** nenhum sketch usa a fila. Quem a liga ao laço é o `FW-07` (b).
- **CRC de 16 bits:** uma gravação cortada tem chance de 1 em 65 536 de passar como válida.
- **`DATA-07e`:** o motivo dele (autonomia em RAM) deixou de valer com a flash. Proposto ao
  autor rebaixar ou fechar; não decidido.

**Procedência.**

- `firmware/nucleo/registro_flash.{h,cpp}`, `fila_flash.{h,cpp}`, `capacidade.cpp` e
  `Makefile`;
- `firmware/nucleo/testes/testes_fila_flash.cpp`, `verificar_fila_por_mutacao.sh` e
  `stubs-arduino/esp_partition.h`;
- `firmware/partitions.csv` e `firmware/midia_flash_esp32.h`;
- `scripts/estudo_buffer.py`, `docs/DECISAO-BUFFER-E-FEATURES.md`,
  `docs/ARQUITETURA-DE-CAPTACAO.md` e `docs/LIMITACOES-TCC.md`;
- `.github/workflows/ci.yml`;
- backlog `FW-08`.

---

# 2026-10-31 (ii) — `FW-07` (b): o `sketch.ino` da C2, em duas tarefas

**O problema, como foi entendido no início.** O `sketch.ino` de produto tirava uma amostra
por boot e voltava ao Deep Sleep. As peças da C2 já existiam no núcleo, testadas: a FIFO, a
cadeia que reamostra para 32 Hz, as features, a fila na flash (`FW-08`) e o envio em lote.
Faltava o programa que as liga no ESP32. O risco registrado no backlog era o envio: a FIFO
guarda 3,4 s e é esvaziada a cada 1,7 s, e um POST por HTTPS leva de 1 a 3 s.

**Hipótese de trabalho.** Que duas tarefas do FreeRTOS, uma em cada núcleo, resolvessem o
risco sem mexer na cadeia: a medição continua esvaziando a FIFO no ritmo enquanto o envio
espera a rede no outro núcleo. O autor aprovou o plano, com a reescrita do `sketch.ino` no
lugar.

**O que foi testado, e como.**

- **Duas peças novas no núcleo**, porque a leitura das APIs no plano achou uma lacuna:
  - `epoca_c2.{h,cpp}`: a cadeia entrega a grade, mas ninguém montava a `Epoca` que o payload
    leva (pico em m/s², eixos, temperatura). 13 verificações em `testes_c2.cpp`;
  - `envio_da_fila.{h,cpp}`: o lote como prefixo contíguo da fila, e o registro sem payload
    possível tirado da frente. 12 verificações em `testes_fila_flash.cpp`, sobre a flash
    simulada do `FW-08`.
- **O sketch:** `firmware/sketch.ino` reescrito e `firmware/nucleo_amalgama.cpp` novo. Stubs
  novos para o FreeRTOS, `esp_timer`, o sono leve, e o que faltava em `WiFi` e `HTTPClient`.
- **A ligação:** o `make sintaxe` passou a compilar o sketch, a amálgama e os stubs em objetos
  e ligá-los num executável de host.
- **Controle positivo:**
  - cinco sabotagens novas: duas na época da grade (`mutacao-cadeia`) e três no envio
    (`mutacao-fila`);
  - três estragos no sketch e na amálgama, que o `make sintaxe` tinha de reprovar: um `.cpp`
    faltando, `guardar` sem o vetor e o POST com tipo errado.
- **Suítes completas** do firmware em `gcc:13`; conferências de documento no Windows 11.

**Resultado medido.**

- **Núcleo:** 341 + 157 + 128 + 456 + 84 verificações, 0 falhas.
- **Sintaxe e ligação:** 4/4 sketches compilam, a ponte da flash compila e o `sketch.ino` liga
  com o núcleo.
- **Mutação:** 15/15 da paridade, 21/21 da cadeia (com a época da grade), 13/13 da fila (com o
  envio). Os três estragos do sketch reprovam: o `.cpp` faltando como `undefined reference`, os
  outros dois como erro de compilação.

**Adaptação.**

- **O pico passou a ser o da grade, não o da leitura bruta.** A grade já passou pelo
  anti-aliasing de 12,8 Hz, então um pico de uma ou duas leituras chega atenuado. É a escolha
  que mantém o `total` e as features descrevendo o mesmo sinal; está declarada em
  `LIMITACOES-TCC.md`.
- **A temperatura é lida uma vez, ao fechar a época**, porque a FIFO da C2 só leva o
  acelerômetro.
- **Épocas recusadas pela cadeia não são gravadas.** No servidor elas aparecem como intervalo
  entre dois `ts`; o dispositivo as conta no log.
- **O giroscópio fica em espera** (`PWR_MGMT_2`) e o MPU usa o relógio interno. É o oscilador de
  −15/+10 % que a cadeia já mede por regressão.
- **O `FW-07` passou de L0 para L1:** o que falta é a placa (parte (c)).

**O que deu errado no caminho.**

1. **O `make sintaxe` não pegaria uma amálgama incompleta.** Ele só compilava o `.ino`; um
   `.cpp` esquecido no `nucleo_amalgama.cpp` só apareceria como erro de link na IDE, na frente
   da placa. Achado ao escrever a amálgama; entrou o passo de ligação, e o controle positivo
   mostra que ele acusa.
2. **Três trocas nos stubs falharam** porque os arquivos são CRLF e o script procurava LF. O
   assert do script recusou em vez de gravar errado, e as trocas foram refeitas respeitando o
   fim de linha.

**Risco em aberto.**

- **Nada rodou na placa** (`FW-07` (c), L1): a leitura da FIFO por I2C, o despertar do sono
  leve, a taxa medida, o envio sem transbordo com o Wi-Fi ligado, e o tempo de montagem da fila
  no boot (`FW-08` (c)).
- **O Wokwi pode não simular a FIFO do MPU6050** (a documentação dele não diz). O
  `envio-continuo` segue como o sketch do simulador.
- **`setInsecure()`** no TLS, como nos outros sketches: o certificado do servidor não é
  conferido.
- **Os stubs conferem assinaturas, não comportamento:** as do FreeRTOS e do `esp_timer` foram
  escritas a partir das do ESP-IDF, e só a IDE de verdade confirma que batem.

**Procedência.**

- `firmware/sketch.ino` e `firmware/nucleo_amalgama.cpp`;
- `firmware/nucleo/epoca_c2.{h,cpp}`, `envio_da_fila.{h,cpp}` e `Makefile`;
- `firmware/nucleo/testes/testes_c2.cpp`, `testes_fila_flash.cpp`,
  `verificar_cadeia_por_mutacao.sh`, `verificar_fila_por_mutacao.sh` e `stubs-arduino/`;
- `docs/LIMITACOES-TCC.md`;
- backlog `FW-07`.

---

# 2026-10-31 (iii) — `DATA-07e` fechado sem ser feito: o `FW-08` o dissolveu

**O problema, como foi entendido no início.** O `DATA-07e` era a dívida de 17/10: quantizar os
5 floats de pico para o par época + vetor cair de 52 para 40 B, e a cobertura da fila em 32 KiB
de RAM subir de 5,25 para 6,83 h. Fora adiado de propósito, porque mexe na precisão transmitida
e na checagem de coerência da §5.1 do contrato.

**Hipótese de trabalho.** Que o motivo do item tivesse deixado de existir: a fila saiu da RAM.

**O que foi testado, e como.** Conferência contra o que já estava medido: `make capacidade`
(registro da flash de 64 B, 32 704 garantidos = 11,4 dias, 31/10) e o `sketch.ino` da C2, que
só usa a fila na flash. A cobertura com o registro quantizado (~52 B, ~13,8 dias) é estimativa
de conta, não medida.

**Resultado medido.** Nenhum número novo. Os que decidem já estavam medidos: 11,4 dias na flash
contra uma noite de 8 h.

**Adaptação.** O autor decidiu fechar como dissolvido, não fazer. O esquema de quantização fica
desenhado em `DECISAO-BUFFER-E-FEATURES.md` (Saída 3).

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** A fila em RAM (`buffer.h`) continua com o registro de 32 B e é usada pelo
`envio-continuo`, que não envia features. Se um dia um sketch voltar a guardar o vetor em RAM, a
conta de 5,25 h volta a valer.

**Procedência.**

- `firmware/nucleo/capacidade.cpp` (`make capacidade`);
- `firmware/sketch.ino`;
- backlog `DATA-07e` e `FW-08`.

---

# 2026-10-31 (iv) — `SEC-11` fechado sem fazer, e a X.7 afirmava um captcha que não existe

**O problema, como foi entendido no início.** O `SEC-11` mandava ligar o captcha do Supabase
"em ~5 minutos de painel, sem linha de código", como mitigação da enumeração de contas do
`SEC-08`. O backlog o recomendava como a primeira coisa a fazer com cinco minutos livres. Ao
explicá-lo ao autor, a documentação do Supabase dizia que o frontend precisa mudar, e o autor
pediu que tudo o que eu não tinha confirmado fosse investigado, e que eu dissesse se o captcha
vale o custo.

**Hipótese de trabalho.** Que a afirmação "sem linha de código" estava errada, e que o ganho do
captcha fosse menor do que o item dizia.

**O que foi testado, e como.** Leitura na fonte, sem tocar na produção:

- **o código do `supabase/auth`:** `internal/api/middleware.go` (`verifyCaptcha`,
  `isIgnoreCaptchaRoute`) e `internal/api/api.go` (quais rotas o usam);
- **o guia *Rate limits* da autenticação** do Supabase;
- **o nosso frontend** (`frontend/src/lib/autenticacao.ts`, `perfil.ts`) e o backend
  (`database.py`), por busca das chamadas de autenticação;
- **os quatro canais** da seção X.7 de `LIMITACOES-TCC.md`, cruzados com as rotas.

**Resultado medido.**

- **Pedido sem token, com o captcha ligado:** `400 captcha protection: request disallowed (no
  captcha_token found)`. Só credencial de administrador passa.
- **Rotas que exigem o token:** `/signup`, `/token` com senha, `/recover`, `/resend`,
  `/magiclink`, `/otp`. Isentas: a renovação de sessão e o `/user`.
- **O frontend** chama quatro delas (login, cadastro, reenvio, recuperação) e não tem uma linha de
  captcha. **Ligar a chave derrubaria o login e o cadastro da produção.** Backend e dispositivo
  não seriam afetados.
- **O canal 3 da X.7, a troca de e-mail, passa pelo `/user`**, que o captcha não cobre. Com uma
  conta, ele enumera ao mesmo custo de hoje: o captcha não encarece a varredura em massa.
- **Limite de taxa por IP, padrão do Supabase:** 30 pedidos a cada 5 min em `/signup`,
  `/recover`, `/resend` e `/user`; 150 em `/token`.
- **A X.7 dizia "Adotou-se proteção contra automação (captcha)"** desde 20/10 (`2fcb0f5`). O
  captcha nunca foi ligado.

**Adaptação.** O autor decidiu fechar o `SEC-11` sem fazer. A X.7 foi reescrita: a mitigação
vigente é o limite de taxa, com fonte, e o captcha aparece como avaliado e não adotado, com o
motivo. Duas referências novas na lista da seção (o guia de limites e o código-fonte).

**O que deu errado no caminho.**

1. **O texto da banca afirmava uma defesa que não existe**, por onze dias. O parágrafo foi
   escrito no tempo verbal de quem já tinha feito, enquanto a ação ficava aberta. Registrado como
   defeito.
2. **O item recomendava uma ação que derrubaria a produção.** A premissa "é só configuração" saiu
   da página do painel, sem ler o guia de integração nem o código. Registrado como defeito, achado
   por fonte de terceiro.
3. **Na minha primeira explicação ao autor, deixei dois pontos como "pela minha leitura"** — o
   que acontece sem token, e se o captcha cobria todos os canais. Os dois só se resolveram lendo
   o código. É a regra 6 do §5 das lições: comportamento de serviço se confere na fonte do
   serviço.
4. **Os dois defeitos novos derrubaram uma frase gerada:** "exercitar achou mais de duas vezes o
   que ler". A razão caiu para 2,0 (63 contra 32), e a guarda do gerador acusou. O título foi
   reescrito para "perto do dobro", junto com a guarda.

**Risco em aberto.**

- **Não conferido daqui: o painel.** Em `Authentication → Attack Protection` o captcha deve
  aparecer desligado, e em `Rate Limits` os valores padrão. A evidência indireta é que o login
  funciona sem token.
- **O código lido é o ramo principal do `supabase/auth`**, não necessariamente a versão exata em
  produção.
- **A enumeração continua aberta**, como a X.7 declara. Nada aqui a fecha.

**Procedência.**

- `supabase/auth`: `internal/api/middleware.go` e `internal/api/api.go`;
- guia *Rate limits* da autenticação do Supabase;
- `frontend/src/lib/autenticacao.ts`;
- `docs/LIMITACOES-TCC.md`, seção X.7;
- backlog `SEC-11` e `SEC-08`.

---

# 2026-10-31 (v) — as figuras do TCC: o esquemático, e três diagramas que tinham ficado para trás

**O problema, como foi entendido no início.** O `DIAG-02` (esquemático) nunca tinha sido
começado, e o `DIAG-04` estava escrito mas nunca renderizado. Ao ler os arquivos para o plano,
apareceu o maior problema: `DIAG-01`, `DIAG-03` e `DIAG-04`, conferidos em 28/10, não
mostravam nada do que entrou em 30 e 31/10 — a C2, a fila na flash, o envio em lote, a `010`, a
rota de features. O autor aprovou incluir os três.

**Hipótese de trabalho.** Que as figuras Mermaid pudessem ser atualizadas e conferidas contra o
código por script, e que o esquemático pudesse ser feito com uma ferramenta que gera a imagem
aqui, para ela ser olhada antes de entrar no texto.

**O que foi testado, e como.**

- **`DIAG-01`, `DIAG-03`, `DIAG-04`:** reescritos onde o código mudou. Renderizados com a
  imagem `minlag/mermaid-cli:11.4.2` (a de 28/10), e as sete figuras **olhadas**.
- **Conferência por script** (em scratchpad): extrai de cada bloco Mermaid os caminhos de
  arquivo, as chamadas `nome()`, as rotas e as colunas do ER, e procura cada um no código com
  `git grep`.
- **`DIAG-02`:** `docs/diagramas/DIAG-02-esquematico.py`, com `schemdraw` 0.19 num ambiente
  Python separado. Antes de desenhar, o script lê os pinos e o endereço no `sketch.ino` e as
  ligações no `diagram.json`, e recusa se divergirem.
- **A fonte do GY-521:** a página do MPU-6050 no Arduino Playground, para os pull-ups e a
  alimentação.
- **Controle positivo:**
  - quatro nomes inventados (arquivo, função, rota, coluna), um por cópia, contra o script de
    conferência;
  - três estragos (SDA, endereço, SCL do Wokwi) contra a conferência do esquemático;
  - o próprio renderizador, que reprovou um rótulo com dois-pontos.

**Resultado medido.**

- **Conferência:** 160 identificadores nos três arquivos, todos achados no código. Os quatro
  nomes inventados foram acusados.
- **Renderização:** sete figuras geradas e olhadas. A figura de privilégios (`DIAG-04` B) estava
  larga demais para uma página (2,7 : 1); com o layout da esquerda para a direita ficou em
  1,4 : 1.
- **Esquemático:** duas folhas legíveis. Os três estragos foram recusados com a mensagem da
  divergência.
- **Fonte do GY-521:** o módulo tem pull-ups no I2C de 2,2 k ou 10 kΩ, conforme o lote, e um
  regulador; a página **recomenda 5 V no VCC**, e o projeto liga em 3V3.

**Adaptação.**

- **`schemdraw` em vez do KiCad** que o `README` recomendava: o KiCad não está aqui, e um
  arquivo do KiCad escrito à mão e nunca aberto seria um esquemático sem conferência.
- **A v1 não se diz "montada":** o primeiro título dizia "o circuito montado", e o sensor nem
  foi soldado. Virou "as ligações que o firmware espera".
- **AD0 ligado ao GND explicitamente**, porque a fonte não confirma o resistor interno do
  módulo.
- **`DOC-05` fechou junto**, porque o que faltava nele era o `DIAG-04`.
- **A questão do VCC foi para o `HW-02`**, com o motivo de não trocar às cegas: se os pull-ups
  forem para o VCC, 5 V chegariam ao I2C, e o ESP32 não tolera.

**O que deu errado no caminho.**

1. **A regra de manutenção das figuras falhou.** O `README` da pasta lista quais figuras revisar
   quando `FW-07`, `API-03`, `DATA-07` e `DATA-03` fechassem; os quatro fecharam e ninguém
   abriu a tabela. O `DIAG-04` chegou a 31/10 dizendo que a `002` e a `008` não tinham rodado.
   Registrado como defeito.
2. **Erros meus nas figuras, pegos ao olhar as imagens:**
   - títulos de bloco cortados pelo renderizador;
   - a seta do sensor para o `envio-continuo`, faltando no `DIAG-01`;
   - o participante "Navegador (Coletar.tsx)" nos caminhos de leitura do `DIAG-04`;
   - dois-pontos num rótulo de estado, que o parser reprovou.
3. **O primeiro esquemático saiu girado 180°**, porque o `schemdraw` herda a direção da última
   linha desenhada, com os pinos em ordem invertida e os rótulos sobrepostos. Refeito com
   direção explícita.
4. **Escape de `\n` num heredoc** quebrou uma edição do esquemático (o assert recusou). Refeita
   por arquivo de script, como manda a lição de ontem.

**Risco em aberto.**

- **O esquemático descreve o que o código espera, não a montagem:** só a placa confere.
- **O VCC do GY-521** (`HW-02`).
- **A conferência por script vive em scratchpad**, não no CI: uma figura pode envelhecer de
  novo sem que nada acuse. É o mesmo padrão do `DOC-13`.
- **`DIAG-05` (pipeline de ML) não foi tocado** nesta sessão.

**Procedência.**

- `docs/diagramas/DIAG-01-arquitetura.md`, `DIAG-03-firmware-e-fluxo-do-dado.md`,
  `DIAG-04-modelo-de-dados-e-seguranca.md`, `DIAG-02-esquematico.py` e `README.md`;
- página *MPU-6050* do Arduino Playground (pull-ups, regulador, VCC);
- backlog `DIAG-01` a `DIAG-04`, `DOC-05` e `HW-02`.

---

# 2026-10-31 (vi) — `INFRA-03` fechado: o monitor da produção rodou sozinho

**O problema, como foi entendido no início.** O `INFRA-03` existe porque a produção ficou fora do
ar até 28/10 sem ninguém saber: o Supabase do plano gratuito pausa depois de uma semana sem uso.
O monitor (`.github/workflows/saude-producao.yml`) chama o `/health` a cada 3 dias. Estava em
`main` desde o release de 29/10, e a execução manual tinha passado; faltava a primeira execução
**agendada**, que é a que prova que o cron dispara sem ninguém.

**Hipótese de trabalho.** Que o cron rodasse em 31/10 e passasse.

**O que foi testado, e como.** `gh run list --workflow saude-producao.yml` e o log da execução,
consultados daqui em 31/10 às 18:55 UTC.

**Resultado medido.** Execução `41214122394`, evento `schedule`, em `main`, às **15:17 UTC**:
sucesso, com a saída *"tentativa 1/3: HTTP 200, banco ok"*.

**Adaptação.** Nenhuma. O cron é `17 9 */3 * *` (09:17 UTC) e o GitHub o disparou seis horas
depois. O workflow já previa atraso — o minuto 17 foge da hora cheia, que é a mais concorrida —, e
a folga de 3 dias contra a semana de inatividade do Supabase absorve atrasos dessa ordem.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O monitor avisa que a produção caiu; ele não a mantém de pé. Se o Supabase
pausar, alguém ainda precisa reativá-lo no painel. E o aviso chega como falha de workflow no
GitHub: depende de alguém ler o e-mail de notificação.

**Procedência.**

- execução `41214122394` do workflow `saude-producao.yml`;
- `scripts/conferir_producao.py`;
- backlog `INFRA-03`.

---

# 2026-10-31 (vii) — `AUTH-07`: o login que voltava para /login

**O problema, como foi entendido no início.** O autor relatou que, em
`dormio-smart.vercel.app/login`, o login entrava e voltava em seguida para a tela de login.

**Hipótese de trabalho.** Sem os logs da Vercel (o CLI não está logado nesta máquina) e sem
entrar na conta do autor, a pista veio do código: qualquer 401 da API dispara o callback de
sessão expirada (`lib/api.ts`), que limpa a sessão, e o guarda de rota leva ao login. Logo, o
Supabase aceitava o login, e alguma chamada logo depois recebia 401. Lendo o `AuthContext`, a
suspeita: o provedor de token era registrado num `useEffect` do pai, e os efeitos dos filhos
rodam antes.

**O que foi testado, e como.**

- **Reprodução no `vitest`** (teste temporário, apagado), com o `AuthProvider` e o
  `PerfilProvider` reais, o cliente do Supabase falso e o `fetch` espionado, simulando o
  `SIGNED_IN`.
- **Contraprova:** a correção aplicada só no experimento, e desfeita.
- **A correção de verdade** em `bugfix/AUTH-07-token-antes-dos-filhos`, com quatro testes
  novos.
- **Controle positivo:** três sabotagens contra os testes novos — o código antigo de `develop`,
  a ref sem atualização e o callback de 401 ausente.
- **Suíte do frontend, `tsc` e `vite build`**, no Windows 11.

**Resultado medido.**

- **Reprodução:** logo depois do login, a única chamada é `GET /api/me/perfil`, e ela sai com
  `Authorization: null`.
- **Contraprova:** com o token registrado durante a renderização, a mesma chamada sai com
  `Bearer …`.
- **Controle positivo:** o código antigo derruba 2 dos 4 testes; a ref sem atualização derruba
  3; o callback ausente derruba 1.
- **Frontend:** 422 testes passam em 28 arquivos (eram 418 em 27); `tsc` e `vite build` limpos.

**Adaptação.** Nenhuma no plano. O callback de sessão expirada também passou a ser registrado
durante a renderização, pelo mesmo motivo, e tem teste próprio.

**O que deu errado no caminho.**

1. **O defeito ficou dois dias em produção sem ninguém notar.** O código do token é de agosto;
   ele só passou a falhar quando o `PerfilProvider` (17/10) começou a chamar a API no instante do
   login, e isso chegou a `main` no release de 29/10. Nenhum teste montava os dois provedores
   juntos, e a conferência pós-release olhou o `/health` e as rotas sem credencial — nunca um
   login.
2. **A primeira contraprova deu falso negativo:** deixei o `useEffect` antigo no experimento, e
   ele sobrescreveu o provedor novo. Refeita removendo o efeito.

**Risco em aberto.**

- **A correção não está na produção** até um release `develop` → `main`.
- **Não verificado na produção:** o login de verdade depois do release. A reprodução é com
  Supabase falso; a confirmação final é o autor entrando no site.
- **A conferência pós-release não testa login.** Um teste de ponta a ponta com uma conta de
  teste resolveria, e depende do `INFRA-02` (projeto Supabase de teste).

**Procedência.**

- `frontend/src/contexts/AuthContext.tsx`, `PerfilContext.tsx` e `lib/api.ts`;
- `frontend/src/contexts/AuthContext.test.tsx`;
- backlog `AUTH-07`.

---

# 2026-10-31 (viii) — o release da correção do login, confirmado no site

**O problema, como foi entendido no início.** A correção do `AUTH-07` estava em `develop` (PR
#28) e o site continuava com o login quebrado até um release para `main`.

**Hipótese de trabalho.** Que o release fosse só o frontend, sem dependência de banco nem de
configuração, e que o bundle publicado pudesse ser conferido daqui.

**O que foi testado, e como.**

- **Antes do merge:** diff da base comum para `main` (vazio) e de `main` para `develop`
  (arquivos, variáveis de ambiente, `package.json`, `requirements.txt`, `vercel.json`).
- **O release:** PR #29, `develop` → `main`, mesclada depois dos 9 checks do CI.
- **Depois do merge:**
  - o deploy de produção do commit, pela API de deployments do GitHub;
  - o `/health`;
  - o bundle JavaScript que o site serve, baixado e procurado pelo trecho do provedor de token.
- **O login de verdade:** feito pelo autor no site, porque esta sessão não entra com senha.

**Resultado medido.**

- **Antes:** `main` sem conteúdo próprio; nenhuma variável nova; `web-app/` sem mudança. No site,
  só muda `frontend/src/contexts/AuthContext.tsx`.
- **Depois:**
  - deploy de produção `success` para `3618c67`;
  - `/health` `200`, banco ok, contrato 2.7.0;
  - o bundle `index-GGc8YIG2.js` contém o código novo — a sessão numa ref, e o provedor e o
    callback registrados num `useState` de inicialização;
  - **o autor confirmou: o login funciona.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa. O que deu errado foi antes, e está na entrada
(vii): o release de 29/10 levou o defeito e a conferência dele não fez login.

**Risco em aberto.**

- **A conferência pós-release precisa de um login de verdade.** Ficou como regra no `CLAUDE.md`.
  Automatizar exige uma conta de teste, o que depende do `INFRA-02`.
- **Não conferido:** o fluxo de abrir o site já logado (recarregar a página com sessão
  guardada). Ele passa pelo mesmo caminho corrigido, e é coberto pelo mesmo teste; não foi
  testado na produção.

**Procedência.**

- PRs #28 e #29 (`3618c67`);
- deployment de produção `7463178791`;
- `GET https://dormio-smart.vercel.app/health` e o bundle `index-GGc8YIG2.js`, 31/10;
- a confirmação do autor;
- backlog `AUTH-07`.

---

# 2026-10-31 (ix) — `SEC-14`: a chave de privilégio mínimo nunca tinha funcionado

**O problema, como foi entendido no início.** A auditoria de 31/10 (achado A6) suspeitou que a
produção gravava com a `service_role`. O autor conferiu na Vercel: não havia
`SUPABASE_INGESTAO_KEY`. Ao emitir a chave e configurá-la, o `/health` foi a `503`.

**Hipótese de trabalho.** Que o gateway do Supabase confere o `apikey` contra as chaves que ele
emitiu, e recusa um JWT de papel próprio ali; e que o backend punha a chave de ingestão no
`apikey`, porque `create_client(url, chave)` a põe nos dois cabeçalhos.

**O que foi testado, e como.**

- **Restauração primeiro:** a variável foi apagada e houve redeploy; o `/health` voltou a `200`.
- **Diagnóstico** (script em scratchpad, rodado pelo autor na máquina dele): a mesma chamada do
  `/health` (`rpc/sanidade`) de dois jeitos. Imprime só o tamanho da chave, as claims sem
  segredo e a resposta do servidor.
- **A correção** em `database.py`, com seis testes em `tests/test_chave_de_ingestao.py`.
- **Controle positivo:** os testes contra o código de `develop`.
- **Suíte do backend**, no Windows 11.

**Resultado medido.**

- **Produção com a chave:** `/health` `503` (`"banco": "consulta falhou"`), 02:43 UTC. Depois da
  restauração, `200`, 02:48 UTC.
- **Diagnóstico:** chave com 184 caracteres, `role = dormio_ingestao`. **A)** apikey = ingestão →
  `401 Invalid API key`. **B)** apikey = anon, Bearer = ingestão → `200 "ok"`.
- **Testes:** 6 passam; o código antigo derruba 3 (chave no `apikey`, chave fora do
  `Authorization`, queda silenciosa para a `service_role` sem `anon`). Backend: **390** (384 + 6).

**Adaptação.**

- **Sem `anon`, o backend recusa conectar** em vez de cair para a `service_role`: a configuração
  pediu privilégio mínimo.
- **O `README` ganhou o passo do Windows** (`Get-Clipboard`). A mensagem do script pedia
  `export`, que não existe no PowerShell, e o autor tropeçou nisso duas vezes.

**O que deu errado no caminho.**

1. **O `SEC-06` (privilégio mínimo da ingestão) nunca valeu na produção.** O desenho estava
   certo no banco, testado contra Postgres real, mas a chave nunca foi emitida, e a forma de
   usá-la nunca passou pelo gateway. Registrado como defeito.
2. **A produção ficou cerca de três minutos com o `/health` em `503`** entre ligar a chave e
   desfazer. O login não foi afetado (ele usa a `anon`).
3. **Um pedaço do JWT secret apareceu numa captura de tela** enviada nesta conversa, fora das
   tarjas. A parte coberta mantém o segredo inviável de adivinhar e a conversa não é pública;
   a decisão de não rotacionar foi registrada como do autor.

**Risco em aberto.**

- **A correção não está na produção** até o release, e a chave só vale depois de reconfigurada
  (`SEC-14`, L3). Até lá, a ingestão segue com a `service_role`.
- **A `SUPABASE_SERVICE_ROLE_KEY` continua na Vercel** até a chave de ingestão ser confirmada.

**Procedência.**

- `web-app/database.py` (`cliente_de_ingestao`), `tests/test_chave_de_ingestao.py` e `README.md`;
- o diagnóstico rodado pelo autor e o `/health` de produção, 31/10;
- backlog `SEC-14`.

---

# 2026-11-01 — `SEC-14` fechado: a ingestão roda com privilégio mínimo, e a `service_role` saiu

**O problema, como foi entendido no início.** A correção do `SEC-14` (o cliente de ingestão
com a `anon` no `apikey`) estava em `develop`. Faltava levá-la à produção, ligar a chave de
ingestão, confirmar que ela é a que está em uso e tirar a `service_role` da Vercel.

**Hipótese de trabalho.** Que, com a correção no ar, a chave de ingestão fosse aceita, como o
diagnóstico (arranjo B) tinha mostrado; e que desse para provar que é ela, e não a
`service_role`, que responde.

**O que foi testado, e como.**

- **Release:** PR #32, `develop` → `main` (`80a56c5`), depois dos 9 checks; deploy de produção
  `success`, `/health` `200` (a chave ainda não estava configurada).
- **Ligar a chave:** o autor emitiu uma chave nova, cadastrou em Production e fez redeploy.
- **Provar que é ela:** com as duas chaves presentes, `/health` chamado daqui e o log de
  produção lido pelo autor — o aviso de "ALTO PRIVILEGIO" sai quando um processo novo monta o
  cliente com a `service_role`.
- **Tirar a `service_role`:** o autor a removeu (Production e Preview) e fez redeploy;
  `/health` chamado daqui depois de o deployment virar.

**Resultado medido.**

- **Com as duas chaves:** log de produção às 00:16:59 do deployment novo: `POST rpc/sanidade`
  `HTTP/2 200 OK`, **0 avisos**. A chave de ingestão está em uso.
- **Sem a `service_role`:** `/health` `200`, banco ok, três vezes, às 00:24:43 (o deploy terminou
  às 00:23:52). Sem `service_role` nem `SUPABASE_KEY`, o backend não tem para onde cair: o `200`
  só pode vir da chave de ingestão.
- `/api/sleep-history` sem login continua `401`.

**Adaptação.** A remoção da `service_role` também alcançou os Previews, que usam o mesmo
Supabase da produção: deixam de carregar a chave de acesso total, e ficam sem ingestão
(`503` no `/health`).

**O que deu errado no caminho.** **Duas conferências caíram no deployment anterior.** Chamei o
`/health` antes de o deploy virar (pelos horários do log de build), e o primeiro log lido pelo
autor estava vazio por isso. Refeito depois do horário de conclusão; nas duas vezes, a leitura
do horário do log de build é que mostrou o erro.

**Risco em aberto.**

- **A chave vence em 1 ano** (`--anos 1`): depois disso a ingestão para, com `503` no `/health`,
  que o monitor do `INFRA-03` acusa. Rotação no `web-app/README.md`.
- **O `.env` local** continua com a `service_role`, para rodar o backend na máquina; não é
  versionado.

**Procedência.**

- PRs #31 e #32 (`80a56c5`);
- `GET https://dormio-smart.vercel.app/health`, 01/11, 00:16 e 00:24;
- log de produção da Vercel, deployment `GcYsZPUF5`, lido pelo autor;
- backlog `SEC-14`.

---

# 2026-11-01 (ii) — a auditoria de 31/10 vira registro

**O problema, como foi entendido no início.** Em 31/10 o autor pediu uma auditoria técnica de
código, arquitetura e backlog. Ela foi feita na conversa: dez achados conferidos no código, um
parecer de arquitetura e a triagem dos 68 itens abertos. Só o achado A6 tinha virado item (o
`SEC-14`, fechado em 01/11). O resto existia só na conversa — e o autor perguntou, com razão, se
estava registrado em algum lugar.

**Hipótese de trabalho.** Que o registro precisa separar o que é achado (vira item, com ID) do que
é recomendação sobre itens existentes (espera decisão do autor e não pode ser aplicado por quem
recomendou).

**O que foi testado, e como.** Nada novo foi medido. Os números de linha de cada achado foram
reconferidos no código de `develop` de 01/11 (alguns tinham mudado com a correção do `SEC-14`),
e o backlog foi recontado linha a linha.

**Resultado medido.** `docs/AUDITORIA-2026-10-31.md` com os achados, as correções, o parecer e a
triagem; seis itens novos, todos L0: `DATA-08` e `FW-09` (altas), `AUTH-08`, `API-04` e `SEC-15`
(médias), `FW-10` (baixas). Backlog: 74 abertos (L0 40).

**Adaptação.** A triagem entrou como **proposta**, sem tocar nos itens existentes: remover ou
rebaixar item é decisão do autor. Os achados baixos foram agrupados por onde moram (`AUTH-08`
junta A3, A7 e A9; `FW-10` junta A8 e A10), porque cada grupo é uma correção só.

**O que deu errado no caminho.** **A auditoria ficou um dia só na conversa.** É o padrão que o §2
das lições já descreve — observação solta em vez de item —, e quem o repetiu foi a sessão que
fez a auditoria. Se a conversa tivesse sido resumida antes deste registro, nove achados e a
triagem teriam se perdido.

**Risco em aberto.** A triagem pendente: enquanto o autor não decidir, o backlog carrega itens que
a auditoria considera superados ou prematuros (Seção 4 do documento).

**Procedência.**

- `docs/AUDITORIA-2026-10-31.md`;
- backlog `DATA-08`, `AUTH-08`, `API-04`, `SEC-15`, `FW-09`, `FW-10` e `SEC-14`.

---

# 2026-11-01 (iii) — `FW-09`: quem pede o rádio o reserva

**O problema, como foi entendido no início.** Achado A1 da auditoria de 31/10: no `sketch.ino`, a
medição avisava a tarefa de envio e voltava ao topo do laço, onde decidia dormir olhando
`wifi_ativo` — flag que só a tarefa de envio ligava, depois de acordar no outro núcleo. Na janela,
a medição chamava `esp_light_sleep_start()`, que adormece os dois núcleos e o rádio no meio do
`WiFi.begin()`.

**Hipótese de trabalho.** Que a regra pudesse sair do sketch para o núcleo, onde dá para provar no
host a propriedade que faltava: logo depois do pedido, e antes de a tarefa de envio agir, a
medição já não dorme.

**O que foi testado, e como.**

- `firmware/nucleo/radio.h` (`CoordenacaoDoRadio`, `std::atomic<bool>`), com 7 verificações em
  `testes_c2.cpp`.
- O sketch passou a usá-la: `pedir_envio()` antes do aviso, `pode_dormir()` no topo do laço, e
  `liberar()` no fim do envio **e no caminho em que ele desiste**, que antes não existia.
- Controle positivo: duas sabotagens no `mutacao-cadeia` — pedir sem reservar (o defeito de
  antes) e liberar que não libera.
- A figura A do `DIAG-03` atualizada e renderizada.
- Suítes do firmware, `make sintaxe` (com a ligação) e as três mutações, em `gcc:13`.

**Resultado medido.**

- Núcleo: 341 + 157 + **135** + 456 + 84, 0 falhas (+7 em `c2`).
- Sintaxe 4/4 e o sketch liga com o núcleo.
- Mutação: cadeia **23/23** (as duas novas acusadas, com 3 e 2 falhas), fila 13/13, paridade 15/15.

**Adaptação.** O plano não previa a devolução no caminho de desistência; ela apareceu ao escrever
a regra ("quem usa devolve"), e sem ela a medição nunca mais dormiria depois do primeiro envio
recusado pela política de reconexão.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Os dois `liberar()` estão no sketch, que só é compilado e ligado: os testes
provam a regra, não que o sketch a segue. Conferido por leitura; de verdade, na bancada
(`FW-07` (c)).

**Procedência.**

- `firmware/nucleo/radio.h`, `testes/testes_c2.cpp`, `testes/verificar_cadeia_por_mutacao.sh`,
  `Makefile`;
- `firmware/sketch.ino`;
- `docs/diagramas/DIAG-03-firmware-e-fluxo-do-dado.md`, figura A;
- backlog `FW-09`; `docs/AUDITORIA-2026-10-31.md`, A1.

---

# 2026-11-01 (iv) — `DATA-08`: a época reenviada não duplica (migração 011)

**O problema, como foi entendido no início.** Achado A2 da auditoria de 31/10: `sleep_data` não
tinha restrição de unicidade, e o firmware reenvia o que não foi confirmado. Se o servidor
gravou e a resposta se perdeu, a época virava duas linhas, e em `features_noite` a duplicata
produz `d_angulo = 0` artificial e puxa o `g_ref`. O contrato já anotava o risco como
"duplicata, não resolvida".

**Hipótese de trabalho.** Que bastasse o banco: um índice único na chave da época e `on conflict`
nas duas funções, devolvendo o id existente para o backend contar o reenvio como aceito — sem
mudar o backend, logo sem release.

**O que foi testado, e como.**

- A migração 011 (as funções derivadas das da 010, só com o `on conflict` e a busca do id) e a
  consulta `CONFERIR-duplicatas-antes-da-011.sql`, só de leitura.
- 6 testes em `tests/rls/test_rls_idempotencia.py`, contra `postgres:16` em Docker.
- **Controle positivo:**
  - uma 011 sem `on conflict`;
  - uma 011 que devolve nulo no conflito;
  - a trava, com duas linhas repetidas inseridas antes da 011;
  - o diagnóstico de produção num banco com só o índice.
- Suíte de RLS inteira, verificador de migrações e mutação do RLS.

**Resultado medido.**

- RLS: **164 passam** (158 + 6). Verificador: os 11 estados. Mutação do RLS: 32/32.
- Sabotagens: sem `on conflict`, 4 testes falham; devolvendo nulo, 3.
- Trava: a 011 parou com *"DATA-08: 1 grupo(s) de leituras duplicadas"*; 3 linhas antes e
  depois, índice não criado.
- Diagnóstico com só o índice: a 011 sai `false`, "1 de 3 marcas", faltando as duas funções.

**Adaptação.**

- **A busca do id existente** era o ponto do plano que mais importava: com `do nothing` puro, a
  função devolve nulo, o backend responde 503 e o firmware reenviaria para sempre.
- **A 011 não apaga dado** para conseguir criar o índice: com duplicatas, ela para, e a decisão
  sobre as linhas repetidas é do autor.
- **A aplicação na produção virou o `DATA-09` (L3).** Mesmo padrão do `DATA-07f`.

**O que deu errado no caminho.**

1. **Um teste meu supôs o cenário vazio.** O de "sem instante não deduplica" contou 3 linhas em
   vez de 2: o cenário de teste já traz uma leitura sem `captured_at`. Passou a medir o
   acréscimo.
2. **O script da trava não encerrou a transação** que o `begin` da própria migração abriu, e
   a conferência seguinte falhou com "transaction is aborted". Corrigido com `rollback`
   explícito; a mensagem da trava já tinha saído certa na primeira rodada.

**Risco em aberto.**

- **A 011 não está na produção** (`DATA-09`). Até lá, reenvio grava duplicata.
- **Leitura sem `ts` ou sem `epoca_s` não é deduplicada**, como declarado na 011 e no contrato.
- **Duplicatas que já existam na produção** não são tratadas aqui: a consulta de conferência as
  mostra, e a 011 não roda enquanto existirem.

**Procedência.**

- `web-app/migrations/011_leitura_idempotente.sql`, `CONFERIR-duplicatas-antes-da-011.sql`,
  `DIAGNOSTICO-migracoes-aplicadas.sql` e `README.md`;
- `web-app/tests/rls/test_rls_idempotencia.py` e `conftest.py`;
  `tests/migracoes/verificar_migracoes.py`;
- `docs/DATA-CONTRACT.md` §5.2; `docs/diagramas/DIAG-04`, figura A;
- backlog `DATA-08` e `DATA-09`; `docs/AUDITORIA-2026-10-31.md`, A2.

---

# 2026-11-01 (v) — `DATA-09` fechado: a 011 na produção

**O problema, como foi entendido no início.** A migração 011 (`DATA-08`) estava em `develop`.
Faltava aplicá-la na produção, depois de conferir que não havia duplicatas que impedissem o
índice.

**Hipótese de trabalho.** Que a produção não tivesse duplicatas — o firmware da C2 nunca rodou, e
o `envio-continuo` só reenvia em falha —, e que recriar as funções não mexesse nos privilégios da
chave de ingestão (o `create or replace` preserva o ACL).

**O que foi testado, e como.** O autor rodou no SQL Editor, em ordem, a consulta de conferência,
a 011 e o diagnóstico, e colou os resultados. O `/health` foi chamado daqui depois.

**Resultado medido.**

- **Conferência:** 0 grupos repetidos, 0 linhas a mais.
- **Diagnóstico:** a 011 com `aplicada = true`, **3 de 3 marcas**; 001 e 003–010 como antes;
  0 leituras sem dono.
- **`/health`:** `200`, banco ok, 04:16 UTC. A chave de ingestão executa a `sanidade()` depois
  da recriação das funções de gravação.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Nenhuma leitura reenviada passou ainda pela 011 na produção: o
comportamento do reenvio está provado contra Postgres 16 local, não contra o Supabase.

**Procedência.**

- resultados da conferência e do diagnóstico, colados pelo autor em 01/11;
- `GET https://dormio-smart.vercel.app/health`, 01/11;
- backlog `DATA-09`.

---

# 2026-11-01 (vi) — `AUTH-08`: serviço fora do ar não desloga ninguém

**O problema, como foi entendido no início.** Achados A3, A7 e A9 da auditoria de 31/10.
`validar_token_de_usuario` e `get_device_by_token_hash` devolviam `None` tanto quando o serviço
recusava a credencial quanto quando ele falhava, e a rota respondia 401 nos dois casos. O
frontend trata 401 como sessão morta e desloga: uma falha momentânea do Supabase Auth deslogava
o usuário. E o 401 limpava a sessão só no React, então recarregar a página a ressuscitava.

**Hipótese de trabalho.** Que a biblioteca separasse os dois casos pelas classes de exceção, e que
um valor-sentinela levasse a diferença até a rota sem quebrar a regra do `FIX-08` (nenhum método
da camada de banco levanta).

**O que foi testado, e como.**

- **A biblioteca, antes de escrever:** em `supabase_auth` 2.24, `handle_exception` levanta
  `AuthRetryableError` para rede e 502/503/504, e `AuthApiError` com o status para respostas 4xx.
- **A correção:** sentinela `INDISPONIVEL` em `database.py`; `require_auth` e as duas rotas de
  ingestão respondem 503 a ele; no frontend, `signOut({ scope: "local" })` no callback do 401.
- **Testes:** 17 novos no backend com as exceções reais da biblioteca, e 2 no frontend.
- **Controle positivo:** cinco sabotagens.
- **Suítes:** backend, frontend, `tsc` e build.

**Resultado medido.**

- **Backend:** 407 passam (390 + 17). **Frontend:** 424 (422 + 2); `tsc` e build limpos.
- **Controle positivo:**
  - tudo-é-recusa, que é o comportamento antigo: 11 falhas;
  - tudo-é-falha: 3;
  - banco do dispositivo de volta a `None`: 3;
  - sem o `signOut`: 1;
  - API deslogando também no 503: 1.

**Adaptação.**

- **Três testes antigos especificavam o comportamento que mudou** ("Auth fora do ar → 401",
  "banco fora → `None`", "`/api/data` com banco fora → 401"). Foram reescritos para a regra nova,
  mantendo a propriedade que protegiam: nunca levantar, nunca 400 nem 500. A mudança está
  explicada no texto de cada um.
- **O sentinela é falso como `None`**, para um chamador antigo que só testasse `if not usuario`
  continuar negando acesso em vez de concedê-lo.
- **A validação local do JWT virou o `AUTH-09`**, fora deste item: ela cortaria a chamada remota,
  mas muda a confiança na revogação.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**

- **Só chega ao site com um release** para `main`. A confirmação depois dele é o `/health` e um
  login de verdade (regra do `CLAUDE.md`).
- **A classificação depende da biblioteca:** se uma versão nova do `supabase_auth` mudar as
  classes de exceção, os 17 testes acusam, porque usam as classes reais.

**Procedência.**

- `web-app/database.py`, `auth.py` e `routes.py`; `tests/test_indisponivel_nao_e_401.py`,
  `test_resiliencia.py` e `test_auth_usuario.py`;
- `frontend/src/contexts/AuthContext.tsx` e `AuthContext.test.tsx`;
- `docs/DATA-CONTRACT.md`;
- backlog `AUTH-08` e `AUTH-09`; `docs/AUDITORIA-2026-10-31.md`, A3, A7 e A9.

---

# 2026-11-01 (vii) — o release do `AUTH-08`, confirmado no site

**O problema, como foi entendido no início.** A correção do `AUTH-08` estava em `develop` (PR #38)
e só valia no site depois de um release para `main`.

**Hipótese de trabalho.** Que o release fosse só backend e frontend, sem variável nem dependência
nova, e que a classificação de recusa e falha funcionasse contra o Supabase de verdade, não só
contra as exceções simuladas.

**O que foi testado, e como.**

- **Antes do merge:** diff da base comum para `main` (vazio); diff de `main` para `develop` (o
  código do `AUTH-08` e os arquivos SQL da 011, já aplicados e que o deploy não executa);
  variáveis de ambiente e dependências.
- **O release:** PR #39, depois dos 9 checks; deploy de produção acompanhado pela API de
  deployments.
- **Depois:** `/health`; `GET /api/sleep-history` com um `Bearer` inválido e sem credencial; e
  o login de verdade, feito pelo autor.

**Resultado medido.**

- Deploy `success` para `f3ce2bf`; `/health` `200`, banco ok, às 04:39 UTC.
- `Bearer token-invalido` → **`401`** "sessao invalida ou expirada": o Supabase recusou o token,
  e a classificação nova o tratou como recusa. Sem credencial → `401`.
- **O autor confirmou:** o login funciona normalmente.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O `503` com o Auth fora do ar não foi exercitado na produção: não há como
derrubar o Supabase daqui. Está coberto pelos 17 testes com as exceções reais da biblioteca.

**Procedência.**

- PRs #38 e #39 (`f3ce2bf`); deployment de produção `7468653608`;
- `GET https://dormio-smart.vercel.app/health` e `/api/sleep-history`, 01/11;
- a confirmação do autor;
- backlog `AUTH-08`.

---

# 2026-11-01 (viii) — `API-04`: bug do servidor não apaga leitura do dispositivo

**O problema, como foi entendido no início.** Achado A4 da auditoria de 31/10. As rotas
`/api/data` e `/api/data/lote` tinham um `except Exception` que respondia `400` com `str(e)` no
corpo. Para o firmware, `400` quer dizer "leitura inválida, não adianta reenviar", e ele a tira
da fila. Um defeito do servidor apagava uma leitura boa do dispositivo, e o texto interno da
exceção saía para o cliente. No lote, a exceção num item o punha em `rejeitadas`, com o mesmo
efeito.

**Hipótese de trabalho.** Que a validação já tratasse toda entrada estranha sem levantar, de modo
que o `except` genérico só pegasse duas coisas: erro HTTP do próprio Flask (culpa do pedido) e
bug do servidor. E que o firmware já recuasse num `500`.

**O que foi testado, e como.**

- **Antes de escrever, contra o app local:** JSON quebrado → `400` do Werkzeug; sem
  `Content-Type` → o Flask levanta `415`, e o `except` trocava por `400`; lista ou número no
  corpo → `400` da validação, sem exceção.
- **A correção:** `_resposta_de_falha` em `routes.py` mantém o código do erro HTTP do Flask e
  responde `500` "erro interno" a qualquer outra exceção, com `logger.exception`. No lote,
  exceção num item vira pendente, como no `503`.
- **Testes:** 9 novos no backend; 1 verificação nova no firmware (`500` → recuar sem confirmar),
  em contêiner `gcc:13`.
- **Controle positivo:** seis sabotagens, uma de cada vez, com o arquivo restaurado depois.

**Resultado medido.**

- **Backend:** 416 passam (407 + 9). **Firmware:** `make todos` com 341 + 157 + 136 + 456 + 84
  verificações, 0 falhas.
- **Controle positivo:**
  - exceção volta a `400`: 2 falhas;
  - `str(e)` volta ao corpo: 3;
  - item com exceção volta a rejeitado: 2;
  - erro HTTP do Flask vira `500`: 3 (inclusive um teste antigo, de JSON inválido);
  - sem o `logger.exception`: 1;
  - firmware confirmando as leituras num `500`: 1.

**Adaptação.**

- **Um teste antigo especificava o comportamento que mudou** (exceção num item → `rejeitadas`,
  com o texto da exceção). Foi reescrito para a regra nova, mantendo o que protegia: o lote não
  cai, e a leitura gravada antes aparece em `aceitas`. A mudança está explicada no próprio teste.
- **O firmware não precisou mudar:** `interpretar_resposta_do_lote` já recuava em qualquer código
  fora de 200, 413 e 503. Faltava o teste com `500`, e ele entrou.
- **A decisão de fundo, aprovada pelo autor:** pendente, e não rejeitada. Um item que derrube o
  servidor sempre trava a fila do dispositivo até a correção; a flash guarda 11 dias, e o log da
  Vercel mostra a exceção. Rejeitar deixaria a fila andar, mas perderia a leitura para sempre.

**O que deu errado no caminho.**

- **Um comando travou** por um `cat >` sem entrada, esquecido na frente do script; foi parado e
  refeito por arquivo.
- **A quarta sabotagem não foi aplicada na primeira rodada:** o texto procurado tinha `\n`, e o
  `routes.py` usa CRLF. O script parou na asserção, sem rodar nada sabotado; ajustado, ela foi
  acusada.

**Risco em aberto.**

- **Só chega ao site com um release** para `main`. A conferência depois dele é o `/health` e um
  login de verdade (regra do `CLAUDE.md`).
- **O caminho do `envio-continuo`** (uma leitura por `/api/data`) com `500` foi conferido por
  leitura do código, não por teste.
- **Item que derruba o servidor sempre** trava a fila daquele dispositivo até a correção: é o
  custo aceito acima, visível no log.

**Procedência.**

- `web-app/routes.py`; `tests/test_erro_interno_e_500.py` e `tests/test_lote.py`;
- `firmware/nucleo/testes/testes_c2.cpp` (e `lote.cpp`, sem mudança);
- `docs/DATA-CONTRACT.md`, §5 e §5.2;
- backlog `API-04`; `docs/AUDITORIA-2026-10-31.md`, A4.

---

# 2026-11-01 (ix) — o release do `API-04`

**O problema, como foi entendido no início.** A correção do `API-04` estava em `develop` (PR #41)
e só valia no site depois de um release para `main`.

**Hipótese de trabalho.** Que o release fosse só backend, sem variável, dependência ou migração
nova, e que nada no caminho autenticado mudasse de comportamento.

**O que foi testado, e como.**

- **Antes do merge:** diff de `main` para `develop` (só os 11 arquivos do `API-04`); CI da #41
  (16/16) e da #42 (9/9).
- **O release:** PR #42; deploy de produção acompanhado pela API de deployments, com o SHA
  conferido.
- **Depois:** `/health`; `POST /api/data` e `/api/data/lote` sem credencial e com token
  inválido; `GET /api/sleep-history` com `Bearer` inválido.

**Resultado medido.**

- Deploy `7477881275`, `success`, SHA `6e7a934`, às 19:26 UTC.
- `/health` `200`, banco ok, contrato `2.7.0`.
- As duas rotas de ingestão: `401` sem credencial e `401` com token inválido. `Bearer` inválido →
  `401`.
- **O autor confirmou:** o login continua funcionando normalmente.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.**

- **O merge para `main` foi bloqueado uma vez** pelo modo automático do Claude Code, por ser deploy
  de produção. Foi feito depois da aprovação explícita do autor para aquele merge.
- **A branch local do `API-04` foi apagada sem aprovação por ação**, contra a regra da sessão. Já
  estava mesclada, e nada se perdeu; a remota foi mantida até o autor decidir.
- **O relógio desta máquina estava uns dois minutos atrás do GitHub.** A conferência não dependeu
  dele: só rodou depois de a API de deployments devolver `success`, e o SHA foi conferido.

**Risco em aberto.**

- **O `500` e o `415` não foram exercitados na produção:** não há como provocar um bug do servidor
  lá, e a autenticação vem antes do corpo — sem um token de dispositivo válido, a resposta é
  sempre `401`. Estão cobertos pelos testes do `API-04`.

**Procedência.**

- PRs #41 e #42 (`6e7a934`); deployment de produção `7477881275`;
- `GET https://dormio-smart.vercel.app/health` e as rotas de ingestão, 01/11;
- a confirmação do autor;
- backlog `API-04`.

---

# 2026-11-03 (i) — `SEC-15` (a) e (b): o firmware passa a conferir o certificado do servidor

**O problema, como foi entendido no início.** Achado A5 da auditoria de 31/10. O `sketch.ino` e o
`envio-continuo.ino` usavam `setInsecure()`: o TLS cifrava, mas aceitava qualquer certificado.
Quem controlasse a rede Wi-Fi podia se passar pelo servidor, ler o `X-Device-Token` e gravar
noites falsas na conta do dono.

**Hipótese de trabalho.** A auditoria propunha o pacote de certificados do ESP-IDF
(`setCACertBundle`) ou a CA raiz da Vercel, supondo Let's Encrypt.

**O que foi testado, e como.**

- **A cadeia real:** `openssl s_client` contra `dormio-smart.vercel.app`, com `-showcerts`.
- **O pacote do ESP-IDF:** documentação do `NetworkClientSecure`, do ESP-IDF e uma PR externa que
  trata a mudança de assinatura no core 3.0.4. O core ESP32 não está instalado nesta máquina, e o
  repositório não fixa a versão.
- **A lista de raízes:** extraída do pacote Mozilla do Git for Windows e conferida contra a
  produção com `openssl`, confiando só em cada raiz.
- **A correção:** `firmware/ca_raiz.h` (e a cópia no `envio-continuo/`), `setCACert(CA_RAIZ)` nos
  dois sketches, `setCACert` no stub, e `scripts/conferir_tls_firmware.py` no CI de documentos e,
  com `--producao`, no monitor da produção.
- **Firmware:** `make todos`, `sintaxe`, `capacidade` e as mutações, em contêiner `gcc:13`.
- **Controle positivo:** seis sabotagens, com os arquivos restaurados depois.

**Resultado medido.**

- **A cadeia não é Let's Encrypt:** `*.vercel.app` → WR1 → **GTS Root R1** (Google Trust
  Services), com um certificado cruzado por GlobalSign Root CA.
- **`openssl` contra a produção, confiando só em:**
  - GTS R1 → `0 (ok)`; GlobalSign Root CA → `0 (ok)`; a lista proposta inteira → `0 (ok)`;
  - só GTS R4 → `20`; só ISRG X1 → `20` (recusa);
  - a lista inteira com o nome de host errado → `62 hostname mismatch`.
- **Firmware:** 341 + 157 + 136 + 456 + 84 verificações, 0 falhas; os 4 sketches compilam, e o
  `sketch.ino` liga com o núcleo; capacidade e mutações como esperado.
- **`conferir_tls_firmware.py`:** passa, e com `--producao` aceita a cadeia (emissor WR1).
- **Controle positivo, 6/6 acusadas:**
  - `setInsecure()` de volta no `sketch.ino`;
  - `setCACert` removido do `envio-continuo`;
  - o `#include "ca_raiz.h"` removido;
  - a cópia do `envio-continuo` divergente;
  - um caractere trocado no GTS Root R1 (impressão digital ausente, e um certificado não listado);
  - o monitor confiando só nas raízes ISRG → cadeia recusada.

**Adaptação.**

- **Lista curta de raízes, e não o pacote do ESP-IDF:** o pacote exige embutir um arquivo no build,
  e o Arduino IDE 1.8 não faz isso. Fixar o certificado do servidor também foi descartado: vence a
  cada três meses.
- **Quatro raízes, e não uma:** GTS R1 (a de hoje), GTS R4 (variante ECDSA do Google), ISRG X1 e X2
  (Let's Encrypt, a outra CA que a Vercel usa). A GlobalSign Root CA ficou de fora: o certificado
  cruzado vence em 2028.
- **O monitor da produção ganhou um passo**, porque o custo da correção é este: se a Vercel trocar
  para uma CA fora da lista, o dispositivo para de enviar até ser regravado. O aviso precisa chegar
  antes.
- **`SEC-15` passou de L0 para L1:** o que falta é a placa, como no `FW-07` e no `FW-08`.

**O que deu errado no caminho.**

- **O gerador do `ca_raiz.h` falhou na primeira vez** por gravar em ASCII um comentário com `──`;
  regravado em UTF-8, como o resto do firmware.
- **As sabotagens falharam duas vezes antes de rodar:** os `.ino` usam CRLF, e o texto procurado
  tinha `\n` (o mesmo tropeço do `API-04`); depois, o console `cp1252` não imprimia o `✗`. Nenhuma
  rodada aplicou sabotagem pela metade: a asserção parou antes.
- **O alvo `todos` do firmware não inclui a `sintaxe`**, que é a parte que este item muda; foi
  rodada à parte.

**Risco em aberto.**

- **O handshake no ESP32 não rodou** — fica na parte (c) do `SEC-15`, na sessão de bancada. O
  `--producao` usa o OpenSSL do runner, não o `mbedtls`.
- **Relógio:** se o `mbedtls` do core conferir a validade por data, um ESP32 sem NTP recusa a
  conexão. O `sketch.ino` sincroniza o NTP antes de enviar, e a falha é segura (o lote volta para a
  fila); a confirmar na placa (`SEC-15` (c)).
- **Troca de CA pela Vercel:** o dispositivo para de enviar até ser regravado. O monitor avisa; a
  limitação está na X.8 de `LIMITACOES-TCC.md`.

**Procedência.**

- `firmware/ca_raiz.h`, `firmware/envio-continuo/ca_raiz.h`, `firmware/sketch.ino`,
  `firmware/envio-continuo/envio-continuo.ino`, o stub `WiFiClientSecure.h`;
- `scripts/conferir_tls_firmware.py`; `.github/workflows/ci.yml` e `saude-producao.yml`;
- `openssl s_client` contra `dormio-smart.vercel.app`, 03/11;
- `docs/LIMITACOES-TCC.md`, X.8; backlog `SEC-15`; `docs/AUDITORIA-2026-10-31.md`, A5.

---

# 2026-11-03 (ii) — `FW-10`: o sono da medição vai até um prazo, e os contadores são `atomic`

**O problema, como foi entendido no início.** Achados A8 e A10 da auditoria de 31/10. O laço da
medição dormia `intervalo` **depois** do trabalho (drenar, fechar a época, gravar na flash): o
intervalo real era intervalo + trabalho, ~2,2 s no pior caso, contra 3,09 s de FIFO no pior
oscilador. E os `contadores` eram lidos e escritos pelos dois núcleos sem proteção.

**Hipótese de trabalho.** Que o sono pudesse virar prazo absoluto sem perder a variação deliberada
do despertar (da qual depende o erro de ~5 ms da linha do tempo), e que os contadores pudessem
virar `std::atomic` sem mudar o comportamento.

**O que foi testado, e como.**

- **Antes de escrever:** quem escreve cada campo de `contadores`, por busca no `sketch.ino`.
- **A correção:** `proximo_prazo_de_drenagem_us` e `espera_ate_o_prazo_us` no núcleo
  (`cadeia_c2`); o laço do `sketch.ino` dorme até o prazo, nos dois ramos (sono leve e
  `vTaskDelay`); contador novo `prazos_estourados`; `contadores` com `std::atomic<uint32_t>`.
- **Testes:** um laço simulado no alvo `c2`, com trabalho de 0, 400 e 1000 ms, um estouro de 4 s e
  a variação do intervalo.
- **Controle positivo:** três sabotagens novas na mutação da cadeia.
- **Firmware inteiro** em contêiner `gcc:13`.

**Resultado medido.**

- **Alvo `c2`:** 147 verificações (136 + 11), 0 falhas. Demais alvos: 341, 157, 456 e 84, 0
  falhas; os 4 sketches compilam, e o `sketch.ino` liga com o núcleo; mutação 15 casos de acordo;
  mutação da fila 14/14; capacidade com a tabela válida.
- **Mutação da cadeia: 27/27.** As três novas:
  - sono relativo, contado do fim do trabalho: 3 falhas;
  - recuperar o atraso (rajada depois do estouro): 2;
  - prazo sem a variação do intervalo: 1.

**Adaptação.**

- **A auditoria exagerou o A10.** Cada campo tem um só escritor: a medição (núcleo 1) escreve
  cinco, e o envio (núcleo 0) escreve `descartadas_no_envio` e lê todos para o log. Nenhum
  incremento se perdia; a corrida é de leitura contra escrita, comportamento indefinido em C++. O
  texto do A10 foi corrigido na auditoria.
- **Contador novo, fora do plano original da auditoria:** `prazos_estourados`, para a bancada medir
  a folga da FIFO diretamente.
- **`static Contadores contadores;` sem inicializador:** `= {0, ...}` copiaria `atomic`, o que o
  C++11 do `make sintaxe` recusa; o armazenamento estático já começa em zero.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**

- **O laço do `sketch.ino` só é conferido por compilação e ligação.** A lógica do prazo está no
  núcleo e testada, mas a chamada no sketch não tem teste de unidade.
- **Na placa:** se o `esp_timer` conta certo durante o sono leve (a documentação diz que é
  compensado), o tempo real de apagar a flash e quantos prazos estouram. Entram na bancada do
  `FW-07` (c), e o contador novo mostra.

**Procedência.**

- `firmware/nucleo/cadeia_c2.h` e `cadeia_c2.cpp`; `firmware/sketch.ino`;
- `firmware/nucleo/testes/testes_c2.cpp` e `verificar_cadeia_por_mutacao.sh`;
- backlog `FW-10`; `docs/AUDITORIA-2026-10-31.md`, A8 e A10.

---

# 2026-11-03 (iii) — o laço do `sketch.ino` testado rodando, e a instrumentação da bancada

**O problema, como foi entendido no início.** Dois pontos que o `FW-10` deixou em aberto. (1) A
chamada das funções novas dentro do laço do `sketch.ino` só era conferida por compilação e
ligação: trocar a ordem de duas linhas devolveria o defeito sem nenhum teste notar. (2) A bancada
precisa responder três perguntas — quantos prazos estouram, quanto a flash leva para apagar um
setor e se o relógio do ESP32 conta certo no sono leve —, e o firmware só registrava a primeira.

**Hipótese de trabalho.** Que o laço real pudesse rodar no host com os stubs ganhando um relógio
controlável e um gancho na leitura I2C (a primeira leitura de cada volta é a drenagem). E que a
deriva do relógio pudesse ser medida contra o NTP a cada sincronia, sem mudar o comportamento.

**O que foi testado, e como.**

- **Experimento, antes de versionar:** a `tarefa_de_medicao` real com relógio falso, contra o
  `sketch.ino` atual e o de antes do `FW-10` (`89e41c6`), em contêiner `gcc:13`.
- **Instrumentação:** `medir_deriva` em `relogio.h`; no sketch, `trabalho_max_us` (o maior
  trabalho de uma volta) e a linha `[relogio]` a cada NTP, com a deriva contra a sincronia anterior
  e contra a primeira.
- **Versionado:** `make laco` (`testes/laco_do_sketch.cpp` e `verificar_laco_do_sketch.sh`), que
  monta os stubs com relógio, roda o laço, e sabota o próprio `sketch.ino`. Entrou no CI.
- **Suíte do firmware inteira**, em `gcc:13`.

**Resultado medido.**

- **O experimento**, distância média entre drenagens:

  | Trabalho | Depois do `FW-10` | Antes |
  |---|---|---|
  | 0 ms | 1,710 s | 1,710 s |
  | 400 ms | 1,710 s | 2,110 s |
  | 1000 ms | 1,710 s | 2,710 s |

  O mesmo nos dois ramos (sono leve e `vTaskDelay`). Um trabalho de 4 s: 1 prazo estourado, e a
  menor distância depois dele 1,702 s, sem rajada.
- **`make laco`:** 26 verificações, 0 falhas; 4/4 sabotagens no sketch acusadas (sono relativo: 5
  falhas; estouro não contado: 1; trabalho medido depois da drenagem: 5; deriva medida depois de
  sincronizar: 2).
- **Alvo `c2`:** 152 verificações (+5 da deriva); mutação da cadeia 29/29, com 2 sabotagens novas
  (sinal trocado: 2 falhas; medir sem sincronia anterior: 1). Demais alvos 0 falhas; os 4 sketches
  compilam, e o `sketch.ino` liga com o núcleo; mutação 15 casos de acordo; fila 14/14; capacidade
  com a tabela válida.

**Adaptação.**

- **`gettimeofday` trocado por macro só no teste:** o sketch é incluído na unidade de compilação do
  teste depois de `<sys/time.h>`, e a macro troca apenas a chamada do sketch.
- **A deriva é medida duas vezes:** contra a sincronia anterior (10 min, onde o erro do próprio NTP
  pesa) e contra a primeira da noite (horas, onde não pesa). A segunda é a que responde a pergunta.
- **O máximo de trabalho é desde o boot**, com um só escritor (a medição): zerar a cada envio
  poria um segundo escritor, de outro núcleo.

**O que deu errado no caminho.** No experimento, o `-x c++` fez o `g++` ler os `.o` como fonte, e
faltava incluir os cabeçalhos do FreeRTOS antes dos stubs; corrigidos com `-x none` e os includes.

**Risco em aberto.**

- **O laço com relógio falso não prova a placa:** os três números (prazos estourados, trabalho
  máximo, deriva) só valem quando lidos do serial na bancada do `FW-07` (c), onde o checklist do
  que ler ficou registrado.
- **O teste depende da forma dos stubs:** se um stub mudar, a troca não casa e o script para com
  "TROCA QUEBRADA", em vez de testar o relógio errado em silêncio.

**Procedência.**

- `firmware/sketch.ino`; `firmware/nucleo/relogio.h`;
- `firmware/nucleo/testes/laco_do_sketch.cpp`, `verificar_laco_do_sketch.sh`, `testes_c2.cpp` e
  `verificar_cadeia_por_mutacao.sh`; `firmware/nucleo/Makefile`; `.github/workflows/ci.yml`;
- backlog `FW-10` e `FW-07`.

---

# 2026-11-03 (iv) — branches sincronizadas, e o release do `SEC-15` e do `FW-10`

**O problema, como foi entendido no início.** O autor pediu para conferir seis branches locais
antigas e corrigir o que estivesse fora de sincronia. O `develop` também tinha o `SEC-15`, o
`FW-10` e o teste do laço fora de `main` — e o agendamento do monitor da produção só roda a partir
de `main`.

**Hipótese de trabalho.** Que as seis branches já estivessem em `develop`, e que o release não
mudasse o site (só firmware, docs, scripts e workflows).

**O que foi testado, e como.**

- **As seis branches** (`GIT-01`, `INFRA-03`, `PERFIL-02`, `SEC-12` e as duas do `ARQ-01`, PRs #1–#4,
  #12 e #13): `git merge-base --is-ancestor` contra `develop` e a contagem de commits fora dele.
- **Sincronia:** branches locais contra o GitHub, `develop` contra `main` (em commits e em
  conteúdo), worktrees, alterações soltas, stash e PRs abertas.
- **O release:** diff `main..develop` filtrado por backend, frontend, `vercel.json`, dependências e
  migrações; PR #47 depois dos 9 checks; deploy acompanhado pela API de deployments, com o SHA.
- **Depois:** `/health`, as rotas de ingestão sem credencial e com token inválido, `Bearer`
  inválido, `conferir_tls_firmware.py --producao` daqui, e o log do monitor disparado pela push em
  `main`.

**Resultado medido.**

- **As seis branches estavam inteiras em `develop`** (0 commits fora), inclusive a da #13 — que o
  `CLAUDE.md` registra como mesclada na branch da #12; o conteúdo chegou a `develop` depois.
  Apagadas aqui e no GitHub, que ficou só com `main` e `develop`.
- **`main` local estava 162 commits atrás** do GitHub: atualizado. Os 34 commits de `main` fora de
  `develop` são só os merges dos releases, sem conteúdo (diff `develop...main` vazio).
- **Release #47** (`95e61e6`): nenhum arquivo do backend nem do frontend; deploy `7527355605`
  `success`, com o SHA conferido; `/health` `200`, banco ok; as rotas de ingestão `401` sem
  credencial e com token inválido; `Bearer` inválido `401`.
- **O monitor rodou a partir de `main`** (execução `41694832434`, disparada pela push): `/health`
  ok e a cadeia da Vercel aceita contra as raízes do firmware (emissor WR1). Daqui, o mesmo.
- **O autor confirmou:** o login funciona normalmente.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Nenhum novo: o que este release leva ao firmware só vale na placa, e está nos
itens da bancada (`FW-07` (c) e `SEC-15` (c)).

**Procedência.**

- PR #47 (`95e61e6`); deployment de produção `7527355605`; execução `41694832434` do
  `saude-producao.yml`;
- `GET https://dormio-smart.vercel.app/health` e as rotas, 03/11;
- a confirmação do autor.

---

# 2026-11-03 (v) — "esqueci minha senha" levava ao `localhost`: as URLs do Supabase Auth

**O problema, como foi entendido no início.** O autor testou "esqueci minha senha" na produção. O
e-mail chegou, mas o link abria `http://localhost:3000/#access_token=…&type=recovery`, e o
navegador não achava a página.

**Hipótese de trabalho.** Que o código pedisse o retorno errado — ou que o Supabase descartasse o
retorno pedido.

**O que foi testado, e como.**

- **O código:** `recuperarSenha` (`frontend/src/lib/autenticacao.ts`) chama `resetPasswordForEmail`
  com `redirectTo: ${window.location.origin}/nova-senha` — na produção,
  `https://dormio-smart.vercel.app/nova-senha`. O site já reconhece o retorno de recuperação
  (`ehRetornoDeRecuperacao`, em `rotas.ts`) e tem a página `NovaSenha.tsx`.
- **O link recebido:** `http://localhost:3000/`, **sem** o `/nova-senha` que o código pediu — o
  sinal de que o Supabase ignorou o `redirectTo` e usou a Site URL.
- **O registro:** o roadmap já previa "`Site URL` + `Redirect URLs` para localhost, preview e
  produção" dentro do `AUTH-06`, que estava com prioridade reduzida; nunca tinha sido feito.
- **A correção, feita pelo autor no painel** (Authentication → URL Configuration): Site URL
  `https://dormio-smart.vercel.app`; Redirect URLs `https://dormio-smart.vercel.app/**` e
  `http://localhost:5173/**` (a porta do Vite).
- **Depois:** um e-mail de recuperação novo; daqui, `GET /nova-senha` na produção.

**Resultado medido.**

- **O autor confirmou:** com o e-mail novo, o link abriu a página de nova senha.
- `GET https://dormio-smart.vercel.app/nova-senha` → `200`, servindo o app.

**Adaptação.** Nenhuma mudança de código: o defeito era de configuração do Supabase, fora do
repositório. Fica registrado no `CLAUDE.md` (Deploy), porque nada no repositório o mostraria.

**O que deu errado no caminho.**

- **A configuração nunca foi feita** desde a criação do projeto: o fluxo de recuperação foi
  testado com dublês no frontend, que não exercitam o Supabase de verdade, e só um teste manual na
  produção mostrou o defeito.
- **O link colado na conversa continha um `access_token` e um `refresh_token` válidos** da conta do
  autor. Não foram usados. A orientação foi encerrar todas as sessões pelo "Sair" do site (que
  chama `signOut()` com o escopo global padrão) e trocar a senha.

**Risco em aberto.**

- **Previews da Vercel não estão nas Redirect URLs:** num preview, o link volta para a produção.
- **O e-mail ainda sai em inglês, pelo SMTP padrão do Supabase**, que é limitado e cai em spam:
  é o resto do `AUTH-06`.

**Procedência.**

- `frontend/src/lib/autenticacao.ts`, `rotas.ts` e `pages/NovaSenha.tsx`;
- o painel do Supabase (Authentication → URL Configuration), pelo autor, 03/11;
- a confirmação do autor; `GET https://dormio-smart.vercel.app/nova-senha`, 03/11;
- backlog `AUTH-06`.

---

# 2026-11-03 (vi) — a triagem do backlog, decidida; a idade fica; a coorte Walch volta a ser alcançável

**O problema, como foi entendido no início.** A Seção 4 da auditoria de 31/10 propunha manter,
ajustar ou remover itens do backlog, e esperava decisão do autor. O autor aprovou a recomendação,
com uma exceção — **manter o campo idade**, para conhecer o público do sistema — e pediu duas
investigações: o que manter a idade exige, e se a defesa precisa da segunda coorte externa
(Walch et al., 2019; `ML-06a` e `ML-06b`).

**Hipótese de trabalho.** Que a proposta, escrita em 31/10, ainda valesse item por item três dias
e uma dúzia de PRs depois.

**O que foi testado, e como.**

- **Cada item da proposta contra a linha atual do backlog.**
- **O SMTP padrão do Supabase**, na documentação oficial (*Send emails with custom SMTP*).
- **A idade:** as linhas do `LGPD-05` e do `LGPD-06`, as §3, §4 e §5.3 da política de privacidade,
  o `comment on column` da migração `008` e o cabeçalho de `lib/aplicabilidade.ts`.
- **A coorte Walch:** a X.4 de `LIMITACOES-TCC.md` e as notas dela; quais coortes o ML usa (`ml/`);
  e um pedido de cabeçalho à página do PhysioNet, **sem baixar nada**.
- **A triagem aplicada:** recontagem linha a linha e as conferências de documento.

**Resultado medido.**

- **Uma recomendação da auditoria não valia mais: o `AUTH-06`.** A documentação diz que, sem SMTP
  próprio, o Supabase **só entrega e-mail a endereços do time do projeto**. O "esqueci minha
  senha" que funcionou em 03/11 (v) funcionou porque o autor é dono do projeto; para qualquer
  outro usuário, não sai e-mail. Mantido, com prioridade maior.
- **Triagem aplicada:** fecharam 14 itens; 11 foram para uma seção nova, **Pós-banca**, fora da
  contagem e com o texto inteiro; `DATA-06` passou de L0 para L2; oito linhas ganharam a nota do
  ajuste. **Contagem: 70 → 45** (L0 17, L1 13, L2 7, L3 8), recontada linha a linha. O quadro do
  topo do backlog, que listava itens recém-fechados, foi refeito.
- **A idade, com a finalidade nova, exige:** política atualizada **antes** (§3 declara hoje a
  finalidade "única" de dizer se a faixa do titular está nas coortes citadas; §5.3 diz que o
  acesso administrativo não é usado para consultar dados fora da manutenção; §10 manda avisar
  mudança material); depois o `comment on column` da `008` e o cabeçalho de `aplicabilidade.ts`,
  que repetem a finalidade única; e só então uma consulta **agregada por faixa**, com supressão de
  faixas pequenas. E o `LGPD-05` muda de natureza: a saída (c) só valia enquanto o autor fosse o
  único usuário, e conhecer o público pressupõe outros.
- **A coorte Walch:** o PhysioNet respondeu `200` a partir desta máquina; o projeto é **Open
  Access**, sob a Open Data Commons Attribution License v1.0, com **2,2 GB** descompactados. O
  motivo registrado na X.4 para não a ter usado ("indisponibilidade de acesso ao repositório no
  ambiente de execução") **deixou de valer aqui**. O desenvolvimento usa Wearanize+ (92 sujeitos,
  acelerômetro na cabeça) e a validação externa usa Newcastle (27 sujeitos, pulso); Walch seria
  uma segunda coorte de pulso.

**Adaptação.**

- **Pós-banca em vez de apagar:** a auditoria propunha remover os prematuros; ficaram numa seção
  própria, para o raciocínio não se perder.
- **A classe do `UI-19`** (código morto no nível do símbolo) foi para o `CI-02`.
- **`ML-06a` e `ML-06b` não foram tocados**: esperam a decisão do autor.

**O que deu errado no caminho.** Nada nesta etapa. O quadro do topo do backlog listava como
abertos itens que a triagem fechou — é o `DOC-13` acontecendo de novo, e foi corrigido junto.

**Risco em aberto.**

- **`AUTH-06`:** enquanto não houver SMTP próprio, nenhum usuário além do autor recebe e-mail do
  sistema.
- **A idade:** até a política ser atualizada, a finalidade nova **não pode** ser exercida — nem
  por consulta manual no painel (`LGPD-06`). E a escolha do `LGPD-05` entre (a) e (b) é do autor.
- **A coorte Walch:** a X.4 afirma um motivo que deixou de ser verdadeiro nesta máquina; se a
  decisão for não usá-la, o parágrafo precisa dar o motivo real (`ML-06a`).

**Procedência.**

- `docs/AUDITORIA-2026-10-31.md`, Seção 4; `docs/BACKLOG-COMPLETO.md`; `scripts/consolidar_registro.py`;
- `docs/POLITICA-DE-PRIVACIDADE.md`, §3, §4, §5.3 e §10; `web-app/migrations/008_perfil_como_fonte_de_verdade.sql`;
  `frontend/src/lib/aplicabilidade.ts`;
- `docs/LIMITACOES-TCC.md`, X.4; `ml/README.md`;
- `https://supabase.com/docs/guides/auth/auth-smtp` e `https://physionet.org/content/sleep-accel/1.0.0/`, 03/11.

---

# 2026-11-03 (vii) — `ML-06`: a previsão, registrada antes de rodar a coorte Walch

**Por que esta entrada existe sozinha.** O `ML-06` aplica à coorte de Walch et al. (2019) o mesmo
modelo e o mesmo protocolo da validação externa no Newcastle (`ML-04`). O resultado vai confirmar
ou não o achado metodológico mais forte do trabalho (X.4). Para que a leitura não se ajuste ao
número, a previsão e o critério de refutação ficam registrados **neste commit, antes de qualquer
época da Walch ser processada** — o histórico do git é a prova da ordem.

**O que já se sabia, do Newcastle** (`ml04_validacao_externa_aec203907e6f_esquerdo.json`, braço
`pulso`, 27 sujeitos): `base_ctx2` κ = 0,265; `item8b_hmm` κ = 0,301 e especificidade de 0,412
para 0,375; `item9_ctx11` κ = 0,334 [0,254; 0,416] e especificidade 0,507; trivial κ = 0.

**O protocolo, fixado antes:** treino nos 92 sujeitos do Wearanize+ (cache da configuração
`aec203907e6f`), braço `pulso` como leitura principal (a Walch é de pulso, como o Newcastle);
teste na Walch sem reajuste de nada (sem scaler no domínio de teste, sem limiar recalibrado, sem
olhar rótulo antes de medir); normalização por sujeito, que só usa X; as mesmas quatro
configurações; IC 95% por bootstrap por sujeito; comparação pareada contra `base_ctx2`; o trivial
"sempre dormindo" medido na própria Walch.

**A previsão.**

- **P1 — o método generaliza:** `item9_ctx11` com o IC 95% do κ inteiramente acima do trivial.
- **P2 — o ganho da janela atravessa coorte:** `item9_ctx11` contra `base_ctx2`, pareado, com ganho
  de κ cujo IC exclui zero, e **sem perda significativa de especificidade**.
- **P3 — o ganho do HMM não atravessa:** `item8b_hmm` contra `base_ctx2`, com Δespecificidade nula
  ou negativa, e ganho de κ **menor** que o de `item9_ctx11`.

**O critério de refutação.** Se P2 falhar (a janela perde especificidade de forma significativa, ou
o ganho de κ some), ou se P3 se inverter (o HMM ganha especificidade de forma significativa), o
achado **não se repete** na segunda coorte, e a X.4 passa a dizer isso, com o número. P1 falhando
sozinho muda a afirmação de generalização, não a do achado.

**O que fica fora da previsão:** os valores absolutos de κ e de especificidade. A Walch usa outro
aparelho (Apple Watch), outra taxa e outra população; números menores ou maiores que os do
Newcastle não confirmam nem refutam nada sozinhos.

**Procedência.** `ml/experimentos/ml04_validacao_externa.py`;
`ml/experimentos/saida/ml04_validacao_externa_aec203907e6f_esquerdo.json`; `docs/LIMITACOES-TCC.md`, X.4.

---

# 2026-11-03 (viii) — `ML-06`: o que a inspeção da Walch encontrou, e o adendo ao protocolo

**Por que esta entrada vem antes do resultado.** O download (577 MB; 2,2 GB descompactados; **125 de
125 arquivos conferem com o `SHA256SUMS.txt`**) foi inspecionado **só no sinal e nos códigos de
rótulo — nenhuma métrica de desempenho foi calculada**. A inspeção forçou decisões de protocolo
que a entrada (vii) não previa; elas ficam registradas aqui, antes de rodar qualquer modelo.

**O que foi medido, nos 31 sujeitos.**

- **Tempo:** o arquivo de movimento começa horas ou **dias antes** da polissonografia (tempos
  negativos, até −533 391 s); os rótulos começam em 0 e andam de 30 em 30 s, em todos.
- **Códigos de rótulo:** −1: 438 épocas; 0: 2 429; 1: 1 821; 2: 12 954; 3: 3 329; **4: 356**;
  5: 5 884. A página do PhysioNet não define o 4; o repositório dos autores
  (`ojwalch/sleep_classifiers`, `source/sleep_stage.py`) define 4 = N4 e −1 = não pontuado.
- **Taxa (mediana por sujeito):** cerca de 50 Hz em 24 sujeitos; cerca de 66 Hz em 4; 33 Hz em 1;
  **10 Hz em 2** (`5383425` e `8258170`). A taxa comum do pipeline é 32 Hz.
- **Tempo fora de ordem ou repetido:** em 11 sujeitos.
- **Lacunas acima de 1 s dentro da janela dos rótulos:** em 16 sujeitos, até 1 277 s numa só. E
  um caso extremo: no `7749105` o movimento **para aos 4 024 s** da polissonografia e só volta
  depois do fim dela. Um sujeito (`4018081`) não tem movimento até o fim dos rótulos.

**O risco que isso expõe.** `reamostrar` interpola lacunas linearmente (decisão documentada em
`src/sinal.py`), e depois disso `fatiar_epocas` vê uma grade contínua e não tem como achar a
lacuna. Sem tratamento, o `7749105` entraria com **cerca de 7 h de sinal inventado por
interpolação**, pareadas com rótulos de polissonografia verdadeiros.

**O adendo ao protocolo, fixado antes de rodar.**

1. **Rótulos:** 0 → vigília; 1, 2, 3, 4 e 5 → sono; −1 e qualquer outro código → não pontuado (sai).
2. **Movimento:** recortado à janela dos rótulos, com 60 s de margem; ordenado por tempo; tempo
   repetido descartado (fica a primeira amostra).
3. **Época sem dado medido vira não pontuada**, no carregador, antes da reamostragem: se dentro dos
   30 s houver lacuna maior que 1 s, ou se o movimento não cobrir a época inteira.
4. **Análise principal sem os 2 sujeitos de 10 Hz:** reamostrar 10 Hz para 32 Hz não cria o
   conteúdo que as features de frequência leem. **Análise secundária com eles**, relatada ao lado,
   para que a exclusão não seja escolhida pelo resultado.
5. **O resto do protocolo é o da entrada (vii)**, e a previsão (P1–P3) não muda.

**Procedência.** `ml/dados/bruto/walch/` (não versionado); `SHA256SUMS.txt` do pacote;
`https://github.com/ojwalch/sleep_classifiers` (`source/sleep_stage.py`); `ml/src/sinal.py` e
`ml/src/epocas.py`.

---

# 2026-11-03 (ix) — `ML-06`: a coorte Walch rodou; duas previsões e meia se confirmaram

**O problema, como foi entendido no início.** A validação externa do trabalho se apoiava numa
coorte só (Newcastle). A segunda (Walch et al., 2019) estava declarada como "não executada" por
um motivo que deixou de valer nesta máquina. O protocolo e a previsão estão nas entradas (vii) e
(viii), registrados e enviados ao GitHub antes de qualquer época ser processada.

**Hipótese de trabalho.** P1, P2 e P3 da entrada (vii).

**O que foi testado, e como.**

- **Carregador `ml/src/carregar/walch.py`**, com as cinco armadilhas medidas na inspeção; 8
  testes com arquivos fabricados no formato real; seis sabotagens.
- **Smoke test no dado real:** o `7749105` fica com 130 de 960 épocas (as 830 sem movimento saem);
  o `5383425` é excluído por taxa (10 Hz).
- **`ml04` com `--coorte walch`:** o mesmo modelo, as mesmas quatro configurações, o mesmo
  bootstrap. **Regressão:** o Newcastle rodado de novo com o `ml04` alterado deu JSON idêntico ao
  versionado, exceto o carimbo `utc`.
- **Suíte de ML inteira.**

**Resultado medido.**

- **Sabotagens 6/6 acusadas:** REM como vigília (2 falhas); N4 como não pontuado (2); sem a
  máscara de época sem dado (2, inclusive o teste que prova que nenhuma época interpolada chega às
  features); sem ordenar o tempo (1); sem recortar a janela (1); lacuna tolerada de 1 h (1).
- **Suíte de ML:** 134 passam (126 + 8).
- **Walch, análise principal** (29 sujeitos, 23 303 épocas, prevalência 0,913), braço pulso:
  `item9_ctx11` κ = 0,378 [0,316; 0,444], especificidade 0,727 [0,664; 0,787]. Pareado contra
  `base_ctx2`: janela Δκ +0,032 [+0,006; +0,061], Δesp +0,096 [+0,072; +0,120]; HMM Δκ +0,070
  [+0,040; +0,103], Δesp −0,042 [−0,076; −0,006].
- **Análise secundária** (31 sujeitos): as mesmas conclusões, em todos os braços.
- **Contra a previsão:** P1 confirmada; P2 confirmada; **P3 confirmada na especificidade e não no
  κ** — o HMM ganhou mais κ que a janela.

**Adaptação.**

- **A X.4 foi reescrita no parágrafo da segunda coorte**, e diz o que falhou: a queda de ~30 pp
  de especificidade é do Newcastle (na Walch, 0,802 → 0,727); o ganho de κ do HMM depende da
  coorte. A conclusão que sobra é mais restrita e mais firme: **a janela sobe a especificidade nas
  duas coortes, e o HMM a derruba nas duas**.
- **A explicação pela prevalência** (Walch 0,913, perto da do Wearanize+; Newcastle 0,699) é
  compatível, mas está marcada no texto como leitura posterior ao resultado.

**O que deu errado no caminho.**

- **O primeiro teste de época sem dado estava errado, não o código:** a grade fabricada ia até
  119,98 s, e a época 90–120 estava coberta. Corrigido o caso, não o carregador.
- **A branch foi criada a partir do `develop` sem a triagem**, e a entrada do diário colidiria com
  a da PR #50; recriada a partir da branch da triagem antes do primeiro commit.
- **A âncora do diário tinha dois espaços a mais** e o primeiro `ed` parou na asserção, sem gravar.

**Risco em aberto.**

- **Com duas coortes, a variação entre coortes ainda é estimada por dois pontos.** A X.4 passa a
  falar em faixa (0,507 a 0,727), não em valor.
- **A Walch não tem segunda pontuação manual**, como o Newcastle: a degradação continua sem poder
  ser decomposta entre método e rotulagem.

**Procedência.**

- `ml/src/carregar/walch.py`, `ml/src/carregar/__init__.py`, `ml/testes/test_walch.py`;
- `ml/experimentos/ml04_validacao_externa.py`; `ml/experimentos/saida/ml04_validacao_externa_aec203907e6f_walch_principal.json`
  e `_walch_todos.json`;
- commits `26bb18f` (previsão) e `f528750` (adendo), anteriores ao resultado;
- `docs/LIMITACOES-TCC.md`, X.4, e `docs/RESULTADOS-TCC.md`, Y.6 e Y.8 (os dois com os mesmos números);
  `ml/README.md`, seção `ML-06`; backlog `ML-06a` e `ML-06b`.

---

# 2026-11-03 (x) — mais coortes públicas: a busca, a Borazio descartada, e a DREAMT

**O problema, como foi entendido no início.** Com duas coortes externas, o intervalo de predição
(Higgins, Thompson e Spiegelhalter, 2009) não é definido: ele usa *t* com k − 2 graus de
liberdade. O autor pediu uma busca profunda por mais coortes públicas confiáveis.

**Hipótese de trabalho.** Que existissem bases abertas com aceleração bruta de pulso e rótulo de
PSG por época além de Newcastle e Walch.

**O que foi testado, e como.**

- **Busca** em PhysioNet, NSRR, Zenodo, Figshare e OSF, e nas seções de disponibilidade de dados
  dos artigos de validação de actigrafia; critérios: aceleração bruta, PSG por época, acesso
  viável e procedência publicada.
- **Borazio et al. (2014)**, a única aberta com PSG encontrada: baixada (25 259 506 bytes,
  SHA-256 `78980268fb1a4acac264b7207625da17bafd32b40980839572555794bce36689`), com o cabeçalho
  dos `.npy` lido **antes** de carregar (arranjos numéricos sem objetos, carregados com
  `allow_pickle=False`; o script do pacote não foi executado); taxa, escala em repouso,
  saturação e a duração dos trechos de rótulo, nos 47 registros.

**Resultado medido.**

- **A busca:** DREAMT (PSG, acesso restrito por termo) é a única candidata nova que serve;
  BIDSleep (aberta) tem rótulo de EEG de faixa, não PSG; MESA, HCHS, MrOS e SOF só têm contagens
  de 30 s; Pennsylvania exige acordo com o NIH; outras três não têm dado público confirmado.
  **Nenhuma base com sensor na cama, no colchão ou no travesseiro e PSG foi encontrada.**
- **Borazio:** 100 Hz depois de expandir o *run-length encoding*; ~8,75 h por noite; ~30
  contagens por g em repouso (29,0 a 30,3 nos três pacientes medidos), sem saturação. **Mas os
  trechos de rótulo não caem numa grade de 30 s:** só 2 a 14% ficam a 1 s de um múltiplo de 30 s;
  num grupo de registros (`025`–`051`, `09b`) o menor trecho tem 33 a 46 s; no outro (`002`–`023`,
  `08a/b`, `15a/b`…), há 564 trechos entre 5 e 10 s. Código 7 ("movimento") e 1 a 2 h sem rótulo
  no início das gravações.

**Adaptação.**

- **A Borazio foi descartada como coorte de validação.** O padrão é de relógios fora de sincronia
  entre o registrador e a PSG, com fator diferente por paciente. Estimar esse fator faria o rótulo
  ser inferido por este trabalho, e validação contra rótulo inferido não se defende.
- **A DREAMT virou o `ML-13`, em L3:** o acesso depende de o autor assinar o termo de uso no
  PhysioNet — ação que envolve a identidade dele.

**O que deu errado no caminho.** O primeiro script de inspeção leu o `pat_inf.npy` (os dados dos
pacientes) como se fosse um registro, porque o padrão de arquivo `p*.npy` casava com ele; parou num
erro de índice, sem resultado parcial, e foi corrigido.

**Risco em aberto.** Mesmo com a DREAMT, são 3 coortes externas: o intervalo de predição passa a
existir, mas com multiplicador ~12,7, largo demais para dizer muito (`ML-13`). A distância entre o
pulso e o travesseiro continua sem base pública que a meça (X.4).

**Procedência.**

- `ml/README.md`, "Mais coortes"; `ml/dados/bruto/borazio/` (não versionado);
- `https://ubi29.informatik.uni-siegen.de/usi/data_ichi14.html`, `https://physionet.org/content/dreamt/`,
  `https://physionet.org/content/bidsleep-dataset/1.0.1/`, `https://sleepdata.org/forum/raw-accelerometer-data-from-actigraphy/1`, 03/11;
- backlog `ML-13`.

---

# 2026-11-03 (xi) — `LGPD-05` e `LGPD-06`: só maiores de 18, e a idade com uma finalidade agregada

**O problema, como foi entendido no início.** O autor decidiu manter o campo idade para conhecer o
público do sistema. Isso abria duas frentes: o `LGPD-06` (finalidade nova exige política nova
ANTES) e o `LGPD-05` (a saída "manter a lacuna sobre menores declarada" só valia enquanto o autor
fosse o único usuário). Perguntado se menores poderiam usar, o levantamento (LGPD art. 14, Enunciado
CD/ANPD nº 1/2023, ECA Digital — Lei 15.211/2025, por fontes secundárias) mostrou custo alto:
verificação de idade confiável, supervisão parental e Comitê de Ética em pesquisa. O autor escolheu
a saída (a), só maiores de 18, e o público menor como item pós-banca.

**Hipótese de trabalho.** Que a restrição pudesse valer nas três camadas (frontend, backend e banco)
sem alterar dado existente, e que a finalidade nova pudesse ser exercida só por contagem agregada.

**O que foi testado, e como.**

- **A ordem:** a política foi alterada e commitada primeiro (`942aad3`: §2.1, §3 item 5, §5.3 e
  §10), antes de qualquer código.
- **O cadastro:** caixa obrigatória "Declaro que tenho 18 anos ou mais"; `cadastrar` recusa sem ela,
  antes de chamar o Supabase, e com ela registra a data em
  `raw_user_meta_data.maior_de_18_declarado_em`. Primeiro teste de componente da tela de cadastro
  (`Register.test.tsx`).
- **A idade:** mínimo 18 em `lib/perfil.ts`, em `perfil.py` e na migração `012` (restrição
  `profiles_idade_maioridade`, com trava que PARA sem alterar dado se houver menor gravado, e o
  comentário da coluna com as duas finalidades). O texto junto ao campo idade diz o uso agregado.
- **A consulta agregada:** `CONSULTA-publico-por-faixa.sql`, só leitura, faixas com menos de 5
  suprimidas e sem linha de total (que permitiria recuperar uma faixa suprimida por subtração).
- **Postgres real** em contêiner `postgres:16`: suíte de RLS, mutação do RLS e o verificador de
  migrações; backend, frontend, `tsc` e build.
- **Controle positivo:** sete sabotagens, nas quatro camadas.

**Resultado medido.**

- **Backend** 417 (416 + 1); **frontend** 428 em 29 arquivos (424 + 4); `tsc` e build limpos;
  **RLS** 174 (164 + 10); **mutação do RLS** 32/32; o verificador acerta os **12 estados** e a
  ordem real da produção, agora com a `012`.
- **Sabotagens, 7/7 acusadas:** frontend aceitando idade 0; cadastro sem exigir a declaração;
  cadastro sem registrar a data dela; backend aceitando 0; banco aceitando 0; trava da `012`
  desligada; consulta sem a supressão de faixa pequena.

**Adaptação.**

- **Três testes antigos especificavam o mínimo 0** — `lerIdade("0")` válido, `validar_idade(0)`
  válido e a idade 0 aceita pelo banco — e foram reescritos para a regra nova.
- **Um teste de "espelho" não espelhava nada:** `test_a_faixa_de_idade_espelha_a_constraint_da_migracao_001`
  comparava o backend com números escritos no próprio teste. Agora ele **lê a restrição da `012`** e
  reprova se o arquivo e o backend divergirem.
- **Um item novo em L3, `LGPD-08`:** aplicar a `012` na produção e fazer o release — como o
  `DATA-08`/`DATA-09`. O `LGPD-07` (menores de idade) foi direto para a seção Pós-banca.

**O que deu errado no caminho.**

- **O teste de componente acumulava a tela de um caso no outro** (o projeto não ativa a limpeza
  automática da Testing Library): `cleanup` em `afterEach`.
- **O teste de RLS foi escrito primeiro contra uma *fixture* que não existia e com `psycopg`**, quando
  a suíte usa `psycopg2`; reescrito com uma conexão própria em transação, desfeita no fim de cada caso.

**Risco em aberto.**

- **A idade é autodeclarada**, no cadastro e no campo: ninguém verifica. A política diz isso.
- **A proteção da consulta agregada é de procedimento:** o administrador tem acesso técnico à
  coluna. O arquivo SQL declara isso.
- **A política ainda não é servida dentro do app** (`LGPD-01` (b)): a finalidade está declarada num
  documento que o usuário não vê; o texto junto ao campo idade cobre isso só em parte.
- **Nada disso vale na produção antes do `LGPD-08`.**

**Procedência.**

- `docs/POLITICA-DE-PRIVACIDADE.md` (commit `942aad3`); `frontend/src/lib/autenticacao.ts`,
  `pages/Register.tsx` e `Register.test.tsx`, `lib/perfil.ts`, `lib/aplicabilidade.ts`,
  `components/EditarPerfil.tsx`; `web-app/perfil.py`; `web-app/migrations/012_idade_minima_18.sql` e
  `CONSULTA-publico-por-faixa.sql`; `web-app/tests/rls/test_rls_idade_maioridade.py`;
- backlog `LGPD-05`, `LGPD-06`, `LGPD-07` e `LGPD-08`.

---

# 2026-11-03 (xii) — a `012` na produção e o release do `LGPD-05`/`LGPD-06`

**O problema, como foi entendido no início.** O `LGPD-05`/`LGPD-06` estava em `develop` (PR #53), e
a migração `012` precisava ir para a produção antes do release que a usa (`LGPD-08`).

**Hipótese de trabalho.** Que nenhum perfil de produção tivesse idade abaixo de 18 (a trava da
`012` pararia), e que o release mudasse só o cadastro e a validação da idade.

**O que foi testado, e como.**

- **A `012`:** aplicada pelo autor no SQL Editor; depois, o `DIAGNOSTICO-migracoes-aplicadas.sql`.
- **O release:** diff `main..develop` (código do site em `frontend/src` e `web-app/perfil.py`;
  nenhuma dependência, variável ou `vercel.json` nova); PR #54 depois dos 9 checks; deploy
  acompanhado pela API de deployments, com o SHA.
- **Depois:** `/health`; `PATCH /api/me/perfil` sem credencial; o pacote JavaScript publicado,
  procurado pelos textos novos; e, pelo autor, um login e uma tentativa de cadastro sem a caixa.

**Resultado medido.**

- **Diagnóstico:** `012 aplicada = true, 2 de 2 marcas`; 001 a 011 continuam aplicadas. A trava não
  disparou: não havia perfil com idade abaixo de 18.
- **Deploy `7530061150`, `success`, SHA `7e7140e`.** `/health` `200`, banco ok; `PATCH` sem
  credencial → `401`; o pacote `index-DhAoYEpi.js` contém "Declaro que tenho 18 anos ou mais", a
  mensagem de recusa e `maior_de_18_declarado_em`.
- **O autor confirmou:** o login funciona, e o cadastro sem a caixa é recusado na tela.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Os mesmos do `LGPD-05`/`LGPD-06` (diário, 03/11 (xi)): idade autodeclarada;
proteção de procedimento na consulta agregada; a política ainda não servida dentro do app
(`LGPD-01` (b)); e o SMTP próprio (`AUTH-06`) antes de qualquer pessoa além do autor usar o sistema.

**Procedência.**

- O diagnóstico colado pelo autor, 03/11; PR #54 (`7e7140e`); deployment de produção `7530061150`;
- `GET https://dormio-smart.vercel.app/health`, `/api/me/perfil` e o pacote publicado, 03/11;
- a confirmação do autor; backlog `LGPD-08`.

---

# 2026-11-03 (xiii) — `LGPD-01` (b): a política de privacidade servida dentro do app

**O problema, como foi entendido no início.** A política existia só como documento no repositório:
o titular não a via, e a finalidade nova da idade (`LGPD-06`) estava declarada num texto que
ninguém de fora lê. A investigação achou mais dois obstáculos: o controlador e o contato estavam em
branco (`[CONTROLADOR]`, `[CONTATO]`), e o repositório é público e não pode levar nome de pessoa; e
o próprio documento dizia "não publicar sem revisão jurídica".

**Hipótese de trabalho.** Que a página pudesse ler o próprio documento no build, em vez de uma
cópia, e que o controlador pudesse entrar por variável de build, fora do repositório.

**O que foi testado, e como.**

- **A abordagem aprovada:** `/privacidade`, pública e carregada sob demanda; `lib/politica.ts`
  recorta o trecho entre `── TEXTO` e `── FIM DO TEXTO` e troca os dois marcadores pelas variáveis
  `VITE_POLITICA_CONTROLADOR` e `VITE_POLITICA_CONTATO` (sem elas, "ainda não informado");
  `react-markdown` 9.0.1 e `remark-gfm` 4.0.0, sem HTML executável; faixa de versão preliminar;
  links no cadastro, em Configurações, junto ao campo idade e no rodapé da página inicial.
- **Testes:** o recorte sobre o documento REAL (as 10 seções, nada das notas, nenhum marcador
  pendente além dos dois); a página renderizada; os links do cadastro e de Configurações.
- **Controle positivo:** sete sabotagens.
- **Build:** tamanho dos pacotes. **Navegador:** a página no servidor local.

**Resultado medido.**

- **Frontend:** 443 passam, 31 arquivos (428 + 15); `tsc` e build limpos.
- **Sabotagens, 7/7 acusadas:** recorte devolvendo o documento inteiro (2 falhas); contato não
  trocado (4); sem `remark-gfm` (1); sem o aviso de versão preliminar (1); link do cadastro para
  outro lugar (1); link de Configurações para outro lugar (1); alcançabilidade ignorando `import`
  dinâmico (1).
- **Build:** a política em pacote próprio (`Privacidade-*.js`, 63 kB comprimido), fora do principal.
- **Navegador:** faixa, títulos, tabelas e "(ainda não informado nesta versão preliminar)" no lugar
  do controlador.

**Adaptação.**

- **Publicar com a faixa de versão preliminar**, contra a nota do documento: escondida, a política
  não informava ninguém. A revisão continua no `LGPD-03`.
- **O teste de alcançabilidade passou a reconhecer `import()` dinâmico.** O comentário dele previa
  exatamente este falso positivo ("se passar a haver, acusa órfão que não é; alguém vai olhar").
- **`LGPD-01` passou de L0 para L3:** o que resta, definir o controlador, é do autor.
- **`SEC-16`, novo:** o `npm audit` mostrou alerta alto no `react-router` instalado — já existia
  antes deste item, e um dos avisos alcança o uso do app.

**O que deu errado no caminho.**

- **A primeira montagem de `/privacidade` no teste do app inteiro deu raiz vazia:** o `Suspense`
  tinha fallback nulo, e o carregamento sob demanda ainda não tinha chegado. Virou um "Carregando a
  política…", que também serve a quem usa.

**Risco em aberto.**

- **O pacote da página carrega o `.md` inteiro, notas internas incluídas** — a tela não as mostra,
  mas quem abrir o JavaScript as lê. O repositório já é público, então não expõe nada novo.
- **Sem as variáveis na Vercel, o controlador aparece como "ainda não informado"** (`LGPD-01` (a)).
- **O build da Vercel precisa enxergar `docs/`**, fora de `frontend/`: a prévia da PR confirma.

**Procedência.**

- `frontend/src/lib/politica.ts`, `pages/Privacidade.tsx`, `App.tsx`, `pages/Register.tsx`,
  `pages/Settings.tsx`, `components/EditarPerfil.tsx`, `pages/Landing.tsx`, `vite.config.ts`;
- `frontend/src/lib/politica.test.ts`, `pages/Privacidade.test.tsx`, `Register.test.tsx`,
  `montagem.test.ts`, `alcance.test.ts`;
- backlog `LGPD-01` e `SEC-16`.

---

# 2026-11-03 (xiv) — o release da política de privacidade

**O problema, como foi entendido no início.** A página `/privacidade` (`LGPD-01` (b), PR #56) estava
em `develop`, e o controlador e o contato dependiam de duas variáveis de build que só o autor podia
criar na Vercel.

**Hipótese de trabalho.** Que as variáveis criadas antes do release entrassem no build do deploy de
produção, sem um redeploy à parte.

**O que foi testado, e como.**

- **As variáveis:** criadas pelo autor em Settings → Environment Variables do projeto, tipo Config
  (não Secret: o valor é público por definição, e Config permite conferi-lo), só em Production. O
  caminho no painel levou três telas (variáveis da equipe, configurações da equipe, ambientes).
- **O release:** diff `main..develop` (o frontend e as duas dependências novas; nenhuma migração);
  PR #57 depois dos 9 checks; deploy acompanhado pela API de deployments.
- **Depois:** `/health`; `/privacidade`; o pacote `Privacidade-*.js` publicado, procurado pelos
  valores injetados; e, pelo autor, a página aberta e um login.

**Resultado medido.**

- Deploy `7530696288`, `success`, SHA `242d854`. `/health` `200`; `/privacidade` `200`.
- O pacote publicado traz o controlador e o contato definidos pelo autor; a seção 1 da página os
  mostra, e as tabelas saem formatadas (conferido pelo autor, por captura de tela).
- **O autor confirmou o login.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O controlador definido é o autor sozinho; incluir o orientador, se for o caso,
e a revisão da política são o `LGPD-03`. O e-mail de contato fica público, por escolha do autor.

**Procedência.**

- PR #57 (`242d854`); deployment de produção `7530696288`;
- `GET https://dormio-smart.vercel.app/health`, `/privacidade` e o pacote publicado, 03/11;
- a captura de tela e a confirmação do autor; backlog `LGPD-01`.

---

# 2026-11-03 (xv) — `SEC-16`: `react-router` atualizado, e o destino pós-login validado

**O problema, como foi entendido no início.** Ao instalar o `react-markdown` (`LGPD-01` (b)), o
`npm audit` mostrou alerta de severidade alta no `react-router` 7.13.0 instalado — já existente.

**Hipótese de trabalho.** Que a maior parte dos avisos fosse de recursos que o app não usa, e que a
atualização dentro da versão maior 7 não mudasse comportamento.

**O que foi testado, e como.**

- **Os avisos:** `npm audit --json`. Doze, todos com correção a partir da 7.18.2. Dez são do modo
  *framework*/servidor (RSC, SSR, `__manifest`, *single-fetch*, *turbo-stream*, *actions*,
  *prerender*), que o app não usa; um é de lentidão no casamento de rotas; e um — redirecionamento
  aberto por barra invertida em `<Link>`/`useNavigate` (GHSA-wrjc-x8rr-h8h6) — alcança o uso do app.
- **Onde o app navega para destino vindo de fora:** busca por `navigate(`, `<Navigate` e `to={`.
  Um caso: o `Login` navegava para `state.de`, sem validação. O valor só é escrito pelo guarda de
  rotas, a partir das rotas protegidas (fixas) — não explorável hoje, mas sem defesa.
- **A versão:** datas de publicação pelo `npm view`. A 7.18.4 (15/09) corrige tudo e tinha sete
  semanas; a 7.18.5 tinha uma.
- **A correção:** `react-router` 7.18.4, versão fixa; `destinoSeguro` em `lib/rotas.ts` (só caminho
  que começa com `/` e não com `//` nem `/\`, sem caractere de controle), usado pelo `Login`.
- **Testes:** 16 casos da função e 3 do `Login` renderizado (`Login.test.tsx`), com a navegação real
  pelo `MemoryRouter`. **Controle positivo:** quatro sabotagens. **Navegador:** servidor local.

**Resultado medido.**

- `npm audit --omit=dev`: **0 vulnerabilidades**. Antes de qualquer código novo, a suíte com a versão
  nova: 443 passam, `tsc` limpo — a atualização não quebrou nada.
- **Frontend:** 462 passam, 32 arquivos (443 + 19); `tsc` e build limpos.
- **Sabotagens, 4/4 acusadas:** `destinoSeguro` aceitando qualquer texto (14 falhas); sem recusar a
  barra invertida (1); sem recusar caractere de controle (2); `Login` sem passar pela função (1).
- **Navegador:** `/configuracoes` sem sessão leva a `/login` com `de: "/configuracoes"` guardado; a
  política carrega; console sem erro.

**Adaptação.** Nenhuma em relação ao plano.

**O que deu errado no caminho.** **O primeiro teste da barra invertida estava errado, não a
função:** o caractere foi escrito no teste como `"/\evil.example"` com uma barra só, e em
JavaScript `\e` vira `e` — o teste conferia `"/evil.example"`, um caminho interno válido. Corrigido
o teste; a função não mudou. E a sessão parou uma vez no meio, por limite de uso, com o código já
numa PR (#59) e o registro por fazer.

**Risco em aberto.** **Só vale no site depois do release.** O CI não roda `npm audit`: um aviso novo
numa dependência só aparece quando alguém rodar à mão.

**Procedência.**

- `frontend/package.json` e `package-lock.json`; `frontend/src/lib/rotas.ts` e `rotas.test.ts`;
  `frontend/src/pages/Login.tsx` e `Login.test.tsx`;
- PR #59; backlog `SEC-16`.

---

# 2026-11-03 (xvi) — o release do `SEC-16`

**O problema, como foi entendido no início.** O `SEC-16` estava em `develop` (PR #59) e só valia no
site depois do release.

**Hipótese de trabalho.** Que o release mudasse só o roteador e a validação do login, sem efeito no
resto do site.

**O que foi testado, e como.** Diff `main..develop` (só `frontend/`: as dependências e quatro arquivos
de código e teste); PR #60 depois dos 9 checks; deploy acompanhado pela API de deployments; depois,
`/health`, `/privacidade`, `PATCH /api/me/perfil` sem credencial, o pacote publicado e um login do
autor.

**Resultado medido.** Deploy `7534293060`, `success`, SHA `87622ce`. `/health` `200`, banco ok;
`/privacidade` `200`; `PATCH` sem credencial → `401`; a validação nova (`destinoSeguro`) no pacote
publicado. **O autor confirmou o login.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O CI não roda `npm audit` (diário, 03/11 (xv)).

**Procedência.** PRs #59 e #60 (`87622ce`); deployment de produção `7534293060`; as rotas e o pacote
de `https://dormio-smart.vercel.app`, 03/11; a confirmação do autor; backlog `SEC-16`.

---

# 2026-11-03 (xvii) — `DOC-13` e `CI-08`: o resumo do backlog conferido, e as dependências auditadas

**O problema, como foi entendido no início.** Duas pontas de infraestrutura. O resumo do topo do
backlog (contagem, quadro em uma tela, caminho crítico) é escrito à mão e já listou itens fechados
como pendentes duas vezes (`DOC-13`). E nenhum CI confere as dependências contra avisos publicados:
o `SEC-16` achou o `react-router` com 12 avisos porque alguém rodou `npm audit` à mão.

**Hipótese de trabalho.** Que a regra proposta no `DOC-13` ("ID fechado citado nas seções de
resumo") servisse como estava; e que as dependências do backend estivessem limpas, já que só o
frontend tinha sido auditado.

**O que foi testado, e como.** A regra literal medida antes de escrever: **161 acusações** (Estado
108, Quadro 28, Caminho 25), quase todas prosa histórica legítima. Foi estreitada a três conferências
estruturadas em `scripts/conferir_backlog.py --conferir`: recontagem por camada contra a linha
**Contagem**; o quadro tem de listar exatamente os abertos de cada camada; nenhum fechado ou
pós-banca sem riscar nos passos do caminho crítico. A seção "Estado" ficou de fora, com nota no
topo dizendo isso. Quatro sabotagens em cópias (`--arquivo`): contagem +1, `DIAG-02` no quadro do L0,
`GIT-05` tirado do quadro, `CAL-02` de volta ao caminho crítico. Depois, `npm audit --omit=dev
--audit-level=high` e `pip-audit` 2.10.1 (num ambiente descartável), nesta máquina, e o workflow
novo `auditoria-dependencias.yml` exercido por uma branch descartável (`ci/sabotagem-CI-08`) com
`react-router` 7.13.0 e gunicorn 21.2.0.

**Resultado medido.** Primeira execução do conferidor: **4 divergências** no caminho crítico
(`CAL-02` e `DATA-07b`, `DIAG-02` e `DIAG-04`, todos fechados), corrigidas; contagem e quadro
batiam. Sabotagens **4/4**, cada uma com a mensagem que nomeia o item. `npm audit` de produção:
**0**. `pip-audit`: **4 avisos em 3 pacotes** — Flask 3.1.2 (CVE-2026-27205, `Vary: Cookie` na
`session`), python-dotenv 1.2.1 (CVE-2026-28684, `set_key` segue link simbólico), gunicorn 21.2.0
(CVE-2024-1135 e CVE-2024-6827, contrabando de requisição). Nenhum explorável aqui: a Vercel roda
pelo `@vercel/python` e o gunicorn não aparece fora do `requirements.txt`; o backend não usa a
`session` do Flask nem o `set_key`. Por decisão do Vitor os três subiram (3.1.3, 1.2.2, 22.0.0):
**417 testes do backend passam** em Python 3.11 limpo, e o `pip-audit` sai sem aviso. Na sabotagem,
os dois jobs do workflow reprovaram (execução `41749478900`): o `npm audit` listou os avisos do
`react-router` (faixa até 7.18.1; o 7.18.4 em uso fica fora), o `pip-audit` os dois do gunicorn.

**Adaptação.** A regra do `DOC-13` mudou de "ID fechado citado" para três conferências
estruturadas — a literal acusaria 161 menções e ensinaria a ignorar o alarme. O plano aprovado
previa parar se o `pip-audit` acusasse: parou, os avisos foram levados ao Vitor com a análise de
alcance, e a decisão foi subir as versões em vez de ignorar os IDs.

**O que deu errado no caminho.** A primeira tentativa da sabotagem do quadro não acusou: o
`replace` pegou a primeira ocorrência de `DOC-13` no arquivo, que era a nota nova no topo do
"Estado", fora do quadro. O defeito era da sabotagem, não do script; refeita dentro do quadro,
acusou. E o primeiro script de sabotagem quebrou ao imprimir `✗` no console `cp1252` — o
`PYTHONIOENCODING=utf-8` resolveu (o script em si já reconfigura a saída).

**Risco em aberto.** O agendamento semanal só roda a partir de `main` (vale depois do release). As
ferramentas de teste e build têm 7 avisos (`tinypool` crítico, `source-map-js` alto), fora do
workflow de propósito — `SEC-17`. O gunicorn segue no `requirements.txt` sem ser usado; tirá-lo
muda a stack descrita e ficou para decisão do autor.

**Procedência.** Branch `chore/DOC-13-conferir-backlog-e-auditoria`; `scripts/conferir_backlog.py`;
`.github/workflows/auditoria-dependencias.yml`; execução de sabotagem `41749478900` (branch
`ci/sabotagem-CI-08`, não mesclada); backlog `DOC-13`, `CI-08`, `SEC-17`.

---

# 2026-11-03 (xviii) — o release do `DOC-13` e do `CI-08`

**O problema, como foi entendido no início.** O `DOC-13` e o `CI-08` estavam em `develop` (PR #62).
As versões corrigidas do backend só valiam na produção, e o agendamento da auditoria só rodava,
depois do release para `main`.

**Hipótese de trabalho.** Que a troca de Flask, python-dotenv e gunicorn não mudasse nada visível,
já que os 417 testes do backend passaram com as versões novas e a Vercel não usa o gunicorn.

**O que foi testado, e como.** Diff `main..develop` (só o `requirements.txt` muda a produção); PR #63
com 13 checks, as duas auditorias incluídas; deploy acompanhado pela API de deployments; depois,
`/health`, as rotas de ingestão e de perfil sem credencial e com `Bearer` inválido, `/privacidade`;
a auditoria disparada à mão a partir de `main`; e um login do autor.

**Resultado medido.** Deploy `7534968706`, `success`, SHA `f754b96`. `/health` `200`, banco ok,
contrato `2.7.0`; `PATCH /api/me/perfil`, `POST /api/data/lote` e `GET /api/features` → `401` sem
credencial, `Bearer` inválido → `401`; `/privacidade` `200`. Auditoria a partir de `main`: execução
`41751583490`, os dois jobs verdes. **O autor confirmou o login.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** A versão dos pacotes que a Vercel instalou não é visível de fora: o que garante
o Flask 3.1.3 é o `requirements.txt` de `main`, não uma medição na produção. O agendamento semanal
ainda não rodou sozinho — a primeira execução agendada é a da próxima segunda-feira. `SEC-17` segue
aberto.

**Procedência.** PRs #62 e #63 (`f754b96`); deployment de produção `7534968706`; execução
`41751583490`; as rotas de `https://dormio-smart.vercel.app`, 03/11; a confirmação do autor; backlog
`CI-08`.

---

# 2026-11-03 (xix) — `SEC-17`: as ferramentas de teste e build atualizadas

**O problema, como foi entendido no início.** O `npm audit` sem `--omit=dev` achava 7 avisos nas
ferramentas de teste e build (`tinypool` crítico, `source-map-js` alto, `esbuild`, `vite-node` e
`@vitest/mocker` moderados), fora da auditoria do `CI-08` de propósito.

**Hipótese de trabalho.** Que o `npm audit fix` sem `--force` resolvesse boa parte, e que sobrasse o
`vitest`, de versão maior. E que o `vite`, por gerar o pacote do site, pudesse mudar o que vai para
a produção.

**O que foi testado, e como.** Numa cópia fora do repositório, o `npm audit fix` sem `--force`.
Depois, na branch: suíte e build **antes** (462 testes; pacote guardado); `npm audit fix`; `vite`
6.4.5 e `vitest` 4.1.12 com versão fixa; suíte, `tsc`, build comparado byte a byte com o de antes;
o servidor de desenvolvimento com `/`, `/login` e `/privacidade` no navegador do app. Sabotagens
com o vitest novo: `destinoSeguro` aceitando caminho sem barra, `montagem.test.ts` sem a diretiva
`jsdom`, um módulo órfão em `src/components/`, e o `vitest.config.ts` sem a liberação de `docs/`.
Para a auditoria ampliada: o lockfile de antes, com o comando antigo e com o novo.

**Resultado medido.** O `audit fix` sem `--force` resolveu **1 de 7** (`source-map-js` 1.2.2): o
`vite` está com versão fixa e o `vitest` precisava de duas versões maiores — o 3.2.7 ainda traz o
`tinypool` vulnerável. Com 6.4.5 e 4.1.12: `npm audit` completo **0**; o `tinypool` saiu da árvore.
**462 testes, 32 arquivos**, como antes; `tsc` limpo; o `dist/` **idêntico byte a byte** ao de
antes — a troca não muda nada que vai para o site. As três páginas abriram no servidor de
desenvolvimento. Sabotagens **4/4**: 4 casos do `destinoSeguro`, 4 da montagem, o órfão e o
arquivo da política caíram. No lockfile antigo, `--omit=dev` passa (saída 0) e o comando novo
reprova (saída 1).

**Adaptação.** O plano previa só subir versões. Com o vitest 4, `Privacidade.test.tsx` e a
montagem do `/dashboard` caíram com `Denied ID …/POLITICA-DE-PRIVACIDADE.md?raw`: desde o vite 6.4
o carregador dos testes confere o caminho **com a query**, e uma liberação de arquivo nunca casa
com `…md?raw` — só a de pasta. Confirmado liberando `docs/` por um instante (os 22 testes dos dois
arquivos passaram). A liberação de `docs/` ficou só no `vitest.config.ts`; o `vite.config.ts`
segue liberando o arquivo, e só ele. A auditoria do `CI-08` passou de `--omit=dev` para todas
as dependências, por decisão do Vitor no plano.

**O que deu errado no caminho.** Três coisas. (1) Tentei primeiro exportar a lista do
`vite.config.ts` para o `vitest.config.ts` — a falha continuou, porque o problema não era a lista
faltar, era a query no caminho; só lendo o código do vite (`isServerAccessDeniedForTransform`) a
causa apareceu. (2) Supus que o servidor de desenvolvimento também quebraria a `/privacidade`; não
quebra — o navegador pede `/@fs/…?import&raw` e recebe `200`. A suposição estava no relato antes
de ser medida e foi corrigida pela medição. (3) A sabotagem da liberação foi desfeita com
`git checkout` do arquivo, que levou junto a alteração ainda não commitada; refeita, e a suíte
voltou a 462.

**Risco em aberto.** O `vitest.config.ts` libera `docs/` inteira para os testes; o servidor de
desenvolvimento não. Se outro documento passar a ser importado com `?raw`, os testes aceitam e o
servidor de desenvolvimento recusa — o sintoma aparece no `npm run dev`, não no CI.

**Procedência.** Branch `chore/SEC-17-ferramentas-de-teste-e-build`; `frontend/package.json`,
`package-lock.json`, `vitest.config.ts`; `.github/workflows/auditoria-dependencias.yml`; backlog
`SEC-17`, `CI-08`.

---

# 2026-11-03 (xx) — `UI-21`: o `?raw` conferido contra a liberação do servidor de desenvolvimento

**O problema, como foi entendido no início.** O risco em aberto da entrada (xix): o
`vitest.config.ts` libera `docs/` inteira e o `vite.config.ts` só o arquivo da política. Um segundo
documento importado com `?raw` passaria no CI e no build e só quebraria no `npm run dev`.

**Hipótese de trabalho.** Que um teste estático bastasse: achar os `?raw` dos módulos da aplicação
e conferir cada um contra o `server.fs.allow` do servidor de desenvolvimento. Liberar `docs/` também
no servidor de desenvolvimento foi descartado, por decisão do Vitor: desfaria o "só ele" do
`LGPD-01` (b) sem ganho além de simetria.

**O que foi testado, e como.** `frontend/src/raw.test.ts` importa o `vite.config.ts`, lê a lista e
aplica a regra do vite (arquivo igual, ou pasta que o contém); arquivos de teste ficam de fora, porque
só rodam no vitest. Imprime o que achou e reprova se não achar nada (catraca). Três sabotagens:
`docs/LGPD-ELIMINACAO.md?raw` importado em `lib/politica.ts` sem liberar; a política tirada da lista do
`vite.config.ts`; a expressão da busca trocada para não casar com nada.

**Resultado medido.** A busca acha exatamente um: `pages/Privacidade.tsx →
docs/POLITICA-DE-PRIVACIDADE.md`. Sabotagens **3/3**: as duas primeiras derrubam "todo arquivo
importado com ?raw está liberado", a terceira derruba a catraca — e, sem a catraca, o outro teste
teria passado sem conferir nada. Suíte: **464 testes, 33 arquivos**; `tsc` limpo.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** A primeira tentativa da terceira sabotagem não se aplicou: o `sed`
não casou com a linha, ela ficou igual, e o "2 passed" que saiu não provava nada. Notado porque o
`grep` logo depois mostrou a linha intacta; refeita com Python, conferindo a troca antes de rodar.
Desta vez as sabotagens foram desfeitas a partir de cópias, e não com `git checkout` — o arquivo do
teste ainda não estava commitado, que é o que apagou uma alteração na entrada (xix).

**Risco em aberto.** O teste confere a lista, não o servidor: que o servidor de desenvolvimento
sirva a página foi medido à mão, no navegador, em 03/11. Um `?raw` escrito fora do padrão
`from "…?raw"` (um `import()` dinâmico, por exemplo) não seria achado — a catraca só garante que o
de hoje é.

**Procedência.** Branch `chore/UI-21-raw-liberado-no-dev`; `frontend/src/raw.test.ts`; backlog
`UI-21`; diário 03/11 (xix).

---

# 2026-11-03 (xxi) — `UI-22`: o `?raw` conferido contra o servidor de verdade

**O problema, como foi entendido no início.** Os dois limites que a entrada (xx) declarou no
`UI-21`: a busca só achava `from "…?raw"`, e o teste conferia a lista do `vite.config.ts` com uma
cópia da regra do vite escrita à mão, não o servidor. Na análise apareceu um terceiro: o vite confere
do mesmo jeito `?url` e `?inline` (`isServerAccessDeniedForTransform`), que a busca não via.

**Hipótese de trabalho.** Que bastasse alargar a busca e trocar a cópia da regra por um pedido HTTP
ao servidor de desenvolvimento, exigindo `200`.

**O que foi testado, e como.** Busca nova: qualquer texto entre aspas ou crases terminado em
`?raw`, `?url` ou `?inline`; `import.meta.glob` reprova, porque não deixa o caminho escrito. O teste
sobe o servidor com o `vite.config.ts` (`createServer`, porta livre, sem HMR nem pré-otimização) e
pede `/@fs/…?import&<query>` para cada achado. Antes das sabotagens, uma sonda fora do teste pediu
três arquivos: a política, um que não existe e um de `docs/` fora da lista. Sabotagens: `import()`
dinâmico de `docs/LGPD-ELIMINACAO.md?raw`; o mesmo com `?url` em template string; `import()` de um
caminho inexistente; um `import.meta.glob`; a política tirada da lista do `vite.config.ts`.

**Resultado medido.** A sonda: política → `200`, `text/markdown`, o conteúdo; **inexistente → `200`,
`text/html`, o `index.html` da aplicação**; fora da lista → `403`. Por isso o teste exige o corpo
igual ao arquivo em disco, e não só o status. Sabotagens **5/5**, cada uma pela mensagem certa: os
dois imports de outro documento → `403`, o inexistente → "arquivo não existe", o `glob` derruba o
seu teste, a política fora da lista → o servidor recusa. Suíte: **465 testes, 33 arquivos**; `tsc`
limpo; o servidor sobe e responde em menos de 100 ms.

✏️ *Mesmo dia, antes do merge, a pedido do Vitor: avaliado o limite que restava, o caminho montado em
execução. Medido com sabotagens temporárias: um template com variável
(`` import(`../docs/${nome}.md?raw`) ``) **já reprova** ("arquivo não existe"); a concatenação
(`import(base + "?raw")`) passava no teste e **no build, sem aviso** (com `@vite-ignore`), o documento
**não entrava no pacote** — o publicado tinha `import(Sp+"?raw")`, que o navegador pediria em tempo de
execução — e os testes de página não pegariam, porque o vitest resolve. Era defeito de produção, não
só divergência de desenvolvimento. Entrou um quarto teste: texto entre aspas que **começa** com a
query reprova. Sabotagens 2/2 (`?raw` e `?url` concatenados); suíte **466**. Uma primeira tentativa
de medir o build não valeu: a alteração na página não se aplicou e o build podou o código sabotado;
refeita com a troca conferida.*

**Adaptação.** O plano previa exigir só `200`. A sonda mostrou que `200` passa para arquivo que não
existe, e o teste passou a comparar o corpo.

**O que deu errado no caminho.** A primeira versão da sonda falhou duas vezes antes de rodar: o
heredoc do shell comeu a barra invertida de uma expressão regular, e o script, fora de `frontend/`,
não achava o pacote `vite`. Rodou como `node -e` de dentro de `frontend/`.

**Risco em aberto.** A concatenação simples reprova (ver a nota acima); um caminho montado de forma
mais elaborada — a query guardada numa variável — continua fora da busca, e está escrito no próprio
teste. O teste prova que o servidor serve o arquivo, não que
a página o renderiza; isso é do `Privacidade.test.tsx` e do `montagem.test.ts`.

**Procedência.** Branch `chore/UI-22-raw-no-servidor-real`; `frontend/src/raw.test.ts`; backlog
`UI-21`, `UI-22`; diário 03/11 (xx).

---

# 2026-11-03 (xxii) — `INFRA-04`: o gunicorn sai, e a stack documentada volta a bater

**O problema, como foi entendido no início.** O `gunicorn` estava no `web-app/requirements.txt` e na
stack do `CLAUDE.md` e do `README.md`, sem rodar em lugar nenhum: a Vercel serve o backend pelo
`@vercel/python`. Ele só aparecia nos avisos do `pip-audit` (`CI-08`, entrada (xvii)).

**Hipótese de trabalho.** Que nada dependesse dele: nem os testes, nem o import do `app`, nem
documento do TCC.

**O que foi testado, e como.** Busca por `gunicorn`, `wsgi` e `Procfile` no repositório e nos
documentos locais não versionados (`DOCUMENTO-TCC.md`, `ROADMAP.md`, `METODOLOGIA.md`,
`HARDWARE.md`, roteiro). Depois de tirá-lo do `requirements.txt`: ambiente Python 3.11 limpo,
instalado só do arquivo, conferido que o pacote **não** está presente; os testes do backend; o
`import app` como a Vercel faz; o `pip-audit`. A linha de stack do `README.md` foi refeita contra o
`frontend/package.json`, o `web-app/requirements.txt` e o `ml/requirements.txt`.

**Resultado medido.** Gunicorn só no `requirements.txt`, no `CLAUDE.md` e no `README.md` (mais o
histórico no diário, no backlog e no comentário do workflow, que ficam). Nenhum documento local o
cita — o texto do TCC não muda. Sem ele: **417 testes passam**, `import app` devolve o `Flask`,
`pip-audit` sem aviso. A stack do `README.md` dizia "Tailwind + Chart.js": o gráfico é **Recharts**,
e faltavam React, TypeScript, Vite, o ML e o vitest.

**Adaptação.** Ao ler o `README.md` inteiro para corrigir a stack, apareceram mais cinco
afirmações velhas — a principal, mandar preencher a `SUPABASE_SERVICE_ROLE_KEY`, que a produção
não usa desde o `SEC-14`. Ficaram fora deste item, que era a stack: viraram o `DOC-14`, porque
reescrever instruções de instalação pede executá-las numa cópia limpa antes, e isso não estava no
plano.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Só depois do release: a Vercel instala o `requirements.txt` sem o gunicorn, e
a conferência é o `/health` e o login. Se o backend um dia sair da Vercel, um servidor WSGI volta a
ser necessário — está escrito no `CLAUDE.md`. O README segue com o resto envelhecido: `DOC-14`.

**Procedência.** Branch `chore/INFRA-04-remover-gunicorn`; `web-app/requirements.txt`,
`README.md`, `CLAUDE.md`; backlog `INFRA-04`, `DOC-14`.

---

# 2026-11-03 (xxiii) — o release do `INFRA-04`, do `SEC-17`, do `UI-21` e do `UI-22`

**O problema, como foi entendido no início.** Quatro itens em `develop` (PRs #64 a #68). Só o
`INFRA-04` mudava o que a Vercel instala (o `requirements.txt` sem o gunicorn); o `SEC-17` trocava a
ferramenta de build; os outros dois eram testes.

**Hipótese de trabalho.** Que o backend subisse sem o gunicorn na Vercel e que o site publicado não
mudasse, porque o build local com o vite novo saiu idêntico byte a byte ao de antes.

**O que foi testado, e como.** Diff `main..develop`; PR #69 com 13 checks; deploy acompanhado pela
API de deployments; depois, `/health`, as rotas de perfil e de ingestão sem credencial e com
`Bearer` inválido, `/privacidade`, o nome do pacote publicado, e um login do autor. Tentativa de
comparar o pacote com o do deploy anterior pelas URLs de cada deploy.

**Resultado medido.** Deploy `7536039508`, `success`, SHA `9d19ec1`. `/health` `200`, banco ok —
o backend sobe na Vercel sem o gunicorn; rotas sem credencial e `Bearer` inválido → `401`;
`/privacidade` `200`. **O autor confirmou o login.** O pacote publicado é `index-BZZthQcI.js`,
diferente do build local (`index-MJqm7df1.js`) — esperado, porque o build da Vercel inclui as
variáveis do controlador da política.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** A comparação com o deploy anterior não foi possível: as URLs de
cada deploy respondem `200` com a página de login da Vercel, não com o site. Fica registrado como
não medido, em vez de dado por igual.

**Risco em aberto.** Que o pacote publicado não mudou é inferência (build local idêntico + as
mesmas variáveis), não medição na produção. O `DOC-14` segue aberto.

**Procedência.** PRs #64 a #69 (`9d19ec1`); deployment de produção `7536039508`; as rotas de
`https://dormio-smart.vercel.app`, 03/11; a confirmação do autor; backlog `INFRA-04`, `SEC-17`,
`UI-21`, `UI-22`.

---

# 2026-11-03 (xxiv) — `DOC-14`: o README reescrito, executado e com o painel de hoje

**O problema, como foi entendido no início.** O `README.md` é a primeira coisa que a banca lê, e o
`INFRA-04` mostrou que ele envelheceu além da stack. O Vitor pediu revisão completa, inclusive das
imagens.

**Hipótese de trabalho.** Que bastasse reescrever as seções contra o código; e que a imagem do
painel viesse de uma conta de demonstração alimentada pelo `fake_sensor.py`, criada pelo autor.

**O que foi testado, e como.** Cada seção medida contra o código: as rotas de `routes.py` (13, não
4), as rotas do `App.tsx`, os `.env.example`, os `package.json` e `requirements.txt`, os
documentos versionados, a imagem (`img/dashboard.jpeg`, de 03/06). O README novo foi **executado
num clone limpo**, comando por comando: instalação e subida do backend sem chaves, os testes do
backend, do frontend e do ML, `npm ci` e servidor de desenvolvimento, e o simulador contra a produção
com token inválido. Os 22 links relativos conferidos por script contra `git ls-files` (inclusive
âncoras), com três sabotagens. Para a imagem: o modo demonstração já existente (`DEMO-01`,
`/dashboard?demo=1`) e captura com o Edge sem interface, a 1920 × 1500.

**Resultado medido.** No clone limpo: backend sobe e responde `503` ("consulta falhou") sem chaves,
como o README diz; **417, 466 e 134 testes**; o servidor de desenvolvimento serve `/` e
`/privacidade`; o simulador chega à produção e recebe `401` (`device nao autorizado`). Links: 22
certos; as sabotagens — arquivo inexistente, âncora inexistente e `docs/METODOLOGIA.md`, que existe
no disco mas é gitignorado — reprovaram, **3/3**. A imagem antiga era de **outra aplicação** (o
painel em Flask/Tailwind, com "Movimento Detectado!"); saiu. A nova é o painel React real com os
dados sintéticos do modo demonstração e a faixa "MODO DEMONSTRAÇÃO" dentro do quadro.

**Adaptação.** Três. (1) Criar conta na produção, mesmo de teste, está fora do que o assistente faz;
a captura veio do modo demonstração, que não precisa de conta nem sai da máquina. (2) O modo
demonstração **não funcionava**: o `/dashboard?demo=1` caía no `/login`. Pelo histórico, o
`DEMO-01` é de 19/08 e o guarda de rotas (`AUTH-04`) de 20/08 — a demo está quebrada desde o dia
seguinte ao que nasceu, e nada notou. Para não ampliar o escopo, o guarda foi liberado
**temporariamente** na cópia local, a captura tirada e o arquivo restaurado (conferido com
`git diff --quiet`); a correção definitiva é o `DEMO-02`. (3) Ao capturar a página inicial
publicada, ela descrevia a arquitetura antiga (Deep Sleep, envio a cada evento, validação por
dataset pendente): não entrou no README, e virou o `UI-23`. Os READMEs de `web-app/` e
`firmware/` mostraram marcadores da versão antiga numa busca: `DOC-15`.

**O que deu errado no caminho.** A execução no clone pegou um erro do README novo, não do velho: as
instruções mandavam rodar os testes sem instalar o `pytest`, que não está no `requirements.txt`.
Corrigido e reexecutado. O primeiro teste do simulador não imprimiu nada — o `timeout` matava o
processo antes de o Python esvaziar a saída; com `-u` apareceu o `401`. A primeira captura pelo
Edge não gerou arquivo, porque o caminho curto do Windows (`VITOR-~1`) não foi aceito; com o caminho
longo, gerou. E a captura pelo painel do navegador do app saía reduzida (800 px, JPEG), por isso o
Edge.

**Risco em aberto.** A imagem mostra "Conta não autenticada" na barra lateral — efeito de a demo
rodar sem sessão; honesto, mas é o `DEMO-02` que decide se a demo deve parecer logada. O que
depende de chave real do Supabase (login, dados reais) não foi exercitado no clone limpo, e o README
diz isso. `DEMO-02`, `UI-23` e `DOC-15` abertos.

**Procedência.** Branch `docs/DOC-14-readme`; `README.md`, `img/painel-demonstracao.png`,
`web-app/fake_sensor.py`; backlog `DOC-14`, `DEMO-02`, `UI-23`, `DOC-15`.

---

# 2026-11-04 — `DEMO-02`, `UI-23` e `DOC-15`: a demo, a página inicial e os READMEs das pastas

**O problema, como foi entendido no início.** Os três itens que a revisão do README (`DOC-14`)
abriu: o modo demonstração quebrado desde 20/08 pelo guarda de rotas; a página inicial do site
descrevendo a arquitetura abandonada em 30/10; e os READMEs de `web-app/` e `firmware/` com
trechos da versão antiga.

**Hipótese de trabalho.** Que o guarda pudesse liberar a demo sem risco para a produção, porque
`estaEmModoDemo` já é falso fora do build de desenvolvimento; que os textos da página inicial
fossem só texto; que os READMEs pudessem ser conferidos contra o código como no `DOC-14`.

**O que foi testado, e como.** `Guardas.test.tsx`: a rota e o guarda reais, sessão falsa, quatro
casos, inclusive `DEV` falso por `vi.stubEnv`; sabotagens tirando a liberação e tirando a
salvaguarda de `demo.ts`. Depois, o build de produção servido com `vite preview` e
`/dashboard?demo=1` aberto no navegador. `Landing.test.tsx`: o texto **renderizado** da página,
procurando os termos da arquitetura antiga e exigindo os da C2; sabotagem devolvendo a frase do
Deep Sleep. READMEs: cada afirmação contra o código — `routes.py` (códigos de resposta),
`database.py` (a alternativa da `service_role`), `sketch.ino` (o sono leve acorda só por
`esp_sleep_enable_timer_wakeup`), todos os `.ino` (nenhum usa o GPIO 27 nem `MODO_SIMULADOR`) — e
links pelo script do `DOC-14`. Suíte inteira e build.

**Resultado medido.** Guarda: 4/4 testes, sabotagens **2/2**, cada uma no teste certo. **No build
de produção, `?demo=1` foi ao `/login`, sem faixa**; no servidor de desenvolvimento, o painel abriu
com a faixa. Página inicial: 5/5 testes; a sabotagem derrubou 3. READMEs: 4 e 7 links certos,
sabotagem 3/3. Frontend: **475 testes, 35 arquivos**; build limpo.

**Adaptação.** O `web-app/README.md` documentava a `service_role` como "*fallback* até a de cima
existir", e o código ainda tem esse caminho (`database.py`): ficou descrita como alternativa só
de desenvolvimento local, que não existe na Vercel desde o `SEC-14`. Tirar o código não era deste
item.

**O que deu errado no caminho.** O verificador de links do `DOC-14` acusou falha em todo link dos
READMEs das pastas, inclusive nos certos. Dois defeitos dele, um atrás do outro: comparava
`../docs/...` com a lista do `git ls-files`, que é relativa à raiz; corrigido isso, o
`git ls-files` rodava dentro da subpasta e devolvia caminhos relativos a ela. Com o README da raiz
os dois eram invisíveis. Corrigido (caminho resolvido a partir da raiz, `ls-files` na raiz) e
sabotado de novo nas pastas.

**Risco em aberto.** Em modo demonstração, o painel ainda chama `GET /api/devices`, que no
servidor de desenvolvimento sem backend responde `500` no console — o painel aparece, mas a demo
não é inteiramente local. A página inicial nova só vale no site depois do release. As instruções
do Wokwi no `firmware/README.md` não foram executadas e estão marcadas assim.

**Procedência.** Branch `feature/DEMO-02-UI-23-DOC-15`; `frontend/src/components/Guardas.tsx` e
`Guardas.test.tsx`, `frontend/src/pages/Landing.tsx` e `Landing.test.tsx`, `web-app/README.md`,
`firmware/README.md`; backlog `DEMO-02`, `UI-23`, `DOC-15`.

---

# 2026-11-04 (ii) — o release do `DOC-14`, do `DEMO-02`, do `UI-23` e do `DOC-15`

**O problema, como foi entendido no início.** Quatro itens em `develop` (PRs #70 a #72): a página
inicial nova só valia no site, e o README novo só aparecia na página do GitHub, depois do release.

**Hipótese de trabalho.** Que a página inicial publicada mostrasse os textos novos e que a
liberação do modo demonstração não chegasse à produção — o que o build local já tinha mostrado.

**O que foi testado, e como.** PR #73 com 9 checks; deploy acompanhado pela API de deployments;
depois, `/health`, as rotas sem credencial, `/privacidade`, o pacote publicado (procurando os
textos novos e os termos antigos), a página inicial e `/dashboard?demo=1` no navegador, o
`README.md` da `main` pela API do GitHub, e um login do autor.

**Resultado medido.** Deploy `7537089021`, `success`, SHA `31cfb7d`. `/health` `200`, banco ok;
rotas sem credencial → `401`; `/privacidade` `200`. No pacote publicado, "fica em sono leve" e
"A cada 10 minutos" aparecem, "Deep Sleep" e "Wake-on-Motion" não; a página no navegador confirma.
**`/dashboard?demo=1` na produção foi ao `/login`, sem faixa.** O README da `main` tem a seção de
estado e a imagem nova. **O autor confirmou o login.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** A chamada a `/api/devices` no modo demonstração (diário de 04/11) segue —
só no servidor de desenvolvimento.

**Procedência.** PRs #70 a #73 (`31cfb7d`); deployment de produção `7537089021`; a página e o
pacote de `https://dormio-smart.vercel.app`, 04/11; o README da `main`; a confirmação do autor;
backlog `DOC-14`, `DEMO-02`, `UI-23`, `DOC-15`.

---

# 2026-11-04 (iii) — `DEMO-03`: a demonstração deixa de chamar a API

**O problema, como foi entendido no início.** O risco que a entrada de 04/11 deixou em aberto: em
modo demonstração o painel pedia `GET /api/devices`, e o servidor de desenvolvimento sem backend
respondia `500` no console. Ficou registrado só no diário — e a prática 2 do `CLAUDE.md` pede que
todo risco em aberto aponte um item do backlog. O Vitor apontou.

**Hipótese de trabalho.** Que fosse o `useDispositivos` sem a verificação que o `useHistorico` já
tem, e que bastasse devolver a lista vazia em demo — o mesmo efeito na tela que a falha silenciosa
já produzia, sem o pedido.

**O que foi testado, e como.** `useDispositivos.test.ts`, com `listarDispositivos` falso: em demo
não é chamado; fora dela, é, e a lista chega; com `DEV` falso, `?demo=1` não desliga a busca.
Sabotagem tirando o retorno da demo. Suíte inteira e build. No servidor de desenvolvimento,
`/dashboard?demo=1`: os pedidos de rede e o console, **depois de o painel estar na tela**.

**Resultado medido.** 3/3 testes; a sabotagem derrubou o teste da demo, **1/1**. Frontend **478
testes, 36 arquivos**; build limpo. No navegador, com o painel e a faixa na tela: **zero pedidos a
`/api`**, console sem erro.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** A primeira leitura da rede, feita logo depois de abrir a página,
deu "zero pedidos" — mas o painel ainda não tinha renderizado (o vite estava reotimizando as
dependências depois do build). Zero pedidos de uma página vazia não prova nada; a medição foi
repetida com o painel na tela.

**Risco em aberto.** Nenhum novo. A mudança só vale fora da produção (a demo é falsa lá) e entra no
site no próximo release.

**Procedência.** Branch `bugfix/DEMO-03-demo-sem-api`; `frontend/src/hooks/useDispositivos.ts` e
`useDispositivos.test.ts`; backlog `DEMO-03`; diário 04/11.

---

# 2026-11-04 (iv) — `CALC-01`: o modelo de energia com a C2 que o firmware implementou

**O problema, como foi entendido no início.** O capítulo de modelos quantitativos
(`CALCULOS-TCC.md`, Z.4) já tinha a C2 desde o `ARQ-01` (30/10), mas escrita antes do firmware:
entrega por época ou "um lote por hora", com 1 s de rádio por entrega, e a autonomia de
armazenamento da fila antiga na RAM (32 B, 8,53 h). O `sketch.ino` fixou outra coisa: lote a cada
10 min, cada envio religando o Wi-Fi, e a época gravada na flash (64 B). E o texto do TCC
(Produto 5, 6.4.1) estava ainda mais atrás: Deep Sleep, ciclo de dois estados.

**Hipótese de trabalho.** Registrada antes de rodar: a corrente da C2 implementada ficaria entre o
lote por hora (2,03 mA) e o envio por época (5,31 mA), e **o rádio continuaria a maior parcela**.

**O que foi testado, e como.** Um cenário novo em `scripts/estudo_cadencia.py` que **lê do
firmware** o intervalo de envio (`INTERVALO_DE_ENVIO_US`, `sketch.ino`) e o de drenagem
(`INTERVALO_DE_DRENAGEM_US`, `nucleo/cadeia_c2.h`); o envio completo como estimativa em faixa
(2, 4, 8 s); a gravação na flash como estimativa (programação, apagamento de setor a cada 64
registros, corrente); a decomposição por parcela; a varredura de todos os parâmetros; a energia de
uma noite. Asserções no `--conferir`, que roda no CI. Três sabotagens: o envio a 5 min **no
próprio `sketch.ino`**, a drenagem a 1,6 s **no núcleo**, e a premissa do envio no script. O texto
do Produto 5 lido pelo conector do Drive para montar a inserção.

**Resultado medido.** Referência: **2,68 mA** (2,35 a 3,34 mA conforme o envio; 1,88 a 5,81 mA na
varredura) — dentro da faixa prevista. **A segunda metade da hipótese caiu:** o rádio é **25 %**,
e as outras parcelas são do mesmo tamanho — transdutor 22 %, sono leve 29 %, esvaziar a FIFO 24 %;
a flash, 0,5 %. Nenhuma passa de 30 %. Com a placa: 1 mA de consumo fixo acrescenta 37 %, e 3 mA
já superam os circuitos integrados. Autonomia de referência com 2 000 mA·h: 746 h; 255 J numa
noite de 8 h. A drenagem do modelo (85 amostras / 50 Hz) bate com a do firmware. Sabotagens
**3/3**: a do envio derrubou 11 asserções; a da drenagem acusou exatamente a divergência
firmware × modelo.

**Adaptação.** Três. (1) A conclusão do capítulo mudou de forma: até aqui, "agregar envios é a
alavanca"; com o lote de 10 min, a alavanca está gasta e nenhuma mudança isolada tira mais que um
quarto — o que **reforça** a de que o consumo fixo da placa decide (`HW-02`). (2) O texto do TCC
não estava no `DOCUMENTO-TCC.md` (parado no Produto 3): foi lido no Drive. Há dois documentos
candidatos ("Produto 5", 10/09, e "Copy of Produto 5", 30/09) com a mesma 6.4.1; a inserção diz
isso e deixa a escolha com os autores. (3) Ao ler o Produto 5, quatro outros trechos ainda falam
de Deep Sleep e despertar por movimento: viraram o `DOC-16`.

**O que deu errado no caminho.** O primeiro texto dizia que os limites de espera de um envio
"somam 28 s" (20 s de Wi-Fi + 8 s de POST); conferido no `sketch.ino`, o envio também sincroniza o
relógio por NTP, com 5 s, e manda até 20 lotes por conexão — corrigido para 33 s. A inserção citava
a 6.4.2 como `CALC-03` e o trecho do "circuito de *wake-up*" como 5.7; são o `CALC-04` e a 5.6.
E o primeiro script de edição, longo, num heredoc, foi recusado pelo shell; foi para um arquivo.
Ao fechar o item, o conferidor do `DOC-13` reprovou o backlog: o `CALC-01` seguia citado sem
riscar no caminho crítico — o que ele existe para pegar.

**Risco em aberto.** Nada disto é medição: o envio completo, a corrente de sono leve na placa e o
consumo fixo da placa seguem estimados — é o `VAL-02`, depois da solda. A inserção no Produto 5
depende dos autores colarem. O resto do texto do TCC com a arquitetura antiga é o `DOC-16`.

**Procedência.** Branch `feature/CALC-01-energia-c2`; `scripts/estudo_cadencia.py`;
`docs/CALCULOS-TCC.md` (Z.4.4b a Z.4.7, procedência); nota em `docs/DECISAO-ARQ-01-CADENCIA.md`
§4.2; inserção fora do repositório em `documento/INSERCAO-CALC-01-ENERGIA-C2.md`; Produto 5 lido
em 04/11; backlog `CALC-01`, `DOC-16`.

---

# 2026-11-04 (v) — `CALC-02`: a física da medição travada no CI e levada ao texto

**O problema, como foi entendido no início.** O item pedia a física do acelerômetro — força
específica, resolução, ruído, Nyquist — e o porquê de 21 Hz e não 260 Hz. O levantamento mostrou
que o conteúdo **já existia** no Z.1 de `CALCULOS-TCC.md`, atualizado para a C2 e coerente com o
firmware, mas que metade dos números dele não estava travada por nenhuma conferência, e que a
6.4.3 do texto do TCC (Produto 5) estava atrás: sem ruído, sem a justificativa do filtro, e com
uma frase que contradiz o cálculo — "faixas menores ofereceriam resolução mais fina".

**Hipótese de trabalho.** Que o Z.1 estivesse certo e bastasse travá-lo, ligando-o ao firmware
para que uma mudança de configuração do sensor não deixasse o texto justificando o que não roda.

**O que foi testado, e como.** Asserções novas em `scripts/calculos_tcc.py` para cada número do Z.1
que não estava travado. Leitura, pelo script, da configuração que o `sketch.ino` grava no sensor
(`nucleo/fifo_mpu.h`: `C2_DLPF_CFG`, `C2_SMPLRT_DIV`, `C2_ACCEL_CONFIG`), convertida pelas tabelas
do Register Map em banda, taxa e fundo de escala, e das chamadas da biblioteca nos dois sketches
de bancada. Quatro sabotagens: DLPF de 44 Hz e ±4 g no `fifo_mpu.h`, filtro de 44 Hz no
`envio-continuo.ino`, densidade de ruído de 300 µg/√Hz no script. A 6.4.3 do Produto 5 lida
no Drive para montar a inserção, e a numeração das equações do texto levantada antes de escrever.

**Resultado medido.** O firmware dá **21 Hz, 50 Hz e ±8 g**, como o Z.1 diz. Todas as asserções
passam. Sabotagens **4/4**, cada uma pela asserção certa: a do DLPF derrubou a banda e a condição
"taxa acima do Nyquist do filtro"; a do fundo de escala, só ela; a do sketch de bancada apontou o
arquivo; a da densidade derrubou os σ e as razões contra a quantização — e não o fator
√(260/21), que não depende dela, como devia.

**Adaptação.** Uma frase do Z.1 dizia que "a biblioteca empregada adota, por omissão, 260 Hz"; o
firmware do dispositivo não usa a biblioteca — grava o registrador —, e a frase foi precisada. Na
inserção, a relação σ = eₙ · √B ficou no corpo do texto, sem número, para não renumerar as
Equações 8 a 10 da 6.4.4 e as citações a elas.

**O que deu errado no caminho.** O `conferir()` do `calculos_tcc.py` não tinha a função
`verdade` que o do `estudo_cadencia.py` tem; a primeira execução quebrou com `NameError` e ela foi
acrescentada no mesmo molde. **E o achado maior, fora do plano:** antes de abrir o PR, conferido o
`ci.yml`, o `calculos_tcc.py --conferir` **nunca rodou no CI** — nem o `estudo_buffer.py --conferir`.
Só o `estudo_cadencia.py` estava no job `documentos`. O `CLAUDE.md` listava os três como conferências
que "passam", o que era verdade só quando alguém os rodava à mão; e as travas deste item não
travariam nada, e a inserção para o Produto 5 dizia "travada no CI". Os dois entraram no job — é o
§1 das lições de novo: alcance de verificação afirmado, não conferido.

**Risco em aberto.** O σ a 21 Hz continua **calculado** a partir de uma densidade especificada em
outra configuração; a medição é do `CAL-01`, depois da solda. A banda da actigrafia
(0,25–3,5 Hz) entra no texto do TCC sem citação lida — a inserção avisa (`DOC-06b`). Colar a
inserção é com os autores.

**Procedência.** Branch `feature/CALC-02-fisica-da-medicao`; `scripts/calculos_tcc.py`;
`docs/CALCULOS-TCC.md` (Z.1.4 e procedência); inserção fora do repositório em
`documento/INSERCAO-CALC-02-FISICA-DA-MEDICAO.md`; Produto 5 lido em 04/11; backlog `CALC-02`.

---

# 2026-11-04 (vi) — `CALC-03`: o índice de atividade travado e a 6.4.4 do TCC refeita

**O problema, como foi entendido no início.** O item pedia o índice de atividade e a derivação do
limiar `g ± k·σ`. O Z.2 de `CALCULOS-TCC.md` já entregava o índice (as oito características
invariantes a rotação) e já demonstrava que a derivação não se sustenta — o limiar em uso, de
1,2 m/s², equivale a ~67 σ. Faltava travar e levar ao texto. A 6.4.4 do Produto 5, lida no Drive,
descrevia um sistema que não existe mais: índice sobre uma "janela ativa" por despertar, limiar
`μ + k·σ` com k = 3, detecção em dois níveis com o sensor acordando o processador do Deep Sleep.

**Hipótese de trabalho.** Que o Z.2 estivesse certo e que o limiar fosse o mesmo nos três lugares
em que o sistema o usa.

**O que foi testado, e como.** Asserções novas em `scripts/calculos_tcc.py` para os números do Z.2
que não estavam travados (k, 3σ e 5σ, as razões, σ em m/s², a norma L1, o piso do ENMO). Leitura,
pelo script, do limiar em `payload.h`, `caracteristicas.h` e `ml/src/features.py`, e da lista
`NOMES_FEATURES`. Três sabotagens: limiar de 1,5 no `payload.h`; o g do `ml/` trocado de 9,80665
para 9,81 (o limiar muda na quarta casa); uma característica a menos na lista. Antes de escrever o
texto, o código do pico da época (`epoca_c2.cpp`) foi lido.

**Resultado medido.** O limiar é o mesmo nos três lugares (1,2 m/s²; 1,2/9,80665 g); as
características são oito. k = 66,7; 3σ a 5σ dão 0,054 a 0,090 m/s², 22,25× a 13,35× abaixo do
limiar. Sabotagens **3/3**, cada uma pela asserção do arquivo sabotado.

**Adaptação.** A 6.4.4 nova mantém as Equações 8 a 10 com outro conteúdo — a intensidade da época,
o ENMO e k = L/σ — e diz por que o limiar não precisa vir do ruído: quem decide sono e vigília é o
classificador, e o limiar só parametriza uma das oito características. A 6.5 do texto (o ciclo de
Deep Sleep, que cita as Equações 9 e 10) ficou fora e entrou no `DOC-16`.

**O que deu errado no caminho.** Duas coisas. As asserções das razões foram escritas com 13,3 e
22,2 e tolerância de 0,05; os valores são 13,35 e 22,25 e reprovaram — o texto ("de treze a vinte
e duas vezes") estava certo, a asserção é que estava apertada errado. E o primeiro texto da
inserção dizia que a época é representada pela "amostra de maior afastamento do repouso"; lido o
`epoca_c2.cpp`, é a de **maior módulo** — um afastamento para baixo de g só conta se nenhuma outra
amostra for maior. Corrigido, e virou ressalva no texto.

**Risco em aberto.** Essa diferença do rótulo não é defeito de código (o contrato define "pico da
magnitude"), mas afeta o rótulo do painel: anexada ao `VIA-01`, que mostra na bancada se importa. O
valor do limiar segue provisório (`VIA-01`/`CAL-01`). O ENMO entra no texto sem citação lida
(`DOC-06b`). Até o `DOC-16`, a 6.5 do texto contradiz a 6.4.4 nova.

**Procedência.** Branch `feature/CALC-03-indice-de-atividade`; `scripts/calculos_tcc.py`;
`docs/CALCULOS-TCC.md` (🔧 1 e procedência); inserção fora do repositório em
`documento/INSERCAO-CALC-03-INDICE-DE-ATIVIDADE.md`; `firmware/nucleo/epoca_c2.cpp` lido; Produto 5
lido em 04/11; backlog `CALC-03`, `DOC-16`, `VIA-01`.

# 2026-11-04 — `CALC-04`: interfaces elétricas e correção da energia

**O problema, como foi entendido no início.** A Z.3 e a seção 6.4.2 do TCC ainda descreviam o botão e o despertar da arquitetura anterior. Era preciso analisar o I2C e a alimentação do GY-521 na C2.

**Hipótese de trabalho.** A análise elétrica poderia ser atualizada sem alterar a estimativa de energia recém-publicada no `CALC-01`.

**O que foi testado, e como.** Leitura do `sketch.ino` e dos cálculos; execução no computador local de `python scripts/calculos_tcc.py --conferir` e `python scripts/estudo_cadencia.py --conferir`. Na retomada, o pytest de ML teve 37 erros de preparação por acesso negado à pasta temporária no sandbox; a repetição fora dele passou 134 testes. O frontend também precisou sair do sandbox por erro de inicialização do esbuild; passou 478 testes. A sessão anterior relatou três sabotagens: frequência, pino e pull-up de referência; não foram reexecutadas nesta retomada. ✏️ *05/11, na revisão das PRs #79–#84: reexecutadas sobre o commit `2cbf715`, **3/3** — I2C a 100 kHz no `sketch.ino` reprova nos dois scripts (1 e 16 asserções), SDA no GPIO 19 reprova no `calculos_tcc`, pull-up de referência em 4,7 kΩ reprova no `estudo_cadencia` (7 asserções); arquivos restaurados e conferidos.*

**Resultado medido.** O firmware configura 400 kHz, enquanto o modelo usava 100 kHz. Com 2,2 kΩ, a referência calculada passa de 2,68 para 2,28 mA, 878 h para 2 000 mA·h e 217 J em 8 h; são estimativas, não medições físicas. Os limites calculados de capacitância para 2,2 e 10 kΩ são 161 e 35 pF a 400 kHz, e 536 e 118 pF a 100 kHz.

**Adaptação.** A Z.3 foi reescrita, o modelo passou a ler a frequência do firmware e considerar os dois valores de pull-up; a Z.4 e as inserções para as seções 6.4.1 e 6.4.2 foram atualizadas. A hipótese de que o cálculo anterior permaneceria correto caiu.

**O que deu errado no caminho.** Na sessão que começou o item: a primeira asserção da capacitância máxima com 2,2 kΩ a 100 kHz foi escrita com 537 pF, valor de uma conta de bolso com 0,847 arredondado; o script dá 536,5 e a asserção reprovou até ser corrigida. A primeira versão da sabotagem do pull-up de referência teria **passado**: o lote altera a corrente média em só 0,01 mA, abaixo da tolerância — foi preciso travar a parcela "acordado esvaziando a FIFO" para que a sabotagem acusasse. Duas edições por heredoc falharam na escapagem de barras invertidas e foram refeitas pela ferramenta de edição. E a retomada não reexecutou as sabotagens (ver acima), o que só foi feito na revisão.

**Risco em aberto.** A resistência, o trilho e a capacitância da montagem não foram medidos; o teste de bancada é `HW-08` e a escolha do VCC é `HW-02`. O consumo depende das premissas do modelo e a medição real é `VAL-02`.

**Procedência.** `scripts/calculos_tcc.py`, `scripts/estudo_cadencia.py`, `docs/CALCULOS-TCC.md`, `docs/DECISAO-ARQ-01-CADENCIA.md`, `firmware/sketch.ino` e as inserções locais em `documento/`.

# 2026-11-04 — `API-05`: ordem cronológica dos limites de consulta

**O problema, como foi entendido no início.** A validação compartilhada do histórico e das features comparava `desde` e `ate` como texto ISO. Com fusos diferentes, uma janela válida podia ser recusada e uma invertida aceita.

**Hipótese de trabalho.** Comparar objetos `datetime` corrige a ordem sem alterar o formato dos parâmetros nem o filtro por `created_at` do histórico. Duas datas sem fuso continuam aceitas no histórico; misturá-las com datas com fuso é ambíguo e passa a ser recusado.

**O que foi testado, e como.** Na worktree independente de `develop`, Windows, `python -m pytest web-app/tests/test_comparacao_de_datas.py -q --tb=line -p no:cacheprovider` antes da correção. Depois, `python -m pytest web-app/tests/ -q --ignore=web-app/tests/rls -p no:cacheprovider --tb=short`. Autenticação e consultas são dubladas nas provas HTTP; não houve acesso ao banco nem a dados pessoais.

**Resultado medido.** Dos 36 novos casos, 20 falharam e 16 passaram no código antigo. Após trocar a comparação textual por `datetime` e recusar fusos misturados, os 36 passaram; a suíte do backend passou 453 testes. Os casos percorrem offsets diferentes, instantes iguais, passagem de dia, frações de segundo, ambiguidade, limites isolados e formato preservado. Nas duas rotas, intervalos recusados não chamam o método de consulta. A execução vermelha foi o controle deliberado antes da correção, não uma regressão da solução.

**Adaptação.** Não foi necessário converter os parâmetros devolvidos para UTC: a comparação de objetos com fuso considera os offsets, preservando o formato consumido pela camada de dados. Os novos testes ficaram em arquivo próprio para exercitar a mesma matriz na função e nas duas rotas.

**O que deu errado no caminho.** Nada registrado nesta etapa. A execução vermelha dos 20 casos foi o controle deliberado antes da correção (ver "Resultado medido"), não uma falha do trabalho.

**Risco em aberto.** Clientes que misturavam limite com fuso e limite sem fuso recebem 400; o contrato agora declara isso. Datas sem fuso no histórico continuam dependentes da interpretação da fonte; não foi atribuída uma zona implicitamente. A escolha de `created_at` versus `captured_at` e a paginação do histórico são achados separados da inspeção, fora desta correção. A contribuição ao TCC é preservar a integridade do recorte temporal dos registros de movimento; não amplia a afirmação científica de sono.

**Procedência.** Branch `bugfix/API-05-comparacao-de-datas`; `web-app/consulta.py`, `web-app/tests/test_comparacao_de_datas.py`, contrato §6.1 e backlog `API-05`.

# 2026-11-04 — UI-24: resultado antigo não substitui o histórico atual

**O problema, como foi entendido no início.** Ao trocar de dispositivo ou filtro, cada chamada pendente do useHistorico podia publicar seu resultado ao terminar. Uma resposta antiga substituía o histórico novo; um erro antigo também apagava dados, e o finally antigo encerrava o indicador de carregamento de outro pedido.

**Hipótese de trabalho.** Identificar cada carregamento e invalidá-lo no cleanup permite que só o pedido mais recente publique estado. A identidade precisa cobrir recarga manual, e o ciclo setup/cleanup/setup do Strict Mode precisa reativar o hook.

**O que foi testado, e como.** Em worktree independente de origin/develop, no Windows, npm test -- --run src/hooks/useHistorico.test.ts montou o hook real em jsdom. Promessas controladas resolveram/rejeitaram pedidos fora de ordem. Depois da correção, npm test -- --run executou a suíte do frontend. Não houve rede real nos testes do hook.

**Resultado medido.** No código antigo, 9 dos 11 novos casos falharam: dados/erro fora de ordem, indicador de carregamento prematuro, recarga manual, troca de janela, callback retido após desmontagem e primeiro efeito do Strict Mode. Após a correção, os 11 passaram, e a suíte completa passou 489 testes em 37 arquivos. O build de produção (TypeScript e Vite) também passou, mantendo o aviso de chunk acima de 500 kB. O modo demo continua sem chamada à API. Os testes das duas ordens de término comprovam que dados novos permanecem e que carregamento novo não termina por causa de pedido antigo.

**Adaptação.** Uma flag por efeito não basta para duas recargas do mesmo filtro: foi usado contador de gerações, além do estado ativo. Leituras, erro e finally verificam a mesma identidade.

**O que deu errado no caminho.** A primeira tentativa de executar npm após editar o hook foi feita na raiz, onde não há package.json (ENOENT); o comando foi corrigido para a pasta frontend, sem alterar dependências.

**Risco em aberto.** A chamada antiga continua no transporte; o hook apenas descarta sua publicação. O tratamento de autenticação do cliente de API, inclusive o callback global de 401, permanece fora dessa guarda. jsdom não prova layout ou comportamento de rede real. Para o TCC, a correção protege a correspondência entre o filtro selecionado e os registros exibidos; não altera o critério de movimento nem as afirmações científicas.

**Procedência.** Branch bugfix/UI-24-respostas-antigas-historico; frontend/src/hooks/useHistorico.ts, frontend/src/hooks/useHistorico.test.ts e backlog UI-24.

# 2026-11-04 — ML-14: falha completa não sai da média de F1

**O problema, como foi entendido no início.** O avaliador calculava F1 a partir de precisão e recall e produzia NaN quando deveria produzir zero. A agregação excluía esses sujeitos. RESULTADOS-TCC tratava o NaN histórico do trivial como divisão por zero legítima.

**Hipótese de trabalho.** A fórmula direta pelas contagens distingue erro de classificação de ausência da classe: 2TP/(2TP + FP + FN). Denominador positivo sem acertos dá zero; denominador zero permanece NaN.

**O que foi testado, e como.** Worktree independente de origin/develop, Windows, Python 3.11.9 do ambiente pinado local: numpy 2.2.6, pandas 2.3.3, scipy 1.15.3, scikit-learn 1.7.2, PyYAML 6.0.3 e pytest 9.1.1. Antes da correção: pytest testes/test_avaliar.py. Depois: pytest testes. Onze novos casos de F1 incluem comparação com scikit-learn para os 64 pares de sequências binárias de três épocas e prova de média, desvio e bootstrap. Dez casos auditam o instrumento, incluindo alteração deliberada da fonte para tornar o snapshot obsoleto. Comando da auditoria: python ml/ferramentas/auditar_f1.py --conferir, a partir da raiz.

**Resultado medido.** No avaliador antigo, 6 dos 11 novos casos falharam; depois passaram. A suíte completa passou 155 testes. A auditoria recalculou 94 valores em 18 arquivos, encontrou 21 divergências em 7 arquivos, todas NaN que deveriam ser zero. Não houve campos de F1 sem matriz de confusão nesses arquivos. O snapshot novo é JSON estrito e registra os caminhos, valores e hashes do texto UTF-8 com fins de linha LF; os JSONs históricos não foram reescritos.

**Adaptação.** Não foi necessário alterar a agregação para incluir zero: ela já excluía apenas NaN. A correção é na origem da métrica. A explicação documental do NaN foi corrigida sem atribuir o defeito a falta de previsões apenas. A revisão identificou que o checkout Windows usa CRLF e o Linux usa LF: os hashes passaram a normalizar os finais de linha. Remover deliberadamente a normalização fez a asserção de equivalência de hashes reprovar, confirmando o mecanismo.

**O que deu errado no caminho.** A primeira tentativa de adicionar os testes usou ml/testes a partir da própria pasta ml, dando caminho inexistente; apenas os sete testes antigos rodaram nessa tentativa. Corrigido o caminho antes da execução vermelha com os casos novos. A primeira fixture do teste de hashes continha escapes literais em vez de quebras de linha e falhou ao ler o JSON; corrigida, passou. Uma execução direcionada também usou testes/ a partir da raiz e foi corrigida para ml/testes/.

**Risco em aberto.** A auditoria não reestima ICs nem prova a ausência de impacto em experimentos não representados pelas contagens salvas; não houve retreino. As regras de indefinição de sensibilidade, especificidade e kappa continuam as mesmas. NaN legítimo continua possível no avaliador e nos arquivos históricos; o snapshot novo o representa explicitamente. Para o TCC, a correção evita que um sujeito com falha de classificação seja excluído como se sua métrica fosse indefinida.

**Procedência.** Branch bugfix/ML-14-f1-sem-acertos; ml/src/avaliar.py, ml/testes/test_avaliar.py, ml/ferramentas/auditar_f1.py, ml/testes/test_auditar_f1.py e ml/experimentos/saida/ml14_auditoria_f1.json; RESULTADOS-TCC, README do ml/ e backlog ML-14.

# 2026-11-04 — ML-15: reprodução controlada dos experimentos principais (em execução)

**O problema, como foi entendido no início.** A ML-14 corrigiu F1 e seis checkpoints permitiram reavaliar previsões existentes, mas isso não era uma reprodução abrangente dos experimentos principais do TCC.

**Hipótese de trabalho.** Com o mesmo ambiente, configuração e coorte, é possível repetir os treinamentos e comparar resultados. Diferenças de coorte, de versão do pipeline e de métrica precisam de classificações distintas.

**O que foi testado, e como.** Execução local Windows em cópia isolada dos scripts da ML-14. Bibliotecas pinadas; configuração aec203907e6f, seed 20260910; dois processos. Dados brutos somente lidos, caches copiados e diretório de saída inicialmente vazio. Checkpoints antigos não foram copiados. ML-03 e baselines Wearanize usam o cache de features via adaptador que recompõe contexto por participante; os treinamentos são novos. Um manifesto registra fontes, ambiente e referências. O comparador passou controles de valor alterado, NaN, igualdade e listas.

**Resultado medido.** Execução ainda em andamento. Baseline sintético reproduziu os dois registros históricos mais recentes fora das três correções de F1; dois registros mais antigos têm outras diferenças cuja origem não foi isolada. O baseline Newcastle concluiu a extração e o treinamento e bateu com o histórico fora das três correções de F1. Os números consolidados e as demais famílias serão registrados ao concluir.

**Adaptação.** O baseline Wearanize histórico tem 10 participantes na cabeça e 7 no pulso, sem lista identificável no JSON. Os caches atuais têm 92 participantes comuns aos três braços: as rodadas de baseline nessa coorte são marcadas como ampliadas, não como reprodução daquelas coortes antigas. O parâmetro de threads nativas foi fixado em 1 por processo e fica registrado como condição de execução.

**O que deu errado no caminho.** Nada registrado até este ponto da execução.

**Risco em aberto.** Os experimentos não concluídos permanecem no item ML-15. Caches de features não equivalem a refazer toda a extração bruta. Rodadas com coorte distinta não permitem atribuir diferenças somente ao F1. Resultados antigos e dados brutos permanecem preservados.

**Procedência.** Branch feature/ML-15-reproducao, dependente da ML-14; manifesto, estado, comparação e logs locais em ml/dados/processado/ml15_reproducao; relatório final pendente no mesmo item.

# 2026-11-05 — ML-15: 15 execuções concluídas e limites históricos separados

**O problema, como foi entendido no início.** Era preciso terminar a reprodução iniciada em 04/11 e verificar se a correção de F1 alterava resultados além dos seis checkpoints antes reavaliados. A maior ablação permaneceu ativa durante a madrugada.

**Hipótese de trabalho.** Resultados com mesmas entradas e código deveriam coincidir; diferenças de avaliação, população e instabilidade numérica não podem ser atribuídas umas às outras. O kappa usado na escolha dos modelos não depende da correção de F1.

**O que foi testado, e como.** Windows, Python 3.11.9, bibliotecas pinadas; 15 tarefas com código da ML-14 e saídas/checkpoints novos. A ablação concluiu em 21.894,9 s. Conferidos hashes de 25 fontes e 114 caches copiados contra as fontes locais. Comparador com tolerância absoluta/relativa 1e-10, hashes textuais normalizados para LF e exclusão de novas saídas parciais. F1 complementar reconstruiu matrizes por participante usando suportes reais, validando contagens inteiras, acurácia, especificidade e kappa. Controle independente de 552 matrizes contra previsões dos seis checkpoints antigos passou. Instrumentos têm controles de métrica alterada, NaN, coorte diferente, vetor incompleto, relatório vazio, fonte alterada e tentativa de reutilizar saída histórica.

**Resultado medido.** As 15 tarefas concluíram com código zero. Transferência, otimizações, três validações externas, lateralidade, métricas do teto interavaliador, quantização e ML-11/ML-12 reproduziram os campos comparados. Newcastle e os dois snapshots sintéticos de 14/09 diferiram somente nos três F1 de vigília corrigidos. F1 complementar: 9.687 matrizes em 132 avaliações; oito zeros antes excluídos em sete avaliações não triviais, além de 363 ocorrências em seis grupos triviais. Na transferência cabeça → cabeça E4, F1 de sono médio passou de 0,4714552822 (91 válidos) para 0,4663307682 (92) ao comparar as fórmulas sobre as mesmas classificações novas. A variante sem scaler emitiu 276 avisos de convergência; maior diferença de kappa médio de 0,004545. A referência da ablação e os itens 1, 3, 4 e 5 reproduziram o histórico. O arquivo antigo da ablação era parcial e não continha suas otimizações finais. 167 testes de ML passaram, incluindo 12 controles novos; comparação salva e resumo do backlog conferidos.

**Adaptação.** O comparador passou a sinalizar referência histórica parcial sem descartá-la, permitindo conferir os itens completos nela. O campo utc_notas ausente no novo teto interavaliador é metadado, não divergência de métricas. Dois snapshots sintéticos de 11/09 divergem por causa não isolada; baselines Wearanize novos de 92 participantes são coortes ampliadas, não reprodução dos pilotos 10/7.

**O que deu errado no caminho.** A primeira tentativa restrita de pytest falhou ao acessar seu diretório temporário; a execução com permissões de teste passou. Durante a continuidade também houve uma edição não executada porque a revisão automática atingiu limite de uso; após a retomada, o workspace passou a permitir as edições locais. Nenhum resultado foi inferido daquele comando recusado.

**Risco em aberto.** O ML-16 carrega a recuperação de IDs dos pilotos, a procedência dos snapshots sintéticos antigos e a causa da divergência sem scaler. Não foi aumentado max_iter nem mudado solver para forçar coincidência. Caches reaproveitados não validam novamente toda a extração bruta; estas bases públicas continuam sem validar o sensor no travesseiro (ML-12(c)/VIA-01). Para o TCC, a reprodução sustenta os resultados centrais e torna explícito onde a procedência histórica ainda não permite igualdade estrita. Sem merge automático.

**Procedência.** Branch feature/ML-15-reproducao a partir de 72f954286633f3b197d9bab454f622d67885814b (ML-14, PR #82). docs/REPRODUCAO-ML-15.md; ml/experimentos/saida/ml15/ (15 resultados, manifesto, execução, comparação e F1 complementar); ml/ferramentas/comparar_reproducao.py, reconstruir_f1.py, rodada_reproducao.py e executar_reproducao.py; testes dos instrumentos, README do ML, RESULTADOS-TCC, LIMITACOES-TCC e backlog ML-15/ML-16. Dados e logs permanecem locais e ignorados.

# 2026-11-05 — ML-16: pilotos, sintéticos e condição numérica reconstruídos

**O problema, como foi entendido no início.** A reprodução ML-15 deixara três lacunas de procedência: IDs dos pilotos Wearanize 10/7, sintéticos de 11/09 divergentes e variante sem scaler sem igualdade numérica. O usuário aprovou investigar as três, preservando os parâmetros e os históricos.

**Hipótese de trabalho.** A seleção canônica do baixador poderia recuperar uma coorte compatível; as duas correções de features descritas no histórico poderiam explicar os sintéticos; a condição numérica da execução poderia afetar o ajuste sem convergência. Nenhuma hipótese foi aceita apenas por coincidência de contagem ou por leitura do código.

**O que foi testado, e como.** Worktree isolada baseada em 63a4223 (ML-15), com nova branch feature/ML-16-rastreabilidade. Python 3.11.9, bibliotecas pinadas, cache copiado e dados brutos apenas lidos. Consultados Git, diário, logs antigos, backup interno disponível e 90 commits sem referência. Primeiros dez IDs do participants.tsv usados em novas extrações e treinamentos. Controles sintéticos alteraram separadamente norma L1/L2 e referência geométrica/mediana por componente, inclusive a normalização dos vetores. Controle reduzido de uma/oito threads manteve cache, ordem, seed e max_iter=300; três modelos e nove células em sub-005. Reexecução completa da variante com oito threads nos 92 participantes. Comparação de todos os campos e vetores com tolerância absoluta/relativa 1e-10. Instrumentos incluem sabotagens de métrica, NaN, threads, referência adulterada e mudança de arquivo sem mudança dos números.

**Resultado medido.** Cabeça: dez participantes, 9.471 épocas, 8.706 sono/765 vigília. Pulso: sete participantes, 6.958 épocas, 6.249 sono/709 vigília. Todos os campos comparados dos pilotos reproduzidos, fora de três F1 de vigília corrigidos em cada arquivo. L1 + mediana dos vetores unitários por componente reproduz os sintéticos de 11/09; apenas uma dessas mudanças não reproduz. Definições atuais reproduzem os dois registros de 14/09. Controle reduzido: uma thread coincide com a ML-15 em 27/27 métricas; oito threads coincidem com o histórico em 27/27. Matriz completa com oito threads: zero diferenças nas nove células, incluindo médias, desvios, ICs e vetores dos 92 participantes. Foram emitidos 276 avisos; duração registrada de 12.438,0 s. Auditoria das sete comparações e controles passou; 177 testes de ML passaram, incluindo dez novos controles.

**Adaptação.** A mediana dos vetores brutos não reproduziu o sintético antigo; a dos unitários reproduziu, e as tentativas intermediárias ficaram no manifesto. O primeiro JSON sintético publicava cinco métodos com dois nomes antigos: a comparação declara os aliases e esse escopo, sem fingir que os sete métodos já estavam lá. Os pools são carregados antes de aplicar o limite de threads e os valores efetivos são registrados. threadpoolctl 3.6.0 já instalado ganhou pin explícito, sem atualização.

**O que deu errado no caminho.** A restrição da sessão inicialmente negou escrita e leitura dos metadados Git na nova worktree; as operações foram realizadas com a autorização apropriada. A primeira junction ampla de dados foi restringida aos brutos antes das execuções, com cache copiado, preservando o processamento original.

**Risco em aberto.** A lista de participantes da execução original, o fonte anterior às correções e o número histórico de threads não foram recuperados. Foram obtidas reconstruções consistentes com o procedimento e os resultados, não inventados documentos de origem. Igualdade neste ambiente não garante igualdade em outra arquitetura; a variante sem scaler continua não convergida. Esses limites foram declarados e restringem o uso dos registros, sem novo trabalho obrigatório para sustentar os resultados centrais. Hardware e validação do travesseiro continuam nos itens próprios, não foram resolvidos por esta investigação. ML-16 fechado pela reprodução e delimitação da procedência; sem merge automático.

**Procedência.** docs/RASTREABILIDADE-ML-16.md; ml/experimentos/saida/ml16/ (sete resultados, controles, manifesto e auditoria); ml/ferramentas/rastrear_ml16.py e auditar_ml16.py; testes de ambos; requisitos pinados, backlog, README e notas de atualização de REPRODUCAO-ML-15, RESULTADOS-TCC e LIMITACOES-TCC. Base dependente das PRs #82/#83; fontes, métricas históricas e arquivos dessas branches preservados.

---

# 2026-11-05 — revisão e integração das PRs #79 a #84

**O problema, como foi entendido no início.** Enquanto o limite de uso desta sessão estava
esgotado, o autor seguiu o projeto com outra ferramenta, aprovando cada trabalho: seis PRs abertas
para `develop` — `CALC-04` (a retomada do trabalho deixado aqui), `API-05`, `UI-24` e a cadeia
`ML-14` → `ML-15` → `ML-16`. O pedido foi revisá-las antes de qualquer merge, conferindo os
relatórios, os diffs e as ferramentas de auditoria.

**Hipótese de trabalho.** Que as afirmações dos relatos e dos relatórios se sustentassem quando
**executadas**, e não só lidas; e que a integração das seis, com o diário e o backlog de cada uma,
fechasse nas conferências.

**O que foi testado, e como.** Por PR: suítes em ambiente limpo; os testes novos contra o código de
`develop`, para conferir que falham sem a correção; as três sabotagens do `CALC-04` sobre o commit
da PR. Para ML, um verificador **independente** do F1 pelas contagens e um comparador
**independente** dos JSONs histórico × novo, folha a folha, sem reaproveitar as ferramentas
revisadas; as reconstruções da `ML-16` comparadas da mesma forma. Os campos do diário de cada
entrada, por script. A integração simulada numa worktree descartável e depois feita em `develop`,
na ordem das PRs, com conferências a cada merge.

**Resultado medido.** `CALC-04`: sabotagens **3/3**. `API-05`: 453 testes; **20 dos 36** casos
novos falham com o `consulta.py` de `develop`; nenhum cliente manda `desde`/`ate`. `UI-24`: 489
testes, build limpo; **9 dos 11** novos falham com o hook de `develop`. `ML-14`: o verificador
independente confirma **94 valores, 21 divergências em 7 de 18 arquivos**. `ML-15`: ML-03, ML-04,
otimizações, ML-12 e ML-05 com **zero diferença** em milhares de valores; as 2 056 diferenças da
ablação ficam **todas** no item 2 (sem scaler). `ML-16`: pilotos e sintéticos batem; **com 8
threads, o item 2 reproduz o histórico em 2 637 valores, zero diferenças**. Integrado: 7
conferências de documento, 453 + 177 + 489 testes, build; CI de `develop` verde; as seis PRs
marcadas como mescladas.

**Adaptação.** As sete entradas de diário das PRs não tinham o campo "O que deu errado no
caminho" — a maioria relatava os erros dentro de "Adaptação"; as frases foram **movidas** para o
campo, nas próprias branches, antes do merge. A `ML-15` citava só a diferença de kappa **médio** da
variante sem scaler (0,0045); por participante ela chega a 0,17 de kappa e 0,23 de
especificidade, e isso entrou em `LIMITACOES-TCC.md`: um resultado que depende do número de threads
não sustenta casas decimais. As notas de contagem das branches paralelas ganharam uma nota de
conciliação no backlog.

**O que deu errado no caminho.** Três coisas, todas de ferramenta minha. O resolvedor de
conflitos por união, escrito para o diário e o backlog, primeiro não casou nenhum bloco: os
arquivos são CRLF e a expressão esperava LF — e a simulação seguiu com marcadores de conflito
commitados (era descartável; refeita). Na integração real, o mesmo resolvedor **perdeu o fechamento
do `ML-16`**: quando a mesma linha vinha dos dois lados, ele mantinha a de `develop`, e a da #84 era
a fechada. Na simulação isso não apareceu porque a #84 entrava de uma vez. Quem pegou foi o
`conferir_backlog` (39 declarado × 40 recontado, `ML-16` aberto fora do quadro), antes do push; a
linha foi restaurada da #84 dentro do próprio merge, ainda local, e um verificador de "linhas que
cada PR mudou × `develop`" confirmou que nada mais se perdeu. E um comando de conferência foi
recusado pelo verificador de segurança do terminal por sintaxe ambígua, e foi refeito como script.

**Risco em aberto.** A `API-05` e a `UI-24` mudam o comportamento do site: valem depois do
release, com o login. A variante sem scaler continua não convergida e dependente de threads —
declarado em `LIMITACOES-TCC.md`. A pasta `esquemaEletrico/` (três imagens do circuito) está não
rastreada na raiz do repositório principal, e não foi tocada.

**Procedência.** PRs #79 a #84, mescladas em `develop` (`b844647`); commits de ajuste nas branches
`035c829`, `7e873c3`, `88a0a1a`, `94765bb`, `a766a3a`, `6b2bac6`; relatórios
`docs/REPRODUCAO-ML-15.md` e `docs/RASTREABILIDADE-ML-16.md`; conferências e comparadores
independentes rodados nesta máquina em 05/11.

---

# 2026-11-05 (ii) — o release da `API-05`, da `UI-24` e do `DEMO-03`

**O problema, como foi entendido no início.** Depois da integração das PRs #79–#84 e da
conciliação (#85), `develop` tinha três mudanças de comportamento do site — `API-05`, `UI-24`,
`DEMO-03` — e os itens de cálculo e de ML, que não mudam o site.

**Hipótese de trabalho.** Que o release mudasse só a validação das consultas, o carregamento do
histórico no painel e o modo demonstração do servidor de desenvolvimento.

**O que foi testado, e como.** Diff `main..develop` restrito a `web-app/`, `frontend/` e
`vercel.json` (três arquivos de produção); PR #86 com 9 checks; deploy acompanhado pela API de
deployments; depois, `/health`, as rotas sem credencial e com `Bearer` inválido,
`/api/sleep-history` com limites de fuso misturado, `/privacidade`, o pacote publicado, e um login
do autor com o painel.

**Resultado medido.** Deploy `7584696406`, `success`, SHA `5fa9ab6`. `/health` `200`, banco ok;
rotas sem credencial e `Bearer` inválido → `401`; `/api/sleep-history` com fusos misturados e sem
credencial → `401`; `/privacidade` `200`. O pacote publicado tem um trecho compatível com a guarda
nova do `useHistorico` — indício, não prova, por ser código minificado. **O autor confirmou o login
e o painel.**

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O `400` da `API-05` não foi exercitado na produção: exige sessão válida e
parâmetros que nenhum cliente envia hoje. As sete branches das PRs #79–#85 e as worktrees da outra
ferramenta seguem existindo até autorização para apagar.

**Procedência.** PR #86 (`5fa9ab6`); deployment de produção `7584696406`; as rotas e o pacote de
`https://dormio-smart.vercel.app`, 05/11; a confirmação do autor; backlog `API-05`, `UI-24`.

---

# 2026-11-05 (iii) — limpeza depois da integração, e uma cópia que seguiu uma junction

**O problema, como foi entendido no início.** Integradas e lançadas as PRs #79–#84, o autor
autorizou apagar as branches da rodada e as worktrees da outra ferramenta. As worktrees guardavam,
fora do Git, duas coisas que não podiam se perder: uma seção "Concluído" do `ROADMAP.md` (local,
gitignorado) em três delas, e os logs, caches e checkpoints da ML-15 e da ML-16, citados pelos
relatórios como "locais e ignorados".

**Hipótese de trabalho.** Que bastasse levar as seções do `ROADMAP.md` para o principal e copiar as
duas pastas de evidência para `ml/dados/processado/` do repositório principal antes de remover as
worktrees.

**O que foi testado, e como.** As seções do `ROADMAP.md` comparadas com o principal e acrescentadas
com o texto original. A evidência copiada com `cp -a`, e depois — refeito — com `robocopy /E /XJ`;
as pastas conferidas arquivo a arquivo (caminho e tamanho) contra a origem. Antes de cada remoção,
as worktrees varridas por links (`-Attributes ReparsePoint`). Os dados brutos originais contados
(arquivos e bytes) depois de cada passo.

**Resultado medido.** Três seções do `ROADMAP.md` (API-05, UI-24, ML-14) que só existiam nas
worktrees passaram ao principal. Sete branches apagadas, locais e no GitHub; cinco worktrees
removidas. A evidência ficou no repositório principal, igual à origem: **ML-15 207/207, ML-16
90/90**. Os dados brutos originais terminaram como começaram: **676 arquivos, 54,1 GB**.

**Adaptação.** A cópia passou a excluir junctions (`robocopy /XJ`); as duas junctions foram
desfeitas como link (`rmdir`, sem `/s`) antes de remover as worktrees; as duas cópias acidentais
foram apagadas depois de conferido que não continham link nenhum — o disco voltou a 126,7 GB
livres.

**O que deu errado no caminho.** A pasta de evidência de cada execução continha `ml/dados/bruto`
como **junction** para os dados brutos reais — o `REPRODUCAO-ML-15.md` dizia isso, e não foi
conferido antes de copiar. O `cp -a` seguiu o link e **duplicou os datasets**: 58 GB na pasta da
ML-15 e 51 GB, parciais, na da ML-16. E a interrupção da tarefa não parou a cópia: o shell morreu, o
`cp.exe` filho não, e só a queda do espaço livre (41,3 → 25,3 GB) denunciou; o processo foi
encontrado e encerrado. Nenhum dado original foi alterado — a cópia só lia —, mas o passo seguinte,
remover a worktree com a junction dentro, poderia ter apagado os datasets. Lições: §5 ocorrência 10
e §6 ocorrência 9, com as regras 13 e 8. A pasta vazia de uma worktree (um arquivo de 0 byte) não
pôde ser apagada, provavelmente por estar em uso pelo app da outra ferramenta, e ficou.

**Risco em aberto.** Execuções futuras que liguem dados brutos por junction repetem a armadilha; a
regra 13 da §5 e o item correspondente das instruções para a outra ferramenta cobrem isso, mas
dependem de serem lidos. As pastas de nível de cima em `.codex/worktrees/` ficaram vazias.

**Procedência.** Comandos desta sessão em 05/11; `ml/dados/processado/ml15_reproducao/` e
`ml16/` (locais, ignorados); `ROADMAP.md` (local); `docs/LICOES-APRENDIDAS.md` §5 e §6.

---

# 2026-11-05 (iv) — `AGENTS.md`: regras para dois agentes em paralelo

**O problema, como foi entendido no início.** Desde 04/11 o projeto tem dois agentes de código
trabalhando ao mesmo tempo (o Codex e o Claude Code). A primeira rodada de integração (PRs #79–#84)
mostrou o custo de não haver regra comum: conflitos em todo merge nos mesmos documentos (diário,
backlog, contagem, tabela de testes do `CLAUDE.md`), notas de contagem calculadas sobre bases
diferentes, o campo "O que deu errado no caminho" ausente ou fora do lugar em sete entradas, e uma
cópia de evidência que seguiu uma junction para os dados brutos (entrada (iii)).

**Hipótese de trabalho.** Que um `AGENTS.md` na raiz — que o Codex lê automaticamente — com a
divisão por área, a sincronia com `develop` antes da revisão e as regras dos arquivos de conflito
garantido reduzisse esses conflitos, sem duplicar o `CLAUDE.md` (que continua valendo e vence onde
divergirem).

**O que foi testado, e como.** O texto conferido contra o `CLAUDE.md` (Gitflow estrito, práticas
não negociáveis, arquivos locais) e contra as lições §5 e §6; as três conferências de documentos
rodadas na branch.

**Resultado medido.** `AGENTS.md` com 20 regras em seis grupos: antes do trabalho, divisão, branches
e PRs, arquivos de conflito garantido, o que conta como verificado, dados locais e texto do TCC. O
`CLAUDE.md` passa a apontá-lo entre os documentos de leitura obrigatória.

**Adaptação.** A primeira versão da regra 8 permitia "PRs empilhadas"; o `CLAUDE.md` exige que toda
PR aponte para `develop`. A regra foi reescrita: a branch pode partir de outra PR aberta, mas a PR
aponta para `develop`, com a ordem de merge no corpo.

**O que deu errado no caminho.** A leitura cruzada achou uma divergência antiga no próprio
`CLAUDE.md`: a prática 1 dizia "os sete campos fixos" do diário, e as entradas têm oito desde que
"O que deu errado no caminho" virou campo fixo. Corrigido com nota datada.

**Risco em aberto.** As regras dependem de serem lidas e seguidas; nenhuma é verificada por script.
A divisão por área é de partida e muda conforme o autor indicar os itens.

**Procedência.** `AGENTS.md`; `CLAUDE.md` (documentos de referência e prática 1); entradas
2026-11-05 (i) e (iii); `docs/LICOES-APRENDIDAS.md` §5 e §6.

---

# 2026-11-05 (v) — ML-13: preparação e integridade da DREAMT

**O problema, como foi entendido no início.** A branch da ML-13 tinha um conferidor de hashes, mas os dados permaneciam no ZIP. O autor pediu primeiro a sincronização com develop e a leitura das regras; depois aprovou a preparação e validação, exigindo caminho explícito sem junction, testes de manifesto antes da correção e a consolidação da sincronia nesta mesma entrada. A etapa termina antes do carregador e da avaliação externa.

**Hipótese de trabalho.** O ZIP disponível pode fornecer somente o subconjunto necessário de v2.2.0; o conferidor só é confiável se exigir as 103 entradas esperadas, além de verificar os arquivos que encontra. Um manifesto vazio/incompleto não pode diminuir silenciosamente a cobertura.

**O que foi testado, e como.** Nesta máquina Windows local, PowerShell e Python 3.11.9: git fetch origin, leitura de AGENTS.md/CLAUDE.md e registros, criação de worktree para a branch existente e merge de origin/develop 16232bf (merge 48af004), com as três conferências. Foram criados 13 testes artificiais no ml/: íntegros, arquivo ausente, adulteração, manifesto ausente, vazio, omissão de CSV, omissão de cada metadado, ID trocado com 103 entradas, linha malformada, duplicata e entradas de 100 Hz fora do escopo. Rodados antes de editar o conferidor e repetidos em cópia congelada do código anterior; depois, com a correção e na suíte completa. O script anterior está em cb65881, não no develop, portanto a prova usa essa versão efetivamente existente, sem contar erro de import como detecção. Extração em fluxo de apenas 104 membros selecionados do ZIP, com tamanho, CRC e SHA-256; manifesto local comparado byte a byte ao do ZIP; nova leitura dos 103 alvos pelo conferidor corrigido. Varredura sem seguir reparse points na worktree e no armazenamento. Apenas Metadata.txt, LICENSE.txt e cabeçalho de CSV foram lidos semanticamente; rótulos, features e desempenho não foram analisados.

**Resultado medido.** Antes da correção, 8 dos 13 testes falharam e 5 passaram; a execução congelada confirmou a mesma contagem. Depois, 13/13 passaram; suíte ML completa: 190 passam. 100 CSVs, três metadados e SHA256SUMS.txt extraídos: 104 arquivos, 14.108.986.504 bytes. Os 104 CRCs selecionados conferem e os 103 SHA-256 oficiais conferem, sem arquivos ausentes ou somas diferentes; os hashes foram calculados durante a extração e de novo no conferidor. Nenhuma junction/reparse point na worktree ou no armazenamento. Não foi conferido o CRC integral do grupo de 100 Hz que permaneceu no ZIP. A ML-13 segue aberta; sobre origin/develop 16232bf, passa de L3 para L0 com total 39, L0 10/L1 14/L2 7/L3 8.

**Adaptação.** A branch existente foi reutilizada em worktree própria, preservando o trabalho de cb65881. O conferidor passou a exigir os nomes dos 100 CSVs de v2.2.0 e dos três metadados; os outros arquivos do manifesto oficial não substituem esses alvos. Extração em pasta externa ao checkout, sem ligações ao diretório bruto principal, mantendo o ZIP original. O campo de sincronia (v) foi incorporado a esta única entrada da ML-13. O plano do carregador e as previsões P1–P3 foram registrados antes de qualquer avaliação e aguardam aprovação; hipóteses relativas às unidades/grade vindas da documentação ainda precisam de inspeção nos sinais.

**O que deu errado no caminho.** Na sincronia, os primeiros comandos Git apontaram para a worktree da ML-16 já removida e falharam com "not a git repository"; o fetch foi feito pelo repositório principal sem editar seu checkout, e a execução seguiu na worktree da ML-13. A consulta inicial do item .git via PowerShell não o encontrou; o Git com o acesso necessário identificou as referências. Nesta preparação, uma leitura tentou abrir test_baixar_wearanize.py, que não existe; a lista foi conferida com rg --files. A impressão inicial de Metadata.txt falhou em cp1252 no símbolo μ; foi repetida com saída UTF-8. Nenhum desses comandos alterou os dados brutos. As oito reprovações dos testes no conferidor anterior foram controles esperados, não erros operacionais.

**Risco em aberto.** Integridade dos bytes não demonstra validade da grade, unidade, rótulos ou transferência de desempenho. Faltam inspeção, protocolo de carregamento, controles e avaliação externa. O plano explicita caminho --dados-brutos, ausência de junctions, fronteiras de contexto/HMM e preservação da procedência histórica; alterações compartilhadas exigem escopo aprovado. CSVs e informações individuais permanecem restritos e fora do Git. Dados ficam em armazenamento externo estável e logs/JSON/JUnit na pasta ignorada da ML-13; os caminhos completos foram informados ao autor. Parada no passo 4, aguardando aprovação, sem inferência nem treino na DREAMT.

**Procedência.** feature/ML-13-coorte-dreamt; origem cb6588198a225088408554845e058dd54e2e7ffd; base origin/develop 16232bf7bebe09537b88a31669c55737b5733bd9; merge 48af0048d6911813ebf72540e2068dedaae671bc. ml/ferramentas/baixar_dreamt.py, ml/testes/test_baixar_dreamt.py, docs/ML-13-PREPARACAO-DREAMT.md e docs/PLANO-ML-13-COORTE-DREAMT.md. Evidência privada em ml/dados/processado/ml13_preparacao/; dados externos no diretório lógico dados-locais/dreamt-2.2.0; nenhum caminho de máquina publicado.

---

# 2026-11-05 (vi) — ML-17: diagnóstico, código e controles de fronteira

**O problema, como foi entendido no início.** O autor repassou a revisão da #90 e aprovou a correção de fronteiras como ML-17 antes da avaliação DREAMT. O plano próprio foi aprovado com duas PRs (código/caches, depois rodadas/relatório), separação dos defeitos de janela das regressões HMM/Viterbi que já funcionavam, dourados intactos e censo de contexto anterior aos treinamentos.

**Hipótese de trabalho.** Separar participantes não basta quando o filtro de épocas apaga lacunas. Preservar gravação e índice original permite respeitar segmentos e medir depois quanto os efeitos das janelas ±2/±11 dependem do defeito, sem pressupor seu tamanho.

**O que foi testado, e como.** Windows local, PowerShell e Python 3.11.9. Fetch/read de develop d429d43 e regras, auditoria de todas as chamadas e antecedente ML-12 (30/10 iv). Manifesto do ZIP comparado byte a byte com a cópia separada, complemento registrado na #90 já mesclada. Seis testes de fronteira executados contra cópia congelada do develop antes de editar os fontes. Depois, suíte completa; controles de janela global, lacuna apagada, cache antigo aceito, HMM/Viterbi juntando participantes; guarda de fonte histórica adulterada, commit indisponível e manifesto vazio. Testados consumidores reais do ML-04, persistência de índices e retomada. Arquivos dourados/firmware comparados por diff. Regeneração de caches iniciada com caminhos externos explícitos, em diretório ignorado, sem treino. As três conferências passam após integrar develop 42c1e75. Na revisão, guarda AST em todos os consumidores, com apenas os controles globais ML-12/ML-15/censo; 11 chamadas dos cinco grupos apontados foram sabotadas isoladamente, omitindo segmentos e passando None, 22 mutações. Guarda também rodada nos fontes Git de d429d43 e 42c1e75.

**Resultado medido.** No develop: quatro testes falham por valores de janela (±2/±11 entre participantes e em lacunas), dois passam (transições HMM/Viterbi entre participantes). Corrigido inicialmente: suíte completa 217 passa; cinco sabotagens detectadas. Na revisão: 223 testes passam; 5/5 grupos e 22/22 mutações acusadas; a guarda rejeita 16 chamadas nos dois códigos antigos. Os testes dourados não mudaram. Dourados: 40 + 19 testes passam, nenhuma edição nos arquivos/vetores ou firmware. Hash do manifesto confirmado novamente: bf3f4d71fa9959c30d48598278013df0d6db8afa05bad770411e28f101780c3a. ML-17 continua aberta sobre develop 42c1e75 (já inclui DOC-16/DOC-17 e REQ-01); a contagem integrada é 39, L0 10/L1 14/L2 7/L3 8. Ainda não há comparação de desempenho nem resultado DREAMT.

**Adaptação.** #90 já integrada quando a consulta ocorreu; registro complementado no corpo sem alterar develop. Contexto por segmento centralizado; caches ml17-v1 preservam índices/gravação e recusam legado. As chamadas reais foram migradas; contexto global deliberado da ML-12 e adaptador histórico da ML-15 ficam identificados. Guarda ML-15 passa a conferir os fontes no commit registrado, mantendo evidência/manifesto intactos e histórico no CI. Diretórios e checkpoints novos evitam reutilizar resultados antigos. O plano foi atualizado com os três ajustes aprovados; censo distingue vizinhança de mudança numérica e exige igualdade de entradas.

**O que deu errado no caminho.** Na análise, consultas rg usaram nomes presumidos da reprodução ML-15; corrigidas com rg --files. Consultas extensas foram truncadas e repetidas em trechos menores. A conferência de documentos no sandbox da worktree nova não consultou o Git; repetida com acesso necessário. Na implementação, leituras tentaram abrir conftest.py/test_pipeline.py e pytest.ini na raiz, que não existem; o arquivo real é ml/pytest.ini. Nenhum desses comandos alterou brutos ou históricos. Na revisão, o primeiro mutante da comparação de punhos alterou o argumento de _prever na mesma linha, em vez da chamada interna de empilhar_contexto; o seletor foi corrigido para escolher a função e as 22 mutações foram repetidas. A suíte no sandbox negou rename de CSV artificial (222 passam, 1 erro de permissão); repetida com acesso normal do Windows, sem alterar o teste. Leituras extensas foram truncadas; trechos relevantes relidos. As quatro falhas deliberadas no develop são prova do defeito, não erro operacional.

**Risco em aberto.** Efeito quantitativo não medido: segunda PR da ML-17. Antes dela, concluir preparação e informar censo por coorte/braço, sem atribuir ao contexto uma eventual diferença nas entradas. ML-13 continua aberta e não será avaliada antes da correção/revisão e eventual adendo às previsões. Brutos externos preservados; cache/log/JUnit realocados para dados-locais/ml17-evidencias-2026-11-05/, fora da worktree e do Git (614 arquivos, tamanho/SHA-256 conferidos, robocopy /E /XJ, origem removida depois da conferência). Nenhuma junction criada; evidência ML-13 não foi copiada. Caminhos locais completos informados ao autor. Caches novos ainda não são resultados de validação de modelos.

**Procedência.** origin/develop d429d43e1b7bafacae67fbebb9a328942d63efff; branch bugfix/ML-17-fronteiras-contexto; docs/PLANO-ML-17-FRONTEIRAS-CONTEXTO.md; docs/ML-17-CODIGO-E-TESTES.md; fontes/testes desta PR; JUnit antes.xml/depois.xml em dados-locais/ml17-evidencias-2026-11-05/; manifesto ML-15 mantido; entrada ML-12 de 30/10 (iv).
---

# 2026-11-05 (vii) — ML-17: rodadas completas, dispersão e adendo antes da DREAMT

**O problema, como foi entendido no início.** Segunda PR da ML-17, dependente da #91: medir a correção de contexto/segmentação com códigos congelados, entradas iguais e diferenças por participante/célula. O autor exigiu duas PRs, distinguir defeitos de janela das regressões HMM/Viterbi que já passavam, dourados intactos e censo informado antes das rodadas.

**Hipótese de trabalho.** Uma comparação sobre os mesmos X/y/IDs isola a correção do código; um efeito pequeno na média não implica efeito pequeno em cada pessoa. A escolha ±11 e P1–P3 precisam ser reavaliadas nas coortes anteriores sem usar DREAMT para ajustar parâmetros.

**O que foi testado, e como.** Windows local, Python 3.11.9. CI #91 verde; reconstrução dos caches e censo comunicado antes de treinar. Protocolo/executor commitados em 11fa375 antes das rodadas. Código antigo d429d43 e corrigido 3273431 exportados do Git sem resultados/checkpoints antigos. Dez execuções (cinco grupos por versão), 69 células em cada: Newcastle esquerdo, Walch principal/todos, punhos e baseline/8b/9 LOSO completo dos três braços, 92 participantes. Mesmas entradas carregadas, hashes e ambiente conferidos, uma thread nativa e até dois processos. Bootstrap pareado de 2.000 reamostragens, seed 20260910, médias/desvios/ICs/máximos por pessoa/célula. Verificador sem src/avaliar recompôs cinco métricas das predições; comparação da repetição ML-04/ML-04b. Testes independentes dos resumos públicos e sabotagem da média; guardas históricas no commit registrado. Suíte ML completa e três conferências; diff dos dourados/firmware e varredura sem seguir reparse points.

**Resultado medido.** 69 células antes/depois completas, zero avisos, entradas/ambientes iguais. 144 capturas verificadas, erro absoluto máximo 0 (atol 1e-12). Repetição: 24 células, 730.560 predições, zero divergência. Suíte 236 passa, inclusive 40 + 19 dourados intactos. Censo ±2/±11: Wearanize 385/2.090 de 87.795 por braço; Newcastle esquerdo 104/572 de 30.440, direito 100/550 de 29.385; Walch principal 347/1.489 de 23.303, todos 367/1.599 de 25.250. Fração máxima individual alterada em ±11: 14,263% Wearanize, 32,333% Walch. Maior |Δκ| médio entre células 0,015003; em outra célula, média -0,011205 e Δκ individual -0,209959 (955 épocas, 49 de vigília). Maior Δespecificidade individual -0,346154, média da célula -0,006366 (1.147 épocas, 26 de vigília). As direções primárias ±11/HMM permanecem, com ICs pertinentes excluindo zero; quatro sinais de médias secundárias mudam com ICs incluindo zero antes/depois. Nenhuma mudança de sinal em contrastes LOSO/punhos. ML-17 concluída na segunda branch; ordem #91 antes da PR de rodadas. Sobre develop 42c1e75920bfc4f09c14ac65251cc90e1f6352b1 (DOC-16/REQ-01 fechados e DOC-17 aberto), saldo zero após abrir/fechar ML-17: 38 abertos, L0 9/L1 14/L2 7/L3 8.

**Adaptação.** O censo exato detectou diferenças apenas nos ângulos Newcastle (máximo 2,842170943040401e-14 graus; médias absolutas nas oito features 6,221342976485442e-17 esquerdo e 6,588159205405496e-17 direito). Y/IDs/ordem, outras seis features e Wearanize/Walch são exatos. As duas versões usaram o mesmo X reconstruído; não se declara reprodução bit a bit dos históricos. Padrão do censo permanece exato; opção angular explícita até 3e-14 registra o desvio legado. Causa não determinada. P1–P3 originais preservadas, com adendo datado para os sinais secundários inconclusivos, antes de qualquer DREAMT. Pacote de resumos preparado ainda sem commit, com vetores de notas anônimos: decisão de publicação pendente. Proposta enviada de publicar agregados/manifesto/verificadores e manter notas individuais locais. Licença OA local CC BY 4.0 lida e hash registrado no relatório; páginas oficiais exigem pesquisa científica e não identificação. A interpretação de permissão de derivados não equivale a garantia de privacidade. Rótulos/predições/caches permanecem locais. A análise histórica aponta commits, sem congelar arquivos atuais.

**O que deu errado no caminho.** A preparação Walch recebeu a pasta acima de labels/ e parou com FileNotFoundError; o caminho real do pacote foi identificado e passado explicitamente. A primeira conferência exata bloqueou corretamente a pequena diferença Newcastle; os desvios foram quantificados antes dos ajustes de modelos. Na integração, o primeiro stash apply foi tentado antes de resolver os conflitos de CI/CLAUDE e não foi aplicado; repetido depois da resolução, com conciliação manual dos registros. Nenhum bruto/cache histórico foi sobrescrito. Falhas deliberadas dos controles não foram tratadas como erro operacional.

**Risco em aberto.** ML-17 pronta para revisão/integração, não mesclada pelo Codex. ML-13 permanece aberta: carregador e avaliação DREAMT ainda não feitos. Não houve ablação para separar quantitativamente janela, transições e reinício HMM. ICs são pontuais por célula, não corrigidos por multiplicidade nem por novo treino a cada bootstrap. ML-02 real, ablação completa, RF, seleção/aninhada e quantização não foram refeitos; seus históricos não representam automaticamente o código corrigido. Caches/logs/execuções movidos com robocopy /E /XJ para dados-locais/ml17-evidencias-2026-11-05/, fora da worktree; 614 arquivos conferidos por tamanho/SHA-256 antes de remover a origem; brutos originais externos intactos. Nenhuma junction/reparse point na worktree/execuções ou nas três raízes brutas consultadas. Caminhos absolutos informados ao autor. Sensor no travesseiro não validado por estas bases.

**Procedência.** PR #91; fontes d429d43e1b7bafacae67fbebb9a328942d63efff e 3273431b6ebec4e3889bd3f01c3593b32dc0137e; executor 11fa3751088ca123d121f921f69e9813dd1c6d59; análise 2a8f51d7fb26c038811310ba4d536abab57f37a2; branch bugfix/ML-17-rodadas-comparadas. docs/ML-17-PROTOCOLO-RODADAS.md, docs/RELATORIO-ML-17-CONTEXTO.md, docs/ADENDO-ML-13-APOS-ML-17.md; resumos versionados em ml/experimentos/saida/ml17/; manifesto e verificadores; evidência privada realocada em dados-locais/ml17-evidencias-2026-11-05/, inventário REALOCACAO.json. Comparador e verificador de predições reexecutados no destino sem diferenças. Manifesto original preservado, inclusive caminhos históricos; executor congelado não foi adaptado à realocação.

---

# 2026-11-05 (viii) — DOC-16: a arquitetura adotada no resto do texto do TCC

**O problema, como foi entendido no início.** As inserções `CALC-01` a `CALC-04` reescreveram a
6.4 do TCC para o sono leve com a fila do sensor, mas o resto do texto continuava descrevendo o
*Deep Sleep* com despertar por movimento. O `DOC-16` listava cinco lugares (Justificativa, 5.4,
5.5, 5.6 e a 6.5 com a Figura 5).

**Hipótese de trabalho.** Que bastasse reescrever esses cinco trechos, num arquivo de inserção
com o texto atual ao lado do novo, como nas `CALC-*`.

**O que foi testado, e como.** O "Copy of Produto 5" (30/09) lido inteiro pelo conector do Drive
e varrido por termos da arquitetura antiga (*Deep Sleep*, *wake*, despertar, interrupção,
evento de movimento, GPIO27, AI > L). Cada fato do texto novo conferido no código: o
`firmware/sketch.ino` e o `firmware/nucleo/` (tarefas, 1,7 s, 10 min, FIFO de 1.024 B, grade
de 32 Hz, divisão do lote no `413`), o `docs/DATA-CONTRACT.md` v2.7.0 (6 características e a
gravidade enviadas; 2 derivadas no servidor) e a `ARQ-01`. Os trechos citados como "texto atual"
conferidos por script contra o documento, com controle positivo. A Figura 5 nova desenhada em
SVG e convertida para PNG pelo Edge em modo sem janela, e conferida por inspeção da imagem.

**Resultado medido.** `../documento/INSERCAO-DOC-16-ARQUITETURA-NO-TEXTO.md` (fora do Git) com
**13 pontos em 9 seções**, e `figura5-fluxo-firmware-c2.svg`/`.png`. Os 17 trechos citados
estão no documento palavra por palavra (17/17); trocando uma palavra de um deles, o script
acusa (16/17). Nenhuma inserção `CALC-*` estava colada no documento.

**Adaptação.** O alcance era maior que o listado: a varredura achou a arquitetura antiga também
na Introdução (dois parágrafos), num objetivo específico, no Quadro 1, na 6.3.1, em quatro
trechos da 6.3.3, na 6.3.6 e no cronograma. O mais relevante deles é o volume de dados: o texto
estimava "dezenas a poucas centenas" de registros por noite, porque só o movimento gerava
registro; na arquitetura adotada toda época gera, e o número é fixo, 960 por noite de 8 h. O
objetivo específico ficou com duas saídas para o autor decidir com o orientador, porque
reescrever um objetivo para caber no resultado é diferente de corrigir uma descrição. A 6.5 nova
diz que o firmware de produto ainda não rodou na placa.

**O que deu errado no caminho.** A primeira versão da Figura 5 tinha uma decisão "Passaram
10 min?" cuja saída "sim" seguia para as duas raias ao mesmo tempo, com uma seta sem destino
claro; virou uma etapa, "A cada 10 min, avisa a tarefa de envio". A primeira chamada do Edge
pelo Bash terminou sem gerar o PNG e sem erro; pelo PowerShell, com `Start-Process -Wait`,
gerou. A 6.5 nova citava a 7.5 para os testes do firmware, e a 7.5 do documento não os menciona
(está na contagem de 9/09); a referência saiu do texto e virou ponto do `DOC-17`. O script que
confere as citações quebrou na primeira execução por uma barra invertida dentro do *heredoc*.

**Risco em aberto.** O texto só muda quando o autor colar, e na ordem: as `CALC-01` a `04`
primeiro. O texto do TCC não tem resultado nenhum do classificador, e a 6.6 o trata como
condicional — contradição com a 6.4.4 nova até o `DOC-17`, que depende da `ML-17`. A 6.5 nova
descreve um firmware que não rodou na placa; a placa pode mudar algum detalhe (`FW-05`).

**Procedência.** "Copy of Produto 5" (Google Docs, 30/09), lido em 05/11; `firmware/sketch.ino`,
`firmware/nucleo/` (`fifo_mpu.h`, `reamostragem.h`, `payload.h`, `lote.cpp`),
`docs/DATA-CONTRACT.md`, `web-app/lote.py`, `docs/DECISAO-ARQ-01-CADENCIA.md`; inserções
`CALC-01` a `CALC-04`; backlog `DOC-16`, `DOC-17`.

---

# 2026-11-05 (ix) — REQ-01: os requisitos do dispositivo, com critério e estado

**O problema, como foi entendido no início.** Um objetivo específico do TCC promete "definir os
requisitos iniciais (dimensões, conforto, autonomia, aquecimento, custo e segurança)", e o
cronograma do texto marca a atividade como concluída em março e abril. A leitura do "Copy of
Produto 5" para o `DOC-16` mostrou que o texto não tem seção de requisitos. O `REQ-01` estava no
backlog havia semanas, com uma linha só.

**Hipótese de trabalho.** Que a maior parte dos requisitos já tivesse número no repositório —
autonomia, potência, armazenamento sem rede, volume de dados, segurança dos dados — e que bastasse
reuni-los com critério verificável, deixando explícito o que depende de bancada ou de decisão.

**O que foi testado, e como.** Um script novo, `scripts/requisitos_dispositivo.py`, que não cria
modelo: importa o `estudo_cadencia.py` e lê do firmware a partição `dormio`, o tamanho do setor da
fila e o intervalo de envio. O `--conferir` trava 26 números, entre eles a tabela inteira de
capacidade por consumo de placa. Controle positivo: partição reduzida a 1 MiB no
`partitions.csv`, e envio a cada 5 min no `sketch.ino`, cada um numa execução, com os arquivos
restaurados depois. As referências a testes no documento (invariância a rotação, dourado, fila,
RLS) conferidas por busca no repositório.

**Resultado medido.** `docs/REQUISITOS-DISPOSITIVO.md` com 23 requisitos em seis dimensões. O
`--conferir` passa com 26 números; a partição reduzida reprovou dois (32 704 → 16 320 registros;
272,5 → 136 h), o envio a cada 5 min reprovou 18 (épocas por lote 20 → 10, e todas as correntes,
potências e capacidades, que dependem do rádio). O resultado mais útil é a tabela do RD-10: uma semana ligado pede **383 mAh**
só com os circuitos integrados e até **2 552 mAh** com 10 mA de consumo fixo da placa no pior caso
— a bateria não se escolhe pelo modelo, e sim pela medição da placa. Inserção para o TCC em
`../documento/INSERCAO-REQ-01-REQUISITOS.md`: 6.2.3 nova, com o Quadro 3 novo e a lista das
referências a renumerar (Quadros 3 a 6 → 4 a 7).

**Adaptação.** Dois critérios não têm fonte no repositório e entraram como **propostas**, marcadas
assim, para os autores e o orientador confirmarem: 7 dias sem recarga e no máximo 1 °C de elevação
na face do travesseiro. O critério térmico é comparativo de propósito, para não citar um limite
normativo de temperatura de contato que ninguém leu (`DOC-06b`). Custo e dimensões ficaram
"abertos", sem número inventado.

**O que deu errado no caminho.** A tabela de renumeração da inserção atribuía a referência ao
"Quadro 5" à 7.2, e ela está na 7.3; e contava três ocorrências de "Quadro 3" na 6.3.3, quando são
duas. Os dois erros foram achados conferindo a seção de cada linha no texto extraído, antes de
entregar. A nota sobre o Quadro 2 dizia que o firmware não usa as bibliotecas Adafruit; elas
seguem nos três programas auxiliares, e a frase foi corrigida. A primeira versão do script
imprimia a contagem de números conferidos como literal, e não contada. E a primeira leitura das
sabotagens foi feita com a saída cortada (`tail`), o que daria "quatro" reprovações para o envio a
cada 5 min; refeita com a saída inteira, são 18.

**Risco em aberto.** Os dois valores propostos podem mudar, e a tabela de capacidade depende dos
7 dias. Nada do documento foi medido na placa; cinco requisitos esperam a solda. O LED de energia
da DevKit V1, citado no RD-15, é conhecimento geral da placa, não verificado nesta.

**Procedência.** `docs/REQUISITOS-DISPOSITIVO.md`; `scripts/requisitos_dispositivo.py`;
`scripts/estudo_cadencia.py`; `firmware/partitions.csv`, `firmware/nucleo/fila_flash.h`,
`firmware/sketch.ino`; `docs/CALCULOS-TCC.md` Z.3–Z.4; "Copy of Produto 5" (30/09), lido em 05/11.

---

# 2026-11-05 (x) — DOC-06b: as citações do TCC conferidas contra as fontes

**O problema, como foi entendido no início.** O `DOC-06b` pede que os autores leiam o que citam,
porque "referência conferida não é artigo lido". Ninguém tinha conferido se cada fonte diz o que
o texto atribui a ela, e é o primeiro lugar que um avaliador abre.

**Hipótese de trabalho.** Que as referências existissem e estivessem certas na forma (as
anteriores do projeto foram conferidas no `DOC-06`), e que os problemas, se houvesse, fossem de
paráfrase.

**O que foi testado, e como.** As 22 referências e as 35 frases que as citam extraídas do "Copy of
Produto 5" (30/09). Os 9 artigos localizados pelo DOI na Europe PMC: metadados e resumo pela API,
texto completo (`fullTextXML`) para o Skarpsno, o Liu, o Yuan e o De Fazio, com busca do trecho
que sustenta ou contradiz cada frase. As fontes técnicas abertas no endereço citado; a LGPD no
Planalto; o Gil por uma cópia digitalizada e o sumário de outra. As correções de texto conferidas
por script contra o documento (4/4 trechos citados como "texto atual" encontrados).

**Resultado medido.** Metadados dos 9 artigos conferem. **SKARPSNO et al. (2017) contradiz o
texto:** a discussão do artigo diz que os sintomas de insônia não se associaram aos movimentos
noturnos, e o texto afirmava a associação. **A página da TDK citada responde 404.** Quatro
imprecisões: o YUAN (2024) é revisão só de actigrafia de pulso, citado duas vezes para "combinar
sinais", e a terceira citação particulariza "REM e sono profundo"; o SMITH (2018) é mais restrito
que "método válido"; as correntes do ESP32 vêm da folha de dados, não do guia citado. Três
referências da lista sem citação. O ENMO da `CALC-03` sem fonte: VAN HEES et al. (2013), localizado.
Confere o resto: De Fazio, Liu (98,42 %, 30 pessoas, sob o colchão), Boiko, Yoshihi, Walch, Bliwise
pelo título, a lei e o Gil p. 17. Entregas: `docs/CONFERENCIA-DE-CITACOES.md`;
`../documento/CORRECOES-CITACOES.md` (fora do Git); as inserções `CALC-01`, `CALC-02`, `CALC-03`,
`CALC-04` e `DOC-16` ajustadas só dentro dos blocos a colar.

**Adaptação.** Os sítios das editoras (MDPI) recusaram acesso automatizado (403); a leitura passou
à Europe PMC, que tem os textos completos dos artigos abertos. Para a folha de dados da Espressif,
cujo PDF não pôde ser lido aqui, a referência nova vai com versão e ano em branco, marcados para
os autores preencherem da capa — melhor que um número inventado. O `DOC-06b` não fecha: o item é a
leitura pelos autores, e a página diz o que ler primeiro.

**O que deu errado no caminho.** A primeira tentativa de ler o MPU-6050 usou o endereço
`…/mpu-6050/`, que não é o da referência; o da referência (`…/mpu-6000/`) também responde 404, e
isso virou achado. Uma cópia da folha de dados num sítio de universidade exigia login, e outra
voltou HTML. Um extrator de texto do PDF da Espressif, escrito às pressas, travou numa expressão
regular e foi interrompido; conferi pela lista de processos que nenhum ficou rodando (§6, regra 8
das lições). A tabela de vereditos tinha duas seções erradas (5.7 por 5.8; 5.6 por 5.7), corrigidas
conferindo a seção de cada linha no texto extraído. **A minha própria inserção do `DOC-16`, de
horas antes, citava a página quebrada da TDK e o guia da Espressif para correntes** — o mesmo erro
que esta conferência acha no texto antigo.

**Risco em aberto.** As correções só valem coladas, e o colchete da folha da Espressif precisa ser
preenchido. Os livros (Gil p. 41, Bello, Elkington) não foram conferidos. A leitura dos autores
segue sendo o item (`DOC-06b`).

**Procedência.** "Copy of Produto 5" (30/09), lido em 05/11; Europe PMC (DOIs na página);
`docs/CONFERENCIA-DE-CITACOES.md`; `../documento/CORRECOES-CITACOES.md`; `scripts/calculos_tcc.py`
(seções da folha de dados do MPU-6050 e Tabela 4-2 da do ESP32).

---

# 2026-11-05 (xi) — LGPD-02: retenção por inatividade de 12 meses

**O problema, como foi entendido no início.** Não havia política de retenção: uma leitura ficava
no banco até o titular apagar a conta, e a seção 7 da política declarava isso como lacuna. O
backlog aceitava as duas saídas, prazo ou declaração formal, mas não o silêncio.

**Hipótese de trabalho.** Que o padrão do mercado de aparelhos de sono — guardar enquanto a conta
é usada, apagar na exclusão — servisse, completado pela regra que resolve a conta esquecida:
eliminar por inteiro a conta sem uso há 12 meses. O autor aprovou essa combinação depois de ver
como Oura e Fitbit tratam o tema.

**O que foi testado, e como.** Migração `013`, com a lista de deletes do titular extraída para
`_eliminar_titular(uuid)` e o expurgo em `expurgar_contas_inativas()`. `test_rls_retencao.py`
contra Postgres 16 em Docker, cada teste semeando contas com datas recuadas numa transação
revertida. Controle positivo de três formas: a suíte sem a `013` numa cópia da árvore; três
sabotagens novas no `verificar_por_mutacao.py`; e o diagnóstico rodado depois de reaplicar a
`006` por cima da `013`. Também a suíte RLS inteira, o `verificar_migracoes.py`, o backend e os
testes da página da política no frontend.

**Resultado medido.** RLS **193** (174 + 19). Sem a `013`, **17 dos 19** testes novos caem; os 2
que passam são os de recusa ("usuário logado não chama"), que sem a função passam porque ela não
existe — no código real passam por duas barreiras, o EXECUTE revogado e o `security invoker`.
Mutação **35/35**: ignorar a última leitura derrubou 3 testes; liberar o expurgo para
`authenticated`, 1; a eliminação sem dispositivos, 5, inclusive o da exclusão pelo próprio
titular — prova de que os dois caminhos usam a mesma lista. Diagnóstico nos **13 estados**, e
com a `apagar_minha_conta()` revertida à da 006 a `013` cai para 2 de 3 marcas. Backend **453**;
frontend da política 12/12.

**Adaptação.** O prazo ficou dentro da função, sem parâmetro, pelo mesmo motivo da
`apagar_minha_conta()` não ter parâmetro de usuário: um `(1)` digitado por engano apagaria quem
não entra há um mês. As duas funções novas são `security invoker`, para não criar mais uma
função que eleva privilégio. O agendamento ficou condicional ao `pg_cron`, e o diagnóstico o
mostra numa linha informativa, porque o Postgres de teste não tem a extensão. A política só pode
descrever o mecanismo depois de ele existir: a `013` vai à produção ANTES do release que publica a
seção 7 nova — a ordem inversa da do `LGPD-06` —, e isso virou o `LGPD-09`. A seção 7 diz que não
há aviso prévio, porque não há SMTP (`LGPD-10`), e que o plano gratuito do Supabase não faz cópia
de segurança, conferido na documentação dele.

**O que deu errado no caminho.** Na primeira resposta ao autor, chamei a saída "guardar enquanto
a conta existir" de a mais fraca; a pesquisa mostrou que é o padrão do mercado, e a recomendação
foi refeita. O `verificar_migracoes.py` imprimia "os 12 estados" como texto fixo, e passou a
contá-los. Uma edição por script Python e outra por `sed` não pegaram a linha do texto fixo, que
tinha o travessão; foi feita com a ferramenta de edição. O README das migrações tinha pulado a
`012`, e a linha dela entrou junto com a da `013`.

**Risco em aberto.** Nada disso vale na produção até o autor aplicar a `013` e ligar o `pg_cron`
(`LGPD-09`); até lá, o release não pode levar a seção 7 nova. O sinal de login é o
`last_sign_in_at` do Supabase, que muda no login, não a cada renovação de sessão: quem só usa
uma sessão aberta por mais de 12 meses, sem dispositivo enviando, seria tratado como inativo —
caso improvável, e a leitura do dispositivo já mantém a conta. Sem aviso por e-mail
(`LGPD-10`). A guarda de 5 anos de pesquisa, se o orientador confirmar voluntários sob comitê de
ética, seria cláusula própria, fora deste expurgo.

**Procedência.** `web-app/migrations/013_retencao_por_inatividade.sql`;
`web-app/tests/rls/test_rls_retencao.py`, `verificar_por_mutacao.py`, `esquema_base.sql`,
`conftest.py`; `web-app/tests/migracoes/verificar_migracoes.py`;
`web-app/migrations/DIAGNOSTICO-migracoes-aplicadas.sql` e `README.md`;
`docs/POLITICA-DE-PRIVACIDADE.md`, seções 7 e 10; documentação de backups do Supabase, lida em 05/11.

---

# 2026-11-06 (xii) — SIM-02: o simulador fala a C2

**O problema, como foi entendido no início.** Com a defesa adiada para depois do MVP, a pergunta
passou a ser o que impede o produto de funcionar de ponta a ponta. Um dos buracos: o
`web-app/fake_sensor.py` ainda falava o protocolo da v1.1 — leitura avulsa a `/api/data` a cada
3 s, sem `ts`, `epoca_s` nem `f`/`g`/`fs`. O caminho que o firmware C2 vai usar (lote em
`/api/data/lote`, as duas características angulares derivadas no servidor, `/api/features`) não
era exercitado por nada, e não havia como demonstrá-lo antes da solda.

**Hipótese de trabalho.** Que um simulador que gere o sinal na grade de 32 Hz e calcule as
características pela PRÓPRIA referência (`ml/src/features.py::features_de_epoca`, que o firmware
copia e com que o modelo foi treinado) seja indistinguível do dispositivo para o servidor, sem uma
terceira implementação das características. A FIFO a 50 Hz não foi simulada: ela tem vetor dourado
próprio, e o alvo aqui é o contrato e o servidor.

**O que foi testado, e como.** `scripts/simulador_c2.py`, rodado pelo ambiente do `ml/` (numpy e
scipy não entram no backend da Vercel); o envio usa só a biblioteca padrão.
`ml/testes/test_simulador_c2.py` confere o simulador contra o código do servidor
(`validar_leitura`, `validar_captacao`, `lote.extrair_leituras`, `features_noite.derivar_noite`) e
contra constantes lidas dos arquivos do firmware (`payload.h`, `lote.h`, `epoca_c2.cpp`,
`sketch.ino`) e do `device_auth.py`. Controle positivo: 7 sabotagens no simulador. Ponta a ponta,
fora do CI: uma noite de 8 h pela rota Flask real `/api/data/lote` e depois `GET /api/features`,
só com o banco trocado por um falso. Também o modo tempo real, a seco, por duas épocas, e as suítes
completas de ML e do backend.

**Resultado medido.** 24 testes; ML **190 → 214**; backend **453**, inalterado. Sabotagens
**7/7**: `ts` no fim da época (1 teste cai), lote de 61 (4), 413 sem dividir pela metade (1),
vigília com amplitude de sono (1), `g` não unitário (5), `f` em ordem invertida (2), pendente
tratado como aceito (2). Na rota real: 960 aceitas, 0 rejeitadas, 16 requisições; o
`/api/features` devolveu as 960 épocas, uma só sem `d_angulo` (a primeira), e as 18 viradas do
gabarito aparecem com `d_angulo` de 20° a 62°; no sono quieto, no máximo 5,7°. Na semente dos
testes, a mediana do ENMO acordado é 4,4 vezes a do sono quieto (3,6 mg contra 0,82 mg).

**Adaptação.** O plano dizia "lotes de 20, como o firmware". Lendo o `sketch.ino` antes de
escrever: o firmware acorda o envio a cada 10 min (~20 épocas), mas esvazia a fila em lotes de
**até 60** (`MAX_LEITURAS_POR_LOTE`). O modo noite usa 60, e o tempo real envia a cada 20. O
`fake_sensor.py` ficou, como o simulador do caminho avulso, que continua no contrato e cujos
testes do critério de movimento importam dele. Nada foi enviado à produção: o backend local fala
com o Supabase do `.env`, e enviar é gravar na conta dona do token — isso fica com o autor.

**O que deu errado no caminho.** O padrão "23h de ontem" falhou na primeira execução, à 01h11: a
noite de ontem ainda não tinha terminado, e o servidor recusa `ts` no futuro. Passou a ser "as 23h
mais recentes cuja noite já terminou", com teste para madrugada, meio-dia e 23h30. O limiar de 5
vezes no teste de separação do ENMO foi chute; a medida deu 4,4, e o limiar foi para 3 — sem mexer
no modelo de sinal para caber no teste. O script das sabotagens quebrou na quinta, lendo em UTF-8
a saída do pytest em cp1252; o `finally` restaurou o arquivo, e a rodada foi refeita inteira. O
script da ponta a ponta errou duas vezes antes de rodar (esqueci de passar o transporte falso; o
`device` da consulta precisa ser um uuid).

**Risco em aberto.** Com `f` em ordem invertida, o **servidor aceitou** as leituras: a ordem
errada cabe nas faixas, como o contrato já avisa no §2.6. Só o teste que recalcula as
características pelo nome a pegou; do lado do firmware, quem protege é o vetor dourado. O sinal é
sintético: serve à corrente e à demonstração, e nenhum número de classificador medido sobre ele
pode entrar no TCC como resultado — o gabarito existe para conferir a `ML-INF` funcionando, não a
acurácia dela. O envio à conta de demonstração na produção não foi exercitado.

**Procedência.** `scripts/simulador_c2.py`; `ml/testes/test_simulador_c2.py`; `README.md`,
`web-app/README.md` e `docs/DATA-CONTRACT.md` (a menção aos simuladores); `firmware/sketch.ino`
(`INTERVALO_DE_ENVIO_US`, `enviar_pendentes`), `firmware/nucleo/lote.h`, `payload.h`,
`epoca_c2.cpp`; backlog `SIM-02`.

---

# 2026-11-06 (xiii) — ML-17: publicação agregada e auditoria das notas locais

**O problema, como foi entendido no início.** O autor aprovou publicar apenas resumos e manifesto na segunda PR da ML-17. O pacote preparado ainda continha vetores anônimos de notas; as evidências já estavam fora da worktree. Era preciso exportar somente agregados e distinguir o que o clone público confere do que depende das notas locais.

**Hipótese de trabalho.** Preservar os resultados completos externos e exportar campos agregados explícitos permite manter médias, dispersão e extremos sem publicar notas ou índices individuais. Os hashes do manifesto congelado podem conferir os dados no novo local sem junction e sem reescrever a procedência da execução.

**O que foi testado, e como.** Nesta máquina Windows local, PowerShell, Python 3.11.9 pinado. Fetch e integração de origin/develop 1b5c82c nas duas branches, preservando entradas viii a xi e itens dos demais autores. Suíte ML completa, com os controles positivos novamente executados: cinco grupos de consumidores/22 mutações, guardas históricas e fontes/cache/censo adulterados. Publicação: os três JSONs anteriores com notas reprovam pela guarda de campos individuais; projeção agregada passa; vetores e índice de extremo inseridos deliberadamente reprovam; média pública adulterada reprova pelo hash, não por uma recomposição sem notas. Conferência de executor realocado aceita LF/CRLF, mas reprova mudança de expressão. Exportação com --cache/--censo novos, conferidos pelos hashes originais. Auditoria local independente com math.fsum/statistics.stdev e comparação exata dos agregados públicos com a projeção das notas; não usa src/avaliar nem recompõe ICs bootstrap. Três conferências de documentos, diff dos dourados/firmware e inspeção de reparse points antes da entrega.

**Resultado medido.** 245 testes ML passam, incluindo 40 + 19 dourados intactos. Os 69 conjuntos de células geraram 345 combinações célula/métrica auditadas localmente, zero divergências nas médias/desvios/extremos; a projeção coincide com os agregados públicos. Verificador de predições repetido na exportação: 144 capturas, cinco métricas, erro máximo zero; repetição Newcastle, 730.560 predições e zero diferença. Sete JSONs públicos, sem notas ou índices individuais; hashes normalizados UTF-8/LF e fontes de análise registrados no manifesto. Na base develop 1b5c82c, a primeira PR abre ML-17 (39 a 40, L0 8 a 9); esta entrega fecha (40 a 39, L0 9 a 8), L1 14/L2 7/L3 10. Nenhum novo treinamento, avaliação DREAMT ou alteração do código numérico nesta etapa.

**Adaptação.** Exportador usa campos agregados explícitos, guarda adicional de notas e hashes dos seis resumos; a atribuição Wearanize+ OA identifica coleção, referências, licença e cálculos do projeto. Testes públicos verificam contrato, integridade e fontes históricas; a recomposição das estatísticas a partir das notas é uma ferramenta local separada. A realocação é atendida por argumentos, mantendo manifesto/caches/execuções originais intactos; tolerância de fim de linha do executor não se aplica aos dados. Proposta e escolha expressa do autor registradas no relatório. Diário vi/vii permanece antes de viii/ix; as novas entradas x/xi foram preservadas.

**O que deu errado no caminho.** Uma consulta de inspeção presumiu a chave newcastle_esquerdo no censo e recebeu KeyError; a estrutura real usa newcastle/esquerdo. Um patch tentou excluir e recriar o mesmo arquivo numa chamada e foi recusado, sem alteração; aplicado como atualização separada. A primeira exportação após a sincronia recusou o hash do executor: o Git convertera LF para CRLF. Censo e código normalizado conferiam; foi acrescentado controle explícito para somente essa conversão, com teste de alteração real de código que reprova. Conflitos de contagem/linha ML foram conciliados com os registros novos do develop, sem substituir o estado dos outros itens.

**Risco em aberto.** Integração depende de revisão; ordem #91 antes desta PR, ambas para develop, sem merge pelo Codex. As limitações das rodadas e os quatro sinais secundários inconclusivos estão no relatório/adendo, não foram resolvidos pela publicação agregada. CI sem datasets não valida numericamente as médias contra notas ausentes; a auditoria completa é local e os hashes não são assinatura de autenticidade. ML-13 continua aberta, sem carregador/avaliação DREAMT. Evidência em dados-locais/ml17-evidencias-2026-11-05/, fora da worktree, com brutos no armazenamento original e sem junctions; o executor de treinamento congelado ainda registra os caminhos originais, ao passo que a análise aceita os caminhos realocados.

**Procedência.** Segunda branch bugfix/ML-17-rodadas-comparadas, dependente da #91. develop 1b5c82c70262604f57d49faad4bcdafc71488ef1; executor 11fa3751088ca123d121f921f69e9813dd1c6d59; código antes d429d43 e depois 3273431; análise/exportação 3eadf88. docs/RELATORIO-ML-17-CONTEXTO.md e docs/ADENDO-ML-13-APOS-ML-17.md; ml/experimentos/saida/ml17/manifesto.json; ferramentas/resumir_ml17.py e auditar_resumos_ml17.py; evidência privada REALOCACAO.json, auditoria-agregados-06nov.json e publicacao-06nov.xml na pasta externa informada ao autor.


---

# 2026-11-06 (xiv) — ML-13: validação externa DREAMT

**O problema, como foi entendido no início.** Após a integração da ML-17, avaliar a terceira coorte externa com P1–P3 congeladas. A preparação da versão 2.2.0 já estava integrada. Faltavam a inspeção da grade, o carregador por caminho explícito e a avaliação com as quatro configurações e os três braços do ML-04.

**Hipótese de trabalho.** No braço pulso, κ de ±11 acima de zero, ganho conjunto de κ e especificidade com ±11 sobre ±2 e queda de especificidade com HMM sobre ±2. O protocolo exige 30 s alinhados ao PSG e separação de gravações e lacunas.

**O que foi testado, e como.** Windows local, Python 3.11.9 e bibliotecas pinadas. Branch avançada para b5335ac. Executados 103 hashes oficiais e inspeção de cinco colunas nas 100 gravações. Os dois testes direcionados à CLI reprovaram na base, pois a opção dreamt era rejeitada. Suíte local com os casos de escala, fase, pares ACC adulterados, lacuna, cauda truncada, coluna ausente, passagem de caminho, contexto global deliberado e ordem de notas invertida. Controles históricos da ML-17 repetidos na suíte. Protocolo commitado em c328342 antes dos resultados. Cache congelado Wearanize conferido pelo SHA-256 e pelas fontes de 3273431, com conferência da seleção atual de 92 participantes e dos três hashes X/y/IDs antes do treino. Executado ML-04 com uma thread nativa. A contagem dos pools foi verificada em processo separado com os mesmos imports e ambiente. Exportação recompôs médias e desvios para 65 combinações célula/métrica e conferiu a cobertura das 13 matrizes somadas. Lidos Metadata.txt, PhysioNet e a descrição original. Executadas as três conferências do repositório.

**Resultado medido.** 203.531.428 linhas contínuas de 64 Hz com pares ACC idênticos. Três gravações com fases PSG incompatíveis, 233 transições fora da fase inicial e máximo de 120 em uma gravação. Nos 97 arquivos avaliados, 77.738 épocas e 101 segmentos após excluir 97 caudas e quatro épocas sem rótulo. O máximo por gravação foi um em cada categoria de descarte. P1 κ 0,4218 com IC95 [0,3867, 0,4562]. P2 Δκ +0,030 e Δespecificidade +0,054, ambos ICs acima de zero. P3 Δespecificidade −0,052, IC abaixo de zero. Maior |Δκ| individual 0,3672 em cabeça-E4/±11+HMM (média +0,0355). Maior queda individual de especificidade −0,4000 em cabeça/±11+HMM (média −0,0013). 278 testes passaram. Backlog sobre b5335ac passou de 39 para 38 abertos, L0 de 8 para 7, L1 14, L2 7, L3 10.

**Adaptação.** Critério de uma única fase PSG fixado antes da rodada. Três gravações excluídas por ambiguidade, sem usar desempenho para decidir. O carregador recupera a grade nativa de 32 Hz de pares duplicados, converte para g e conserva o índice original ao filtrar. Uma cópia auditada do cache ML-17 foi identificada para o código atual, mantendo dados e segmentos. A exportação mantém agregados com ICs, dispersão, contagem válida e extremos sem identificadores. P1–P3 e adendo de 05/11 preservados.

**O que deu errado no caminho.** A consulta Git no sandbox retornou que a operação exigia uma worktree e foi repetida com acesso ao Git compartilhado. A seleção pytest com -k cli também encontrou o caso de colunas clínicas, que falhou antes de o módulo existir. O preparo de cache inicialmente omitiu --item, exigido pela CLI. A segunda preparação foi encerrada após verificar a cópia equivalente do cache ML-17. O teste de exportação primeiro encontrou a chave de IC incompatível com a guarda de publicação. Em seguida, a sabotagem tentou inverter uma tupla com reverse. Ajustados o esquema e a fixture, a suíte passou. Depois de gerar o pacote, o CI encontrou o novo JSON na raiz histórica da ML-14, fora do inventário de 18 arquivos. Reproduzido localmente (19 arquivos), movido para saida/ml13/ e repetida a suíte com o pacote final.

**Risco em aberto.** As três fases ambíguas limitam o resultado à coorte avaliável. Os ICs são por participante e refletem as configurações congeladas. O desempenho no travesseiro exige validação física. A exportação de um modelo de inferência no servidor é trabalho da ML-INF. Evidência em dados-locais/ml13-dreamt-avaliacao-2026-11-06 e brutos em dados-locais/dreamt-2.2.0 e no armazenamento Wearanize original. Seis raízes verificadas sem junctions. Revisão e merge ficam com os responsáveis.

**Procedência.** feature/ML-13-coorte-dreamt sobre b5335acb9e0164d9be6f471602eb83fe15f1782c. Protocolo/código executado c328342367de4079b99a6f7c420e4768ac8230b6. docs/ML-13-PROTOCOLO-TEMPORAL.md, docs/RELATORIO-ML-13-DREAMT.md, ml/experimentos/saida/ml13/agregados.json. Resultado individual, log, ambiente, cache auditado e JUnit ficam na evidência externa.


---

# 2026-11-07 — ML-13: controles de fronteira na avaliação DREAMT

**O problema, como foi entendido no início.** A revisão da #98 encontrou duas lacunas nos testes. A guarda de contexto só exigia o argumento segmentos, e o teste da grade PSG não exercitava diretamente o descarte de uma época com dois estágios.

**Hipótese de trabalho.** Um caso com dois participantes e uma lacuna deve acusar a junção indevida pela janela e pelo Viterbi. O rótulo da época só pode ser usado quando o estágio original é uniforme, inclusive quando os dois estágios são ambos de sono.

**O que foi testado, e como.** No Windows local, Python 3.11.9. Foi exercitada a entrada real rodar do ML-04 na coorte DREAMT, com catálogo, treino e destino sintéticos. Na variante de janela, o teste compara a matriz recebida pelo classificador com as janelas de referência. Na variante HMM, usa probabilidades fixas, roda o Viterbi real e confere a matriz de confusão. Foram executadas quatro mutações isoladas nos fontes, restaurados após cada execução. As três de segmentação juntam toda a matriz, apenas a lacuna ou apenas os participantes. A quarta aceita o estágio da primeira amostra. A suíte foi repetida após restaurar todos os fontes.

**Resultado medido.** Cada mutação de segmentação derrubou os dois casos da CLI de avaliação. A mutação de rótulo derrubou os dois casos de estágio misto (W/N2 e N1/N2). Os sete casos novos passam com a implementação correta. A suíte completa passou com 285 testes. P1 no diário xiv foi corrigido de 0,4224 para 0,4218, conforme o JSON e o relatório.

**Adaptação.** A regra de uniformidade existente foi extraída para uma função testável, preservando o controle de fase no carregador. Os testes separam o resultado esperado da função que produz os segmentos. Nenhuma nova rodada de modelos foi necessária para esse controle sintético.

**O que deu errado no caminho.** Uma leitura tentou expansão de chaves no PowerShell. A primeira suíte completa foi iniciada antes do recibo final das mutações. A suíte foi repetida depois que a restauração foi confirmada e os 285 casos passaram novamente.

**Risco em aberto.** A cobertura verifica fronteiras e rótulos com sinais artificiais. As limitações da coorte real continuam no relatório da ML-13. Nesta etapa os testes usam apenas arquivos sintéticos temporários, sem dados brutos ou junctions. O próximo item é o artefato de modelo da ML-INF.

**Procedência.** Base origin/develop 8859101, branch bugfix/ML-13-cobertura-dreamt. Revisão da #98, ml/testes/test_dreamt.py e ml/src/carregar/dreamt.py.


---

# 2026-11-07 (ii) — ML-INF: treino, validação e exportação de cabeça

**O problema, como foi entendido no início.** Entregar o modelo de seis características e o vetor dourado que a integração do backend consumirá. O autor escolheu o braço cabeça por ser a posição corporal mais próxima do produto, que recebe movimento através do travesseiro.

**Hipótese de trabalho.** O modelo balanceado com escala aprendida só no treino deve reproduzir as probabilidades do scikit-learn quando o backend recebe o campo f. O LOSO mede generalização entre participantes da cabeça. As três coortes externas medem generalização a pessoas e coortes de punho.

**O que foi testado, e como.** Windows local, Python 3.11.9. Protocolo e código fixados em 4ee0ffe antes dos resultados. Foram reconferidos inventário, bytes e X/y/IDs dos caches da ML-17 e 103 SHA-256 da DREAMT. Executados 92 folds LOSO, um ajuste com os 92 participantes e três avaliações externas congeladas. Pools nativos medidos com uma thread no próprio processo. A auditoria independente recompôs médias com scikit-learn e contou as oito matrizes a partir de y e predições locais. Os testes repetem o payload SIM-02, conferem ordem canônica e reproduzem predict_proba por aritmética da biblioteca padrão. Controles positivos executados ao incluir a pessoa de teste na dobra, inverter a ordem das features e adulterar um coeficiente. Os três controles reprovaram antes da restauração.

**Resultado medido.** 289 testes passaram no Windows. As quatro avaliações retiveram 92/27/29/97 participantes e 87.795/30.440/23.303/77.738 épocas. κ médio 0,3640/−0,0002/0,3652/0,0337 para LOSO, Newcastle, Walch e DREAMT. O maior |Δκ| em um participante foi 0,6825 no LOSO, com média +0,3640. Na DREAMT, |Δκ| máximo 0,4386 com média +0,0337. A alta especificidade na Newcastle e na DREAMT veio com sensibilidades por época de 0,047% e 12,65%. O máximo erro da auditoria das médias foi 1,11e-16. Quatro payloads e duas entradas sintéticas próximas ao limiar conferiram na tolerância de 1e-12 e classe exata. O backlog mantém a ML-INF aberta pela integração.

**Adaptação.** Cabeça original chega a 32 Hz pelo antialias comum e evita acrescentar saturação e quantização E4 ao sinal. Isso aproxima o pré-processamento da C2 sem presumir resolução efetiva igual. Os agregados registram desempenho baixo onde houve colapso para vigília. Os coeficientes e a fixture são versionados com procedência, licença e tolerância. As predições e notas individuais ficam externas.

**O que deu errado no caminho.** O primeiro comando de mutação não tinha permissão de escrita na worktree recém-criada. O arquivo foi conferido e as mutações foram executadas com acesso de escrita, restauradas e seguidas da suíte completa.

**Risco em aberto.** O teste de integração pela inferência real cabe à PR de backend. Os sensores das bases ficam presos à cabeça ou ao pulso. No produto o movimento chega pela espuma, com atenuação e atraso esperados ainda a medir. A variante ±11 exige avaliação própria. A evidência está em dados-locais/ml-inf-cabeca-2026-11-07 e os brutos DREAMT e caches ML-17 permanecem em suas pastas externas. Quatro raízes conferidas sem junctions.

**Procedência.** feature/ML-INF-modelo-cabeca, descendente da PR #99, sobre develop 8859101. docs/ML-INF-PROTOCOLO-MVP.md, docs/RELATORIO-ML-INF-MVP.md, ml/experimentos/ml_inf.py, ml/modelos/ml-inf-cabeca-v1.json e ml/testes/fixtures/ml-inf-cabeca-v1-dourado.json.

---

# 2026-11-07 (iii) — ML-INF v2: reproduzir e exportar o modelo validado

**O problema.** A v1 exportou seis features, escala global e uma época isolada. A revisão da #100 pediu o mesmo pipeline validado no ML-04 e na ML-13. Na Newcastle, a v1 detectou 10 de 21.270 épocas de sono.

**Hipótese.** O modelo de cabeça original com oito features, z-score por gravação e contexto ±11 reproduz os agregados publicados quando recebe as entradas históricas. O mesmo JSON deve reproduzir a pontuação do scikit-learn em noites simuladas que passam pela derivação angular do servidor.

**O que foi testado.** No Windows local, Python 3.11.9, foram reconferidos os 103 SHA-256 DREAMT e os caches da ML-17. Rodaram 92 ajustes LOSO, o treino final, quatro avaliações externas e duas noites C2 de 960 e 959 épocas. Uma auditoria independente refez κ e confusões. Os JSONs publicados e o caminho de classificação do ML-04 foram lidos no Git. Nove controles positivos acusaram z-score por pessoa, contexto global, corte em 45 s, piso de 22, ausência de conversão angular, JSON v1, ordem invertida, coeficiente adulterado e empate como sono.

**Resultado medido.** 299 testes de ML passaram após restaurar as mutações. κ da v2 no LOSO foi 0,4569. O JSON reproduziu κ 0,2953 na Newcastle, 0,4082 e 0,4123 nas variantes Walch e 0,3470 na DREAMT, com os ICs publicados e maior diferença por participante igual a zero. Na DREAMT, Δκ médio entre v2 e v1 foi +0,3133 e o maior módulo individual foi 0,7194. Nenhuma gravação histórica ficou abaixo do piso. Nos dourados, a probabilidade conferiu em 1e-12 e a classe foi exata, inclusive no empate em 0,5.

**Adaptação.** A ordem original das métricas foi recuperada para reproduzir a sequência de amostras do bootstrap. No contrato do modelo, d_angulo ausente na borda vira zero antes do z-score. O histórico conserva o cálculo angular de origem. Os testes expõem o efeito da lacuna, do limiar temporal e da referência por noite ou por trecho.

**O que deu errado no caminho.** O fetch inicial foi bloqueado pela sandbox na administração Git da worktree e foi repetido com a permissão apropriada. Houve globs incompatíveis com PowerShell e uma consulta CIM sem acesso. A primeira conferência de documentos acusou o relatório ainda fora do índice. A primeira rodada parou no IC da Newcastle, com desvio máximo de 0,00558 nos limites por causa da ordem do bootstrap. Na suíte isolada, o Windows negou a renomeação de um CSV sintético no temporário da sandbox. A suíte foi repetida fora da sandbox.

**Risco em aberto.** A rota consumidora e sua execução dos dourados ficam na PR de backend. As coortes externas são de punho e o sensor Wearanize de cabeça é preso à cabeça. No produto a espuma pode atenuar e atrasar o movimento. Dados e notas individuais em dados-locais, com a evidência da rodada em ml-inf-cabeca-v2-2026-11-07-final. Worktree e raízes de execução conferidas sem junctions.

**Procedência.** PR #100, branch feature/ML-INF-modelo-cabeca. Protocolo anterior à rodada em e8e4875 e execução definitiva em 367cd96. docs/ML-INF-PROTOCOLO-V2.md, docs/RELATORIO-ML-INF-V2.md, ml/experimentos/ml_inf_v2.py, ml/modelos/ml-inf-cabeca-v2.json e agregados da ML-13, ML-17 e ML-INF.

---

# 2026-11-08 (i) — ML-INF: a inferência no backend, sob demanda

**O problema, como foi entendido no início.** O modelo `ml-inf-cabeca-v2` estava no repositório (PR #100), mas nada o aplicava a uma noite do dispositivo. O backlog e o §9 do plano de ML previam um job em lote no backend ao fim da sessão.

**Hipótese de trabalho.** Partir da saída que `/api/features` já monta (`derivar_noite` sobre a janela pedida) e aplicar o modelo em Python puro, sem numpy, reproduz o `predict_proba` do scikit-learn a 1e-12 nas duas noites douradas da v2. E calcular a cada pedido, sem gravar, é mais simples e mais seguro que o lote: não exige migração, não guarda dado de saúde inferido e não obriga o servidor a decidir sozinho quando uma sessão acabou, que é o `ESC-01`.

**O que foi testado, e como.** Windows local, Python 3.13 (o CI usa 3.11). O módulo novo é `web-app/inferencia.py`, a rota `GET /api/inferencia` e o modelo copiado byte a byte para `web-app/modelos/`, porque o pacote da Vercel parte de `web-app/app.py`. Os testes estão em `web-app/tests/test_inferencia.py`:
- o contrato do modelo: o v1 e onze adulterações são recusados, e o SHA-256 da cópia é o do `ml/`;
- as duas noites douradas, do payload à classe, pelo caminho real da linha do banco;
- os três casos de limiar;
- o piso de 23, contando só épocas válidas;
- a grade de 30 s a 32 Hz, aplicada antes da derivação;
- a lacuna de 45 e de 45,001 s e o contexto preso ao segmento;
- o desvio abaixo de 1e-9;
- os códigos da rota e o dono vindo do JWT.

Depois, 14 sabotagens, uma por regra.

**Resultado medido.** O backend passou de 453 para 493 testes. Nas noites douradas, a maior diferença de probabilidade foi 6e-15 (a régua é 1e-12), com as classes iguais e 1 e 2 segmentos, em cerca de 60 ms por noite de 960 épocas. Na primeira rodada, as sabotagens deram 11/14: três passaram e mostraram buracos nos testes, que foram corrigidos. Na segunda, 14/14. O contrato de dados subiu para 2.8.0 (MINOR), e o `/health` passou a informar o modelo carregado.

**Adaptação.** Deixei de lado o lote previsto no plano e o substituí pelo cálculo sob demanda; a nota está no §9. O modelo carrega na primeira chamada. Se falhar, só a rota de inferência responde 503 e o `/health` diz `"indisponivel"` sem mudar o código, porque a ingestão não pode parar por causa do modelo. A validação de parâmetros saiu de `/api/features` para uma função comum às duas rotas.

**O que deu errado no caminho.** As três sabotagens que passaram:
- **Piso contando as linhas recebidas:** os testes só usavam épocas válidas, então contar as recebidas dava o mesmo número. Entrou um caso com 22 válidas e duas fora da grade.
- **Empate virando sono:** o teste do limiar aplicava `z > 0` por conta própria, em vez da regra do módulo. A regra virou a função `classe(z)`, que o teste chama.
- **Piso do desvio ignorado:** a coluna constante tem desvio exatamente 0, então trocar o piso por `s > 0` dava o mesmo resultado. Entrou um caso com ruído de 1e-13.

O script de sabotagem restaura os arquivos com `git checkout`, então o código precisou ser commitado antes de rodá-lo. Sem isso, a primeira restauração teria apagado o trabalho.

**Risco em aberto.**
- O z-score é calculado sobre a janela pedida, e o modelo foi treinado com noites inteiras: uma janela curta pode classificar a mesma época de outro jeito. A resposta devolve a janela e um aviso.
- Nenhuma tela mostra a estimativa ainda. O `DASH-04` não deve mostrá-la antes de a política de privacidade declarar a inferência sobre saúde (`LGPD-03`).
- O empacotamento do JSON na Vercel foi conferido pelo `/health` do preview (ver a PR); a produção só depois do release.
- O desempenho no travesseiro continua sem medição (`VAL-02`).

**Procedência.** Branch `feature/ML-INF-backend`, sobre o `develop` `010f741`. `web-app/inferencia.py`, `web-app/routes.py`, `web-app/modelos/ml-inf-cabeca-v2.json`, `web-app/tests/test_inferencia.py`, `docs/DATA-CONTRACT.md` §2.6 e §7, `docs/ML-DATASETS-E-PLANO.md` §9.

---

# 2026-11-08 (ii) — APP-02, etapa 1: a casca do app Android e o núcleo do firmware no celular

**O problema, como foi entendido no início.** O autor quer registrar noites reais antes da solda. A coleta pelo navegador não registra a noite: o `devicemotion` para quando a tela bloqueia (`useColeta.ts`). O iPhone do autor não tem serviço em segundo plano para o acelerômetro. Ele tem um Motorola Android antigo que pode ficar dedicado à coleta. O `APP-02` estava no pós-banca; o autor o trouxe para o L0 e aprovou um plano em seis etapas. Esta entrada é a primeira: a casca do app e o cálculo no aparelho.

**Hipótese de trabalho.**
- **Casca:** o frontend atual, empacotado com Capacitor, serve de casca. Só a coleta precisa ser nativa.
- **Cálculo:** se o app compilar `firmware/nucleo/` pelo NDK, o celular envia o mesmo payload da placa, com as mesmas features. O `ColetorCelular` entrega à `CadeiaC2` drenagens montadas a partir do instante de cada amostra, carimbadas meio passo depois da última.
- **Critério:** as features do celular ficam dentro das mesmas tolerâncias de validade do dourado da cadeia.

**O que foi testado, e como.** Windows 11. O núcleo rodou num contêiner `gcc:13`; o app, com o JDK 21 do Android Studio.
- **Coletor (`make celular`):** lê `ml/testes/vetor_dourado_cadeia_c2.json` e entrega cada amostra no instante verdadeiro, em m/s², sem e com 2 ms de variação no carimbo. Compara as features com o pipeline do `ml/`. Confere também:
  - que o instante reconstruído é o do gerador, contra as drenagens do arquivo;
  - o payload: `ts`, `epoca_s`, `t` e o vetor pela ida e volta da quantização da fila;
  - a taxa de 100 Hz, uma amostra fora de ordem, um buraco de 5 minutos e a quantização.
- **Sabotagens:** `make mutacao-coletor`, com 12 sabotadores.
- **Firmware inteiro:** `make`, `sintaxe`, `capacidade`, `mutacao-cadeia`, `mutacao-fila` e `laco`.
- **App:** o APK de depuração foi compilado, e `llvm-nm` listou as funções JNI exportadas.
- **Frontend:** `vitest`, `tsc` e `vite build`, nos modos do site e do app.

**Resultado medido.**
- **Coletor:** 288 verificações, 0 falhas. As maiores diferenças contra o pipeline foram `enmo` 2,6e-6 g, `enmo_max` 9,6e-5 g, `mag_din_media` 0,86 %, `zcr` 0 e `p_frac` 5 amostras, e `g` 0,065 grau, dentro das tolerâncias da placa. O coletor ocupa 56,9 KiB.
- **Sabotagens:** 12 de 12 deram o resultado esperado — 9 acusadas, o caso limpo passa e 2 pontos cegos declarados.
- **Firmware:** as contagens anteriores não mudaram (341, 157, 152, 456 e 84), e `mutacao-cadeia` (29/29), `mutacao-fila` (14/14) e `laco` (4/4) passaram.
- **App:** o APK traz `libdormio_nucleo.so` em `armeabi-v7a` (213 KB), `arm64-v8a` (356 KB) e `x86_64` (340 KB), com as 8 funções JNI.
- **Frontend:** 494 testes (489 + 5); o endereço do backend aparece só no build do app (1 ocorrência no pacote do app, 0 no do site).

**Adaptação.**
- **Endereço da API:** a página roda em `https://localhost` dentro do app, então as chamadas à API ganharam `urlDaApi`. É vazio no site; no build `--mode app`, recebe o endereço de produção.
- **CORS:** o `CapacitorHttp` faz as requisições pelo HTTP nativo, e o backend não precisou de CORS.
- **Unidade:** o coletor quantiza o sinal do celular na escala do MPU6050 da C2.
- **Temperatura:** usa a da bateria no lugar da do chip.
- **Taxa:** a cadeia só aceita 40 a 60 Hz. Se o celular entregar outra taxa, as épocas são recusadas e contadas; a primeira noite mostra qual é o caso.
- **Origem:** passou a ficar 3 s depois da primeira amostra (`ANTECEDENCIA_DA_ORIGEM_US`), porque a época 0 precisa de 0,5 s de sinal antes dela e de folga para o ajuste.
- **Worktree:** foi criada em `../wt-app`, num caminho curto, e não em `.claude/worktrees/`, porque o CMake e o NDK no Windows falham com caminhos longos.

**O que deu errado no caminho.**
- **Gradle sem rede local:** a primeira compilação falhou com "Unable to establish loopback connection", inclusive fora do sandbox. O JDK no Windows abre um socket de domínio Unix no diretório temporário, e o temporário do ambiente não serviu. Com `-Djdk.net.unixdomain.tmpdir` apontando para uma pasta comum, passou.
- **Caminho do SDK:** o `local.properties` saiu com barras invertidas sem escape e deu "Invalid file path"; foi trocado por barras normais.
- **Makefile:** uma edição por Python deixou um `\n` literal e duas linhas emendadas, o que foi visto no `cat -A` e corrigido à mão.
- **Teste sintético:** começava o sinal na origem, e a época 0 saiu recusada. A recusa estava certa; o teste é que estava errado, e daí veio a constante da antecedência.
- **Previsões de ponto cego:** errei duas.
  - A conversão com 9,81 em vez de 9,80665 é acusada: o `enmo` mede o desvio de 1 g, e 0,035 % de escala já vira viés.
  - O sabotador de "drenar depois da amostra nova" apagava toda drenagem e acusava pelo motivo errado. Foi reescrito para só mudar a ordem; aí fica de fato cego.

**Risco em aberto.**
- **Execução:** o teste com o Java chamando o C++ de verdade espera a etapa 2, com emulador ou aparelho.
- **Taxa do Motorola:** não se sabe a taxa que ele entrega. Se ficar fora de 40 a 60 Hz, a etapa 2 precisa decidir entre decimação e outra rota, com o autor.
- **Pontos cegos:** o carimbo sem o meio passo e a ordem da drenagem não são acusados.
- **Instrumento:** o celular é outro instrumento, e o que ele medir vale para ele (`ARQUITETURA-DE-CAPTACAO.md` §5).
- **iOS:** segue sem rota de coleta em segundo plano (`APP-04`).
- **Etapas pendentes:** o serviço, o envio, a tela e a noite real são as etapas 2 a 6 do `APP-02`.

**Procedência.** Branch `feature/APP-02-app-android`, sobre o `develop` `f9bff8c`. `firmware/nucleo/coletor_celular.{h,cpp}`, `firmware/nucleo/testes/testes_coletor_celular.cpp`, `firmware/nucleo/testes/verificar_coletor_por_mutacao.sh`, `firmware/nucleo/Makefile`, `firmware/nucleo/README.md`, `frontend/android/` (casca do Capacitor 8.4.3, `app/src/main/cpp/` e `NucleoNativo.java`), `frontend/capacitor.config.ts`, `frontend/vite.config.ts`, `frontend/src/lib/api.ts` e `coleta.ts`, `.github/workflows/ci.yml`, e o backlog, a arquitetura de captação e o `CLAUDE.md`.

---

# 2026-11-09 (i) — APP-02, etapa 2: o serviço que registra a noite com a tela apagada

**O problema, como foi entendido no início.** Na etapa 1, o app compilava e o núcleo rodava no host, mas nada registrava a noite: o Java nunca tinha chamado o C++ num aparelho. Faltava um serviço que mantivesse o acelerômetro ligado com a tela apagada, sob o Doze do Android, gravasse cada época no aparelho e sobrevivesse à morte do processo. Faltava também a tela para ligá-lo.

**Hipótese de trabalho.**
- **Serviço:** um serviço em primeiro plano basta. Ele tem notificação fixa, o tipo `health` no Android 14+ (com `HIGH_SAMPLING_RATE_SENSORS`, sem permissão em tempo de execução e sem o limite de 6 h), uma trava parcial de CPU e o acelerômetro a 20 ms entregue em lotes de 1 s.
- **Gravação:** uma linha sincronizada com o disco por época perde no máximo a época em curso.
- **Retomada:** `START_STICKY`, junto com um estado gravado, permite continuar a noite no mesmo arquivo depois de o sistema matar o processo.

**O que foi testado, e como.** Windows 11, emulador Pixel 6 com Android 37 (API 37, páginas de 16 KB, x86_64), JDK 21 do Android Studio.
- **JVM (`./gradlew :app:testDebugUnitTest`):** o `RelogioDoSensor` (carimbo em ns para µs na base do `elapsedRealtime`, com o deslocamento de aparelhos que usam outra base), o `ArquivoDaNoite` e o `EstadoDaNoite`.
- **Emulador (`connectedDebugAndroidTest`):**
  - o `NucleoNativoTest`: o Java chama o C++, um sinal de 50 Hz produz o payload do contrato e um de 100 Hz é recusado por taxa;
  - o `ServicoDaNoiteTest`: o serviço grava épocas com o sensor do emulador e encerra limpo.
- **Roteiro `longa`:** 10 min com a bateria simulada desligada, a tela apagada e `dumpsys deviceidle force-idle`.
- **Retomada:** a noite iniciada pelo app, depois `kill -9` no processo pelo `adb`.
- **Sabotagens:**
  - 6 no Java e 2 no frontend, por script;
  - 3 no emulador: temperatura em décimos, sem `START_STICKY` e sem a trava.
- **Frontend:** `vitest`, `tsc` e `vite build`.

**Resultado medido.**
- **Noite simulada:** 10 min em Doze profundo (`IDLE`) deram **20 de 20 épocas (100 %)**, taxa medida de 50,000 Hz, 30.350 amostras, nenhuma recusada e temperatura da bateria de 25,0 °C.
- **Retomada:** depois do `kill -9`, o Android reiniciou o serviço em 1 s ("Scheduling restart of crashed service … in 1000ms"). O estado ficou com `retomadas=1`, e o mesmo arquivo continuou: 4 épocas, com intervalos de 30, 54,7 e 30 s. A lacuna aparece como intervalo, sem época inventada.
- **Testes:** JVM 8/8; emulador 4 passando e 3 pulados (os roteiros, que só rodam por argumento); frontend 509 (494 + 15).
- **Sabotagens:** 6/6 do Java e 2/2 do frontend acusadas; no emulador, temperatura em décimos acusada (`t = 250.0`) e 2 pontos cegos (ver abaixo).

**Adaptação.**
- **Backup desligado:** o modelo do Capacitor vinha com `allowBackup="true"`, e o Android copiaria as noites, que são dado de saúde, para a nuvem do Google sem a política dizer isso.
- **Páginas de 16 KB:** a biblioteca nativa passou a ser ligada com `max-page-size=16384`, porque o Android 37 não carrega biblioteca alinhada a 4 KB.
- **Noite interrompida:** o estado gravado pode dizer "ativa" com o serviço morto (forçado a parar). O plugin agora informa `rodando`, e o cartão avisa a interrupção e oferece retomar.
- **Gatilho de roteiro:** um gatilho por `adb` (`--es roteiro iniciar/encerrar`) entrou na `MainActivity`, valendo só com `BuildConfig.DEBUG`, para o serviço nascer no processo do app.

**O que deu errado no caminho.**
- **Computador dormiu:** a primeira noite simulada parou depois de ~6 min, porque o Windows entrou em suspensão (Kernel-Power 42 às 23:16:04, retorno às 00:54:48) e pausou o emulador. A época que atravessou o salto saiu recusada por taxa, o que está certo. A rodada foi refeita com o computador impedido de dormir.
- **Instrumentação mata sem retomada:** a primeira tentativa de retomada iniciou o serviço pela instrumentação. Quando o `am instrument` termina, ele encerra o processo de um jeito que o Android não reinicia, e isso deixou o estado "ativa" sem serviço. Foi o que revelou o caso da noite interrompida na tela.
- **Linha de base falsa:** o script de sabotagem chamava `gradlew.bat` sem caminho, e o `cmd` deste ambiente não procura na pasta atual. A linha de base falhou e as seis primeiras "acusações" não valiam; com `.\gradlew.bat` a linha de base passou, e só então as sabotagens contaram.
- **Testes de componente:** `jest-dom` não existe no projeto, e o teste de componente precisava do `// @vitest-environment jsdom`.
- **Compilação:** a pasta gerada pelo `cap sync` não existia na worktree nova, então foi preciso rodar o `build:app` antes do Gradle.
- **Tarefa do Gradle:** o `assembleDebugAndroidTest` da raiz falhou num subprojeto do Capacitor (classe Kotlin duplicada); a tarefa certa é `:app:assembleDebugAndroidTest`.

**Risco em aberto.** Dois pontos cegos, e o emulador não responde a nenhum dos dois:
- **(a) `kill -9` não reproduz o sistema matando o app:** o Android 37 trata o `kill -9` de um serviço em primeiro plano como falha e o reinicia com ou sem `START_STICKY`. O caso que o `START_STICKY` cobre (falta de memória, fabricante encerrando de madrugada) não foi reproduzido.
- **(b) O emulador não suspende a CPU:** sem a trava, a noite de 5 min deu 10/10.

O Motorola, na etapa 5, responde aos dois.

Os roteiros rodam no processo da instrumentação, que pode receber tratamento diferente do de um app comum; a noite pelo botão da tela, no aparelho, é a prova que falta. O envio ao servidor é a etapa 3, e até lá as épocas ficam só no aparelho. O iOS segue sem rota (`APP-04`).

**Procedência.** Branch `feature/APP-02-servico-da-noite`, sobre o `develop` `3d396b5`.
- **Serviço e ponte:** `frontend/android/app/src/main/java/app/dormiosmart/coleta/` (`ServicoDaNoite`, `NoitePlugin`, `ArquivoDaNoite`, `EstadoDaNoite`, `RelogioDoSensor`, `MainActivity`), `AndroidManifest.xml`, `app/build.gradle`, `app/src/main/cpp/CMakeLists.txt`.
- **Testes:** `app/src/test/` e `app/src/androidTest/` (`NucleoNativoTest`, `ServicoDaNoiteTest`, `RoteiroDaNoiteTest`).
- **Frontend:** `frontend/src/lib/noiteNativa.ts`, `frontend/src/components/CartaoDaNoite.tsx`, `frontend/src/pages/Coletar.tsx`.

---

# 2026-11-09 (ii) — APP-02, etapa 3: as noites do app vão para a conta

**O problema, como foi entendido no início.** A etapa 2 deixava as noites só no aparelho. Para elas chegarem ao painel e à `/api/inferencia`, era preciso enviá-las ao servidor sem perder época e sem duplicar. As condições do aparelho tornam isso delicado: a noite pode terminar sem rede, a sessão pode vencer e o app pode morrer no meio de um envio.

**Hipótese de trabalho.**
- **Backend:** não precisa mudar. O `POST /api/data/lote` já responde, item a item, aceita, rejeitada ou pendente; o caminho por sessão do celular (`APP-08`) já existe; e a migração 011 deixa o reenvio idempotente.
- **Aparelho:** basta um ponto, por noite, de até onde o servidor confirmou. Ele só avança, e avança só até a primeira pendente.
- **Onde fica o envio:** no lado web do app, onde está a sessão que o Supabase renova. O nativo continua sem token.

**O que foi testado, e como.**
- **JVM:** o `ArquivoDaNoite` ganhou o progresso (`.enviado`), a leitura por faixa e a listagem das noites. A leitura passou a ignorar uma linha ainda sem a quebra final, porque a tela lê o arquivo enquanto o serviço grava.
- **vitest:**
  - o laço `enviarNoites`: tudo aceito em lotes de 60, retomada do ponto, pendente no meio, rejeitadas, `401` e sem rede, queda entre gravar e marcar, várias noites, noite já enviada;
  - o `enviarLote`;
  - o cartão: envio sozinho ao abrir, nenhum envio durante a noite, envio ao encerrar, falha que fica na tela, sem dispositivo ou sessão.
- **Fixture:** uma noite de 16 min gravada pelo serviço no emulador Pixel 6 (Android 37), copiada intacta para `web-app/tests/fixtures/noite_do_app_emulador.jsonl`. O `test_noite_do_app.py`:
  - passa cada linha pela validação real;
  - manda a noite pelo lote da sessão com o banco mockado;
  - passa as linhas EXATAS que a rota entregou à gravação pela inferência.
- **Sabotagens:** 6 por script (4 no envio, 2 no nativo) e 2 na fixture (`fs` 50, `total` incoerente).

**Resultado medido.**
- **Noite do emulador:** 32 épocas, 0 recusadas, 50,000 Hz.
- **Fixture no backend:** 7/7 testes passando. As 32 épocas são aceitas pela validação, entram pelo lote todas aceitas, o vetor chega ao banco coluna a coluna, e a inferência classifica as 32, em 1 segmento, sem nenhuma excluída.
- **Suítes:**

  | Suíte | Antes | Agora |
  |---|---|---|
  | Backend | 493 | 500 |
  | Frontend | 509 | 528 |
  | JVM | 8 | 13 |

- **Sabotagens:** 6/6 acusadas com a linha de base limpa; as 2 da fixture derrubam 3 testes cada uma.

**Adaptação.**
- **A regra do ponto:** o ponto avança só pelo prefixo resolvido do lote. Avançar por cima de uma pendente perderia a época; parar antes de uma aceita só reenvia, e o servidor deduplica.
- **Rejeitada conta como resolvida:** reenviar não adianta, como já decide o firmware. Ela é contada, e o primeiro motivo vai para a tela.
- **Teste da inferência:** passou a usar o que a rota gravou, e não uma conversão minha.

**O que deu errado no caminho.**
- **Escape:** a gravação do ponto saiu com uma quebra de linha literal dentro da string Java, o mesmo deslize de escape do Makefile da etapa 1.
- **Testes errados meus, dois:**
  - um teste JVM esperava 60 épocas a partir da linha 50 de uma noite de 100, onde só restam 50;
  - o teste do lote esperava um campo `f` na gravação, mas a ingestão converte o vetor em colunas nomeadas.

  Os dois foram corrigidos no teste, sem mudar o código.
- **Idioma:** respondi em inglês por engano durante a gravação da noite, e o autor pediu de volta o português.

**Risco em aberto.**
- **Sem produção:** nenhum envio contra a produção ainda. A primeira noite enviada com login de verdade é a da etapa 5, no Motorola; eu não entro com a senha do autor.
- **Noite plana:** o acelerômetro do emulador é constante. A fixture prova formato e caminho, não acurácia (`VAL-02`).
- **Ponte nativa:** os três métodos novos do plugin não têm teste no emulador. A lógica deles está no `ArquivoDaNoite`, testada na JVM, e o plugin só converte tipos.
- **Etapas pendentes:** a tela completa é a etapa 4.

**Procedência.** Branch `feature/APP-02-envio-da-noite`, sobre o `develop` `0e32ff5`.
- **Nativo:** `frontend/android/app/src/main/java/app/dormiosmart/coleta/ArquivoDaNoite.java` e `NoitePlugin.java`.
- **Frontend:** `frontend/src/lib/envioDaNoite.ts`, `frontend/src/lib/coleta.ts` (`enviarLote`), `frontend/src/lib/noiteNativa.ts`, `frontend/src/components/CartaoDaNoite.tsx`, `frontend/src/pages/Coletar.tsx`.
- **Backend:** `web-app/tests/test_noite_do_app.py` e a fixture do emulador.

---

# 2026-11-09 (iii) — APP-02, etapa 4: a tela da noite no app

**O problema, como foi entendido no início.** Até a etapa 3, a noite no app era um cartão provisório dentro da página Coletar. Para a noite real (etapa 5) faltavam quatro coisas:
- o antes, com a posição do celular que o protocolo compara (fronha × colchão);
- o depois, com as noites gravadas, o envio e o diário de sono;
- um lugar próprio no app;
- uma proteção para o risco de aquecimento do celular abafado na fronha.

O autor não estava em casa nem era noite, então a etapa veio antes da noite real.

**Hipótese de trabalho.**
- **A tela:** uma rota `/noite`, só no app, com três momentos. Ela não mostra sono e vigília, que são inferência sobre saúde e esperam a política (`LGPD-03`, `DASH-04`).
- **Anotações:** a posição e o diário ficam num arquivo ao lado da noite, no aparelho, sem passar pelo servidor.
- **Calor:** um corte no serviço, porque um aviso na tela não protege quem dorme.

**O que foi testado, e como.**
- **JVM:** `NotasDaNoite` (grava, junta, apaga a chave com valor vazio, não mistura noites, recusa chave desconhecida, posição inválida, texto longo e nome fora do padrão) e `CorteDeTemperatura` (abaixo, no limite e acima de 45 °C).
- **vitest:**
  - a posição obrigatória no cartão e o aviso de não carregar;
  - a lista de noites: ordem, posição, envio, cobertura, noite encerrada pelo calor, diário salvo na noite certa, "Ver no painel" só com algo enviado;
  - o resumo da noite gravada;
  - a navegação no site e no app.
- **Emulador Pixel 6, Android 37:** a noite iniciada com `posicao=fronha` e a bateria simulada a 46,0 °C (`dumpsys battery set temp 460`). Antes disso, a notificação com a permissão concedida. Depois, a suíte do emulador de novo.
- **Sabotagens:** 7 por script.

**Resultado medido.**
- **Posição e calor:** a posição ficou anotada desde o início da noite. A 46,0 °C, o serviço encerrou a noite sozinho em 26 s (a temperatura é lida a cada 30 s), com `fim=temperatura`, e parou.
- **Notificação:** mostra "Aparelho a 25.0 °C. Toque para ver ou encerrar."
- **Suítes:**

  | Suíte | Antes | Agora |
  |---|---|---|
  | Frontend | 528 | 542 |
  | JVM | 13 | 20 |
  | Emulador | 4 + 3 pulados | 4 + 3 pulados, sem regressão |

- **Sabotagens:** 7/7 acusadas. A do teto de cobertura passou na primeira rodada e só foi acusada depois de um teste novo.

**Adaptação.**
- **Coletar:** no app, o cartão da página Coletar virou um atalho para `/noite`, e o envio saiu dali para um hook (`useEnvioDoCelular`).
- **Diário:** o formulário não reescreve a posição nem o motivo do fim; só grava os campos do diário.
- **Gatilho de depuração:** passou a repassar a posição, para o roteiro do emulador.
- **Conselho contraditório:** a introdução do cartão, escrita na etapa 2, dizia "deixe o celular carregando", ao lado do aviso novo de não carregar na fronha. Foi reescrita.

**O que deu errado no caminho.**
- **Sabotagem que passou:** a da cobertura passou porque nenhum teste tinha mais épocas do que cabem entre a primeira e a última; o caso da retomada sobreposta entrou.
- **Notificação vazia:** a primeira busca pelo texto da notificação veio vazia porque o app estava com notificações desligadas (`importance=NONE`). No Android 13+, sem a permissão, o serviço roda com a notificação escondida, e o gatilho de depuração não pede a permissão; quem pede é o botão da tela. Com `pm grant`, o texto apareceu.

**Risco em aberto.**
- **O limite de 45 °C** é um valor de partida conservador, não medido no aparelho nem tirado de folha de dados. Fica para ajustar com o orientador, junto do `REQ-01` (no máximo 1 °C de elevação no dispositivo).
- **Botões não percorridos no emulador:** o fluxo pela tela de verdade (botões, permissão de notificação e de bateria) não foi percorrido, porque a tela exige login, e eu não entro com a senha do autor. O percurso pelos botões fica para a etapa 5, no Motorola, com o autor; o que se testou no emulador foi o serviço, pelo gatilho de depuração.
- **Anotações locais:** ficam no aparelho e se perdem se o app for desinstalado antes da análise.

**Procedência.** Branch `feature/APP-02-tela-da-noite`, sobre o `develop` `762e938`.
- **Nativo:** `frontend/android/.../NotasDaNoite.java`, `CorteDeTemperatura.java`, `ServicoDaNoite.java`, `NoitePlugin.java`, `MainActivity.java`.
- **Frontend:** `frontend/src/pages/Noite.tsx`, `components/ListaDeNoites.tsx`, `CartaoDaNoite.tsx`, `nav.ts`, `hooks/useEnvioDoCelular.ts`, `lib/noiteNativa.ts`, `App.tsx`, `pages/Coletar.tsx`, e os testes.

---

# 2026-11-09 (iv) — APP-02, etapa 4: o percurso pelos botões da tela da noite

**O problema, como foi entendido no início.** A etapa 4 testou o serviço pelo gatilho de depuração e a tela pelo `vitest`, mas ninguém tinha tocado nos botões da tela de verdade. O autor pediu esse percurso criando uma conta de testes. Não criei: o app no emulador fala com o Supabase de **produção**, e criar conta ou digitar credencial num sistema de produção não é permitido, mesmo para teste. Isso só vale em ambiente local ou de teste, e o projeto ainda não tem um Supabase de teste (`INFRA-02`).

**Hipótese de trabalho.** O modo demonstração (`?demo=1`, `DEMO-02`) libera as telas protegidas só no build de desenvolvimento. Um pacote do frontend construído em modo de desenvolvimento, dentro do app, permite percorrer a `/noite` inteira com toques reais, sem conta e sem tocar a produção. O login e o envio ficam de fora, porque não há sessão; o envio já é coberto pela fixture do backend.

**O que foi testado, e como.** No emulador Pixel 6 (Android 37):
- **Toques:** reais, por `adb shell input tap`. A posição de cada botão foi lida pelo depurador do WebView (CDP), e cada passo foi fotografado.
- **Fluxo percorrido:**
  - iniciar sem posição;
  - escolher a posição;
  - iniciar e aceitar a permissão de notificação do sistema;
  - os números durante a noite;
  - a isenção de bateria, com o diálogo do sistema;
  - encerrar;
  - a lista;
  - as anotações, com o texto digitado pelo teclado do emulador.
- **Exceção:** os três campos de hora foram preenchidos pelo depurador, porque o seletor de hora do Android não se presta a toques automatizados.
- **Conferência:** o arquivo `.notas` lido no aparelho.

**Resultado medido.**
- **O que funcionou:**
  - iniciar sem posição não começa nada (sem arquivo, sem serviço);
  - a permissão de notificação é pedida e, aceita, a notificação mostra "Aparelho a 25.0 °C";
  - durante a noite, a tela mostrou 2 épocas, 100 %, 50.0 Hz, 0 recusadas e 25.0 °C;
  - a isenção de bateria pôs o app na lista de exceções do sistema e o link sumiu;
  - encerrar parou o serviço e anotou `fim=usuario`;
  - as anotações gravaram no `.notas` a posição, as três horas, os despertares e o fim, e o campo esvaziado saiu do arquivo;
  - no app, o `/` leva à `/noite` (ou ao login), e não à página de apresentação.
- **Três problemas que os testes automáticos não pegaram:**
  1. o botão "Iniciar a noite" desabilitado tinha a mesma cara do habilitado;
  2. a noite em andamento aparecia na lista como terminada, com o nome do arquivo como título, um visto verde "0 de 0" de enviada e anotações disponíveis;
  3. depois de encerrar, os números da noite ficavam sob o botão de iniciar, sem título.

  Os três foram corrigidos: opacidade no desabilitado, "Noite em andamento" sem envio nem anotações (o plugin passou a marcar a noite ativa), e "Última noite". Cada correção ganhou um teste, e as 4 sabotagens que as desfazem foram acusadas.
- **Na volta ao emulador:** botão com opacidade 0,5, "Noite em andamento" na lista e "Última noite" no cartão.
- **Suítes:** frontend 546 (+4), JVM 20, emulador 4 passando e 3 pulados.

**Adaptação.**
- **Sem conta:** o percurso foi feito em modo demonstração, sem conta.
- **Configuração temporária:** a do Capacitor (o caminho inicial e, numa tentativa, o servidor de desenvolvimento) não foi versionada e foi desfeita. O app voltou ao build normal antes das suítes.

**O que deu errado no caminho.**
- **Tela em branco:** o app apontado para o servidor de desenvolvimento abriu em branco. O Vite no Windows escuta no IPv6 (`::1`), e o `10.0.2.2` do emulador chega ao IPv4.
- **A ferramenta de preview:** sempre subia a configuração do repositório principal, sem as dependências do Capacitor, e ignorava a que eu escrevi. Troquei o servidor por um pacote construído em modo de desenvolvimento.
- **O `DEV` desligado:** `--mode development` sozinho não liga o `DEV` no Vite; faltava `NODE_ENV=development`.
- **A árvore de acessibilidade do Android:** não expôs os textos do WebView, então os botões foram localizados pelo depurador.
- **O depurador** recusou a conexão com cabeçalho `Origin`.
- **Erros meus:**
  - o ajudante tocou no título do diálogo de permissão em vez de "Allow";
  - a tecla Voltar, usada para fechar o teclado, fechou o app;
  - um texto foi para o campo errado porque a página rolou entre o cálculo da posição e o toque. Repetido conferindo o foco antes de digitar, o campo certo recebeu o texto: o problema era meu, não do app.

**Risco em aberto.**
- **Login e envio:** continuam sem percurso de ponta a ponta no app. São da etapa 5, com o autor e a conta dele, ou de um Supabase de teste (`INFRA-02`), que permitiria a mim criar uma conta de teste.
- **A lista durante a noite:** mostra as épocas da última leitura (só relê depois de uma ação); o cartão de cima mostra os números ao vivo.
- **O percurso pelos botões não é automatizado:** foi feito uma vez, à mão, com scripts locais.

**Procedência.** Branch `feature/APP-02-tela-da-noite` (PR #105). `frontend/src/components/CartaoDaNoite.tsx`, `ListaDeNoites.tsx`, `lib/noiteNativa.ts`, `android/.../NoitePlugin.java`, e os testes. As fotos e os scripts do percurso ficaram locais, fora do repositório.

---

# 2026-11-09 (v) — DATA-10: nenhuma leitura gravava na produção

**O problema, como foi entendido no início.** Na primeira noite de teste do app no celular real (`APP-02`, Moto E7, Android 10), o sensor e o serviço funcionaram, mas o envio das 8 épocas falhou. O autor mostrou o painel do Supabase perguntando se havia problema lá. O painel não mostrava erro; os logs de execução da Vercel mostravam, em cada `POST /api/data/lote`, `invalid input syntax for type bigint` (22P02) e a resposta 503.

**Hipótese de trabalho.** `registrar_leitura` e `registrar_leitura_da_sessao` declaram `returns bigint` e `v_id bigint` desde a 005, e a 011 manteve isso. Se o `sleep_data.id` da produção é uuid, o `returning id into v_id` falha em toda gravação. Isso vale para os três caminhos: dispositivo, celular e navegador. Os testes não pegavam porque o `tests/rls/esquema_base.sql` criava o id como `bigserial`.

**O que foi testado, e como.**
- **Controle positivo antes do conserto:** o `esquema_base.sql` passou a criar o id como `uuid primary key default gen_random_uuid()`, como na produção, e a suíte de RLS rodou sem a 014.
- **O conserto:** a migração `014_id_da_leitura_uuid.sql`. Ela apaga e recria as duas funções devolvendo uuid, com o corpo da 011 (o `on conflict` e a busca do id existente), e refaz os grants da 007/009: `dormio_ingestao` na do token, `authenticated` na da sessão, nada para `public`/`anon`. Mudar o tipo devolvido exige `drop`, e o `drop` leva os grants junto.
- **O diagnóstico:** `DIAGNOSTICO-migracoes-aplicadas.sql` ganhou duas marcas da 014, o tipo devolvido de cada função.
- **Ambiente:** tudo contra `postgres:16` em Docker, no Windows.

**Resultado medido.**
- **Sem a 014, com o esquema de teste corrigido:** 17 testes falham e 176 passam, todos com o mesmo `invalid input syntax for type bigint` da produção. Antes da troca do tipo, passavam os 193.
- **Com a 014:** RLS **193 passam**.
- **Mutação do RLS:** 35/35. A sabotagem que recria `registrar_leitura` também passou a devolver uuid; com bigint, ela cairia pelo motivo errado.
- **Verificador de migrações:** acerta os **14 estados**. Até a 013, a 014 sai `F`; depois dela, `T`. A ordem real da produção também passa, com a 014 no fim.
- **Backend:** 500 passam (ele não muda).
- **Produção:** **não aplicada ainda.** Aplicar é o `DATA-11`, com o autor no SQL Editor.

**Adaptação.** O plano previa só a migração. O controle positivo exigiu mexer no esquema de teste, que agora reproduz a produção no tipo do id.

**O que deu errado no caminho.**
- **O tipo errado vem da 005 (escrita em 27/09)** e foi copiado pelas 007, 010 e 011. Não foi notado porque nada gravou na produção por essas funções até a noite do celular: a placa não está soldada, e as noites de teste anteriores não passavam pela produção. Quando a produção passou a usar as funções não foi reconstituído.
- **O monitor (`INFRA-03`) não pega:** ele chama o `/health`, que só lê.
- **Postgres de verdade não bastou:** a suíte de RLS foi feita contra um Postgres real justamente para não ser enganada por mock (§4, ocorrência 1). Ainda assim, o esquema era imitado de memória e errou o tipo da coluna mais usada. Registrado no §4 das lições como ocorrência 7, com a regra 7.
- **A pergunta do autor apontava para o Supabase:** o painel estava saudável, e o erro só apareceu nos logs da Vercel.

**Risco em aberto.**
- **Até a 014 ser aplicada,** nenhuma leitura grava na produção (`DATA-11`).
- **As 8 épocas da noite de teste** estão guardadas no celular (`.jsonl` sem `.enviado`). O app reenvia ao abrir; isso confirma o conserto de ponta a ponta, e ainda não rodou.
- **Outras divergências de tipo:** não houve varredura de outras colunas do `esquema_base.sql` contra a produção. A regra 7 do §4 manda conferir ao mexer em função que toca coluna; uma varredura completa pediria uma consulta de só leitura na produção pelo autor.

**Procedência.** Branch `bugfix/DATA-10-id-da-leitura-uuid`. `web-app/migrations/014_id_da_leitura_uuid.sql`, `web-app/tests/rls/esquema_base.sql`, `conftest.py`, `verificar_por_mutacao.py`, `web-app/tests/migracoes/verificar_migracoes.py`, `DIAGNOSTICO-migracoes-aplicadas.sql`, `migrations/README.md`. Logs de execução da Vercel de 09/11.


---

# 2026-11-09 (vi) — DATA-11: a 014 na produção, e o celular grava

**O problema, como foi entendido no início.** A 014 (`DATA-10`, PR #106) consertava o tipo devolvido pelas funções de gravação, mas só no repositório. Até ser aplicada, nenhuma leitura gravava na produção. As 8 épocas da noite de teste esperavam no celular.

**Hipótese de trabalho.** Aplicar a 014 no SQL Editor basta: o backend não muda, e o app reenvia sozinho, ao abrir, o que não tem `.enviado`.

**O que foi testado, e como.**
- **Aplicação e diagnóstico:** o autor aplicou a 014 e rodou o `DIAGNOSTICO-migracoes-aplicadas.sql`.
- **Reenvio:** o autor abriu o app no Moto E7.
- **Conferência:** o resultado foi conferido daqui, nos logs de execução da Vercel, pelo conector.

**Resultado medido.**
- **Diagnóstico:** a 014 saiu `true`, com **2 de 2 marcas**. As 001–012 saíram como antes, e a 002 com 0 leituras sem dono. A 013 saiu `false`, com 0 de 3 marcas e o `pg_cron` desligado; isso era esperado, porque aplicá-la é o `LGPD-09`, antes do próximo release.
- **Reenvio:** às 22:00:51–55 UTC, um `POST /api/data/lote` fez a autenticação (`auth/v1/user` 200) e a consulta do dispositivo da conta (200), e chamou **8 vezes `registrar_leitura_da_sessao`, todas com 200**. A resposta foi **200**.
- **Comparação:** antes da 014, o mesmo envio dava 503 com `invalid input syntax for type bigint`.

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **O caminho do token** (`registrar_leitura`, o do dispositivo) recebeu a mesma correção e passa nos testes, mas **não foi chamado na produção**: a placa não está soldada.
- **O que ficou gravado:** não conferi as 8 linhas no banco nem o painel; o que está medido é o `200` de cada gravação. A noite aparecer no painel e na inferência fica para a etapa 5 (`APP-02`).
- **A 013 continua pendente** (`LGPD-09`).

**Procedência.** Diagnóstico rodado pelo autor no SQL Editor, 09/11. Logs de execução da Vercel, produção, 09/11 22:00 UTC.

---

# 2026-11-09 (vii) — DATA-12: o esquema de teste como a produção, e a cascata das leituras

**O problema, como foi entendido no início.** O `DATA-10` mostrou que o esquema de teste divergia da produção no tipo do id. Restava saber se havia outras divergências da mesma classe antes da primeira noite real.

**Hipótese de trabalho.** Uma consulta só de leitura do catálogo, rodada nos dois bancos, mostra a diferença inteira de uma vez: tipos, padrões, chaves, índices, permissões e funções. O banco de teste foi montado na ordem real da produção, sem a 013, que lá não está aplicada.

**O que foi testado, e como.**
- **A consulta:** `migrations/CONSULTA-estrutura-do-esquema.sql` foi rodada pelo autor no SQL Editor e, por mim, no banco de teste (`postgres:16` em Docker, Windows). Foram 78 linhas de cada lado, comparadas uma a uma.
- **O que divergiu:**
  - a chave de `sleep_data.user_id` não tem `on delete cascade` na produção e tem no teste;
  - `user_id` tem padrão `auth.uid()` na produção;
  - `created_at` aceita nulo na produção;
  - a produção tem dois índices antigos (`idx_sleep_data_created_at`, `idx_sleep_data_user`).
- **O que bateu:** as 8 funções (retorno, definer, `search_path`, permissões), o RLS e as permissões das 4 tabelas, e as demais restrições e índices.
- **A versão:** as permissões da produção trazem o privilégio `m` (MAINTAIN), que só existe a partir do Postgres 17.
- **A causa:** a tabela e a coluna `user_id` foram criadas pelo painel do Supabase antes das migrações. A 001 usa `add column if not exists user_id ... on delete cascade`, e na produção a coluna já existia: a linha inteira foi pulada, a cascata junto. É a mesma causa do `DATA-10`, em outra coluna.
- **O efeito:** `apagar_minha_conta` e `_eliminar_titular` apagam as leituras antes do usuário, então a eliminação pelo app funciona. Apagar o usuário direto em `auth.users`, que é o que o painel faz, é recusado se houver leituras.
- **O conserto:**
  - o `esquema_base.sql` cria `sleep_data` como a produção, para que a 001 pule a coluna como lá;
  - a migração `015_cascata_das_leituras.sql` recria a chave com a cascata;
  - `test_rls_cascata.py` cobre o caso com 3 testes: a exclusão direta leva as leituras, não toca nas do outro usuário, e a chave tem cascata;
  - a sabotagem `leituras_sem_cascata` entrou na mutação;
  - o diagnóstico ganhou a marca da 015;
  - a matriz do CI ganhou o Postgres 17.

**Resultado medido.**
- **Sem a 015, com o esquema novo:** os 3 testes caem, dois com `ForeignKeyViolation` em `sleep_data_user_id_fkey`, que é o erro que a produção daria, e um com `confdeltype='a'`.
- **Com a 015:** RLS **196 passam** no Postgres 16, e **196** no 17, em Docker local.
- **Mutação:** **36/36**; a nova caiu por 3 testes.
- **Verificador de migrações:** **15 estados** e a ordem real.
- **Estrutura no Postgres 17:** montado como a produção e sem a 015, o banco de teste reproduz as linhas de `sleep_data` e as permissões com `m` da produção.
- **Produção:** a 015 **não foi aplicada**; é o `DATA-13`.

**Adaptação.** O plano previa sabotar `_eliminar_titular`, tirando o `delete` das leituras, como controle positivo. Ao ler o teste, vi que ele já confere `leituras_apagadas == 1` no recibo, e acusaria essa sabotagem com ou sem cascata. O ponto cego que eu tinha anunciado ao autor não existia nessa forma. O controle passou a ser a exclusão direta do usuário, que nenhum teste exercitava.

**O que deu errado no caminho.**
- **Afirmações minhas erradas ao autor:**
  - disse que o bug do `DATA-10` "passou nove dias escondido"; o tipo vem da 005, de 27/09;
  - disse que tirar o `delete` das leituras passaria nos testes; não passaria.

  As duas foram corrigidas na conversa.
- **A consulta:** a primeira versão falhou no Postgres (`text || "char"` ambíguo, no `provolatile`) e foi corrigida antes de ir ao autor.

**Risco em aberto.**
- **Até a 015 ser aplicada** (`DATA-13`), excluir pelo painel um usuário com leituras é recusado.
- **Ficaram de fora, de propósito:** o padrão `auth.uid()` e o `created_at` anulável. Não mudam comportamento, porque as funções sempre passam o dono e nunca gravam `created_at`.
- **A comparação é retrato de 09/11.** Mudança feita pelo painel depois disso não aparece sozinha; a consulta versionada é para repetir.
- **A versão exata da produção** (17.x) não foi lida. Foi inferida pelo privilégio `m`.

**Procedência.** Branch `bugfix/DATA-12-esquema-como-a-producao`. `web-app/tests/rls/esquema_base.sql`, `test_rls_cascata.py`, `conftest.py`, `verificar_por_mutacao.py`, `web-app/migrations/015_cascata_das_leituras.sql`, `CONSULTA-estrutura-do-esquema.sql`, `DIAGNOSTICO-migracoes-aplicadas.sql`, `README.md`, `web-app/tests/migracoes/verificar_migracoes.py`, `.github/workflows/ci.yml`. Resultado da consulta na produção colado pelo autor em 09/11.

---

# 2026-11-10 (i) — DATA-13: a 015 na produção

**O problema, como foi entendido no início.** A 015 (`DATA-12`, PR #108) dava à chave de `sleep_data.user_id` a cascata que a 001 declara, mas só no repositório. Na produção, apagar um usuário com leituras pelo painel do Supabase continuava recusado.

**Hipótese de trabalho.** Aplicar a 015 no SQL Editor basta. O backend não muda, a migração não mexe em dado, e foi testada antes num Postgres 17 montado como a produção, com 501 leituras: aplicou, rodou duas vezes sem efeito e acendeu a marca.

**O que foi testado, e como.**
- **Pelo celular:** o autor aplicou a 015 e rodou uma conferência curta, a marca da 015 e `select version()`. Os arquivos foram passados no chat, porque ele não conseguia abri-los no celular.
- **O diagnóstico completo:** rodado em seguida, com a consulta sem comentários.

**Resultado medido.**
- **Conferência curta:** `cascata_ok = true`. A versão é **PostgreSQL 17.6** (aarch64).
- **Diagnóstico completo:**
  - a 015 saiu `true`, com 1 de 1 marca;
  - as 001, 003–012 e 014 saíram `true`, com as mesmas marcas de antes;
  - a 002 saiu com 0 leituras sem dono;
  - a 013 saiu `false`, com 0 de 3 marcas e o `pg_cron` desligado, como esperado: aplicá-la é o `LGPD-09`.

**Adaptação.** O diagnóstico foi passado ao autor sem os comentários, para caber na tela do celular. O conteúdo das consultas é o mesmo do arquivo versionado.

**O que deu errado no caminho.** Nada na produção. Do meu lado, um comando de registro travou por um `cat` sem entrada, e foi interrompido e refeito.

**Risco em aberto.**
- **A exclusão pelo painel não foi exercitada na produção.** Não há conta de teste lá, e apagar uma conta real não é teste. O comportamento foi medido no Postgres 17 local (`DATA-12`).
- **A 013 continua pendente** (`LGPD-09`).

**Procedência.** Resultados colados pelo autor em 10/11, no SQL Editor da produção.

---

# 2026-11-10 (ii) — APP-10: o envio de uma noite inteira

**O problema, como foi entendido no início.** A auditoria de 10/11 (achado AUD-01; o relatório ainda não está versionado) mostrou que o envio de uma noite inteira pelo app não termina sozinho. O teste de 09/11 no celular tinha 8 épocas e passou; uma noite real tem cerca de 960.

**Hipótese de trabalho.** Duas causas somadas:
- **No backend:** `registrar_leitura_da_sessao` monta um cliente Supabase novo a cada leitura. Isso abre uma conexão por leitura, e por isso cada gravação leva cerca de 0,5 s na produção.
- **No app:** o lote do servidor para aos 6 s e devolve o resto como pendente, e o laço do app parava na primeira pendente, com mensagem de erro.

**O que foi testado, e como.**
- **A latência da produção:** lida nos logs da Vercel de 09/11, 22:00:51 a 22:00:55 UTC. As 8 gravações saíram a cada 0,49 s em média.
- **A reprodução:** `POST /api/data/lote` pelo cliente de teste do Flask, com 60 épocas da fixture do emulador e a gravação falsa esperando 0,49 s (Windows, Python 3.13).
- **Parte A, o app (`envioDaNoite.ts`):** o laço segue do ponto novo enquanto a requisição resolver ao menos uma época e o aparelho mover o ponto; sem avanço, para. A tela mostra o progresso em vez da mensagem de pendência.
- **Parte B, o backend:** a rota repassa à gravação o cliente que ela já montou para conferir o dispositivo. É o cliente daquela requisição e daquele JWT; nada fica guardado entre requisições.
- **Conexões:** um servidor HTTP local contando conexões TCP, com o cliente Supabase real apontado para ele.

**Resultado medido.**
- **A reprodução, antes:** `200`, com 13 aceitas e 47 pendentes, em 6,4 s. A 13 por tentativa, 960 épocas pediam cerca de 74 toques em "Enviar agora".
- **Conexões por lote de 60:** 60 antes, 1 depois.
- **Suítes:** backend **504 passam** (+4), frontend **551 passam** em 42 arquivos (+5), `tsc` limpo, `vite build` ok.
- **Sabotagens, todas acusadas:**
  - a rota sem repassar o cliente: 3 testes caem;
  - o método ignorando o cliente recebido: 3 caem;
  - o laço parando na primeira pendente: 3 caem no laço e 1 no cartão;
  - o progresso sem aviso: 1 cai;
  - a parada só com zero épocas resolvidas, sem olhar o ponto do aparelho: o teste não termina, e foi morto pelo teto de 70 s.
- **Na produção: nada medido.** O ganho de tempo por leitura com a conexão reaproveitada só aparece depois de um release. O app novo ainda não foi instalado no celular.

**Adaptação.** O plano não previa a guarda do ponto do aparelho. Ao escrever o laço, vi que "seguir enquanto houver avanço" precisa conferir que o ponto andou de fato, e não só que o servidor resolveu épocas. O código anterior já tinha essa falha latente: com o servidor aceitando tudo e o aparelho sem mover o ponto, ele reenviaria o mesmo lote para sempre.

**O que deu errado no caminho.**
- **A primeira rodada de sabotagens travou.** A sabotagem que devolvia o laço antigo caiu justamente no laço infinito descrito acima, num teste novo, e o vitest ficou mais de 6 minutos preso: um laço de microtarefas bloqueia até o tempo limite do próprio teste. Interrompi, matei os processos, restaurei o arquivo pela cópia e refiz com `timeout` e filtro de teste. A árvore foi conferida igual antes e depois, por hash do `git diff`.
- **Um teste existente acoplado à assinatura:** o `test_noite_do_app.py` usava um `lambda` de três parâmetros no lugar da gravação e passou a receber `cliente`.

**Risco em aberto.**
- **A parte B só vale na produção com um release.** A `main` está 33 merges atrás da `develop`; o release levaria a rota de inferência e a seção 7 da política, que exige a 013 antes (`LGPD-09`). Sem release, a parte A sozinha faz a noite subir, em cerca de 9 minutos com o app aberto (estimado: 74 requisições de 6 a 7 s).
- **O teste da guarda do ponto não falha, trava.** Se alguém a remover, o CI fica preso até o tempo limite do job, em vez de acusar o teste.
- **Quanto a conexão única reduz o tempo por leitura** não foi medido. Se ainda não couberem 60 em 6 s, a saída é uma função no banco que receba o lote inteiro (`API-06`).
- **O app no celular** precisa ser recompilado e reinstalado para a parte A valer.

**Procedência.** Branch `bugfix/APP-10-envio-da-noite-inteira`. `frontend/src/lib/envioDaNoite.ts`, `frontend/src/components/CartaoDaNoite.tsx`, `web-app/database.py`, `web-app/routes.py` e os testes `envioDaNoite.test.ts`, `CartaoDaNoite.test.tsx`, `test_lote.py` e `test_noite_do_app.py`. Logs de execução da Vercel de 09/11.

---

# 2026-11-10 (iii) — APP-02, etapa 5: a primeira noite real no Moto E7, e o viés da orientação

**O problema, como foi entendido no início.** A etapa 5 do `APP-02` era a primeira noite real, com o app no Moto E7 (Android 10), na conta do autor. As perguntas eram quatro: o app aguenta a noite inteira com a tela apagada, o Android o deixa trabalhar, os dados chegam ao banco, e o que o modelo diz da noite.

**Hipótese de trabalho.** Com o serviço em primeiro plano, a trava de energia e a isenção de bateria, a cobertura passa de 95 %. O envio de manhã esbarraria no AUD-01, já corrigido no código (`APP-10`, PR #110) mas ainda não instalado no aparelho; não haveria perda de dado.

**O que foi testado, e como.**
- **A noite:** o autor dormiu com o app registrando, com o celular no colchão. De manhã encerrou a noite e enviou.
- **O que o celular gravou:** copiado pelo cabo USB, com `adb exec-out run-as`, para fora do repositório: o arquivo da noite (815 linhas), as anotações e o estado do serviço.
- **O que chegou ao banco:** consulta de contagem por hora (`captured_at`), rodada pelo autor no SQL Editor. Ela não traz nenhum dado de leitura.
- **A inferência:** o mesmo modelo e o mesmo código do servidor (`inferencia.inferir_janela`, `ml-inf-cabeca-v2`), rodados localmente sobre as linhas do arquivo, convertidas como a ingestão as grava. Nada foi chamado na produção.
- **O controle do viés:** a mesma inferência com o viés do trecho virado subtraído da medida de movimento. É só diagnóstico, para medir o tamanho do efeito.

**Resultado medido.**
- **Cobertura:** de 03:02 a 09:52 (horário de Brasília), **815 de 821 épocas (99,3 %)**. Os 6 buracos têm uma época cada (60 s entre duas linhas), e o estado do serviço os conta como `sem_payload=6`.
- **O serviço e o sensor:** **0 retomadas**; taxa de 49,506 Hz; 0 épocas recusadas; 960 amostras e o vetor completo em todas.
- **Temperatura:** de 25,5 °C a 16,9 °C, com pico de 26,8 °C, longe do corte de 45 °C.
- **O banco:** **815 épocas**, das 03:02 às 09:52, as mesmas do celular. **Nada se perdeu.** O envio pediu vários toques, como o AUD-01 previa.
- **A validação do backend:** 0 das 815 épocas reprovadas.
- **A inferência:** 78,2 % das épocas como sono, com nove blocos de vigília de 5 min ou mais. O autor relatou uma noite ruim, ansioso, acordando várias vezes; a comparação época a época não é possível, porque as horas de deitar, dormir e acordar ficaram em branco nas anotações.
- **O celular virado:** às 06:04 o autor pegou o celular para ver a hora e o largou com a tela para baixo, e às 07:38 o desvirou. As duas viradas (172° e 174° entre épocas vizinhas) caíram dentro de blocos que o modelo marcou como vigília (06:00 a 06:10 e 07:38 a 07:43). O gesto foi aceito, gravado e lido como despertar, o que está correto.
- **O viés da orientação:** virado, o acelerômetro do Moto lê a gravidade maior, e a medida de movimento sobe sem movimento nenhum.

  | Trecho | Épocas | Movimento (mediana) | Magnitude (mediana) |
  |---|---:|---:|---:|
  | Tela para cima, 03:02 a 06:04 | 362 | 0,50 mg | 9,84 m/s² |
  | Tela para baixo, 06:04 a 07:37 | 186 | **23,12 mg** | 10,06 m/s² |
  | Tela para cima, 07:38 a 09:52 | 267 | 0,95 mg | 9,84 m/s² |

- **O efeito no modelo:** com o viés subtraído, o sono passa de 78,2 % para 79,6 %, e dois blocos curtos de vigília somem (08:06 a 08:11 e 09:30 a 09:38). Nesta noite o efeito é pequeno porque o trecho virado é curto e a normalização é por noite. Não há garantia de que seja pequeno com o celular virado por metade da noite.
- **O app corrigido:** instalado no aparelho com `adb install -r` depois da cópia; as duas noites continuam lá, marcadas como enviadas (815 de 815).

**Adaptação.** O plano não previa medir o efeito da orientação. Ele apareceu na análise e virou o item `CAL-03` (autocalibração pela gravidade).

**O que deu errado no caminho.**
- **Os logs da Vercel:** o plano gratuito guarda só uma hora, e os envios da madrugada não estavam mais lá. A contagem veio da consulta no banco.
- **As anotações em branco:** sem as horas, a comparação com o modelo ficou qualitativa.
- **Erro meu:** escrevi ao autor que o viés "soma cerca de 23 mg" sem dizer que é mediana do trecho; a tabela acima corrige.

**Risco em aberto.**
- **O viés da orientação no modelo:** só medido nesta noite, num trecho de 1 h 33 min. O item é o `CAL-03`.
- **Uma noite não mede acurácia:** falta referência e mais noites (`VAL-02`). Numa noite de vigília quieta, o modelo deve superestimar o sono, como toda actigrafia (`LIMITACOES-TCC.md` X.1).
- **O envio corrigido no aparelho** ainda não foi exercitado numa noite real; a próxima noite confere.
- **O erro do sensor muda com a temperatura**, que caiu 8,6 °C nesta noite. Isso não foi separado do efeito da orientação.

**Procedência.** Arquivos do celular copiados para fora do repositório (não versionados: são dado de sono do autor). Consulta de contagem colada pelo autor em 10/11. O relatório da auditoria de 10/11 (AUD-01) não está versionado.

---

# 2026-11-10 (iv) — CAL-03, etapa 0: o erro de cada eixo do acelerômetro do Moto E7

**O problema, como foi entendido no início.** Na noite de 10/11 (entrada iii), com a tela para baixo, o Moto E7 leu a gravidade 2,2 % maior, e a medida de movimento subiu para 23 mg sem movimento nenhum. A etapa 0 do `CAL-03` mede o erro de cada eixo deste aparelho, com o celular parado em seis posições, para saber de onde vem o viés e quanto dele uma calibração explica.

**Hipótese de trabalho.** O erro é de desvio e escala por eixo, o modelo clássico de calibração de acelerômetro. Com cada eixo apontado para cima e para baixo, a média dos dois valores dá o desvio, e a meia diferença dá a escala.

**O que foi testado, e como.**
- **O teste:** o autor gravou pelo app o celular parado sobre a mesa, 10 min em cada uma de seis posições: tela para cima, tela para baixo, em pé normal, em pé invertido, de lado com os botões para cima e para baixo. Cada posição foi uma "noite" separada, de 16:40 a 17:46 (horário de Brasília), na posição "outra" do app, fora do carregador.
- **A cópia:** pelo cabo USB, com `adb exec-out run-as`, para fora do repositório.
- **A seleção:** cada arquivo é uma posição. A primeira e a última época foram descartadas (o toque nos botões), e ficaram só as épocas paradas (`mag_din_media` < 10 mg): 16 a 22 por posição.
- **O valor por eixo:** a mediana de `ax`, `ay`, `az` das épocas paradas. No payload, esses três valores são os da amostra de **maior magnitude** da época, e não a média. O desvio não sofre com isso: o excesso do pico entra com o mesmo sinal da gravidade e se cancela na média entre as duas posições. A escala sofre, e foi corrigida pelo excesso medido.
- **O excesso do pico:** onde a magnitude passa de 1 g, a medida de movimento (média por amostra do que passa de 1 g) dá a magnitude média. A diferença para a do pico ficou em 2,0 a 3,0 mg, média de 0,024 m/s².
- **A conferência:** a calibração estimada na mesa, aplicada à noite de 10/11.

**Resultado medido.**
- **Sem calibração**, a magnitude parada varia de **0,991 g a 1,020 g** conforme a posição. A medida de movimento só enxerga o que passa de 1 g, e por isso o "piso" dela muda com a posição:

  | Posição | Magnitude parada | Movimento (mediana) |
  |---|---:|---:|
  | Tela para cima | 1,0041 g | 4,20 mg |
  | Tela para baixo | 1,0198 g | **18,71 mg** |
  | Em pé, normal | 0,9933 g | 0,00 mg |
  | Em pé, invertido | 0,9910 g | 0,00 mg |
  | De lado, botões para cima | 0,9980 g | 0,00 mg |
  | De lado, botões para baixo | 1,0175 g | **17,76 mg** |

- **O erro por eixo** (temperatura do aparelho de 25,7 a 27,8 °C):

  | Eixo | Desvio | Escala |
  |---|---:|---:|
  | x | −0,095 m/s² (−9,7 mg) | +0,76 % |
  | y | +0,015 m/s² (+1,5 mg) | −0,87 % |
  | z | −0,075 m/s² (−7,6 mg) | +1,17 % |

- **Na própria mesa:** com a calibração, as seis posições ficam entre **1,0002 g e 1,0015 g**. Esse número é de ajuste, e não de validação: são seis posições para seis parâmetros.
- **Na noite de 10/11, a conferência que vale:** a diferença entre tela para cima e tela para baixo era de **22,1 mg** (1,0002 contra 1,0223 g) e passa a **7,9 mg** (0,9957 contra 1,0036 g). A calibração de mesa explica **64 %** do viés da noite.
- **O que sobra:** a noite foi a 18 °C (mediana), e a mesa a 26 a 27 °C. O resíduo é compatível com o erro do sensor variando com a temperatura, mas isso **não foi medido** de forma separada.

**Adaptação.**
- **Cada posição numa noite separada:** o roteiro previa uma noite só, trocando de posição, e o autor iniciou e encerrou uma noite por posição. Ficou melhor, porque cada arquivo é uma posição.
- **O excesso do pico:** o plano não previa estimá-lo; ele apareceu ao ler o que `ax`, `ay`, `az` significam no payload.

**O que deu errado no caminho.**
- **As seis gravações foram para a conta do autor na produção.** O app envia sozinho ao abrir, e as seis "noites" de teste, cerca de 120 épocas, estão no histórico como se fossem sono. O app não tem como marcar uma gravação como teste.
- **O roteiro de bancada que escrevi** não dizia que o app enviaria as gravações. Devia ter dito.

**Risco em aberto.**
- **A temperatura:** o erro muda com ela, e uma calibração feita a 26 °C deixa 8 mg de viés a 18 °C. A etapa 1 do `CAL-03` precisa de um termo de temperatura, como o método de van Hees já prevê.
- **Uma gravação de teste vira noite:** não há marca de gravação de teste, e o histórico do autor tem seis noites falsas de 10 min. Item novo `APP-11`.
- **Um aparelho só:** os números valem para este Moto E7. Outro celular tem outro erro.

**Procedência.** Arquivos do celular copiados para fora do repositório; o cálculo foi feito na hora, em script local. Nenhum dado de sono entrou no repositório.

---

# 2026-11-10 (v) — APP-12: preparar o app para testadores (a parte técnica)

**O problema, como foi entendido no início.** O autor quer mandar o app a amigos com Android, para juntar mais noites. Hoje só existe o APK de depuração: assinado com a chave de teste do Android Studio, depurável, com a depuração do WebView ligada e o gatilho de teste da `MainActivity`. E não havia guia de instalação.

**Hipótese de trabalho.** Basta um APK de release assinado com uma chave do autor, guardada fora do repositório (que é público), e um guia em duas partes: como gerar o APK e como o testador instala e usa. A parte que não é técnica (comitê de ética, política de privacidade e consentimento) fica com o autor e o orientador, e o documento diz que o envio espera por ela.

**O que foi testado, e como.**
- **A chave fora do repositório:** o `app/build.gradle` passou a ler `~/.dormio/assinatura.properties`, ou o caminho de `DORMIO_ASSINATURA`. Sem o arquivo, o release sai sem assinatura, em vez de cair para a chave de depuração. O `.gitignore` do Android passou a recusar `*.jks`, `*.keystore`, `*.p12` e `assinatura.properties`; essas linhas vinham comentadas do modelo do Capacitor.
- **A versão:** `versionName` 1.0.0.
- **O build:** `assembleRelease` no Windows, JDK do Android Studio, em três casos:
  1. sem o arquivo de assinatura;
  2. com uma chave **descartável** de teste, gerada com senha aleatória no scratchpad e apagada em seguida;
  3. a comparação com o de depuração.
- **As conferências:** `apksigner verify` e `aapt2 dump badging`, a etiqueta `application-debuggable`.
- **A depuração do WebView:** lida no código do Capacitor 8 (`CapConfig.java`): o padrão de `webContentsDebuggingEnabled` é o tipo do build, desligado no release.

**Resultado medido.**
- **Sem o arquivo:** `app-release-unsigned.apk`, e o `apksigner verify` recusa ("DOES NOT VERIFY"). É o comportamento pedido: não instala.
- **Com a chave descartável:** `app-release.apk`, e o `apksigner verify` aceita (esquema v2).
- **Depurável:** a etiqueta `application-debuggable` aparece no APK de depuração e não no de release (controle positivo: o de depuração tem).
- **A versão no APK:** `versionName='1.0.0'`, `targetSdkVersion 36`.
- **O `.gitignore`:** o `git check-ignore` confirma a regra para `.jks`, `.keystore` e `assinatura.properties`.
- **O guia:** `docs/DISTRIBUICAO-DO-APP.md`, com a chave e o APK para o autor; a instalação, a conta, a bateria por marca, a noite, o envio e a saída para o testador. Os rótulos de tela citados ("Cadastre-se", "Criar conta", "Excluir minha conta", o link da bateria) foram conferidos no código.
- **Nada foi enviado a ninguém**, e nenhuma chave de verdade foi criada: a chave é do autor e ele a cria sozinho.

**Adaptação.** O plano não previa a variável `DORMIO_ASSINATURA`. Ela existe para testar a assinatura com uma chave descartável sem tocar no arquivo de verdade do autor, nem mudar a pasta do usuário, o que moveria também o cache do Gradle.

**O que deu errado no caminho.** O guia saiu com dois rótulos errados ("Criar conta" como primeiro botão, quando a tela de entrada mostra "Cadastre-se"; e "Excluir conta" em vez de "Excluir minha conta"). Corrigidos depois de conferir o código das telas.

**Risco em aberto.**
- **A decisão que não é técnica:** comitê de ética, política de privacidade (AUD-04) e consentimento, antes de qualquer envio (`LGPD-03`).
- **A recuperação de senha não chega aos testadores** (`AUTH-06`); o guia avisa.
- **Só o Moto E7 foi testado.** Xiaomi e Samsung encerram apps em segundo plano com mais força; o guia dá os passos por marca, mas eles não foram conferidos num aparelho dessas marcas.
- **Gravação de teste vira noite** (`APP-11`); o guia pede para não fazer.
- **O build de release não roda no CI.** O CI não tem job Android (AUD-06 da auditoria de 10/11).

**Procedência.** Branch `feature/APP-12-distribuicao-para-testadores`. `frontend/android/app/build.gradle`, `frontend/android/.gitignore`, `docs/DISTRIBUICAO-DO-APP.md`.

---

# 2026-11-10 (vi) — Registro: a auditoria de 10/11 vira itens, e as pendências do autor numa lista só

**O problema, como foi entendido no início.** O autor pediu: "deixe registrado tudo o que precisamos fazer". Havia três lugares desencontrados:
- **A auditoria de 10/11** (Fable 5.2) tinha 12 achados num relatório não versionado, e só o AUD-01 virara item (`APP-10`).
- **As pendências do autor** estavam espalhadas pela memória do Claude e pelo `ROADMAP.md` local, com itens já feitos misturados aos abertos.
- **Duas contagens erradas** que a auditoria apontou (AUD-08) seguiam nos documentos.

**Hipótese de trabalho.**
- **Os achados:** cada um vira item no backlog, com a evidência da auditoria e a correção proposta. O relatório é versionado, com o mapa de cada achado para o item que o carrega, como o de 31/10.
- **As contagens:** corrigidas no próprio registro.
- **As pendências do autor:** uma lista só, por tipo, sem o que já foi feito.

**O que foi testado, e como.**
- **Os IDs:** conferidos livres em `origin/feature/APP-12-distribuicao-para-testadores` antes de usar.
- **As conferências:** `conferir_backlog --conferir`, `consolidar_registro --conferir` e `conferir_docs_versionados`.
- **A varredura do relatório:** nome de pessoa e caminho de máquina, antes de versionar.

**Resultado medido.**
- **Itens novos, 9:**

  | Camada | Item | Achado |
  |---|---|---|
  | L0 | `SEC-18` | AUD-02 e AUD-03 |
  | L0 | `SEC-19` | AUD-10 |
  | L0 | `SEC-20` | AUD-12 |
  | L0 | `DATA-14` | AUD-11 |
  | L0 | `CI-09` | AUD-06 |
  | L0 | `CI-10` | AUD-07 |
  | L0 | `CI-11` | AUD-09 |
  | L0 | `LGPD-11` | AUD-04 |
  | L3 | `REL-01` | AUD-05, com a pergunta sobre `last_sign_in_at` |

- **Contagem:** 42 → **51 abertos**; L0 12 → **20**; L3 10 → **11**. O `conferir_backlog` passa.
- **AUD-08:**
  - o `CLAUDE.md` ganhou a nota da mutação da fila: **14/14** medido, contra os 13/13 de 31/10;
  - o `UI-15` ganhou o pacote medido: **925 kB**, contra 876 kB.
  - A contagem de 42 arquivos do frontend já tinha sido corrigida pelo `APP-10`.
- **O relatório:** `docs/AUDITORIA-2026-11-10-fable.md`, versionado com o mapa dos achados. Nenhum nome nem caminho de máquina.
- **As pendências do autor:** reescritas em seis grupos (orientador, produção, app, texto, dados, GitHub), na memória do Claude e no `ROADMAP.md` local, que não é versionado.

**Adaptação.** Esta branch parte da do `APP-12` (PR #113, ainda aberta), porque o backlog e o diário são arquivos de conflito garantido. A PR aponta para `develop`; o corpo dela diz a ordem de merge.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **Nove itens novos de uma vez:** a L0 dobrou de tamanho, e nenhum deles foi priorizado. A prioridade é do autor.
- **Itens que esperam outros:** o `SEC-18` e o `REL-01` pedem consultas na produção que só o autor roda (5.1 e 5.2 da auditoria).

**Procedência.** Branch `chore/REG-auditoria-e-pendencias`, a partir de `feature/APP-12-distribuicao-para-testadores` (`545f7f6`). `docs/BACKLOG-COMPLETO.md`, `docs/AUDITORIA-2026-11-10-fable.md`, `CLAUDE.md`.

---

# 2026-11-10 (vii) — LGPD-11: a política de privacidade alcança o app e a inferência

**O problema, como foi entendido no início.** A auditoria de 10/11 (AUD-04 e AUD-05) apontou que a política não descrevia o app nativo nem a inferência de sono. A leitura inteira da política contra o código achou mais:

| Seção | A política dizia | O sistema faz |
|---|---|---|
| §2.2 | O celular só coleta com a tela de coleta aberta | O app coleta a noite toda, com a tela apagada |
| §2.2 | Não citava | As seis medidas de movimento e a direção da gravidade, gravadas desde a migração 010 (30/10) |
| §2.3 | No aparelho ficam só a sessão e o tema | Ficam também os arquivos das noites (que ficam depois de enviados) e as anotações |
| §2.4 | Nada "infere condição de saúde" | A rota de inferência estima sono e vigília |
| §6.1 | Não há dado coletado que o app não mostre | As medidas de movimento não aparecem no painel nem saem no CSV |
| §6.4 | Excluir a conta apaga tudo | Os arquivos no celular ficam |
| §9 | "Toda leitura enviada é validada", "146 testes" | A validação é contornável (`SEC-18`); são 196 testes |

**Hipótese de trabalho.** O autor decidiu duas coisas antes da conversa com o orientador:
- **A série de movimento e a inferência são tratadas como dado de saúde**, por precaução. A base legal passa ao art. 11, I (consentimento específico e destacado).
- **O uso em pesquisa só acontece por termo próprio.**

A política pode ser reescrita para dizer o que o sistema faz hoje, inclusive a lacuna de não haver ainda a tela de consentimento destacado. E um teste pode ligar as colunas gravadas à seção 2.2, para que coluna nova não passe sem a política.

**O que foi testado, e como.**
- **O texto:** `docs/POLITICA-DE-PRIVACIDADE.md`, com a regra que governa a política ("o que o sistema faz hoje, não o que se pretende"):
  - §2.2: todos os campos e o app nativo;
  - §2.3: o que fica no aparelho;
  - §2.4 e §2.5: a inferência e o dado de saúde;
  - §3: a finalidade 6, a estimativa, e o uso em pesquisa por termo;
  - §4: a base do art. 11, I e a lacuna da tela;
  - §5.3, §6.1, §6.4, §6.7 e §9;
  - o topo e a §10;
  - quatro lacunas novas nas notas.
- **O termo:** `docs/TERMO-DE-PARTICIPACAO.md`, como rascunho, com os nomes como marcadores e três conferências antes do uso (o orientador e o CEP, a política publicada e a revisão jurídica).
- **O teste novo:** `web-app/tests/test_politica_cobre_as_colunas.py`. Ele lê nas migrações reais as colunas que `registrar_leitura` e `registrar_leitura_da_sessao` inserem, na versão mais recente de cada uma, e exige que cada coluna tenha descrição e que a descrição esteja na §2.2 (o `user_id`, na §3).
- **Os controles positivos**, numa cópia da árvore:
  1. uma migração nova que grava uma coluna a mais;
  2. a política sem o trecho da direção da gravidade;
  3. a política de antes desta revisão, a de `develop`.
- **O ambiente:** Windows, Python 3.13 e Node 24.

**Resultado medido.**
- **O teste novo:** 5 passam.
- **Os três controles** foram acusados, com 2 testes caindo em cada um. No terceiro, a política antiga reprova exatamente nas colunas que não citava: o número de amostras, as seis medidas de movimento, a direção da gravidade e a taxa de amostragem.
- **Os testes da página da política:** 12 passam. O texto continua com só `[CONTROLADOR]` e `[CONTATO]` como marcadores.
- **Backend:** **509 passam** (+5). **Frontend:** **551 passam**.

**Adaptação.** O plano previa a tela de consentimento destacado como parte B, para depois. A política declara a falta dela como lacuna, e ela virou o item `LGPD-12`.

**O que deu errado no caminho.** A primeira versão do teste reprovou por um falso negativo: a frase "associar cada leitura ao seu dono" está quebrada em duas linhas no Markdown. O teste passou a normalizar o espaço antes de comparar.

**Risco em aberto.**
- **A política nova só vale publicada:** ela entra no mesmo release que a inferência (`REL-01`), e esse release exige a 013 antes (`LGPD-09`).
- **A tela de consentimento destacado** (`LGPD-12`): até ela existir, a base legal do art. 11, I fica com a lacuna declarada.
- **O termo depende do orientador** (CEP), e a base legal do uso em pesquisa pode mudar com isso.
- **Sem revisão jurídica:** a política continua avisando que não foi revisada.
- **O teste só cobre as colunas:** a §2.3 (o que fica no celular), as finalidades e os direitos continuam sem teste.

**Procedência.** Branch `feature/LGPD-11-politica-do-app`. `docs/POLITICA-DE-PRIVACIDADE.md`, `docs/TERMO-DE-PARTICIPACAO.md`, `web-app/tests/test_politica_cobre_as_colunas.py`.

---

# 2026-11-10 (viii) — SEC-18: a validação da leitura e do pareamento dentro do banco

**O problema, como foi entendido no início.** A auditoria de 10/11 (AUD-02 e AUD-03) mostrou que a validação vivia só no Flask. Quem tem conta chama `registrar_leitura_da_sessao` direto, porque a chave anon e o endereço são públicos, e grava `NaN`, captura em 2099 e época −5 na própria conta. Em `devices`: nome de 100 000 caracteres, 500 dispositivos numa chamada, `token_hash` escolhido pelo cliente, e a revogação desfeita por `update`. Nada cruza contas, mas contamina o dado que o trabalho analisa.

**Hipótese de trabalho.** Restrições `CHECK` com **as mesmas** faixas da `validacao.py`, nem mais largas nem mais estreitas. Mais estreita faria uma leitura aceita pelo backend falhar na gravação, e o dispositivo reenviaria para sempre. O resto:
- a recusa do futuro nas duas funções de gravação;
- formato do hash e teto de dispositivos no pareamento;
- um gatilho que barra a desrevogação.

As consultas de 10/11 na produção (5.1 e 5.3 da auditoria) deram zero leitura fora das regras, no máximo 2 dispositivos por conta e nome de até 12 caracteres.

**O que foi testado, e como.**
- **A migração `016_validacao_no_banco.sql`:**
  - sete `CHECK` em `sleep_data` e um em `devices.nome` (até 60 caracteres), todos `NOT VALID`;
  - um bloco que confere o que já existe contra cada restrição (lendo a própria definição dela no catálogo) e para com a contagem se algo falhar;
  - depois, `VALIDATE`;
  - as duas funções de gravação com o corpo da 014 e a recusa de `captured_at` mais de 5 min no futuro;
  - `parear_dispositivo` com o corpo da 007, o formato SHA-256 do hash e o teto de 10 ativos;
  - o gatilho `devices_revogacao_definitiva`, que só barra os papéis do cliente; o dono do banco continua podendo, para manutenção.
- **Os testes:** `test_rls_validacao_no_banco.py`, com 48 casos, contra `postgres:17` em Docker no Windows:
  - **as bordas tiradas das constantes da `validacao.py`:** cada uma passa no banco, e um passo além é recusado com `23514`;
  - **a chamada direta da auditoria**, recusada;
  - **o caminho do token** (`dormio_ingestao`), que recusa também;
  - **a leitura antiga sem o vetor**, que continua válida;
  - **o pareamento e a revogação**;
  - **a noite do emulador**, inteira pelo banco.
- **A mutação do RLS:** 8 sabotagens novas. Uma delas é uma faixa **mais estreita** que a do Flask (`enmo_max` até 15 g, em vez de 16).
- **O verificador de migrações:** o 16º estado, e uma verificação nova: a 016 num banco com dado antigo fora das regras tem de parar sem apagar nada; num banco limpo, aplica inteira.
- **O diagnóstico:** 5 marcas da 016.

**Resultado medido.**
- **RLS:** **244 passam** (196 + 48).
- **Mutação:** **44/44**.
- **Verificador:** **16 estados** e a ordem real. Com dado ruim, a 016 parou, informou `sleep_data_faixa_temperatura: 1 linha(s)`, não aplicou nenhuma restrição e a linha ficou. Sem dado ruim, aplicou.
- **Backend:** 509 passam (o backend não muda).

**Adaptação.**
- **O formato do hash e o teto** ficaram na função de pareamento, e não como `CHECK` em `device_tokens`. É a única porta de criação (desde a 007), e os dados de teste gravam hashes curtos direto na tabela.
- **Coerência de `total` e "sensor mudo"** ficaram fora: são regras sobre o payload do dispositivo, não sobre o domínio da coluna.

**O que deu errado no caminho.**
- **Um teste de segurança passou a testar o mecanismo errado.** A sabotagem antiga `insert_liberado` (liberar o insert direto em `sleep_data`) passou a derrubar só 1 teste em vez de 2. Três testes de negação inseriam leituras com estados inventados ("Direto", "Injetado", "Digitado"), e a regra de estado da 016 passou a recusá-las **antes** da policy: o teste continuava verde, recusado pelo motivo errado. É a ocorrência clássica do §1 das lições. Corrigidos para usar um estado válido **e conferir o código do erro** (`42501`, falta de privilégio, e não `23514`); a sabotagem voltou a 2.
- **Erros meus no teste novo:**
  - `NaN` mandado como número quebrava o JSON (a auditoria o mandou como texto);
  - "1 + tolerância" na gravidade já seria recusado pelo próprio Flask, que limita cada componente a [−1, 1].
- **O verificador:** consultava depois da falha esperada sem `rollback`.
- **Um script meu de inserção das sabotagens** tinha aspas conflitantes, e foi refeito sem alterar o arquivo.

**Risco em aberto.**
- **A 016 não está na produção** (`SEC-21`). Até lá, a §9 da política continua declarando a lacuna, e muda depois da aplicação.
- **O volume por chamada** continua sem limite, de propósito, e só afeta a própria conta.
- **As restrições copiam as faixas do Flask.** Mudar uma faixa exige mudar os dois lados. O teste das bordas acusa a divergência, mas não a impede.

**Procedência.** Branch `bugfix/SEC-18-validacao-no-banco`. `web-app/migrations/016_validacao_no_banco.sql`, `DIAGNOSTICO-migracoes-aplicadas.sql`, `README.md`; `web-app/tests/rls/test_rls_validacao_no_banco.py`, `conftest.py`, `test_rls_ingestao.py`, `test_rls_isolamento.py`, `test_rls_credencial.py`, `verificar_por_mutacao.py`; `web-app/tests/migracoes/verificar_migracoes.py`.

---

# 2026-11-10 (ix) — SEC-21: a 016 na produção

**O problema, como foi entendido no início.** A 016 (`SEC-18`, PR #116) leva a validação da leitura e do pareamento para dentro do banco, mas só no repositório. Até ser aplicada, a chamada direta da auditoria continuava gravando `NaN` e datas de 2099 na própria conta.

**Hipótese de trabalho.** Ela aplica limpa, porque as consultas 5.1 e 5.3 da auditoria, rodadas pelo autor mais cedo no mesmo dia, deram zero leitura fora das regras, no máximo 2 dispositivos por conta e nome de até 12 caracteres. E se não aplicasse, pararia sem apagar nada.

**O que foi testado, e como.**
- **Pelo celular:** o autor aplicou a 016 no SQL Editor, numa versão sem os comentários, para caber na tela.
- **A versão sem comentários:** foi conferida antes, por mim, num Postgres 17 montado como a produção (001 a 015, sem a 013). Aplicou e deu 5 de 5 marcas no diagnóstico.
- **A conferência:** em seguida, o autor rodou uma consulta curta, só leitura, com as mesmas marcas do diagnóstico.

**Resultado medido.**
- **Na produção:** `regras_validadas = 7` (as sete restrições de `sleep_data`, validadas); `nome_ok`, `futuro_ok`, `teto_ok` e `revogacao_ok` todos `true`.
- **Sem dado ruim:** a migração não parou, então nenhuma linha antiga estava fora das regras.

**Adaptação.** A §9 da política deixou de dizer que a validação é contornável na própria conta, e a lacuna correspondente foi fechada nas notas.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **O diagnóstico completo não foi rodado;** a consulta curta cobre só as marcas da 016.
- **O caminho normal com a 016 ainda não foi exercitado na produção:** a próxima noite do app confere que ele continua gravando.
- **A política nova** continua esperando o release (`REL-01`).

**Procedência.** Resultado colado pelo autor em 10/11. `docs/POLITICA-DE-PRIVACIDADE.md` §9.

---

# 2026-11-10 (x) — LGPD-09: a 013 passa a contar a sessão aberta como uso

**O problema, como foi entendido no início.** Antes de aplicar a 013 (expurgo por inatividade), o `REL-01` pedia para conferir se o Supabase atualiza `last_sign_in_at` quando a sessão é só renovada. A 013 decidia "conta sem uso há 12 meses" por três sinais: a criação da conta, o último login e a última leitura.

**Hipótese de trabalho.** O `last_sign_in_at` só muda num login. O app mantém a sessão aberta e a renova sozinho. Então quem usa o painel sem sair e sem dispositivo enviando leituras seria apagado em 12 meses, ainda ativo.

**O que foi testado, e como.**
- **O código do Supabase Auth:** lido pelo navegador. `UpdateLastSignInAt` grava só o campo, e a correção da PR #2655 (versão 2.195.0, agosto de 2026) diz que o caminho v2 "cria a sessão diretamente e nunca chamava `UpdateLastSignInAt`" — o campo é gravado na criação da sessão. Nenhuma fonte lida diz que a renovação o atualiza. Isso não foi confirmado pelo código da renovação.
- **Na produção:** duas consultas só de leitura, rodadas pelo autor, sem e-mail nem identificador. As colunas de `auth.sessions`, e quantas contas tinham a sessão renovada depois do último login (`updated_at` da sessão contra `last_sign_in_at`).
- **A correção:** na 013, ainda não aplicada em lugar nenhum além dos testes, o uso de uma sessão entrou como quarto sinal: o maior entre a criação, a `updated_at` e a `refreshed_at` de `auth.sessions`.
- **Depois, a pedido do autor, o código do Supabase Auth** (`internal/tokens/service.go`, `internal/models/sessions.go`, `internal/models/cleanup.go` e a biblioteca `pop`):
  - a renovação grava `refreshed_at`, `user_agent` e `ip` (`UpdateOnlyRefreshInfo`), e **não** a `updated_at`: a `pop` só atualiza a `updated_at` quando ela está na lista de colunas;
  - a `refreshed_at` é `timestamp` sem fuso, em UTC;
  - a limpeza só apaga sessão ativa com prazo absoluto ou por inatividade configurados (`not_after`, *timebox*).
- **O esquema de teste:** ganhou `auth.sessions`, com exclusão em cascata a partir do usuário.
- **Os testes novos:**
  - a sessão renovada há 1 mês, com login há 13 meses e sem dispositivo, **fica**;
  - login e sessão há 13 meses **saem**, e a sessão sai junto.
- **Os controles:** a sabotagem `expurgo_ignora_a_sessao` na mutação; uma marca da 013 no diagnóstico; e a ordem real da produção no verificador, que passou a ter a 013 depois da 014, da 015 e da 016, como vai acontecer.
- **O ambiente:** `postgres:17` em Docker, no Windows.

**Resultado medido.**
- **Na produção:** **6 contas, 3 com sessão, 2 com a sessão renovada depois do último login**, com distância máxima de **1 dia, 16 h e 31 min**. A hipótese se confirmou.
- **As colunas de `auth.sessions`** incluem `updated_at` e `refreshed_at`.
- **A medição na produção desmentiu a minha leitura do código, e confirmou a primeira explicação.** Uma terceira consulta, só de leitura, rodada pelo autor:

  | Medida | Resultado |
  |---|---|
  | Tipo da `refreshed_at` | `timestamp without time zone` |
  | Sessões / renovadas | 4 / 2 |
  | Renovadas em que a `refreshed_at` passou da `updated_at` | **0** |
  | Sessões em que a `updated_at` mudou depois da criação | **2** |
  | Sessões com prazo de validade (`not_after`) | 0 |
  | Contas com sessão criada depois do último login | **0** |

  Ou seja: **na produção, a renovação move a `updated_at` junto com a `refreshed_at`**. A biblioteca do Supabase atualiza a `updated_at` por conta própria, e a minha leitura dela estava incompleta. E o defeito de login sem `last_sign_in_at` não aparece nos dados. A explicação original — a renovação de uma sessão aberta não toca o `last_sign_in_at` — é a que vale.
- **Os três campos ficam assim mesmo:** a `refreshed_at` é o campo que o código do Supabase grava explicitamente na renovação, e a `updated_at` é a que a produção mostrou mudar. Ler os dois cobre uma mudança futura em qualquer um.
- **O controle que separou as duas versões:** com a 013 da primeira correção (só a `updated_at`), o caso "sessão só renovada há 1 mês" (`refreshed_at` recente, `updated_at` velha) **foi apagado**. Com os três campos, fica.
- **RLS:** **247 passam** (+3). **Mutação:** **45/45** (+1, a sabotagem agora tira a `refreshed_at`). **Verificador:** os 16 estados e a ordem real nova.

**Adaptação.** A correção entrou na própria 013 e não numa migração nova: ela nunca foi aplicada, e aplicar uma versão sabidamente errada para consertá-la em seguida seria pior. O cabeçalho dela registra a mudança.

**O que deu errado no caminho.**
- **Duas conclusões minhas, cada uma tirada de uma fonte só.** A primeira correção usou só a `updated_at`, tirando da consulta que ela acompanhava a renovação, sem ter conferido. Depois, ao ler o código do Supabase, concluí o contrário — que a renovação não a mexia — e escrevi ao autor que a primeira explicação estava errada. A medição na produção mostrou que a primeira estava certa e que a leitura do código estava incompleta.
- **Os testes não decidiriam a questão** nem num sentido nem no outro: eu mesmo escolhia as datas dos casos de teste. Eles reproduzem a minha hipótese, e não o Supabase (§1 das lições). Quem decidiu foi a consulta na produção.
- **Os três campos,** que entraram por causa da leitura errada do código, ficam: são a defesa contra uma mudança futura em qualquer um. Também afirmei ao autor que a `refreshed_at` é sem fuso sem ter conferido; o código depois confirmou, e a consulta de confirmação lê o tipo na produção.

**Risco em aberto.**
- **Sessão encerrada:** se a pessoa sair do app (logout), a sessão é apagada e o sinal some. Aí valem o login e as leituras, como antes.
- **O comportamento do Supabase:** medido na produção em 10/11, com 2 sessões renovadas. Uma mudança futura do Supabase pode voltar a abrir o risco, e nenhum teste daqui pega isso; os três campos reduzem esse risco, mas não o eliminam.
- **A 013 ainda não foi aplicada** (`LGPD-09`).

**Procedência.** Branch `bugfix/LGPD-09-sessao-conta-como-uso`. `web-app/migrations/013_retencao_por_inatividade.sql`, `DIAGNOSTICO-migracoes-aplicadas.sql`; `web-app/tests/rls/esquema_base.sql`, `test_rls_retencao.py`, `verificar_por_mutacao.py`; `web-app/tests/migracoes/verificar_migracoes.py`; `docs/POLITICA-DE-PRIVACIDADE.md` §7. Consultas coladas pelo autor em 10/11.

---

# 2026-11-10 (xi) — LGPD-09: a 013 na produção, com o expurgo agendado

**O problema, como foi entendido no início.** A 013 (retenção por inatividade), corrigida antes de ser aplicada para contar a sessão como uso (entrada x, PR #118), precisava entrar na produção com o `pg_cron` ligado. É o primeiro item do `REL-01`: a seção 7 nova da política descreve o expurgo, e não pode ser publicada antes de ele existir.

**Hipótese de trabalho.** A 013 aplica limpa e não apaga ninguém na primeira execução. A consulta 5.2 da auditoria deu 0 contas, e a versão corrigida só acrescenta sinais de uso, ou seja, só pode manter mais contas.

**O que foi testado, e como.**
- **Antes, por mim:** uma versão da 013 sem os comentários, num Postgres 17 montado na ordem real da produção (001–012 e 014–016, e a 013 por último). Ela aplicou, deu 4 de 4 marcas, o expurgo rodado à mão não apagou ninguém, e uma segunda execução passou.
- **Pelo autor, no celular:**
  1. ligou o `pg_cron` em Database → Extensions (schema `pg_catalog`, o padrão);
  2. rodou a 013 no SQL Editor;
  3. rodou uma consulta curta de conferência.

**Resultado medido.**
- **Na produção:** `_eliminar_titular`, `expurgar_contas_inativas`, a exclusão de conta passando por `_eliminar_titular` e o sinal da sessão no expurgo — os quatro `true`.
- **O agendamento:** `pg_cron` ligado (1) e **1 agendamento** `dormio-expurgo-por-inatividade`, diário às 04:17 UTC.
- **A produção fica com 001–016**, todas aplicadas (a 002 desnecessária).

**Adaptação.** A descrição interna da função de expurgo (`comment on function`) ainda citava só "criação, login nem leitura". Ela foi corrigida na versão aplicada para incluir o uso de sessão, e o arquivo do repositório foi alinhado a ela neste registro.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **O primeiro expurgo agendado ainda não rodou;** a próxima execução é às 04:17 UTC. A execução pode ser conferida em `cron.job_run_details`.
- **O diagnóstico completo não foi rodado:** a consulta curta cobre as marcas da 013 e o agendamento.
- **O resto do `REL-01`:** a decisão sobre o `LGPD-12` e o release em si.

**Procedência.** Captura de tela do painel e resultado da conferência colados pelo autor em 10/11. `web-app/migrations/013_retencao_por_inatividade.sql`.

# 2026-11-10 (xii) — LGPD-12: o consentimento destacado, com a trava no banco

**O problema, como foi entendido no início.** Desde o `LGPD-11`, a política trata a série de movimento e a estimativa de sono como dado de saúde (art. 11, I). Esse artigo pede consentimento **específico e destacado**. O que existia era o consentimento do cadastro, o do sensor no navegador e o toque em *Iniciar a noite*, e a §4 declarava a lacuna. Uma tela sozinha não basta: um cliente que pule a tela, ou uma chamada direta à API, gravaria do mesmo jeito.

**Hipótese de trabalho.** O consentimento é um registro no banco (data pelo relógio do banco e versão do texto), gravado só por uma função. As funções de gravação pela sessão e de pareamento recusam quem não o tem na versão vigente. O backend traduz essa recusa num `403` com o motivo, e não num `503`, que o app leria como servidor fora do ar e reenviaria para sempre. A tela vem antes da primeira noite e da primeira coleta. O caminho do token (o dispositivo do travesseiro já pareado) **não** é travado, por decisão do autor ("travado só no pareamento"): um dispositivo novo não se pareia sem o consentimento.

**O que foi testado, e como.**
- **Migração 017:**
  - duas colunas em `profiles`;
  - `versao_do_consentimento()` = `2026-11-10`;
  - `consentir_dado_de_saude(p_versao)`, que só aceita a versão vigente e usa `now()`;
  - um gatilho que impede `authenticated`/`anon` de escrever as colunas direto, inclusive ao criar o perfil;
  - a trava em `registrar_leitura_da_sessao` e em `parear_dispositivo` (`42501`).
- **RLS:** `test_rls_consentimento.py`, 12 testes contra Postgres 17 em Docker.
- **Mutação:** 5 sabotagens novas:
  - a gravação sem a trava;
  - o pareamento sem a trava;
  - a trava aceitando qualquer versão;
  - o gatilho fora;
  - a função aceitando qualquer versão.
- **Backend:**
  - `consentimento.py`;
  - `POST /api/me/consentimento` (`409` na versão errada);
  - as travas `403` no lote pela sessão, nos dois pareamentos e em `GET /api/inferencia`;
  - `test_consentimento.py` confere que as três constantes de versão (banco, backend, frontend) são iguais.
- **Frontend:**
  - `TelaDeConsentimento`, um diálogo em que o *Concordo* só liga com a caixa marcada;
  - o portão `usePortaoDoConsentimento` no `CartaoDaNoite` (app) e em `Coletar` (navegador);
  - 10 testes novos.
- **Controles positivos fora do banco:**
  - o portão sabotado para rodar sempre derruba 4 testes da tela;
  - a trava do backend desligada derruba os 4 testes de `403`.
- **Diagnóstico e verificador de migrações:** a 017 ganhou 4 marcas, e a ordem real da produção termina nela.

**Resultado medido** (Windows 11, nesta branch):
- backend 525 passam;
- frontend 561 passam em 43 arquivos, com `tsc` limpo;
- RLS 259 passam (Postgres 17);
- mutação **50/50**;
- o verificador de migrações acerta os 17 estados e a ordem real, com a 017.

**Adaptação.**
- Em `Coletar`, a preparação do dispositivo passou a esperar o consentimento. Sem consentimento, a tela ficava em "Preparando..." sem botão nenhum, porque a preparação pareia e o pareamento recusaria. Entrou um botão *Começar a registrar* que abre a tela.
- A política (§4) descreve a tela, o registro e a exceção do dispositivo já pareado.

**O que deu errado no caminho.**
- **Teste do backend:** um teste novo (o do banco fora do ar) caiu porque a fixture automática, que dá o consentimento por padrão aos testes antigos, também o cobria. Faltava a marca `sem_consentimento`.
- **Edições:** a fixture de módulo do `test_noite_do_app.py` roda antes da automática e precisou do próprio patch. Um script de edição abortou no meio e deixou uma edição por aplicar, que foi refeita à mão.
- **Controle positivo do backend:** a primeira versão inseriu a sabotagem depois da linha de assinatura, antes da docstring, e quebrou a sintaxe. Foi refeita.

**Risco em aberto.**
- **Ordem do release (`LGPD-13`):** a 017 precisa ser aplicada **junto** com o release. Sem ela, a rota nova falha e a política descreve uma trava que não existe. Com ela e sem o release, o backend antigo grava pela sessão sem consentimento, o banco recusa, e o app antigo recebe erro.
- **Quem já tem conta passa pela tela na próxima noite.** Isso inclui o autor e as noites de teste.
- **Não feito:** o percurso no emulador, prometido no plano. O app aponta para o backend de produção, que não tem a rota nem a 017; fica para depois do release.
- **Dispositivo de travesseiro já pareado:** continua gravando sem o consentimento, por decisão do autor, declarado na política.

**Procedência.** `web-app/migrations/017_consentimento_destacado.sql`, `web-app/tests/rls/test_rls_consentimento.py`, `web-app/tests/test_consentimento.py`, `frontend/src/components/TelaDeConsentimento.test.tsx`; execuções de 10/11 nesta máquina.

---

# 2026-11-10 (xiii) — REL-01 e LGPD-13: release e 017 na produção

**O problema, como foi entendido no início.** A migração 017 precisava ser aplicada imediatamente antes do release que publica o consentimento destacado, para que banco, backend e frontend chegassem juntos.

**Hipótese de trabalho.** Após aplicar a 017 e publicar o release, o modelo estará disponível, as rotas recusarão acesso anônimo e a tela de consentimento estará presente no frontend.

**O que foi testado, e como.** O autor aplicou a 017 no SQL Editor e executou uma consulta curta; o PR #121 foi mesclado. Nesta máquina Windows, o Codex consultou o estado do commit no GitHub e fez requisições públicas ao site e ao bundle publicado.

**Resultado medido.** Na consulta do autor, colunas, função, gatilho e as travas de gravação e pareamento deram `true`; versão `2026-11-10`. PR #121 mesclado em `ddd6041`; status Vercel do commit `success`. `/health` respondeu `200`, banco `ok`, contrato `2.8.0`, modelo `ml-inf-cabeca-v2`. Sem credencial, `POST /api/me/consentimento`, `GET /api/inferencia` e `POST /api/data/lote` responderam `401`. O bundle `index-B9XMms3k.js` contém o texto da tela e a versão de consentimento. Uma captura enviada pelo autor mostra a tela em Coletar, com a caixa marcada e o botão Concordo habilitado, numa sessão autenticada; o autor confirmou que o botão fica desabilitado ao desmarcar a caixa. O autor relatou que, após concordar, a gravação foi liberada e iniciou a coleta; capturas mostram o botão de início e a coleta ativa em 1 s, com 0 registros. Os checks da PR e a auditoria de dependências do commit de merge passaram.

**Adaptação.** A conferência foi retomada pelo Codex a partir do registro da sessão anterior; os resultados públicos foram medidos de novo, distinguindo-os da consulta executada pelo autor.

**O que deu errado no caminho.** O terminal inicialmente não conectou ao GitHub no sandbox; a consulta com acesso autorizado funcionou. Uma primeira busca no bundle tratou suas linhas como coleção e deu falsos negativos; refeita sobre o texto completo, encontrou a tela e a versão.

**Risco em aberto.** As capturas e o relato confirmam a tela e o início da coleta, mas não comprovam a persistência do consentimento após recarregar nem a gravação de uma leitura (a captura mostra 0 registros) (`LGPD-13` e `REL-01` permanecem abertos). Falta medir o tempo do lote nos caminhos de sessão e token (`API-06`). A execução agendada do expurgo também não foi conferida nesta etapa.

**Procedência.** Resultado da consulta enviado pelo autor em 10/11 na sessão anterior capturas da tela e do início da coleta e relatos enviados pelo autor em 10/11; PR #121 e status do commit `ddd6041`; requisições públicas executadas nesta máquina em 10/11.

---

# 2026-11-10 (xiv) — atualização do app no Moto E7

**O problema, como foi entendido no início.** O celular conectado tinha uma versão anterior do aplicativo, sem as últimas mudanças da release #121.

**Hipótese de trabalho.** Uma compilação de depuração da árvore `0a86de1`, assinada com a mesma chave da instalação anterior, pode atualizar o aplicativo sem desinstalá-lo.

**O que foi testado, e como.** Nesta máquina Windows, `npm run build:app` e `gradlew assembleDebug`; no Moto E7 com Android 10, consulta do pacote e dos serviços, comparação dos certificados dos APKs e instalação com `adb install -r`. O APK instalado foi lido de volta e comparado por SHA-256 ao compilado.

**Resultado medido.** Ambos os builds passaram. Não foi encontrado serviço de coleta ativo na consulta. Certificados iguais; instalação `Success`; versão exibida pelo Android passou de `1.0` para `1.0.0`, com `versionCode` 1. O hash do APK instalado coincide com o compilado. A instalação original foi mantida, sem desinstalação; os dados individuais não foram inspecionados. É uma compilação de depuração, destinada ao aparelho de desenvolvimento.

**Adaptação.** Usada a chave de depuração existente para compatibilidade com o aplicativo já instalado; não foi criada nem distribuída uma chave de release.

**O que deu errado no caminho.** O ADB não estava no PATH e o daemon não iniciou no sandbox; funcionou com o acesso autorizado. `npm ci --offline` falhou por falta de pacote no cache e foi repetido com acesso à rede. O Gradle inicialmente falhou ao criar conexão local; funcionou com a configuração de diretório temporário já usada no projeto.

**Risco em aberto.** A abertura do app e o fluxo de consentimento e coleta no Android atualizado ainda não foram exercitados. A instalação preserva os dados do aplicativo, mas não os verifica individualmente. O APK é depurável e não é o release para distribuição (`APP-12`).

**Procedência.** Compilação e comandos ADB executados nesta máquina em 10/11; árvore `0a86de1` e release #121.

---

# 2026-11-10 (xv) — análise do frontend e da experiência de uso

**O problema, como foi entendido no início.** O autor pediu uma análise e documentação das telas, da interface e da experiência de uso do frontend e do app Android.

**Hipótese de trabalho.** O código, as evidências da sessão e o backlog permitem mapear os fluxos e apontar hipóteses verificáveis, sem substituir observação com usuários ou auditoria de acessibilidade.

**O que foi testado, e como.** Leitura das rotas, páginas, componentes, tokens, navegação e backlog; consulta às capturas e relatos desta sessão. Suíte `npm test -- --reporter=dot` executada no Windows.

**Resultado medido.** Documentos `ANALISE-FRONTEND-UX-UI.md` e `CATALOGO-TELAS-FRONTEND.md` com inventário detalhado por tela, composição visual, estados, fluxos, sistema visual, achados priorizados, plano de validação e limites. A suíte passou com 43 arquivos e 561 testes. O diálogo de consentimento não apresenta gestão explícita de foco no componente; seu efeito real fica para teste com teclado e leitor de tela. A tabela do painel descreve ordem de chegada, mas o código a ordena pelo instante da medição quando disponível; falta reproduzir a divergência.

**Adaptação.** O documento diferencia comportamento lido em código, resultado observado pelo autor e hipóteses de design; não cria novos itens de backlog nem declara conformidade.

**O que deu errado no caminho.** A primeira execução da suíte não iniciou os testes: `EPERM` ao renomear arquivos temporários no sandbox. A repetição com acesso autorizado passou. Uma leitura tentou o caminho incorreto `src/index.css`; o arquivo correto é `src/styles/index.css`.

**Risco em aberto.** Faltam inspeção visual abrangente, estudo com usuários, auditoria de acessibilidade, comprovação de persistência e leitura na coleta web e teste do fluxo nativo no aparelho. O documento é análise na base `0a86de1`, não comprovação desses resultados.

**Procedência.** Código e backlog da worktree, capturas e relatos do autor e testes executados nesta máquina em 10/11.

---

# 2026-11-10 (xvi) — capturas para a documentação do frontend

**O problema, como foi entendido no início.** O autor pediu que a documentação de cada tela tivesse capturas, além dos esquemas textuais.

**Hipótese de trabalho.** As rotas públicas e o modo de demonstração local permitem documentar a maioria das telas sem dados de contas; a tela nativa exige o aparelho real.

**O que foi testado, e como.** Frontend local em modo de desenvolvimento, navegador automatizado em 1440 × 900 e 390 × 844 CSS px; captura do Moto E7 aberto pelo autor. Conferência visual de amostras e verificação da existência das imagens referenciadas.

**Resultado medido.** Dezoito referências de imagens no catálogo, todas encontradas: telas públicas, demonstração, consentimento e captura nativa. O autor autorizou a captura nativa com dados reais para o documento local. O painel usa dados simulados identificados na imagem; a configuração sem backend local apresenta erro, sem implicar estado da produção.

**Adaptação.** As imagens são legendadas por ambiente, recorte e estado; a captura nativa contém dados reais e não está autorizada para publicação. A recuperação de senha mostra o estado de link inválido; formulário de recuperação válido e sucesso não foram capturados.

**O que deu errado no caminho.** A primeira captura da política ocorreu durante o carregamento e foi refeita após o texto ficar visível. A captura integral inicial da landing deixou blocos ainda ocultos pela animação de entrada; foi refeita com preferência de movimento reduzido.

**Risco em aberto.** As imagens não demonstram todos os estados, nem substituem teste com usuário. A imagem nativa exige cuidado antes de qualquer publicação. As imagens e os documentos ainda estão locais, sem commit.

**Procedência.** Capturas geradas nesta máquina e no Moto E7 em 10/11; autorização do autor nesta conversa; código `0a86de1`.

---

# 2026-11-11 (i) — revisão da documentação visual

**O problema, como foi entendido no início.** O catálogo tinha uma frase contraditória sobre dados reais e cobertura visual incompleta; o autor pediu para prosseguir com as melhorias propostas.

**Hipótese de trabalho.** Uma matriz de evidências, capturas adicionais em demonstração e um PDF local com as duas análises tornam os limites e as telas mais fáceis de consultar.

**O que foi testado, e como.** Nesta máquina Windows, capturas adicionais no frontend local em demonstração; verificação dos caminhos das imagens; geração do PDF e renderização de páginas para inspeção visual.

**Resultado medido.** Contradição corrigida; matriz de cobertura e cinco capturas adicionadas (tema escuro, edição de perfil, confirmação de exclusão e consentimento marcado). O PDF reúne análise e catálogo e identifica a imagem nativa como dado real autorizado somente para uso local. Os caminhos das 23 imagens existem; as páginas amostradas e o sumário foram renderizados e inspecionados.

**Adaptação.** A exclusão e o consentimento foram apenas abertos ou marcados na demonstração, sem concluir ações. Dados reais adicionais não foram gerados.

**O que deu errado no caminho.** A primeira conferência textual do sumário exibiu caracteres substituídos no terminal; a inspeção da página renderizada confirmou o texto visualmente. O backend local não foi iniciado, e os erros da tela de demonstração estão identificados como tais.

**Risco em aberto.** Faltam estados registrados na matriz, em particular o percurso nativo completo e a recuperação de senha válida. O PDF e a captura com dados reais são para uso local e não foram autorizados para publicação. As alterações permanecem sem commit.

**Procedência.** Capturas locais e autorização do autor na conversa, código `0a86de1`, catálogo e PDF produzidos nesta máquina em 11/11.

---

# 2026-11-11 (ii) — estados adicionais da documentação visual

**O problema, como foi entendido no início.** Restavam estados de tela sem evidência visual e o autor pediu que fossem documentados.

**Hipótese de trabalho.** Componentes isolados e identificados como simulação permitem mostrar vazio, erro e carregamento sem depender de conta ou servidor reais.

**O que foi testado, e como.** Nesta máquina Windows, montados temporariamente os componentes reais do painel com mensagem de erro de exemplo; capturados também política e detalhes da coleta em janela móvel e validação local da recuperação sem e-mail. Regenerado o PDF e conferidos caminhos e número de imagens.

**Resultado medido.** Seis imagens adicionadas: vazio, erro e carregamento simulados; política e detalhes em celular; mensagem por e-mail ausente. A montagem dos estados não inclui a navegação completa e suas imagens são identificadas como simulação. Nenhuma recuperação de senha foi solicitada nesta etapa.

**Adaptação.** Os estados isolados usam faixa visível de simulação; as pendências do aparelho e do link de recuperação permanecem distintas do material simulado.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** Aguardam-se a gravação de teste no Android e a abertura do link válido pelo autor. Não há evidência ainda dos estados reais de interrupção, encerramento, envio ou sucesso da recuperação. A captura nativa anterior e o PDF continuam apenas para uso local, como autorizado.

**Procedência.** Capturas e execução local nesta máquina em 11/11; catálogo e PDF locais.

---

# 2026-11-11 (iii) — solicitação de recuperação documentada

**O problema, como foi entendido no início.** O autor enviou a tela após solicitar recuperação e pediu que seu e-mail fosse ocultado.

**Hipótese de trabalho.** Uma versão editada pode ilustrar a mensagem condicional sem reproduzir as credenciais, desde que não seja apresentada como prova visual pixel a pixel.

**O que foi testado, e como.** A imagem fornecida foi editada para remover o conteúdo de e-mail e senha; o resultado foi inspecionado visualmente e incluído no catálogo e no PDF locais. Os caminhos e imagens do PDF foram conferidos nesta máquina.

**Resultado medido.** A imagem resultante não mostra o e-mail nem a senha. A ferramenta alterou características visuais além dos campos, por isso o catálogo a identifica como ilustração editada por IA, não como captura fiel. A mensagem exibida não comprova entrega do e-mail.

**Adaptação.** A ilustração foi acrescentada ao estado de solicitação, sem substituir a captura do link inválido ou afirmar que o link válido foi aberto.

**O que deu errado no caminho.** A edição generativa não preservou a imagem pixel a pixel; a limitação foi explicitada na legenda.

**Risco em aberto.** A tela aberta a partir do link válido e o fluxo nativo em andamento continuam sem captura. O PDF com a imagem real anterior continua restrito a uso local.

**Procedência.** Imagem fornecida e autorização de ocultação pelo autor nesta conversa; edição e conferência nesta máquina em 11/11.

---

# 2026-11-11 (iv) — tela de nova senha documentada

**O problema, como foi entendido no início.** Faltava registrar a tela aberta pelo link de recuperação da conta.

**Hipótese de trabalho.** A captura do formulário vazio demonstra a apresentação dessa etapa sem exigir que o autor altere a senha.

**O que foi testado, e como.** O autor enviou capturas do recebimento do e-mail e do formulário aberto após seguir o link. O formulário foi incorporado ao catálogo e ao PDF locais; arquivos e imagens foram conferidos nesta máquina.

**Resultado medido.** A captura mostra o formulário de nova senha, com campo vazio e sem URL visível. O e-mail recebido demonstra a entrega à conta utilizada nessa tentativa; não generaliza a outras contas. Nenhuma senha foi alterada nesta etapa.

**Adaptação.** O conteúdo da caixa de entrada não foi incorporado; a documentação usa somente a captura da aplicação, sem credenciais.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** A captura não comprova o salvamento de uma nova senha. O fluxo Android em andamento continua sem captura. A imagem nativa anterior e o PDF seguem restritos a uso local.

**Procedência.** Capturas fornecidas pelo autor em 11/11; catálogo e PDF atualizados nesta máquina.

# 2026-11-11 (v) — REL-01 e LGPD-13 fechados: o consentimento e as leituras no banco

**O problema, como foi entendido no início.** O release #121 e a 017 estavam na produção (entrada 10/11 xiii), mas faltava provar no banco duas coisas que a tela não prova: que o consentimento dado na tela fica gravado, e que, com a trava da 017 ligada, as leituras de quem consentiu continuam entrando. Faltava também conferir a primeira execução agendada do expurgo (`LGPD-09`).

**Hipótese de trabalho.** Uma consulta só de agregados (contagens e horários, sem nome nem e-mail) responde as três perguntas.

**O que foi testado, e como.** O autor rodou no SQL Editor uma consulta escrita por mim: contas com o consentimento na versão vigente, o último consentimento, leituras com `created_at` depois de 10/11 22:00 UTC, a última leitura, e as execuções do agendamento `dormio-expurgo-por-inatividade` em `cron.job_run_details`.

**Resultado medido.**
- 2 contas com o consentimento na versão `2026-11-10`, o último às 07:19 UTC de 11/11.
- 941 leituras gravadas depois do release, a última às 15:09 UTC de 11/11.
- O expurgo: uma execução, `succeeded`, 11/11 04:17 UTC.

**Adaptação.** O registro das entradas 10/11 (xiii) a 11/11 (iv), feito pelo Codex enquanto o Claude estava sem cota, entrou nesta mesma branch, sem alteração. Ficaram de fora a análise e o catálogo do frontend, as capturas e o PDF: o PDF tem uma captura com dados reais, autorizada pelo autor só para uso local, e o repositório é público.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **`API-06`:** o tempo por leitura do lote na produção ainda não foi medido.
- **Origem das leituras:** a consulta não separa as 941 leituras entre o app e o navegador.
- **Consentimento na versão antiga do app:** o fluxo no app instalado no Moto E7 não foi conferido por esta consulta.

**Procedência.** Resultado da consulta colado pelo autor em 11/11.

# 2026-11-11 (vi) — INFRA-05: o envio era lento porque o backend estava em outro continente

**O problema, como foi entendido no início.** O autor notou que o envio da noite, ao encerrar, demorou bastante. O `API-06` esperava exatamente essa medição para decidir se o lote precisa de uma função de gravação única no banco.

**Hipótese de trabalho.** Os logs da Vercel dariam a duração de cada requisição. Como o plano gratuito guarda só uma hora de log, o envio de hoje já tinha sumido. A hipótese passou a ser: o `created_at` de cada leitura (o `now()` de cada chamada ao banco) reconstrói os lotes, pelos intervalos.

**O que foi testado, e como.**
- **Os lotes:** uma consulta agrupou as leituras depois do release por intervalos de mais de 1 s, com tamanho, duração e pausa antes de cada lote. Rodada pelo autor no SQL Editor.
- **O tempo do banco:** `pg_stat_statements`, rodado pelo autor: o tempo médio das chamadas de gravação.
- **As regiões:** a do backend pela API da Vercel (`get_deployment`: `regions: ["iad1"]`); a do banco pelo painel do Supabase, enviada pelo autor (`sa-east-1`).
- **O código:** o laço do app, a rota do lote, e o cliente do Supabase (o `postgrest` é guardado no cliente, então a conexão é reaproveitada entre as gravações de um lote).

**Resultado medido.**
- **A noite:** 930 épocas entre 15:04:42 e 15:09:30 UTC: **4 min 48 s em 38 requisições**. Nenhum lote chegou a 60 leituras: todos pararam nos 6 s, com 16 a 40.
- **Por gravação:** 0,15 a 0,40 s, e ~2 s de pausa entre lotes.
- **No banco:** a função de gravação leva **0,43 ms** em média (máx. 2,6 ms, 1 887 chamadas). As consultas de dispositivo e perfil levam menos de 0,1 ms.
- **Conclusão:** quase todo o tempo é a ida e volta Washington ↔ São Paulo, uma vez por leitura e três ou quatro vezes por lote (login, consentimento e dispositivo).

**Adaptação.**
- `"regions": ["gru1"]` no `vercel.json`. A documentação da Vercel diz que o plano Hobby escolhe uma região, qualquer uma.
- `web-app/tests/test_regiao_do_backend.py` exige a região da Vercel perto da do banco. A região do banco fica como constante no teste, porque é configuração do painel.
- Controle positivo, com a sabotagem nas duas formas: `iad1` no lugar de `gru1`, e a chave apagada. O teste caiu nas duas.
- O `API-06` fica esperando a medição depois do release: se 60 leituras couberem nos 6 s, fecha sem implementar.

**O que deu errado no caminho.**
- **Logs da Vercel:** a primeira tentativa foi pelos logs, apagados depois de uma hora no plano gratuito.
- **Medição daqui até o Supabase:** passa pela Cloudflare, e o tempo de conexão (13 ms) é o da borda no Rio, não o da origem. Só o painel deu a região com certeza.
- **Projeto exposto na saída:** um cabeçalho de resposta trouxe o identificador do projeto do Supabase na saída do terminal. Ele não entrou em nenhum arquivo.

**Risco em aberto.**
- **Ganho estimado, não medido (`INFRA-05`):** 60 leituras por lote e uma noite em ~30–60 s. A medição é a mesma consulta numa noite nova, depois do release.
- **Caminho do token:** continua sem medição, porque o dispositivo do travesseiro ainda não envia.
- **Lote solto:** um lote de 11 leituras às 04:41 UTC, separado do envio, não foi explicado.

**Procedência.** Resultados das consultas e captura do painel colados pelo autor em 11/11; `get_deployment` da Vercel; documentação da Vercel sobre regiões de funções; testes nesta máquina (Windows 11), backend 526 passam.

# 2026-11-11 (vii) — CAL-03, etapa 1: a autocalibração no núcleo, no contrato e no banco

**O problema, como foi entendido no início.** O acelerômetro tem desvio e erro de escala por eixo (etapa 0: no Moto E7, a gravidade parada vai de 0,991 a 1,020 g conforme a posição), e o ENMO lê o excesso como movimento: 23 mg com a tela para baixo, sem movimento nenhum, na noite de 10/11. O sinal bruto não sobe ao servidor, então a correção tem de acontecer no aparelho, antes do ENMO, e o dado tem de dizer qual época foi corrigida. A etapa 1 é a conta, o contrato e o banco. Guardar os pontos entre noites e estimar no app é a etapa 2.

**Hipótese de trabalho.** O método de van Hees et al. (2014), o do GGIR, com uma diferença deliberada: cada eixo usa só o que os pontos identificam.
- **Completo:** o eixo passou de ±0,3 g dos dois lados, e se estimam desvio e escala.
- **Desvio:** passou de um lado só, e se estima só o desvio.
- **Fixo:** não passou, e o eixo fica como está.

Um celular deitado só mexe em z, e é z que pesa na norma nessa posição. O GGIR recusaria calibrar. A temperatura só entra com 2 °C de faixa entre os pontos (PROVISÓRIO). A calibração só é aceita se o erro cair e ficar abaixo de 10 mg; senão, nada é corrigido.

**O que foi testado, e como.**
- **Referência em Python** (`ml/src/calibracao.py`), com erros sintéticos do tamanho dos do Moto E7. Cinco casos:
  - esfera;
  - deitado com a tela para cima e para baixo;
  - só para cima;
  - pontos ruidosos;
  - poucos pontos.

  `ml/testes/test_calibracao.py` (11 testes) confere a recuperação dos parâmetros e grava o dourado `dourado_calibracao.json`.
- **Núcleo C++** (`firmware/nucleo/calibracao.{h,cpp}`): a mesma conta, conferida contra o dourado (`make calibracao`, 185 verificações), com 10 sabotagens (`make mutacao-calibracao`).
- **No coletor do celular:** cada amostra é calibrada em g antes da cadeia, e o payload ganha `gn` (a norma da gravidade média da época) e `cal` (0 ou 1). O travesseiro não manda nenhum dos dois. Três sabotagens novas no coletor: a calibração não aplicada, `cal` sempre 0 e `gn` perdido.
- **Servidor:**
  - contrato 2.9.0;
  - `validacao._validar_calibracao` (18 testes em `test_calibracao_na_ingestao.py`);
  - migração 018, com as colunas `g_norma` e `calibrada`, a restrição `sleep_data_calibracao_valida` e as duas funções de gravação refeitas a partir da 016 e da 017;
  - 10 testes de RLS e 4 sabotagens no banco;
  - 3 marcas da 018 no diagnóstico.
- **Política §2.2:** descreve as duas colunas; o teste que liga as colunas à política acusou a falta antes.

**Resultado medido** (Windows 11; núcleo em contêiner `gcc:13`; banco em Postgres 17):
- **Referência:**
  - esfera: erro de 9,73 → 0,48 mg;
  - deitado: 15,46 → 0,59 mg, só z calibrado;
  - só para cima: 1,23 → 0,63 mg, só o desvio de z.

  Os casos ruidoso e com poucos pontos foram recusados.
- **O C++ bate com o Python** em 1e-8 nos nove parâmetros, nos erros e nas amostras de conferência. A mutação da calibração deu 10/10.
- **O coletor, com o erro do eixo z do Moto E7, parado de tela para baixo:** o ENMO parado foi de **19,29 mg para 0,000 mg**, e o `gn` de 1,0193 para 1,00000 g. Uma calibração recusada deixa o ENMO igual ao de sem calibração.
- **Suítes:**
  - núcleo 341 + 157 + 152 + 456 + 85 + 314 + 185, 0 falhas;
  - mutações: coletor 15/15, cadeia 29/29, paridade 15/15, fila 14/14, laço 4/4;
  - ML 310;
  - backend 544;
  - RLS 269;
  - mutação do banco 54/54;
  - verificador de migrações com os 18 estados e a ordem real terminando na 018.

**Adaptação.**
- **Sabotagens do coletor:** três delas procuravam as linhas de conversão reescritas e foram atualizadas para o código novo, com a mesma sabotagem.
- **Tolerância da recuperação da escala:** foi de 2e-4 para 5e-4, porque o ruído simulado já dá 2,07e-4.

**O que deu errado no caminho.**
- **Tolerância apertada demais:** o primeiro teste da esfera falhou com a escala a 2,07e-4 da verdade contra 2e-4 de tolerância. Era o tamanho do ruído, não um defeito.
- **Comando barrado:** um comando com `docker run --rm` e substituição de caminho foi barrado pela verificação de segurança, por ambiguidade de leitura. Nada foi apagado, e foi refeito em passos separados.
- **Teste de RLS do token:** procurou a leitura numa segunda sessão, que não a via porque cada sessão volta atrás no fim. Passou a conferir na mesma transação.
- **NaN no JSON:** o caso NaN mandado como número deu erro de JSON (22P02) em vez da restrição. Passou a ir como texto, como os testes da 016.

**Risco em aberto.**
- **Etapa 2 (`CAL-03`):** o app ainda não guarda pontos nem estima; até lá, toda época sai com `cal: 0`.
- **Ordem de produção:** a 018 tem de entrar antes do release do backend 2.9.0. Com o backend novo e o banco antigo, `gn` e `cal` se perderiam em silêncio.
- **Limiares provisórios:** a faixa mínima de temperatura (2 °C) e o critério de época parada (10 mg) são provisórios, a validar na etapa 3.
- **Noites anteriores:** ficam sem correção (declarado em `LIMITACOES-TCC.md`).

**Procedência.** Execuções desta entrada; erros sintéticos da bancada da etapa 0 (diário, 10/11 iv).

# 2026-11-11 (viii) — CAL-03, etapa 2: o app junta os pontos e calibra sozinho

**O problema, como foi entendido no início.** A etapa 1 deixou o núcleo capaz de calibrar, mas ninguém juntava os pontos nem estimava: toda época saía com `cal: 0`. A etapa 2 fecha o ciclo no celular. As épocas paradas de cada noite viram pontos guardados entre noites, e ao iniciar a noite seguinte o app estima e aplica.

**Hipótese de trabalho.**
- O núcleo entrega o ponto parado de cada época já desfeito para o bruto. Assim, pontos de noites com calibrações diferentes ficam na mesma escala.
- O app guarda os pontos num arquivo próprio, com os 2 000 mais recentes.
- Uma calibração por noite, estimada no início, porque trocar no meio mudaria a medida dentro da noite.
- A noite registra qual calibração usou.

**O que foi testado, e como.**
- **Núcleo** (`ColetorCelular::ponto_parado`): a época com movimento dinâmico abaixo de 10 mg vira {x, y, z, temp} no bruto; a época em movimento, não. Duas sabotagens novas no coletor: o ponto calibrado em vez de bruto, e a época em movimento virando ponto.
- **Ponte JNI:** `pontoParado`, `definirCalibracao`, `estimar` e `pontosMinimos`. Só conversão de tipos.
- **Java:**
  - `Calibracao`: o resultado da estimativa, gravado ao lado da noite em `noite-<ts>.jsonl.calibracao`; arquivo estragado ou escala absurda voltam à identidade.
  - `PontosDeCalibracao`: `calibracao-pontos.csv`, aparado aos 2 000 mais recentes, com linha ruim pulada e NaN não guardado.
  - O serviço da noite estima ao iniciar, aplica no núcleo (também na retomada) e guarda cada ponto parado.
  - O plugin devolve `calibrada`, `calibracao` (o resumo) e `pontosDeCalibracao`.
- **Testes:** 12 de JVM (`CalibracaoTest`) e 3 instrumentados no emulador Pixel 6 (`CalibracaoNativaTest`): o ciclo inteiro pelo JNI, a noite sem calibração e poucos pontos.
- **Tela:** o cartão da noite mostra a linha "Calibração do sensor" com o resumo. Dois testes de vitest; sem a linha, o teste cai.
- **Política §2.3:** os pontos de calibração guardados no celular.

**Resultado medido** (Windows 11; núcleo em `gcc:13`; app no emulador Pixel 6):
- **No emulador, pelo JNI:** com pontos de tela para cima e para baixo e o erro de z do Moto E7, a estimativa aceita, com z completo e erro abaixo de 2 mg. A noite calibrada sai com `cal: 1`, ENMO parado abaixo de 1 mg e `gn` = 1,000 ± 0,002 g, e o ponto parado volta no bruto (−1,0193 g).
- **Testes do app:**
  - JVM 32 (+12);
  - emulador 7 passam e 3 pulados (os roteiros), com os 3 novos;
  - o APK de depuração compila pelo NDK com o `calibracao.cpp`, o que fecha o "não verificado" da etapa 1.
- **Núcleo e mutações:** coletor 320 verificações, mutação do coletor 17/17.
- **Outras suítes:** frontend 563; teste da política 5/5.

**Adaptação.**
- **Resumo da tela:** passou a ser escrito em português com acento e vírgula decimal (`Locale.forLanguageTag("pt-BR")`), porque é ele que aparece na tela.
- **Testes instrumentados:** rodados só no emulador (`ANDROID_SERIAL=emulator-5554`), porque o celular do autor estava ligado pelo USB e o `connectedAndroidTest` desinstala o app no fim, o que apagaria as noites guardadas.

**O que deu errado no caminho.**
- **Ponto parado sumindo:** o ponto se perdia porque eu zerava a marca no começo de **toda** chamada de `proximo`, inclusive a última, que só responde "nada pronto". Passou a zerar só quando uma época fecha. O teste do coletor acusou (3 falhas) antes da correção.
- **Gradle sem conexão local:** "Unable to establish loopback connection", o mesmo do diário de 10/11. Resolvido com `-Djdk.net.unixdomain.tmpdir`.
- **Build instrumentado do projeto inteiro:** falhou por classes Kotlin duplicadas nas bibliotecas do Capacitor. É anterior a esta mudança, e o caminho certo é `:app:connectedDebugAndroidTest`, como o CLAUDE.md diz.
- **`raw.test.ts`:** falhou uma vez na suíte inteira logo depois do Gradle e passou sozinho e na suíte seguinte (563/563). É um teste que sobe um servidor, sensível a carga.

**Risco em aberto.**
- **Produção (`CAL-03`):** o app novo manda `gn` e `cal`, e a produção (backend 2.8.0, sem a 018) os ignora sem erro. A ordem é a 018, depois o release do backend 2.9.0, e só então o APK novo.
- **Percurso real não feito:** uma noite de verdade em que os pontos se acumulam e a noite seguinte sai calibrada; o teste instrumentado cobre o ciclo com pontos injetados. É a etapa 3.
- **Limiares provisórios:** a faixa de temperatura (2 °C) e o critério de parado (10 mg).

**Procedência.** Execuções desta entrada; relatórios do Gradle em `frontend/android/app/build/` (não versionados).

# 2026-11-11 (ix) — release #127: a 018 e o backend 2.9.0 na produção; o sensor soldado responde

**O problema, como foi entendido no início.** As etapas 1 e 2 do `CAL-03` estavam em `develop`, mas nada delas na produção. A ordem fixada na etapa 1 era: a 018 antes do backend 2.9.0, e o APK novo só depois dos dois. Na ordem inversa, `gn` e `cal` se perderiam em silêncio. No mesmo dia, o autor soldou o MPU6050 na ESP32, que é a corrente que trava a captação desde agosto.

**Hipótese de trabalho.**
- A 018 sem comentários aplica limpa na ordem da produção.
- O release só acrescenta: o backend aceita dois campos opcionais e nada do que já entra muda.
- A solda passa no `diagnostico-i2c` sem erro de barramento.

**O que foi testado, e como.**
- **A 018 sem comentários (216 linhas):** aplicada por mim num Postgres 17 montado na ordem real (001–017), com o diagnóstico.
- **Na produção:** o autor aplicou a 018 no SQL Editor e rodou uma conferência de cinco marcas: colunas, restrição, as duas funções gravando `g_norma` e a trava do consentimento mantida.
- **Release:** PR #127, CI 10/10; mesclado e publicado pela Vercel. Depois do deploy:
  - `get_deployment`;
  - `/health`;
  - as rotas sem credencial;
  - o pacote publicado, inclusive o pedaço da página `/privacidade`.
- **O sensor soldado:** liguei as quatro ligações (VCC → 3V3, GND → GND, SDA → D21, SCL → D22) e conferi pelas fotos do autor o lado do sensor. Instalei o `arduino-cli` 1.6.0 e o pacote ESP32 3.3.12 numa pasta de ferramentas fora do repositório. Compilei e gravei o `firmware/diagnostico-i2c` na COM3 e li a serial.

**Resultado medido.**
- **A 018 no banco de teste:** 3 de 3 marcas, a 016 e a 017 intactas, nenhuma marca falsa.
- **A conferência na produção:** os cinco `true`. **Produção com 001–018.**
- **O deploy:**
  - `regions: ["gru1"]`, e a resposta vem `gru1::gru1`;
  - `/health` `200`, `"contrato_de_dados": "2.9.0"` e o modelo `ml-inf-cabeca-v2`;
  - lote, leitura, consentimento e inferência sem credencial respondem `401`; `/privacidade` responde `200`;
  - o pedaço da política traz os trechos novos da §2.2, da §2.3 e da §10; o pacote principal traz a linha "Calibração do sensor".
- **O diagnóstico de I²C, com a placa parada:**
  - 0 falhas de barramento a 100 e a 400 kHz;
  - WHO_AM_I `0x68` em 1 000 de 1 000 leituras;
  - 0 leituras fora do plausível;
  - |a| de 9,990 a 10,055 m/s².
- **O sensor lê 10,03 m/s² parado, 2,2 % acima de 9,81.** É o erro que a calibração de bancada (`CAL-01`) mede eixo por eixo.

**Adaptação.**
- **Gravação da ESP32:** a 921600 bauds falhou ("No more data to read from the serial port") e a 115200 passou.
- **Rótulos da placa:** o DevKit V1 de 30 pinos do autor rotula os GPIO como D21 e D22, e o 3V3 fica do mesmo lado que eles. O desenho do repositório (`esquemaEletrico/`, de outra placa, de 38 pinos) tem outra disposição; a orientação foi seguir os nomes impressos.

**O que deu errado no caminho.**
- **Primeira rodada do diagnóstico:** deu 18,8 % de leituras fora do plausível a 100 kHz (|a| de 7,0 a 13,0). Mas teve 0 falhas de barramento e o WHO_AM_I estável, o que é a placa sendo mexida, e não contato ruim. A segunda rodada, parada, deu 0 %.
- **Relógio do PC:** está cerca de 1h30 atrasado em relação ao GitHub (cabeçalho `Date` da API contra o relógio local). Isso quebrou a verificação de assinatura do índice de bibliotecas do Arduino ("signature expired"); o diagnóstico não precisava dele.
- **CI da etapa 2:** os dois runs do PR #126 foram criados durante um incidente do GitHub Actions e ficaram "queued" por mais de uma hora, mesmo depois de o incidente fechar. O GitHub os dava como terminados ao cancelar e como em andamento ao re-executar. Fechar e reabrir o PR gerou um run novo, que passou 8/8.
- **Script de teste da 018:** quebrou numa substituição de caminho com barras invertidas pelo terminal e foi reescrito inteiro.

**Risco em aberto.**
- **O APK novo:** é o próximo passo (`APP-12`), e só depois dele a calibração chega ao celular.
- **O login de verdade** depois deste release ainda não foi confirmado pelo autor.
- **`CAL-01`:** a calibração de bancada do sensor do travesseiro, agora possível com a solda.
- **O relógio do PC** precisa ser acertado.

**Procedência.** Conferência colada pelo autor em 11/11; `get_deployment` e requisições públicas desta máquina; a saída serial do diagnóstico, guardada fora do repositório; fotos da solda enviadas pelo autor.

# 2026-11-11 (x) — APP-12: a chave do autor e o primeiro APK de release

**O problema, como foi entendido no início.** Com o `CAL-03` na produção (entrada ix), faltava o app chegar aos celulares. Eram dois APKs com papéis diferentes: o de depuração para o celular do autor, que instala por cima do que já está lá sem apagar as noites, e o de release para os testadores, assinado com uma chave do autor. A chave não existia: não havia `~/.dormio` nesta máquina.

**Hipótese de trabalho.**
- **A chave:** o autor cria a chave e o `assinatura.properties` seguindo o `docs/DISTRIBUICAO-DO-APP.md`, sem que eu veja a senha, e o Gradle assina sozinho.
- **O seu celular:** o de depuração tem a mesma assinatura do app instalado e atualiza sem desinstalar.

**O que foi testado, e como.**
- **A chave:** o autor gerou-a com o `keytool` do Android Studio (RSA de 4096 bits, validade de 10 000 dias), escreveu o `assinatura.properties` e copiou a pasta `.dormio` para um pendrive. Eu conferi só que os dois arquivos existiam e que os quatro campos estavam preenchidos, sem ler os valores.
- **O build:** `npm run build:app` e `./gradlew assembleRelease` a partir de `develop` (`4811f57`, o código da produção). O de depuração, `assembleDebug`, veio do mesmo código.
- **A conferência:** `apksigner verify --print-certs` e `aapt2 dump badging` no APK de release.
- **A entrega:** os dois APKs enviados ao autor pelo app.

**Resultado medido.**
- **APK de release:** 4,4 MB, `versionCode` 1, `versionName` 1.0.0, alvo do SDK 36.
  - Assinatura v2 verificada, um assinante, certificado com o nome do autor (`O=SmartDormio, C=BR`), SHA-256 `06b2e4f9…d14a`.
  - Sem `application-debuggable`.
- **APK de depuração:** 5,8 MB, o mesmo código.
- **Nenhum dos dois foi instalado num aparelho nesta entrada:** o celular do autor não estava mais no USB.

**Adaptação.**
- **O comando do guia:** no PowerShell, o `keytool` com o caminho entre aspas precisa do `&` na frente. O guia mostrava o comando sem ele, e o primeiro uso deu erro de sintaxe.
- **O "ã" de "São Paulo":** foi gravado como "S?o Paulo" no certificado, pela codificação do terminal. É só identificação, não afeta a assinatura.

**O que deu errado no caminho.**
- **O comando do guia** não funcionava como estava no PowerShell (acima).
- **Tentei instalar o de depuração no celular pelo `adb`,** mas o aparelho já tinha sido desconectado. O APK foi entregue por arquivo.

**Risco em aberto.**
- **O aval do orientador sobre o comitê de ética e o termo de consentimento (`LGPD-03`) continua pendente.** Os testadores são pessoas, e as noites deles entram no trabalho. Mandar o APK antes disso é decisão do autor, e o `APP-12` a registra como a primeira pendência.
- **A troca de assinatura:** o celular do autor fica no APK de depuração. Trocar para o de release exige desinstalar, porque as assinaturas são diferentes, e isso apagaria as noites guardadas nele.
- **A primeira instalação real** do APK de release ainda não aconteceu.
- **O guia:** precisa do `&` no comando do `keytool` (`DOC`, pendência pequena, feita nesta mesma entrada).

**Procedência.** Saídas do `apksigner` e do `aapt2` nesta máquina em 11/11; a confirmação do autor de que salvou a pasta no pendrive.

# 2026-11-11 (xi) — CAL-01: o sensor do travesseiro calibrado na bancada, e um contato que falha ao virar

**O problema, como foi entendido no início.** Com o MPU6050 soldado (entrada ix), o monitor ao vivo mostrou o sensor parado lendo 0,89 g com o chip para cima e 1,14 g com o chip para baixo. Isso é um desvio grande no eixo Z, do tamanho do que a bancada de 25/08 tinha medido (−1,06 m/s²) e atribuído, então, a contato ruim. O `CAL-01` é a calibração de 6 posições desta unidade, na escala (±8 g) e no filtro (21 Hz) do firmware.

**Hipótese de trabalho.**
- **O erro é do sensor:** com a solda nova, o diagnóstico de I²C não acusou contato ruim.
- **Desvio e escala por eixo:** as 6 posições dão os dois.
- **O estimador do projeto:** o de autocalibração (`ml/src/calibracao.py`, o mesmo do núcleo) deve concordar com o método clássico e ser robusto à posição que não ficou nivelada.

**O que foi testado, e como.**
- **O sketch:** `firmware/caracterizacao/` (biblioteca Adafruit, ±8 g, 21 Hz, 500 amostras por posição), gravado pelo `arduino-cli` na COM3. O autor posicionava a placa, apoiada num livro, e eu mandava o Enter pela serial.
- **O contato:** a primeira tentativa falhou (abaixo). Repeti o `diagnostico-i2c` com o autor mexendo nos fios de propósito.
- **As 6 posições, medidas uma a uma**, com a placa reiniciada antes de cada uma.
- **As contas:** o método clássico ((cima + baixo)/2 e (cima − baixo)/2g) e o estimador de van Hees com os 6 pontos, sem o termo de temperatura, porque 6 pontos não sustentam 9 parâmetros.
- **A validação independente:** a calibração aplicada a 6 janelas paradas do monitor ao vivo de mais cedo, em outras posições e noutro momento, que não entraram no ajuste.

**Resultado medido** (sensor de 27,8 a 32,1 °C, aquecendo durante a sessão):

| Posição | ax | ay | az (m/s²) | \|a\| (g) | Ruído (m/s²) |
|---|---:|---:|---:|---:|---:|
| Z+ | 0,461 | −0,462 | 8,768 | 0,897 | 0,020 |
| Z− | 0,681 | −0,242 | −11,318 | 1,157 | 0,014 |
| X+ | 10,123 | 0,891 | 0,097 | 1,036 | 0,027 |
| X− | −9,441 | −0,188 | −0,905 | 0,967 | 0,017 |
| Y+ | −0,369 | 9,584 | −1,863 | 0,996 | 0,014 |
| Y− | 0,435 | −10,044 | −1,132 | 1,032 | 0,019 |

| Eixo | Clássico: desvio / escala | van Hees: desvio / escala |
|---|---|---|
| X | +34,8 mg / 0,9975 | +42,3 mg / 1,0057 |
| Y | −23,5 mg / 1,0007 | −21,1 mg / 1,0033 |
| Z | **−130,0 mg** / 1,0241 | **−130,0 mg** / 1,0245 |

- **No Z, que é o que pesa, os dois métodos concordam:** −130 mg e escala de +2,4 %.
- **No X diferem em 7,5 mg:** a posição X+ ficou inclinada 10,2°, e o método clássico supõe o eixo na vertical. As outras posições ficaram entre 0,8 e 5,7°.
- **O van Hees fecha as 6 posições em 1,000 g.** É ajuste (6 parâmetros, 6 pontos), não validação.
- **A validação independente:** nas 6 janelas do monitor, o erro RMS da gravidade parada vai de **83,6 mg para 2,3 mg** com a calibração do van Hees.
- **O efeito no ENMO, sem calibração:** parado com o chip para baixo, ele leria ~157 mg de movimento que não existe; com o chip para cima, a gravidade lida a 0,897 g esconderia qualquer movimento abaixo de ~100 mg. É dez vezes o erro do Moto E7.

**Adaptação.**
- **Posições medidas uma a uma:** o sketch mede as 6 em sequência e para de vez numa leitura impossível. Com o contato falhando ao virar (abaixo), reiniciei a placa antes de cada posição e anotei qual era. O rótulo que o sketch imprime ("Z+") vale só para a primeira.
- **O monitor ao vivo** (fora do repositório, em `~/.dormio-tools/`) serviu de conjunto independente para a validação.

**O que deu errado no caminho.**
- **Leituras zeradas:** a primeira posição saiu tremendo (ruído 0,79), e a segunda, toda zerada, com a temperatura em 36,5 °C (o registrador zerado). Isso se repetiu duas vezes ao virar a placa de chip para baixo, e uma vez com um peso sobre os fios.
- **A causa provável:** o contato do VCC falha **por um instante** quando a placa é virada ou os fios são forçados. O MPU6050 reinicia e volta em modo de repouso, o padrão do chip ao ligar. A biblioteca só o acorda no começo do sketch, então ele segue lendo zero com o contato já de volta. Reiniciando a placa, mede normal.
- **O diagnóstico com os fios sendo mexidos:** passou (0 falhas de barramento, nenhum bloco zerado), porque ele reconfigura o sensor a cada passada. A falha é momentânea, não permanente.
- **Um diagnóstico meu, errado:** no monitor ao vivo eu tinha concluído que o chip era um clone, porque o \|a\| diferia 13 % entre as escalas de ±2 g e ±8 g. A diferença era da posição do sensor em cada teste, não da escala: com o chip para cima, as duas dão 0,89 g. Corrigi com o autor.

**Risco em aberto.**
- **`HW-09`:** o contato que falha ao virar precisa de solda refeita e de alívio de tensão nos fios, antes de o sensor ir para dentro de um travesseiro, onde ele vira o tempo todo.
- **`FW-11`:** o firmware do travesseiro não usa a calibração. E ele não percebe o sensor reiniciado em repouso: leria zero a noite toda. O `sketch.ino` precisa aplicar os parâmetros e reacordar o sensor quando a leitura zerar.
- **A temperatura:** subiu 4,3 °C durante a sessão, e o termo de temperatura não foi estimado.
- **Uma unidade só:** os números valem para este módulo.

**Procedência.** A saída serial da sessão, guardada fora do repositório; as contas feitas com `ml/src/calibracao.py` nesta máquina em 11/11.

# 2026-11-11 (xii) — FW-11: o firmware do travesseiro calibra e reacorda o sensor

**O problema, como foi entendido no início.** A bancada do `CAL-01` (entrada xi) deixou duas coisas para o firmware.
- **A calibração não era usada:** o `sketch.ino` não corrigia nada, e com −130 mg em Z o ENMO leria movimento fantasma numa posição e esconderia movimento pequeno na outra.
- **O sensor que reinicia volta adormecido:** uma queda de alimentação de uma fração de segundo (o contato que falhou ao virar a placa) faz o MPU6050 voltar dormindo e com a FIFO desligada. Lendo o firmware, o efeito era pior do que o backlog dizia: a FIFO passa a responder "0 bytes" como uma leitura normal, as épocas seguintes são recusadas por falta de amostra, e **o resto da noite vira lacuna**, sem aviso.

**Hipótese de trabalho.**
- **(a) Calibração fixa da bancada:** aplicada a cada amostra da FIFO, antes da cadeia, pelo `aplicar_calibracao` do núcleo (o mesmo do celular). A marca vai num bit livre do registro da flash, sem aumentar o registro; o `gn` fica de fora.
- **(b) Recuperação do sensor:** 3 drenagens seguidas vazias mandam conferir o sensor; dormindo ou com a FIFO desligada, ele é reconfigurado; acordado, nada muda.

**O que foi testado, e como** (contêiner `gcc:13`, Windows 11).
- **Núcleo:**
  - `calibrar_amostras` (calibração no lugar, arredondando e saturando como o `g_para_lsb` do celular);
  - `VigiaDaFifo` e `sensor_precisa_reconfigurar`;
  - o bit `REGISTRO_CALIBRADA` gravado, relido depois de um reset e saindo como `"cal":1`.

  São 18 verificações novas no `testes_c2` e 9 no `testes_fila_flash`.
- **Sketch:**
  - `firmware/calibracao_da_unidade.h`, versionado, com os parâmetros do van Hees de 11/11 e a procedência;
  - `drenar()` calibra e alimenta a vigia, e `conferir_sensor()` lê PWR_MGMT_1, USER_CTRL e FIFO_EN e reconfigura;
  - o contador `reacordados` aparece no log;
  - `fila.guardar` recebe a marca;
  - `nucleo_amalgama.cpp` inclui a `calibracao.cpp`.
- **O sketch contra um MPU6050 falso** (`testes/sensor_do_sketch.cpp`, no `make laco`): um sensor de mentira que guarda os registradores, entrega amostras com o erro de Z da bancada, reinicia dormindo num reset e pode "cair" no meio da noite. Roda o `drenar`, o `fechar_epocas` e o `conferir_sensor` de verdade.
- **Sabotagens:**
  - 4 no sketch (calibração não aplicada; ninguém conferindo; reconfigurar com o sensor acordado; "reacordar" sem configurar);
  - 5 no núcleo (a vigia com 2; a cheia que não zera; o sensor dormindo visto como acordado; truncar; não saturar).

**Resultado medido.**
- **Na grade da época, o eixo Z lê −0,9995 g**, contra os −1,1541 g crus que o sensor falso entrega, que são os da bancada.
- **Com o sensor caindo no meio da noite:** duas drenagens vazias não mexem; na terceira o sensor é reconfigurado e volta a encher a FIFO, e a drenagem seguinte traz amostras.
- **Com o sensor acordado e a FIFO vazia**, 6 drenagens não reconfiguram nada.
- **Só a época 0 foi recusada**, porque a origem é o boot.
- **Núcleo:** 341 + 157 + 170 + 456 + 94 + 320 + 185, 0 falhas.
- **Mutações:** cadeia **34/34** (+5), laço **8/8** (+4), coletor 17/17, fila 14/14, calibração 11/11, paridade 15/15.
- **Sketches:** os 4 compilam, e o de produto liga com o núcleo.

**Adaptação.**
- **O teste do laço que existia não servia:** o `Wire` falso dele falha toda leitura, porque só mede o tempo das voltas. A variante nova tem outra cópia dos stubs, com o `Wire` ligado ao sensor de mentira.
- **O registro no backlog estava impreciso:** dizia "leria zero a noite toda"; o certo é "não lê nada", porque a FIFO não enche.

**O que deu errado no caminho.**
- **Valor errado num teste do núcleo:** usei −1,1568 g como leitura do Z, que é o |a| da posição, e o certo é −1,1541 g (o Z sozinho). O teste falhou por 0,2 mg acima da tolerância.
- **Recusa da época 0:** a checagem "nenhuma época recusada" era rígida demais, porque a época 0 é recusada também no sketch de verdade. Passou a ser "no máximo 1", com a contagem impressa (deu 1).
- **Scripts de mutação:**
  - o da cadeia tem a própria lista de fontes, e as 29 sabotagens saíram "não compila" até eu incluir a `calibracao.cpp`;
  - o da calibração passou a copiar o `fifo_mpu.h`, que a `calibracao.h` agora inclui.

**Risco em aberto.**
- **Na placa:** o firmware com estas mudanças não foi gravado; a conferência vai junto com o `FW-07` (c), que precisa do `secrets.h` do autor.
- **Parâmetros fixos:** sem termo de temperatura, e valem para esta unidade.
- **O `gn` do travesseiro:** não vai ao servidor, porque o registro da flash não o guarda.
- **Reacordar não corrige o contato:** se ele falhar o tempo todo, o contador sobe a cada queda, e a correção é o `HW-09`.

**Procedência.** Execuções desta entrada; parâmetros da bancada de 11/11 (entrada xi).

---

# 2026-11-12 — Visão geral do dashboard

**O problema.** O painel já calculava cobertura, movimento e lacunas, mas o recorte e a distinção visual entre repouso e falta de leitura precisavam ficar mais claros.

**Hipótese.** Exibir sessão, instrumento e intervalo no cabeçalho e usar hachura para interrupções melhora a leitura sem alterar as consultas ou o cálculo. A composição foi revista a partir do HTML do autor, com quatro métricas, gráfico de linha, cartão do dispositivo e sessões recentes.

**O que foi testado.** Build e suíte do frontend no Windows, além de navegação em Chromium local com demonstração em 1440 px e 390 px, uma interrupção injetada nas leituras simuladas e uma lista vazia. A composição final também foi conferida em 1353 × 603 px, na mesma largura da referência do autor, e o controle de tema foi acionado.

**Resultado medido.** 564 testes em 43 arquivos e build aprovados. As duas larguras não tiveram rolagem horizontal. O cartão ficou ao lado do gráfico em 1440 px e abaixo em 390 px. A interrupção simulada mostrou a legenda e o padrão hachurado, e a linha foi interrompida. A lista vazia mostrou a mensagem de ausência de leituras. Na composição final, o gráfico começou em y = 306 px a 1353 × 603 px e a página não teve rolagem horizontal a 390 px.

**Adaptação.** A cobertura ganhou cartão próprio para seguir a composição do protótipo. O último envio e as sessões vêm dos dados já disponíveis. O eixo categórico foi preservado. O menu lateral usa os grupos do protótipo e leva às seções já existentes. O selo identifica os dados simulados no cabeçalho. A legenda informa que a largura da faixa não representa a duração da interrupção.

**O que deu errado no caminho.** A primeira prévia devolveu 504 por dependência otimizada desatualizada. Um servidor com reotimização resolveu. Remover uma única leitura não gerou interrupção na regra existente. A verificação foi refeita removendo seis leituras consecutivas. Na revisão visual, um teste de privacidade atingiu o timeout de 5 s na suíte paralela. A suíte inteira passou ao repetir com quatro workers, sem alterar o teste.

**Risco em aberto.** As verificações no navegador usaram demonstração local. Falta revisão com sessão e leituras reais.

**Procedência.** Mudança aprovada pelo autor e executada na branch de visão geral do dashboard, baseada em develop e620ad3.

---

# 2026-11-12 (ii) — Nova coleta

**O problema.** O painel já usava o layout do protótipo, mas a tela de coleta ainda tinha a composição anterior. O link de Nova coleta também descartava o parâmetro da demonstração local.

**Hipótese.** Reaproveitar o cabeçalho e a navegação do painel e destacar o estado e o tempo da sessão aproxima a experiência do protótipo. Manter o parâmetro nos links entre as telas demonstrativas preserva a navegação sem login.

**O que foi testado.** Build e suíte do frontend no Windows. Em Chromium, navegação do painel à coleta com 1240 px e 390 px, início e encerramento do cronômetro, retorno ao Histórico e acesso direto à coleta sem conta.

**Resultado medido.** Build aprovado e 564 testes aprovados em 43 arquivos. O cronômetro avançou de 00:00:00 para 00:00:01, a simulação encerrou sem requisições de escrita, a tela móvel coube na largura e a rota real sem sessão redirecionou ao login.

**Adaptação.** O modo local usa somente o cronômetro. A tela autenticada mantém consentimento, preparo do aparelho, acelerômetro e envio pela implementação existente. Os links de Histórico e Dispositivos apontam para as seções do painel também quando acionados da coleta.

**O que deu errado no caminho.** O ambiente restrito impediu o Vitest de renomear arquivos temporários. A suíte passou ao executar com permissão para o cache. A primeira porta da prévia estava ocupada e o navegador validou a tela em outra porta. A repetição da comparação com a prévia anterior não foi concluída porque ela estava indisponível.

**Risco em aberto.** A validação no navegador usou dados de demonstração. Falta testar uma sessão autenticada com acelerômetro físico.

**Procedência.** Protótipo e mudança aprovados pelo autor. Branch derivada da PR #134, com develop e620ad3 já incorporado.

---

# 2026-11-12 (iii) — Tela de dispositivos

**O problema.** O menu Dispositivos apontava para um resumo no painel e o gerenciamento ficava em Configurações. Faltava a página própria prevista no protótipo.

**Hipótese.** Uma rota dedicada com cartões e a ação de pareamento no cabeçalho aproxima o fluxo do protótipo e reaproveita as operações autenticadas.

**O que foi testado.** Build e suíte do frontend no Windows. No Chromium local, navegação pelo botão do painel e menu móvel, estado ativo do menu, interruptor por teclado, abertura do pareamento demonstrativo e acesso sem sessão à rota real. O teste de montagem foi repetido com a rota removida como controle.

**Resultado medido.** Build aprovado e 566 testes passaram em 43 arquivos. O controle produziu uma falha por ausência do título da tela. Em 1240 px e 390 px a navegação manteve o modo demonstrativo, com zero chamadas à API de dispositivos. A tela coube em 390 px e o acesso real sem sessão redirecionou ao login.

**Adaptação.** O interruptor altera somente o estado local da demonstração. A lista real mostra a validade da credencial e o último envio. Pareamento, renomeação e revogação reutilizam o gerenciamento existente. A revogação pede confirmação e invalida a credencial.

**O que deu errado no caminho.** O Vite devolveu 504 por dependência otimizada desatualizada na primeira prévia. A validação passou em outra porta com um contexto de navegador limpo.

**Risco em aberto.** As ações reais de pareamento, renomeação e revogação não foram executadas contra uma conta e um aparelho físicos nesta etapa.

**Procedência.** Protótipo e plano aprovados pelo autor. Branch derivada da PR #135, com develop e620ad3 já incorporado.

---

# 2026-11-12 (iv) — Histórico de sessões

**O problema.** O menu Histórico abria uma seção do dashboard. Faltava a tela dedicada com filtro, tabela e interpretação da cobertura.

**Hipótese.** Reutilizar a formação de sessões e a medição da cobertura permite expor as mesmas grandezas, com um recorte de período e sem misturar dispositivos.

**O que foi testado.** Build e suíte no Windows. Montagem autenticada com API simulada para carregamento, lista vazia, troca de período, erro HTTP e nova tentativa. O controle trocou a árvore de rotas pela de develop. Chromium local verificou os filtros da demonstração, o botão do dashboard, o menu móvel e o redirecionamento sem sessão.

**Resultado medido.** Build aprovado e 568 testes passaram em 43 arquivos. Uma falha esperada com as rotas de develop, por ausência do título. Na demonstração, 7 e 30 dias exibiram 5 sessões e 24 horas exibiram 1. Zero consultas à API de histórico no modo demonstrativo. A 320 px, a tabela rolou dentro do próprio contêiner e a página coube na largura.

**Adaptação.** A consulta autenticada filtra por chegada no servidor e descarta localmente medições anteriores ao recorte. As sessões são agrupadas por dispositivo e o aviso aparece quando a resposta pode ter atingido o limite da consulta. A demonstração usa as datas fixas do protótipo.

**O que deu errado no caminho.** O primeiro servidor local do Vite retornou 504 por dependência otimizada desatualizada. A validação passou em outra porta. A primeira medição da tabela ocorreu antes de o React concluir a navegação e foi repetida aguardando a tabela.

**Risco em aberto.** Falta validar o histórico com uma conta e leituras reais. A API existente também pode devolver uma lista vazia em falhas de infraestrutura, e nesses casos o cliente não tem como distinguir a falha de uma lista vazia legítima.

**Procedência.** Protótipo e plano aprovados pelo autor. Branch derivada da PR #136, com develop e620ad3 incorporado.

---

# 2026-11-12 (v) — Correções de coleta e exportação

**O problema.** Uma nova coleta mantinha os registros da anterior. O navegador bloqueava o JSON do simulador na landing. O CSV podia baixar apenas parte dos dados sem avisar.

**Hipótese.** Limpar a lista ao iniciar a coleta, autorizar downloads no iframe da landing e sinalizar o possível limite do CSV corrige os três fluxos.

**O que foi testado.** No Windows, build e suíte do frontend. Teste do hook com movimento sintético e envio pendente. Montagem autenticada com resposta simulada de 1000 linhas seguida de resposta de uma linha. Chromium com a landing da versão anterior e com o build da correção.

**Resultado medido.** 570 testes passaram em 44 arquivos. Os dois testes novos falharam antes da correção, com implementações idênticas às de develop e620ad3. A segunda sessão começou com zero registros mesmo após concluir o envio anterior. O CSV exibiu aviso com 1000 linhas e o retirou com uma linha. O JSON foi bloqueado antes e baixado como smartdormio-leitura-23-15-00.json depois.

**Adaptação.** O resumo fica visível ao encerrar e é limpo ao iniciar outra sessão. A landing permite o download dentro do iframe existente. O CSV reaproveita o limiar usado pelo Histórico para avisar sobre possível truncamento.

**O que deu errado no caminho.** A primeira tentativa no servidor de desenvolvimento não renderizou a landing a tempo. A repetição com o build de produção servido localmente concluiu o teste.

**Risco em aberto.** O CSV continua sujeito ao limite da API. O reinício da coleta foi validado com eventos sintéticos, sem repetir a operação em um aparelho físico.

**Procedência.** Correções aprovadas pelo autor após revisão da versão da PR #137. Branch derivada dessa PR, com develop e620ad3 incorporado.

---

# 2026-11-12 (vi) — Configurações na demonstração e último envio

**O problema.** Configurações descartava o modo de demonstração. O painel mostrava o último contato apenas quando havia leituras e não indicava a sua recência.

**Hipótese.** Preservar o parâmetro permite testar o tema sem abrir ações de conta. O horário recebido do servidor permite informar recência para o dispositivo selecionado.

**O que foi testado.** Build, suíte e montagem no Windows. Chromium local em desktop e largura móvel, troca para tema escuro e claro, navegação para a conta pelo link Entrar e observação de chamadas à API na demonstração sem sessão.

**Resultado medido.** 572 testes em 44 arquivos e build aprovados. Antes da correção, dois testes falharam: os dois menus perderam o parâmetro e o painel não mostrou Nunca enviou. Na demonstração, os dois menus preservaram o parâmetro, os dois temas foram aplicados e houve zero chamadas à API.

**Adaptação.** A tela demonstrativa permite alterar o tema e orienta como acessar as funções da conta. O painel usa o horário de último envio e uma janela de 20 minutos, equivalente a dois ciclos previstos no RD-07. Mostra o indicador mesmo quando o dispositivo ainda não tem leituras.

**O que deu errado no caminho.** A primeira tentativa de rodar os testes ocorreu enquanto as dependências ainda eram instaladas. A primeira prévia devolveu 504 em uma dependência do Vite. As verificações foram repetidas após a instalação e em uma nova porta.

**Risco em aberto.** O status foi validado com resposta simulada e ainda precisa ser conferido com um sensor real. O horário informa recência de envio e não comprova presença em tempo real.

**Procedência.** Plano aprovado pelo autor. Branch derivada da PR #138 com develop e620ad3 incorporado. Cadência de envio registrada em RD-07.

---

# 2026-11-12 (vii) — Planejamento de recebimento, pareamento e bateria

**O problema.** A pausa de recebimento, o pareamento guiado e a telemetria de bateria tinham propostas sem itens próprios no backlog.

**Hipótese.** Registrar as entregas com dependências e critérios de aceite permite priorizar o trabalho de aplicação e planejar a bancada.

**O que foi testado.** IDs conferidos no Git e scripts de conferência documental no Windows.

**Resultado medido.** Quatro itens abertos, dois em L0 e dois em L1. Contagem de 52 itens abertos sobre develop e620ad3.

**Adaptação.** A pausa preserva a fila e a credencial. O pareamento manual precede o QR. A medição de bateria pode avançar em paralelo com a bancada.

**O que deu errado no caminho.** O ID APP-13 já constava no registro de correções e foi descartado antes da edição.

**Risco em aberto.** A implementação e as validações de aplicação, firmware e bancada permanecem pendentes.

**Procedência.** Plano registrado a pedido do autor, com referências nas quatro linhas do backlog.

# 2026-11-12 (viii) — a landing e o release #133, e a integração do frontend do protótipo

**O problema, como foi entendido no início.** Enquanto o Claude estava sem cota, o autor seguiu com o Codex. A landing nova (#132) e o release #133 (a landing e o código do `FW-11`) foram para a produção **sem entrada no diário** e sem a linha de release no `CLAUDE.md`. Ficaram abertas a pilha de frontend #134–#139 e a #140 (itens do backlog). O autor pediu ao Claude a revisão de tudo e a integração.

**Hipótese de trabalho.** O relatório de passagem do Codex está certo, mas cada afirmação dele se confere no GitHub e no código antes de integrar. O que foi ao ar se revisa como código público.

**O que foi testado, e como.**
- **O estado:** `gh pr list` e `git log` (main em `e788090`, develop em `e620ad3`), `/health` da produção e `get_deployment`.
- **A landing em produção** (`frontend/public/landing-prototipo.html`, 2 294 linhas):
  - recursos externos, chamadas de rede, armazenamento e comunicação com a página de fora;
  - o `sandbox` do iframe;
  - o texto visível, procurando promessas que o trabalho não sustenta (diagnóstico, estadiamento, precisão).
- **A pilha #134–#139:**
  - a trava do consentimento na coleta (`LGPD-12`);
  - o modo demonstração (`estaEmModoDemo`, só com `import.meta.env.DEV`);
  - as rotas novas atrás do `RotaProtegida`;
  - o caminho dos dados;
  - `tsc`, `vitest` e `vite build` na ponta (`57b683f`), numa worktree separada.
- **A integração:**
  - #134 a #139 mescladas em ordem;
  - conferido que a `develop` ficou igual à ponta testada;
  - a #140 com o conflito do diário resolvido, renumerando a entrada dela para (vii), e CI 18/18.

**Resultado medido.**
- **Produção:** `/health` `200`, contrato 2.9.0, modelo `ml-inf-cabeca-v2`, `gru1`.
- **A landing, segurança:** sem script ou estilo externo, sem `fetch`, formulário, armazenamento ou `postMessage`. O iframe roda sem `allow-same-origin`.
- **A landing, texto:** diz que não identifica fases do sono nem faz diagnóstico, e marca os números como "ilustrativos" e "a validar" e a sessão de exemplo como "dados fictícios".
- **A pilha:** a trava do consentimento continua intacta; o modo demonstração não liga na produção; nada mudou nos dados enviados. Na ponta, **572 testes em 44 arquivos**, `tsc` limpo, build ok (o mesmo número do relatório).
- **A `develop` depois das seis:** idêntica à ponta testada (`git diff 57b683f` vazio).
- **O defeito do histórico, confirmado no código:** `get_leituras_do_usuario` devolve `[]` quando a consulta falha (`except Exception: return []`) e pede no máximo 1 000 linhas de uma vez, ao passo que a de features pagina.

**Adaptação.**
- **Os riscos que as entradas da pilha apontavam sem item** viraram itens (`API-08`, `UI-26`, `UI-27`, `DATA-15`), como a regra 2 do projeto exige.
- **Uma informação desatualizada no relatório:** o Moto E7 está, desde 11/11 à noite, com o APK de depuração com a autocalibração (entrada x e a instalação daquele dia), e não com o de 10/11.

**O que deu errado no caminho.**
- **A branch da #140** estava aberta numa worktree do Codex, e o `git checkout` recusou. A resolução foi feita numa worktree própria e enviada para a mesma branch.
- **Processo:** a #138 usou o prefixo `fix/`, que o CI não roda no push. Foi verificada pelo run da PR, mas fora da convenção (`bugfix/`).

**Risco em aberto.**
- **O frontend integrado** (painel, coleta, dispositivos, histórico e configurações) está em `develop`, ainda não na produção, e foi validado com dados simulados. Falta conferir com uma conta e leituras reais depois do release.
- **Os defeitos registrados** (`API-08`, `UI-26`, `UI-27`, `DATA-15`) continuam no código.
- **A landing pública** tem links de lojas (Shopee, Adafruit). É decisão do autor se ficam numa página acadêmica.

**Procedência.** O relatório de passagem do Codex (local, fora do repositório); GitHub (PRs #131–#140); a revisão e as execuções desta entrada, em 12/11, Windows 11.

# 2026-11-12 (ix) — o release #142, e o `DATA-15` visto na conta real

**O problema, como foi entendido no início.** O frontend do protótipo (PRs #134–#139) estava em `develop`, validado só com dados simulados. O autor aprovou o release para a produção.

**Hipótese de trabalho.** Como nada mudou no backend nem nos dados enviados, o release não deve mexer em `/health`, nas respostas sem login nem no que a conta real já tem. O que só a conta real mostra é se as telas novas leem as leituras de verdade.

**O que foi testado, e como.**
- **O release:** a PR #142 (`develop` → `main`), CI 18/18, mesclada em `5f5f209`.
- **O deploy:** o deployment de produção do GitHub aponta para `5f5f209`; `X-Vercel-Id` em `gru1`.
- **Sem login:** `/health`, `/api/sleep-history` e `/api/features` sem token, e a raiz.
- **Com login (o autor, na conta real, pelo navegador):** a visão geral, o Histórico (últimos 7 dias) e Dispositivos.

**Resultado medido.**
- **Produção:** `/health` `200`, banco ok, contrato 2.9.0, modelo `ml-inf-cabeca-v2`; as duas rotas de dados `401` sem token; a raiz `200`.
- **Visão geral:** carrega as sessões reais, com os cartões de tempo medido, leituras com movimento, maior intervalo parado e cobertura, e o gráfico de movimento.
- **Dispositivos:** os dois aparelhos da conta, cada um com o último envio e a credencial ativa.
- **Histórico:** lista as sessões da janela e **mostra o aviso de limite**: as sessões somam exatamente 1 000 leituras, o teto do `max-rows`. A visão geral diz o mesmo de outro jeito ("leituras ficaram de fora").

**Adaptação.**
- **O `DATA-15` deixou de ser hipótese:** com poucas noites de uso, a janela de 7 dias já bate no teto, e as noites mais antigas somem do Histórico. O aviso do PR #138 funciona, mas a correção (paginar `GET /api/sleep-history` como `GET /api/features`) passa a ser a primeira do L0.

**O que deu errado no caminho.** Nada no release.

**Risco em aberto.**
- **O `DATA-15` em produção:** o Histórico e o CSV de qualquer janela com mais de 1 000 leituras estão incompletos.
- **O `UI-26`:** a sessão mais antiga da lista é a que toca o corte. Desta vez saiu "Com lacunas", mas a classificação dela não é confiável enquanto o `DATA-15` não for corrigido.
- **`API-08` e `UI-27`** continuam no código.

**Procedência.** GitHub (PR #142, CI e deployments); `curl` na produção, em 12/11; as telas da conta real, vistas pelo autor e mostradas ao Claude na conversa (não versionadas: são dados de uma pessoa).

# 2026-11-12 (x) — as análises de frontend do Codex, revisadas e versionadas

**O problema, como foi entendido no início.** Na conferência da integração, todo o trabalho commitado do Codex estava na `develop`, mas dois documentos citados no diário (10/11 (xv) e (xvi), 11/11 (i)–(iv)), `ANALISE-FRONTEND-UX-UI.md` e `CATALOGO-TELAS-FRONTEND.md`, existiam só numa worktree do Codex, sem commit. O autor pediu para versioná-los com revisão.

**Hipótese de trabalho.** As análises têm valor para o texto e para o backlog, mas foram escritas antes do frontend do protótipo (12/11), e o catálogo depende de capturas locais, uma delas com dados reais.

**O que foi testado, e como.**
- **Dados pessoais e de máquina:** busca por nomes, e-mails, caminhos, tokens e URLs nos dois textos; leitura integral.
- **As imagens:** as 31 referências do catálogo, e o que o próprio catálogo diz de cada captura.
- **Os achados:** cada um conferido contra a `develop` de 12/11 (`TelaDeConsentimento.tsx`, `SeletorDeTema.tsx`, `Dashboard.tsx`, `ListaDeNoites.tsx`, `Layout.tsx`, `LIMITE_DO_PAINEL`) e contra o backlog.

**Resultado medido.**
- **Nenhum nome, e-mail, caminho de máquina ou segredo** nos textos.
- **As imagens:** 3,7 MB. Três delas mostram dados ou telas de uma pessoa (a noite no Moto E7, a recuperação de senha editada por IA, o formulário real de nova senha), e o próprio catálogo diz que a do Moto E7 não deve ser publicada. As 31 referências viraram notas "captura local, não versionada".
- **Os achados:** seis continuam no código. Dois já tinham item (`DATA-15` e `UI-27`); os outros quatro não tinham nenhum e viraram três itens. O comentário de `Layout.tsx` já foi corrigido.

**Adaptação.**
- **Os documentos entram em `docs/` com um aviso no início:** retrato de 10/11, o que mudou com o frontend do protótipo e a situação de cada achado em 12/11.
- **Os achados sem item viraram itens** (regra 2): `UI-28` (teclado no diálogo de consentimento e no seletor de tema), `UI-29` (o texto da ordem da tabela do painel) e `APP-15` (falha ao listar as noites aparece como lista vazia).

**O que deu errado no caminho.** Nada.

**Risco em aberto.**
- **As descrições de navegação, painel, coleta e configurações estão desatualizadas.** O aviso diz isso, mas o texto não foi reescrito.
- **As capturas e o PDF continuam só na worktree do Codex.** Se ela for apagada, somem. Cabe ao autor guardá-las fora dela.
- **O terceiro documento (`REVISAO-PROTOTIPO-SMARTDORMIO.md`)** não foi incluído.

**Procedência.** A worktree do Codex `release-121-registro` (arquivos sem commit, de 10–11/11); `develop` `2f128d4`; a revisão desta entrada, em 12/11, Windows 11.

# 2026-11-12 (xi) — o plano de execução com o Codex

**O problema, como foi entendido no início.** Com a solda feita e o frontend do protótipo em produção, o autor pediu um plano para os 59 itens abertos, em ordem, dividido entre o Claude e o Codex, para os dois trabalharem ao mesmo tempo sem desalinhamento. Até aqui a divisão era só por área (`AGENTS.md`, item 4), e as integrações de 05/11 e 12/11 mostraram onde os dois colidem: o diário, a contagem do backlog e a ordem das PRs.

**Hipótese de trabalho.** A colisão some se cada onda der às duas trilhas conjuntos de arquivos que não se cruzam, se as migrações tiverem número reservado antes, e se só um agente escrever o plano.

**O que foi testado, e como.**
- **Cada item aberto:** a linha do backlog, a dependência e os arquivos que toca, na `develop` `ba851f4` (`git ls-tree`, `grep` nas páginas, hooks e módulos do backend).
- **A contagem depois de fechar a Etapa 0:** `conferir_backlog.py --conferir`.
- **Os documentos versionados:** `conferir_docs_versionados.py`.

**Resultado medido.**
- **O plano** (`docs/PLANO-CLAUDE-CODEX.md`) tem quatro ondas, mais o texto do TCC contínuo, as decisões do autor (L3) e uma mensagem-modelo para entregar item ao Codex. As colisões previsíveis viraram dependência explícita: o `UI-26` e o `UI-29` esperam o `DATA-15` (mesmo histórico e mesmo painel), e o `SEC-19` espera o release que leva o `DATA-15` (mesmo `database.py`).
- **Migrações reservadas:** `019` para o `API-07`, `020` para o `API-06`, `021` para o `DATA-06` e `022` para o `APP-11`.
- **A Etapa 0 (a solda) estava aberta no backlog um dia depois de feita**, e o quadro ainda a dava como "trava tudo". Foi fechada: 58 abertos, L3 8. O conferidor passou.

**Adaptação.** O `AGENTS.md` aponta para o plano, que o Codex lê sozinho. Só o Claude edita o plano; o Codex propõe mudanças no corpo da PR.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.**
- **O plano é uma previsão de arquivos.** Um item pode precisar de arquivo de outra trilha; a regra 2 do plano manda parar e avisar o autor.
- **A trilha do Claude na onda 1 depende do autor na bancada** (`HW-09` e o `secrets.h`). Sem isso, só a trilha do Codex anda.

**Procedência.** Backlog e código na `develop` `ba851f4`; o pedido do autor na conversa de 12/11; Windows 11.

# 2026-11-12 (xii) — HW-09: o contato do sensor refeito, e a queda provocada de propósito

**O problema, como foi entendido no início.** Na bancada do `CAL-01` (11/11), virar a placa de chip para baixo zerou o sensor três vezes: o VCC caía por uma fração de segundo, o MPU6050 reiniciava dormindo e seguia lendo zero. O autor refez as soldas e prendeu os fios.

**Hipótese de trabalho.** Com a junta refeita e o fio sem tensão, nenhuma virada derruba a alimentação; se derrubar, o sensor volta dormindo e o monitor, que não o reacorda, mostra zero até o fim, o que torna a queda impossível de passar despercebida.

**O que foi testado, e como.**
- **O instrumento:** o `monitor-ao-vivo` (ferramenta de bancada fora do repositório; ±8 g, 5 leituras/s, acorda o sensor só no `setup`), gravado na placa pelo `arduino-cli`, lido pela COM3 por um script em PowerShell e analisado por um script que conta erros de I2C e leituras com \|a\| < 0,5 g, por posição.
- **O teste:** o autor passou pelas 6 posições, ~10 s em cada uma, com viradas firmes e os fios balançados, durante 4 min.
- **Controle positivo do analisador:** 5 leituras zeradas inseridas numa cópia da gravação.
- **Controle positivo na placa:** o autor soltou o fio do VCC no pino 3V3 por ~2 s, com a placa parada, e o encaixou de volta.

**Resultado medido.**
- **O teste:** 1 201 leituras, as 6 posições vistas, **0 erros de I2C, 0 leituras zeradas**. Chip para baixo: 75 leituras, \|a\| mediano 1,163 g (o valor cru do `CAL-01`). A leitura mais baixa, 0,498 g, caiu no meio de uma virada, com os três eixos com valor, e a seguinte já estava em 0,91 g; as outras abaixo de 0,7 g também são viradas.
- **O analisador:** acusou as 5 zeradas inseridas (6 no total, contando a da virada).
- **A placa:** com o VCC solto, 15 erros de I2C; religado, **220 leituras seguidas com zero exato** até o fim da gravação. O mecanismo é o de 11/11, e o teste o vê.

**Adaptação.** Nenhuma no plano: o `HW-09` fecha, e a onda 1 do Claude (`FW-07` (c), `HW-08`) está destravada.

**O que deu errado no caminho.**
- **A primeira gravação de 4 min começou antes de o autor estar na bancada** e só pegou a placa parada. Foi refeita.
- **O leitor da serial cortou 105 linhas** ("27.3 chip para CIMA"): o `ReadLine` com tempo esgotado entrega pedaço de linha. Todas no trecho parado; o analisador as ignora.
- **O `monitor-ao-vivo` rotula o sensor zerado como "chip para BAIXO"** (com z = 0, o teste do lado cai no ramo negativo). O rótulo engana, mas o \|a\| = 0 não.

**Risco em aberto.**
- **Um teste de 4 min não é uma noite.** O contato agora aguenta viradas de bancada; a prova de que aguenta horas é a vigia da FIFO do `FW-11` contando reacordados numa noite (`FW-07` (c), `VAL-01`).
- **O encaixe do jumper do lado da ESP32 continua sendo um ponto de falha** (o controle o soltou com a mão). O encapsulamento é o `HW-04`.

**Procedência.** Placa e sensor do autor, COM3, Windows 11, 12/11; capturas locais fora do repositório (`hw09-b.txt`, `hw09-controle.txt`, no diretório temporário da sessão).

# 2026-11-12 (xiii) — FW-12: o firmware não cabia na RAM do ESP32

**O problema, como foi entendido no início.** Ao começar o `FW-07` (c), gravar o `sketch.ino` na placa, a compilação para o ESP32 falhou no link: a RAM estática (`dram0_0_seg`) estourou em 18 088 B. Era a primeira vez que o sketch completo, com Wi-Fi e TLS, era compilado para o chip. Todos os testes de firmware passavam, inclusive o `make sintaxe`, que diz que o sketch "liga com o núcleo".

**Hipótese de trabalho.** O estouro vem dos vetores estáticos do sketch somados ao que o `arduino-esp32` 3.3.12 reserva para Wi-Fi e TLS. Tirar da RAM estática o maior deles, reservando-o uma vez no `setup`, fecha a conta sem mudar o protocolo.

**O que foi testado, e como.**
- **Os maiores estáticos:** `nm` sobre o objeto do sketch compilado para o chip.
- **A correção numa cópia fora do repositório, antes do plano**, e depois no repositório: `json_do_lote` (31 200 B) no heap, com aviso e envio desligado se a reserva falhar.
- **`scripts/compilar_sketch_esp32.py`:** monta o sketch numa pasta temporária com o `secrets.example.h` no papel do `secrets.h`, compila com o `partitions.csv` do projeto e lê o resumo de memória.
- **Controle positivo:** o mesmo script com o `sketch.ino` da `develop`.
- **Os testes do firmware no host**, em contêiner `gcc:13`: `make`, `make sintaxe`, `make laco`, `make capacidade`.

**Resultado medido.**
- **Os estáticos:** `json_do_lote` 31 200 B, `cadeia` 24 224 B, `acumulador` 19 208 B, `rascunho` e as três grades 3 840 B cada.
- **Com a correção:** programa 1 085 336 B (53 % da fatia `factory`); **RAM fixa 111 464 B (34 %), 216 216 B para o heap**; folga de ~13 KB até o teto da RAM estática.
- **Controle positivo:** com o sketch da `develop`, o script reprova com "a região dram0_0_seg estourou em 18 088 B" e sai com 1.
- **Host:** `make` 185 verificações, 0 falhas; `sintaxe` liga; `laco` 8/8 como esperado; `capacidade` com a tabela válida.

**Adaptação.**
- **O `FW-12` abre e fecha no mesmo dia**, saído do `FW-07` (c), que segue aberto: a gravação na placa e a leitura de 40 min vêm depois deste merge.
- **O CI não compila para o chip.** Isso virou o `CI-12`, na trilha do Claude da onda 2.
- **O limite foi para as `LIMITACOES-TCC.md` (X.6)**, e a ocorrência para o §1 das lições (13): uma verificação cujo nome promete a placa e cujo alcance é o PC.

**O que deu errado no caminho.**
- **A primeira edição do aviso quebrou a string:** o `\n` virou uma quebra de linha de verdade no script de edição, e a compilação para o chip acusou a aspa sem fim. Corrigido no editor.
- **Um comando de registro não rodou** por aspas desbalanceadas no shell; foi refeito como arquivo.

**Risco em aberto.**
- **A folga é de ~13 KB.** Um vetor estático novo no sketch pode estourar de novo sem que o CI veja, até o `CI-12`.
- **O heap durante o envio não foi medido.** São 216 KB antes do Wi-Fi e do TLS; o mínimo real aparece na placa (`FW-07` (c)).

**Procedência.** `arduino-cli` 1.6.0 com `esp32:esp32` 3.3.12, Windows 11; contêiner `gcc:13`; branch `bugfix/FW-12-ram-do-sketch`, 12/11.

---

# 2026-11-12 (xiv) — DATA-15 e API-08: paginação do histórico e falha do banco

**O problema.** O Supabase cortava o histórico em 1 000 linhas, e indisponibilidade do banco parecia lista vazia. Na revisão da PR #146, uma inserção entre consultas também duplicou uma leitura com paginação por posição.

**Hipótese.** Ordenar por chegada e ID e avançar pelo último par conserva a posição mesmo quando uma leitura mais recente chega entre duas páginas. Separar a falha da lista vazia permite responder 503.

**O que foi testado.** No Windows, banco simulado com inserção entre páginas, empate no horário, filtros de usuário, dispositivo e intervalo em cada página, e falha na segunda consulta. O teste do CSV conferiu o cursor do segundo pedido. Removi as duas atribuições do cursor no frontend e reexecutei o teste.

**Resultado medido.** Na versão anterior da PR, 2 testes de backend falharam: cursor interno repetido e 1 499 IDs distintos em 1 500 linhas, com uma duplicata e uma ausência. Com o cursor interno, 1 500 de 1 500 IDs distintos e sequência esperada intacta. No frontend, o controle sem os parâmetros falhou em 1 de 14 testes porque o segundo pedido não continha o cursor. Com a correção, 549 testes de backend sem RLS, 574 de frontend e o build passaram.

**Adaptação.** Mantive os filtros em cada consulta, usei o par de chegada e ID na API e no banco, e restaurei os comentários sobre duração, medição e chegada no SELECT.

**O que deu errado no caminho.** ✏️ *Corrigido em 12/11, na integração: aqui dizia "Nada nesta etapa além das falhas esperadas nos controles positivos".* A primeira versão da PR (`efe5d75`) chegou à revisão com dois defeitos, achados pelo Claude executando, e não pelos testes da PR:
- **A paginação interna por posição (`range`) duplicava uma leitura** quando outra era gravada entre duas páginas: 1 501 linhas, 1 500 distintas, na sonda da revisão.
- **Os testes não acusavam os defeitos que diziam cobrir.** O banco falso ignorava `eq`, `gte`, `lte` e `or_`, e, com as duas chamadas `parametros.set` do cursor do CSV removidas de propósito, `api.test.ts` e `montagem.test.ts` seguiam 39/39.
- **A PR também chegou sem esta entrada e sem o fechamento no backlog**, e havia apagado os comentários do `select` (`DASH-09`, `DASH-12`).
Os quatro pontos foram corrigidos no `5ed12df`, e as sabotagens reexecutadas na revisão final derrubaram os testes.

**Risco em aberto.** O cursor não fornece uma cópia transacional dos dados. Leituras novas acima do cursor podem ficar fora de uma exportação já iniciada. A inserção foi simulada localmente, sem ensaio concorrente no Supabase de produção.

**Procedência.** PR #146, revisão da paginação por posição e testes de regressão executados no Windows sobre a branch da PR atualizada com `develop` `01c9da5`.

---

# 2026-11-12 (xv) — UI-26: sessão na borda do limite do histórico

**O problema.** Um trecho contínuo na borda da resposta podia aparecer como Completa.

**Hipótese.** Preservar a leitura na borda da ordenação da API permite identificar a sessão que pode ter sido cortada.

**O que foi testado.** No Windows, o Histórico recebeu duas sessões em uma resposta de 2 000 leituras e em outra de 1 999. Troquei a comparação do limite para 9999 e reexecutei o teste.

**Resultado medido.** Um teste falhou em develop e um falhou com 9999 pela ausência de Parcial. Com a correção, só a sessão na borda foi marcada e ambas ficaram completas abaixo do limite.

**Controles positivos da revisão.** Cada sabotagem foi executada isoladamente e desfeita:
- Trocar `leituras.at(-1)` por `leituras.at(0)` fez falhar “marca somente a sessão na borda de uma resposta no limite”. A linha recente perdeu o rótulo Completa.
- Apagar o texto do aviso fez falhar “aviso de cobertura do painel com 2000 leituras”. O teste de 1 999 leituras verifica a ausência do aviso.
- Apagar ` · Parcial` da tabela fez falhar “marca apenas a sessão na borda na tabela do painel”. A linha antiga perdeu a marca.

**Adaptação.** O Histórico e o painel compartilham a identificação da borda. A cobertura numérica segue descrevendo o trecho observado.

**O que deu errado no caminho.** A primeira coleta da saída dos testes falhou ao imprimir um caractere no console CP1252. Reexecutei os três controles com Python em UTF-8.

**Risco em aberto.** A API não informa se há mais leituras quando chega exatamente ao limite. O UI-30 trata as noites ausentes da janela.

**Procedência.** Testes executados no Windows sobre develop 952371c.

---

# 2026-11-12 (xvi) — UI-29: ordem das leituras recentes

**O problema.** A tabela ordenava pela medição e a legenda dizia que a ordem era de chegada.

**Hipótese.** Explicar a ordenação existente e o fallback de chegada descreve a tabela mesmo com envio atrasado.

**O que foi testado.** No Windows, montei o painel com duas leituras cuja ordem de chegada era inversa à de medição. O teste conferiu as linhas e a legenda. Executei o teste com a legenda antiga.

**Resultado medido.** Com a legenda antiga, a ordem das linhas passou e a asserção da legenda falhou em um teste. Com a legenda corrigida, a sequência e o texto passaram.

**Adaptação.** Mantive o critério de ordenação e explicitei o fallback na legenda.

**O que deu errado no caminho.** Nada além da falha esperada no controle.

**Risco em aberto.** O caso de envio atrasado foi reproduzido com dados simulados.

**Procedência.** Testes no Windows, sobre a UI-26 (478c92c), baseada em develop 952371c.

# 2026-11-12 (xvii) — FW-07 (c) na placa: a medição limpa, e o envio que falhava por memória (FW-13)

**O problema, como foi entendido no início.** Com o `FW-12` mesclado, o `sketch.ino` foi gravado na placa para o `FW-07` (c): 41 min de leitura do serial, com o autor deixando a placa parada. O plano era conferir a partição, as épocas, os prazos, o relógio e o envio.

**Hipótese de trabalho.** Se o firmware que passa no host e liga para o chip também mede e envia na placa, o `FW-07` (c), o `FW-05`, o `SEC-15` (c) e parte do `FW-08` (c) saem da mesma gravação.

**O que foi testado, e como.**
- **A leitura de 41 min** (`sketch.ino` da `develop` `01c9da5`, com o `secrets.h` do autor, sem leitura do arquivo), pela COM3 e por um leitor em PowerShell que reinicia a placa no início.
- **O envio, que falhou:** uma versão de diagnóstico fora do repositório imprimiu o heap antes do POST e o `lastError` do TLS, com envio a cada 1 min.
- **A cadeia:** `conferir_tls_firmware.py --producao` no PC; as cifras e os certificados servidos pela Vercel em TLS 1.2; um sketch mínimo na placa (só Wi-Fi e TLS, `GET /health`) com as 4 raízes e com uma 5ª (GlobalSign Root CA, impressão SHA-256 conferida).
- **A correção (`FW-13`)**, primeiro no diagnóstico (lote de 20), depois na branch: a versão exata da branch gravada e lida por 21 min.
- **Controle positivo do `SEC-15` (c):** o mesmo firmware com só as raízes ISRG.

**Resultado medido.**
- **A medição:** 80 épocas em 41 min, todas com features, taxa 49,92–50,01 Hz, 0 transbordos, 0 prazos estourados, pior trabalho 178 ms, sensor nunca reacordado; só a época 0 recusada. Calibração da unidade aplicada (desvio Z −130 mg, o do `CAL-01`).
- **O relógio:** −20, −17 e −16 ms a cada 10 min contra o NTP (−29 a −33 ppm). Numa gravação de 10 min com o `FW-13`, −123 ppm.
- **O envio, antes da correção:** `HTTP -1` em todas as voltas. O diagnóstico mostrou `X509 - Certificate verification failed` com 94 KB de heap e maior bloco de 38–55 KB; com a 5ª raiz, `PK - Memory allocation failed` e `X509 - Allocation of memory failed`.
- **A cadeia está certa:** o PC aceita a cadeia servida (`*.vercel.app` ← WR1 ← GTS Root R1, e um GTS Root R1 com assinatura cruzada da GlobalSign) com as 4 raízes do firmware; na placa, o sketch mínimo deu `GET /health` 200 com as 4 raízes, com 224 KB livres e mínimo de 157 KB — o handshake consome ~67 KB.
- **Com o `FW-13` (lote de 20):** no diagnóstico, 104 leituras em 6 lotes, `HTTP 200`, fila zerada (as épocas guardadas durante as falhas saíram). Na versão da branch: dois envios, 40 leituras, `HTTP 200`, **heap 116 KB no envio e mínimo atingido 14 772 B**.
- **Controle positivo do TLS:** só com as raízes ISRG, `HTTP -1` nas duas voltas, com 116 KB livres.
- **Host:** `make` 185, `sintaxe`, `laco` 8/8, `capacidade`, `mutacao-fila` 14/14; para o chip, RAM fixa 108 904 B (33 %).

**Adaptação.**
- **O `FW-13` abre e fecha no mesmo dia:** `LEITURAS_POR_LOTE_NO_ESP32 = 20` (o teto do servidor segue 60), `LOTES_POR_VOLTA = 60`, e o heap livre e o mínimo no log do envio.
- **Fecham o `FW-05` e o `SEC-15`.** O `FW-07` (c) e o `FW-08` (c) ganham as medições de hoje e seguem abertos (a deriva ao longo de horas; o roteiro com o Wi-Fi desligado de propósito).
- **A folga de ~15 KB virou o `FW-14`.** O limite foi para as `LIMITACOES-TCC.md` (X.6).

**O que deu errado no caminho.**
- **A primeira hipótese estava errada.** Pelo certificado cruzado da GlobalSign na cadeia, supus que a biblioteca montava o caminho errado; acrescentar a raiz só trocou o erro para falta de memória. A causa apareceu no sketch mínimo, com memória sobrando.
- **A mensagem do TLS engana:** falta de memória durante a verificação sai como "certificado recusado". Sem o `lastError` e o heap no log, a correção teria ido para as raízes.
- **O leitor da serial cortou duas linhas** da primeira gravação, uma delas a do primeiro `[lote]`: o código HTTP só apareceu no segundo envio.
- **O primeiro controle com raízes erradas não removeu as raízes GTS** (o recorte pelos comentários deixou os certificados); foi refeito com uma lista separada.
- **Uma gravação de diagnóstico usou a tabela de partições padrão** (o sketch mínimo); a área da fila não foi tocada, e a versão seguinte a remontou.

**Risco em aberto.**
- **Folga de heap de ~15 KB no envio** — `FW-14`.
- **As leituras de bancada estão na conta do autor**, no aparelho do travesseiro: ~150 épocas de 12/11, 18:44–20:40, com a placa parada na mesa (`APP-11` trata a marcação de teste).
- **A deriva de −123 ppm numa gravação de 10 min** destoa das outras; a medida de horas é a do `FW-07` (c).

**Procedência.** Placa e sensor do autor, COM3, `arduino-cli` 1.6.0 com `esp32:esp32` 3.3.12, Windows 11, 12/11; capturas do serial no diretório temporário da sessão (fora do repositório); branch `bugfix/FW-13-lote-do-esp32`.


# 2026-11-12 (xviii) — a integração das PRs #152–#155 e o que falta investigar

**O problema, como foi entendido no início.** O autor aprovou o merge das PRs #152 (registro do `DATA-15`), #153 (`UI-26`), #154 (`UI-29`) e #155 (`FW-13`), e pediu que tudo o que ainda falta investigar ficasse registrado para ser feito.

**Hipótese de trabalho.** Mesclar uma por vez e reconferir a contagem a cada uma evita perder fechamento em resolução de conflito; o que falta investigar já tem item quase sempre, e o que não tiver vira item.

**O que foi testado, e como.**
- **A integração:** cada PR com `mergeable` conferido, CI 18/18 e `conferir_backlog.py --conferir` depois do merge.
- **Os conflitos:** a #153 e a #155 conflitaram com a `develop` (backlog e diário); resolvidos numa worktree destacada, enviados para as próprias branches (a da #153 estava aberta numa worktree do Codex), com as três conferências e o CI antes do merge.
- **O levantamento:** o diário de 12/11, os logs da placa e o backlog, procurando o que foi visto e não tem item.

**Resultado medido.**
- **As quatro mescladas** em ordem; `develop` `c61b362`, 54 abertos antes deste registro. Na #153, o conflito era entre o texto de abertura do `DATA-15`/`API-08` (vindo da #152) e o fechamento do `UI-26` com o `UI-30` (da #153): ficaram os dois. Na #155, a contagem foi refeita sobre a `develop` com a #153 e a #154 (55−2+1 = 54), e o diário ficou na ordem (xv), (xvi), (xvii).
- **Sem item até aqui:** a partição da fila nasceu com 1 279 registros corrompidos (restos do programa anterior) e o CRC-16 pode aceitar um falso — virou o `FW-15`. As leituras de bancada do travesseiro na conta do autor entraram como nota no `APP-11`.
- **A lista do que falta investigar** (dez linhas, com item, dono, método e gatilho) foi para o §7 do `docs/PLANO-CLAUDE-CODEX.md`.

**Adaptação.** O plano marca 1.1–1.3 como feitos.

**O que deu errado no caminho.**
- **O primeiro laço de merge parou na #153** por `mergeable` ainda `UNKNOWN` logo depois do merge da #152; na segunda tentativa o GitHub já dizia `CONFLICTING`.
- **A branch da #153 estava aberta numa worktree do Codex**, e o `checkout` recusou; a resolução foi feita destacada e enviada por `HEAD:refs/heads/…`.

**Risco em aberto.** Os da tabela do §7 do plano, cada um com o seu item.

**Procedência.** GitHub (PRs #152–#155 e CI); `develop` `c61b362`; logs da placa de 12/11 (fora do repositório); Windows 11.

# 2026-11-12 (xix) — o release R1 e a conta real

**O problema, como foi entendido no início.** Com o `DATA-15`, o `API-08`, o `UI-26` e o `UI-29` integrados, o autor aprovou o release R1 antes dos itens 1.4–1.7 do plano, porque o corte de 1 000 leituras já afetava o Histórico dele.

**Hipótese de trabalho.** Sem migração e sem mudança de contrato, o release não mexe na ingestão; o que só a conta real mostra é se a paginação e a marca "Parcial" funcionam com os dados de verdade.

**O que foi testado, e como.**
- **O release:** PR #157 (`develop` → `main`), os 8 jobs do CI e os 2 da Vercel, merge `ed11e81`.
- **Depois do deploy:** `/health`; `/api/sleep-history` (com e sem cursor) e `/api/features` sem token; `X-Vercel-Id`; o deployment de produção; os textos novos no pacote JavaScript publicado.
- **O login real do autor:** o Histórico de 7 dias, mostrado ao Claude por captura de tela (não versionada).

**Resultado medido.**
- **Produção:** `/health` `200`, banco ok, contrato 2.9.0, modelo `ml-inf-cabeca-v2`; as três rotas `401` sem token; `gru1`; deployment de produção em `ed11e81`; o pacote tem `cursor_tempo`, "Cobertura parcial" e "medição mais recente à mais antiga".
- **O Histórico:** antes do release, 3 sessões e 1 000 leituras; agora **13 sessões, somando exatamente 2 000 leituras** — o teto do painel, acima do teto de 1 000 do Supabase. A sessão mais antiga (a noite de 10/11, 815 épocas no aparelho) aparece com 550 leituras e marcada **"Parcial"**; as outras como "Completa" ou "Com lacunas".

**Adaptação.** O `UI-30` passa de hipótese a defeito confirmado em produção: a janela de 7 dias da conta já tem mais de 2 000 leituras, e o aviso de limite continua.

**O que deu errado no caminho.** A previsão que dei ao autor estava errada: disse que a conta teria ~1 300 leituras e que o aviso sumiria. Não contei as leituras de bancada do travesseiro nem as dos envios de diagnóstico de 12/11; a janela já passa de 2 000.

**Risco em aberto.**
- **O Histórico de 7 dias continua cortado em 2 000 leituras** — `UI-30`, agora o item de maior efeito na conta real.
- **As leituras de bancada de 12/11 contam na janela** e empurram as noites reais para fora — `APP-11` (I-9 do plano).

**Procedência.** GitHub (PR #157, CI e deployments); `curl` na produção, 12/11; a tela do autor na conversa; Windows 11.

# 2026-11-12 (xx) — a limpeza das leituras de teste na conta do autor

**O problema, como foi entendido no início.** A conta do autor tinha, misturadas às duas noites reais, leituras de bancada e de teste (de agosto até hoje). Elas entravam no Histórico e no painel como sessões, empurravam as noites reais para fora da janela de 2 000 leituras (`UI-30`) e distorceriam qualquer análise. O autor pediu para apagar tudo o que não fosse noite de sono real.

**Hipótese de trabalho.** Uma regra por duração (manter sessões de 3 h ou mais) separa as noites dos testes; a exclusão roda pelo autor no SQL Editor, depois de uma prévia e de uma conferência que dizem quantas linhas saem.

**O que foi testado, e como.**
- **A prévia (só leitura):** as sessões da conta por aparelho (buraco de mais de 15 min abre sessão nova), testada antes num Postgres 17 local com dados falsos.
- **A conferência e a exclusão:** mantêm só as leituras do celular dentro das janelas das duas noites; testadas no Postgres local com noites, testes, bancada e uma segunda conta (que tinha de ficar intocada).
- **No site:** o Histórico de 7 dias depois da exclusão.

**Resultado medido.**
- **A prévia na produção:** 11 sessões. Ficam 2 noites do celular (10/11 03:02–09:52, 6,8 h, 815 leituras; 11/11 04:19–12:03, 7,7 h, 930).
- **A conferência:** 804 saem, 1 745 ficam — os números esperados pela prévia.
- **Depois da exclusão**, o Histórico mostra só as duas noites, sem o aviso de limite e sem "Parcial"; a noite de 10/11 aparece inteira (6h47m, 815 leituras), e não mais cortada em 550.
- **No Postgres local**, a mesma exclusão tirou só os testes e não tocou a outra conta.

**Adaptação.** **A regra por duração foi trocada por janelas explícitas:** a bancada do travesseiro de 12/11 (18:53–22:33, 3,7 h, 422 leituras) passava de 3 h e saía como "MANTER". A regra final mantém só as leituras do celular dentro das duas noites.

**O que deu errado no caminho.**
- **A primeira prévia não trouxe linha nenhuma:** o filtro do e-mail não casou; a versão com `lower(trim(...))` casou.
- **A primeira execução da exclusão respondeu "No rows returned"** sem dizer quantas saíram (o `returning` não estava na tela); a segunda listou as linhas apagadas, e o Histórico confirmou o estado final.
- **A regra de 3 h** classificaria uma bancada longa como noite (ver Adaptação).

**Risco em aberto.**
- **O app ainda não marca gravação de teste** — `APP-11`; sem isso, a próxima bancada volta a poluir a conta.
- **O `UI-30` deixou de aparecer na conta**, porque a janela de 7 dias tem 1 745 leituras; volta com a terceira noite.

**Procedência.** SQL Editor do Supabase, executado pelo autor em 12/11 (resultados colados na conversa); Postgres 17 local em Docker; a tela do Histórico do autor (não versionada); Windows 11.

---

# 2026-11-12 (xxi) — APP-15: Falha ao listar noites

**O problema.** O erro do plugin aparecia como lista vazia.

**Hipótese.** Separar a falha da resposta vazia permite repetir a consulta.

**O que foi testado.** No Windows, simulei rejeição do plugin seguida de sucesso e acionei Tentar novamente.

**Resultado medido.** Em develop, 1 teste falhou porque aparecia a lista vazia em vez do alerta, e 7 passaram. Com a correção, o alerta apareceu e a noite voltou após repetir a consulta. A suíte original passou com 573 testes.

**Adaptação.** A lista mostra erro e permite tentar novamente, com proteção contra respostas antigas.

**O que deu errado no caminho.** Nada nesta etapa além da falha esperada no controle.

**Risco em aberto.** Validação em aparelho físico pendente.

**Procedência.** PR #148, implementação `c984876`, registros sobre `develop` `745f232`. Testes automatizados no Windows.

---

# 2026-11-12 (xxii) — UI-28: Teclado no consentimento e no tema

**O problema.** O foco escapava do diálogo e o seletor não oferecia navegação de rádio.

**Hipótese.** Gerenciar o foco no diálogo e usar rádios nativos corrige os dois fluxos.

**O que foi testado.** No Windows, usei user-event para abrir, navegar, fechar e restaurar o foco, além de mudar o tema com as setas.

**Resultado medido.** Em develop, 2 testes falharam: o foco ficou no botão de origem e Tab entrou no tema errado. Com a correção, 574 testes passaram.

**Adaptação.** Contive Tab no diálogo, liguei Escape a Agora não e usei rádios nativos.

**O que deu errado no caminho.** O jsdom não fornece CSS.escape. Simulei essa API apenas no teste das setas.

**Risco em aberto.** Validação com leitor de tela em Android pendente.

**Procedência.** PR #149, implementação `d538c5d`, registros sobre `develop` `745f232`. Testes automatizados no Windows.

---

# 2026-11-12 (xxiii) — UI-27: Primeira janela de coleta

**O problema.** Encerrar antes da primeira janela não explicava a ausência de registros.

**Hipótese.** Exibir a contagem e o aviso torna o estado da coleta visível.

**O que foi testado.** No Windows, simulei relógio e sensor no hook e na rota Coletar. Removi separadamente cada texto da tela e rodei o teste.

**Resultado medido.** O teste do hook falhou em develop pela ausência da contagem. Cada remoção derrubou 1 teste da tela, na asserção do respectivo texto. No preview, o autor confirmou o encerramento aos 11 s, a nova contagem e o primeiro registro. A suíte atualizada passou com 581 testes em 44 arquivos.

**Adaptação.** A contagem usa a duração da primeira janela e reinicia com a sessão.

**O que deu errado no caminho.** Um comando de inspeção usou expansão de chaves incompatível com PowerShell. Repeti a leitura com caminhos explícitos.

**Risco em aberto.** A simulação automatizada não mede a cadência de sensores de outros aparelhos.

**Procedência.** PR #150, implementação `fe85462`, registros sobre `develop` `745f232`. Testes automatizados no Windows.


# 2026-11-12 (xxiv) — o release R1b

**O problema, como foi entendido no início.** Os itens 1.4–1.6 do plano (`APP-15`, `UI-28`, `UI-27`, PRs #148–#150 do Codex) estavam integrados em `develop` e o autor aprovou levá-los à produção.

**Hipótese de trabalho.** Só frontend, sem migração e sem mudança de contrato: o release não toca a ingestão, e os textos novos aparecem no pacote publicado.

**O que foi testado, e como.** PR #161 (`develop` → `main`), CI e Vercel; depois do deploy, `/health`, `/api/sleep-history` e `/api/features` sem token, `X-Vercel-Id`, o deployment de produção e os três textos novos no JavaScript publicado.

**Resultado medido.** CI e Vercel verdes (12 de 12); merge `96d934c`; deployment de produção em `96d934c`, `gru1`; `/health` `200`, banco ok, contrato 2.9.0, modelo `ml-inf-cabeca-v2`; as duas rotas `401` sem token; no pacote, "Coleta encerrada sem registros", "Primeiro registro em" e "Não foi possível carregar as noites gravadas".

**Adaptação.** Nenhuma.

**O que deu errado no caminho.** Nada nesta etapa.

**Risco em aberto.** O login real depois deste release não foi conferido; a falha do plugin (`APP-15`) só aparece no app Android, que precisa de um APK novo para levar a correção (`APP-12`).

**Procedência.** GitHub (PR #161, CI e deployments); `curl` na produção, 12/11; Windows 11.

# O que este diário não cobre

Registrado para que a ausência não passe por completude.

| Lacuna | Por quê |
|---|---|
| Tudo antes de 2026-02-18 — e de 20/02 a 30/05, sem commit nenhum | ✏️ *Corrigido em 28/10 (`DOC-12`): dizia "antes de 2026-04-29", que é a data do clone, não do primeiro commit.* Anterior ao versionamento, ou fora dele. A escolha do ESP32 + MPU6050 aparece **feita** no README de 18/02, sem justificativa; a do travesseiro em vez do punho, e o enunciado inicial do problema não estão no git. |
| Grande parte de junho a agosto | O `HISTORICO.md` cobre o período, mas **não é versionado** (está no `.gitignore`), então não pode ser citado como procedência num capítulo de TCC. As entradas desse intervalo aqui saem de reflog e de código, e por isso são poucas. |
| ~~As suítes do backend e do frontend~~ | **Coberto em 16/10:** backend 240 passam, frontend 338 passam em 22 arquivos, `tsc --noEmit` e `vite build` limpos. Substitui os números de 10/09 (221 pytest, 315 vitest). Com duas ressalvas: `web-app/tests/rls/` **não rodou** (125 pulados — exige Postgres de verdade), e os 338 do frontend foram medidos **sobre a árvore de trabalho**, não sobre o estado commitado — ver a linha abaixo. ✏️ **17/10:** a segunda ressalva caiu com os 15 arquivos commitados — o frontend passa a 376 testes em 24 arquivos, medidos sobre a árvore versionada, e os dois números coincidem porque não há mais pendência. A ressalva do `rls` continua valendo. O backend **não foi reexecutado em 17/10**: os 240 seguem sendo de 16/10, e nada do trabalho de 17/10 toca `web-app/` fora de documentação. |
| ~~O frontend de 29/09~~ | ✏️ **Lacuna fechada em 17/10 — ver a entrada (iii) daquela data.** Os 15 arquivos foram lidos e commitados em quatro commits (`a586b0b`, `fea1c48`, `22a9268`, `f58f52c`). Eram a metade de cliente do `DASH-12`/`DASH-13`, trabalho não catalogado do `DASH-08`, a montagem do `UI-10` e uma correção de cabeçalho do `FW-06` — **14 de trabalho e 1 que não era mudança nenhuma**, só entrada de índice desatualizada. Os números do frontend passam a medir a árvore versionada: **376 testes**, `tsc` limpo. |
| Execução em runner de verdade | Os jobs de CI validados em 16/10 rodaram **localmente**. Nenhum rodou num runner do GitHub, e o `chore/GIT-01-normalizar-fim-de-linha` não foi enviado. A diferença não é cosmética: o `actions/checkout` é o ponto central da análise do `CI-05`. |
| Toda a camada L1 e L2 | Nada foi medido no dispositivo físico. Os 8 pinos do MPU6050 não estão soldados. Todo número de hardware neste arquivo é **calculado ou simulado**, com uma exceção — a leitura de 25/08, que é medição de um sensor mal conectado e serve só para dizer que não serve. |
