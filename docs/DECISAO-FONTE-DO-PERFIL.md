# Decisão — qual é a fonte de verdade do perfil

> **Item:** `PERFIL-01`. Fecha também o `LGPD-04`, por outro caminho que o previsto.
> **Data:** 2026-10-17. **Decidido por:** Vitor Mendes Oliverio.
> **Procedência do diagnóstico:** diário de 2026-10-17 (iii); `docs/LICOES-APRENDIDAS.md`
> §5 ocorrência 4; migração `001` linha 125; migração `006` linhas 151 e 169.
>
> Este arquivo existe porque a decisão tem uma parte que **não** é código e que, se não
> ficar escrita, volta como defeito silencioso: *com dois lugares guardando o nome, qual
> deles manda?*

---

## 0. Uma correção de rótulo, antes de tudo

O enunciado da decisão veio como *"saída (B) — tornar `profiles` fonte de verdade — e usar a
coluna `idade`"*. No `docs/BACKLOG-COMPLETO.md`, a saída que torna `profiles` canônica é a
**(A)**; a **(B)** é a oposta (Auth canônico, `profiles` encolhe para âncora de eliminação,
`idade` sai por migração).

Seguiu-se a **descrição em prosa**, não a letra: ela é inequívoca, foi dada duas vezes na
mesma frase ("tornar `profiles` fonte de verdade" e "usar a coluna `idade`"), e as duas
metades só são consistentes entre si na saída (A) — na (B) a coluna `idade` deixaria de
existir. Fica registrado aqui para que ninguém, lendo "(B)" no diário, conclua que o
projeto removeu a coluna.

**Portanto: implementada a saída (A) do `PERFIL-01`.**

---

## 1. O problema, em uma frase

`public.profiles` tem duas colunas (`nome`, `idade`) que nada de produção lê, e
`auth.users.raw_user_meta_data.nome` tem o nome que o aplicativo de fato exibe. Tornar
`profiles` canônica **inverte** essa relação, e inverter cria a pergunta que o backlog
nomeou como o maior custo da saída (A):

> *"uma segunda escrita no fluxo do `UI-11` — com o segundo modo de falha que vem junto
> (gravou no Auth, falhou em `profiles`, e agora os dois divergem e nada diz qual vale)."*

O que segue é a resposta, e ela **não** é "sincronizar com cuidado".

---

## 2. A decisão: três regras, em ordem de precedência

### Regra 1 — Leitor único

**Nada no aplicativo lê `user_metadata.nome`.** O nome exibido, em qualquer tela, vem de
`profiles.nome`, por `GET /api/me/perfil`.

Isto é o que resolve a divergência, e é a única parte que *precisa* ser verdade. Divergência
entre duas cópias só é ambiguidade quando **as duas são lidas**: é aí que "qual vale?" não
tem resposta. Com um leitor único, a outra cópia não é um segundo valor em disputa — é
resíduo. Resíduo tem um problema (seção 4), e o problema do resíduo **não é a correção da
tela**.

A Regra 1 não é um conselho. É verificada por
`frontend/src/fonteDoNomeDoPerfil.test.ts`, que varre `src/` e reprova se `user_metadata`
aparecer em linha de código. Validada por controle positivo (seção 7).

### Regra 2 — Destino único por campo

Cada campo tem **um** destino de escrita, e nunca dois:

| Campo | Onde é gravado | Por quê |
|---|---|---|
| `nome` | `profiles`, via `PATCH /api/me/perfil` | é dado de perfil |
| `idade` | `profiles`, via `PATCH /api/me/perfil` | idem |
| `email` | Supabase Auth, via `updateUser` | é **credencial de acesso**, não perfil: troca por link de confirmação, com o desfecho `email-pendente` que o `UI-11` já modelou |

O modo de falha que o backlog previu para a saída (A) — *"gravou no Auth, falhou em
`profiles`, e agora os dois divergem e nada diz qual vale"* — **não existe neste desenho, e
não por cuidado na ordem das chamadas: por não haver campo com dois destinos.** A tela
continua fazendo duas chamadas a dois serviços, como já fazia desde o `UI-11`, mas nenhuma
delas escreve o mesmo dado que a outra. `nome` não pode divergir de si mesmo porque só
existe um lugar onde ele é escrito e um lugar de onde é lido.

