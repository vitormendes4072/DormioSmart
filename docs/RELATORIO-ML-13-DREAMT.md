# ML-13 — validação externa na DREAMT

**06/11/2026.** P1, P2 e P3 se confirmaram no braço primário pulso.
A configuração ±11 sem HMM obteve κ médio **0.4218**
em **97 participantes e 77.738 épocas**, com IC95
[0.3867, 0.4562]. A análise segue o
[protocolo temporal congelado](ML-13-PROTOCOLO-TEMPORAL.md), as
[previsões de 05/11](PLANO-ML-13-COORTE-DREAMT.md) e o
[adendo ML-17](ADENDO-ML-13-APOS-ML-17.md).

## Coorte e cobertura

Os 103 hashes oficiais conferiram. Dos 100 CSVs, três gravações
tinham duas fases de pontuação incompatíveis com uma grade única
de 30 s. A regra de exclusão foi registrada em c328342 antes da
avaliação. Nos 97 arquivos avaliáveis houve 77.839
épocas na grade após a preparação, das quais 97 caudas incompletas
e quatro épocas sem rótulo foram descartadas. O máximo de cada
tipo de descarte em uma gravação foi uma época. Nenhuma época
com lacuna ou ACC ausente foi encontrada nesses arquivos.
Restaram 101 segmentos, 58.129 épocas de sono e
19.609 de vigília. A prevalência de sono foi 74.78%.

## Previsões registradas

| Previsão no pulso | Efeito estimado [IC95] | Decisão |
|---|---|---|
| P1, κ de ±11 sem HMM | 0.4218 [0.3867, 0.4562] | Confirmada, IC inteiro acima de zero |
| P2, Δκ ±11 − ±2 | 0.0298 [0.0145, 0.0457] | Ganho confirmado |
| P2, Δespecificidade ±11 − ±2 | 0.0536 [0.0377, 0.0702] | Ganho confirmado, P2 conjunta satisfeita |
| P3, Δespecificidade HMM ±2 − base ±2 | -0.0521 [-0.0666, -0.0361] | Confirmada, IC inteiro abaixo de zero |

Bootstrap percentil com 2.000 reamostragens por participante e seed
20260910. Os contrastes usam os mesmos participantes. A âncora sempre
sono teve κ 0.0000, especificidade
0.0000 e acurácia macro
0.7452. A melhora em κ e especificidade
com ±11 e a queda de especificidade com HMM ±2 repetem a direção
observada em Newcastle e Walch na ML-17. No pulso, o Δκ do HMM ±2
inclui zero. A especificidade da combinação ±11+HMM também inclui zero
no contraste com ±2.

## Todas as células

| Treino | Configuração | κ médio [IC95] | Especificidade média [IC95] | Acurácia | F1 vigília | F1 sono |
|---|---|---:|---:|---:|---:|---:|
| cabeca | base_ctx2 | 0.2922 [0.2585, 0.3265] | 0.4528 [0.4189, 0.4874] | 0.7383 | 0.4242 | 0.8180 |
| cabeca | item8b_hmm | 0.3121 [0.2752, 0.3486] | 0.3837 [0.3479, 0.4205] | 0.7627 | 0.4144 | 0.8383 |
| cabeca | item9_ctx11 | 0.3470 [0.3101, 0.3857] | 0.5007 [0.4648, 0.5360] | 0.7584 | 0.4721 | 0.8307 |
| cabeca | item9b_ctx11_hmm | 0.3472 [0.3097, 0.3867] | 0.4516 [0.4140, 0.4879] | 0.7675 | 0.4600 | 0.8390 |
| cabeca_e4 | base_ctx2 | 0.3678 [0.3356, 0.3992] | 0.4690 [0.4348, 0.5012] | 0.7860 | 0.4826 | 0.8515 |
| cabeca_e4 | item8b_hmm | 0.3825 [0.3462, 0.4201] | 0.4123 [0.3752, 0.4505] | 0.7985 | 0.4755 | 0.8619 |
| cabeca_e4 | item9_ctx11 | 0.4048 [0.3701, 0.4393] | 0.5258 [0.4897, 0.5605] | 0.7940 | 0.5197 | 0.8550 |
| cabeca_e4 | item9b_ctx11_hmm | 0.4033 [0.3644, 0.4419] | 0.4855 [0.4477, 0.5226] | 0.7967 | 0.5095 | 0.8581 |
| pulso | base_ctx2 | 0.3919 [0.3610, 0.4235] | 0.4983 [0.4634, 0.5317] | 0.7934 | 0.5053 | 0.8558 |
| pulso | item8b_hmm | 0.4075 [0.3701, 0.4441] | 0.4462 [0.4089, 0.4825] | 0.8054 | 0.5024 | 0.8654 |
| pulso | item9_ctx11 | 0.4218 [0.3867, 0.4562] | 0.5519 [0.5154, 0.5867] | 0.7991 | 0.5367 | 0.8576 |
| pulso | item9b_ctx11_hmm | 0.4175 [0.3791, 0.4558] | 0.5095 [0.4713, 0.5473] | 0.8018 | 0.5242 | 0.8609 |

