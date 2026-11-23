# DormioSmart — Hardware, fases e contrato de dados

Referência para tudo que envolve o dispositivo físico e o dado que ele produz. Ler antes de qualquer tarefa de firmware, hardware ou integração device↔backend. Complementa o `CLAUDE.md` (operacional) e o `docs/METODOLOGIA.md`.

> ✏️ **Versionado desde 16/11/2026 (`GIT-05`).** Até então era interno, e o `scripts/calculos_tcc.py` (que roda no CI) e outros documentos o citavam sem que um clone o trouxesse. Atualizado no mesmo dia para o estado do projeto: as marcas ✏️ *16/11* dizem o que mudou desde que o texto foi escrito, em maio. A arquitetura vigente é a do `ARQ-01` (`docs/DECISAO-ARQ-01-CADENCIA.md`), os requisitos estão em `docs/REQUISITOS-DISPOSITIVO.md` e o contrato de dados em `docs/DATA-CONTRACT.md`. Onde este texto divergir do diário, o diário vence.

---

## Fases do projeto

O TCC vai de uma prova de conceito simulada até um **dispositivo físico que funciona na prática**. As duas fases convivem no mesmo repositório; o firmware deve ser escrito pensando na transição.

**Fase 1 — Simulação (Wokwi)**
- Valida a lógica do firmware (leitura do MPU6050, envio dos dados) sem placa.
- Onde está o mocking de hardware/software. Bom para iterar rápido e para a primeira entrega.
- ✏️ *16/11: a simulação serviu à primeira entrega. Hoje a lógica é testada no host, em C++ puro (`firmware/nucleo/`, `make`), e o `sketch.ino` compila para o ESP32 no CI (`CI-12`). O desenho de maio, Deep Sleep com Wake-on-Motion, foi substituído pela arquitetura C2 do `ARQ-01` (30/10): sono leve, lendo a FIFO do sensor a 50 Hz.*

**Fase 2 — Dispositivo real (entregável final)**
- Montagem física com os componentes reais, gravação do firmware na placa, leitura real do sensor, energia/autonomia e o dado real chegando na web-app.
- **Critério de sucesso:** o dispositivo **funciona montado**, capta movimento durante uma noite real e os dados aparecem na aplicação. Simulação não substitui essa validação.
- ✏️ *16/11, estado: as soldas foram refeitas e conferidas nas 6 posições (`HW-09`, 12/11). O `sketch.ino` rodou 41 min na placa, 80 épocas, todas com features (`FW-07` (c), 12/11), e envia à produção com `HTTP 200` em lotes de 20 (`FW-13`). **Falta:** a energia (`HW-02`), o encapsulamento e a segurança térmica (`HW-04`), a viabilidade de bancada (`VIA-01`), uma noite captada pelo travesseiro (`VAL-01`) e as fotos e o diagrama de montagem (`HW-06`; `hardware/` segue vazia).*
- Entregar também: esquema de ligação (wiring), diagrama de montagem e fotos do protótipo em `hardware/` — material de TCC **e** de conteúdo público.

> **Wokwi é meio, não fim.** Ao escrever firmware, manter o código preparado para rodar em placa física, não amarrado a particularidades do simulador. Deixar sempre claro o que é mock/simulado e o que já roda no hardware real.

---

## Bill of materials (BOM)

Lista pré-base informada pelo usuário em maio. ✏️ *16/11: o botão e o resistor eram andaime de simulação e saíram do produto — o `sketch.ino` não usa botão (`HW-01`, separado pelo esquemático do `DIAG-02`).*

| Componente | Função declarada | Leitura crítica |
|---|---|---|
| 1x ESP32 DevKit V1 | microcontrolador + Wi-Fi | núcleo legítimo, serve Fase 1 e Fase 2 |
| 1x MPU6050 (módulo GY-521) | acelerômetro + giroscópio (movimento) | mede **movimento**, não sono diretamente — ver "Adequação do hardware" |
| 1x Push Button | "simula o sinal de Wake-up" | **artefato de simulação**: num dispositivo real, o wake-up vem do próprio movimento (Wake-on-Motion do MPU6050), não de um botão. Provavelmente não faz parte do produto final |
| 1x Resistor 10kΩ | pull-down físico do botão | só existe por causa do botão; cai junto se o botão sair |
| Jumpers / fios | conexão em protoboard | montagem de protótipo |

