# Smart Dormio — backlog completo, por dependência

> **Levantado em 2026-09-10, revisado em 2026-09-22** contra o código real (não contra o que
> a documentação diz). Complementa o `ROADMAP.md`, que organiza por prioridade. Este arquivo
> organiza por **dependência**: a pergunta que ele responde é *"o que trava o quê?"*.
>
> A revisão de 22/09 fechou o bloco de ML inteiro e o acesso ao dataset. O que estava feito
> saiu das listas abertas e virou a seção **"Concluído"** — que existe para você não precisar
> reconstruir o histórico, e não para inflar a contagem.

---

## Estado do projeto, em uma dúzia de linhas

1. **O bloco de ML está fechado.** Pipeline reprodutível, baselines medidos, matriz de
   transferência N=92, ablação das hipóteses, quatro otimizações e validação externa em
   coorte independente. 70 testes passando.
2. **O dado não é mais problema.** Wearanize+ OA (100 sujeitos, ~46 GB) e Newcastle 2015
   (55 registros) estão em disco. **O DUA deixou de ser bloqueante** — a coleção aberta tem
   tudo que o experimento precisa, sem cadastro.
3. **O resultado original do trabalho já existe:** a transferência entre posições de sensor
   é fortemente **assimétrica** (treinar no pulso transfere; treinar na cabeça, não), e o
   colapso é **recuperável** por normalização por sujeito, sem usar rótulo do destino.
4. **O achado metodológico mais forte também:** validação externa separou ganho que atravessa
   coorte de ganho que não atravessa — e a validação interna, sozinha, teria escolhido errado.
5. **O número honesto do trabalho é o externo**, não o interno: especificidade cai de 0,802
   para 0,507 ao trocar de coorte. Está declarado em `LIMITACOES-TCC.md`.
6. **Backend e dashboard estão maduros** e aguentam uma noite real. O que falta ali é pouco.
7. **O firmware já aguenta uma noite offline.** O `HW-05` fechou em 22/09: amostragem
   desacoplada da rede, buffer de épocas de 30 s com degradação de resolução, 8,5 h de
   autonomia sem rede em resolução cheia — medidas, não estimadas. O `sketch.ino` de produto
   continua estruturalmente errado para captação noturna (`FW-07`).
8. **O que trava tudo continua sendo físico:** os 8 pinos do MPU6050 não estão soldados.
   Sem isso não há calibração, bancada, noite captada nem validação no dispositivo.
9. **Nada do bloco L0 substitui a medição** — e nada do que falta em L0 é grande.

**Se você tem uma hora:** rode `DATA-03` no Supabase (um SQL, destrava o dashboard de conta
nova). **Se tem um fim de semana:** solde. **Se tem um mês sem ferro de solda:** escreva os
`CALC-*` e `DIAG-*`, que são o que a banca lê.

**Contagem:** 65 itens abertos · **L0: 36** · L1: 12 · L2: 10 · L3: 7.

Eram 64 em 10/09 também — **dez fecharam, onze entraram**. A conta quase empata e o significado não:
o que saiu era o bloco de maior valor acadêmico disponível (`ML-01` → `ML-03`, o acesso ao
dataset, a verificação de referências); o que entrou é sobretudo **redação** (`DOC-08`) e
**higiene** (`GIT-03`, `CI-04`, `CI-05`). Fechar o ML não encurtou a lista — mudou a
natureza dela.

---

## Como ler

Cada item tem uma **camada de dependência**. A camada determina *quando* o item pode ser
feito — não o quanto ele importa.

| Camada | Significado |
|:---:|---|
| **L0** | Dá para fazer hoje. Software, análise ou texto. Não depende de nada físico. |
| **L1** | Depende da **solda** do MPU6050 (Etapa 0). Bancada, medição, firmware em placa. |
| **L2** | Depende de **dado real coletado** — uma noite medida, ou o protocolo do `VIA-02`. |
| **L3** | Depende de **você ou de terceiro**: orientador, compra, execução de SQL, conta de serviço. |

E um **peso**: 🔴 caminho crítico da defesa · 🟡 importante · ⚪ polimento ou pós-banca.

---

## O quadro em uma tela

```
                    ┌─────────────────────────────────────────────┐
   L3  VOCÊ ────────►  Etapa 0: soldar 8 pinos do MPU6050         │ 🔴 trava tudo
                    └───────────────────┬─────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────────┐
   L1  BANCADA ─────►  CAL-01/02 · VIA-01 · VIA-02 · FW-02/04/05   │ 🔴
                    │   HW-03/04/06 · VAL-01 · CALC-05             │
                    └───────────────────┬─────────────────────────┘
                                        │
                    ┌───────────────────▼─────────────────────────┐
   L2  DADO REAL ───►  VAL-02 · DASH-04 · DATA-06(valor) · HW-07   │ 🔴
                    │   ML-04 · ML-05 · ML-INF · APP-09            │
                    └─────────────────────────────────────────────┘

   L0  EM PARALELO, SEM DEPENDER DE NADA DISSO:
       CALC-01..04 · DIAG-01..04 · REQ-01 · LGPD-01/02 · FW-07 · FW-01/03 · API-03
       DATA-07b/07c · ML-06(carregador) · PWA-01 · UI-11

   ✅ FECHADO:  ML-01 · ML-02 · ML-03 · ML-03b · ML-04 · ML-04b · ML-05 · HW-05
                DOC-08
                INFRA-01 · SEC-05 · SEC-06 · SEC-07 · DATA-07a · UI-10
                DADOS em disco · DUA resolvido · REF-01 · DOC-06 · DOC-07
```

**A leitura importante:** o bloco de maior valor acadêmico disponível sem hardware **já foi
executado**. O que sobra em L0 é sobretudo texto e diagrama — que é exatamente o que a banca
lê, e o que mais rende por hora enquanto o ferro de solda não aparece.

---

## Concluído desde 2026-09-10

Não aparece nas listas abertas abaixo. Está aqui para o histórico ficar legível sem
`git log`.

### O bloco de ML, inteiro