Os desvios, ICs das cinco métricas, n válido e as 13 matrizes de
confusão somadas por época estão no
[JSON agregado](../ml/experimentos/saida/ml13_dreamt_agregados.json).
Cada média dá o mesmo peso a cada participante. As matrizes somadas
dão o mesmo peso a cada época.

## Dispersão dos efeitos

Em cada célula, o par entre parênteses dá o menor e o maior Δ individual.

| Treino | Configuração contra base ±2 | Δκ médio [IC95] (mínimo a máximo) | Δespecificidade média [IC95] (mínimo a máximo) |
|---|---|---|---|
| cabeca | item8b_hmm | 0.0198 [0.0026, 0.0372] (-0.1694 a 0.2582) | -0.0692 [-0.0842, -0.0536] (-0.4000 a 0.1125) |
| cabeca | item9_ctx11 | 0.0548 [0.0415, 0.0681] (-0.0890 a 0.2573) | 0.0478 [0.0336, 0.0618] (-0.2000 a 0.3235) |
| cabeca | item9b_ctx11_hmm | 0.0550 [0.0346, 0.0760] (-0.1661 a 0.3053) | -0.0013 [-0.0205, 0.0173] (-0.4000 a 0.3309) |
| cabeca_e4 | item8b_hmm | 0.0147 [-0.0022, 0.0318] (-0.1214 a 0.3004) | -0.0567 [-0.0710, -0.0422] (-0.2667 a 0.1667) |
| cabeca_e4 | item9_ctx11 | 0.0370 [0.0229, 0.0515] (-0.1355 a 0.1844) | 0.0568 [0.0432, 0.0707] (-0.2000 a 0.2222) |
| cabeca_e4 | item9b_ctx11_hmm | 0.0355 [0.0149, 0.0573] (-0.1774 a 0.3672) | 0.0164 [-0.0025, 0.0360] (-0.2137 a 0.3246) |
| pulso | item8b_hmm | 0.0156 [-0.0007, 0.0334] (-0.2141 a 0.2678) | -0.0521 [-0.0666, -0.0361] (-0.3556 a 0.1458) |
| pulso | item9_ctx11 | 0.0298 [0.0145, 0.0457] (-0.1919 a 0.2012) | 0.0536 [0.0377, 0.0702] (-0.2444 a 0.2119) |
| pulso | item9b_ctx11_hmm | 0.0256 [0.0046, 0.0485] (-0.2193 a 0.3160) | 0.0112 [-0.0093, 0.0331] (-0.3556 a 0.2880) |

