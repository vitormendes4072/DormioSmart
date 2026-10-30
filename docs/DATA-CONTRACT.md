# Contrato de dados — Smart Dormio

**Versão:** 2.7.0 · **Itens:** API-03, DATA-01, DATA-02, SEC-02, SEC-03, DASH-05, DASH-06, DATA-04, APP-01, SEC-06, SEC-07, APP-08, DASH-08, DASH-12, DASH-13, DATA-07a, DATA-07b, DATA-07c

> **2.7.0 (MINOR — nada quebra em campo):** a seção 2.6 deixou de ser só declarada. `f`, `g`
> e `fs` são emitidos pelo firmware, validados na ingestão, gravados (migração 010) e
> devolvidos, com as duas features derivadas no servidor, por `GET /api/features`. Payload
> sem `f` continua sendo o payload correto.
>
> **2.6.0 (MINOR — nada quebra em campo):** rota nova e opcional, `POST /api/data/lote`,
> para entregar várias leituras numa requisição (seção 5.2). O `POST /api/data` não mudou
> uma linha; um firmware que nunca use o lote continua conforme.
>
> **2.5.0 (MINOR — nada quebra em campo):** o payload ganha o **vetor de
> características por época** (`f`), campo **opcional**, e a seção 2.6 fixa a
> ordem canônica das oito, a unidade de cada uma e a representação em ponto
> fixo (DATA-07a).
>
> ⚠️ **Declarado, não implementado — em nenhum dos três lados.** Nenhum
> firmware emite `f`, o backend ainda não o valida nem o persiste, e não há
> coluna para ele. Esta versão existe para que as três implementações sejam
> escritas **contra o mesmo documento** em vez de convergirem por acaso; o
> trabalho de implementar é o `DATA-07b`. Enquanto isso, **o formato sem `f` é
> o formato corrente e continua sendo o único aceito** — nenhum firmware
> precisa ser regravado, hoje ou quando o `f` entrar.
>
> **Por que MINOR e não MAJOR.** Pela regra da seção 7, MAJOR é o que quebra
> firmware em campo — campo removido, renomeado, unidade alterada, header novo
> obrigatório. Aqui nada disso acontece: `f` é campo opcional novo e nenhuma
> obrigatoriedade muda. (A v2.0.0 foi MAJOR porque *a obrigatoriedade* de `t` e
> `gx/gy/gz` mudou, o que não é o caso agora.)

Este documento é a fonte única de verdade sobre o dado que trafega entre
firmware, backend e banco. Firmware (`firmware/sketch.ino`), simulador
(`web-app/fake_sensor.py`) e backend (`web-app/routes.py`) devem sempre
declarar a mesma versão deste contrato. Divergência entre eles é bug.

**Desde a v2.5.0 há um quarto interessado: o pipeline de ML.** A definição das
características (seção 2.6) vive em `ml/src/features.py` e é consumida por duas
implementações independentes — a de Python e a que o firmware terá. Duas
implementações da mesma fórmula divergem, e a divergência é silenciosa: o modelo
treina numa definição de `enmo_media` e roda sobre outra, sem erro em lugar
nenhum. É por isso que a seção 2.6 fixa ordem, unidade e faixa de cada uma, e por
isso que existe um vetor dourado (`ml/testes/vetor_dourado.json`) que os dois
lados devem reproduzir.

---

## 1. Fluxo

```
ESP32 + MPU6050 ──POST /api/data──▶ Flask ──registrar_leitura()──▶ Supabase
                  X-Device-Token            (papel dormio_ingestao)   (sleep_data)
                                                                    │
Celular ────────▶POST /api/data──▶ Flask ──registrar_leitura_       │
                  Authorization             da_sessao()  ───────────┤ RLS
                                            (JWT do usuário)        │
                                                                    │
SPA (frontend) ──GET /api/sleep-history──▶ Flask ──JWT do usuário───┘
                  Authorization: Bearer
```

Três caminhos, credenciais distintas e propositalmente diferentes:

- **Ingestão por token** (ESP32) não tem sessão de usuário, então o RLS não se
  aplica. Desde a v2.4.0 o backend **não usa mais a `service_role`**: usa o
  papel `dormio_ingestao`, que tem `EXECUTE` em três funções e nenhum
  privilégio de tabela. O dono da linha é resolvido **dentro do banco**, a
  partir do token — não existe parâmetro por onde escolhê-lo.
- **Ingestão por sessão** (celular) tem sessão, e desde a v2.4.0 não passa por
  credencial privilegiada nenhuma: grava por função concedida a
  `authenticated`, que deriva o dono de `auth.uid()` e confere a posse do
  dispositivo no banco.
- **Leitura** tem sessão. O backend repassa o JWT do usuário ao Supabase e quem
  filtra é o RLS, não código Python.

---

## 2. Payload de ingestão (device → backend)

`POST /api/data` · `Content-Type: application/json` · `X-Device-Token: <token>`

| Campo | Tipo | Unidade | Origem | Obrigatório |
|---|---|---|---|---|
| `ax` | float | m/s² | `a.acceleration.x` | **sim** |
| `ay` | float | m/s² | `a.acceleration.y` | **sim** |
| `az` | float | m/s² | `a.acceleration.z` | **sim** |
| `total` | float | m/s² | magnitude do vetor de aceleração | **sim** |
| `status` | string | — | rótulo do dispositivo | **sim** |
| `gx` | float | rad/s | `g.gyro.x` | não (v2.0.0) |
| `gy` | float | rad/s | `g.gyro.y` | não (v2.0.0) |
| `gz` | float | rad/s | `g.gyro.z` | não (v2.0.0) |
| `t` | float | °C | `temp.temperature` | não (v2.0.0) |
| `ts` | string | ISO 8601 | relógio do dispositivo | não (v2.0.0) |
| `epoca_s` | int | s | janela agregada | não (v2.0.0) |
| `metodo` | string | — | como a janela foi resumida | se `epoca_s` |
| `amostras` | int | — | amostras no agregado | não |
| `f` | array | — | 6 características intra-época | não (v2.5.0) |
| `g` | array | — | gravidade unitária da época, 3 componentes | se `f` |
| `fs` | float | Hz | taxa de amostragem que produziu `f` | se `f` |

### 2.0 Dois tipos de dispositivo (v2.0.0)

