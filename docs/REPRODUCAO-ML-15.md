# ML-15 — reprodução dos experimentos após a correção de F1

**Execução:** 04–05/11/2026, Windows, Python 3.11.9. **Base:**
`72f954286633f3b197d9bab454f622d67885814b` (ML-14). **15 execuções concluídas**, com as ressalvas abaixo.

## Pergunta e alcance

A correção da ML-14 muda a avaliação, sem mudar o ajuste dos classificadores.
Esta rodada repete os treinamentos principais, compara os resultados salvos e
quantifica F1 onde há informação suficiente. Serve à rastreabilidade dos resultados
do TCC; não constitui uma validação nova do sensor no travesseiro.

As saídas e os checkpoints desta rodada começaram vazios. Os resultados históricos
foram preservados. Features já extraídas foram reaproveitadas em caches **copiados**;
portanto, esta é uma reprodução de treinamento e avaliação sobre essas entradas,
e não uma reprodução integral de toda a extração a partir do dado bruto. O baseline
Newcastle voltou a processar os registros brutos. O teto interavaliador voltou a
ler as pontuações humanas. DREAMT não entrou: não fazia parte destas experiências.

## Condições de execução

| Condição | Valor |
|---|---|
| Configuração | `aec203907e6f`; seed `20260910` |
| NumPy / pandas / SciPy | 2.2.6 / 2.3.3 / 1.15.3 |
| scikit-learn / PyYAML | 1.7.2 / 6.0.3 |
| Unidade temporal | 32 Hz; épocas de 30 s; contexto padrão ±2 épocas |
| Concorrência | 2 experimentos; OMP/OpenBLAS/MKL/NumExpr limitados a 1 thread cada |
| Random Forest | `n_jobs=-1`, preservado do experimento; não está limitado pela linha anterior |
| Coorte comum Wearanize | 92 participantes, 87.795 épocas por braço |
| Quantização e ML-11 | 10 dobras, conforme os experimentos históricos |
| ML-12 | 10 dobras externas e 5 internas |

O [manifesto](../ml/experimentos/saida/ml15/manifesto.json) registra os hashes das
fontes, referências históricas e 114 arquivos de cache de entrada. Os caches foram
conferidos byte a byte por SHA-256 contra os originais locais. Para fontes textuais
e resultados, o hash normaliza CRLF para LF, para sobreviver ao checkout Windows/Linux.
Os hashes identificam a entrada disponível; não certificam a validade científica
de um pré-processamento que esta rodada não refez.

ML-03 e os baselines Wearanize usam um
[adaptador de entrada](../ml/ferramentas/rodada_reproducao.py): ele reconstrói o
contexto por participante e entrega as features e contagens aos algoritmos originais.
Os modelos são ajustados novamente. A ablação e as otimizações usam seus carregadores
de cache originais. Checkpoints históricos não foram usados como resultados de treino.

## Comparação com o histórico

O [comparador](../ml/ferramentas/comparar_reproducao.py) percorre campos, listas e
valores numéricos, com tolerância absoluta e relativa de `1e-10`; NaN versus NaN é
igualdade. Ele identifica alterações de F1 separadamente, mas **não atribui sua causa**:
nas coortes diferentes, mudanças de F1 não podem ser atribuídas somente à fórmula.
Novas saídas parciais são excluídas, e uma referência histórica parcial é sinalizada.

São ignorados `utc`, `segundos`, `parcial` e os campos textuais `AVISO`, `nota`,
`o_que_nao_mede`, `teto_no_newcastle`, `nota_assimetria`. Os demais campos, inclusive
novos e removidos, são registrados. Compatibilidade de quatro metadados
(`n_sujeitos`, `n_epocas`, `hash_config`, `seed`) **não prova** identidade de participantes;
listas de sujeitos e vetores salvos também entram na comparação quando existem.

