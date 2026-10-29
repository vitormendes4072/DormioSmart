# DIAG-05 — Pipeline experimental de aprendizado de máquina

> **Item do backlog:** nenhum — este diagrama **nasce aqui**. O backlog foi levantado em
> `2026-09-10` e revisado em `22/09`, antes de o bloco de ML fechar (`ML-05` fechou em
> `28/09`), e por isso não previa uma figura para ele. O item `DIAG-02` do backlog
> (esquemático do circuito) continua aberto e **não** foi absorvido aqui — ver
> `README.md` desta pasta.
> **Onde entra no TCC:** capítulo de Metodologia, seção de procedimento experimental.
> É a figura que o leitor precisa ter à vista ao ler o capítulo de Resultados
> (`docs/RESULTADOS-TCC.md`, seções Y.2 a Y.7).
> **Estado do código:** verificado em `2026-09-29` contra `ml/src/`, `ml/experimentos/`
> e `ml/config.yaml` (`contexto_epocas: 2`, `epoca_s: 30`, `taxa_comum_hz: 32`,
> `seed: 20260910`, `validacao.estrategia: leave_one_subject_out`).

Convenções de leitura: ver `DIAG-01`.

---

## A — Do sinal bruto ao resultado

```mermaid
flowchart TB
    subgraph FONTES["FONTES DE DADO"]
        W["Wearanize+ OA · DOI 10.34973/xrmf-5726 · CC-BY-4.0<br/>100 sujeitos · ~46 GB · PSG pontuada<br/>3 posicoes: cabeca (ZMax, 256 Hz/12 bits),<br/>pulso (Empatica E4, 32 Hz/8 bits), coxa"]
        N["Newcastle 2015 · 55 .bin + 28 PSG<br/>GENEActiv de punho a 85,70 Hz<br/>OUTRO fabricante, centro e equipe de pontuacao"]
        S["sintetico — so exercita o pipeline<br/>ml/src/carregar/sintetico.py<br/>NAO e achado (ml/README.md)"]
        WA["(FUTURO) Walch et al. 2019 — ML-06a/06b<br/>segunda coorte externa<br/>nao alcancavel do ambiente de execucao"]
    end

    CAR["INTERFACE UNICA DE CARREGAMENTO<br/>ml/src/carregar/__init__.py<br/>carregar('wearanize', posicao=, qualidade=, sujeitos=, pontuador=)"]
    W --> CAR
    N --> CAR
    S --> CAR
    WA -.-> CAR

    CAR --> SIN["ml/src/sinal.py<br/>reamostragem para 32 Hz<br/>passa-baixa anti-aliasing a 12,8 Hz<br/>(0,8 x Nyquist)"]
    SIN --> EP["ml/src/epocas.py<br/>fatiar_epocas() — 30 s fixos,<br/>a resolucao dos rotulos de PSG<br/>em TODAS as bases"]
    EP --> FE["ml/src/features.py — 8 features<br/>enmo_media · enmo_desvio · enmo_max<br/>mag_din_media · zcr · p_frac<br/>inclinacao_rel · d_angulo<br/>invariantes a rotacao"]
    FE --> CTX["empilhar_contexto(n_vizinhas)<br/>base: +/-2 epocas (config.yaml)"]

    CTX --> MOD["ml/src/modelos.py<br/>regressao_logistica: StandardScaler +<br/>LogisticRegression(class_weight='balanced')<br/>class_weight NAO e detalhe: sem ele,<br/>com ~87% de sono, a especificidade morre"]

    MOD --> AV["ml/src/avaliar.py<br/>split_por_sujeito() = leave-one-subject-out<br/>metrica agregada POR SUJEITO, nunca pooled<br/>IC 95% por bootstrap percentil (2000 reamostras)"]

    AV --> OUT["ml/experimentos/saida/*.json<br/>cada resultado carrega o hash do config<br/>ml/experimentos/_retomada.py:<br/>LOSO com checkpoint por dobra"]

    classDef futuro stroke-dasharray: 6 4;
    class WA futuro;
```

**A regra de validação que o diagrama codifica.** O agrupamento é sempre o **participante**.
Épocas da mesma noite são altamente correlacionadas; embaralhar por época infla a acurácia
de forma espetacular e falsa. Onde há registro bilateral, os dois punhos do mesmo
participante ficam sempre do mesmo lado da partição.

---

## B — Os três braços e a matriz de transferência (`ML-03`)

Os braços existem para separar duas variáveis que, com as duas posições originais, ficariam
confundidas: a **posição** do sensor e a **qualidade da grade de aquisição**.

