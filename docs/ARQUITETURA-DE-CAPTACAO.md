# Arquitetura de captação: dispositivo, celular e modos de registro

**Data:** 2026-10-30 · **Itens:** `ARQ-01`, `ML-11`, `APP-02`, `APP-04`, `APP-09`, `DATA-06`,
`VIA-02` · **Estado:** registro de análise. ✅ **Uma decisão saiu dele em 30/10:** o
travesseiro usa a arquitetura **C2** (sono leve + FIFO), escolhida pelo autor depois do
`ML-11` e a confirmar com o orientador (`ARQ-01`, `RQ-01`). **Seguem abertos:** os modos de
registro (`ARQ-02`) e a redução para 3 features (`ML-12`).

> **Reprodutibilidade.**
>
> ```bash
> python3 scripts/estudo_cadencia.py --conferir                        # energia do ESP32
> ml/.venv/Scripts/python ml/experimentos/ml11_ablacao_features.py     # o que cada arquitetura entrega ao modelo
> ```
>
> O resultado do `ML-11` está em `ml/experimentos/saida/ml11_ablacao_features.json`. A análise
> de energia do ESP32 está em `docs/DECISAO-ARQ-01-CADENCIA.md` e não é repetida aqui.

---

## 1. As perguntas

O autor fez três perguntas, em 29 e 30/10:

1. **Todas as 8 features são necessárias, ou alguma sai sem grande perda?** Se o modelo vive
   com poucas features, e se essas poucas não exigem amostragem rápida, o ESP32 pode voltar ao
   despertar por movimento (WoM) e gastar o mínimo.
2. **O sono leve com FIFO só vale para o ESP32. Como fica o registro pelo celular?**
3. **Dá para oferecer mais de uma forma de registro, conforme o que o usuário pretende?**

E uma premissa que ele explicitou: **o celular não tem as mesmas limitações do ESP32.**

## 2. Hipóteses, declaradas antes de medir

| # | Hipótese | Como se testa |
|---|---|---|
| H1 | `enmo_desvio`, `enmo_max`, `mag_din_media` e `p_frac` são redundantes entre si (correlação de 0,74 a 0,96 na base de cabeça); tirar qualquer uma delas custa pouco | `ML-11`, tirar uma de cada vez |
| H2 | Poucas features (3 ou 4) chegam perto do kappa das 8 | `ML-11`, seleção progressiva |
| H3 | O que o WoM consegue entregar (evento binário por época + postura) perde muito em relação às 8 | `ML-11`, conjuntos por arquitetura, cercando o WoM entre um limite inferior e um superior |
| H4 | No celular, o gargalo não é energia, e sim **o sistema operacional** deixar o app rodar a noite toda | Pesquisa (§5) |
| H5 | Os modos de registro cabem no contrato de dados atual sem quebra | Leitura do `DATA-CONTRACT.md` (§6) |

## 3. Resultados do `ML-11`

**Como foi medido.** O pipeline do produto, sem mudança: normalização por sujeito, contexto de
±2 épocas, regressão logística balanceada, validação cruzada de 10 dobras por sujeito. Mudam só
as colunas que entram. Cada diferença é **pareada por dobra** contra as 8 features, com IC de
95 %.

**As bases:**
- **Wearanize, cabeça:** 92 pessoas, 87 795 épocas. É a mais próxima do travesseiro: sensor
  na testa.
- **Wearanize, pulso:** as mesmas 92 pessoas.
- **Newcastle:** 27 pessoas, pulso, a base mais fraca (κ de 0,25).

Rodou em 30/10, Windows 11, `ml/.venv`, em ~6 min. Rodou duas vezes, e os números saíram
idênticos.

**A régua:** o teto entre pontuadores humanos é κ = 0,612 (`ML-05`). Os maiores ganhos que o
projeto já mediu foram de +0,123 (suavização por HMM) e +0,075 (janela de contexto maior). Uma
diferença de 0,01 é pequena; uma de 0,07 é da ordem do maior ganho já obtido.

