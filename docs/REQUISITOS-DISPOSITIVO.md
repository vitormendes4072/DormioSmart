# Requisitos do dispositivo (REQ-01)

> **Escrito em 05/11/2026**, sobre `develop` `aeec783`. Responde ao objetivo específico do TCC que
> promete "definir os requisitos iniciais (dimensões, conforto, autonomia, aquecimento, custo e
> segurança)". Até aqui o texto do TCC não tinha seção de requisitos, embora o cronograma marcasse a
> atividade como concluída.
>
> **Os números calculados saem de `scripts/requisitos_dispositivo.py --conferir`**, que roda no CI
> (job `documentos`). O script deriva cada número do modelo de energia já conferido
> (`estudo_cadencia.py`) e do próprio firmware (`firmware/partitions.csv`, `fila_flash.h`,
> `sketch.ino`). Nenhum número desta página foi escrito de cabeça.

## Como ler

Cada requisito tem um **critério verificável**, de onde ele vem e em que **estado** está:

| Estado | Significado |
|---|---|
| **Atendido em teste** | Verificado por teste automatizado no computador. Ainda não na placa. |
| **Calculado** | Atendido pelo modelo, com as premissas declaradas. Falta medir. |
| **A medir** | Precisa da placa montada (depende da solda do sensor). |
| **Aberto** | Falta uma decisão ou uma compra. O item do backlog que a carrega está indicado. |
| **Proposto** | O valor do critério é proposta deste documento e **precisa ser confirmado pelos autores e pelo orientador**. |

Nada aqui foi medido na placa: o firmware de produto ainda não rodou nela.

---

## 1. Medição e dados

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-01 | Medir o movimento continuamente durante a captação | Acelerômetro a 50 Hz, filtro passa-baixas de 21 Hz e faixa de ±8 g, sem lacuna entre esvaziamentos da fila do sensor | `ARQ-01`; `firmware/nucleo/fifo_mpu.h`; `CALCULOS-TCC.md` Z.1 | Atendido em teste · a medir na placa (`FW-05`) |
| RD-02 | Resumir cada época de 30 s no próprio dispositivo | Uma linha por época: rótulo de repouso ou movimento, 6 características e a direção da gravidade | Contrato de dados v2.7.0, §2.6; `payload.cpp` | Atendido em teste |
| RD-03 | Características independentes da orientação do travesseiro | Nenhuma característica muda quando o sinal é rotacionado | `test_features_invariantes_a_rotacao` (`ml/testes/test_vetor_dourado.py`) | Atendido em teste |
| RD-04 | O dispositivo calcula o mesmo que o pipeline de análise | O núcleo em C++ reproduz o vetor de referência do pipeline em Python | Alvo `dourado` do firmware; `test_dourado_cadeia_c2.py` | Atendido em teste |
| RD-05 | Não perder dados sem rede por pelo menos uma noite | Fila na *flash* com capacidade ≥ 8 h. **Calculado a partir do firmware: 32 704 registros, 272,5 h (11,4 dias)** | `partitions.csv`; `fila_flash.h`; `make capacidade` | Atendido em teste |
| RD-06 | Não perder épocas por queda de energia ou falha de envio | Uma época sai da fila só depois de o servidor confirmar o recebimento; a fila sobrevive à reinicialização | `firmware/nucleo/fila_flash.h`, `lote.cpp`; alvo `fila` (mutação 13/13) | Atendido em teste |
| RD-07 | Os dados chegam ao painel dentro de um intervalo previsível | Envio a cada 10 min, em lotes de **20 épocas**; atraso máximo de 10 min mais a duração do envio, com rede | `sketch.ino` (`INTERVALO_DE_ENVIO_US`) | Atendido em teste · a medir na placa |
| RD-08 | Volume de dados previsível | **960 registros por noite de 8 h**, independentemente da quantidade de movimento | Época de 30 s | Calculado |

## 2. Autonomia

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-09 | Funcionar uma semana sem recarga, sempre ligado | **7 dias = 168 h** de operação contínua (o projeto não tem botão de liga e desliga) | Proposta deste documento | **Proposto** |
| RD-10 | Bateria dimensionada pela corrente medida, e não pela estimada | A capacidade é escolhida depois de medir o consumo fixo da placa (ver a tabela abaixo) | `CALCULOS-TCC.md` Z.4.5; `HW-02` | Aberto (`HW-02`) |

**Capacidade necessária para 168 h**, pela Equação 2 (A = C/I), conforme o consumo fixo da placa, que
**não foi medido**:

