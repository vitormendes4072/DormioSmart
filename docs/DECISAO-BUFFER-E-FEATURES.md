# Decisão: como o buffer do firmware carrega as 8 features

**Data:** 2026-09-29 · **Itens:** `DATA-07a`, `DATA-07b`, `FW-07` · **Estado:** decidido, não implementado

> **Reprodutibilidade.** Todo número deste documento sai de dois programas:
>
> ```bash
> python3 scripts/estudo_buffer.py              # layout, flash, desgaste, energia
> python3 scripts/estudo_buffer.py --conferir   # só as asserções; sai != 0 se divergir
> python3 ml/experimentos/quantizacao_features.py   # o custo em kappa, MEDIDO
> ```
>
> Mesma convenção do `CALCULOS-TCC.md`: cada constante traz fonte, e onde o
> valor não pôde ser conferido na folha de dados ele entra como **parâmetro em
> faixa**, nunca como número citado.

---

## O problema que originou o estudo

O `DATA-07` exige que o dispositivo envie o **vetor de 8 features por época**
(`ml/src/features.py`), não só magnitude e rótulo. A objeção imediata: guardar
8 `float32` a mais por época dobra o registro de 32 B para 64 B, e portanto
**corta pela metade** a autonomia offline que o `HW-05` dimensionou.

O dilema parecia ser *"features completas ou autonomia"*. **Ele não existe.**
Três saídas independentes o dissolvem, e qualquer uma sozinha já bastaria.

---

## Achado que precede as três: a restrição de 4 KiB não se aplica

O orçamento de 4 KiB / 128 épocas vem da **RTC slow memory**, e ela só é
necessária porque o `FW-07` planeja um ciclo *acordar → medir → agregar →
dormir*: o heap não sobrevive ao Deep Sleep, a RTC sobrevive.

Só que o `CALC-01`, seção Z.4.3, já havia estabelecido — antes deste estudo e
sem relação com ele — que **o vetor de 8 features é incompatível com Deep
Sleep**:

> *"A arquitetura de despertar por movimento exige que o acelerômetro permaneça
> em modo de baixo consumo, e esse modo não atinge a taxa que a extração de
> características requer. As duas arquiteturas não se combinam."*

As features exigem a época **inteira** amostrada a ≥ 42 Hz, e as épocas se
sucedem sem intervalo. Não há janela ociosa em que dormir. Logo, na arquitetura
que carrega features, **o processador fica ativo a noite toda e o heap está
disponível** — 520 KiB de SRAM interna, dos quais ~300 KiB livres.

O teto que gerava o dilema pertence a uma arquitetura que o próprio requisito
elimina. Isso não é licença para desperdiçar bytes, mas é o enquadramento
correto: comparar contra 32 KiB de heap, não contra 4 KiB de RTC.

---

## Saída 1 — flash em vez de RAM

### O que a placa tem, conferido

| Fato | Valor | Fonte |
|---|---|---|
| Flash SPI do módulo | **4 MiB** | ESP32-WROOM-32 Datasheet v2.4, §1 |
| PSRAM | **não existe** | idem — PSRAM é do WROVER, não do WROOM |
| SRAM interna | 520 KiB | idem |
| Partição de dados | **1,5 MiB** | `arduino-esp32`, `tools/partitions/default.csv` |

> ⚠️ **Correção ao enunciado do estudo.** Os 4 MiB são do chip, mas **não estão
> disponíveis para dados**. O esquema padrão de 4 MB reserva ~1,2 MB para a
> aplicação em duas fatias de OTA e deixa **1,5 MB** de SPIFFS. Uma tabela sob
> medida sem OTA — que este projeto pode adotar, já que não faz OTA — chega a
> ~2,8 MB. A diferença entre 4 MB e 1,5 MB é de quase 3×, e é a diferença entre
> um número de folheto e um número de projeto.
>
> ⚠️ **E o repositório não versiona `partitions.csv` nem `platformio.ini`.**
> Portanto o esquema padrão é o que vale hoje, e trocá-lo é uma decisão a tomar
> — não um dado a assumir.

### Quanto cabe

Com o registro de 40 B da Saída 3, em resolução plena de 30 s:

| Orçamento | Épocas | Cobertura |
|---|---:|---:|
| 4 KiB RTC | 102 | 0,85 h |
| 32 KiB heap | 819 | 6,8 h |
| **1,5 MiB flash (padrão)** | **39 321** | **327 h = 13,7 dias** |
| 2,8 MiB flash (sob medida) | 73 395 | 612 h = 25,5 dias |

