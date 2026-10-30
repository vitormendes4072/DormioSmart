# Pendências em aberto — Smart Dormio

> **Gerado por `scripts/consolidar_registro.py`.** Não edite à mão.
>
> **Conferido item a item contra o repositório em 2026-10-20**, na branch
> `chore/GIT-01-normalizar-fim-de-linha`, árvore limpa. O que a
> conferência mediu está no campo **Conferência** de cada item, e só
> aparece quando ela **discordou** do backlog ou acrescentou um número.
>
> **Em 2026-10-28** as discordâncias foram reconferidas e aplicadas ao
> backlog (`GIT-06`). Cada uma traz, no fim da nota, o que foi feito —
> inclusive as duas que **não** fecharam (`DIAG-01`, `DIAG-03`).

## Por que em documento próprio, e não no topo do backlog

Três razões, em ordem de peso.

**(1) O eixo é outro.** O `BACKLOG-COMPLETO.md` organiza por **camada de
dependência** (L0–L3) e responde *'o que trava o quê?'*. Este arquivo
organiza por **natureza do desbloqueio** e responde *'o que eu faço, e o
que só sai se outra pessoa agir?'*. São perguntas diferentes, e as
respostas não se mapeiam uma na outra: o `ARQ-01` é um item de camada L0
cujas partes (a) e (b) são software e cuja parte (c) é bancada; o
`PERFIL-02` é L0 na tabela e L3 no título. Pôr as duas taxonomias no
mesmo arquivo cria **duas ordenações dos mesmos itens no mesmo lugar**, e
a que estiver no topo passa a parecer a que vale.

**(2) O projeto já pagou por afirmação duplicada que divergiu.** É a
regra 7 do §1 das lições — *verificação não recompõe o que ela verifica* —
e a assimetria de `serieMisturaInstrumentos`, em que o comentário e a
implementação tinham alcances diferentes. Uma seção no topo do backlog
seria uma segunda cópia do estado de cada item, mantida à mão,
ao lado da primeira. **A cópia divergiria, e a de cima é a que se lê.**

**(3) Este arquivo é gerado e conferível; uma seção não seria.** A
contagem por grupo sai de um `Counter`, e o `--conferir` reprova se o
arquivo em disco divergir dos dados. Uma seção escrita à mão no backlog
não tem como ficar vermelha — que é exatamente a ocorrência 5 do §6 das
lições (*o verde era um `✅` num arquivo de texto*).

**O que a separação custa, e como está pago.** O risco é o §2 — *análise
correta que não chega onde a decisão é tomada*. Mitigado com uma linha no
`BACKLOG-COMPLETO.md`, logo abaixo da contagem, apontando para cá. Uma
linha, não um resumo: resumo é a cópia que diverge.

---

## Contagem

| Grupo | Itens |
|---|---:|
| A — Depende só de software: dá para fazer a qualquer momento | **35** |
| B — Depende de decisão do Vitor | **10** |
| C — Depende de ação do Vitor que não é decisão | **8** |
| D — Bloqueado por hardware ou coleta | **24** |
| E — Bloqueado por terceiro | **4** |
| **Total** | **81** |

⚠️ **Este total não é comparável à contagem do backlog, e a diferença não é
erro de nenhum dos dois.** São unidades de contagem diferentes: o backlog
conta **itens**, e aqui alguns itens aparecem **partidos**, porque suas
partes dependem de coisas diferentes e juntá-las esconde o que trava o
quê. Os partidos são `ARQ-01` (a,b software · a-escolha decisão · c
bancada), `LGPD-01` (a decisão · b software · c terceiro), `LGPD-02`
(prazo decisão · implementação software), `FW-08` (escolhas decisão ·
implementação software), `UI-19` (ferramenta decisão · classe software),
`CI-02` (configuração decisão · execução software), `DATA-07b`,
`DATA-06`, `ML-09` e `ML-10`. E entraram **três itens que o backlog não
tinha em 20/10**: o push, o projeto Supabase de teste e a decisão de
escopo do 'conceito de noite' — os três eram parágrafo solto dentro de
outro item. **Desde 28/10 têm ID no backlog:** `GIT-07`, `INFRA-02` e
`ESC-01`.

---

## A — Depende só de software: dá para fazer a qualquer momento

**35 itens.**

### `CALC-01` 🔴

Modelo de energia/autonomia: corrente por estado, duty cycle, autonomia. É predição; a medição é o `VAL-02`.

*Camada no backlog: L0.*

### `CALC-02` 🔴

Física do acelerômetro: força específica, resolução, ruído, Nyquist — e por que 21 Hz e não 260 Hz.

*Camada no backlog: L0.*

### `CALC-03` 🔴