| Família / execução | Resultado da comparação |
|---|---|
| ML-02 sintético | Reproduz os dois snapshots de 14/09 fora de três F1 de vigília que passam de NaN para zero. Os dois snapshots de 11/09 têm outras diferenças e não foram reproduzidos. |
| ML-02 Newcastle | Mesmas métricas e matrizes, fora de três F1 de vigília corrigidos para zero. 27 participantes e 59.825 épocas. |
| ML-02 Wearanize cabeça | Nova análise de 92 participantes; o histórico tinha 10 e 9.471 épocas, sem a lista de IDs. Não é reprodução da mesma coorte. |
| ML-02 Wearanize pulso | Nova análise de 92 participantes; o histórico tinha 7 e 6.958 épocas, sem a lista de IDs. Não é reprodução da mesma coorte. |
| ML-03 transferência | Todas as métricas e os vetores salvos das nove células reproduzidos. |
| ML-03b ablação | Referência e itens 1, 3, 4 e 5 reproduzidos. Item 2 sem scaler diverge. O bloco final de otimizações foi concluído agora e não existia no arquivo histórico parcial. |
| ML-03b otimizações | Baseline e itens 6, 7, 8, 8b e 9 reproduzidos, inclusive parâmetros escolhidos e vetores por sujeito. |
| ML-04 Newcastle | Todos os campos comparados reproduzidos. |
| ML-04 Walch principal | Todos os campos comparados reproduzidos. |
| ML-04 Walch todos | Todos os campos comparados reproduzidos. |
| ML-04b lateralidade | Todos os campos comparados reproduzidos. |
| ML-05 teto interavaliador | Métricas, censo e vetores reproduzidos. O campo histórico `utc_notas`, um carimbo de data, não é emitido pelo script atual. |
| Quantização | Todos os campos comparados reproduzidos. |
| ML-11 ablação de features | Todos os campos comparados reproduzidos. |
| ML-12 validação aninhada | Todos os campos comparados reproduzidos, inclusive o controle positivo. |

### Limites da reprodução histórica

**Atualização de 05/11 — ML-16 concluída.** Os pilotos 10/7 foram reconstruídos
pela ordem canônica e reproduzidos; L1/mediana unitária por componente reproduziu
os sintéticos antigos; oito threads reproduziram integralmente o item sem scaler.
O ajuste continua não convergido. As listas/fontes originais ausentes não foram
inventadas: os limites da reconstrução constam em
[RASTREABILIDADE-ML-16.md](RASTREABILIDADE-ML-16.md). O texto abaixo registra o
estado encontrado ao concluir a ML-15, antes dessa investigação.


O arquivo histórico da ablação tem `parcial=true`: contém a referência e os itens
1–5, mas não o bloco final de otimizações. Este bloco tem também um experimento
próprio completo, reproduzido separadamente. Não se deve anunciar o arquivo antigo
como uma execução integral que esta rodada teria apenas confirmado.

Na variante de logística **sem scaler**, os 276 ajustes emitiram
`ConvergenceWarning`. Os nove kappas médios diferem dos históricos; o maior módulo
de diferença é aproximadamente **0,004545**, em cabeça E4 → cabeça. A referência,
o rescaler no destino, Random Forest e a normalização por sujeito reproduziram os
campos históricos comparados. A falta de convergência é um limite da variante,
e a causa exata da divergência numérica entre execuções não foi isolada. Não se
alteraram solver, tolerância ou número de iterações para forçar coincidência.

Os snapshots sintéticos de 11/09 e os baselines Wearanize de 10/7 participantes
continuam como registros históricos com procedência insuficiente para reprodução
estrita nesta rodada. Uma execução ampliada não recupera os IDs das coortes antigas.
A investigação dessa procedência e da variante sem convergência foi registrada no
**ML-16**, sem substituir silenciosamente os resultados antigos.

## F1 complementar

Vários experimentos principais publicam acurácia, especificidade e kappa por sujeito,
sem publicar F1. Por isso, repetir seus JSONs não bastaria para verificar o alcance
da ML-14. A ferramenta [reconstruir_f1.py](../ml/ferramentas/reconstruir_f1.py) recupera
as matrizes inteiras a partir das métricas salvas e do suporte real de sono/vigília
de **cada** participante nos caches. Ela exige que acurácia, especificidade, kappa e
limites das contagens concordem; não usa a prevalência global como substituto.

Foram reconstruídas e verificadas **9.687 matrizes em 132 avaliações**.
Como controle independente, 552 matrizes reconstruídas dos seis checkpoints
históricos dos itens 8b/9 foram confrontadas com suas previsões salvas: coincidiram.
Alterar deliberadamente acurácia ou kappa é recusado. Os testes também cobrem a
inclusão de zero na média, no desvio e no intervalo, e a ausência legítima da classe.

O relatório complementar usa bootstrap percentil sobre participantes, 2.000
reamostragens, seed 20260910 reiniciada por métrica e por fórmula. Assim, seus ICs
são uma avaliação complementar; não são uma tentativa de reproduzir a sequência
de sorteios consumida pelas outras métricas do relatório original.