> ✏️ *16/11: a conectividade foi decidida — as épocas ficam numa fila na flash e vão em lote quando há rede (`FW-08`, `API-03`). A energia segue em aberto (`HW-02`: LiPo + TP4056, e se o DevKit fica) e o encapsulamento também (`HW-04`).* O diagnóstico de maio, abaixo, vale para essas duas.
>
> **Diagnóstico honesto:** este é um BOM de **prova de conceito / Fase 1**, não de dispositivo de monitoramento de sono real. Push button + pull-down são andaime de simulação. Falta tudo da Fase 2: **alimentação/autonomia** (bateria LiPo + módulo de carga tipo TP4056, ou outra estratégia), **encapsulamento/fixação** (como o aparelho fica no corpo/colchão a noite toda) e a decisão de **conectividade/armazenamento** (Wi-Fi a noite inteira drena bateria; talvez buffer local + sync).

---

## Adequação do hardware ao problema — análise obrigatória

Antes de planejar a Fase 2, avaliar criticamente se o conjunto de periféricos resolve o problema **de verdade**, não só se monta:

1. **O sensor responde à pergunta de pesquisa?** O MPU6050 capta movimento. Estimar sono/vigília a partir de movimento tem base na literatura de **actigrafia** (defensável), mas **estadiamento de sono** (REM, sono profundo) não se faz só com acelerômetro. Garantir que o hardware sustenta o que o projeto afirma medir (ver `docs/METODOLOGIA.md`).
2. **Componentes de simulação vs. de produto.** Mapear o que existe só por causa do Wokwi (push button, pull-down) e o que vai pro dispositivo real. Não levar andaime de simulação pra montagem final sem justificar.
3. **O que falta para funcionar uma noite inteira.** Energia, autonomia, fixação, robustez de conexão, persistência se cair o Wi-Fi. Listar lacunas e propor solução.
4. **Sugerir trocas/adições com trade-offs** (custo, o que já foi comprado, complexidade) e deixar a decisão final com o usuário — sem pivotar nada sozinho.

### Abertura para repensar o hardware

Os componentes foram comprados, mas **não são intocáveis**. Ao planejar tarefa de hardware, propor (com justificativa) quando algo melhorar eficiência, custo, autonomia ou viabilidade:
- substituir/complementar um sensor;
- trocar a estratégia de energia/conectividade;
- pivotar parte da arquitetura (onde o processamento acontece, como o dado é enviado).

Apresentar trade-offs (o que ganha, o que perde, o que já foi comprado e seria descartado) e deixar a decisão final com o usuário. Prioridade sempre: **funcionar na prática**, não só passar na simulação.

---

## Contrato de dados (firmware ↔ backend ↔ banco)

> ✏️ *16/11: o contrato existe — `docs/DATA-CONTRACT.md`, versão 2.12.0, conferido pelos testes do backend, do firmware e do app. A lista abaixo é o que ele precisava cobrir, escrita antes dele.*

O dado que viaja do ESP32 até o Supabase precisa de um **contrato explícito e versionado**, definido **antes** de implementar a integração. É pré-requisito da Fase 2 e do ML — sem ele, integração, banco e ML ficam construídos sobre suposições que divergem. Documentar e manter como fonte da verdade:

- **Esquema do payload:** campos que o device envia, tipos, unidades (aceleração em g ou m/s²?), timestamp (fuso, formato, relógio do device vs. do servidor).
- **Frequência e agregação:** leitura crua a cada X ms, ou agregação no device (ex.: índice de movimento por minuto)? Muda bateria, volume de dados e o que o ML recebe.
- **Schema do banco:** tabelas, chaves, relação device → usuário → noite → leitura. Definir antes de criar tabela na mão.
- **Erros e bordas:** dado fora de faixa, duplicado, ou chegando após queda de conexão (reenvio/idempotência).
- **Versionamento:** se o formato mudar, registrar a versão — dado antigo no banco não pode quebrar a análise depois.

> A segurança desse fluxo (autenticação do device, RLS, validação de entrada) está nas Decisões técnicas do `CLAUDE.md`.

---

## Validação de hardware

