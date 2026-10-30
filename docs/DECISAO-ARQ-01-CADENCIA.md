# Análise: cadência de amostragem e arquitetura de energia (ARQ-01, partes a e b)

**Data:** 2026-10-29 · **Item:** `ARQ-01` · **Estado:** ✅ **(a) e (b) decididos pelo autor
em 2026-10-30: arquitetura C2** (sono leve + FIFO, MPU a 50 Hz, DLPF de 21 Hz, taxa medida e
reamostragem igual à do `ml/`, entrega em lote pelo `API-03`). A decisão muda a frase da
pergunta de pesquisa e **vai ao orientador para confirmação** junto com o `RQ-01`. O `ARQ-01`
só fecha com a parte (c), medida na placa.

> **A decisão, em uma linha (30/10).** Escolhida a C2 depois do `ML-11`
> (`docs/ARQUITETURA-DE-CAPTACAO.md`), que mediu o lado do modelo: o que o WoM entrega custa
> de 0,07 a 0,10 de kappa na base de cabeça, e a C2 custa 3,4 mA a mais que o WoM (só nos
> circuitos integrados). O conjunto de features (8 ou 3) **não** foi decidido: espera o
> `ML-12`. As consequências estão aplicadas no backlog (`HW-03`, `FW-05`, `FW-07`, `FW-08`), no
> `CALCULOS-TCC.md` (Z.1.4 e Z.4.4b) e no `CLAUDE.md`.

> **Reprodutibilidade.** Todo número deste documento sai de:
>
> ```bash
> python3 scripts/estudo_cadencia.py              # o estudo inteiro
> python3 scripts/estudo_cadencia.py --conferir   # só as asserções; sai != 0 se divergir
> ```
>
> O script **importa** as constantes e os dois modelos do `scripts/calculos_tcc.py` em vez de
> copiá-los, e reprova se as arquiteturas de referência deixarem de dar os 23,9 mA e 1,91 mA do
> `CALCULOS-TCC.md` Z.4.4. Mesma convenção dos outros estudos: onde o valor não foi conferido na
> fonte primária, ele entra como **parâmetro em faixa**, e a faixa é varrida.
>
> **Nada aqui foi medido.** São especificação de folha de dados, premissas declaradas e
> aritmética. A parte (c) existe para isso.

---

## 1. O problema

O firmware de bancada amostra a **0,1 Hz** (`INTERVALO_AMOSTRA_MS = 10000` no
`envio-continuo.ino`): 3 amostras por época de 30 s. O `AcumuladorDeFeatures` recusa a época,
e o código de features do `DATA-07b`, correto e testado, nunca emitiu uma feature em campo.

Subir a cadência esbarra no Z.4.3: as features pedem ≥ 42 Hz (Nyquist do DLPF de 21 Hz), o
modo de baixo consumo do MPU6050 vai até 40 Hz, e passar disso obriga o modo normal (500 µA) e
elimina o despertar por movimento (WoM). O backlog resumiu como **"escolher entre o vetor de 8
features e o Deep Sleep com WoM"**.

Esta análise mostra que **essa dicotomia estava incompleta**: o Z.4.4 comparou o WoM com uma
amostragem contínua em que o processador fica **ativo a noite toda**, e há um meio-termo que
nenhum documento do projeto considerava.

## 2. O que a folha de dados acrescentou

Conferido nesta sessão (fontes no cabeçalho do script):

