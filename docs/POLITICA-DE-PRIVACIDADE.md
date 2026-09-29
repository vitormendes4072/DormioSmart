# Política de privacidade — Smart Dormio

**Rascunho** · versão 0.1 · 2026-09-29 · item de backlog `LGPD-01`

> **Como ler este documento.** O que está entre as linhas `── TEXTO ──` é a
> política propriamente dita, redigida para ser publicada. O que está fora delas
> são **notas para o Vitor**, não para o titular nem para a banca — mesma
> convenção de `docs/CALCULOS-TCC.md` e `docs/LGPD-ELIMINACAO.md`.
>
> **Regra que governou a redação:** descrever **o que o sistema faz hoje**, não o
> que se pretende. Onde um direito não tem mecanismo implementado, o texto diz
> isso — não promete. Uma política que anuncia um canal inexistente é pior que
> uma política ausente: cria expectativa de conformidade que o sistema não
> sustenta, e é verificável em trinta segundos por quem quiser conferir.
>
> ⚠️ **Não publicar sem revisão jurídica.** Este rascunho foi escrito a partir do
> código, não a partir de assessoria. Ele descreve com precisão o que o sistema
> faz; ele **não** garante que o que o sistema faz basta.

---

## Notas de levantamento (não vão para o texto)

**Fontes.** Tudo abaixo foi conferido no código em 2026-09-29, não presumido:
`docs/diagramas/DIAG-04-modelo-de-dados-e-seguranca.md` (modelo ER e privilégio),
`web-app/migrations/001` a `007`, `web-app/validacao.py`, `web-app/routes.py`,
`frontend/src/`, `docs/DATA-CONTRACT.md` v2.5.0, `docs/LGPD-ELIMINACAO.md`.

**Correção de numeração — e ela afeta mais arquivos que este.** O
`LGPD-ELIMINACAO.md` pede, nas próprias notas, que os artigos sejam conferidos
antes da entrega, porque foram citados de memória. Conferidos:

| Onde o repositório diz | O correto | Conferido em |
|---|---|---|
| "eliminação — art. 18, **V**" | eliminação é o inciso **VI** | Lei 13.709/2018, art. 18 |
| — | o inciso **V** é **portabilidade** | idem |

O inciso V trata de *portabilidade dos dados a outro fornecedor*; a *eliminação
dos dados pessoais tratados com o consentimento do titular* é o **VI**. A troca
aparece em `docs/LGPD-ELIMINACAO.md`, `docs/DATA-CONTRACT.md` §6.2,
`web-app/routes.py`, `web-app/migrations/006` e no `BACKLOG-COMPLETO.md`.
Corrigida nos mesmos commits desta política.

Sobre `art. 13, §4º`: a citação **existe e é onde a pseudonimização é definida**,
mas o artigo inteiro trata de *estudos em saúde pública*, e por isso citá-lo
sozinho para sustentar "dado pseudonimizado continua sendo dado pessoal" é
frouxo. O argumento fica mais firme apoiado no **art. 12**, que retira do escopo
da lei apenas o dado **anonimizado** — de onde se segue, por contraste, que o
pseudonimizado permanece dentro. O texto abaixo usa essa formulação.

**O que eu NÃO consegui determinar pelo código, e você precisa decidir:**

1. **Quem é o controlador.** Pessoa física (você) ou a instituição de ensino? Muda
   o nome, o endereço e o canal de contato na abertura e no fim do texto. Deixei
   como `[CONTROLADOR]` e `[CONTATO]`.
2. **Base legal.** Escrevi **consentimento** (art. 7º, I) porque é o que a
   arquitetura sugere — cadastro voluntário, sem vínculo prévio. Se o uso for de
   pesquisa acadêmica com participantes recrutados sob TCLE e aprovação de comitê
   de ética, a base muda para o art. 7º, IV (*estudos por órgão de pesquisa*) e a
   política precisa ser reescrita em torno disso. **Essa decisão é sua e não
   dá para inferir do repositório.**
3. **Se haverá coleta real com terceiros.** Enquanto o único titular for você
   testando, quase nada disto vale na prática. No instante em que houver um
   segundo participante, vale tudo.

---

── TEXTO ────────────────────────────────────────────────────────────────────

# Política de Privacidade — Smart Dormio

**Última atualização:** 29 de setembro de 2026

O Smart Dormio é um protótipo acadêmico de monitoramento não invasivo de
movimento durante o sono, desenvolvido como trabalho de conclusão de curso. Esta
política descreve, com precisão e sem promessas, **o que o sistema faz hoje** com
os dados de quem o utiliza.

