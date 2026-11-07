# ML-INF — modelo MVP de cabeça

A regressão logística balanceada usa seis características por época e
limiar 0,5. O braço cabeça original foi escolhido pela cadeia da C2,
antes dos resultados. O [protocolo](ML-INF-PROTOCOLO-MVP.md) fixa
a amostragem, a variante, os parâmetros e as coortes.

| Avaliação | Participantes | Épocas | κ médio [IC95] | Especificidade média [IC95] | κ / especificidade sempre sono |
|---|---:|---:|---:|---:|---:|
| Wearanize cabeça (LOSO) | 92 | 87.795 | 0,3640 [0,3332 a 0,3970] | 0,5405 [0,5032 a 0,5787] | 0,0000 / 0,0000 |
| Newcastle esquerdo | 27 | 30.440 | -0,0002 [-0,0006 a 0,0002] | 0,9993 [0,9988 a 0,9998] | 0,0000 / 0,0000 |
| Walch principal | 29 | 23.303 | 0,3652 [0,3179 a 0,4115] | 0,4381 [0,3884 a 0,4886] | 0,0000 / 0,0000 |
| DREAMT | 97 | 77.738 | 0,0337 [0,0220 a 0,0478] | 0,9424 [0,9276 a 0,9538] | 0,0000 / 0,0000 |

A transferência foi irregular. Na Newcastle, o IC de κ inclui zero.
O modelo detectou 10 de 21.270 épocas de sono (sensibilidade por época
de 0,047%). Na DREAMT, detectou 7.351 de 58.129 (12,65%). A acurácia
macro foi 0,297 na Newcastle e 0,336 na DREAMT, diante de 0,703 e
0,745 do trivial sempre sono. A especificidade alta nessas duas
coortes veio junto com muitas classificações de vigília.

No LOSO, cada participante foi avaliado com padronização e regressão
ajustadas exclusivamente nos outros participantes. O modelo publicado
foi ajustado com os 92 e aplicado às três coortes externas com a escala
e o limiar do treino. Os hiperparâmetros foram fixados no protocolo.

Os contrastes pareados abaixo usam o mesmo participante para modelo e
trivial. O maior desvio em módulo é medido por participante. Cada IC
usa 2.000 reamostragens de participantes.

| Avaliação | Δκ médio [IC95] | Maior módulo de Δκ | Δespecificidade média [IC95] | Maior módulo de Δespec. |
|---|---|---:|---|---:|
| Wearanize cabeça (LOSO) | 0,3640 [0,3332 a 0,3970] | 0,6825 | 0,5405 [0,5016 a 0,5771] | 0,9412 |
| Newcastle esquerdo | -0,0002 [-0,0006 a 0,0002] | 0,0038 | 0,9993 [0,9988 a 0,9998] | 1,0000 |
| Walch principal | 0,3652 [0,3179 a 0,4115] | 0,6592 | 0,4381 [0,3859 a 0,4886] | 0,7143 |
| DREAMT | 0,0337 [0,0220 a 0,0478] | 0,4386 | 0,9424 [0,9284 a 0,9543] | 1,0000 |

O [JSON de avaliação](../ml/experimentos/saida/ml-inf/agregados.json)
inclui desvios, n válido, mínimos/máximos individuais sem identificadores,
acurácia, F1 e as matrizes de confusão somadas. A macro média dá o mesmo
peso a cada participante. As matrizes dão o mesmo peso a cada época.
Uma conferência a partir das predições locais recompôs as oito
matrizes e as médias com scikit-learn. A maior diferença absoluta
nas médias foi 1,11e-16, na Walch.

## Alcance

Newcastle, Walch e DREAMT são coortes de punho. As três avaliam
generalização para outras pessoas e coortes no domínio de punho.
A comparação não isola posição de sensor, população e dispositivo.
O Wearanize mede com o sensor preso à cabeça. Na C2 o movimento
chega ao sensor pela espuma do travesseiro, com atenuação e atraso
esperados. A magnitude desses efeitos e o desempenho no travesseiro
precisam de validação física.

A DREAMT usou as 97 gravações avaliáveis pela regra de fase PSG da ML-13.
Os ICs refletem a variação da coorte e o protocolo fixado. A primeira
variante futura usa contexto ±11, com avaliação própria. O ganho na
DREAMT motiva essa variante, que cabe em lote com a noite completa.
O MVP usa uma época por vez.

## Paridade e integração

As seis colunas do treino vieram de features_de_epoca sobre a grade
comum de 32 Hz em g, com 960 amostras por época. O cache de cabeça
preserva as entradas da ML-17 e passou pela verificação do inventário,
dos bytes e de X/y/IDs. Os dourados existentes da C2 cobrem o cálculo
das features e suas tolerâncias com o firmware. A resolução e o
transporte quantizado do dispositivo têm tolerâncias próprias.

O [modelo publicado](../ml/modelos/ml-inf-cabeca-v1.json) inclui parâmetros,
ordem, limiar, atribuição Wearanize+ OA e procedência. O
[vetor dourado](../ml/testes/fixtures/ml-inf-cabeca-v1-dourado.json)
contém quatro payloads do SIM-02 (seed 7) e duas entradas sintéticas
cercando o limiar. As probabilidades vieram do predict_proba. O teste
regera o campo f do simulador e confere as probabilidades usando
aritmética da biblioteca padrão, com tolerância absoluta de 1e-12 e
classe exata. A regressão também exige que o StandardScaler receba
apenas as linhas de treino de cada dobra.

Na PR consumidora, o backend deve validar a quantidade e a ordem
canônica das seis features do modelo. O teste de integração entrega
os campos f dos payloads dourados ao caminho real da inferência.
A pontuação usa somente a biblioteca padrão. A regra de classe é
p(sono) > 0,5, com vigília em caso de igualdade.

## Reprodução

Executado em Windows local, Python 3.11.9, bibliotecas pinadas e uma
thread nativa medida no processo. Os caches congelados de Wearanize,
Newcastle e Walch foram verificados contra o manifesto ML-17. Os 103
SHA-256 da DREAMT foram reconferidos antes da rodada. O protocolo e
o código de treino estavam commitados antes da avaliação. O commit,
hash de configuração, hash de X/y/IDs de treino e versões de execução
constam do JSON de avaliação.

A partir de ml/, com os brutos e evidências nas pastas locais:

~~~text
python -m ferramentas.baixar_dreamt --pasta PASTA_DREAMT
python -m experimentos.ml_inf --evidencia-ml17 EVIDENCIA_ML17 --dados-dreamt PASTA_DREAMT --saida NOVA_PASTA_LOCAL
~~~

A execução completa está em dados-locais/ml-inf-cabeca-2026-11-07,
fora da worktree. Predições, rótulos, índices individuais e caches
ficam locais. Os brutos DREAMT permanecem em dados-locais/dreamt-2.2.0
e a evidência congelada da ML-17 em dados-locais/ml17-evidencias-2026-11-05.
Nenhuma junction foi usada.