Um desfecho parcial continua possível (nome e idade gravados, e-mail pendente ou com erro) —
e esse já era o caso desde o `UI-11`, já tem estado com nome próprio e já é relatado campo
por campo. O que mudou é só **para onde** vai a metade do perfil.

### Regra 3 — `user_metadata.nome` é insumo de criação, e nada mais

A cópia no metadado **continua existindo**, com um papel único e declarado: é o valor
digitado no cadastro, lido **uma vez**, para semear `profiles.nome`.

Semear acontece em exatamente dois pontos, e os dois são a mesma operação:

1. **No cadastro**, pelo gatilho `handle_new_user` (migração `001`).
2. **No reparo**, quando `GET /api/me/perfil` encontra a linha ausente (seção 3).

Depois da semeadura, o metadado nunca mais é lido — pela Regra 1 — e, na primeira correção
de nome, é **limpo** (seção 4).

#### Por que o metadado não pode simplesmente sair do cadastro

Seria a solução categórica: um único lugar desde o início, e nenhuma cópia para administrar.
Não dá, e o motivo está no código:

`lib/autenticacao.ts` chama `signUp` e, **com confirmação de e-mail ligada, `signUp` não
devolve sessão** (`temSessaoImediata`). Sem sessão não há `auth.uid()`, e sem `auth.uid()` a
policy `profiles_insert_own` nega a escrita — o cliente **não pode** inserir o próprio
perfil no momento do cadastro. As alternativas seriam escrever por papel privilegiado
(recusada: o enunciado deste item exige o cliente do usuário) ou pedir o nome de novo depois
do primeiro login (perde o nome que a pessoa já digitou, e deixa a saudação vazia até ela
reparar).

O gatilho é `security definer` e não depende de sessão. Ele fica — e **fica por razão
conferida no artefato, não por inércia.**

#### Por que o gatilho não pode ser removido mesmo que o nome saísse de lá

`apagar_minha_conta()` devolve `perfil_apagado: v_perfis > 0` (migração `006`, linha 169), e
`descreverRecibo` em `frontend/src/lib/conta.ts` mostra "o perfil" ao titular com base nesse
campo. Sem o gatilho, uma conta que nunca editou o perfil não teria linha em `profiles`, e o
recibo de eliminação passaria a dizer, com toda a razão técnica e nenhuma utilidade, que
nenhum perfil foi apagado. O gatilho é o que mantém o `perfil_apagado` significando alguma
coisa.

---

## 3. O que acontece na criação de conta — e o caso que o diagnóstico já viu

**Fluxo normal:** `signUp` com `options.data.nome` → gatilho `handle_new_user` insere
`(id, nome)` em `profiles` → primeira carga de tela faz `GET /api/me/perfil` e lê dali.
`idade` nasce nula, e nulo é um estado válido e declarado (seção 5).

**O caso que não é hipotético:** `web-app/migrations/DIAGNOSTICO-perfil-nao-criado.sql`
existe no repositório porque **já aconteceu** usuário criado com `profiles` vazio — o gatilho
não existia no projeto, e o bloco 3 daquele arquivo é literalmente *"ZERO LINHAS AQUI =
causa confirmada"*, com um reparo manual embaixo.

Isso é decisivo para esta decisão, e é o tipo de coisa que só aparece abrindo a pasta de
migrações. Com `profiles` canônica, **linha ausente deixa de ser detalhe de esquema e passa
a ser nome em branco na tela** — degradação silenciosa (§7 das lições: *o dado fica ausente
ou fica errado-com-cara-de-certo?*). Aqui ficaria ausente, o que é o lado aceitável, mas
ainda assim é regressão visível causada pela mudança.

Duas saídas foram consideradas:

