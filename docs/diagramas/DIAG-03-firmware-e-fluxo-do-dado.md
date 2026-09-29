# DIAG-03 — Firmware: laço, política de rede e as transformações do dado

> **Item do backlog:** `DIAG-03` ("fluxograma do firmware / máquina de estados"), ampliado
> para cobrir também os pontos em que o dado muda de forma (amostra → época de 30 s →
> features → classificação), que o backlog não pedia explicitamente.
> **Onde entra no TCC:** capítulo de Desenvolvimento, seção de firmware (figuras A e B)
> e seção de tratamento do dado (figura C). A figura C também serve ao capítulo de
> Metodologia, como ponte para os resultados de ML.
> **Estado do código:** verificado em `2026-09-29`. As figuras A e B descrevem
> `firmware/envio-continuo/envio-continuo.ino` sobre `firmware/nucleo/`, que é o que
> roda hoje. `firmware/sketch.ino` **não** é descrito aqui: ele tira uma amostra por
> boot e a reescrita é o item aberto `FW-07`.

Convenções de leitura: ver `DIAG-01`.

---

## A — O laço principal (`envio-continuo.ino`)

A propriedade que o diagrama existe para mostrar: **o bloco 1 não depende do bloco 2**.
Nada na medição espera por rede, por serial ou pelo sensor estar vivo.

```mermaid
flowchart TB
    INI(["setup()"]) --> CFG["Wire.begin(21,22)<br/>tentar_iniciar_sensor() — NAO bloqueia<br/>WiFi.mode(WIFI_STA)<br/>cadencia.iniciar(t0, 10 000 ms)<br/>acumulador.iniciar(30 s)"]
    CFG --> LOOP{{"loop()<br/>agora = relogio.atualizar(millis())"}}

    LOOP --> B1["BLOCO 1 — MEDIR<br/>(sem dependencia externa)"]
    B1 --> S1{"sensor offline e<br/>passaram 5 s?"}
    S1 -->|sim| S2["tentar_iniciar_sensor()"]
    S1 -->|nao| C1
    S2 --> C1{"cadencia.deve_amostrar(agora)?<br/>grade ABSOLUTA: t0 + k*periodo"}
    C1 -->|nao| FECH
    C1 -->|sim| SO{"sensor online?"}
    SO -->|nao| INV["acumulador.amostrar_invalida(agora)"]
    SO -->|sim| LE["mpu.getEvent()<br/>total = raiz(ax^2+ay^2+az^2)"]
    LE --> PL{"magnitude_plausivel(total)?"}
    PL -->|"nao (registrador zerado)"| INV2["amostrar_invalida()<br/>explicar_sensor_mudo()"]
    PL -->|sim| AM["acumulador.amostrar(...)"]
    INV --> FECH
    INV2 --> FECH
    AM --> FECH["acumulador.fechar_ate(agora)<br/>fecha o que venceu, mesmo sem amostra"]
    FECH --> GUA["ao_fechar_epoca() -> buffer.guardar(epoca)"]
    GUA --> CHE{"buffer cheio?"}
    CHE -->|sim| DEG["degradar(): funde pares adjacentes<br/>das epocas MAIS ANTIGAS<br/>nivel n -> 30 * 2^n s, teto 1920 s"]
    CHE -->|nao| B2
    DEG --> TET{"ja no nivel 6?"}
    TET -->|sim| DESC["descartes++ — epoca perdida e CONTADA"]
    TET -->|nao| B2
    DESC --> B2

    B2["BLOCO 2 — REDE<br/>(nao alcanca o bloco 1)"]
    B2 --> RD["cuidar_da_rede(agora) — ver figura B"]
    RD --> RL["cuidar_do_relogio(agora)<br/>NTP; sem hora valida a epoca sai SEM ts"]
    RL --> DR{"conectado e buffer nao vazio<br/>e ms_ate_o_proximo >= 4000?"}
    DR -->|nao| CED
    DR -->|sim| POST["drenar(): ate 3 POSTs por volta<br/>montar_payload() -> POST /api/data"]
    POST --> RESP{"codigo HTTP"}
    RESP -->|"201 entregue"| OK["confirmar_entrega()"]
    RESP -->|"400 recusa deterministica"| OK
    RESP -->|"401 / 503 / outro"| FICA["epoca CONTINUA no buffer<br/>encerra a rajada"]
    OK --> DR
    FICA --> CED
    CED["relatar() a cada 60 s<br/>delay(min(ms_ate_o_proximo, 20))"]
    CED --> LOOP
```

**Onde a época vazia entra.** Uma época sem nenhuma amostra sai marcada `EPOCA_VAZIA` e
**ocupa lugar no buffer** — custa 32 bytes dizer "aqui não houve medida". Ela não é
enviada (`ax/ay/az` são obrigatórios e inventá-los seria fabricar medida): `drenar()`
chama `confirmar_entrega()` e conta em `lacunas_puladas`. No banco a lacuna aparece como
o intervalo entre dois `ts`, que é o que ela é.

---

## B — A política de reconexão (`firmware/nucleo/reconexao.h`)

