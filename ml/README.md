# `ml/` — pipeline de sono × vigília (ML-01 e ML-02)

> Implementa o §7 e o §10 de `docs/ML-DATASETS-E-PLANO.md`.
> **Leia o §0 daquele documento antes deste.** Ele é a fundamentação de tudo
> aqui, e explica por que a especificidade — e não a acurácia — é o número que
> importa.

---

## Estado (2026-09-21)

| Item | Estado |
|---|---|
| `ML-01` · estrutura reprodutível, features, carregadores | ✅ escrito |
| `ML-02` · baselines medidos | ✅ executado (sintético, Wearanize+, Newcastle) |
| Wearanize+ OA em disco | ✅ **100 sujeitos, ~46 GB** |
| Newcastle em disco | ✅ **55 `.bin` + 28 PSG** |
| `ML-03` · matriz de transferência entre posições | ✅ executada, **N = 92** |
| `ML-03b` · ablação (itens 1–5) | ✅ executada, N = 92 |
| `ML-03b` · otimizações (itens 6, 7, 8, **8b**, **9**) | ✅ executadas, N = 92 |
| `ML-04` · **validação externa** (treina Wearanize+, testa Newcastle) | ✅ executada, N = 27 |
| `ML-04b` · **efeito do lado do corpo** (punho esq. × dir.) | ✅ executada, pareada, N = 26 |
| `ML-05` · **teto de concordância entre pontuadores** | ✅ executado, n = 96 e n = 90 |
| `ML-04` · validação externa no **Walch** | ❌ **dado não baixado** — ver abaixo |
| Testes (7 arquivos, 70 casos) | ✅ **70 passando** em 2026-09-21 |

```bash
cd ml
pip install -r requirements.txt
python -m pytest testes -q                       # 70 passando
python -m experimentos.ml03b_otimizacoes --item resumo
python -m experimentos.ml04_validacao_externa --comparar
python -m experimentos.ml04_validacao_externa --lados
```

### Por que os experimentos rodam em pedaços

`experimentos/_retomada.py` faz o leave-one-subject-out salvar um checkpoint
**por dobra**. Não é enfeite: as rodadas longas deste projeto já foram
interrompidas quatro vezes por limite externo, e um item de ~11 minutos não
cabe numa chamada de shell de 2 minutos. Com o checkpoint, uma interrupção
custa **uma dobra** (~2 s) em vez de um item inteiro, e o N continua 92 —
não foi preciso reduzir amostra em item nenhum.

O resultado **não depende de onde a execução foi cortada**: cada dobra é
independente por construção e a predição de cada sujeito é gravada na
posição dele. `testes/test_retomada.py` verifica que rodar em uma chamada e
rodar em vinte dão o mesmo vetor, bit a bit.

Os itens caros (`8b`, `9`) e o `--preparar` do `ML-04` imprimem `INCOMPLETO`
e saem com código 2 quando o orçamento da chamada acaba. **Rode o mesmo
comando de novo** até dizer `COMPLETO`.

---

## Wearanize+ OA — baixar e rodar

> **O DUA não está no caminho crítico.** A coleção aberta `Wearanize+ OA`
> (DOI `10.34973/xrmf-5726`, **CC-BY-4.0**) tem os três acelerômetros e a PSG
> pontuada, baixa **sem cadastro**, e é a versão com a unidade do Empatica
> **corrigida**. O DUA da coleção restrita destrava só os questionários.
> Procedimento completo: `docs/WEARANIZE-ACESSO.md`.

### 1. Baixar

```bash
cd ml

# Auditar o formato sem gastar banda: só os sidecars, poucos MB
python -m ferramentas.baixar_wearanize --so-metadados --n-sujeitos 100

# Piloto: 10 sujeitos, ~5 GB  ← comece por aqui
python -m ferramentas.baixar_wearanize --n-sujeitos 10

# Sujeitos específicos
python -m ferramentas.baixar_wearanize --sujeitos sub-005 sub-007 sub-008

# O N do experimento pulso -> cabeça: ~45 GB
python -m ferramentas.baixar_wearanize --n-sujeitos 92

# Conferir integridade (relê o cabeçalho EDF e checa o tamanho previsto)
python -m ferramentas.baixar_wearanize --verificar
```

**Download interrompido retoma de onde parou** — o servidor aceita
`Range` (HTTP 206, verificado). Rodar o mesmo comando de novo continua; não
recomeça.

