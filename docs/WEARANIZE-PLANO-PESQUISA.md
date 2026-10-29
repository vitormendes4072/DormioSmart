# Plano de pesquisa — Wearanize+ (rascunho para revisão)

> **RASCUNHO. Não enviar sem revisar.** Escrito em 2026-09-14 a partir do escopo definido
> em `docs/ML-DATASETS-E-PLANO.md`. O procedimento de envio está em `docs/WEARANIZE-ACESSO.md`.
>
> **Este texto serve a dois destinos** e o mesmo conteúdo cobre os dois:
> - a seção *Recipient's research plan* (**Annex II**) do formulário de DUA
>   (`DTA_Wearanize_nonEU_v1.docx`), enviado por e-mail ao Dr. Martin Dresler;
> - o campo *project description* do formulário "Request access" do portal RDR.
>
> **A versão em inglês (§A) é a que se envia** — mas não para o campo do Anexo II do `.docx`.
> A tradução (§B) existe para você conferir o que está assinando — **não a envie junto**.
>
> ### 🔴 Atualização 2026-09-14 (4ª rodada) — o Anexo II tem limite de 300 palavras
>
> Abri o `DTA_Wearanize_nonEU_v1.docx` de verdade (detalhes em `docs/WEARANIZE-ACESSO.md` §8).
> O campo onde este plano é colado diz, literalmente: **"Recipient's research plan (maximum
> 300 words)"**. O §A abaixo tem várias páginas — serve para o orientador, para a introdução do
> TCC, e para o campo *project description* do portal RDR (texto livre). **Para colar no
> Anexo II do `.docx`, use o §C — versão condensada, 297 palavras, contadas.**
>
> ### ⚠️ Antes de enviar, preencha os `[[colchetes]]`
>
> - `[[INSTITUTION]]` — nome oficial completo da instituição, em inglês
> - `[[DEPARTMENT / PROGRAMME]]` — curso/departamento
> - `[[CITY, STATE, BRAZIL]]` — endereço da sede
> - `[[SUPERVISOR NAME, TITLE]]` — orientador
> - `[[ORCID]]` — o seu ORCID iD
> - `[[EXPECTED DEFENCE DATE]]` — data prevista de defesa
> - ~~`[[N]]` em *"3 (three) years"* — o prazo de vigência que você quer propor (cláusula 13)~~
>   **Não aplicável nesta versão.** O `DTA_Wearanize_nonEU_v1.docx` já vem com o prazo fixado
>   em **dez (10) anos**, sem colchete a preencher (`WEARANIZE-ACESSO.md` §8.2). A tabela
>   "Tratamento, segurança e retenção" abaixo (linha "Prazo proposto") também deve refletir
>   isso — não é mais uma proposta sua.
>
> ### 🔴 Decisão de escopo — atualizada em 2026-09-14, depois de abrir os arquivos
>
> **Verificado, não inferido:** este plano inteiro é executável na coleção aberta
> **Wearanize+ OA** (CC-BY-4.0), **sem DUA**, com **N = 92** para o experimento pulso→cabeça
> e **N = 86** para a matriz 3×3. O único item abaixo que exige a coleção restrita é o uso dos
> **questionários** (PSQI/PHQ-9) para estratificação — que é secundário.
>
> **Ou seja: você provavelmente não precisa enviar isto.** Se os questionários não entrarem na
> análise, use o §A apenas como descrição de projeto (para o orientador, para a qualificação,
> para a introdução do TCC) e **não abra o processo de DUA**, que custa assinatura
> institucional, jurídico e meses.
>
> Dois números do §A precisam ser atualizados se você enviar: o N do experimento (**92**, não
> "os 130") e o fato de que as duas pontuações manuais existem para **96** sujeitos.
>
> Este rascunho está escrito **pedindo a coleção restrita e declarando que a OA já está em
> uso**. É a forma honesta: mostra que o pedido é focado, não genérico. Se você decidir não
> pedir o acesso restrito, **use o §A apenas como descrição de projeto** e ignore as partes
> marcadas com ▸.

---

# §A · English version — to be submitted

## Project title

Wrist-to-head accelerometer transfer for sleep/wake classification: quantifying the
performance cost of moving a sensor off the body, toward non-contact in-pillow sleep
monitoring

## Project type

Undergraduate final-year research project (*Trabalho de Conclusão de Curso* / Bachelor's
thesis), `[[DEPARTMENT / PROGRAMME]]`, `[[INSTITUTION]]`, `[[CITY, STATE, BRAZIL]]`.
Non-commercial academic research. No external funding. No industrial partner.

## Applicant

| | |
|---|---|
| **Recipient scientist / applicant** | Vitor Mendes Oliverio, undergraduate student, `[[DEPARTMENT / PROGRAMME]]`, `[[INSTITUTION]]` |
| **ORCID** | `[[ORCID]]` |
| **E-mail** | vitormendes4072@gmail.com |
| **Supervisor** | `[[SUPERVISOR NAME, TITLE]]`, `[[DEPARTMENT]]`, `[[INSTITUTION]]` |
| **Recipient institution** | `[[INSTITUTION]]`, `[[CITY, STATE, BRAZIL]]` |
| **Project partners** | None |
| **Persons requiring access to the data** | The two persons listed above, and no one else. Each will submit a separate RDR access request under their own ORCID account. |