> **Aviso de natureza do serviço.** Este é um protótipo de pesquisa, não um
> produto comercial e não um dispositivo médico. Ele não diagnostica, não trata e
> não monitora condição de saúde alguma. As informações que apresenta não devem
> orientar decisão clínica de espécie nenhuma.

## 1. Quem trata os seus dados

O controlador dos dados é **[CONTROLADOR]**, que pode ser contatado em
**[CONTATO]**.

## 2. Que dados são coletados

### 2.1 Dados que você fornece

| Dado | Quando | Onde fica |
|---|---|---|
| **Endereço de e-mail** | No cadastro | Serviço de autenticação |
| **Senha** | No cadastro | Serviço de autenticação, apenas como *hash* — nunca em texto legível |
| **Nome** | No cadastro | Tabela de perfis |
| **Nome do dispositivo** | Ao parear um aparelho, opcional | Tabela de dispositivos |

### 2.2 Dados gerados pelo uso

O objeto do serviço é a **medição de movimento**. Cada leitura registra:

- **Aceleração nos três eixos** e a **magnitude** do vetor de aceleração;
- Um **rótulo de estado** — "Repouso" ou "Movimento" — calculado pelo próprio
  dispositivo a partir da magnitude;
- A **temperatura do circuito integrado do sensor**, quando o aparelho a tiver;
- Leituras do **giroscópio**, quando o aparelho o tiver;
- Dois **instantes**: quando a medição foi feita e quando ela chegou ao servidor;
- A **duração da janela** resumida pela leitura e o **método** usado para
  resumi-la;
- O **identificador do aparelho** que enviou.

Quando o sensor é um **celular**, esses dados vêm da API de movimento do
navegador, e **somente enquanto a tela de coleta estiver aberta e com sua
permissão explícita**. O navegador solicita essa permissão; negá-la impede a
coleta por esse caminho e não afeta o restante do aplicativo.

### 2.3 O que é armazenado no seu navegador

- A **sua sessão de acesso**, mantida pela biblioteca de autenticação para que
  você não precise entrar novamente a cada recarregamento;
- A **sua preferência de tema** (claro ou escuro).

**Não há cookies de rastreamento, de publicidade ou de análise de audiência**, e
o serviço não integra nenhuma ferramenta de medição de comportamento.

### 2.4 O que o sistema explicitamente NÃO coleta

- **Áudio, imagem ou vídeo.** O aparelho não tem microfone nem câmera.
- **Localização.** Nem do aparelho, nem do navegador.
- **Dados de contatos, agenda, aplicativos instalados ou navegação.**
- **Idade.** A estrutura do banco tem um campo para ela, herdado de uma versão
  anterior do projeto, mas **nenhuma tela o preenche e nenhuma funcionalidade o
  utiliza**. Ele está vazio para todos os titulares.

### 2.5 Sobre a natureza dos dados de movimento

Convém ser explícito, porque o assunto merece: **a série temporal de movimento
noturno é um dado sobre o seu corpo.** Ainda que não constitua diagnóstico e não
seja tratada aqui como dado de saúde, ela descreve seu comportamento durante o
sono, e uma série longa o bastante é, por si, capaz de distinguir uma pessoa de
outra. É por essa razão que este serviço **não anonimiza** os dados como
alternativa a apagá-los (seção 6.4).

## 3. Para que os dados são usados

Exclusivamente para:

1. **Apresentar a você as suas próprias medições**, no painel do aplicativo;
2. **Permitir que você exporte** as suas medições;
3. **Manter sua conta funcionando** — autenticar, associar cada leitura ao seu
   dono, distinguir os seus aparelhos.

**Não há nenhum outro uso.** Os dados não são usados para publicidade, não são
vendidos, não são cedidos, não alimentam perfilamento comercial e não são
combinados com dados de outras fontes.

> **Sobre o uso dos dados em pesquisa.** Os resultados de aprendizado de máquina
> deste trabalho foram obtidos sobre **bases públicas de terceiros**, com dados
> de outros indivíduos, obtidas sob acordo de uso — **não** sobre dados de
> usuários deste serviço. Caso venha a existir intenção de usar dados coletados
> aqui em pesquisa, isso exigirá consentimento específico e separado, e esta
> política será atualizada **antes**, não depois.

## 4. Com que base legal

O tratamento se apoia no **seu consentimento** (Lei nº 13.709/2018, art. 7º, I),
manifestado ao criar a conta e ao autorizar o acesso ao sensor de movimento. Você
pode revogá-lo a qualquer momento apagando sua conta (seção 6.4).

## 5. Quem tem acesso

### 5.1 Dentro do sistema

O isolamento entre usuários **não depende de código da aplicação**: é imposto
pelo próprio banco de dados, por políticas de segurança em nível de linha, que
restringem toda leitura e toda escrita ao titular autenticado. Uma falha de
programação na aplicação não é suficiente para expor os dados de um titular a
outro.