| Fato | Fonte | Consequência |
|---|---|---|
| O MPU6050 tem **FIFO de 1024 B**, feita para *"read the data in bursts and then go into a low-power mode"* | PS-MPU-6000A-00 Rev. 3.2, §4 e §5.1 | Só acelerômetro, 6 B por amostra: **170 amostras**, ou **3,40 s a 50 Hz**. O processador pode dormir entre leituras |
| O acelerômetro amostra a **1 kHz**; com cristal externo de 32,768 kHz, a 1,024 kHz | Mesma folha, §6.6 | A taxa é 1 kHz / (1 + divisor): **não há 32 Hz nem 64 Hz** (o mais perto: 32,26 Hz, +0,81 %; 62,5 Hz, −2,34 %). Com o cristal, 32 e 64 Hz seriam exatos, mas o módulo GY-521 não o tem |
| O oscilador interno tem **±5 % a 25 °C** e **−15 % a +10 % na faixa de temperatura** | Mesma folha, §6.6 | **Nenhuma** taxa ditada pelo MPU cai exata na grade. O firmware precisa medir a taxa real e reamostrar, como o `ml/` já faz com as bases públicas (`sinal.py::taxa_efetiva`) |
| No sono leve do ESP32, RAM e estado da CPU **sobrevivem** | ESP-IDF v6.1, *Sleep Modes* | O acumulador de 18,8 KiB não se perde, ao contrário do Deep Sleep |
| No sono leve, **a conexão Wi-Fi não é mantida** | Mesma página | Cada entrega paga reassociação. Isso pesa a favor do lote (`API-03`) |

**Não conferido** (entra como faixa ou como condição): a fórmula do divisor e os degraus do
DLPF (só em cópia de terceiros do *Register Map*); se a FIFO funciona no modo de baixo consumo;
a latência de saída do sono leve (0,2–3 ms varridos); o custo de CPU por amostra.

## 3. As arquiteturas

- **A. WoM, sem features.** É o `sketch.ino` de hoje: o ESP32 em Deep Sleep, o MPU em baixo
  consumo a 20 Hz, e o despertar a cada evento. Registra **eventos**; não produz o vetor de 8
  features.
- **B. Contínua com a CPU ativa.** É o Z.4.4: o ESP32 a 80 MHz a noite toda, o MPU a 500 µA,
  lendo amostra por amostra.
- **C1. Sono leve, uma amostra por despertar.** O temporizador do ESP32 acorda a 64 Hz, lê uma
  amostra e volta a dormir. O relógio é o do ESP32 (cristal de 40 MHz), então a grade de 32 Hz
  sai exata por decimação por 2.
- **C2. Sono leve com a FIFO.** O MPU enche a FIFO a 50 Hz, e o ESP32 acorda quando ela está
  pela metade (85 amostras, a cada 1,70 s), esvazia em rajada e volta a dormir. O relógio é o
  do MPU, então é preciso estimar a taxa e reamostrar.
- **C2-LP, condicional.** É C2 com o MPU em baixo consumo a 40 Hz e o DLPF em 10 Hz. Só vale
  se a FIFO funcionar nesse modo, o que não foi conferido.
- **D. Híbrida, descartada.** WoM no repouso e amostragem só na atividade. As épocas paradas,
  que são justamente o sono, ficariam sem features e sem a estimativa da gravidade (`ĝ`), da
  qual `inclinacao_rel` e `d_angulo` dependem. Ela entrega features só onde elas importam menos.

## 4. (a) Comparação

### 4.1 Corrente média, só circuitos integrados

São as premissas do Z.4.4, sem mudança: rádio de 100 mA, POST de 1 s, uma entrega por época,
ESP32 a 20 mA, bateria hipotética de 2 000 mA·h.

| Arquitetura | I<sub>média</sub> | Autonomia | Features |
|---|---:|---:|---|
| A. WoM | 1,91 mA | 1 049 h | não |
| B. Contínua, CPU ativa | 23,9 mA | 84 h | sim |
| C1. Sono leve por amostra (64 Hz) | 7,64 mA | 262 h | sim, grade exata |
| **C2. Sono leve + FIFO (50 Hz)** | **5,31 mA** | **377 h** | sim, reamostrada |
| C2-LP (condicional) | 4,80 mA | 417 h | sim, mas com banda de 10 Hz |

**C2 é 4,5× mais barata que B**, e é B que o Z.4.4 chamava de "amostragem contínua". O ganho não
vem do sensor, que é o mesmo nas duas, e sim de o processador passar 93,6 % da hora em sono
leve e só 3,1 % acordado lendo a FIFO (o resto é rádio), em vez de 97 % em modo ativo.