## Background

Wrist actigraphy is the established low-cost alternative to polysomnography (PSG) for
sleep/wake estimation, but it requires the participant to wear a device throughout the night.
Our project develops **Smart Dormio**, a non-contact sleep monitor: a single triaxial MEMS
accelerometer (InvenSense MPU-6050) mechanically coupled to a **pillow**. The device records
no EEG, no EOG and no photoplethysmography, so its claims are deliberately restricted to
sleep/wake classification per 30 s epoch and to the rest-period and fragmentation metrics
derived from it. No sleep staging is attempted, for the physical reason that REM and N3 are
both motionless states and are therefore indistinguishable to an accelerometer.

This design raises one methodological objection that determines whether the work is
scientifically defensible, and it is the objection any examining board will raise first:
**every public accelerometry dataset with PSG labels was recorded with the sensor attached to
the body — almost always the wrist — while our device sits under the head, uncoupled from it.**
A model trained on wrist data and deployed on pillow data crosses a domain shift in sensor
position and mechanical coupling, and the size of that shift is, at present, unmeasured.

The literature suggests the shift is not negligible and may not favour our position.
Meredith-Jones et al. (2024), comparing five body locations against home PSG, report that
overall accuracy was higher at the wrist (mostly > 80%) than at locations near the centre of
mass (generally < 80%), with specificity "considerably better" at the wrist than at the waist,
while sensitivity was higher near the centre of mass. The mechanism is intuitive and it is the
mechanism that matters for us: specificity depends on catching the participant *awake*, and an
awake wrist in bed moves a great deal, whereas an awake head on a pillow may not move at all.
Conversely, Razjouyan et al. (2017) found that a single trunk-mounted sensor combining posture
change with body acceleration outperformed wrist acceleration alone (85.8% vs 79.8% accuracy),
which suggests that orientation-derived features may partly compensate for the loss.

Neither result tells us what happens at the head. **We have found no public dataset other than
Wearanize+ that contains a head-mounted accelerometer recorded concurrently with expert-scored
PSG.** That is precisely why we are requesting this dataset.

## Research question

**How much sleep/wake classification performance, measured as Cohen's kappa, is lost when a
model trained on wrist accelerometry is applied unchanged to head accelerometry recorded on
the same night from the same participants under the same PSG labels?**

Secondary questions:

1. How does that loss compare with the loss in the reverse direction (head → wrist) and with
   the thigh position (ActivPAL), i.e. is the degradation a property of the target position or
   of the direction of transfer?
2. Does adding orientation-derived features (posture angle and its inter-epoch change) reduce
   the transfer loss, as Razjouyan et al. (2017) would predict?
3. How does the transfer loss compare with the **inter-rater ceiling** given by the two
   independent expert manual scorings included in the dataset? A transfer loss smaller than
   the disagreement between two human scorers is a qualitatively different result from one
   larger than it.

## Why the Wearanize+ data specifically

Three properties, and we are not aware of any other public dataset that has all three:

1. **A triaxial accelerometer on the head** (Zmax headband, 256 Hz, in g). The head is the
   closest available kinematic proxy for what a pillow-mounted sensor senses, because a pillow
   sensor measures the load the head applies to the pillow. No other public dataset with PSG
   labels provides this.
2. **Three sensor positions recorded simultaneously — head, wrist (Empatica E4, 32 Hz) and
   thigh (ActivPAL, 20 Hz) — sharing a single set of PSG labels from the same night.** This
   turns the position shift from a declared limitation into a measurable quantity: train on
   one position, test on another, report the drop. Cross-cohort or cross-study comparisons
   cannot isolate position from population, protocol and scorer; a within-night, within-subject
   design can.
3. **Raw triaxial acceleration in physical units, not proprietary activity counts.** This is
   decisive for us and it excludes most large actigraphy datasets. Activity counts are the
   output of an undisclosed manufacturer algorithm and have no physical unit; there is no
   published function mapping MPU-6050 acceleration onto them, so a model trained on counts
   cannot run on our device's data. Acceleration is a physical quantity and transfers.

The manual AASM scoring by expert scorers at 30 s resolution, and the accelerometer-based
manual device synchronisation described in the reference paper, are what make the
signal-to-label alignment trustworthy enough for this comparison to mean anything.

▸ **Questionnaire data (restricted collection only).** We additionally request the PSQI and
PHQ-9 responses in order to test whether the wrist→head transfer loss is larger in
participants with poorer self-reported sleep quality. The actigraphy literature consistently
reports that sleep/wake accuracy declines as sleep disturbance increases (Conley et al., 2019;
Li et al., 2025); if the transfer loss follows the same pattern, that is a limitation a
pillow-based device must declare. This stratification is **secondary** to the main research
question and we would proceed without it if the questionnaire data cannot be shared.

## Planned methods