Até a v1.2.0 o único emissor era o ESP32 e todo campo era obrigatório. Com o
celular como segunda fonte (APP-01), três deixaram de fazer sentido universal:

- **`t`** é a temperatura do **chip do MPU6050**. Celular não tem equivalente.
  Enviar número inventado seria mentir no dado.
- **`gx/gy/gz`** dependem de giroscópio, que nem todo aparelho tem — e a web
  devolve `rotationRate` nulo nesse caso. O giroscópio **não entra em nenhum
  critério**: o movimento é decidido só pela magnitude da aceleração.

Ausente é aceito; **presente continua sendo validado com a mesma régua**.

**Faixa do giroscópio ampliada** de ±12 para ±40 rad/s: MPU6050 em ±500 °/s dá
±8,73 rad/s, mas celular vai a ±2000 °/s ≈ ±34,9. *Tradeoff assumido:* com o
teto antigo, um MPU6050 corrompido reportando 30 rad/s era rejeitado como
fisicamente impossível; esse filtro se perde. Aceito porque o giroscópio não
alimenta nenhuma decisão, e porque a alternativa — faixa por tipo de
dispositivo — acoplaria a validação ao cadastro para proteger um campo que
ninguém lê.

### 2.5 Agregação por época (v2.0.0)

O ESP32 envia **uma amostra por evento**: acorda, mede, dorme. Um celular
amostrando a 50 Hz geraria **~180 mil linhas por hora** — precisa resumir uma
janela antes de enviar.

Ambos ausentes (`epoca_s` e `metodo`) = amostra instantânea, o comportamento
do ESP32. Com `epoca_s`, `metodo` passa a ser **obrigatório**: uma leitura que
resume 60 s sem dizer *como* resumiu não é interpretável depois, e o histórico
ficaria ambíguo no dia em que o método mudasse. Mesmo princípio de `status`,
que viaja com o dado em vez de ser recalculado.

| `metodo` | O que `total` significa |
|---|---|
| `pico-da-magnitude` | A maior magnitude \|a\| observada na janela |

**Por que o pico, e não a média.** A média sobre 60 s dilui um giro de 2 s até
ele desaparecer — exatamente o evento que se quer registrar. O pico preserva a
detectabilidade e **mantém as unidades e o limiar existentes**: `total`
continua sendo magnitude em m/s², e `|total − 9,81| > 1,2` continua sendo o
critério, sem exceção para o celular.

**Consequência que fez o método ser escolhido:** o dispositivo envia `ax/ay/az`
**da amostra de pico**, então a checagem de coerência da seção 5.1 continua
valendo sem caso especial.

> ⚠️ **`pico-da-magnitude` é a escolha provisória.** O `CALC-03` formaliza o
> índice de atividade (SMA, ENMO, contagens). O identificador viaja com o dado
> justamente para que trocar de método depois não torne o histórico ambíguo —
> cada linha diz como foi produzida.

**Chaves curtas por decisão de projeto:** economizam bytes na transmissão do
ESP32. O backend traduz para os nomes de coluna (seção 4).

### 2.6 Vetor de características por época (v2.5.0, DATA-07a)

> ✅ **Estado em 2026-10-30 (v2.7.0, `DATA-07b` fechado):** as sete linhas da
> tabela abaixo estão implementadas — emissão em `firmware/nucleo/payload.cpp`,
> validação em `web-app/validacao.py::_validar_features`, persistência na
> migração `010`, derivação em `web-app/features_noite.py`, servida por
> `GET /api/features` (abaixo, "Derivação no servidor"). A nota de 17/10 fica
> como procedência.
>
> ⚠️ **Estado em 2026-10-17 — o cálculo existe nos dois lados; o transporte
> não.** Esta nota dizia "nada implementa esta seção ainda", e isso deixou de
> ser verdade pela metade, então vale a precisão:
>
> | o que | onde | estado |
> |---|---|---|
> | definição das 6 + `ĝ` | `ml/src/features.py` | ✅ |
> | **cálculo no firmware** | `firmware/nucleo/caracteristicas.{h,cpp}`, `filtro.{h,cpp}` | ✅ `DATA-07b` (a)(b) |
> | **paridade Python ↔ C++ provada** | `firmware/nucleo/testes/testes_dourado.cpp` (`make dourado`) | ✅ `DATA-07b` (c) |
> | emissão de `f`/`g`/`fs` no payload | `firmware/nucleo/payload.cpp` | ❌ |
> | validação na ingestão | `web-app/validacao.py` | ❌ |
> | persistência e migração | `web-app/` | ❌ `DATA-07b` (d) |
> | derivação das 2 angulares no servidor | `web-app/` | ❌ `DATA-07b` (e) |
>
> Ou seja: **`f` continua não sendo emitido, não sendo validado e não sendo
> persistido, e um payload sem ele continua sendo o payload correto.** O que
> mudou é que o dispositivo já sabe calcular o vetor, com paridade medida (a
> divergência é só o resíduo de borda do filtro, idêntica à que a referência
> em Python já tinha contra o scipy).
>
> ⚠️ **E há um pré-requisito que não é de software:** o cálculo exige a época
> completa a 32 Hz, e o firmware em campo amostra a cada 10 s — **3 amostras
> por época**. Pela tabela de "Época incompleta não tem paridade" abaixo, isso
> é a faixa de 54 % de divergência. O acumulador **recusa** a época em vez de
> emitir um vetor plausível e errado, então o caminho é inerte até o `FW-06`
> fixar a taxa.

O modelo do `ML-01` não consome magnitude e rótulo: consome um **vetor de
características por época de 30 s**. Enquanto o dispositivo enviar só
`total` e `status`, o dado captado pelo Dormio **não entra no mesmo pipeline**
que produziu todos os resultados do bloco de ML — e a validação em campo
(`VAL-01`, `VAL-02`) não tem como acontecer.

#### O que o dispositivo envia, e o que ele não envia

**O dispositivo envia seis características, não oito.** As outras duas são
derivadas no servidor, e a razão é de dependência, não de economia:

```
f  = [ enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr, p_frac ]   ← do dispositivo
g  = [ gx̂, gŷ, gẑ ]     gravidade unitária da época                     ← do dispositivo
                         ↓
inclinacao_rel = arccos( ĝ_t · ĝ_ref )    ĝ_ref = mediana geométrica da NOITE INTEIRA
d_angulo       = arccos( ĝ_t · ĝ_{t-1} )                                 ← derivadas no servidor
```