Na varredura de todos os parâmetros em faixa (I<sub>esp</sub>, I<sub>rf</sub>, t<sub>post</sub>,
latência de despertar, relógio do I²C, CPU por amostra), C2 fica entre **3,20 e 18,55 mA**, e B
entre **22,6 e 46,2 mA**. O topo de C2 é quase todo rádio: 240 mA durante 2 s, 120 vezes por
hora.

**Em C2, o rádio responde por 63 % da corrente.** É a mesma conclusão que o Z.4.4 tirou para o
WoM (87 %): passado o modo de sono, quem decide é o número de transmissões.

### 4.2 Com lote (`API-03`): uma entrega por hora

| | A | B | C1 | C2 |
|---|---:|---:|---:|---:|
| I<sub>média</sub> | 0,27 mA | 21,24 mA | 4,36 mA | **2,03 mA** |

Com o lote, **C2 chega a 2,03 mA, praticamente o WoM de hoje** (1,91 mA, que entrega por evento),
e **com** as features. Em circuitos integrados puros, o WoM com lote continua 7,6× mais barato.
Esse é o preço das features, e não deve ser escondido.

### 4.3 O consumo fixo da placa

São os parâmetros do Z.4.5, ainda não medidos (`HW-02`):

| I<sub>placa</sub> | A | B | C1 | C2 | B / C2 | C2 / A |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 1,91 | 23,88 | 7,64 | 5,31 | 4,50 | 2,79 |
| 1 mA | 2,91 | 24,88 | 8,64 | 6,31 | 3,94 | 2,17 |
| 5 mA | 6,91 | 28,88 | 12,64 | 10,31 | 2,80 | 1,49 |
| 10 mA | 11,91 | 33,88 | 17,64 | 15,31 | 2,21 | 1,29 |

A ordem **A < C2 < C1 < B** vale em toda a faixa, e o `--conferir` trava isso. Como no Z.4.5,
a placa não inverte nada, mas comprime as razões. Com o DevKit de hoje (miliampères de repouso),
**C2 custa só 1,3 a 1,5× o WoM**, enquanto B custa 2,8 a 4,2× (placa de 5 a 10 mA).

### 4.4 Critérios além da corrente

| | A. WoM | B. Contínua | C1 | C2 |
|---|---|---|---|---|
| **Pergunta de pesquisa**, "baixo consumo" e "eventos de movimento" | literal | difícil de sustentar | sustentável | sustentável |
| **Hipótese**, validação contra acelerometria pública | só com uma feature degradada: −0,07 a −0,10 de κ na cabeça (`ML-11`, 30/10) | sim | sim | sim |
| O `ml/` consome? | não, nem o pipeline nem o dourado | sim | sim, grade exata | sim, reamostrada como as bases públicas |
| `HW-03` (INT do MPU num GPIO RTC) | **necessário** | desnecessário | desnecessário | opcional (alarme de transbordo da FIFO) |
| `FW-07` (reescrever o `sketch.ino`) | como escrito: buffer no RTC, Deep Sleep | muda: heap e laço contínuo | muda: sono leve | muda: sono leve e driver de FIFO |
| `FW-08` (flash como registro) | o estudo assume heap de ~300 KiB, que não sobrevive ao Deep Sleep | vale | vale (sono leve preserva a RAM) | vale |
| Complexidade nova | nenhuma | baixa | média: temporizador de 64 Hz e despertar a cada 15,6 ms | média: FIFO, estimativa de taxa e reamostragem |
| Só a medição responde | — | — | se o despertar a cada 15,6 ms cabe | latência, transbordo, taxa real |

**Sobre A e a hipótese.** O WoM não fica sem validação de saída: dá para simular o despertar por
limiar nas bases públicas e medir o kappa de uma "contagem de eventos por época". ✏️ *30/10:
medido, com proxies, no `ML-11` (`docs/ARQUITETURA-DE-CAPTACAO.md` §3.3).* Na base de cabeça,
que é o substituto mais próximo do travesseiro, o que o WoM entrega custa de **0,07 a 0,10 de
kappa** contra as 8 features (de 66 % para 50–55 % do teto humano); no pulso, de 0,01 a 0,05.
O mesmo experimento mostrou que **três features bastam** (`mag_din_media`, `p_frac`,
`d_angulo`), o que simplifica a C2, mas não muda a energia dela.

