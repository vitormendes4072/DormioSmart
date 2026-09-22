# Smart Dormio — bases públicas de sono e plano de execução do ML

> ## 🔄 Revisão de 2026-09-14 — o que mudou
>
> Uma segunda rodada **abriu os arquivos** da coleção aberta `Wearanize+ OA`
> (`10.34973/xrmf-5726`) em vez de ler só a documentação. Três consequências:
>
> 1. **O DUA saiu do caminho crítico.** A coleção aberta, CC-BY-4.0 e sem cadastro, tem os
>    três acelerômetros e a PSG pontuada. O `ML-03` roda nela com **N = 92**. O DUA da
>    coleção restrita destrava **só os questionários**.
> 2. **A nota ⁱ do §2.1 estava errada** na via de solução que propunha (o cabeçalho EDF não
>    declara a faixa do sensor). Substituída pela **nota ʲ**, que resolve as células do Zmax,
>    do E4 e do ActivPAL medindo a grade de quantização nos arquivos.
> 3. **A taxa do Zmax deixou de ser 🟡 e virou ✅: 256 Hz**, confirmada em 300 canais.
>
> Procedimento, evidência e armadilhas técnicas: **`docs/WEARANIZE-ACESSO.md`**.
> Seções tocadas: §2.1 (tabela + notas ᵉ, ⁱ, ʲ), §3 (quadro e seção do Wearanize+), §4, §8.

> **Pesquisa feita em 2026-09-10 · referências verificadas na fonte em 2026-09-10.**
> Atualiza e amplia o `docs/DATASET.md` (levantamento de
> 2026-05-31, item `DEC-01`), que continua válido na conclusão central e ficou **defasado
> em duas coisas importantes**: surgiu um dataset novo em dezembro de 2025 que muda a
> recomendação, e a análise anterior não distinguia *aceleração bruta* de *contagens de
> atividade proprietárias* — distinção que decide se um dataset transfere ou não.
>
> Cobre: **(§0) o que o hardware sustenta, com números e fontes** · (§1) a pergunta que o ML
> pode responder · (§2) o problema de construto · (§3) as bases, uma a uma ·
> (§4) a recomendação · (§5) o que ela obriga o projeto a fazer · (§6) o feedback ao usuário ·
> (§7–§9) o plano de execução · (§10) a ordem.
>
> **Se for ler só uma seção, leia o §0.** Ele responde à pergunta "só com um MPU6050 dá para
> monitorar sono com base científica?" e é a fundamentação de todo o resto. O texto de
> limitações pronto para o TCC está em **`docs/LIMITACOES-TCC.md`**.

---

## §0. O que o hardware sustenta — a evidência, com números

> Esta seção existe porque a pergunta *"só com um MPU6050 dá para monitorar sono com base
> científica?"* precisa de resposta com número e fonte, não com opinião. Ela é a
> fundamentação do escopo declarado no `README.md`, e é o material bruto do texto de
> limitações (`docs/LIMITACOES-TCC.md`).
>
> **Regra desta seção:** cada número está colado à fonte que o produziu, com a população em
> que foi medido. Número de um estudo não é atribuído a outro, e faixa citada em revisão
> sem fonte primária localizada está marcada como tal.
>
> ✅ **Estado das citações (verificação de 2026-09-10).** A autoria, o ano, o veículo e o DOI
> de **todas** as referências do §0 foram confirmados na fonte (PubMed/Europe PMC, texto
> completo). Não há mais trabalho citado "pelo título por falta de autoria". O que
> **permanece** marcado está listado no bloco de pendências ao final das Fontes, e são
> **duas frases citadas**, não referências.
>
> Ainda assim, o `METODOLOGIA.md` continua valendo: *sugestão de busca ≠ citação*. **Abra
> cada artigo antes de citá-lo no TCC** — as referências abaixo estão completas o bastante
> para montar a ABNT sem inferência, mas ler o trabalho é outra coisa.

### §0.1 · Sono × vigília: o que a literatura mede

| Estudo | População | Sensibilidade<br>(detectar sono) | Especificidade<br>(detectar vigília) | Acurácia |
|---|---|:---:|:---:|:---:|
| **Walch et al., 2019** — Apple Watch, movimento **+ FC + proxy circadiano**, rede neural | 31 adultos, 1 noite de PSG em laboratório (Univ. de Michigan) | 93% | **59,6%** | 90% |
| **Ode et al., 2022 (ACCEL)** — **só aceleração bruta** do braço, features de *jerk* | 25 voluntários saudáveis japoneses, 32 noites com PSG, LOOCV | 96,13 ± 5,61% | **80,18 ± 12,71%** | 91,71 ± 4,80% |
| **Li et al., 2025** — MotionWatch8 (actígrafo clínico de pulso) | 16 mulheres peri/pós-menopausa (51,4 ± 4,2 anos), 59 noites, laboratório a 30 °C | 94,8% | **33,1%** | 87,3% |
| **Conley et al., 2019** — meta-análise, **valor agrupado de "actigrafia" em geral** | 49 estudos, 1 582 participantes | 83% (DP 12,0) | **51%** (DP 19) | 82% (DP 7) |

**O padrão é constante e é o que interessa:** a sensibilidade fica sempre alta (83% no valor
agrupado, ~95% nos estudos individuais) e a especificidade varia de **33% a 80%**, com média
agrupada de **51%**. Acertar sono é fácil — quase tudo é sono. O número que diz se o
aparelho está de fato medindo é a **especificidade**, e é ela que oscila.

O melhor resultado da tabela (ACCEL, 80,2%) é também o que mais alerta: **desvio-padrão de
±12,7 pontos**. Em parte dos sujeitos o método desaba. Média sem dispersão, neste domínio,
esconde exatamente o caso que importa — e note que a linha de Conley traz desvio de 19
pontos na especificidade agrupada, o que diz a mesma coisa em escala de literatura inteira.

> ⚠️ **Sobre a linha de Li et al.:** a população é estreita — 16 mulheres na menopausa, em
> câmara a 30 °C, num protocolo desenhado para estudar fogachos. **Não é um valor genérico
> de "actigrafia clínica"** e não deve ser citado como tal. Está aqui porque é uma medição
> bem documentada de um actígrafo de grau clínico contra PSG, e porque os autores publicam
> sensibilidade, especificidade *e* acurácia juntas — o que permite a conta do §0.2.
>
> ✅ **Se o TCC precisar de um número genérico de "actigrafia de referência", use a linha de
> Conley et al. (2019)**, não a de Li et al.: 83% / 51% / 82%, agrupados sobre 49 estudos e
> 1 582 participantes. É o valor com fonte nomeada, população ampla e dispersão publicada.
> No subgrupo de adultos saudáveis (18 estudos, n = 461) os valores são 89% / 53% / 88%.

### §0.2 · Por que acurácia bruta é enganosa aqui — e a conta que prova

Numa noite de PSG a maior parte das épocas é sono. Então o classificador degenerado
**"sempre dormindo"** — que ignora o sensor por completo — já acerta a fração de sono da
noite.

Dá para recuperar essa fração dos próprios números publicados, porque
`acurácia = p·sensibilidade + (1−p)·especificidade`, onde `p` é a fração de épocas de sono.
Isolando `p = (acurácia − especificidade) / (sensibilidade − especificidade)`:

| Estudo | `p` implicado | "Sempre dormindo" acertaria | Acurácia publicada | Diferença |
|---|:---:|:---:|:---:|:---:|
| Li et al., 2025 (MotionWatch8) | 87,8% | **87,8%** | 87,3% | **−0,5 pt** |
| Walch et al., 2019 (mov. + FC + relógio) | 91,0% | **91,0%** | 90,0% | **−1,0 pt** |

**Nos dois casos, o classificador que não olha o sensor tem acurácia ligeiramente maior que
o método publicado.** Dois estudos independentes, populações e aparelhos diferentes, mesmo
resultado.

> **Esta conta é uma derivação nossa** a partir da sensibilidade, especificidade e acurácia
> publicadas por cada estudo — nenhum dos dois artigos apresenta esta comparação. A
> identidade usada é aritmética exata, não aproximação.

Isso **não** significa que actigrafia seja inútil: o classificador trivial não produz WASO,
latência, número de despertares nem fragmentação, que são justamente as saídas úteis. O que
a conta mata é a **acurácia como número de manchete**. Um TCC que publicar "89% de acurácia"
sem o baseline ao lado está publicando um número que a banca refuta em trinta segundos, com
uma linha de aritmética.

**Consequência operacional para o `ML-02`:** o baseline trivial não é uma formalidade
metodológica. É o primeiro resultado a ser medido, e provavelmente será competitivo.

### §0.3 · O viés conhecido: superestimar sono, e piorar em quem dorme mal

| Achado | Fonte |
|---|---|
| **Condições crônicas:** TST **+22,42 min** (IC 95%: 11,92 a 32,91) e eficiência do sono **+5,21%** (IC 95%: 1,41 a 9,00). Ambos **estatisticamente significativos.** SOL **−7,70 min** (IC 95%: −15,22 a −0,18), também significativo | Conley et al., 2019 (meta-análise de **96 estudos**, 4 134 participantes) |
| **Adultos saudáveis:** TST **+11,23 min** (IC 95%: **−3,98** a 26,44) e eficiência **+1,90%** (IC 95%: −0,65 a 4,44). ⚠️ **Os dois são tendências NÃO significativas** — o IC cruza o zero | Conley et al., 2019 |
| **Amostra completa (todos os estudos):** TST **+17,88 min** (IC 95%: 7,90 a 27,85) e eficiência **+3,77%** (IC 95%: 1,87 a 5,59) | Conley et al., 2019 |
| TST **+18,6 min**, eficiência **+3,5%**; latência **−11,2 min** e WASO **−9,1 min** | Li et al., 2025 (MotionWatch8) |
| A acurácia **declina conforme aumenta a severidade do distúrbio do sono** | Li et al., 2025 |
| Em populações com insônia, a superestimação de TST relatada varia de **14 a 60 min** | Paquet, Kawinska & Carrier, 2007 → ver a ressalva abaixo: é **fonte secundária**, e é a fonte correta a citar |

> ⚠️ **Correção importante em relação à versão anterior deste documento.** A linha dos
> **+11,2 min em adultos saudáveis** estava sendo apresentada como um achado, e **não é**:
> no artigo original ela é descrita como *"a non-statistically significant trend"*, com
> intervalo de confiança de −3,98 a +26,44 min — ou seja, compatível com zero. **O achado
> significativo da meta-análise é o do grupo com condições crônicas.** Citar os 11,2 min sem
> essa ressalva é atribuir a Conley et al. uma conclusão que eles explicitamente não tiram.
> Isso **fortalece** o argumento do §0.3, em vez de enfraquecê-lo: o viés é pequeno e incerto
> em quem dorme bem, e grande e comprovado em quem dorme mal.

> ✅ **A faixa de 14 a 60 min foi rastreada.** Ela aparece textualmente em
> **Paquet, Kawinska & Carrier (2007)**, *Sleep* 30(10):1362–1369: *"The majority of studies
> on insomniac populations have shown that actigraphy overestimates TST (from 14 to 60
> minutes) and SE compared to PSG"*. **Não existe fonte primária única para o número** — a
> faixa é uma agregação que os autores fazem sobre seis estudos: Kushida et al. (2001),
> Sivertsen et al. (2006), Edinger et al. (2004), Hauri & Wisbey (1992), Verbeek et al.
> (2001) e Lichstein et al. (2006). **Como citar no TCC:** atribuir a faixa a Paquet et al.
> (2007), declarando que se trata de síntese da literatura, ou ir a um dos seis primários e
> citar o número específico daquele estudo. **Não atribuir a faixa a "a literatura" sem
> nome.**

A causa é sempre a mesma e é física: **vigília deitada e imóvel é indistinguível de sono
para um acelerômetro.** Daí o corolário incômodo — *quem mais precisa da medida (sono
fragmentado, insônia) é quem recebe a medida pior*. E o dado de Conley et al. sustenta
exatamente esse corolário: o viés só vira estatisticamente detectável no grupo doente.

### §0.4 · Por que não há estadiamento: a razão é física, não algorítmica

| Estágio | O que o define | Tem assinatura no movimento? |
|---|---|:---:|
| N1 / N2 / N3 | Atividade **cortical**: fusos do sono, complexos K, ondas delta — fenômenos de EEG, em microvolts | ❌ |
| REM | **Movimento ocular** (EOG) + **atonia muscular** (EMG) | ❌ — e a atonia é *ausência* de movimento |

O detalhe que fecha a questão: **REM e N3 são ambos estados quietos.** Para um acelerômetro
são o mesmo estado. Não existe modelo que separe o que o sinal não distingue.

O que os wearables usam para separar REM de NREM não é movimento — é o **sistema autonômico**,
pela variabilidade da frequência cardíaca. É exatamente o que Walch et al. mediram: com
movimento **+ FC + proxy circadiano**, a classificação vigília/NREM/REM chega a **~72%**. A
FC carrega o sinal de estágio; o movimento entra como coadjuvante. **O Dormio não mede FC**
(e o §0.6 mostra que não pode).

A revisão sistemática de **Yuan, Hill, Kyle & Doherty (2024)** sobre estadiamento por
actigrafia é direta ao ponto:

> "a actigrafia mede apenas movimento de membro periférico, usando atividade como proxy de
> vigília e inatividade como proxy de sono e, por extensão, tem capacidade limitada de
> inferir os estágios do sono, pela ausência de sinais fisiológicos."
> — tradução de: *"actigraphy measures peripheral limb movement alone, using activity as a
> proxy for wake and inactivity as a proxy for sleep, and by extension, has limited capacity
> to infer the stages of sleep due to the lack of physiological signals."*