Duas semanas sem rede, em resolução plena, **sem degradar uma única vez**.

### Desgaste

A intuição do enunciado está certa, e com folga larga. A 2 registros/min, o
layout de 40 B escreve **112 KiB/dia**. Contra um orçamento de 1,5 MiB × 100 000
ciclos = 146 GiB, são **3 741 anos** com nivelamento. Mesmo adotando a endurance
pessimista de 10 000 ciclos: 374 anos.

O único cenário apertado é o cruzamento de **três** pessimismos simultâneos —
10 000 ciclos **e** zero nivelamento **e** operação 24 h/dia — que dá ~1,0 ano.
Desfazer qualquer um dos três já leva a mais de uma década:

| Cenário | 100k ciclos | 10k ciclos |
|---|---:|---:|
| Com nivelamento (LittleFS/NVS fazem por padrão) | 3 741 anos | 374 anos |
| Sem nivelamento, 24 h/dia | 9,7 anos | **1,0 ano** |
| Sem nivelamento, 8 h/noite (uso real) | 29,1 anos | 2,9 anos |

Como LittleFS e NVS fazem nivelamento por padrão, o cenário sem nivelamento não
é o que se vai construir. **O desgaste não é um risco.**

### Energia

Aqui o enunciado também estava certo em desconfiar — e a resposta é que o custo
existe e é irrelevante, por uma razão estrutural.

Como o vetor de features **obriga** a arquitetura de amostragem contínua (achado
acima), a referência de consumo é a do `CALC-01` Z.4.4: **23,9 mA médios**. O
processador já está ligado a noite inteira. Contra isso:

| Corrente de escrita (parâmetro declarado) | Custo médio | % dos 23,9 mA |
|---:|---:|---:|
| 4 mA | 0,62 µA | 0,0026 % |
| 10 mA | 1,54 µA | 0,0064 % |
| 20 mA | 3,08 µA | 0,0129 % |

> A corrente durante programação/apagamento **não foi confirmada** na folha do
> W25Q32JV que foi possível consultar (ela dá 4 mA de corrente ativa e 1 µA em
> repouso). Entra como parâmetro em faixa com sensibilidade, exatamente como a
> corrente de rádio no `CALC-01`. Os tempos (0,7 ms por página de 256 B, 400 ms
> por setor de 4 KiB) são da folha.

Mesmo no extremo superior, **0,013 %**. Para comparação, **uma** transmissão por
época (100 mA por 1 s) custa 3,33 mA médios — mais de **mil vezes** a
persistência. A conclusão do Z.4.4 (o rádio domina; agregar entregas é o que
importa) não muda em nada por gravar em flash.

### Consequência de projeto

O buffer em RAM vira **cache de escrita**, e o registro durável passa a ser o
arquivo em flash. Isso é estritamente melhor que a RTC em dois aspectos além do
tamanho: a flash é **não-volátil**, então sobrevive a queda de energia e a
reset, coisas que a RTC slow memory não garante. Uma noite interrompida por
tomada solta deixa de ser uma noite perdida.

---

## Saída 2 — a redundância existe, mas não é a que parecia

### `d_angulo` **não** é a diferença de `inclinacao_rel`

A hipótese do enunciado é intuitiva e está **errada** — e o erro é de geometria,
não de implementação. As duas features são ângulos sobre uma **esfera**:

```
inclinacao_rel[t] = arccos( ĝ_t · ĝ_ref )
d_angulo[t]       = arccos( ĝ_t · ĝ_{t-1} )
```

O que vale entre elas é a **desigualdade triangular esférica**, não uma
igualdade:

```
| θ_t − θ_{t−1} |  ≤  d_angulo[t]  ≤  θ_t + θ_{t−1}
```

A igualdade só valeria se `ĝ_ref`, `ĝ_{t−1}` e `ĝ_t` estivessem sempre no mesmo
grande círculo, e não estão.

**Medido nas 87 795 épocas do Wearanize+ (pulso):** a aproximação
`d_angulo ≈ |Δinclinacao_rel|` tem correlação 0,904 e erro mediano de **0,010
grau** — mas erro máximo de **149,4 graus**. E o erro não é aleatório: cresce
monotonicamente com o tamanho da virada.

