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
  | art. 6º, III — necessidade (minimização) | ✅ `LGPD-04`, seção 9 da política |
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
- Falta a parte de interface: hoje a eliminação existe como rota, e só. Está
  registrado como **UI-10** no backlog.
