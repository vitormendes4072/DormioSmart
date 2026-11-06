# ML-17 — efeito do contexto por participante e segmento contínuo

**Execução em 05/11/2026, Windows local, Python 3.11.9.**
Primeira entrega: PR #91 (código, testes e caches). Esta segunda entrega parte
dela e contém as rodadas e a análise. Ordem de merge: #91, depois a segunda PR.

A correção tem efeito mensurável. O maior módulo da mudança média de κ numa
célula foi **0,015003**; a maior mudança individual de κ foi **0,209959**, em
outra célula. A especificidade de um participante mudou **0,346154** (34,62 pontos
percentuais). As direções primárias que fundamentam P1–P3 foram preservadas.
Quatro sinais de médias secundárias mudaram, com ICs incluindo zero antes e
depois; estão registrados no [adendo anterior à DREAMT](ADENDO-ML-13-APOS-ML-17.md).

## O que foi executado

- Código antigo: `d429d43e1b7bafacae67fbebb9a328942d63efff`.
- Código corrigido: `3273431b6ebec4e3889bd3f01c3593b32dc0137e`, da #91.
- Executor: commit `11fa375`, congelado antes dos ajustes de modelos.
- **69 células em cada versão:** 36 externas (três braços × quatro configurações
  × Newcastle esquerdo/Walch principal/Walch todos), 24 de punhos (três braços ×
  quatro configurações × dois lados) e nove de otimizações (três braços ×
  baseline/HMM ±2/±11, com LOSO completo dos 92 participantes).
- As versões foram executadas de novo, com saídas/checkpoints novos. O “antes”
  não foi copiado dos resultados históricos. Só foram retomados checkpoints
  criados por esta execução.
- Configuração `aec203907e6f`, seed `20260910`, hiperparâmetros fixos, 92
  participantes de treino, bibliotecas iguais, **uma thread nativa por processo**
  e no máximo dois processos de rodadas simultâneos. As dez execuções terminaram com **zero avisos**.
- Foram conferidos os hashes de X/y/IDs efetivamente carregados em cada grupo:
  **iguais entre antes e depois**. Nenhum ajuste de parâmetros nas coortes de teste.

O [protocolo e censo](ML-17-PROTOCOLO-RODADAS.md) foram commitados antes das
rodadas. [Manifesto público](../ml/experimentos/saida/ml17/manifesto.json) registra
fontes Git, executor, análise, ambiente, hashes e estados, sem caminhos de máquina.

## Dados reconstruídos e o que não reproduziu exatamente

Wearanize (três braços) e Walch (duas variantes) reconstruíram X/y/IDs exatamente
contra os caches anteriores. No Newcastle, rótulos, IDs/ordem e as seis features
intra-época também coincidiram. Os dois ângulos tiveram diferenças:

| Destino | Máximo absoluto, graus | Média absoluta nas oito features | Épocas diferentes | Participantes afetados | Maior número de épocas diferentes em um participante |
|---|---:|---:|---:|---:|---:|
| Esquerdo | 2,842170943040401e-14 | 6,221342976485442e-17 | 1.017 | 27 | 69 |
| Direito | 2,842170943040401e-14 | 6,588159205405496e-17 | 1.036 | 26 | 88 |

**A causa dessa diferença não foi determinada.** O conferidor exato bloqueou
a primeira tentativa. Depois da quantificação, a comparação foi feita com
**o mesmo X reconstruído nas duas versões**. O censo mantém padrão exato e só
admite, por opção explícita, até 3e-14 graus nas duas colunas angulares do
legado; qualquer desvio nas demais colunas, y ou IDs/ordem reprova. A igualdade
entre as entradas das duas rodadas permanece exata.

Portanto, esta é uma comparação controlada do código com entradas comuns.
Não é reprodução bit a bit dos caches/números históricos, nem reconstituição
de sua máquina/quantidade histórica de threads. Brutos e caches antigos
não foram sobrescritos.

## Censo comunicado antes de treinar

São épocas da sequência retida, incluindo quebras após rótulos não pontuados.
Mudança de vizinhança e mudança numérica foram contadas separadamente e
coincidiram nestes dados.

