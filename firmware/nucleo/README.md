# `firmware/nucleo/` — a lógica que não pode depender do Arduino

Buffer de épocas, controle de cadência, política de reconexão e serialização
do payload. **Zero** `#include <Arduino.h>`, zero `WiFi.h`, zero `delay()`.

```bash
cd firmware/nucleo
make            # compila e roda a suíte, as paridades e a cadeia C2
make capacidade # mede quantas horas cabem no buffer
make sintaxe    # confere se os .ino compilam (stubs do Arduino)
make mutacao-cadeia  # sabota a cadeia C2 e exige que a suíte acuse
```

✏️ *30/10 (`FW-07`): `make` roda quatro alvos — 341 verificações da suíte
original, 157 da paridade (`dourado`), 105 das peças da C2 (`c2`) e 456 da
cadeia C2 contra o dourado dela (`cadeia`). Contados em 30/10, `gcc:13`.*

Não há `arduino-cli` nem `platformio` no ambiente. Há `g++`, e para esta
camada ele basta.

---

## Por que existe

O `envio-continuo.ino` chamava `conectarWiFi()` **dentro do laço de
amostragem**, e `conectarWiFi()` gastava até 20 s em `delay(500)`. Com
intervalo de 10 s, uma queda de rede fazia cada ciclo levar 20–30 s.

A série continuava saindo. Com aparência normal. Com a base de tempo
derivada.

Para actigrafia — cuja unidade **é** a época fixa de 30 s — isso é pior que
lacuna. A lacuna a análise vê; a deriva, não. **Dado distorcido que parece
válido é o modo de falha mais caro deste projeto**, e a maior parte das
decisões aqui sai dessa frase.

## As quatro regras

**1. Nada na medição espera por conectividade.** Nem conexão, nem envio, nem
serial, nem init de sensor. Os três travamentos saíram: `while (!Serial)`,
`while(1)` no `mpu.begin()` falho, e a conexão síncrona no laço.

**2. Perda de cadência vira campo no dado.** Época com menos amostras que a
cadência prometia sai com `EPOCA_INCOMPLETA`; época sem amostra nenhuma sai
como `EPOCA_VAZIA` e **ocupa lugar no buffer**. Custa 32 bytes dizer "aqui não
houve medida" — e sem isso a análise veria duas épocas encostadas e concluiria
que a noite foi medida sem falha.

**3. O buffer é de épocas, não de amostras.** Com amostras, "buffer cheio" só
tem saídas ruins: descartar o antigo perde o adormecer, descartar o novo perde
o despertar. Com épocas há uma terceira: agregar o já guardado em janelas mais
longas e continuar medindo. Perde-se **resolução**, não **cobertura**.

**4. A grade é absoluta.** O próximo instante é sempre `t0 + k·período`, nunca
`última + período`. Na segunda forma, todo atraso de execução entra
permanentemente na base de tempo e nunca mais sai.

## A degradação é exata, não uma aproximação

O contrato (`docs/DATA-CONTRACT.md` §2.5) define o único método aceito como
`pico-da-magnitude`. **Máximo é associativo**: o pico de duas épocas de 30 s
adjacentes *é* o pico da época de 60 s que as cobre — não uma estimativa, o
valor exato. Degradar não introduz erro de agregação nenhum; o que se perde é
só saber em qual metade o pico caiu.

Se o método fosse média, isso não valeria, e `total` deixaria de ser comparável
com o limiar de 1,2 m/s² sem caso especial. É mais uma razão para o pico.

**Teto imposto pelo backend:** `validar_agregacao` rejeita `epoca_s > 3600`.
Com base de 30 s, isso trava a degradação no nível 6 (1920 s). Degradar além
disso produziria época que o firmware guarda e não consegue entregar — pior
que descartar, porque ocupa espaço fingindo que o dado está salvo.

## Capacidade — medida, não estimada

`make capacidade` roda o buffer de verdade, enchendo de verdade. Registro de
**32 bytes**, travado por `static_assert`:

| Orçamento | Épocas | Resolução cheia (30 s) | Com degradação |
|---|---:|---:|---:|
| 4 KB — RTC, sobrevive ao Deep Sleep | 128 | **1,07 h** | **65,6 h** |
| 6 KB — RTC folgado | 192 | 1,60 h | 99,7 h |
| 32 KB — heap | 1024 | **8,53 h** | **543 h** |
| 128 KB — heap generoso | 4096 | 34,1 h | 2182 h |

A faixa entre as duas colunas é o valor do buffer ser de épocas: ali o dado
continua **inteiro** e só a granularidade piora. Com amostras instantâneas
essa faixa não existe.

**O `envio-continuo` usa 1024 épocas (32 KB de heap)**: uma noite de 8 h em
resolução cheia, sem degradar uma única vez. A placa não dorme nesse sketch,
então não há razão para espremer no RTC.

