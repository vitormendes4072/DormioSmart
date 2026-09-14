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
| Testes (3 arquivos, 18 casos) | ⚠️ **15 passaram, 3 reprovaram e foram corrigidos — correção NÃO reexecutada** |
| Newcastle em disco | ❌ **não baixado** (ver abaixo) |
| Vetor dourado p/ o firmware | ⚠️ invalidado, **precisa ser regenerado** |

### ⚠️ Duas coisas que ficaram sem verificação por execução

1. **O Newcastle não foi baixado.** A rede do ambiente onde isto foi escrito
   bloqueia o Zenodo (`403 blocked-by-allowlist`). O carregador real está
   escrito (`src/carregar/newcastle.py`) mas **nunca rodou contra um `.bin`
   verdadeiro** — em particular o leitor do formato proprietário. Todo número
   já produzido veio do gerador sintético.

2. **A correção de 2026-09-14 não foi reexecutada.** Três testes reprovaram,
   o diagnóstico foi conclusivo, a correção foi escrita — mas naquela sessão o
   sandbox perdeu o acesso ao sistema de arquivos e a suíte não pôde rodar de
   novo. **Rode `pytest` antes de confiar.**

```bash
cd ml
pip install -r requirements.txt
python -m pytest testes -q                       # ← comece por aqui
python -m experimentos.ml02_baselines --dataset sintetico
```

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
│   ├── baseline.py        # trivial, Cole-Kripke, Sadeh, calibração
│   ├── modelos.py         # logística, RF, suavização
│   └── avaliar.py         # métricas + split por sujeito
├── experimentos/          # ml02_baselines.py + saida/*.json (log versionado)
└── testes/                # vetor dourado, reamostragem, sanidade
```

**A interface única é o que decide se trocar de dataset custa um dia ou uma
semana.** Quando o Wearanize+ chegar, é escrever `src/carregar/wearanize.py` e
trocar a string.

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

## Próximos passos

1. **Rodar `pytest`** e confirmar a correção de 2026-09-14. Regenerar o vetor
   dourado (`testes/vetor_dourado.json` está invalidado de propósito).
2. **Baixar o Newcastle** (CC-BY 4.0, sem cadastro, 962,8 MB) para
   `dados/bruto/newcastle/` e validar o leitor de `.bin` contra um arquivo real
   — de preferência comparando com `actipy`.
3. **Rodar o `ML-02` sobre dado real.** Aí sim os números valem.
4. `ML-03` — transferência entre posições, quando o DUA do Wearanize+ sair.