### 3.1 Tirar uma feature de cada vez

| Feature retirada | Δκ cabeça [IC 95 %] | Δκ pulso | Δκ Newcastle |
|---|---:|---:|---:|
| `enmo_media` | −0,003 [−0,013; +0,008] | +0,000 | −0,003 |
| `enmo_desvio` | +0,001 [−0,000; +0,002] | +0,002 | +0,001 |
| `enmo_max` | −0,000 [−0,004; +0,004] | +0,005 | +0,001 |
| **`mag_din_media`** | **−0,049 [−0,069; −0,028]** | **−0,011** [−0,021; −0,001] | +0,001 |
| `zcr` | +0,002 [−0,003; +0,007] | −0,003 | +0,001 |
| **`p_frac`** | **−0,017 [−0,033; −0,001]** | −0,001 | +0,004 |
| `inclinacao_rel` | −0,001 [−0,002; +0,001] | −0,001 | +0,030 (n.s.) |
| **`d_angulo`** | **−0,008 [−0,012; −0,004]** | +0,003 | **−0,024** [−0,034; −0,013] |

Em negrito, as perdas cujo IC não cruza o zero. **Cinco das oito saem sem perda detectável**
nas duas bases de 92 pessoas: as três `enmo_*`, `zcr` e `inclinacao_rel`. Duas delas são
redundantes com `mag_din_media` por correlação, na cabeça: `enmo_desvio` (0,88) e `enmo_max`
(0,74). A `enmo_media` não é (0,25) e ainda assim sai sem perda: a correlação não explica tudo,
e por isso se mediu em vez de argumentar.

### 3.2 Quantas bastam

A seleção progressiva, a partir de nenhuma feature, na cabeça:

| Conjunto | κ | Especificidade |
|---|---:|---:|
| `mag_din_media` | 0,371 | 0,586 |
| + `p_frac` | 0,399 | 0,668 |
| + `d_angulo` | **0,405** | 0,664 |
| + `enmo_media` | 0,408 | 0,667 |
| as 8 | 0,403 | 0,672 |

⚠️ Essa tabela é **otimista**: a seleção escolhe e mede nos mesmos dados. O teste honesto é
levar o conjunto escolhido na cabeça, **fixo**, a bases que não participaram da escolha:

| Base (fora da amostra) | 3 features da cabeça: Δκ contra as 8 | Δ especificidade |
|---|---:|---:|
| Pulso | +0,004 [−0,004; +0,011] | −0,011 |
| Newcastle | **+0,044 [+0,002; +0,086]** | −0,043 |

**Três features — `mag_din_media`, `p_frac` e `d_angulo` — empatam com as oito.** Fora da
amostra, o kappa empata ou sobe. A especificidade cai 1 a 4 pontos, e isso precisa entrar na
leitura: é a métrica fraca do projeto inteiro.

### 3.3 O que cada arquitetura entrega ao modelo

| Conjunto | Arquitetura | κ cabeça (% do teto) | Δκ cabeça [IC 95 %] | Δκ pulso | Δκ Newcastle |
|---|---|---:|---:|---:|---:|
| as 8 | **C2** (sono leve + FIFO) | **0,403 (66 %)** | — | — | — |
| 6 intra-época | o que o dispositivo calcula | 0,395 (65 %) | −0,008 | +0,005 | +0,007 |
| `p_frac` + postura | **WoM, limite superior** | 0,334 (55 %) | **−0,070 [−0,104; −0,035]** | −0,008 (n.s.) | +0,004 |
| evento + postura | **WoM, limite inferior** | 0,313 (51 %) | **−0,090 [−0,122; −0,058]** | **−0,039** | −0,001 |
| só evento | WoM sem leitura de gravidade | 0,306 (50 %) | **−0,097** | **−0,047** | −0,009 |
| só postura | uma leitura de gravidade por época | 0,305 (50 %) | **−0,098** | −0,017 | +0,003 |
| contagem clássica | actigrafia de 1 número | 0,379 (62 %) | −0,024 | −0,000 | (sem dado) |