| Faixa de `d_angulo` | n | Erro médio da aproximação |
|---|---:|---:|
| [0, 1) graus | 73 386 | 0,03 grau |
| [1, 5) graus | 5 070 | 0,80 grau |
| [5, 20) graus | 4 719 | 3,70 graus |
| [20, 60) graus | 3 276 | 12,51 graus |
| [60, 180) graus | 1 252 | **31,10 graus** |

A aproximação é excelente onde não há virada e falha exatamente nas **5,16 %**
de épocas que *são* viradas — que é tudo o que `d_angulo` existe para capturar.
Ela não serve: erraria pouco em média e muito onde importa, que é o pior modo de
falha possível para uma feature.

### O que serve: guardar `ĝ`, não os dois ângulos

Ambas as features são funções do **vetor gravidade unitário da época**. Guardando
`ĝ` e derivando os ângulos na drenagem, a reconstrução é **exata** — erro máximo
medido de `0,000e+00` grau nas duas.

**E isso rende um benefício que vale mais que os bytes.** `ĝ_ref` é a mediana
geométrica (Weiszfeld) da **gravação inteira** — o firmware não tem como
calculá-la em streaming, e a proposta que existia no `features.py` era um
"acumulador direcional com aquecimento". Isso é um **estimador diferente**, não
uma aproximação com tolerância: divergiria do Python em silêncio, e o vetor
dourado atual é cego para isso (seus 5 casos são de época única, então as duas
features inter-época valem 0 em todos).

Guardando `ĝ`, a `ĝ_ref` é calculada na drenagem com **o mesmo Weiszfeld**. A
divergência que o `DATA-07` existe para prevenir deixa de ser possível nas duas
features onde ela estava garantida. **Este é o ganho principal do estudo**, e não
é sobre memória.

### Nenhuma outra feature é derivável

As seis intra-época medem coisas independentes do mesmo sinal: `enmo_media`,
`enmo_desvio` e `enmo_max` são três momentos distintos da mesma distribuição e
nenhum determina os outros; `mag_din_media` opera sobre o sinal **sem gravidade**,
que o ENMO não isola; `zcr` é frequência, não amplitude; `p_frac` é uma contagem
acima de limiar, que nenhum momento recupera. Todas ficam.

---

## Saída 3 — quantização, com o custo medido e não argumentado

### O esquema

| Feature | Representação | Fundo | Passo | Folga sobre o ruído |
|---|---|---:|---:|---:|
| `enmo_media` | u16 | 1 g | 15,3 µg | 41,9× o piso de 0,64 mg |
| `enmo_desvio` | u16 | 1 g | 15,3 µg | 41,9× |
| `enmo_max` | u16 | 16 g | 244,1 µg | 6,6× o σ por amostra (1,6 mg) |
| `mag_din_media` | u16 | 2 g | 30,5 µg | 21,0× |
| `zcr` | u16 | — | **exato** | contagem inteira, 0..959 |
| `p_frac` | u16 | — | **exato** | contagem inteira, 0..959 |
| `ĝ` (3 componentes) | 3 × i16 | [−1, 1] | 3,05e−5 | ~0,002 grau de resolução angular |

Dois pontos que o enunciado não previa e que mudam o desenho:

- **`zcr` e `p_frac` não precisam ser quantizados.** São frações de uma contagem
  de amostras (0..959 numa época de 30 s a 32 Hz). Guardadas como a **contagem
  inteira**, cabem em `uint16` **sem perda nenhuma** — é a representação exata,
  não uma aproximação.
- **`enmo_max` é o único apertado**, porque o fundo precisa cobrir 16 g (o máximo
  observado nas bases é 6,44 g, e o teto físico em fundo de ±8 g é ~12,9 g).
  Contra o piso de 0,64 mg a folga seria só 2,6× — mas ele é um **máximo**, e o
  ruído relevante para um máximo é o σ por amostra de 1,6 mg, onde a folga é 6,6×.

### O custo, medido

Quantizadas, propagadas pelo pipeline do produto (normalização por sujeito +
contexto ±2 + regressão logística balanceada), comparadas **pareado por dobra**
contra `float64`, em 10 dobras agrupadas por sujeito:

| Base | n | Δκ com u16 | Δκ com u12 | Δκ com u10 | Δκ com u8 |
|---|---:|---:|---:|---:|---:|
| Wearanize+ pulso | 87 795 | **−0,00008** | −0,00024 | −0,00066 | +0,00027 |
| Wearanize+ cabeça | 87 795 | **−0,00003** | −0,00116 | −0,02022 | **−0,03802** |
| Newcastle | 59 825 | **+0,00005** | −0,00037 | −0,00158 | **−0,01068** |

**Como ler esses números.** O teto de concordância entre pontuadores humanos é
κ = 0,612 (`ML-05`) e o maior ganho que o projeto obteve com otimização foi o HMM,
Δκ = +0,123 (`ML-03b` item 8b). O custo do u16 é da ordem de **1e−4** — mais de
mil vezes menor que aquele ganho, e uma ordem de grandeza abaixo do desvio entre
dobras (±0,045 a ±0,082). É ruído numérico.

**Onde quebra.** O u8 já custa Δκ = −0,038 na **cabeça** — que é justamente a
posição do Dormio. Isso é o que justifica ficar em 16 bits em vez de descer mais:
não é margem inventada, é o ponto medido onde a perda aparece.

---

## Recomendação

**Adotar as três, nesta combinação.** Elas não competem: cada uma resolve uma
coisa diferente, e a terceira é a que torna as outras duas baratas.

### O registro: 40 bytes

| Campo | Tipo | Bytes |
|---|---|---:|
| `indice` | u32 | 4 |
| 6 features intra-época | 6 × u16 | 12 |
| `ĝ` (gravidade unitária da época) | 3 × i16 | 6 |
| `pico_total` | u16 | 2 |
| `pico_ax/ay/az` | 3 × i16 | 6 |
| `temp_pico` | i16 | 2 |
| `amostras`, `esperadas` | 2 × u16 | 4 |
| `duracao_s` | u16 | 2 |
| `nivel`, `flags` | 2 × u8 | 2 |
| **total** | | **40** |

Comparado às alternativas:

| Layout | Bytes | 32 KiB heap | 1,5 MiB flash |
|---|---:|---:|---:|
| A. hoje, sem features | 32 | 8,53 h | 409,6 h |
| B. ingênuo, 8 × float32 | 64 | 4,27 h | 204,8 h |
| C. `ĝ` em float | 68 | 4,01 h | 192,8 h |
| **D. proposto** | **40** | **6,83 h** | **327,7 h** |

O layout D carrega **as oito features** e custa **+25 %** sobre o registro atual,
que não carrega nenhuma — contra os +100 % do caminho ingênuo. Note que o layout
C, que seria a leitura "guardar `ĝ`" sem quantizar, é o **pior** dos quatro: é a
quantização que torna a Saída 2 gratuita.

### Ordem de implementação

1. **`ĝ` em vez dos dois ângulos** — é a que resolve a divergência silenciosa, e
   é pré-requisito de qualquer paridade honesta. Vale mesmo se nada mais for
   adotado.
2. **Ponto fixo de 16 bits** — custo medido de 1e−4 em κ, ganho de 40 % no
   registro. Independente do meio de armazenamento.
3. **Flash como registro durável, RAM como cache de escrita** — exige decidir a
   tabela de partições e escolher LittleFS ou NVS. É a maior mudança
   arquitetural das três e a que dá a folga de ordens de magnitude.

A Saída 4 do enunciado (reduzir autonomia em RAM) **não é necessária** e não foi
avaliada em profundidade: com 6,83 h de heap em resolução plena e 13,7 dias em
flash, não há autonomia a cortar.

### O que isto não resolve

Nada aqui implementa as features em C++. O `DATA-07b` continua sendo o item
grande — biquad Butterworth ida-e-volta, acumulação por época, e um alvo de teste
que leia o `vetor_dourado.json`. Este estudo decide **o formato do que será
guardado**, não produz o que guarda.

E duas pendências novas ficam registradas:

- **O vetor dourado precisa de casos multi-época.** Os 5 atuais são de época
  única, então `inclinacao_rel` e `d_angulo` valem 0 em todos e a paridade delas
  não é testada por nada. Com a decisão de guardar `ĝ`, o que o dourado precisa
  fixar passa a ser o próprio `ĝ` por época, além dos ângulos derivados.
- **A tabela de partições precisa ser versionada.** Hoje o esquema é o padrão
  implícito do Arduino; se a flash vira armazenamento de dado de pesquisa, o
  layout dela é parte do projeto e não pode ficar dependendo do que a IDE
  escolhe.