O maior |Δκ| individual foi 0,3672, em cabeça-E4 com ±11+HMM
(Δ médio +0,0355). A maior queda individual de especificidade foi
−0,4000 em cabeça com ±11+HMM (Δ médio −0,0013). Essa mesma célula
teve o maior |Δ| individual de acurácia, +0,1445 (média +0,0292), e de
F1 de sono, +0,0958 (média +0,0211). O maior |Δ| individual de F1
de vigília foi +0,2946 em cabeça-E4 com ±11+HMM (média +0,0268).

## Execução e limites

O ML-04 executou no Windows local com Python 3.11.9, NumPy 2.2.6,
pandas 2.3.3, SciPy 1.15.3, scikit-learn 1.7.2 e threadpoolctl 3.6.0.
A execução foi limitada a uma thread nativa. Um processo separado com
os mesmos imports e ambiente confirmou três pools com uma thread cada.
Os 12 ajustes terminaram com código zero, sem avisos de convergência no log.

O treino preservou o cache congelado da ML-17. Foi verificado o SHA-256
dos bytes originais, a identidade de configuração e os hashes das fontes
de 3273431. As duas fontes com novos hashes adicionam o caminho DREAMT.
A extração Wearanize, a seleção dos 92 participantes e os vetores do cache
foram preservados. Uma cópia recebeu a identidade da branch atual. Cada
braço tem os mesmos 98 segmentos. O ML-04 comparou X/y/IDs dos três braços
com o manifesto da ML-17 antes de ajustar. Uma preparação redundante dos
brutos foi encerrada após essa conferência.

As 12 células resultam dos parâmetros congelados e de regressão logística
balanceada. A normalização por participante usa as features da gravação.
As transições HMM vieram do treino. Os ICs descrevem variação entre os
participantes avaliáveis nesta coorte. A comparação é de transferência
entre sensores junto ao corpo. O desempenho no travesseiro segue uma
questão de validação física. As três exclusões limitam a análise aos 97
participantes cuja fase foi verificável. Uma análise das fases ambíguas
exigiria um protocolo próprio.

A exportação recompôs médias e desvios das notas locais para 12 células
mais o trivial, cinco métricas por célula. Foram conferidas 13 matrizes
com o mesmo suporte e o total de épocas. Os testes locais no Windows
passaram com 278 casos. Dois testes da CLI falharam na base b5335ac
porque a opção dreamt não existia. Os controles de pares ACC, fase, coluna
obrigatória, lacuna, cauda, remoção de segmentos e ordem dos pares
foram executados com os casos sintéticos.

## Reprodução

Executar a partir de ml/, com o ambiente pinado. Conferir os 103
arquivos e preparar o cache do treino com ml03b_otimizacoes
(--item baseline --preparar-cache --pasta e --cache explícitos),
ou conferir o cache congelado como acima. O hash do treino precisa
corresponder ao manifesto ML-17.

```text
python -m ferramentas.baixar_dreamt --pasta PASTA_DREAMT
python -m experimentos.ml04_validacao_externa --coorte dreamt --dados-brutos PASTA_DREAMT --dados-wearanize PASTA_WEARANIZE --cache CACHE_TREINO --saida-dir SAIDA_PRIVADA
python -m ferramentas.resumir_ml13 --entrada RESULTADO_PRIVADO.json --saida experimentos/saida/ml13_dreamt_agregados.json
```

O commit de protocolo e código anterior à rodada foi
c328342367de4079b99a6f7c420e4768ac8230b6. Os hashes de entrada e a seed
estão no JSON agregado. A evidência completa está em
dados-locais/ml13-dreamt-avaliacao-2026-11-06, fora da worktree.
Os brutos DREAMT ficam em dados-locais/dreamt-2.2.0 e o Wearanize
no armazenamento bruto original. Nenhuma junction foi usada.

Referências consultadas. [DREAMT v2.2.0](https://doi.org/10.13026/3f7y-2d80),
[artigo original](https://proceedings.mlr.press/v248/wang24a.html) e
[PhysioNet](https://doi.org/10.1038/s44360-026-00096-z).