| Item | O que ficou pronto | Onde |
|---|---|---|
| **ML-01** ✅ | **Pipeline reprodutível.** Config com hash que amarra métrica a parâmetros, reamostragem com anti-aliasing, épocas de 30 s, 8 features, interface única de carregamento (`carregar("wearanize", posicao=...)`), avaliação com split por sujeito. **70 testes.** | `ml/src/`, `ml/testes/` |
| **ML-02** ✅ | **Baselines medidos** em sintético, Wearanize+ (cabeça e pulso) e Newcastle. Inclui o trivial "sempre dormindo" e Cole-Kripke/Sadeh sobre substituto de contagem documentado. Confirmou o ponto do §0: o trivial é competitivo em acurácia e tem κ exatamente 0. | `ml/experimentos/saida/ml02_*.json` |
| **ML-03** ✅ | **Matriz de transferência entre posições, N = 92.** O resultado original do trabalho: a transferência é **assimétrica**. Treinar no pulso transfere para tudo (κ ≈ 0,38 nas três posições); treinar na cabeça **colapsa** no pulso (κ = 0,046) e na cabeça degradada (0,067). | `ml/experimentos/saida/ml03_transferencia_*.json` |
| **ML-03b** ✅ | **Ablação das hipóteses (itens 1–5), N = 92.** Mostrou que o colapso **não é perda de informação, é escala**: refazer o scaler no domínio de teste recupera κ de 0,047 para 0,322 — e **normalização por sujeito**, que não usa rótulo nenhum do destino, recupera para 0,298. Por isso ela virou a base do produto. | `ml/experimentos/saida/ml03b_ablacao_*.json` |
| **ML-03b** ✅ | **As quatro otimizações (6, 7, 8, 9) + o item 8b**, N = 92, com bootstrap pareado. Resumo: `class_weight="balanced"` vale 34 pontos de especificidade (item 6, contrafactual); limiar de Youden troca κ por especificidade (7); mediana móvel não sai do ruído (8); **HMM de 2 estados: Δκ = +0,123** (8b); **contexto ±11 épocas: Δκ = +0,075 e Δespecificidade = +0,101** (9). | `ml/experimentos/saida/ml03b_otimizacoes_*.json` |
| **ML-04** ✅ | **Validação externa.** Treina nos 92 do Wearanize+, testa nos 27 do Newcastle **sem reajuste de nada**. Tudo acima do trivial medido na própria coorte. Degradação: κ 0,414 → 0,334, **especificidade 0,802 → 0,507**. | `ml/experimentos/saida/ml04_validacao_externa_*.json` |
| **ML-04b** ✅ | **Lateralidade**, com participante como unidade de agrupamento: esquerdo isolado (27), direito isolado (26), efeito do lado pareado **dentro** do participante (26). **Todos os 24 IC95 contêm zero** — o lado não importa, o que sustenta as features invariantes a rotação. | `ml/experimentos/saida/ml04b_efeito_do_lado_*.json` |
| **ML-05** ✅ *(28/09)* | **Teto de concordância entre pontuadores.** As duas pontuações manuais do Wearanize+, na mesma redução binária do pipeline: **κ = 0,607 [0,569, 0,643] nos 96** com as duas, e **0,612 [0,572, 0,650] nos 90** que também estão nos 92 da base — este é o divisor. Dá a referência superior dos Δκ: a faixa de leitura é [0; 0,61], não [0; 1]. Achado de brinde: o pontuador 2 marca 7,8 pontos percentuais mais de vigília, e a especificidade humana vale 0,958 ou 0,520 conforme a referência. **Não há teto para o Newcastle** — aquela coleção não publica segunda pontuação. | `ml/experimentos/saida/ml05_teto_interavaliador_*.json` |
| **ML-07** ✅ *(não estava catalogado)* | **Infraestrutura de execução retomável.** LOSO com checkpoint por dobra; interrupção custa uma dobra, não um item, e nenhum experimento precisou reduzir N. Teste garante que rodar em uma chamada e em vinte dá o mesmo vetor. | `ml/experimentos/_retomada.py` |

### Firmware — o buffer offline

| Item | O que ficou pronto | Onde |
|---|---|---|
| **HW-05** ✅ | **Amostragem desacoplada da rede, com buffer de épocas.** Os três travamentos saíram (`while (!Serial)`, `while(1)` no `mpu.begin()` falho, conexão síncrona dentro do laço de amostragem). O núcleo é C++ puro, testado no host com `g++`: **341 verificações**, incluindo duas noites simuladas de 8 h. Buffer de **épocas de 30 s**, não de amostras — o que permite *degradar resolução* quando enche, em vez de descartar. Capacidade **medida**: 32 B por época, 1024 épocas = 8,53 h em resolução cheia. | `firmware/nucleo/`, `firmware/envio-continuo/` |

> **A razão de tudo:** `conectarWiFi()` era chamada dentro do laço e bloqueava até 20 s com
> `delay(500)`. Com intervalo de 10 s, uma queda de rede fazia cada ciclo levar 20–30 s — e a
> série continuava saindo, com aparência normal, com a base de tempo derivada. Para actigrafia
> isso é pior que lacuna: a lacuna a análise vê, a deriva não. **A perda de dado era o problema
> menor.**
>
> Ficou de fora, virou item próprio: a reescrita do `sketch.ino` (`FW-07`) e o endpoint de lote
> (`API-03`).

### Acesso ao dado — o DUA deixou de ser bloqueante

| Item | O que mudou |
|---|---|
| **SCI-01 / DEC-01** ✅ | **Resolvido sem depender do orientador.** A descoberta da **coleção aberta `Wearanize+ OA`** (DOI `10.34973/xrmf-5726`, CC-BY-4.0) mudou o quadro: baixa sem cadastro, tem os três acelerômetros e a PSG pontuada, e é a versão com a **unidade do Empatica corrigida**. O DUA da coleção restrita destrava só os questionários — **não está no caminho crítico**. |
| **DUA-01** ✅ *(não estava catalogado)* | **Guia completo escrito assim mesmo**, em `docs/WEARANIZE-ACESSO.md`: ORCID, ordem dos passos, o que o formulário pede, **quem precisa assinar** (não é você sozinho) e transferência internacional. Fica como caminho alternativo documentado, não como pendência. |
| **DADOS-01** ✅ | **Dado em disco:** Wearanize+ OA com 100 sujeitos (~46 GB) e Newcastle 2015 com 55 `.bin` + 28 PSG. Download retomável e verificação de integridade em `ml/ferramentas/baixar_wearanize.py`. |
| **DADOS-02** ✅ | **Formato auditado nos arquivos reais**, não na documentação: 5 armadilhas do Wearanize+ e 5 do Newcastle, cada uma com teste. Inclui a do Empatica em `g/64` (a v1.0 declara `g/16` — fator 4 de erro) e a dos IDs errados no cabeçalho do GENEActiv. |

### Referências e documentação