Índice de atividade e a derivação do limiar. Já **recortado** em 29/09: a seção demonstra por que `g ± k·σ` não produz número útil (k = 67). O que resta é a redação do índice por época.

*Camada no backlog: L0.*

**Conferência.** O backlog ainda diz 'boa parte já está resolvida pelo `ML-01`' e 'o item virou transpor, não decidir' — frase que o próprio `CALC-03` de 29/09 desmentiu. O texto do item não foi atualizado depois do achado dos 67 σ. ✏️ **28/10:** riscada no backlog.

### `CALC-04` 🟡

Análise elétrica: pull-down, pull-ups do I2C, níveis 3,3 V, fonte de despertar.

*Camada no backlog: L0.*

### `DIAG-02` 🟡

Esquemático do circuito; v1 (1 sensor) e v2 (2, endereços I2C).

*Camada no backlog: L0.*

**Conferência.** Confirmado aberto: não há `DIAG-02-*.md` em `docs/diagramas/`.

### `DIAG-04` 🟡

Sequência do fluxo autenticado + modelo ER. Escrito e revisado em 17/10. **Falta só uma coisa:** os três blocos mermaid foram validados por **parser**, nunca por **renderização** — ninguém olhou as figuras.

*Camada no backlog: L0.*

### `DOC-05` 🟡

READMEs e `CLAUDE.md`. Falta só o `DIAG-04`. O `CLAUDE.md` é versionado desde 27/10 (`DOC-11`).

*Camada no backlog: L0.*

### `DOC-06b` 🔴

**Ler os artigos antes de citá-los** (referência conferida ≠ artigo lido) e converter para o padrão de citação do TCC.

*Camada no backlog: L0.*

### `DOC-09` 🟡

Diário de engenharia — registro corrente. O intervalo de junho a agosto segue esparso, porque o `HISTORICO.md` que o cobre não é versionado e não pode servir de procedência.

*Camada no backlog: L0.*

### `LGPD-01` 🟡

Política de privacidade e termos. Rascunho escrito. Faltam **(b)** a rota e a página que sirvam o texto — isto é software puro. **(a)** controlador e base legal e **(c)** revisão jurídica estão nos grupos B e E.

*Camada no backlog: L0.*

**Conferência.** O item estava inteiro em L0; a conferência o divide, porque as três partes dependem de coisas diferentes.

### `LGPD-02` 🟡

Não existe política de retenção: nenhum expurgo, nenhum prazo. Implementar um prazo, ou declarar formalmente que não haverá.

*Camada no backlog: L0 e L2.*

**Conferência.** ⚠️ **Item listado duas vezes no backlog**, em camadas diferentes: na seção de documentação como L0 🟡, e na seção L2 como ⚪ 'bloqueante da distribuição, não do desenvolvimento'. É um item, e a contagem de 76 só fecha se ele for contado uma vez. A **decisão** do prazo está no grupo B. ✏️ **28/10:** **a contagem não fechava**: a recontagem linha a linha mostrou que ele **estava** contado duas vezes. A linha de L2 virou ponteiro, e o bloqueio de distribuição foi para a de L0.

### `REQ-01` 🟡

Documentar requisitos: dimensões, conforto, autonomia, aquecimento, custo, segurança.

*Camada no backlog: L0.*

### `ML-06b` 🟡

Escrever `ml/src/carregar/walch.py`. A interface única garante que é só isso. ⚠️ Escrever carregador sem ver o arquivo real produziu as 10 armadilhas já catalogadas: escreva, mas **não confie até rodar**.

*Camada no backlog: L0.*

**Conferência.** Confirmado aberto: `ml/src/carregar/` tem `base.py`, `newcastle.py`, `sintetico.py` e `wearanize.py`. Não há `walch.py`.

### `ML-08` ⚪

Combinação item 9 + HMM com LOSO interno (N=92). **Provavelmente esforço mal gasto** — a validação externa já mostrou que o ganho do HMM não atravessa coorte. Registrado para não parecer esquecimento.

*Camada no backlog: L0.*

### `DATA-07e` 🔴

Quantizar os 5 floats de pico: 52 B → 40 B, e a cobertura de 5,25 h → 6,83 h em 32 KiB. Dívida assumida de propósito, porque mexe na precisão **transmitida** e na checagem de coerência da §5.1 do contrato. Esquema já desenhado, com custo medido em κ (u16 custa Δκ ≈ 1e−4).

*Camada no backlog: L0.*

### `FW-08` 🔴

Flash como registro durável, RAM como cache de escrita. Decidido e dimensionado desde 29/09: 1,5 MiB, 39 321 épocas = **13,7 dias** sem degradar uma vez, desgaste de 3 741 anos, energia em centésimos de por cento. **Decidir (a)** LittleFS ou NVS e **(b) versionar `partitions.csv`**. ⚠️ Depende do `ARQ-01`: o estudo assume o heap de ~300 KiB, que só existe na arquitetura contínua.