Já foi medida uma falha de sono na transferência **cabeça → cabeça E4** que a fórmula
antiga excluiria: o F1 médio de sono passa de **0,4714552822** (91 válidos) para
**0,4663307682** (92 válidos). O F1 de vigília do classificador trivial passa de
indefinido para zero nos três braços Wearanize e nas três coortes externas.
O arquivo complementar distingue a fórmula antiga e a corrigida **sobre as mesmas
classificações novas**; não confunde efeito da fórmula com efeito do retreinamento.

Além do caso da transferência, houve zeros de F1 antes excluídos na referência
recalculada pela ablação, em três células Random Forest e em duas configurações
sem balanceamento. Ao todo são **oito ocorrências não triviais em sete avaliações**;
a contagem inclui participantes repetidos entre configurações. Os seis grupos
triviais somam outras 363 ocorrências. Os valores, desvios e ICs de todas as
avaliações estão no JSON complementar.

Kappa e especificidade continuam sendo as métricas das comparações e da escolha
dos parâmetros nestes experimentos. F1 corrigido não selecionou outro modelo.

## Artefatos e conferência

- [Resultados novos](../ml/experimentos/saida/ml15/resultados/), separados dos originais.
- [Comparação detalhada](../ml/experimentos/saida/ml15/comparacao.json), com hashes e diferenças.
- [F1 complementar](../ml/experimentos/saida/ml15/f1_complementar.json), com médias, desvios, ICs e contagem de zeros antes excluídos.
- [Manifesto](../ml/experimentos/saida/ml15/manifesto.json), com ambiente e entradas.
- [Estado da execução](../ml/experimentos/saida/ml15/execucao.json), com duração, término de cada tarefa e hashes dos logs.
- Logs, caches e checkpoints ficam apenas no diretório local ignorado
  `ml/dados/processado/ml15_reproducao/`. Dados brutos não entram no Git.

Conferir as evidências salvas, a partir da raiz, sem dados brutos e sem treinamento:

```sh
python ml/ferramentas/comparar_reproducao.py --novos ml/experimentos/saida/ml15/resultados --saida ml/experimentos/saida/ml15/comparacao.json --conferir
python -m pytest ml/testes -q
```

Para repetir os treinamentos, criar **outra pasta isolada**, contendo `ml/src/`,
`ml/config.yaml`, os arquivos Python de `ml/experimentos/` e os caches de entrada
listados no manifesto em `ml/dados/processado/`. Disponibilizar os datasets autorizados
em `ml/dados/bruto/` dessa cópia (na execução Windows foi uma junction). Criar
`ml/experimentos/saida/` vazio: não copiar os JSONs nem `_parciais` históricos.
Instalar `ml/requirements.txt` em Python 3.11 e executar, substituindo o caminho:

```sh
python ml/ferramentas/executar_reproducao.py --pasta CAMINHO_DA_PASTA_ISOLADA
python ml/ferramentas/reconstruir_f1.py --ml-isolado CAMINHO_DA_PASTA_ISOLADA/ml --saida CAMINHO_DA_PASTA_ISOLADA/f1_complementar.json
```

O executor preserva os comandos da rodada, usa dois processos e retoma apenas os
checkpoints criados na nova pasta. O código 2 das otimizações significa orçamento
de tempo atingido, e provoca continuação; outros códigos de erro ficam no estado.
Ele recusa a primeira execução com saída preenchida. Não repetir o comando na
mesma pasta enquanto já houver uma execução ativa.

## Verificação e conclusão

As 15 tarefas concluíram com código zero; a ablação consumiu cerca de 6 h 05 min.
A primeira tentativa restrita de testes não acessou o diretório temporário do
pytest; a execução com as permissões de teste passou. **167 testes de ML passaram**, incluindo 12 novos controles. A suíte final confere também
que os 15 resultados têm comparação salva, que as 132 avaliações complementares
apontam para o hash certo e que as fontes coincidem com o manifesto.

A reprodução confirma os resultados centrais usados na seleção e na validação
externa. Ela também mostra que não seria correto anunciar igualdade integral de
todo o histórico: a variante sem convergência, os dois snapshots sintéticos
antigos e as duas coortes piloto exigem as ressalvas registradas no ML-16.
O texto histórico do TCC foi preservado; notas de conferência apontam este relatório.
