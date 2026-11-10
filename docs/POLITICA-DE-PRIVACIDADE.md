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
**Atualização de 30/09:** conferido no Planalto, o §4º do art. 13 abre com *"Para
os efeitos deste artigo"* — a própria lei circunscreve aquela definição ao art.
13, o que torna a objeção acima textual, e não apenas contextual. A formulação
por contraste com o art. 12 foi estendida a `docs/LGPD-ELIMINACAO.md`,
`docs/DATA-CONTRACT.md` e ao cabeçalho da migração `006`, que ainda repetiam a
antiga. Nenhuma outra citação de artigo da LGPD no repositório está incorreta —
varredura completa registrada nas notas do `LGPD-ELIMINACAO.md`.

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

**Última atualização:** 10 de novembro de 2026

> **O que mudou nesta revisão** (seção 10 pede que mudança material seja
> anunciada):
>
> - **o aplicativo para Android** passou a ser descrito: ele registra a noite
>   inteira com a tela apagada e guarda arquivos no seu celular (seções 2.2 e 2.3);
> - **o sistema passou a estimar sono e vigília** a partir do movimento (seção 3,
>   item 6). Essa estimativa não é diagnóstico;
> - **a série de movimento passou a ser tratada como dado de saúde**, por
>   precaução, e a base legal mudou com isso (seções 2.5 e 4);
> - **o uso em pesquisa** passou a ser descrito: só com um termo próprio, assinado
>   à parte (seção 3).
>
> *Revisão anterior (5 de novembro de 2026):* passou a haver prazo de retenção
> (seção 7): uma conta sem uso há 12 meses é apagada por inteiro, automaticamente.
>
> *Revisão de 3 de novembro de 2026:* o serviço passou a ser destinado
> apenas a maiores de 18 anos (seção 2.1), com declaração no cadastro; e a idade
> ganhou uma segunda finalidade, apenas agregada (seção 3 e seção 5.3).

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
| **Declaração de ter 18 anos ou mais** | No cadastro, obrigatória, com a data em que foi feita | Serviço de autenticação |
| **Endereço de e-mail** | No cadastro | Serviço de autenticação |
| **Senha** | No cadastro | Serviço de autenticação, apenas como *hash* — nunca em texto legível |
| **Nome** | No cadastro, e corrigível em *Configurações → Conta* | Tabela de perfis |
| **Idade** | **Opcional**, em *Configurações → Conta*. Nunca pedida no cadastro | Tabela de perfis |
| **Nome do dispositivo** | Ao parear um aparelho, opcional | Tabela de dispositivos |

> ✏️ **Mudança de 2026-10-17, e ela é material** (seção 10): a **idade passou a
> ser coletada**. Até esta data o campo existia na estrutura do banco e estava
> vazio para todos os titulares — a versão anterior desta política dizia, na
> seção 2.4, que a idade **não** era coletada, e isso era verdade. Deixou de
> ser. A finalidade está declarada na seção 3, é a única, e o campo é opcional:
> deixá-lo em branco é um estado normal, e apagá-lo retira o dado (seção 6.5).
>
> **O serviço é destinado apenas a maiores de 18 anos.** O cadastro exige a
> declaração de que você tem 18 anos ou mais, e a idade informada em
> *Configurações → Conta* não pode ser inferior a 18. A idade é **autodeclarada e
> não é verificada** por documento: o sistema confia na declaração, e esta é uma
> limitação deste protótipo. Crianças e adolescentes não devem usar o serviço; o
> tratamento de dados deles exige salvaguardas próprias (art. 14 da Lei nº
> 13.709/2018), que este protótipo não oferece.
>
> *Até 3 de novembro de 2026, esta seção declarava que o sistema não tratava de
> forma diferente a idade de menor de 18 anos. A lacuna foi fechada restringindo
> o serviço a maiores de idade.*

### 2.2 Dados gerados pelo uso

O objeto do serviço é a **medição de movimento**. O aparelho mede o movimento
continuamente e o resume em **épocas** de 30 segundos. Cada época enviada registra:

- **Aceleração nos três eixos** e a **magnitude** do vetor de aceleração;
- Um **rótulo de estado** — "Repouso" ou "Movimento" — calculado pelo próprio
  aparelho a partir da magnitude;
- **Seis medidas de movimento da época:** a média, o desvio e o máximo da
  aceleração acima da gravidade, a média do movimento dinâmico, a taxa de
  cruzamentos por zero e a fração de amostras com movimento;
- A **direção da gravidade** na época, isto é, a inclinação do aparelho;
- A **taxa de amostragem** e o **número de amostras** que produziram a época;
- Uma **temperatura**: a do circuito integrado do sensor, no dispositivo do
  travesseiro; a da **bateria**, no celular;
- Leituras do **giroscópio**, quando o aparelho o tiver;
- Dois **instantes**: quando a medição foi feita e quando ela chegou ao servidor;
- A **duração da janela** resumida pela leitura e o **método** usado para
  resumi-la;
- O **identificador do aparelho** que enviou.

**No aplicativo para Android**, a noite é registrada por um serviço do próprio
aplicativo, que **continua medindo com a tela apagada**, do momento em que você
toca em *Iniciar a noite* até tocar em *Encerrar*. Enquanto ele mede, uma
**notificação fixa** fica visível: é o sinal de que o registro está ativo. Nada é
medido fora desse intervalo. As épocas ficam guardadas no celular e são enviadas
à sua conta quando você abre o aplicativo.

**Na versão para navegador**, o celular só mede enquanto a tela de coleta estiver
aberta, e **com a sua permissão explícita**, pedida pelo navegador. Negá-la
impede a coleta por esse caminho e não afeta o restante do aplicativo.

### 2.3 O que fica guardado no seu aparelho

**No navegador:**

- A **sua sessão de acesso**, mantida pela biblioteca de autenticação para que
  você não precise entrar novamente a cada recarregamento;
- A **sua preferência de tema** (claro ou escuro).

**No celular, pelo aplicativo para Android:**

- **O arquivo de cada noite**, com as épocas descritas na seção 2.2. O arquivo
  **continua no celular depois de enviado**; o aplicativo só marca até onde o
  envio foi confirmado;
- **As anotações da noite**, se você as preencher: onde o celular ficou, a hora
  em que deitou, em que acha que adormeceu e em que acordou, os despertares, uma
  observação livre e o motivo do fim do registro. **As anotações nunca saem do
  celular**: não são enviadas à sua conta nem a ninguém;
- **O estado do registro**: contadores técnicos da noite (épocas gravadas,
  retomadas, a taxa do sensor, a temperatura).

Esses arquivos ficam na área privada do aplicativo, que outros aplicativos não
leem, e **não entram no backup automático do Android** para a nuvem. Eles saem do
celular quando você **desinstala o aplicativo**.

**Não há cookies de rastreamento, de publicidade ou de análise de audiência**, e
o serviço não integra nenhuma ferramenta de medição de comportamento.

### 2.4 O que o sistema explicitamente NÃO coleta

- **Áudio, imagem ou vídeo.** O aparelho não tem microfone nem câmera.
- **Localização.** Nem do aparelho, nem do navegador.
- **Dados de contatos, agenda, aplicativos instalados ou navegação.**
- **Diagnóstico ou histórico clínico.** O aplicativo não pede, não guarda e não
  produz diagnóstico de condição alguma. Ele produz, sim, uma **estimativa de
  sono e vigília** a partir do movimento (seção 3, item 6) — e é por isso que a
  série de movimento passou a ser tratada como dado de saúde (seção 2.5).