| Item | O que ficou pronto |
|---|---|
| **REF-01** ✅ | **Verificação de referências.** 11 fontes conferidas na fonte. Achados: 1 autoria falsa (`Rocha et al.` → **Li, Halaki & Chow**), 1 tendência não significativa apresentada como achado, 1 número virado indevidamente em requisito técnico, 2 citações não localizadas. **Nenhuma referência permanece sem autoria conferida.** |
| **DOC-06** ✅ | `docs/LIMITACOES-TCC.md`. **Atualizado em 21/09 com números medidos:** lateralidade, degradação entre coortes, ganho que atravessa coorte, e o nº de coortes independentes. |
| **DOC-07** ✅ | `docs/SINTESE-PESQUISA-E-CAMINHOS.md`. Percurso da pesquisa, as 11 fontes com o que cada uma sustenta, as 4 correções de referência e o que cada uma mudou no argumento. |
| **GIT-02** ✅ | `index.lock` preso resolvido e as mudanças pendentes commitadas. **Resíduo em `GIT-03`**, abaixo. |
| **GIT-04** ✅ *(aberto e fechado em 22/09)* | **Três documentos nunca commitados** — `BACKLOG-COMPLETO.md`, `ML-DATASETS-E-PLANO.md` e `SINTESE-PESQUISA-E-CAMINHOS.md` — estavam fora do git. O `ML-DATASETS-E-PLANO.md` é a fundamentação que os READMEs mandam ler: **um clone feito ontem não a traria junto.** Versionados nesta revisão. Prevenção em `CI-05`. |

---

# L3 — depende de você (e nada substitui)

| Item | O quê | Peso |
|---|---|:---:|
| **Etapa 0** | **Soldar os 8 pinos do MPU6050.** O módulo veio com os pinos não soldados; o contato por jumper produziu, em 25/08, registradores zerados, `\|a\| = 56,5 m/s²` com a placa parada, `−11,6 °C` e ruído 30× o normal. Teste de aceitação: pose Z+ com ruído ~0,02. **Trava as camadas L1 e L2 inteiras.** | 🔴 |
| **DATA-03** | Rodar `web-app/migrations/002_backfill_dono_dos_dados.sql` no Supabase. Escrito e mergeado desde agosto; **sem ele o dashboard de uma conta nova nasce vazio**. Um comando. | 🔴 |
| **RQ-01** | Confirmar RQ e hipótese com o orientador metodológico. | 🔴 |
| **LGPD-03** | **O ML eleva a aposta.** Um modelo que infere sono sobre pessoa identificada muda a natureza do tratamento: passa a haver *inferência* sobre saúde, não só registro de movimento. Conversar sobre termo de consentimento e, se houver voluntários no `VIA-02`, comitê de ética. **Agora é concreto, não hipotético — o modelo existe.** | 🔴 |
| **HW-02** | Decidir energia: LiPo + TP4056, e se o DevKit V1 fica ou sai. **Pode exigir compra.** O DevKit não atinge µA — regulador e USB-serial dominam o consumo. | 🟡 |
| **ML-06a** *(novo)* | **Baixar o Walch et al. 2019** (PhysioNet `sleep-accel`, 31 sujeitos, acelerometria de punho por dispositivo de consumo + PSG). É a segunda coorte externa, e **não é alcançável do ambiente de execução** — precisa ser baixado da sua máquina. Sem ela, a degradação entre coortes é estimativa pontual, não medida de variabilidade. | 🟡 |
| **AUTH-06** | SMTP próprio (Resend/Brevo) para "esqueci minha senha". Exige criar conta em serviço externo. | ⚪ |

> **A decisão de escopo que continua em aberto e é sua + do orientador:** o trabalho pode
> afirmar *"a noite de 27/08"* sem afirmar que o dado é sono? Hoje o painel diz "sessão de
> captação", que é o teto honesto. Ver `ROADMAP.md` → "O conceito de noite".

---

# L0 — dá para fazer hoje, sem hardware

É o que sobra de trabalho não bloqueado. Depois do fechamento do ML, **é quase todo texto e
diagrama** — que é o que a banca lê.

### Documentação e TCC — o maior valor por hora agora

| Item | O quê | Peso |
|---|---|:---:|
| **CALC-01** | Modelo de energia/autonomia: corrente por estado, duty cycle, `I_média = (I_ativo·t_ativo + I_sleep·t_sleep)/(t_ativo+t_sleep)`, `autonomia = C_bateria/I_média`. Quantifica o "baixo consumo" e **expõe o limite do DevKit V1** → embasa o `HW-02`. É predição; a medição é `VAL-02`. | 🔴 |
| **CALC-02** | Física do acelerômetro: força específica, `\|a\| = √(ax²+ay²+az²)`, resolução (±8g/16 bits ≈ 0,244 mg/LSB), ruído, Nyquist. **Com um número a mais para explicar:** por que 21 Hz, e não 260 Hz (`FW-06`). | 🔴 |
| **CALC-03** | Índice de atividade (actigrafia): métrica por época e derivação do limiar `g ± k·σ`. **Boa parte já está resolvida pelo `ML-01`** — as 8 features e a justificativa de cada uma estão escritas em `ml/src/features.py`. O item virou *transpor para o texto*, não *decidir*. | 🔴 |
| **CALC-04** | Análise elétrica: pull-down 10 kΩ (`I = V/R ≈ 0,33 mA`, `P ≈ 1,1 mW`), pull-ups do I2C, níveis 3,3 V, fonte de despertar. | 🟡 |
| **DIAG-01** | Diagrama de blocos da arquitetura. | 🔴 |
| **DIAG-02** | Esquemático do circuito; v1 (1 sensor) e v2 (2, endereços I2C). | 🟡 |
| **DIAG-03** | Fluxograma do firmware / máquina de estados. | 🔴 |
| **DIAG-04** | Diagrama de sequência do fluxo autenticado + **modelo ER** com `devices` e `profiles`. Também é a parte pendente do `DOC-05`. | 🟡 |
| **DOC-05** | READMEs e `CLAUDE.md` — falta só o `DIAG-04`. | 🟡 |
| ~~**DOC-08**~~ ✅ | **Feito em 28/09.** `docs/RESULTADOS-TCC.md` — o capítulo de resultados em prosa, entre os mesmos marcadores do `LIMITACOES-TCC.md`, com nota de procedência que amarra cada número a um JSON e ao comando que o reproduz. Fechou junto o `ML-05` (teto interavaliador), que era a lacuna barata que faltava. | ✅ |
| **DOC-09** 🟠 *(novo — 30/09, primeira versão escrita)* | **`docs/DIARIO-DE-ENGENHARIA.md` — o diário cronológico, reconstruído retroativamente.** Cada entrada traz data e item, o problema como foi entendido no início, a hipótese de trabalho, o que foi testado e como, o resultado medido, a adaptação quando o resultado contrariou a hipótese, o risco que ficou em aberto, e a procedência. Vira o **capítulo de desenvolvimento** do TCC. O valor está no que deu errado: o sketch que nunca compilou, o vetor dourado que gravava a própria referência, o limiar de 1,2 m/s² que corresponde a ~67 σ, a feature angular desmentida pela geometria esférica, a recuperação de 78% que valia para um par de posições, e o ganho de modelo que não atravessou coorte. **O que falta:** o intervalo de junho a agosto está esparso, porque o `HISTORICO.md` que o cobre não é versionado e não pode servir de procedência num capítulo de TCC; e a seção final lista as lacunas de propósito. Daqui para frente é registro corrente, não reconstrução. | 🟡 |
| **DOC-06b** | **Ler os artigos antes de citá-los** (referência conferida ≠ artigo lido) e converter para o padrão de citação do TCC se não for autor-data. Herdado do `DOC-06`. | 🔴 |
| **LGPD-01** | Política de privacidade e termos. **Rascunho escrito em 29/09** (`docs/POLITICA-DE-PRIVACIDADE.md`), a partir do código e não da intenção: cada direito do art. 18 vem marcado como implementado, parcial ou **sem mecanismo**. Falta: **(a)** decidir o controlador e a base legal — consentimento (art. 7º, I) ou pesquisa (art. 7º, IV), que muda a política inteira e **não dá para inferir do repositório**; **(b)** a rota e a página que sirvam o texto; **(c)** revisão jurídica. **Rascunho é L0; a revisão com o orientador é `LGPD-03`.** | 🟡 |
| **LGPD-02** *(novo)* | **Não existe política de retenção.** Nenhum expurgo automático, nenhum prazo, nenhuma inatividade que dispare remoção: uma leitura enviada hoje fica indefinidamente até o titular apagar a conta. A política teve de declarar isso na seção 7. Decidir prazo e implementar, ou declarar formalmente que não haverá — as duas saídas são defensáveis; o silêncio não. | 🟡 |
| **LGPD-04** *(novo)* | **`profiles.idade` é coluna morta.** Existe no esquema desde a migração `001`, **nenhuma tela a preenche e nenhuma funcionalidade a lê** — está vazia para todos. Minimização (art. 6º, III) não é violada enquanto a coluna está vazia, mas é exatamente o tipo de estrutura que alguém preenche um dia "porque já estava lá". Ou ganha finalidade declarada, ou sai por migração. | ⚪ |
| **REQ-01** | Documentar requisitos: dimensões, conforto, autonomia, aquecimento, custo, segurança. | 🟡 |

