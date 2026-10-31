# Correções aplicadas — Smart Dormio

> **Gerado por `scripts/consolidar_registro.py`.** Não edite este arquivo
> à mão: o `--conferir` do script reprova se ele divergir da tabela de
> dados, e documento gerado e editado à mão mente sobre a própria
> procedência. Para mudar o conteúdo, mude a tabela `DEFEITOS` no script.
>
> **Fonte:** `docs/DIARIO-DE-ENGENHARIA.md` (procedência primária),
> `docs/LICOES-APRENDIDAS.md` (o mesmo material por padrão de falha), o
> histórico do git e os itens fechados do `docs/BACKLOG-COMPLETO.md`.
> Onde este arquivo e o diário divergirem, **o diário vence.**

Este arquivo existe para servir ao **capítulo de desenvolvimento**. A
pergunta que ele responde não é *o que foi consertado* — isso o `git log`
já responde — e sim **por qual instrumento cada defeito apareceu**, que é
a única coisa aqui que sustenta uma afirmação de método.

---

## Resumo quantitativo

**130 correções registradas**, todas sustentadas no repositório.

**A unidade de contagem, dita antes dos números, porque ela decide como
lê-los.** Uma linha deste arquivo é **uma correção**: um defeito, uma
causa, uma correção. Em 4 linhas, porém, a causa e a correção foram
uma só e os defeitos foram vários — `DADOS-02` (10), `REF-01` (4), `GIT-06` (14), `SEC-12` (2) —, e agrupá-las foi deliberado,
porque separá-las contaria a mesma correção várias vezes. **Contando
defeito em vez de correção, o total seria 156.** Este
arquivo usa **130**, que é o número menor e o mais defensável.

**Fora da contagem, e visível:** 1 linha(s) — `ML-04b` —,
em que a hipótese se confirmou e o que se corrigiu foi a afirmação
que se podia extrair do resultado, não um defeito. Estão na seção da
área, marcadas ⛔, e não entram em número nenhum deste arquivo.

### Por área

| Área | Correções |
|---|---:|
| Segurança | 19 |
| Interface | 23 |
| Firmware | 18 |
| Dados e ML | 24 |
| Documentação | 23 |
| Infraestrutura | 23 |
| **Total** | **130** |

### Por instrumento — o campo que dá valor a este arquivo

| Como foi encontrado | Correções | O que o instrumento é |
|---|---:|---|
| **leitura** | 28 | Inspeção do código ou do documento, raciocinando sobre ele. Nada roda, nada se confere contra terceiro. |
| **cálculo** | 4 | Aritmética sobre os próprios números do projeto. O mais barato de todos, e derrubou premissas grandes. |
| **execução** | 49 | Rodar código do projeto — suíte, job, compilador, script — e a **saída** acusar. O defeito não estava escondido: estava não exercitado. |
| **controle positivo** | 13 | Provocar o defeito de propósito e exigir que a verificação acuse. Inclui verificação por mutação. **É o único instrumento que mede o alcance de uma verificação.** |
| **inventário** | 21 | Conferir estado declarado contra estado real: `grep` por símbolo, `git ls-files` contra o disco, varredura de afirmações em documentos. |
| **terceiro** | 11 | Especificação, documentação oficial, artigo, issue ou API de terceiro. O artefato que decide a resposta está **fora** do repositório. |
| **dado real** | 3 | Só apareceu com o arquivo ou a medição real em mãos. |
| **uso real** | 1 | Alguém usou o produto como usuário. |
| **Total** | **130** | |

### As três derivações que os números sustentam

> ⚠️ **São derivação nossa, não medição de nada.** O denominador é a
> tabela deste arquivo, isto é, *o que o projeto registrou* — e o próprio
> `LICOES-APRENDIDAS.md` adverte, na seção do que não cobre, que os
> padrões de instrumento são **provavelmente subcontados, porque só se
> descobre instrumento defeituoso quem procura**. A mesma ressalva vale
> aqui, e com um agravante: defeito que nunca foi encontrado não aparece
> em tabela nenhuma. **Nenhuma destas três frases é uma taxa de defeitos
> do projeto; são proporções do que foi achado.**

**(1) Exercitar achou perto do dobro do que ler.**
Execução, controle positivo e uso real somam **63 de 130**
registros (48%). Leitura e cálculo — os dois
instrumentos que não precisam rodar nada — somam **32** (24%). A razão é de **2,0 para 1**.

Com a ressalva que impede a leitura fácil: isto **não** diz que ler é
pouco útil. Diz que, neste projeto, leitura e execução acharam classes
**diferentes** de defeito — a leitura achou lógica errada (o `201` sem
gravar, a medição esperando pela rede, o sketch de uma amostra por boot),
e a execução achou **alcance** insuficiente. Alcance não se vê lendo, e é
por isso que a razão é essa e não o contrário.

**(2) 14 correções tinham a causa fora do repositório.**
Fonte de terceiro e dado real somam **14 de 130** (10%) — defeitos cuja causa não está em nenhuma
linha deste projeto, e que **nenhum teste daqui poderia pegar**: a
especificação do PostgREST, a unidade do Empatica em `g/64`, o valor de
uma chave num painel do Supabase, a API do Actions, os coeficientes do
`scipy`. É a justificativa quantitativa das regras 6 e 8 do §5 das lições
(*comportamento de serviço se confere na especificação do serviço*;
*conclusão condicionada a configuração não fecha por leitura*) — e o
motivo pelo qual o item mais repetido deste projeto é **um projeto
Supabase de teste**, que deve a quatro itens e desde 28/10 tem item próprio
(`INFRA-02`).

**(3) As próprias verificações do projeto estavam defeituosas
26 vezes — e 24 dessas 26 só apareceram
rodando ou sabotando.**
São **26 de 130** registros (20%) em que a coisa errada era um teste, uma
guarda de CI, um harness de mutação ou um vetor de referência — não o
código. A distribuição:

| Instrumento que achou | Verificações defeituosas |
|---|---:|
| controle positivo | 12 |
| execução | 12 |
| terceiro | 1 |
| leitura | 1 |

As duas que sobram da conta são as que valem mais. **Uma** foi pega por
leitura — o `CI-05`, cuja especificação não podia reprovar porque
`actions/checkout` monta a árvore a partir do commit; foi raciocínio, e
foi o mais barato de todos. **A outra** veio de fonte de terceiro: os
coeficientes de referência do filtro, escritos de memória, que faziam o
teste reprovar código correto até serem conferidos contra o `scipy`.

**Então a regra honesta não é *não confie em leitura*.** É que leitura
pega alcance quando se faz a pergunta certa — *em que máquina isto
ficaria vermelho?* —, e essa pergunta funcionou exatamente uma vez em
26. Nas outras 25, o alcance só apareceu quando
alguém tentou fazer a verificação falhar.

### Procedência

| Procedência | Correções | O que significa |
|---|---:|---|
| `completa` | 117 | Commit **e** artefato reabrível — teste, script, seção de documento. Dá para reconferir sem acreditar em ninguém. |
| `parcial` | 13 | Só a mensagem de commit, só a entrada de diário, ou correção em arquivo não versionado. Entra porque omitir seria pior, e entra **marcada**. |

**50 dos 130 defeitos revelaram que a premissa estava
errada** — não que o código estava errado. É a seção mais instrutiva deste
arquivo e tem lugar próprio no fim.

### O que foi deixado fora de propósito

Para a contagem não inflar, **não** entraram: funcionalidade entregue
(`AUTH-01..05`, `UI-01..07`, `DASH-01/02/05/06/10`, `APP-01/07/08`,
`BRAND-01/03`, `DEMO-01`, `SEC-04`, `WEB-04`, `DATA-01/04/05`, `CI-01`, o
bloco `ML-01..ML-08` como entrega); otimização sem defeito de corretude;
e endurecimento que não consertou comportamento errado. **Entregar o que
não existia não é corrigir defeito.**

**Entraram de propósito, e é escolha discutível:** defeito em *documento*
e defeito em *instrumento de medida*. Os dois entram porque, neste
projeto, são a maior parte do que o registro tem de instrutivo — uma
afirmação falsa numa política de privacidade e um vetor dourado que se
regrava sozinho são defeitos com consequência. Quem precisar da contagem
só de código filtra pela coluna de área.

---

## Segurança — 19 defeitos

*7 controle positivo · 5 terceiro · 4 leitura · 1 dado real · 1 execução · 1 uso real*

### 2026-08-20 · `AUTH-03`

**O defeito.** A leitura de dados não exigia JWT e não aplicava RLS por dono.

**Como foi encontrado.** *leitura* — O backend lia com privilégio de serviço; o dono da linha não entrava na consulta.

**A correção.** Leitura passa a exigir JWT e a aplicar RLS por dono.

**Commit.** `90e666c` · procedência **completa**

### 2026-08-25 · `SEC-06 / CALC-02`

**O defeito.** Sensor que responde ao I2C mas não mede virava movimento fabricado no banco.

**Como foi encontrado.** *dado real* — Registradores zerados são leitura válida para o código: `‖a‖` calculado sobre zeros produz número, não erro.

**A correção.** Guarda de leitura zerada no sketch — a leitura ruim falha em vez de virar dado.

**Nota.** Veio da sessão de 25/08: `‖a‖ = 56,5 m/s²` com a placa parada, `−11,6 °C`, ruído 30× o normal.

**Commit.** `c4d1976` · procedência **completa**

### 2026-08-28 · `SEC-07`

**O defeito.** Havia um caminho de leitura de `sleep_data` que ignorava o RLS.

**Como foi encontrado.** *leitura* — `get_latest_data` consultava com privilégio que contorna a policy.

**A correção.** O caminho foi removido, não corrigido — e a referência a ele na documentação caiu no commit seguinte.

**Commit.** `b3b31c7, a0a7152` · procedência **completa**

### 2026-09-28 · `SEC-05` 🔄

**O defeito.** A suíte que afirmava isolamento entre usuários rodava contra Supabase mockado — e mock não exercita policy nenhuma.

**Como foi encontrado.** *controle positivo* — A hipótese de que mock cobriria RLS caiu de saída: não há policy a exercitar num dublê.

**A correção.** Suíte reescrita contra Postgres de verdade, e submetida a verificação por mutação (o esquema é sabotado, uma vez por sabotador, e exige-se que a suíte acuse cada um).

**🔄 A premissa estava errada.** O trabalho afirmava isolamento entre usuários, e a prova disso era um mock. É o §4 das lições em sua forma mais grave: o instrumento não tocava no mecanismo que dizia cobrir.

**Commit.** `f1ef319` · procedência **completa**

### 2026-09-28 · `SEC-05`

**O defeito.** Um teste de RLS olhava só a primeira linha do resultado e passava por acidente.

**Como foi encontrado.** *controle positivo* — A asserção sobre a primeira linha é satisfeita por um resultado que vaza nas seguintes.

**A correção.** Corrigido por causa de uma sabotagem do verificador por mutação — não por revisão.

**Nota.** O defeito estava no instrumento, e o que o achou foi o instrumento que mede o instrumento.

**Commit.** `f1ef319` · procedência **completa**

### 2026-09-28 · `SEC-08 (primeiro)`

**O defeito.** A credencial do dispositivo vivia na tabela exposta ao cliente.

**Como foi encontrado.** *leitura* — `devices` é lida pelo frontend; o segredo estava numa coluna dela.

**A correção.** Credencial movida para fora da tabela exposta (migração `007`).

**Commit.** `3e38c9f` · procedência **completa**

### 2026-10-17 · `PERFIL-01`

**O defeito.** A migração `008` ampliava o que o papel `dormio_ingestao` pode executar, e o `SEC-06` existe para mantê-lo mínimo.

**Como foi encontrado.** *execução* — `create function` concede `EXECUTE` a `PUBLIC` por padrão no PostgreSQL. A migração criava `tocar_updated_at()` e o papel herdava o privilégio sem que nada o concedesse.

**A correção.** `revoke` explícito na própria migração.

**Nota.** Acusado por `test_o_papel_executa_exatamente_tres_funcoes` na primeira execução — o teste cujo docstring diz 'enumera o que ele PODE, para que ampliar apareça no diff'.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-17 · `PERFIL-01` 🔄

**O defeito.** `test_ana_nao_cria_profile_para_o_bruno` barrava pela chave estrangeira, não pela policy — e passava com a policy de `insert` escancarada.

**Como foi encontrado.** *controle positivo* — O teste inseria com um uuid inventado, para não colidir com a linha que o gatilho cria. Uuid inventado não existe em `auth.users`: o comando morria em `profiles_id_fkey` e nunca chegava ao RLS.

**A correção.** Terceira usuária real, sem perfil, para que o cenário tenha só um mecanismo capaz de recusar.

**🔄 A premissa estava errada.** Medido, não suposto: com `profiles_insert_own` em `with check (true)`, o teste continua passando — caem só os dois testes estruturais. O cenário que o teste queria montar era justamente o que o id falso tornava impossível.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-17 · `PERFIL-01`

**O defeito.** Dois barramentos em série escondiam um ao outro: o teste do `upsert` alheio anunciava cobrir duas policies e cobria uma.

**Como foi encontrado.** *controle positivo* — `upsert` contra vítima que já tem linha cai no ramo de `update`. Quem recusa é a policy de `update`, e a de `insert` escancarada passa despercebida.

**A correção.** Um teste por estado da linha de destino — um para a policy de `insert`, outro para a de `update`.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-17 · `PERFIL-01` 🔄

**O defeito.** Premissa de que policy de `UPDATE` sem `with check` seria mais frouxa — e não é.

**Como foi encontrado.** *controle positivo* — Sem `with check`, o PostgreSQL usa o `using` também como verificação da linha resultante. Remover a cláusula não abre a transferência de linha para outro dono.

**A correção.** A sabotagem ficou registrada com o alcance real: nenhum teste de acesso pode cair, quem detecta é o teste estrutural.

**🔄 A premissa estava errada.** Era premissa de quem escreveu o sabotador, não conferida, e o verificador por mutação a derrubou.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-19 · `PERFIL-01` 🔄

**O defeito.** A gravação do perfil apagaria o nome do titular num `PATCH` que só mandasse a idade — em silêncio, com `200`.

**Como foi encontrado.** *terceiro* — `upsert` do PostgREST é um `POST`, e a especificação v12.2 diz que coluna ausente do corpo é gravada como `null` salvo com `Prefer: missing=default` — header que o cliente Python só manda com `default_to_null=False`, que não é o padrão.

**A correção.** Não foi passar o header (o default de `profiles.nome` é nulo, daria no mesmo): a gravação virou `update` e, só se ele afetar zero linhas, `insert`. O `update` leva exatamente as colunas do corpo — semântica de SQL, não de serviço de terceiro.

**🔄 A premissa estava errada.** A hipótese de que o `upsert` não mexia no nome vinha da docstring do cliente Python, que fala de `columns` e não de `missing` — a camada errada, lida com atenção. E o ganho maior da correção é de testabilidade: com `upsert` a propriedade 'um PATCH de um campo não toca os outros' não tinha onde ser testada neste repositório; com SQL, tem.