> ✏️ **A última linha desta lista mudou em 2026-11-10.** Dizia que nada no
> aplicativo "pede, guarda ou infere condição de saúde" e que a série de
> movimento **não** era tratada como dado de saúde. A segunda parte deixou de
> valer quando o sistema passou a estimar sono e vigília (seção 3, item 6).
>
> ✏️ **Esta lista tinha uma quarta linha, e ela saiu em 2026-10-17.** Dizia:
> *"**Idade.** A estrutura do banco tem um campo para ela, herdado de uma versão
> anterior do projeto, mas nenhuma tela o preenche e nenhuma funcionalidade o
> utiliza. Ele está vazio para todos os titulares."* Era verdade quando foi
> escrita e deixou de ser: a idade passou a ser coletada, de forma opcional, com
> a finalidade da seção 3. Registrado aqui em vez de apagado em silêncio, para
> que quem tenha lido a versão anterior saiba exatamente o que mudou.

### 2.5 Sobre a natureza dos dados de movimento

Convém ser explícito, porque o assunto merece: **a série temporal de movimento
noturno é um dado sobre o seu corpo**, e uma série longa o bastante é, por si,
capaz de distinguir uma pessoa de outra. É por essa razão que este serviço **não
anonimiza** os dados como alternativa a apagá-los (seção 6.4).

**Este serviço trata essa série, e a estimativa de sono e vigília feita a partir
dela, como dado de saúde** — dado pessoal sensível, na definição da Lei nº
13.709/2018 (art. 5º, II). É uma escolha de precaução: uma estimativa de como uma
pessoa identificada dormiu está perto o bastante de um dado de saúde para que o
risco de classificá-la para baixo não valha a pena. Isso muda a base legal (seção
4), e não muda o que o serviço é: ele não diagnostica nada (aviso no topo).

## 3. Para que os dados são usados

Exclusivamente para:

1. **Apresentar a você as suas próprias medições**, no painel do aplicativo;
2. **Permitir que você exporte** as suas medições;
3. **Manter sua conta funcionando** — autenticar, associar cada leitura ao seu
   dono, distinguir os seus aparelhos.
4. **Dizer se a sua idade está na faixa das pesquisas que embasam o trabalho.**
   É a primeira das duas finalidades da idade, e convém ser explícito sobre o
   que ela não é:

   - **O que acontece:** o aplicativo compara a idade que você informou com as
     faixas de idade das pesquisas citadas pelo trabalho e mostra **uma frase**
     dizendo se os números apresentados foram medidos em pessoas da sua faixa,
     ou se aplicá-los a você é extrapolar. Nenhuma das pesquisas citadas cobre a
     faixa a partir de 60 anos, por exemplo, e você tem o direito de saber isso
     ao olhar o painel.
   - **O que NÃO acontece:** a idade **não entra em cálculo nenhum**. Não
     pondera nenhuma métrica, não altera nenhum limiar, não separa a sua série
     em grupos, não alimenta modelo algum e não produz comparação com "o
     esperado para a sua idade". Se isso mudar, é **finalidade nova**, e esta
     política será atualizada antes (seção 10).
   - **Sem idade informada, a frase simplesmente não aparece**, e nada mais no
     aplicativo muda.
5. **Conhecer, de forma apenas agregada, o perfil etário de quem usa o
   sistema** — a segunda finalidade da idade, desde 3 de novembro de 2026. O
   responsável pelo projeto conta **quantas contas há em cada faixa de idade**
   (18 a 24, 25 a 34, 35 a 44, 45 a 54, 55 a 64, 65 ou mais, e "não informada").
   Faixas com menos de cinco pessoas **não são exibidas**, para que ninguém seja
   identificável pela contagem. Nenhuma idade é consultada pessoa a pessoa, e a
   contagem não é cruzada com medições nem com nenhum outro dado. Se você não
   informar a idade, entra apenas na contagem de "não informada".