*Camada no backlog: L0.*

### `DATA-06` 🔴

O limiar viaja com a leitura. **A coluna e o campo dão para criar já**; o *valor* do limiar do celular depende do `VIA-02` (grupo D).

*Camada no backlog: L0.*

**Conferência.** Confirmado aberto: `grep` por `limiar` em `web-app/migrations/*.sql` devolve vazio.

### `SEC-08 (declaração)` 🟠

Decidido em 20/10 — saída (B′). O que resta é **declaração**, e a seção X.7 de `LIMITACOES-TCC.md` já foi escrita. ⚠️ Obrigação de reconferir na semana da entrega: **se as issues #35844 e #2702 forem corrigidas antes, a seção passa a afirmar falha que não existe.**

*Camada no backlog: L0.*

**Conferência.** Marcado ✅ DECIDIDO no backlog **e contado como aberto** na soma de 76. Defensável — há resíduo declarado —, mas o `✅` é exatamente o que o §6 das lições adverte.

### `SEC-09` 🟡

Dois canais de enumeração fora do cadastro (`email_exists` na troca de e-mail; `recuperarSenha`). **Declarado, não corrigível daqui** — os comentários falsos do código já foram corrigidos; o oráculo está na resposta do Supabase.

*Camada no backlog: L0.*

### `SEC-10` 🟠

Pré-sequestro por retenção de credencial. **Não explorável na configuração atual** (com a confirmação desligada não existe estado 'não confirmado' para ocupar): é **pré-condição** de qualquer adoção futura da saída (A), não pendência corrente.

*Camada no backlog: L0.*

**Conferência.** Item de maior severidade declarada do projeto e evidência mais fraca — dois relatos de comunidade, nada medido. A classificação é da **classe**, não da confirmação.

### `LGPD-06` ⚪

Se a idade for usar em cálculo, é finalidade nova e precisa de declaração nova **antes**. Hoje ela decide um texto e não entra em conta nenhuma. ⚠️ Ordem obrigatória: política primeiro, código depois.

*Camada no backlog: L0.*

### `UI-18` 🟡

Duas partes, não três: **(a)** asserção nomeada por rota — hoje só `/configuracoes` tem, e por isso a varredura cobre rota nova mas **não rota removida**; **(b)** as três afirmações condicionais de honestidade científica (`AvisoDeLacuna`, `NotaDeInferencia`, `NotaDeEscopo`), uma asserção por condição com o par negativo de cada.

*Camada no backlog: L0.*

**Conferência.** ⚠️ **A parte (c) do item é falsa e caiu nesta conferência.** Ela afirma que 'o `montagem.test.ts` não está em nenhum job do `ci.yml` — e nem o `vitest` está: os jobs são `documentos`, `rls` e os do firmware'. O `ci.yml` tem **seis** jobs, e o `frontend` roda `npm test` → `vitest run` desde o commit `01a7faa` (19/08), dois meses antes de a afirmação ser escrita. Medido aqui: `npx vitest run` coleta **418 testes em 27 arquivos**, incluindo `src/montagem.test.ts` (16 testes). O que é verdade é mais estreito e já é o `CI-06`: nenhum job rodou em runner desde 10/09, e o `montagem.test.ts` é posterior a essa data. ✏️ **Esta nota ficou oito dias num arquivo sem commit**, e a parte (c) só foi riscada do backlog em 27/10, por quem a redescobriu do zero sem saber desta.

### `UI-19 (classe)` 🟡

As duas instâncias fecharam em 20/10; **a classe não.** Não há verificação de alcance no nível do **símbolo** — export que ninguém importa, dentro de arquivo que está no grafo, passa pelo `alcance.test.ts` (arquivo) e pelo `montagem.test.ts` (render). Ferramenta pronta (`knip`, `ts-prune`) ou script próprio **com controle positivo**, porque o instrumento é a parte difícil e isso já foi medido.

*Camada no backlog: L0.*

### `FW-07` 🔴

Parte (b): reescrever o `sketch.ino`, que hoje tira **uma amostra por boot** e dorme, em torno da cadeia C2 que a parte (a) deixou pronta e testada no núcleo (30/10: `fifo_mpu.h`, `reamostragem.h`, `cadeia_c2.h`, `lote.h`). Falta a cola com o hardware: ESP32 em **sono leve**, os registradores da C2, a FIFO lida por I2C em blocos, o despertar com intervalo variado, buffer no heap e na flash (`FW-08`) e drenagem pelo `POST /api/data/lote`. Sem a placa ela só compila; e um POST que bloqueie mais de ~1,7 s deixa a FIFO transbordar.

*Camada no backlog: L0.*