`ĝ_ref` é a mediana geométrica dos vetores gravidade da **gravação inteira**
(`direcao_referencia` em `ml/src/features.py`, por Weiszfeld). Um dispositivo
que drena em tempo real **não pode conhecê-la**: quando envia a época 12, as
épocas 13 a 960 ainda não existem. Qualquer estimativa incremental que ele
fizesse seria um **estimador diferente** do de referência — não uma aproximação
com tolerância declarada, mas outra fórmula — e divergiria em silêncio, que é
exatamente o defeito que este contrato existe para prevenir.

Enviando `ĝ`, as duas features saem do **mesmo código** que produziu os
resultados do ML, sobre a noite completa. A reconstrução é exata: ver
`ml/testes/test_redundancia_angular.py`.

> **`d_angulo` não é a diferença de `inclinacao_rel`.** São ângulos numa esfera,
> e entre eles vale a desigualdade triangular esférica
> (`|θ_t − θ_{t−1}| ≤ d_angulo ≤ θ_t + θ_{t−1}`), não uma igualdade. Medido em
> 87 795 épocas: a aproximação erra 0,01 grau na mediana e **149 graus** no pior
> caso, concentrado nas viradas — que é tudo o que a feature existe para
> capturar. O registro está em `docs/DECISAO-BUFFER-E-FEATURES.md`.

#### Ordem canônica — as três implementações seguem esta

A ordem é a de `NOMES_FEATURES` em `ml/src/features.py`, e **trocá-la é mudança
MAJOR** deste contrato: um vetor na ordem errada passa em toda validação de
faixa e produz um modelo errado em silêncio.

| # | Nome | Unidade | Faixa física | O que é |
|---:|---|---|---|---|
| 0 | `enmo_media` | g | 0 a 1 | média de `max(‖a‖ − 1, 0)` na época |
| 1 | `enmo_desvio` | g | 0 a 1 | desvio-padrão do mesmo ENMO |
| 2 | `enmo_max` | g | 0 a 16 | máximo do mesmo ENMO |
| 3 | `mag_din_media` | g | 0 a 2 | média de ‖a − ĝ‖₂, a magnitude dinâmica |
| 4 | `zcr` | — | 0 a 1 | fração de cruzamentos por zero da magnitude sem DC |
| 5 | `p_frac` | — | 0 a 1 | fração de amostras com ‖a − ĝ‖ acima do limiar |

E `g` = `[gx̂, gŷ, gẑ]`, cada componente em **[−1, 1]**, com ‖g‖ = 1 ± 1e−3.

> **`‖g‖ = 1 ± 1e−3` é coerência, não orçamento de paridade.** Ela pergunta
> "este vetor é mesmo unitário?" a **um** lado, e os dois lados a satisfazem
> sozinhos porque os dois normalizam. Ela **não** diz quanto as duas
> implementações podem discordar em *direção* — isso é outro número, medido no
> `DATA-07c`: o resíduo de borda do filtro faz `ĝ` divergir até **0,082 grau**
> entre Python e a referência de firmware, e a tolerância de paridade adotada é
> **0,25 grau**. Confundir as duas coisas leva a conferir `ĝ` com uma régua
> 4× mais fina do que qualquer implementação correta consegue atender.

**Duas armadilhas de unidade, ambas já custaram tempo neste projeto:**

- **`f` está em g, não em m/s².** O resto do payload (`ax`, `ay`, `az`, `total`)
  está em m/s². A mistura é deliberada: o pipeline de ML inteiro opera em g,
  porque é a unidade das bases públicas, e converter no meio do caminho seria
  criar um ponto a mais onde as definições divergem. O backend **não converte**.
- **`enmo_max` admite até 16 g** enquanto as outras do domínio de g ficam em 1 ou
  2. Não é descuido: é um máximo, e o teto físico com fundo de escala de ±8 g é
  de ~12,9 g. O fundo de escala de cada uma está na tabela porque ele define o
  passo do ponto fixo (abaixo).

#### Representação

No **payload JSON**, `f` e `g` são arrays de número decimal — JSON não tem ponto
fixo, e economizar bytes aqui não vale o acoplamento.

No **buffer do firmware**, cada uma ocupa 16 bits de ponto fixo, com o fundo de
escala da tabela acima. Essa escolha **não é livre**: o custo em desempenho foi
medido, não argumentado — Δκ da ordem de 1e−4 nas três bases, contra um ganho de
+0,123 do HMM e um teto humano de 0,612. Descer a 8 bits já custa −0,038 na
posição da cabeça, que é a do Dormio. Reprodução em
`ml/experimentos/quantizacao_features.py`; decisão em
`docs/DECISAO-BUFFER-E-FEATURES.md`.

`zcr` e `p_frac` são frações de uma contagem de amostras (0..959 numa época de
30 s a 32 Hz) e o firmware as guarda **como a contagem inteira** — em `uint16` é
representação exata, não quantização.

#### `fs` é obrigatório quando `f` está presente

A taxa de amostragem que produziu o vetor. Sem ela, `zcr` e `p_frac` não são
interpretáveis (as duas são frações de uma contagem que depende de quantas
amostras a época teve) e o filtro de gravidade não é reproduzível. Mesmo
princípio de `metodo` na seção 2.5: o que descreve **como** o número foi
produzido viaja com o número, senão o histórico fica ambíguo no dia em que a
taxa mudar — e ela vai mudar, porque o `FW-06` ainda não fixou a taxa final.

#### Época incompleta não tem paridade (medido no DATA-07c)

O vetor `f` só é comparável entre as implementações quando a época está
**completa**. Abaixo disso as duas pontas deixam de calcular a mesma coisa, e
não por arredondamento:

| amostras na época | divergência em `mag_din_media` |
|---:|---:|
| 8 | 54 % |
| 10 | 30 % |
| 64 | 3,0 % |
| 300 | 0,82 % |
| 960 (completa) | 0,26 % |

São duas causas somadas. Até 9 amostras, `estimar_gravidade` desiste de filtrar
e devolve a média — um **estimador diferente**, que a referência estilo-firmware
não tem. Acima disso, o filtro simplesmente ainda não assentou.