6. **Estimar, época a época, se você estava dormindo ou acordado.** Desde 10 de
   novembro de 2026. Convém ser explícito também aqui:

   - **O que acontece:** quando a sua sessão pede, o servidor aplica um modelo
     às medidas de movimento (seção 2.2) de uma janela de até 24 horas e devolve,
     para cada época, a estimativa "sono" ou "vigília" e a probabilidade dela.
   - **Como o modelo foi feito:** treinado e avaliado em **bases públicas de
     terceiros**, com sensores no pulso e na cabeça — **não** com dados de
     usuários deste serviço, e **não** com o sensor no travesseiro.
   - **O que NÃO acontece:** a estimativa **não é gravada**: é calculada a cada
     pedido e devolvida só a você. Não é diagnóstico, não alimenta nenhum outro
     cálculo e não é compartilhada. Ela erra, e erra de modo conhecido: quem está
     acordado e parado tende a ser classificado como dormindo.
   - **Onde aparece:** hoje, em nenhuma tela; está disponível para a sua sessão
     pela interface do serviço. Quando uma tela passar a mostrá-la, ela trará o
     mesmo aviso que a resposta do servidor já traz.

**Não há nenhum outro uso.** Os dados não são usados para publicidade, não são
vendidos, não são cedidos, não alimentam perfilamento comercial e não são
combinados com dados de outras fontes.

> **Sobre o uso dos dados em pesquisa.** Os resultados de aprendizado de máquina
> deste trabalho foram obtidos sobre **bases públicas de terceiros**, com dados
> de outros indivíduos, obtidas sob acordo de uso — **não** sobre dados de
> usuários deste serviço.
>
> **Os dados de um usuário só entram no trabalho acadêmico se ele assinar um
> termo de participação próprio**, separado desta política e do cadastro. O termo
> diz quais dados são usados, como e por quanto tempo, e pode ser revogado a
> qualquer momento. **Quem não assinar o termo usa o serviço normalmente, e os
> seus dados não entram no trabalho.** Usar o aplicativo não equivale a
> participar da pesquisa.

## 4. Com que base legal

O tratamento se apoia no **seu consentimento**. Como a série de movimento é
tratada como dado de saúde (seção 2.5), a base é a do **art. 11, I** da Lei nº
13.709/2018, que exige consentimento **específico e destacado**, para finalidades
específicas. Os dados que não são de saúde (e-mail, nome, idade, nome do
dispositivo) seguem no art. 7º, I.

⚠️ **O que existe hoje, e o que falta.** O consentimento é manifestado ao criar
a conta, ao autorizar o sensor no navegador e, no aplicativo para Android, a cada
vez que você toca em *Iniciar a noite*. **Ainda não há uma tela própria e
destacada** para o consentimento sobre a série de movimento e a estimativa de
sono — é o que o art. 11, I pede, e ela está em desenvolvimento. Até ela existir,
esta lacuna fica declarada aqui.

Você pode revogar o consentimento a qualquer momento apagando sua conta (seção
6.4). O uso em pesquisa tem consentimento próprio, pelo termo de participação
(seção 3).

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
do que a manutenção do serviço exigir. **A idade é consultada apenas de forma
agregada**, pela contagem por faixa descrita na seção 3, item 5 — nunca por
pessoa.

A única exceção é a de quem **assinar o termo de participação** (seção 3): as
medições dessas pessoas são analisadas noite a noite pelo responsável pelo
projeto, nos termos do próprio termo. O que vai para o texto do trabalho não
identifica ninguém.

## 6. Seus direitos, e como exercê-los **hoje**

Esta é a seção que esta política existe para ser honesta. A lei assegura os
direitos abaixo. O que segue diz, para cada um, **se há mecanismo implementado**.

### 6.1 Confirmação de que há tratamento, e acesso aos dados (art. 18, I e II)

✅ **Implementado, com uma limitação declarada.** Entre na sua conta: o painel
exibe as suas medições.

⚠️ **As seis medidas de movimento e a direção da gravidade** (seção 2.2) **não
aparecem no painel e não saem na exportação** (6.2). Elas estão disponíveis para
a sua sessão pela interface do serviço, assim como a estimativa de sono (seção 3,
item 6); uma solicitação pelo canal da seção 8 também é atendida. As anotações
da noite ficam só no seu celular, e você as vê no próprio aplicativo.

