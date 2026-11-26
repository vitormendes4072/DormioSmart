# Estudo de energia: bateria, autonomia e aquecimento (`HW-02`)

> **Estado:** estudo de 17/11/2026, revisado no mesmo dia (seção 11), sem medição de corrente na
> placa. Os números de consumo da placa são **estimativas em faixa** sustentadas por folha de
> dados e por relatos de bancada de terceiros; o `RD-10` manda medir antes de comprar, e a seção
> 9 diz como. A recomendação da seção 8 é a escolha **condicionada** a essa medida.
>
> Convenção de números (a mesma de `CALCULOS-TCC.md`): *especificação* (folha de dados),
> *cálculo* (conta sobre números declarados), *estimativa* (faixa arbitrada ou relato de
> terceiros) e *medição* (feita neste projeto, com data).

## 1. A pergunta

Hoje o travesseiro funciona ligado ao USB de um computador. O projeto precisa de uma bateria
que: (a) **caiba** no travesseiro sem ser percebida pela cabeça (`RD-14`); (b) **dure** o
bastante para justificar um dispositivo que fica sempre ligado (`RD-09`); (c) **não aqueça**
a face do travesseiro (`RD-11`, `RD-12`) nem ofereça risco térmico dentro da roupa de cama
(`HW-04`, `CALC-05`).

## 2. O que já existia no projeto

- `CALCULOS-TCC.md` §Z.4: o modelo de consumo por estado. Na arquitetura adotada (`ARQ-01`, C2),
  **2,28 mA só dos circuitos integrados** (faixa da varredura: 1,88 a 5,19 mA): transdutor
  0,600 mA, processador em sono leve 0,787 mA, processador acordado 0,212 mA, rádio a cada
  10 min 0,667 mA, gravação na *flash* 0,014 mA. §Z.4.5 conclui que o **consumo fixo da placa
  de desenvolvimento decide a autonomia** e que ele precisa ser medido.
- `REQUISITOS-DISPOSITIVO.md` §2 e §3: `RD-09` (7 dias, proposto), `RD-10` (medir antes de
  comprar), `RD-11` a `RD-13` (potência média e picos), `RD-15` (o LED de energia sempre aceso).
- Backlog: `HW-02` (energia), `HW-04` (encapsulamento e segurança térmica), `HW-10` (medir a
  bateria), `CALC-05` (térmica medida), `HW-11` (o contato da alimentação do sensor).
- **A proposta anterior de alimentação**, feita pelos autores fora do repositório: uma página
  com modelo 3D (`SmartDormio_Alimentacao.html`), com **LiPo 1S → PowerBoost 500C (5,2 V) → VIN
  do ESP32**, numa caixa de 80 × 100 × 20 mm com abertura para a recarga. É avaliada na seção 10.

## 3. O que consome na placa

### 3.1 Os circuitos integrados, com a frequência real do processador

O §Z.4.4c supõe o processador a **80 MHz** quando acordado (20 a 31 mA). O `sketch.ino` não
chama `setCpuFrequencyMhz`, e o core do Arduino para ESP32 usa **240 MHz** por padrão (30 a
68 mA, *especificação*). Mantida a fração da hora acordada do modelo (1,06 %, a que dá os
0,212 mA a 20 mA), a parcela do processador acordado sobe para 0,32 a 0,72 mA (referência
0,48 mA, a 45 mA). O rádio fica na faixa do modelo: 100 mA por 4 s a cada 10 min na
referência, e de 100 mA por 2 s a 240 mA por 8 s nos extremos (*cálculo* sobre *especificação*
e *estimativa*):

| Parcela | Referência | Faixa |
|---|---:|---:|
| Transdutor (só o acelerômetro; o giroscópio está em espera no firmware) | 0,600 mA | — |
| Processador em sono leve | 0,787 mA | — |
| Processador acordado, a 240 MHz | 0,48 mA | 0,32 a 0,72 mA |
| Rádio, um envio a cada 10 min | 0,667 mA | 0,33 a 3,2 mA |
| Gravação na *flash* | 0,014 mA | — |
| **Circuitos integrados** | **2,55 mA** | **2,05 a 5,32 mA** |

