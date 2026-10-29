# `firmware/nucleo/` — a lógica que não pode depender do Arduino

Buffer de épocas, controle de cadência, política de reconexão e serialização
do payload. **Zero** `#include <Arduino.h>`, zero `WiFi.h`, zero `delay()`.

```bash
cd firmware/nucleo
make            # compila e roda as 341 verificações
make capacidade # mede quantas horas cabem no buffer
make sintaxe    # confere se os .ino compilam (stubs do Arduino)
```

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
então não há razão para espremer no RTC. O `sketch.ino`, quando for reescrito
(`FW-07`), precisará das 128 no RTC — o heap não sobrevive ao Deep Sleep.

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
tick), e o item `API-03` — endpoint de lote no backend.

## Os arquivos

| Arquivo | O quê |
|---|---|
| `relogio.h` | `millis()` estendido para 64 bits (wrap em 49,7 dias) e resolução monotônico → hora de parede |
| `cadencia.h` | Grade absoluta, contagem de ticks perdidos, sem `delay()` |
| `epoca.h/.cpp` | Registro de 32 B, acumulador por pico, fusão para degradação |
| `buffer.h` | Fila de tamanho fixo com degradação no lugar do descarte |
| `reconexao.h` | Backoff exponencial com teto e jitter determinístico |
| `payload.h/.cpp` | JSON do contrato v2.0.0, ISO 8601 sem `gmtime` |
| `capacidade.cpp` | A medição |
| `testes/` | 341 verificações, incluindo duas noites simuladas de 8 h |

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