| Saída | Por que não / por que sim |
|---|---|
| **Fallback de leitura:** se a linha falta, ler o metadado | ❌ Reintroduz o segundo leitor, e com uma condição — "leitor único, **exceto** quando a linha falta". Invariante com cláusula de exceção é exatamente o que apodrece: alguém, um dia, usa o fallback para outra coisa. |
| **Reparo na leitura:** se a linha falta, `GET` a cria, semeada pelo metadado, e devolve já criada | ✅ É a mesma semeadura da Regra 3, no único momento em que ela ainda faz sentido. Depois dela o invariante vale sem exceção, e nenhum consumidor a jusante precisa de ramo de fallback. |

**Escolhida a segunda.** `GET /api/me/perfil` tem efeito colateral — e é idempotente, o que
é a propriedade que de fato importa num `GET`. Está dito no docstring da rota, porque um
`GET` que escreve sem avisar é armadilha para quem lê o código depois.

---

## 4. Como a divergência é impedida de voltar

Depois da primeira correção de nome, o metadado guardaria o nome **antigo**. Ninguém o lê
(Regra 1), então nenhuma tela fica errada. Mas o problema que sobra não é de corretude:

> O titular exerceu o art. 18, III (correção de dado inexato). O valor inexato continua
> armazenado em `auth.users`, sem finalidade — a semeadura já ocorreu e não ocorre de novo.
> Isso contraria o próprio art. 18, III e a minimização do art. 6º, III.

Por isso a tela **limpa o resíduo**: depois de o `PATCH` ter sucedido, e **somente** depois,
`EditarPerfil` chama `updateUser({ data: { nome: null } })`.

Três propriedades deste passo, porque é o ponto onde um desenho descuidado recriaria o
problema que a seção 2 eliminou:

1. **Não é a escrita autoritativa, e não pode ser confundida com ela.** Ela acontece *após* a
   gravação em `profiles` ter respondido com sucesso. Se ela falhar, a correção **aconteceu**
   — e a tela diz que aconteceu, porque aconteceu. Confirmação pessimista (§6 das lições) se
   aplica ao que é afirmado: afirmamos a correção porque ela foi verificada, e **não**
   afirmamos a limpeza, que vai num campo próprio do resultado.
2. **É retentável sem estado.** Cada correção de nome bem-sucedida tenta de novo. E a
   exclusão de conta remove a linha de `auth.users` inteira, quando o `GRANT` existe.
3. **Limpa em vez de sincronizar.** Gravar o nome novo nos dois lados manteria duas cópias
   atuais e nada dizendo qual manda — reconstruindo a ambiguidade e duplicando dado pessoal
   para sempre. Limpar deixa **uma** cópia e torna a Regra 1 autoevidente: o campo passa a
   valer `null`, e um `null` não pode ser confundido com fonte de verdade.

Por que no cliente e não no backend: `updateUser` age sobre a **sessão** do chamador. O
cliente do Flask (`cliente_do_usuario`) só autentica o PostgREST (`client.postgrest.auth(jwt)`);
`client.auth` não tem sessão. Fazer isso no servidor exigiria a API de administração, isto é,
papel privilegiado — recusado pelo enunciado do item e pelo `SEC-06`. O navegador é o único
lugar onde essa escrita acontece com a credencial do próprio titular.

---

## 5. Para que serve `idade`

**A resposta honesta tem duas partes, e a segunda é mais importante que a primeira.**

**Finalidade declarada:** dizer ao titular se a idade dele está **dentro ou fora da faixa
das coortes em que os métodos citados por este trabalho foram validados**. É um aviso de
aplicabilidade, e as faixas não são inventadas aqui — saem das coortes que o repositório já
cita:

| Coorte | Faixa | Onde está citada |
|---|---|---|
| Walch et al., 2019 | 31 adultos | `docs/ML-DATASETS-E-PLANO.md` §tabela |
| Li; Halaki; Chow, 2025 | 16 mulheres, 51,4 ± 4,2 anos | idem |
| Meredith-Jones et al., 2024 | 137 participantes, 8 a 16 anos | idem, e `docs/LIMITACOES-TCC.md` X.2 |
| Conley et al., 2019 (agrupado) | subgrupo de adultos saudáveis, 18 estudos, n = 461 | `docs/ML-DATASETS-E-PLANO.md` |

