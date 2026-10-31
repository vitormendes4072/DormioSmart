# DIAG-03 — Firmware: as duas tarefas, a política de rede e as transformações do dado

> **Item do backlog:** `DIAG-03` ("fluxograma do firmware / máquina de estados"), ampliado
> para cobrir também os pontos em que o dado muda de forma (amostra → grade → época de 30 s →
> features → classificação), que o backlog não pedia explicitamente.
> **Onde entra no TCC:** capítulo de Desenvolvimento, seção de firmware (figuras A e B)
> e seção de tratamento do dado (figura C). A figura C também serve ao capítulo de
> Metodologia, como ponte para os resultados de ML.
> **Estado do código:** ✏️ **reescrito em `2026-10-31`** para a arquitetura C2 (`ARQ-01`,
> `FW-07`, `FW-08`). Até 30/10 as figuras A e B descreviam o `envio-continuo.ino`, porque o
> `sketch.ino` de produto tirava uma amostra por boot; desde 31/10 o `sketch.ino` é o da C2, e é
> ele que as figuras descrevem. Os identificadores das três figuras foram conferidos contra o
> código em 31/10 por script, com controle positivo.
> ⚠️ **Nada do `sketch.ino` rodou na placa.** Ele compila e liga com o núcleo no host
> (`make sintaxe`); o núcleo que ele usa é testado no host. A figura A descreve o código, não um
> comportamento medido (`FW-07` (c)).
> O `envio-continuo.ino` continua no repositório como instrumento de bancada e sketch do Wokwi;
> o laço dele, que estas figuras mostravam até 30/10, está no histórico do git.

Convenções de leitura: ver `DIAG-01`.

---

## A — As duas tarefas do `sketch.ino` (C2)

A propriedade que o diagrama existe para mostrar: **a medição nunca espera pela rede**. Ela
roda no núcleo 1 e esvazia a FIFO do sensor no mesmo ritmo com o Wi-Fi ligado ou desligado; o
envio roda no núcleo 0 e só é acordado por ela.

```mermaid
flowchart TB
    INI(["setup()"]) --> CFG["midia.abrir() + fila.montar()<br/>sem a particao dormio: mede e NAO guarda<br/>Wire.begin(21, 22) · configurar_mpu()<br/>50 Hz · DLPF 21 Hz · +/-8 g · FIFO so do acelerometro<br/>cadeia.iniciar(origem_us)"]
    CFG --> TM & TE

    subgraph MED["MEDICAO · nucleo 1"]
        direction TB
        TM["intervalo_de_drenagem_us()<br/>~1,7 s com variacao de [0, 20 ms)"]
        TM --> W{"wifi_ativo?"}
        W -->|nao| SL["esp_light_sleep_start()<br/>sono leve: RAM e I2C sobrevivem"]
        W -->|sim| VD["vTaskDelay()<br/>acordada, no MESMO ritmo"]
        SL --> DR
        VD --> DR
        DR["drenar(): INT_STATUS + FIFO_COUNT, depois os bytes<br/>em blocos de 120 B · avaliar_fifo()"]
        DR --> OV{"transbordou ou<br/>leitura falhou?"}
        OV -->|sim| RS["resetar_fifo()<br/>registrar_drenagem(t, 0, 0, true)"]
        OV -->|nao| RG["registrar_drenagem(t, amostras, n, false)"]
        RS --> FE
        RG --> FE
        FE["fechar_epocas(): cadeia.proxima_epoca()"]
        FE --> PR{"EPOCA_PRONTA?"}
        PR -->|"recusada (transbordo, taxa, poucas drenagens)"| REC["NAO grava · conta no log<br/>no servidor vira lacuna entre dois ts"]
        PR -->|sim| FT["acumulador: 6 features + g sobre os 960 pontos<br/>quantizar() · epoca_da_grade()<br/>instante_para_gravar()"]
        FT --> GU["fila.guardar() sob mutex<br/>registro de 64 B na flash"]
        REC --> HE
        GU --> HE{"passaram 10 min<br/>e o Wi-Fi esta desligado?"}
        HE -->|sim| NT["xTaskNotifyGive(tarefa_envio)"]
        HE -->|nao| TM
        NT --> TM
    end

    subgraph ENV["ENVIO · nucleo 0"]
        direction TB
        TE["ulTaskNotifyTake(): dorme ate a medicao avisar"]
        TE --> PD{"fila ok e<br/>reconexao.deve_tentar()?"}
        PD -->|nao| TE
        PD -->|sim| WON["wifi_ativo = true<br/>conectar_wifi(): ate 20 s"]
        WON --> NTP["sincronizar_relogio(): NTP ate 5 s<br/>parede.sincronizar() sob mutex"]
        NTP --> PL["preparar_lote(): ate 60, prefixo contiguo da fila<br/>registro sem payload possivel sai da frente"]
        PL --> PO["POST /api/data/lote<br/>X-Device-Token"]
        PO --> AP["aplicar_resposta(): confirma na fila<br/>so o prefixo que o servidor aceitou"]
        AP --> MAIS{"mais pendentes, sem recuo,<br/>e menos de 20 lotes?"}
        MAIS -->|sim| PL
        MAIS -->|nao| OFF["desligar_wifi()<br/>wifi_ativo = false<br/>registrar_sucesso / registrar_falha"]
        OFF --> TE
    end

```

