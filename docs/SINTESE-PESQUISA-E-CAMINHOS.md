# Smart Dormio — síntese da pesquisa e caminhos implementáveis

> **Consolidado em 2026-09-10.** Amarra num documento só o que saiu de duas sessões de
> trabalho: o levantamento de bases públicas e o §0 sobre o que o hardware sustenta
> (`ML-DATASETS-E-PLANO.md`), a seção de limitações redigida (`LIMITACOES-TCC.md`), o
> backlog por dependência (`BACKLOG-COMPLETO.md`) e a **verificação de referências**, que
> corrigiu quatro coisas e mudou o argumento em três delas.
>
> **Para que serve:** responder, num lugar só, às três perguntas que a banca vai fazer —
> *o que vocês estudaram?*, *o que concluíram?*, *e o que dá para fazer com isso?*
>
> **O que este documento NÃO é:** não substitui o `ML-DATASETS-E-PLANO.md` (que tem o
> detalhe de cada base e o plano de execução), nem o `BACKLOG-COMPLETO.md` (que tem o item
> a item). Ele é a camada de cima.

**Índice:** [§1 O que foi estudado](#1-o-que-foi-estudado) · [§2 Conclusões](#2-conclusões)
· [§3 Caminhos implementáveis](#3-caminhos-implementáveis) · [§4 Recomendação](#4-recomendação)

---

## 1. O que foi estudado

### 1.1 O percurso, e por que ele foi nesta ordem

A investigação não começou pela pergunta "qual dataset usar?". Começou uma camada acima,
porque essa pergunta estava mal formulada. O percurso real foi:

```
  ┌────────────────────────────────────────────────────────────────────┐
  │ 1. A PERGUNTA DE HARDWARE                                          │
  │    "Só com um MPU6050 dá para monitorar sono com base científica?" │
  │    → exigia número e fonte, não opinião                            │
  └───────────────────────────┬────────────────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────────────────┐
  │ 2. O TETO DA AFIRMAÇÃO                                             │
  │    O que a literatura de actigrafia de fato mede, com que          │
  │    desempenho, em que população, e com que viés conhecido          │
  └───────────────────────────┬────────────────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────────────────┐
  │ 3. SÓ ENTÃO: QUE DATASET SERVE                                     │
  │    Porque o rótulo que o modelo precisa depende do que ele vai     │
  │    afirmar — e isso ficou decidido no passo 2                      │
  └───────────────────────────┬────────────────────────────────────────┘
                              ▼
  ┌────────────────────────────────────────────────────────────────────┐
  │ 4. VERIFICAÇÃO DAS REFERÊNCIAS                                     │
  │    Autoria, ano, veículo, DOI e os números, na fonte.              │
  │    → achou 1 autoria falsa e 3 afirmações que a fonte não sustenta │
  └────────────────────────────────────────────────────────────────────┘
```

O passo 4 é o que separa este trabalho de um levantamento comum, e é o que o
`METODOLOGIA.md` exige em uma linha: *sugestão de busca ≠ citação*. Sem ele, o documento
teria entrado no TCC com um autor inventado.

### 1.2 As fontes verificadas, e o que cada uma sustenta

Todas com **autoria, ano, veículo, volume, páginas e DOI conferidos na fonte** (PubMed /
Europe PMC / texto completo) em 2026-09-10. A lista formatada para ABNT está em
`ML-DATASETS-E-PLANO.md` → "Fontes".

| # | Fonte | O que ela sustenta | Onde entra no Dormio |
|:-:|---|---|---|
| 1 | **Walch et al. (2019)** · *SLEEP* 42(12) zsz180 | Sono×vigília com movimento + FC + proxy circadiano: **93% sens · 59,6% espec · 90% acur**. Vigília/NREM/REM: **~72%** | Prova que **estadiamento depende de FC**, não de movimento. É o §0.4 inteiro. Também é a 3ª coorte de teste |
| 2 | **Ode et al. (2022)** · *iScience* 25(2) 103727 | **Só aceleração bruta**, features de *jerk*: **96,13 ± 5,61% sens · 80,18 ± 12,71% espec · 91,71 ± 4,80% acur** | É o **teto realista** do Dormio: o melhor que aceleração pura entrega. E o ±12,7 mostra que a média esconde os casos ruins |
| 3 | **Li, Halaki & Chow (2025)** · *Sensors* 25(10) 3040 | Actígrafo **clínico** contra PSG: **94,8% sens · 33,1% espec · 87,3% acur**; TST +18,6 min; **acurácia declina com a severidade do distúrbio** | É o **piso**. Mostra que nem grau clínico salva a especificidade |
| 4 | **Conley et al. (2019)** · *Sleep Med Rev* 46:151–160 | Meta-análise, 96 estudos, 4 134 participantes. Agrupado (49 estudos, n=1 582): **83% sens · 51% espec · 82% acur**. Viés: significativo em crônicos, **não** significativo em saudáveis | É o **número genérico citável** de "actigrafia de referência" — o que faltava. E é a base do argumento do viés diferencial |
| 5 | **Paquet, Kawinska & Carrier (2007)** · *SLEEP* 30(10):1362–1369 | Superestimação de TST em insones: **14 a 60 min**. ⚠️ É **síntese secundária** de seis primários | Magnitude do viés no caso extremo. Citar como síntese, nunca como medição |
| 6 | **Yuan, Hill, Kyle & Doherty (2024)** · *J Sleep Res* 33(4) e14143 | Actigrafia mede **movimento de membro periférico**, com "capacidade limitada de inferir os estágios do sono, pela ausência de sinais fisiológicos" | Fundamenta "não fazemos estadiamento" como **conclusão citada**, não como desculpa |
| 7 | **Meredith-Jones et al. (2024)** · *IJBNPA* 21(1) art. 40 (+ errata art. 62) | 137 crianças (8–16 a.): acurácia **>80% no pulso** vs. **<80%** perto do centro de massa. **Sensibilidade maior no centro de massa; especificidade melhor no pulso** | A notícia desconfortável: é razoável esperar que o travesseiro tenha especificidade **pior** que o pulso |
| 8 | **Razjouyan et al. (2017)** · *JCSM* 13(11):1301–1310 | Sensor no tórax com **postura + aceleração**: acurácia **85,8%** vs. **79,8%** do pulso (**+6 pts**); correlação com PSG sobe de *r*=0,0–0,3 para 0,4–0,8 | A **compensação**: postura recupera o que a posição central perde. Justifica `angulo_z` e `d_angulo` nas features |
| 9 | **Leitão et al. (2018)** · *Sensors* 18(10) art. 3441 | BCG/SCG: energia <30 Hz, amplitude ~10 mg pico a pico. Acelerômetros comerciais **>98 µg/√Hz** → ~5 bits, "compromete fortemente a análise" | Encerra a discussão sobre extrair batimento cardíaco do travesseiro |
| 10 | **TDK InvenSense (2013)** · PS-MPU-6000A-00 Rev. 3.4, §6.2 | MPU-6050: **400 µg/√Hz**, típico, **a 10 Hz, AFS_SEL=0 (±2 g), ODR=1 kHz** | O número do nosso componente, com a condição de medição — que é o que faz a comparação valer |
| 11 | **Lee et al. (2025)** · *JCSM* 21(3):573–582 | 24 estudos, 798 participantes. Dispositivos de consumo vs. PSG: TST **−16,9 min**, eficiência **−4,7%**, WASO **+13,3 min** | 🔍 **Direção oposta à da actigrafia de pesquisa.** Muda a estratégia de validação — ver §2.5 |

### 1.3 As bases públicas avaliadas

Nove bases foram examinadas contra um critério que o levantamento anterior não tinha:
**o dataset entrega aceleração bruta ou contagens proprietárias?** Essa coluna decide tudo,
porque não existe função pública que converta aceleração de um MPU6050 em *activity counts*
de um Actiwatch.

| Base | Bruto? | Rótulo PSG? | Veredito | Papel no projeto |
|---|:---:|:---:|:---:|---|
| **Wearanize+** (130 · cabeça + pulso + coxa) | ✅ | ✅ manual AASM | 🥇 | **Principal.** Único com acelerômetro **na cabeça** com rótulo de PSG. Permite medir o salto entre posições |
| **Newcastle 2015** (28 · dois pulsos, CC-BY) | ✅ | ✅ | 🥈 | **Ponto de partida imediato.** Baixa hoje, sem DUA |
| **Walch 2019** (31 · Apple Watch) | ✅ | ✅ 5 classes | 🥉 | **Teste externo.** Já endossado pelo orientador |
| DREAMT (100 · Empatica E4) | ✅ | ✅ | ⚠️ | População de laboratório de apneia (IMC 33,7; AHI 22,1) — 2º *domain shift* |
| MESA / SHHS (2 000+) | ❌ **counts** | ✅ | ❌ | **A armadilha.** Só referência populacional citável |
| BCG piezo (32 · 212 noites) | ⚠️ outro transdutor | ❌ | ❌ | Citação na fundamentação: não-contato na cama capta sinal fisiológico |
| MMASH · UK Biobank · Sleep-EDF | vários | ❌ / sem accel | ❌ | Fora |

**A conclusão de construto, dita com todas as letras:** *não existe dataset público de
acelerômetro dentro de um travesseiro com rótulo de sono.* Isso é limitação — e é também a
justificativa da originalidade do trabalho.

### 1.4 A grandeza é a mesma? Sim — e isso foi verificado

A pergunta que decide se o projeto é viável não é "há dados?", é **"os dados são
comensuráveis com o que o MPU6050 mede?"**. A resposta é sim para as três bases
recomendadas, e é não para o MESA — e a diferença é de **natureza**, não de grau:

- **Aceleração é grandeza física.** Tem dimensão (L·T⁻²) e unidade SI. Qualquer acelerômetro
  mede a mesma coisa; as diferenças são de **fidelidade**, não de **objeto**.
- ***Activity counts* não são grandeza física.** Não têm unidade. São a saída de um algoritmo
  proprietário não publicado. **Não existe função que converta aceleração em counts.**

As especificações de cada sensor foram conferidas em folha de dados, manual do fabricante ou
artigo do dataset — a tabela completa, com a fonte de cada célula, está em
`ML-DATASETS-E-PLANO.md` §2.1. O resumo:

| Sensor | Faixa | Bits | Resolução | Taxa |
|---|:---:|:---:|:---:|:---:|
| **MPU6050** (Dormio) | ✅ ±8 g | ✅ 16 | ✅ **0,244 mg/LSB** | ✅ ≥42 Hz (a definir) |
| **GENEActiv** (Newcastle) | ✅ ±8 g | ✅ 12 | ✅ 3,9 mg/LSB | ✅ 85,70 Hz |
| **Empatica E4** (Wearanize+, pulso) | ✅ ±2 g | ✅ 8 | ✅ **15,6 mg/LSB** | ✅ 32 Hz |
| **Apple Watch** (Walch) | ⛔ Apple não publica | ⛔ | ⛔ | ✅ ~50 Hz |
| **Zmax Lite** (Wearanize+, cabeça) | ⛔ · 📄 no EDF | ⛔ · 📄 | ⛔ · 📄 | 🟡 256 Hz · 📄 |
| **ActivPAL** (Wearanize+, coxa) | ⛔ modelo não documentado | ⛔ | ⛔ | ✅ 20 Hz |
| **Actiwatch** (MESA) | ❌ | ❌ | ❌ | ❌ counts / 30 s |

<sub>✅ confirmado em fonte primária · 🟡 provável, com ressalva · ⛔ indisponível
publicamente (busca documentada no §2.1) · 📄 não publicado em texto, mas legível no
cabeçalho EDF do próprio dado · ❌ não aplicável (não é grandeza física).</sub>

**Nenhuma célula ⛔ sustenta conclusão alguma.** As três conclusões que dependem desta tabela
— a comensurabilidade das três bases, o fator de 64× em resolução, e o "MPU6050 não é o elo
fraco" — apoiam-se exclusivamente em células ✅.

**O achado que sai daí, e é contra-intuitivo:** o MPU6050 **não é o elo fraco da cadeia**.
Em resolução, ele é **64× mais fino** que o E4 — que é o sensor de pulso do Wearanize+. Pela
derivação do §2.2 daquele documento, o piso de ruído no `ENMO_media` é de ~0,64 mg para o
MPU6050 contra ≥1,95 mg para o E4. **O sensor barato do TCC tem especificação melhor que a
do wearable de pesquisa contra o qual ele seria comparado.**

Isso desloca a preocupação para onde ela de fato pertence: **não é o sensor, é o
acoplamento** (§2.3 e o `VIA-01`).

---

## 2. Conclusões

### 2.1 A afirmação máxima honesta

Tudo converge para uma frase, e é esta que o trabalho pode defender sem exposição:

> **O dispositivo registra eventos de movimento durante o repouso de forma não invasiva e, a
> partir deles, estima o período de repouso e sua fragmentação, com desempenho da ordem do
> que a literatura de actigrafia reporta — reconhecidamente limitado na discriminação de
> vigília quieta, com tendência conhecida a superestimar o tempo de sono, e sem qualquer
> estadiamento de sono.**

Repare no que ela **não** faz: não promete estágios, não promete diagnóstico, não promete
nota de qualidade, e **declara o viés em vez de escondê-lo**.

### 2.2 O que ficou estabelecido sobre a capacidade

| Pergunta | O acelerômetro sustenta? | Evidência |
|---|:---:|---|
| Houve movimento nesta época? | ✅ | É o que o projeto já faz |
| Dormindo ou acordado? | ⚠️ **com ressalva grave** | Sens. alta e estável; **espec. entre 33% e 80%** (fontes 2, 3, 4) |
| Início/fim do período de repouso? | ✅ | Métrica mais confiável da actigrafia |
| Quantos despertares, quão fragmentada? | ✅ | Movimento é o sinal direto |
| REM, N1, N2, N3? | ❌ | Fontes 1 e 6. É **física**, não algoritmo |
| Apneia, ronco, distúrbio clínico? | ❌ | Fora do escopo e do hardware |

### 2.3 Os três limites que são físicos, não de implementação

**(a) Vigília quieta é indistinguível de sono.** Um corpo desperto, deitado e imóvel produz
o mesmo sinal que um corpo adormecido. Nenhum modelo conserta o que o sinal não contém. É
por isso que a especificidade oscila de 33% a 80% na literatura inteira — e o corolário é
incômodo: *quem mais precisa da medida (insônia, sono fragmentado) recebe a medida pior.*

**(b) REM e N3 são ambos estados quietos.** Para um acelerômetro, são o mesmo estado. O que
os wearables usam para separá-los não é movimento, é o sistema autonômico via variabilidade
da frequência cardíaca (fonte 1). **O Dormio não mede FC — e não pode.**

**(c) BCG está fora de alcance, e não é questão de esforço.** PPG exige contato óptico com
tecido perfundido; não atravessa fronha. A alternativa mecânica exigiria um acelerômetro
com ruído ~4× menor que os comerciais que a própria literatura diz já comprometerem a
análise (fontes 9 e 10). Trocar transdutor + posição + cadeia de processamento cardíaco não
é item de roadmap — é outro TCC.

### 2.4 A conta que a banca vai fazer, e que é melhor fazer antes

Numa noite de PSG a maioria das épocas é sono. Então o classificador degenerado **"sempre
dormindo"** — que ignora o sensor por completo — já acerta a fração de sono da noite.

Dá para recuperar essa fração dos próprios números publicados, porque
`acurácia = p·sens + (1−p)·espec`. Isolando `p`:

| Estudo | `p` implicado | "Sempre dormindo" acertaria | Acurácia publicada | Diferença |
|---|:---:|:---:|:---:|:---:|
| Li et al., 2025 | 87,8% | **87,8%** | 87,3% | **−0,5 pt** |
| Walch et al., 2019 | 91,0% | **91,0%** | 90,0% | **−1,0 pt** |

**Nos dois casos, o classificador que não olha o sensor tem acurácia ligeiramente maior que
o método publicado.** Dois estudos independentes, populações e aparelhos diferentes, mesmo
resultado. *(Esta derivação é nossa; a identidade é aritmética exata, não aproximação.)*

Isso **não** significa que actigrafia seja inútil — o classificador trivial não produz WASO,
latência, despertares nem fragmentação, que são as saídas úteis. O que a conta mata é a
**acurácia como número de manchete**. Um TCC que publicar "89% de acurácia" sem o baseline
ao lado está publicando um número que a banca refuta em trinta segundos.

**Consequência operacional:** o `ML-02` não é formalidade metodológica. É o primeiro
resultado a medir, e provavelmente será competitivo.

### 2.5 As quatro correções — e o que cada uma mudou no argumento

Esta seção é **rastro metodológico**. Vale a pena no TCC, porque mostra que o trabalho
verificou as próprias fontes em vez de confiar na primeira leitura.

---

**🔧 Correção 1 — a autoria falsa.**

- **O que estava escrito:** o estudo do MotionWatch8 atribuído a *"Rocha et al., 2025"*.
- **O que a fonte diz:** **Li, X.; Halaki, M.; Chow, C. M.** (2025), *Sensors* 25(10):3040.
- **Como o erro aconteceu:** inferência, não leitura. E há uma pista forense — **Rocha, L. A.**
  é o último autor do artigo de sismocardiografia da *Sensors* de 2018 (fonte 9). Duas
  referências foram cruzadas.
- **O que mudou na conclusão:** **nada** no conteúdo — os números 94,8 / 33,1 / 87,3 estavam
  certos e a população também. Mudou a **integridade da referência**. Um sobrenome
  inventado numa lista ABNT é falha de honestidade acadêmica, e a banca não distingue
  descuido de fabricação.
- **A lição operacional:** a sessão anterior *sabia* que não tinha confirmado e citou pelo
  título — o que foi a decisão certa. O erro foi ter escrito o sobrenome antes disso.

---

**🔧 Correção 2 — os 11,2 min que não são significativos.**

- **O que estava escrito:** "superestimação de **+11,2 min** em adultos saudáveis e **+22,4
  min** em adultos com condições crônicas" — as duas apresentadas como achados equivalentes.
- **O que a fonte diz:** em saudáveis, Conley et al. descrevem literalmente *"a
  non-statistically significant trend"*, com IC 95% de **−3,98 a +26,44 min** — compatível
  com zero. Em crônicos, +22,42 min com IC 11,92–32,91: **significativo**.
- **O que mudou na conclusão:** o argumento **ficou mais forte, não mais fraco.** A versão
  antiga dizia "actigrafia superestima sono em todo mundo, um pouco mais nos doentes". A
  versão correta diz: **o viés só é estatisticamente detectável em quem dorme mal.** Isso é
  exatamente o corolário do §2.3(a) — e agora com evidência que o sustenta, em vez de um
  número que a diluía.
- **Risco de banca evitado:** apresentar os 11,2 min como achado é atribuir a Conley et al.
  uma conclusão que eles explicitamente recusam. Um avaliador que abrir o artigo encontra
  isso na primeira página.

---

**🔧 Correção 3 — os 6,5 µg/√Hz que não eram requisito.**

- **O que estava escrito:** "Aquisição de BCG/SCG **exige** acelerômetros com densidade de
  ruído abaixo de ~6,5 µg/√Hz."
- **O que a fonte diz:** Leitão et al. **não enunciam esse requisito**. Os 6,5 µg/√Hz são a
  especificação do acelerômetro **que os próprios autores projetaram**. O que o artigo
  sustenta é outra coisa: sinais de ~10 mg pico a pico abaixo de 30 Hz; acelerômetros
  comerciais **acima de 98 µg/√Hz** produzem ~0,54 mg de resolução — "roughly a 5-bit
  resolution […] which strongly compromises the signal analysis".
- **O que mudou na conclusão:** a conclusão prática é **a mesma** (BCG está fora de
  alcance), mas a **cadeia de evidência mudou de lugar**. Antes: "400 é 60× o requisito de
  6,5". Agora: "400 é ~4× o valor dos acelerômetros comerciais que o próprio artigo diz já
  comprometerem a análise, e ~62× o do sensor dedicado". A segunda formulação é defensável
  linha a linha; a primeira colocava na boca dos autores um limiar que eles não publicaram.
- **Por que isso importa mais do que parece:** era a única afirmação do documento em que um
  número foi transformado em **norma técnica**. É o tipo de erro que passa despercebido
  justamente porque a conclusão está certa.

---

**🔧 Correção 4 — as duas citações que não existem.**

- **O que estava escrito:** duas frases, entre aspas, atribuídas a fontes específicas.
- **O que a fonte diz:**
  1. A citação atribuída à **revisão de estadiamento** — sobre o método confundir vigília
     quieta com sono — **não foi localizada** no artigo publicado. O documento citava o
     **preprint** de medRxiv; a versão revisada por pares é Yuan et al. (2024), *J Sleep
     Res*, e traz outra formulação, que diz o mesmo com mais precisão e **foi conferida
     palavra por palavra no texto completo**.
  2. A citação atribuída ao **estudo pediátrico** — que **trocava sensibilidade e
     especificidade de lugar** ao justificar a vantagem do punho — **não foi localizada**, e
     contradiz o artigo: nele, é perto do centro de massa que a sensibilidade é maior; a
     vantagem do punho está na **especificidade**.
- **O que mudou na conclusão:** no caso (2), mudou de verdade. A justificativa da §0.5 era
  "o pulso ganha por sensibilidade". A justificativa correta é "**o pulso ganha por
  especificidade**" — que é precisamente a métrica em jogo para o Dormio. O argumento
  sobrevive e fica **mais afiado**, porque agora aponta para o número certo.
- **Estado (fechado em 2026-09-10):** ✅ as duas frases **não existem mais em nenhum
  documento** — varredura dos quatro arquivos, zero ocorrências. E **não são reproduzidas
  nem nestes avisos**: um alerta que repete o texto errado entre aspas vira ele próprio a
  fonte do erro, porque a frase fica disponível para ser copiada de volta. A redação
  anterior está no **histórico do git**, que é o lugar certo para auditoria.
- **A lição:** aspas são a forma de citação mais perigosa. Um número errado é um erro; uma
  frase entre aspas que o autor não escreveu é atribuição falsa. E a correção de uma
  atribuição falsa não deve reimprimir a frase falsa.

---

**Resumo do que as correções fizeram com o trabalho:** nenhuma delas derrubou uma
conclusão. Três delas **fortaleceram** o argumento, porque a versão verificada é mais
específica que a versão inferida. Isso não é sorte — é o padrão quando se vai à fonte.

### 2.6 O achado da última rodada: cuidado com o wearable de consumo como referência

O `METODOLOGIA.md` lista, como referência de validação viável na ausência de PSG, "comparar
contra wearable/app comercial". A meta-análise de **Lee et al. (2025)** complica isso:

| | Direção do viés vs. PSG |
|---|---|
| **Actigrafia de pesquisa** (Conley et al., 2019) | **Superestima** sono (TST +22,4 min em crônicos), subestima vigília |
| **Dispositivos de consumo** (Lee et al., 2025) | **Subestima** sono (TST −16,9 min), **superestima** vigília (WASO +13,3 min) |

**São direções opostas.** A explicação plausível é que os relógios de consumo usam FC e
algoritmos proprietários calibrados de outro jeito — mas a explicação importa menos que a
consequência: **"actigrafia superestima sono" é uma afirmação sobre algoritmos de actigrafia
aplicados a movimento bruto, não sobre relógios comerciais.** Citar as duas fontes como se
dissessem a mesma coisa é erro factual.

**Consequência para o projeto:** validar o Dormio contra um Fitbit é comparar dois
instrumentos enviesados em direções diferentes, e o resultado não é interpretável sem
declarar isso. Se essa rota for usada, ela precisa vir com a ressalva — e provavelmente é
melhor que o papel do wearable comercial seja **contexto**, não referência.

### 2.7 O que continua incerto — e isso é honesto, não falha

| Incerteza | Quem resolve | Quando |
|---|---|---|
| **O travesseiro capta movimento de corpo sem mexer a cabeça?** É a incógnita central do projeto. Não há dataset, não há literatura no caso exato | `VIA-01` (bancada) | Depois da solda |
| **Quanto se perde ao trocar pulso por posição central?** Há indício de direção (fonte 7), não magnitude para este caso | `ML-03` (Wearanize+) e `VIA-02` | `ML-03` é L0; `VIA-02` é L1 |
| **A taxa do acelerômetro do Zmax** — 🟡 provável 256 Hz (explícito só em preprint) | 📄 **Cabeçalho EDF** do dataset: declara amostras por registro **por canal**. Resolve também faixa, bits e escala, via `physical/digital min-max` | Ao baixar. **Sem consequência para o pipeline** |
| **Faixa e bits do Apple Watch** — ⛔ **fechado como indisponível.** Apple não publica; o artigo não informa; o *teardown* dá código de marcação, não peça — e o firmware é quem configura | Encerrado. A doc da Apple confirma que o dado chega em **ponto flutuante em g**, logo a quantização **não é observável** | **Nenhuma consequência** |
| **Modelo do ActivPAL** — ⛔ **fechado como não documentado.** Verificado no artigo, no protocolo do Healthy Brain Study, no `README` do repositório (vazio) e na página do Radboud | Escrever aos autores, ou ler os metadados do arquivo | Baixa prioridade |
| **Ruído em repouso dos aparelhos de pesquisa** — ✅ **fonte confirmada e aberta:** Lettink, van Wieringen, Altenburg, Chinapaw & van Hees (2024), *JMPB* 7(1), **CC BY**. 64 aparelhos, cinco marcas, mesa vibratória, 60 s de repouso, 127 observações | 🟡 Valores por marca estão na **Figura 3** e no **Suplemento S3**, não extraídos. Duas vias abertas: ler a versão de registro no repositório Pure do Amsterdam UMC, ou **computar do dado bruto no Zenodo** (CC BY, DOI 10.5281/zenodo.8160791) | **Joga a favor:** subestimar o ruído dos aparelhos de pesquisa torna nosso argumento *mais difícil*, e ele sobrevive |
| **O custo real de ler os `.bin` do GENEActiv em Python** — estimativa de ~1 dia, não medida | Fazer | L0, imediato |
| **O viés de −1,06 m/s² em Z** foi medido através de contato ruim, e o filtro mudou de 260 para 21 Hz depois | `CAL-01` + `CAL-02` | Depois da solda |
| **A frase do preprint de Yuan et al.** — medRxiv bloqueou o acesso; não sabemos se a frase antiga existia lá | Baixo valor; a frase publicada é melhor | — |

---

## 3. Caminhos implementáveis

Organizados por **quando podem começar**, não por importância. A camada é o que determina o
*quando*; o peso é o que determina o *quanto importa*.

> **Sobre as estimativas de esforço:** são estimativas de quem leu o código e a
> documentação, **não medições**. Trate como ordem de grandeza. As marcadas com ~ têm
> incerteza maior porque dependem de coisa não verificada (formato de arquivo, latência de
> terceiro).

### 3.1 🟢 L0 — dá para começar hoje, sem hardware nenhum

Este é o maior bloco disponível, e quase todo ele é **entregável de TCC**.

---

#### C1 · Pipeline de ML reprodutível sobre o Newcastle  `ML-01` 🔴

| | |
|---|---|
| **Exige** | Nada físico. Download de 962,8 MB (Zenodo, CC-BY 4.0, sem cadastro, sem DUA) |
| **Entrega** | A estrutura `ml/` do §7: carregadores com interface única, janelamento de 30 s, 8 features invariantes à orientação, seed fixa, config versionado. É a fundação de tudo o que vem depois |
| **Risco** | 🟡 Médio-baixo. O único ponto real de atrito são os `.bin` proprietários do GENEActiv — lidos nativamente em R (`GENEAread`, `GGIR`); em Python dá, mas custa. **Atenção documentada pelos próprios autores:** os IDs de participante *dentro do cabeçalho* dos `.bin` estão **errados**; o ID válido é o do nome do arquivo |
| **Esforço** | ~1 semana para a Fase 0 + ~1 dia (estimado) para o parsing dos `.bin` |
| **Por que vale** | Sem isto, nada do resto tem validade científica. E é software puro — não espera a solda |

---

#### C2 · Baselines medidos antes de qualquer modelo  `ML-02` 🔴

| | |
|---|---|
| **Exige** | C1 pronto |
| **Entrega** | Três números que mudam a conversa: (0) "sempre dormindo", (1) Cole-Kripke e Sadeh — os algoritmos que a actigrafia usa desde 1992/1994, (2) regressão logística interpretável |
| **Risco** | 🟢 Baixo tecnicamente. 🔴 **Alto em expectativa:** é bem possível que Cole-Kripke empate com o modelo aprendido. Isso não é fracasso — é uma conclusão legítima de TCC, desde que descoberta agora e não na banca |
| **Esforço** | ~2–3 dias |
| **Por que vale** | É o item que protege o trabalho do erro mais comum da área. **Se ele não for reportado, todos os outros números mentem** (§2.4) |

---

#### C3 · Experimento de transferência entre posições  `ML-03` 🔴

| | |
|---|---|
| **Exige** | C1 + o **DUA do Wearanize+** — formulário com plano de pesquisa, submetido via ORCID. ⚠️ **Latência de terceiro, não sua** |
| **Entrega** | **O resultado original do trabalho.** Treina no pulso, testa na cabeça, mede a queda de kappa. A base tem três posições, os *mesmos* rótulos, a *mesma* noite — nenhuma outra permite isso |
| **Risco** | 🟡 O DUA pode demorar. **Mitigação já embutida:** o pipeline nasce no Newcastle e trocar de base é trocar o carregador |
| **Esforço** | ~1 semana depois que a base chegar. O formulário: uma tarde |
| **Por que vale** | Responde à pergunta que a banca *vai* fazer: *"vocês treinaram num sensor de pulso e o produto é de travesseiro — como sabem que funciona?"*. Com qualquer outra base, a resposta é uma limitação declarada. Com esta, é um número. **Transforma a maior fraqueza metodológica no resultado mais original** |
| **⚠️ Ação hoje** | **Enviar o pedido de DUA agora.** É um formulário. Quanto antes sair, menos ele bloqueia |

---

#### C4 · O contrato de dados passa a carregar features  `DATA-07` 🔴

| | |
|---|---|
| **Exige** | Nada. Campo novo e **opcional** → versão **MINOR**, nada quebra em campo |
| **Entrega** | Hoje cada linha leva magnitude + rótulo. Um modelo precisa de um vetor por época. ~10 números × 960 épocas = **~9,6 mil valores por noite** — trivial para o banco. *(Enviar sinal bruto seria ~11 MB/noite: não faça.)* |
| **Risco** | 🟢 Baixo |
| **Esforço** | ~1–2 dias |
| **Por que vale** | **Sem isto, nenhum modelo treinado roda sobre o que o Dormio grava.** É a ponte entre C1 e o produto |

---

#### C5 · Firmware: época de 30 s e amostragem ≥ 42 Hz  `FW-05` `DATA-02` 🔴

| | |
|---|---|
| **Exige** | Escrita e teste no Wokwi: L0. **Validação em placa: L1** |
| **Entrega** | Época de **30 s** (não 60, não livre) — é a resolução dos rótulos de PSG em **todas** as bases. Amostragem ≥ 42 Hz (Nyquist do filtro de 21 Hz do `FW-06`), reamostrada para uma grade comum de **32 Hz** |
| **Risco** | 🟡 Consumo. Amostrar mais rápido gasta mais — quantificar no `CALC-01` |
| **Esforço** | ~2–3 dias |
| **Por que vale** | Época diferente exige reamostrar rótulo, e **reamostrar rótulo inventa informação**. Esta decisão trava a compatibilidade com a literatura inteira |

---

#### C6 · O bug que trava o firmware offline  `HW-05` 🔴

| | |
|---|---|
| **Exige** | Nada. É bug real no código: `while (WiFi.status() != WL_CONNECTED)` sem saída |
| **Entrega** | Buffer local + sync + timeout. O `DASH-12` (já feito) existe **porque** este item existe: sem `captured_at`, o buffer chegaria empilhado e o painel veria uma sessão de 2 segundos |
| **Risco** | 🟢 Baixo |
| **Esforço** | ~1–2 dias |
| **Por que vale** | Uma noite inteira de captação com Wi-Fi instável é o cenário real. Hoje o dispositivo trava |

---

#### C7 · O bloco de texto do TCC  `CALC-01..04` `DIAG-01..04` 🔴

| | |
|---|---|
| **Exige** | Nada. É análise e escrita |
| **Entrega** | Modelo de energia/autonomia (`I_média`, `autonomia = C/I_média` — e expõe o limite do DevKit V1, embasando o `HW-02`); física do acelerômetro (±8g/16 bits ≈ 0,244 mg/LSB, Nyquist, e **por que 21 Hz e não 260**); índice de atividade e derivação do limiar `g ± k·σ`; diagrama de blocos, esquemático, fluxograma, sequência + ER |
| **Risco** | 🟢 Nenhum |
| **Esforço** | ~1 semana para o conjunto |
| **Por que vale** | **É o bloco que mais rende por hora enquanto o hardware espera, e é o que a banca lê.** `CALC-03` e `ML-01` são o mesmo assunto por dois caminhos |

---

#### C8 · LGPD, com a aposta elevada pelo ML  `LGPD-01` `LGPD-03` 🔴

| | |
|---|---|
| **Exige** | Rascunho é L0. **Revisão com o orientador é L3** |
| **Entrega** | Política de privacidade e termos (hoje a tela de Configurações exibe "em elaboração"); direito de eliminação ("Excluir conta", hoje desabilitado — a exportação CSV já cobre portabilidade) |
| **Risco** | 🔴 **O ML muda a natureza do tratamento.** Registrar movimento é uma coisa; **inferir estado de sono de pessoa identificada** é outra — passa a haver inferência sobre saúde. Se o `VIA-02` envolver voluntários, some-se termo de consentimento e possivelmente comitê de ética |
| **Esforço** | ~2 dias de rascunho + a conversa |
| **Por que vale** | É o item que, se ignorado, aparece na banca como pergunta que não tem resposta boa na hora |

---

#### C9 · Testar o RLS de verdade  `INFRA-01` + `SEC-05` 🔴

| | |
|---|---|
| **Exige** | Nada. Supabase CLI + Postgres local |
| **Entrega** | Os 221 testes **mockam o Supabase inteiro** — a garantia central de isolamento entre usuários **não tem cobertura automatizada**. Com Postgres local dá para testar que o usuário A não lê a linha de B |
| **Risco** | 🟢 Baixo |
| **Esforço** | ~2–3 dias |
| **Por que vale** | É a diferença entre "temos RLS" e "provamos que o RLS funciona". Numa banca de Engenharia da Computação, a segunda frase é outra coisa |

---

### 3.2 🟡 L1 — depende da solda dos 8 pinos

> 🔒 **Etapa 0 trava tudo aqui.** O módulo veio com os pinos não soldados; o contato por
> jumper produziu, em 25/08: registradores zerados, `|a| = 56,5 m/s²` com a placa parada,
> `−11,6 °C` e ruído 30× o normal. **Toda medição feita até aqui é provisória.** São 8
> pontos de solda. Teste de aceitação: pose Z+ com ruído ~0,02.

| Caminho | Exige | Entrega | Risco | Esforço |
|---|---|---|:---:|---|
| **`CAL-01` + `CAL-02`** — caracterização de 6 posições | Solda + `FW-06` já aplicado | Viés e escala por eixo desta unidade. ⚠️ **Precisa ser feita DEPOIS do `FW-06`** — o filtro mudou de 260 para 21 Hz, e o limiar do `DATA-02` é definido sobre esse ruído | 🟡 Se o viés real for grande, o ENMO não se desloca: **ele se destrói** (−1,06 m/s² é 11% de `g`) | ~meio dia |
| **`VIA-01`** — viabilidade de bancada | Solda | 2 min parado → 2 min mexendo a cabeça → 2 min virando o corpo. Pergunta: *os três blocos se separam?* | 🔴 **É a incógnita central do projeto.** Se o travesseiro subcaptar movimento de corpo, nenhum modelo conserta | ~meio dia |
| **`VIA-02`** — o mesmo com celular em paralelo | Solda + o PWA `/coletar` | O limiar do celular, a diferença de acoplamento **medida**, e o grupo de controle | 🟡 | ~meio dia |
| **`VAL-01`** — uma noite real captada | Tudo acima + `HW-04` (encapsulamento, **segurança térmica do LiPo dentro do travesseiro**) | O critério de sucesso da Fase 2. O painel já aguenta 2000 leituras | 🔴 Sem isto, não há Fase 2 | 1 noite + preparo |
| **`FW-02` · `FW-04` · `HW-03`** | Solda | Deep Sleep real (hoje é mock do Wokwi); firmware sem dependências do simulador; Wake-on-Motion pelo INT do MPU (hoje é **botão** — andaime) | 🟡 | ~3–4 dias |

**O ganho de agrupar:** `CAL-01` + `VIA-01` + `VIA-02` cabem **num dia de bancada** e
produzem de uma vez a calibração, a viabilidade demonstrada e o limiar do celular.

### 3.3 🔵 L2 — depende de dado real coletado

| Caminho | Exige | Entrega | Risco | Esforço |
|---|---|---|:---:|---|
| **`DASH-04`** — noite completa na tela | `VAL-01` | Linha do tempo e lacunas como indicador de repouso. **O gráfico já está preparado; falta o dado** | 🟢 | ~1–2 dias |
| **`VAL-02`** — validação quantitativa | `VAL-01` | F1, matriz de confusão, curva de corrente×tempo **medida** (o `CALC-01` é predição; este é medição) | 🟡 | ~2–3 dias |
| **`ML-04`** — calibrar o modelo com dado próprio *(no backlog: `ML-09`, desde 28/10 — o `ML-04` de lá é a validação externa)* | `VAL-01` + C1 | **Ajuste de limiar, não re-treino.** n=1 não treina nada | 🟡 O risco é a tentação de chamar isso de validação | ~2 dias |
| **`ML-05`** — o que o modelo devolve ao usuário *(no backlog: `ML-10`)* | `ML-04` | Início/fim do repouso, despertares longos, fragmentação, latência **aparente** até a quietude, regularidade entre noites, comparação com a própria linha de base | 🔴 **É onde o escopo vaza.** Ver a lista do "não devolver" abaixo | ~3–4 dias |
| **`HW-07`** — fusão de 2 acelerômetros | `VIA-01` mostrar subcaptação | 2º MPU6050 sob o colchão, endereços `0x68`/`0x69` no mesmo I2C. **Gatilho, não plano** | 🟡 **Implica rever a redação da RQ** com o orientador: travesseiro → cama/travesseiro | +1 peça barata + ~1 semana |

> ### A régua do `ML-05`, que vem do `DASH-09`/`DASH-11`
>
> **Não devolver:** estágios de sono ("2h de REM") · nota de qualidade 0–100 (número
> inventado, já eliminado no `UI-04`/`WEB-03` — **não voltar pela porta do ML**) · qualquer
> frase clínica ("você pode ter apneia") · comparação com "a média das pessoas" (o Dormio
> não tem população normativa).
>
> **Se a frase na tela não puder ser rastreada até um número medido e uma incerteza
> declarada, ela não vai para a tela.**

### 3.4 🟣 L3 — depende de você ou de terceiro

| Caminho | Por quê | Urgência |
|---|---|:---:|
| **Etapa 0 — soldar** | Nenhum agente faz. **É a coisa mais importante do projeto** | 🔴🔴 |
| **`DATA-03`** — rodar `002_backfill_dono_dos_dados.sql` no Supabase | Escrito e mergeado desde agosto. **Sem ele, o dashboard de uma conta nova nasce vazio** | 🔴 |
| **`RQ-01` · `SCI-01`/`DEC-01`** — confirmar RQ e estratégia de dataset com o orientador | A recomendação de base **mudou** (Wearanize+ como principal). O orientador endossou Walch; a mudança precisa ser conversada | 🔴 |
| **DUA do Wearanize+** | Formulário via ORCID. **Latência de terceiro** | 🔴 (enviar hoje) |
| **A decisão de escopo sobre "noite"** | O painel pode dizer *"a noite de 27/08"* sem afirmar que o dado é sono? Hoje diz "sessão de captação", que é o teto honesto | 🟡 |
| **`HW-02`** — energia (LiPo + TP4056; o DevKit fica?) | Pode exigir compra. O DevKit V1 **não atinge µA** — regulador e USB-serial dominam | 🟡 |
| **`GIT-02`** — remover `.git/index.lock` e commitar | Um comando | 🔴 (trivial) |

---

## 4. Recomendação

### 4.1 A sequência que eu seguiria

```
  HOJE, NA MESMA SEMANA (paralelo, sem esperar nada)
  ├─ [15 min]  GIT-02 · DATA-03 · enviar o DUA do Wearanize+
  ├─ [1 tarde] Marcar a conversa com o orientador (RQ-01 + a mudança de base)
  ├─ [1 tarde] Achar quem solda: laboratório do curso, assistência, ferro próprio
  └─ [1 sem]   C1 — baixar o Newcastle e montar o ml/ reprodutível

  SEMANAS 2–3
  ├─ C2 — baselines medidos  ◄── o item que protege o trabalho
  ├─ C4 + C5 — contrato com features + época de 30 s
  └─ C7 — CALC + DIAG (o bloco que a banca lê)

  ASSIM QUE A SOLDA SAIR  ◄── um único dia de bancada
  └─ CAL-01 + CAL-02 → VIA-01 → VIA-02

  DEPOIS
  ├─ VAL-01 (uma noite) → DASH-04 → VAL-02
  ├─ C3 (ML-03) quando o Wearanize+ chegar  ◄── o resultado original
  └─ ML-04 → ML-05
```

### 4.2 Por que nesta ordem — os três raciocínios

**(1) O que tem latência de terceiro sai primeiro, mesmo sendo pequeno.** O DUA e a solda
não consomem seu tempo — consomem calendário. Um formulário enviado hoje e um ferro de
solda localizado hoje valem mais que uma semana de código, porque **destravam** semanas
futuras. É o único tipo de tarefa em que atrasar custa juros compostos.

**(2) O bloco L0 de ML é o maior valor acadêmico disponível, e não espera nada.** `ML-01` →
`ML-02` → `ML-03` são software puro, são entregáveis de TCC, e resolvem de passagem o
`CALC-03`. Enquanto o hardware espera, **não há motivo para o projeto ficar parado** — só
não dá para fingir que o que sai de L0 substitui a medição.

**(3) O `ML-02` vem antes de qualquer modelo sofisticado, e isso não é negociável.** Pela
§2.4: se o baseline trivial não for reportado, todos os outros números mentem. Descobrir na
semana 2 que Cole-Kripke empata é uma conclusão de TCC. Descobrir na banca é outra coisa.

### 4.3 Os trade-offs, ditos com clareza

| Decisão | O que se ganha | O que se perde | Minha leitura |
|---|---|---|---|
| **Wearanize+ como base principal** (em vez de manter só o Walch) | O único experimento que mede o *domain shift* de posição. Vira o resultado original | Um DUA no caminho; base nova (dez/2025), pouca ferramenta de comunidade — **você abre trilha** | **Vale**, com o Newcastle como rede de segurança. Mas **precisa ser conversado com o orientador**, que endossou o Walch |
| **Época de 30 s fixa** | Compatibilidade com a literatura inteira | Perde-se liberdade de ajustar a granularidade | **Não é escolha.** Época diferente exige reamostrar rótulo, e isso inventa informação |
| **Não acrescentar sensor de medição** | Escopo fechado, defensável, entregável | Fica sem FC — e portanto sem estadiamento, para sempre | **Vale.** PPG destruiria a proposta de valor ("não invasivo, sem contato"); BCG é outro TCC (§2.3c). Luz/temperatura ambiente (~R$ 10–40, mesmo I2C) são opcionais **como contexto**, jamais como evidência de estágio |
| **`HW-07` (2º acelerômetro) como contingência** | Resolve a subcaptação **se** ela existir | Custo baixo (1 peça), mas **exige rever a redação da RQ** | **Manter como gatilho, não como plano.** Quem decide é o `VIA-01`. Ambos os resultados são defensáveis |
| **Reportar o baseline trivial** | Blindagem contra a refutação de trinta segundos | Provavelmente vai mostrar que o modelo ganha pouco | **Vale sempre.** O constrangimento de não reportar é maior que o de reportar |

### 4.4 Risco de TCC × risco técnico — e eles não são o mesmo

Esta é a distinção que mais importa para priorizar, e ela costuma ser confundida.

**🎓 Risco de TCC — prazo e banca. É o que pode reprovar mesmo com o produto funcionando.**

| Risco | Gravidade | Mitigação |
|---|:---:|---|
| **Chegar na banca sem uma noite real captada** | 🔴🔴 | **Soldar.** É o único caminho. O critério de sucesso da Fase 2 é explícito: "funciona montado, capta uma noite, o dado aparece" — e "simulação não substitui essa validação" |
| **Publicar acurácia sem o baseline ao lado** | 🔴🔴 | `ML-02`. Custa 2–3 dias e é refutável em 30 segundos se faltar |
| **Referência com autoria inventada na lista ABNT** | 🔴 | ✅ **Já mitigado.** Todas conferidas na fonte. Falta você **ler** os artigos — referência conferida ≠ artigo lido |
| **Afirmar mais do que o §2.1 permite** em resumo, introdução ou considerações finais | 🔴 | Checklist do `LIMITACOES-TCC.md`. É o erro que se comete **fora** da seção de limitações |
| **RQ não confirmada com o orientador** | 🔴 | `RQ-01`. Uma conversa |
| **Pergunta de LGPD sem resposta na hora** | 🟡 | `LGPD-01` + `LGPD-03` |

**⚙️ Risco técnico — o que pode não funcionar. Grave, mas geralmente já previsto.**

| Risco | Gravidade | Leitura honesta |
|---|:---:|---|
| **A especificidade vai decepcionar** | 🔴 | **É limitação física, não de modelo** (§2.3a). Todo trabalho sério de actigrafia relata isso. **Reporte o número; não o esconda atrás da acurácia.** Não é risco — é resultado esperado |
| **O baseline trivial pode empatar** | 🔴 | Idem. Se o modelo chegar a 88% e "sempre dormindo" acerta 88%, ele não aprendeu nada. É **descoberta**, não falha |
| **O travesseiro subcaptar movimento de corpo** | 🟡🔴 | **O risco técnico genuíno.** Nenhum modelo conserta. Gatilho do `HW-07`. Só o `VIA-01` responde |
| **O viés de calibração destruir o ENMO** | 🟡 | −1,06 m/s² em Z é 11% de `g`. `CAL-01` **depois** do `FW-06` |
| **O DUA do Wearanize+ demorar** | 🟡 | Mitigação embutida: pipeline nasce no Newcastle, trocar de base é trocar o carregador |
| **n=1 não valida** | 🟡 | Já está no `METODOLOGIA.md` e continua valendo. Dado próprio **calibra e ilustra**; não valida |

**A assimetria que decide a prioridade:** quase todo o risco técnico da lista acima **já
está previsto, documentado e é defensável na banca** — inclusive os 🔴, porque são
limitações da área inteira, não do trabalho. O risco de TCC é o oposto: é **evitável** e,
se não for evitado, não tem defesa boa na hora.

**Por isso a recomendação prática é curta:** *solde os oito pinos, envie o DUA, e enquanto
isso construa o `ml/` — nesta ordem de urgência de calendário, mesmo que a ordem de esforço
seja o inverso.*

### 4.5 O enquadramento que sustenta tudo isso

Há uma leitura que vale mais que qualquer número isolado, e é a que deve fechar as
Considerações Finais:

> **O Dormio não precisa vencer o pulso. Ele precisa mostrar que uma posição não invasiva
> alcança desempenho comparável ao de um sensor vestido.**

Se o objetivo fosse superar a actigrafia de pulso, o trabalho estaria condenado antes de
começar — a §2.3 explica por quê, e é física. Mas **equivalência sob restrição** é outra
pergunta, e é uma boa pergunta de engenharia: *quanto se perde ao trocar um sensor vestido
por um sensor que a pessoa não sente?*

Ela é específica, é mensurável (`VIA-01`, `VIA-02`, `ML-03`), **não está respondida na
literatura** — nenhuma base pública tem acelerômetro em travesseiro com rótulo de sono — e é
literalmente a RQ do trabalho. **O resultado é publicável nos dois sentidos:** se a perda for
pequena, valida o conceito; se for grande, quantifica um limite que ninguém quantificou e
justifica o `HW-07` com evidência em vez de intuição.

---

## Documentos relacionados

| Arquivo | O que tem lá que não tem aqui |
|---|---|
| **`docs/ML-DATASETS-E-PLANO.md`** | O §0 com cada número colado à sua fonte e população · as nove bases uma a uma · as features do §7 · o plano de execução e validação · a lista de fontes formatada |
| **`docs/LIMITACOES-TCC.md`** | O texto de limitações em tom acadêmico, pronto para colar, com citações autor-data |
| **`docs/BACKLOG-COMPLETO.md`** | Os 64 itens abertos, com camada de dependência e peso |
| **`docs/METODOLOGIA.md`** | A régua: RQ, reprodutibilidade, validação, rastreabilidade. *Sugestão de busca ≠ citação* |
| **`docs/HARDWARE.md`** | BOM, fases, adequação do hardware, a arquitetura v1 → v2 |
| **`ROADMAP.md`** · **`HISTORICO.md`** | Prioridade e o que já foi concluído |