> ⚠️ **Correção de citação.** A versão anterior deste documento trazia aqui **outra frase
> entre aspas**, atribuída a esta mesma revisão, afirmando em substância que o método
> confunde vigília quieta com sono e por isso superestima o sono. **Aquela frase não foi
> localizada no texto publicado** (Yuan et al., 2024, *J Sleep Res*) — o documento citava o
> **preprint** de medRxiv (2023), cuja redação difere. A frase acima é a do artigo revisado
> por pares, conferida palavra por palavra no texto completo, e **diz a mesma coisa com mais
> força** para o argumento do §0.4.
>
> *A frase removida não é reproduzida aqui de propósito: um aviso que repete o texto errado
> entre aspas vira ele próprio a fonte do erro. O histórico do git preserva a versão
> anterior, se for preciso auditar.*

> **Isto é bom para o trabalho, não ruim.** A base que se usaria para tentar estadiamento é
> a mesma que documenta por que não dá. "Não fazemos estadiamento" deixa de ser ressalva
> defensiva e vira **conclusão fundamentada com citação**.

### §0.5 · A posição do sensor — a notícia desconfortável

A intuição diz que o travesseiro, mais central que o pulso, captaria melhor o movimento do
corpo. Para **esta tarefa específica**, a literatura de posicionamento diz o contrário:

> Acurácia geral **maior no pulso (majoritariamente > 80%)** do que em posições próximas ao
> centro de massa — cintura, coxa e lombar — onde ficou **geralmente < 80%**. A
> **sensibilidade** foi *maior* perto do centro de massa; a **especificidade** foi
> "consideravelmente melhor" no pulso do que na cintura.
> — **Meredith-Jones et al. (2024)**, 137 crianças e adolescentes de **8 a 16 anos**,
> 11 algoritmos, Actigraph wGT3X-BT (pulso, cintura) e Axivity AX3 (pulso, lombar, coxa),
> contra PSG domiciliar. Valores gerais do estudo: sensibilidade **91,8 ± 5,6%**,
> especificidade **63,8 ± 13,8%**.

⚠️ **A população é pediátrica**, e isso limita a transferência direta. Mas o **mecanismo** é
geral e é o que importa: a especificidade depende de **flagrar a pessoa acordada**. O pulso
acordado na cama se mexe muito — celular, coçar, virar de página. **A cabeça no travesseiro,
acordada e parada, não se mexe.**

> ⚠️ **Uma citação foi removida daqui, de propósito.** A versão anterior atribuía aos
> autores, **entre aspas**, uma conclusão que **trocava as duas métricas de lugar**: dava ao
> pulso a vantagem pelo critério errado. **A frase não foi localizada no texto completo do
> artigo** e contradiz o que ele relata — no estudo, é perto do centro de massa que a
> **sensibilidade** é maior; a vantagem do pulso está na **especificidade**. O bloco acima
> foi reescrito para dizer só o que está publicado.
>
> *A frase removida não é reproduzida aqui: repeti-la entre aspas num aviso é o jeito mais
> provável de ela voltar ao texto. Está no histórico do git, se for preciso auditar.*
>
> 📌 Nota bibliográfica: este artigo tem uma **errata publicada** (Meredith-Jones et al.,
> 2024b, *IJBNPA* 21(1):62) que corrige a lista de referências e o algoritmo da Tabela 5.
> **Ela não afeta a Tabela 3**, que é de onde vêm os números acima — mas a errata deve
> constar da referência ABNT.

**Conclusão honesta: é razoável esperar que o travesseiro tenha especificidade *pior* que o
pulso, não melhor.** Transferir um modelo treinado em pulso para o travesseiro provavelmente
degrada o resultado. Quem mede isso é o `VIA-01`; quem mede o salto entre posições *com
rótulo de PSG* é o `ML-03`, no `Wearanize+`.

**A contrapartida, e é real:** **Razjouyan et al. (2017)**, no *JCSM*, com sensor único no
tórax em 21 participantes com queixa de sono (50,8 ± 12,8 anos), mostrou que **combinar
mudanças de postura/posição com aceleração corporal melhorou a detecção de épocas de
sono/vigília em relação à aceleração de pulso isolada**: acurácia de **85,8% no tórax contra
79,8% no pulso** — **+6 pontos**. A correlação com a PSG nos parâmetros de sono também subiu
de fraca (*r* = 0,0–0,3, pulso) para moderada/forte (*r* = 0,4–0,8, tórax). Postura é onde
uma posição central ganha — e o MPU6050 entrega o ângulo de graça. É por isso que `angulo_z` e
`d_angulo` estão nas features do §7: elas não são enfeite, são a compensação prevista pela
literatura para a perda de especificidade da posição.

### §0.6 · Valeria acrescentar sensores? Ganho por custo e complexidade

| Sensor | Custo / complexidade | O que destrava | Veredito |
|---|---|---|:---:|
| **Postura/ângulo do próprio MPU6050** | **Zero** — já comprado, já no barramento | Ganho documentado em sono×vigília: **+6 pontos de acurácia** (Razjouyan et al., 2017 — §0.5) | ✅ **fazer** |
| **Luz ambiente + temperatura ambiente** (BH1750, BME280) | Baixo, ~R$ 10–40, mesmo I2C | **Nada** em sono×vigília. Ganha *contexto*: higiene do sono, correlação de ambiente com fragmentação. Resolve de passagem o `EXP-02` (hoje o MPU mede a temperatura do próprio chip, que não serve) | 🟡 opcional |
| **PPG / frequência cardíaca** | — | Seria o **maior ganho científico** (§0.4) | ❌ **impossível nesta forma** |
| **Microfone** | Baixo tecnicamente | Ronco, respiração | ❌ não |
| **EEG** | Alto | Estadiamento de verdade | ❌ autocontraditório |