```mermaid
flowchart LR
    ORIG["Wearanize+ · 92 sujeitos com<br/>cabeca E pulso simultaneos<br/>prevalencia de sono 0,895"]

    ORIG --> A1["BRACO 1 — cabeca<br/>('cabeca', 'original')<br/>256 Hz · 12 bits"]
    ORIG --> A2["BRACO 2 — cabeca degradada<br/>('cabeca', 'e4')<br/>MESMO sinal a 32 Hz · 8 bits<br/>degradar_para_e4()"]
    ORIG --> A3["BRACO 3 — pulso<br/>('pulso', 'original')<br/>32 Hz · 8 bits"]

    A1 -->|"1 vs 2: isola o custo da QUALIDADE<br/>posicao constante"| CQ["custo da qualidade<br/>kappa 0,398 -> 0,327 = 0,071"]
    A2 --> CQ
    A3 -->|"3 vs 2: isola o custo da POSICAO<br/>qualidade constante"| CP["custo da posicao<br/>kappa 0,377 -> 0,327 = 0,050"]
    A2 --> CP

    A1 --> MAT["MATRIZ 3x3 · 92 dobras COMPARTILHADAS<br/>em cada dobra: 1 sujeito fora,<br/>1 modelo por braco treinado nos 91,<br/>cada modelo avaliado nos 3 bracos do excluido.<br/>So varia quem treinou e quem testou."]
    A2 --> MAT
    A3 --> MAT

    MAT --> ASS["O RESULTADO ORIGINAL — assimetria<br/>treinar no pulso transfere: 0,377 / 0,376 / 0,378<br/>treinar na cabeca COLAPSA: 0,398 -> 0,067 / 0,046"]
    ASS --> ABL["ML-03b · ablacao<br/>nao e perda de informacao, e ESCALA<br/>refazer o scaler no destino: 0,047 -> 0,322<br/>normalizacao por sujeito (sem rotulo<br/>do destino): 0,047 -> 0,298"]
```

---

## C — Validação externa e a conclusão metodológica (`ML-04`)

```mermaid
flowchart TB
    T["TREINO — Wearanize+, 92 sujeitos<br/>ajustado de uma vez, na totalidade"]
    T -->|"SEM reajuste de nada:<br/>sem reestimar normalizador no destino,<br/>sem recalibrar limiar,<br/>sem acesso aos rotulos da coorte externa"| E["TESTE — Newcastle, 27 sujeitos<br/>punho esquerdo · 30 440 epocas<br/>prevalencia de sono 0,699"]

    E --> R1["Contexto +/-11 — a melhor configuracao<br/>kappa 0,334 [0,254 a 0,416]<br/>especificidade 0,507 [0,442 a 0,576]"]
    E --> R2["Trivial medido NA PROPRIA coorte<br/>kappa 0,000 — a regua honesta"]

    I["VALIDACAO INTERNA (N=92)<br/>kappa 0,414 · especificidade 0,802"]
    I -.->|"degradacao ao trocar de coorte"| R1

    R1 --> C1["O NUMERO HONESTO DO TRABALHO<br/>e o externo, nao o interno:<br/>especificidade 0,802 -> 0,507"]

    subgraph SEL["O QUE A VALIDACAO EXTERNA DECIDIU"]
        H["HMM de 2 estados<br/>interno: delta kappa +0,123 (o dobro do contexto)<br/>externo: +0,036, e especificidade CAI (-0,037 a -0,050)<br/>a matriz de transicao carrega a prevalencia da coorte"]
        K["Contexto +/-11 epocas<br/>interno: delta kappa +0,075<br/>externo: +0,062 a +0,069, especificidade +0,081 a +0,095<br/>escala temporal e propriedade do fenomeno, nao da coorte"]
        H --> CONC["A validacao interna, sozinha,<br/>teria escolhido o HMM — e errado.<br/>Selecao de modelo apoiada so em<br/>validacao interna e insuficiente aqui."]
        K --> CONC
    end
    R1 --> SEL

    TETO["TETO DE CONCORDANCIA HUMANA — ML-05<br/>duas pontuacoes manuais do Wearanize+<br/>kappa 0,612 [0,572 a 0,650] em 90 sujeitos<br/>a faixa de leitura e [0; 0,61], nao [0; 1]<br/>NAO EXISTE para o Newcastle: aquela colecao<br/>nao publica segunda pontuacao"]
    TETO -.-> I

    L2["(FUTURO) ML-06 — segunda coorte externa (Walch 2019)<br/>com uma so, a degradacao e estimativa pontual,<br/>nao medida de variabilidade entre coortes"]
    R1 -.-> L2

    classDef futuro stroke-dasharray: 6 4;
    class L2 futuro;
```

## O que este diagrama não autoriza a dizer

1. **Nada aqui foi medido no Dormio.** As três figuras descrevem experimentos sobre
   acelerometria de cabeça, punho e coxa de bases públicas. Nenhuma época do MPU6050
   entrou em nenhum deles — a Etapa 0 (solda) ainda não aconteceu.
2. **A posição "cabeça" do Wearanize+ é um sensor acoplado à cabeça, não apoiado no
   travesseiro.** O custo de posição de 0,050 em kappa é o custo da **posição anatômica**;
   o custo do **acoplamento mecânico através do travesseiro** permanece não medido, e é
   o que o `VIA-01` decide.
3. **`κ` das duas coortes não se comparam diretamente**: kappa depende da prevalência, que
   é 0,895 na base de desenvolvimento e 0,699 na externa. A leitura válida é cada um
   contra o trivial medido na própria coorte.
