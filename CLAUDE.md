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
- **Web-app (backend):** Python · Flask 3.1 · Supabase (Postgres + Auth, com RLS) · Gunicorn · deploy no Vercel
- **Frontend:** React 18 · TypeScript · Vite · vitest · `@supabase/supabase-js`
- **ML:** Python 3.11 · numpy · pandas · scipy · scikit-learn — versões **pinadas** em `ml/requirements.txt`. O bloco de ML está fechado (ver backlog, "Concluído").

### Documentos de referência

**Ler no início de toda sessão, nesta ordem** (✏️ ordem trocada em 2026-10-27; antes era o
`ROADMAP.md`, que é gitignorado e organiza por prioridade, não por dependência):

1. **`docs/BACKLOG-COMPLETO.md`** — o que está pendente, organizado por dependência (L0–L3). É o que responde *"o que trava o quê?"*.
2. **`docs/DIARIO-DE-ENGENHARIA.md`** — registro cronológico do que foi feito, **incluindo o que deu errado**. Procedência primária de tudo: onde outro documento divergir dele, o diário vence.
3. **`docs/LICOES-APRENDIDAS.md`** — os padrões de falha que este projeto já demonstrou, com o checklist do §9. **Ler antes de propor qualquer coisa.**
4. **`docs/CORRECOES-APLICADAS.md`** e **`docs/PENDENCIAS-ABERTAS.md`** — **gerados** por `scripts/consolidar_registro.py`; não editar à mão (o `--conferir` reprova).

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

1. **Todo trabalho é registrado no diário**, no formato das entradas existentes (os sete campos
   fixos), **incluindo o que deu errado**.
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
| Backend (Flask) | `cd web-app && pytest --ignore=tests/rls` | **390 passam** ✏️ *(31/10, `SEC-14`: +6)*; antes **384 passam** ✏️ *(30/10, branch do `DATA-07b`; eram 316 no `API-03` e 293 em 28/10)* |
| Frontend | `cd frontend && npx vitest run` | **422 passam, 28 arquivos** ✏️ *(31/10, `AUTH-07`: +4 do `AuthContext.test.tsx`)* |
| Tipos e build | `cd frontend && npm run build` (`tsc --noEmit && vite build`) | `tsc` limpo; `vite build` ok (avisa do chunk único — `UI-15`) |
| RLS (Postgres real) | `DORMIO_RLS_DATABASE_URL=... pytest tests/rls` | **158 passam** contra `postgres:16` em Docker ✏️ *(30/10, `DATA-07b`: +7 da migração 010; eram 151 em 28/10)*, com a base imitando os privilégios padrão do Supabase (`SEC-12`) — **pulam** sem a variável, de propósito |
| Mutação do RLS | `python web-app/tests/rls/verificar_por_mutacao.py` | **32/32 sabotagens detectadas** |
| Diagnóstico e ordem das migrações | `DORMIO_RLS_DATABASE_URL=... python web-app/tests/migracoes/verificar_migracoes.py` | os 10 estados (30/10, com a 010) e a ordem real da produção; 3/3 sabotagens acusadas em 28/10, e a da 010 (função que grava nulo) em 30/10 |
| ML | `cd ml && .venv/Scripts/python -m pytest testes` | **126 passam** ✏️ *(30/10, branch do `FW-07`: +19 do dourado da cadeia C2)* |
| Mutação do dourado | `cd ml && .venv/Scripts/python testes/verificar_vetor_dourado_por_mutacao.py` | **12/12**, e o ponto cego registrado segue cego |
| Firmware | `cd firmware/nucleo && make && make sintaxe capacidade mutacao mutacao-cadeia mutacao-fila` | **341 + 157 + 135 + 456 + 84 verificações, 0 falhas; 4/4 sketches e a ponte da flash compilam, e o `sketch.ino` liga com o núcleo; mutação 15/15; mutação da cadeia C2, do payload, da época da grade e do rádio 23/23; mutação da fila e do envio 13/13** (em contêiner `gcc:13`, 31/10) ✏️ *(30/10, `FW-07` e `DATA-07b`: entraram os alvos `c2` e `cadeia`; 31/10, `FW-08`: o alvo `fila`, e o `capacidade` passou a validar `firmware/partitions.csv`)* |
| Conferências de documento | `python scripts/<nome>.py --conferir` para `calculos_tcc`, `estudo_buffer`, `conferir_docs_versionados`, `consolidar_registro` | todas passam |

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

**CI:** `.github/workflows/ci.yml`, seis jobs: `test` (backend), `rls` (matriz Postgres 14 e
16, mais mutação na 16), `frontend` (vitest, tsc, vite), `ml`, `firmware` e `documentos`.
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
- **Health check:** ✏️ **existe desde o `WEB-04`** — `GET /health`, sem autenticação, respondendo `200` quando o banco está alcançável e `503` quando o app está de pé e o banco não. A linha anterior ("ainda não existe — criar um endpoint simples é item de roadmap") foi corrigida em 17/10 pelo `DOC-11`, junto com a da seção "Testes".
- **Monitor da produção** (`INFRA-03`, 28/10): `.github/workflows/saude-producao.yml` chama o `/health` a cada 3 dias por `scripts/conferir_producao.py` e reprova se o banco não responder. ⚠️ O Supabase é do **plano gratuito e pausa depois de uma semana sem uso** — foi o que derrubou a produção até 28/10; se o job reprovar, a primeira coisa a olhar é o painel do Supabase. O agendamento só roda a partir de `main`; o workflow está lá desde o release de 29/10 (execução manual `40818265459` passou). ✏️ *31/10: a primeira execução **agendada** rodou e passou (`41214122394`, 15:17 UTC — o cron é 09:17, e o GitHub atrasou seis horas); `INFRA-03` fechado.*
- **Banco de produção** (diagnóstico de 30/10): migrações 001–010 **todas aplicadas** (a 002 desnecessária), na ordem real 001, 003–006, 008, 009, 007, 010. Migração nova: aplicar no SQL Editor e rodar `web-app/migrations/DIAGNOSTICO-migracoes-aplicadas.sql`. ✏️ *30/10: a **010** (`DATA-07b`) foi aplicada antes do release, como exigia o `DATA-07f`.*
- **Chaves do backend em produção** (01/11, `SEC-14`): a ingestão usa a `SUPABASE_INGESTAO_KEY` (papel `dormio_ingestao`, vence em 1 ano), com a `anon` no `apikey`. A **`SUPABASE_SERVICE_ROLE_KEY` não existe mais na Vercel**, em nenhum ambiente: se a chave de ingestão falhar, o `/health` vai a `503` em vez de cair para acesso total. Previews ficam sem ingestão (`503` no `/health`). Release #32 (`80a56c5`).
- **Release de 31/10** (PR #29, `3618c67`): leva a correção do login (`AUTH-07`) — o login voltava para `/login` desde o release de 29/10. Deploy de produção `success`, `/health` `200`, o bundle publicado contém a correção, e o autor confirmou o login no site. ⚠️ A conferência pós-release precisa incluir **um login de verdade**: `/health` e rotas sem credencial não pegaram este defeito.
- **Release de 30/10** (PR #20, `fa5f164`): produção com o backend do contrato **2.7.0** — `/health` `200`, banco ok, `"contrato_de_dados": "2.7.0"`, medido daqui depois do deploy; `POST /api/data/lote` e `GET /api/features` respondem `401` sem credencial. Nenhuma leitura com vetor foi gravada na produção ainda.
- **Observações:** funções serverless no Vercel têm cold start; o `app` precisa estar disponível no import (ver Decisões técnicas).