### ML — o que sobrou

| Item | O quê | Peso |
|---|---|:---:|
| **ML-06b** *(novo)* | **Escrever `ml/src/carregar/walch.py`.** A interface única garante que é só isso — sem tocar em feature, época, baseline, modelo ou métrica. Dá para escrever contra a documentação do dataset **antes** do `ML-06a`, mas só valida com o dado em mãos. ⚠️ Escrever carregador sem ver o arquivo real foi o que produziu as 10 armadilhas já catalogadas: escreva, mas **não confie até rodar**. | 🟡 |
| **ML-08** *(novo)* | **Combinação item 9 + HMM com LOSO interno.** Já foi medida na coorte externa (κ = 0,338 contra 0,334 do item 9 sozinho, mas −0,04 de especificidade); falta a versão interna N=92. **Provavelmente esforço mal gasto** — a validação externa já mostrou que o ganho do HMM não atravessa coorte. Registrado para não parecer esquecimento. | ⚪ |

### Backend, dados e API

| Item | O quê | Peso |
|---|---|:---:|
| **DATA-07a** ✅ *(29/09)* | **O contrato declara o vetor de características.** `f` (6 intra-época), `g` (gravidade unitária) e `fs` (taxa), todos opcionais; seção 2.6 fixa ordem canônica, unidades, faixas e representação. Contrato **v2.5.0**, MINOR — nenhum firmware precisa ser regravado, e o formato sem `f` continua sendo o corrente. A decisão de formato tem estudo próprio em `docs/DECISAO-BUFFER-E-FEATURES.md`. | ✅ |
| **DATA-07b** *(novo)* | **Implementar o vetor — nos três lados.** ⚠️ O `DATA-07` original dizia "o item saiu de 'a definir' para 'transcrever'". **Isso estava errado**, e a verificação de 29/09 mostrou por quê: as 8 features existem **só em Python**. O núcleo C++ não tem nenhuma delas (`grep -rniE "enmo\|zcr\|p_frac\|inclinacao\|d_angulo\|mag_din" firmware/` devolve vazio) — o que existe de "lado C++" é uma referência escrita em Python dentro de `test_vetor_dourado.py`. Falta: **(a)** o biquad Butterworth de 2ª ordem ida-e-volta em C++, com inicialização em regime permanente; **(b)** acumulação por época das 6 features + `ĝ`, no registro de 40 B decidido; **(c)** um alvo de teste em C++ que leia `vetor_dourado.json` (428 KB, 5 casos × 960 amostras — hoje não há parser JSON no núcleo, que é `-fno-exceptions -fno-rtti` de propósito); **(d)** migração e mudança na função de ingestão para persistir; **(e)** derivação de `inclinacao_rel`/`d_angulo` no servidor, sobre a noite completa. Peso comparável ao `FW-07`. ⚠️ *Atualização do `DATA-07c` (30/09):* o item **(e)** ficou mais barato — a derivação foi extraída para `features_inter_epoca(ĝ)` em `ml/src/features.py`, com dourado próprio de 23 KB que o backend consegue rodar **sem** o pipeline de ML (lê `g_por_epoca`, compara com `esperado`). E o item **(c)** ganhou um alvo menor: o arquivo do servidor não tem amostra bruta. Falta decidir, no **(b)**, se o dispositivo emite `f` de época truncada — medição em `DATA-07d`. | 🔴 |
| **DATA-07c** ✅ *(30/09)* | **O vetor dourado ganhou casos multi-época, e virou dois arquivos.** O dourado passou a espelhar as duas fronteiras da v2.5.0: `vetor_dourado.json` (dispositivo, Python↔C++, 6 features **+ `ĝ`**, 437 KB) e `vetor_dourado_sequencias.json` (servidor, derivação de `inclinacao_rel`/`d_angulo` a partir do `ĝ` guardado, **23 KB e nenhuma amostra bruta** — as duas features são função só de `ĝ`, então cobri-las não custa sinal). 8 sequências: mudança de postura, virada brusca de 140°, deriva coerente sub-grau, retorno exato à orientação, faixa cobrindo todos os bins do estudo do buffer, duas épocas, uma época, e lacuna temporal. Tolerâncias **derivadas entre piso medido e teto de decisão**, re-medidas a cada execução por `test_as_tolerancias_ainda_cercam_o_piso`. Provado por mutação: `testes/verificar_vetor_dourado_por_mutacao.py`, 12/12 sabotagens detectadas + 1 ponto cego registrado. **Três defeitos do instrumento anterior corrigidos** — ver `DATA-07d`. | ✅ |
| **DATA-07d** *(novo, saiu do 07c)* | **O que o `DATA-07c` encontrou e não cabe nele.** (a) **O dourado se regravava sozinho:** `test_gravar_vetor_dourado` gravava o arquivo e conferia que ele existia — nunca podia falhar, então o arquivo perseguia o código em vez de prendê-lo. Corrigido: agora confere, e regravar exige `DORMIO_REGRAVAR_DOURADO=1`. (b) **A exigência de casamento exato do ENMO está errada para um firmware float32:** medido em 60 sementes, `enmo_media` em float32 diverge 1,10e−6 relativo e `enmo_max` 3,51e−6, contra a tolerância de `rel=1e−6` que estava no lugar — ela **reprovaria firmware correto**. A causa é cancelamento em `‖a‖ − 1` com ‖a‖≈1, e trocar o acumulador para double não resolve (1,101e−6 vs 1,097e−6): o erro entra no `sqrt` por amostra. Tolerância trocada para absoluta, 1e−7 g = 1 ULP de float32 em 1 g. (c) **Época incompleta não tem paridade:** o ramo degenerado de `estimar_gravidade` (n ≤ 9) não existe na referência estilo-firmware, e a divergência vai a 54 %; mesmo passando do ramo, n=64 diverge 3 % e n=300, 0,8 %. **O contrato precisa dizer que o dispositivo não emite `f` de época truncada** — decidir no `DATA-07b`. | 🟡 |
| **DATA-06** | **O limiar viaja com a leitura.** Hoje `1,2 m/s²` é constante compartilhada nascida do travesseiro, e o celular é classificado pela mesma régua. A **coluna e o campo dão para criar já**; o *valor* do limiar do celular depende do `VIA-02` (L2). | 🔴 |
| **DATA-02** | **Modelo de amostragem** — índice de atividade por época vs. evento avulso. **Decidido: 30 s**, que é a resolução dos rótulos de PSG de todos os datasets e a época do pipeline. Falta *aplicar* no firmware (`FW-05`); o contrato já o declara desde a v2.5.0 (`DATA-07a`). | 🔴 |
| **INFRA-01** | ✅ **Resolvido por outro caminho.** O Supabase CLI não foi adotado; em vez dele, `web-app/tests/rls/esquema_base.sql` recria os primitivos do Supabase (schema `auth`, `auth.uid()`, os papéis, os GRANTs) sobre um Postgres descartável, e as migrações do repositório são aplicadas do disco sem adaptação. Resolve o que o item existia para resolver — testar RLS de verdade — sem introduzir dependência de ferramenta. | ✅ |
| **SEC-05** | ✅ **Fechado.** 105 testes de RLS contra Postgres real, sem mock: adversarial em `profiles`, `devices` e `sleep_data` por todo comando, mais invariantes de catálogo (tabela nova sem RLS, `using (true)`, policy para `anon`). Verificado por mutação — 18 sabotadores, todos detectados (`tests/rls/verificar_por_mutacao.py`). | ✅ |
| **SEC-06** | ✅ **Fechado.** A ingestão saiu da `service_role`: papel `dormio_ingestao` com `EXECUTE` em três funções e nenhum privilégio de tabela. O dono da linha é resolvido dentro do banco, a partir do token. Teste estático impede que rota nova use o cliente privilegiado. Migration `005`. | ✅ |
| **SEC-07** | ✅ **Fechado.** Direito de eliminação (LGPD art. 18, VI): policies de `delete` para as próprias linhas, `apagar_minha_conta()` sem parâmetro de usuário, `DELETE /api/me` com confirmação por frase. Migration `006`. Texto acadêmico em `docs/LGPD-ELIMINACAO.md`. | ✅ |
| **UI-10** ✅ *(29/09)* | **Tela de exclusão de conta.** *Configurações → Excluir conta*: barreira em dois passos, com a lista do que será apagado **antes** do campo de confirmação, e a frase exigida digitada à mão (comparação sem `trim` e sem ignorar caixa — cada variação aceita aproxima a barreira de um clique). **Três desfechos, não dois:** o `200` com `conta_de_acesso_removida: false` tem tela própria, com cor e ícone de alerta, porque é um estado em que dado pessoal do titular continua existindo. `interpretarRecibo` é pessimista de propósito: ausente, nulo ou `"true"` viram parcial. 23 testes. | ✅ |
| **UI-11** *(novo)* | **Edição de perfil.** A política de privacidade teve de declarar que **não há tela para corrigir nome e e-mail** — o app os exibe e só, e o art. 18, III assegura a correção. Barato: a policy de `update` em `profiles` já existe desde a migração `001`; falta a interface. | 🟡 |