**Na cabeça, que é o substituto mais próximo do travesseiro, o WoM perde de 0,07 a 0,10 de
kappa**: o modelo cai de 66 % para 50–55 % do teto humano. É uma perda da ordem do maior ganho
que o projeto já obteve, e os dois limites a mostram, então ela não depende do proxy exato. No
pulso, a perda é menor (0,01 a 0,05). No Newcastle não se detecta nada, mas lá nem o modelo das
8 passa de κ 0,25.

⚠️ **O que os proxies do WoM são** (cabeçalho do script): o limite inferior é "houve movimento
acima de 1,2 m/s² na época"; o superior é a fração de amostras acima desse limiar a 32 Hz, que um
WoM real não alcança. A postura usa a época inteira, o que é otimista para uma leitura só. O
circuito de detecção do MPU6050 não usa exatamente esse critério.

### 3.4 `ML-12`: a redução sobrevive a uma validação honesta? (30/10)

**Como foi medido** (`ml/experimentos/ml12_validacao_aninhada.py`). A seleção progressiva foi
refeita **dentro** de cada uma das 10 dobras externas, com 5 dobras internas que só veem os
sujeitos de treino. A regra de parada foi fixada antes de rodar: o menor conjunto a até 0,005
do melhor kappa interno. Depois, o mesmo com o Viterbi de 2 estados do produto (HMM). O
contexto de ±2 épocas passou a ser aplicado **por sujeito**. Comparação pareada contra as 8,
IC 95 %. ~11 min no total.

**Controle positivo:** uma coluna-isca que vaza o rótulo (`y` com 20 % de ruído) foi a
primeira escolha em **10 de 10** dobras. O instrumento acha uma feature informativa quando
ela existe.

**O que a seleção aninhada escolhe:**

| Base | Escolhida em quantas das 10 dobras | Tamanho |
|---|---|---|
| Cabeça | `mag_din_media` 10, `d_angulo` 10, `p_frac` 8, `enmo_media` 3 | 2 a 4 |
| Pulso | `mag_din_media` 10, `inclinacao_rel` 1 | 1 a 2 |
| Newcastle | `d_angulo` 10, `p_frac` 5, `mag_din_media` 1 | 1 a 2 |

`enmo_desvio`, `enmo_max` e `zcr` **nunca** foram escolhidas, em nenhuma base. O trio do
`ML-11` é a união do que cada base escolhe mais.

**Kappa e especificidade contra as 8** (Δ, IC 95 %; em negrito, IC que não cruza o zero):

| Base | Conjunto | Δκ | Δκ com HMM | Δ especificidade | Δ espec. com HMM |
|---|---|---:|---:|---:|---:|
| Cabeça | seleção aninhada | −0,010 [−0,023; +0,004] | −0,014 | **−0,028** | **−0,027** |
| Cabeça | trio do `ML-11` | +0,002 [−0,010; +0,015] | +0,003 | −0,008 | −0,013 |
| Pulso | seleção aninhada | **+0,015** [+0,009; +0,020] | +0,014 | **−0,025** | **−0,027** |
| Pulso | trio do `ML-11` | +0,003 [−0,004; +0,011] | +0,001 | **−0,012** | −0,016 |
| Newcastle | seleção aninhada | +0,035 [−0,000; +0,071] | **+0,073** | **−0,055** | **−0,046** |
| Newcastle | trio do `ML-11` | **+0,045** | **+0,071** | **−0,043** | **−0,044** |

Referência das 8: κ 0,402 na cabeça (0,531 com HMM), 0,373 no pulso (0,500), 0,250 no
Newcastle (0,300).

**Leitura:**

1. **No kappa, a redução sobrevive.** Nenhuma perda significativa em nenhuma base, com ou sem
   HMM. No pulso e no Newcastle o kappa até sobe.