| Coorte / braço | Épocas | Alteradas ±2 | Alteradas ±11 | Máximo % por participante, ±11 |
|---|---:|---:|---:|---:|
| Wearanize / cabeça | 87.795 | 385 | 2.090 | 14,263 % |
| Wearanize / cabeça E4 | 87.795 | 385 | 2.090 | 14,263 % |
| Wearanize / pulso | 87.795 | 385 | 2.090 | 14,263 % |
| Newcastle / esquerdo | 30.440 | 104 | 572 | 2,391 % |
| Newcastle / direito | 29.385 | 100 | 550 | 2,391 % |
| Walch / principal | 23.303 | 347 | 1.489 | 32,333 % |
| Walch / todos | 25.250 | 367 | 1.599 | 32,333 % |

No Wearanize são 98 segmentos para 92 participantes; na Walch principal,
129 segmentos para 29 participantes. Há seis quebras adicionais no treino e
100 na Walch principal. Newcastle tem um segmento por gravação selecionada.
Os destinos são comuns aos três braços de treino. O máximo percentual por
participante pode pertencer a uma pessoa diferente do máximo absoluto.

Essas contagens não limitam as mudanças de predição às bordas: os coeficientes
também são reajustados.

## Efeito antes/depois: média e caso individual

Todas as diferenças abaixo são **corrigido − antigo**, com os mesmos dados.
κ é adimensional; especificidade e acurácia estão na escala 0–1.

| Métrica / célula do maior caso individual | Δ médio da célula | Δ individual de maior módulo |
|---|---:|---:|
| kappa — `walch_principal/cabeca/item9b_ctx11_hmm` | -0,011205 | -0,209959 |
| especificidade — `otimizacoes/pulso/9` | -0,006366 | -0,346154 |
| acuracia — `walch_principal/cabeca/item9b_ctx11_hmm` | +0,000622 | +0,093220 |

O caso extremo de κ tem 955 épocas, 49 de vigília; o de especificidade, 1.147
épocas e 26 de vigília; o de acurácia, 118 épocas e 38 de vigília. No caso da
especificidade, foram 23/26 épocas de vigília corretas antes e 14/26 depois.
Esses suportes ajudam a interpretar o tamanho da diferença, sem descartá-la.

A maior mudança média de κ foi +0,015003 em Walch todos/pulso/±11, cujo máximo
individual foi 0,086725. A maior mudança média de especificidade foi −0,028150
em Walch principal/cabeça/±11+HMM, com máximo individual de 0,265306.

### Braço primário: pulso

| Coorte / configuração | κ antes → depois | Δκ médio | Máx. módulo individual de Δκ | Especificidade antes → depois |
|---|---:|---:|---:|---:|
| `newcastle/base_ctx2` | 0,2648 → 0,2620 | -0,002798 | 0,021124 | 0,4119 → 0,4080 |
| `newcastle/item8b_hmm` | 0,3006 → 0,2993 | -0,001203 | 0,077199 | 0,3750 → 0,3698 |
| `newcastle/item9_ctx11` | 0,3340 → 0,3280 | -0,005986 | 0,086386 | 0,5073 → 0,4889 |
| `newcastle/item9b_ctx11_hmm` | 0,3376 → 0,3289 | -0,008778 | 0,080372 | 0,4661 → 0,4499 |
| `walch_principal/base_ctx2` | 0,3459 → 0,3483 | +0,002379 | 0,030849 | 0,6311 → 0,6305 |
| `walch_principal/item8b_hmm` | 0,4156 → 0,4116 | -0,004067 | 0,119466 | 0,5888 → 0,5795 |
| `walch_principal/item9_ctx11` | 0,3776 → 0,3916 | +0,013931 | 0,086725 | 0,7268 → 0,7188 |
| `walch_principal/item9b_ctx11_hmm` | 0,3899 → 0,3996 | +0,009679 | 0,061603 | 0,6366 → 0,6280 |
| `walch_todos/base_ctx2` | 0,3423 → 0,3448 | +0,002443 | 0,030849 | 0,6309 → 0,6304 |
| `walch_todos/item8b_hmm` | 0,4164 → 0,4138 | -0,002613 | 0,119466 | 0,5922 → 0,5835 |
| `walch_todos/item9_ctx11` | 0,3766 → 0,3916 | +0,015003 | 0,086725 | 0,7269 → 0,7187 |
| `walch_todos/item9b_ctx11_hmm` | 0,3930 → 0,4070 | +0,014016 | 0,149248 | 0,6367 → 0,6287 |