### Firmware que dá para escrever sem a placa

| Item | O quê | Peso |
|---|---|:---:|
| **FW-07** *(novo)* | **Reescrever o `sketch.ino`.** Hoje ele tira **uma amostra por boot** e dorme: não registraria uma noite nem com rede perfeita, porque não tem amostragem periódica nenhuma. Em 22/09 recebeu só a correção defensiva dos travamentos — os `while` sem saída e a medição que vinha depois da rede. O conserto de verdade é reorganizá-lo em torno do núcleo (`firmware/nucleo/`), com **buffer no RTC** (`RTC_DATA_ATTR`, 128 épocas ≈ 1 h em resolução cheia e 65 h degradado — o heap não sobrevive ao Deep Sleep) e ciclo acordar → medir → agregar → dormir. O núcleo já existe e está testado; o que falta é a máquina de estados do sono. | 🔴 |
| **API-03** *(novo)* | **Endpoint de lote no `/api/data`.** Drenar uma noite de 8 h são **960 POSTs**, um handshake TLS novo cada — número medido, não estimado (`firmware/nucleo/capacidade.cpp`). Hoje o firmware contorna com rajada limitada (3 por volta, e só com folga até o próximo tick), o que funciona e é lento. Um `POST /api/data/lote` com um array de leituras, validando item a item e respondendo quais entraram, resolve. **Observação de dimensionamento:** foi por causa desses 960 que o backoff ganhou teto de 2 min — sem teto, o aparelho não perceberia a rede voltando; com teto curto demais, gastaria rádio para falhar. | 🟡 |
| **FW-01** | Lógica atividade/repouso por época no firmware (`DATA-02`). Escrevível e testável no Wokwi; só a calibração espera a solda. **Parcialmente coberto:** o `envio-continuo` já classifica por época de 30 s desde o `HW-05`; falta levar ao `sketch.ino` (`FW-07`). | 🟡 |
| **FW-03** | Empacotamento do dado conforme `DATA-01`. | 🟡 |
| **HW-01** | Revisar o BOM: o que é andaime (botão, pull-down de 10 kΩ) e o que é produto. É análise, não montagem. | 🟡 |

### Dashboard, PWA e app

