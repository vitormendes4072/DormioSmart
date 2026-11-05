# ML-16 — reconstrução dos registros históricos

**Data:** 05/11/2026. **Base:** `63a4223` (ML-15), dependente das PRs #82/#83.
A investigação preserva os históricos e as evidências da ML-15. **As três partes foram concluídas**, com os limites de procedência explicitados abaixo.

## 1. Pilotos Wearanize de 10/7 participantes

O baixador original seleciona os primeiros IDs de `participants.tsv`, na ordem do
arquivo (`listar_sujeitos_remotos` e `--n-sujeitos 10`). A lista canônica local,
conferida contra os arquivos disponíveis, fornece:

- Cabeça: `sub-001`, `sub-002`, `sub-004`, `sub-005`, `sub-007`, `sub-008`,
  `sub-009`, `sub-010`, `sub-011`, `sub-012`.
- Pulso: os mesmos candidatos; `sub-001`, `sub-002` e `sub-004` não têm esse sensor.
  O carregador entrega os outros sete.

| Posição | Participantes efetivos | Épocas | Sono | Vigília |
|---|---:|---:|---:|---:|
| Cabeça | 10 | 9.471 | 8.706 | 765 |
| Pulso | 7 | 6.958 | 6.249 | 709 |

Foram refeitos a extração dos sinais brutos desses participantes e os treinamentos.
**Todos os campos comparados dos dois registros históricos foram reproduzidos**,
exceto os três F1 de vigília que passam de NaN para zero em cada arquivo, conforme
ML-14. Isso inclui matrizes de confusão e escalas calibradas por dobra; o achado não
se apoia apenas no número de participantes ou de épocas.

A lista da execução original não foi recuperada de um log. Esta é uma **coorte
reconstruída**, sustentada pelo procedimento de download e pela reprodução de todos
os resultados publicados. Não se afirma que foi encontrada uma lista original que
não existe nos JSONs. Os IDs são pseudônimos do dataset, sem dados demográficos.

## 2. Sintéticos de 11/09 versus 14/09

O histórico descreve duas correções da representação: trocar magnitude dinâmica L1
por L2 e trocar mediana por componente por mediana geométrica da direção de referência
(diário de 14/09, ML-01; commit `11eb4b7`). O hash da configuração YAML é igual nas
quatro saídas, mas não identifica essas definições no código.

Foram executados controles mantendo dados, seed, configuração, classificador e uma
thread, mudando apenas as duas definições investigadas:

| Magnitude / referência | VP logística | VN logística | VP suavizada | VN suavizada |
|---|---:|---:|---:|---:|
| L2 / geométrica, atual | 8.671 | 1.071 | 8.734 | 1.087 |
| L1 / geométrica | 8.666 | 1.078 | 8.726 | 1.093 |
| L2 / mediana dos vetores unitários | 8.669 | 1.073 | 8.740 | 1.088 |
| L1 / mediana dos vetores unitários | **8.669** | **1.078** | **8.717** | **1.093** |

A combinação L1/mediana por componente reproduz os resultados de 11/09; a combinação
atual reproduz os dois de 14/09. Alterar somente uma das definições **não** reproduz
11/09. Também foram testadas medianas dos vetores brutos; elas não coincidiram
com os registros antigos. As tentativas intermediárias estão resumidas no manifesto.
Um controle geométrico com oito threads também manteve os números atuais.

O primeiro arquivo de 11/09 publicava cinco métodos; o segundo passou a conter
sete, incluindo os dois calibrados. Para o primeiro, a auditoria compara os cinco
originalmente publicados e explicita os aliases dos nomes dos dois baselines.
Para o segundo e os dois registros de 14/09, compara o arquivo completo, excluídos
os campos de tempo/notas declarados pelo comparador da ML-15. Restam somente os
três F1 corrigidos de NaN para zero em cada comparação.

**Limite de procedência:** a primeira versão rastreada de `features.py` já contém
as correções. Também foram examinados os commits locais sem referência e o backup
interno disponível, sem recuperar o arquivo anterior. Portanto, a combinação antiga
é uma reconstrução experimental consistente com as alterações descritas e com todos
os números; não é uma cópia recuperada daquele arquivo-fonte. Ela existe apenas no
contexto temporário da ferramenta de auditoria. O pipeline atual mantém L2 e mediana
geométrica, e é restaurado mesmo se o controle falhar.

## 3. Logística sem scaler: sensibilidade às threads nativas

