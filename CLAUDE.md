# DormioSmart — Instruções para Claude

> **Versionado desde 2026-10-27** (`DOC-11`/`GIT-05`). Até então era gitignorado, e nenhuma
> correção nele chegava a um clone ou a uma verificação — a de 17/10 envelheceu em dez dias sem
> que nada notasse. O que é pessoal (mídia, devlog, caminhos da máquina) está em
> `CLAUDE.local.md`, que **não** é versionado. **Repositório público:** nada que entre aqui pode
> conter segredo, nome de pessoa ou caminho de máquina.

## Contexto do projeto

DormioSmart (SmartDormio) é um **dispositivo embarcado de baixo consumo para monitoramento não invasivo do sono, instalado dentro de um travesseiro**, desenvolvido como Trabalho de Conclusão de Curso por dois autores. O ESP32 + MPU6050 capta o movimento durante o repouso (sem contato com o corpo) em **sono leve, lendo em rajadas a memória interna (FIFO) do sensor a 50 Hz** — arquitetura decidida em 2026-10-30 (`ARQ-01`, `docs/DECISAO-ARQ-01-CADENCIA.md`; até ali o desenho era Deep Sleep com Wake-on-Motion, que não alimenta as features do modelo); os dados vão para uma aplicação web que os armazena e apresenta. O escopo é deliberadamente modesto: registrar indícios de movimento ancorados em actigrafia, **sem** prometer estadiamento de sono nem diagnóstico clínico. Detecção de áudio/ronco é expansão futura, não requisito do MVP.

O projeto tem **duas fases**: Fase 1 = simulação no Wokwi (suficiente para a primeira entrega); Fase 2 = **dispositivo físico real funcionando**, que é o entregável que importa para a defesa. Detalhes de hardware, BOM e fases em `docs/HARDWARE.md`.

Como é um TCC, decisões precisam de validade científica. A pergunta de pesquisa, a estratégia de validação, o uso de dataset público + ML e o rigor de reprodutibilidade estão em `docs/METODOLOGIA.md`.

**Stack:**
- **Firmware:** C++ · Arduino · ESP32 · MPU6050 · Wokwi (Fase 1) → placa física (Fase 2). O núcleo (`firmware/nucleo/`) é C++ puro, testado no host com `g++`.
- **Web-app (backend):** Python · Flask 3.1 · Supabase (Postgres + Auth, com RLS) · deploy no Vercel (pelo `@vercel/python`; ✏️ *03/11, `INFRA-04`: o Gunicorn constava aqui e no `requirements.txt` sem rodar em lugar nenhum — saiu. Backend fora da Vercel volta a precisar de um servidor WSGI*)
- **Frontend:** React 18 · TypeScript · Vite · vitest · `@supabase/supabase-js`
- **ML:** Python 3.11 · numpy · pandas · scipy · scikit-learn — versões **pinadas** em `ml/requirements.txt`. O bloco de ML está fechado (ver backlog, "Concluído").

### Documentos de referência

**Ler no início de toda sessão, nesta ordem** (✏️ ordem trocada em 2026-10-27; antes era o
`ROADMAP.md`, que é gitignorado e organiza por prioridade, não por dependência):

1. **`docs/BACKLOG-COMPLETO.md`** — o que está pendente, organizado por dependência (L0–L3). É o que responde *"o que trava o quê?"*.
2. **`docs/DIARIO-DE-ENGENHARIA.md`** — registro cronológico do que foi feito, **incluindo o que deu errado**. Procedência primária de tudo: onde outro documento divergir dele, o diário vence.
3. **`docs/LICOES-APRENDIDAS.md`** — os padrões de falha que este projeto já demonstrou, com o checklist do §9. **Ler antes de propor qualquer coisa.**
4. **`AGENTS.md`** — ✏️ *(05/11)* as regras para **dois agentes em paralelo** (o Codex e o Claude Code): divisão por área, IDs, sincronia com `develop` antes da revisão, os arquivos de conflito garantido e as junctions para dados brutos. Valem também para o Claude.
5. **`docs/CORRECOES-APLICADAS.md`** e **`docs/PENDENCIAS-ABERTAS.md`** — **gerados** por `scripts/consolidar_registro.py`; não editar à mão (o `--conferir` reprova).

Ler quando o assunto aparecer (os três primeiros são **gitignorados** — existem só no disco do autor):
- **`ROADMAP.md`** — prioridades e a seção "▶ Agora". Abre com a pergunta de pesquisa e a hipótese, que são a régua de prioridade.
- **`docs/METODOLOGIA.md`** — RQ, validação científica, dataset + ML, reprodutibilidade. Antes de qualquer tarefa de ML ou de validação.
- **`docs/HARDWARE.md`** — fases, BOM, contrato de dados, validação de hardware. Antes de firmware/hardware/integração.
- **`docs/LIMITACOES-TCC.md`** — limites medidos, que são material de defesa. Limite quantificado vai para lá, não só para o diário.

### Estrutura principal

```
firmware/        # C++/Arduino do ESP32 + MPU6050
  nucleo/        #   núcleo em C++ puro + Makefile de host (testes, dourado, mutação, sintaxe, capacidade)
web-app/         # backend Flask
  app.py         #   entrypoint (corrige sys.path, cria o app, registra rotas)
  routes.py      #   rotas, expostas via init_routes(app)
  tests/         #   pytest; tests/rls/ fala com Postgres de verdade
frontend/        # React + TS + Vite (src/main.tsx é o ponto de entrada)
ml/              # pipeline, experimentos e testes; ml/.venv é o ambiente pinado local
scripts/         # conferências que rodam no CI (docs versionados, cálculos, buffer, registro)
docs/            # backlog, diário, lições, limitações, diagramas/ (devlog/ e fontes/ são gitignorados)
hardware/        # vazia — nada versionado ainda
.github/workflows/ci.yml
vercel.json      # configuração de deploy no Vercel
```

### Como rodar

```bash
# Pré-requisitos: Python 3.11+, Node 22, conta/projeto no Supabase, .env com as chaves (ver web-app/.env.example)
cd web-app
pip install -r requirements.txt
python app.py            # sobe local em http://0.0.0.0:5000 (debug)
```

> O **Supabase** é externo; sem as chaves no `.env`, a web-app não conecta. O deploy de produção é automático no **Vercel** a partir da branch de produção.

Testes de todas as camadas: ver a seção **"Testes"**.

---

## Práticas não negociáveis

Valem para toda sessão, com qualquer ferramenta. Cada uma existe porque o projeto já pagou por
não a ter seguido (ver `docs/LICOES-APRENDIDAS.md`).

1. **Todo trabalho é registrado no diário**, no formato das entradas existentes (os oito campos
   fixos, entre eles "O que deu errado no caminho"), **incluindo o que deu errado**. ✏️ *05/11:
   aqui dizia "sete campos"; as entradas têm oito desde que o campo de erros virou fixo.*
2. **O que exigir trabalho próprio vira item no backlog**, não observação solta. Risco em aberto
   aponta o item que o carrega (§2 das lições).
3. **Teste de segurança ou de alcance precisa de controle positivo:** sabote de propósito e
   confirme que a verificação acusa — e por qual mecanismo (§1 e §4).
4. **Nada é dado por verificado sem ter sido executado.** Afirmação revisada por leitura é
   hipótese. Ao relatar, separar o que rodou do que foi lido, e dizer em que máquina rodou.
5. **Afirmação de estado neste arquivo leva número e data da medição** (§6, regra 6): número com
   data envelhece visivelmente; adjetivo não.

---