Volume medido em 20 sujeitos: **486 MB por EDF em média** (mín. 285, máx. 553).

### 2. Rodar

```bash
python -m pytest testes/test_wearanize.py -q

python -m experimentos.ml02_baselines --dataset wearanize --posicao cabeca
```

### 3. O experimento que é a contribuição original (`ML-03`)

```python
from src.carregar import carregar
from src.carregar.wearanize import sujeitos_com_posicoes

# As 9 células da matriz TÊM de rodar sobre o mesmo conjunto de sujeitos,
# senão as quedas de kappa não são comparáveis entre si.
comuns = sujeitos_com_posicoes(["cabeca", "pulso", "coxa"])   # N = 86

treino = carregar("wearanize", posicao="pulso",  sujeitos=comuns)
teste  = carregar("wearanize", posicao="cabeca", sujeitos=comuns)
# ... treinar em `treino`, avaliar em `teste`, reportar Δκ

# Só a transferência principal, com N maior:
comuns2 = sujeitos_com_posicoes(["pulso", "cabeca"])          # N = 92

# O teto inter-avaliador — o número contra o qual o Δκ deve ser lido.
# ✅ MEDIDO: ver `ML-05` abaixo. κ = 0,612 [0,572, 0,650] nos 90 que têm as duas
# pontuações E estão nos 92 da base. Não precisa refazer esta conta à mão:
#   python -m experimentos.ml05_teto_interavaliador --resumo
p1 = carregar("wearanize", posicao="cabeca", pontuador=1, sujeitos=comuns)
p2 = carregar("wearanize", posicao="cabeca", pontuador=2, sujeitos=comuns)
```

### 4. O que o dataset tem, medido nos arquivos (não na documentação)

| | Canal | Taxa | Unidade no EDF | Sujeitos |
|---|---|---:|---|---:|
| **cabeça** | `Zmax_ACC[XYZ]` | 256 Hz | `g` | **100**/100 |
| **pulso** | `Emp_ACC[XYZ]` | 32 Hz | **`g/64`** | **92**/100 |
| **coxa** | `ActivPal_ACC[XYZ]` | 20 Hz | `g` | **93**/100 |
| pontuador 1 | `PSG_Manual_Scor1` | 1/30 Hz | — | **100**/100 |
| pontuador 2 | `PSG_Manual_Scor2` | 1/30 Hz | — | **96**/100 |
| postura | `PSG_Pos.` | 4 Hz | — | 96/100 |

**cabeça + pulso = 92** · **três posições = 86**. Para comparar: Newcastle tem
28 e Walch tem 31.

### 5. As cinco armadilhas, todas tratadas e testadas

Documentadas por extenso em `src/carregar/wearanize.py`, uma por teste em
`testes/test_wearanize.py`:

| # | Armadilha | Por que morde |
|:-:|---|---|
| **1** | O rótulo é `PSG_Manual_Scor1` no EDF e `PSG_Manual_scor1` no `.tsv` — **S maiúsculo só num deles** | Casamento sensível a maiúscula acha o acelerômetro e **perde o rótulo**. O sintoma não é exceção: é zero época. |
| **2** | O Empatica está em **`g/64`**, não em `g` | Sem dividir, a aceleração de pulso sai **64× maior**. E a v1.0 (coleção **restrita**) declara `g/16` — **fator 4 de erro** no braço "treina" do ML-03. O carregador **aborta** se encontrar `g/16`. |
| **3** | Nem todo sujeito tem os três sensores (8 sem pulso, 7 sem coxa) | Pedir "pulso" não pode derrubar os 92 que têm. São pulados com aviso. E a matriz 3×3 precisa do **mesmo N nas 9 células**. |
| **4** | O `channels.tsv` **declara** `scor2` para os 100, mas o **EDF só tem em 96** | Montar a lista de sujeitos pelo `.tsv` quebra em 4. O teto inter-avaliador é **N = 96**, não 100. |
| **5** | O nº de canais varia por sujeito (**38 a 61**) | Indexar canal por posição fixa quebra. Tudo é por nome. |

**E uma coisa que o dataset dá de graça:** o registro de dados do EDF dura
**exatamente 30 s** e os canais de pontuação têm **1 amostra por registro**. Um
registro = uma época = um rótulo. `t0_rotulo = 0.0` não é suposição, é a
estrutura do arquivo — o que elimina inteira a classe de bug que foi a
ARMADILHA 5 do `newcastle.py`.