| Consumo fixo da placa | Corrente de referência (2,28 mA) | Pior caso da varredura (5,19 mA) |
|---|---|---|
| 0 mA (só os circuitos integrados) | **383 mAh** | 872 mAh |
| 1 mA | 551 mAh | 1 040 mAh |
| 5 mA | 1 223 mAh | 1 712 mAh |
| 10 mA | 2 063 mAh | **2 552 mAh** |

A leitura importante é a da coluna da esquerda. Com os circuitos integrados apenas, a semana cabe
numa bateria pequena. O consumo fixo da placa ESP32 DevKit V1 (regulador e conversor USB-serial),
na faixa de 1 a 10 mA, multiplica a capacidade necessária por até cinco. É por isso que o RD-10 manda
medir antes de comprar.

## 3. Aquecimento

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-11 | Potência média baixa o bastante para não aquecer o travesseiro | **7,5 mW** com a corrente de referência; **50,1 mW** no pior caso da varredura com placa de 10 mA | P = V·I, 3,3 V | Calculado |
| RD-12 | Aquecimento imperceptível na face do travesseiro | Depois de 8 h de operação, a face sobre o dispositivo fica **no máximo 1 °C acima** de um ponto de controle do mesmo travesseiro | Proposta deste documento; medição do `CALC-05` | **Proposto** · a medir (`CALC-05`) |
| RD-13 | Picos de potência curtos e espaçados | Rádio de 0,33 a 0,79 W (100 a 240 mA), por 2 a 8 s, a cada 10 min | `CALCULOS-TCC.md` Z.4.5 | Calculado |

O RD-12 é deliberadamente **comparativo**: não depende de citar um limite normativo de temperatura de
contato, e é medível com dois termopares. Se os autores preferirem um limite absoluto, ele precisa
vir de uma norma lida (por exemplo, as de segurança de equipamentos em contato prolongado com a
pele), e não desta página (`DOC-06b`).

## 4. Dimensões e conforto

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-14 | O módulo não é percebido pela cabeça | Espessura e área máximas do módulo encapsulado | — | **Aberto**: depende do encapsulamento e do travesseiro escolhido |
| RD-15 | Nenhuma emissão perceptível à noite | Sem som; nenhuma luz visível através do travesseiro | — | A medir: a placa DevKit V1 tem um LED de energia sempre aceso |
| RD-16 | Nada preso ao corpo | O dispositivo fica inteiro dentro do travesseiro | Escopo do projeto (Seção 5.2 do TCC) | Atendido por concepção |

## 5. Custo

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-17 | Custo de componentes de um protótipo | Soma dos preços pagos (ESP32 DevKit V1, módulo GY-521, bateria, carregador, encapsulamento) | — | **Aberto**: faltam os preços pagos pelos autores, a bateria e o carregador (`HW-02`) |

## 6. Segurança

| ID | Requisito | Critério verificável | Origem | Estado |
|---|---|---|---|---|
| RD-18 | Nenhuma tensão acima de 3,3 V nos pinos do ESP32 | Tensão de repouso de SDA e SCL medida ≤ 3,3 V; os *pull-ups* do módulo ligados ao trilho de 3,3 V | `CALCULOS-TCC.md` Z.3; `DIAG-02` | **Aberto** (`HW-02`, `HW-08`) |
| RD-19 | Bateria protegida contra sobrecarga, descarga profunda e curto-circuito | Módulo de carga com circuito de proteção | `HW-02` | **Aberto** (`HW-02`): nada comprado |
| RD-20 | Dados cifrados em trânsito, com o servidor autenticado | HTTPS com conferência do certificado contra as raízes do firmware | `SEC-15`; `conferir_tls_firmware.py` | Atendido em teste e no monitor da produção |
| RD-21 | Credencial do dispositivo revogável, sem expor segredo se o banco vazar | Token guardado como resumo criptográfico; marcação de revogação | Tabela `devices` | Atendido |
| RD-22 | Cada pessoa vê só os próprios dados | Isolamento no próprio banco (RLS), não por filtro na aplicação | Suíte RLS (174 testes) e mutação 32/32 | Atendido em teste |
| RD-23 | Dados não guardados indefinidamente | Prazo de retenção ou declaração formal de que não haverá | `LGPD-02` | **Aberto** (`LGPD-02`) |

---

## O que fica para os autores

1. **Confirmar ou trocar os dois valores propostos:** 7 dias sem recarga (RD-09) e 1 °C de
   elevação (RD-12).
2. **Informar os preços pagos** (RD-17) e, quando houver, as dimensões do travesseiro e do
   encapsulamento (RD-14).
3. **A medir na placa:** RD-01, RD-07, RD-12, RD-15 e RD-18. A primeira medição útil é a do consumo
   fixo da placa, porque é ela que decide a bateria (RD-10).