**Scope.** Binary sleep/wake classification per 30 s epoch. No sleep staging. PSG labels are
mapped as: 0 → Wake; 1–4 (N1, N2, N3, REM) → Sleep; −1 (unscorable) → epoch discarded.

**Preprocessing.** All accelerometer channels are resampled to a common 32 Hz grid (the native
rate of the Empatica E4 and the lowest common viable rate across devices and our own hardware),
and epoched at 30 s, aligned to the PSG labels without label resampling.

**Features.** Eight per epoch, all invariant to sensor orientation, since a sensor loose in a
pillow has an arbitrary and changing orientation: mean, standard deviation and maximum of ENMO
(`max(|a|/g − 1, 0)`); signal magnitude area; zero-crossing rate of the DC-removed signal;
fraction of the epoch above a movement threshold; posture angle `atan2(az, sqrt(ax² + ay²))`;
and the inter-epoch change of that angle. Each epoch also carries the features of its ±2
neighbouring epochs. Every feature is computable on an ESP32 microcontroller in single-precision
floating point without buffering the whole night — this constraint is deliberate, because a
feature the device cannot compute cannot be part of a deployable model.

**Models, in increasing order of complexity, none skipped.** (0) The degenerate "always asleep"
baseline, which on a PSG night is typically 85–90% accurate and which we report first,
explicitly, because any accuracy figure is meaningless beside it. (1) Cole-Kripke and Sadeh,
the classical actigraphy algorithms. (2) Logistic regression over the feature set, for
interpretability. (3) Random forest / gradient boosting. (4) Temporal smoothing (moving median
or a two-state HMM). A 1-D CNN over the raw window will be attempted only if time permits and
only if it clearly beats step 3.

**The transfer experiment — the original contribution.** A 3×3 matrix over the three sensor
positions. For each ordered pair (train position, test position), the model is trained on the
training position and evaluated unchanged on the test position, using the same subjects' same
nights and the same PSG labels. The reported quantity is **Δκ**, the drop in Cohen's kappa
relative to the matched-position diagonal. The cell of interest is **train = wrist, test =
head**. This is, to our knowledge, the first direct measurement of that quantity.

**Validation.** Splits are by **subject**, never by epoch, since epochs within a night are
strongly autocorrelated and epoch-level shuffling inflates accuracy spectacularly and falsely.
Random seeds and configuration files are fixed and versioned alongside every reported result.

**Metrics.** Per epoch: sensitivity (sleep), **specificity (wake)**, Cohen's kappa, F1 and the
confusion matrix. Specificity is reported prominently because it is where accelerometer-based
sleep/wake classification fails — lying awake and still is indistinguishable from sleep to an
accelerometer — and because reporting it is the honesty test of this kind of work. Per night:
error in total sleep time, wake after sleep onset and sleep onset latency, with Bland-Altman
plots showing systematic bias and limits of agreement. Where the dataset provides two
independent manual scorings, the inter-rater agreement between them is computed and reported as
the realistic performance ceiling.

**Independent cohorts.** Models will additionally be evaluated on two openly licensed datasets
already in hand — Newcastle 2015 (28 subjects, GENEActiv on both wrists at 85.7 Hz, PSG labels,
CC-BY-4.0) and Walch et al. 2019 (31 subjects, Apple Watch, PSG labels, ODC-By-1.0) — so that
generalisation across independent cohorts is tested rather than assumed.

## Relevance of the requested data

The requested data is the only public source of a head-mounted accelerometer recorded
concurrently with expert-scored PSG. Without it, the central claim of our project — that a
non-contact pillow sensor can approach the performance of a worn sensor — remains an
untestable assertion, and the position shift can only be declared as a limitation. With it,
the shift becomes a number with a confidence interval.

Note that the aim is **not** to show that a pillow sensor outperforms wrist actigraphy; the
literature suggests it will not. The aim is to quantify **equivalence under constraint**: how
much performance is given up in exchange for a sensor the user does not have to wear. Both
possible outcomes are informative. A small loss supports the non-contact concept; a large loss
quantifies a limit that has not been quantified before and justifies a hardware redesign on
evidence rather than intuition.

## Intended deliverables

1. An undergraduate thesis (*Trabalho de Conclusão de Curso*) in Portuguese, defended at
   `[[INSTITUTION]]` around `[[EXPECTED DEFENCE DATE]]` and deposited in the institutional
   repository. It will report the Δκ transfer matrix, per-epoch and per-night metrics,
   Bland-Altman plots, and the inter-rater ceiling.
2. An open-source analysis pipeline (Python), published under a permissive licence. **Code
   only — no data, no data derivatives, and no redistribution of any kind.**
3. Possibly a short conference paper or preprint on the transfer result, should the supervisor
   judge the result worth disseminating.

We acknowledge the obligation, under the Data Use Agreement, to submit any manuscript or
abstract to the provider for review at least thirty days before disclosure, and to acknowledge
the provider and the provider's scientist as contributors of the data in every disclosure. We
will cite the reference paper (doi:10.1093/sleepadvances/zpaf094) and the dataset
(doi:10.34973/j6jf-9e62) in all outputs.

