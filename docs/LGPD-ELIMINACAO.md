# Direito de eliminação — texto para a seção de LGPD do TCC

Rascunho para a seção de conformidade. Tom acadêmico, terceira pessoa.
Item de backlog: **SEC-07**. Implementação em
`web-app/migrations/006_direito_de_eliminacao.sql` e `web-app/routes.py`.

---

## Parágrafo principal

> O direito de eliminação previsto no art. 18, VI, da Lei nº 13.709/2018 foi
> implementado no nível do banco de dados, e não apenas na camada de aplicação.
> Três granularidades foram disponibilizadas ao titular: a exclusão de leituras
> individuais, a de um dispositivo pareado e a da conta por completo. As duas
> primeiras operam por políticas de *Row Level Security* restritas ao próprio
> registro (`sleep_data_delete_own` e `profiles_delete_own`, ambas condicionadas
> a `user_id = auth.uid()`); a terceira, por meio da função
> `apagar_minha_conta()`, que remove em uma única transação as leituras, os
> dispositivos, o perfil e o registro de autenticação do titular, nessa ordem —
> ditada pelas chaves estrangeiras, de modo que nenhuma interrupção intermediária
> deixe registros órfãos. A função não recebe parâmetro de identificação: o
> titular é obtido exclusivamente de `auth.uid()`, derivado do token de sessão
> validado, o que torna estruturalmente impossível que uma sessão legítima seja
> usada para eliminar os dados de outro usuário. Optou-se pela exclusão efetiva
> dos registros, e não por sua anonimização, porque séries temporais de
> acelerometria noturna não são razoavelmente anonimizáveis — a própria série
> constitui identificador quando cruzada com outras fontes — e porque o art. 12
> da mesma lei retira de seu alcance apenas o dado efetivamente *anonimizado*,
> de sorte que o registro meramente desvinculado de seu titular, por conservar
> a possibilidade de reassociação, permanece dado pessoal e sujeito à disciplina
> legal. Registra-se
> que não foi concedida política de atualização sobre a tabela de leituras: a
> eliminação é direito do titular, enquanto a alteração de uma medição já
> registrada comprometeria a integridade do conjunto experimental sem produzir
> qualquer efeito verificável externamente.

## Parágrafo complementar, sobre verificação

> A efetividade das políticas foi verificada por testes automatizados
> executados contra uma instância real de PostgreSQL, com as migrações do
> projeto aplicadas, e não contra simulacros da camada de acesso. Os testes
> incluem, para cada operação, o caso adversarial correspondente — a tentativa
> de eliminar registros pertencentes a outro titular — e o caso de uso legítimo,
> este último necessário para descartar a hipótese de que as negativas
> decorressem de falha de configuração do ambiente de teste. Verificou-se
> adicionalmente, por análise do catálogo do banco, que a função de exclusão
> permanece sem parâmetro de identificação e inacessível às credenciais
> anônima e de ingestão. A suíte é submetida a validação por mutação: dezoito
> alterações deliberadamente incorretas do esquema são aplicadas e se confirma
> que cada uma é detectada, procedimento que impede que o conjunto de testes
> passe a atestar garantias que deixou de verificar.

## Ressalva que precisa constar

> Registra-se uma limitação de implementação: a tabela de autenticação
> (`auth.users`) é gerenciada pela plataforma utilizada e o privilégio de
> exclusão sobre ela não está disponível em todas as configurações de projeto.
> Quando ausente, a operação elimina integralmente os dados de tratamento —
> leituras, dispositivos e perfil — e informa ao titular, na própria resposta,
> que o registro de acesso permanece e depende de remoção administrativa. Optou-se
> por explicitar a eliminação parcial em vez de reportar conclusão integral, e
> por não contornar a limitação por meio da API administrativa da plataforma,
> o que exigiria reintroduzir credencial de alto privilégio em um fluxo de
> usuário — precisamente o acoplamento removido no item SEC-06.

---

## Notas para você, não para a banca

- ✅ **Numeração conferida em 2026-09-29**, contra o texto da Lei 13.709/2018.
  **E estava errada**: o texto dizia *art. 18, V* para eliminação, quando o
  inciso V é **portabilidade** — eliminação é o **VI**. A troca aparecia em
  onze lugares do repositório (aqui, no `DATA-CONTRACT.md`, no
  `BACKLOG-COMPLETO.md`, no `routes.py`, no `database.py`, na migração `006` e
  em quatro arquivos de teste) e foi corrigida em todos.