A correção é de +0,27 mA na referência (+12 %). Está dentro da faixa que o §Z.4 já declarava,
mas desloca a referência para cima. Ela também aponta uma economia de firmware: rodar a 80 MHz
(o Wi-Fi funciona nessa frequência) devolve 0,16 a 0,48 mA (`FW-20`).

### 3.2 O consumo fixo da placa

A placa usada é a **ESP32 DevKit V1** com o módulo **GY-521** (MPU6050). Fontes de consumo fixo,
presentes em todos os estados, inclusive no sono leve (*estimativa*, salvo indicação):

| Fonte | Referência | Faixa | Natureza |
|---|---:|---:|---|
| Regulador AMS1117 da DevKit, alimentado "por trás" (bateria no pino 3V3) | 4 mA | 3 a 5 mA | relato de bancada: caiu a 12 µA ao isolar o regulador; o AMS1117 em operação normal gasta ~5 mA (*especificação*) |
| LED de energia da DevKit | 1,3 mA | 1,0 a 1,5 mA | resistor de ~1 kΩ em 3,3 V |
| Ponte USB-serial CP2102, sem USB | 0,15 mA | 0,1 a 0,2 mA | *especificação* (suspensão) |
| **LED de energia do GY-521** | 1,35 mA | 1,2 a 1,5 mA | relato de bancada: 1,39 mA → 44 µA ao remover o LED |
| Regulador do GY-521 | 0,075 mA | 0,05 a 0,1 mA | relato de bancada |

### 3.3 Os três cenários

Somando os circuitos integrados (3.1) ao fixo da placa (3.2), referência com referência e
extremo com extremo (*cálculo* sobre *estimativa*):

| Cenário | O que muda na placa | Fixo da placa | **Total (referência)** | Faixa |
|---|---|---:|---:|---:|
| **S1** | nada: bateria no pino 3V3 | 6,9 mA | **9,4 mA** | 7,4 a 13,6 mA |
| **S1'** | tirar os **dois LEDs** (sem tocar no regulador) | 4,2 mA | **6,8 mA** | 5,2 a 10,6 mA |
| **S2** | tirar os dois LEDs e **isolar o AMS1117** | 0,24 mA | **2,8 mA** | 2,2 a 5,6 mA |

**O pico do rádio** é outra grandeza: transmissão 802.11b a 240 mA e recepção a 95–100 mA
(*especificação* da série ESP32), por alguns segundos a cada 10 min; a Espressif recomenda que
a fonte entregue **500 mA ou mais**. É o pico que dimensiona os fios, o fusível e o capacitor
de reserva (seção 8.1), não a autonomia.

## 4. Quanto tempo precisa durar

O dispositivo fica **sempre ligado** (não tem botão de liga e desliga), então a autonomia conta
em horas corridas, não em noites.

| Patamar | Horas | Justificativa |
|---|---:|---|
| Inaceitável | < 24 h | exigiria recarga diária: o usuário acaba dormindo sem dado |
| **Mínimo proposto** | **72 h** | três noites seguidas sem recarga (um fim de semana); é o que permite uma validação de várias noites (`VAL-01`) sem mexer no aparelho |
| **Alvo (`RD-09`)** | **168 h** | uma recarga por semana, como um relógio inteligente comum |

O mínimo de 72 h é **proposta deste estudo** e precisa ser confirmado pelos autores e pelo
orientador, como o `RD-09`.

## 5. Química e formato da célula