**Commit.** `275665a` · procedência **completa**

### 2026-10-20 · `SEC-08` 🔄

**O defeito.** A tela de cadastro dizia quem tem conta: e-mail já cadastrado recebia 'Já existe uma conta com este e-mail.' — enumeração de e-mails com um formulário e nenhuma ferramenta.

**Como foi encontrado.** *uso real* — `traduzirErroDeAuth` decide por `codigo === c || texto.includes(t)`, e havia **dois** caminhos até a frase: por `code` (`user_already_exists`) e por `message` (`already registered`).

**A correção.** A frase saiu nos dois caminhos e virou condicional, no modelo do `recuperarSenha`. Os dois testes que exigiam a frase foram reescritos para afirmar o oposto, com controle positivo: devolvida a frase ao código, os dois reprovam.

**🔄 A premissa estava errada.** O `UI-19` havia concluído em 19/10, em negrito, que 'a proteção existe e não há vazamento', raciocinando que `cadastrar` não ramifica. O raciocínio está **correto sobre o código** e **falso sobre este projeto**: a resposta idêntica é o que o Supabase faz com a confirmação de e-mail LIGADA, e aqui ela está DESLIGADA. A premissa não conferida não era código — era o valor de uma chave num painel, artefato que não está no repositório, não aparece em `grep` e não dá para dublar.

**Commit.** `fd89e55` · procedência **completa**

### 2026-10-20 · `SEC-08` 🔄

**O defeito.** A saída recomendada pelo próprio item — ligar a confirmação de e-mail — não fecha o cadastro, e abre dois canais novos.

**Como foi encontrado.** *terceiro* — Com a confirmação ligada, `signUp` devolve 200 com `identities` vazio para endereço existente e populado para novo: o oráculo muda de lugar (status HTTP → campo JSON), não desaparece. A doc oficial é ressalvada — 'an error message that **attempts to** hide this information' — e a qualificação foi lida como garantia.

**A correção.** A recomendação mudou para a saída (B′): confirmação desligada até a banca, captcha no painel, sem proxy no Flask, e os quatro canais declarados em `LIMITACOES-TCC.md` X.7 com fonte e severidade calibrada (ASVS 5.0 § 6.3.8, Nível 3).

**🔄 A premissa estava errada.** É a ocorrência 10 do §1 das lições, e a variante mais incômoda: o **veredito** da análise anterior vinha de medição e estava certo; a **recomendação** vinha de uma frase de documentação de terceiro sobre um regime que o projeto nunca rodou, e estava errada. Mesmo parágrafo, mesmo negrito, procedência incomparável — e a recomendação é a única metade que alguém executa.

**Commit.** `4ca7fa3, 2fcb0f5` · procedência **completa**

### 2026-10-20 · `SEC-09`

**O defeito.** Dois comentários no código prometiam segurança inexistente.

**Como foi encontrado.** *terceiro* — O cabeçalho de `temSessaoImediata` afirmava que com a confirmação ligada 'os dois caminhos ficam indistinguíveis pelo cliente' (`identities` os distingue); o de `Login.tsx` afirmava que `recuperarSenha` 'responde idêntico com ou sem conta' (issue `supabase/auth` #2702 diz que não, em conteúdo, e a cheat sheet da OWASP exige uniformidade também em tempo).

**A correção.** Nenhuma linha de lógica mudou — o código já era o melhor alcançável do lado do cliente. Mudou a **afirmação**, com a frase da fonte citada inteira dentro do comentário.

**Nota.** Comentário que promete segurança inexistente encerra a análise de quem revisa, o que é pior que comentário nenhum.

**Commit.** `2fcb0f5` · procedência **completa**

### 2026-10-20 · `SEC-10`

**O defeito.** A retenção de credencial em conta não confirmada estava classificada como nota de rodapé do custo de uma alternativa, e é uma classe de ataque com nome próprio.

**Como foi encontrado.** *terceiro* — Enumeração é divulgação de informação; isto é acesso indevido a conta, com os dados de sono do titular dentro. Enterrar a segunda num parágrafo sobre a primeira esconde a diferença de dano — e **muda o sinal da decisão**: a saída (A) deixa de ser 'ganho parcial por custo alto' e passa a ser trocar um vazamento de informação por uma via de acesso indevido.

**A correção.** Promovida a item próprio (`SEC-10`), com a pré-condição explícita: se a saída (A) for adotada algum dia, isto se resolve antes ou junto, nunca depois.

**Nota.** Severidade declarada mais alta do projeto e evidência mais fraca: dois relatos de comunidade, um termo em doc oficial, um artigo para a classe, e **nada medido aqui**. A classificação 🟠 é da classe, não da confirmação, e está dito assim no item.

**Commit.** `2fcb0f5` · procedência **parcial**

### 2026-10-28 · `SEC-12` 🔄

**O defeito.** A chave pública (`anon`) executava as sete funções aplicadas na produção, e a `device_tokens` da 007 nasceria com todos os privilégios para o cliente.

**Como foi encontrado.** *controle positivo* — No Supabase, objeto criado pelo `postgres` em `public` nasce com privilégio NOMINAL para `anon` e `authenticated`; as migrações faziam `revoke ... from public`, que não alcança grant nominal.

**A correção.** Migração 009 (revoga nominalmente e muda o padrão de funções futuras) e a 007 revogando a própria tabela e função. Impacto medido localmente antes de corrigir: nenhum.

**🔄 A premissa estava errada.** Que objeto novo nasce sem privilégio. Verdade no Postgres puro, falsa no Supabase — e a configuração que decidia isso (`pg_default_acl`) não está no repositório.

**Nota.** Achado porque uma sabotagem do verificador de migrações não foi acusada; a causa da cegueira levou à configuração da produção.

**Commit.** `040fe4b` · procedência **completa**

### 2026-10-28 · `SEC-12`

**O defeito.** Catorze testes da suíte de RLS — os que afirmam o que `anon` e `authenticated` NÃO alcançam — passavam no vazio.

**Como foi encontrado.** *controle positivo* — A base de teste não reproduzia os privilégios padrão do Supabase: sem grant nominal para revogar, todo `revoke from public` parecia bastar.

**A correção.** `esquema_base.sql` passa a declarar os padrões medidos na produção; sem a 009 os 14 reprovam, com ela os 151 passam. Teste e dois sabotadores novos para o padrão: mutação 32/32.

**Commit.** `040fe4b` · procedência **completa**

### 2026-10-31 · `SEC-11`

**O defeito.** A seção X.7 de `LIMITACOES-TCC.md`, texto que vai ao documento final, dizia "Adotou-se proteção contra automação (captcha)" desde 20/10. O captcha nunca foi ligado, e o frontend não tem uma linha dele.

**Como foi encontrado.** *leitura* — O parágrafo foi escrito junto com a decisão (B′) do `SEC-08`, no tempo verbal de quem já tinha feito, enquanto a ação ficava aberta como `SEC-11`. Nada conferia a afirmação do texto contra o estado do item.

**A correção.** Parágrafo reescrito: a mitigação vigente é o limite de taxa por IP do serviço, com fonte; o captcha aparece como avaliado e não adotado, com o motivo.

**Nota.** Achado ao investigar o próprio `SEC-11`. É o §1 das lições na forma mais direta: uma defesa afirmada que não existe, no texto da banca.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (iii) do diário)` · procedência **parcial**

### 2026-10-31 · `SEC-11` 🔄

**O defeito.** O `SEC-11` mandava ligar o captcha no painel em "~5 min, sem linha de código", e o backlog o recomendava como a primeira coisa a fazer com cinco minutos. Com o captcha ligado o Supabase responde `400` a todo login e cadastro sem token, e o frontend não envia token.

**Como foi encontrado.** *terceiro* — A afirmação saiu da página de configuração do painel, sem ler o guia de integração nem o código do servidor. O guia diz que o frontend precisa mudar; o código mostra o `400`.

**A correção.** Item fechado sem fazer, com as fontes (`middleware.go`, `api.go`, o guia de limites de taxa); a linha de conselho do backlog riscada.

**🔄 A premissa estava errada.** O item foi para L3, "é por você", sob a premissa de que não havia software envolvido. Havia: as quatro chamadas de autenticação do frontend.

**Nota.** Dano evitado, não ocorrido: a chave nunca foi ligada. Se tivesse sido, a produção perderia login e cadastro até um deploy do frontend.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (iii) do diário)` · procedência **parcial**

---

## Interface — 23 defeitos

*9 execução · 7 leitura · 5 inventário · 2 controle positivo*

### 2026-06-03 · `FIX-06`

**O defeito.** O painel prometia 'Fase do Sono' e dados de ambiente que o projeto não mede.

**Como foi encontrado.** *leitura* — Rótulos herdados do protótipo visual, sem relação com o escopo declarado.

**A correção.** Fase do Sono → Status do Sensor; Ambiente → Do Chip; Aceleração Total → Movimento.

**Commit.** `17f4515` · procedência **completa**

### 2026-08-20 · `AUTH-02`

**O defeito.** A sidebar não mostrava a conta da sessão, e 'Sair' não encerrava a sessão de fato.

**Como foi encontrado.** *execução* — O estado exibido não vinha do provedor de sessão.

**A correção.** Sidebar lê a sessão, e 'Sair' encerra.

**Commit.** `6185c6e` · procedência **completa**

### 2026-08-21 · `BRAND-02`

**O defeito.** Os contornos internos das letras viraram recortes na logo vetorial.

**Como foi encontrado.** *execução* — Regra de preenchimento do SVG tratando contorno interno como furo.

**A correção.** Caminhos refeitos.

**Commit.** `72c59d3` · procedência **completa**

### 2026-08-21 · `BRAND-02`

**O defeito.** Um hex cru num comentário disparava a guarda de tokens de cor.

**Como foi encontrado.** *execução* — A guarda casava o padrão em qualquer posição do arquivo, inclusive em comentário.

**A correção.** O hex saiu do comentário.

**Nota.** Falso positivo de uma verificação, e vale registrar como tal: a guarda estava certa no propósito e larga no alcance.

**Commit.** `e2a8c36` · procedência **completa**

### 2026-08-21 · `UI-08`

**O defeito.** O caminho dos estáticos servidos sob `/frontend` estava errado, e o escape do regex no `vercel.json` também.

**Como foi encontrado.** *execução* — Dois erros de roteamento no build duplo (SPA + Flask).

**A correção.** Caminho e escape corrigidos em dois commits.

**Commit.** `508d064, a1acd55` · procedência **completa**

### 2026-08-21 · `UI-10 (mobile)`

**O defeito.** Rótulo que quebrava linha e eixo Y estreito no celular.

**Como foi encontrado.** *execução* — Largura do eixo calculada para desktop.

**A correção.** Polimento mobile.

**Commit.** `0d7cd32` · procedência **completa**

### 2026-08-21 · `UI-13`

**O defeito.** A chamada principal da landing levava a um painel vazio.

**Como foi encontrado.** *leitura* — O botão oferecia o painel a quem não tem dado nem conta.

**A correção.** A chamada deixou de oferecer painel vazio.

**Commit.** `146a2e7` · procedência **completa**

### 2026-08-22 · `UI-16 (revelação)`

**O defeito.** A animação de revelação ficava presa ao recarregar a página no meio dela.

**Como foi encontrado.** *execução* — A varredura pós-restauração tinha um só gatilho, e ele não disparava quando o navegador restaurava a posição de rolagem.

**A correção.** Segundo gatilho para a varredura pós-restauração.

**Commit.** `ae4f8a4, 1373703` · procedência **completa**

### 2026-08-24 · `APP-06`

**O defeito.** A coleta pelo celular falhava em silêncio em computador sem acelerômetro.

**Como foi encontrado.** *execução* — Ausência de sensor não produzia erro — produzia nada.

**A correção.** O caso passou a ser detectado e dito.

**Commit.** `efa5be0` · procedência **completa**

### 2026-08-24 · `DASH-07`

**O defeito.** A média do repouso estava contaminada por épocas de movimento, e o limiar era invisível no gráfico.

**Como foi encontrado.** *leitura* — A média era calculada sobre a série inteira, inclusive sobre o que ela deveria servir de referência para classificar.

**A correção.** Média do repouso recortada, e o limiar desenhado.

**Commit.** `a017551` · procedência **completa**

### 2026-08-25 · `APP-10`

**O defeito.** O X vermelho de falha aparecia enquanto a época ainda estava sendo enviada.

**Como foi encontrado.** *execução* — O estado 'enviando' não existia: havia só enviado e falhou.

**A correção.** Estado de envio próprio.

**Nota.** É o §6 das lições com o sinal invertido — desfecho anunciado antes de haver desfecho, só que para o lado pessimista.

**Commit.** `3cce0fa` · procedência **completa**

### 2026-08-25 · `APP-12`

**O defeito.** A tela de coleta falava a língua do desenvolvedor.

**Como foi encontrado.** *leitura* — Termos de implementação na interface do usuário.

**A correção.** Texto reescrito.

**Commit.** `826ea9f` · procedência **completa**

### 2026-08-28 · `DASH-09`

**O defeito.** O painel tratava ausência de dado como dado.

**Como foi encontrado.** *leitura* — Épocas sem medida entravam no cálculo como se tivessem medida.

**A correção.** Cobertura da medição explícita no painel.

**Commit.** `7407a05` · procedência **completa**

### 2026-08-28 · `DASH-11`

**O defeito.** O painel misturava 'quanto foi medido' com 'o aparelho parou', e tratava movimento como instante em vez de intervalo.

**Como foi encontrado.** *leitura* — Lacuna material e pausa por intervalo eram o mesmo estado no código.

**A correção.** Os dois separados, movimento como intervalo, recorte declarado.

**Commit.** `9d67bcf, 9d962f8` · procedência **completa**

### 2026-09-09 · `APP-13`

**O defeito.** A mensagem de falha de rede acusava a internet do usuário.

**Como foi encontrado.** *leitura* — Toda falha de requisição era atribuída à conexão de quem usa.

**A correção.** Mensagem que não atribui causa que não foi verificada.

**Commit.** `f4f77f5` · procedência **completa**

### 2026-10-17 · `UI-10` 🔄

**O defeito.** A tela de exclusão de conta estava inalcançável: `ExcluirConta.tsx` estava commitado com 23 testes passando e **nenhum arquivo versionado o importava**.

**Como foi encontrado.** *inventário* — As três linhas que o montam em `Settings.tsx` estavam presas numa árvore de trabalho não commitada desde 29/09, porque os *hunks* não se separavam do `DASH-13`.

**A correção.** Montado. E a correção de fundo é `frontend/src/alcance.test.ts`: percorre os `import` a partir de `main.tsx` e reprova quando um módulo de `src/` fica fora do grafo.

**🔄 A premissa estava errada.** Por dezoito dias o backlog dizia `UI-10 ✅`, o `LGPD-ELIMINACAO.md` dizia 'a interface existe desde 29/09' e a **política de privacidade dizia ao titular onde clicar** para exercer o art. 18, VI. Nada no repositório podia pegar: `tsc` não reclama de módulo não importado, o `vite build` poda o que não entra no grafo e segue verde, e os 23 testes são de `lib/`, então passavam com o componente desmontado.