---

## ML-03b — otimizações 6 a 9 (Wearanize+, N = 92, LOSO)

> Base: features normalizadas **por sujeito** (item 5 da ablação — não usa
> rótulo nenhum, logo não vaza), logística com `class_weight="balanced"`,
> contexto ±2 épocas. É a linha "baseline" da tabela.

Δ é contra o baseline do mesmo braço. **Ganho dentro do IC não é ganho.**

| item | | κ cabeça | Δκ (IC95 pareado) | espec. cabeça | Δespec. (IC95 pareado) |
|---|---|---:|---|---:|---|
| — | baseline (±2) | 0,383 | — | 0,724 | — |
| 6 | sem `class_weight` | 0,417 | +0,034 — **dentro do IC** | 0,379 | −0,345 **PERDA** |
| 7 | limiar de Youden | 0,333 | −0,050 — dentro do IC | 0,792 | +0,068 **ganho** |
| 8 | mediana móvel (janela 5) | 0,399 | +0,016 — **dentro do IC** | 0,734 | +0,010 — dentro do IC |
| **8b** | **HMM de 2 estados** | **0,507** | **+0,123 [+0,105, +0,142]** | 0,727 | +0,003 — dentro do IC |
| **9** | **contexto ±11 (~11 min)** | 0,458 | **+0,075 [+0,060, +0,090]** | **0,825** | **+0,101 [+0,083, +0,118]** |

Os três braços concordam, e a concordância é o achado:

| | Δκ (8b · HMM) | Δκ (9 · ±11) | Δespec. (9 · ±11) |
|---|---|---|---|
| cabeça | +0,123 [+0,105, +0,142] | +0,075 [+0,060, +0,090] | +0,101 [+0,083, +0,118] |
| cabeça degradada (E4) | +0,122 [+0,101, +0,145] | +0,082 [+0,066, +0,099] | +0,106 [+0,088, +0,126] |
| pulso | +0,123 [+0,105, +0,142] | +0,058 [+0,041, +0,075] | +0,119 [+0,099, +0,139] |

**As quatro leituras:**

1. **A suavização temporal só rende na versão forte.** A mediana móvel — o
   que o §7 chamava de "passo 4" — não sai do ruído em nenhum braço
   (Δκ ≤ +0,016). O HMM de 2 estados, com a matriz de transição contada nos
   rótulos **do treino de cada dobra**, rende **+0,12 de κ** nos três. A
   diferença entre os dois é o custo de trocar de estado ser calibrado nos
   dados em vez de arbitrado por uma janela fixa.

2. **A janela do Sadeh era mesmo a diferença.** Passar o contexto de ±2 para
   ±11 épocas dá o único ganho que aparece **em κ e em especificidade ao
   mesmo tempo** — e especificidade é a métrica do §0. Confirma a suspeita
   que motivou o item: o Sadeh vinha batendo a logística porque enxergava
   ~11 minutos, não porque fosse um algoritmo melhor.

3. **Os itens 6 e 7 são contrafactuais, não melhorias.** O item 6 mede o que
   `class_weight="balanced"` compra: tirá-lo derruba a especificidade em 34
   pontos e o κ nem sobe fora do IC. O item 7 troca κ por especificidade, sem
   ganhar nos dois.

4. **Dois testes, lado a lado, em toda comparação.** `[IC disjunto]` exige
   que os dois IC95 individuais não se sobreponham; `[pareado]` é o IC95
   bootstrap da **diferença** sobre os mesmos 92 sujeitos. Os braços rodam
   sobre os mesmos sujeitos, e a variância entre sujeitos (dp ≈ 0,16 em κ) é
   comum aos dois — exigir IC disjuntos descartaria como ruído um efeito que
   o par reproduz em quase todo sujeito. O veredito formal é o pareado; o
   conservador fica como piso. O item 9 no braço cabeça é exatamente o caso
   em que os dois discordam.

---

## ML-04 — validação externa: treina Wearanize+, testa Newcastle

> Treino: **92 sujeitos** do Wearanize+, de uma vez. Teste: **27 sujeitos**
> do Newcastle 2015 (punho esquerdo), **sem reajuste de nada** — sem refazer
> scaler no domínio de teste, sem recalibrar limiar, sem olhar um rótulo do
> Newcastle antes de medir.