## 5. (b) Banda e taxa, contra os 12,8 Hz

### 5.1 O critério não é "2 × banda do DLPF"

O `ml/` filtra a **12,8 Hz** (0,8 × Nyquist da grade de 32 Hz) antes de reamostrar. Uma
componente de entrada em f > f<sub>s</sub>/2 aparece em f<sub>s</sub> − f, e **só contamina as
features se cair abaixo de 12,8 Hz**. O que dobra para a faixa entre 12,8 Hz e
f<sub>s</sub>/2 o filtro de software remove. Logo, o requisito é que o DLPF já tenha atenuado
o sinal em **f<sub>s</sub> − 12,8 Hz**:

| f<sub>s</sub> | Entrada que dobra para dentro dos 12,8 Hz |
|---:|---:|
| 40 Hz | acima de 27,2 Hz |
| 50 Hz | acima de 37,2 Hz |
| 62,5 Hz | acima de 49,7 Hz |

Isso refina o Z.1.4 sem invalidá-lo. Os 42 Hz garantem o Nyquist da banda do DLPF; o critério
contra os 12,8 Hz é o que o próprio `CALCULOS-TCC.md`, em "Uma divergência técnica", pediu. A
50 Hz com DLPF de 21 Hz, o que dobra para a banda útil está acima de 37 Hz, quase o dobro do
corte do DLPF. A 40 Hz com o mesmo DLPF, a dobra começa em 27 Hz, pouco acima do corte, e
**não é seguro**. A atenuação do DLPF em cada frequência não está na folha de produto, então
esse julgamento é qualitativo.

### 5.2 A combinação por arquitetura

| Arquitetura | DLPF | Taxa no sensor | Até a grade de 32 Hz |
|---|---|---|---|
| A | (WoM, 20 Hz em baixo consumo) | — | não há grade |
| B, C2 | **21 Hz** (o de hoje, `FW-06`) | **50 Hz** (divisor 19) | medir a taxa real pelo relógio do ESP32; Butterworth de 4ª ordem a 12,8 Hz de fase zero na época, na taxa de origem; interpolar para 960 amostras. É **a mesma cadeia** do `sinal.py::reamostrar` |
| C1 | 21 Hz | **64 Hz** pelo temporizador do ESP32 (leitura de registrador, sem FIFO) | filtro de 12,8 Hz e decimação por 2: grade exata, sem interpolação |
| C2-LP | **10 Hz** | 40 Hz em baixo consumo | como em C2, mas o DLPF corta **abaixo** dos 12,8 Hz: as features divergem do `ml/` por construção. Exigiria refazer o `ml/` com corte de 10 Hz e medir o kappa |

**Por que 50 Hz em C2, e não 62,5 ou 100 Hz:** é a menor taxa nativa acima dos 42 Hz com a
dobra longe do DLPF (37 Hz). 62,5 Hz empurra a dobra para 50 Hz ao custo de 25 % mais
despertares. Fica como opção, se a parte (c) mostrar energia relevante acima de 37 Hz, o que
num travesseiro é improvável.

**Por que não C2-LP agora:** economiza 0,5 mA (5,31 → 4,80), menos que a incerteza do consumo
fixo da placa, e cobra duas incógnitas (a FIFO no modo de baixo consumo, e o kappa com corte de
10 Hz). Fica registrada como otimização posterior.

## 6. Recomendação

> ✅ **Adotada pelo autor em 30/10** (ver o cabeçalho). O texto abaixo é o de 29/10, mantido
> como procedência.

> ⚠️ **É uma recomendação, não uma decisão.** A escolha muda a frase da pergunta de pesquisa e
> o capítulo de energia, e é do autor com o orientador.

**C2: sono leve com FIFO, MPU a 50 Hz, DLPF de 21 Hz, taxa estimada e reamostragem igual à do
`ml/`, com entrega em lote (`API-03`).**

