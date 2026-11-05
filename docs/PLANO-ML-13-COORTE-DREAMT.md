# ML-13 — próximo plano e previsão para a coorte DREAMT

**Registro em 05/11/2026, antes de qualquer avaliação na DREAMT.**
Status: **proposta para aprovação do autor**. A preparação e a integridade dos
dados foram verificadas; o carregador e a avaliação ainda não foram implementados.
Nenhuma feature, prevalência empírica dos rótulos ou métrica de desempenho da
DREAMT foi calculada. As previsões abaixo não são resultados observados.

## Objetivo e base da previsão

Aplicar à terceira coorte externa os classificadores treinados no Wearanize+,
sem ajustar parâmetros, limiares ou HMM aos rótulos da DREAMT. Isso testa se as
direções dos efeitos observadas no Newcastle e na Walch se repetem. Continua sendo
evidência sobre acelerometria de pulso/cabeça, sem validar o sensor no travesseiro.

O braço primário será **pulso**; cabeça e cabeça-E4 serão análises secundárias
predefinidas, não alternativas para escolher a melhor depois do resultado. Usar
os mesmos 92 participantes de treino e as quatro configurações do ML-04:
`base_ctx2`, `item8b_hmm`, `item9_ctx11`, `item9b_ctx11_hmm`. Configuração
`aec203907e6f`, seed `20260910`, bibliotecas pinadas. Registrar também versões,
pools nativos e a quantidade efetiva de threads, fixada em uma para a nova rodada.

Fundamentação disponível antes da DREAMT: no braço pulso, a janela ±11 aumentou
κ e especificidade no Newcastle e na Walch. O HMM aumentou κ em magnitudes
diferentes e reduziu a especificidade nas duas. A previsão anterior da Walch
não se confirmou integralmente para κ do HMM; não se repetirá essa previsão
como se já houvesse sido confirmada. Fontes: `ml/README.md`, seção Walch;
`docs/DIARIO-DE-ENGENHARIA.md`, 03/11 (vii)–(ix); JSONs externos anteriores.

## Previsões registradas

As três previsões referem-se ao braço pulso, com participante como unidade de
avaliação. Diferenças usam bootstrap **pareado**, não sobreposição de ICs.

| ID | Previsão | Critério antecipado |
|---|---|---|
| P1 | A configuração ±11 mantém desempenho acima do trivial "sempre dormindo". | Limite inferior do IC 95% de κ de `item9_ctx11` acima de zero. |
| P2 | A janela ±11 preserva o ganho de κ e de especificidade sobre ±2. | Limites inferiores dos ICs 95% pareados de Δκ e Δespecificidade (`item9_ctx11 − base_ctx2`) acima de zero. |
| P3 | O HMM volta a reduzir especificidade sobre a base ±2. | Limite superior do IC 95% pareado de Δespecificidade (`item8b_hmm − base_ctx2`) abaixo de zero. |

Se o IC incluir zero, o efeito direcional fica **inconclusivo**, não confirmado.
Um IC inteiramente na direção contrária refuta a previsão direcional. Falhar o
critério de P1 impede afirmar a generalização prevista. P2 requer os dois ganhos;
ganho em apenas uma métrica não confirma a previsão conjunta. Não se substituirá
o braço pulso por outro braço para declarar confirmação.

Não se fixa uma faixa de valores absolutos nem o sinal do Δκ do HMM. A configuração
±11+HMM e os outros braços serão apresentados integralmente como secundários.
Valores fora do esperado serão reportados, não usados para ajustar o protocolo.

## Plano de implementação proposto

1. **Inspecionar o contrato real, sem inferência.** Ler CSVs em fluxo, usando apenas
   tempo, aceleração e estágio para o pipeline. Conferir passo temporal, escala,
   valores ausentes, lacunas e alinhamento da pontuação. A documentação declara
   grade de 64 Hz, ACC de origem a 32 Hz e unidade 1/64 g; isso ainda precisa de
   confirmação nos sinais. Medir dispersão e extremos de problemas de qualidade,
   não só médias. Não usar colunas de apneia ou outros sinais como features.