**Por que a medição não dorme com o Wi-Fi ligado.** O sono leve desliga o rádio e derrubaria a
conexão no meio do envio. A FIFO do MPU guarda 3,4 s e é esvaziada a cada 1,7 s; um POST por
HTTPS leva de 1 a 3 s. Por isso a medição espera **acordada** enquanto o envio está no ar, e é
o fato de ela estar em outro núcleo que impede a FIFO de transbordar. Nada disso foi medido: é
o desenho, e a sessão de bancada (`FW-07` (c)) é que diz se ele se sustenta.

**Onde a época recusada entra.** Uma época que a cadeia recusa (FIFO transbordada, taxa medida
fora de ±20 %, drenagens de menos) **não é gravada**. No banco ela aparece como o intervalo entre
dois `ts`, que é o que ela é. Diferente do `envio-continuo`, onde a lacuna ocupa um registro
vazio no buffer: na flash o tempo de cada registro é gravado com ele, e a lacuna não precisa de
marcador.

---

## B — A política de reconexão (`firmware/nucleo/reconexao.h`)

A máquina de estados responde a uma pergunta só — "já posso tentar?" — e **nunca espera**: a
espera vira consulta a relógio. No `sketch.ino` ela é consultada a cada aviso da medição (de 10
em 10 min); uma volta de envio que termina bem libera a próxima de imediato, e uma que falha
afasta a próxima pelo recuo exponencial.

```mermaid
stateDiagram-v2
    direction LR
    [*] --> Livre : iniciar(agora)
    Livre --> Enviando : aviso da medicao<br/>e deve_tentar(agora)
    Enviando --> Livre : volta ok<br/>registrar_sucesso() + registrar_queda()<br/>proxima tentativa no proximo aviso
    Enviando --> Recuando : Wi-Fi nao subiu, 401/503,<br/>ou pendentes no lote<br/>registrar_falha()
    Recuando --> Enviando : aviso da medicao<br/>e espera vencida
    Recuando --> Recuando : aviso antes da espera vencer<br/>(nada acontece)

    note right of Recuando
        espera = min(base * 2^n, teto) + jitter
        base 2 s · teto 2 min · jitter 1,5 s
        Jitter deterministico (sem rand()).
        A medicao continua em todos os
        estados; o dado vai para a flash.
    end note
```

---

## C — Onde o dado muda de forma

Cada seta é uma transformação. O texto do TCC deve poder apontar para o arquivo que a
executa — por isso os nomes estão no diagrama.