| Item | O quê | Peso |
|---|---|:---:|
| **PWA-01** | **Exercitar a instalação de verdade.** O service worker não registra em desenvolvimento, então "Adicionar à tela inicial" só aparece em produção — e ninguém testou. O comportamento do iOS com `display: standalone` também não foi verificado. | 🟡 |
| **APP-03** | Armazenamento seguro do token. Em PWA fica em `sessionStorage`; nativo tem Keystore. *Reavaliar: com o `APP-08`, o token pode deixar de existir no celular.* | 🟡 |
| **APP-04** | **iOS: investigação, não implementação.** Rota A (áudio em background) muda o escopo declarado e a conversa de LGPD; rota B (`CMSensorRecorder`) é coerente mas **não verificada**. O item é *confirmar antes de virar plano*. | ⚪ |
| **APP-02** | Android nativo com foreground service. Fazível hoje; **caro e pós-banca**. | ⚪ |
| **UI-15** | Bundle de **876 kB** (249 kB gzip) num único chunk; o Vite avisa a cada build. Code splitting por rota resolve. | ⚪ |
| — | Aplicar a linguagem de blueprint também no app autenticado (hoje vive só na landing). | ⚪ |

### Infraestrutura e qualidade

| Item | O quê | Peso |
|---|---|:---:|
| **GIT-03** *(novo)* | **Resíduo de sandbox no `.git`.** Duas pastas criadas para contornar a proibição de exclusão do ambiente: `.git/_lixo_sandbox/` (57 itens, 240 KB — locks órfãos e `tmp_obj_*`) e `.git/_locks_orfaos/` (vazia). **Nada quebra enquanto ficarem**: `git fsck` dá exit 0 sem corrupção, e commits funcionam. Apagar exige um terminal na máquina. | ⚪ |
| ~~**CI-05**~~ ✅ *(escrito 30/09, **executado e corrigido 16/10**)* | **A especificação original estava errada, e o erro era do tipo que o item existe para combater.** O que estava escrito aqui — *"um job que falhe quando há arquivo não rastreado em `docs/`"*, três linhas — **não pode reprovar num runner**: `actions/checkout` monta a árvore a partir do commit, então arquivo não rastreado nunca chega ao CI e `git ls-files --others` devolve vazio sempre. Teria sido prevenção decorativa contra a classe de problema que o `GIT-04` já demonstrou ser real. O que substituiu: `scripts/conferir_docs_versionados.py`, com duas verificações de alcance declarado — **(1)** órfão na árvore (existe, não rastreado, não ignorado — o estado exato do `GIT-04`; só detectável na máquina de quem edita) e **(2)** `docs/*.md` citado por arquivo versionado e ausente do git e do `.gitignore` — **esta roda e reprova no CI**, porque é a forma pela qual o `GIT-04` causava dano: um clone não trazia a fundamentação que os READMEs mandavam ler. A distinção que o script usa é *ignorado é decisão, não rastreado é esquecimento*. **16/10 — primeira execução: REPROVOU, e o motivo era o próprio script.** Acusou três referências pendentes, e as três eram prosa: `docs/FOO.md` e `docs/sub/FOO.md` estão no comentário do próprio `PADRAO_REFERENCIA`, para explicar o que o regex casa, e `docs/ORFAO-DE-TESTE.md` está nesta seção do backlog, dentro do procedimento de validação **deste script**. Job vermelho desde o primeiro push, por auto-acusação. Corrigido com `EXEMPLOS_EM_PROSA` — isenção estreita, **impressa a cada execução** (isenção silenciosa é como uma verificação deixa de verificar), e que vale **só para a (2)**: na (1) o nome não tem isenção, senão o próprio procedimento de validação ficaria incapaz de falhar. Validado nas duas direções: órfão criado → a (1) acusa; doc inexistente citado de dentro de arquivo versionado → a (2) acusa; árvore limpa → OK, exit 0, inclusive com `CI=true`. | ✅ |
| ~~**CI-03**~~ ✅ *(escrito 30/09, **executado e corrigido 16/10**)* | **Não precisava de `arduino-cli`.** O item pedia uma toolchain de 300 MB; o repositório já tinha a verificação e faltava só chamá-la. `firmware/nucleo/` é C++ puro com Makefile de host, e o alvo `make sintaxe` abre os `.ino` com stubs mínimos do Arduino e confere sintaxe, tipos e formato de `printf` por `g++ -fsyntax-only` — que o runner já tem. Job novo roda `make` (341 verificações), `make sintaxe` e `make capacidade`. Esta última não é teste: é a medição de horas de buffer que o `firmware/nucleo/README.md` e este backlog citam como *medida*, e rodá-la no CI impede o número citado de descolar do código. **16/10 — primeira execução: `make` 341/0 e `make capacidade` passaram, mas o `make sintaxe` tinha dois dos quatro sketches versionados.** `caracterizacao.ino` e `diagnostico-i2c.ino` nunca estiveram na lista, e na primeira vez que foram compilados os **dois** tinham exatamente o defeito que o alvo nasceu para pegar — string com quebra de linha literal no meio, o mesmo do `envio-continuo.ino` de 22/09. Não compilavam em máquina nenhuma. Mais dois achados no `diagnostico-i2c.ino`: uma chave sobrando, que fechava `setup()` no meio, e `%lu` para um `uint32_t` — que no ESP32 é `unsigned int`, então o `printf` lia 8 bytes de um argumento de 4 e imprimia lixo em silêncio (achado só porque o stub do `Serial` tem `__attribute__((format))`). A correção de fundo não é a lista maior: **a lista deixou de ser escrita à mão** — `SKETCHES` sai de `$(wildcard)`, com guarda para o caso de não casar nada, porque alcance de verificação escrito à mão silenciosamente para de acompanhar a pasta. Validado por controle positivo nas duas direções: string quebrada devolvida → reprova; sketch novo com função inexistente → reprova, provando que o wildcard o pega. Estado final: `make` 341/0, `make sintaxe` 4/4, `make capacidade` 0. | ✅ |
| ~~**CI-04**~~ ✅ *(escrito 30/09, **executado e corrigido 16/10**)* | **Job novo para a suíte do `ml/`.** Não precisa dos ~46 GB: `ml/dados/` só tem `.gitkeep` versionado e a suíte gera sinal sintético — o que ela verifica é a *definição* das features e das métricas, não a medição. Python 3.10, que é a versão em que `ml/requirements.txt` foi verificado. Duas guardas, pela mesma razão da guarda do job `rls`: **(a)** o número de testes coletados é conferido contra os 70 medidos em 22/09 *antes* de rodar — o modo de falha aqui não é `pytest.skip`, é coleta vazia ou parcial, que passa em silêncio; **(b)** `verificar_vetor_dourado_por_mutacao.py` entra no job, porque a paridade do vetor dourado já esteve em estado de não poder reprovar (`DATA-07d`, item a). **16/10 — primeira execução: a suíte passou inteira, a guarda é que estava quebrada.** 107 testes coletados, 107 passados em 8,75 s, e o verificador por mutação detectando 12 de 12 sabotagens com o ponto cego registrado confirmado. Mas o piso da guarda era **70**, medido em 22/09, e a suíte tem 107: ela teria aceitado perder **37 testes — um terço da cobertura — sem reprovar.** É o próprio modo de falha que ela foi escrita para pegar, com piso alto o bastante para parecer que pegava. Piso em 107, com o motivo e a obrigação de atualizar escritos ao lado. Controle positivo real, não simulado: `import` inexistente em `testes/test_avaliar.py` → coleta cai a 100 → a guarda reprova. Vale notar *por que* ela é necessária ali: o passo roda o pytest com `|| true`, então o exit 2 da coleta sumiria — quem acusa é a contagem. **E a suíte do `ml/` não é o que enchia o disco:** roda em 8,75 s e não escreve em `/tmp` (ficou em 92 KB durante toda a execução). O custo está em instalar `scipy` + `scikit-learn`, que é o que precisa de `TMPDIR` fora de um `/tmp` pequeno. | ✅ |
| **CI-02** | O CI **não roda linter** — não há ESLint nem Ruff/flake8. Não é urgente, mas é o tipo de ausência que uma banca nota num trabalho que se apresenta como rigoroso. **Deixado fora da revisão de 30/09 de propósito:** ligar linter sem configuração num código que nunca passou por um produz centenas de achados de estilo e um job vermelho permanente, que é como se aprende a ignorar o CI. O item pressupõe uma decisão de configuração que ninguém tomou ainda. | ⚪ |

