# AGENTS.md — instruções para agentes de código neste repositório

> **Versionado desde 2026-11-05.** Lido automaticamente pelo Codex. As regras de engenharia do
> projeto estão no [`CLAUDE.md`](CLAUDE.md) e **valem integralmente para qualquer agente**; este
> arquivo não as repete — acrescenta o que é preciso para **dois agentes trabalharem em paralelo**
> (o Codex e o Claude Code) sem conflito. Onde os dois divergirem, vale o `CLAUDE.md`.
> **Repositório público:** nada que entre aqui pode conter segredo, nome de pessoa ou caminho de
> máquina.

## Antes de qualquer trabalho

1. Ler, nesta ordem: [`CLAUDE.md`](CLAUDE.md), [`docs/BACKLOG-COMPLETO.md`](docs/BACKLOG-COMPLETO.md),
   o fim de [`docs/DIARIO-DE-ENGENHARIA.md`](docs/DIARIO-DE-ENGENHARIA.md) e
   [`docs/LICOES-APRENDIDAS.md`](docs/LICOES-APRENDIDAS.md) (o checklist do §9).
2. **O autor indica o item.** Plano apresentado e aprovado antes de implementar.
3. **Nunca fazer merge, nem push em `develop` ou `main`.** Toda entrega é uma PR para `develop`,
   revisada antes do merge. Commits sem `Co-Authored-By`.

## Divisão do trabalho

4. **Cada item tem um dono, combinado com o autor antes de começar.** Divisão de partida:
   - **Codex:** ML (inclusive o `ML-13`, DREAMT), bugs de backend e de frontend, testes.
   - **Claude Code:** textos do TCC e arquivos de inserção, firmware, cálculos, releases e a
     integração das PRs.

   Item fora da sua área: perguntar ao autor antes.
5. **IDs novos:** antes de criar um item (`HW-xx`, `ML-xx`…), conferir em `origin/develop`
   atualizado que o ID está livre, e dizer ao autor qual vai usar. Dois itens com o mesmo ID
   quebram o backlog.

## Branches, worktrees e PRs

6. **Uma worktree por item**, fora do checkout principal do repositório — que é onde o Claude Code
   trabalha. Nunca editar nem commitar no checkout principal. Encontrou trabalho não commitado lá:
   perguntar ao autor.
7. **Branch sempre a partir de `origin/develop` atualizado.** Antes de pedir o merge, trazer o
   `develop` para a branch (`git merge origin/develop`), resolver os conflitos e rodar de novo:

   ```bash
   python scripts/conferir_backlog.py --conferir
   python scripts/consolidar_registro.py --conferir
   python scripts/conferir_docs_versionados.py
   ```

   A PR chega à revisão **sem conflito com `develop`**.
8. **Trabalho que depende de outra PR ainda aberta parte da branch dela, mas a PR aponta para
   `develop`** — nunca para a outra branch (regra do `CLAUDE.md`, "Gitflow estrito"). A ordem de
   merge vai escrita no corpo da PR.

## Os arquivos de conflito garantido

`docs/DIARIO-DE-ENGENHARIA.md`, `docs/BACKLOG-COMPLETO.md` (linha **Contagem:**, notas de
contagem, quadro em uma tela, caminho crítico) e a tabela de testes do `CLAUDE.md`. Neles:

9. **Entrada de diário sempre no fim**, imediatamente antes de `# O que este diário não cobre`,
   precedida de `---`, com a data e um sufixo — `(i)`, `(ii)`… — se já houver entrada naquele dia.
10. **A nota de contagem diz sobre que commit de `develop` foi calculada.** Contagens escritas em
   branches paralelas valem para a base delas, não para a sequência integrada.
11. **Nunca editar a linha ou a entrada de outro item**, a não ser para fechá-lo como parte do
   próprio trabalho — e então dizer isso na PR.

## O que conta como verificado

12. **Diário com os oito campos, cada um no seu lugar:** O problema · Hipótese · O que foi testado ·
   Resultado medido · Adaptação · **O que deu errado no caminho** · Risco em aberto · Procedência.
   Erro de comando, caminho errado, sandbox, permissão vão em "O que deu errado", não em
   "Adaptação". Se não houve erro: "Nada nesta etapa".
13. **Controle positivo se executa, não se herda.** Ao retomar trabalho de outra sessão ou de outro
   agente, reexecutar as sabotagens antes de fechar o item. Nunca fechar com "a sessão anterior
   relatou".
14. **Testes novos falham sem a correção.** Rodar os testes novos contra o código de `develop` e
   registrar quantos falham: é a prova de que testam o defeito.
15. **Dispersão, não só média.** Quando um resultado diverge, informar a maior diferença por
   participante ou por célula, além da média.
16. **Separar o que rodou do que foi lido, e dizer em que máquina rodou** (prática 4 do `CLAUDE.md`).

## Dados e pastas locais

17. **Junctions para dados brutos.** Se uma worktree ou pasta de execução tiver junction para
   `ml/dados/bruto`, desfazer o link com `rmdir <caminho>` — **sem `/s`**, que remove só o link —
   **antes** de copiar, mover ou apagar a pasta. `cp`, `Remove-Item -Recurse` e a remoção de
   worktree podem seguir o link (`LICOES-APRENDIDAS.md`, §5, ocorrência 10). Para copiar
   evidência: `robocopy <origem> <destino> /E /XJ`, conferindo arquivo a arquivo. Ao terminar uma
   execução, registrar no relatório onde ficam os dados locais e se há junctions.
18. **Dados brutos e dados com termo de uso nunca entram no Git** (`ml/dados/` é ignorado). O
   DREAMT, em particular, proíbe redistribuição.
19. **Não versionar material do autor** que não esteja no Git, como `esquemaEletrico/`, nem os
   arquivos locais listados no `CLAUDE.md` (`ROADMAP.md`, `CLAUDE.local.md`…).

## Texto do TCC

20. **Não editar o documento do TCC.** Atualizações vão para `../documento/` (fora do Git), em
   `INSERCAO-<item>-<tema>.md`, com o texto atual ao lado do novo. Há duas cópias do "Produto 5";
   confirmar com o autor qual é a vigente.
