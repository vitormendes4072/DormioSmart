# ML-INF v2 — modelo de cabeça para inferência por noite

O exportador usa `cabeca`, `qualidade="original"`, e `item9_ctx11` do
ML-04 corrigido pela ML-17. A v1 usava seis features, uma época isolada
e escala global. Na Newcastle esquerda, detectou 10 de 21.270 épocas
de sono. O κ na DREAMT foi 0,0337, com 12,65% de sensibilidade por época.
A v1 fica registrada no [relatório original](RELATORIO-ML-INF-MVP.md) e
nos [agregados da v1](../ml/experimentos/saida/ml-inf/agregados.json).

## Resultados da rodada

κ médio por participante. O trivial prediz sono em todas as épocas.

| Avaliação | Pessoas / épocas | v1 | v2 [IC95] | Trivial | Média de Δκ v2 − v1 | Maior \|Δκ\| individual |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Wearanize cabeça, LOSO | 92 / 87.795 | 0,3640 | 0,4569 [0,4161; 0,4969] | 0,0000 | +0,0929 | 0,4106 |
| Newcastle esquerda | 27 / 30.440 | −0,0002 | 0,2953 [0,2131; 0,3809] | 0,0000 | +0,2955 | 0,7118 |
| Walch principal | 29 / 23.303 | 0,3652 | 0,4082 [0,3362; 0,4824] | 0,0000 | +0,0430 | 0,3852 |
| Walch todos | 31 / 25.250 | — | 0,4123 [0,3439; 0,4846] | 0,0000 | — | — |
| DREAMT | 97 / 77.738 | 0,0337 | 0,3470 [0,3101; 0,3857] | 0,0000 | +0,3133 | 0,7194 |

A v1 foi avaliada na Walch principal. Nas quatro comparações pareadas,
as etiquetas e a ordem das épocas coincidiram. O ganho resulta da
mudança conjunta de normalização, contexto e conjunto de features.
A v2 detectou 19.012 de 21.270 épocas de sono na Newcastle (89,38%) e
50.660 de 58.129 na DREAMT (87,15%). Os [agregados da v2](../ml/experimentos/saida/ml-inf/agregados-v2.json)
trazem dispersão, ICs, contraste com o trivial e matrizes de confusão.

O JSON reproduziu as probabilidades do estimador nas quatro avaliações
externas com erro absoluto máximo 0 e classes iguais. A diferença máxima
das métricas compartilhadas por participante contra as referências locais
foi 0 em cada avaliação. κ, IC95 e participantes válidos reproduziram
os agregados publicados. A matriz de confusão DREAMT coincidiu nas quatro
células. Uma auditoria independente com `cohen_kappa_score` e
`confusion_matrix` refez as cinco avaliações, com erro máximo de
`1,67e-16` no κ médio. Cada participante tinha uma gravação em cada
conjunto. Os mínimos observados foram 555, 839, 118, 118 e 711 épocas
na ordem da tabela, de modo que o piso de 23 não excluiu nenhuma noite.

## Referências publicadas

| Avaliação | κ publicado | IC95 publicado | Artefato e chave |
| --- | ---: | ---: | --- |
| DREAMT | 0,3470 | [0,3101; 0,3857] | [ML-13, agregados](../ml/experimentos/saida/ml13/agregados.json), `resultados.cabeca.item9_ctx11.kappa.media` |
| Newcastle esquerda | 0,2953 | [0,2131; 0,3809] | [ML-17, comparação](../ml/experimentos/saida/ml17/comparacao.json), `newcastle/cabeca/item9_ctx11 → kappa.depois` |
| Walch principal | 0,4082 | [0,3362; 0,4824] | [ML-17, comparação](../ml/experimentos/saida/ml17/comparacao.json), `walch_principal/cabeca/item9_ctx11 → kappa.depois` |
| Walch todos | 0,4123 | [0,3439; 0,4846] | [ML-17, comparação](../ml/experimentos/saida/ml17/comparacao.json), `walch_todos/cabeca/item9_ctx11 → kappa.depois` |