- O que dá para testar em software (lógica isolada da camada de hardware) entra na suíte de testes normal.
- O que só se verifica no dispositivo real (leitura do sensor montado, consumo, estabilidade do Wi-Fi, captação noturna) é **verificação manual documentada**: registrar procedimento e resultado em `hardware/` ou no devlog. **Não marcar item de Fase 2 como concluído com base apenas na simulação.**

---

## Arquitetura do produto: v1 (núcleo) → v2 (fusão de 2 acelerômetros)

Decisão de 2026-05-31, registrada como **contingência projetada** (não como pivô já executado).
Vem do levantamento de sensores feito no planejamento; resumo da análise abaixo.

### v1 — núcleo proposto (hipótese atual)
Um único MPU6050 embarcado no travesseiro, captando eventos de movimento (ESP32 em sono leve).
✏️ **30/10 (`ARQ-01`):** a arquitetura de energia decidida é **sono leve + FIFO do MPU a 50 Hz**, não Deep Sleep
com Wake-on-Motion — ver `docs/DECISAO-ARQ-01-CADENCIA.md`. O INT do MPU (`HW-03`) deixou de ser pré-requisito.
É a proposta do documento e a base da RQ. **Mantida como caminho principal.**

### Limitação antecipada (por análise — ainda NÃO medida)
Da física do acoplamento mecânico + literatura de sensor não-contato sob colchão (MDPI Sensors,
2023/2025): o travesseiro acopla bem o **movimento da cabeça** e mudanças de posição que a
envolvem, mas **pode subcaptar movimento do corpo sem deslocamento da cabeça** (ex.: rolar na
cama). A evidência não-contato mais forte é **sob o colchão**, onde o corpo inteiro acopla —
acoplamento melhor que o do travesseiro. **É uma limitação ANTECIPADA, não demonstrada:** quem
decide é o VIA-01 (teste de bancada).

> ✏️ *16/11: o `VIA-01` foi feito — em 16/11, uma sessão de bancada do autor (n = 1), com dois ciclos de 5 min de cada bloco e 45 épocas fora das bordas, separou o corpo virando do repouso (δ de Cliff = +1,00 em `enmo_media`, p < 0,001 na permutação) e a cabeça do repouso (δ = +0,99 em `mag_din_media`), com o mesmo resultado em cada ciclo isolado; cabeça e corpo **não** se separaram entre si (δ = +0,55, p = 0,061). Pelo critério fixado antes, **fica a v1**, e o `HW-07` não foi acionado. Limite: n = 1, e o giro até a posição de bruços mexe a cabeça no lugar. Diário, 16/11 (ix).*

> Redação honesta para o TCC: *"limitação identificada por análise de viabilidade e literatura,
> a ser validada empiricamente pelo protótipo"* — **nunca** "limitação medida/comprovada" sem o VIA-01.

### v2 — escopo do produto com 2 acelerômetros (solução de contingência)
- **Componentes:** 2× MPU6050 — um no travesseiro, um sob o colchão (ou na estrutura da cama).
- **Barramento:** mesmo I2C; endereços `0x68` e `0x69` via pino `AD0` do 2º módulo (sem hub).
- **Dado:** índice de atividade por época **por fonte** (travesseiro vs. cama) + fusão (atualizar
  o contrato de dados acima); permite mostrar a contribuição de cada sensor.
- **Energia/térmico:** ambos de baixo consumo e **não-contato** — preserva a premissa do projeto.
- **Custo:** +1 MPU6050 (peça barata) + fios; única compra adicional.
- **Identidade / RQ:** deixa de ser "apenas no travesseiro" → "não-invasivo **na cama/travesseiro**".
  **Exige revisar a redação da RQ com o orientador** (a contribuição e o escopo seguem: movimento
  não-invasivo de baixo consumo).
- **Embasamento:** fusão de sensores / cobertura espacial, alinhada à literatura de smart-bed (MDPI).

### Gatilho de decisão
**VIA-01** (bancada, com o hardware já em mãos) decide:
- travesseiro sozinho distingue movimento → **fica em v1** (economia de escopo);
- subcaptura confirmada → **aciona v2**.
Ambos os resultados são informativos e defensáveis na banca (foresight + validação planejada).
VIA-01 é uma sonda de bancada leve (protoboard, **sem solda**) e **não é pré-requisito do documento
de 03/06** — é validação de Fase 2.