⚠️ **Consequência para o `DATA-07b`:** o dispositivo **não pode emitir `f` de uma
época truncada** — nem no encerramento da noite, nem quando a drenagem corta o
buffer no meio. Ou ele descarta a época incompleta, ou o payload carrega a
contagem de amostras para o servidor descartar. Enquanto isso não for decidido,
o risco é real e silencioso: uma época curta produz um vetor de características
plausível, dentro de todas as faixas desta seção, e simplesmente errado.

✅ **Decidido em 2026-10-30 (v2.7.0): o dispositivo descarta.** O
`AcumuladorDeFeatures` recusa a época com menos de 960 amostras, e
`montar_payload` só emite `f` para época de nível 0 (30 s) com todos os valores
dentro das faixas. Época degradada (60 s ou mais) também sai **sem** `f`: as
features não fundem (`firmware/nucleo/caracteristicas.h`), e o vetor de uma das
metades descreveria 30 s de uma leitura que resume mais. Vetor fora de faixa
também sai sem `f`, em vez de levar a leitura inteira a um `400`.

A medição está travada em
`ml/testes/test_vetor_dourado.py::test_epoca_incompleta_nao_tem_paridade`.

#### Validação (implementada na v2.7.0, `web-app/validacao.py::_validar_features`)

- `f` presente exige `g` e `fs`; qualquer um dos três sozinho é `400`.
- `f` exige `epoca_s` — um vetor de características de uma amostra instantânea
  não significa nada.
- `f` com comprimento ≠ 6, ou `g` com comprimento ≠ 3 → `400`.
- Cada elemento finito e dentro da faixa da tabela → senão `400`, com a mesma
  régua dos demais campos numéricos.
- `‖g‖` fora de 1 ± 1e−3 → `400`. É a checagem de coerência de `g`, análoga à
  de `total` contra `(ax, ay, az)` na seção 5.1.
- **Ausente continua sendo o caso normal**, e continuará sendo depois que o
  firmware novo existir: dispositivo velho em campo é dispositivo válido.
- `fs` é número em (0, 200] Hz.

#### Persistência (migração 010)

Dez colunas em `sleep_data`, uma por número e **com o nome dele**:
`enmo_media`, `enmo_desvio`, `enmo_max`, `mag_din_media`, `zcr`, `p_frac`,
`g_x`, `g_y`, `g_z` e `fs_features`. Não um array: num array a ordem é
implícita, e uma troca passaria em toda faixa. A ordem de `f` vira nome uma vez,
em `validacao.colunas_de_features`. Uma restrição (`sleep_data_features_tudo_ou_nada`)
exige as dez preenchidas ou as dez nulas.

⚠️ **A 010 entra no banco antes do release do backend da v2.7.0.** Na ordem
inversa, o backend validaria `f` e a função de gravação antiga o descartaria,
respondendo `201`. O `DIAGNOSTICO-migracoes-aplicadas.sql` confere as funções,
não só as colunas.

#### Derivação no servidor: `GET /api/features`

`inclinacao_rel` e `d_angulo` não são gravadas: são derivadas na leitura, sobre
a janela pedida, por `web-app/features_noite.py` — a mesma conta de
`ml/src/features.py::features_inter_epoca`, reescrita em Python puro e conferida
contra `ml/testes/vetor_dourado_sequencias.json` (`g_ref` a 1e-12, ângulos a
1e-6 grau).

```
GET /api/features?device=<uuid>&desde=<ISO 8601 com fuso>&ate=<ISO 8601 com fuso>
Authorization: Bearer <JWT do usuário>
```

- Os três parâmetros são obrigatórios, e a janela vai até **24 h**. A janela
  faz parte do resultado: `inclinacao_rel` é medida contra a postura típica
  **da janela** (`g_ref`, mediana geométrica), e a mesma época tem outro valor
  noutra janela. O que é "a noite" é o `ESC-01`; até lá, quem pede escolhe.
- Entram só as épocas **com vetor e com `captured_at`**. Sem o instante da
  medição não há como ordenar a noite nem reconhecer um buraco.
- **Uma diferença deliberada em relação ao `ml/`:** `d_angulo` é `null` na
  primeira época e em toda época que começa mais de 45 s depois da anterior.
  As bases públicas não têm buracos; o dispositivo tem, e uma hora sem leitura
  apareceria como uma virada enorme "em 30 s". Sem buraco, o resultado é
  idêntico ao do `ml/`.
- Resposta `200`: `{"device_id", "desde", "ate", "ordem_features", "g_ref",
  "lacuna_maxima_s", "epocas": [{"instante", <as oito pelo nome>, "fs"}]}`.
  `400` para parâmetro faltando, sem fuso ou janela acima de 24 h; `401` sem
  JWT; `503` se a consulta falhar — uma lista vazia pareceria noite sem
  movimento.

### 2.1 `total` — o que é e o que NÃO é

```
total = √(ax² + ay² + az²)
```

É a **magnitude bruta do vetor de aceleração, com a gravidade incluída**.
Em repouso vale ≈ 9,81 m/s² — **não vale zero**.

A *intensidade de movimento* exibida no dashboard é derivada disto, não
transmitida pelo device:

```
intensidade = |total − 9,81|
```

Em repouso ≈ 0; durante um evento, cresce. **É sobre a intensidade — não
sobre `total` — que o limiar de movimento é aplicado** (seção 2.2).

### 2.2 `status` — classificação do dispositivo

Valores: `"Repouso"` · `"Movimento"`

**Critério único, simétrico:**

```
intensidade = |total − 9,81|
status = intensidade > 1,2 m/s²  ?  "Movimento"  :  "Repouso"
```

| Constante | Valor | Onde vive |
|---|---|---|
| `GRAVIDADE` | 9,81 m/s² | firmware, simulador, dashboard |
| `LIMIAR_MOVIMENTO` | **1,2 m/s²** — provisório | firmware, simulador |

> O limiar de 1,2 m/s² é **provisório** e será calibrado empiricamente no
> **VIA-01** (teste de bancada com o sensor no travesseiro). O valor preserva a
> sensibilidade do limite superior que já existia (11,0 − 9,81 = 1,19) e estende
> a mesma sensibilidade ao lado de baixo, que antes só disparava a −1,81.

**Quem classifica é o dispositivo.** O dashboard exibe o rótulo recebido e nunca
reclassifica: duas implementações da mesma regra foi exatamente o defeito que
este contrato corrigiu.

