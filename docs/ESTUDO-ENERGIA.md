# Estudo de energia: bateria, autonomia e aquecimento (`HW-02`)

> **Estado:** estudo de 17/11/2026, sem medição de corrente na placa. Os números de consumo da
> placa são **estimativas em faixa** sustentadas por folha de dados e por relatos de bancada de
> terceiros; o `RD-10` manda medir antes de comprar, e a seção 9 diz como. A recomendação da
> seção 8 é a escolha **condicionada** a essa medida.
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
- **Simulação com bateria de lítio:** não há no repositório. O que existe com "bateria
  simulada" é o app do celular no emulador Android (diário, 09/11), sem relação com a placa.
  A tabela de capacidade por consumo fixo do `RD-09` é o mais próximo disso.

## 3. O que consome na placa, além dos chips

A placa usada é a **ESP32 DevKit V1** com o módulo **GY-521** (MPU6050). Fontes de consumo fixo,
presentes em todos os estados, inclusive no sono leve (*estimativa*, salvo indicação):

| Fonte | Corrente | Natureza |
|---|---:|---|
| Regulador AMS1117-3.3 da DevKit | ~5 mA em operação (11 mA máx.) | *especificação* do AMS1117 |
| Regulador da DevKit alimentado "por trás" (bateria no pino 3V3) | ~4 mA | relato de bancada: caiu a 12 µA ao isolar o regulador |
| LED de energia da DevKit | ~1,3 mA | resistor de 1 kΩ em 3,3 V |
| Ponte USB-serial CP2102, sem USB | ~0,1 a 0,2 mA | *especificação* (suspensão) |
| **LED de energia do GY-521** | **~1,35 mA** | relato de bancada: 1,39 mA → 44 µA ao remover o LED |
| Regulador do GY-521 | 0,05 a 0,1 mA | relato de bancada |

Daí três cenários de consumo total, somando os chips (2,28 mA; 1,88 a 5,19 mA) ao fixo da placa
(*cálculo* sobre *estimativa*):

| Cenário | O que muda na placa | Fixo da placa | **Total (referência)** | Faixa |
|---|---|---:|---:|---:|
| **S1** | nada: bateria no pino 3V3 | ~6,5 mA | **~8,8 mA** | 7,3 a 13,6 mA |
| **S1'** | tirar os **dois LEDs** (sem tocar no regulador) | ~4,2 mA | **~6,5 mA** | 6,1 a 9,5 mA |
| **S2** | tirar os dois LEDs e **isolar o AMS1117** | ~0,2 mA | **~2,5 mA** | 2,0 a 5,5 mA |

**O pico do rádio** é outra grandeza: transmissão 802.11b a 240 mA e recepção a 95–100 mA
(*especificação* da série ESP32), por alguns segundos a cada 10 min. É ele que dimensiona o
quanto a célula e os fios precisam entregar sem a tensão afundar, não a autonomia.

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
| Li-ion 18650 (NMC/LCO) protegida | 3,7 V nominal, 4,2 V cheia | 2 600 mAh | 18 × 67–69 mm, ~45 g | **sim** (LDO) | runaway mais violento; lata de aço |
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

Dois cuidados (*estimativa*, relatos de terceiros e folhas de dados das células):

- **Logo depois da carga, a célula marca 3,60 a 3,65 V**, no limite do ESP32. Fora do
  carregador, ela cai a ~3,4 V em 30 min a 2 h e a 3,30–3,35 V em algumas horas. Regra: **a
  célula descansa pelo menos 2 h depois da carga** antes de voltar ao travesseiro (ou o
  carregador termina em 3,5 V).
- **O GY-521 tolera:** o MPU6050 vai a 3,46 V, mas o módulo tem regulador próprio, que recebe
  a tensão da célula.