> ✏️ *Até 10 de novembro de 2026, esta seção dizia que não havia "nenhuma
> categoria de dado seu que o aplicativo colete e não mostre". Deixou de ser
> verdade quando as medidas de movimento por época passaram a ser enviadas.*

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

✅ **Implementado**, exceto para as medições — e a exceção é deliberada.

- **Nome do dispositivo:** pode ser alterado em *Configurações → Meus
  dispositivos*.
- **Seu nome e sua idade:** em *Configurações → Conta → Editar dados*. Valem
  assim que você salva. A idade pode ser **apagada** deixando o campo em branco
  (ver 6.5).
- **Seu e-mail:** na mesma tela, com uma diferença que a tela avisa **antes** de
  você salvar: o e-mail é a sua credencial de acesso, então a troca **não é
  imediata** — enviamos um link de confirmação e o seu acesso continua pelo
  endereço antigo até você confirmar. Dependendo da configuração do serviço de
  autenticação, pode ser pedida confirmação também no endereço atual.
- **Medições já registradas:** **não são alteráveis, por decisão de projeto** — e
  isso é deliberado, não uma lacuna. O banco não concede permissão de atualização
  sobre as leituras. Apagar é visível: a linha sai. Editar seria invisível, e
  destruiria o valor probatório do conjunto. Se uma medição estiver errada, o
  caminho é apagá-la, não reescrevê-la.

> ✏️ **Correção de procedência, 2026-10-17 — e é a segunda deste tipo nesta
> política em um dia.** O texto desta seção dizia, até hoje, *"Seu nome e seu
> e-mail: **não há tela para alterá-los**. O aplicativo os exibe, e só. Para
> corrigi-los, é necessário solicitar pelo canal da seção 8."* A tela foi
> entregue na manhã de 2026-10-17 (item `UI-11`) e **esta política não foi
> atualizada junto**: por algumas horas ela mandou o titular escrever para um
> canal de contato a fim de exercer um direito que estava a dois cliques.
>
> O defeito é o mesmo da seção 6.4 — registro que não acompanha o código — com o
> sinal **invertido**: lá a política afirmava um mecanismo que não existia; aqui
> ela negava um que existia. O primeiro cria expectativa que o sistema não
> sustenta; o segundo faz o titular desistir de um direito que ele tinha. Está
> registrado como ocorrência 5 do §6 de `docs/LICOES-APRENDIDAS.md`.

### 6.4 Eliminação (art. 18, VI) e revogação do consentimento (art. 18, IX)

✅ **Implementado.** Em *Configurações → Excluir conta*. A operação exige que você
digite uma frase de confirmação, e é **irreversível**. Ela apaga:

- todas as suas leituras;
- todos os seus dispositivos;
- o seu perfil.

> ✏️ **Correção de procedência, 2026-10-17.** O "✅ Implementado" acima está
> escrito desde 29/09 e, **na versão versionada do aplicativo, a tela não
> existia**: o componente `ExcluirConta` estava commitado e testado, e as três
> linhas que o montam na tela de Configurações ficaram numa árvore de trabalho
> não commitada por dezoito dias. Uma política de privacidade que indica ao
> titular *onde* exercer um direito é a última afirmação do repositório que pode
> estar à frente do código. Montado e versionado hoje (commit do `UI-10`); o
> mecanismo que deveria ter pegado a ausência está no `UI-17` do backlog.
>
> ✏️ **Atualização de 2026-10-19: esse mecanismo existe.** Há agora uma
> verificação automática que **reprova** se a tela de exclusão de conta sair da
> tela de Configurações — não só se o arquivo dela desaparecer do projeto, que
> era o alcance da verificação anterior. Em termos práticos para quem lê esta
> política: a afirmação de que existe um lugar para exercer o art. 18, VI
> passou a ser conferida a cada execução da suíte de testes, e não apenas na
> leitura de quem escreveu o parágrafo.