2. **Fixar o protocolo de carregamento antes das métricas.** Definir, a partir da
   inspeção, a âncora das épocas PSG de 30 s e o tratamento de preparação `P`,
   `Missing`, lacunas e épocas incompletas. Não converter preparação em vigília
   nem preencher ausência de medição por interpolação longa. Se a grade de rótulo
   não puder ser comprovada, registrar o impedimento antes de avaliar. Qualquer
   adendo de protocolo será datado e commitado antes dos resultados.
3. **Implementar o carregador e a seleção da coorte.** Criar
   `ml/src/carregar/dreamt.py`, com caminho recebido explicitamente; registrar
   a coorte no carregamento e acrescentar `--coorte dreamt --dados-brutos CAMINHO`
   ao ML-04. Para DREAMT, a ausência de caminho deve reprovar. Não criar junctions
   ou embutir caminhos de máquina. Treino/cache Wearanize também deve ser recebido
   por caminho explícito, com identidade conferida, sem depender de uma ligação
   ao diretório bruto principal.
4. **Testar com dados artificiais e controles positivos.** Cobrir conversão de
   unidade, grade 64/32 Hz, alinhamento dos estágios, preparação/ausência, coluna
   ausente, arquivo truncado, lacunas e segmentos descontínuos. Testar a passagem
   de `--dados-brutos`, a falha sem caminho e a invariância das features a colunas
   clínicas não utilizadas. Rodar os casos contra o código anterior e executar
   as sabotagens, indicando o mecanismo de cada reprovação.
5. **Auditar contexto e HMM antes da rodada externa.** Não concatenar contextos
   entre participantes ou através de lacunas. As transições HMM vêm somente do
   treino; a normalização por participante usa somente X. A leitura do caminho
   atual do ML-04 mostra empilhamento sobre matrizes concatenadas: isso precisa
   de análise explícita antes da extensão, sem alterar silenciosamente os
   resultados antigos. Se uma correção compartilhada for necessária, apresentar
   seu alcance e validação ao autor antes de prosseguir.
6. **Preservar a procedência histórica.** A guarda da ML-15 hoje confere hashes
   das fontes contra os arquivos atuais. Estender ML-04 muda esses bytes; a
   guarda deve passar a conferir o commit histórico registrado, sem reescrever
   os manifestos da ML-15. Esse ajuste e o histórico necessário no checkout do
   CI precisam constar da implementação e dos testes, com controle positivo.
7. **Executar a avaliação somente depois da aprovação e do protocolo congelado.**
   Usar todas as quatro configurações e os três braços. Não selecionar/excluir
   participantes pelo desempenho nem ajustar parâmetros na DREAMT. Registrar
   exclusões físicas justificadas, suporte, NaN legítimo e n válido por métrica.

## Medidas e apresentação previstas

- κ, especificidade e acurácia por participante, com média, desvio e IC 95% por
  bootstrap de 2.000 reamostragens e seed fixa. Trivial medido na própria coorte.
- Diferenças pareadas contra a base, com IC, maior aumento e maior queda por
  participante e por célula. Não resumir divergências somente pela média.
- F1 corrigido e matrizes de confusão como análise complementar, sem passar a
  selecionar modelos por F1 depois dos resultados.
- Todas as configurações, exclusões e resultados secundários serão reportados.
  Comparar direções com Newcastle/Walch; três coortes ainda limitam a precisão
  de qualquer análise entre populações.
- Dados, rótulos, predições e detalhes individuais ficam no armazenamento local
  ignorado. Publicar apenas código, protocolo e resumos compatíveis com o termo
  de uso, sem redistribuir os dados clínicos.

## Arquivos previstos e entrega

Principalmente `ml/src/carregar/dreamt.py`, o registro em
`ml/src/carregar/__init__.py`, `ml/experimentos/ml04_validacao_externa.py` e testes
correspondentes. A guarda de fonte histórica e o checkout de CI serão ajustados
se a implementação tocar as fontes registradas pela ML-15. Diário e linha própria
da ML-13 registrarão o progresso e as conferências.

Antes de pedir revisão: atualizar `origin/develop`, integrar na branch, resolver
conflitos, rodar as três conferências e os testes aplicáveis, com CI verde. A PR
continua apontando para `develop`; merge depende da revisão e autorização.

**Esta próxima etapa aguarda aprovação.** Nenhuma avaliação da DREAMT está
autorizada ou executada por este documento sozinho.