| Célula | Tensão | Capacidade típica | Tamanho, massa | Precisa de regulador? | Segurança térmica e mecânica |
|---|---|---:|---|---|---|
| **LiFePO4 (LFP) 14500** | 3,2 V nominal, 3,6 V cheia, 2,5 V vazia | 600 mAh | 14 × 50 mm, ~17 g | **não** (ver 5.1) | química mais estável; lata de aço |
| **LiFePO4 18650** | idem | 1 500 mAh | 18 × 65 mm, ~40 g | **não** | idem |
| **LiFePO4 26650** | idem | 3 300 mAh | 26 × 66 mm, ~88 g | **não** | idem |
| Li-ion 18650 (NMC/LCO) protegida | 3,7 V nominal, 4,2 V cheia | 2 600 mAh | 18 × 67–69 mm, ~45 g | **sim** (LDO) | *runaway* mais violento; lata de aço |
| LiPo em bolsa 103450 | 3,7 V nominal, 4,2 V cheia | 2 000 mAh | 10 × 34 × 50 mm, ~38 g | **sim** (LDO) | invólucro mole: o pior caso sob a pressão da cabeça |
| 3 × AA NiMH | 3,6 a 4,2 V | 2 000 mAh | 3 pilhas AA | **sim** (LDO) | segura, mas ocupa três vezes o volume |

**Comparação térmica (*medição* de terceiros, calorimetria ARC, células 18650 a 100 % de carga,
Frontiers in Chemistry, 2024):**

| Catodo | Início do autoaquecimento | Disparo do *runaway* (> 10 °C/min) | Temperatura máxima |
|---|---:|---:|---:|
| LCO (o típico das LiPo e de parte das 18650) | 111,8 °C | 180,2 °C | **545,1 °C** |
| **LFP** | 62,5 °C | **não detectado** | **239,3 °C** |
| NCM811 | 62,5 °C | 147,4 °C | 462,5 °C |
| NCA | 101,7 °C | 165,4 °C | 491,8 °C |

O LFP começa a se aquecer cedo, mas **não dispara o *runaway* no ensaio** e chega a menos da
metade da temperatura máxima do LCO. Para uma célula embaixo da cabeça de alguém dormindo, é a
diferença que importa.

**Mecânica.** O circuito de proteção (DW01 + FS8205 e equivalentes) corta sobrecarga, descarga
profunda e curto, mas **não protege contra esmagamento ou perfuração**. Por isso o invólucro conta
tanto quanto a química: a lata de aço cilíndrica aguenta a pressão de uma cabeça; a bolsa de LiPo
não foi feita para isso.

### 5.1 O LFP alimenta o ESP32 sem regulador

A faixa do ESP32 é de **3,0 a 3,6 V no módulo** (o circuito integrado opera de 2,3 a 3,6 V; o
máximo absoluto é 3,6 V; *especificação* Espressif). O LFP passa a maior parte da descarga num
patamar de **3,2 a 3,3 V**, dentro dessa faixa, e desce a 3,0 V perto do fim. Ligado direto no
pino 3V3, ele elimina o regulador, sua corrente própria e o calor que ele dissiparia.

Três cuidados (*estimativa*, relatos de terceiros e folhas de dados das células):

- **Logo depois da carga, a célula marca 3,60 a 3,65 V**, no limite do ESP32. Fora do
  carregador, ela cai a ~3,4 V em 30 min a 2 h e a 3,30–3,35 V em algumas horas. Regra: **a
  célula descansa pelo menos 2 h depois da carga** antes de voltar ao travesseiro.
- **No fim da descarga**, abaixo de ~3,1 V em repouso, o pico do rádio pode puxar o 3V3 para
  menos de 3,0 V: o Wi-Fi fica fora da faixa recomendada antes de a célula estar vazia. É uma das
  razões do fator de 0,90 na capacidade útil (seção 6) e do capacitor de reserva (8.1).
- **O GY-521 tolera:** o MPU6050 vai a 3,46 V, mas o módulo tem regulador próprio, que recebe
  a tensão da célula. Com isso, a dúvida antiga do `HW-02` sobre ligar o VCC do módulo em 5 V
  deixa de existir: com a célula não há 5 V, e o módulo fica no 3V3, como hoje.