A Li-ion e a LiPo, de 4,2 V cheias, precisam de um LDO de baixo consumo próprio que aguente o
pico do rádio (por exemplo, RT9080: 600 mA, 0,31 V de queda a 600 mA; ME6211: 500 mA,
~40 µA próprios). O LDO dissiparia ~8 mW em média e ~0,27 W nos picos (*cálculo*: 0,9 V × I).

## 6. Autonomia por célula e cenário

Capacidade útil = nominal × 0,90 (LFP até 3,0 V) ou × 0,85 (Li-ion e LiPo até o limite do LDO) ou
× 0,80 (NiMH), × 0,90 de envelhecimento e temperatura (*cálculo* sobre *estimativa*):

| Célula | Útil | **S1** (8,8 mA) | **S1'** (6,5 mA) | **S2** (2,5 mA) |
|---|---:|---:|---:|---:|
| LFP 14500 | 486 mAh | 55 h (2,3 d) | 75 h (3,1 d) | 194 h (8,1 d) |
| **LFP 18650** | **1 215 mAh** | **138 h (5,8 d)** | **187 h (7,8 d)** | **486 h (20 d)** |
| LFP 26650 | 2 673 mAh | 304 h (12,7 d) | 411 h (17 d) | 1 069 h (45 d) |
| Li-ion 18650 + LDO | 1 989 mAh | 226 h (9,4 d) | 306 h (12,8 d) | 796 h (33 d) |
| LiPo 103450 + LDO | 1 530 mAh | 174 h (7,2 d) | 235 h (9,8 d) | 612 h (25 d) |
| 3 × AA NiMH + LDO | 1 440 mAh | 164 h (6,8 d) | 222 h (9,2 d) | 576 h (24 d) |

Na faixa de S1 (7,3 a 13,6 mA), a LFP 18650 dá de **89 a 166 h**: acima do mínimo de 72 h
mesmo no pior caso, sem mexer na placa.

## 7. Aquecimento

| Fonte de calor | Potência | Natureza |
|---|---:|---|
| Placa e sensor, média (S2 / S1 / pior S1) | 8 / 29 / 45 mW | *cálculo*, P = 3,3 V × I |
| Rádio, pico | 0,33 a 0,79 W, por segundos a cada 10 min | `RD-13` |
| Resistência interna da LFP (~50 mΩ) no pico de 300 mA | ~4,5 mW | *cálculo*, I²R |
| Regulador (só nas opções com LDO) | ~8 mW média, ~0,27 W no pico | *cálculo* |

Em uso normal, nada disso esquenta o travesseiro de forma perceptível: a média é de dezenas de
miliwatts, e a célula trabalha a menos de 0,01 C. **O risco térmico real é a falha** (curto,
sobrecarga, esmagamento), e ele se controla com a química (LFP), a lata de aço, a proteção, o
fusível e **carregar fora do travesseiro**. A afirmação "não esquenta" só vale depois do ensaio do
`CALC-05` contra o `RD-12`.

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

### Recomendação

**Uma célula LiFePO4 18650 de ~1 500 mAh, removível num suporte, ligada direto no pino 3V3 da
DevKit V1, carregada fora do travesseiro num carregador de LiFePO4.**