⚠️ **Não leia estes κ lado a lado com os do LOSO.** A prevalência de sono é
**0,699** no Newcastle e ~0,85 no Wearanize+, e κ depende da prevalência. A
leitura válida é contra o trivial medido **no próprio Newcastle**, que está
na primeira linha.

| treino | configuração | κ | espec. |
|---|---|---:|---:|
| — | **trivial "sempre dormindo" no Newcastle** | **0,000** | **0,000** |
| pulso | base (±2) | 0,265 [0,191, 0,346] | 0,412 |
| pulso | + HMM (8b) | 0,301 | 0,375 |
| pulso | **contexto ±11 (9)** | **0,334 [0,254, 0,416]** | **0,507** |
| pulso | ±11 + HMM | 0,338 | 0,466 |
| cabeça | base (±2) | 0,239 | 0,357 |
| cabeça | contexto ±11 (9) | 0,301 | 0,438 |

Comparação **pareada entre configurações**, nos mesmos 27 sujeitos:

| treino | vs. base (±2) | Δκ | Δespec. |
|---|---|---|---|
| pulso | + HMM (8b) | +0,036 [+0,008, +0,067] | **−0,037 [−0,058, −0,014]** |
| pulso | contexto ±11 (9) | **+0,069 [+0,039, +0,102]** | **+0,095 [+0,065, +0,130]** |
| cabeça | + HMM (8b) | +0,008 — dentro do IC | **−0,050 [−0,073, −0,029]** |
| cabeça | contexto ±11 (9) | **+0,062 [+0,040, +0,086]** | **+0,081 [+0,057, +0,108]** |

**As três leituras, e a segunda é a que muda uma conclusão:**

1. **Todas as configurações ficam acima do trivial na coorte nova**, com o
   IC95 de κ inteiramente acima de zero. O modelo generaliza — não bem, mas
   generaliza, e isso não era garantido.

2. **O ganho do HMM não atravessa a coorte; o do contexto largo atravessa.**
   Dentro do Wearanize+ o HMM valia **+0,12 de κ**, o triplo do contexto
   largo. No Newcastle sobra **+0,036** no melhor braço, e **custa
   especificidade em todos os três** (−0,04 a −0,05, fora do IC). A
   explicação é direta: a matriz de transição do HMM é ajustada à estrutura
   de uma coorte com ~85% de sono, e o Newcastle tem 70%. **O item 9 é o
   ganho real do trabalho; o item 8b é um ganho de coorte.** É o tipo de
   conclusão que só a validação externa produz — o LOSO teria eleito o HMM.

3. **A degradação entre coortes é grande, e tem de ir para o texto.** No
   melhor braço (pulso → punho, contexto ±11): κ cai de 0,414 para 0,334, e a
   **especificidade cai de 0,802 para 0,507**. O número honesto do trabalho é
   o de fora, não o de dentro.

### ML-04b — quanto o lado do corpo importa

```bash
python -m experimentos.ml04_validacao_externa --lados
```

O Newcastle tem os **dois punhos** de quase todo participante, o que permite isolar o
efeito do lado. Censo: **27 esquerdos, 26 direitos, 26 com os dois** (o `ncl010` não tem
punho direito, então o pareado fecha 26 — não 27).

⚠️ **As 53 gravações não são 53 observações.** Os dois punhos de um participante são a
mesma noite, o mesmo sono e a mesma pontuação de PSG, medidos de dois lugares. A unidade
de agrupamento é o **participante**. Por isso a saída traz três coisas separadas, e nunca
uma média das 53:

| | o que é | n |
|---|---|---:|
| (a) | esquerdo isolado | 27 |
| (b) | direito isolado | 26 |
| **(c)** | **efeito do lado, pareado DENTRO do participante** | **26** |

A (c) é a comparação limpa: cada participante é seu próprio controle — mesma noite, mesmo
rótulo, mesmo modelo, muda só o lado — e toda a variância entre participantes, que é a
maior fonte de ruído aqui (dp ≈ 0,2 em κ), sai da conta.

**Resultado: o lado não importa.** Nas 24 comparações (3 braços × 4 configurações × 2
métricas), **todos os IC95 contêm zero**. A maior diferença absoluta observada foi 0,027
em κ. Na melhor configuração (pulso, contexto ±11):