A Li-ion e a LiPo, de 4,2 V cheias, precisam de um LDO de baixo consumo próprio que aguente o
pico do rádio (por exemplo, RT9080: 600 mA, 0,31 V de queda a 600 mA; ME6211: 500 mA,
~40 µA próprios). O LDO dissiparia ~8 mW em média e ~0,27 W nos picos (*cálculo*: 0,9 V × I).

## 6. Autonomia por célula e cenário

Capacidade útil = nominal × 0,90 (LFP até 3,0 V) ou × 0,85 (Li-ion e LiPo até o limite do LDO) ou
× 0,80 (NiMH), × 0,90 de envelhecimento e temperatura (*cálculo* sobre *estimativa*):

| Célula | Útil | **S1** (9,4 mA) | **S1'** (6,8 mA) | **S2** (2,8 mA) |
|---|---:|---:|---:|---:|
| LFP 14500 | 486 mAh | 52 h (2,1 d) | 72 h (3,0 d) | 175 h (7,3 d) |
| **LFP 18650** | **1 215 mAh** | **129 h (5,4 d)** | **179 h (7,5 d)** | **436 h (18 d)** |
| LFP 26650 | 2 673 mAh | 284 h (11,8 d) | 395 h (16,4 d) | 960 h (40 d) |
| Li-ion 18650 + LDO | 1 989 mAh | 211 h (8,8 d) | 294 h (12,2 d) | 714 h (30 d) |
| LiPo 103450 + LDO | 1 530 mAh | 162 h (6,8 d) | 226 h (9,4 d) | 549 h (23 d) |
| 3 × AA NiMH + LDO | 1 440 mAh | 153 h (6,4 d) | 213 h (8,9 d) | 517 h (22 d) |

Para a LFP 18650, nas faixas de cada cenário: **89 a 164 h** em S1, **114 a 234 h** em S1' e
**216 a 549 h** em S2. O mínimo de 72 h é cumprido em toda a faixa de S1, sem mexer na placa; o
alvo de 168 h, na referência de S1'.

## 7. Aquecimento

| Fonte de calor | Potência | Natureza |
|---|---:|---|
| Placa e sensor, média (S2 / S1 / pior S1) | 9 / 31 / 45 mW | *cálculo*, P = 3,3 V × I |
| Rádio, pico | 0,33 a 0,79 W, por segundos a cada 10 min | `RD-13` |
| Resistência interna da LFP (~50 mΩ) no pico de 300 mA | ~4,5 mW | *cálculo*, I²R |
| Regulador (só nas opções com LDO) | ~8 mW média, ~0,27 W no pico | *cálculo* |

Em uso normal, nada disso esquenta o travesseiro de forma perceptível: a média é de dezenas de
miliwatts, e a célula trabalha a menos de 0,01 C (9,4 mA numa célula de 1 500 mAh). **O risco
térmico real é a falha** (curto, inversão, sobrecarga, esmagamento), e ele se controla com a
química (LFP), a lata de aço, a proteção, o fusível e **carregar fora do travesseiro**. A
afirmação "não esquenta" só vale depois do ensaio do `CALC-05` contra o `RD-12`.

## 8. Decisão

Matriz de 1 (pior) a 5 (melhor), com os critérios do autor (*juízo deste estudo*):

| Opção | Tamanho | Autonomia | Aquecimento e segurança | Simplicidade | Custo |
|---|:-:|:-:|:-:|:-:|:-:|
| **LFP 18650 direto no 3V3** | 4 | 4 | **5** | **5** | 4 |
| LFP 14500 direto no 3V3 | **5** | 2 | 5 | 5 | 5 |
| LFP 26650 direto no 3V3 | 2 | **5** | 5 | 5 | 3 |
| Li-ion 18650 + LDO | 4 | 5 | 3 | 3 | 4 |
| LiPo em bolsa + LDO | 5 | 4 | **1** | 3 | 4 |
| 3 × AA NiMH + LDO | 1 | 4 | 5 | 3 | 4 |
| LiPo + PowerBoost 500C no VIN (proposta anterior, seção 10) | 3 | 1 | 1 | 4 | 3 |