Os três braços, todas as configurações e os punhos estão no
[comparativo completo das 69 células](../ml/experimentos/saida/ml17/comparacao.json),
com agregados públicos de médias, desvios,
ICs, n válido, diferenças pareadas, mínimos/máximos e maior módulo individual.
Não houve NaN nas métricas dessas células. Não se calculou uma média global
misturando células correlacionadas.

## A escolha de ±11 sobrevive à correção?

No LOSO completo, o ganho de ±11 sobre ±2 permanece positivo em κ e especificidade
nos três braços, com ICs pareados acima de zero:

| Braço / métrica | Ganho ±11 antes | Ganho ±11 corrigido [IC95 pareado] |
|---|---:|---:|
| `cabeca/kappa` | +0,074995 | +0,073765 [+0,059270; +0,088634] |
| `cabeca/especificidade` | +0,100748 | +0,095107 [+0,078036; +0,113830] |
| `cabeca_e4/kappa` | +0,081859 | +0,079871 [+0,063391; +0,096092] |
| `cabeca_e4/especificidade` | +0,106378 | +0,102089 [+0,083285; +0,120605] |
| `pulso/kappa` | +0,057704 | +0,060712 [+0,042845; +0,079392] |
| `pulso/especificidade` | +0,119256 | +0,114254 [+0,094291; +0,134627] |

No pulso das coortes externas, os efeitos corrigidos são:

| Coorte | Ganho κ de ±11 [IC95] | Ganho especificidade de ±11 [IC95] | Efeito HMM ±2 em especificidade [IC95] |
|---|---:|---:|---:|
| `newcastle` | +0,065967 [+0,034672; +0,097303] | +0,080954 [+0,052797; +0,111268] | -0,038123 [-0,061712; -0,015764] |
| `walch_principal` | +0,043288 [+0,015547; +0,073927] | +0,088295 [+0,067104; +0,110736] | -0,050997 [-0,086003; -0,016168] |
| `walch_todos` | +0,046848 [+0,020109; +0,074921] | +0,088328 [+0,067416; +0,109350] | -0,046858 [-0,078473; -0,014733] |

As direções primárias de P1–P3 permanecem; isso é evidência das coortes anteriores,
**não resultado nem confirmação na DREAMT**. P1–P3 continuam como registradas.

A mudança de sinal de quatro médias secundárias está no adendo. Não houve
mudança de sinal das médias nos efeitos LOSO nem nos contrastes intraindividuais
dos punhos. Os [efeitos completos](../ml/experimentos/saida/ml17/efeitos.json)
e [contrastes dos punhos](../ml/experimentos/saida/ml17/lados_intra_sujeito.json)
incluem os ICs, suportes e o controle incorreto de empilhar lados como pessoas.

## F1 e verificações independentes

- [F1 complementar](../ml/experimentos/saida/ml17/f1_complementar.json): todas as
  69 células. Maior mudança individual, em módulo, em F1 de vigília: **0,196078**, em Walch
  principal/cabeça/±11+HMM (mudança média −0,013188). Não houve valores inválidos
  de F1 nestas células; falhas completas continuam valendo zero.
- Verificador sem importar `src/avaliar` recalculou cinco métricas a partir de
  **144 capturas** de predições. **Maior erro absoluto 0; zero divergências**
  com tolerância absoluta de 1e-12.
- Controle de repetição: os caminhos ML-04 e ML-04b ajustam novamente as 12
  células do Newcastle esquerdo em cada versão. **24 células, 730.560
  predições comparadas, zero diferença**.
- CI verifica o contrato dos agregados, ausência de notas/índices individuais e
  hashes UTF-8/LF; uma média adulterada reprova pela integridade do arquivo.
  A auditoria local separada usa math.fsum/statistics.stdev: 345 combinações
  célula/métrica em 69 células, zero divergências nas médias, desvios e extremos.
  Não recompõe ICs bootstrap. Guardas de fontes leem o commit histórico registrado.