O credencial usada pelos aparelhos para enviar leituras **não consegue ler dado
nenhum**: ela tem permissão para executar três funções específicas e não tem
privilégio sobre nenhuma tabela. O aparelho também não informa a quem pertence a
leitura — o dono é determinado dentro do banco, a partir da credencial.

### 5.2 Operadores

O serviço utiliza dois fornecedores de infraestrutura, que tratam os dados por
conta do controlador:

| Operador | Papel |
|---|---|
| **Supabase** | Banco de dados e autenticação |
| **Vercel** | Hospedagem da aplicação e da interface |

**Transferência internacional.** Os servidores desses fornecedores podem estar
**fora do Brasil**. Isso caracteriza transferência internacional de dados
(art. 33 e seguintes da Lei nº 13.709/2018).

### 5.3 O administrador do sistema

O responsável pelo projeto tem, por necessidade operacional, acesso
administrativo ao banco de dados, e portanto **acesso técnico aos dados
armazenados**. Esse acesso não é usado para consultar medições individuais fora
do que a manutenção do serviço exigir.

## 6. Seus direitos, e como exercê-los **hoje**

Esta é a seção que esta política existe para ser honesta. A lei assegura os
direitos abaixo. O que segue diz, para cada um, **se há mecanismo implementado**.

### 6.1 Confirmação de que há tratamento, e acesso aos dados (art. 18, I e II)

✅ **Implementado.** Entre na sua conta: o painel exibe as suas medições. Não há
nenhuma categoria de dado seu que o aplicativo colete e não mostre.

### 6.2 Portabilidade (art. 18, V)

✅ **Implementado, com uma limitação declarada.** Em *Configurações → Seus dados*
há a exportação em CSV, com instante, magnitude, intensidade, temperatura e
estado de cada leitura.

⚠️ **A exportação traz no máximo 2.000 leituras**, as mais recentes. Uma noite de
oito horas em épocas de 30 segundos produz cerca de 960 leituras, então o limite
cobre a noite mais recente com folga — mas **não** um histórico longo. Se você
tiver mais que isso e precisar do conjunto completo, solicite pelo canal da seção
8.

### 6.3 Correção de dados incompletos, inexatos ou desatualizados (art. 18, III)

⚠️ **Parcialmente implementado.**

- **Nome do dispositivo:** pode ser alterado em *Configurações → Meus
  dispositivos*.
- **Seu nome e seu e-mail:** **não há tela para alterá-los.** O aplicativo os
  exibe, e só. Para corrigi-los, é necessário solicitar pelo canal da seção 8.
- **Medições já registradas:** **não são alteráveis, por decisão de projeto** — e
  isso é deliberado, não uma lacuna. O banco não concede permissão de atualização
  sobre as leituras. Apagar é visível: a linha sai. Editar seria invisível, e
  destruiria o valor probatório do conjunto. Se uma medição estiver errada, o
  caminho é apagá-la, não reescrevê-la.

### 6.4 Eliminação (art. 18, VI) e revogação do consentimento (art. 18, IX)

✅ **Implementado.** Em *Configurações → Excluir conta*. A operação exige que você
digite uma frase de confirmação, e é **irreversível**. Ela apaga:

- todas as suas leituras;
- todos os seus dispositivos;
- o seu perfil.

⚠️ **Pode haver remoção parcial, e o aplicativo diz quando há.** O cadastro de
acesso — a linha que guarda o **seu e-mail** — pertence ao serviço de
autenticação, e a permissão para removê-la pode não estar disponível na
configuração do projeto. Quando não estiver, os dados acima são apagados, **o seu
e-mail permanece**, e a tela informa isso explicitamente, em vez de anunciar
sucesso. Nesse caso, a remoção do cadastro depende de solicitação pelo canal da
seção 8.

> **Por que eliminação e não anonimização.** Uma série temporal de acelerometria
> noturna com carimbo de tempo não é razoavelmente anonimizável: a própria série
> funciona como identificador quando cruzada com outra fonte. Como a lei retira
> de seu alcance apenas o dado efetivamente **anonimizado** (art. 12), desvincular
> a leitura do seu dono não cumpriria o direito de eliminação — apenas produziria
> um registro órfão que continuaria sendo dado pessoal. Por isso as linhas são
> removidas de fato.

### 6.5 Anonimização ou bloqueio de dados desnecessários ou excessivos (art. 18, IV)

❌ **Sem mecanismo implementado.** Não existe função de bloquear temporariamente o
tratamento nem de anonimizar um subconjunto das suas leituras. O que existe é a
eliminação total (6.4) e a eliminação de leituras individuais pela API. Uma
solicitação por esse direito será atendida manualmente, pelo canal da seção 8.