- ✅ **`art. 13, §4º` trocado pelo `art. 12` em 2026-09-30.** A citação antiga
  existia e era onde a pseudonimização está definida, mas o artigo inteiro trata
  de *estudos em saúde pública* — e, conferido no Planalto, o §4º abre com
  **"Para os efeitos deste artigo"**, ou seja, a própria lei limita aquela
  definição ao art. 13. Usá-lo sozinho para sustentar "dado pseudonimizado
  continua sendo dado pessoal" era frouxo por escrito na lei, não só por
  contexto. O parágrafo principal agora se apoia no **art. 12**, que retira do
  alcance da lei apenas o dado **anonimizado** — e só quando a anonimização não
  seja reversível com esforços razoáveis (art. 12, *caput* e §1º): por
  contraste, o pseudonimizado permanece dentro. Mesma troca feita no
  `docs/DATA-CONTRACT.md` e no cabeçalho da migração `006`, que repetiam a
  formulação antiga. O `docs/POLITICA-DE-PRIVACIDADE.md` já usava a nova.
- ✅ **Varredura completa do repositório em 2026-09-30.** Toda citação de artigo
  da Lei 13.709/2018 fora de referência bibliográfica foi conferida contra o
  texto no Planalto. As demais estão corretas:

  | Citação | Confere? |
  |---|---|
  | art. 6º, III — necessidade (minimização) | ✅ `LGPD-04`, seção 9 da política — ✏️ **ver a nota de 17/10 ao fim deste arquivo: a base mudou** |
  | art. 7º, I — consentimento · art. 7º, IV — estudos por órgão de pesquisa | ✅ |
  | art. 12 — anonimizado fora do alcance da lei | ✅ |
  | art. 16 — eliminação após o término do tratamento | ✅ |
  | art. 18, I e II — confirmação e acesso | ✅ |
  | art. 18, III — correção | ✅ `UI-11` |
  | art. 18, IV — anonimização, bloqueio ou eliminação de dado excessivo | ✅ |
  | art. 18, V — portabilidade | ✅ |
  | art. 18, VI — eliminação | ✅ (ver ressalva abaixo) |
  | art. 18, VII, VIII e IX — compartilhamento, negativa, revogação | ✅ |
  | art. 19 — prazo de atendimento | ✅ |
  | art. 33 e seguintes — transferência internacional | ✅ |
  | art. 13, §4º — pseudonimização | ⛔ trocado pelo art. 12 (acima) |

  `docs/ML-DATASETS-E-PLANO.md` e `docs/SINTESE-PESQUISA-E-CAMINHOS.md` também
  contêm a abreviação "art.", mas como número de artigo de periódico
  (`Sensors` 18(10) art. 3441, `IJBNPA` 21(1) art. 40) — não são citações legais
  e ficaram fora da varredura de propósito.
- ⚠️ **O art. 18, VI é mais estreito do que o texto acima sugere.** O inciso lê
  *"eliminação dos dados pessoais tratados **com o consentimento** do titular"*.
  Isso fecha com a política atual, que declara consentimento (art. 7º, I) como
  base legal. **Mas o `LGPD-01` deixou em aberto** a possibilidade de a base
  migrar para o art. 7º, IV (*estudos por órgão de pesquisa*), se o projeto for
  a comitê de ética. Se isso acontecer, o art. 18, VI deixa de ser o fundamento
  direto e o apoio passa a ser o **art. 18, IV** combinado com o **art. 16** —
  e este parágrafo, mais as onze ocorrências do repositório, precisam ser
  revistos de novo. Fica registrado para não ser redescoberto na banca.
- A ressalva sobre `auth.users` **só se aplica se o seu projeto não tiver o
  privilégio**. Rode a verificação nº 4 do rodapé da migration 006 e veja o
  que dá. Se der `true`, corte a ressalva inteira — ela descreve um problema
  que você não tem.
- O número "dezoito" no parágrafo de verificação é a contagem atual dos
  sabotadores. Se acrescentar mais, atualize — ou troque por "diversas", que
  não envelhece.
- Não escrevi nada sobre prazo de atendimento do pedido (art. 19) porque a
  exclusão aqui é imediata e automática. Se a banca perguntar, esse é o
  argumento: não há prazo porque não há intermediação humana.