⚠️ **Pode haver remoção parcial, e o aplicativo diz quando há.** O cadastro de
acesso — a linha que guarda o **seu e-mail** — pertence ao serviço de
autenticação, e a permissão para removê-la pode não estar disponível na
configuração do projeto. Quando não estiver, os dados acima são apagados, **o seu
e-mail permanece**, e a tela informa isso explicitamente, em vez de anunciar
sucesso. Nesse caso, a remoção do cadastro depende de solicitação pelo canal da
seção 8.

⚠️ **O que fica no seu celular não sai com a conta.** A exclusão da conta apaga
o que está no servidor. **Os arquivos das noites e as anotações guardados no
celular** (seção 2.3) continuam lá até você **desinstalar o aplicativo**.

> **Por que eliminação e não anonimização.** Uma série temporal de acelerometria
> noturna com carimbo de tempo não é razoavelmente anonimizável: a própria série
> funciona como identificador quando cruzada com outra fonte. Como a lei retira
> de seu alcance apenas o dado efetivamente **anonimizado** (art. 12), desvincular
> a leitura do seu dono não cumpriria o direito de eliminação — apenas produziria
> um registro órfão que continuaria sendo dado pessoal. Por isso as linhas são
> removidas de fato.

### 6.5 Anonimização ou bloqueio de dados desnecessários ou excessivos (art. 18, IV)

⚠️ **Parcialmente implementado, e a parte implementada é nova.**

- **Idade:** ✅ pode ser **retirada** a qualquer momento, apagando o campo em
  *Configurações → Conta → Editar dados*. O campo volta a ficar vazio no banco,
  e a frase da seção 3 deixa de aparecer. É eliminação daquele dado, não
  bloqueio dele.
- **Bloqueio temporário do tratamento, e anonimização de um subconjunto das
  leituras:** ❌ sem mecanismo. O que existe é a eliminação total (6.4) e a
  eliminação de leituras individuais pela API. Uma solicitação por esses será
  atendida manualmente, pelo canal da seção 8.
- **Por que as leituras não são anonimizadas como alternativa a apagá-las:** ver
  a seção 2.5 — uma série longa de movimento noturno é, por si, capaz de
  distinguir uma pessoa de outra, então chamar de anonimizado o que não é seria
  pior que não oferecer.

### 6.6 Informação sobre compartilhamento (art. 18, VII)

✅ **Atendido por esta política.** A seção 5 lista integralmente com quem os dados
são compartilhados. Não há outros.

### 6.7 Informação sobre a possibilidade de não consentir (art. 18, VIII)

✅ **Atendido por esta política.** Você pode não criar conta, e nesse caso nenhum
dado seu é tratado. Pode criar conta e não autorizar o sensor de movimento do
celular: o aplicativo funciona, e apenas a coleta por esse caminho fica
indisponível. No aplicativo para Android, pode negar a notificação e a isenção
da economia de bateria: o registro funciona, mas o Android pode interrompê-lo no
meio da noite. Pode, a qualquer momento, apagar tudo (6.4).

### 6.8 Prazo de resposta

Os direitos com mecanismo implementado (6.1, 6.2, 6.4) são exercidos por você
mesmo, na hora, sem intermediação humana. Para os que dependem de solicitação
(6.3 parcialmente, 6.5), **não há prazo de atendimento comprometido**, porque não
há estrutura de atendimento: este é um protótipo acadêmico mantido por uma
pessoa. Dizê-lo é mais útil que anunciar um prazo que não seria cumprido.

## 7. Por quanto tempo os dados são guardados

**Enquanto você usar o serviço, e até 12 meses depois do último uso.**

- **Enquanto a conta é usada, os dados ficam.** A finalidade deles é o seu
  próprio histórico (seção 3), e um histórico só serve se estiver lá quando
  você o procurar. Você pode apagá-los a qualquer momento, por inteiro, pela
  exclusão da conta (seção 6.4).