#### Histórico — a assimetria corrigida em 1.1.0

Até a v1.0.0 o firmware usava um limiar sobre a magnitude bruta:

```cpp
status = (total > 11.0 || total < 8.0) ? "Movimento Detectado!" : "Dormindo";
```

Isso equivalia a **+1,19 para cima e −1,81 para baixo** em torno de 9,81 —
enquanto o dashboard sempre exibiu desvio absoluto. Consequência visível: um
pico *mais alto* podia ser pintado como repouso ao lado de um pico *mais baixo*
pintado como movimento.

O rótulo `"Dormindo"` também **excedia o escopo do projeto** — o dispositivo não
sabe se alguém dorme, apenas se houve movimento (ver Escopo no `ROADMAP.md`).

**Rótulos legados permanecem no banco.** As linhas gravadas antes desta versão
mantêm `"Dormindo"` / `"Movimento Detectado!"`, e o dashboard os reconhece. Não
reescrevemos medição já coletada para casar com nomenclatura nova: o dado
registrado é o que o dispositivo de fato reportou naquele momento.

### 2.3 `t` — temperatura do chip, não do ambiente

O MPU6050 reporta a temperatura **do próprio circuito integrado**. Não é
temperatura ambiente, não é temperatura corporal e não deve ser apresentada
como qualquer uma das duas (ver Escopo no `ROADMAP.md`).

O `fake_sensor.py` simula esse campo em torno de **32 °C**, coerente com um CI
em operação. Até a v1.0.0 ele simulava 24 °C descrito como "temperatura base do
quarto" — corrigido na v1.1.0.

### 2.4 Timestamp

> **Atualizado na v2.0.0:** o campo `ts` passou a existir, **opcional**. O texto
> abaixo continua descrevendo o caso em que ele é omitido — que é o do ESP32.

O device **não envia timestamp**. O ESP32 não tem RTC com bateria e perde a
hora a cada Deep Sleep; um relógio derivado do NTP a cada acordar gastaria
energia e falharia offline. O `created_at` é gerado pelo **banco** (`default now()`).

*Consequência assumida:* sem `ts`, o timestamp é o do **recebimento**, não o da
captação. Com a rede saudável a diferença é de segundos.

**`ts` (v2.0.0)** existe para os dois casos em que isso deixa de servir: um
celular que agrega por época e envia em lote, e o buffer offline do `HW-05`,
que enviará leitura de horas antes. Vai para a coluna `captured_at`.

`created_at` **continua existindo e continua sendo o do recebimento** — `ts` é
campo novo, não substituição, então nenhuma linha antiga muda de significado.

**Instante no futuro é recusado.** Relógio de celular é ajustável pelo usuário;
uma leitura com data futura envenenaria qualquer janela de consulta e ficaria
pendurada no topo do gráfico para sempre. Tolerância de 5 minutos de
adiantamento, que cobre relógio dessincronizado sem aceitar disparate.
`ts` sem fuso horário é recusado — instante ambíguo não é instante.

---

## 3. Autenticação na ingestão

A partir da **v2.2.0** há **dois caminhos**, um por classe de origem. Em ambos, o
`user_id` **nunca vem do corpo da requisição**.

| Origem | Credencial | De onde sai o dono |
|---|---|---|
| ESP32 | `X-Device-Token: <token>` | da linha do dispositivo, resolvida pelo hash |
| Celular | `Authorization: Bearer <JWT>` + `device_id` no corpo | do JWT validado |

O token tem precedência quando os dois vêm — cenário que só acontece por engano de
cliente, já que um ESP32 nunca envia `Authorization`.

### 3.1 Por que o celular não usa token (APP-08)

O `X-Device-Token` existe porque **o ESP32 não tem login**. Não há usuário na frente
dele, não há sessão, não há como renovar credencial; um segredo longo no `secrets.h` é o
que resta.

O celular não tem esse problema: quem abre a tela de coleta já está autenticado — a mesma
sessão que carrega o painel. Exigir que essa pessoa pareie um dispositivo, copie um token
de 43 caracteres e cole noutra tela era pedir que ela fizesse à mão o que o navegador já
tinha feito.

E era pior que incômodo: colocava uma credencial de **escrita** dentro do navegador, onde
não existe equivalente ao Keystore do Android. O melhor possível ali era `sessionStorage`,
que apenas encurta a janela de exposição.

Com autenticação por sessão, **não há token nenhum no navegador** — não há o que um XSS
exfiltrar.

### 3.2 O que o cliente pode e não pode dizer

No caminho por sessão, o cliente informa **apenas qual dos seus dispositivos** está
enviando. Isso é conferido contra o dono **antes de qualquer escrita**, com filtro por
`user_id` acompanhando o RLS.

`device_id` inexistente, revogado ou **de outra pessoa** respondem igual — `404`.
Distinguir os casos permitiria descobrir ids de dispositivos alheios.

`POST /api/devices/celular` (autenticado) devolve o dispositivo `celular` do usuário,
criando na primeira vez. É *create-or-get*: uma chamada por sessão de coleta criando toda
vez encheria a conta de órfãos. **Nunca devolve token** — a linha tem um `token_hash`
gerado cujo valor em claro é descartado, então o caminho por token simplesmente não é
utilizável nesse registro, que é o desejado.

## 3.3 Autenticação do dispositivo (SEC-02)

Header obrigatório: `X-Device-Token: <token opaco>`

- Gerado pela aplicação ao parear um dispositivo, exibido ao usuário **uma única vez**.
- O banco guarda apenas o **SHA-256** do token (`devices.token_hash`), nunca o valor.
- O backend resolve `token → device → user_id` e carimba a linha.
- Token revogado ou inexistente → `401`.

---

## 4. Mapeamento payload → coluna

| Payload | Coluna `sleep_data` | Tipo |
|---|---|---|
| `ax` | `accel_x` | double precision |
| `ay` | `accel_y` | double precision |
| `az` | `accel_z` | double precision |
| `gx` | `gyro_x` | double precision |
| `gy` | `gyro_y` | double precision |
| `gz` | `gyro_z` | double precision |
| `t` | `temp` | double precision |
| `total` | `movimento_total` | double precision |
| `status` | `status` | text |
| — | `created_at` | timestamptz (`now()`) |
| — | `user_id` | uuid (do token) |
| — | `device_id` | uuid (do token) |