- **245 testes ML passaram em 06/11**, incluindo os controles e os **40 + 19 dourados**.
  Nenhum arquivo/valor dos dourados ou firmware foi alterado. CI testa código
  e coerência das evidências; não reexecuta os datasets ausentes do Git.

[Verificação publicada](../ml/experimentos/saida/ml17/verificacao_predicoes.json).
Os quatro testes de defeito falharam no d429d43 por valores de janela;
os dois de HMM/Viterbi entre participantes já passaram lá. Esta distinção
permanece no [relatório da primeira entrega](ML-17-CODIGO-E-TESTES.md).

## Interpretação e limites

A comparação mede o conjunto de correções: contexto por participante/gravação/
segmento e operações temporais associadas. HMM/Viterbi do ML-04 já separavam
participantes; a extensão trata quebras internas. **Não foi feita uma ablação
para atribuir cada parcela do efeito separadamente à janela, às transições
ou ao reinício do Viterbi.** Features intra/interépoca e firmware permanecem
inalterados. As diferenças angulares da reconstrução foram isoladas por entrada comum.

Os ICs são pontuais por célula, com bootstrap pareado de participantes,
2.000 reamostragens e seed 20260910. Reamostram os escores observados, não
refazem o treino a cada reamostragem; não há correção por multiplicidade.
Os logs preservam a saída dos scripts, inclusive seu seed padrão de IC pareado
onde aplicável; os ICs do relatório foram recalculados segundo o protocolo.

**Não refeitos nesta etapa:** ML-02 real, matriz completa de transferência/ablação,
Random Forest, itens 6/7/mediana das otimizações, seleção de features ML-11,
quantização e validação aninhada ML-12 completa. Seus chamadores foram auditados/
migrados; seus números históricos não são apresentados como resultados do código
corrigido. Tampouco houve avaliação, treino ou carregador da DREAMT, nem validação
do sensor no travesseiro. Essas bases usam sensores presos ao corpo.

## Reprodução e armazenamento

A partir da raiz do repositório, ambiente pinado, dados obtidos legalmente:

1. Preparar os caches novos com `ml03b_otimizacoes --preparar-cache` e
   `ml04_validacao_externa --preparar`, usando caminhos explícitos de bruto/cache.
   Na Walch, passar a pasta que contém `labels/` e `motion/`.
2. Executar `ml/ferramentas/censo_contexto_ml17.py`. O padrão é exato;
   a opção angular do legado precisa ser informada e o resultado registrado.
3. Usar o executor do commit 11fa375, `rodar_ml17.py --preparar` com
   `--pasta`, `--cache`, `--censo`, seguido de `--rodar`.
   O manifesto preserva as fontes e exige entrada imutável.
4. `resumir_ml17.py --pasta PASTA_DA_RODADA --saida PASTA_DOS_RESUMOS`
   confere os hashes e exporta somente agregados; exige fontes de análise commitados.
   Após realocação, passar também `--cache NOVO_CACHE --censo NOVO_CENSO`: ambos
   são conferidos pelos hashes originais, sem alterar o manifesto privado.
5. `auditar_resumos_ml17.py --pasta PASTA_DA_RODADA --publicos PASTA_DOS_RESUMOS
   --saida RELATORIO_LOCAL.json` recompõe as estatísticas das notas locais e compara
   com os agregados públicos. Não executa ajuste de modelo; o clone sem os dados
   pode testar contrato/hashes, mas não recompor essas médias das notas ausentes.

Dados brutos continuam no armazenamento original do projeto. Caches, logs,
JUnit, cópias Git, rótulos e predições foram realocados para o diretório lógico
`dados-locais/ml17-evidencias-2026-11-05/`, fora da worktree e do Git; caminho
absoluto informado ao autor. Foram copiados com robocopy /E /XJ e conferidos
614 arquivos por tamanho e SHA-256 antes de remover somente a origem.
REALOCACAO.json, privado, guarda o inventário e os caminhos originais.
O manifesto congelado não foi reescrito: seus caminhos absolutos de cache/censo
continuam registrando o local da execução. O executor congelado exige esses caminhos; não se promete retomada direta de
treinamento após mover a evidência. O exportador atual aceita os caminhos novos,
verifica caches/censo/fontes pelos hashes antigos e tolera apenas a conversão
LF/CRLF do executor feita pelo Git; mudança de código é recusada.
Os comparadores aceitam --pasta no novo local e foram reexecutados dali:
69 células idênticas ao pacote preparado, 144 capturas e cinco métricas com erro
máximo zero, 24 células repetidas e 730.560 predições sem divergência. **Nenhuma junction criada ou encontrada** na worktree/
execuções. Não houve cópia dos brutos. Antes de copiar/remover evidência, conferir
links e usar `rmdir` sem `/s` para junctions e `robocopy /E /XJ` para cópia.

