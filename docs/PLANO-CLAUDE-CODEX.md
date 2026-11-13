# Plano de execução — Claude Code e Codex em paralelo

**Versão de 12/11/2026, sobre `develop` `ba851f4`.** O backlog tinha 59 itens abertos (L0 28 · L1 16 ·
L2 6 · L3 9). Este plano diz **em que ordem** cada um entra, **quem é o dono** e **quais arquivos
cada dono pode tocar em cada onda**, para que os dois agentes trabalhem ao mesmo tempo sem PRs que
conflitem.

- **O `AGENTS.md` continua valendo inteiro.** Este plano só preenche a divisão do item 4 de lá,
  item por item.
- **O backlog continua sendo a fonte do *quê*.** Este plano é a fonte do *quando* e do *quem*.
- **Só o Claude edita este arquivo**, nas PRs de integração. O Codex informa no corpo da PR o que
  mudaria aqui, para que os dois não escrevam no mesmo arquivo ao mesmo tempo.

---

## 1. Quem faz o quê

| Dono | Área (o que pode editar) | Papel |
|---|---|---|
| **Codex** | `web-app/` (menos as migrações não reservadas a ele), `frontend/src/`, `ml/` | Bugs e funcionalidades de backend e frontend, testes desses módulos, ML |
| **Claude** | `firmware/`, `frontend/android/`, `.github/`, `scripts/`, `vercel.json`, os textos de `docs/` e `../documento/` | Firmware e bancada, app nativo, CI e infraestrutura, cálculos e texto do TCC; **revisão por execução, integração e releases** |
| **Autor** | O ferro de solda, a placa, o celular, o painel do Supabase e da Vercel, o orientador | Decide, solda, mede, dorme com o aparelho, aprova planos e merges |

**Os arquivos de conflito garantido** (diário, backlog, a tabela de testes do `CLAUDE.md`) seguem as
regras 9–11 do `AGENTS.md`: cada um escreve só a entrada e a linha do próprio item, e a contagem diz
sobre que commit foi feita. Quem resolve o conflito na integração é o Claude.

## 2. Como uma tarefa anda

1. **O autor entrega o item a um dos dois**, pelo ID e pela onda deste plano.
2. **O agente apresenta o plano, e o autor aprova** (`CLAUDE.md`, protocolo por tarefa).
3. **O agente implementa** numa worktree própria (o Codex em `.codex/worktrees/`, nunca no checkout
   principal), com testes que falham sem a correção e com controle positivo.
4. **PR para `develop`**, sem conflito, com três seções obrigatórias no corpo:
   - **Arquivos tocados;**
   - **Depende de** (PRs e itens);
   - **O que muda neste plano** (o dono propõe; quem aplica é o Claude).
5. **O Claude revisa executando:** roda os testes novos contra `develop` (têm de falhar), refaz as
   sabotagens e confere o diário.
6. **O autor aprova o merge, e o Claude mescla.** Uma PR por vez, rodando
   `conferir_backlog.py --conferir` depois de cada uma.
7. **Release (`develop` → `main`):** só o Claude, só com a aprovação do autor, e com a conferência
   pós-deploy completa (`/health`, `401`, região e um login real).

### Números reservados

Duas PRs com a mesma migração quebram o banco. Cada número abaixo pertence a um item; um número
novo, o autor reserva aqui antes.

| Migração | Item | Dono |
|---|---|---|
| `019` | `API-07` (pausar o recebimento) | Codex |
| `020` | `API-06` (lote numa chamada) | Codex |
| `021` | `DATA-06` (o limiar viaja com a leitura) | Codex |
| `022` | `APP-11` (marcar gravação de teste), se precisar de coluna | Codex |

IDs novos de backlog seguem a regra 5 do `AGENTS.md`: conferir em `origin/develop` e avisar o autor.

## 3. A ordem, em ondas