2. **Na especificidade, não sai de graça.** Ela cai de 0,8 a 5,5 pontos, e a queda é
   significativa em 9 dos 12 casos. Especificidade é justamente a métrica fraca do projeto (a
   externa é 0,507, `ML-04`). O que o kappa ganha vem de mais sono acertado, à custa de
   vigília.
3. **Para o `DATA-07e`, a conta não fecha a favor de reduzir.** O ganho seria 8 B por época. A
   flash do `FW-08` já guarda 13,7 dias em resolução plena com o registro de 40 B. Pagar de 1 a
   4 pontos de especificidade por 8 B que não faltam é troca ruim. **A recomendação desta
   análise é manter as 6 features no dispositivo.**

**(d) O contexto atravessava a fronteira entre sujeitos.** Em todos os experimentos desde o
`ML-02`, `empilhar_contexto` rodou sobre a base concatenada, e a janela de ±2 épocas misturava
duas pessoas nas fronteiras. Medido: o contexto global dá κ **+0,001 a +0,002** acima do
contexto por sujeito (IC que não cruza o zero na cabeça e no Newcastle). É um vazamento real e
**desprezível**: duas épocas por fronteira, num universo de ~950 por sujeito, e uma ordem de
grandeza abaixo de qualquer efeito que o projeto reportou. Os resultados anteriores não mudam
de leitura.

## 4. O dispositivo ESP32: o que o `ML-11` muda na análise de energia

1. **A escolha entre WoM e features continua real, e agora tem preço medido.** O WoM economiza
   corrente (`DECISAO-ARQ-01-CADENCIA.md`: 1,91 contra 5,31 mA, só nos chips) e custa 0,07 a 0,10
   de kappa no substituto mais próximo do travesseiro.
2. **Reduzir as features não economiza energia na C2.** Lá, o custo é manter o sensor amostrando
   e o rádio, não o cálculo. Calcular duas features ou seis custa o mesmo.
3. **Mas sai justamente a feature mais exigente com a taxa.** A `zcr` (cruzamentos por zero) é a
   que mais depende de amostragem rápida e banda larga, e ela não faz falta. As três que ficam
   dependem da média e do limiar da aceleração dinâmica e da direção da gravidade. **Hipótese,
   não medida:** elas devem tolerar o DLPF de 10 Hz, o que tornaria viável a variante C2-LP
   (40 Hz em baixo consumo). Ganho estimado: 0,5 mA, menos que a incerteza da placa.
4. **O registro de época encolheria.** Hoje o dispositivo envia 6 features em 16 bits (12 B) mais
   a gravidade (6 B). Com 2 features no dispositivo (`mag_din_media` e `p_frac`; o `d_angulo` é
   derivado no servidor a partir da gravidade), seriam 4 B mais 6 B: **8 B a menos por época**.
   É aritmética sobre o `VetorDeFeatures`. Mudaria o contrato v2.5.1, o firmware e o dourado; é
   o `DATA-07e` que decide o layout.
5. **Uma terceira saída, só como hipótese:** um WoM que, além do evento, amostrasse em rajadas
   curtas para estimar a `mag_din_media`. Fica entre A e C2 em energia e em informação, e nada
   aqui a mede.

## 5. O celular

### 5.1 O que existe hoje

A rota `/coletar` (`APP-01`, em produção desde agosto) lê o acelerômetro pelo navegador
(`devicemotion`, ~60 Hz), resume cada época pelo **pico da magnitude** e envia pela mesma API do
travesseiro (`metodo: "pico-da-magnitude"`). Limitação declarada no próprio código
(`frontend/src/hooks/useColeta.ts`): **o navegador para o sensor quando a tela bloqueia ou a aba
vai para o fundo.** O *Wake Lock* segura a tela acesa, à custa de bateria e calor. A coleta
serve para **sessões de minutos** (bancada, `VIA-01`, `VIA-02`), não para uma noite, e a tela
diz isso ao usuário.