### `FW-01` 🟡

Lógica atividade/repouso por época no firmware. **Parcialmente coberto:** o `envio-continuo` já classifica por época de 30 s desde o `HW-05`; falta levar ao `sketch.ino` (`FW-07`).

*Camada no backlog: L0.*

### `FW-03` 🟡

Empacotamento do dado conforme `DATA-01`.

*Camada no backlog: L0.*

### `HW-01` 🟡

Revisar o BOM: o que é andaime (botão, pull-down de 10 kΩ) e o que é produto. É análise, não montagem.

*Camada no backlog: L0.*

### `APP-03` 🟡

Armazenamento seguro do token. *Reavaliar: com o `APP-08`, o token pode deixar de existir no celular.*

*Camada no backlog: L0.*

### `APP-02` ⚪

Android nativo com foreground service. Fazível hoje; **caro e pós-banca**.

*Camada no backlog: L0.*

### `UI-15` ⚪

Bundle num único chunk; o Vite avisa a cada build. Code splitting por rota resolve.

*Camada no backlog: L0.*

**Conferência.** Confirmado aberto: `vite.config.ts` não tem `manualChunks` nem `rollupOptions`.

### `UI-20` ⚪

Aplicar a linguagem de blueprint também no app autenticado (hoje vive só na landing).

*Camada no backlog: L0.*

**Conferência.** ⚠️ **Item sem ID**, listado com '—' no backlog. Entra na contagem de 46 para a soma fechar, e um item sem ID não dá para citar, fechar nem rastrear. ✏️ **28/10:** ganhou o ID `UI-20`.

### `GIT-05` 🟡

Reduzir a lista de **8 ponteiros pendurados** — arquivo por arquivo: versionar, ou parar de citar. O `ROADMAP.md` é o primeiro a decidir (8 arquivos rastreados o citam). Só o `HISTORICO.md` é ponteiro legítimo.

*Camada no backlog: L0.*

**Conferência.** Confirmado por execução: `conferir_docs_versionados.py` sai 0 e imprime os 8 isentos. A verificação (3) **não cobre nenhum dos oito; pega o nono.**

### `DOC-13` ⚪

Nada confere o resumo, o quadro e o caminho crítico do backlog contra as linhas dos itens; em 29/10 eles citavam seis itens fechados como pendentes. Uma conferência que reprove ID fechado citado ali.

*Camada no backlog: L0.*

### `SEC-13` 🟡

A suíte de RLS reaplica os GRANTs das tabelas depois de todas as migrações, o que desfaz qualquer `revoke` que uma delas faça. Separar o arquivo das sabotagens do de GRANTs, e rodar estes logo depois da 001.

*Camada no backlog: L0.*

### `CI-02` ⚪

O CI **não roda linter** — não há ESLint nem Ruff/flake8. Pressupõe uma decisão de configuração que ninguém tomou, porque ligar linter sem configuração produz um job vermelho permanente.

*Camada no backlog: L0.*

**Conferência.** Confirmado aberto: não há `.eslintrc*`, `eslint.config.*`, `ruff.toml` nem `setup.cfg` em lugar nenhum do repositório. A **decisão** de configuração está no grupo B.

---

## B — Depende de decisão do Vitor

**10 itens.**

Cada linha traz a decisão em uma frase. Nenhum destes itens anda
sem uma resposta sua — e nenhum deles exige que você escreva
código para responder.

### `LGPD-01 (a)` 🟡

Controlador e base legal da política de privacidade.

**A decisão.** O controlador é você pessoa física ou a instituição de ensino? E a base legal é consentimento (art. 7º, I) ou pesquisa (art. 7º, IV)? Muda a política inteira e **não dá para inferir do repositório.**

*Camada no backlog: L0.*

### `LGPD-02 (prazo)` 🟡

Política de retenção.

**A decisão.** Qual o prazo de retenção, ou se vai declarar formalmente que não haverá expurgo. **As duas saídas são defensáveis; o silêncio não.**

*Camada no backlog: L0.*

### `LGPD-05` 🟡

Idade autodeclarada pode revelar que o titular é criança ou adolescente, e o art. 14 impõe tratamento próprio. Hoje o sistema não verifica e não trata diferente.

**A decisão.** (a) restringir o cadastro a maiores de 18, (b) implementar o fluxo de consentimento de responsável, ou (c) manter a lacuna declarada. **A defesa de (c) expira no dia em que alguém além de você criar conta.**

*Camada no backlog: L0.*

### `ARQ-02 — modos de registro` ⚪

Quatro modos analisados em `docs/ARQUITETURA-DE-CAPTACAO.md`: travesseiro com bateria máxima (WoM), travesseiro com análise completa (sono leve + FIFO), celular para teste rápido (navegador) e celular para a noite inteira (app nativo).