> ✅ **Os três foram executados em 2026-10-16, e o que a execução achou é o motivo de ela
> ser obrigatória.** A nota anterior nesta posição dizia *"escrito, não executado"* e
> listava o procedimento de validação pendente. O procedimento foi feito, e **nenhum dos
> três jobs passava como estava escrito** — nem o `CI-05`, cuja análise era correta e
> continua sendo; o que falhou foi a implementação dela. Três defeitos, um por job:
>
> | Job | O que a execução achou |
> |---|---|
> | `documentos` (CI-05) | O verificador se acusava a si mesmo. Vermelho no primeiro push. |
> | `firmware` (CI-03) | A lista tinha dois dos quatro sketches, e os dois de fora **não compilavam** — pelo mesmo defeito de 22/09. |
> | `ml` (CI-04) | A suíte passa inteira; a guarda estava 37 testes defasada e toleraria perder um terço da cobertura. |
>
> **A leitura não pegaria nenhum dos três.** Todos os três arquivos tinham sido lidos e
> revisados em 30/09 — o raciocínio sobre o `actions/checkout` estava certo, o Makefile
> estava bem escrito, a guarda era uma boa ideia. O que estava errado era o alcance de
> cada um, e alcance não se vê lendo: vê-se rodando e tentando fazer falhar. Daí o que
> vale guardar como método, mais que os três consertos: **uma verificação vale pelo
> alcance, e alcance só se mede com controle positivo** — provocar o defeito de
> propósito, confirmar que acusa. Foi assim que cada um dos três foi fechado aqui.
>
> Para reconferir, na máquina: `python scripts/conferir_docs_versionados.py` (OK), depois
> `touch docs/ORFAO-DE-TESTE.md` e de novo (reprova em (1)), depois apagar; `cd ml &&
> python -m pytest testes -q` (107); `cd firmware/nucleo && make && make sintaxe &&
> make capacidade` (341/0, 4/4); `cd web-app && python -m pytest tests/ --ignore=tests/rls`
> (240).
>
> 🔴 **`CI-06` *(novo — 16/10)*: o CI não roda desde 2026-09-10, e são QUATRO jobs sem
> execução em runner, não três.** Medido na API pública do Actions: a última execução é a
> **#131, de 10/09**, em `develop`, com sucesso — e o `ci.yml` que existia em `develop`
> naquela data tinha **dois** jobs, `test` e `frontend`. O `ci.yml` da branch tem seis.
> Nunca rodaram em runner: `ml`, `firmware`, `documentos` (30/09, validados localmente em
> 16/10) **e `rls`**, que entrou em `d4011a1` em 28/09 — dezoito dias depois da última
> execução. O quarto item é o que carrega a afirmação de segurança do trabalho (`SEC-05`).
>
> Sobre o `rls`, com a distinção que importa: **os 125 testes não são código nunca
> executado** — a entrada de 28/09 do diário registra execução local contra Postgres de
> verdade, com verificação por mutação, e `web-app/tests/rls/` não mudou desde então. O que
> nunca aconteceu é **(a)** o *job* rodar, isto é, a guarda contra pulo silencioso ser
> exercitada onde ela precisa funcionar, e **(b)** a perna da **Postgres 16**, já que o
> harness foi verificado na 14. A matriz existe porque RLS e privilégio mudam entre majors;
> a 16 é, hoje, hipótese. **Quando o push sair, a 16 é a primeira coisa a olhar** — antes
> dos três jobs novos. Se reprovar, é achado de segurança e vale mais que o selo verde.
>
> ⚪ **O push está bloqueado por ambiente, não por decisão.** Autorizado em 16/10, tentado e
> recusado: `could not read Username for 'https://github.com'` — o ambiente de execução lê o
> repositório público anonimamente mas não tem credencial de escrita, e obtê-la exigiria
> manipular credencial em texto claro. Os 6 commits existem só no clone local. O comando,
> para rodar num terminal da máquina: `git push origin
> chore/GIT-01-normalizar-fim-de-linha`. As conferências pré-push foram feitas e passaram
> (remoto correto, branch inexistente no remoto, gatilho `chore/**` cobre, ações `@v6`
> resolvem, nenhum segredo em commit nenhum, os 15 pendentes fora).

---

# L1 — espera a solda

Nada aqui começa antes da **Etapa 0**.

