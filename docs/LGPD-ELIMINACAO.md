# Direito de eliminação — texto para a seção de LGPD do TCC

Rascunho para a seção de conformidade. Tom acadêmico, terceira pessoa.
Item de backlog: **SEC-07**. Implementação em
`web-app/migrations/006_direito_de_eliminacao.sql` e `web-app/routes.py`.

---

## Parágrafo principal

> O direito de eliminação previsto no art. 18, V, da Lei nº 13.709/2018 foi
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
> constitui identificador quando cruzada com outras fontes — e porque o art. 13,
> §4º, da mesma lei equipara o dado pseudonimizado ao dado pessoal. Registra-se
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

- **Confira a numeração dos artigos** antes de entregar. Estou citando de
  memória: art. 18, V (eliminação) e art. 13, §4º (pseudonimização equiparada
  a dado pessoal). Valem uma olhada no texto da lei.
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
- Falta a parte de interface: hoje a eliminação existe como rota, e só. Está
  registrado como **UI-10** no backlog.