**`f`, `g` e `fs` ainda não têm coluna.** A persistência do vetor faz parte do
`DATA-07b`, junto com a migração e a mudança na função de ingestão (que desde o
`SEC-06` é quem grava — ver seção 1). Registrado aqui para que a ausência seja
uma lacuna declarada e não um esquecimento: hoje um payload com `f` teria o
campo silenciosamente descartado, que é por isso que o backend ainda deve
**recusá-lo** em vez de aceitá-lo pela metade.

---

## 5. Respostas de `POST /api/data`

| Código | Significado |
|---|---|
| `201` | Persistido e confirmado |
| `400` | Payload malformado — campo ausente, tipo errado ou fora de faixa (SEC-03) |
| `401` | `X-Device-Token` ausente, inválido ou revogado |
| `503` | Backend íntegro, mas o banco não persistiu |

`201` só é devolvido se a gravação foi **confirmada** — nunca otimista (FIX-02).

A ordem importa: **autenticação antes de validação**. Um payload inválido sem
token devolve `401`, não `400` — quem não se identifica não recebe diagnóstico
do próprio payload.

### 5.2 `POST /api/data/lote` (v2.6.0, API-03)

Várias leituras numa requisição só. Existe porque, na arquitetura do `ARQ-01` (sono leve +
FIFO), o rádio é **63 %** da corrente média com uma entrega por época, e uma entrega por hora
a reduz de 5,31 para 2,03 mA (`docs/DECISAO-ARQ-01-CADENCIA.md`).

**Autenticação:** a mesma do `/api/data`, nos dois caminhos (seção 3). No caminho por sessão,
o `device_id` vai no envelope, não em cada leitura. E vale a mesma ordem: sem credencial,
`401` antes de qualquer olhar no corpo.

**Envelope:**

```json
{"leituras": [ {<leitura da seção 2>}, {<leitura>}, ... ]}
```

Cada leitura é **exatamente** o corpo do `POST /api/data`, validado pelas mesmas regras (5.1)
e gravado pela mesma função. Uma leitura não pode ser válida num caminho e inválida no outro.

**Teto:** 60 leituras por lote (meia hora de épocas de 30 s). Mais que isso responde `413`, e
nada é gravado: o cliente divide o lote.

**Resposta (`200`):** cada leitura cai em **exatamente uma** de três listas, pelo índice dela
no array enviado:

```json
{"aceitas": [0, 1, 3], "rejeitadas": [{"indice": 2, "erro": "..."}], "pendentes": [4, 5]}
```

| Lista | Significa | O que o dispositivo faz |
|---|---|---|
| `aceitas` | gravadas **e confirmadas** (FIX-02, item a item) | apaga da fila |
| `rejeitadas` | inválidas, com o motivo | descarta: reenviar não adianta |
| `pendentes` | não gravadas: o banco falhou ou o tempo acabou | reenvia no próximo lote |

Quando o banco falha numa leitura, o servidor **para ali**: aquela e todas as seguintes voltam
como pendentes. O mesmo vale quando o trabalho passa de 6 s, para não estourar o limite da
função serverless.

| Código | Significado |
|---|---|
| `200` | Lote processado; ler as três listas |
| `400` | Envelope malformado (`leituras` ausente, não lista, vazia) |
| `401` | Credencial ausente, inválida ou revogada |
| `404` | Caminho por sessão: dispositivo inexistente, revogado ou de outra pessoa |
| `413` | Mais de 60 leituras |
| `503` | **Nada** foi gravado e há pendentes: um `200` vazio pareceria sucesso |

⚠️ **Duplicata, não resolvida:** se a resposta se perder depois da gravação, o dispositivo
reenvia leituras já gravadas. O `/api/data` tem o mesmo risco desde sempre; o lote só o
concentra. Uma chave de idempotência (por exemplo, dispositivo + `ts`) fica para quando o
firmware enviar `ts` (contrato v2.0.0).

### 5.1 Regras de validação (SEC-03)

> **v2.1.0 — os três eixos exatamente zero são recusados (SEC-06).**
>
> Caso real de bancada em 25/08/2026: o MPU6050 passou a devolver **todos os
> registradores zerados**. O delator foi a temperatura — **36,5 °C** é
> exatamente o que a biblioteca produz com o registrador em zero
> (`raw / 340 + 36,53`). Causa típica: alimentação mal encaixada. O chip
> sobrevive do vazamento dos pull-ups do I²C, responde no barramento — então
> `mpu.begin()` **passa** — e não mede.
>
> **Por que isso era perigoso.** Com os eixos zerados, `total` = 0, e o
> dispositivo calcula a intensidade como `|0 − 9,81| = 9,81` — muito acima do
> limiar. Ele classifica como **Movimento** e envia. E o payload passava em
> tudo o mais: zero está dentro da faixa física, a coerência fecha
> (`0 = √(0+0+0)`) e o status é válido. Um fio solto encheria a base de
> eventos de movimento **fabricados** a noite inteira — e num trabalho de
> actigrafia isso não é tela quebrada, é resultado inválido.
>
> **Por que a regra é "os três exatamente zero", e não um piso de magnitude.**
> Em queda livre `|a|` realmente tende a zero, e não cabe ao backend decidir
> que isso nunca acontece. Já os três eixos darem `0,00` ao mesmo tempo não é
> medida: o ruído de um acelerômetro vivo torna isso praticamente impossível.
> É assinatura de registrador morto, não de física.
>
> O firmware já não envia (guarda de magnitude implausível nos dois sketches),
> mas firmware velho continua em campo e a base é o que sobra no fim. Defesa
> em profundidade, como o RLS junto do filtro por dono.

Todos os nove campos são **obrigatórios**. Numéricos precisam ser finitos
(`NaN` e `Infinity` são rejeitados) e booleano não conta como número.

| Campo | Faixa aceita | De onde vem o limite |
|---|---|---|
| `ax`, `ay`, `az` | −100 a 100 m/s² | `MPU6050_RANGE_8_G` = ±78,5 m/s², com margem |
| `gx`, `gy`, `gz` | −12 a 12 rad/s | `MPU6050_RANGE_500_DEG` = ±8,73 rad/s, com margem |
| `t` | −40 a 85 °C | faixa de operação do datasheet do MPU6050 |
| `total` | 0 a 175 m/s² | magnitude nunca é negativa; teto = √3 · 100 |
| `status` | `"Repouso"` ou `"Movimento"` | seção 2.2 |