## Metodologia de desenvolvimento — Gitflow estrito

Branches:
- `main` — produção
- `develop` — integração
- `feature/<id-do-item>-<descricao>` — novas funcionalidades (base: `develop`)
- `bugfix/<id-do-item>-<descricao>` — correções (base: `develop`)

**Nunca fazer merge direto.** Sempre apresentar o resumo das alterações para o usuário revisar e aprovar o merge para `develop`.

**PR sempre com base em `develop`, nunca empilhada sobre outra branch** (✏️ 30/10). A PR #13 tinha como base a branch da #12; a #12 entrou em `develop` 19 s antes, a #13 foi mesclada na branch antiga, e o `ML-11` ficou fora de `develop` sem que nada avisasse. Trabalho que depende de outra PR ainda aberta parte da branch dela, mas a PR aponta para `develop`: o diff mostra os dois, e qualquer ordem de merge chega ao lugar certo.

### Protocolo por tarefa — itens do roadmap

**Nunca começar a implementar sem aprovação explícita do plano.**

1. **O usuário indica o item** — não escolher sozinho qual será o próximo
2. **Analisar o problema** — ler os arquivos envolvidos (e o doc de referência relevante: `HARDWARE.md` ou `METODOLOGIA.md`), entender o impacto real, identificar riscos
3. **Apresentar plano de implementação** com:
   - Diagnóstico do problema (o que está errado e por quê)
   - Abordagem escolhida e alternativas descartadas
   - Arquivos que serão alterados
   - Riscos ou efeitos colaterais esperados
   - Onde e como os testes serão escritos
   - **Para o TCC:** como a alteração se justifica no texto e a qual item da RQ ela serve
4. **Aguardar aprovação** — não avançar até o usuário confirmar
5. Após aprovação, usar `bugfix/` para correções e `feature/` para novas funcionalidades
6. Criar worktree isolada baseada em `develop`:
   ```bash
   git worktree add .claude/worktrees/<nome> -b feature/<id>-<descricao> develop
   # ou
   git worktree add .claude/worktrees/<nome> -b bugfix/<id>-<descricao> develop
   ```
7. Implementar seguindo o plano. **Se algo mudar o plano** (efeito colateral inesperado, problema maior que o previsto): parar, reportar e aguardar nova aprovação
8. **Verificar localmente:**
   - Rodar os testes existentes — todos devem continuar passando
   - Adicionar testes cobrindo o item novo, onde fizer sentido (ver "Testes")
   - **Se algum teste falhar:** não avançar — reportar com diagnóstico e aguardar decisão
9. **Push da branch e verificar CI (se configurado):**
   ```bash
   git push origin <branch>
   ```
   - Com CI configurado: aguardar e só avançar com verde ✅; se falhar, investigar o log, corrigir e novo push
   - Sem CI ainda: a verificação local cumpre esse papel (configurar CI é item de roadmap)
10. Apresentar: resumo das alterações + testes locais + status do CI — **nunca fazer merge sozinho**
11. Após aprovação do merge:
    ```bash
    git checkout develop
    git merge --no-ff <branch> -m "Merge <branch> into develop"
    git push origin develop
    git branch -d <branch>
    git push origin --delete <branch>
    ```
12. Registrar: entrada no `docs/DIARIO-DE-ENGENHARIA.md`, item fechado ou criado no `docs/BACKLOG-COMPLETO.md` (com a contagem por camada fechando), e `ROADMAP.md` **localmente** (`[x]` e **Concluído** com o nome da branch)
13. **Se for um marco que vale mostrar:** gerar a entrada de devlog (regras em `CLAUDE.local.md`, quando existir na máquina)
14. Limpar worktree:
    ```bash
    git worktree remove .claude/worktrees/<nome-da-feature>
    git worktree prune
    ```

### Protocolo para tarefas fora do roadmap

1. **Analisar e apresentar plano** antes de implementar — mesma regra
2. Aguardar aprovação
3. Implementar em `feature/<descricao>` baseada em `develop`
4. **Verificar** — testes + reporte de resultados. Parar se houver falha
5. Ao concluir, avaliar se o item vira entrada no `ROADMAP.md` (histórico) ou é pontual demais

---

## Segredos, credenciais e arquivos de controle interno

Repositório **público** + build in public = risco de vazamento real, em duas frentes: o que vai pro git e o que aparece nas gravações.

### O que NUNCA pode ser versionado
- `.env` e variantes (`.env.*`) — chaves do Supabase, tokens. Manter `web-app/.env.example` sem valores reais como referência.
- Segredos de firmware (senha de Wi-Fi, token do device): usar `secrets.h` (ignorado) + `secrets.example.h` (versionado, sem valores).
- `CLAUDE.local.md`, `ROADMAP.md`, `HISTORICO.md`, `DOCUMENTO-TCC.md`, `ROTEIRO-APRESENTACAO.md`,
  `.claude/`, `docs/devlog/` — controle interno, só local. **Nunca** commitar nem dar push. O
  devlog fica salvo localmente para organização pessoal; o Git ignora a pasta inteira.
  ✏️ **O `CLAUDE.md` saiu desta lista em 2026-10-27**, por decisão do autor (`DOC-11`/`GIT-05`):
  ele é versionado, e o que nele era pessoal foi para o `CLAUDE.local.md`.
- **Material do texto do TCC não é versionado** (decisão do autor, 2026-08-21 — revoga a regra
  anterior, que mandava versionar as Figuras 1–3). Isso inclui figuras de arquitetura, diagramas
  produzidos para o documento e qualquer arquivo que exista para o texto acadêmico, não para o
  repositório. O `.gitignore` cobre `img/MPU6050 Sleep Data Pipeline*`.
  > ⚠️ A regra vale daqui pra frente. Arquivo já commitado continua no histórico mesmo depois
  > de removido — ver a seção sobre `.gitignore` e histórico logo abaixo.

> O `.gitignore` já cobre tudo isso. Ao criar arquivo novo com segredo, conferir que casa com uma regra do `.gitignore` **antes** do primeiro `git add`.

### `.gitignore` só vale pro futuro — atenção ao histórico
Ele não remove o que já está no histórico. Se uma credencial **já foi commitada** algum dia, segue acessível mesmo que não esteja na versão atual. Regra de ouro: **credencial que já foi pública = comprometida → rotacionar** (gerar nova no Supabase, trocar Wi-Fi). Limpar histórico (`git filter-repo`/BFG) é complementar, não substitui a rotação. Verificar com `git log --all -p -S "SUPABASE"`.

### Build in public — vazamento por gravação
Git limpo não adianta se a chave aparece num vídeo. As regras de gravação ficam no
`CLAUDE.local.md`, junto com as de devlog.

> ⚠️ Ao remover uma worktree, arquivos ignorados pelo git dentro dela são apagados junto. Manter
> os arquivos internos (`CLAUDE.local.md`, `ROADMAP.md`) na **raiz do repositório principal**,
> nunca dentro de worktrees.

---

## Worktrees — regra obrigatória

O Claude cria uma worktree nova a cada sessão e não remove sozinho; sem limpeza, acumulam em `.claude/worktrees/`.

**Ao finalizar cada tarefa:**
```bash
git worktree remove .claude/worktrees/<nome-da-worktree>
git worktree prune
git branch -d claude/<nome-da-sessao>   # branch de sessão, se não virou feature
```

Worktrees legítimas: a da feature/bugfix em andamento e a da sessão atual (`claude/*`, removida ao encerrar).

---

## Commits