1. É a única arquitetura que entrega o vetor de features (a hipótese) com uma corrente que se
   defende como "baixo consumo": 4,5× abaixo da contínua ingênua, e, com a placa de hoje, 1,3 a
   1,5× o WoM.
2. A cadeia de sinal no dispositivo passa a ser a mesma que o `ml/` aplica às bases públicas.
   A divergência de banda que o "Uma divergência técnica" temia desaparece por construção.
3. Ela não depende do `HW-03`, a ligação do INT que exige solda e GPIO RTC.
4. **O custo, sem esconder:** em circuitos integrados puros, o WoM com lote continua 7,6× mais
   barato. Se a defesa precisar do menor consumo absoluto e aceitar ficar sem as features, a
   resposta é A.

**Plano B**, se a parte (c) derrubar C2 (despertar caro, transbordo da FIFO, taxa instável): C1
mantém o sono leve com o relógio do ESP32, a 7,64 mA. B fica como último recurso.

## 7. O que muda, se C2 for escolhida

| Onde | Mudança |
|---|---|
| `CALCULOS-TCC.md` Z.4.3 | Continua verdadeiro (WoM e features não se combinam), e ganha a ressalva de que "contínua" não implica CPU ativa |
| `CALCULOS-TCC.md` Z.4.4–Z.4.5 | Ganham a terceira linha (C2) e a tabela de lote. O texto pronto para o TCC **não foi editado**: muda depois da decisão |
| `CALCULOS-TCC.md` Z.1.4 | Ganha o critério de dobra contra 12,8 Hz (§5.1) |
| Pergunta de pesquisa (`RQ-01`) | "Baixo consumo" passa a se sustentar por sono leve com FIFO, não por Deep Sleep com WoM |
| `CLAUDE.md`, "Contexto do projeto" | Diz *"usando Deep Sleep e Wake-on-Motion"*; deixaria de ser verdade |
| `HW-03` | Deixa de ser pré-requisito; vira opcional |
| `FW-07` | A reescrita do `sketch.ino` passa a ser em torno do sono leve e da FIFO, e não do buffer no RTC |
| `FW-05` | Desbloqueia com taxa e banda definidas (50 Hz, DLPF de 21 Hz) |
| `FW-08` | A premissa do heap de ~300 KiB passa a valer |
| `API-03` | Sobe de prioridade: em C2, o rádio é 63 % da corrente |

## 8. A parte (c): o que só a placa responde

1. A **latência real** de saída do sono leve e a corrente do sono leve **na placa** (a folha dá
   0,8 mA para o chip).
2. Se o esvaziamento a cada 1,70 s **nunca transborda** a FIFO numa noite, contando o bit de
   transbordo.
3. A **taxa real** do MPU (contagem de amostras contra o relógio do ESP32) e a deriva dela numa
   noite dentro do travesseiro.
4. O tempo de parede do fechamento da época (filtro de fase zero e interpolação sobre 1 500
   amostras, mais as features), que tem de caber antes de a FIFO encher.
5. O tempo de **reassociação Wi-Fi** depois do sono leve, que o modelo trata como t<sub>post</sub>
   de 0,5–2 s.
6. O relógio do I²C: o `envio-continuo.ino` usa 100 kHz implícitos, e o modelo varre 100 e 400
   kHz.

## 9. Limitações desta análise

- **Predição, não medição.** Vale tudo o que o Z.4.7 diz do modelo de origem.
- A folha de produto foi lida na **Rev. 3.2**. O `calculos_tcc.py` cita a 3.4, que não foi
  relida aqui.
- A fórmula do divisor, os degraus do DLPF e o comportamento da FIFO no modo de baixo consumo
  vêm do *Register Map*, que **não foi conferido na fonte primária**. O PDF da TDK não baixou.
- O modelo de C2 soma o pull-up durante todo o tempo acordado, não só durante o tráfego I²C
  (superestima levemente).
- O custo de **energia** da reassociação Wi-Fi está dentro do t<sub>post</sub> em faixa. Ele não
  foi modelado à parte.