**A decisão.** Quais modos oferecer, e se o travesseiro terá um ou dois? A análise recomenda um modo só no travesseiro antes da banca.

*Camada no backlog: L0.*

### `FW-08 (a, b) — as escolhas` 🔴

Persistência em flash.

**A decisão.** LittleFS ou NVS? E versionar o `partitions.csv` — hoje o esquema é o padrão implícito da IDE, e se a flash vira armazenamento de dado de pesquisa o layout dela é parte do projeto, não escolha de ferramenta.

*Camada no backlog: L0.*

### `UI-19 (ferramenta)` 🟡

Verificação de alcance no nível do símbolo.

**A decisão.** Ferramenta pronta (`knip` / `ts-prune`, mais uma dependência) ou script próprio (mais código nosso, e o instrumento é a parte difícil — a primeira tentativa sub-relatou código morto)?

*Camada no backlog: L0.*

### `CI-02 (configuração)` ⚪

Linter.

**A decisão.** Qual configuração de ESLint/Ruff adotar, e quantos achados de estilo você aceita corrigir de uma vez — porque ligar sem decidir isso produz um job vermelho permanente, que é como se aprende a ignorar o CI.

*Camada no backlog: L0.*

### `HW-02` 🟡

Energia: LiPo + TP4056, e se o DevKit V1 fica ou sai. O DevKit **não atinge µA** — regulador e USB-serial dominam o consumo.

**A decisão.** O DevKit V1 fica (e a autonomia do trabalho é a dele) ou sai (e há compra)? **Pode exigir compra.**

*Camada no backlog: L3.*

### `ESC-01 — 'o conceito de noite'` 🔴

A decisão de escopo que atravessa o trabalho inteiro.

**A decisão.** O trabalho pode afirmar *'a noite de 27/08'* sem afirmar que o dado é sono? Hoje o painel diz 'sessão de captação', que é o teto honesto. É sua **e do orientador**.

*Camada no backlog: L3.*

**Conferência.** Está num parágrafo solto do backlog, não numa linha de item — é a maior decisão em aberto sem ID próprio. ✏️ **28/10:** virou o item `ESC-01`.

### `APP-04` ⚪

iOS: **investigação, não implementação.** Rota A (áudio em background) muda o escopo declarado e a conversa de LGPD; rota B (`CMSensorRecorder`) é coerente e **não verificada**.

**A decisão.** Vale gastar a investigação antes da banca, sabendo que a rota A muda o escopo declarado do trabalho?

*Camada no backlog: L0.*

---

## C — Depende de ação do Vitor que não é decisão

**8 itens.**

Nada aqui é decisão: a decisão já foi tomada, ou nunca houve uma.
São ações que só você pode executar, porque exigem credencial,
terminal na máquina, ferro de solda ou uma conta num serviço.

### `Etapa 0 — soldar` 🔴

**Soldar os 8 pinos do MPU6050.** Teste de aceitação: pose Z+ com ruído ~0,02. **Trava as camadas L1 e L2 inteiras.**

*Camada no backlog: L3.*

**Conferência.** O contato por jumper produziu, em 25/08, registradores zerados, `‖a‖ = 56,5 m/s²` com a placa parada, `−11,6 °C` e ruído 30× o normal. O viés de Z, `−1,06 m/s²`, é **89% do limiar de movimento inteiro.**

### `SEC-11` ⚠️

Ligar captcha no painel do Supabase (`Authentication → Settings → Bot and Abuse Protection`). ~5 min, zero código, cobre `signup`/`token`/`recover`. ⚠️ **É mitigação: reduz a taxa, não elimina o oráculo** — e ligar isto **não autoriza mudar uma palavra da X.7**.

*Camada no backlog: L3.*

### `DATA-07f` 🔴

Aplicar `web-app/migrations/010_vetor_de_caracteristicas.sql` no SQL Editor da produção **antes** do release do backend da v2.7.0, e conferir com o diagnóstico (a linha da 010 com as quatro marcas `true`). Na ordem inversa, `f` validado seria descartado pela função antiga, com `201`.

*Camada no backlog: L3.*

**Conferência.** A 010 não quebra o backend de hoje: a gravação sem vetor foi medida contra Postgres 16 com as dez colunas nulas.

### `INFRA-03 — monitor da produção` 🟡

O job que chama o `/health` de produção a cada 3 dias está em `main` desde o release de 29/10, e a execução manual passou. Falta a primeira execução **agendada** (pelo cron, 31/10) — é ela que fecha o item.

*Camada no backlog: L3.*

**Conferência.** A produção esteve fora do ar até 28/10 sem ninguém saber: o projeto Supabase do plano gratuito pausa depois de uma semana sem uso. Reativado pelo Vitor no mesmo dia.