**Commit.** `22a9268` · procedência **completa**

### 2026-10-17 · `DASH-12 / DASH-13` 🔄

**O defeito.** O painel versionado pedia 20 linhas ao backend e usava a hora de **chegada** como base de tempo — dez minutos de celular descritos como a noite.

**Como foi encontrado.** *inventário* — Os dois itens estavam feitos só do lado do servidor. O backend está commitado e testado desde 10/09; o cliente ficou na árvore de trabalho.

**A correção.** Cliente commitado: `captured_at` em `LeituraSono`, `instanteDaLeitura`, e `limite` enviado pelo painel e pela exportação.

**🔄 A premissa estava errada.** O `ROADMAP.md` declarava os dois '✅ corrigido em 2026-09-10', com descrição detalhada do que mudou. E o `ROADMAP.md` não é versionado — é por não ser versionado que ele pôde carregar um `✅` errado por seis semanas sem que nenhuma verificação o alcançasse (`GIT-05`).

**Commit.** `a586b0b` · procedência **completa**

### 2026-10-17 · `DASH-08`

**O defeito.** O painel não dizia de que instrumento veio a série, e havia trabalho pronto para isso que ninguém mencionava.

**Como foi encontrado.** *inventário* — `descreverDispositivo`, `descreverRecorte`, `tiposPresentes` e `serieMisturaTipos` estavam escritos e não commitados. A última era decisão documentada, com três testes, **ligada em lugar nenhum**.

**A correção.** Commitado. `serieMisturaTipos` foi ligada, mas não como porta de entrada do aviso: quem decide se ele *aparece* continua sendo `serieMisturaInstrumentos`; quem decide se ele *nomeia as classes* passou a ser `serieMisturaTipos`.

**Nota.** Apareceu na leitura uma assimetria registrada de passagem: a justificativa escrita de `serieMisturaInstrumentos` fala de 'um travesseiro e um celular', e a implementação é só `dispositivos.length > 1` — o alcance do código é mais largo que o do comentário.

**Commit.** `fea1c48` · procedência **completa**

### 2026-10-17 · `UI-11` 🔄

**O defeito.** A especificação do item estava errada: ela mandava gravar o perfil numa tabela que nada lê.

**Como foi encontrado.** *inventário* — A especificação dizia 'a policy de `update` em `profiles` já existe; falta a interface'. Um `grep` por `profiles` em código de produção devolveu **nada** — as únicas referências do repositório estavam em `web-app/tests/rls/`. O nome exibido vinha de `auth.users.raw_user_meta_data`.

**A correção.** Implementado pelo Supabase Auth, não pela tabela. A sincronização de `profiles` foi recusada de propósito e virou item próprio (`PERFIL-01`).

**🔄 A premissa estava errada.** Implementado conforme especificado, o item teria entregado uma tela em que a pessoa clica 'salvar', recebe 'dados atualizados', e o nome continua o mesmo — confirmação falsa (§6) produzida por premissa não conferida (§5), os dois padrões em série, cada um invisível a partir do outro. A conclusão prática do item ('é barato') estava certa **por acidente e pelo motivo errado**.

**Commit.** `2316b06` · procedência **completa**

### 2026-10-19 · `UI-17` 🔄

**O defeito.** A catraca de alcance provava `import` e o nome dela dizia 'alcance': passava com o provedor fora do JSX, com o componente fora da tela e com a rota ausente.

**Como foi encontrado.** *controle positivo* — `alcance.test.ts` percorre o grafo de `import` e para aí. Componente importado e nunca usado no JSX passa.

**A correção.** `frontend/src/montagem.test.ts`, 16 testes, que monta pelo `await import('./main.tsx')` — o ponto de entrada de produção. A alternativa idiomática (`render(<AuthProvider><PerfilProvider><App/></…>)`) reproduziria o defeito que existe para pegar, porque verificaria a composição escrita no teste.

**🔄 A premissa estava errada.** Medido por 11 sabotagens, 11 detectadas — e a coluna que importa: **em 5 das 5 sabotagens em que foi medido, o `alcance.test.ts` continuou verde**, inclusive com o `<PerfilProvider>` fora do `main.tsx` e o `<ExcluirConta />` fora do `Settings.tsx`, que é o defeito do `UI-10` refeito um nível acima. A catraca não estava errada: afirmava exatamente o que dizia afirmar, e o que dizia era menos do que se precisava.

**Commit.** `377482b` · procedência **completa**

### 2026-10-19 · `UI-17`

**O defeito.** Com o prazo padrão de 5 s, o primeiro teste de montagem estourava e o `createRoot` da montagem abandonada caía no `#root` do teste seguinte.

**Como foi encontrado.** *execução* — A primeira montagem paga a transformação de todo o grafo de `src/` pelo Vite (~13 s); o `import` em curso resolvia depois do `afterEach`.

**A correção.** Prazo de 60 s, com o motivo escrito ao lado da constante.

**Nota.** O sintoma foram oito falhas de 'useAuth precisa estar dentro de <AuthProvider>' **numa árvore em que o provedor estava lá** — um erro que manda procurar o defeito no lugar errado.

**Commit.** `377482b` · procedência **completa**

### 2026-10-19 · `UI-16` 🔄

**O defeito.** A varredura de exports mortos sub-relatava código morto: acusou `nomeDoDispositivo` como vivo.

**Como foi encontrado.** *controle positivo* — A varredura contava **frequência de identificador** e colidiu com uma `useState` local de mesmo nome em `pages/Coletar.tsx`, que não importa a função.

**A correção.** Refeita por **nome importado**. A premissa do `UI-16` está correta — e por pouco não ganhou uma 'correção' falsa.

**🔄 A premissa estava errada.** O instrumento estava errado na direção perigosa: um falso 'está vivo' encerra a investigação, e aqui ele contradizia a premissa de um item aberto.

**Commit.** `377482b, 9a40446` · procedência **completa**

### 2026-10-20 · `UI-16`

**O defeito.** `nomeDoDispositivo` era export morto com três testes próprios.

**Como foi encontrado.** *inventário* — O cabeçalho do painel passou a usar `descreverRecorte` (`DASH-08`), e a função antiga sobrou com uso só nos próprios testes.

**A correção.** Função e testes apagados — e não mantidos como 'a forma só o nome', porque dois caminhos para o mesmo rótulo convidam as duas redações a divergirem. O comentário que justificava 'Dispositivo desconhecido' migrou para o teste de `descreverRecorte`, onde o rótulo sobreviveu.

**Commit.** `9a40446` · procedência **completa**

---

## Firmware — 18 defeitos

*10 execução · 3 leitura · 2 cálculo · 1 terceiro · 1 controle positivo · 1 inventário*

### 2026-08-20 · `DATA-02` 🔄

**O defeito.** O critério de movimento era assimétrico: 52% menos sensível para baixo do que para cima.

**Como foi encontrado.** *cálculo* — `total > 11.0 || total < 8.0` sobre a magnitude bruta. Contra `g = 9,81`, o limite superior dispara a 1,19 m/s² de desvio e o inferior só a 1,81 m/s². Nada no código dizia que era intencional, porque não era.

**A correção.** Critério simétrico, `|‖a‖ − 9,81| > 1,2 m/s²`, preservando a sensibilidade do lado que já era o mais sensível. Declarado **provisório** no contrato de dados.

**🔄 A premissa estava errada.** O enunciado de partida era 'ajustar os dois limites', sob a premissa de que representavam a mesma sensibilidade. Uma subtração a derrubou. E a correção plantou o problema seguinte: o 1,2 herdou a autoridade de estar escrito num contrato, e a nota de 'provisório' foi lida cada vez menos — ver `CALC-03`.

**Commit.** `9333359, c715f68` · procedência **completa**

### 2026-08-25 · `FW-08 (secrets)`

**O defeito.** O `secrets.h` estava dessincronizado entre as pastas dos sketches.

**Como foi encontrado.** *leitura* — Cada sketch tinha a própria cópia.

**A correção.** Script de sincronização.

**Commit.** `68608da` · procedência **completa**

### 2026-09-10 · `FW-06` 🔄

**O defeito.** O filtro passa-baixa do MPU6050 estava na banda padrão de 260 Hz, e isso mudou o ruído de base.

**Como foi encontrado.** *cálculo* — O ruído cresce com `√B`: passar de 21 Hz para 260 Hz multiplica σ por 3,52, e o piso do ENMO médio é proporcional a σ.

**A correção.** Filtro para 21 Hz (`σ = 1,833 mg`).

**🔄 A premissa estava errada.** A consequência não estava prevista: **o limiar de movimento é definido sobre o ruído de base, e o ruído de base mudou** — o que invalidou a caracterização de 25/08 pela segunda vez (contato ruim *e* banda diferente) e virou o item `CAL-02`. E 21 Hz implica amostragem ≥ 42 Hz por Nyquist, que atravessa os 40 Hz do modo de baixo consumo: a desigualdade é estrita, e custa 4,5× na corrente do transdutor. Foi daí que saiu, cinco semanas depois, o `ARQ-01`.

**Commit.** `f58f52c (cabeçalho), docs/CALCULOS-TCC.md Z.1 e Z.2.2` · procedência **parcial**

### 2026-09-22 · `HW-05` 🔄

**O defeito.** A medição esperava pela rede, e a série continuava saindo com aparência normal e base de tempo derivada.

**Como foi encontrado.** *leitura* — `conectarWiFi()` era chamada **dentro** do laço de amostragem e gastava até 20 s em `delay(500)`. Com intervalo de 10 s, uma queda de rede fazia cada ciclo levar 20–30 s.

**A correção.** Quatro regras, e a arquitetura saiu delas: nada na medição espera por conectividade; perda de cadência vira campo no dado (`EPOCA_INCOMPLETA`, `EPOCA_VAZIA`, e a época vazia ocupa lugar no buffer); o buffer é de épocas, não de amostras, o que permite degradar resolução em vez de descartar; e a grade é absoluta (`t0 + k·período`, nunca `última + período`).

**🔄 A premissa estava errada.** O enunciado de partida era 'acrescentar buffer', sob a premissa de que o prejuízo de uma queda de rede é a lacuna na série. Para actigrafia, cuja unidade *é* a época fixa de 30 s, a deriva é pior que a lacuna: **a lacuna a análise vê; a deriva, não.** A perda de dado era o problema menor.

**Commit.** `846986a, c0725ca, 54504f6` · procedência **completa**

### 2026-09-22 · `HW-05`

**O defeito.** Uma amostra em cada três desaparecia, e **toda época saía marcada `INCOMPLETA` com a medição perfeita**.

**Como foi encontrado.** *execução* — O fechamento de época era preguiçoso, e `amostrar` recusava amostra de um slot futuro por não ter como fechar o anterior — as dos instantes 30 000, 60 000, 90 000 ms.

**A correção.** Fechamento no lugar certo.

**Nota.** Na placa isso apareceria depois de uma noite de coleta; na suíte do host apareceu em 3 ms. A suíte pegou quatro defeitos nesse dia — este, o `fundir`, e duas expectativas de teste que estavam erradas, não o código.

**Commit.** `846986a` · procedência **completa**

### 2026-09-22 · `HW-05`

**O defeito.** `fundir` consultava `a->vazia()` **depois** de mesclar as flags: época com dado fundida com lacuna saía marcada como lacuna.

**Como foi encontrado.** *execução* — Ordem entre a consulta e a mesclagem.

**A correção.** Consulta antes da mesclagem.

**Commit.** `846986a` · procedência **completa**

### 2026-09-22 · `HW-05`

**O defeito.** Duas expectativas da própria suíte estavam erradas — não o código.

**Como foi encontrado.** *execução* — Asserções escritas a partir do comportamento esperado por leitura, não do especificado.

**A correção.** Expectativas corrigidas.

**Nota.** Registrado porque é o modo de falha que faz mexer no código certo: um valor de referência errado reprova implementação correta.

**Commit.** `846986a` · procedência **completa**

### 2026-09-22 · `(sem item)` 🔄

**O defeito.** O `envio-continuo.ino` tinha duas strings com quebra de linha literal no meio. **Não compilava em máquina nenhuma** — e era tratado como código em funcionamento, com o backlog discutindo melhorias nele.

**Como foi encontrado.** *execução* — Nada no repositório tentava compilar firmware: o CI olhava Python e frontend, e o sketch só era exercitado manualmente no Wokwi, onde o arquivo aberto era o da máquina de quem editava, não o versionado.

**A correção.** Alvo `make sintaxe` (`g++ -fsyntax-only` com stubs mínimos do Arduino), que gera um `secrets.h` falso em `bin/` e o põe por último no caminho de include — roda em qualquer clone sem exigir credencial.

**🔄 A premissa estava errada.** A premissa era 'código versionado num repositório com CI é código que ao menos compila'. E uma causa mais funda ficou registrada na mesma revisão: `sketch.ino` e `envio-continuo.ino` tinham chegado a **critérios de movimento diferentes** antes do `FW-06`, porque o núcleo era duplicado em cada sketch e as cópias divergiram na primeira correção. Daí a unidade de tradução única.

**Commit.** `846986a, c0725ca` · procedência **completa**

### 2026-09-22 · `FW-07` 🔄

**O defeito.** O sketch de produto tira **uma amostra por boot** e dorme: não registraria uma noite nem com rede perfeita.

**Como foi encontrado.** *leitura* — Não tem amostragem periódica nenhuma. O problema não era robustez, era ausência de estrutura.

**A correção.** Em 22/09 recebeu **só** a correção dos travamentos; o conserto de verdade foi separado como `FW-07` e continua aberto.

**🔄 A premissa estava errada.** O enunciado do `HW-05` para ele era 'correção defensiva nos travamentos', sob a premissa de que, tirados os travamentos, o sketch serviria para captação noturna. Enquanto o `FW-07` estiver aberto, o 'firmware de produto' do trabalho é o `envio-continuo.ino`, que não dorme.

**Commit.** `54504f6` · procedência **completa**

### 2026-10-16 · `CI-03` 🔄

**O defeito.** O `make sintaxe` tinha **dois dos quatro** sketches versionados, e na primeira vez que os outros dois foram compilados os **dois** tinham string com quebra de linha literal — o defeito exato que o alvo nasceu para pegar.

**Como foi encontrado.** *execução* — A lista `SKETCHES` era escrita à mão.

**A correção.** A lista deixou de ser escrita à mão: sai de `$(wildcard)`, com guarda para o caso de não casar nada. Validado por controle positivo nas duas direções — string quebrada devolvida reprova; sketch novo com função inexistente reprova, provando que o wildcard o pega.

**🔄 A premissa estava errada.** É a ocorrência 4 do §1 das lições: *alcance de verificação escrito à mão silenciosamente para de acompanhar a pasta.* Os dois sketches passaram de 22/09 a 16/10 sem compilar em máquina nenhuma.

**Commit.** `7feeef9` · procedência **completa**

### 2026-10-16 · `CI-03`