▸ **Question for the provider:** we would be grateful for guidance on whether an undergraduate
thesis deposited in an institutional repository constitutes a "Disclosure" for the purposes of
the thirty-day review clause, so that we can plan our submission timeline accordingly.

## Data handling, security and retention

| | |
|---|---|
| **Storage location** | A single encrypted workstation at `[[INSTITUTION]]` / the applicant's encrypted personal workstation, full-disk encryption enabled. No cloud storage, no shared drive, no public repository. |
| **Access** | Restricted to the two persons named above. No third party will access or process the data. |
| **Authorized processors** | **None.** All processing is local. No cloud compute service (Google Colab, Kaggle, or similar) will be used on this data. |
| **Re-identification** | No linkage, comparison or processing that could derive a participant's identity will be attempted, in accordance with the Agreement. |
| **Redistribution** | None. Data will not be committed to version control, shared, or published in any form. Published figures will present aggregate results only. |
| **Breach notification** | The provider will be notified promptly of any personal data breach. |
| **Withdrawal of consent** | Upon notification that a participant has withdrawn permission, all use of the relevant data will cease immediately and all copies will be deleted, with written confirmation on request. |
| **Proposed term** | `[[N]]` (three) years from the effective date. |
| **Retention after term** | We propose Option 1 of Clause 13: all data destroyed upon expiry, with written confirmation of complete deletion provided on request. |
| **Applicable law** | The recipient will comply with the Brazilian *Lei Geral de Proteção de Dados* (LGPD, Law 13.709/2018) in addition to the terms of the Agreement. |

We note that the European Commission adopted an adequacy decision for Brazil on 26 January
2026, recognising Brazil as providing an adequate level of data protection under Article 45
GDPR.

## Ethics

The project analyses previously collected, pseudonymised data from a completed study conducted
under the Donders Centre for Cognitive Neuroimaging blanket approval, protocol "Imaging Human
Cognition" (NL45659.091.14), approved by METC Oost-Nederland (2014/288). No new human data
collection is involved in the requested-data component of the project, and no contact with the
participants of the Wearanize+ study will occur.

▸ `[[Add here whether your institution's ethics committee requires a submission for secondary
use of existing pseudonymised data, and its status. If not required, say so explicitly — the
provider will want to know.]]`

## Current status

We are already working with the openly licensed **Wearanize+ OA** collection
(doi:10.34973/xrmf-5726, CC-BY-4.0) and with the Newcastle 2015 and Walch 2019 datasets, and
the analysis pipeline is under construction. The present request concerns the restricted
collection, and specifically the questionnaire data (PSQI, MADRE, PHQ-9), which is not part of
the open-access collection.

## References cited

- Sikder, N., Verkaar, L., Paltarzhytskaya, A., Acan, S., Bovy, L., Almazova, T., Krugliakova, E.,
  Rosenblum, Y., Krauledat, M., Dresler, M., & Zerr, P. (2026). Wearanize+: a multimodal dataset
  for evaluating wearable technologies in sleep research. *SLEEP Advances*, 7(1), zpaf094.
- Conley, S., et al. (2019). Agreement between actigraphic and polysomnographic measures of
  sleep in adults with and without chronic conditions: a systematic review and meta-analysis.
  *Sleep Medicine Reviews*.
- Meredith-Jones, K., et al. (2024). Comparison of wrist- and hip-worn accelerometer placements
  and algorithms for sleep assessment in children and adolescents. *IJBNPA*, 21(1).
  *(See also the published erratum, IJBNPA 21(1):62.)*
- Razjouyan, J., et al. (2017). Improving sleep quality assessment using wearable sensors by
  including information from postural/sleep position changes. *JCSM*.
- Walch, O., et al. (2019). Sleep stage prediction with raw acceleration and photoplethysmography
  heart rate data derived from a consumer wearable device. *Sleep*.
- van Hees, V. T., et al. (2015). *PLoS ONE*, 10(11), e0142533. *(Newcastle 2015 dataset)*
- Li, J., et al. (2025). *(actigraphy vs PSG in peri/post-menopausal women — see
  `docs/ML-DATASETS-E-PLANO.md` §0.1 for the full reference)*

> ⚠️ **Complete these references from the sources before sending.** `METODOLOGIA.md` is
> explicit: a search suggestion is not a citation. The entries above are abbreviated and
> some lack full bibliographic detail.

---

# §B · Tradução para conferência — NÃO ENVIAR

> Tradução fiel do §A, para você verificar o que está assinando. Onde o inglês é termo
> técnico ou contratual, o termo original vai entre parênteses.

## Título do projeto

Transferência de acelerômetro pulso→cabeça para classificação sono/vigília: quantificando o
custo em desempenho de tirar o sensor do corpo, rumo ao monitoramento não-contato em travesseiro

## Tipo de projeto

Trabalho de Conclusão de Curso (graduação), `[[DEPARTAMENTO / CURSO]]`, `[[INSTITUIÇÃO]]`,
`[[CIDADE, ESTADO, BRASIL]]`. Pesquisa acadêmica não comercial. Sem financiamento externo.
Sem parceiro industrial.

## Solicitante