| métrica | esquerdo | direito | Δ (esq − dir) |
|---|---:|---:|---|
| κ | 0,334 | 0,326 | +0,009 [−0,015, +0,031] |
| especificidade | 0,507 | 0,519 | −0,009 [−0,038, +0,017] |

É evidência a favor das DECISÕES TÉCNICAS 1 e 2 (`src/features.py`): as features foram
construídas invariantes a rotação — `inclinacao_rel` no lugar de `angulo_z`, norma L2 no
lugar da SMA L1 — e invariância a montagem prevê exatamente insensibilidade ao lado. Com
26 participantes, porém, efeito menor que ~0,03 em κ não seria distinguível do ruído:
**ausência de efeito detectável não é demonstração de ausência de efeito.**

**O número errado, calculado de propósito.** O JSON guarda, sob `d_INCORRETO_empilhado`,
o que sairia se as 52 gravações pareadas fossem empilhadas como independentes. O IC de κ
passa de 0,163 de largura para 0,114 — **estreita ~30%** sem que nenhuma evidência nova
tenha entrado (próximo do fator 1/√2 que se espera de dobrar o N artificialmente). Está
ali para documentar o tamanho do viés; não vai para tabela.

## ML-05 — teto de concordância entre pontuadores (Wearanize+)

```bash
python -m experimentos.ml05_teto_interavaliador            # ~2,5 min, relê os 100 EDFs
python -m experimentos.ml05_teto_interavaliador --resumo   # relê o JSON, instantâneo
python -m experimentos.ml05_teto_interavaliador --reescrever-notas   # só a prosa do JSON
```

O dataset tem **duas pontuações manuais** da mesma PSG. Compará-las, na mesma redução
binária que o pipeline usa, dá a **referência superior** dos Δκ — quanto do erro do
modelo é erro e quanto é margem onde dois humanos também discordam.

| recorte | κ | acurácia |
|---|---:|---:|
| 96 com as duas pontuações | 0,607 [0,569, 0,643] | 0,916 [0,906, 0,926] |
| **90** — interseção com os 92 da base | **0,612 [0,572, 0,650]** | 0,916 [0,905, 0,927] |

**São 96, não 100 nem 92.** ARMADILHA 4: o `channels.tsv` declara `scor2` para os 100, o
EDF só tem em 96. E os 92 da base não são subconjunto dos 96 — a interseção é **90**. O
divisor de toda fração do teto é o 0,612 dos 90, porque é o único medido nos *mesmos*
participantes dos números do modelo.

Lido contra ele: base ±2 = 62,7% · contexto ±11 = 75,0% · HMM = 82,9% (braço cabeça). O
custo de posição é 8,1% do teto e o de sensor, 11,6%.

⚠️ **Três coisas que este κ não é.** (1) Não é concordância em **estadiamento**, e **não é
comparável** com os κ de 5 classes da literatura em direção nenhuma — o colapso de classes
puxa para cima, a correção pelo acaso com classe majoritária puxa para baixo, e nenhum dos
dois efeitos foi quantificado. (2) Não é limite teórico: um modelo pode concordar com o
pontuador 1 mais do que o pontuador 2 concorda. (3) **Não vale para o Newcastle**, que não
publica segunda pontuação — logo os números do `ML-04` não têm teto e não são expressos como
fração dele.

**A discordância humana é assimétrica e mora na vigília.** O pontuador 2 marca 7,8 pontos
percentuais mais de vigília. Com o pontuador 1 como referência a especificidade humana é
0,958; com o pontuador 2, 0,520 — mesmo par de pontuações. κ e acurácia não se movem. Sempre
diga qual é a referência.

### O que falta: Walch

O Walch et al. 2019 (Apple Watch, 31 sujeitos, PhysioNet `sleep-accel`) era a
segunda coorte independente prevista, e **não foi feito**: o servidor do
PhysioNet não é alcançável do ambiente desta sessão (o proxy devolve 403 no
túnel TLS). Falta baixar o dado **e** escrever `src/carregar/walch.py` — a
interface única já garante que só isso é preciso, mas nada disso está
escrito. Não confundir com "rodou e deu ruim": não rodou.

---

## Resultado do ML-02 (dado sintético, 12 sujeitos, 10 800 épocas)

> ⚠️ **Dado sintético. Não é medição, não é achado, não vai para o TCC.**
> Serve para provar que o pipeline roda ponta a ponta. O que vale é a **forma**
> dos resultados, não os valores.