**O defeito.** `diagnostico-i2c.ino` tinha uma chave sobrando, fechando `setup()` no meio.

**Como foi encontrado.** *execução* — Nunca havia sido compilado.

**A correção.** Chave removida.

**Commit.** `7feeef9` · procedência **completa**

### 2026-10-16 · `CI-03`

**O defeito.** `%lu` para um `uint32_t` — no ESP32 um `unsigned int`: o `printf` lia 8 bytes de um argumento de 4 e imprimia lixo em silêncio.

**Como foi encontrado.** *execução* — Especificador de formato incompatível com o tipo na plataforma de destino.

**A correção.** Especificador corrigido.

**Nota.** Achado **só** porque o stub do `Serial` tem `__attribute__((format))` — é o instrumento, e não o compilador da IDE, que pegou.

**Commit.** `7feeef9` · procedência **completa**

### 2026-10-17 · `DATA-07b`

**O defeito.** `features.h` sequestrou o `<features.h>` da glibc, e nada compilava.

**Como foi encontrado.** *execução* — Com o `-I.` do Makefile, todo cabeçalho de sistema que faz `#include <features.h>` passou a incluir o do projeto. O erro era `missing binary operator before token "("` **dentro de `/usr/include/`**, apontando para a biblioteca padrão, sem mencionar o arquivo culpado — e atingia até `filtro.cpp`, que não o inclui.

**A correção.** Renomeado para `caracteristicas.h`, que além de não colidir segue o padrão de nomes da casa (`epoca`, `cadencia`, `relogio`, `payload`).

**Nota.** Seguir o padrão de nomes teria evitado o problema de graça.

**Commit.** `6d328bb` · procedência **completa**

### 2026-10-17 · `DATA-07b` 🔄

**O defeito.** Os coeficientes do filtro em `float32` enviesavam o estimador: o ganho em corrente contínua saiu 1,0000120 onde tem de ser exatamente 1.

**Como foi encontrado.** *execução* — Cancelamento catastrófico na própria expressão: `1 + a1 + a2 = 0,0023283`, uma soma que perde quase três ordens de grandeza, então 1e−7 de erro por coeficiente vira 4,3e−5 no ganho. Em termos físicos, injeta 1,2e−5 g em `‖a − ĝ‖` de forma **sistemática** — viés de estimador, não ruído, e portanto não se cancela no somatório.

**A correção.** Coeficientes em `double`, a custo **zero** — o laço interno já acumulava em `double`, então eles eram `float` truncado promovido a `double` em toda multiplicação, o pior dos dois mundos. O ganho DC passou a fechar em 1e−16.

**🔄 A premissa estava errada.** A tentação era afrouxar a tolerância de 1e−5. O teste estava certo e o estimador estava errado — e nenhuma tolerância deste item foi afrouxada: as duas que se mexeram foram apertadas ou alinhadas com a régua já existente do outro lado.

**Commit.** `6d328bb` · procedência **completa**

### 2026-10-17 · `DATA-07b`

**O defeito.** Os coeficientes de referência escritos no teste estavam errados — escritos de memória.

**Como foi encontrado.** *terceiro* — `b0 ≈ 5,37e−4` e `a1 ≈ −1,93338` de memória, contra `b0 = 5,8207613e−4` e `a1 = −1,9306064` reais.

**A correção.** Conferido contra `scipy.signal.butter` de verdade: a forma fechada do módulo e o scipy concordam em 2,2e−19 nos cinco coeficientes.

**Nota.** Registrado porque é o modo de falha mais fácil de não notar: um valor de referência inventado faz o teste reprovar código correto, e a reação natural é mexer no código.

**Commit.** `7cddf66` · procedência **completa**

### 2026-10-17 · `DATA-07b`

**O defeito.** A asserção `inclinacao_rel == 0` reprovou, e estava mais fina que a física.

**Como foi encontrado.** *execução* — Piso de condicionamento do `arccos`: com uma época só, `ĝ_ref` é o próprio `ĝ`, o produto interno é 1, e ali `dθ/dc = −1/√(1−c²)` explode, transformando 1 ulp em ~6e−7 grau.

**A correção.** Régua de 1e−5 grau — a **mesma** que `test_angulo_entre_vetores_paralelos_nao_e_nan` usa do outro lado.

**Commit.** `7cddf66` · procedência **completa**

### 2026-10-17 · `DATA-07b` 🔄

**O defeito.** O harness de mutação do lado C++ tinha contaminação entre rodadas: uma sabotagem apareceu como **detectada**, e a detecção era resíduo da sabotagem anterior.

**Como foi encontrado.** *controle positivo* — A primeira versão restaurava só `caracteristicas.cpp` entre sabotagens, deixando `filtro.cpp` sabotado da rodada anterior.

**A correção.** Árvore nova (`mktemp -d`) por sabotagem, e exigência de que cada trecho case **exatamente uma vez**, com erro alto quando não casa — *um sabotador morto se lê como ponto cego.*

**🔄 A premissa estava errada.** É o **mesmo defeito** que o `DATA-07c` achou no instrumento do Python, com outra roupa, e na mesma data pela manhã. A reincidência é o argumento mais forte de o `LICOES-APRENDIDAS.md` existir.

**Commit.** `7cddf66` · procedência **completa**

### 2026-10-17 · `FW-06`

**O defeito.** O cabeçalho do `caracterizacao.ino` afirmava o contrário do código.

**Como foi encontrado.** *inventário* — Edição de cabeçalho pendente de outra sessão, nunca commitada.

**A correção.** Cabeçalho alinhado ao código.

**Commit.** `f58f52c` · procedência **completa**

---

## Dados e ML — 24 defeitos

*15 execução · 2 dado real · 2 cálculo · 2 controle positivo · 1 terceiro · 1 inventário · 1 leitura*

### 2026-09-14 · `ML-01` 🔄

**O defeito.** As features herdadas da actigrafia clássica (`angulo_z` e a *signal magnitude area*) não eram invariantes a rotação.

**Como foi encontrado.** *execução* — Num travesseiro a orientação é arbitrária **e muda durante a noite**. `angulo_z` depende de qual eixo é 'z'; a norma L1 sobre gravidade bruta varia até **73% só por causa da montagem**, e mesmo restrita à componente dinâmica variou ~6%.

**A correção.** `angulo_z` saiu; entraram `inclinacao_rel` e `d_angulo`, invariantes por construção (`(Rĝ_a)·(Rĝ_b) = ĝ_a·ĝ_b`). A SMA L1 saiu; entrou `mag_din_media` (norma L2).

**🔄 A premissa estava errada.** A premissa era que features clássicas de punho servem para o travesseiro, e que o que muda é a escala, não a definição. Risco que ficou: `mag_din_media` **não pode ser citada como *signal magnitude area* no TCC** — é outra norma, e usar o nome clássico atribuiria ao trabalho uma comparação com a literatura que ele não faz.

**Commit.** `38ae2a5` · procedência **completa**

### 2026-09-14 · `ML-01`

**O defeito.** `direcao_referencia` também não era invariante a rotação, na primeira escrita.

**Como foi encontrado.** *execução* — Defeito residual da mesma classe, no mesmo dia.

**A correção.** Corrigida, com teste de invariância próprio.

**Commit.** `11eb4b7` · procedência **completa**

### 2026-09-14 · `DADOS-02` 🔄

**O defeito.** Dez divergências entre o que a documentação dos datasets declara e o que os arquivos têm. A pior: o Empatica em `g/64` onde a v1.0 declara `g/16` — **fator 4 de erro, silencioso**, no braço 'treina' do `ML-03`.

**Como foi encontrado.** *dado real* — A premissa era que a documentação do dataset descreve o dataset. Outras do mesmo lote: `PSG_Manual_scor1` no `.tsv` contra `PSG_Manual_Scor1` no EDF (casamento sensível a maiúscula acha o acelerômetro e **perde o rótulo** — o sintoma não é exceção, é zero época); `scor2` declarado para 100 sujeitos e presente em **96**; nº de canais variando de **38 a 61** por sujeito.

**A correção.** Todo acesso passou a ser por nome, nunca por posição. O carregador **aborta** se encontrar a declaração `g/16`, em vez de converter pelo fator que achar. Um teste por armadilha em `ml/testes/test_wearanize.py`.

**🔄 A premissa estava errada.** É o de maior potencial de dano do projeto: o fator 4 teria contaminado em silêncio o braço 'treina' da matriz de transferência, que é **o resultado original do trabalho**. Foi pego por auditoria dos arquivos reais, não por leitura da documentação — e a regra de método ficou escrita para o próximo carregador (`ML-06b`): *escreva contra a documentação, mas não confie até rodar.*

**Commit.** `5c2720c` · procedência **completa**

### 2026-09-14 · `ML-02`

**O defeito.** O alinhamento PSG/acelerômetro no Newcastle estava errado, e o carregador não lia a estrutura real do zip nem aplicava a calibração.

**Como foi encontrado.** *dado real* — Escrito contra a documentação, antes da primeira medição real.

**A correção.** Alinhamento e carregador corrigidos em dois commits.

**Commit.** `602bc44, 8006642` · procedência **completa**

### 2026-09-14 · `ML-02` 🔄

**O defeito.** A acurácia não serve como métrica de decisão neste domínio: o classificador trivial 'sempre dormindo' é **competitivo em acurácia** e tem **κ exatamente 0**.

**Como foi encontrado.** *execução* — A prevalência de sono numa noite de PSG é alta. Aplicada a dois trabalhos da literatura que publicam sensibilidade, especificidade e acurácia, a identidade `acurácia = p·sens + (1−p)·espec` recupera a acurácia que o trivial teria alcançado *naquele mesmo estudo*, e a diferença contra a publicada é pequena.

**A correção.** κ de Cohen passou a ser a métrica primária em todo o trabalho, e toda comparação é contra o trivial **medido na própria coorte**, porque κ depende da prevalência e valores de coortes diferentes não são comparáveis entre si.

**🔄 A premissa estava errada.** A premissa era que acurácia serviria como métrica de leitura. É o §8 das lições: a média esconde o caso que importa.

**Commit.** `38ae2a5` · procedência **completa**

### 2026-09-14 · `ML-02`

**O defeito.** Cole-Kripke e Sadeh não podiam ser usados como publicados.

**Como foi encontrado.** *terceiro* — Exigem *activity counts* de Actiwatch, e não há função pública que converta aceleração em counts.

**A correção.** Substituto documentado (passa-banda 0,25–3 Hz, retificado, integrado), com a obrigação de aparecer no texto como 'Cole-Kripke aplicado a um substituto de contagem' e com a segunda diferença declarada (épocas de 30 s, não os 60 s originais).

**Nota.** É o tipo de atalho de redação que uma banca cobra, e está registrado como advertência, não como detalhe.

**Commit.** `38ae2a5` · procedência **completa**

### 2026-09-14 · `ML-03`

**O defeito.** `ml03_transferencia.py` não calculava trivial/Sadeh por braço.

**Como foi encontrado.** *execução* — Baseline agregado onde a comparação exige um por posição.

**A correção.** Calculado por braço.

**Commit.** `fd215ff` · procedência **completa**

### 2026-09-15 · `ML-03` 🔄

**O defeito.** A hipótese de que a transferência entre posições de sensor seria **simétrica** caiu.

**Como foi encontrado.** *execução* — Matriz 3×3 com o mesmo N nas nove células (N = 92, LOSO): pulso → qualquer posição dá κ ≈ 0,38; cabeça → cabeça fica em 0,398–0,401; **cabeça → pulso cai a 0,046** e cabeça → cabeça degradada a **0,067** — quedas de 85% e 88% da diagonal de origem.

**A correção.** A hipótese foi abandonada e o achado virou o resultado original do trabalho. A pergunta seguinte deixou de ser 'quanto se perde' e passou a ser 'o que exatamente é perdido' (`ML-03b`).

**🔄 A premissa estava errada.** A direção que interessa ao produto — treinar com dado de cabeça — é justamente a que colapsa.

**Commit.** `896abba` · procedência **completa**

### 2026-09-15 · `ML-03b` 🔄

**O defeito.** A leitura fácil do resultado — 'a normalização recupera 70% a 80%' — estava errada.

**Como foi encontrado.** *execução* — Os 71,0% e os 77,6% são **ambos de `cabeça → pulso`**. Em `cabeça → cabeça-E4` a recuperação é **metade**: 34,5% e 41,5%. A faixa é de **um par de posições, não da matriz**.

**A correção.** O texto de resultados teve de dizer isso com essas palavras ('cerca de três quartos […] e cerca de dois quintos'). Sem a frase, o número parece valer para a matriz inteira e não vale.

**🔄 A premissa estava errada.** Autocorreção antes de o número sair do repositório, e as duas ressalvas que ficaram declaradas: as frações são medidas contra a diagonal de **origem** (contra a de **destino** sairia 83,3% em vez de 77,6% — a adotada é a conservadora, e a escolha tem de ser declarada); e a floresta aleatória **não é 'o modelo sem normalizador'**, porque é insensível a deslocamento monotônico de escala por construção.

**Commit.** `44de161` · procedência **completa**

### 2026-09-18 · `ML-04` 🔄

**O defeito.** A hipótese de que a degradação entre coortes seria **uniforme** caiu — e a validação interna, sozinha, teria escolhido a modificação errada.

**Como foi encontrado.** *execução* — Modelo ajustado nos 92 de desenvolvimento e aplicado a 27 de coorte independente, **sem reajuste de nada**. O ganho do HMM praticamente desapareceu (Δκ +0,123 → +0,036) **e** veio com perda de especificidade estatisticamente distinguível (−0,037); o da janela de contexto preservou magnitude e direção (+0,075 → +0,069).

**A correção.** A explicação é o que cada modificação aprende: a matriz de transição do HMM é estimada sobre a **prevalência** da coorte de treino; a janela de contexto não codifica prevalência alguma — só muda a escala temporal, que é propriedade do fenômeno, não da coorte.

**🔄 A premissa estava errada.** Daí a limitação metodológica que o trabalho declara, e é o achado mais forte dele: **seleção de modelo apoiada só em validação cruzada interna é insuficiente neste domínio.** Risco declarado: **uma única** coorte externa, então a degradação relatada é estimativa pontual, não medida de variabilidade.

**Commit.** `83382b2` · procedência **completa**

### 2026-09-18 · `ML-03b item 8`

**O defeito.** A mediana móvel não sai do ruído.

**Como foi encontrado.** *execução* — Bootstrap pareado da diferença sobre os mesmos sujeitos.

**A correção.** Descartada. O HMM de 2 estados ficou como candidato — e teria sido escolhido se a decisão parasse ali.

**Commit.** `2db4c08` · procedência **completa**

### 2026-09-21 · `ML-04b` — ⛔ **fora da contagem**

**O defeito.** Nenhum — a hipótese se confirmou, e o defeito estaria em declarar mais do que ela permite.

**Como foi encontrado.** *execução* — Comparação intraparticipante nos 26 com registro bilateral: Δκ = +0,009 (IC 95%: −0,014 a +0,031), e **todos os 24 IC 95% contêm zero**.