A ML-17 fica concluída nesta segunda PR, sujeita à revisão e à ordem de integração.
A ML-13 permanece aberta; seguir com o carregador/avaliação só após integrar a
correção e considerar o adendo. Texto do TCC e Google Docs não foram alterados.

## Revisão e publicação aprovada (06/11)

Develop 1b5c82c70262604f57d49faad4bcdafc71488ef1 integrado nas duas branches,
com LGPD-02 fechado e LGPD-09/10 abertos. A #91 abre ML-17 (39 a 40); esta
segunda PR fecha o item (40 a 39): L0 8/L1 14/L2 7/L3 10. Notas explicitam a
base; diário vi/vii antes de viii/ix, preservadas também x/xi de outros itens.
A #91 recebeu guarda AST com somente três exceções intencionais (ML-12, ML-15,
censo): cinco grupos acusam 22/22 mutações isoladas em 11 chamadas. A suíte
completa de 06/11 repete esses controles, além de publicação, realocação e
integridade histórica. Os seis testes no código antigo foram reexecutados em
05/11: quatro falhas numéricas de janela e dois sucessos HMM/Viterbi.
Nenhuma nova rodada de ajuste de modelo: o código numérico permanece intacto.

**Escolha expressa do autor em 06/11:** publicar resumos das 69 células (médias,
desvios, ICs, n válido, diferenças pareadas e maiores módulos individuais sem ID),
manifesto e verificadores. Vetores de notas, índices de extremos, rótulos/predições
e caches permanecem externos. O pacote público tem sete JSONs e nenhum vetor de
notas. Os três JSONs anteriores com vetores foram rejeitados pela nova guarda
antes da conversão; nunca foram commitados/publicados nesta entrega.

O manifesto registra os hashes dos seis resumos em UTF-8/LF e a referência do
código de análise/exportação (3eadf884882b9feade13afaae1a6f1e3033eeba7). O CI
confere estrutura, integridade e fontes históricas, sem alegar recompor médias
sem as notas. O verificador local recompôs 345 combinações célula/métrica com
aritmética independente, sem divergência; predições também foram reconferidas
na exportação (144 capturas, erro máximo zero; repetição sem diferença).
A realocação preserva o manifesto congelado. Dados brutos não foram movidos.

**Licença efetivamente lida:** README.txt do Wearanize+ OA declara CC-BY 4.0;
LICENSE.txt tem SHA-256
26a75f49a0c9894a6c8239dc9de20f36d031e12ee04fcc2f74db87e2c00059e5.
Não é a licença MIT dos scripts nem o DUA da coleção restrita. A
[coleção oficial OA](https://data.ru.nl/collections/di/dcmn/DSC_wrnzpoa_t0000925a_195)
e as [instruções dos autores](https://github.com/Niloy333/Wearanize_plus#access-instructions)
exigem pesquisa científica e proíbem tentar identificar participantes.
A [CC BY 4.0, §§2–3](https://creativecommons.org/licenses/by/4.0/legalcode.en)
permite compartilhar material e derivados, exigindo atribuição, licença e
indicação de alterações; direitos de privacidade não são licenciados (§2b).
Conclusão interpretativa: métricas individuais científicas sem identificação
são compatíveis com a permissão de derivados; não há autorização específica
para métricas por participante nem garantia de anonimato só por remover IDs.
Publica-se o pacote agregado aprovado acima. O manifesto atribui Wearanize+ OA
e identifica os cálculos como modificações do projeto, com links à licença, à
coleção OA e às referências solicitadas pela coleção:
[artigo](https://doi.org/10.1093/sleepadvances/zpaf094) e
[coleção primária](https://doi.org/10.34973/j6jf-9e62).