### 6.6 Informação sobre compartilhamento (art. 18, VII)

✅ **Atendido por esta política.** A seção 5 lista integralmente com quem os dados
são compartilhados. Não há outros.

### 6.7 Informação sobre a possibilidade de não consentir (art. 18, VIII)

✅ **Atendido por esta política.** Você pode não criar conta, e nesse caso nenhum
dado seu é tratado. Pode criar conta e não autorizar o sensor de movimento do
celular: o aplicativo funciona, e apenas a coleta por esse caminho fica
indisponível. Pode, a qualquer momento, apagar tudo (6.4).

### 6.8 Prazo de resposta

Os direitos com mecanismo implementado (6.1, 6.2, 6.4) são exercidos por você
mesmo, na hora, sem intermediação humana. Para os que dependem de solicitação
(6.3 parcialmente, 6.5), **não há prazo de atendimento comprometido**, porque não
há estrutura de atendimento: este é um protótipo acadêmico mantido por uma
pessoa. Dizê-lo é mais útil que anunciar um prazo que não seria cumprido.

## 7. Por quanto tempo os dados são guardados

**Por prazo indeterminado, até que você os apague.**

⚠️ Sejamos precisos, porque aqui é fácil parecer melhor do que se é: **não existe
política de retenção implementada**. Não há expurgo automático, não há prazo após
o qual leituras antigas sejam descartadas, não há inatividade que dispare
remoção. Uma leitura enviada hoje permanece no banco indefinidamente, a menos que
você use a exclusão da seção 6.4.

Isso é uma **limitação declarada**, não uma escolha de desenho: uma política de
retenção é trabalho não executado. Enquanto não existir, o controle está
inteiramente com você.

## 8. Contato

Para exercer qualquer direito que não tenha mecanismo na interface, ou para
qualquer dúvida sobre esta política: **[CONTATO]**.

## 9. Segurança

O que existe, concretamente:

- **Senhas** são armazenadas apenas como *hash*, pelo serviço de autenticação.
- **Credenciais de dispositivo** são guardadas apenas como *hash* SHA-256, numa
  tabela à qual o navegador não tem acesso algum. O valor em texto é exibido uma
  única vez, no pareamento, e descartado.
- **Isolamento entre titulares** é imposto pelo banco de dados, não pela
  aplicação, e é verificado por 105 testes automatizados contra um banco real —
  incluindo os casos adversariais, em que se tenta ler e apagar dado alheio.
- **A credencial de ingestão** não tem privilégio sobre tabela nenhuma.
- **Toda leitura enviada é validada** — faixa física, coerência interna, recusa de
  instante futuro e de sensor que responde mas não mede.

Nenhuma dessas medidas torna um sistema invulnerável, e esta política não afirma
que torne.

## 10. Alterações nesta política

Mudanças materiais — nova categoria de dado, nova finalidade, novo operador —
serão anunciadas antes de entrarem em vigor. A data no topo indica a última
revisão.

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Lacunas conhecidas (para o backlog, não para o texto)

O que esta política teve de declarar como ausente, e que vira item:

| Lacuna | Onde aparece | Sugestão |
|---|---|---|
| Sem política de retenção | §7 | `LGPD-02` — decidir prazo e implementar expurgo, ou declarar formalmente que não haverá |
| Sem tela para corrigir nome e e-mail | §6.3 | `UI-11` — edição de perfil. Barato: a policy de `update` em `profiles` já existe |
| Sem bloqueio nem anonimização parcial | §6.5 | Provavelmente não vale implementar num protótipo; manter declarado |
| Exportação limitada a 2.000 linhas | §6.2 | Herdado do `DASH-13`. Paginação resolve, mas só importa quando houver histórico longo |
| Remoção parcial de conta possível | §6.4 | Já tratado no `UI-10`; o conserto de raiz está no cabeçalho da migração `006` |
| Sem página que sirva esta política | — | `LGPD-01` continua aberto: falta a rota e o link em *Configurações* |
| `profiles.idade` existe e não é usada | §2.4 | Coluna morta. Ou passa a ser coletada com finalidade declarada, ou é removida por migração — hoje ela é uma promessa de coleta que não acontece |

**Nota sobre a última linha, porque ela é de princípio:** minimização de dados
(art. 6º, III) fala em coletar o necessário para a finalidade. Uma coluna que
existe sem finalidade declarada não viola nada enquanto está vazia, mas é
exatamente o tipo de estrutura que um dia alguém preenche "porque já estava lá".
Removê-la é mais barato agora que justificá-la depois.