✏️ **30/10: esta linha dizia que o `sketch.ino` reescrito (`FW-07`) precisaria
das 128 épocas no RTC, porque o heap não sobrevive ao Deep Sleep.** A decisão
do `ARQ-01` (C2) trocou o Deep Sleep por **sono leve, que preserva a RAM**:
o buffer vai para o heap, e o registro durável para a flash (`FW-08`). A linha
das 128 no RTC fica na tabela como medida, não como escolha.

Por que `sizeof` no host vale para o ESP32: os campos têm largura fixa e estão
em ordem decrescente de alinhamento, então não há padding em nenhum dos dois
ABIs. Se alguém acrescentar um campo, o `static_assert` quebra o build **antes**
de a medição passar a mentir.

## Custo de drenar (dimensiona o backoff)

8 h de buffer = **960 POSTs**, um handshake TLS novo cada. Seriam 2880 se o
buffer fosse de amostras, e 1,2 milhão quando o `FW-05` subir a amostragem
para ≥ 42 Hz — e continuariam sendo 960 épocas. **É a agregação, não o buffer,
que torna a drenagem possível.**

Ainda assim 960 POSTs sequenciais são caros. Daí duas decisões: drenagem em
rajada limitada (no máximo 3 por volta, e só se houver folga até o próximo
tick), e o item `API-03` — endpoint de lote no backend. ✏️ *30/10: o `API-03`
fechou (`POST /api/data/lote`, até 60 leituras), e o lado do dispositivo é o
`lote.h`, abaixo.*

## A arquitetura C2 — da FIFO à grade de 32 Hz (`FW-07`, 30/10)

Na C2 (`docs/DECISAO-ARQ-01-CADENCIA.md`) o MPU6050 amostra sozinho a 50 Hz
**nominais** na FIFO e o ESP32 acorda em sono leve a cada ~1,7 s para
esvaziá-la. O modelo espera outra coisa: 960 amostras numa grade de 32 Hz por
época. Entre as duas pontas há três problemas, e um arquivo para cada:

1. **A FIFO não tem carimbo de tempo** e o oscilador do sensor erra até
   −15/+10 %. `cadeia_c2.h` ajusta uma reta (contagem acumulada × instante da
   drenagem) e **mede** a taxa, em vez de assumir 50 Hz.
2. **De ~50 para 32 Hz é decimação.** `reamostragem.h` aplica a cadeia do
   `ml/src/sinal.py::reamostrar` por época: Butterworth de 4ª ordem a 12,8 Hz,
   fase zero, na taxa de origem, com 0,5 s de margem de cada lado; depois
   interpolação linear.
3. **O que os bytes significam** e quando a leitura não presta (transbordo,
   desalinhamento): `fifo_mpu.h`.

**Medido em 30/10** (`ml/testes/dourado_cadeia_c2.py`, 50 sementes × 4 taxas):
com o instante verdadeiro de cada amostra, a cadeia por época dá a mesma grade
que o `ml/` da noite inteira em 1,5e-6 g — a margem resolve as bordas. O que
sobra é o **relógio**: a regressão erra o instante em até ~5 ms, e isso move
`enmo_max` em até 2,2e-3 g e `zcr` em até 8 cruzamentos. Daí o dourado da
cadeia conferir contra **duas** referências — o pipeline (validade, régua
larga) e a mesma conta em Python (exatidão, régua de 1e-4 g). O C++ bate com
a segunda em **9,2e-8 g** e com a linha do tempo dela em 0 s.

**Um achado de projeto, não de código:** a 50 Hz exatos, 1,7 s são 85
amostras inteiras, e o despertar trava em fase com a amostragem — toda
drenagem cai no mesmo ponto entre duas amostras e a regressão não tem como
tirar a média. `intervalo_de_drenagem_us` varia o intervalo em [0, 20 ms) e o
pior erro de tempo cai de 8,1 para 4,7 ms.

⚠️ **O relógio do ESP32 é tomado como verdadeiro.** Em sono leve ele conta
por um oscilador interno mais pobre que o cristal; quanto ele erra é a parte
(c) do `ARQ-01`, e só a placa responde. ⚠️ **Nada disto rodou num MPU6050**:
o que está verificado é a aritmética, contra o dourado e por mutação.

**Controle positivo** (`make mutacao-cadeia`): 16 sabotadores — taxa nominal
no lugar da medida, sem anti-aliasing, Q errado, filtro causal, sem meio
passo, sem margem, grade deslocada, FIFO little-endian, regressão com todas as
drenagens, escala de ±16 g; e, na suíte de unidade, transbordo e taxa que
deixam de recusar, lote que confirma pendentes ou aceita pendente no meio,
buffer que confirma depois de degradar, FIFO no teto que deixa de ser
transbordo. **16/16 acusados pelo alvo esperado** em 30/10.

**Memória:** `CadeiaC2` ocupa 23,7 KiB (anel de 2304 amostras, área de
trabalho do filtro, 48 drenagens); a grade de saída são mais 11,3 KiB. Cabe
porque o sono leve preserva a RAM — não caberia nos 8 KB do RTC.