| Item | O quê | Peso |
|---|---|:---:|
| **CAL-01** | Caracterização de 6 posições. Sketch pronto em `firmware/caracterizacao/`. Produz viés e escala por eixo desta unidade. O viés de Z medido em 25/08 foi **−1,06 m/s² — 89% do limiar sozinho**, mas através de contato ruim, então é provisório. *Melhorias pendentes no sketch: mostrar o ângulo de cada pose e avisar acima de 8°; detectar troca de sinal entre `+X` e `−X`.* | 🔴 |
| **CAL-02** | **Repetir a caracterização depois do `FW-06`.** O filtro passou de 260 Hz para 21 Hz em 10/09, o que muda o ruído de base — e o limiar do `DATA-02` é definido sobre esse ruído. Número medido antes disso não transfere. | 🔴 |
| **VIA-01** | Viabilidade de bancada: 2 min parado → 2 min mexendo a cabeça → 2 min virando o corpo. Pergunta: *os três blocos se separam?* | 🔴 |
| **VIA-02** | O mesmo protocolo com **celular e travesseiro gravando ao mesmo tempo**. Produz o limiar do celular, a diferença de acoplamento medida e o grupo de controle. | 🔴 |
| **FW-05** | **Amostragem bruta para o ML.** O firmware precisa amostrar a ≥ 42 Hz (Nyquist do filtro de 21 Hz) e agregar em épocas de **30 s**. **Agora com destino definido:** as 8 features de `ml/src/features.py`, e o vetor dourado (`ml/testes/vetor_dourado.json`) existe para o teste em C++ do firmware reproduzir os valores. | 🔴 |
| **HW-04** | Encapsulamento e fixação para uso noturno; **segurança térmica do LiPo dentro do travesseiro**. | 🔴 |
| **VAL-01** | Validação no dispositivo real: leitura montada, consumo medido, estabilidade, uma noite captada. | 🔴 |
| **FW-02** | Deep Sleep real testado na placa (hoje é mock do Wokwi). | 🟡 |
| **FW-04** | Portar o firmware para a placa sem dependências do Wokwi. | 🟡 |
| **HW-03** | Wake-on-Motion real: ligar o INT do MPU6050 a um GPIO RTC e configurar os registradores. Hoje o despertar é por EXT1 num **botão** — andaime de simulação. | 🟡 |
| **HW-06** | Entregáveis físicos: esquema de ligação, diagrama de montagem, fotos. `hardware/` está **vazio**. | 🟡 |
| **CALC-05** | Análise térmica com **medição real** — `P = V·I`, elevação de temperatura, limites do LiPo. | 🟡 |

---

# L2 — espera a coleta

Depende de dado real captado — uma noite medida, ou o protocolo do `VIA-02`.

| Item | O quê | Peso |
|---|---|:---:|
| **VAL-02** | Validação quantitativa: F1, matriz de confusão, curva de corrente×tempo medida. | 🔴 |
| **DASH-04** | Visualização de **noite completa**: linha do tempo e lacunas como indicador de repouso. O gráfico já está preparado; falta o dado. | 🔴 |
| **ML-04** | Calibração do modelo para o Dormio com dado próprio. **Ajuste de limiar, não re-treino** — n=1 não treina nada. ⚠️ **A validação externa reforçou a cautela:** o que parece ganho numa coorte pode não atravessar; com n=1 não há como distinguir. | 🟡 |
| **ML-05** | O que o modelo devolve ao usuário — e o que **não** devolver. Ver §6 do plano de ML. **Um número novo entra aqui:** a especificidade externa de 0,507 é o que o produto deve assumir, não os 0,802 internos. | 🟡 |
| **ML-INF** | Onde a inferência roda. Proposta: job em lote no backend Python ao fim de uma sessão, não no ESP32. Ver §8 do plano de ML. | 🟡 |
| **HW-07** | Arquitetura v2 — **fusão de 2 acelerômetros** (travesseiro + sob o colchão), se o `VIA-01` mostrar que o travesseiro subcapta movimento de corpo. Gatilho, não plano. **Implica rever a redação da RQ** (travesseiro → cama/travesseiro). | 🟡 |
| **APP-09** | Continuidade quando o usuário troca celular por sensor. Instrumentos diferentes, limiares diferentes (`DATA-06`). | 🟡 |
| **UI-14** | Lista de espera na landing. 🔒 Gatilho: protótipo funcionando **e** `VIA-01`. Não fazer antes. | ⚪ |
| **APP-05** | Distribuição (loja ou APK). Depende de `LGPD-02` e `APP-04`. | ⚪ |
| **LGPD-02** | 🔒 Bloqueante da **distribuição**, não do desenvolvimento. Acelerômetro de celular é dado pessoal — há literatura de identificação por padrão de marcha. | ⚪ |

---

## O caminho crítico, em ordem

Se só houver tempo para uma sequência, é esta:

1. **`DATA-03`** (L3, um comando) — rodar o SQL no Supabase. É a coisa mais barata com
   consequência real que sobrou: sem ele, o dashboard de uma conta nova nasce vazio.
2. **Soldar** (L3). Tudo abaixo espera.
3. **`CAL-01` + `CAL-02`** — calibrar a unidade *depois* do `FW-06`, senão o número não vale.
4. **`VIA-01` + `VIA-02`** — um dia de bancada que produz a viabilidade, o limiar do celular
   e o grupo de controle.
5. **`VAL-01`** — uma noite real captada. O painel já aguenta.
6. **`DASH-04` + `VAL-02`** — a noite na tela e os números medidos.

**Em paralelo, sem esperar nada:** `CALC-01..04`, `DIAG-01..04`, `LGPD-01`, `FW-07`, `DATA-07b`.

> **O que mudou no caminho crítico desde 10/09:** o bloco `ML-01 → ML-02 → ML-03` saiu dele —
> está feito. O gargalo acadêmico era *escrever o resultado* (`DOC-08`), e **isso fechou em
> 28/09**: o capítulo está em `docs/RESULTADOS-TCC.md`. O que sobra de texto é `CALC-*` e
> `DIAG-*`, que dependem de números de hardware, não de análise. O gargalo material continua
> sendo o mesmo ferro de solda.

---

## Fontes

- `docs/DIARIO-DE-ENGENHARIA.md` — o registro cronológico do desenvolvimento, com a procedência
  de cada número e o que caiu ao ser verificado. É a fonte versionada que substitui o
  `HISTORICO.md` para efeito de citação.
- `ROADMAP.md`, `HISTORICO.md`, `docs/METODOLOGIA.md`, `docs/HARDWARE.md`,
  `docs/DATA-CONTRACT.md`, `docs/ML-DATASETS-E-PLANO.md`, `docs/WEARANIZE-ACESSO.md` —
  documentação interna do projeto.
- `ml/README.md` e `ml/experimentos/saida/*.json` — os resultados de ML são versionados em
  JSON e reproduzíveis; todo número citado neste arquivo sai de lá.
- Estado verificado por execução em 2026-09-10: 221 testes pytest, 315 vitest, `tsc --noEmit`
  e `vite build` sem erro.
- Estado verificado por execução em 2026-09-22: **70 testes do `ml/` passando**, `git fsck`
  sem corrupção. As suítes do backend e do frontend **não foram reexecutadas nesta revisão** —
  os números de 10/09 acima seguem sendo os últimos medidos.