**A correção.** A ressalva é o valor da entrada: **com 26 participantes, efeito menor que ~0,03 em κ não seria distinguível do ruído.** O texto não pode dizer 'o lado não importa' sem o poder do teste ao lado.

**Nota.** É o caso raro deste registro em que o resultado confirmou a hipótese. Entra porque o que se corrigiu foi a **afirmação** que se podia extrair dele.

**Commit.** `d51fa66` · procedência **completa**

### 2026-09-28 · `ML-05` 🔄

**O defeito.** A faixa de leitura dos Δκ do trabalho é [0; 0,61], não [0; 1].

**Como foi encontrado.** *execução* — As duas pontuações manuais do Wearanize+, comparadas entre si na mesma redução binária do pipeline, dão κ = 0,607 nos 96 sujeitos com as duas, e **0,612 nos 90** que também estão nos 92 da base — este é o divisor certo.

**A correção.** O capítulo de resultados foi reescrito contra esse teto.

**🔄 A premissa estava errada.** A premissa era que a concordância entre dois humanos daria um teto próximo de 1. Contra 1,0 um κ de 0,41 parece ruim; contra 0,61 é outra leitura. E o achado de brinde é desconfortável: o pontuador 2 marca **7,8 pontos percentuais** mais de vigília que o pontuador 1, e **a especificidade humana vale 0,958 ou 0,520 conforme qual dos dois se toma como referência** — o que tira a especificidade externa do modelo (0,507) de parecer um número isolado. Risco: **não há teto para o Newcastle**, e é justamente o número que o trabalho declara como honesto.

**Commit.** `ab3d542` · procedência **completa**

### 2026-09-29 · `CALC-03` 🔄

**O defeito.** O limiar de 1,2 m/s² em uso **não foi derivado do ruído**, e a derivação clássica `g ± k·σ` não o gera nem o explica.

**Como foi encontrado.** *cálculo* — Uma divisão. Com `σ = 1,833 mg = 0,0180 m/s²` na banda de 21 Hz, `k = 1,2 / 0,0180 ≈ **67 σ**`. Limiares derivados de ruído operam tipicamente entre 3 σ e 5 σ: um limiar a 67 σ não pertence a essa família. A derivação honesta daria entre **0,054 e 0,090 m/s²** — de treze a vinte e duas vezes menor.

**A correção.** O item foi **recortado, não cumprido**: a seção Z.2.3 passou a demonstrar *por que a derivação não produz número útil*, em vez de produzir um número que pareceria derivado e não seria.

**🔄 A premissa estava errada.** O backlog dizia que o item já estava 'boa parte resolvido' e que virara *transpor, não decidir*. De onde o 1,2 vem de verdade está em 20/08: da correção da assimetria, herdado de `11,0 − 9,81 = 1,19`. É número de engenharia, não de estatística — e uma derivação escrita com `k = 67` implícito seria **pior que a ausência dela**, porque daria ao 1,2 uma procedência que ele não tem, num documento que vai à banca.

**Commit.** `4fb72e4` · procedência **completa**

### 2026-09-29 · `DATA-07` 🔄

**O defeito.** `d_angulo` **não** é a diferença de `inclinacao_rel` entre épocas vizinhas, e guardar só uma das duas não reconstrói a outra.

**Como foi encontrado.** *cálculo* — São ângulos **numa esfera**, e entre eles não vale uma igualdade: vale a desigualdade triangular esférica `|θ_t − θ_{t−1}| ≤ d_angulo ≤ θ_t + θ_{t−1}`, que deixa **um grau de liberdade** que só `ĝ` fecha.

**A correção.** O dispositivo guarda **`ĝ`** por época, e as duas features angulares são derivadas **no servidor**, sobre a noite completa, pelo mesmo código que produziu os resultados do ML. A reconstrução é exata.

**🔄 A premissa estava errada.** Medido em **87 795 épocas**: a aproximação erra **0,01 grau na mediana** e **149 graus no pior caso**, com o erro concentrado nas viradas — que é tudo aquilo para o que a feature existe. **A mediana boa era a armadilha:** tornava a hipótese plausível exatamente onde nada acontece (§8). E resolveu de passagem um problema que não estava sendo procurado: `ĝ_ref` é a mediana geométrica da gravação **inteira**, e um dispositivo que drena em tempo real não pode conhecê-la — a proposta anterior era um 'acumulador direcional com aquecimento', que é **estimador diferente**, não aproximação com tolerância, e divergiria do Python em silêncio.

**Commit.** `3f2cb87` · procedência **completa**

### 2026-09-29 · `DATA-07b` 🔄

**O defeito.** A afirmação de que 'o item virou transcrever' estava errada: as 8 features existiam **só em Python**.

**Como foi encontrado.** *inventário* — Um `grep -rniE "enmo|zcr|p_frac|inclinacao|d_angulo|mag_din" firmware/` devolveu **vazio**. O que o projeto chamava de 'lado C++' era uma referência **escrita em Python** dentro de `test_vetor_dourado.py` — útil como especificação, e nenhuma linha de firmware.

**A correção.** O item foi reescrito com as cinco partes que faltavam de verdade, e o peso reclassificado para comparável ao `FW-07`.

**🔄 A premissa estava errada.** **O item de maior peso do projeto foi subestimado por seis dias porque ninguém rodou o grep.** O custo foi de classificação: o item figurava como pequeno.

**Commit.** `85f573d, 3f2cb87` · procedência **completa**

### 2026-09-30 · `DATA-07d` 🔄

**O defeito.** O vetor dourado **gravava a própria referência**: `test_gravar_vetor_dourado` gravava o arquivo e conferia que ele existia. Isso nunca falha.

**Como foi encontrado.** *controle positivo* — Qualquer mudança na definição de uma feature reescrevia o dourado e a suíte seguia verde: **o arquivo perseguia o código em vez de prendê-lo.**

**A correção.** Agora ele **confere**, e regravar exige dizer que se quer regravar (`DORMIO_REGRAVAR_DOURADO=1`) e explicar no commit o que mudou de definição.

**🔄 A premissa estava errada.** A premissa era que uma suíte de paridade que passa é uma suíte que verifica paridade. Um vetor dourado que se regrava sozinho não é vetor dourado, é log — e é indistinguível de um que prende, até o dia em que uma definição muda em silêncio.

**Commit.** `0f22941, 4d1b5d2` · procedência **completa**

### 2026-09-30 · `DATA-07d`

**O defeito.** A tolerância do ENMO **reprovaria firmware correto**.

**Como foi encontrado.** *execução* — Estava em `rel = 1e−6`. Medido em **60 sementes** com a fórmula em float32 — que é o que o ESP32 calcula —, `enmo_media` diverge 1,10e−6 relativo e `enmo_max` 3,51e−6. A causa é **cancelamento catastrófico** em `‖a‖ − 1` com `‖a‖ ≈ 1`. Trocar o acumulador para double **não resolve** (1,101e−6 contra 1,097e−6), porque o erro entra no `sqrt` **por amostra**, não na soma.

**A correção.** Tolerância **absoluta**, `1e−7 g` = 1 ULP de float32 em 1 g, que fica 6 400× abaixo do piso de ruído do ENMO no MPU6050.

**Commit.** `0f22941` · procedência **completa**

### 2026-09-30 · `DATA-07d`

**O defeito.** Época incompleta não tem paridade nenhuma, e nada dizia isso.

**Como foi encontrado.** *execução* — O ramo degenerado de `estimar_gravidade` (n ≤ 9) não existe na referência estilo-firmware, e ali a divergência vai a **54%**. Mesmo passando desse ramo: n = 64 diverge 3% e n = 300, 0,8%.

**A correção.** Medido e declarado. **O contrato ainda precisa dizer que o dispositivo não emite `f` de época truncada** — segue como decisão pendente.

**Commit.** `0f22941` · procedência **completa**

### 2026-09-30 · `DATA-07d` 🔄

**O defeito.** Os 5 casos do dourado eram **todos de época única**, então `inclinacao_rel` e `d_angulo` valiam **0 em todos os cinco**: as duas features de definição mais delicada não tinham referência nenhuma.

**Como foi encontrado.** *controle positivo* — E zero é trivialmente invariante a rotação, então o teste de invariância delas **passava sem testar nada**.

**A correção.** O dourado virou dois arquivos, um por fronteira do contrato, com 8 sequências (mudança de postura, virada brusca de 140°, deriva coerente sub-grau, retorno exato à orientação, faixa cobrindo todos os bins, duas épocas, uma época, lacuna temporal). As tolerâncias passaram a ser derivadas entre piso medido e teto de decisão, e `test_as_tolerancias_ainda_cercam_o_piso` **re-mede o piso a cada execução**.

**🔄 A premissa estava errada.** Era o mais silencioso dos quatro defeitos do instrumento: o que devia pegar a divergência era cego exatamente onde ela importa. *Uma tolerância medida uma vez e depois só comentada envelhece.*

**Commit.** `4d1b5d2` · procedência **completa**

### 2026-10-16 · `(contrato)`

**O defeito.** O backend declarava contrato `2.5.0` com o `DATA-CONTRACT.md` em `2.5.1` desde 30/09.

**Como foi encontrado.** *execução* — Divergência introduzida ao versionar o documento sem tocar o backend.

**A correção.** Backend alinhado ao documento.

**Nota.** `test_informa_a_versao_do_contrato_de_dados` não fixa a versão num literal — **lê do documento**, exatamente para que a divergência não fosse possível em silêncio. Funcionou: acusou na primeira execução da suíte do backend depois de 30/09. O teste estava certo e disponível por duas semanas sem ninguém rodar, **o que é o argumento do CI em uma frase.**

**Commit.** `fa34897` · procedência **completa**

### 2026-10-28 · `ML-WIN-01`

**O defeito.** Os dois testes de vetor dourado reprovavam no Windows por divergência no último dígito de 71 de 14 952 floats.

**Como foi encontrado.** *execução* — Comparação por igualdade exata de um JSON gravado em Linux: ordem de soma e libm diferem entre plataformas (pior caso medido: 8,0e-13 relativo).

**A correção.** Estrutura exata e floats com tolerância derivada (1e-9 relativo) entre o piso medido e o teto do verificador por mutação, 12/12 em Linux e no Windows.

**Commit.** `7016c81` · procedência **completa**

### 2026-10-28 · `ML-WIN-01` 🔄

**O defeito.** A régua de 1e-9 relativo que substituiu a igualdade exata do dourado reprovou no runner: `d_angulo` divergiu 5,7e-9.

**Como foi encontrado.** *execução* — O piso tinha sido medido num único par de plataformas, e régua relativa é a forma errada para `degrees(arccos(c))`, cujo erro relativo cresce como 1/θ² perto de 1.

**A correção.** Ângulos com régua absoluta de 1e-4°, derivada da condição do `arccos`; 12/12 no verificador por mutação em Linux e no Windows.

**🔄 A premissa estava errada.** Uma régua medida entre duas plataformas vale para as outras. O runner do Actions muda de máquina entre execuções: a primeira passou até com igualdade exata, a segunda reprovou.

**Commit.** `58ae504` · procedência **completa**

### 2026-10-28 · `ML-WIN-01` 🔄

**O defeito.** O teste de retomada fazia mais de uma dobra por chamada no Windows com orçamento zero.

**Como foi encontrado.** *execução* — `elapsed > orcamento_s` com o relógio do Windows em degraus de ~15,6 ms: duas leituras no mesmo degrau dão 0 s, e `0 > 0` é falso.

**A correção.** `>=`. Hipótese confirmada antes de corrigir: com um relógio em degraus, o teste reprova 3 de 3 em Linux.

**🔄 A premissa estava errada.** O relógio de parede mede tempo decorrido com resolução suficiente para um orçamento zero. Em Linux mede; no Windows, não — e a falha alternava entre execuções, o que a fazia parecer acaso.

**Commit.** `7016c81` · procedência **completa**

### 2026-10-30 · `ML-12`

**O defeito.** Em todos os experimentos desde o `ML-02`, o contexto de ±2 épocas foi empilhado sobre a base concatenada, e nas fronteiras misturava features de dois sujeitos.

**Como foi encontrado.** *leitura* — `empilhar_contexto` replica a borda da matriz que recebe; os experimentos passavam a base inteira, não um sujeito por vez.

**A correção.** O `ML-12` aplica o contexto por sujeito e mediu a diferença: +0,001 a +0,002 de κ a favor do global, desprezível. Os experimentos anteriores não foram refeitos, de propósito: o efeito é uma ordem de grandeza menor que qualquer um deles.