- ✅ **A interface existe desde 29/09** (`UI-10`): *Configurações → Excluir
  conta*, com confirmação por frase e tela própria para o desfecho parcial. A
  linha abaixo ficou obsoleta e está mantida só para o histórico ficar legível.
  > ✏️ **Correção de 2026-10-17.** "Existe desde 29/09" estava errado, e a
  > linha obsoleta abaixo estava **mais certa que esta** por dezoito dias. O
  > componente `ExcluirConta` foi commitado em 29/09 (`916e210`) e **nenhum
  > arquivo versionado o importava**: a eliminação continuou existindo "como
  > rota, e só" até a montagem em 17/10 (`22a9268`), porque as três linhas que
  > a põem na tela ficaram numa árvore de trabalho não commitada. Os 23 testes
  > do item são de `lib/` e passavam com o componente inalcançável. A data
  > honesta da interface é **17/10**; a de 29/09 é a do componente. Ocorrência
  > registrada no §6 de `docs/LICOES-APRENDIDAS.md`; o mecanismo que faltava é
  > o `UI-17`.
  >
  > ✏️ **19/10: o mecanismo existe agora, nas duas metades.** O
  > `frontend/src/alcance.test.ts` (17/10) reprova quando um módulo de `src/`
  > sai do grafo de `import`; o `frontend/src/montagem.test.ts` (19/10) monta o
  > aplicativo pelo ponto de entrada de produção e **reprova quando o
  > `<ExcluirConta />` sai do JSX das Configurações** — inclusive quando o
  > `import` fica no lugar, que é o caso em que a catraca de alcance passa.
  > Medido: removida a tag, cai o teste que a nomeia, e o `alcance.test.ts`
  > continua verde. Também está presa a **barreira de duas etapas**, não só o
  > botão: o campo de confirmação não existe antes do clique e existe depois.
  > A frase acima — *"o mecanismo que faltava"* — podia ficar verdadeira para
  > sempre sem que ninguém notasse, e é por isso que esta nota tem data.
- Falta a parte de interface: hoje a eliminação existe como rota, e só. Está
  registrado como **UI-10** no backlog.

---

## ✏️ Nota de 2026-10-17 — o que o `PERFIL-01` muda neste arquivo

Três coisas, e a segunda é a que mais importa para a redação do TCC.

**1. `perfil_apagado` passou a significar mais do que significava.** O texto
acadêmico acima diz que a função remove "as leituras, os dispositivos, o perfil
e o registro de autenticação". Era verdade e era **quase vazio**: até hoje a
linha de `profiles` continha um `nome` que o aplicativo não lia e uma `idade`
sempre nula, então `perfil_apagado: true` relatava a remoção de uma linha sem
conteúdo em uso. Com `profiles` como fonte de verdade (`PERFIL-01`), aquela
linha passa a conter **o nome exibido e a idade autodeclarada** — o recibo
continua dizendo a mesma frase e ela passou a ser substantiva. Nada a corrigir
no texto; vale registrar que o seu alcance aumentou.

> E vale notar o inverso, porque era o risco da outra saída do `PERFIL-01`: se a
> coluna `nome` tivesse sido **removida** (a saída que recomendava encolher a
> tabela), `perfil_apagado` passaria a reportar a remoção de uma linha vazia, e
> o recibo prometeria mais do que entrega. Era exatamente a ressalva registrada
> no item, e ela deixou de ser necessária.

**2. A minimização (art. 6º, III) mudou de fundamento, e o `LGPD-04` fechou por
onde não se esperava.** A tabela de citações acima marca o art. 6º, III como
conferido, apontando para o `LGPD-04` — cuja tese era que `profiles.idade` era
coluna morta e devia **sair por migração**. A coluna não saiu: ela passou a ser
coletada, com finalidade declarada, opcional e retirável pelo titular. O que
sustenta a conformidade com aquele artigo, portanto, **não é mais a ausência do
dado, e sim a existência de uma finalidade cumprida por código**
(`frontend/src/lib/aplicabilidade.ts`) — ver a seção 3 da política de
privacidade e `docs/DECISAO-FONTE-DO-PERFIL.md` §5.

A diferença é material numa banca: "não coletamos" é uma defesa; "coletamos para
isto, e isto acontece" é outra, e a segunda exige poder mostrar o que acontece.

**3. Entrou uma lacuna nova, e é de produto.** Coletar idade autodeclarada pode
revelar que o titular é criança ou adolescente, e o **art. 14** da Lei
13.709/2018 impõe tratamento próprio — melhor interesse, e consentimento de um
dos pais ou responsável no caso de criança. **O sistema não verifica idade e não
trata de forma diferente a idade declarada de menor de 18 anos.** Está declarado
como limitação na seção 2.1 da política e registrado como `LGPD-05`. Não é
implementação pendente: é decisão a tomar (restringir o cadastro, exigir
consentimento de responsável, ou manter a lacuna declarada enquanto o protótipo
tiver um usuário).

| Citação nova | Confere? |
|---|---|
| art. 14 — dado de criança e adolescente | ⚠️ citado como **lacuna declarada**, não como implementado (`LGPD-05`) |
| art. 18, IV — retirada da idade pelo titular | ✅ seção 6.5 da política, campo em branco apaga o dado |
