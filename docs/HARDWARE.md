# DormioSmart — Hardware, fases e contrato de dados

Referência para tudo que envolve o dispositivo físico e o dado que ele produz. Ler antes de qualquer tarefa de firmware, hardware ou integração device↔backend. Complementa o `CLAUDE.md` (operacional) e o `docs/METODOLOGIA.md`.

---

## Fases do projeto

O TCC vai de uma prova de conceito simulada até um **dispositivo físico que funciona na prática**. As duas fases convivem no mesmo repositório; o firmware deve ser escrito pensando na transição.

**Fase 1 — Simulação (Wokwi)**
- Valida a lógica do firmware (Deep Sleep, Wake-on-Motion, leitura do MPU6050, envio dos dados) sem placa.
- Onde está o mocking de hardware/software. Bom para iterar rápido e para a primeira entrega.

**Fase 2 — Dispositivo real (entregável final)**
- Montagem física com os componentes reais, gravação do firmware na placa, leitura real do sensor, energia/autonomia e o dado real chegando na web-app.
- **Critério de sucesso:** o dispositivo **funciona montado**, capta movimento durante uma noite real e os dados aparecem na aplicação. Simulação não substitui essa validação.
- Entregar também: esquema de ligação (wiring), diagrama de montagem e fotos do protótipo em `hardware/` — material de TCC **e** de conteúdo público.

> **Wokwi é meio, não fim.** Ao escrever firmware, manter o código preparado para rodar em placa física, não amarrado a particularidades do simulador. Deixar sempre claro o que é mock/simulado e o que já roda no hardware real.

---

## Bill of materials (BOM)

Lista pré-base informada pelo usuário (a versão definitiva está nos arquivos do projeto — confirmar lá ao analisar):

| Componente | Função declarada | Leitura crítica |
|---|---|---|
| 1x ESP32 DevKit V1 | microcontrolador + Wi-Fi | núcleo legítimo, serve Fase 1 e Fase 2 |
| 1x MPU6050 (módulo GY-521) | acelerômetro + giroscópio (movimento) | mede **movimento**, não sono diretamente — ver "Adequação do hardware" |
| 1x Push Button | "simula o sinal de Wake-up" | **artefato de simulação**: num dispositivo real, o wake-up vem do próprio movimento (Wake-on-Motion do MPU6050), não de um botão. Provavelmente não faz parte do produto final |
| 1x Resistor 10kΩ | pull-down físico do botão | só existe por causa do botão; cai junto se o botão sair |
| Jumpers / fios | conexão em protoboard | montagem de protótipo |

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