**Por que PPG está descartado, e não é questão de esforço.** PPG exige contato óptico com
tecido perfundido. Não atravessa fronha e espuma. Para ter FC, o Dormio teria que virar um
wearable — **destruindo a proposta de valor declarada** ("não invasivo, sem contato com o
corpo") e a RQ junto.

A alternativa mecânica seria **BCG** — extrair o batimento da vibração. Aqui um número
encerra a discussão. **Leitão et al. (2018)**, na *Sensors*, ao construir um sistema de
aquisição de sismocardiograma de alta resolução, registra:

> - Os sinais de BCG/SCG têm energia **abaixo de 30 Hz** e amplitude da ordem de
>   **10 mg pico a pico**.
> - Os acelerômetros MEMS comerciais usados na literatura de SCG têm densidade de ruído
>   **acima de 98 µg/√Hz**, o que dá uma resolução de sistema de ~0,54 mg — *"roughly a
>   5-bit resolution for the full acquisition system which strongly compromises the signal
>   analysis"*.
> - O acelerômetro **que os autores projetaram** para viabilizar a aplicação tem densidade
>   de ruído **abaixo de 6,5 µg/√Hz**.
>
> O **MPU6050 tem 400 µg/√Hz** — folha de dados TDK InvenSense, PS-MPU-6000A-00 Rev. 3.4,
> §6.2, *Power Spectral Density*, medida **a 10 Hz, com AFS_SEL = 0 (fundo de escala ±2 g) e
> ODR = 1 kHz** (valor típico).

> ⚠️ **Correção em relação à versão anterior.** O documento afirmava que *"BCG/SCG exige
> densidade de ruído < ~6,5 µg/√Hz"*. **O artigo não diz isso.** Os 6,5 µg/√Hz são a
> **característica do sensor que os autores construíram**, não um limiar de requisito
> publicado. Atribuir a Leitão et al. um requisito que eles não enunciam é exatamente o tipo
> de erro que o `METODOLOGIA.md` proíbe. O que o artigo **de fato** sustenta é o parágrafo
> acima — e ele basta.

**A conta correta, e ela continua encerrando a discussão:** o MPU6050 tem **~4× mais ruído
que os acelerômetros comerciais** que o próprio artigo diz já comprometerem seriamente a
análise do sinal (400 vs. 98 µg/√Hz), e **~62× mais ruído** que o sensor dedicado que os
autores tiveram de projetar. E os trabalhos de BCG na cama usam **película piezoelétrica sob
o colchão**, não acelerômetro no travesseiro (ver a base de BCG avaliada no §3). Trocar de
transdutor, trocar de posição e acrescentar processamento de sinal cardíaco não é um item de
roadmap — é outro TCC.

**Microfone:** já está registrado como `EXP-01` condicional, e deve continuar condicional.
Muda o escopo declarado, transforma a conversa de LGPD (gravar o som de um quarto a noite
inteira é ordens de magnitude mais sensível que registrar aceleração) e convida a banca a
perguntar por que um trabalho de actigrafia grava áudio.

> ### Recomendação de escopo
>
> **Não acrescentar sensor de medição.** Fechar o escopo em **sono × vigília + postura** e
> fazer isso bem. O orçamento de complexidade vai para (i) as features de ângulo, que já
> são grátis, e (ii) opcionalmente luz e temperatura ambiente como **contexto**, jamais
> como evidência de estágio.
>
> O `HW-07` (segundo acelerômetro sob o colchão) permanece **condicional ao `VIA-01`** — e
> note que ele adiciona **acoplamento**, não modalidade. É a resposta certa para o problema
> certo, se o problema se confirmar.

### §0.7 · A afirmação máxima honesta

Tudo acima converge para uma frase, e é esta que o trabalho pode defender:

> **O dispositivo registra eventos de movimento durante o repouso de forma não invasiva e,
> a partir deles, estima o período de repouso e sua fragmentação, com desempenho da ordem
> do que a literatura de actigrafia reporta — reconhecidamente limitado na discriminação de
> vigília quieta, com tendência conhecida a superestimar o tempo de sono, e sem qualquer
> estadiamento de sono.**

Repare no que ela **não** faz: não promete estágios, não promete diagnóstico, não promete
nota de qualidade, e **declara o viés em vez de escondê-lo**. É o mesmo escopo que o
`README.md` e o `WEB-03` já assumem — ou seja, o produto já está calibrado. Falta o ML não
estragar isso.

### §0.8 · O enquadramento que sustenta a RQ

Há uma leitura de tudo isto que vale mais que qualquer número isolado:

> **O Dormio não precisa vencer o pulso. Ele precisa mostrar que uma posição não invasiva
> alcança desempenho comparável ao de um sensor vestido.**

Isso muda a natureza da contribuição. Se o objetivo fosse superar a actigrafia de pulso, o
trabalho estaria condenado antes de começar — o §0.5 explica por quê, e é física. Mas
**equivalência sob restrição** é outra pergunta, e é uma boa pergunta de engenharia:
*quanto se perde ao trocar um sensor vestido por um sensor que a pessoa não sente?*

Ela é específica, é mensurável (`VIA-01`, `VIA-02`, `ML-03`), **não está respondida na
literatura** — nenhuma base pública tem acelerômetro em travesseiro com rótulo de sono — e é
literalmente a RQ do trabalho. O resultado é publicável nos dois sentidos: se a perda for
pequena, valida o conceito; se for grande, quantifica um limite que ninguém quantificou e
justifica o `HW-07` com evidência em vez de intuição.

---

## §1. Antes de escolher a base: que pergunta o modelo pode responder?

A escolha do dataset não é a primeira decisão. A primeira é **o que o modelo vai afirmar**,
porque isso define que rótulo ele precisa — e, portanto, que dataset serve.

O Smart Dormio mede **uma coisa**: aceleração de um MPU6050 mecanicamente acoplado a um
travesseiro. Sem EEG, sem EOG, sem frequência cardíaca. Isso define um teto duro:

| Pergunta | O acelerômetro sozinho sustenta? | Comentário |
|---|:---:|---|
| Houve movimento nesta época? | ✅ | É o que o projeto já faz hoje. |
| A pessoa está dormindo ou acordada? | ⚠️ **com ressalva** | É a tarefa clássica da actigrafia. Funciona — mas com um viés conhecido e grave (§9). |
| Quando começou e terminou o período de repouso? | ✅ | Derivável da anterior, e é a métrica mais confiável da actigrafia. |
| Quantos despertares, e quão fragmentada foi a noite? | ✅ | Movimento é o sinal direto disso. |
| REM, N1, N2, N3? | ❌ | **Não.** Ver a caixa abaixo. |
| Apneia, ronco, distúrbio clínico? | ❌ | Fora do escopo e fora do hardware. |

> ### O achado que decide o escopo do ML
>
> **A evidência com números está no §0.4** — aqui vai só a conclusão. Walch et al. (2019),
> justamente a base que o `DEC-01` já havia escolhido, mostram que **movimento sozinho não
> estadia sono**: quem carrega o sinal de estágio é a **frequência cardíaca** (mais um proxy
> do relógio circadiano). O Smart Dormio não mede frequência cardíaca, e o §0.6 mostra que
> não pode medir na forma atual — PPG exige contato óptico com tecido perfundido.
>
> **Decisão recomendada:** o modelo do TCC classifica **sono × vigília por época**, e
> deriva daí métricas de período de repouso e fragmentação. Nada de REM.

---

## §2. O problema de construto, dito com todas as letras

Não existe dataset público de acelerômetro **dentro de um travesseiro** com rótulo de sono.
Isso o `DATASET.md` já dizia, e continua verdade em setembro de 2026. O que muda é o
entendimento de **quantos** saltos existem entre um dataset e o Dormio:

```
   dataset público                                        Smart Dormio
   ───────────────                                        ────────────
   1. POSIÇÃO       pulso / cabeça / coxa       ──────►    travesseiro (não-contato)
   2. ACOPLAMENTO   preso ao corpo, rígido      ──────►    espuma, complacente, amortecido
   3. TRANSDUÇÃO    accel bruto  OU  contagens  ──────►    accel bruto (MPU6050)
   4. TAXA          32 – 256 Hz                 ──────►    a definir (FW-05)
   5. POPULAÇÃO     saudáveis OU pacientes      ──────►    n=1, o autor
```

Cada salto custa desempenho. **O salto 3 é o mais subestimado e o mais fatal:** um dataset
de "actigrafia" pode não conter aceleração nenhuma — só *activity counts*, um número
inteiro por época produzido pelo firmware proprietário do fabricante, por um algoritmo não
publicado. Não há como reproduzir esse número a partir de um MPU6050. Um modelo treinado em
counts **não roda** sobre dado do Dormio, por mais parecido que o nome do sensor seja.

É por isso que a tabela do §3 tem uma coluna "bruto?" e ela vale mais que a coluna "N".

### §2.1 · A grandeza é a mesma? A tabela de comensurabilidade

> **Especificações verificadas em folha de dados / manual do fabricante / artigo do dataset,
> em 2026-09-10 (duas rodadas de busca).** Cada célula tem **estado explícito** e fonte ou
> justificativa. Nada foi preenchido por inferência nem por fonte comercial de terceiro.
>
> **Convenção de estado:**
> **✅ confirmado** — lido em fonte primária citável (folha de dados, manual do fabricante,
> artigo revisado por pares) ·
> **🟢 derivado do dado** — não publicado por ninguém, mas **medido por nós nos arquivos do
> dataset**, com o método declarado na nota ʲ ·
> **🟡 provável** — há fonte explícita, mas com ressalva (preprint, ou grupo de canais) ·
> **⛔ indisponível publicamente** — busca documentada, fabricante não publica ·
> **📄 no arquivo** — não publicado em texto, mas **legível no cabeçalho do próprio dado**
>
> 🔄 **Atualização de 2026-09-14 (2ª rodada).** As colunas do Zmax, do E4 e do ActivPAL foram
> revistas **abrindo os arquivos da coleção aberta Wearanize+ OA** — 100 `channels.tsv` e o
> cabeçalho EDF completo de `sub-005`. A nota ʲ registra o método e o que mudou. A nota ⁱ
> **estava errada na premissa** e foi corrigida.

Aceleração é uma **grandeza física**: tem dimensão (L·T⁻²), tem unidade SI, e qualquer
acelerômetro mede a mesma coisa (força específica). *Activity counts* **não são** grandeza
física: não têm unidade, e são a saída de um algoritmo não publicado. A diferença não é de
grau, é de natureza.

| | **MPU6050** (Dormio) | **GENEActiv** (Newcastle) | **Apple Watch** (Walch) | **Zmax Lite** (Wearanize+, cabeça) | **Empatica E4** (Wearanize+, pulso) | **ActivPAL** (Wearanize+, coxa) | **Actiwatch** (MESA) |
|---|---|---|---|---|---|---|---|
| **Grandeza** | ✅ Aceleração | ✅ Aceleração | ✅ Aceleração | ✅ Aceleração | ✅ Aceleração | ✅ Aceleração | ❌ *activity counts* |
| **Unidade entregue** | ✅ LSB → g → m/s² | ✅ g (SI, bruto não filtrado) ᵇ | ✅ **g** (ponto flutuante) ᵈ | ✅ LSB → g ⁱ | ✅ g | ✅ g | ❌ nenhuma |
| **Eixos** | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 | ✅ 3 | ❌ escalar |
| **Taxa** | ✅ progr. 4–1000 Hz (projeto: ≥42 Hz) ᵃ | ✅ **85,70 Hz** ᶜ | ✅ **~50 Hz** (20 Hz em 2 sujeitos) ᵈ | ✅ **256 Hz** ʲ | ✅ **32 Hz** ᶠ ʲ | ✅ **20 Hz** ᵍ ʲ | ✅ 1 valor / 30 s |
| **Faixa** | ✅ ±2/±4/±8/±16 g (projeto: **±8 g**) ᵃ | ✅ **±8 g** ᵇ ᶜ | ⛔ Apple não publica ᵈ | 🟢 **±2 g** — derivado ʲ | ✅ **±2 g** (padrão) ᶠ ʲ | 🟡 **±4 g?** — derivado ʲ | — |
| **Bits** | ✅ **16** ᵃ | ✅ **12** ᵇ | ⛔ ᵈ | 🟢 **12** — derivado ʲ | ✅ **8** (da faixa selecionada) ᶠ ʲ | 🟡 **10?** — derivado ʲ | — |
| **Resolução** | ✅ **0,244 mg/LSB** (±8 g) | ✅ **3,9 mg/LSB** ᵇ | ⛔ ᵈ | 🟢 **0,977 mg/LSB** (1/1024 g) ʲ | ✅ **15,6 mg/LSB** (1/64 g) ᶠ ʲ | 🟢 **7,81 mg/LSB** (1/128 g) ʲ | — |
| **Ruído (folha de dados)** | ✅ **400 µg/√Hz** ᵃ | ⛔ não publicada | ⛔ não publicada | ⛔ não publicada | ⛔ não publicada | ⛔ não publicada | — |
| **Ruído em repouso (medido por terceiro)** | — | 🟡 **medido, valor sob assinatura** ʰ | — | — | — | 🟡 **medido, valor sob assinatura** ʰ | — |
| **Comensurável com o Dormio?** | — | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ **impossível** |

<sub>
ᵃ TDK InvenSense, *MPU-6000/MPU-6050 Product Specification*, PS-MPU-6000A-00 Rev. 3.4 (2013), §6.2. O ruído é dado **a 10 Hz, AFS_SEL = 0 (±2 g), ODR = 1 kHz** — condição diferente da que o projeto pretende usar (±8 g). ⚠️ **Medir depois da solda, não presumir.**<br>
ᵇ ActivInsights, *GENEActiv Product Information Sheet* (jan/2025): "Range +/- 8g · Resolution 12 bit (3.9mg)". Frequências de registro selecionáveis 10–100 Hz.<br>
ᶜ van Hees *et al.* (2015), *PLoS ONE* 10(11) e0142533 — protocolo do dataset de Newcastle: "configured to collect data at 85.70 Hz with a ±8 g dynamic range", punho não dominante.<br>
ᵈ Walch *et al.* (2019): Apple Watch **Series 2 e 3**; aceleração "returned in units of g"; ~50 Hz, 20 Hz nos dois primeiros sujeitos; <3% do tempo com lacunas, interpoladas. **⛔ Fechado como indisponível.** Busca feita: (i) Apple não publica especificação do acelerômetro do Watch; (ii) o artigo não a informa; (iii) o *teardown* do Series 3 (iFixit) identifica um "Bosch gyro + accelerometer" por **código de marcação**, não por número de peça com folha de dados pública — e ainda que identificasse, a faixa e a ODR são **configuradas pelo firmware da Apple**, não determinadas pelo chip. **Consequência prática: nenhuma.** A documentação da Apple (`CMAcceleration`, Core Motion) define os campos `x`, `y`, `z` como "acceleration in G's (gravitational force)" em **ponto flutuante** — a quantização do ADC **não é observável** no dado entregue, então não há o que corrigir no pré-processamento.<br>
ᵉ ✅ **RESOLVIDO EM 2026-09-14: são 256 Hz, confirmado no arquivo.** *(Histórico: Sikder* et al. *(2026), revisado por pares, agrupava EEG + acelerômetro + PPG "at a sampling rate of 256 Hz" — ambíguo; Esfahani* et al. *(bioRxiv 2023) dizia "**all** with a sampling frequency of 256 Hz" — explícito, mas preprint.)* **A confirmação não dependeu de bibliografia nem do DUA:** a coleção **aberta** `Wearanize+ OA` foi baixada anonimamente e os 100 arquivos `channels.tsv` declaram `Zmax_ACCX/Y/Z … sampling_frequency = 256.0` em **300/300 canais**, sem exceção; o cabeçalho EDF confirma de forma independente, com **7 680 amostras por registro de 30 s** (= 256 Hz). **A célula deixa de ser 🟡 e passa a ✅.** Ver nota ʲ.<br>
ᶠ Empatica, *E4 wristband user's manual*, §2.1: "Sampling frequency: 32 Hz (Non customizable) · Default range ±2g · Ranges of ±4g or ±8g are selectable with custom firmware · **Resolution: 8 bits of the selected range**". Em ±2 g: 4 g / 256 = 0,015625 g = **15,6 mg/LSB**. Confirmado também em Sikder *et al.* (2026): E4 grava ACT triaxial a 32 Hz.<br>
ᵍ **⛔ Fechado como não documentado.** Sikder *et al.* (2026): "Activpal primarily records tri-axial ACT data at 20 Hz" — mas **o artigo não informa o modelo** (activPAL3 / activPAL4 / activPAL4pro), e faixa e bits dependem dele. Busca feita: texto completo do artigo (nada além de "PAL Technologies"); **protocolo do Healthy Brain Study** (Aarts *et al.*, 2021, *PLoS ONE* 16(12) e0260952) — **zero menções a activPAL** em 143 mil caracteres; `README.md` do repositório oficial do dataset (`Niloy333/Wearanize_plus`) — **vazio**; página do Radboud Data Repository — diz apenas "ActivPAL leg patch". Existem especificações por modelo em sites comerciais de terceiros; **não foram usadas** (não são fonte para um TCC). **Vias de resolução:** escrever aos autores, ou ler os metadados do arquivo quando o DUA sair. **Consequência prática: mínima** — a coxa é a posição mais distante do caso do Dormio, e as features do §7 são invariantes à escala do LSB.<br>
ʰ **🟡 Medido por terceiro independente; valores por marca em figura e suplemento.** **Lettink, van Wieringen, Altenburg, Chinapaw & van Hees (2024)**, *JMPB* 7(1), art. jmpb.2024-0003, **CC BY 4.0** (ficha completa nas Fontes). 64 acelerômetros de cinco marcas — Axivity, ActiGraph, **GENEActiv**, MOX e **activPAL** — em mesa vibratória, com **60 s sem movimento** antes de cada experimento; medida primária = **desvio-padrão do sinal bruto em repouso**, por eixo; 127 observações. Ruído difere entre marcas: MOX o mais alto (>12 mg de diferença), ActiGraph o mais baixo (>2,5 mg de diferença). ⚠️ **Os valores absolutos de GENEActiv e activPAL estão na Figura 3 e no Material Suplementar S3, e não foram extraídos** (figura é imagem; suplemento é arquivo à parte). ✅ **Mas o dado bruto é aberto** (Zenodo, CC BY, DOI 10.5281/zenodo.8160791): os números são **computáveis**. Ver §2.2.<br>
ⁱ ~~Hypnodyne não publica ficha técnica detalhada do ZMax… **📄 Resolvível no arquivo:** o EDF armazena, por canal, `physical minimum/maximum` e `digital minimum/maximum`… Abrir o cabeçalho responde às três células de uma vez.~~ 🔴 **ESTA NOTA ESTAVA ERRADA E FOI SUBSTITUÍDA PELA NOTA ʲ.** A primeira frase continua válida — a Hypnodyne de fato não publica ficha técnica, e o Dreamento expõe `ScaleAccel` sem publicar o fator. **O que estava errado é a via de solução.** O cabeçalho EDF **não** responde: no `sub-005` da coleção OA, `digital min/max` = `-32768 / 32767` (o span do contêiner EDF de 16 bits, não do sensor) e `physical min/max` traz os **extremos observados daquela gravação, diferentes por canal** (`Zmax_ACCX`: −2 a 1,144531; `Zmax_ACCY`: −1,56835 a 1,999023). O pipeline de conversão reescalou tudo para o span cheio do EDF. **Os campos do EDF descrevem a gravação, não o sensor.** A via que funciona é a da nota ʲ.<br>
ʲ **🟢 Derivado dos arquivos da coleção aberta `Wearanize+ OA` (DOI 10.34973/xrmf-5726), versão PlugNPlay v1.1, em 2026-09-14.** Método, e ele é reprodutível: (i) foram baixados os **100** arquivos `sub-NNN_task-sleep_channels.tsv` (um por participante, acesso anônimo via WebDAV — 100/100 a HTTP 200); (ii) `units` e `sampling_frequency` foram lidos diretamente do arquivo; (iii) faixa, bits e resolução foram derivados da **grade de quantização** dos campos `min_val`/`max_val` agregados sobre todos os participantes. **Taxas — confirmadas, não derivadas:** `Zmax_ACC*` = **256,0 Hz** em 300/300 canais, `Emp_ACC*` = **32,0 Hz** em 276/276, `ActivPal_ACC*` = **20,0 Hz** em 279/279; cada uma confirmada de forma independente pelo número de amostras por registro EDF de 30 s (7 680 / 960 / 600). **Zmax:** unidade `g`; extremos globais **−2,0** (exato) e **1,999023**; como `2 − 1,999023 = 1/1024` e todos os extremos observados caem na grade de 1/1024 g, segue faixa **±2 g**, resolução **1/1024 g = 0,977 mg/LSB** e 4 g ÷ (1/1024 g) = 4096 = **12 bits**. **Empatica E4:** unidade declarada **`g/64`**, extremos globais **−128 / +127** = inteiro de 8 bits com sinal ⇒ ±2 g e 1/64 g = **15,625 mg/LSB** — batendo exatamente com o manual (nota ᶠ) e com a derivação original deste documento. **ActivPAL:** unidade `g`, grade de **1/128 g = 7,8125 mg/LSB** (todos os extremos caem nela) — isto é 🟢 firme; já a faixa **±4 g** e os **10 bits** são 🟡, porque os extremos observados (−3,969 a +3,984 g) **não encostam na trava**, então 8 g ÷ (1/128 g) = 1024 = 2¹⁰ é a explicação coerente, não uma leitura. **O modelo do ActivPAL continua ⛔** (nota ᵍ). ⚠️ **Redação para o TCC:** estes valores são *derivados por nós dos dados*, não especificação de fabricante. Escrever "derivado dos arquivos do dataset", jamais "segundo a folha de dados". Detalhamento completo em **`docs/WEARANIZE-ACESSO.md` §6.2 e §6.3**.
</sub>

### §2.2 · O piso de ENMO imposto pelo ruído — derivação nossa

Uma consequência prática da tabela acima, e que **não está publicada em lugar nenhum**: o
ENMO é `max(|a|/g − 1, 0)` — tem um **retificador**. Em repouso o valor verdadeiro é zero,
mas o ruído flutua para os dois lados e o `max(·, 0)` corta só o lado negativo. **O ruído
não se cancela: vira um viés positivo.**

Com banda de 16 Hz (após reamostrar para 32 Hz):

| Sensor | Fonte de ruído considerada | σ por amostra | **Piso de `ENMO_media`** |
|---|---|:---:|:---:|
| **MPU6050** | Térmico, 400 µg/√Hz × √16 Hz | 1,6 mg | **≈ 0,64 mg** |
| **GENEActiv** | Quantização, 3,9 mg/√12 | 1,13 mg | **≥ 0,49 mg** |
| **Empatica E4** | Quantização, 15,6 mg/√12 | 4,5 mg | **≥ 1,95 mg** |

Fórmulas: ruído gaussiano → `E[max(δ,0)] = σ/√(2π) = 0,399·σ`; quantização uniforme →
`E[max(δ,0)] = q/8`.

**O que isso diz, e é contra-intuitivo:** o MPU6050 **não é o elo fraco**. O piso do E4 —
que é o sensor de pulso do Wearanize+ — é cerca de **3× o nosso**, e o do GENEActiv é da
mesma ordem. Em resolução, o E4 (15,6 mg/LSB) é **64× mais grosseiro** que o MPU6050 em
±8 g (0,244 mg/LSB).

> ⚠️ **Três ressalvas honestas, porque esta conta é nossa e não de um artigo:**
> 1. Para GENEActiv, E4 e ActivPAL só foi possível considerar a **quantização** — nenhum
>    desses fabricantes publica densidade de ruído. Os pisos deles são portanto **limites
>    inferiores**; os valores reais são mais altos. A comparação não é simétrica.
>    ✅ **E isso é verificável — Lettink et al. (2024) mediram exatamente isso.** A medida
>    deles é o **desvio-padrão do sinal bruto em repouso**, que é a mesma grandeza do nosso
>    σ. As diferenças *entre marcas* que eles reportam são de **2,5 a 12 mg**, o que implica
>    que os desvios absolutos estão na casa de **unidades de mg** — bem acima do nosso piso
>    de quantização (1,13 mg para o GENEActiv). **A assimetria é contra nós, não a nosso
>    favor:** subestimar o ruído dos aparelhos de pesquisa torna o argumento "o MPU6050 não
>    é o elo fraco" *mais difícil* de sustentar, não mais fácil. **Ele sobrevive assim
>    mesmo.**
>
>    📌 **Como fechar esta célula em cinco minutos, se quiser o número exato.** Duas vias,
>    ambas legítimas e abertas:
>    - **(a) Ler.** Figura 3 e Material Suplementar S3 do artigo — que é **CC BY**, não
>      pago. O site do editor bloqueia acesso automatizado, mas a **versão de registro está
>      aberta no repositório Pure do Amsterdam UMC** (link nas Fontes), e o acesso
>      institucional via Portal de Periódicos CAPES / CAFe também abre. O que pedir: *"o
>      desvio-padrão do sinal em repouso, por marca, da Figura 3 / Tabela S3"*.
>    - **(b) Computar.** O dado bruto dos experimentos está aberto no **Zenodo** (CC BY,
>      DOI 10.5281/zenodo.8160791, ~1,5 GB). Basta isolar os 60 s da condição sem movimento
>      e calcular o desvio-padrão por eixo. Isso preenche a célula com número próprio, e de
>      quebra é um exercício que usa o mesmo código do `ml/`.
> 2. Para o MPU6050 vale o inverso: o térmico domina e a quantização (0,07 mg) é
>    desprezível — mas o valor de folha de dados é medido em **±2 g**, e o projeto pretende
>    usar **±8 g**. **Medir após a solda.**
> 3. A conta de quantização assume ruído com *dither* (aproximadamente independente entre
>    amostras). Em repouso absoluto e sem agitação térmica, quantização vira um *offset*
>    determinístico, não ruído. Na prática há sempre dither; ainda assim, é aproximação.
>
> **O que fazer com isso:** é argumento de fundamentação, não resultado. A confirmação é o
> `CAL-01` — cujo critério de aceitação já registrado no `ROADMAP.md` (pose Z+ com ruído
> ~0,02 m/s² = 2 mg) coincide quase exatamente com o piso teórico do componente na banda do
> filtro de 21 Hz (`400 µg/√Hz × √21 = 1,8 mg`). O critério que já estava escrito é, portanto,
> bem escolhido.

---

## §3. As bases, uma a uma

### Quadro comparativo

| Base | N | Sensor / posição | Bruto? | Taxa | Rótulo | Acesso | Serve? |
|---|:---:|---|:---:|:---:|---|---|:---:|
| **Wearanize+ OA** | **130** (100 no PlugNPlay) | Zmax **cabeça** + E4 pulso + ActivPAL coxa | ✅ | **256 / 32 / 20 Hz** ✅ | **PSG manual ×2, AASM, 30 s** | ✅ **RDR aberto, CC-BY-4.0, SEM cadastro** | 🥇 |
| **Newcastle 2015** | 28 | GENEActiv, **dois pulsos** | ✅ | 85,7 Hz | **PSG, 30 s** | Zenodo, **CC-BY 4.0, sem cadastro** | 🥈 |
| **Walch 2019 (sleep-accel)** | 31 | Apple Watch, pulso | ✅ | ~50 Hz (20 Hz em 2 sujeitos) | **PSG, 5 classes** | PhysioNet **aberto**, ODC-By 1.0 | 🥉 |
| **DREAMT** | 100 | Empatica E4, pulso | ✅ | 32 Hz (ACC) | **PSG, 30 s** | PhysioNet **restrito** — assinar DUA | ⚠️ |
| **MESA / SHHS (NSRR)** | 2 000+ | Actiwatch Spectrum, pulso | ❌ **counts** | épocas de 30 s | PSG (noite) + actigrafia (7 dias) | Cadastro + **DUA + evidência de IRB** | ❌ |
| **BCG piezo (Figshare)** | 32 · 212 noites | Película piezo **sob o colchão** | ⚠️ outro transdutor | 140 Hz | **sem PSG, sem estágio** | Figshare, aberto | ❌ |
| **MMASH** | 22 | ActiGraph wGT3X-BT, pulso | ✅ | — | **sem PSG** | PhysioNet, ODbL 1.0 | ❌ |
| **UK Biobank** | 100 000+ | Axivity AX3, pulso | ✅ | 100 Hz, ±8 g | **sem PSG** (rótulo algorítmico) | Aplicação + **£500 / 3 anos** | ❌ |
| **Sleep-EDF Expanded** | 197 noites | — | — | — | PSG completo | PhysioNet aberto | ❌ **sem acelerômetro** |

<sub>`Bruto?` = o dataset entrega aceleração, e não contagens proprietárias de atividade. É a
coluna que decide se o dado transfere para um MPU6050. 🔄 **Linha do Wearanize+ atualizada em
2026-09-14:** as taxas foram confirmadas no arquivo (nota ʲ), e a coluna *Acesso* mudou —
existe uma coleção **aberta, CC-BY-4.0, sem cadastro e sem DUA**, com os três acelerômetros e
a PSG pontuada. Ver a seção do Wearanize+ abaixo e `docs/WEARANIZE-ACESSO.md`.</sub>

---

### 🥇 Wearanize+ — a base que mede o *domain shift* em vez de argumentar sobre ele

> ## 🔄 Revisão de 2026-09-14 — leia antes do resto desta seção
>
> Esta seção foi escrita supondo que a base útil estava atrás de um DUA. **Não está.**
> Existem **duas** coleções, e a aberta serve:
>
> | | **Wearanize+ OA** — `10.34973/xrmf-5726` | **Wearanize+** — `10.34973/j6jf-9e62` |
> |---|---|---|
> | Acesso | ✅ **Aberto, CC-BY-4.0, sem cadastro** | 🔒 DUA institucional, meses |
> | Três acelerômetros + PSG pontuada | ✅ sim | ✅ sim |
> | Pontuações manuais | ✅ **duas** | ⚠️ **uma** |
> | Unidade do acelerômetro do E4 | ✅ `g/64` (correta) | 🔴 `g/16` (**errada por fator 4**) |
> | Download por arquivo | ✅ um EDF por sujeito | ❌ 3 zips de 33–51 GB |
> | Questionários PSQI/MADRE/PHQ-9 | ❌ não | ✅ **o único motivo do DUA** |
>
> **Verificado abrindo os arquivos** (100 `channels.tsv` + cabeçalho EDF de `sub-005`,
> baixados anonimamente): o `ML-03` roda com **N = 92** (cabeça+pulso) ou **N = 86** (matriz
> 3×3 completa) na coleção **aberta**. Para comparar: Newcastle tem N=28 e Walch N=31.
>
> 🔴 **O bug de unidade não é detalhe.** Na v1.0 (restrita) a aceleração de pulso sai **4×
> maior** que a real. Pulso é o braço "treina" do `ML-03` — o experimento mediria um artefato
> de escala. **Use a OA.**
>
> **O DUA saiu do caminho crítico.** Procedimento, evidência e armadilhas em
> **`docs/WEARANIZE-ACESSO.md`**.

**O que é.** 130 adultos jovens saudáveis (18–39 anos, média 23,2), **uma noite cada, em
casa**, com PSG completa e três wearables simultâneos. Disponível: PSG de 118, Zmax de 122,
Empatica de 121, ActivPAL de 129. A PSG foi **pontuada manualmente** por técnicos
experientes, em épocas de 30 s, segundo o manual da AASM — e também automaticamente pelo
U-Sleep v2.0, com todos os conjuntos no dataset.

> ✅ **Disponibilidade real na coleção aberta, contada arquivo por arquivo (2026-09-14).**
> A versão **PlugNPlay** traz **100** participantes (os que têm PSG *e* Zmax *e* pontuação
> manual); a versão **raw**, os **130**. Dentro dos 100:
> Zmax **100**, Empatica **92**, ActivPAL **93**, `PSG_Manual_Scor1` **100**,
> `PSG_Manual_Scor2` **100** *(mas o arquivo de origem do 2º pontuador só existe para 96 —
> ver `WEARANIZE-ACESSO.md` §6.4)*, `PSG_USleep_score` **96**, `PSG_Pos.` **96**.
> Os 4 sujeitos incompletos são exatamente os gravados com Mentalab: `sub-115`, `sub-124`,
> `sub-129`, `sub-130`.

**Por que ela é a mais relevante para *este* projeto, especificamente:**

1. **O Zmax tem acelerômetro triaxial na CABEÇA.** É a peça que não existe em
   nenhuma outra base. Um sensor no travesseiro não mede o pulso nem a coxa: ele mede a
   **carga que a cabeça aplica ao travesseiro**. Movimento de cabeça é o proxy cinemático
   menos ruim disponível, e este é o único dataset público que o traz com rótulo de PSG.
   ✅ *Taxa: **256 Hz**, confirmado no arquivo em 2026-09-14* — `sampling_frequency = 256.0`
   nos 300 canais `Zmax_ACC*` dos 100 `channels.tsv` da coleção aberta, mais 7 680 amostras
   por registro EDF de 30 s. Não depende mais do preprint de Esfahani *et al.* nem da frase
   ambígua do artigo. Unidade **`g`**; faixa **±2 g**, **12 bits**, **0,977 mg/LSB** —
   estes três **derivados** da grade de quantização, não publicados por ninguém (nota ʲ do
   §2.1). Para o pré-processamento a consequência é pequena: reamostramos para 32 Hz de
   qualquer forma.
2. **Três posições, os MESMOS rótulos, a MESMA noite.** Isso permite um experimento que
   nenhuma outra base permite: treinar no pulso e testar na cabeça, treinar na cabeça e
   testar na coxa, e **medir a queda**. O trabalho para de dizer "a transferência é uma
   limitação declarada" e passa a dizer "a transferência custa X pontos de kappa, e aqui
   está a medida". Para uma banca, a diferença entre as duas frases é enorme.
3. **Sincronização por acelerômetro, feita à mão.** Os autores pediram que o participante
   pulasse cinco vezes antes de dormir e ao acordar, e depois sincronizaram os aparelhos
   **por inspeção visual dos acelerômetros triaxiais**. O alinhamento entre sinal e rótulo
   é confiável, que é onde datasets multi-dispositivo normalmente falham.

**Ressalvas honestas:**

- **Cabeça ≠ travesseiro.** O Zmax é preso à testa: acoplamento rígido, ganho ~1. O
  travesseiro é espuma: complacente, amortecido, e só registra movimento que **carrega**
  o travesseiro. Movimento de corpo com a cabeça parada é a incógnita — a mesma que o
  `VIA-01` existe para responder. A cabeça reduz o salto de posição, não o elimina.
- **População jovem e saudável.** Média de 23 anos. Generaliza mal para idosos ou pacientes.
- **Uma noite por participante.** Sem variabilidade intra-sujeito.
- **É novo** (publicado em dez/2025). Pouca ferramenta de comunidade, pouco benchmark
  para comparar. Você vai abrir trilha.
- ~~**Acesso em duas partes:** a coleção *Wearanize+ OA* é aberta e baixa direto; a completa
  exige **assinar um DUA** com plano de pesquisa, submetido via ORCID. Planeje o prazo.~~
  ✅ **Corrigido em 2026-09-14.** A ressalva estava certa na forma e errada no peso: dava a
  entender que a parte útil estava atrás do DUA. **A coleção aberta `Wearanize+ OA`
  (`10.34973/xrmf-5726`, CC-BY-4.0) tem os três acelerômetros, a PSG pontuada e duas
  pontuações manuais** — e baixa hoje, sem cadastro, via WebDAV anônimo. O DUA da coleção
  restrita (`10.34973/j6jf-9e62`) destrava **apenas os questionários**. Ver
  `docs/WEARANIZE-ACESSO.md`.
- ⚠️ **Nova ressalva, descoberta na verificação:** nem todos os 100 sujeitos do PlugNPlay têm
  os três sensores. Pulso+cabeça: **92**. Três posições: **86**. É preciso declarar o N de
  cada célula da matriz do `ML-03` — não são todas iguais.

---

### 🥈 Newcastle 2015 — a que você baixa hoje, sem pedir licença a ninguém

**O que é.** 28 pacientes de clínica do sono, uma noite de PSG cada, com **um GENEActiv em
cada pulso** a 85,7 Hz (55 arquivos `.bin` — falta o pulso direito de um participante).
Rótulos de PSG em `.txt`, resolução de 30 s. Um `.csv` com diagnóstico, idade e sexo.
**962,8 MB**, licença **CC-BY 4.0**, sem cadastro, sem DUA, sem espera.

**Por que ela entra no plano:** é a base com **menor atrito absoluto**. Dá para começar o
pipeline nesta semana enquanto o DUA do Wearanize+ tramita. Aceleração bruta de verdade,
rótulo de PSG de verdade, licença permissiva de verdade.

**Ressalvas:** só pulso; N pequeno; população de clínica do sono (diagnósticos variados —
o `.csv` diz quais, e isso precisa ir para a análise, não ficar de fora); os `.bin` são
formato proprietário GENEActiv, lidos nativamente por R (`GENEAread`, `GGIR`) — em Python
dá, mas custa um dia. **Atenção documentada pelos próprios autores:** os IDs de
participante *dentro do cabeçalho* dos `.bin` estão **errados** e devem ser ignorados; o ID
válido é o do nome do arquivo.

---

### 🥉 Walch 2019 (sleep-accel) — a que o projeto já escolheu, e que continua valendo

**O que é.** 31 sujeitos (39 recrutados; 4 excluídos por falha de transmissão, 3 por apneia,
1 por transtorno comportamental do REM), Apple Watch no pulso durante uma noite de PSG na
Universidade de Michigan. Aceleração em **g**, a ~50 Hz (20 Hz nos dois primeiros sujeitos,
por bateria), frequência cardíaca por PPG, contagem de passos, e rótulo de PSG em 5 classes
(`0` vigília, `1` N1, `2` N2, `3` N3, `5` REM). 2,2 GB descompactado, 550 MB em zip.
**Acesso aberto**, licença **Open Data Commons Attribution v1.0**.
DOI: `10.13026/hmhs-py35`.

**Por que continua no plano:** o `DEC-01` já a escolheu e o orientador endossou a direção —
não há motivo para descartar. Ela ganha um papel novo e melhor: **terceiro conjunto de
teste externo**, para medir generalização entre coortes independentes (Newcastle é do Reino
Unido e clínica; Walch é dos EUA e universitária; Wearanize+ é holandesa e jovem). E tem a
melhor ferramenta de apoio: código Python de referência em
[`ojwalch/sleep_classifiers`](http://github.com/ojwalch/sleep_classifiers).

**Ressalva específica:** o Apple Watch **não amostra continuamente**. Há lacunas, e a taxa
efetiva varia. Tratar como série regular sem verificar é erro — e é exatamente a classe de
erro que o `DASH-11` já custou caro ao projeto uma vez.

---

### ⚠️ DREAMT — grande, mas de uma população que não é a sua

100 participantes do laboratório do sono da Duke, Empatica E4 no pulso esquerdo, ACC
triaxial bruto a 32 Hz (unidade 1/64 g), rótulos de técnico a cada 30 s, com PSG completa
alinhada. A versão 2.2.0 (jun/2026) corrigiu um **desalinhamento entre ACC e PSG** das
versões anteriores — se for usar, use a 2.2.0.

**O problema não é o tamanho, é quem são as pessoas.** O estudo recrutou num laboratório de
apneia: idade média 56,2 anos, IMC médio 33,7, AHI médio 22,1 (saudável é < 5), e **68 dos
100 participantes obesos ou muito obesos**. Um modelo treinado aí aprende o padrão de
movimento de uma população com distúrbio respiratório do sono e obesidade. Aplicar isso a
um usuário jovem e saudável é um segundo *domain shift*, empilhado sobre o de posição.

Acesso: **restrito** — exige conta no PhysioNet e assinar o *PhysioNet Restricted Health
Data Use Agreement 1.5.0*.

---

### ❌ MESA / SHHS (NSRR) — o exemplo perfeito da armadilha das *contagens*

MESA tem 2 237 participantes com PSG domiciliar completa **e** 7 dias de actigrafia de
pulso. Números que fazem qualquer um querer usar. E é a base **menos utilizável** desta
lista, por um motivo técnico decisivo:

> O dispositivo usado no MESA — o **Philips Actiwatch Spectrum** — **não entrega
> acelerometria bruta**. Ele entrega *activity counts* em épocas de 30 s, calculados pelo
> firmware proprietário do fabricante.

Não há função pública que converta aceleração de MPU6050 em counts de Actiwatch. Um modelo
treinado nessas colunas aprende a escala de um algoritmo fechado, não a física de um
acelerômetro. **É o cenário exato do risco que este documento existe para sinalizar.**

Some-se o atrito de acesso: cadastro, formulário de solicitação, acordo de uso do dataset
(DAUA) **e evidência de revisão por comitê de ética institucional (IRB)**, com aprovação em
dias a semanas. Para um TCC com prazo, é caro por um dado que não transfere.

**Uso legítimo:** como **referência populacional citável** no texto (distribuição de
eficiência do sono, WASO, despertares numa amostra grande), não como fonte de treino.

---

### ❌ Dataset de BCG sob o colchão — a posição certa, o sinal errado, sem rótulo

Publicado na *Scientific Data* em 2024: 32 participantes da Beijing Sport University, **212
noites** (média de ~55 h por participante), sete noites consecutivas cada, **no próprio
dormitório** — não em laboratório. Sensor de **película piezoelétrica** de 700 mm sob o
colchão, à altura do tórax, a 140 Hz. Referências de frequência cardíaca (cinta) e
respiração (cinta capacitiva, 20 Hz). Disponível no Figshare (`10.6084/m9.figshare.26013157`).

É a base com a **posição mais parecida** com a filosofia do Dormio (não-contato, na cama) e
mesmo assim **não serve para treinar o modelo**, por duas razões independentes:

1. **O transdutor é outro.** Película piezoelétrica mede **carga gerada por deformação**
   (`Q = d₃₃·F`); um MPU6050 mede **força específica**. As unidades, a resposta em
   frequência e o que cada um enxerta como ruído são diferentes. Não é uma questão de
   reescalar.
2. **Não há rótulo de sono.** Os próprios autores declaram como limitação a **ausência de
   PSG**. Sem rótulo, não há aprendizado supervisionado — e "sono" não é algo que se rotule
   por consenso a partir do próprio sinal sem circularidade.

**Uso legítimo:** citação na fundamentação, para sustentar que sensoriamento não-contato na
cama capta sinal fisiológico útil — que é a ponte de construto que o `METODOLOGIA.md` pede.

---

### ❌ As demais, em uma linha cada

- **MMASH** (22 sujeitos, ActiGraph wGT3X-BT, ODbL 1.0, aberto): rico em contexto
  psicofisiológico — cortisol, melatonina, HRV — mas **sem PSG**. Rótulo de sono vem do
  software do actígrafo, o que é referência circular. Não treina.
- **UK Biobank** (100 000+ com Axivity AX3, pulso, 100 Hz, ±8 g): aceleração bruta de
  verdade e em escala, mas **sem PSG** — os rótulos de sono são saída de algoritmo, não
  padrão-ouro. Some-se **£500 pelos 3 primeiros anos** e um processo de aplicação. Fora de
  escopo para um TCC.
- **Sleep-EDF Expanded** (197 noites, PhysioNet, aberto): PSG excelente — EEG Fpz-Cz e
  Pz-Oz a 100 Hz, EOG, EMG submentoniano, fluxo oronasal e temperatura retal a 1 Hz — e
  **nenhum acelerômetro**. É a base certa para um trabalho de EEG; não tem relação com este.

---

## §4. Recomendação

> **Principal: `Wearanize+ OA`** *(a coleção **aberta**, `10.34973/xrmf-5726` — revisão de
> 2026-09-14; ver a caixa na seção do Wearanize+).*
> **Ponto de partida imediato e alternativa: `Newcastle 2015`.**
> **Terceiro conjunto, de teste externo: `Walch 2019`** — mantendo o que o `DEC-01` decidiu.

> 🔄 **O que a revisão de 2026-09-14 muda nesta recomendação.** O parágrafo seguinte dizia que
> o Newcastle era necessário como ponto de partida "porque a recomendação principal tem um DUA
> no caminho". **Esse motivo caiu:** a coleção aberta do Wearanize+ baixa hoje. O Newcastle
> continua no plano, mas por um motivo melhor — **é uma coorte independente**, britânica e de
> clínica do sono, e serve para testar generalização, não para desbloquear o cronograma.

**Por que o Wearanize+ como principal.** Porque é o único que responde à pergunta que a
banca vai fazer. A pergunta é: *"vocês treinaram num sensor de pulso e o produto é um
sensor de travesseiro — como sabem que funciona?"*. Com qualquer outra base, a resposta é
uma limitação declarada. Com o Wearanize+, a resposta é um número: treina no pulso, testa
na cabeça, mede a queda de kappa. **A base transforma a maior fraqueza metodológica do
projeto no seu resultado mais original.** E, de quebra, o acelerômetro de cabeça é o
proxy mais próximo do que um travesseiro sente.

**Por que o Newcastle como alternativa e primeiro passo.** Porque a recomendação principal
tem um DUA no caminho, e um TCC não pode ficar bloqueado esperando aprovação. O Newcastle é
CC-BY, baixa hoje, e tem exatamente o que o pipeline precisa para nascer: aceleração bruta
+ rótulo de PSG em 30 s. **Construa o pipeline inteiro no Newcastle.** Quando o Wearanize+
chegar, é trocar o carregador de dados.

**Por que manter o Walch.** Já foi endossado pelo orientador; descartar sem necessidade
gera retrabalho de justificativa. Ele ganha função melhor do que tinha: com Newcastle,
Wearanize+ e Walch você tem **três coortes independentes**, de três países e três perfis de
população, e "o modelo generaliza entre coortes" vira uma afirmação testada.

**O que NÃO usar, e por quê — vale escrever no TCC:** MESA e SHHS, apesar do tamanho,
porque entregam contagens proprietárias e não aceleração. Esta frase, com a justificativa
técnica, mostra à banca que a escolha foi feita por critério e não por conveniência.

---

## §5. O que esta escolha obriga o projeto a fazer

Escolher um dataset não é só baixar um arquivo. Cada linha abaixo é uma mudança concreta,
e todas viraram itens no `BACKLOG-COMPLETO.md`.

| # | Obrigação | Por quê | Item |
|:-:|---|---|---|
| 1 | **Época de 30 s.** Não 60, não livre. | É a resolução dos rótulos de PSG em **todas** as bases. Época diferente exige reamostrar rótulo, e reamostrar rótulo inventa informação. ✅ *E no Wearanize+ isso já vem pronto: o registro de dados do EDF tem **exatamente 30 s**, com **1 amostra** por canal de pontuação — um registro = uma época = um rótulo. Não há alinhamento a fazer.* | `DATA-02`, `FW-05` |
| 2 | **Amostrar bruto a ≥ 42 Hz**, e reamostrar tudo (datasets e Dormio) para uma **grade comum** — proposta: **32 Hz**. | O filtro do MPU está em 21 Hz (`FW-06`); Nyquist exige ≥ 42 Hz. As bases estão em 20, 32, 50, 85,7 e 256 Hz — sem grade comum, a mesma feature significa coisas diferentes em cada uma. 32 Hz é o mínimo comum viável (é a taxa do E4). | `FW-05` |
| 3 | **Features invariantes à orientação.** Nunca `ax`, `ay`, `az` crus. | Um sensor solto num travesseiro tem orientação arbitrária **e mutável** — o travesseiro vira durante a noite. Feature por eixo aprende a orientação do dataset, não o movimento. | §7 |
| 4 | **Separar gravidade de aceleração dinâmica.** | Em repouso `\|a\| ≈ 9,81`; a informação está no desvio. Padrão da área: **ENMO** = `max(\|a\|/g − 1, 0)`. | §7 |
| 5 | **`CAL-01` vira pré-requisito, não item solto.** | Um viés de **−1,06 m/s² em Z** — o medido em 25/08 — é 11% de `g`. Aplicado ao ENMO, ele não desloca o resultado: ele o destrói. Calibrar **depois** do `FW-06`, porque o filtro mudou. | `CAL-01`, `CAL-02` |
| 6 | **O contrato de dados precisa levar features, não só o veredito.** | Hoje cada linha leva magnitude + rótulo. Um modelo precisa de um vetor por época. Sem isso, nada do que for treinado roda sobre o que o Dormio grava. | `DATA-07` |
| 7 | **Split por sujeito, sempre.** | Épocas da mesma noite são altamente correlacionadas. Embaralhar por época infla a acurácia de forma espetacular e falsa — é o erro mais comum da literatura de wearables. | §8 |
| 8 | **O modelo não afirma estágio.** | §1. E o `DASH-09`/`DASH-11` já ensinaram que afirmar mais do que se mede sai caro. | `ML-05` |

---

## §6. O que o modelo devolve ao usuário

O pedido original foi "algum feedback dos dados, identificar padrões de sono". Isso é
possível — desde que o feedback seja do tipo que o sinal sustenta.

### ✅ Feedback honesto e útil

| Métrica | Como o usuário lê | Sustentação |
|---|---|---|
| **Início e fim do período de repouso** | "Você se aquietou às 23h47 e levantou às 6h58." | Métrica mais confiável da actigrafia. |
| **Despertares longos** | "3 períodos de agitação: 1h12, 3h40 e 5h05." | Movimento é o sinal direto. |
| **Fragmentação** | "Índice de movimento: 14 eventos/hora — sua média é 9." | Contagem por hora, comparável entre noites. |
| **Latência aparente até a quietude** | "Levou 22 min entre deitar e ficar quieto." | Não é latência de sono (que exige EEG). **O nome importa.** |
| **Regularidade entre noites** | "Nos últimos 7 dias você se deitou entre 23h30 e 01h20." | Não precisa de modelo nenhum — e é, provavelmente, o feedback mais acionável de todos. |
| **Comparação com a própria linha de base** | "Esta noite teve 40% mais movimento que a sua média." | n=1 é limitação para *validar*; é vantagem para *personalizar*. |

### ❌ O que não devolver, por mais que dê vontade

- **Estágios de sono** ("2h de REM") — o hardware não sustenta. §1.
- **Nota de qualidade do sono** (0–100) — número inventado, sem referência. Foi
  explicitamente eliminado do painel no `UI-04`/`WEB-03`; não voltar pela porta do ML.
- **Qualquer frase clínica** ("você pode ter apneia", "seu sono é ruim") — é
  aconselhamento de saúde a partir de dispositivo não validado. Problema ético,
  regulatório e de LGPD, não só de escopo.
- **Comparação com "a média das pessoas"** — o Dormio não tem população normativa.

> **A régua:** se a frase na tela não puder ser rastreada até um número medido e uma
> incerteza declarada, ela não vai para a tela. É a mesma régua do `DASH-09` e do
> `DASH-11`, aplicada ao ML.

---

## §7. Plano de execução — dados e features

### Fase 0 · Fundação reprodutível (≈ 1 semana, L0)

Sem isto, nada do resto tem validade científica — o `METODOLOGIA.md` já exige.

```
ml/
├── README.md              # origem, versão e licença de cada dataset
├── requirements.txt       # versões PINADAS
├── config.yaml            # seed, taxa comum, tamanho de época, split
├── dados/                 # gitignored — dado nunca entra no git
│   ├── bruto/             # como veio, jamais editado no lugar
│   └── processado/        # épocas + features, versionado por hash do config
├── src/
│   ├── carregar/          # um módulo por dataset, mesma interface de saída
│   ├── epocas.py          # janelamento de 30 s + alinhamento com rótulo
│   ├── features.py        # ENMO, SMA, etc. — compartilhado com o firmware
│   ├── baseline.py        # Cole-Kripke, Sadeh
│   ├── modelos.py
│   └── avaliar.py         # métricas por época E por noite
└── experimentos/          # um arquivo por experimento, com log de métricas
```

**Interface única de carregamento** é o detalhe que decide se a Fase 2 custa um dia ou uma
semana. Todo carregador devolve a mesma coisa:

```python
# (n_epocas, n_features), (n_epocas,), (n_epocas,)
X, y, id_sujeito = carregar("newcastle")   # ou "wearanize", ou "walch"
```

### Fase 1 · Janelamento e features

**Época:** 30 s, alinhada ao rótulo de PSG. **Contexto:** cada época carrega também as
features das ±2 épocas vizinhas — a literatura de actigrafia é unânime em que a vizinhança
importa (uma época quieta cercada de movimento é diferente de uma cercada de quietude).

**Features por época** — todas invariantes à orientação, todas calculáveis num ESP32:

| Feature | Fórmula | Por que |
|---|---|---|
| `ENMO_media` | média de `max(\|a\|/g − 1, 0)` | Padrão da área. Descarta gravidade sem precisar saber a orientação. |
| `ENMO_desvio` | desvio-padrão do mesmo | Distingue movimento contínuo de pico isolado. |
| `ENMO_max` | máximo | Captura o evento breve que a média dilui. |
| `SMA` | `(1/T)·Σ(\|ax\|+\|ay\|+\|az\|)` | *Signal magnitude area* — clássico de actigrafia. |
| `zcr` | taxa de cruzamento por zero do sinal sem DC | Proxy de frequência sem FFT. |
| `p_frac` | fração da época acima do limiar | É **exatamente** o que o Dormio já calcula hoje. |
| `angulo_z` | `atan2(az, √(ax²+ay²))` | Postura. Van Hees usa a *mudança* dele para detectar período de sono. |
| `d_angulo` | variação de `angulo_z` entre épocas | Mudança de postura = evento de virada. |

> **Regra de ouro:** toda feature aqui tem de ser calculável **no dispositivo**, em ponto
> flutuante simples, sem buffer da noite inteira. Se uma feature exige a noite toda, ela
> não pode existir num modelo que roda em tempo real — e vira só análise offline.

### Fase 2 · Modelos, do mais burro ao menos burro

Nesta ordem, sem pular:

| Passo | Modelo | Serve para |
|:-:|---|---|
| 0 | **"Sempre dormindo"** | O baseline degenerado. Numa noite de PSG acerta ~85–90%. **Se ele não for reportado, todos os outros números mentem.** |
| 1 | **Cole-Kripke e Sadeh** (1992/1994) | Os algoritmos que a actigrafia usa há 30 anos. Se um deles empatar com o modelo aprendido, a conclusão do TCC é essa — e é uma conclusão legítima. |
| 2 | **Regressão logística** sobre as features | Interpretável: dá para dizer *qual* feature pesa. Numa banca, isso vale mais que 2 pontos de acurácia. |
| 3 | **Random Forest / Gradient Boosting** | Captura não-linearidade. Ainda explicável por importância de feature. |
| 4 | **Suavização temporal** (mediana móvel ou HMM de 2 estados) | Sono tem estrutura: não se alterna acordado/dormindo a cada 30 s. Isto costuma render mais ganho que trocar de classificador. |
| 5 | *(opcional, só se sobrar tempo)* CNN 1-D sobre a janela bruta | Provavelmente **não** compensa com N desta ordem. Se for tentado, tem de vencer o passo 3 de forma clara. |

---

## §8. Plano de execução — validação

**Split:** por **sujeito**, nunca por época. Proposta: validação cruzada *leave-one-subject-out*
no Newcastle (N=28 permite), e teste em coorte independente.

**Seed fixa** em tudo que sorteia. **Config versionado** junto com o resultado.

### Métricas — por época e por noite

Acurácia sozinha não diz nada aqui, porque a classe é desbalanceada (a maior parte de uma
noite de PSG é sono).

| Nível | Métrica | Por que ela, especificamente |
|---|---|---|
| Época | **Sensibilidade (sono)** | Sempre alta. Não impressiona ninguém. |
| Época | **Especificidade (vigília)** | 🔴 **É aqui que a actigrafia falha, sempre.** Ficar deitado e imóvel acordado é indistinguível de dormir para um acelerômetro. Este número é o teste de honestidade do trabalho. |
| Época | **Kappa de Cohen** | Corrige o acaso. É a métrica que a literatura de sono usa para comparar. |
| Época | **F1 e matriz de confusão** | Exigidos pelo `METODOLOGIA.md`. |
| Noite | **Erro de TST, WASO, SOL** | O usuário não vê épocas: vê "dormi 7h12". Um modelo com kappa medíocre pode acertar o TST, e vice-versa. |
| Noite | **Bland-Altman** | Mostra viés sistemático e limites de concordância. É o gráfico que a área espera ver. |

### O experimento que é o resultado original — `ML-03`

Com o Wearanize+, e só com ele — **e, desde 2026-09-14, com a coleção aberta dele**:

|  | testa: **cabeça** | testa: **pulso** | testa: **coxa** |
|---|:---:|:---:|:---:|
| **treina: cabeça** | *(referência)* | Δκ | Δκ |
| **treina: pulso** | **Δκ ← esta célula** | *(referência)* | Δκ |
| **treina: coxa** | Δκ | Δκ | *(referência)* |

> ⚠️ **O N não é o mesmo em todas as células — declare cada um.** Verificado sujeito a
> sujeito na coleção aberta (2026-09-14):
>
> | Subconjunto | N |
> |---|:---:|
> | Cabeça (Zmax) — todos | **100** |
> | **Cabeça + pulso** (as duas células destacadas) | **92** |
> | Cabeça + pulso, com as duas pontuações manuais | **90** |
> | **Matriz 3×3 completa** (cabeça + pulso + coxa) | **86** |
> | Idem, com as duas pontuações manuais | **84** |
>
> **Para a matriz 3×3 ser comparável entre células, use o mesmo conjunto de sujeitos nas
> nove** — ou seja, os **86**. Variar o N por célula torna as quedas de kappa não
> comparáveis entre si, e é o tipo de erro que a banca encontra.
>
> ✅ **E há um teto para comparar contra.** A coleção aberta traz **duas pontuações manuais
> independentes** (N = 96). A concordância entre os dois pontuadores humanos é o **teto
> realista de desempenho** — e a pergunta que vale mais que o Δκ isolado é: *a perda de
> transferência pulso→cabeça é maior ou menor que a discordância entre dois especialistas?*
> Se for menor, o argumento do travesseiro fica muito difícil de atacar.

A célula destacada é a resposta ao ceticismo da banca: **quanto custa treinar num pulso e
aplicar perto da cabeça?** Se a queda for pequena, o argumento do travesseiro fica muito
mais forte. Se for grande, isso também é resultado — e justifica o `HW-07` (fusão de dois
sensores) com evidência em vez de intuição.

---

## §9. O que muda no pipeline atual, e os riscos

### Mudanças necessárias

| Onde | O quê | Item |
|---|---|---|
| **Firmware** | Amostrar a ≥ 42 Hz; agregar em épocas de 30 s; calcular as 8 features de §7 no dispositivo. | `FW-05` |
| **Contrato** | Levar o vetor de features por época, não só magnitude + rótulo. Campo novo e opcional → **MINOR**, nada quebra em campo. | `DATA-07` |
| **Banco** | Uma coluna `jsonb` com as features, ou colunas dedicadas. ~10 números × 960 épocas = **~9,6 mil valores por noite** — trivial. *(Enviar sinal bruto seria ~11 MB por noite: não faça.)* | `DATA-07` |
| **Backend** | Inferência em **lote, ao fim da sessão** — não no ESP32, não em tempo real. O Python já está lá. | `ML-INF` |
| **Frontend** | Uma seção nova no painel para as métricas de §6, com a incerteza declarada ao lado. | `ML-05` |
| **`ml/`** | Hoje contém apenas um diretório `data/` vazio. | `ML-01` |

### Riscos, sem maquiagem

1. **🔴 A especificidade vai decepcionar.** É uma limitação física, não de modelo:
   deitado e imóvel acordado ≡ dormindo, para um acelerômetro. Todo trabalho sério de
   actigrafia relata isso. **Reporte o número; não o esconda atrás da acurácia.**
2. **🔴 O baseline trivial pode empatar.** "Sempre dormindo" acerta ~85–90% numa noite de
   PSG. Se o modelo chegar a 88%, ele não aprendeu nada. **Descobrir isso antes da banca
   é o objetivo do `ML-02`** — depois é constrangimento.
3. **🟡 O salto travesseiro↔corpo pode ser grande demais.** O `ML-03` mede o salto
   corpo↔corpo; travesseiro↔corpo só o `VIA-01`/`VIA-02` medem. Se o travesseiro
   subcaptar movimento de corpo, nenhum modelo conserta — é o gatilho do `HW-07`.
4. **🟡 n=1 não valida.** Dado próprio calibra e ilustra; não valida. Isso já está em
   `METODOLOGIA.md` e continua valendo.
5. **🟡 O DUA do Wearanize+ pode demorar.** Mitigação já embutida: o pipeline nasce no
   Newcastle e a troca de dataset é trocar o carregador.
6. **🔴 O ML muda a conversa de LGPD.** Registrar movimento é uma coisa; **inferir estado
   de sono de pessoa identificada** é outra — passa a haver inferência sobre saúde. Se o
   `VIA-02` envolver voluntários, some-se termo de consentimento e possivelmente comitê de
   ética. `LGPD-03`.

---

## §10. Ordem sugerida

```
AGORA (L0, sem hardware)          DEPOIS DA SOLDA (L1/L2)
─────────────────────────         ───────────────────────
1. Baixar Newcastle (CC-BY)       6. CAL-01 + CAL-02 (calibrar pós-FW-06)
2. ml/ reprodutível (Fase 0)      7. VIA-01 + VIA-02
3. ML-02: baselines medidos       8. FW-05 em placa
4. ML-01: modelo simples          9. ML-04: calibrar com dado próprio
5. Pedir o DUA do Wearanize+     10. ML-05: entra no produto
   └─► ML-03 quando chegar
```

Os passos 1–4 são **software puro, entregáveis de TCC, e não dependem de nada físico**.
O passo 5 é um formulário — quanto antes for enviado, menos ele bloqueia.

---

## Fontes

**Desempenho de actigrafia e capacidade do sensor (§0)**

> ✅ Todas as referências abaixo tiveram **autoria, ano, veículo, volume, páginas e DOI
> conferidos na fonte** em 2026-09-10 (PubMed / Europe PMC / texto completo). Os números
> citados foram lidos no texto do artigo, não em resumo de terceiros.

- **WALCH, O.; HUANG, Y.; FORGER, D.; GOLDSTEIN, C.** (2019). *Sleep stage prediction with raw acceleration and photoplethysmography heart rate data derived from a consumer wearable device.* **SLEEP**, v. 42, n. 12, zsz180. DOI: <https://doi.org/10.1093/sleep/zsz180> · PMID 31579900 · PMC6930135
  → verbatim: *"our method scored 90% of epochs correctly, with 59.6% of true wake epochs (specificity) and 93% of true sleep epochs (sensitivity) scored correctly. Accuracy for differentiating wake, NREM sleep, and REM sleep was approximately 72% when all features were used."* Rede neural, movimento + FC + proxy circadiano. Ponto de operação exato da Tabela 2: acurácia 0,901 · vigília 0,596 · sono 0,930 · κ 0,449.
- **ODE, K. L.; SHI, S.; KATORI, M.; MITSUI, K.; TAKANASHI, S.; OGUCHI, R.; AOKI, D.; UEDA, H. R.** (2022). *A jerk-based algorithm ACCEL for the accurate classification of sleep–wake states from arm acceleration.* **iScience**, v. 25, n. 2, 103727. DOI: <https://doi.org/10.1016/j.isci.2021.103727> · PMID 35106471 · PMC8784328
  → **só aceleração bruta**: sensibilidade **96,13 ± 5,61%**, especificidade **80,18 ± 12,71%**, acurácia **91,71 ± 4,80%**. População: 25 voluntários recrutados sem diagnóstico de distúrbio do sono, doença mental ou neurodegenerativa; **32 noites** com PSG, validação *leave-one-out*; Universidade de Tóquio.
- **LI, X.; HALAKI, M.; CHOW, C. M.** (2025). *Validation of MotionWatch8 Actigraphy Against Polysomnography in Menopausal Women Under Warm Conditions.* **Sensors**, v. 25, n. 10, 3040. DOI: <https://doi.org/10.3390/s25103040> · PMC12115337
  → 16 mulheres peri/pós-menopausa (51,4 ± 4,2 anos; IMC 26,0 ± 3,1), 59 noites, 30 °C: acurácia **87,3%**, sensibilidade **94,8%**, especificidade **33,1%**; TST **+18,6 min**, eficiência **+3,5%**, latência **−11,2 min**, WASO **−9,1 min**; acurácia declina com a severidade do distúrbio.
  ⚠️ **Correção:** uma versão anterior deste documento atribuiu este estudo a *"Rocha et al., 2025"*. **A atribuição era falsa** — foi inferência, não leitura da fonte. A autoria correta é Li, Halaki e Chow.
- **CONLEY, S.; KNIES, A.; BATTEN, J.; ASH, G.; MINER, B.; HWANG, Y.; JEON, S.; REDEKER, N. S.** (2019). *Agreement between actigraphic and polysomnographic measures of sleep in adults with and without chronic conditions: A systematic review and meta-analysis.* **Sleep Medicine Reviews**, v. 46, p. 151–160. DOI: <https://doi.org/10.1016/j.smrv.2019.05.001> · PMID 31154154 · PMC6594867
  → **96 estudos, 4 134 participantes** (762 saudáveis, 724 com condições crônicas). Condições crônicas: TST **+22,42 min** (IC 95%: 11,92–32,91) e eficiência **+5,21%** (IC 95%: 1,41–9,00), **significativos**. Saudáveis: TST **+11,23 min** (IC 95%: −3,98 a 26,44) e eficiência **+1,90%** (IC 95%: −0,65 a 4,44), **explicitamente descritos como tendência não significativa**. Amostra completa: TST **+17,88 min**, eficiência **+3,77%**. Desempenho agrupado por época (49 estudos, n = 1 582): sensibilidade **0,83** (DP 0,120), especificidade **0,51** (DP 0,19), acurácia **0,82** (DP 0,07); subgrupo saudável (18 estudos, n = 461): **0,89 / 0,53 / 0,88**.
- **PAQUET, J.; KAWINSKA, A.; CARRIER, J.** (2007). *Wake detection capacity of actigraphy during sleep.* **SLEEP**, v. 30, n. 10, p. 1362–1369. DOI: <https://doi.org/10.1093/sleep/30.10.1362> · PMC2266273
  → **fonte da faixa de 14 a 60 min.** Verbatim: *"The majority of studies on insomniac populations have shown that actigraphy overestimates TST (from 14 to 60 minutes) and SE compared to PSG."* É **síntese secundária** sobre seis estudos primários: Kushida et al. (2001, *Sleep Med* 2:389–96); Sivertsen et al. (2006, *Sleep* 29:1353–58); Edinger et al. (2004, *Behav Sleep Med* 2:41–49); Hauri & Wisbey (1992, *Sleep* 15:293–301); Verbeek et al. (2001, *Percept Mot Skills* 92:852–56); Lichstein et al. (2006, *Sleep* 29:232–39).
- **YUAN, H.; HILL, E. A.; KYLE, S. D.; DOHERTY, A.** (2024). *A systematic review of the performance of actigraphy in measuring sleep stages.* **Journal of Sleep Research**, v. 33, n. 4, e14143. DOI: <https://doi.org/10.1111/jsr.14143> · PMID 38384163 · PMC7618292
  → verbatim: *"actigraphy measures peripheral limb movement alone, using activity as a proxy for wake and inactivity as a proxy for sleep, and by extension, has limited capacity to infer the stages of sleep due to the lack of physiological signals."*
  📌 O documento antes citava o **preprint** de medRxiv (2023). Usar a versão publicada.
- **MEREDITH-JONES, K. A.; HASZARD, J. J.; GRAHAM-DEMELLO, A.; CAMPBELL, A.; STEWART, T.; GALLAND, B. C.; COX, A.; KENNEDY, G.; DUNCAN, S.; TAYLOR, R. W.** (2024). *Validation of actigraphy sleep metrics in children aged 8 to 16 years: considerations for device type, placement and algorithms.* **International Journal of Behavioral Nutrition and Physical Activity**, v. 21, n. 1, art. 40. DOI: <https://doi.org/10.1186/s12966-024-01590-x> · PMC11020269
  → 137 participantes de 8 a 16 anos; acurácia **majoritariamente > 80% no pulso** vs. **geralmente < 80%** perto do centro de massa (cintura, coxa, lombar); sensibilidade maior perto do centro de massa; especificidade "consideravelmente melhor" no pulso. Valores gerais: sensibilidade 91,8 ± 5,6%, especificidade 63,8 ± 13,8%. ⚠️ **população pediátrica.**
  📌 **Errata:** MEREDITH-JONES, K. A. *et al.* (2024). *Correction to: Validation of actigraphy sleep metrics…* **IJBNPA**, v. 21, n. 1, art. 62. DOI: <https://doi.org/10.1186/s12966-024-01608-4> — corrige a lista de referências e o algoritmo da Tabela 5; **não afeta os números acima**, que vêm da Tabela 3.
- **RAZJOUYAN, J.; LEE, H.; PARTHASARATHY, S.; MOHLER, J.; SHARAFKHANEH, A.; NAJAFI, B.** (2017). *Improving Sleep Quality Assessment Using Wearable Sensors by Including Information From Postural/Sleep Position Changes and Body Acceleration: A Comparison of Chest-Worn Sensors, Wrist Actigraphy, and Polysomnography.* **Journal of Clinical Sleep Medicine**, v. 13, n. 11, p. 1301–1310. DOI: <https://doi.org/10.5664/jcsm.6802> · PMID 28992827 · PMC5656479
  → 21 participantes com queixa de sono (50,8 ± 12,8 anos; 47,8% mulheres). Sensor no tórax identificou épocas de sono/vigília com acurácia **85,8%** contra **79,8%** do pulso (**+6 pontos**). Correlação com PSG: pulso *r* = 0,0–0,3; tórax *r* = 0,4–0,8.
- **LEITÃO, F.; MOREIRA, E.; ALVES, F.; LOURENÇO, M.; AZEVEDO, O.; GASPAR, J.; ROCHA, L. A.** (2018). *High-Resolution Seismocardiogram Acquisition and Analysis System.* **Sensors**, v. 18, n. 10, art. 3441. DOI: <https://doi.org/10.3390/s18103441> · PMID 30322147 · PMC6211127
  → sinais de BCG/SCG: energia **abaixo de 30 Hz**, amplitude ~**10 mg pico a pico**. Acelerômetros MEMS comerciais usados na literatura de SCG: densidade de ruído **acima de 98 µg/√Hz** → resolução de ~0,54 mg, *"roughly a 5-bit resolution for the full acquisition system which strongly compromises the signal analysis"*. O acelerômetro **desenvolvido pelos autores** tem densidade de ruído **abaixo de 6,5 µg/√Hz**.
  ⚠️ **Correção:** os 6,5 µg/√Hz **não são um requisito publicado** para BCG/SCG — são a especificação do sensor que os autores construíram. Ver §0.6.
- **TDK INVENSENSE.** *MPU-6000/MPU-6050 Product Specification*, Documento PS-MPU-6000A-00, Revisão 3.4, 19 ago. 2013. §6.2, *Accelerometer Specifications* — <https://product.tdk.com/system/files/dam/doc/product/sensor/mortion-inertial/imu/data_sheet/mpu-6000-datasheet1.pdf>
  → *Noise Performance · Power Spectral Density*: **400 µg/√Hz**, valor **típico**, medido **a 10 Hz, com AFS_SEL = 0 (fundo de escala ±2 g) e ODR = 1 kHz**.
- **LEE, Y. J.; LEE, J. Y.; CHO, J. H.; KANG, Y. J.; CHOI, J. H.** (2025). *Performance of consumer wrist-worn sleep tracking devices compared to polysomnography: a meta-analysis.* **Journal of Clinical Sleep Medicine**, v. 21, n. 3, p. 573–582. DOI: <https://doi.org/10.5664/jcsm.11460> · PMID 39484805 · PMC11874098
  → 24 estudos, 798 participantes (Fitbit, Jawbone, myCadian, WHOOP, Garmin, Basis B1, Zulu, Huami Arc, E4, Readiband, Apple Watch, Xiaomi Mi Band 5). Diferenças médias significativas (dispositivo − PSG): TST **−16,854 min** (IC 95%: −26,332 a −7,375); eficiência **−4,691%** (IC 95%: −7,079 a −2,302); latência **+2,574 min** (IC 95%: 0,606 a 4,542); WASO **+13,255 min** (IC 95%: 4,522 a 21,988).
  🔍 **Achado que contraria a intuição, e que vale para o TCC:** a convenção de sinal é confirmável no próprio texto (os autores dizem que *"other devices reported longer wake after sleep onset than polysomnography"*, com MD positivo de +24,140 no subgrupo). Ou seja: **os dispositivos de consumo SUBESTIMAM o tempo de sono e SUPERESTIMAM a vigília — direção oposta à da actigrafia de pesquisa** (Conley et al., 2019). A leitura honesta: *"actigrafia superestima sono"* é uma afirmação sobre **algoritmos de actigrafia aplicados a movimento bruto**, não sobre **relógios de consumo com algoritmos proprietários multissensor**, que são calibrados de outro jeito. **Não citar as duas fontes como se dissessem a mesma coisa.**

### ⚠️ O que continua pendente após a verificação de 2026-09-10

✅ **Fechado em 2026-09-10 (terceira rodada).** Eram duas citações inventadas, e **ambas já
não existem em nenhum documento** — nem no corpo do texto, nem em nota, nem entre aspas num
aviso. A varredura dos quatro arquivos confirma zero ocorrências.

O registro do que houve, **sem reproduzir o texto removido** (repetir a frase errada num
aviso é o jeito mais provável de ela voltar):

| Onde estava | O que era | Estado |
|---|---|---|
| §0.4 e `LIMITACOES-TCC.md` X.1 | Citação entre aspas atribuída a **Yuan et al. (2024)** sobre confusão entre vigília quieta e sono. Não localizada no artigo publicado; o documento citava o **preprint**, de redação diferente | ✅ Substituída por frase do texto revisado por pares, conferida palavra por palavra |
| §0.5 e `LIMITACOES-TCC.md` X.3 | Citação entre aspas atribuída a **Meredith-Jones et al. (2024)** que **trocava sensibilidade e especificidade de lugar** ao justificar a vantagem do pulso. Não localizada no artigo — e contrária ao que ele relata | ✅ Removida; os dois blocos reescritos com o que está publicado |

A redação anterior está preservada no **histórico do git**, que é o lugar certo para
auditoria — e o único em que reproduzi-la não cria risco de reintrodução.

✅ **Resolvido em 2026-09-10 (segunda rodada):** a meta-análise de dispositivos de pulso de
consumo (*JCSM*, 2025) teve autoria, volume, páginas, DOI **e valores agrupados** conferidos
na fonte. É **Lee, Lee, Cho, Kang & Choi (2025)**. Ver a entrada acima — e note o achado
sobre a **direção do viés**, que é oposta à da actigrafia de pesquisa.

**Nenhuma referência dos documentos permanece sem autoria conferida.**

### Especificações de hardware — estado após a rodada de fechamento (2026-09-10)

Os cinco itens abertos foram trabalhados até um **estado terminal**: ou confirmados em fonte
citável, ou fechados como **indisponíveis publicamente** com a busca documentada e a
consequência avaliada. **Nenhum deles bloqueia o pipeline** — o pré-processamento reamostra
tudo para 32 Hz e as features do §7 são invariantes à escala do LSB.

| Item | Estado terminal | Busca feita | Consequência prática |
|---|---|---|---|
| **Faixa e bits do Apple Watch** | ⛔ **Indisponível publicamente — fechado** | Apple não publica; Walch *et al.* não informam; *teardown* do Series 3 identifica um Bosch por **código de marcação**, não por número de peça — e faixa/ODR são configuradas por firmware, não pelo chip | **Nenhuma.** A doc da Apple (`CMAcceleration`) define os eixos em **ponto flutuante em g**; a quantização do ADC não é observável no dado |
| **Modelo do ActivPAL** (e faixa/bits) | ⛔ **Não documentado — fechado** | Texto completo de Sikder *et al.*; protocolo do Healthy Brain Study (143 mil caracteres, **zero menções**); `README` do repositório oficial (**vazio**); página do Radboud Data Repository | **Mínima.** Coxa é a posição mais distante do caso do Dormio. Vias: escrever aos autores, ou ler os metadados do arquivo |
| **Taxa do acelerômetro do Zmax** | 🟡 **Provável 256 Hz** · 📄 **confirmável no arquivo** | Artigo revisado por pares (ambíguo) + preprint (explícito, "all"). **Resolução mecânica:** cabeçalho EDF declara amostras por registro **por canal** | **Nenhuma** — reamostramos para 32 Hz |
| **Faixa, bits e ruído do Zmax** | ⛔ **Não publicado** · 📄 **confirmável no arquivo** | Página de especificações da Hypnodyne retornou vazia; doc do Dreamento expõe `ScaleAccel` sem o fator | **Nenhuma.** O EDF guarda `physical min/max` e `digital min/max` por canal — resolve escala, faixa e resolução de uma vez |
| **Ruído em repouso dos aparelhos de pesquisa** | ✅ **Fonte confirmada** · 🟡 valores por marca em figura/suplemento, **computáveis de dado aberto** | ✅ Autoria conferida pela **API do Crossref**: **Lettink, van Wieringen, Altenburg, Chinapaw & van Hees (2024)**, *JMPB* 7(1), **CC BY**. Versão de registro aberta no Pure do Amsterdam UMC. Dado bruto aberto no Zenodo (CC BY) | **A favor do argumento, não contra** — ver §2.2, ressalva 1, que traz as duas vias para fechar a célula |

**O que resta genuinamente aberto nos documentos, ao todo: uma coisa.**

**Os valores absolutos de ruído em repouso por marca** (Figura 3 / Material Suplementar S3
de Lettink et al., 2024). A fonte está confirmada e é aberta; só os números não foram
extraídos nesta rodada. **A ausência torna o §2.2 conservador, não otimista** — e o §2.2
registra as duas vias para preencher a célula, ambas legítimas: ler a figura na versão
aberta do repositório, ou **computar o desvio-padrão a partir do dado bruto no Zenodo**.

**Encerrados nesta rodada:** a autoria do artigo do JMPB (✅ Crossref) e as duas citações
inventadas (✅ removidas de todos os documentos, e **não reproduzidas nem nos avisos** —
ver o bloco anterior).

**Nenhuma conclusão de nenhum dos documentos depende de um valor não confirmado.** As três
conclusões que usam a tabela do §2.1 — (i) a grandeza é a mesma para as três bases
recomendadas e não é para o MESA; (ii) o E4 é 64× mais grosseiro que o MPU6050; (iii) o
MPU6050 não é o elo fraco — apoiam-se **exclusivamente** em células ✅ confirmadas.

**Bases recomendadas** — autoria conferida na fonte em 2026-09-10

- **SIKDER, N.; VERKAAR, L.; PALTARZHYTSKAYA, A.; ACAN, S.; BOVY, L.; ALMAZOVA, T.; KRUGLIAKOVA, E.; ROSENBLUM, Y.; KRAULEDAT, M.; DRESLER, M.; ZERR, P.** (2026). *Wearanize+: a multimodal dataset for evaluating wearable technologies in sleep research.* **SLEEP Advances**, v. 7, n. 1, zpaf094. DOI: <https://doi.org/10.1093/sleepadvances/zpaf094> · PMID 41675978 · PMC12888818 · repositório: <https://doi.org/10.34973/j6jf-9e62> · código: <https://github.com/Niloy333/Wearanize_plus>
  ✅ **Ano resolvido na página oficial do periódico (Oxford Academic):** recebido 25/09/2025, aceito 15/12/2025, **publicado online em 27/12/2025**, **fascículo em 10/02/2026**. O volume/fascículo é **7(1), 2026**, e a própria *string* de citação que a OUP fornece usa **2026** — embora o aviso de copyright diga "© The Author(s) 2025". **Para a ABNT: 2026.** A anotação anterior de "dez/2025" referia-se à publicação antecipada online; as duas datas estão certas, mas a que vai na referência é a do fascículo.
  📌 **Detalhe útil de formato:** a versão *PlugNPlay* é distribuída como **um arquivo EDF por participante** (canais `[device]_[channel]`, EEG-BIDS v1.10.0), com os escores de sono integrados a 1/30 Hz. Isso simplifica o carregador do §7 — e é o que torna as células "📄 no arquivo" da tabela do §2.1 resolvíveis mecanicamente.
- **VAN HEES, V. T.; SABIA, S.; ANDERSON, K. N.; DENTON, S. J.; OLIVER, J.; CATT, M.; ABELL, J. G.; KIVIMÄKI, M.; TRENELL, M. I.; SINGH-MANOUX, A.** (2015). *A Novel, Open Access Method to Assess Sleep Duration Using a Wrist-Worn Accelerometer.* **PLoS ONE**, v. 10, n. 11, e0142533. DOI: <https://doi.org/10.1371/journal.pone.0142533> · PMC4646630
  → Protocolo do dataset de Newcastle. **Fonte das especificações de aquisição:** GENEActiv (Activinsights Ltd), punho não dominante, **85,70 Hz, faixa dinâmica ±8 g**. Dados no Zenodo (CC-BY 4.0): <https://zenodo.org/records/1160410> · processamento de referência: <https://github.com/wadpac/psg-ncl-acc-spt-detection-eval>
  📌 É o mesmo van Hees do algoritmo de ângulo-z usado nas features do §7.
- **WALCH, O.; HUANG, Y.; FORGER, D.; GOLDSTEIN, C.** (2019) — ficha completa acima, em "Desempenho de actigrafia". Dados: PhysioNet, ODC-By 1.0, <https://physionet.org/content/sleep-accel/1.0.0/> · código: <http://github.com/ojwalch/sleep_classifiers>

**Especificações de hardware dos sensores (§2.1)**
- **TDK INVENSENSE.** *MPU-6000/MPU-6050 Product Specification*, PS-MPU-6000A-00 Rev. 3.4, 19 ago. 2013 — ficha completa acima.
- **ACTIVINSIGHTS.** *GENEActiv Product Information Sheet*, jan. 2025 — <https://activinsights.com/wp-content/uploads/2025/01/GENEActiv-Product-Information-Sheet-JAN-2025.pdf>
  → "Range +/- 8g · Resolution 12 bit (3.9mg)"; frequências selecionáveis 10–100 Hz; "raw, unfiltered tri-axial acceleration data in SI units in an open data format".
- **EMPATICA.** *E4 wristband user's manual*, §2.1 *Technical Specifications* (2020).
  → "3-Axis accelerometer · Sampling frequency: 32 Hz (Non customizable) · Default range ±2g · Ranges of ±4g or ±8g are selectable with custom firmware · Resolution: 8 bits of the selected range."
- **ESFAHANI, M. J.; WEBER, F. D.; BOON, M.; ANTHES, S.; ALMAZOVA, T.; *et al.*** (2023). *Validation of the sleep EEG headband ZMax.* **bioRxiv** (⚠️ **preprint, não revisado por pares**). DOI: <https://doi.org/10.1101/2023.08.18.553744>
  → "The Lite version of ZMax EEG headband comprises two frontal EEG channels (F7-Fpz, F8-Fpz), a tri-axial accelerometer, and a PPG sensor, **all with a sampling frequency of 256 Hz**." É a única fonte localizada que desfaz a ambiguidade da taxa do acelerômetro do Zmax. **Não citar como se fosse revisado por pares.**
- **APPLE INC.** *CMAcceleration — Core Motion*, documentação do desenvolvedor — <https://developer.apple.com/documentation/coremotion/cmacceleration>
  → Define `x`, `y`, `z` como "acceleration in G's (gravitational force)" em ponto flutuante. É a fonte que sustenta a afirmação de que a quantização do ADC do Apple Watch **não é observável** no dado entregue.
- **LETTINK, A.; VAN WIERINGEN, W. N.; ALTENBURG, T. M.; CHINAPAW, M. J. M.; VAN HEES, V. T.** (2024). *Inter-Brand, -Dynamic Range, and -Sampling Rate Comparability of Raw Accelerometer Data as Used in Physical Behavior Research.* **Journal for the Measurement of Physical Behaviour**, v. 7, n. 1, art. jmpb.2024-0003. DOI: <https://doi.org/10.1123/jmpb.2024-0003> · **licença CC BY 4.0** · versão de registro em acesso aberto no repositório Pure do Amsterdam UMC: <https://pure.amsterdamumc.nl/en/publications/39929e95-8881-4d28-84ed-431f1176cd49>
  ✅ **Autoria conferida via API do Crossref** (metadados são abertos mesmo quando o site do editor bloqueia). 📌 **van Hees de novo** — é o terceiro trabalho desta lista com ele: o protocolo do Newcastle, o algoritmo de ângulo-z das features do §7, e esta caracterização.
  → **Método:** 64 acelerômetros de cinco marcas (Axivity, ActiGraph, **GENEActiv**, MOX, **activPAL**) em mesa vibratória mecânica. Antes de cada experimento, **60 s em repouso** para medir o ruído; a medida primária é o **desvio-padrão do sinal bruto na condição sem movimento**, por eixo, agregado por marca/faixa/taxa como mediana, média e percentil 95. **127 observações de repouso** no total. Os aparelhos foram configurados em ±8 g — mesma faixa do GENEActiv no Newcastle.
  → **Resultado:** o ruído em repouso **difere entre marcas** — MOX é o mais alto (diferença >12 mg para todas as demais) e ActiGraph o mais baixo (diferença >2,5 mg para Axivity, GENEActiv e MOX). Os autores observam que isso importa justamente em estudos de vida livre, "where a lot of time is spent with limited movement" — que é exatamente o regime do sono.
  → ⚠️ **Os valores absolutos por marca estão na Figura 3** ("Signal noise in rest for all three axes, stratified by brand and sampling rate") **e no Material Suplementar S3** ("the complete output of the noise comparison across brands and configurations"). **Não foram extraídos aqui:** a Figura 3 é imagem e o S3 é arquivo separado. Ver o §2.2 para o que isso muda — e o que não muda.
- **LETTINK, A.; VAN WIERINGEN, W. N.; ALTENBURG, T. M.; CHINAPAW, M. J. M.; VAN HEES, V. T.** (2023). *Mechanical shaker experiments: Amsterdam study into the properties of wearable accelerometers (ASPWA)*, versão 1.0 [conjunto de dados]. **Zenodo.** DOI: <https://doi.org/10.5281/zenodo.8160791> · **CC BY 4.0**
  → **O dado bruto dos experimentos acima, aberto.** Três arquivos: `unstructured_raw_data.zip` (~1,04 GB), `structured_raw_data.zip` (~542 MB) e a documentação da estrutura de pastas (PDF). **Contém as gravações da condição sem movimento de GENEActiv e activPAL** — ou seja, os números do §2.2 são **computáveis** a partir de dado aberto, não só legíveis num suplemento.

**Avaliadas e não recomendadas**
- DREAMT v2.2.0 (PhysioNet, acesso restrito) — <https://physionet.org/content/dreamt/2.2.0/>
- MESA / NSRR — <https://sleepdata.org/datasets/mesa> · nota sobre ausência de dado bruto: <https://sleepdata.org/replies/1114>
- Dataset de BCG em ambiente natural (Scientific Data, 2024) — <https://www.nature.com/articles/s41597-024-03950-5> · dados: <https://doi.org/10.6084/m9.figshare.26013157>
- MMASH (PhysioNet, ODbL 1.0) — <https://physionet.org/content/mmash/1.0.0/>
- UK Biobank — <https://ukbiobank.ac.uk/enable-your-research/costs>
- Sleep-EDF Expanded (PhysioNet) — <https://archive.physionet.org/physiobank/database/sleep-edfx/>

**Documentação interna**
- `docs/DATASET.md` (levantamento `DEC-01`, 2026-05-31) · `docs/METODOLOGIA.md` · `docs/HARDWARE.md` · `ROADMAP.md`