**Nota.** Achado ao escrever o `ML-12`, lendo `src/epocas.py` para reusar.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (iv) do diário)` · procedência **parcial**

---

## Documentação — 23 defeitos

*10 inventário · 9 leitura · 3 terceiro · 1 execução*

### 2026-06-03 · `(README)`

**O defeito.** O subtítulo do README não correspondia ao título, e o nome do produto não estava padronizado.

**Como foi encontrado.** *leitura* — Deriva de redação entre revisões.

**A correção.** Subtítulo alinhado ('detecção de movimento') e nome padronizado para 'Smart Dormio'.

**Commit.** `33000ee, 182f68e` · procedência **completa**

### 2026-09-29 · `REF-01` 🔄

**O defeito.** Quatro defeitos nas referências bibliográficas, sendo um de **autoria falsa**.

**Como foi encontrado.** *terceiro* — Conferência de 11 fontes **na fonte**: 1 autoria falsa (`Rocha et al.` → **Li, Halaki & Chow**), 1 tendência não significativa apresentada como achado, 1 número virado indevidamente em requisito técnico, 2 citações não localizadas.

**A correção.** Corrigidos. **Nenhuma referência permanece sem autoria conferida.**

**🔄 A premissa estava errada.** A premissa era que citação escrita por quem leu o material está certa, e que a conferência acharia erros de formatação. E o que **não** foi fechado está registrado como `DOC-06b`: **referência conferida ≠ artigo lido.** As 11 têm autoria correta; quantas foram lidas além do resumo não está registrado.

**Commit.** `fab1d95` · procedência **completa**

### 2026-09-29 · `LGPD-01`

**O defeito.** O direito de eliminação estava citado como art. 18, **V** — e é o **VI**. A troca estava em **cinco lugares**, propagada por cópia.

**Como foi encontrado.** *terceiro* — O inciso V trata de *portabilidade a outro fornecedor*; a *eliminação dos dados tratados com consentimento* é o VI. Os cinco lugares: `LGPD-ELIMINACAO.md`, `DATA-CONTRACT.md` §6.2, `routes.py`, a migração `006` e o `BACKLOG-COMPLETO.md`.

**A correção.** Corrigido nos cinco, com varredura completa conferindo que nenhuma outra citação de artigo da LGPD no repositório está incorreta.

**Commit.** `7a5d21a, fab1d95` · procedência **completa**

### 2026-09-30 · `LGPD-01`

**O defeito.** O argumento de que 'dado pseudonimizado continua sendo dado pessoal' estava apoiado no art. 13, §4º, e o apoio era frouxo.

**Como foi encontrado.** *terceiro* — A citação **existe e é onde a pseudonimização é definida**, mas o artigo inteiro trata de *estudos em saúde pública*. Conferido no Planalto, o §4º abre com 'Para os efeitos deste artigo' — **a própria lei circunscreve a definição ao art. 13**, o que torna a objeção textual, e não apenas contextual.

**A correção.** O argumento passou a ser apoiado no **art. 12**, que retira do escopo da lei apenas o dado **anonimizado** — de onde se segue, por contraste, que o pseudonimizado permanece dentro.

**Nota.** É o caso em que a citação não estava 'errada' e ainda assim não sustentava o que lhe pediam.

**Commit.** `fab1d95` · procedência **completa**

### 2026-10-17 · `DOC-10 / UI-10` 🔄

**O defeito.** **Quatro** documentos afirmavam que a tela de exclusão de conta existia, durante os dezoito dias em que ela estava inalcançável.

**Como foi encontrado.** *inventário* — O backlog (`UI-10 ✅`), o `LGPD-ELIMINACAO.md` ('a interface existe desde 29/09'), a `POLITICA-DE-PRIVACIDADE.md` §6.4 (que **dizia ao titular onde clicar**) e o `DIAG-04`, que era o quarto e passou pela primeira varredura.

**A correção.** Os quatro corrigidos, com nota de procedência. Varredura por termos ('ainda não existe', 'não há tela', 'existe como rota') sobre `docs/`, `*.md`, `frontend/src/` e `web-app/`.

**🔄 A premissa estava errada.** Detalhe que vale guardar: logo abaixo da afirmação falsa no `LGPD-ELIMINACAO.md` estava a linha 'Falta a parte de interface: hoje a eliminação existe como rota, e só', marcada como obsoleta e mantida 'para o histórico ficar legível' — **a linha dita obsoleta estava mais certa que a que a substituiu**, por dezoito dias.

**Commit.** `22a9268, c80c2b8, fb2f18f` · procedência **completa**

### 2026-10-17 · `(iv)` 🔄

**O defeito.** A política de privacidade §6.3 **negava** a tela que o `UI-11` acabara de entregar, e mandava o titular escrever para um canal de contato.

**Como foi encontrado.** *inventário* — O commit do `UI-11` (`2316b06`) não tocou a política. Mesmo dia, sinal invertido em relação ao caso do `UI-10`.

**A correção.** Corrigida horas depois, ao fechar o `PERFIL-01`.

**🔄 A premissa estava errada.** A regra que os dois casos custaram — *o commit que entrega o mecanismo atualiza o documento que fala dele, no mesmo commit* — **não tem mecanismo**, e isso está dito: nada no repositório liga uma afirmação da política de privacidade a um teste. O que existe é a varredura à mão.

**Commit.** `fb2f18f` · procedência **completa**

### 2026-10-17 · `DOC-11` 🔄

**O defeito.** O `CLAUDE.md` dizia 'ainda não há suíte de testes nem CI' e 'health check ainda não existe'. As duas eram falsas havia semanas.

**Como foi encontrado.** *inventário* — Afirmação de estado em arquivo de instrução, sem número e sem data.

**A correção.** Corrigido com os números medidos e a tabela de como rodar cada camada — e, como a correção envelheceu em dez dias dentro de um arquivo gitignorado, o arquivo passou a ser versionado em 27/10, com a parte pessoal em `CLAUDE.local.md`.

**🔄 A premissa estava errada.** O que distingue esta ocorrência das outras do §6: as outras enganavam **sobre** o sistema; esta **instruía a não verificá-lo** — é o arquivo que orienta cada sessão de trabalho dizendo que não há o que rodar. Daí a regra: afirmação de estado em arquivo de instrução traz o número e a data da medição, porque número com data envelhece **visivelmente** e adjetivo não.

**Nota.** Até 27/10 esta linha era de procedência parcial: a correção de 17/10 não tinha commit possível, porque o `CLAUDE.md` estava no `.gitignore`.

**Commit.** `4014798` · procedência **completa**

### 2026-10-27 · `UI-18`

**O defeito.** A parte (c) do item afirmava que o `vitest` não estava em nenhum job do `ci.yml` — e o job `frontend` o roda desde 19/08.

**Como foi encontrado.** *inventário* — A frase repetia a lista de jobs do `CLAUDE.md` gitignorado, que estava errada (*'`documentos`, `rls` e os do firmware'*; são seis).

**A correção.** Riscada no backlog, com o commit de origem do job (`01a7faa`).

**Nota.** A conferência de 20/10 já tinha achado isto, e o achado ficou oito dias num arquivo sem commit; a correção de 27/10 foi redescoberta do zero. É o §2 das lições acontecendo com o próprio registro.

**Commit.** `4014798` · procedência **completa**

### 2026-10-27 · `GIT-05`

**O defeito.** A previsão escrita no item — *'versionando o `CLAUDE.md`, a lista de ponteiros aceitos cai de 8 para 7'* — estava errada.

**Como foi encontrado.** *execução* — O arquivo versionado precisa apontar para o `CLAUDE.local.md`, e isso é ponteiro para arquivo ignorado: sai um, entra outro.

**A correção.** Medido com o `CLAUDE.md` no índice, num clone em Linux: continuam 8. Corrigido no backlog antes do commit.

**Commit.** `4014798` · procedência **completa**

### 2026-10-28 · `GIT-06`

**O defeito.** Cinco linhas deste registro, de procedência 'completa', citavam o commit `846966a`, que não existe.

**Como foi encontrado.** *inventário* — Erro de digitação do hash `846986a` (o núcleo do firmware, 22/09), e nada conferia que um hash citado existe.

**A correção.** Hash corrigido, uma das linhas passou a citar também o `c0725ca`, e o `--conferir` passou a reprovar hash inexistente e histórico raso — com `fetch-depth: 0` no job `documentos`.

**Nota.** Não é `instrumento`: o defeituoso era o registro, não uma verificação. Na primeira execução marcou-se `instrumento=True`, e a guarda de prosa do gerador reprovou — o texto da derivação (3) só admite duas verificações defeituosas achadas sem rodar.

**Commit.** `16552bd` · procedência **completa**

### 2026-10-28 · `GIT-06`

**O defeito.** A tabela 'A premissa que caiu' mostrava, em cerca de metade das linhas, uma frase que não era a premissa.

**Como foi encontrado.** *leitura* — O gerador pegava a primeira frase do campo `premissa`, que muitas vezes é comentário (*'A tentação era afrouxar a tolerância'*).

**A correção.** Campo próprio `premissa_curta`, obrigatório quando há premissa.

**Commit.** `16552bd` · procedência **completa**

### 2026-10-28 · `GIT-06` 🔄

**O defeito.** Catorze afirmações do backlog contrariadas pela conferência de 20/10 continuavam no backlog oito dias depois: `DIAG-01` e `DIAG-03` como não começados, a frase velha do `CALC-03`, o `LGPD-02` contado duas vezes, `PWA-01` e `PERFIL-02` na camada errada, o item sem ID, `ML-04`/`ML-05` com ID repetido, os números do `GIT-03` e do `CI-06`, e três pendências sem item (o push, o projeto Supabase de teste, o conceito de noite).

**Como foi encontrado.** *inventário* — A conferência foi escrita num documento gerado que nunca entrou no git, e o backlog não foi tocado.

**A correção.** Reconferidas em 28/10 e aplicadas. Os dois DIAG ficaram abertos, com o que falta escrito; a contagem foi refeita linha a linha.

**🔄 A premissa estava errada.** A conferência de 20/10 dizia que o desenho estava pago: *'mitigado com uma linha no `BACKLOG-COMPLETO.md`'*. A linha não existia, e a conferência inteira não chegou a quem decide — o §2 das lições.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 28/10 do diário)` · procedência **parcial**

### 2026-10-28 · `DIAG-03`

**O defeito.** Os diagramas de 29/09 omitiam as features em C++ de 17/10, a rota `/api/me/perfil` e o `/health`, e o `DIAG-03` rotulava o payload como `v2.4.0` sem dizer que o contrato estava em 2.5.1.

**Como foi encontrado.** *inventário* — Diagrama datado que ninguém reconferiu depois que o código mudou.

**A correção.** Conferidos contra o código (55 afirmações do `DIAG-01` batem) e atualizados pela convenção do próprio diagrama — `(NÃO EXERCITADO)` para código que existe e não roda.

**Commit.** `7016c81` · procedência **completa**

### 2026-10-28 · `DOC-12` 🔄

**O defeito.** O diário dizia que o trabalho anterior a 29/04 não estava no repositório; estavam lá sete commits de 18–19/02.

**Como foi encontrado.** *inventário* — 29/04 é a data do clone no reflog, e a entrada de abertura a tomou pelo início do histórico — contra o aviso da própria seção 'Sobre as datas'.

**A correção.** Entrada reconstruída a partir dos sete commits; a lacuna real ficou delimitada (nenhum commit de 20/02 a 30/05).

**🔄 A premissa estava errada.** O registro do projeto é fonte confiável sobre o próprio projeto. Tem a mesma autoridade de um documento de terceiro e a mesma chance de estar errado — e um `git log --reverse` custava um segundo.

**Commit.** `7016c81` · procedência **completa**

### 2026-10-28 · `DOCS-WIN-01`

**O defeito.** A linha do `DOCS-WIN-01` no backlog estava partida em seis desde o commit `4014798`, com um CR solto no meio.

**Como foi encontrado.** *leitura* — O texto citava `\n`, `\r\n` e `\r` como exemplo, e o script que o gravou os converteu em caracteres de controle.

**A correção.** Linha reconstruída a partir dos bytes; conferido que nenhuma linha de tabela ficou sem `|` final.

**Nota.** Achado na revisão dos patches pedida pelo Vitor antes do commit.

**Commit.** `2254934` · procedência **completa**

### 2026-10-28 · `PERFIL-02`

**O defeito.** O README das migrações não listava a 008, e a tabela estava fora de ordem (007, 006, 005, 004).

**Como foi encontrado.** *leitura* — A 008 foi escrita depois do README, e nada confere um contra o outro.

**A correção.** Tabela em ordem, com a 008 e a 009, a seção de diagnóstico e a armadilha dos privilégios padrão.

**Commit.** `040fe4b` · procedência **completa**

### 2026-10-30 · `FW-07`

**O defeito.** A pendência gerada do `FW-07` seguiu descrevendo buffer no RTC e Deep Sleep depois de o `ARQ-01` decidir a C2 (sono leve).

**Como foi encontrado.** *leitura* — A propagação da decisão atualizou a linha do `FW-07` no backlog e não a pendência em `consolidar_registro.py` — o mesmo padrão do `DOC-05` de 29/10, ao contrário.

**A correção.** Pendência reescrita na mesma leva do `API-03`, que ao fechar precisou ler a linha vizinha.

**Nota.** Dano: zero (a decisão ainda não tinha saído da branch). Mostra de novo o que o `DOC-13` registra: nada confere a linha do backlog contra a pendência gerada.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (iii) do diário)` · procedência **parcial**

### 2026-10-30 · `FW-07`

**O defeito.** O `firmware/nucleo/README.md` e o texto que o `make capacidade` imprime seguiam dizendo que o `sketch.ino` reescrito usaria 128 épocas no RTC, porque o heap não sobrevive ao Deep Sleep, e que o `API-03` era item aberto.

**Como foi encontrado.** *leitura* — A propagação da C2 (30/10) passou pelo backlog, pelo `CLAUDE.md` e pelos documentos de decisão, e não pelos textos do núcleo — que são os que quem for escrever o sketch lê primeiro. O fechamento do `API-03` também não voltou a eles.

**A correção.** Os dois textos reescritos para a C2 (heap, flash do `FW-08`) e para o `API-03` fechado, com nota de correção.

**Nota.** Achado ao escrever a parte (a) do `FW-07`, lendo o README para acrescentar a seção da cadeia. Dano: zero (o sketch não foi escrito). Terceira vez no mesmo dia que a propagação de uma decisão esquece um texto — o padrão que o `DOC-13` registra.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (v) do diário)` · procedência **parcial**

### 2026-10-29 · `DOC-05`

**O defeito.** A linha do `DOC-05` no backlog dizia que o `CLAUDE.md` está no `.gitignore` e que toda correção nele fica fora do git — ele é versionado desde 27/10.

**Como foi encontrado.** *leitura* — Fechar o `DOC-11` atualizou a pendência gerada do `DOC-05` e não a linha do item no backlog.

**A correção.** Linha corrigida, com a marca ✏️; o `DOC-13` ganhou a ressalva de que a guarda proposta não pegaria este caso.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 29/10 (iv) do diário)` · procedência **parcial**

### 2026-10-29 · `DATA-03`

**O defeito.** O resumo, o quadro e o caminho crítico do backlog citavam como pendentes seis itens fechados — e o primeiro conselho do arquivo era rodar o `DATA-03`, fechado na véspera.

**Como foi encontrado.** *leitura* — Fechar um item mexia na linha dele e na contagem; ninguém buscava o ID no resto do arquivo.

**A correção.** As três seções reconferidas contra as linhas dos itens e corrigidas, com a marca ✏️ onde o texto mudou.

**Nota.** §6 das lições, ocorrência 8. Achado por leitura, ao responder o que fazer a seguir; a guarda que faltava virou o `DOC-13`.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 29/10 (iii) do diário)` · procedência **parcial**

### 2026-10-17 · `(ii)`

**O defeito.** Uma afirmação da própria sessão saiu sem conferência: 'o `README.md` manda ler `METODOLOGIA.md`, `HARDWARE.md` e `DATASET.md`'.

**Como foi encontrado.** *inventário* — Conferido, ele os lista **pelo nome, sem caminho**, na árvore de 'Estrutura'. O efeito sobre quem clona é o mesmo; a afirmação não era — e a verificação (3) não os pegaria por ali.

**A correção.** Corrigida no mesmo dia, e registrada.

**Nota.** É o §3 do próprio documento de lições, cometido enquanto ele era escrito.

**Commit.** `3127c38` · procedência **completa**

### 2026-10-17 · `(iii)`

**O defeito.** 'Reportei duas afirmações falsas e eram três' — conferi o lugar errado do arquivo certo.

**Como foi encontrado.** *inventário* — Procurei no `LGPD-ELIMINACAO.md` a tabela de citações da Lei, cuja coluna é *'Confere?'* — ela afirma que a **citação** do artigo está correta, não que o direito esteja implementado —, concluí que o arquivo estava certo e segui. A afirmação falsa estava trinta linhas abaixo, na lista de notas.

**A correção.** A terceira afirmação corrigida.

**Nota.** É o §5 aplicado a quem escrevia o §5: o artefato que eu abri não era o que decidia a resposta, era o vizinho dele.

**Commit.** `c80c2b8` · procedência **completa**

### 2026-10-31 · `FW-08` 🔄

**O defeito.** O estudo do buffer, o backlog, a pendência gerada e dois documentos de decisão diziam que a partição de dados padrão tem **1,5 MiB** e cobre **13,7 dias**. A tabela padrão do `arduino-esp32` tem 0x160000 = **1 408 KiB** de dados.

