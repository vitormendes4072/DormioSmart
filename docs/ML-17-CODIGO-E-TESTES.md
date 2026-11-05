# ML-17 — primeira entrega: código, fronteiras e caches

**05/11/2026, Windows local, Python 3.11.9.** Base `origin/develop`
`d429d43e1b7bafacae67fbebb9a328942d63efff`. Esta é a primeira de duas PRs.
A ML-17 e a ML-13 continuam abertas; rodadas e relatório antes/depois ficam
na segunda PR, que parte desta e também aponta para develop.

## Prova antes de corrigir

O arquivo `test_fronteiras_contexto.py` foi executado contra uma cópia congelada
dos arquivos versionados em d429d43, antes da edição dos fontes.

| Grupo | Casos | No develop | Mecanismo |
|---|---:|---|---|
| Defeito: janela entre participantes, ±2 e ±11 | 2 | falham | Valores da janela incluem o vizinho |
| Defeito: lacuna após filtro de rótulos, ±2 e ±11 | 2 | falham | Épocas antes/depois da lacuna aparecem adjacentes |
| Regressão: transições HMM entre participantes | 1 | passa | Não conta a emenda como transição |
| Regressão: Viterbi do ML-04 entre participantes | 1 | passa | Suavização já separada por participante |

Resultado: **4 falhas e 2 sucessos**, por valores, sem falha de import/assinatura.
Os dois últimos testes não são apresentados como defeitos corrigidos.

## Código e alcance

- Segmentação construída de participante, gravação e índice original de época,
  preservados antes de remover rótulos inválidos. Não reagrupa blocos separados
  do mesmo ID. Contexto replica somente as pontas do próprio segmento.
- Carregamento comum, ML-02, ML-03b ablação/otimizações, ML-04 e comparação de
  punhos, ML-11 e quantização usam o contexto segmentado. A ML-12 usa segmentos
  no caminho principal; seu contexto global deliberado continua como controle.
- HMM/Viterbi já separavam participantes no ML-04. A extensão aplica a mesma
  proteção a lacunas internas; mediana e transições de treino também respeitam
  segmentos. Nenhum rótulo de teste é usado para ajustar o HMM.
- O adaptador histórico `rodada_reproducao.py` permanece intacto e classificado
  como reprodução do código histórico. Não será usado como atalho para a rodada
  corrigida, pois não preserva os índices. A reprodução antiga exige as fontes
  históricas, não uma combinação com os fontes corrigidos atuais.
- Saídas corrigidas têm diretório próprio `ml17-v1`. Checkpoints das otimizações
  incluem versão, fontes de execução, configuração, entradas e segmentos.

## Caches versionados, dados fora do Git

`src/cache_temporal.py` define o contrato `ml17-v1`: configuração, hashes
das fontes de preparação, seleção de treino e identidade temporal por linha.
NPZ guarda `indice_epoca` e `gravacao`; o cache Wearanize guarda esses campos
por braço. Formato antigo/incompatível é recusado, sem assumir continuidade.

O cache base tem chave nova; Newcastle/Walch usam diretórios novos. A preparação
recebe os caminhos externos explicitamente (`--pasta` no ML-03b e
`--dados-brutos`/`--dados-wearanize` no ML-04), com `--cache` e
`--saida-dir` para isolar a execução. Nenhuma junction é necessária.
`--preparar-cache` no ML-03b prepara somente features, sem ajuste de modelos.

Os hashes de código/configuração não substituem a conferência das entradas.
Antes das rodadas, `ferramentas/censo_contexto_ml17.py` exige igualdade de
X, y, IDs, ordem e arquivos com o legado; se houver divergência, interrompe a
atribuição do efeito exclusivamente ao contexto. Conta separadamente épocas
com vizinhança alterada e vetores numericamente alterados, para ±2 e ±11.

A regeneração dos dados derivados foi iniciada no armazenamento ignorado desta
worktree, com dados brutos externos e sem copiar/linkar os datasets. O censo
será informado ao autor antes de treinar/avaliar. Esta primeira entrega não
anuncia uma conclusão numérica da repetição das coortes.

## Guarda histórica e controles executados

A guarda da ML-15 agora lê os 25 fontes do commit `base_codigo` registrado no
manifesto e confere seus hashes normalizados em LF. Alterar o código atual
não exige reescrever a evidência antiga. Manifesto, resultados e adaptador
históricos não foram modificados. O CI ML obtém o histórico completo.

Controles: hash histórico adulterado, commit indisponível e manifesto de fontes
vazio reprovam. Cinco sabotagens da correção também foram executadas por testes:
janela global restaurada numa chamada real, lacuna apagada, cache antigo aceito,
HMM juntando participantes e Viterbi juntando participantes. Cada uma é acusada
pela verificação correspondente, nomeada em `test_controles_ml17.py`.

## Verificação local e limites

**217 testes passaram** na suíte ML completa. Novos casos cobrem consumidores
reais do ML-04, persistência após filtro e passagem dos segmentos pela retomada,
além de fronteiras, caches e controles. Piso de coleta do CI atualizado para 217.

**Dourados intactos:** nenhuma edição nos arquivos dos testes/vetores dourados
ou no firmware. Os 40 testes de `test_vetor_dourado.py` e os 19 de
`test_dourado_cadeia_c2.py` passaram dentro da suíte. Não houve alteração das
features intra-época; contexto continua sendo uma operação de ML fora do firmware.

Não foram executados treinamentos ou avaliações de desempenho nesta etapa.
A regeneração/censo não confirma nem refuta P1–P3 da DREAMT. A segunda PR
registrará dispersão, máximos por participante/célula, o que foi repetido e
o que não foi; qualquer mudança de direção terá adendo antes da DREAMT.

## Evidência local

JUnit antes/depois, cópia congelada do develop e logs de preparação:
`ml/dados/processado/ml17/`, ignorado pelo Git. Os brutos continuam no
armazenamento original do projeto; caminhos completos informados ao autor.
Não se criou junction, cópia de dados brutos ou ligação para esse diretório.
A evidência privada anterior da ML-13 permanece na sua worktree anterior.

Antes de copiar/remover uma pasta, conferir reparse points; desfazer junctions
com `rmdir` sem `/s` e copiar evidência com `robocopy /E /XJ`.