- **Tamanho:** 18 × 65 mm, ~40 g, o volume de um marcador de texto, rígido. Cabe ao lado da placa.
- **Autonomia:** 5,8 dias sem mexer na placa (S1), 7,8 dias tirando os dois LEDs (S1'), cerca de
  20 dias isolando o regulador (S2). O mínimo de 72 h é cumprido já em S1, mesmo no pior caso
  da faixa (89 h).
- **Aquecimento:** sem regulador, sem LDO, a química mais estável e a lata de aço.
- **Montagem:** sem placa nova e sem módulo de carga dentro do travesseiro. O carregador fica
  fora: um módulo TP5000 ajustado para 3,6 V ou um carregador comum com modo LiFePO4.

**Componentes:**

1. Célula LiFePO4 18650 de 1 400 a 1 800 mAh, **de fabricante identificado e com certificação
   UN38.3** (contra célula falsificada).
2. Suporte de 18650 com fios, e **um fusível em série** (por exemplo, 500 mA), entre a célula e o
   pino 3V3.
3. Chave liga e desliga no fio da célula (permite desligar sem abrir o travesseiro).
4. Proteção da célula: LFP de fabricante com proteção integrada, ou uma placa de proteção para
  LiFePO4 de 1S (corte por descarga em ~2,5 V).
5. Carregador de LiFePO4 (TP5000 em 3,6 V ou um carregador de bancada com modo LiFePO4).
6. Para o `HW-10`: um divisor resistivo de alto valor (1 MΩ + 1 MΩ, com capacitor) num pino do
   ADC1, para ler a tensão da célula. No LFP, a tensão é quase plana: serve para avisar o fim,
   não para dar porcentagem.

**Alternativa**, se a LFP 18650 não for encontrada com procedência: Li-ion 18650 **protegida** de
2 600 mAh, com um LDO RT9080 de 3,3 V no pino 3V3 e carregador TP4056 com proteção. Mais
autonomia, mais calor no pico e química menos estável.

**Descartada para dentro do travesseiro:** a LiPo em bolsa. Fina, mas é a pior combinação de
química (LCO) e invólucro para ficar sob a pressão de uma cabeça a noite toda.

### Regras de uso que vêm com a decisão

- **Nunca ligar o USB com a célula conectada.** O regulador da DevKit põe 3,3 V no mesmo pino da
  célula: com ela abaixo disso, ele a carregaria sem controle de corrente, e esquentaria. Para
  gravar o firmware, desligar a chave da célula (ou tirá-la do suporte).
- **Carregar fora do travesseiro**, sobre superfície não inflamável.
- **Depois da carga, esperar pelo menos 2 h** antes de recolocar (seção 5.1).

## 9. O que medir, e como (antes de comprar a capacidade definitiva)

O `RD-10` continua valendo: a recomendação acima já cumpre o mínimo com folga, mas a autonomia
real depende do consumo fixo medido.

1. **Corrente média por cenário.** Um multímetro na escala de mA em série com a célula, ou um
   módulo **INA219** entre a célula e o 3V3 (lê corrente e tensão pelo I2C, e serve depois ao
   `HW-10`). Medir em S1, tirar os LEDs (S1') e medir de novo. Sessões de 30 min, para pegar
   três envios.
2. **O pico do rádio:** a tensão no 3V3 durante o envio não pode cair abaixo de 3,0 V (o INA219
   ou um osciloscópio). Se cair, encurtar e engrossar os fios da célula ou pôr um capacitor de
   470 µF a 1 000 µF no 3V3.
3. **Descarga real:** uma célula cheia, sem recarga, até o firmware parar; comparar com a seção
   6. O log da placa já registra o horário de cada envio, e a última época mostra quando acabou.
4. **Temperatura (`CALC-05` contra `RD-12`):** 8 h no travesseiro, com um termômetro na face
   sobre o dispositivo e outro num ponto de controle do mesmo travesseiro; a temperatura do
   próprio MPU6050, que vai em cada época, entra como terceira série.

## 10. O que muda nos outros documentos

- `REQUISITOS-DISPOSITIVO.md`: o mínimo de 72 h ao lado do `RD-09`; a decisão proposta no `RD-10`
  e no `RD-17`.
- `CALCULOS-TCC.md` §Z.4.5: os cenários S1, S1' e S2 como hipótese a medir.
- `BACKLOG-COMPLETO.md`: o `HW-02` com a recomendação e o que falta (comprar, medir, montar).

## Fontes

- ESP32-WROOM-32 e série ESP32, folhas de dados (faixa de alimentação; consumo do rádio):
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
- Placa alternativa avaliada e não escolhida (carregador só para LiPo de 4,2 V):
  [FireBeetle 2 ESP32-E](https://wiki.dfrobot.com/dfr0654/).
