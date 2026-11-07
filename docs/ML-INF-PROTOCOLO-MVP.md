# ML-INF — protocolo do modelo de cabeça

**07/11/2026.** Protocolo aprovado pelo autor e registrado antes do treino.

## Entrada e escolha do braço

O treino usa os 92 participantes da interseção Wearanize+ OA da ML-17,
braço `cabeca`, `qualidade="original"`. O pipeline antialias do projeto
converte o Zmax de 256 Hz para a grade comum de 32 Hz em g. A variante
`cabeca_e4` usaria a mesma grade e acrescentaria a quantização de 8 bits
(15,625 mg por nível) e a saturação em ±2 g do Empatica. A C2 usa um
MPU6050 de 16 bits em ±8 g (4.096 LSB/g nominais) e aplica antialias antes
de reamostrar de 50 para 32 Hz. A escolha segue a cadeia de aquisição.
A resolução efetiva e o acoplamento da C2 no travesseiro são questões de bancada.

Usar as seis primeiras colunas de `features_de_epoca` na grade de 960
amostras por época: enmo_media, enmo_desvio, enmo_max, mag_din_media, zcr,
p_frac. Os dourados da C2 verificam a referência comum de features e o
transporte do vetor. O simulador gera sua grade diretamente a 32 Hz e
exercita o payload até a pontuação, separado do teste da FIFO e do filtro.

## Modelo e avaliação

Regressão logística balanceada, L2 com C=1, lbfgs, max_iter=2000 e seed
20260910. Padronização StandardScaler com média e escala aprendidas
somente no treino. Classe sono quando p(sono) > 0,5. Uma thread nativa.
O MVP usa as seis features de uma época. A primeira variante posterior
será ±11, motivada pelo ganho da DREAMT, com avaliação própria no braço
cabeça. A janela cabe na inferência em lote da noite completa. Ângulos
e HMM ficam para variantes posteriores.

- LOSO no braço cabeça. Ajustar padronização e regressão de novo em
  cada dobra, usando somente os participantes de treino.
- Ajustar o modelo publicável com os 92 participantes. Avaliar os mesmos
  coeficientes e escalas em Newcastle esquerdo, Walch principal e DREAMT
  v2.2.0 com o protocolo temporal da ML-13. Os conjuntos externos ficam
  fora da seleção de parâmetros e de limiar.
- Comparar com sempre sono em cada coorte. Reportar médias macro, desvios,
  n válido, IC95 percentil com 2.000 reamostragens de participantes,
  contrastes pareados, extremos individuais sem identificadores e
  confusões agregadas.

As três coortes externas são de punho. Elas medem generalização para
outras pessoas e coortes nesse domínio, sem isolar o efeito da posição.
O Wearanize mede um sensor preso à cabeça. Na C2 o movimento chega ao
sensor através da espuma do travesseiro, com atenuação e atraso esperados,
cuja magnitude precisa de medição física.

## Artefatos

Modelo JSON com os parâmetros do treino, ordem e escala, limiar e
procedência, incluindo atribuição CC BY 4.0 do Wearanize+ OA. O vetor
dourado fixa épocas geradas pelo simulador e casos próximos ao limiar.
A referência numérica é o predict_proba do scikit-learn. O teste de
integração no backend será na PR consumidora, com tolerância de 1e-12
e classe exata. Os dados e resultados individuais ficam locais.