**Como foi encontrado.** *leitura* — O estudo de 29/09 citou `tools/partitions/default.csv` sem abrir o arquivo; o 1,5 MiB virou constante de `estudo_buffer.py` e de `capacidade.cpp`, e o 13,7 dias se propagou a partir dali. A `--conferir` do estudo testava a conta, não o dado de entrada.

**A correção.** Constante corrigida para 0x160000 nos dois lugares, com nota. A tabela que o projeto usa passou a ser versionada (`firmware/partitions.csv`) e `make capacidade` mede a cobertura sobre ela, em vez de sobre uma constante.

**🔄 A premissa estava errada.** O número entrou como fato de folha e foi tratado como estável, quando depende da versão do pacote `arduino-esp32` — que é justamente o argumento para versionar a tabela.

**Nota.** Dano: superestimava em 9 %. Nenhuma decisão mudou: mais de uma semana em qualquer das duas tabelas.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (iii) do diário)` · procedência **parcial**

---

## Infraestrutura — 23 defeitos

*13 execução · 4 inventário · 4 leitura · 1 controle positivo · 1 terceiro*

### 2026-10-28 · `DOCS-WIN-01` 🔄

**O defeito.** `conferir_docs_versionados.py` dava resultado errado no Windows: a verificação (3) não enxergava ponteiro nenhum, e a (2) acusava arquivos ignorados como pendentes.

**Como foi encontrado.** *execução* — O pipe em modo texto traduz `\n` em `\r\n` no Windows; todo caminho menos o último chegava ao `git check-ignore` com `\r` no fim e não casava regra nenhuma.

**A correção.** Entrada em bytes e `encoding` explícito — também no `verificar_por_mutacao.py`, que morria em `cp1252`. Controle positivo: a mesma árvore dá 8 ponteiros em Linux e 0 no Windows antes; 8 nos dois depois.

**🔄 A premissa estava errada.** Uma verificação que passa no CI vale em qualquer máquina. O CI (Ubuntu) estava verde e certo; a máquina de quem edita, que é onde a (1) existe para rodar, media errado em silêncio.

**Commit.** `ca01355` · procedência **completa**

### 2026-10-28 · `DOCS-WIN-02`

**O defeito.** `calculos_tcc.py` e `estudo_buffer.py` quebravam no console do Windows — o primeiro no `--conferir`, depois de as asserções baterem, de modo que o exit 1 parecia reprovação dos cálculos.

**Como foi encontrado.** *execução* — Saída com símbolos fora do `cp1252` (✓, ĝ, σ). Registrado em 28/10 só para o `calculos_tcc`; medir os dois scripts nos dois modos mostrou que o relatório do `estudo_buffer` também quebrava.

**A correção.** `sys.stdout.reconfigure(encoding='utf-8')` nos dois. Controle: com um valor sabotado, o `--conferir` sai 1 e diz o que falhou.

**Commit.** `7016c81` · procedência **completa**

### 2026-10-28 · `SEC-13`

**O defeito.** O verificador de migrações reaplicava os GRANTs depois das migrações e não via uma migração que tirasse privilégio do código de main.

**Como foi encontrado.** *controle positivo* — O mesmo desenho do `conftest.py` da suíte de RLS, copiado.

**A correção.** GRANTs aplicados uma vez, logo depois da 001; a sabotagem passou a ser acusada ('permission denied for table sleep_data'). Na suíte de RLS ficou como item (`SEC-13`).

**Commit.** `040fe4b` · procedência **completa**

### 2026-10-30 · `ML-11`

**O defeito.** O commit do `ML-11` (PR #13) não chegou a `develop`: a PR foi mesclada na branch da #12, que já tinha entrado em `develop` 19 s antes.

**Como foi encontrado.** *inventário* — A #13 foi aberta empilhada, com base na branch da #12, contando que o GitHub a redirecionaria para `develop` quando a #12 entrasse; o redirecionamento não acontece quando a base é mesclada e a PR de cima é mesclada logo em seguida, na base velha.

**A correção.** O trabalho seguinte partiu da branch que contém o `ML-11` e a PR aponta para `develop`, levando os dois. Regra no `CLAUDE.md`: PR sempre com base em `develop`.

**Nota.** Achado ao conferir `gh pr view 13` antes de começar o trabalho seguinte; nenhum dado se perdeu, mas `develop` ficou sem o `ML-11` por algumas horas.

**Commit.** `(o commit que introduz esta linha: um commit não cita o próprio hash — ver a entrada de 30/10 (ii) do diário)` · procedência **parcial**

### 2026-02-18 · `(bootstrap)`

**O defeito.** O `requirements.txt` não era UTF-8, e o import de `routes` quebrava no Vercel com `ModuleNotFoundError`.

**Como foi encontrado.** *execução* — Codificação do arquivo e `sys.path` do runtime serverless.

**A correção.** Conversão para UTF-8 e `sys.path` ajustado em dois commits.

**Commit.** `ac1a29e, 374e254, 16448e1` · procedência **completa**

### 2026-02-19 · `(bootstrap)`

**O defeito.** Conflito de versão do cliente Supabase produzia erro de proxy, e o *lazy loading* era simulado.

**Como foi encontrado.** *execução* — `httpx` não pinado contra a versão do `supabase`.

**A correção.** `supabase` em 2.28.0, `httpx` fixado, e *lazy loading* real.

**Commit.** `739f24e, 5d2c513` · procedência **completa**

### 2026-06-02 · `FIX-01`

**O defeito.** `/api/sleep-history` devolvia 500 quando o banco falhava.

**Como foi encontrado.** *execução* — Exceção da camada de banco subindo sem tratamento.

**A correção.** Resposta de erro própria, com teste cobrindo o caminho.

**Commit.** `eace580, 7b9e52a` · procedência **completa**

### 2026-06-02 · `FIX-02` 🔄

**O defeito.** `POST /api/data` respondia **`201 Created` sem gravar**: o dispositivo recebia confirmação de um dado que não existia.

**Como foi encontrado.** *leitura* — A resposta `201` era emitida **antes** de o resultado da escrita ser verificado, então a falha do Supabase não virava erro HTTP.

**A correção.** A resposta passou a depender do resultado da escrita, com testes para 201 persistido, 503 sem persistir e 400 com JSON inválido.

**🔄 A premissa estava errada.** A hipótese de partida era 'problema de leitura' — o dado estaria gravado e a consulta não o traria. É a **primeira ocorrência registrada** do padrão que se repete em todo o projeto, *confirmação emitida antes da verificação* (§6), e que reaparece no `APP-10`, no `UI-10` e no `PERFIL-01`.

**Commit.** `42d543a, c92ed58` · procedência **completa**

### 2026-06-03 · `FIX-03 / FIX-04`

**O defeito.** Faltava `load_dotenv()` no `app.py`, e o `teste_conexao.py` chamava uma API que não existia.

**Como foi encontrado.** *execução* — O `.env` não era carregado em desenvolvimento local; o script de diagnóstico usava uma interface antiga.

**A correção.** `load_dotenv()` acrescentado e o script reescrito sobre `db.get_client()`.

**Commit.** `0ad144b, 21f3255` · procedência **completa**

### 2026-06-03 · `FIX-05 / FIX-07`

**O defeito.** `charts.js` era código morto não referenciado, e o `fake_sensor.py` usava `requests` em vez do `httpx` já pinado.

**Como foi encontrado.** *leitura* — Resíduo de versões anteriores.

**A correção.** `charts.js` removido; `fake_sensor.py` passou a `httpx`.

**Commit.** `2dfe5b5, 84f5a0c` · procedência **completa**

### 2026-08-19 · `FIX-08`

**O defeito.** Log com emoji e ausência de garantia de não-500 na camada de banco.

**Como foi encontrado.** *execução* — Emoji quebrava a codificação do log no runtime; a camada de banco podia propagar exceção.

**A correção.** Log sem emoji e garantia de não-500.

**Commit.** `ec5f8b0` · procedência **completa**

### 2026-08-21 · `(CI)`

**O defeito.** O CI **não disparava** em `chore`, `docs`, `security` e `ci` — cobria só `feature` e `bugfix`.

**Como foi encontrado.** *leitura* — Lista de prefixos em `on.push.branches` incompleta, e descoberta depois de uma branch desse tipo passar sem verificação nenhuma.

**A correção.** Prefixos acrescentados.

**Nota.** Vale registrar porque é o que torna a branch de trabalho atual (`chore/GIT-01-…`) coberta pelo gatilho — e é a única razão pela qual o push, quando sair, fará o CI rodar.

**Commit.** `ba9f31a` · procedência **completa**

### 2026-08-21 · `(repo)`

**O defeito.** Material interno estava no repositório público, e o README da `web-app` descrevia um front Jinja já aposentado.

**Como foi encontrado.** *inventário* — Conteúdo de trabalho versionado por inércia.

**A correção.** Material interno retirado; front Jinja aposentado e README corrigido.

**Commit.** `9b4052e, 9b187ee` · procedência **completa**

### 2026-09-18 · `GIT-01` 🔄

**O defeito.** `git status` acusava 144 arquivos modificados com **20 243 inserções e 20 243 remoções** — o mesmo número dos dois lados — e nenhuma mudança de conteúdo.

**Como foi encontrado.** *execução* — `git diff --ignore-cr-at-eol` devolveu **vazio**: editar no Windows salvava CRLF no disco enquanto o histórico guardava LF.

**A correção.** `.gitattributes` com `* text=auto`, tipos declarados explicitamente para o caso de o heurístico hesitar, `*.sh text eol=lf` (com CRLF o interpretador lê `#!/bin/bash\r` e não encontra o programa) e binários marcados `binary`, porque uma única conversão corrompe o arquivo.

**🔄 A premissa estava errada.** A hipótese era que alguma ferramenta havia reformatado o repositório. E o problema real não era a feiura do diff: era que um ajuste de três linhas ficava indistinguível de vinte mil linhas de nada, e **revisão que não se consegue fazer não se faz**. Quantos diffs passaram sem revisão nesse período não é recuperável.

**Commit.** `f188ec9` · procedência **completa**

### 2026-09-22 · `GIT-04` 🔄

**O defeito.** **Três documentos nunca commitados**, entre eles a fundamentação que os READMEs mandam ler.

**Como foi encontrado.** *inventário* — Comparação de `git ls-files docs/` com o conteúdo da pasta — e o problema não estava sendo procurado. Os três: `BACKLOG-COMPLETO.md`, `ML-DATASETS-E-PLANO.md` e `SINTESE-PESQUISA-E-CAMINHOS.md`.

**A correção.** Versionados na mesma revisão. A prevenção ficou registrada como `CI-05`.

**🔄 A premissa estava errada.** A premissa era que o que está em `docs/` está versionado, exceto o que o `.gitignore` exclui de propósito. Um clone feito no dia anterior não traria a fundamentação junto, e quem clonasse encontraria READMEs apontando para um arquivo inexistente. E nada impedia que acontecesse de novo — o `CI-05`, **como foi especificado naquele momento, não impediria.**

**Commit.** `6264934, aae01f3` · procedência **completa**

### 2026-09-30 · `CI-05` 🔄

**O defeito.** A prevenção especificada **não podia reprovar**: um job que falha 'quando há arquivo não rastreado em `docs/`' devolveria vazio sempre.

**Como foi encontrado.** *leitura* — Não foi uma execução, foi um raciocínio sobre o que o `actions/checkout` monta: o git envia **objetos commitados e nada mais**, então num runner **não existe** arquivo não rastreado em `docs/` — não porque o repositório esteja limpo, mas porque o arquivo não rastreado nunca sai da máquina de quem o escreveu.

**A correção.** Reimplementado com **duas** verificações de alcance declarado em `scripts/conferir_docs_versionados.py`: (1) órfão na árvore, **só detectável na máquina de quem edita**, e o script **diz isso** quando roda com `CI` no ambiente; (2) referência pendente — `docs/*.md` citado por arquivo rastreado e ausente do git **e** do `.gitignore` —, que **roda e reprova no CI**, porque tanto a citação quanto a ausência viajam no commit.

**🔄 A premissa estava errada.** A premissa era que a especificação estava correta e o trabalho era de transcrição. O resultado seria **um selo verde que não verificou nada**, contra uma classe de problema que o `GIT-04` já demonstrou ser real. A distinção que o script passou a usar é a única que importa: **ignorado é decisão, não rastreado e não ignorado é esquecimento.** E os outros dois itens do lote mudaram de natureza na direção oposta — ficaram mais baratos: o `CI-03` pedia uma toolchain de 300 MB e o repositório já tinha a verificação; o `CI-04` parecia exigir os ~46 GB de dado e não exige.

**Commit.** `6312267` · procedência **completa**

### 2026-10-16 · `CI-05`

**O defeito.** Na primeira execução, **o verificador se acusava a si mesmo**: reprovou com três referências pendentes, e as três eram prosa.

**Como foi encontrado.** *execução* — `docs/FOO.md` e `docs/sub/FOO.md` estão no comentário do próprio `PADRAO_REFERENCIA`, para explicar o que o regex casa, e `docs/ORFAO-DE-TESTE.md` está no backlog, dentro do procedimento de validação **deste mesmo script**. Job vermelho desde o primeiro push.

**A correção.** `EXEMPLOS_EM_PROSA`, isenção estreita e **impressa a cada execução** — porque isenção silenciosa é como uma verificação deixa de verificar sem ninguém notar. Vale **só para a verificação (2)**: na (1) o nome não tem isenção, senão o próprio procedimento de validação ficaria incapaz de falhar.

**Nota.** Validado nas duas direções: órfão criado → a (1) acusa; doc inexistente citado de dentro de arquivo versionado → a (2) acusa; árvore limpa → exit 0, inclusive com `CI=true`.

**Commit.** `7feeef9` · procedência **completa**

### 2026-10-16 · `CI-04` 🔄

**O defeito.** A guarda de coleta estava **37 testes defasada**: piso em 70, suíte com 107. Ela toleraria perder **um terço da cobertura** sem reprovar.

**Como foi encontrado.** *execução* — O piso foi medido em 22/09 e nada o reconferia.

**A correção.** Piso em 107, com o motivo e a obrigação de atualizar escritos ao lado. Controle positivo real, não simulado: `import` inexistente em `testes/test_avaliar.py` → coleta cai a 100 → a guarda reprova.

**🔄 A premissa estava errada.** **É o próprio modo de falha que ela existia para pegar**, com piso alto o bastante para parecer que pegava. E ela é necessária ali por um detalhe que vale registrar: o passo roda o pytest com `|| true`, então o exit 2 da coleta sumiria — quem acusa é a contagem.

**Commit.** `6359912` · procedência **completa**

### 2026-10-16 · `CI-06` 🔄

**O defeito.** **Quatro** jobs nunca rodaram num runner, não três — e o CI não roda desde 2026-09-10.

**Como foi encontrado.** *terceiro* — Medido na API pública do Actions: a última execução é a **#131, de 10/09**, em `develop`, com sucesso. O `ci.yml` que existia em `develop` naquela data tinha **dois** jobs (`test`, `frontend`); o da branch tem seis. O quarto é o `rls`, que entrou em 28/09 — dezoito dias depois da última execução.