O ML-04 constrói a regressão balanceada com `max_iter=2000` e a semente
do projeto na [linha 393](../ml/experimentos/ml04_validacao_externa.py#L393).
O ramo sem HMM chama `clf.predict(X_ctx)` na
[linha 425](../ml/experimentos/ml04_validacao_externa.py#L425). O ML-04
delega a regra de empate ao scikit-learn. Na versão 1.7.2, o método
`LinearClassifierMixin.predict` usa `scores > 0` no caso binário
(`sklearn/linear_model/_base.py:377`). Para classes 0 e 1, logit zero
dá probabilidade 0,5 e classe 0, vigília. A classe deve usar o sinal
do logit para preservar a regra mesmo quando a probabilidade arredonda.

## Contrato para o backend

O consumidor usa o [modelo v2](../ml/modelos/ml-inf-cabeca-v2.json). O JSON declara as
oito features, os 184 nomes no formato `feature__deslocamento`, os
coeficientes na mesma ordem e o intercepto. A coluna central tem sufixo
`__+0`. A lista é gerada sondando `empilhar_contexto` com um código
distinto para cada célula da janela. O exportador fixa a atribuição
CC BY 4.0 e os hashes da configuração, das entradas e da matriz empilhada.

Uma época válida tem as oito features numéricas e finitas. Na entrada do
modelo, converter o `d_angulo` ausente nas bordas para `0.0` antes de
contar e normalizar. O piso de 23 épocas válidas está em
`normalizacao.minimo_epocas_validas`. Abaixo dele, a inferência devolve a
contagem observada e a exigida. Aplicar o z-score a toda a gravação, com
`ddof=1` e desvio substituído por 1 quando for menor que `1e-9`. Depois,
empilhar ±11 com replicação da ponta de cada segmento.

O servidor deriva os ângulos da noite e usa o intervalo estritamente
maior que 45 s para separar o contexto. Na grade de 30 s, uma época
ausente dá intervalo de 60 s e o mesmo corte do índice original do ML.
Fora da grade, as regras podem divergir. Os testes cobrem 30, 45,
45,001 e 60 s com índices originais explícitos. Também demonstram
`d_angulo` indefinido no servidor onde o ML compara as duas épocas
através da lacuna. No histórico da DREAMT, a referência de inclinação é
por trecho contínuo do sinal. Um teste com direções ortogonais mostra
que a referência da noite inteira pode dar 90° onde a referência por
trecho dá 0°. A reprodução usa as entradas históricas preservadas.

As [noites douradas](../ml/testes/fixtures/ml-inf-cabeca-v2-dourado.json)
têm 960 e 959 épocas, com um e dois segmentos. Ao
comparar os mesmos vetores de gravidade, o maior erro de inclinação foi
`4,26e-14` grau e o de `d_angulo` nas épocas comparáveis foi zero. Na
lacuna sintética, o ML calculou 0,0141° através do buraco e o servidor
retornou `None`. O dourado tem probabilidades de referência por época,
mais três entradas de contexto próximas ao corte, incluindo 0,5 exato
com classe vigília. A conferência independente usa a biblioteca padrão
para z-score, preenchimento e pontuação, com tolerância absoluta de
`1e-12` e classe exata.

## Escopo da evidência

Newcastle, Walch e DREAMT têm sensores de punho. As avaliações medem
transferência para essas pessoas e coortes, sem isolar o efeito da
posição. No Wearanize de cabeça o sensor fica preso à cabeça. Na C2,
o movimento chega pela espuma do travesseiro, que pode atenuar e
atrasar o sinal. A magnitude desse efeito depende de medição física.
Os dourados exercitam a aritmética a partir do payload sintético e a
derivação no servidor. A validação da rota consumidora fica na PR de
backend.

Rodaram no Windows local, Python 3.11.9, os 103 SHA-256 da DREAMT,
a verificação dos caches ML-17, 92 ajustes LOSO, o ajuste final,
as quatro avaliações externas, os dourados e a auditoria de κ e das
confusões. Os alvos e o ramo de classificação do ML-04 foram lidos no
Git. A tentativa inicial reproduziu o κ da Newcastle, mas o limite do
IC diferiu em até 0,00558 porque a ordem de consumo do gerador aleatório
do bootstrap era a da v1. A rodada definitiva usa a ordem do ML-04.

Os nove controles positivos reprovaram seus testes direcionados. Foram
executados z-score por pessoa, contexto global, corte de lacuna em 45 s
exatos, piso de 22, ausência da conversão angular, troca pelo JSON v1,
inversão dos nomes, adulteração de coeficiente e empate como sono. A
base de `develop` ainda não contém o exportador. A troca pelo JSON v1
exercitou a rejeição da versão anterior pelo contrato novo. Após
restaurar os arquivos, os 299 testes de ML passaram no Windows local.

A evidência individual fica em `dados-locais/ml-inf-cabeca-v2-2026-11-07-final`.
Os brutos DREAMT, os caches ML-17 e as referências ML-13 permanecem nas
respectivas pastas de `dados-locais/`. A worktree e as pastas usadas
na rodada foram verificadas sem junctions. O Git contém os parâmetros,
as duas noites sintéticas e os agregados.

## Como reproduzir

A partir de `ml/`, com o ambiente Python do projeto, conferir os arquivos
DREAMT e executar o exportador com as referências locais da ML-17 e da
ML-13. O exportador verifica os caches congelados contra o manifesto
versionado da ML-17 e as notas de referência contra os agregados
publicados. A pasta de saída deve ser nova e externa ao repositório.

```text
python -m ferramentas.baixar_dreamt --pasta <dreamt-2.2.0>
python -m experimentos.ml_inf_v2 --evidencia-ml17 <evidencia-ml17> --dados-dreamt <dreamt-2.2.0> --referencia-ml13 <resultado-local-ml04-dreamt.json> --saida <nova-pasta-local>
```