### `INFRA-02 — projeto Supabase de teste` 🔴

Criar um projeto Supabase de teste e rodar um punhado de `curl`. **Fecharia quatro itens de uma vez:** o ponto cego do `UI-11` (a troca de e-mail exige confirmação? `updateUser({data:{nome:null}})` apaga a chave?), o canal 2 do `SEC-08` (`identities`), o canal 4 / `SEC-09` (`/recover` em domínio real) e o `SEC-10` inteiro.

*Camada no backlog: L3.*

**Conferência.** ⚠️ **Não tem item próprio**, e o diário de 20/10 (iii) registra isso textualmente: 'quatro itens esperando o mesmo objeto, e ele não tem item'. É a terceira sessão seguida em que o instrumento que falta é o mesmo. **Candidato número 1 a item novo.** ✏️ **28/10:** virou o item `INFRA-02`.

### `GIT-03` ⚪

Apagar o resíduo de sandbox no `.git`. Nada quebra enquanto ficar: `git fsck` dá exit 0 e os commits funcionam. **Exige um terminal na máquina.**

*Camada no backlog: L0.*

**Conferência.** ⚠️ **Número do backlog defasado.** Ele diz '`.git/_lixo_sandbox/` (57 itens, 240 KB)' e '`.git/_locks_orfaos/` (vazia)'. Medido agora: `_lixo_sandbox/` tem **148 itens** e `_locks_orfaos/` tem **9**. O item não mudou de natureza; o número citado como medido envelheceu — é o §3 das lições no próprio backlog. ✏️ **28/10:** medido de novo (148 itens, 330 KB; 9) e corrigido no backlog.

### `ML-06a` 🟡

Baixar o Walch et al. 2019 (PhysioNet `sleep-accel`, 31 sujeitos). **Não é alcançável do ambiente de execução** — precisa ser baixado da sua máquina. Sem ela, a degradação entre coortes é **estimativa pontual, não medida de variabilidade**.

*Camada no backlog: L3.*

### `AUTH-06` ⚪

SMTP próprio (Resend/Brevo) para 'esqueci minha senha'. Exige criar conta em serviço externo.

*Camada no backlog: L3.*

---

## D — Bloqueado por hardware ou coleta

**24 itens.**

### `ML-12 (c)` 🟡

Repetir a comparação 8 × 3 features com dado do travesseiro, quando o `VIA-01`/`VIA-02` o produzirem. As partes (a) e (b) fecharam em 30/10: no kappa a redução sobrevive; na especificidade custa de 1 a 5 pontos, e a recomendação é manter as 6 no dispositivo.

*Camada no backlog: L1.*

### `CAL-01` 🔴

Caracterização de 6 posições. Sketch pronto. Produz viés e escala por eixo desta unidade.

*Camada no backlog: L1.*

### `CAL-02` 🔴

**Repetir** a caracterização depois do `FW-06`. O filtro passou de 260 Hz para 21 Hz, o que muda o ruído de base — e o limiar é definido sobre esse ruído. **Número medido antes disso não transfere.**

*Camada no backlog: L1.*

### `VIA-01` 🔴

Viabilidade de bancada: 2 min parado → 2 min mexendo a cabeça → 2 min virando o corpo. *Os três blocos se separam?*

*Camada no backlog: L1.*

### `VIA-02` 🔴

O mesmo protocolo com **celular e travesseiro gravando ao mesmo tempo**. Produz o limiar do celular (`DATA-06`), a diferença de acoplamento medida e o grupo de controle.

*Camada no backlog: L1.*

### `ARQ-01 (c)` 🔴

**Medir na placa**: os 18,8 KiB do acumulador, os ~29 000 MACs em `double` por época e o tempo de parede do fechamento são `sizeof` e aritmética no host. Se a escolha for o sono leve com FIFO: a latência e a corrente do sono leve na placa, o transbordo da FIFO (esvaziada a cada 1,70 s a 50 Hz), a taxa real do MPU e a reassociação Wi-Fi (§8 do documento do `ARQ-01`). **O `ARQ-01` só fecha com (c).**

*Camada no backlog: L1.*

### `FW-05` 🔴

Amostragem bruta para o ML, na arquitetura decidida no `ARQ-01` (C2, 30/10): MPU a 50 Hz pela FIFO, DLPF de 21 Hz, ESP32 em sono leve, taxa medida e reamostragem para 32 Hz como o `ml/`. O lado C++ das features já existe e passa.

*Camada no backlog: L1.*

### `FW-02` 🟡

Deep Sleep real testado na placa (hoje é mock do Wokwi).

*Camada no backlog: L1.*

### `FW-04` 🟡

Portar o firmware para a placa sem dependências do Wokwi.

*Camada no backlog: L1.*

### `HW-03` 🟡