Implementada em `frontend/src/lib/aplicabilidade.ts`, com teste. É **função pura de uma
faixa documentada**, não cálculo clínico.

**O que `idade` NÃO faz, e está dito assim na política:** não entra em conta nenhuma. Não
pondera métrica, não estratifica série, não alimenta modelo, não altera limiar. Ela decide o
texto de um aviso, e mais nada.

Essa distinção é o ponto. Declarar que a idade "estratifica a análise de sono" seria a
finalidade que soa melhor — e seria **finalidade declarada que o código não cumpre**, que é o
§6 das lições na forma mais barata de cometê-lo: um parágrafo numa política de privacidade,
que não tem como ficar vermelho. Se um dia a idade entrar em cálculo, isso é **finalidade
nova** e exige declaração nova, antes e não depois. Está no backlog como `LGPD-06`.

**Por que não "apenas cadastral":** um dado pessoal coletado para existir no cadastro não
sobrevive ao art. 6º, III — é literalmente o que o `LGPD-04` descreve. "Cadastral" seria a
finalidade mais fácil de escrever e a menos defensável das duas.

**Três consequências que vêm junto, e nenhuma é cosmética:**

1. **`idade` é opcional, e permanece opcional.** Nulo é estado de primeira classe: sem idade,
   o aviso de aplicabilidade simplesmente não aparece. Um campo obrigatório para alimentar um
   aviso seria coleta desproporcional à finalidade.
2. **A §2.4 da política de privacidade afirma hoje que a idade NÃO é coletada.** Essa frase
   deixa de ser verdadeira no instante em que a tela grava o campo. Corrigida no mesmo
   commit, com nota de procedência — é o mesmo erro de classe do `UI-10`, em que três
   documentos afirmavam o que o código não fazia, e aqui seria a versão inversa: o código
   fazendo o que o documento nega.
3. **Idade autodeclarada pode revelar que o titular é criança ou adolescente** (art. 14 da
   Lei 13.709/2018, que exige melhor interesse e, para criança, consentimento de um dos pais
   ou responsável legal). O sistema **não verifica idade e não trata idade declarada de menor
   de forma diferente hoje.** Isso é lacuna, está dita como lacuna na política e virou o item
   `LGPD-05` — e é **decisão do Vitor**, não deste trabalho de implementação: a alternativa
   (restringir a maiores de 18 no cadastro) é mudança de produto.

---

## 6. O que a decisão custou em código

| Onde | O que mudou |
|---|---|
| `web-app/migrations/008_perfil_como_fonte_de_verdade.sql` | ⚠️ **a aplicar no Supabase** — `updated_at` que se mantém, teto de tamanho do nome, e os comentários que declaram o papel de cada coluna |
| `web-app/perfil.py` | validação e acesso, pelo cliente do usuário. **`update` + `insert`, e não `upsert`** — ver a nota abaixo |
| `web-app/routes.py` | `GET`/`PATCH /api/me/perfil` |
| `web-app/database.py` | `nome_do_metadado` — a única leitura do metadado no servidor, e só no reparo |