**Coerência interna:** `total` precisa bater com `√(ax²+ay²+az²)` dentro de
**0,5 m/s²**. O firmware transmite 2 casas decimais, então o desvio esperado é
de centésimos; a folga pega payload montado errado sem punir arredondamento.

> Os rótulos legados (`"Dormindo"`, `"Movimento Detectado!"`) **são rejeitados na
> escrita** — o contrato v1.1.0 os aposentou. Continuam sendo lidos do banco,
> onde já estão gravados (seção 2.2).

---

## 6. Leitura (backend → SPA)

`GET /api/sleep-history` · `Authorization: Bearer <JWT>`

Devolve um array (possivelmente vazio — nunca `500`, FIX-01) das leituras
**do usuário autenticado**, mais recentes primeiro:

```json
[{ "created_at": "2026-08-19T03:14:22.511Z",
   "captured_at": "2026-08-19T03:14:20.000Z",
   "movimento_total": 9.83, "temp": 31.2, "status": "Dormindo",
   "epoca_segundos": 30,
   "device_id": "8f14e45f-ceea-467a-9f3d-a1b2c3d4e5f6" }]
```

`401` sem JWT válido. O isolamento entre usuários é garantido pelo **RLS**, não
por filtro em código.

### 6.0 Os dois instantes (DASH-12, v2.3.0)

`created_at` é **quando a linha chegou** (gerado pelo banco). `captured_at` é
**quando o dispositivo mediu** (declarado por ele, seção 2.4). São coisas
diferentes, e o cliente usa o segundo.

Até a v2.2.0 o `select` trazia só o primeiro, e isso era incoerente com o
próprio painel: ele aceitava a **duração** declarada pelo dispositivo
(`epoca_segundos`) como verdade e ignorava o **instante** declarado pelo mesmo
dispositivo. Na prática, latência de rede aparecia como irregularidade de
cadência — e o buffer offline do `HW-05` chegaria todo empilhado em poucos
segundos de `created_at`, fazendo o painel ver uma "sessão de 2 segundos" com
o resto da noite como lacuna.

**`captured_at` é anulável** — as linhas anteriores a ele não o têm, e
preenchê-las com `created_at` afirmaria um instante que o dispositivo nunca
declarou. O cliente resolve com fallback explícito (`instanteDaLeitura`, em
`frontend/src/types/sleep.ts`).

**A ordenação continua por `created_at`**, que nunca é nulo (`default now()`);
ordenar por coluna anulável deixaria as linhas antigas em posição arbitrária.
Quem reordena pelo instante de medição é o cliente.

### 6.1 Recorte da consulta (DASH-05, DASH-06)

Todos os parâmetros são opcionais. **Sem nenhum deles o comportamento é o
anterior**: as 20 leituras mais recentes de todos os dispositivos do usuário.

| Parâmetro | Tipo | Padrão | Efeito |
|---|---|---|---|
| `device` | uuid | — | Recorta por instrumento |
| `desde` | ISO 8601 | — | Limite inferior de `created_at` |
| `ate` | ISO 8601 | — | Limite superior de `created_at` |
| `limite` | inteiro ≥ 1 | 20 | Máximo de linhas; teto de **2000** |

> **O padrão de 20 é do protocolo, não da tela (DASH-13).** O painel e a
> exportação passam `limite=2000` explicitamente. Enquanto não passavam, toda
> a máquina de cobertura, lacuna e sessão operava sobre as 20 linhas mais
> recentes — dez minutos de celular — enquanto a tela descrevia esse recorte
> como a captação inteira. Uma noite de 8 h em épocas de 60 s dá ~480 linhas;
> em épocas de 30 s, ~960.

**Por que `device` existe.** Até o DASH-05 a consulta filtrava só por dono.
Quem pareasse dois dispositivos recebia os dois **misturados na mesma série e
nas mesmas métricas**, com o limite repartido por ordem de chegada — dois
instrumentos plotados como um. Por isso `device_id` também entrou no retorno:
sem ele o cliente não tem como rotular a origem de cada ponto quando exibe
todos.

**Por que parâmetro inválido responde `400`, e não lista vazia.** A garantia de
"sempre devolve lista, nunca 500" (FIX-01) vale para *falha de infraestrutura*.
Não vale para *erro do cliente*: um uuid digitado errado que respondesse `[]`
mostraria um gráfico vazio e faria o usuário concluir que o dispositivo não
mandou nada. `limite` acima do teto é a exceção — é grampeado, não recusado,
porque pedir demais não é erro.

**`device` do cliente é seguro.** O `user_id` nunca vem da requisição: sai do
JWT validado. A consulta filtra pelos dois e o RLS filtra de novo no banco.
Pedir o dispositivo de outra pessoa devolve vazio porque o dono não casa.

---

## 6.2 Eliminação do dado (SEC-07, v2.4.0)

`DELETE /api/me` · `Authorization: Bearer <jwt>` · corpo obrigatório:

```json
{ "confirmacao": "APAGAR MINHA CONTA" }
```

Elimina **todo** o dado pessoal do titular: leituras, dispositivos e perfil,
mais a linha de `auth.users` quando o privilégio permitir. Irreversível.

| Código | Significado |
|---|---|
| `200` | Executado. Corpo traz o recibo — ver abaixo |
| `400` | `confirmacao` ausente ou diferente da frase exata |
| `401` | Sessão ausente, expirada ou inválida |
| `503` | Nada foi apagado (fonte indisponível) |

Recibo do `200`:

```json
{
  "leituras_apagadas": 812,
  "dispositivos_apagados": 2,
  "perfil_apagado": true,
  "conta_de_acesso_removida": true
}
```

**`conta_de_acesso_removida: false` significa eliminação incompleta.** O dado
de `public` saiu, mas a linha de `auth.users` — que guarda o e-mail — ficou,
porque a tabela pertence ao Supabase e o privilégio de `DELETE` nela não existe
em todo projeto. Nesse caso a resposta traz um campo `aviso` dizendo isso ao
titular, em vez de reportar sucesso limpo. O conserto está no cabeçalho de
`web-app/migrations/006_direito_de_eliminacao.sql`.

**Por que a confirmação por frase.** É a única barreira entre um `DELETE`
disparado por engano — retry automático de cliente HTTP, clique duplo, fetch
repetido por hot reload — e a perda definitiva do histórico. Nenhum desses
digita a frase.