### Recomendação

**Uma célula LiFePO4 18650 de ~1 500 mAh, removível num suporte, ligada direto no pino 3V3 da
DevKit V1, carregada fora do travesseiro num carregador de LiFePO4.**

- **Tamanho:** 18 × 65 mm, ~40 g, o volume de um marcador de texto, rígido. Cabe ao lado da placa.
- **Autonomia:** 5,4 dias sem mexer na placa (S1), 7,5 dias tirando os dois LEDs (S1'), cerca de
  18 dias isolando o regulador (S2). O mínimo de 72 h é cumprido já em S1, mesmo no pior caso
  da faixa (89 h).
- **Aquecimento:** sem regulador, sem LDO, a química mais estável e a lata de aço.
- **Montagem:** sem placa nova e sem módulo de carga dentro do travesseiro.

### 8.1 O circuito

Esquemático: `docs/diagramas/DIAG-02-esquematico.py`, folha **v4** (PROJETO, não montado).
✏️ *25/11: era a folha v3. No orçamento das peças, a célula escolhida (LiFePO4 18650 Rontek)
veio **sem proteção**, e o circuito ganhou a placa de proteção U3. Ela corta pelo negativo, e
por isso o terra de todo o circuito passou a ser o **P−** dela. A v3 continua gerada, como
registro.*

```
 B1 (+) ── U3 B+ ═ P+ ── Q1 AO3401A ── F1 1 A ── S1 ──┬──────────┬────────── 3V3   U1 ESP32 DevKit V1
 LiFePO4  placa de      D → S, porta  (sem PTC)  chave │          │                 (GY-521 no 3V3 e I2C
 3,0–3,6 V proteção     no P−                       C1 1000 µF  R1 1 MΩ              como na v1)
 B1 (−) ── U3 B−                                       │          ├──┬────── GPIO35 (ADC1)
           U3 P− ══ GND do circuito                   GND      R2 1 MΩ  C2 100 nF
                                                                  │      │
 (todo "GND" é o P− da U3; o B− da célula só vai à U3)           GND    GND ──────── GND
```

| Ref. | Componente | Por quê |
|---|---|---|
| B1 | LiFePO4 18650, 1 400 a 1 800 mAh, **de fabricante identificado e com certificação UN38.3**, com proteção integrada ou uma placa de proteção para LiFePO4 1S (corte em ~2,5 V). ✏️ *25/11, no orçamento: Rontek RTLFPO 18650, 3,2 V, "2 000 mAh 3C" no rótulo, **sem proteção**; a importadora responde pelo produto, mas a capacidade é o topo do que uma LFP 18650 entrega, e a real sai do ensaio de descarga (seção 9, item 4). Com 1 400 mAh, o pior caso da faixa ainda dá ~83 h (cálculo)* | contra célula falsificada e descarga profunda |
| U3 | ✏️ *25/11:* placa de proteção (PCM) para **LiFePO4 1S**, fixa no circuito, soldada aos fios do suporte; corte de descarga **entre 2,0 e 2,5 V** (o anúncio da Rontek, 6 A contínuos, não diz o valor: confirmar antes de comprar) | a célula comprada não tem proteção. Se ela se esgota no meio da noite, o ESP32 reinicia em ciclo e continua drenando, e só a placa impede a descarga profunda. Ela corta pelo **negativo**: o GND do circuito é o **P−** dela. Uma placa serve às duas células. Ela não se protege de célula invertida (o Q1 protege o ESP32, não ela) |
| Q1 | P-MOSFET de baixa resistência (por exemplo, da família AO3401 ou SI2301) como proteção contra inversão. ✏️ *25/11: AO3401A (SOT-23) numa plaquinha adaptadora para DIP; dreno do lado da U3, fonte do lado da carga, porta no P−* | a célula é removível e vai e volta do carregador: invertida, ela poria −3,3 V no ESP32. Um diodo em série custaria 0,2 a 0,4 V, fora da folga do LFP; o MOSFET, com 0,05 a 0,1 Ω a 3,2 V de porta, custa 15 a 30 mV no pico |
| F1 | **fusível rápido de 1 A**, de vidro ou lâmina, **não PTC** | protege os fios contra curto. 500 mA ficaria no limite do que o ESP32 pede; um PTC de 0,5 A tem ~0,5 a 1 Ω e derrubaria 0,15 a 0,3 V no pico do rádio |
| S1 | chave liga e desliga de 1 A ou mais | desligar sem abrir o travesseiro e **isolar a célula para gravar pelo USB** |
| C1 | eletrolítico de baixo ESR, 1 000 µF, ≥ 6,3 V, junto do pino 3V3 | segura o pico do rádio contra a resistência da célula, dos contatos e dos fios |
| R1, R2, C2 | divisor 1 MΩ + 1 MΩ com 100 nF, no GPIO35 | a leitura da bateria do `HW-10`. ADC1, porque o ADC2 não funciona com o Wi-Fi ligado. O divisor gasta ~1,8 µA. No LFP, a tensão é quase plana: serve para avisar o fim, não para dar porcentagem |
| fios | curtos e **soldados**, sem jumper de encaixe | é o mesmo defeito do `HW-11`, agora no caminho da corrente toda |

**Carregador**, fora do travesseiro: um carregador de bancada com modo LiFePO4, ou um módulo
TP5000 ajustado para 3,6 V. **Nunca** um carregador de Li-ion comum, que vai a 4,2 V.
✏️ *25/11: escolhido o módulo TP5000 USB-C "Li-ion/LiFePO4". Antes da primeira carga, conferir
como ele seleciona 3,6 V (muitos saem de fábrica em 4,2 V) e medir a tensão final com o
multímetro: não pode passar de 3,65 V.*

**Alternativa**, se a LFP 18650 não for encontrada com procedência: Li-ion 18650 **protegida** de
2 600 mAh, com um LDO RT9080 de 3,3 V entre o fusível e o pino 3V3, e carregador TP4056 com
proteção. Mais autonomia, mais calor no pico e química menos estável.

**Descartada para dentro do travesseiro:** a LiPo em bolsa. Fina, mas é a pior combinação de
química (LCO) e invólucro para ficar sob a pressão de uma cabeça a noite toda.

### Regras de uso que vêm com a decisão

- **Nunca ligar o USB com a chave S1 fechada.** O regulador da DevKit põe 3,3 V no mesmo nó da
  célula: com ela abaixo disso, ele a carregaria sem controle de corrente, e esquentaria (~0,7 W
  no regulador). Para gravar o firmware, abrir S1.
- **Carregar fora do travesseiro**, sobre superfície não inflamável.
- **Depois da carga, esperar pelo menos 2 h** antes de recolocar (seção 5.1).
- **Conferir a polaridade** ao recolocar a célula, mesmo com o Q1.

## 9. O que medir, e como (antes de comprar a capacidade definitiva)

O `RD-10` continua valendo: a recomendação acima já cumpre o mínimo com folga, mas a autonomia
real depende do consumo fixo medido.

1. **Corrente média por cenário.** Um multímetro na escala de mA em série com a célula, ou um
   módulo **INA219** entre a célula e o 3V3 (lê corrente e tensão pelo I2C, e serve depois ao
   `HW-10`). Medir em S1, tirar os LEDs (S1') e medir de novo. Sessões de 30 min, para pegar
   três envios. Com o multímetro, a escala de mA derruba tensão no pico do rádio: se a placa
   reiniciar durante o envio, usar a escala de A para o pico e a de mA só no repouso.
2. **O pico do rádio:** a tensão no 3V3 durante o envio não pode cair abaixo de 3,0 V (o INA219
   ou um osciloscópio).
3. **O log serial com a célula:** o USB alimentaria a placa junto com a célula. Para ler o log
   com a placa na bateria, usar um cabo USB **só de dados**, com o fio de 5 V cortado. Na DevKit V1 a ponte CP2102 costuma ser
   alimentada pelo 3V3 e continua funcionando, mas **conferir na placa** antes de confiar nisso. Sem esse cabo, a
   descarga se acompanha pelo servidor: a última época gravada diz quando a célula acabou.
4. **Descarga real:** uma célula cheia, sem recarga, até o firmware parar; comparar com a seção 6.
5. **Temperatura (`CALC-05` contra `RD-12`):** 8 h no travesseiro, com um termômetro na face
   sobre o dispositivo e outro num ponto de controle do mesmo travesseiro; a temperatura do
   próprio MPU6050, que vai em cada época, entra como terceira série.

## 10. A proposta anterior: LiPo + PowerBoost 500C no VIN

A página dos autores (seção 2) propõe **LiPo 1S → PowerBoost 500C → VIN do ESP32**. Ela funciona
eletricamente, e acerta em duas regras que este estudo também adota (retirar do travesseiro para
carregar; desligar a alimentação externa antes de ligar o USB). Mas a energia faz duas conversões:
o PowerBoost sobe de 3,7 V para 5,2 V (~5 mA próprios com o LED aceso, *especificação* do
fornecedor), e o AMS1117 da DevKit desce de 5,2 V para 3,3 V (~5 mA próprios, e 37 % da potência
virando calor). Com os 2,55 mA dos circuitos integrados, os dois LEDs e a ponte USB-serial, e uma
eficiência de 85 % suposta para o PowerBoost em carga baixa (*estimativa*; o fornecedor não
publica a curva nessa faixa):

| | Proposta anterior | Recomendação (S1) |
|---|---:|---:|
| Corrente tirada da célula | ~22 mA | ~9,4 mA |
| Potência dissipada no travesseiro | ~82 mW | ~31 mW |
| Autonomia com LiPo de 2 000 mAh / LFP 18650 | ~69 h | ~129 h |

Abaixo do mínimo de 72 h, com o dobro e meio do calor, e com a LiPo em bolsa. **A caixa** (80 ×
100 × 20 mm, com abertura de recarga) pode ser aproveitada, trocando o alojamento da LiPo e do
PowerBoost por um suporte de 18650.

## 11. Revisão de 17/11

Conferido contra o firmware, as folhas de dados e o esquemático, depois da primeira versão:

- **Corrigido — a frequência do processador.** O §Z.4.4c supõe 80 MHz; o firmware roda a 240 MHz.
  A referência dos circuitos integrados passou de 2,28 a 2,55 mA (3.1), e os cenários foram
  refeitos: S1 de 8,8 para 9,4 mA, S1' de 6,5 para 6,8 mA, S2 de 2,5 para 2,8 mA. A autonomia da
  LFP 18650 em S1 caiu de 138 para 129 h; o mínimo de 72 h segue cumprido em toda a faixa.
- **Corrigido — a soma do consumo fixo de S1.** A tabela das fontes somava 6,9 mA e o cenário dizia
  ~6,5 mA; agora as duas dizem 6,9 mA, com a faixa de cada fonte declarada.
- **Corrigido — o fusível.** A primeira versão sugeria 500 mA, no limite dos 500 mA que a
  Espressif pede da fonte. Passou a 1 A, rápido e não PTC.
- **Acrescentado — a proteção contra inversão (Q1)**, o capacitor de reserva como parte do circuito
  e não como remédio, os fios soldados, o pino do divisor (GPIO35, no ADC1), o cuidado com o fim
  da descarga e o cabo só de dados para o log com a célula.
- **Acrescentado — o esquemático:** a folha v3 do `DIAG-02`, gerada e conferida.
- **Acrescentado — a proposta anterior dos autores** (seção 10) e a resposta à dúvida do VCC do
  GY-521 (5.1).
- **Conferido sem mudança:** o giroscópio está em espera no firmware (o transdutor a 0,600 mA vale);
  o I2C roda a 400 kHz, como o §Z.4.4c corrigiu em 04/11; as contas de capacidade útil, de
  autonomia, de potência e de C-rate foram refeitas e batem.

## Fontes

- ESP32-WROOM-32 e série ESP32, folhas de dados (faixa de alimentação; fonte de 500 mA ou mais;
  consumo por modo e do rádio):
  [ESP32-WROOM-32](https://documentation.espressif.com/esp32-wroom-32_datasheet_en.html),
  [ESP32](https://documentation.espressif.com/esp32_datasheet_en.html),
  [consumo do rádio, cópia da folha de dados](https://docs.deneyapkart.org/en/Cards/Deneyap-Kart/Power-Consumption-esp32.md).
- Consumo da DevKit e do regulador alimentado por trás:
  [Hubble, consumo do ESP32](https://community.hubble.com/guides/esp32-power-consumption-datasheet-vs-reality),
  [esp32.com, deep sleep](https://esp32.com/viewtopic.php?p=96892),
  [lucidar.me](https://lucidar.me/en/esp32/power-consumption-of-esp32/).
- LED do GY-521: [MySensors](https://forum.mysensors.org/post/103184),
  [Arduino Forum](https://forum.arduino.cc/t/mpu-6050-accel-gyro-and-low-power/412368).
- LiFePO4 direto no ESP32:
  [Home Assistant Community](https://community.home-assistant.io/t/how-to-power-an-esp32-supermini-board-directly-from-a-lifepo4-battery/975202),
  [Arduino Forum](https://forum.arduino.cc/t/how-to-safely-power-an-esp32-with-a-lifepo4-battery-and-charge-it/1431270).
- Térmica das químicas: [Frontiers in Chemistry, 2024, doi 10.3389/fchem.2024.1324840](https://www.frontiersin.org/journals/chemistry/articles/10.3389/fchem.2024.1324840/full);
  definições de início de *runaway*: [BAM, meta-análise](https://opus4.kobv.de/opus4-bam/files/56807/Meta-analysis.pdf).
- Proteção de célula e seus limites: [Battery University, BU-304b](https://batteryuniversity.com/article/bu-304b-making-lithium-ion-safe),
  [DW01, folha de dados](https://mm.digikey.com/Volume0/opasdata/d220001/medias/docus/7158/5272_DW01.pdf).
- Células LiFePO4: [EEMB](https://www.eemb.com/products-52),
  [IFR26650-33A](https://cdn.simpower.co.nz/wp-content/uploads/2022/03/IFR26650-33A.pdf),
  [Keeppower IFR14500](https://keeppower.com/product/14500-3-2v-600mah-lifepo4-rechargeable-lithium-ion-battery-cell-ifr14500).
- Tensão de repouso do LiFePO4: [Wevolver](https://www.wevolver.com/article/lifepo4-voltage-chart-soc-voltages-for-32v12v24v48v-systems),
  [SkyRC](https://blog.skyrc.com/understanding-lifepo4-batteries/).
- Carregador TP5000: [revisão de bancada](https://lygte-info.dk/review/Review%20Charger%20TP5000%204.2-3.6V%20module%20UK.html).
- Reguladores: [RT9080](https://cdn.sparkfun.com/assets/7/2/5/b/3/DS9080.pdf),
  [ME6211](https://wmsc.lcsc.com/wmsc/upload/file/pdf/v2/lcsc/2201121200_MICRONE-Nanjing-Micro-One-Elec-ME6211C25M5G_C2835813.pdf).
- PowerBoost 500C (consumo próprio e conversor): [Adafruit](https://www.adafruit.com/product/1944),
  [guia da Adafruit](https://learn.adafruit.com/adafruit-powerboost-500-plus-charger/overview).
- Placa alternativa avaliada e não escolhida (carregador só para LiPo de 4,2 V):
  [FireBeetle 2 ESP32-E](https://wiki.dfrobot.com/dfr0654/).