Os logs locais antigos confirmam os avisos de convergência: uma primeira tentativa
usava 2.000 iterações e foi interrompida; o commit `2f7669c` reduziu o limite para
300. O log seguinte contém os avisos de 300 iterações. A ML-15 também usou 300,
mas limitou as bibliotecas nativas a uma thread. Os arquivos de log antigos não
registram a quantidade de threads.

Foi isolada essa condição, mantendo o cache, a ordem das amostras, o código,
`class_weight="balanced"`, seed e `max_iter=300`. No primeiro participante comum,
`sub-005`, foram ajustados os três modelos de origem e avaliados nas três posições:

| Condição | Comparação de acurácia, especificidade e kappa |
|---|---|
| Uma thread | 27/27 valores coincidem com a ML-15 |
| Oito threads | 27/27 valores coincidem com o histórico |

Os seis ajustes terminaram nas 300 iterações e emitiram um aviso cada. A alteração
controlada de threads é suficiente para mudar os números nesta variante não
convergida. Não foi isolada a operação aritmética interna que desencadeia a diferença.
Também não se afirma que a execução antiga registrou oito threads: essa informação
não foi salva; é a condição encontrada que reproduz os valores.

A repetição completa com oito threads percorreu os mesmos **92 participantes** e as
**nove células** do item 2. **Nenhuma diferença** foi encontrada no bloco inteiro:
médias, desvios, intervalos, suportes e vetores por sujeito coincidem com o histórico
na tolerância absoluta/relativa de 1e-10. Foram emitidos os 276 avisos esperados.
O manifesto registra a duração e o hash do log dessa execução.

Ambiente local: Windows, Python 3.11.9, NumPy 2.2.6, SciPy 1.15.3, scikit-learn 1.7.2.
Pools BLAS OpenBLAS 0.3.29 e 0.3.28, arquitetura declarada Haswell. O limite foi
conferido nos pools carregados. `threadpoolctl` 3.6.0, já presente no ambiente,
passou a ter pin explícito em `ml/requirements.txt`; não houve atualização da biblioteca. Não foram alterados solver, tolerância, número de
iterações ou dados para forçar convergência. Recuperar o número histórico não torna
esse ajuste convergido nem recomendado. A evidência não promete igualdade em outra
arquitetura ou implementação numérica.

## Evidências e como conferir

As métricas novas, os controles e os hashes ficam em
[ml/experimentos/saida/ml16/](../ml/experimentos/saida/ml16/).
Dados brutos, caches, logs e tentativas intermediárias ficam locais, sob
`ml/dados/processado/ml16/`, fora do Git. A auditoria não exige esses dados para
conferir os resultados já publicados:

```sh
python ml/ferramentas/auditar_ml16.py --conferir
python -m pytest ml/testes -q
```

Para repetir um controle, usar Python 3.11 e `ml/requirements.txt`, com uma **pasta
nova diferente em cada comando**. Exemplos a partir da raiz, substituindo os caminhos:

```sh
python ml/ferramentas/rastrear_ml16.py --modo piloto-cabeca --dados-brutos CAMINHO_WEARANIZE --threads 1 --saida NOVA_PASTA_CABECA
python ml/ferramentas/rastrear_ml16.py --modo piloto-pulso --dados-brutos CAMINHO_WEARANIZE --threads 1 --saida NOVA_PASTA_PULSO
python ml/ferramentas/rastrear_ml16.py --modo sintetico --norma l1 --referencia mediana-unitaria --threads 1 --saida NOVA_PASTA_SINTETICO
python ml/ferramentas/rastrear_ml16.py --modo sem-scaler --cache CAMINHO_CACHE --threads 8 --saida NOVA_PASTA_ABLACAO
```

A ferramenta registra variantes, pools nativos, versões, candidatos, hash de
configuração e hash do próprio instrumento. Ela recusa saída já existente, aplica
as variantes de features apenas no sintético e restaura os módulos após a execução.
Os testes incluem alterações deliberadas e controles que não reproduzem o histórico.

## Efeito sobre o TCC

Esta investigação recupera a capacidade de repetir os números e delimita a
procedência que continua sem registro original. O resultado não altera os modelos
escolhidos, os experimentos externos ou o escopo do sensor no travesseiro. Os
sintéticos continuam sendo testes do pipeline, não evidência de desempenho real.
A variante sem scaler continua limitada pela falta de convergência.

**177 testes de ML passaram**, incluindo dez novos controles. A auditoria das
sete comparações e seus controles passou. Foram testadas sabotagens
de métricas, NaN indevido, threads, referência autodeclarada adulterada e mudança do
arquivo sem alteração dos números. A ML-16 pode ser fechada pela reprodução dos
resultados e delimitação explícita do que foi reconstruído; nenhum histórico foi
substituído ou silenciosamente reescrito.