Em cada onda, as duas trilhas tocam **conjuntos de arquivos que não se cruzam**. Dentro de uma
trilha, a ordem numérica é a de execução. A onda seguinte começa quando os itens que a destravam
estiverem mesclados, e não quando todos os da onda anterior estiverem.

### Onda 0 — preparar (hoje)

| # | Item | Dono | O que é | Destrava |
|---|---|---|---|---|
| 0.1 | Etapa 0 | Claude | Fechar no backlog "soldar os pinos do MPU6050" (feito em 11/11); o que sobrou é o `HW-09` | o quadro do backlog volta a dizer a verdade |
| 0.2 | — | Claude | Este plano versionado, e o `AGENTS.md` apontando para ele | o Codex lê o plano sozinho |
| 0.3 | `HW-09` ✅ *(12/11)* | Autor | Refazer as soldas do sensor e prender os fios; o Claude conduz o teste nas 6 posições com o monitor ao vivo | toda a bancada (onda 1, trilha Claude) |
| 0.4 | `INFRA-05` | Autor | Depois da próxima noite com o celular, rodar a consulta do lote; o Claude fecha o item | `API-06` |

### Onda 1 — o que já afeta a produção, e a placa ganhando vida

**Trilha Codex** (só `web-app/database.py`, `web-app/routes.py`, `web-app/tests/`, `frontend/src/`):

