# ML-17 — protocolo congelado antes das rodadas

**05/11/2026, antes de treinar/avaliar as coortes nesta etapa.**
Primeira entrega: PR #91. A segunda PR parte dela e aponta para develop;
ordem de merge: #91, depois a PR de rodadas. Nenhum merge pelo Codex.

## Código, entrada e execução fixados

- Antes: d429d43e1b7bafacae67fbebb9a328942d63efff.
- Depois: 3273431b6ebec4e3889bd3f01c3593b32dc0137e (código da #91).
- Configuração aec203907e6f, seed 20260910, bibliotecas pinadas, Python 3.11.9,
  Windows local. Uma thread nativa por processo, no máximo dois processos.
- Mesmos 92 participantes do treino, mesmos rótulos/ordem/seleções e modelos.
  Quatro configurações, três braços; Newcastle esquerdo e Walch principal/todos.
  Repetir punhos do ML-04b e baseline/8b/9 do ML-03b completo.
- Fontes exportados do Git, sem JSON/checkpoint histórico no diretório de saída.
  Adaptadores do executor só indicam entradas e registram métricas/predições;
  não substituem contexto, ajuste ou inferência dos fontes congelados.
- Congelar hashes dos fontes, executor, censo e caches. Os estados das execuções
  registram também hashes de X/y/IDs efetivamente carregados; a comparação recusa
  entradas diferentes entre antes e depois ou rodadas incompletas.

## Divergência encontrada na regeneração e como será isolada

Wearanize (três braços) e Walch (duas variantes) reconstruíram X/y/IDs exatamente.
No Newcastle, y/IDs/ordem e as seis features intra-época também são exatos, mas
os dois ângulos têm diferenças em relação ao cache legado:

| Destino | Máximo absoluto, graus | Média absoluta nas oito features | Épocas com alguma diferença | Participantes com diferença | Maior número de épocas diferentes em um participante |
|---|---:|---:|---:|---:|---:|
| Esquerdo | 2,842170943040401e-14 | 6,221342976485442e-17 | 1.017 | 27 | 69 |
| Direito | 2,842170943040401e-14 | 6,588159205405496e-17 | 1.036 | 26 | 88 |

O conferidor exato bloqueou a primeira tentativa. A causa dessa diferença
numérica não foi determinada; não será atribuída a threads ou bibliotecas
sem controle que o demonstre. Nenhum arquivo/teste dourado foi modificado.

**Antes e depois usarão o mesmo X reconstruído**, não X antigo numa versão e X
novo na outra. Portanto esta é uma comparação do código sobre entrada comum,
não uma promessa de reproduzir bit a bit os números históricos originais.
O censo conserva padrão exato; uma opção explícita limita a diferença legada
somente às duas colunas angulares, até 3e-14 graus, registrando a dispersão.
Qualquer diferença nas outras features, y, IDs/ordem ou acima desse limite
reprova. A igualdade entre as entradas efetivas das duas rodadas permanece exata.

## Censo informado ao autor antes das rodadas

| Coorte / braço | Épocas | Vizinhanças/vetores alterados ±2 | Vizinhanças/vetores alterados ±11 |
|---|---:|---:|---:|
| Wearanize / cabeça | 87.795 | 385 | 2.090 |
| Wearanize / cabeça E4 | 87.795 | 385 | 2.090 |
| Wearanize / pulso | 87.795 | 385 | 2.090 |
| Newcastle / esquerdo | 30.440 | 104 | 572 |
| Newcastle / direito | 29.385 | 100 | 550 |
| Walch / principal | 23.303 | 347 | 1.489 |
| Walch / todos | 25.250 | 367 | 1.599 |

São contagens de épocas, não de células da matriz de features. Mudança de
vizinhança e diferença numérica foram contadas separadamente e coincidiram nestes
dados. Destino Newcastle/Walch é comum aos três braços de treino. Nenhuma dessas
contagens permite inferir o tamanho do efeito nas métricas, porque o treino muda.

## Análise definida antes dos resultados

Comparar todas as 69 células (36 externas, 24 de punhos, 9 de otimizações).
Informar κ/especificidade/acurácia, médias antes/depois, diferenças pareadas,
desvio, IC95 bootstrap com 2.000 reamostragens/seed 20260910, maior aumento/queda,
máximo absoluto por participante/célula e n válido. F1 e confusões são complementares.
Um verificador sem importar src/avaliar recalculará cinco métricas a partir das
predições locais. Dados/predições permanecem ignorados, sem junctions.

P1–P3 da DREAMT permanecem registradas. Se a correção mudar a direção de algum
efeito nas coortes anteriores, registrar adendo datado e commitado antes da
DREAMT. Nada nesta etapa autoriza ou executa avaliação DREAMT.