| | |
|---|---|
| **Cientista recebedor / solicitante** | Vitor Mendes Oliverio, graduando, `[[CURSO]]`, `[[INSTITUIÇÃO]]` |
| **ORCID** | `[[ORCID]]` |
| **E-mail** | vitormendes4072@gmail.com |
| **Orientador** | `[[NOME DO ORIENTADOR, TITULAÇÃO]]` |
| **Instituição recebedora** | `[[INSTITUIÇÃO]]`, `[[CIDADE, ESTADO, BRASIL]]` |
| **Parceiros do projeto** | Nenhum |
| **Pessoas que precisam de acesso** | As duas pessoas acima, e ninguém mais. Cada uma fará seu próprio pedido no RDR com o próprio ORCID. |

## Contexto

A actigrafia de pulso é a alternativa de baixo custo estabelecida à polissonografia (PSG) para
estimar sono/vigília, mas exige que a pessoa use um aparelho a noite inteira. Nosso projeto
desenvolve o **Smart Dormio**, um monitor de sono não-contato: um único acelerômetro MEMS
triaxial (InvenSense MPU-6050) acoplado mecanicamente a um **travesseiro**. O dispositivo não
registra EEG, EOG nem fotopletismografia, de modo que suas afirmações se restringem
deliberadamente à classificação sono/vigília por época de 30 s e às métricas de período de
repouso e fragmentação dela derivadas. Não há tentativa de estadiamento do sono, por uma razão
física: REM e N3 são ambos estados quietos e, portanto, indistinguíveis para um acelerômetro.

Esse desenho levanta uma objeção metodológica que decide se o trabalho é cientificamente
defensável, e é a primeira objeção que qualquer banca vai fazer: **toda base pública de
acelerometria com rótulo de PSG foi gravada com o sensor preso ao corpo — quase sempre ao
pulso — enquanto nosso dispositivo fica sob a cabeça, desacoplado dela.** Um modelo treinado em
dado de pulso e aplicado em dado de travesseiro atravessa um deslocamento de domínio de posição
e de acoplamento mecânico, e o tamanho desse deslocamento hoje não está medido.

A literatura sugere que ele não é desprezível e pode não favorecer nossa posição.
Meredith-Jones et al. (2024), comparando cinco posições corporais contra PSG domiciliar,
relatam acurácia geral maior no pulso (majoritariamente > 80%) do que em posições próximas ao
centro de massa (geralmente < 80%), com especificidade "consideravelmente melhor" no pulso do
que na cintura, enquanto a sensibilidade foi maior perto do centro de massa. O mecanismo é
intuitivo e é o que importa para nós: a especificidade depende de flagrar a pessoa *acordada*,
e um pulso acordado na cama se mexe muito, ao passo que uma cabeça acordada no travesseiro pode
não se mexer nada. Em contrapartida, Razjouyan et al. (2017) mostraram que um sensor único no
tórax, combinando mudança de postura com aceleração corporal, superou a aceleração de pulso
isolada (85,8% contra 79,8% de acurácia), o que sugere que features derivadas de orientação
podem compensar parte da perda.

Nenhum dos dois resultados diz o que acontece na cabeça. **Não encontramos nenhuma base pública
além do Wearanize+ que contenha um acelerômetro na cabeça gravado concomitantemente a PSG
pontuada por especialista.** É exatamente por isso que estamos solicitando este dataset.

## Pergunta de pesquisa

**Quanto se perde de desempenho de classificação sono/vigília, medido pelo kappa de Cohen,
quando um modelo treinado em acelerometria de pulso é aplicado sem modificação a acelerometria
de cabeça gravada na mesma noite, dos mesmos participantes, sob os mesmos rótulos de PSG?**

Perguntas secundárias:

1. Como essa perda se compara à perda no sentido inverso (cabeça → pulso) e à posição da coxa
   (ActivPAL) — ou seja, a degradação é propriedade da posição de destino ou do sentido da
   transferência?
2. Acrescentar features derivadas de orientação (ângulo de postura e sua variação entre épocas)
   reduz a perda de transferência, como Razjouyan et al. (2017) preveriam?
3. Como a perda de transferência se compara ao **teto inter-avaliador** dado pelas duas
   pontuações manuais independentes incluídas no dataset? Uma perda menor que a discordância
   entre dois humanos é um resultado qualitativamente diferente de uma perda maior que ela.

## Por que os dados do Wearanize+, especificamente

Três propriedades — e não conhecemos outra base pública que tenha as três:

1. **Um acelerômetro triaxial na cabeça** (headband Zmax, 256 Hz, em g). A cabeça é o proxy
   cinemático mais próximo disponível do que um sensor em travesseiro sente, porque um sensor
   em travesseiro mede a carga que a cabeça aplica ao travesseiro. Nenhuma outra base pública
   com rótulo de PSG oferece isso.
2. **Três posições de sensor gravadas simultaneamente — cabeça, pulso (Empatica E4, 32 Hz) e
   coxa (ActivPAL, 20 Hz) — compartilhando um único conjunto de rótulos de PSG da mesma noite.**
   Isso transforma o deslocamento de posição de limitação declarada em grandeza mensurável:
   treina numa posição, testa em outra, relata a queda. Comparações entre coortes ou entre
   estudos não conseguem isolar posição de população, protocolo e pontuador; um desenho
   intra-noite e intra-sujeito consegue.
