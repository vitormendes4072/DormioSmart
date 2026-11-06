# ML-13 — adendo após a correção ML-17

**05/11/2026, após as rodadas ML-17 e antes de qualquer avaliação DREAMT.**

As previsões **P1–P3 permanecem integralmente como registradas** em
[PLANO-ML-13-COORTE-DREAMT.md](PLANO-ML-13-COORTE-DREAMT.md). Esse arquivo não foi
reescrito. Não se escolheram novos modelos, braços, janelas, limiares ou HMM
com os resultados da ML-17; nenhuma feature/métrica da DREAMT foi calculada.

## Evidência corrigida que fundamenta a decisão

Com o código corrigido, a janela ±11 sem HMM continua aumentando κ e
especificidade sobre ±2 no pulso de Newcastle e Walch principal, com IC95
pareados inteiramente acima de zero. O HMM com ±2 continua reduzindo
especificidade nas duas, com IC95 inteiramente abaixo de zero. A variante Walch
com baixa taxa e os três braços LOSO também preservam as direções pertinentes.

Isso mantém a fundamentação anterior de P1–P3, sem confirmar previsões na terceira
coorte. O resultado da DREAMT continua desconhecido. Os valores/ICs completos
estão no [relatório ML-17](RELATORIO-ML-17-CONTEXTO.md) e em
[efeitos.json](../ml/experimentos/saida/ml17/efeitos.json).

## O que mudou de sinal e não será herdado como resultado reproduzido

A tabela usa o efeito da configuração sobre a base ±2. São **sinais da média**;
em todos os quatro casos os ICs incluem zero antes e depois. Portanto não se
trata de inversão de um efeito direcional confirmado.

| Configuração / métrica | Código antigo: efeito médio [IC95] | Corrigido: efeito médio [IC95] | Leitura |
|---|---:|---:|---|
| `walch_principal/pulso/item9b_ctx11_hmm` / especificidade | +0,005491 [-0,029616; +0,037051] | -0,002531 [-0,037246; +0,028013] | Inconclusivo nas duas versões |
| `walch_todos/cabeca/item9_ctx11` / acuracia | -0,002142 [-0,013572; +0,009180] | +0,000824 [-0,009221; +0,011038] | Inconclusivo nas duas versões |
| `walch_todos/pulso/item9_ctx11` / acuracia | -0,006677 [-0,018465; +0,004588] | +0,000605 [-0,010956; +0,011752] | Inconclusivo nas duas versões |
| `walch_todos/pulso/item9b_ctx11_hmm` / especificidade | +0,005773 [-0,027396; +0,035498] | -0,001731 [-0,033578; +0,027447] | Inconclusivo nas duas versões |

A combinação ±11+HMM e a acurácia dessas análises secundárias não substituem os
critérios de P1–P3. Em particular, o pequeno ganho médio de especificidade da
combinação no pulso da Walch deixou de ter sinal positivo; ele já era
inconclusivo. Não será apresentado como ganho estabelecido que a correção
preservou. Não houve mudança de sinal das médias nos contrastes LOSO ou de punhos.

## Alcance do controle

A comparação refez as duas versões sobre o **mesmo X reconstruído**, com hashes
X/y/IDs iguais. Os caches antigos Newcastle não reproduziram bit a bit dois
ângulos (máximo 2,842170943040401e-14 graus), cuja causa não foi determinada.
Esse desvio não foi misturado ao contraste entre códigos. Os hiperparâmetros,
a seleção de participantes e as regras de avaliação permaneceram fixos.

Este adendo registra a revisão das evidências anteriores, sem apagar o registro
original. A avaliação da DREAMT permanece posterior à integração/revisão da
ML-17 e ao carregador com protocolo temporal explícito. Nenhum texto do TCC
ou Google Docs foi editado.