| # | Item | O que é | Arquivos principais | Depende de |
|---|---|---|---|---|
| 1.1 | `DATA-15` + `API-08` ✅ *(12/11, #146)* | Paginar `GET /api/sleep-history` como `GET /api/features`; falha do banco vira `503`, e o painel mostra "não foi possível carregar" | `database.py`, `routes.py`, `lib/api.ts`, `hooks/useHistorico.ts`, `pages/Historico.tsx`, `lib/exportar.ts` | — |
| 1.2 | `UI-26` ✅ *(12/11, #153)* | A sessão que toca o corte é "parcial", nunca "completa" | `pages/Historico.tsx`, `lib/metricas.ts` | 1.1 mesclado |
| 1.3 | `UI-29` ✅ *(12/11, #154)* | O texto da ordem da tabela do painel | `pages/Dashboard.tsx` | 1.1 mesclado (mexe no painel) |
| 1.4 | `APP-15` | Erro ao listar as noites deixa de parecer lista vazia | `components/ListaDeNoites.tsx` | — (pode correr junto da 1.1) |
| 1.5 | `UI-28` | Teclado no diálogo de consentimento e no seletor de tema | `components/TelaDeConsentimento.tsx`, `components/SeletorDeTema.tsx` | — |
| 1.6 | `UI-27` | Avisar até a primeira janela da coleta fechar | `pages/Coletar.tsx`, `hooks/useColeta.ts` | — |
| 1.7 | `UI-18` | Provar na tela as notas de honestidade (lacuna, inferência, escopo) | testes do painel | 1.3 mesclado |

**Trilha Claude** (só `firmware/` e `docs/`; precisa do autor na bancada e do `secrets.h` dele):

| # | Item | O que é | Depende de |
|---|---|---|---|
| 1.8 | `FW-07` (c) | Gravar o `sketch.ino` na placa; ler pelo serial os prazos da FIFO, o pior trabalho e a deriva do relógio | `HW-09` |
| 1.9 | `FW-05` ✅ *(12/11)* | Medir na placa a FIFO de verdade, a taxa real e o transbordo | 1.8 |
| 1.10 | `SEC-15` (c) ✅ *(12/11)* | O handshake TLS na placa contra a produção | 1.8 |
| 1.11 | `FW-08` (c) | A fila na flash na placa: Wi-Fi desligado, religado, reenvio sem duplicata | 1.8 |
| 1.12 | `HW-08` | O I2C na bancada: pull-ups, 100 e 400 kHz | `HW-09` |
| 1.13 | **Integração e release R1** ✅ *(12/11, #157, com 1.1–1.3 e o firmware; 1.4–1.7 vão num R1b)* | Revisar e mesclar 1.1–1.7; release com login real | as PRs do Codex |

### Onda 2 — a primeira noite do travesseiro, e a dívida de segurança e CI

**Trilha Codex** (backend de autenticação e chaves; o frontend fica livre):

| # | Item | O que é | Arquivos principais | Depende de |
|---|---|---|---|---|
| 2.1 | `SEC-19` | Tirar o recuo para a `service_role` | `web-app/database.py` | R1 (a 1.1 mexe no mesmo arquivo) |
| 2.2 | `AUTH-09` | Validar o JWT localmente pelo JWKS | `web-app/auth.py` | 2.1 |
| 2.3 | `APP-11` | Marcar uma gravação como teste, para que não vire noite | app (tela da noite) e backend; migração `022` só se precisar | o desenho combinado com o Claude, porque toca `frontend/android/` |

**Trilha Claude** (`.github/`, `scripts/`, `web-app/tests/rls/`, `firmware/`, `vercel.json`):

| # | Item | O que é | Depende de |
|---|---|---|---|
| 2.4 | `VIA-01` | Bancada: 2 min parado, 2 min mexendo a cabeça, 2 min virando o corpo | onda 1 da placa |
| 2.5 | `VAL-01` | A primeira noite com o travesseiro (o autor dorme; o Claude analisa) | 2.4 |
| 2.6 | `DATA-14` | O `t` do celular é a temperatura da bateria: contrato e núcleo | — |
| 2.7 | `CI-10` | O Python do CI igual ao da Vercel | — |
| 2.8 | `CI-09` | Um job para o app Android | — |
| 2.9 | `CI-11` | Os dois harnesses de mutação com mensagem certa | — |
| 2.9b | `CI-12` | Compilar o `sketch.ino` para o ESP32 no CI (`scripts/compilar_sketch_esp32.py`) | — |
| 2.10 | `SEC-13` | A suíte de RLS sem reaplicar os GRANTs no fim | — |
| 2.11 | `SEC-20` | Cabeçalhos de segurança no `vercel.json` | — |
| 2.12 | **Integração e release R2** | | |

**Autor:** dormir com o travesseiro (2.5) e levar ao orientador o pacote da seção 4.

### Onda 3 — dispositivos e envio

**Trilha Codex** (as telas de dispositivos e o lote):

| # | Item | O que é | Depende de |
|---|---|---|---|
| 3.1 | `API-07` | Pausar e retomar o recebimento por aparelho (migração `019`) | R2 |
| 3.2 | `UI-25` | O guia de pareamento manual | 3.1 (mesma tela) |
| 3.3 | `API-06` | O lote numa chamada ao banco (migração `020`) | `INFRA-05` fechado com a medição |

**Trilha Claude:**

| # | Item | O que é | Depende de |
|---|---|---|---|
| 3.4 | `ARQ-01` (c) | Confirmar a cadência C2 com a noite do travesseiro | 2.5 |
| 3.5 | `VIA-02` | Celular e travesseiro gravando juntos | 2.5 |
| 3.6 | `HW-10` | Bateria real: firmware e medição. O campo opcional na API vai numa PR do Codex, depois da 3.1 | `HW-02` |
| 3.7 | `APP-14` | Pareamento por QR Code no Android (protótipo) | 3.2 mesclado, `HW-02` |
| 3.8 | **Integração e release R3** | Migrações `019` e `020` aplicadas pelo autor antes do merge | |

**Codex, em paralelo:** `ML-12` (c), com as noites do travesseiro (3.4 entrega os dados).

### Onda 4 — o dado real vira resultado (L2)

| # | Item | Dono | O que é | Depende de |
|---|---|---|---|---|
| 4.1 | `DATA-06` | Codex | O limiar viaja com a leitura (migração `021`) | 3.5 |
| 4.2 | `ML-09` | Codex | Ajuste de limiar para o travesseiro, sem retreino | 2.5, 3.5 |
| 4.3 | `ML-10` | Codex | O que o modelo devolve ao usuário, e o que não devolve (assumir a especificidade externa de 0,507) | 4.2 |
| 4.4 | `VAL-02` | Claude, e o Codex na parte de ML | F1, matriz de confusão, curva de corrente × tempo medida | 4.2 |
| 4.5 | `DASH-04` | Codex | Noite completa no painel, com o `aviso` da inferência | `LGPD-03` (política) |
| 4.6 | `HW-04`, `CALC-05`, `HW-06` | Claude e autor | Encapsulamento, calor medido, fotos e montagem | `HW-02` |
| 4.7 | `HW-07` | — | Contingência: só se o `VIA-01` mostrar que o travesseiro não capta o corpo | 2.4 |
| 4.8 | **Integração e release R4** | Claude | | |

### Contínuo — texto do TCC (Claude e autor; não conflita com nenhuma trilha)

| Item | O que é | Quando |
|---|---|---|
| `DOC-17` | Os resultados do classificador nas inserções do Produto 5 | já, e de novo depois do `VAL-02` |
| `DOC-06b` | O autor lê as fontes; o Claude prepara o roteiro de leitura | já, até a banca |
| `CAL-03` | O que resta da autocalibração (o teste frio, com o autor) | quando o autor decidir |
| `APP-02` | Fechar a etapa que falta, com as noites do Moto | junto da 2.5 |

### Por último — o que não muda o trabalho

`CI-02` (linter) e `GIT-05` (ponteiros para arquivos que o clone não traz): Claude, quando as ondas 1–3
estiverem mescladas.

## 7. O que falta investigar (12/11, depois das PRs #146–#155)

Cada linha tem um item no backlog; esta tabela diz **o que precisa ser medido ou decidido**, quem
puxa e o que dispara a investigação. Ordem: o que bloqueia a primeira noite do travesseiro primeiro.

| # | Investigação | Item | Dono | Como | Gatilho |
|---|---|---|---|---|---|
| I-1 | A folga de heap no envio é de ~15 KB (mínimo 14 772 B no TLS). Aguenta uma noite? | `FW-14` | Claude + autor | O log do envio já imprime o mínimo; ler numa noite inteira. Abaixo de ~10 KB: uma conexão TLS por volta, não por lote | `VAL-01` |
| I-2 | A deriva do relógio ao longo de horas: −29 a −33 ppm em 41 min, e −123 ppm numa gravação de 10 min, que destoa | `FW-07` (c) | Claude + autor | A linha `[relogio]` de uma noite inteira; comparar a acumulada | `VAL-01` |
| I-3 | A partição da fila nasceu com lixo (1 279 corrompidos) e o CRC-16 pode aceitar um registro falso (~2 % por montagem) | `FW-15` | Claude | Ler a montagem; teste do host com lixo que passa no CRC; apagar a partição na primeira montagem ou ao gravar | antes de `VAL-01` |
| I-4 | A fila com o Wi-Fi desligado de propósito, e se o reenvio duplica linhas no banco | `FW-08` (c) | Claude + autor | Roteiro na bancada; consulta de duplicatas por `(device_id, captured_at)` no SQL Editor | bancada |
| I-5 | O I2C: pull-ups e 400 kHz | `HW-08` | Claude + autor | Multímetro e o `diagnostico-i2c` | bancada |
| I-6 | O tempo de envio de uma noite real com o backend em São Paulo | `INFRA-05`, depois `API-06` | Autor (consulta) + Claude | A consulta do lote depois da próxima noite com o celular | próxima noite |
| I-7 | O Histórico de 7 dias mostra no máximo 2 000 leituras | `UI-30` | Codex | Paginar a janela pelo cursor ou resumir as sessões no servidor | onda 1 |
| I-8 | O que o CI não vê: a compilação para o chip | `CI-12` | Claude | Job com `arduino-cli` e `scripts/compilar_sketch_esp32.py` | onda 2 |
| I-9 ✅ *(12/11: 804 leituras de teste apagadas pelo autor; ficaram as duas noites)* | As leituras de bancada de 12/11 na conta do autor (~150 épocas do travesseiro) e as 6 gravações de teste de 10/11 | `APP-11` | Autor (apagar) / Codex (marcar teste) | Decisão do autor | — |
| I-10 | Conferir em produção, depois do release R1, que o Histórico deixou de cortar em 1 000 e que a sessão da borda sai "Parcial" | `DATA-15`, `UI-26` | Claude + autor | Login real depois do R1 | release R1 |

**Ferramenta, fora do repositório:** o leitor da serial em PowerShell corta linhas quando a leitura
esgota o tempo, e a partida da placa sai com bytes trocados (o carregador fala a 74 880 baud). Não
afeta o firmware; pesa na leitura das gravações de bancada.

## 4. O que só o autor faz (L3), e o que cada decisão destrava

| Item | Decisão ou ação | Destrava |
|---|---|---|
| `LGPD-03` | Comitê de ética e termo para os testadores (o APK já foi a um amigo) | `APP-12`, `DASH-04` |
| `RQ-01` | Critérios do orientador: autonomia, aquecimento, a cadência C2 | `ARQ-01` (c), o texto |
| `ESC-01` | O que o trabalho pode chamar de "noite" | `DASH-04`, o texto |
| `HW-02` | Bateria e regulador (pode exigir compra); o VCC do GY-521 | `HW-04`, `HW-10`, `CALC-05`, `APP-14` |
| `LGPD-01` | Quem é o controlador dos dados | a política final |
| `AUTH-06` | SMTP próprio no Supabase | `LGPD-10` (o Codex implementa o aviso depois) |
| `INFRA-02` | Criar um projeto Supabase de teste | testes de login de ponta a ponta (o Claude liga ao CI) |
| `APP-12` | Distribuir aos testadores | depois do `LGPD-03` |
| `APP-11` | Apagar do histórico as 6 gravações de teste de 10/11 | — |

## 5. Regras para não haver desalinhamento

1. **Um item tem um dono por vez.** Trocar de dono passa pelo autor, e a PR antiga é fechada.
2. **Fora da trilha, não se mexe.** Se o Codex precisar mudar o firmware (ou o Claude, o frontend),
   o agente para e avisa o autor; o dono da área faz, ou libera por escrito na PR.
3. **Contrato de dados (`docs/DATA-CONTRACT.md`, `web-app/validacao.py`, `firmware/nucleo/payload.cpp`)
   tem dono por mudança:** quem abre a versão nova do contrato faz os três lados, ou combina antes
   qual PR vai primeiro.
4. **Migração só com número reservado** (seção 2), e aplicada na produção pelo autor, antes do merge do
   release que a usa.
5. **A PR chega sem conflito com `develop`** (regra 7 do `AGENTS.md`). Quando duas PRs da mesma
   onda tocam o diário, quem mescla depois resolve, e o Claude confere a contagem.
6. **Relato não é verificação.** O Claude reexecuta os testes e as sabotagens de toda PR do Codex
   antes de recomendar o merge; o Codex faz o mesmo se revisar algo do Claude.
7. **Nada de dado do autor no repositório:** capturas com dados reais, tokens, `secrets.h`, a chave
   de assinatura.

## 6. Como passar uma tarefa ao Codex

Mensagem-modelo (trocar o ID e a linha da tabela):

> Leia `AGENTS.md`, `docs/PLANO-CLAUDE-CODEX.md` e a linha do `<ID>` em `docs/BACKLOG-COMPLETO.md`.
> Você é o dono do `<ID>` (onda `<n>`, item `<n.m>`). Toque só os arquivos da sua trilha naquela onda.
> Apresente o plano antes de implementar. Entregue uma PR para `develop` com "Arquivos tocados",
> "Depende de" e "O que muda neste plano" no corpo. Não mescle.