```mermaid
flowchart TB
    A["(NAO EXERCITADO) AMOSTRA NA FIFO DO MPU6050<br/>ax, ay, az em int16 · 4096 LSB/g<br/>50 Hz nominais, oscilador interno -15/+10 %<br/>firmware/nucleo/fifo_mpu.h"]
    B["(NAO EXERCITADO) GRADE DE 32 Hz — 960 pontos por epoca<br/>firmware/nucleo/cadeia_c2.h · reamostragem.h<br/>taxa MEDIDA por regressao contagem x instante<br/>anti-aliasing de 12,8 Hz, ida e volta"]
    FT["(NAO EXERCITADO) 6 FEATURES + g POR EPOCA<br/>firmware/nucleo/caracteristicas.h<br/>enmo_media · enmo_desvio · enmo_max<br/>mag_din_media · zcr · p_frac<br/>quantizadas em 16 bits (18 B)"]
    EP["(NAO EXERCITADO) EPOCA DE 30 s<br/>firmware/nucleo/epoca_c2.h<br/>pico da magnitude DA GRADE, em m/s2<br/>temperatura lida ao fechar"]
    RG["(NAO EXERCITADO) REGISTRO DE 64 B NA FLASH<br/>firmware/nucleo/fila_flash.h · registro_flash.h<br/>epoca + vetor + seq + instante + CRC<br/>particao dormio: 11,4 dias sem rede"]
    D["PAYLOAD JSON — contrato 2.7.0<br/>firmware/nucleo/payload.cpp<br/>ax ay az total status ts epoca_s metodo amostras<br/>+ f (6) · g (3) · fs, so em epoca de 30 s<br/>com todos os valores na faixa do contrato"]
    E["LINHA EM public.sleep_data<br/>web-app/validacao.py valida f, g, fs<br/>migracao 010: dez colunas nomeadas,<br/>tudo-ou-nada · captured_at = medicao"]
    N["AS 8 FEATURES DA NOITE<br/>web-app/features_noite.py · GET /api/features<br/>inclinacao_rel e d_angulo derivadas no servidor<br/>sobre a janela pedida (ate 24 h)"]
    F["SERIE DO PAINEL<br/>frontend/src/lib/metricas.ts<br/>lib/cobertura.ts: sessoes, lacunas,<br/>cadencia mediana, fracao em movimento"]
    G["EXPORTACAO CSV<br/>frontend/src/lib/exportar.ts"]

    A -->|"drenagem a cada ~1,7 s"| B
    B --> FT
    B --> EP
    FT --> RG
    EP --> RG
    RG -->|"montar_payload_do_registro()<br/>POST /api/data/lote"| D
    D --> E
    E -->|"GET /api/sleep-history (RLS)"| F
    F --> G
    E -->|"RLS, pelo JWT do usuario"| N

    H["VETOR DE 8 FEATURES POR EPOCA<br/>ml/src/features.py<br/>mesmas definicoes; paridade C++ x Python<br/>medida contra os vetores dourados"]
    I["CLASSIFICACAO SONO/VIGILIA<br/>ml/src/modelos.py<br/>configuracao de base: regressao logistica<br/>com class_weight=balanced e contexto +/-2<br/>(ml/config.yaml, contexto_epocas: 2)<br/>modificacoes medidas em Y.5: contexto +/-11, HMM"]

    J["SINAL BRUTO DE DATASET PUBLICO<br/>Wearanize+ OA · Newcastle 2015<br/>ml/src/carregar/"]
    J -->|"reamostragem para 32 Hz com<br/>anti-aliasing a 12,8 Hz — ml/src/sinal.py"| K["EPOCAS DE 30 s<br/>ml/src/epocas.py · empilhar_contexto()"]
    K --> H --> I

    M["(FUTURO) ML-INF: o modelo classifica<br/>a noite do Dormio"]
    N -.-> M
    I -.-> M

    classDef futuro stroke-dasharray: 6 4;
    class M futuro;
```

## O ponto que este diagrama existe para deixar claro

Até 30/10 havia **duas cadeias de transformação que não se tocavam**: a do produto ia de amostra
a rótulo por limiar fixo, e a da pesquisa ia de dataset público a 8 features e classificador.
✏️ **Desde 31/10 as duas se encontram no código:** o dispositivo calcula as mesmas 6 features
que o `ml/`, com paridade medida contra os vetores dourados; o servidor as grava e deriva as
outras duas sobre a noite (`GET /api/features`), na mesma ordem que o modelo consome.

O que **não** mudou, e precisa estar dito no mesmo parágrafo:

- **Nenhuma época real percorreu a cadeia.** Tudo o que está marcado `(NÃO EXERCITADO)` roda no
  host, testado, e nunca na placa: o MPU6050 ainda não foi soldado (Etapa 0).
- **O classificador continua fora do produto.** O rótulo `status` que chega ao banco é limiar
  fixo (`|total − 9,81| > 1,2 m/s²`, `firmware/nucleo/payload.h`). A seta para o `ML-INF` é
  projeto.

Afirmar na banca que "o Dormio usa aprendizado de máquina para classificar sono" seria falso
hoje. O que é verdade é que o dispositivo produz, por construção, o vetor que o modelo consome,
e que o pipeline de ML mediu o custo da decisão de posicionamento do sensor que o Dormio adota.