Esta é a máquina de estados propriamente dita. Ela responde a uma pergunta só — "já posso
tentar?" — e **nunca espera**: a espera vira consulta a relógio.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Conectado
    Conectado --> Fora : registrar_queda()<br/>tentativas = 0
    Fora --> Tentando : deve_tentar(agora)<br/>WiFi.begin()
    Tentando --> Conectado : WL_CONNECTED<br/>registrar_sucesso()
    Tentando --> Fora : estourou orcamento_ms = 8 000<br/>registrar_falha()<br/>espera = min(base*2^n, teto) + jitter
    Conectado --> Conectado : drenar() em rajada de ate 3

    note right of Fora
        base 2 s · teto 2 min · jitter 1,5 s
        Teto existe para o aparelho
        PERCEBER a rede voltando.
        Jitter e deterministico (sem rand()).
        A amostragem continua em todos
        os estados; o dado vai ao buffer.
    end note
```

---

## C — Onde o dado muda de forma

Cada seta é uma transformação. O texto do TCC deve poder apontar para o arquivo que a
executa — por isso os nomes estão no diagrama.

```mermaid
flowchart TB
    A["AMOSTRA INSTANTANEA<br/>ax, ay, az em m/s2, gx/gy/gz, temp<br/>MPU6050 a 0,1 Hz hoje (10 s)<br/>FW-05 pede >= 42 Hz"]
    B["EPOCA DE 30 s — 32 bytes<br/>firmware/nucleo/epoca.h<br/>metodo: pico-da-magnitude<br/>guarda ax/ay/az DA AMOSTRA DE PICO<br/>flags: INCOMPLETA · VAZIA · DEGRADADA<br/>COM_AMOSTRA_INVALIDA"]
    C["ROTULO status<br/>firmware/nucleo/payload.h<br/>|total - 9,81| > 1,2 m/s2 -> movimento<br/>LIMIAR PROVISORIO — recalibrar em CAL-01/VIA-01"]
    D["PAYLOAD JSON v2.4.0<br/>firmware/nucleo/payload.cpp<br/>ax ay az total status<br/>+ ts epoca_s metodo amostras"]
    E["LINHA EM public.sleep_data<br/>web-app/routes.py traduz as chaves<br/>curtas para os nomes de coluna<br/>captured_at = medicao<br/>created_at = recebimento"]
    F["SERIE DO PAINEL<br/>frontend/src/lib/metricas.ts<br/>lib/cobertura.ts: sessoes, lacunas,<br/>cadencia mediana, fracao em movimento"]
    G["EXPORTACAO CSV<br/>frontend/src/lib/exportar.ts"]

    A -->|"acumula por pico na grade absoluta"| B
    B -->|"classificar(intensidade)"| C
    C --> D
    B --> D
    D -->|"POST /api/data"| E
    E -->|"GET /api/sleep-history (RLS)"| F
    F --> G

    H["VETOR DE 8 FEATURES POR EPOCA<br/>ml/src/features.py<br/>enmo_media · enmo_desvio · enmo_max<br/>mag_din_media · zcr · p_frac<br/>inclinacao_rel · d_angulo"]
    I["CLASSIFICACAO SONO/VIGILIA<br/>ml/src/modelos.py<br/>configuracao de base: regressao logistica<br/>com class_weight=balanced e contexto +/-2<br/>(ml/config.yaml, contexto_epocas: 2)<br/>modificacoes medidas em Y.5: contexto +/-11, HMM"]

    J["SINAL BRUTO DE DATASET PUBLICO<br/>Wearanize+ OA · Newcastle 2015<br/>ml/src/carregar/"]
    J -->|"reamostragem para 32 Hz com<br/>anti-aliasing a 12,8 Hz — ml/src/sinal.py"| K["EPOCAS DE 30 s<br/>ml/src/epocas.py · empilhar_contexto()"]
    K --> H --> I

    L["(FUTURO) DATA-07: as 8 features<br/>viajam no contrato, nao so o veredito"]
    M["(FUTURO) ML-INF: o modelo classifica<br/>o dado do Dormio"]
    B -.-> L -.-> H
    E -.-> M
    I -.-> M

    classDef futuro stroke-dasharray: 6 4;
    class L,M futuro;
```

## O ponto que este diagrama existe para deixar claro

Há **duas cadeias de transformação distintas**, e hoje elas não se tocam:

- A cadeia do **produto** vai de amostra a época a rótulo por **limiar fixo**
  (`|total − 9,81| > 1,2`), e termina no painel. Não há modelo nela.
- A cadeia da **pesquisa** vai de sinal de dataset público a época a **8 features** a
  classificador, e termina em JSON de experimento. Não há dado do Dormio nela.

As duas setas tracejadas (`DATA-07`, `ML-INF`) são exatamente o que falta para juntá-las,
e estão abertas no backlog. Afirmar na banca que "o Dormio usa aprendizado de máquina para
classificar sono" seria falso hoje; o que é verdade é que o pipeline de ML mediu o custo da
decisão de posicionamento do sensor que o Dormio adota.