### 5.2 O que muda em relação ao ESP32

| | ESP32 (travesseiro) | Celular |
|---|---|---|
| Energia | **o problema central**: bateria pequena, sem tomada no travesseiro | quase irrelevante: o celular dorme na tomada |
| Taxa de amostragem | limitada pelo modo do sensor e pelo custo de acordar | 50 Hz é o padrão do sistema; até ~100 Hz para apps de terceiros no iOS |
| CPU para as features | cabe, com folga medida no host (`DATA-07b`) | sobra |
| O que limita a noite inteira | a bateria | **o sistema operacional**: o navegador corta o sensor; o app nativo depende de serviço em primeiro plano (Android) ou de uma API específica (iOS) |
| Onde fica o sensor | dentro do travesseiro, sob a cabeça | sobre o colchão, longe da cabeça, compartilhado com quem dorme ao lado |
| Mecanismo de economia | FIFO do MPU + sono leve (`DECISAO-ARQ-01-CADENCIA.md`) | o mesmo, em hardware: o *sensor hub* do celular acumula amostras numa FIFO e acorda o processador em lote (*batching*) |

**A arquitetura C2 do ESP32 é a mesma ideia que os celulares já fazem em hardware.** O Android
expõe isso como *batching* (`registerListener` com `maxReportLatencyUs`). A documentação do AOSP
diz que o lote poupa energia porque o processador não acorda a cada evento, e que FIFOs maiores
poupam mais.

### 5.3 As três rotas para o celular registrar a noite

| Rota | Noite inteira? | Features? | Custo | Estado |
|---|---|---|---|---|
| **Navegador (PWA)**, a de hoje | **não**: o sensor para com a tela bloqueada; com *Wake Lock*, tela acesa a noite toda | dá para calcular as 8 no navegador | já existe | em produção, para minutos |
| **Android nativo** com serviço em primeiro plano e *batching* | **sim**, com ressalva: fabricantes (Samsung, Xiaomi, OPPO) matam apps em segundo plano mesmo com exceção de bateria | sim, a 50 Hz | um app nativo inteiro | `APP-02`, ⚪, pós-banca |
| **iOS** | **não verificado**. `CMSensorRecorder` grava a 50 Hz em segundo plano, com janela relatada de 12 h, mas a documentação e os fóruns falam sobretudo do Apple Watch | sim, se a rota funcionar no iPhone | app nativo + conta de desenvolvedor | `APP-04`, investigação |

### 5.4 O que a literatura diz do celular sobre a cama

- **Sleep Time (iPhone) contra polissonografia** (J Clin Sleep Med, 2015, 20 adultos, celular
  sobre a cama): a eficiência do sono bateu, mas sono leve, sono profundo e latência não. O app
  **detectou bem o sono e mal a vigília**, e acertou 45,9 % do estadiamento.
- **Celular contra actígrafo** (2012, adultos saudáveis, relatado em resumo de busca; os
  repositórios do artigo recusaram acesso, então **não conferido na fonte**): concordância
  razoável em tempo total de sono, vigília após o início do sono e eficiência; não na latência.
- **Quatro apps contra polissonografia** (2019): dois deles, incluindo o Sleep Cycle, não foram
  confiáveis nem para sono × vigília; nenhum detectou REM.
- **Vigília quieta:** como todo acelerômetro, o celular confunde vigília imóvel com sono. É o
  mesmo limite físico que o projeto já mede como especificidade baixa (`RESULTADOS-TCC.md`).
- **Lacuna:** uma revisão de 2021 registra que faltam dados de validação do celular para sono ×
  vigília, e não há estudo grande e recente com o celular deitado no colchão.

**Consequência para o projeto:** o celular sobre o colchão é uma linha de base plausível, não um
instrumento validado. Isso reforça o que o `ROADMAP.md` (P4) já dizia: o celular é o **grupo de
controle** contra o qual o travesseiro prova valor, e o `VIA-02` (os dois gravando ao mesmo
tempo) é o que mede a diferença.