- **Uma conta sem uso há 12 meses é apagada por inteiro, automaticamente.** Sem
  uso quer dizer: nenhum login, nenhum uso do aplicativo com a sessão já aberta
  (ele mantém você conectado, e cada uso renova a sessão), nenhuma leitura
  recebida de um dispositivo seu e nenhuma conta criada nos últimos 12 meses —
  basta um desses para a conta continuar. A eliminação é a mesma da seção 6.4: leituras, dispositivos, perfil
  e o cadastro de acesso. A verificação roda uma vez por dia.
- **Não há aviso antes dessa eliminação.** O serviço ainda não envia e-mails
  próprios; quando passar a enviar, o aviso prévio será acrescentado aqui.

O prazo de 12 meses segue o princípio da necessidade (LGPD, art. 6º, III): uma
conta que ninguém usa há um ano não serve mais à finalidade para a qual os dados
foram coletados, e o tratamento termina (art. 15, I).

**Cópias de segurança.** O banco de dados roda no plano gratuito do provedor
(seção 5.2), que não faz cópias de segurança automáticas. O dado apagado — por
você ou pelo prazo acima — sai do banco no momento da eliminação, sem cópia
que o guarde depois.

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
  aplicação, e é verificado por **196 testes** automatizados contra um banco
  real — incluindo os casos adversariais, em que se tenta ler, alterar e apagar
  dado alheio, e em que se tenta gravar perfil na conta de outra pessoa.
  *(Eram 105 em 29/09, 146 em 17/10 e 196 em 10/11.)*
- **A credencial de ingestão** não tem privilégio sobre tabela nenhuma.
- **Toda leitura enviada é validada** — faixa física, coerência interna, recusa
  de instante futuro e de sensor que responde mas não mede. As faixas e a recusa
  do futuro valem também **dentro do próprio banco de dados**, desde 10 de
  novembro de 2026: uma leitura fora delas é recusada mesmo que chegue sem passar
  pelo servidor da aplicação.

Nenhuma dessas medidas torna um sistema invulnerável, e esta política não afirma
que torne.

## 10. Alterações nesta política

Mudanças materiais — nova categoria de dado, nova finalidade, novo operador —
serão anunciadas antes de entrarem em vigor. A data no topo indica a última
revisão.

- **10 de novembro de 2026:** o aplicativo para Android (seções 2.2, 2.3, 6.4 e
  6.7); a estimativa de sono e vigília (seção 3, item 6); a série de movimento
  tratada como dado de saúde e a base legal do art. 11, I (seções 2.4, 2.5 e 4);
  o uso em pesquisa só por termo próprio (seções 3 e 5.3); correções nas seções
  6.1 e 9.
- **5 de novembro de 2026:** prazo de retenção — eliminação automática da conta
  sem uso há 12 meses (seção 7).
- **3 de novembro de 2026:** serviço restrito a maiores de 18 anos, com
  declaração no cadastro (seção 2.1); segunda finalidade da idade, apenas
  agregada (seção 3, item 5, e seção 5.3).
- **17 de outubro de 2026:** a idade passou a ser coletada, de forma opcional
  (seções 2.1, 3, 6.3 e 6.5).

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Lacunas conhecidas (para o backlog, não para o texto)

O que esta política teve de declarar como ausente, e que vira item:

| Lacuna | Onde aparece | Sugestão |
|---|---|---|
| ~~Sem política de retenção~~ | §7 | ✅ **Fechada em 05/11 pelo `LGPD-02`:** enquanto a conta é usada, os dados ficam; conta sem login, leitura nem criação há 12 meses é eliminada por inteiro (migração `013`, agendamento diário pelo `pg_cron`). ⚠️ **Ordem do release:** a seção 7 só pode ir ao ar depois de a `013` estar aplicada e agendada na produção — o contrário do `LGPD-06`, porque aqui a política descreve um mecanismo, e não pode chegar antes dele. Fica sem aviso prévio por e-mail, que depende do SMTP (`AUTH-06`) |
| ~~Sem tela para corrigir nome e e-mail~~ | §6.3 | ✅ **Fechada em 17/10** pelo `UI-11` (nome e e-mail) e pelo `PERFIL-01` (idade, e o nome passando a gravar em `profiles`). A sugestão original — *"barato: a policy de `update` em `profiles` já existe"* — estava certa na conclusão e errada no motivo: nenhum código de produção tocava `profiles`. Ver §5 ocorrência 4 das lições |
| **A política não acompanhou o `UI-11` no mesmo dia** | §6.3 | ⚠️ Não é lacuna de produto, é de processo: a tela saiu na manhã de 17/10 e esta política continuou dizendo que ela não existia. Ocorrência 5 do §6 das lições. O mecanismo que faltaria para pegar isso **não existe** — nada liga uma afirmação desta política a um teste |
| Idade declarada de menor de 18 não tem tratamento próprio | §2.1 | `LGPD-05` — decidir entre exigir consentimento de responsável, restringir o cadastro a maiores de 18, ou manter a lacuna declarada. **É decisão de produto, não de implementação** |
| **Sem consentimento específico e destacado para a série de movimento** | §4 | ✏️ *10/11:* a série passou a ser tratada como dado de saúde (art. 11, I), que pede essa tela. Item `LGPD-12`. Até lá, a lacuna fica declarada no texto |
| **As medidas de movimento por época não aparecem no painel nem saem no CSV** | §6.1 | ✏️ *10/11:* disponíveis só por `GET /api/features`. Acrescentar ao CSV fecha a lacuna |
| **A exclusão da conta não apaga os arquivos do celular** | §6.4 | ✏️ *10/11:* declarado. Apagar as noites locais junto com a conta é uma mudança no app |
| ~~A validação do servidor é contornável na própria conta~~ | §9 | ✅ *10/11:* fechada pelo `SEC-18` (migração 016), aplicada na produção no mesmo dia (`SEC-21`). A coerência de `total` e o "sensor mudo" continuam só no servidor |
| Sem bloqueio nem anonimização parcial | §6.5 | Provavelmente não vale implementar num protótipo; manter declarado |
| Exportação limitada a 2.000 linhas | §6.2 | Herdado do `DASH-13`. Paginação resolve, mas só importa quando houver histórico longo |
| Remoção parcial de conta possível | §6.4 | Já tratado no `UI-10`; o conserto de raiz está no cabeçalho da migração `006` |
| Sem página que sirva esta política | — | `LGPD-01` continua aberto: falta a rota e o link em *Configurações* |
| ~~`profiles.idade` existe e não é usada~~ | §2.4 | ✅ **Fechada em 17/10 pelo `PERFIL-01`/`LGPD-04`**, pelo primeiro dos dois caminhos: a coluna **passou a ser coletada com finalidade declarada** (§3), opcional e retirável (§6.5) |

**Nota sobre a linha da idade, porque ela é de princípio — e o que mudou nela.**
Minimização de dados (art. 6º, III) fala em coletar o necessário **para a
finalidade**. A versão anterior desta nota dizia que remover a coluna era mais
barato que justificá-la depois, e isso continua certo como regra geral. A decisão
foi a outra, e o que a sustenta é que a finalidade **não é cadastral**: "estar no
perfil" não é finalidade nenhuma, e uma idade coletada para existir no cadastro
não sobreviveria a este artigo. O que sustenta a coleta é o uso da §3 — dizer ao
titular se os números que ele está vendo foram medidos em pessoas da faixa de
idade dele.

**E o teste que essa decisão tem de passar o tempo todo é este:** a finalidade
declarada é verdadeira porque existe código que a cumpre
(`frontend/src/lib/aplicabilidade.ts`), não porque está escrita aqui. Uma
finalidade que só existe em política de privacidade é indistinguível de uma
coluna morta com justificativa — e é a forma mais barata de cometer o §6 das
lições (*"confirmação emitida antes da verificação"*), porque um parágrafo deste
arquivo não tem como ficar vermelho.