**A correção.** A contagem foi corrigida no registro. **Nada foi executado**: a tentativa de push foi recusada por ausência de credencial de escrita no ambiente.

**🔄 A premissa estava errada.** A categoria 'escrito, não executado' sempre teve um item a mais do que o backlog contava, **e o item a mais é justamente o que carrega a afirmação de segurança do trabalho** (`SEC-05`, isolamento entre usuários). Com a distinção que precisa ser feita com cuidado: os testes de RLS **não são código nunca executado** — rodaram localmente contra Postgres de verdade. O que nunca aconteceu é o **job** rodar, isto é, a guarda contra pulo silencioso ser exercitada no lugar onde ela precisa funcionar; e a perna da **Postgres 16**, já que o harness foi verificado na 14.

**Commit.** `6443005` · procedência **completa**

### 2026-10-17 · `GIT-05` 🔄

**O defeito.** O aviso de captação foi escrito num arquivo que **não chega a um clone**: o `ROADMAP.md` está no `.gitignore`. A varredura achou **oito** arquivos ignorados que arquivos rastreados mandam ler.

**Como foi encontrado.** *execução* — Descoberto porque `git status` **não acusou** a edição. O `ROADMAP.md` é citado por 8 arquivos rastreados, inclusive `frontend/src/lib/metricas.ts`.

**A correção.** O aviso foi para o `README.md`, que é versionado. E entrou a verificação **(3)** em `scripts/conferir_docs_versionados.py`, validada por controle positivo nas duas direções.

**🔄 A premissa estava errada.** O `CI-05` **não acusa isso, e não por defeito**: sua verificação (2) trata *ignorado como decisão, não esquecimento*, e a distinção está certa. O que faltava é que ignorar é decisão sobre **distribuição** e não diz nada sobre o **ponteiro** que ficou no texto. ⚠️ E a (3) **nasceu com os oito dentro da isenção**, cada um com motivo impresso a cada execução: **hoje não cobre nenhum dos oito; pega o nono.** É catraca, não cobertura, e está dito assim no script, no `ci.yml` e no backlog — porque uma verificação que estreia com todas as violações atuais isentas é o §1 de novo se não se disser isso.

**Commit.** `688165c` · procedência **completa**

### 2026-10-17 · `PERFIL-01`

**O defeito.** O ID do item novo colidia com um item fechado: `ML-07` já existe.

**Como foi encontrado.** *inventário* — ID escolhido por lembrança. `ML-08` também estava tomado.

**A correção.** Renomeado para `LGPD-06` em todos os lugares que já o citavam.

**Nota.** Achado por `grep` de conferência **depois** de escrever, não por lembrança.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-17 · `PERFIL-01`

**O defeito.** O `conferir_docs_versionados.py` reprovou duas vezes em dez minutos, contra quem o escreveu.

**Como foi encontrado.** *execução* — Caminho de arquivo abreviado com reticências no meio do nome: a verificação (2) lê isso como citação de arquivo que um clone não traz. E o erro foi repetido ao **descrever** o erro.

**A correção.** Caminhos escritos inteiros.

**Nota.** Pequeno, e é a verificação (2) fazendo exatamente o que existe para fazer — o que vale registrar é que ela funcionou contra o autor, duas vezes seguidas.

**Commit.** `778ec27` · procedência **completa**

### 2026-10-17 · `(iii)`

**O defeito.** 208 linhas de conteúdo alheio entraram no diário, duplicando uma entrada.

**Como foi encontrado.** *execução* — O heredoc que escrevia o texto num arquivo temporário falhou por permissão, e o script seguinte leu um `/tmp/entrada.md` **pré-existente e de outro dono**.

**A correção.** Revertido e reescrito com ferramenta de arquivo. **A lição é de método:** script que lê arquivo temporário precisa falhar quando o arquivo não é o que ele acabou de escrever — `set -euo pipefail` no heredoc teria interrompido antes.

**Nota.** Apareceu em `git diff --numstat` como `208 0`, que é um número impossível para uma inserção de entrada única. **Conferir o `numstat` antes de commitar foi o que pegou.**

**Commit.** `(revertido antes de commit)` · procedência **parcial**

---

## Os defeitos que revelaram premissa errada

É a seção que o capítulo de desenvolvimento deve usar, porque é a única
em que o trabalho aprende algo em vez de só consertar algo. Em cada um
destes casos o enunciado de partida estava errado, e seguir o enunciado
com competência teria produzido a coisa errada bem feita.

| Data | Item | A premissa que caiu |
|---|---|---|
| 2026-09-28 | `SEC-05` | Que uma suíte contra Supabase mockado provava isolamento entre usuários. |
| 2026-10-17 | `PERFIL-01` | Que o teste de inserção alheia era barrado pela policy — era pela chave estrangeira. |
| 2026-10-17 | `PERFIL-01` | Que policy de `UPDATE` sem `with check` seria mais frouxa. |
| 2026-10-19 | `PERFIL-01` | Que o `upsert` não mexia nas colunas que o corpo da requisição não traz. |
| 2026-10-20 | `SEC-08` | Que o cadastro não revelava quem tem conta, porque `cadastrar` não ramifica. |
| 2026-10-20 | `SEC-08` | Que ligar a confirmação de e-mail tornaria idênticas as respostas para endereço novo e existente. |
| 2026-10-17 | `UI-10` | Que componente commitado e testado estava ao alcance do usuário. |
| 2026-10-17 | `DASH-12 / DASH-13` | Que os dois itens estavam feitos, como dizia o `ROADMAP.md` — estavam só do lado do servidor. |
| 2026-10-17 | `UI-11` | Que bastava a interface sobre a policy de `update` em `profiles` — e nada lê `profiles`. |
| 2026-10-19 | `UI-17` | Que provar o caminho de `import` provava que a tela é alcançável. |
| 2026-10-19 | `UI-16` | Que a varredura de exports mortos não deixava escapar código morto. |
| 2026-08-20 | `DATA-02` | Que os dois limites do critério de movimento representavam a mesma sensibilidade. |
| 2026-09-10 | `FW-06` | Que mudar a banda do filtro não mexia no limiar de movimento. |
| 2026-09-22 | `HW-05` | Que o prejuízo de uma queda de rede é a lacuna na série. |
| 2026-09-22 | `(sem item)` | Que código versionado num repositório com CI ao menos compila. |
| 2026-09-22 | `FW-07` | Que, tirados os travamentos, o sketch de produto serviria para captação noturna. |
| 2026-10-16 | `CI-03` | Que a lista de sketches escrita à mão cobria os sketches versionados. |
| 2026-10-17 | `DATA-07b` | Que coeficientes do filtro em `float32` bastavam. |
| 2026-10-17 | `DATA-07b` | Que cada rodada do harness de mutação partia de uma árvore limpa. |
| 2026-09-14 | `ML-01` | Que features clássicas de punho servem para o travesseiro, mudando só a escala. |
| 2026-09-14 | `DADOS-02` | Que a documentação do dataset descreve o dataset. |
| 2026-09-14 | `ML-02` | Que acurácia serviria como métrica de leitura. |
| 2026-09-15 | `ML-03` | Que a transferência entre posições de sensor seria simétrica. |
| 2026-09-15 | `ML-03b` | Que 'a normalização recupera 70% a 80%' valia para a matriz inteira. |
| 2026-09-18 | `ML-04` | Que a degradação entre coortes seria uniforme entre as modificações. |
| 2026-09-28 | `ML-05` | Que a concordância entre dois humanos daria um teto próximo de 1. |
| 2026-09-29 | `CALC-03` | Que o limiar de 1,2 m/s² vinha do ruído, e o item era só transpor a derivação. |
| 2026-09-29 | `DATA-07` | Que `d_angulo` é a diferença de `inclinacao_rel` entre épocas vizinhas. |
| 2026-09-29 | `DATA-07b` | Que as features já existiam em C++, e o item era transcrever. |
| 2026-09-30 | `DATA-07d` | Que uma suíte de paridade que passa verifica paridade. |
| 2026-09-30 | `DATA-07d` | Que os casos do dourado davam referência a todas as features. |
| 2026-09-29 | `REF-01` | Que citação escrita por quem leu o material está certa. |
| 2026-10-17 | `DOC-10 / UI-10` | Que a tela de exclusão existia, como afirmavam quatro documentos. |
| 2026-10-17 | `(iv)` | Que a política de privacidade acompanhava a tela entregue no mesmo dia. |
| 2026-10-17 | `DOC-11` | Que o arquivo de instruções descrevia o estado do projeto. |
| 2026-10-28 | `GIT-06` | Que uma conferência escrita chega ao backlog. |
| 2026-10-28 | `DOCS-WIN-01` | Que uma verificação que passa no CI vale em qualquer máquina. |
| 2026-10-28 | `ML-WIN-01` | Que o piso medido em duas plataformas valia para todas. |
| 2026-10-28 | `ML-WIN-01` | Que o relógio tinha resolução para um orçamento zero. |
| 2026-10-28 | `DOC-12` | Que 29/04 marcava o início do versionamento. |
| 2026-10-28 | `SEC-12` | Que objeto novo nasce sem privilégio para o cliente. |
| 2026-06-02 | `FIX-02` | Que o dado estava gravado e o problema era de leitura. |
| 2026-09-18 | `GIT-01` | Que alguma ferramenta havia reformatado o repositório. |
| 2026-09-22 | `GIT-04` | Que o que está em `docs/` está versionado, salvo o que o `.gitignore` exclui. |
| 2026-09-30 | `CI-05` | Que a especificação do job estava correta e o trabalho era de transcrição. |
| 2026-10-16 | `CI-04` | Que a guarda de coleta, medida em 22/09, ainda tinha o piso certo. |
| 2026-10-16 | `CI-06` | Que eram três, e não quatro, os jobs nunca rodados num runner. |
| 2026-10-17 | `GIT-05` | Que um aviso escrito no `ROADMAP.md` chega a quem clona. |
| 2026-10-31 | `FW-08` | Que o tamanho da área de dados da tabela padrão era um dado conhecido e estável. |
| 2026-10-31 | `SEC-11` | Que ligar o captcha no painel era uma mudança só de configuração. |

**50 de 130.** E a distribuição por instrumento dentro
deste subconjunto é a parte que vale registrar:

| Instrumento | Premissas derrubadas |
|---|---:|
| execução | 15 |
| inventário | 10 |
| controle positivo | 9 |
| terceiro | 5 |
| leitura | 5 |
| cálculo | 4 |
| uso real | 1 |
| dado real | 1 |

**41 das 50 premissas caíram quando alguém saiu
do próprio raciocínio** — rodando, sabotando, conferindo o artefato,
abrindo a especificação do fornecedor, ou preenchendo o formulário como
usuário. As outras 9 caíram lendo e calculando, e vale
nomeá-las, porque são o contraexemplo da leitura fácil deste arquivo:

- **`DATA-02`** (cálculo) — O critério de movimento era assimétrico: 52% menos sensível para baixo do que para cima.
- **`FW-06`** (cálculo) — O filtro passa-baixa do MPU6050 estava na banda padrão de 260 Hz, e isso mudou o ruído de base.
- **`HW-05`** (leitura) — A medição esperava pela rede, e a série continuava saindo com aparência normal e base de tempo derivada.
- **`FW-07`** (leitura) — O sketch de produto tira **uma amostra por boot** e dorme: não registraria uma noite nem com rede perfeita.
- **`CALC-03`** (cálculo) — O limiar de 1,2 m/s² em uso **não foi derivado do ruído**, e a derivação clássica `g ± k·σ` não o gera nem o explica.
- **`DATA-07`** (cálculo) — `d_angulo` **não** é a diferença de `inclinacao_rel` entre épocas vizinhas, e guardar só uma das duas não reconstrói a outra.
- **`FIX-02`** (leitura) — `POST /api/data` respondia **`201 Created` sem gravar**: o dispositivo recebia confirmação de um dado que não existia.
- **`CI-05`** (leitura) — A prevenção especificada **não podia reprovar**: um job que falha 'quando há arquivo não rastreado em `docs/`' devolveria vazio sempre.
- **`FW-08`** (leitura) — O estudo do buffer, o backlog, a pendência gerada e dois documentos de decisão diziam que a partição de dados padrão tem **1,5 MiB** e cobre **13,7 dias**. A tabela padrão do `arduino-esp32` tem 0x160000 = **1 408 KiB** de dados.

Os **4 de cálculo** são o detalhe que merece ficar: os
quatro saíram de **aritmética sobre números que já estavam escritos no
projeto** — uma subtração contra `g`, uma divisão por σ, uma desigualdade
triangular, uma raiz de banda. É o instrumento mais barato que existe
aqui, nenhum deles levou mais de um minuto, e os quatro derrubaram
premissa que estava em uso havia semanas. **Se há uma recomendação de
método que sai deste arquivo inteiro, é essa: antes de transpor um número
para o texto, divida-o por outro.**

E os **5 de leitura** têm traços que valem contra a
conclusão apressada de que ler não serve. Em quatro deles, o que a
leitura achou não foi um erro de escrita, foi uma **estrutura ausente** —
a resposta emitida antes da verificação, a conexão dentro do laço de
amostragem, a amostragem periódica que não existia, o job que não tinha
como reprovar. Nenhum apareceria rodando, porque em três dos quatro casos
**não havia o que rodar**. O quinto (`FW-08`, 31/10) é de outra natureza:
um número citado de um arquivo de terceiro que ninguém tinha aberto. A
conferência do estudo rodava e passava, porque testava a conta, não o
dado de entrada — só abrir o arquivo o derrubava.

---

## O que este arquivo não cobre

Registrado para que a ausência não passe por completude.

| Lacuna | Por quê |
|---|---|
| Defeitos anteriores a 2026-02-18 | Anteriores ao primeiro commit (`d74aa01`). Não há procedência. ✏️ **Até 28/10 esta linha dizia 29/04**, que é a data do clone no reflog, não do início do histórico — a mesma premissa estava no diário e nas lições, e foi corrigida lá no `DOC-12`. Entre 20/02 e 30/05 não há commit nenhum. |
| Grande parte de junho a agosto | O `HISTORICO.md` cobre o período e **não é versionado**, então não serve de procedência num capítulo de TCC. Os defeitos desse intervalo aqui saem de mensagem de commit, e por isso vários estão marcados `parcial`. |
| Todo defeito de hardware | **Nada foi medido no dispositivo físico.** Os 8 pinos do MPU6050 não estão soldados. A única medição de hardware do projeto é a de 25/08, que é a medição de um sensor mal conectado e serve só para dizer que não serve. Quando a bancada existir, é provável que esta seja a área mais cara do arquivo. |
| Defeitos que ninguém achou | Óbvio e precisa estar escrito, porque é o que invalida qualquer leitura das três derivações como taxa. |
| A fronteira `execução` × `inventário` | Traçada por critério declarado no cabeçalho do script, e há casos de fronteira. Quem discordar de uma classificação move uma linha na tabela e os números acompanham. |