## 6. Modos de registro: mais de uma opção para o usuário

### 6.1 A proposta

O usuário escolhe pelo que pretende, não pela tecnologia:

| Modo | Para quem | Instrumento e arquitetura | O que registra | O que o usuário ganha | O que perde |
|---|---|---|---|---|---|
| **Travesseiro, bateria máxima** | quer só um diário de agitação noturna, sem recarregar toda semana | ESP32, arquitetura A (WoM) | eventos de movimento por época (+ postura, se a variante com leitura de gravidade for implementada) | a maior autonomia | o modelo de sono × vigília (ver §3) |
| **Travesseiro, análise completa** | quer a estimativa de sono × vigília | ESP32, arquitetura C2 (sono leve + FIFO) | as 6 features por época; o servidor deriva as outras 2 | o modelo inteiro | autonomia menor (§4) |
| **Celular, teste rápido** | quer experimentar sem comprar o sensor, ou calibrar | navegador (`/coletar`) | pico por época, ou as features, durante minutos | começar agora, de graça | não registra uma noite |
| **Celular, noite inteira** | não tem o sensor | app nativo (Android primeiro) | as 8 features por época, a 50 Hz | o modelo, sem hardware | precisa do app nativo (pós-banca) e de tomada; mede pelo colchão, não pela cabeça |

### 6.2 O que já sustenta isso, e o que falta

**Já existe** (H5, lida no `DATA-CONTRACT.md` e no banco):

- `devices.tipo` (`travesseiro` | `celular`);
- o campo `metodo` em cada leitura, que diz **como** a época foi resumida (é como o modo
  viajaria);
- o campo opcional `f` do contrato v2.5.1, para as features;
- o painel recortado por dispositivo, que avisa quando mistura instrumentos (`DASH-05`).

**Falta:**

1. **O limiar por instrumento (`DATA-06`).** Hoje 1,2 m/s² vale para todos, e o celular no
   colchão não mede o que o travesseiro mede.
2. **Modelos por instrumento.** O modelo foi treinado em sensores presos ao corpo (cabeça e
   pulso). Nem o travesseiro nem o celular no colchão são isso (`ML-DATASETS-E-PLANO.md`,
   "Cabeça ≠ travesseiro"). Cada instrumento precisa de pelo menos uma recalibração, e é o
   `VIA-02` que dá o primeiro número.
3. **Continuidade quando o usuário troca de instrumento (`APP-09`).** Noites de instrumentos
   diferentes não são comparáveis sem aviso.
4. **No ESP32, o modo como configuração.** Os dois firmwares (A e C2) podem conviver na mesma
   placa, com o modo escolhido no painel e entregue ao dispositivo. Isso dobra o caminho a
   testar no `FW-07`. **Não é recomendado antes da banca:** um modo só, bem medido, defende
   melhor que dois pela metade.

### 6.3 O que isso faz com a pergunta de pesquisa