| modelo | acur | sens | espec | kappa | F1 vig |
|---|---:|---:|---:|---:|---:|
| **0 · sempre dormindo** | **87,3%** | 100,0% | **0,0%** | **0,000** | — |
| 1a · Cole-Kripke, escala arbitrária | 87,3% | 100,0% | 0,0% | 0,000 | — |
| 1b · Sadeh, escala arbitrária | 87,3% | 100,0% | 0,0% | 0,000 | — |
| 1c · Cole-Kripke, escala calibrada (LOSO) | 90,1% | 94,3% | 60,5% | 0,550 | 60,7% |
| 1d · Sadeh, escala calibrada (LOSO) | 90,5% | 95,2% | 58,4% | 0,556 | 61,0% |
| 2 · regressão logística (LOSO) | 90,2% | 91,9% | **78,7%** | **0,616** | 67,2% |
| 4 · logística + suavização | **90,8%** | 92,4% | **79,8%** | **0,636** | 68,8% |

**As três leituras que importam, e todas já aparecem aqui:**

1. **O trivial acerta 87,3% sem olhar o sensor.** O melhor modelo ganha
   **3,5 pontos** sobre ele. Publicar "90,8% de acurácia" sem esta linha ao
   lado é publicar um número que a banca refuta em trinta segundos.

2. **Sadeh calibrado tem acurácia MAIOR que a regressão logística (90,5% vs
   90,2%) e é PIOR nas duas métricas que importam** — kappa 0,556 vs 0,616,
   especificidade 58,4% vs 78,7%. É a demonstração, em uma linha de tabela, de
   por que a acurácia engana neste domínio.

3. **Kappa do trivial é exatamente 0.** É a métrica que ele não consegue
   inflar, e por isso é a que a literatura de sono usa para comparar.

E a conferência da identidade do §0.2 contra a literatura real:

```
Li et al. 2025 (MotionWatch8)    p = 87,8% → trivial acertaria 87,8% vs 87,3% publicado → −0,5 pt
Walch et al. 2019 (Apple Watch)  p = 91,0% → trivial acertaria 91,0% vs 90,0% publicado → −1,0 pt
```

Nos dois estudos publicados, **o classificador que ignora o sensor tem acurácia
maior que o método publicado.**

---

## As quatro decisões técnicas

Registradas por extenso no código, com o motivo. Resumo:

| # | Onde | Decisão |
|:-:|---|---|
| **1** | `src/features.py` | **`angulo_z` foi removido.** Depende de qual eixo é "z" e de montagem consistente — num travesseiro a orientação é arbitrária e muda durante a noite. Entraram `inclinacao_rel` (ângulo contra a gravidade de referência **da própria gravação**) e `d_angulo` (reorientação entre épocas). Ambos invariantes a rotação: `(Rĝ_a)·(Rĝ_b) = ĝ_a·ĝ_b`. |
| **2** | `src/features.py` | **A SMA clássica (norma L1) saiu; entrou `mag_din_media` (norma L2).** A L1 não é invariante a rotação — sobre gravidade bruta varia até 73% só por causa da montagem, e mesmo sobre a componente dinâmica o teste mediu ~6%. A L2 é invariante por construção. ⚠️ **Não citar como *signal magnitude area* no TCC.** |
| **3** | `src/baseline.py` | **Cole-Kripke e Sadeh exigem *activity counts*, que não temos.** Não há função pública que converta aceleração em counts de Actiwatch — é a armadilha do MESA. Usamos um **substituto documentado** (passa-banda 0,25–3 Hz, retificado, integrado). ⚠️ Isto **não é "Cole-Kripke"**: é *"Cole-Kripke aplicado a um substituto de contagem"*, e é assim que vai para o texto. Segunda diferença declarada: rodam em 30 s, não nos 60 s originais. |
| **4** | `src/baseline.py` | **A escala do substituto tem de ser calibrada — e só no treino.** Com escala arbitrária os dois algoritmos **degeneram para "sempre dormindo"** (linhas 1a/1b da tabela): os limiares publicados foram ajustados à escala do fabricante. Calibramos **um parâmetro**, por dobra, **exclusivamente nos sujeitos de treino**, com os limiares publicados intactos. A degeneração é reportada junto, porque ela própria é evidência de que counts proprietários não se reproduzem a partir de aceleração bruta. |

---

## Estrutura