**Por que eliminação e não anonimização.** Dado de acelerometria noturna com
carimbo de tempo não é razoavelmente anonimizável: a série temporal é ela mesma
um identificador quando cruzada com outra fonte. A LGPD só retira de seu alcance
o dado efetivamente **anonimizado** (art. 12) — o pseudonimizado continua sendo
dado pessoal —, então desvincular a linha do
dono não cumpriria o art. 18, VI — e criaria exatamente a linha órfã que o
DATA-03 existe para consertar.

**O que não foi permitido junto.** `sleep_data` ganhou policy de `delete` e
**não** de `update`. Eliminar é direito do titular; reescrever uma medição não
é. Apagar é visível — a linha sai. Editar é invisível, e destruiria o valor
probatório do conjunto.

---

## 7. Versionamento

SemVer. **MAJOR** = quebra o firmware em campo (campo removido/renomeado,
unidade alterada, novo header obrigatório). **MINOR** = campo opcional novo.
**PATCH** = correção de redação.

| Versão | Data | Mudança |
|---|---|---|
| 2.7.0 | 2026-10-30 | **MINOR.** A seção 2.6 implementada (`DATA-07b` (d) e (e)): `f`/`g`/`fs` emitidos pelo firmware (só época de 30 s com vetor dentro das faixas), validados na ingestão, gravados em dez colunas nomeadas (migração 010) e servidos por `GET /api/features`, que deriva `inclinacao_rel` e `d_angulo` sobre a janela pedida, com `d_angulo` nulo depois de buraco. Payload sem `f` não muda |
| 2.6.0 | 2026-10-30 | **MINOR.** `POST /api/data/lote` (seção 5.2, `API-03`): até 60 leituras por requisição, resposta com `aceitas`, `rejeitadas` e `pendentes` por índice. O `POST /api/data` não muda |
| 2.5.1 *(nota de estado, 2026-10-17)* | — | **Não é mudança de contrato: nenhum campo, faixa ou obrigatoriedade mudou, e por isso a versão NÃO foi incrementada** (o backend declara `CONTRATO_DE_DADOS = "2.5.1"` e continua correto). A nota de abertura da seção 2.6 deixou de dizer "nada implementa esta seção": o `DATA-07b` implementou o **cálculo** das 6 features e de `ĝ` no firmware e **provou a paridade** Python↔C++ contra o `vetor_dourado.json` (`make dourado`). O **transporte segue não implementado** — `f` não é emitido, validado nem persistido. Registrado também o pré-requisito de taxa: a 10 s de cadência a época tem 3 amostras, e o firmware recusa emitir |
| 2.5.1 | 2026-09-30 | **PATCH — nenhuma mudança de formato.** A seção 2.6 ganha dois fatos medidos no `DATA-07c`, ambos sobre a seção que ainda não está implementada: **(a)** época incompleta não tem paridade entre as implementações (até 54 % de divergência em `mag_din_media`), então o dispositivo não pode emitir `f` de época truncada — decidir *como* no `DATA-07b`; **(b)** o `‖g‖ = 1 ± 1e−3` é checagem de coerência de um lado, e **não** o orçamento de discordância entre implementações, que é de 0,25 grau. Nenhum campo, faixa ou obrigatoriedade muda |
| 2.5.0 | 2026-09-29 | Payload ganha o vetor de características por época: `f` (6 intra-época), `g` (gravidade unitária) e `fs` (taxa), todos opcionais; seção 2.6 fixa ordem canônica, unidades, faixas e representação em ponto fixo (DATA-07a). **MINOR:** campo opcional novo, nenhuma obrigatoriedade muda, nenhum firmware precisa ser regravado. ⚠️ **Declarado, não implementado** — nenhum dos três lados emite, valida ou persiste `f`; isso é o `DATA-07b` |
| 2.4.0 | 2026-09-27 | Ingestão sai da `service_role` e passa a gravar por função, com o papel `dormio_ingestao` de privilégio mínimo (SEC-06); `DELETE /api/me` expõe o direito de eliminação do titular (SEC-07, LGPD art. 18, VI). **MINOR:** o payload de ingestão é idêntico e nenhum firmware precisa ser regravado |
| 2.3.0 | 2026-09-10 | O `select` de leitura passa a trazer `captured_at` — o instante da **medição**, ao lado de `created_at`, o da **chegada** (DASH-12). **MINOR:** campo novo e anulável na resposta; a ingestão não muda e nenhum firmware precisa ser regravado |
| 2.2.0 | 2026-08-25 | Ingestão aceita autenticação por **sessão** (`Authorization: Bearer` + `device_id`) além do token de dispositivo; rota `POST /api/devices/celular` (APP-08). **MINOR:** caminho novo e opcional, o do ESP32 segue intocado |
| 2.1.0 | 2026-08-25 | Recusa leitura com os três eixos exatamente zero — assinatura de sensor que responde mas não mede (SEC-06). **MINOR:** só rejeita o que já era dado inválido; nenhum dispositivo saudável é afetado |
| 2.0.0 | 2026-08-24 | `t` e `gx/gy/gz` viram opcionais; faixa do giroscópio para ±40 rad/s; campos `ts`, `epoca_s`, `metodo` e `amostras` (DATA-04, APP-01). **MAJOR** pela regra abaixo — nenhum firmware em campo quebra, mas a obrigatoriedade de campo mudou |
| 1.3.0 | 2026-08-23 | Leitura aceita recorte por `device`, janela `desde`/`ate` e `limite`; retorno passa a incluir `device_id` (DASH-05, DASH-06). **Compatível:** ingestão intocada, e a leitura sem parâmetros responde como antes |
| 1.0.0 | 2026-08-19 | Contrato inicial; formaliza payload existente, adiciona `X-Device-Token`, `user_id` e `device_id` (DATA-01/SEC-04) |
| 1.2.0 | 2026-08-19 | Validação de entrada: campos obrigatórios, faixas físicas, coerência de `total`, `status` restrito (SEC-03); autenticação de device implementada (SEC-02) |
| 1.1.0 | 2026-08-19 | Critério de movimento simétrico (`\|total−9,81\| > 1,2`); rótulos `Repouso`/`Movimento`; `t` documentado e simulado como temperatura de chip (DATA-02) |
