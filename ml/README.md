# `ml/` — pipeline de sono × vigília (ML-01 e ML-02)

> Implementa o §7 e o §10 de `docs/ML-DATASETS-E-PLANO.md`.
> **Leia o §0 daquele documento antes deste.** Ele é a fundamentação de tudo
> aqui, e explica por que a especificidade — e não a acurácia — é o número que
> importa.

---

## Estado (2026-09-14)

| Item | Estado |
|---|---|
| `ML-01` · estrutura reprodutível, features, carregadores | ✅ escrito |
| `ML-02` · baselines medidos | ✅ **executado** sobre dado sintético |
| Carregador do **Wearanize+ OA** (`ML-03`) | ✅ **escrito**, ⚠️ **não executado** |
| Script de download do Wearanize+ | ✅ **escrito**, ⚠️ **não executado** |
| Testes (4 arquivos, ~45 casos) | ⚠️ **nada reexecutado nesta sessão** |
| Newcastle em disco | ❌ não baixado |
| Wearanize+ em disco | ❌ não baixado |
| Vetor dourado p/ o firmware | ⚠️ invalidado, **precisa ser regenerado** |

### ⚠️ O que ficou sem verificação por execução

1. **Nada foi executado na sessão de 2026-09-14 (2ª parte).** O ambiente
   perdeu o shell (bug de plataforma, lock da pasta). O carregador do
   Wearanize+, o script de download e os testes novos estão escritos e **nunca
   rodaram**. Comece por `pytest`.

2. **O que FOI verificado nessa sessão, e não é pouco:** o formato do dataset
   foi conferido **abrindo os arquivos reais** no servidor (WebDAV anônimo, sem
   baixar tudo) — 100 cabeçalhos EDF, 100 `channels.tsv`, e um registro de
   dados decodificado amostra a amostra. As taxas, as unidades, a grafia dos
   canais e o censo de sensores no carregador **são medidos, não supostos**.
   Detalhe em `docs/WEARANIZE-ACESSO.md` §6.

3. **O Newcastle continua não baixado.** `src/carregar/newcastle.py` nunca
   rodou contra um `.bin` verdadeiro.

```bash
cd ml
pip install -r requirements.txt
python -m pytest testes -q                       # ← comece por aqui
python -m experimentos.ml02_baselines --dataset sintetico
```

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

# O teto inter-avaliador — o número contra o qual o Δκ deve ser lido:
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