```
ml/
├── config.yaml            # seed, grade de 32 Hz, época de 30 s, contexto ±2
├── requirements.txt       # versões PINADAS
├── dados/                 # gitignored — dado nunca entra no git
├── src/
│   ├── configuracao.py    # config + hash (o hash amarra métrica a parâmetros)
│   ├── sinal.py           # reamostragem COM anti-aliasing
│   ├── epocas.py          # janelamento de 30 s + contexto
│   ├── features.py        # as 8 features
│   ├── carregar/          # interface única: X, y, id = carregar("newcastle")
│   │   ├── base.py        #   o contrato (Gravacao, ConjuntoEpocas)
│   │   ├── newcastle.py   #   GENEActiv, punho, .bin proprietário
│   │   ├── wearanize.py   #   Zmax/Empatica/ActivPAL, EDF, 3 posições
│   │   └── sintetico.py   #   gerador — exercita o pipeline, não é resultado
│   ├── baseline.py        # trivial, Cole-Kripke, Sadeh, calibração
│   ├── modelos.py         # logística, RF, suavização
│   └── avaliar.py         # métricas + split por sujeito
├── ferramentas/           # CLI: baixar_wearanize.py (download + integridade)
├── experimentos/          # ml02_baselines.py + saida/*.json (log versionado)
└── testes/                # vetor dourado, reamostragem, sanidade, wearanize
```

**A interface única é o que decide se trocar de dataset custa um dia ou uma
semana.** Ela já provou o ponto: o Wearanize+ entrou como
`src/carregar/wearanize.py` + uma string, sem tocar em feature, época,
baseline, modelo ou métrica.

A única extensão que o `ML-03` exigiu foi `posicao=`, porque o Wearanize+ é o
único dataset com mais de uma posição de sensor — e posição é parâmetro dele,
não um dataset separado. Datasets de uma posição só **rejeitam** o argumento
(`TypeError`), em vez de ignorá-lo em silêncio.

---

## As três armadilhas já tratadas no código

1. **Aliasing.** Decimar 85,70 → 32 Hz sem filtrar antes dobra energia de alta
   frequência para dentro da banda, de forma irreversível e invisível.
   `src/sinal.py` filtra antes; `testes/test_reamostragem.py` verifica com um
   tom de 30 Hz que rebateria para 2 Hz — bem no meio da banda do movimento.

2. **IDs errados no Newcastle.** Os autores documentam que o ID de participante
   *dentro do cabeçalho* dos `.bin` está errado; o válido é o do **nome do
   arquivo**. Não é cosmético: o ID é a chave do split por sujeito, e usar o
   errado mistura o mesmo sujeito entre treino e teste. `newcastle.py` só lê o
   nome do arquivo e ignora o cabeçalho explicitamente.

3. **Split por época.** Épocas da mesma noite são altamente correlacionadas.
   `avaliar.split_por_sujeito` faz leave-one-subject-out, e
   `test_sanidade_dominio.py` verifica que nenhum sujeito vaza.

---

## Próximos passos — nesta ordem

Tudo abaixo **exige execução**, e nada foi executado ainda.

1. **`python -m pytest testes -q`.** Confirma a correção pendente de
   2026-09-14 **e** a suíte nova do Wearanize+. Os testes do Wearanize+ não
   precisam do dataset em disco — eles fabricam EDFs mínimos com as mesmas
   esquisitices dos arquivos reais. Regenerar o vetor dourado
   (`testes/vetor_dourado.json` está invalidado de propósito).
2. **`python -m ferramentas.baixar_wearanize --so-metadados`.** Poucos MB.
   Confirma que a rede alcança o servidor e que o formato é o esperado, antes
   de comprometer 5 GB.
3. **`python -m ferramentas.baixar_wearanize --n-sujeitos 10`** (~5 GB) e
   `--verificar`.
4. **`python -m experimentos.ml02_baselines --dataset wearanize --posicao cabeca`.**
   O primeiro número real do projeto. Esperar que o baseline trivial seja
   competitivo — é o ponto do `ML-02`, não um problema.
5. **Baixar o Newcastle** (CC-BY 4.0, 962,8 MB) e validar o leitor de `.bin`
   contra um arquivo real, comparando com `actipy`.
6. **`ML-03`** — a matriz 3×3 de transferência entre posições, com o teto
   inter-avaliador ao lado. É a contribuição original do trabalho, e agora não
   depende de DUA nenhum.