## A fila na flash (`FW-08`, 31/10)

A fila em RAM (`buffer.h`) não guarda o vetor, perde tudo num reset e, cheia, funde épocas —
e época fundida não tem features. `fila_flash.h` grava cada época num registro de 64 B
(`registro_flash.h`) na partição `dormio` de `firmware/partitions.csv`, em log circular:

- **entregue sem apagar:** a confirmação programa um byte de `0xFF` para `0x00`; só `0x00`
  conta, então um corte no meio reenvia em vez de perder;
- **cheia recusa a nova:** o setor só é apagado se não tiver pendente;
- **sobrevive a reset:** `montar()` relê a partição e reconstrói cabeça e cauda pela `seq`;
  gravação cortada é recusada pelo CRC e pulada;
- **instante na gravação:** hora de parede se o relógio já foi sincronizado; senão,
  monotônico da sessão — e depois de um reset sem sincronia a época vai sem `ts`.

`make capacidade` lê a tabela e mede **32 704 registros = 272,5 h = 11,4 dias**. `make fila`
testa tudo contra uma flash NOR simulada, com corte de energia em cada byte; `make
mutacao-fila` sabota a fila de 10 maneiras. A ponte com o ESP32 é
`firmware/midia_flash_esp32.h`, que por ora só passa pelo `make sintaxe`.

## Os arquivos

| Arquivo | O quê |
|---|---|
| `relogio.h` | `millis()` estendido para 64 bits (wrap em 49,7 dias) e resolução monotônico → hora de parede |
| `cadencia.h` | Grade absoluta, contagem de ticks perdidos, sem `delay()` |
| `epoca.h/.cpp` | Registro de 32 B, acumulador por pico, fusão para degradação |
| `buffer.h` | Fila de tamanho fixo com degradação no lugar do descarte |
| `reconexao.h` | Backoff exponencial com teto e jitter determinístico |
| `payload.h/.cpp` | JSON do contrato v2.0.0, ISO 8601 sem `gmtime` |
| `filtro.h/.cpp` | Biquad Butterworth ida e volta (`DATA-07b`) |
| `caracteristicas.h/.cpp` | As 6 features e `g` por época (`DATA-07b`) |
| `fifo_mpu.h/.cpp` | Registradores da C2 e decodificação da FIFO (`FW-07`) |
| `reamostragem.h/.cpp` | Anti-aliasing de 4ª ordem e interpolação para 32 Hz (`FW-07`) |
| `cadeia_c2.h/.cpp` | Taxa medida por regressão e a grade de cada época (`FW-07`) |
| `lote.h/.cpp` | Envelope e leitura da resposta do `POST /api/data/lote` (`FW-07`) |
| `registro_flash.h/.cpp` | O registro de 64 B da flash: CRC, instante, marca de entregue (`FW-08`) |
| `fila_flash.h/.cpp` | Log circular na partição `dormio`, que sobrevive a reset (`FW-08`) |
| `epoca_c2.h/.cpp` | A `Epoca` de uma época da cadeia C2: pico da grade, temperatura (`FW-07` (b)) |
| `envio_da_fila.h/.cpp` | Da fila ao lote e de volta: prefixo contíguo, registro sem payload sai da frente (`FW-07` (b)) |
| `capacidade.cpp` | A medição |
| `testes/` | Suíte, paridades, peças e cadeia da C2, e os verificadores por mutação |

O núcleo entra nos sketches por `nucleo_amalgama.cpp` — a IDE do Arduino só
compila arquivos da pasta do sketch, então uma única unidade de tradução
inclui os `.cpp` do núcleo. A alternativa seria duplicar o núcleo em cada
sketch, e as cópias divergiriam na primeira correção — que é exatamente como
`sketch.ino` e `envio-continuo.ino` acabaram com critérios de movimento
diferentes antes do `FW-06`.

## O que a suíte pegou

Quatro bugs, um deles sério: o fechamento de época era preguiçoso, e
`amostrar` recusava amostra de um slot futuro por não ter como fechar o
anterior. **Uma amostra em cada três** — as dos instantes 30 000, 60 000,
90 000… — sumia, e toda época saía marcada `INCOMPLETA` com a medição
perfeita. Na placa isso apareceria depois de uma noite de coleta; aqui
apareceu em 3 ms. O teste de regressão está em
`testar_amostra_na_virada()`.

Os outros: `fundir` consultava `a->vazia()` *depois* de mesclar as flags (uma
época com dado fundida com uma lacuna saía marcada como lacuna); e duas
expectativas de teste que estavam erradas, não o código.

`make sintaxe` existe pelo mesmo motivo: até 2026-09-22 o `envio-continuo.ino`
versionado tinha duas strings com quebra de linha literal no meio — **não
compilava em máquina nenhuma**, e ninguém percebeu porque nada no repositório
tentava compilar.