- **Nunca** adicionar `Co-Authored-By: Claude`
- Padrão `tipo: descrição em minúsculas` — tipos: `feat`, `fix`, `refactor`, `docs`, `chore`, `test`, `ci`, `security`
- Referenciar o ID do item do roadmap quando aplicável: `fix: corrigir comportamento X (ID)`

---

## Testes

> ✏️ **Corrigido em 2026-10-17 (`DOC-11`). Este parágrafo dizia "ainda não há suíte de
> testes nem CI", e isso era falso havia semanas.** Mais grave que estar desatualizado:
> este é o arquivo que orienta cada sessão de trabalho, então a frase instruía sessões a
> **não** rodar uma suíte que existe. Achado por varredura ao fechar o `PERFIL-01`, por
> busca dos termos "ainda não existe" no repositório. Ocorrência registrada no §6 das
> lições, e é a terceira vez em um dia que um documento deste projeto afirma um estado
> que o artefato contradiz.

> ✏️ **Reconferido em 2026-10-27 (`DOC-11`, segunda passagem).** A tabela de 17/10 estava
> desatualizada nos números, **omitia a suíte de ML inteira** e listava errado os jobs do CI
> (dizia `documentos`, `rls` e firmware; são seis, e o `frontend` roda `vitest` desde 19/08).
> Uma cópia de backup fora do repositório, de 28/08, ainda dizia *"Testes: ainda não existem"*
> — arquivo gitignorado tem cópias, e as cópias divergem em silêncio. Foi o que levou a versioná-lo.

**Há suíte e há CI.** Números **executados em 2026-10-28**, Windows 11, na branch
`chore/GIT-01-normalizar-fim-de-linha`, **sem nenhuma variável de ambiente**, nesta ordem de
custo para rodar:

| Onde | Como rodar | Resultado em 28/10 |
|---|---|---|
| Backend (Flask) | `cd web-app && pytest --ignore=tests/rls` | **551 passam** ✏️ *(13/11, `CI-10`: +2 do `test_versao_do_python.py`; em contêiner `python:3.12` com `CI=true` — fora do CI, um deles pula)*; antes **549 passam** ✏️ *(12/11, DATA-15 e API-08, Windows, sem RLS)*; antes **544 passam** ✏️ *(11/11, `CAL-03` etapa 1: +18 do `test_calibracao_na_ingestao.py` — `gn` e `cal` do contrato 2.9.0)*; antes **526 passam** ✏️ *(11/11, `INFRA-05`: +1 do `test_regiao_do_backend.py` — as funções na região do banco)*; antes **525 passam** ✏️ *(10/11, `LGPD-12`: +16 do `test_consentimento.py` — a rota do consentimento, as travas 403 e as três versões iguais)*; antes **509 passam** ✏️ *(10/11, `LGPD-11`: +5 do `test_politica_cobre_as_colunas.py` — toda coluna gravada tem de estar na §2.2 da política)*; antes **504 passam** ✏️ *(10/11, `APP-10`: +4 do `test_lote.py` — um cliente por requisição no caminho por sessão; Windows, Python 3.13)*; antes **500 passam** ✏️ *(09/11, `APP-02` etapa 3: +7 do `test_noite_do_app.py`, uma noite do emulador da ingestão ao modelo)*; antes **493 passam** ✏️ *(08/11, `ML-INF`: +40 do `test_inferencia.py`; Windows, Python 3.13)*; antes **453 passam** ✏️ *(05/11, `API-05`: +36 do `test_comparacao_de_datas.py`; 03/11, `LGPD-05`: +1; 01/11, `API-04`: +9; 01/11, `AUTH-08`: +17; 31/10, `SEC-14`: +6)*; antes **384 passam** ✏️ *(30/10, branch do `DATA-07b`; eram 316 no `API-03` e 293 em 28/10)* |
| Frontend | `cd frontend && npx vitest run` | **574 passam, 44 arquivos** ✏️ *(12/11, DATA-15 e API-08, Windows)*; antes **572 passam, 44 arquivos** ✏️ *(12/11, frontend do protótipo, PRs #134–#139 do Codex: painel, coleta, dispositivos, histórico, configurações; reexecutado pelo Claude na ponta `57b683f`)*; antes **563 passam, 43 arquivos** ✏️ *(11/11, `CAL-03` etapa 2: +2 da linha de calibração no cartão)*; antes **561 passam, 43 arquivos** ✏️ *(10/11, `LGPD-12`: +10 do `TelaDeConsentimento.test.tsx` — a tela e o portão antes da noite)*; antes **551 passam, 42 arquivos** ✏️ *(10/11, `APP-10`: +5 do laço de envio e do cartão; a contagem de arquivos dizia 43 desde 09/11, e a medida é 42 — `git ls-files` também)*; antes **546 passam** ✏️ *(09/11, `APP-02` etapa 4, percurso pelos botões: +4 dos três achados)*; antes **542 passam, 43 arquivos** ✏️ *(09/11, `APP-02` etapa 4: +14 da tela da noite — `ListaDeNoites`, a navegação, o resumo e a posição no cartão)*; antes **528 passam, 40 arquivos** ✏️ *(09/11, `APP-02` etapa 3: +19 do envio — `envioDaNoite.test.ts`, `enviarLote` e o cartão)*; antes **509 passam, 39 arquivos** ✏️ *(09/11, `APP-02` etapa 2: +15 do `noiteNativa.test.ts` e do `CartaoDaNoite.test.tsx`)*; antes **494 passam, 37 arquivos** ✏️ *(08/11, `APP-02`: +5 do endereço do backend no app, em `api.test.ts` e `coleta.test.ts`)*; antes **489 passam, 37 arquivos** ✏️ *(05/11, `UI-24`: +11 do `useHistorico.test.ts`; 04/11, `DEMO-03`: +3 do `useDispositivos.test.ts`; 04/11, `DEMO-02` e `UI-23`: +4 do `Guardas.test.tsx` e +5 do `Landing.test.tsx`; 03/11, `UI-22`: o `raw.test.ts` passou a 4 testes, e sobe o servidor de desenvolvimento; 03/11, `UI-21`: +2 do `raw.test.ts`; 03/11, `SEC-17`: com **vitest 4.1.12** e vite 6.4.5 — mesma contagem; o `vitest.config.ts` libera `docs/` para o `?raw` da política; 03/11, `SEC-16`: +19, com o `Login.test.tsx`; 03/11, `LGPD-01` (b): +15, com `politica.test.ts` e `Privacidade.test.tsx`; 03/11, `LGPD-05`: +4, com o `Register.test.tsx`; 01/11, `AUTH-08`: +2; 31/10, `AUTH-07`: +4 do `AuthContext.test.tsx`)* |
| Tipos e build | `cd frontend && npm run build` (`tsc --noEmit && vite build`) | `tsc` limpo; `vite build` ok (avisa do chunk único — `UI-15`) |
| RLS (Postgres real) | `DORMIO_RLS_DATABASE_URL=... pytest tests/rls` | **270 passam** ✏️ *(13/11, `SEC-13`: +1, o `pos_migracao.sql` sem GRANT; Postgres 17 em Docker)*; antes **269 passam** ✏️ *(11/11, `CAL-03` etapa 1: +10 do `test_rls_calibracao.py`, a 018; Postgres 17 em Docker)*; antes **259 passam** ✏️ *(10/11, `LGPD-12`: +12 do `test_rls_consentimento.py`, a 017; Postgres 17 em Docker)*; antes **247 passam** ✏️ *(10/11, `LGPD-09`: +3 da 013 corrigida — a sessão conta como uso, inclusive a `refreshed_at`, que é o que a renovação grava)*; antes **244 passam** ✏️ *(10/11, `SEC-18`: +48 do `test_rls_validacao_no_banco.py`, a 016; Postgres 17 em Docker)*; antes **196 passam** ✏️ *(09/11, `DATA-12`: +3 do `test_rls_cascata.py`; o `esquema_base.sql` cria `sleep_data` como a produção — `user_id` do painel, sem cascata —, e sem a 015 os 3 caem; passa também no Postgres 17, local)*; antes **193 passam** ✏️ *(09/11, `DATA-10`: o `esquema_base.sql` passou a criar `sleep_data.id` como uuid, como na produção; sem a 014, 17 caem com o erro da produção)*; antes **193 passam** ✏️ *(05/11, `LGPD-02`: +19 do `test_rls_retencao.py`, contra `postgres:16` em Docker; 03/11, `LGPD-05`/`LGPD-06`: +10 da 012 e da consulta agregada; 01/11, `DATA-08`: +6 da 011)*; antes **158 passam** contra `postgres:16` em Docker ✏️ *(30/10, `DATA-07b`: +7 da migração 010; eram 151 em 28/10)*, com a base imitando os privilégios padrão do Supabase (`SEC-12`) — **pulam** sem a variável, de propósito |
| Mutação do RLS | `python web-app/tests/rls/verificar_por_mutacao.py` ✏️ *(13/11, `CI-11`: os papéis do Supabase são do **servidor** inteiro — rodar a suíte e a mutação no **mesmo banco**, ou num Postgres só para elas; com outro banco dependendo dos papéis, a preparação para e nomeia o banco)* | **54/54 sabotagens detectadas** ✏️ *(11/11, `CAL-03`: +4 da 018 — a régua, a régua mais estreita, a sessão e o token descartando as colunas)*; antes **50/50** ✏️ *(10/11, `LGPD-12`: +5 da 017 — as duas travas, a versão, o gatilho e a função)*; antes **45/45** ✏️ *(10/11, `LGPD-09`: +1, o expurgo sem a sessão)*; antes **44/44** ✏️ *(10/11, `SEC-18`: +8 da 016)*; antes **36/36** ✏️ *(09/11, `DATA-12`: +1, a chave sem cascata)*; antes **35/35** ✏️ *(05/11, `LGPD-02`: +3 do expurgo)* |
| Diagnóstico e ordem das migrações | `DORMIO_RLS_DATABASE_URL=... python web-app/tests/migracoes/verificar_migracoes.py` | os 18 estados (11/11, com a 018 do `CAL-03`); antes os 17 estados (10/11, com a 017 do `LGPD-12`); antes os 16 estados (10/11, com a 016) e a 016 parando sem apagar nada com dado antigo fora das regras e a ordem real da produção; 3/3 sabotagens acusadas em 28/10, e a da 010 (função que grava nulo) em 30/10 |
| ML | `cd ml && .venv/Scripts/python -m pytest testes` | **310 passam** ✏️ *(11/11, `CAL-03`: +11 do `test_calibracao.py` — a referência da autocalibração e o `dourado_calibracao.json`; Windows/Python 3.11.9)*; antes **299 passam** ✏️ *(07/11, ML-INF v2: +10 casos de contrato, noites e fronteiras; Windows/Python 3.11.9)*; antes **289 passam** ✏️ *(07/11, ML-INF: +4 controles de LOSO, contrato e dourados; Windows/Python 3.11.9)*; antes **285 passam** ✏️ *(07/11, cobertura ML-13: +7 casos; Windows, Python 3.11.9)*; antes **278 passam** ✏️ *(06/11, ML-13: +9 do carregador, CLI e exportação agregada DREAMT, Windows/Python 3.11.9)*; antes **269 passam** ✏️ *(06/11, integração do `develop` com o `SIM-02` na `ML-17` 2/2: 245 da branch + 24 do `test_simulador_c2.py`; a 1/2 integrada tinha 223 + 24 = 247)*; antes **245 passam** ✏️ *(06/11, publicação agregada `ML-17`: +9 controles de realocação, publicação e auditoria local; suíte Windows, Python 3.11.9)*; antes **236 passam** ✏️ *(05/11, segunda etapa `ML-17`: +13 controles de executor, comparador e evidências; Windows, Python 3.11.9)*; antes **223 passam** ✏️ *(05/11, revisão `ML-17`: +6 testes de contrato AST e 22 mutações em 11 chamadas; suíte completa Windows, Python 3.11.9)*; antes **217 passam** ✏️ *(05/11, `ML-17`: suíte completa executada no Windows, Python 3.11.9; 190 da base com a ML-13 e +27 de fronteiras/caches/controles/procedência; dourados intactos)*; antes **177 passam** ✏️ *(05/11: `ML-14` +21, `ML-15` +12, `ML-16` +10 — F1, reprodução e rastreabilidade; 03/11, `ML-06`: +8 do carregador da Walch; 30/10, branch do `FW-07`: +19 do dourado da cadeia C2)* |
| Mutação do dourado | `cd ml && .venv/Scripts/python testes/verificar_vetor_dourado_por_mutacao.py` | **12/12**, e o ponto cego registrado segue cego |
| Firmware | `cd firmware/nucleo && make && make sintaxe capacidade mutacao mutacao-cadeia mutacao-fila mutacao-coletor laco` | ✏️ *(13/11, `FW-15`: `make fila` **115**, `mutacao-fila` **17/17**; `capacidade` 32 640 registros = 272,0 h, com um setor de cabeçalho de formato; na placa, a montagem formata a área sem a marca)*; antes ✏️ *(12/11, `FW-13`: **na placa**, envio com `HTTP 200` em lotes de 20; para o chip, RAM fixa **108 904 B (33 %)**; no host `make` 185, `laco` 8/8, `mutacao-fila` 14/14; o log do envio imprime o heap — mínimo medido no TLS 14 772 B, `FW-14`)*; antes ✏️ *(12/11, `FW-12`: **para o chip**, `python scripts/compilar_sketch_esp32.py` (precisa do `arduino-cli` com `esp32:esp32` 3.3.12) — programa 1 085 336 B, **RAM fixa 111 464 B (34 %), 216 216 B para o heap**; o `make sintaxe` liga com stubs e não vê o teto de RAM do ESP32. No host, nesta data: `make` 185, `laco` 8/8)*; **341 + 157 + 170 + 456 + 94 + 320 + 185 verificações, 0 falhas** ✏️ *(11/11, `FW-11`: +18 no `c2` (calibrar as amostras, a vigia da FIFO, o sensor que reiniciou) e +9 na `fila` (o bit da calibração); `make mutacao-cadeia` **34/34** (+5) e `make laco` **8/8** (+4: o sketch contra um MPU6050 falso, `testes/sensor_do_sketch.cpp`); em contêiner `gcc:13`)*; antes **341 + 157 + 152 + 456 + 85 + 320 + 185** ✏️ *(11/11, `CAL-03` etapa 2: +6 do ponto parado no coletor; `make mutacao-coletor` **17/17**)*; antes **341 + 157 + 152 + 456 + 85 + 314 + 185** ✏️ *(11/11, `CAL-03`: +185 do `make calibracao` contra o dourado do `ml/`; +26 no coletor e +1 na fila; `make mutacao-calibracao` **10/10** e `make mutacao-coletor` **15/15** com as 3 novas; em contêiner `gcc:13`)*; antes **341 + 157 + 152 + 456 + 84 + 288** ✏️ *(08/11, `APP-02`: +288 do `make celular`, o coletor do celular contra o dourado da cadeia; `make mutacao-coletor` 12/12 como esperado, com 2 pontos cegos declarados; em contêiner `gcc:13`)*; antes **341 + 157 + 152 + 456 + 84** ✏️ *(03/11, `FW-10`: +16 no alvo `c2`, com a deriva do relógio; 01/11, `API-04`: +1)*; ✏️ *(03/11)* `make laco`: o laço real do `sketch.ino` com relógio falso, 26 verificações e 4/4 sabotagens no sketch acusadas; **4/4 sketches e a ponte da flash compilam, e o `sketch.ino` liga com o núcleo; mutação 15/15; mutação da cadeia C2, do payload, da época da grade, do rádio, do prazo da drenagem e da deriva do relógio 29/29 ✏️ *(03/11: +5 do `FW-10`; o total inclui o caso sem sabotagem)*; mutação da fila e do envio 13/13** ✏️ *(10/11, auditoria: o `make mutacao-fila` diz **14/14 como esperado**; o número desta linha é de 31/10)* (em contêiner `gcc:13`, 31/10) ✏️ *(30/10, `FW-07` e `DATA-07b`: entraram os alvos `c2` e `cadeia`; 31/10, `FW-08`: o alvo `fila`, e o `capacidade` passou a validar `firmware/partitions.csv`)* |
| App Android (`APP-02`) | `cd frontend && npm run build:app`, depois `cd android && ./gradlew assembleDebug` com o JDK 21 do Android Studio (`JAVA_HOME`) e o `local.properties` apontando o SDK (gitignorado) | ✏️ *13/11, `CI-09`: também **no CI** (`app-android.yml`): `testDebugUnitTest` **32 passam** e o `assembleRelease` sem assinatura (5,18 MB, as três ABIs), Ubuntu 24.04, JDK 21.* ✏️ *11/11, `CAL-03` etapa 2: `testDebugUnitTest` **32 passam** (+12 do `CalibracaoTest`); `:app:connectedDebugAndroidTest` no emulador Pixel 6 **7 passam, 3 pulados** (+3 do `CalibracaoNativaTest`). No Windows, o Gradle precisa de `JAVA_TOOL_OPTIONS=-Djdk.net.unixdomain.tmpdir=<pasta comum>` (senão "Unable to establish loopback connection"). ⚠️ **Com o celular do autor no USB, mirar o emulador (`ANDROID_SERIAL=emulator-5554`)**: o `connectedAndroidTest` desinstala o app no fim, e com ele as noites guardadas.* ✏️ *11/11, `APP-12`: a chave do autor existe (`~/.dormio`, com cópia fora do computador); o primeiro APK de release (v1.0.0, `versionCode` 1) saiu de `develop` `4811f57`, assinado e não depurável — **a cada APK novo para testadores, subir o `versionCode`**.* ✏️ *10/11, `APP-12`: `./gradlew assembleRelease` gera o APK de release, não depurável; assinado só com a chave do autor, lida de `~/.dormio/assinatura.properties` (fora do repositório) — sem ela sai sem assinatura. Como mandar a testadores: `docs/DISTRIBUICAO-DO-APP.md`.* ✏️ *09/11, etapa 4: `testDebugUnitTest` **20 passam** (+7 das anotações e do corte por calor); `connectedDebugAndroidTest` 4 passam, 3 pulados. Etapa 3: `testDebugUnitTest` **13 passam** (+5 do progresso do envio e da linha pela metade). Etapa 2: `./gradlew :app:testDebugUnitTest` **8 passam** (JVM: relógio do sensor, arquivo e estado da noite); `./gradlew :app:connectedDebugAndroidTest` no emulador Pixel 6, Android 37: **4 passam, 3 pulados** (os roteiros, que só rodam com `-e roteiro`); roteiro `longa` de 10 min em Doze: 20/20 épocas. 08/11: o APK de depuração compila com `libdormio_nucleo.so` em `armeabi-v7a`, `arm64-v8a` e `x86_64` e as 8 funções JNI exportadas* |
| Conferências de documento | `python scripts/<nome>.py --conferir` para `calculos_tcc`, `estudo_buffer` (✏️ *04/11, `CALC-02`: estes dois só entraram no CI agora — até ali rodavam só à mão*), `consolidar_registro`; sem `--conferir` para `conferir_docs_versionados` e ✏️ *(03/11, `SEC-15`)* `conferir_tls_firmware`; ✏️ *(03/11, `DOC-13`)* `conferir_backlog` com `--conferir` — o resumo do topo do backlog contra as linhas; ✏️ *(05/11, `REQ-01`)* `requisitos_dispositivo` com `--conferir` — os números de `docs/REQUISITOS-DISPOSITIVO.md`; ✏️ *(13/11, `SEC-20`)* `conferir_csp` sem argumentos, **depois do `npm run build`** — a CSP do `vercel.json` contra os scripts inline do site gerado; ✏️ *(13/11, `CI-11`)* `conferir_subprocess_utf8` sem argumentos — `subprocess` lendo texto sem `encoding` | todas passam |

Total: **967 testes** de pytest/vitest + **498 verificações** do núcleo C++. ✏️ *30/10: com as
linhas acima, 316 + 418 + 151 + 126 = **1 011** de pytest/vitest (frontend e RLS não foram
reexecutados: valem os números de 28/10) e **1 059** verificações do núcleo. A soma de 28/10 com
a própria tabela daria 969, não 967 — a diferença não foi investigada.*

**Rodando no Windows** — o CI é Ubuntu. Desde 28/10 os scripts e a suíte de ML funcionam no
Windows sem ajuste (`DOCS-WIN-01`, `DOCS-WIN-02`, `ML-WIN-01`). Resta uma diferença:
- Não há `g++` nem `make`: rodar o firmware em contêiner, montando `firmware/` **e**
  `ml/testes/` (o alvo `dourado` lê `ml/testes/vetor_dourado.json`).
- Script novo que imprima símbolo fora do `cp1252` (✓ ✗ ⓘ ĝ σ) precisa de
  `sys.stdout.reconfigure(encoding="utf-8")` — é o que os quatro já corrigidos fazem.

**Auditoria de dependências** (`CI-08`, 03/11): `.github/workflows/auditoria-dependencias.yml` — `npm audit --audit-level=high` (✏️ *03/11, `SEC-17`: com as ferramentas de teste e build; até ali `--omit=dev`*) e `pip-audit` sobre `web-app/requirements.txt`, quando as dependências mudam e toda segunda-feira (o agendamento só a partir de `main`). Dependência nova ou versão nova passa por ele; para rodar à mão: `cd frontend && npm audit` e `pip-audit -r web-app/requirements.txt`.

✏️ *13/11, `CI-10`: o Python do backend no CI vem do `web-app/.python-version` (**3.12**), o mesmo arquivo que a Vercel lê — na pasta do backend, não na raiz, onde a Vercel o ignora; trocar de versão é trocar esse arquivo, e o `test_versao_do_python.py` reprova se o job e o arquivo divergirem. O ML segue em 3.10 no CI.*

✏️ *13/11, `CI-09`: `.github/workflows/app-android.yml` roda `npm run build:app`, os testes de JVM (`testDebugUnitTest`) e o `assembleRelease` sem assinatura quando o `frontend/` ou o `firmware/nucleo/` mudam, e confere a `libdormio_nucleo.so` nas três ABIs do APK. NDK `27.0.12077973` e CMake `3.22.1` fixos — trocar é decisão. Os instrumentados e a assinatura seguem só na máquina do autor.*

✏️ *13/11, `CI-12`: `.github/workflows/firmware-esp32.yml` compila o `sketch.ino` **para o ESP32** (`arduino-cli` 1.6.0, `esp32:esp32` 3.3.12, com cache) quando o firmware muda, e exige que uma cópia sabotada (o lote na RAM estática) reprove.*

**CI:** `.github/workflows/ci.yml`, seis jobs: `test` (backend), `rls` (matriz Postgres 14,
16 e 17 — ✏️ *09/11, `DATA-12`: a 17 é a da produção* —, mais mutação na 16), `frontend` (vitest, tsc, vite), `ml`, `firmware` e `documentos`.
**Rodou num runner em 2026-10-28** (execução `40639232458`, `ubuntu-24.04`): os sete jobs
passaram, inclusive a perna Postgres 16, que até ali era hipótese. A imagem é **fixa**
(`runs-on: ubuntu-24.04`, `CI-07`): migrar para outra é decisão, nas seis linhas de uma vez.

Convenções por camada:
- **Web-app (Flask):** lógica de rotas e funções puras com `pytest`; isolar chamadas ao Supabase (mock). **Exceção deliberada:** `tests/rls/` **não** mocka nada e fala com um Postgres real — mock não exercita policy nenhuma (§4 das lições).
- **ML:** carregamento de dados, sanidade do pipeline, treino fim a fim em amostra pequena; registrar métricas (ver `docs/METODOLOGIA.md`).
- **Firmware:** Fase 1 tem teste limitado (Wokwi) — priorizar lógica isolável; Fase 2 exige validação no dispositivo real (ver `docs/HARDWARE.md`).
- **Controle positivo é obrigatório** (§1 e §4 de `docs/LICOES-APRENDIDAS.md`): nenhuma verificação nova conta como pronta sem provocar o defeito de propósito e confirmar que ela acusa — nomeando o teste que deve cair.

---

## Decisões técnicas (operacionais)

- **Supabase — segurança (não só "não commitar chave"):**
  - **Tipos de chave:** `anon` (pública, vai ao cliente) vs. `service_role` (secreta, full-access). **Nunca** pôr a `service_role` em cliente, front, firmware ou qualquer lugar público — só no backend via `.env`.
  - **Row Level Security:** RLS **ligado** em todas as tabelas, com políticas que restrinjam cada linha ao dono. Com RLS off, a chave `anon` lê/escreve tudo. É item de roadmap, não detalhe.
  - **Autenticação do dispositivo:** o ESP32 usa credencial própria (token de device), nunca a `service_role`.
  - **Validação de entrada:** o backend valida o que o device manda antes de persistir. Não confiar no cliente.
- **Deploy no Vercel:** `vercel.json` controla o build; `app.py` precisa expor `app` globalmente (o Vercel importa essa variável). Não envolver a criação do `app` em condicionais que impeçam o import.
- **Wokwi é meio, não fim; dataset público + ML é decisão em aberto:** ver `docs/HARDWARE.md` e `docs/METODOLOGIA.md`.

---

## Deploy

- **Produção:** Vercel — https://dormio-smart.vercel.app
- **Região das funções** (`INFRA-05`, 11/11): `gru1` (São Paulo), no `vercel.json`, porque o banco do Supabase é `sa-east-1`. Até 11/11 rodavam em `iad1`, o padrão, e cada gravação cruzava o continente: o envio de uma noite levou 4 min 48 s, com o banco gastando 0,43 ms por gravação. Mudar o Supabase de região é mudar esta linha junto (`test_regiao_do_backend.py` confere).
- **Cabeçalhos de segurança** (`SEC-20`, 13/11): a primeira rota do `vercel.json` põe a CSP e os demais cabeçalhos em todo o site. **Script inline só entra por hash:** mudar o script do tema no `frontend/index.html` ou qualquer `<script>` da `landing-prototipo.html` exige trocar o hash no `script-src` — `python scripts/conferir_csp.py --imprimir` (depois do `npm run build`) lista os hashes, e o CI reprova se divergirem. Origem nova (outra API, outro CDN de fonte) entra na diretiva certa da CSP, ou o navegador a bloqueia sem erro na tela.
- **Health check:** ✏️ **existe desde o `WEB-04`** — `GET /health`, sem autenticação, respondendo `200` quando o banco está alcançável e `503` quando o app está de pé e o banco não. A linha anterior ("ainda não existe — criar um endpoint simples é item de roadmap") foi corrigida em 17/10 pelo `DOC-11`, junto com a da seção "Testes".
- **Cadeia TLS da produção** (`SEC-15`, 03/11): o firmware só confia nas raízes de `firmware/ca_raiz.h` (hoje a Vercel usa Google Trust Services, WR1 → GTS Root R1). O monitor abaixo confere a cadeia da Vercel contra essa lista (`conferir_tls_firmware.py --producao`). Se reprovar, a Vercel trocou de CA: incluir a raiz nova e regravar o firmware — os dispositivos não perdem dado, mas param de enviar.
- **Monitor da produção** (`INFRA-03`, 28/10): `.github/workflows/saude-producao.yml` chama o `/health` a cada 3 dias por `scripts/conferir_producao.py` e reprova se o banco não responder. ⚠️ O Supabase é do **plano gratuito e pausa depois de uma semana sem uso** — foi o que derrubou a produção até 28/10; se o job reprovar, a primeira coisa a olhar é o painel do Supabase. O agendamento só roda a partir de `main`; o workflow está lá desde o release de 29/10 (execução manual `40818265459` passou). ✏️ *31/10: a primeira execução **agendada** rodou e passou (`41214122394`, 15:17 UTC — o cron é 09:17, e o GitHub atrasou seis horas); `INFRA-03` fechado.*
- **Release de 05/11** (PR #86, `5fa9ab6`, deploy `7584696406`): leva a `API-05` (limites de consulta comparados como instante; fusos misturados → `400`), a `UI-24` (o painel descarta respostas antigas do histórico), o `DEMO-03` (só o servidor de desenvolvimento) e, sem efeito no site, os `CALC-01` a `CALC-04` e os `ML-14` a `ML-16`. Conferido: `/health` `200`; rotas sem credencial e `Bearer` inválido → `401`; `/api/sleep-history` com fusos misturados e sem credencial → `401` (a autenticação vem antes; o `400` só com sessão, e nenhum cliente manda esses parâmetros — **não exercitado na produção**); `/privacidade` `200`; o autor confirmou o login e o painel.
- **Release de 04/11** (PR #73, `31cfb7d`, deploy `7537089021`): leva o `DOC-14` (README novo), o `DEMO-02` (modo demonstração pelo guarda, só em desenvolvimento), o `UI-23` (página inicial na arquitetura C2) e o `DOC-15`. Conferido: `/health` `200`; rotas sem credencial → `401`; `/privacidade` `200`; a página inicial publicada com os textos novos e sem "Deep Sleep" nem "Wake-on-Motion" (no navegador e no pacote); **`/dashboard?demo=1` na produção vai ao `/login`, sem faixa**; o README da `main` com as seções novas; o autor confirmou o login.
- **Release de 03/11, sexto** (PR #69, `9d19ec1`, deploy `7536039508`): leva o `INFRA-04` (backend sem o gunicorn), o `SEC-17` (vite 6.4.5, vitest 4.1.12), o `UI-21` e o `UI-22`. Conferido: `/health` `200`, banco ok — a Vercel instalou o backend sem o gunicorn e ele sobe —; rotas sem credencial e `Bearer` inválido → `401`; `/privacidade` `200`; o autor confirmou o login. **Não medido:** que o pacote do site publicado ficou idêntico ao anterior — a igualdade byte a byte é do build local (o da Vercel tem as variáveis do controlador, e os deploys antigos ficam atrás do login da Vercel).
- **Release de 03/11, quinto** (PR #63, `f754b96`, deploy `7534968706`): leva o `DOC-13` e o `CI-08` — Flask 3.1.3, python-dotenv 1.2.2 e gunicorn 22.0.0 no backend, e a auditoria de dependências em `main`. Conferido: `/health` `200`, banco ok; rotas sem credencial e `Bearer` inválido → `401`; `/privacidade` `200`; a auditoria rodou a partir de `main` (execução manual `41751583490`, os dois jobs verdes); o autor confirmou o login. Não conferível de fora: a versão dos pacotes que a Vercel instalou.
- **Release de 03/11, quarto** (PR #60, `87622ce`, deploy `7534293060`): leva o `SEC-16` — `react-router` 7.18.4 e o destino pós-login validado. Conferido: `/health` `200`, `/privacidade` `200`, `PATCH /api/me/perfil` sem credencial → `401`, a validação nova no pacote publicado; o autor confirmou o login.
- **Release de 03/11, terceiro** (PR #57, `242d854`, deploy `7530696288`): leva a página `/privacidade`. As variáveis `VITE_POLITICA_CONTROLADOR` e `VITE_POLITICA_CONTATO` foram criadas pelo autor antes (Production, Config) e entraram no build. Conferido: `/health` `200`, `/privacidade` `200`, os dois valores no pacote publicado; o autor conferiu a página (seção 1 com o controlador e o contato, tabelas formatadas) e confirmou o login.
- **Política de privacidade no app** (03/11, `LGPD-01` (b)): `/privacidade` lê `docs/POLITICA-DE-PRIVACIDADE.md` no build. O controlador e o contato vêm das variáveis **`VITE_POLITICA_CONTROLADOR`** e **`VITE_POLITICA_CONTATO`**, a definir na Vercel (ambiente de produção) **antes do release que leva a página** — são de build, então mudar o valor exige novo deploy. Sem elas, a página diz "ainda não informado". Editar o texto da política é editar o documento: a página acompanha no próximo deploy.
- **Migração `012` aplicada na produção** (03/11, `LGPD-08`): idade a partir de 18; diagnóstico `2 de 2 marcas`, 001–011 intactas. **Produção com 001–012.**
- **Release de 03/11, segundo** (PR #54, `7e7140e`, deploy `7530061150`): leva o `LGPD-05`/`LGPD-06` — **muda o site:** cadastro só com a declaração de 18+, idade mínima 18. Conferido: `/health` `200`, `PATCH /api/me/perfil` sem credencial → `401`, o pacote publicado contém a caixa e o registro da data; o autor confirmou o login e a recusa do cadastro sem a caixa. A contagem agregada do público é `web-app/migrations/CONSULTA-publico-por-faixa.sql`, só leitura — a única forma de consultar a idade que a política autoriza.
- **Banco de produção** (diagnóstico de 30/10): migrações 001–010 **todas aplicadas** (a 002 desnecessária), na ordem real 001, 003–006, 008, 009, 007, 010. Migração nova: aplicar no SQL Editor e rodar `web-app/migrations/DIAGNOSTICO-migracoes-aplicadas.sql`. ✏️ *30/10: a **010** (`DATA-07b`) foi aplicada antes do release, como exigia o `DATA-07f`.* ✏️ *01/11: a **011** (`DATA-08`, leitura idempotente) foi aplicada e conferida (`DATA-09`): 0 duplicatas antes, 3 de 3 marcas depois. Produção com **001–011** aplicadas.* ✏️ *09/11: a **014** (`DATA-10`) conserta o tipo devolvido pelas funções de gravação — **sem ela, nenhuma leitura grava na produção**; aplicá-la é o `DATA-11`.* ✏️ *09/11, mais tarde: a **014** foi aplicada e conferida (`DATA-11`): 2 de 2 marcas, e o celular gravou 8 épocas com `200`. Produção com **001–012 e 014**; a 013 espera o `LGPD-09`.* ✏️ *09/11, `DATA-12`: a **015** dá à chave de `sleep_data.user_id` a cascata que a 001 declara (na produção a coluna veio do painel, sem ela); aplicá-la é o `DATA-13`. A produção roda Postgres **17**.* ✏️ *10/11: a **015** foi aplicada e conferida (`DATA-13`): 1 de 1 marca, e as demais como antes. Produção com **001–012, 014 e 015**, em **PostgreSQL 17.6**; a 013 espera o `LGPD-09`.* ✏️ *10/11, mais tarde: a **016** (`SEC-18`, validação no banco) foi aplicada e conferida (`SEC-21`). Produção com **001–012 e 014–016**.* ✏️ *10/11, mais tarde: a **013** (`LGPD-09`, com a sessão contando como uso) foi aplicada e o expurgo agendado (`pg_cron`, 04:17 UTC). **Produção com 001–016.*** ✏️ *10/11, `LGPD-12`: a **017** (consentimento destacado) trava a gravação pela sessão sem o consentimento; aplicá-la **junto com o release** é o `LGPD-13`.* ✏️ *10/11, release #121: a **017** aplicada e conferida logo antes do merge. **Produção com 001–017.*** ✏️ *11/11, release #127: a **018** (`CAL-03`) aplicada e conferida antes do merge. **Produção com 001–018.***
- **Release de 10/11** (PR #121, `ddd6041`): 017 aplicada pelo autor e conferida por consulta (colunas, função, gatilho e travas de gravação e pareamento verdadeiros; versão `2026-11-10`). Deploy Vercel com sucesso; `/health` `200`, banco ok e modelo `ml-inf-cabeca-v2`; consentimento, inferência e lote sem credencial `401`; bundle publicado contém a tela e a versão. Medido nesta máquina em 10/11. Captura enviada pelo autor mostra a tela autenticada com a caixa marcada e o botão habilitado; o autor confirmou que ele desabilita com a caixa desmarcada. Após concordar, o autor relatou que a coleta iniciou; captura em 1 s mostra 0 registros. ✏️ *11/11 (consulta do autor): 2 contas com o consentimento vigente e 941 leituras gravadas depois do release; o primeiro expurgo agendado rodou (`succeeded`, 04:17 UTC). `REL-01` e `LGPD-13` fechados. **Não medido:** o tempo por leitura do lote (`API-06`).* Diário, 10/11 (xiii) e 11/11 (v).
- **Release R4, 13/11** (PR #178, `6b8e52a`): `AUTH-09` — o JWT do usuário validado localmente pelo JWKS do projeto (só ES256; `iss`, `aud`, `role`, `sub` e `exp` exigidos; chave conhecida vale até 24 h se a renovação do JWKS falhar); sem efeito no site, `CI-09`. Sem migração; dependências novas PyJWT 2.15.1 e cryptography 50.0.2. Conferido: `/health` `200`; `401` sem token, com `Bearer` inválido, com HS256 forjado e com `kid` inexistente (este último prova que a função alcança o JWKS). **Latência de `/api/sleep-history?limite=1`, 20 pedidos com a sessão do autor, do navegador dele:** mediana 130 → **113 ms**, p90 148 → 142 ms; todos `200`. Janela de revogação: o token vale até expirar (3 600 s). Diário, 13/11 (xiii).
- **Release R3, 13/11** (PR #174, `3d50f27`): `SEC-19` (a ingestão só com a `SUPABASE_INGESTAO_KEY`; sem ela, ingestão e `/health` em `503`) e `SEC-20` (CSP por hash e cabeçalhos de segurança); sem efeito no site, `CI-10` e `SEC-13`. Sem migração. Conferido: `/health` `200` (a chave de ingestão configurada), contrato 2.9.0, `gru1`; os cinco cabeçalhos no `/`, `/login`, landing e `/health`; a CSP contra as páginas servidas, 10 de 10 hashes; rotas sem token, `Bearer` inválido e token de dispositivo falso `401`. **Login do autor:** landing, painel e Histórico carregaram. Diário, 13/11 (x).
- **Release R2, 13/11** (PR #168, `2fbf17d`): `UI-30` (o Histórico percorre a janela por cursor, até 16 páginas, com "página N de até 16" e consulta de confirmação no teto); sem efeito no site, o firmware `FW-15`/`FW-16` (já na placa) e o `CI-12`. Sem migração, backend intacto. Conferido: `/health` `200`, contrato 2.9.0, `gru1`; rotas sem token `401`; o texto do progresso no pacote publicado. **A medir no login do autor:** o tempo do Histórico de 7 e de 30 dias (acima de ~10 s em 30 dias, o resumo no servidor vira item).
- **Release R1b, 12/11** (PR #161, `96d934c`): `APP-15` (falha ao listar as noites com "Tentar novamente"), `UI-28` (teclado no consentimento e no tema) e `UI-27` (aviso da primeira janela da coleta) — PRs #148–#150 do Codex. Sem migração, backend intacto. Conferido: `/health` `200`, contrato 2.9.0, `gru1`; rotas sem token `401`; os três textos novos no pacote publicado. **Não conferido:** o login real depois deste release.
- **Release R1, 12/11** (PR #157, `ed11e81`): `DATA-15` (histórico paginado por cursor, CSV completo), `API-08` (503 na falha do banco), `UI-26` (sessão da borda "Parcial"), `UI-29` (legenda), e o firmware `FW-12`/`FW-13` (sem efeito no site). Sem migração. Conferido: `/health` `200`, contrato 2.9.0, `gru1`; rotas sem token `401`; o pacote publicado com `cursor_tempo`, "Cobertura parcial" e a legenda nova. **Login real do autor:** o Histórico de 7 dias passou de 3 sessões (1 000 leituras) para 13 (2 000, o teto do painel), com a sessão mais antiga marcada "Parcial" — o `DATA-15` e o `UI-26` funcionando, e o `UI-30` confirmado: a janela de 7 dias já passa de 2 000 leituras.
- **Release de 12/11, segunda parte** (PR #142, `5f5f209`): o frontend do protótipo (painel, coleta, dispositivos, histórico, configurações; PRs #134–#139). Sem migração, backend intacto. `/health` `200`, contrato 2.9.0, `gru1`, `401` sem token; login real do autor ok. **Na conta real, o Histórico de 7 dias já bate no teto de 1 000 leituras: o `DATA-15` está confirmado em produção.**
- **Release de 12/11** (PR #133, `e788090`, feito com o Codex): a landing nova (`frontend/public/landing-prototipo.html` num iframe isolado; `/?apresentacao=leve` para a versão leve) e o código do `FW-11` (só firmware: na placa, com o `FW-07` (c)). Conferido pelo Claude depois: `/health` `200`, contrato 2.9.0, modelo carregado, `gru1`; o HTML sem recurso externo, rede nem armazenamento, e o texto sem promessa de diagnóstico. **Não estava no diário até 12/11 (viii).**
- **Release de 11/11** (PR #127, `64529e8`): o `CAL-03` (autocalibração, contrato **2.9.0**) e o `INFRA-05`. A **018** foi aplicada pelo autor antes do merge e conferida (colunas `g_norma` e `calibrada`, restrição, as duas funções gravando, a trava do consentimento mantida): **produção com 001–018**. Conferido depois do deploy: `regions: ["gru1"]`; `/health` `200` com `"contrato_de_dados": "2.9.0"` e o modelo; rotas sem credencial `401`; `/privacidade` `200`, com a §2.3 nova no pedaço da página. **Não confirmado:** o login de verdade. A calibração só chega ao celular com o APK novo (`APP-12`). Diário, 11/11 (ix).
- **URLs do Supabase Auth** (03/11, `AUTH-06`): Site URL `https://dormio-smart.vercel.app`; Redirect URLs `https://dormio-smart.vercel.app/**` e `http://localhost:5173/**`. Configuração **do painel**, não do repositório: um `redirectTo` fora dessa lista é descartado sem aviso, e o link do e-mail cai na Site URL. Até 03/11 a Site URL era a padrão (`http://localhost:3000`), e o "esqueci minha senha" levava ao `localhost`. Previews da Vercel não estão na lista.
- **Release de 03/11** (PR #47, `95e61e6`): leva o `SEC-15` (o firmware confere o certificado), o `FW-10` (sono até um prazo) e o `make laco`. Não muda o site: nenhum arquivo do backend nem do frontend. Conferido depois do deploy `7527355605`: `/health` `200`, rotas de ingestão sem credencial e com token inválido → `401`, `Bearer` inválido → `401`; o monitor rodou a partir de `main` (execução `41694832434`) e o passo novo aceitou a cadeia TLS da Vercel contra as raízes do firmware. O autor confirmou o login.
- **Segundo release de 01/11** (PR #42, `6e7a934`): leva o `API-04` — bug do servidor nas rotas de ingestão responde `500` sem expor a exceção, e não `400` (que fazia o firmware descartar a leitura). Conferido depois do deploy `7477881275`: `/health` `200`, rotas de ingestão sem credencial e com token inválido → `401`, `Bearer` inválido → `401`, e o autor confirmou o login. Não exercitados na produção: o `500` (não há como provocar um bug lá) e o `415` (a autenticação vem antes do corpo).
- **Release de 01/11** (PR #39, `f3ce2bf`): leva o `AUTH-08` — Auth ou banco fora do ar responde `503` e não desloga; só recusa de credencial é `401`. Conferido depois do deploy: `/health` `200`, `Bearer` inválido → `401` (a recusa real do Supabase classificada como recusa), e o autor confirmou o login. Não exercitado na produção: o `503` com o Auth fora do ar.
- **Chaves do backend em produção** (01/11, `SEC-14`): a ingestão usa a `SUPABASE_INGESTAO_KEY` (papel `dormio_ingestao`, vence em 1 ano), com a `anon` no `apikey`. A **`SUPABASE_SERVICE_ROLE_KEY` não existe mais na Vercel**, em nenhum ambiente: se a chave de ingestão falhar, o `/health` vai a `503` em vez de cair para acesso total. Previews ficam sem ingestão (`503` no `/health`). Release #32 (`80a56c5`).
- **Release de 31/10** (PR #29, `3618c67`): leva a correção do login (`AUTH-07`) — o login voltava para `/login` desde o release de 29/10. Deploy de produção `success`, `/health` `200`, o bundle publicado contém a correção, e o autor confirmou o login no site. ⚠️ A conferência pós-release precisa incluir **um login de verdade**: `/health` e rotas sem credencial não pegaram este defeito.
- **Release de 30/10** (PR #20, `fa5f164`): produção com o backend do contrato **2.7.0** — `/health` `200`, banco ok, `"contrato_de_dados": "2.7.0"`, medido daqui depois do deploy; `POST /api/data/lote` e `GET /api/features` respondem `401` sem credencial. Nenhuma leitura com vetor foi gravada na produção ainda.
- **Observações:** funções serverless no Vercel têm cold start; o `app` precisa estar disponível no import (ver Decisões técnicas).
