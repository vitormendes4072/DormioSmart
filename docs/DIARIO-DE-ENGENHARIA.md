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