Wake-on-Motion real: ligar o INT do MPU6050 a um GPIO RTC. Hoje o despertar é por EXT1 num **botão** — andaime de simulação. ⚠️ **30/10: deixou de ser pré-requisito** — com a C2 (`ARQ-01`) o ESP32 acorda por temporizador; o INT vira opcional (alarme de transbordo da FIFO).

*Camada no backlog: L1.*

### `HW-04` 🔴

Encapsulamento e fixação para uso noturno; **segurança térmica do LiPo dentro do travesseiro**.

*Camada no backlog: L1.*

### `HW-06` 🟡

Entregáveis físicos: esquema de ligação, diagrama de montagem, fotos.

*Camada no backlog: L1.*

**Conferência.** Confirmado: `hardware/` está **vazio**.

### `CALC-05` 🟡

Análise térmica com **medição real** — `P = V·I`, elevação de temperatura, limites do LiPo.

*Camada no backlog: L1.*

### `VAL-01` 🔴

Uma noite captada. 🛑 **Com o firmware como está, a noite sai sem feature nenhuma e o modelo não a consome** — cadência de 0,1 Hz (3 amostras por época) e o acumulador recusa a época. O transporte do vetor existe desde 30/10 (`DATA-07b`); o que falta é firmware: `FW-05`, `FW-07` (b) e `FW-08` → **só então** captar.

*Camada no backlog: L1.*

**Conferência.** Confirmado: `INTERVALO_AMOSTRA_MS = 10000` em `envio-continuo.ino:109`. O `montar_payload` emite `f`/`g`/`fs` desde o `DATA-07b`, mas nenhum sketch o chama com o vetor.

### `VAL-02` 🔴

Validação quantitativa: F1, matriz de confusão, curva de corrente×tempo medida.

*Camada no backlog: L2.*

### `DASH-04` 🔴

Visualização de **noite completa**: linha do tempo e lacunas como indicador de repouso. O gráfico já está preparado; falta o dado.

*Camada no backlog: L2.*

### `ML-09 (calibração)` 🟡

Calibração do modelo para o Dormio com dado próprio. **Ajuste de limiar, não re-treino** — n=1 não treina nada.

*Camada no backlog: L2.*

**Conferência.** ⚠️ **Colisão de ID:** `ML-04` também é o item de validação externa, **fechado em 18/09**. Dois itens com o mesmo ID, um fechado e um aberto, nas seções 'Concluído' e L2. O mesmo vale para `ML-05`. ✏️ **28/10:** o aberto virou `ML-09`; os documentos de plano, que numeram assim, ganharam a correspondência ao lado.

### `ML-10 (devolução)` 🟡

O que o modelo devolve ao usuário — e o que **não** devolver. **A especificidade externa de 0,507 é o que o produto deve assumir, não os 0,802 internos.**

*Camada no backlog: L2.*

**Conferência.** ⚠️ Mesma colisão de ID do `ML-04`: `ML-05` fechado é o teto interavaliador (28/09). ✏️ **28/10:** virou `ML-10`.

### `ML-INF` 🟡

Onde a inferência roda. Proposta: job em lote no backend Python ao fim de uma sessão, **não no ESP32**.

*Camada no backlog: L2.*

### `HW-07` 🟡

Arquitetura v2 — fusão de 2 acelerômetros, **se o `VIA-01` mostrar** que o travesseiro subcapta movimento de corpo. Gatilho, não plano. **Implica rever a redação da RQ.**

*Camada no backlog: L2.*

### `APP-09` 🟡

Continuidade quando o usuário troca celular por sensor. Instrumentos diferentes, limiares diferentes (`DATA-06`).

*Camada no backlog: L2.*

### `UI-14` ⚪

Lista de espera na landing. 🔒 Gatilho: protótipo funcionando **e** `VIA-01`. Não fazer antes.

*Camada no backlog: L2.*

### `APP-05` ⚪

Distribuição (loja ou APK). Depende de `LGPD-02` e `APP-04`.

*Camada no backlog: L2.*

### `PWA-01` 🟡

**Exercitar a instalação de verdade.** O service worker não registra em desenvolvimento, então 'Adicionar à tela inicial' só aparece em produção — e ninguém testou. O comportamento do iOS com `display: standalone` também não foi verificado.

*Camada no backlog: L3.*

**Conferência.** ⚠️ **Reclassificado.** O backlog o põe em L0, e ele não é software que dá para fazer hoje: exige um dispositivo e um deploy de produção para exercitar. `public/sw.js` e `lib/instalacao.ts` existem; o que falta é o teste em aparelho. ✏️ **28/10:** movido para a seção L3 do backlog.

---

## E — Bloqueado por terceiro

**4 itens.**

### `RQ-01` 🔴