A RQ fala de **um** dispositivo embarcado. Os modos do celular não entram nela: entram como
linha de base (o `VIA-02`) e como trabalho futuro. Os dois modos do travesseiro entram, e é
exatamente a escolha que o `ARQ-01` (a) pede ao autor e ao orientador. Ter os dois **como
opção do usuário** é uma resposta possível ("o dispositivo oferece economia máxima ou análise
completa"), mas aumenta o que é preciso validar.

## 7. Conclusões

| Hipótese | Resultado |
|---|---|
| H1, redundância | **Em parte.** `enmo_desvio` e `enmo_max` saem sem perda; `mag_din_media` e `p_frac`, não (−0,049 e −0,017 na cabeça). A redundância é assimétrica: o grupo carrega informação, e quem a carrega é `mag_din_media`. Fora do grupo, `enmo_media`, `zcr` e `inclinacao_rel` também saem sem perda |
| H2, poucas bastam | **Confirmada, com ressalva.** Três features (`mag_din_media`, `p_frac`, `d_angulo`) empatam com as oito fora da amostra; a especificidade cai 1 a 4 pontos |
| H3, o WoM perde muito | **Confirmada na cabeça** (−0,07 a −0,10 de κ, entre os dois limites); menor no pulso; indetectável no Newcastle, cujo modelo já é fraco |
| H4, o celular é limitado pelo sistema, não pela energia | **Sustentada pela pesquisa**, não testada aqui |
| H5, o contrato comporta os modos | **Sustentada pela leitura**: `devices.tipo`, `metodo` e `f` já existem |

**O que isso diz sobre a escolha do autor:**

1. **A inclinação pelo sono leve com FIFO se sustenta com número.** No substituto mais próximo do
   travesseiro, o WoM custa de 0,07 a 0,10 de kappa, e a C2 custa 3,4 mA a mais (só nos chips;
   menos com a placa e o lote).
2. **"Todas as features são necessárias?" Não.** Três bastam, e a mais exigente com a taxa
   (`zcr`) não está entre elas. Isso simplifica o firmware e o registro, mas **não muda a
   energia**: a C2 continua precisando amostrar a época inteira.
3. **O celular entra como outro instrumento, não como outra arquitetura do mesmo dispositivo.**
   No celular, a energia não é o problema; o sistema operacional é. Navegador serve para minutos;
   Android nativo serve para a noite; iOS não está verificado.
4. **Os modos de registro são viáveis no contrato de hoje**, e cada instrumento novo pede limiar e
   recalibração do modelo (`DATA-06`, `VIA-02`).

**O que fica aberto:**

- ✏️ *30/10, `ML-12` (§3.4):* a redução para 3 features **sobrevive no kappa** a uma validação
  aninhada e ao HMM, mas **custa de 1 a 5 pontos de especificidade**. A recomendação passou a
  ser **manter as 6 features no dispositivo**: o ganho de 8 B por época não paga a perda. O dado
  do travesseiro (`ML-12` (c)) segue aberto.
- Que modos oferecer ao usuário, e se o travesseiro terá um ou dois (`ARQ-02`).
- A escolha do `ARQ-01` (a), com o orientador.

## 8. O que este documento não decide

- **Qual arquitetura o travesseiro usa.** É o `ARQ-01` (a), do autor com o orientador (`RQ-01`).
- **Se o app nativo entra antes da banca.** O `ROADMAP.md` (P4) diz que não; nada aqui muda isso.
- **O limiar e o modelo do celular.** Dependem do `VIA-02`, que depende da solda.

## 9. Fontes externas

- AOSP, *Sensor batching*:
  `https://android.googlesource.com/platform/docs/source.android.com/+/1d734fa/src/devices/sensors/batching.jd`.
- Apple Developer Forums, taxas de acelerômetro para apps de terceiros e `CMSensorRecorder` a
  50 Hz: `https://developer.apple.com/forums/thread/813136`.
- Fórum de desenvolvedores sobre fabricantes que matam apps em segundo plano:
  `https://dev.to/stoyan_minchev/what-android-oems-do-to-background-apps-and-the-11-layers-i-built-to-survive-it-28bb`.
- *(Not so) Smart sleep tracking through the phone*, 2019, polissonografia com quatro apps:
  `https://pubmed.ncbi.nlm.nih.gov/31674096`.
- Sleep Time contra polissonografia, J Clin Sleep Med 11(7):709–715, 2015:
  `https://pmc.ncbi.nlm.nih.gov/articles/PMC4481053`.
- Revisão de 2021 sobre a lacuna de validação: `https://www.frontiersin.org/journals/digital-health/articles/10.3389/fdgth.2021.721919/full`.
- *Wake Lock* e o ciclo de vida da página: `https://whatpwacando.today/wake-lock`.

⚠️ As fontes sobre Android e iOS são em parte fóruns e relatos de desenvolvedores, não
documentação oficial. Elas sustentam hipóteses (`APP-02`, `APP-04`), não afirmações.
