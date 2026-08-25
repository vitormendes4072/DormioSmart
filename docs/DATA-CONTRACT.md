# Contrato de dados — Smart Dormio

**Versão:** 2.2.0 · **Itens:** DATA-01, DATA-02, SEC-02, SEC-03, DASH-05, DASH-06, DATA-04, APP-01, APP-08

Este documento é a fonte única de verdade sobre o dado que trafega entre
firmware, backend e banco. Firmware (`firmware/sketch.ino`), simulador
(`web-app/fake_sensor.py`) e backend (`web-app/routes.py`) devem sempre
declarar a mesma versão deste contrato. Divergência entre eles é bug.

---

## 1. Fluxo

```
ESP32 + MPU6050 ──POST /api/data──▶ Flask ──service_role──▶ Supabase (sleep_data)
                  X-Device-Token                                    │
                                                                    │ RLS
SPA (frontend) ──GET /api/sleep-history──▶ Flask ──JWT do usuário───┘
                  Authorization: Bearer
```

Dois caminhos, credenciais distintas e propositalmente diferentes:

- **Ingestão** não tem sessão de usuário, então o RLS não se aplica. O backend
  usa `service_role` e autentica o **dispositivo** por token.
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

### 5.1 Regras de validação (SEC-03)

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
   "movimento_total": 9.83, "temp": 31.2, "status": "Dormindo",
   "device_id": "8f14e45f-ceea-467a-9f3d-a1b2c3d4e5f6" }]
```

`401` sem JWT válido. O isolamento entre usuários é garantido pelo **RLS**, não
por filtro em código.

### 6.1 Recorte da consulta (DASH-05, DASH-06)

Todos os parâmetros são opcionais. **Sem nenhum deles o comportamento é o
anterior**: as 20 leituras mais recentes de todos os dispositivos do usuário.

| Parâmetro | Tipo | Padrão | Efeito |
|---|---|---|---|
| `device` | uuid | — | Recorta por instrumento |
| `desde` | ISO 8601 | — | Limite inferior de `created_at` |
| `ate` | ISO 8601 | — | Limite superior de `created_at` |
| `limite` | inteiro ≥ 1 | 20 | Máximo de linhas; teto de **2000** |

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

## 7. Versionamento

SemVer. **MAJOR** = quebra o firmware em campo (campo removido/renomeado,
unidade alterada, novo header obrigatório). **MINOR** = campo opcional novo.
**PATCH** = correção de redação.

| Versão | Data | Mudança |
|---|---|---|
| 2.2.0 | 2026-08-25 | Ingestão aceita autenticação por **sessão** (`Authorization: Bearer` + `device_id`) além do token de dispositivo; rota `POST /api/devices/celular` (APP-08). **MINOR:** caminho novo e opcional, o do ESP32 segue intocado |
| 2.0.0 | 2026-08-24 | `t` e `gx/gy/gz` viram opcionais; faixa do giroscópio para ±40 rad/s; campos `ts`, `epoca_s`, `metodo` e `amostras` (DATA-04, APP-01). **MAJOR** pela regra abaixo — nenhum firmware em campo quebra, mas a obrigatoriedade de campo mudou |
| 1.3.0 | 2026-08-23 | Leitura aceita recorte por `device`, janela `desde`/`ate` e `limite`; retorno passa a incluir `device_id` (DASH-05, DASH-06). **Compatível:** ingestão intocada, e a leitura sem parâmetros responde como antes |
| 1.0.0 | 2026-08-19 | Contrato inicial; formaliza payload existente, adiciona `X-Device-Token`, `user_id` e `device_id` (DATA-01/SEC-04) |
| 1.2.0 | 2026-08-19 | Validação de entrada: campos obrigatórios, faixas físicas, coerência de `total`, `status` restrito (SEC-03); autenticação de device implementada (SEC-02) |
| 1.1.0 | 2026-08-19 | Critério de movimento simétrico (`\|total−9,81\| > 1,2`); rótulos `Repouso`/`Movimento`; `t` documentado e simulado como temperatura de chip (DATA-02) |