Confirmar RQ e hipótese com o **orientador metodológico**.

*Camada no backlog: L3.*

### `LGPD-03` 🔴

**O ML eleva a aposta.** Um modelo que infere sono sobre pessoa identificada muda a natureza do tratamento: passa a haver *inferência* sobre saúde, não só registro de movimento. Termo de consentimento e, se houver voluntários no `VIA-02`, **comitê de ética**. Agora é concreto, não hipotético — o modelo existe.

*Camada no backlog: L3.*

### `LGPD-01 (c)` 🟡

Revisão jurídica da política de privacidade.

*Camada no backlog: L0.*

### `SEC-09 / X.7 — issues de terceiro` 🟡

A seção X.7 depende de **duas issues em aberto** (`supabase/supabase` #35844 e `supabase/auth` #2702). **Se forem corrigidas antes da entrega, a seção passa a afirmar falha que não existe** — espelho exato do `DOC-11`. Reconferir na semana da entrega e registrar a data de consulta.

*Camada no backlog: L0.*

### `DUA do Wearanize+ restrito` ⚪ — ⛔ **não é pendência, fora da contagem**

**Não está no caminho crítico, e isto é o que mudou de verdade no projeto.** A coleção aberta `Wearanize+ OA` tem tudo que o experimento precisa, sem cadastro. O DUA destrava só os questionários, e exige assinatura que **não é só sua**. Guia completo em `docs/WEARANIZE-ACESSO.md`.

*Camada no backlog: (fechado).*

**Conferência.** Entra na lista **porque o enunciado pediu os bloqueios de terceiro**, e porque é o bloqueio de terceiro mais citado na história do projeto. Hoje é caminho alternativo documentado, **não pendência** — e por isso fica fora da contagem.

---

## O que a conferência não conseguiu verificar

Separado de propósito, porque *'não verificado'* e *'verificado e aberto'*
não são a mesma informação — é a distinção que o `LIMITACOES-TCC.md` faz
sobre a segunda coorte externa.

| O que | Por quê |
|---|---|
| **Se o `DATA-03` e o `PERFIL-02` já rodaram no Supabase** | Exige acesso ao projeto. Os dois arquivos `.sql` estão em disco e mergeados; **se foram aplicados em produção não é observável daqui.** Os dois seguem listados como abertos porque é o que o backlog afirma, e isso é repetir status não conferido — está dito para que você possa fechá-los em dez segundos se já tiverem rodado. |
| **A suíte de RLS** | Exige Postgres de verdade, e este ambiente não tem `apt-get` nem root. Contado estaticamente: **125 funções de teste** em 6 arquivos, com 11 `parametrize`. ✏️ **A 'divergência' 146 × 149 que esta linha registrava foi resolvida em 28/10, e não era divergência:** contando a coleta em cada commit, são **146** em `778ec27` e `73c213f` (17/10) e **149** desde `275665a` (19/10), que acrescentou 3 testes. Os dois documentos estavam certos para as suas datas. |
| **O `vite build`** | `EPERM` ao esvaziar `frontend/dist/` neste ambiente — o sandbox não desvincula arquivo na pasta montada, mesma limitação do `GIT-03`. O `tsc --noEmit` roda e sai **limpo**. |
| **Qualquer número de hardware** | Os 8 pinos não estão soldados. |

## O que a conferência mediu e confirmou

Executado em **2026-10-20**, na branch `chore/GIT-01-normalizar-fim-de-linha`,
árvore limpa. **É fotografia daquela data**, não estado corrente — os
números atuais estão na seção "Testes" do `CLAUDE.md`:

| Camada | Medido | Bate com o registro? |
|---|---|---|
| Núcleo C++ (`make`) | **341 verificações, 0 falhas** | sim |
| Paridade do dourado (`make dourado`) | **157 verificações, 0 falhas** | sim |
| Sketches (`make sintaxe`) | **4/4 compilam** | sim |
| `ml/` (`pytest testes`) | **107 passam** | sim — e é exatamente o piso da guarda do `CI-04` |
| Backend (`pytest --ignore=tests/rls`) | **293 passam** | sim |
| Frontend (`vitest run`) | **418 testes em 27 arquivos** | sim |
| `tsc --noEmit` | limpo | sim |
| `conferir_docs_versionados.py` | **exit 0**, 8 ponteiros isentos | sim |
| Commits sem push | **76** contra `origin/main` **e** `origin/develop` | **não** — o backlog diz 6 |
| Jobs no `ci.yml` | **6** (`test`, `rls`, `frontend`, `ml`, `firmware`, `documentos`) contra **2** em `develop` | sim — os quatro do `CI-06` |
| `.git/_lixo_sandbox/` | **148 itens**; `_locks_orfaos/` **9** | **não** — o backlog diz 57 e 'vazia' |