3. **Aceleração triaxial bruta em unidades físicas, não contagens de atividade proprietárias.**
   Isso é decisivo para nós e exclui a maior parte das grandes bases de actigrafia. *Activity
   counts* são a saída de um algoritmo não divulgado do fabricante e não têm unidade física;
   não existe função publicada que mapeie aceleração de MPU-6050 nelas, então um modelo
   treinado em counts não roda sobre o dado do nosso dispositivo. Aceleração é grandeza física
   e transfere.

A pontuação manual pelo manual da AASM, feita por especialistas em resolução de 30 s, e a
sincronização manual dos dispositivos por acelerômetro descrita no artigo de referência são o
que torna o alinhamento sinal-rótulo confiável o bastante para que esta comparação signifique
alguma coisa.

▸ **Dados de questionário (só na coleção restrita).** Solicitamos adicionalmente as respostas
do PSQI e do PHQ-9 para testar se a perda de transferência pulso→cabeça é maior em
participantes com pior qualidade de sono autorrelatada. A literatura de actigrafia relata
consistentemente que a acurácia sono/vigília declina conforme aumenta o distúrbio do sono
(Conley et al., 2019; Li et al., 2025); se a perda de transferência seguir o mesmo padrão, é
uma limitação que um dispositivo em travesseiro precisa declarar. Essa estratificação é
**secundária** à pergunta principal, e seguiríamos sem ela se o dado de questionário não puder
ser compartilhado.

## Métodos planejados

**Escopo.** Classificação binária sono/vigília por época de 30 s. Sem estadiamento. Rótulos de
PSG mapeados como: 0 → vigília; 1–4 (N1, N2, N3, REM) → sono; −1 (não pontuável) → época
descartada.

**Pré-processamento.** Todos os canais de acelerômetro são reamostrados para uma grade comum de
32 Hz (a taxa nativa do Empatica E4 e a menor taxa comum viável entre os dispositivos e o nosso
próprio hardware) e janelados em 30 s, alinhados aos rótulos de PSG sem reamostrar rótulo.

**Features.** Oito por época, todas invariantes à orientação do sensor, já que um sensor solto
num travesseiro tem orientação arbitrária e mutável: média, desvio-padrão e máximo do ENMO
(`max(|a|/g − 1, 0)`); área de magnitude do sinal (SMA); taxa de cruzamento por zero do sinal
sem DC; fração da época acima de um limiar de movimento; ângulo de postura
`atan2(az, sqrt(ax² + ay²))`; e a variação desse ângulo entre épocas. Cada época carrega também
as features das ±2 épocas vizinhas. Toda feature é calculável num microcontrolador ESP32 em
ponto flutuante de precisão simples, sem bufferizar a noite inteira — essa restrição é
deliberada, porque uma feature que o dispositivo não consegue calcular não pode fazer parte de
um modelo implantável.

**Modelos, em ordem crescente de complexidade, sem pular nenhum.** (0) O baseline degenerado
"sempre dormindo", que numa noite de PSG acerta tipicamente 85–90% e que relatamos primeiro,
explicitamente, porque qualquer número de acurácia é vazio ao lado dele. (1) Cole-Kripke e
Sadeh, os algoritmos clássicos de actigrafia. (2) Regressão logística sobre o conjunto de
features, pela interpretabilidade. (3) Random forest / gradient boosting. (4) Suavização
temporal (mediana móvel ou HMM de dois estados). Uma CNN 1-D sobre a janela bruta só será
tentada se houver tempo e se vencer o passo 3 de forma clara.

**O experimento de transferência — a contribuição original.** Uma matriz 3×3 sobre as três
posições de sensor. Para cada par ordenado (posição de treino, posição de teste), o modelo é
treinado na posição de treino e avaliado sem modificação na posição de teste, usando as mesmas
noites dos mesmos sujeitos e os mesmos rótulos de PSG. A grandeza relatada é **Δκ**, a queda do
kappa de Cohen em relação à diagonal de posição casada. A célula de interesse é **treino =
pulso, teste = cabeça**. Até onde sabemos, esta é a primeira medição direta dessa grandeza.

**Validação.** Divisões por **sujeito**, nunca por época, já que épocas de uma mesma noite são
fortemente autocorrelacionadas e embaralhar por época infla a acurácia de forma espetacular e
falsa. Sementes aleatórias e arquivos de configuração são fixos e versionados junto de cada
resultado relatado.

**Métricas.** Por época: sensibilidade (sono), **especificidade (vigília)**, kappa de Cohen, F1
e matriz de confusão. A especificidade é relatada com destaque porque é onde a classificação
sono/vigília por acelerômetro falha — ficar deitado e imóvel acordado é indistinguível de
dormir para um acelerômetro — e porque relatá-la é o teste de honestidade deste tipo de
trabalho. Por noite: erro de tempo total de sono, WASO e latência de início do sono, com
gráficos de Bland-Altman mostrando viés sistemático e limites de concordância. Onde o dataset
fornece duas pontuações manuais independentes, a concordância entre elas é calculada e relatada
como teto realista de desempenho.

