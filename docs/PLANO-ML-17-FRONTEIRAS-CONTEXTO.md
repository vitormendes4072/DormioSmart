# ML-17 — contexto por participante e por segmento contínuo

**05/11/2026 — plano aprovado com os ajustes abaixo; implementação em andamento.**
Base consultada: `origin/develop` `d429d43e1b7bafacae67fbebb9a328942d63efff`
(PR #90 integrada). Dono: Codex, conforme indicação do autor.
A ML-13 permanece aberta; a avaliação da DREAMT depende da conclusão da ML-17.

## Ajustes aprovados antes da implementação — 05/11

- Duas PRs para develop: a primeira entrega código, testes de fronteira,
  guarda histórica da ML-15 e contrato de caches versionados; a segunda parte
  da primeira e entrega rodadas/relatório antes-depois. Ordem de merge: primeira,
  depois segunda. A ML-13 continua aberta.
- HMM e Viterbi do ML-04 já separam participantes no develop. Seus testes entram
  como regressão e devem passar no d429d43. Os testes de janela entre participantes
  e de lacunas devem falhar nesse commit. Grupos serão reportados separadamente.
- Contexto não existe no firmware. Arquivos e valores dos testes do vetor dourado
  não serão alterados; qualquer mudança necessária neles interrompe o trabalho.
- Antes de iniciar treinamentos/avaliações, informar o censo de épocas de contexto
  alteradas por coorte/braço. Separar mudança de vizinhança de mudança numérica.

## Diagnóstico por leitura

`empilhar_contexto`, em `ml/src/epocas.py`, replica as pontas da matriz recebida,
mas não conhece participantes, gravações ou lacunas. Receber a coorte inteira
faz a janela atravessar as fronteiras. Não há medição nova do efeito nas métricas.

- ML-04: contexto aplicado depois da concatenação no treino Wearanize e nos
  destinos Newcastle/Walch; também no caminho de comparação dos punhos.
- ML-03b: `montar_X` e as otimizações operam sobre matrizes concatenadas, inclusive
  a comparação ±2/±11 que ajudou a escolher a janela.
- ML-02 e `processar_gravacoes`: já empilham dentro de cada gravação. O risco aqui
  é comprimir épocas depois de retirar rótulos inválidos ou épocas sem cobertura,
  tornando vizinhas linhas que não eram contíguas no tempo.
- ML-11 e quantização usam a base concatenada. ML-12 tem um caminho por sujeito
  e um caminho global deliberado de comparação; o caminho por sujeito não resolve
  lacunas internas.
- O adaptador da ML-15 também empilha por sujeito, mas não tem os índices de época.
  Sua reprodução histórica não deve mudar de significado silenciosamente.

**Antecedente:** o diário de 30/10 (iv), ML-12, já registra a diferença entre
contexto global e por sujeito para ±2. Esta leitura não transforma aquele efeito
em evidência para ±11, para a validação externa ou para segmentos descontínuos.
O novo relatório revisará explicitamente esse limite, sem apagar a entrada antiga.

## Abordagem proposta

### 1. Fixar a identidade temporal e versionar os caches

Preservar, desde `idx` devolvido por `fatiar_epocas`, para cada linha:
participante, gravação e índice original da época. Depois do filtro de rótulos,
uma nova sequência começa quando muda participante/gravação ou o índice deixa
de aumentar exatamente uma unidade. Não agrupar por ID apagando as fronteiras
entre blocos separados do mesmo participante.

Os caches de features Newcastle/Walch e o cache base Wearanize atuais descartam
esses índices. Criar uma versão nova com identidade de fontes, configuração,
ordem e seleção; recusar cache antigo no caminho corrigido. Regenerar os dados
derivados necessários a partir dos brutos, sem sobrescrever caches/evidências
históricos. Não inventar continuidade com `arange` sobre a matriz filtrada.

Dados e caches externos serão indicados explicitamente por argumentos/caminhos
de execução; nenhuma junction. Na comparação, conferir a igualdade de X, y, IDs
e ordem entre as entradas antigas e reconstruídas. Se divergir, investigar e
separar esse efeito antes de atribuir diferenças ao contexto.

### 2. Centralizar o empilhamento por segmento

Manter a primitiva de replicação das pontas de um único segmento e acrescentar
um caminho explícito segmentado reutilizável em `ml/src/epocas.py`.
Validar comprimentos e identidade temporal; segmentos vazios, unitários ou menores
que a janela devem funcionar sem buscar linhas de outro segmento.

Migrar todas as chamadas de produção/experimentos inventariadas, inclusive
ML-02, ML-03b (ablação e otimizações), ML-04 e comparação de lados, ML-11,
quantização e o caminho corrigido da ML-12. Manter os controles globais deliberados
da ML-12 explicitamente identificados como controles, nunca como padrão corrigido.

Usar a mesma identidade de segmento nas operações temporais associadas:
transições HMM apenas dentro de segmentos do treino; Viterbi e mediana reiniciados
a cada segmento da avaliação. A normalização por participante continua usando
somente X. Não alterar limiares, modelos, features, seed ou hiperparâmetros.

### 3. Provar o defeito antes da correção e o alcance depois

Adicionar testes em `ml/testes/`, com dados artificiais:

- Duas pessoas com features sentinela distintas; a janela da última época de A
  não pode conter B. Cobrir ±2, ±11 e participantes curtos.
- Mesmo participante com duas gravações e com uma lacuna no índice original:
  contexto não atravessa nenhuma dessas fronteiras.
- Filtro de rótulo inválido e época sem cobertura no caminho real ML-02/carregamento:
  o filtro preserva a quebra temporal.
- Invariância: mudar, permutar ou acrescentar outros participantes/segmentos não
  altera o contexto de um segmento já existente.
- Transições HMM, Viterbi e mediana respeitam a mesma segmentação.
- Cache sem os índices necessários reprova; o cache novo preserva-os ao salvar/ler.

Executar testes de fronteira contra o develop congelado em d429d43 antes de editar
o código: devem falhar por valores de janela incorretos, não por import ou função
inexistente. Testar chamadas reais dos experimentos, não apenas uma função nova.

Depois executar as sabotagens: restaurar empilhamento global numa chamada real,
remover a quebra na lacuna e permitir reutilização do cache antigo. Registrar
qual teste acusa cada defeito e por qual mecanismo. Reexecutar controles nesta
sessão, sem herdar relatos anteriores.

### 4. Preservar a procedência da ML-15

O teste `test_evidencias_publicadas_cobrem_a_rodada_completa` compara hashes de
fontes históricas aos arquivos atuais. Ao corrigir epocas/ML-04, essa igualdade
deixará de fazer sentido. Conferir as fontes no commit histórico registrado,
sem reescrever manifesto, números ou resultados da ML-15. O teste deve continuar
acusando adulteração de fonte histórica/evidência e ausência de histórico.

Manter o adaptador histórico como reprodução declarada do algoritmo antigo;
a nova rodada usa o caminho corrigido, sem reutilizar o adaptador como atalho
que perca índices temporais. Ajustar o checkout do CI para disponibilizar o
histórico necessário, com controle positivo.

### 5. Medir o efeito com a mesma entrada

Antes de executar, congelar lista de participantes, hashes de entrada, protocolo,
versões, seed 20260910, configuração aec203907e6f e uma thread nativa efetiva.
Manter dobras, exclusões, modelos e opções iguais entre antes e depois.

Rodada principal: ML-04 completo nas quatro configurações
`base_ctx2`, `item8b_hmm`, `item9_ctx11`, `item9b_ctx11_hmm`, nos três braços,
para Newcastle/punho esquerdo e Walch principal + secundária com baixa taxa.
São 36 células por versão. Repetir também a comparação dos punhos do ML-04b.

Para conferir a escolha da janela, repetir ML-03b otimizações baseline, 8b e 9,
com os 92 participantes e os três braços. Testes funcionais cobrem as demais
chamadas; não declarar que ML-11, quantização, ablação inteira ou seleção aninhada
foram reavaliadas se não tiverem sido. O relatório apontará quais resultados
históricos continuam somente como evidência do código anterior.

Comparar a versão antiga e a corrigida nesta mesma máquina/ambiente, com saídas
novas e isoladas. Além de média/desvio/IC, informar diferenças pareadas por
participante, maior aumento, maior queda e máximo absoluto por célula de κ,
especificidade e acurácia; reportar suporte/NaN e F1 complementar. Medir quantas
épocas de contexto mudaram e sua distribuição nas fronteiras/lacunas. Não
pressupor que as diferenças de predição fiquem restritas às pontas, pois o treino
também muda.

Se necessário para explicar o efeito, separar comparação com fronteiras apenas
de participante da versão completa por segmentos, identificando as condições.
Os históricos e seus manifestos permanecem intactos.

### 6. Liberar a DREAMT somente depois da revisão

Manter P1–P3 da ML-13 como registradas. Comparar a direção de cada efeito em
Newcastle/Walch corrigidos; se alguma mudar, registrar adendo datado e commitado
antes de rodar DREAMT, conservando a previsão original e a justificativa.
Uma correção sem mudança de direção também será documentada, sem alegar que isso
confirma previamente as previsões na terceira coorte.

## Arquivos e entrega

Previstos: `ml/src/epocas.py`, `ml/src/carregar/base.py`,
`ml/src/carregar/__init__.py`, os módulos de experimento inventariados com chamadas
(incluindo ML-03b ablação/otimizações), utilitários de cache/rodada necessários,
`ml/src/modelos.py`, testes de fronteira e de procedência histórica, e
`.github/workflows/ci.yml` se necessário ao histórico.
ML-12 global e adaptador histórico receberão tratamento explícito de controle/
reprodução; não serão convertidos silenciosamente.

Registro: linha da ML-17 e sua contagem, diário com oito campos, relatório com
matriz antes/depois, código/ambiente/entradas e limitações. Integração de
origin/develop antes da revisão, três conferências e suíte ML/CI verdes.
Não haverá merge ou push em develop/main pelo Codex.

**Para o TCC:** remover contaminação temporal torna a evidência de transferência
entre participantes/coortes defensável; não valida o sensor no travesseiro.
A atualização do texto acadêmico ficará com o responsável por essa área.

**Critério de conclusão:** testes de fronteira vermelhos no código antigo e verdes
no corrigido, sabotagens detectadas, nenhuma chamada não classificada, entradas
temporais rastreáveis, rodada e dispersão publicadas com os limites e procedência
histórica preservada. O carregador/avaliação DREAMT não fazem parte desta correção.

**Plano aprovado.** As rodadas permanecem posteriores ao censo de contexto e à
validação do código; a entrega se divide nas duas PRs descritas no adendo.