> ⚠️ **A nota do `update` + `insert`, porque não é escolha de estilo: é um defeito de perda
> de dado que foi medido na especificação antes de chegar a produção.**
>
> O `upsert` do PostgREST manda `insert ... on conflict do update set <...>`, e a pergunta
> decisiva é **o que acontece com as colunas que o corpo não traz**. A resposta está na
> documentação do PostgREST (v12.2, *Prefer Header → Missing*), literal:
>
> > *"When doing POST and PATCH requests, **any missing columns in the payload will be
> > inserted as `null` value by default**. To use the `DEFAULT` column value instead, use the
> > `Prefer: missing=default` header."*
>
> Upsert é um `POST`. E `postgrest.base_request_builder.pre_upsert` só manda
> `missing=default` quando `default_to_null=False` — e o padrão do cliente é `True`, ou seja,
> **o header não vai**. A cadeia fecha: `PATCH {"idade": 30}` → `upsert({id, idade})` →
> coluna ausente tratada como `null` → **`nome` do titular apagado, com `200` na resposta.**
>
> Na tela de **correção** de dado pessoal, que existe para cumprir o art. 18, III. É o §7 das
> lições (degradação silenciosa) com o §6 em cima (confirmação antes da verificação), e
> **nenhum teste com dublê pegaria**: o dublê é o nosso cliente, não o PostgREST — que roda
> no Supabase e não neste repositório.
>
> Com duas instruções separadas não há o que supor: cada uma leva exatamente as colunas do
> corpo, e os dois casos ficaram presos em SQL contra Postgres real — *"alterar só a idade
> não apaga o nome"* e o simétrico. Os testes de `upsert` **alheio** continuam, porque aquele
> é o comando que um atacante pode mandar direto ao PostgREST, e o que se afirma ali é que
> ele é recusado.
>
> **O que isto custou de aprendizado, e é o motivo de estar escrito aqui e não só no código:**
> a docstring do cliente Python diz que o comportamento de campo ausente *"só se aplica a
> upsert em lote"*, e foi ela que quase encerrou a análise — tranquilizadora e sobre outra
> coisa (ela descreve o `columns`, não o `missing`). A especificação do **servidor** diz o
> oposto. Ler a biblioteca e concluir sobre o serviço é o §5 das lições numa variante nova:
> não é documentação velha, é **a documentação da camada errada**.
| `frontend/src/lib/perfil.ts` | nome e idade saem do Auth e vão para a rota; e-mail fica |
| `frontend/src/lib/aplicabilidade.ts` | a finalidade da seção 5, implementada |
| `frontend/src/contexts/PerfilContext.tsx` | um leitor, compartilhado entre a saudação e a tela de edição |
| `frontend/src/components/Sidebar.tsx` | para de ler o metadado |
| `frontend/src/fonteDoNomeDoPerfil.test.ts` | a Regra 1, como catraca |
| `docs/POLITICA-DE-PRIVACIDADE.md` | §2.1, §2.4, §3, §6.3, §9 e lacunas |
| `docs/LGPD-ELIMINACAO.md` | o `LGPD-04` e o que o recibo promete |
| `docs/diagramas/DIAG-04-modelo-de-dados-e-seguranca.md` | o modelo ER, que era o motivo de decidir antes |

---

## 7. Como cada verificação nova foi provada capaz de reprovar

§1 e §4 das lições: nenhuma verificação entra sem provocar o defeito de propósito.

| Verificação | Sabotagem aplicada | Reprovou? |
|---|---|---|
| `fonteDoNomeDoPerfil.test.ts` | leitura de `user_metadata.nome` reintroduzida no `Sidebar` | ver §Controles do diário de 17/10 (iv) |
| idem — guarda do próprio instrumento | varredura apontada para pasta vazia | idem |
| `test_perfil.py` — adversarial de rota | rota reescrita para aceitar `user_id` do corpo | idem |
| `test_rls_isolamento.py` — `upsert` alheio | `profiles_insert_own` com `with check (true)` | idem |

---

## 8. O que esta decisão não resolve

Registrado para que a ausência não passe por completude.

- **O ponto cego do `UI-11` continua aberto.** Os dublês exercitam a orquestração deste
  código, não o comportamento do Supabase. Vale para a limpeza de resíduo da seção 4:
  **não está provado que `updateUser({data:{nome:null}})` apaga a chave** em projeto real —
  só que o nosso código a chama depois do `PATCH` e não deixa a falha dela contaminar o
  relato. Fecha com projeto Supabase de teste, junto com o resto do `UI-11`.
- **Não há teste de componente** (`UI-17`). `EditarPerfil` ganhou um campo e um aviso novos, e
  nenhum teste prova que eles aparecem na tela. O `alcance.test.ts` prova caminho de
  `import`, não renderização — e é por isso que o campo de idade tem a lógica inteira em
  `lib/`.
- **A migração `008` não foi aplicada.** Até ela rodar no Supabase, `updated_at` de
  `profiles` continua congelado na criação e o teto de tamanho do nome não existe no banco.
  A rota funciona sem ela; o que falta é o que está escrito aqui.