**Coortes independentes.** Os modelos serão avaliados adicionalmente em duas bases de licença
aberta já em mãos — Newcastle 2015 (28 sujeitos, GENEActiv nos dois pulsos a 85,7 Hz, rótulos
de PSG, CC-BY-4.0) e Walch et al. 2019 (31 sujeitos, Apple Watch, rótulos de PSG, ODC-By-1.0) —
de modo que a generalização entre coortes independentes seja testada, e não presumida.

## Relevância dos dados solicitados

Os dados solicitados são a única fonte pública de acelerômetro montado na cabeça gravado
concomitantemente a PSG pontuada por especialista. Sem eles, a afirmação central do projeto —
de que um sensor não-contato em travesseiro pode se aproximar do desempenho de um sensor
vestido — permanece uma asserção não testável, e o deslocamento de posição só pode ser
declarado como limitação. Com eles, o deslocamento vira um número com intervalo de confiança.

Note que o objetivo **não** é mostrar que um sensor em travesseiro supera a actigrafia de
pulso; a literatura sugere que não vai. O objetivo é quantificar **equivalência sob
restrição**: quanto de desempenho se abre mão em troca de um sensor que o usuário não precisa
vestir. Os dois desfechos possíveis são informativos. Perda pequena valida o conceito
não-contato; perda grande quantifica um limite que ninguém quantificou antes e justifica um
redesenho de hardware com evidência em vez de intuição.

## Entregáveis previstos

1. Um Trabalho de Conclusão de Curso em português, defendido em `[[INSTITUIÇÃO]]` por volta de
   `[[DATA PREVISTA DE DEFESA]]` e depositado no repositório institucional. Relatará a matriz
   de transferência Δκ, as métricas por época e por noite, os gráficos de Bland-Altman e o teto
   inter-avaliador.
2. Um pipeline de análise de código aberto (Python), publicado sob licença permissiva.
   **Apenas código — sem dados, sem derivados de dados, e sem redistribuição de qualquer tipo.**
3. Possivelmente um artigo curto de conferência ou preprint sobre o resultado de transferência,
   caso o orientador julgue que vale a divulgação.

Reconhecemos a obrigação, sob o Acordo de Uso de Dados, de submeter qualquer manuscrito ou
resumo ao provedor para revisão com pelo menos trinta dias de antecedência da divulgação, e de
reconhecer o provedor e o cientista do provedor como contribuidores dos dados em toda
divulgação. Citaremos o artigo de referência (doi:10.1093/sleepadvances/zpaf094) e o dataset
(doi:10.34973/j6jf-9e62) em todos os produtos.

▸ **Pergunta ao provedor:** agradeceríamos orientação sobre se uma monografia de graduação
depositada em repositório institucional constitui "Divulgação" (*Disclosure*) para efeito da
cláusula de revisão de trinta dias, para que possamos planejar nosso cronograma de submissão.

## Tratamento, segurança e retenção dos dados

| | |
|---|---|
| **Local de armazenamento** | Uma única estação de trabalho criptografada em `[[INSTITUIÇÃO]]` / a estação pessoal criptografada do solicitante, com criptografia de disco inteiro ativada. Sem nuvem, sem drive compartilhado, sem repositório público. |
| **Acesso** | Restrito às duas pessoas nomeadas acima. Nenhum terceiro acessará ou processará os dados. |
| **Processadores autorizados** | **Nenhum.** Todo o processamento é local. Nenhum serviço de computação em nuvem (Google Colab, Kaggle ou similar) será usado sobre estes dados. |
| **Reidentificação** | Nenhum vínculo, comparação ou processamento que possa derivar a identidade de um participante será tentado, conforme o Acordo. |
| **Redistribuição** | Nenhuma. Os dados não serão commitados em controle de versão, compartilhados ou publicados sob qualquer forma. Figuras publicadas apresentarão apenas resultados agregados. |
| **Notificação de incidente** | O provedor será notificado prontamente sobre qualquer violação de dados pessoais. |
| **Retirada de consentimento** | Ao ser notificado de que um participante retirou a permissão, todo uso do dado correspondente cessará imediatamente e todas as cópias serão apagadas, com confirmação por escrito mediante solicitação. |
| **Prazo proposto** | `[[N]]` (três) anos a contar da data de vigência. |
| **Retenção após o prazo** | Propomos a Opção 1 da Cláusula 13: todos os dados destruídos ao término, com confirmação escrita da deleção completa mediante solicitação. |
| **Lei aplicável** | O recebedor cumprirá a Lei Geral de Proteção de Dados (LGPD, Lei 13.709/2018) além dos termos do Acordo. |

Registramos que a Comissão Europeia adotou decisão de adequação para o Brasil em 26 de janeiro
de 2026, reconhecendo o Brasil como provedor de nível adequado de proteção de dados nos termos
do Artigo 45 do GDPR.

## Ética

O projeto analisa dados pseudonimizados previamente coletados, de um estudo concluído conduzido
sob a aprovação-guarda-chuva do Donders Centre for Cognitive Neuroimaging, protocolo "Imaging
Human Cognition" (NL45659.091.14), aprovado pelo METC Oost-Nederland (2014/288). Nenhuma nova
coleta de dados humanos está envolvida no componente do projeto que usa os dados solicitados, e
não haverá contato com os participantes do estudo Wearanize+.

▸ `[[Acrescente aqui se o comitê de ética da sua instituição exige submissão para uso
secundário de dados pseudonimizados já existentes, e o status dela. Se não exigir, diga isso
explicitamente — o provedor vai querer saber.]]`

## Situação atual

Já estamos trabalhando com a coleção aberta **Wearanize+ OA** (doi:10.34973/xrmf-5726,
CC-BY-4.0) e com as bases Newcastle 2015 e Walch 2019, e o pipeline de análise está em
construção. O presente pedido diz respeito à coleção restrita, especificamente aos dados de
questionário (PSQI, MADRE, PHQ-9), que não fazem parte da coleção aberta.

---

# §C · Versão condensada (≤300 palavras) — para colar no Anexo II do `.docx`

> **297 palavras, contadas com `wc -w`.** O Anexo II do `DTA_Wearanize_nonEU_v1.docx` exige
> no máximo 300 (`docs/WEARANIZE-ACESSO.md` §8.1) — o §A não cabe, este cabe. Condensado do §A,
> mesmos fatos e números, sem cortar nenhuma alegação (só o desenvolvimento). Preencha
> `[[colchetes]]` do §A normalmente no resto do formulário; este texto vai só na caixa do
> Anexo II.

Background: Wrist actigraphy is the established alternative to polysomnography (PSG) for
sleep/wake estimation, but requires wearing a device overnight. We are developing Smart
Dormio, a non-contact sleep monitor: a single triaxial accelerometer (MPU-6050) coupled to a
pillow, with claims restricted to sleep/wake classification per 30-second epoch. Every public
PSG-labelled accelerometry dataset was recorded with the sensor on the body -- almost always
the wrist -- while our device sits under the head, uncoupled from it. The size of that domain
shift is unmeasured.

Research question: How much sleep/wake classification performance (Cohen's kappa) is lost when
a model trained on wrist accelerometry is applied unchanged to head accelerometry, recorded the
same night from the same participants under the same PSG labels?

Why Wearanize+: to our knowledge the only public dataset with three body-worn accelerometers
(head/Zmax, wrist/Empatica, thigh/ActivPAL) recorded simultaneously with expert PSG scoring on
the same night, in physical units rather than proprietary activity counts. This turns the
position shift from a declared limitation into a measurable quantity.

Planned methods: Eight orientation-invariant kinematic features per 30-second epoch (ENMO
statistics, signal magnitude, zero-crossing rate, active fraction, posture angle and its
inter-epoch change), computed identically across positions. Leave-one-subject-out logistic
regression is trained on one position and tested unchanged on another, across all position
pairs; the primary outcome is the kappa drop for train=wrist/test=head versus same-position
performance. Inter-rater agreement between the dataset's two manual PSG scorers is reported as
a performance ceiling. Models are additionally validated on two independent open cohorts
(Newcastle 2015, Walch 2019).

Intended deliverables: an undergraduate thesis (Trabalho de Conclusao de Curso) reporting the
cross-position kappa-drop matrix, deposited in the institutional repository; and an open-source
analysis pipeline (code only, no data or derivatives). Any manuscript will be shared with the
provider for review before submission, per the Agreement.

---

## Notas de revisão — leia antes de mandar

1. ⚠️ **Decida se vai mesmo pedir o acesso restrito.** O §0 do `WEARANIZE-ACESSO.md` mostra que
   todo o experimento cabe na coleção aberta. Se você não for usar os questionários, o custo
   (assinatura institucional, jurídico, meses de espera) não se paga.
2. ⚠️ **A "Situação atual" e as partes marcadas com ▸ pressupõem que você já baixou a OA.**
   Se ainda não baixou, ou baixe antes de enviar, ou reescreva essas partes. **Não afirme o que
   não é verdade** — é o mesmo princípio do `METODOLOGIA.md`.
3. ⚠️ **Tabela "Processadores autorizados" diz "Nenhum — tudo local".** Se você pretende treinar
   em Colab, isso é falso e vira violação contratual. **Decida agora e escreva a verdade.**
4. ⚠️ **As referências estão abreviadas.** Complete na fonte antes de enviar.
5. ⚠️ **Fale com o orientador antes de enviar qualquer coisa.** O DUA precisa de assinatura
   institucional (`WEARANIZE-ACESSO.md` §3.3) — mandar um plano de pesquisa sem o orientador
   saber cria um compromisso que você não pode cumprir sozinho.
6. 📌 O plano promete um baseline trivial, especificidade em destaque e teto inter-avaliador.
   **Isso é bom** — é o que o `ML-DATASETS-E-PLANO.md` §0.2 e §9 já exigiam, e é o que separa
   um trabalho honesto de um que a banca desmonta em trinta segundos. **Não retire na revisão.**
