# Catálogo detalhado de telas e design — DormioSmart

**Data:** 10/11/2026 · **Base:** `0a86de1`, conteúdo incluído na release #121. Complementa `ANALISE-FRONTEND-UX-UI.md` com especificações de cada tela. Os desenhos abaixo são **esquemas de estrutura**, não capturas nem reprodução em escala.

**Como ler:** as descrições são derivadas do código. As capturas web foram produzidas localmente em 10/11/2026; as áreas protegidas usam modo de demonstração sem sessão real. A captura nativa foi feita no Moto E7 com autorização do usuário. Não houve teste com usuários de todas as telas. A captura do Moto E7 reproduz data e métricas reais de uma gravação, sem nome ou e-mail visível; as demais capturas utilizam páginas públicas ou demonstração sem conta real. “Avaliar” identifica uma hipótese, não um defeito medido.

**Sobre as imagens:** desktop em 1440 × 900 CSS px (algumas páginas em captura integral); celular web simulado em 390 × 844 CSS px (área visível); Android em resolução do próprio aparelho. A faixa vermelha identifica demonstração com dados simulados. A tela de configurações mostra erro de servidor do ambiente local, não evidência de erro em produção. A captura Android contém dados reais de uma gravação e foi autorizada apenas para este documento local: não publicá-la sem nova avaliação.

> **Retrato de 10/11, versionado em 12/11 (diário 12/11 (x)).** O Codex escreveu estas análises sobre o código de `0a86de1`, e o Claude as revisou antes de entrar no repositório. Em 12/11, o frontend do protótipo (PRs #134–#139, release #142) mudou a navegação e acrescentou `/historico` e `/dispositivos`, e redesenhou o painel, a coleta e as configurações. **O que aqui fala de navegação, painel, coleta e configurações descreve a versão anterior.** As capturas de tela ficaram locais, fora do repositório: as de demonstração por peso e por serem de uma versão antiga, e a do Moto E7, a da recuperação de senha e a do formulário real por mostrarem dados ou telas de uma pessoa.
>
> **Os achados, conferidos contra a `develop` de 12/11:**
>
> | Achado | Situação em 12/11 |
> |---|---|
> | Diálogo de consentimento sem gestão de foco | Continua (`TelaDeConsentimento.tsx` só declara `aria-modal`): **`UI-28`** |
> | Seletor de tema sem setas no `radiogroup` | Continua: **`UI-28`** |
> | Exportação e histórico limitados ao teto do painel | Continua, e confirmado em produção: **`DATA-15`** |
> | Painel diz "na ordem em que chegou", mas ordena pela medição | Continua (`Dashboard.tsx`): **`UI-29`** |
> | Falha ao listar as noites vira "nenhuma noite" | Continua (`ListaDeNoites.tsx`, `catch` com lista vazia): **`APP-15`** |
> | Coleta curta: a primeira leitura só sai depois de uma janela | Registrado: **`UI-27`** |
> | Comentário de `Layout.tsx` dizendo que as rotas não são protegidas | Corrigido: o comentário atual aponta a proteção de rota |

## Matriz de evidências visuais

| Tela ou estado | Evidência disponível | Ainda falta |
|---|---|---|
| Landing, login e cadastro | Desktop e janela móvel simulada; recuperação com e-mail ausente | Outros estados de validação e erro |
| Recuperação de senha | Link inválido; ilustração editada da solicitação; formulário real aberto após o link | Confirmação após alterar senha |
| Política | Região inicial em desktop e janela móvel | Parte inferior e verificação de tabelas |
| Painel | Dados simulados, desktop e móvel; tema escuro; componentes de vazio, erro e carregamento isolados | Fluxos de dados reais autorizados |
| Coletar e consentimento | Antes do início e diálogo marcado/desmarcado em demonstração | Capturas de envio, confirmação de leitura salva e recuperação de falha |
| Noite Android | Tela inicial no Moto E7 com métricas reais, autorizada para uso local | Durante registro, interrupção, encerramento, envio e anotações |
| Configurações | Tema claro/escuro, edição e confirmação de exclusão em demonstração | Conta e dispositivos reais autorizados; erros e sucessos de operações |

A ausência de captura não significa ausência da funcionalidade. Em demonstração o backend local estava desligado: erros exibidos nesse ambiente não representam automaticamente a produção. A captura Android contém dados reais e não deve ser compartilhada ou versionada sem revisão e autorização específica para publicação.

## 1. Princípios de composição compartilhados

### Web autenticada, desktop

```text
┌─────────────────┬────────────────────────────────────────────┐
│ MARCA           │ Conteúdo da rota                            │
├─────────────────┤ Título + descrição / ação                   │
│ Início          │                                            │
│ Coletar         │ Cartões, estados e controles                │
│ Configurações   │                                            │
│                 │                                            │
├─────────────────┤                                            │
│ Perfil / e-mail │                                            │
│ Sair            │                                            │
└─────────────────┴────────────────────────────────────────────┘
```

A lateral possui largura `w-56`, fundo de cartão, borda, marca, destinos e resumo da conta. O destino ativo recebe fundo e texto na cor primária. A área central usa fundo geral, `p-4` em telas pequenas e `md:p-8` em telas maiores. A lateral é fixa ao topo por `sticky` e ocupa a altura da tela.

### Celular e app nativo

```text
┌──────────────────────────────┐
│ Título e contexto            │
│                              │
│ Cartão e ação principal      │
│                              │
│ Conteúdo rolável             │
│                              │
├──────────────────────────────┤
│ [Noite*] [Início] [Coletar]  │
│       [Configurações]        │
└──────────────────────────────┘
* Noite está na navegação nativa; a distribuição ilustrada não é em escala.
```

A barra de destinos fica fixa na borda inferior, com ícone e nome e uso da área segura. O conteúdo reserva espaço inferior. No app Android, a opção **Noite** é acrescentada à mesma fonte de navegação. Em desktop há **Sair** também no rodapé da barra lateral; no celular está em Configurações.

### Camada visual

- Cores semânticas em `frontend/src/styles/theme.css`: fundo, cartão, texto principal/secundário, primário, erro, borda e gráficos; os mesmos nomes são resolvidos para claro ou escuro.
- A identidade usa azul `#35a2ef`. No tema claro, o azul de ação é `#0b6db5`; no escuro, `#4fb3f5`. Fundo claro `#f4f7fb`; escuro `#070d18`.
- A fonte principal declarada é Outfit; há reservas do sistema e importação de fontes externas. Hierarquia frequente: rótulo pequeno, título, subtítulo, seção em cartão, detalhe secundário.
- Formas arredondadas, bordas discretas, ícones Lucide e espaçamento entre blocos são recorrentes. O estilo “blueprint” da landing usa molduras, cotas e traçado de sinal.
- Existem respostas de carregamento, erro e estados vazios, mas não necessariamente uniformes em todos os componentes. Há implementação específica para preferência por redução de movimento; cobertura integral deve ser testada.

## 2. Landing — `/`

*[Captura local, não versionada: Landing em desktop — `01-landing-desktop.png`]*

*Desktop; captura integral com preferência por movimento reduzido para mostrar os blocos abaixo da dobra.*

*[Captura local, não versionada: Landing em celular — `11-landing-mobile.png`]*

*Janela móvel simulada; região inicial visível.*

**Finalidade:** apresentar o projeto a quem chega pelo link e conduzir pessoas autenticadas ao painel ou visitantes ao acesso. No Android nativo, a rota `/` redireciona para `/noite`.

**Composição, de cima para baixo:**

```text
[MARCA]                                      [Entrar / Ir ao painel]

TCC · ENGENHARIA DA COMPUTAÇÃO · 2026
Monitoramento de movimento
DURANTE O REPOUSO                    [traçado ilustrativo]
Explicação curta e ação de acesso

[O que registra]                    [O que não registra]
Como funciona: sensor → envio → visualização
Onde está hoje: fase 1 / fase 2
Links do projeto e política
```

**Design:** cabeçalho com marca e ação alinhadas; conteúdo central com largura máxima; título grande, palavra-chave em azul, texto de apoio e traçado animado. Seções usam linhas, molduras e detalhes que remetem a desenho técnico. Há animação de entrada dos blocos e efeito discreto nos botões, com regra para reduzir movimento. Em dispositivos menores, tamanhos e arranjo usam classes responsivas; a posição final exata deve ser conferida em renderização.

**Conteúdo e ações:** informa que o produto registra movimento, horário e intensidade, e distingue isso de estadiamento, diagnóstico e outras medidas. Explica sensor no travesseiro, envio por Wi-Fi e painel, além do estado das duas fases. O botão do cabeçalho depende da sessão; links externos e política completam o percurso.

**Estados:** visitante, pessoa com sessão e experiência nativa com redirecionamento. Conteúdo e evidência de estágio do projeto devem ser mantidos atuais; a landing descreve a arquitetura planejada e não comprova operação do protótipo físico.

**Avaliação:** a separação “registra / não registra” fortalece a compreensão do limite do produto. Validar se uma pessoa identifica rapidamente o que pode usar hoje e se percebe que o protótipo físico ainda exige testes. Arquivo: `frontend/src/pages/Landing.tsx`.

## 3. Entrar — `/login`

*[Captura local, não versionada: Tela de login em desktop — `02-login.png`]*

*[Captura local, não versionada: Tela de login em celular — `12-login-mobile.png`]*

*[Captura local, não versionada: Validação de e-mail ausente para recuperação — `29-login-validacao-email.png`]*

*Mensagem local ao solicitar recuperação sem preencher e-mail; nenhum e-mail foi enviado.*

**Finalidade:** autenticar ou iniciar a recuperação de senha.

```text
            [MARCA]
     Seu guia para um sono de qualidade
       ┌───────────────────────┐
       │ Bem-vindo de volta    │
       │ E-mail     [_______]  │
       │ Senha      [_____◉]   │
       │    Esqueci minha senha│
       │ [       Entrar       ]│
       │ Não tem conta? Cadastre-se
       └───────────────────────┘
```

**Design:** tela centralizada em altura e largura, com marca acima de cartão estreito (`max-w-sm`), cantos arredondados, borda e halos suaves ao fundo. Campos empilhados têm rótulos; o ícone dentro do campo alterna visibilidade da senha. A ação principal ocupa a largura disponível. Em celular, o cartão mantém margens e ocupa o espaço disponível.

**Ações:** preencher e-mail e senha, mostrar/ocultar senha, entrar, solicitar recuperação informando o e-mail e acessar cadastro. Quando a pessoa veio de uma rota protegida, o retorno usa destino interno validado.

**Estados:** erro com `role=alert`; envio com botão desabilitado e “Entrando...”; aviso de recuperação; mensagem para e-mail ausente. Recuperação depende da configuração de e-mail do serviço; `AUTH-06` aponta restrição para destinatários externos.

**Avaliação:** a apresentação concentra a tarefa e rotula controles; verificar anúncio do envio e da resposta de recuperação, e avaliar a frase “sono de qualidade” diante do escopo limitado de monitoramento, sem concluir que promete um resultado clínico. Arquivos: `pages/Login.tsx`, `components/AuthLayout.tsx`, `lib/autenticacao.ts`.

## 4. Cadastro — `/cadastro`

*[Captura local, não versionada: Cadastro em desktop — `03-cadastro.png`]*

*[Captura local, não versionada: Cadastro em celular — `13-cadastro-mobile.png`]*

**Finalidade:** criar conta e apresentar a política antes do tratamento de dados.

**Composição:** usa a mesma casca de autenticação: marca, subtítulo, cartão central, título “Criar conta” e formulário vertical. Os campos são nome completo, e-mail e senha; o controle de senha oferece visibilidade. Abaixo ficam declaração de maioridade, referência à política, ação principal e link para login.

**Ações e estados:** informar dados, declarar maioridade, ler política, enviar ou ir ao login. Há validação e erro; durante envio a ação muda de estado; o código também contempla tela de confirmação de e-mail e alternativas associadas.

**Avaliação:** mostrar requisitos de senha antes da tentativa ajuda a antecipar erro. Convém testar se a distinção entre cadastro/maioridade e consentimento destacado para dados de saúde é compreensível: a última etapa aparece mais tarde antes da coleta. Verificar retorno da política, uso com teclado e mensagens em telas pequenas. Arquivo: `pages/Register.tsx`.

## 5. Recuperação e nova senha — `/login` e `/nova-senha`

*[Captura local, não versionada: Nova senha com link inválido — `04-nova-senha.png`]*

*Estado de link inválido, sem sessão de recuperação.*

*[Captura local, não versionada: Formulário real de nova senha após abrir o link — `31-nova-senha-formulario-real.png`]*

*Captura enviada pelo autor em 11/11/2026 após abrir o link de recuperação: campo vazio, sem URL ou senha visível. Confirma a abertura do formulário; não comprova troca de senha.*

*[Captura local, não versionada: Ilustração editada da mensagem de solicitação de recuperação — `30-recuperacao-ilustracao-editada.png`]*

*Imagem fornecida pelo autor após solicitar a recuperação e editada por IA para ocultar e-mail e senha. A edição recriou elementos visuais; é uma ilustração do estado relatado, não uma captura fiel para verificação de detalhes. A mensagem exibida não confirma que o e-mail foi entregue.*

**Recuperação:** o link “Esqueci minha senha” pertence ao formulário de login e usa o e-mail informado ali; não há uma rota separada de solicitação. A resposta de sucesso é condicional (“Se houver uma conta...”); o código reconhece limites dessa uniformização.

**Nova senha:** usa cartão de autenticação, título, instrução de tamanho mínimo, campo e botão de visibilidade, erro e ação de salvar. O estado de sucesso apresenta ícone de confirmação, “Senha alterada” e caminho para início. O estado de link inválido informa a expiração/uso único e oferece retorno ao login.

**Avaliação:** verificar o percurso real via e-mail e os diferentes estados do link; uma tela correta não garante entrega para contas fora do time. Arquivo: `pages/NovaSenha.tsx`.

## 6. Política de privacidade — `/privacidade`

*[Captura local, não versionada: Início da política de privacidade — `05-privacidade.png`]*

*Início da página; conteúdo abaixo da dobra não aparece na imagem.*

*[Captura local, não versionada: Política em janela móvel — `27-politica-mobile.png`]*

*Região inicial em janela móvel simulada.*

**Finalidade:** disponibilizar o documento antes e depois do cadastro.

**Design:** página pública com conteúdo centralizado até `max-w-3xl`; no topo, link de retorno à marca e caixa com ícone de escudo e aviso de versão preliminar. O corpo é um artigo textual com títulos, parágrafos, listas, citações, links e tabelas, renderizado a partir do documento Markdown. A página é carregada sob demanda com uma mensagem de espera.

**Ações e estados:** abrir pela landing, cadastro, configurações ou consentimento; seguir links do texto; voltar pelo link superior. Os dados configuráveis são preenchidos no build. Como o link de retorno superior aponta para `/`, a experiência de ida e volta ao consentimento merece verificação específica.

**Avaliação:** testar legibilidade de tabelas e rolagem em telas estreitas, ampliação e navegação por títulos. Não inferir que os usuários leem ou compreendem a política só porque ela está acessível. Arquivo: `pages/Privacidade.tsx`.

## 7. Painel — `/dashboard`

*[Captura local, não versionada: Painel desktop com dados simulados — `06-dashboard-demo.png`]*

*Modo de demonstração: números e horários são simulados.*

*[Captura local, não versionada: Painel no tema escuro — `22-dashboard-escuro-demo.png`]*

*Tema escuro, demonstração sem conta real.*

*[Captura local, não versionada: Painel móvel com dados simulados — `14-dashboard-mobile-demo.png`]*

*Região visível no tamanho móvel simulado.*

*[Captura local, não versionada: Painel sem leituras em montagem simulada — `24-painel-vazio-simulado.png`]*

*[Captura local, não versionada: Erro de carregamento em montagem simulada — `25-painel-erro-simulado.png`]*

*[Captura local, não versionada: Carregamento em montagem simulada — `26-painel-carregando-simulado.png`]*

*Estes três estados foram montados separadamente com componentes reais da aplicação, texto de erro de exemplo e uma faixa explícita. Não mostram uma sessão ou falha real, nem a navegação completa do painel.*

**Finalidade:** mostrar leituras disponíveis e o recorte selecionado de movimento.

```text
[INÍCIO / TÍTULO]                            [Dispositivo ▼]
[Aviso de mistura / lacuna, quando aplicável]
[Seleção: última sessão ↔ todas, quando houver várias]

[Eventos]   [Medido]   [Maior pausa]   [Intensidade]
[Nota sobre inferência / limites]
┌──────────────────────────────────────────────────────────────┐
│ Intensidade do movimento        legenda e limiar             │
│                    gráfico de barras                         │
└──────────────────────────────────────────────────────────────┘
┌───────────────────────┐ ┌──────────────────────────────────┐
│ Repouso × Movimento   │ │ Leituras recentes                │
│ proporções / horários │ │ Hora | intensidade | estado ...  │
└───────────────────────┘ └──────────────────────────────────┘
```

**Design:** o cabeçalho apresenta contexto e seletor. Avisos aparecem antes dos números quando a cobertura ou mistura de instrumentos pode afetar a interpretação. Quatro cartões compactos usam ícone, número, unidade e detalhe; a grade é de duas colunas em tamanho comum e quatro em telas largas. O gráfico de barras e os painéis inferiores ficam em cartões; a tabela pode rolar horizontalmente no celular. A série usa azul/âmbar, indicação de lacuna e linha de limiar; gráficos não reanimam a cada atualização.

**Dados apresentados:** eventos, tempo medido/cobertura, maior pausa sem movimento registrado e intensidade média do repouso; gráfico por instante, proporção por tempo medido, primeira/última leitura e até oito leituras recentes. Temperatura de chip aparece na tabela apenas quando há valor. Sem medida suficiente, uma mensagem substitui a proporção.

**Ações e estados:** selecionar aparelho e alternar recorte quando há múltiplas sessões; carregando, falha com “Tentar novamente” e vazio têm apresentações próprias. O seletor continua acessível nesses estados. A série padrão é a última sessão, quando existe.

**Ponto concreto a revisar:** o código ordena as leituras recentes pelo instante da medição, com fallback para chegada, mas uma frase sob a tabela diz “na ordem em que chegou”. Quando medição e envio divergem, o texto pode descrever a ordem errada. Isso foi identificado por leitura, não reproduzido em produção.

**Avaliação:** testar interpretação de “medido”, “cobertura”, “pausa” e “repouso” e interação com gráfico sem mouse; verificar se a tabela é alternativa suficiente para o recorte completo. Fontes: `pages/Dashboard.tsx`, `components/CardMetrica.tsx`, `AvisoDeLacuna.tsx`, seletores e `lib/metricas.ts`.

## 8. Coleta curta — `/coletar`

*[Captura local, não versionada: Coleta em desktop no modo de demonstração — `07-coletar-demo.png`]*

*[Captura local, não versionada: Coleta em janela móvel simulada — `15-coletar-mobile-demo.png`]*

*Estado anterior ao consentimento, sem coleta efetiva.*

*[Captura local, não versionada: Detalhes técnicos da coleta expandido no celular — `28-coletar-detalhes-mobile.png`]*

*Controles expandidos em demonstração, sem iniciar o sensor.*

**Finalidade:** usar o sensor disponível no navegador para uma sessão curta com tela ligada.

```text
REGISTRAR MOVIMENTO
Usar este celular como sensor
┌────────────────────────────────────────────┐
│ ⚠ Deixe a tela ligada e o app aberto      │
│ Explicação dos limites e da coleta noturna │
└────────────────────────────────────────────┘
┌────────────────────────────────────────────┐
│ [▶ Começar a registrar]                    │
│ ou tempo decorrido · número de registros   │
│ [■ Parar]                                  │
└────────────────────────────────────────────┘
▸ Detalhes técnicos
```

**Design:** título e contextualização, aviso com ícone e borda de destaque, moldura para ação principal e um elemento `details` recolhível para informações técnicas. Ao iniciar, temporizador numérico e total de registros substituem a ação inicial; Parar é visualmente destacado em cor destrutiva. No fim, quando há registros, aparece resumo e link ao painel.

**Detalhes técnicos:** nome do dispositivo usado para envio, seletor da janela de agregação (desativado enquanto coleta), amostras da janela e lista de até 12 registros exibidos, com horário, amostras, intensidade, classificação e estado de envio. Falha tem motivo no próprio texto, sem depender de tooltip.

**Estados:** sem consentimento; preparo; erro de preparo; pronto; coletando; parado com resumo; erros gerais e falhas de registros. A lista usa estados de envio, gravado e falhou. O aviso de falhas fica fora da área recolhida.

**Observado nas capturas:** tema escuro, aviso superior, botão azul, diálogo em primeiro plano e estado de coleta em 1 segundo com zero registros. O usuário confirmou a marcação do consentimento e o início; o salvamento de leitura e persistência após recarga não foram confirmados.

**Avaliação:** esclarecer que a primeira leitura aparece apenas após uma janela e se ela foi enviada ou salva; testar sensor indisponível, orientação, bloqueio de tela e falhas de rede. Arquivos: `pages/Coletar.tsx`, `hooks/useColeta.ts`, `hooks/useEnvioDoCelular.ts`.

## 9. Diálogo de consentimento — coleta e noite

*[Captura local, não versionada: Consentimento em desktop — `10-consentimento-demo.png`]*

*[Captura local, não versionada: Consentimento em tamanho móvel — `17-consentimento-mobile-demo.png`]*

*Caixa desmarcada e botão desabilitado; modo de demonstração, sem envio de consentimento.*

*[Captura local, não versionada: Consentimento marcado em tema escuro — `23-consentimento-marcado-demo.png`]*

*Caixa marcada e botão habilitado; não foi acionado o envio.*

**Finalidade:** apresentar o tratamento dos dados de saúde em momento separado do cadastro, antes da ação de coleta.

```text
[escurecimento do conteúdo de fundo]
┌─────────────────────────────────────────┐
│ escudo  Antes de começar: seus dados... │
│ • O que é medido e guardado             │
│ • Estimativa e limites                  │
│ • Tratamento e possibilidade de apagar │
│ Detalhes: política de privacidade       │
│ [ ] Li e concordo...                    │
│ [ Concordo ]  [ Agora não ]             │
└─────────────────────────────────────────┘
```

**Design:** sobreposição fixa escura, caixa com borda e fundo de cartão; ocupa até `max-w-md`, tem rolagem vertical e limite de altura. Em telas pequenas alinha ao fundo; em `sm` e acima centraliza. Título com escudo, lista de explicações, link, caixa marcada pelo usuário e dois botões.

**Comportamento:** sem caixa marcada, “Concordo” fica desabilitado; durante envio as ações ficam indisponíveis e aparece indicador. “Agora não” fecha pelo fluxo do componente, sem concordar. Mensagens de erro usam alerta. O usuário confirmou visualmente a habilitação e desabilitação; não foi confirmado nesta sessão se um aceite persistiu após recarregar.

**Acessibilidade a verificar:** o componente fornece `role=dialog`, `aria-modal` e título associado, mas não mostra tratamento explícito de foco inicial, contenção de foco ou devolução do foco. Testar com teclado e leitor de tela antes de afirmar o impacto. Arquivos: `components/TelaDeConsentimento.tsx`, `hooks/usePortaoDoConsentimento.ts`, `lib/consentimento.ts`.

## 10. Noite inteira — `/noite` no Android

*[Captura local, não versionada: Tela Noite no Moto E7 — `18-noite-android-dados-reais.png`]*

*Captura real autorizada para uso local: contém data e métricas de gravação anterior. Não é dado simulado. A captura mostra a tela antes de iniciar uma nova noite.*

*[Captura local, não versionada: Rota Noite no navegador — `08-noite-web.png`]*

*No navegador, a rota explica que o registro noturno requer o aplicativo Android.*

**Finalidade:** conduzir o ciclo antes, durante e depois de uma noite no aplicativo nativo.

```text
REGISTRO DA NOITE
A noite inteira
┌─────────────────────────────────────────┐
│ ☾ Registrar a noite inteira             │
│ Explicação sobre tela apagada           │
│ Onde o celular vai ficar?               │
│ ( ) Fronha  ( ) Colchão  ( ) Outro      │
│ Aviso de calor                           │
│ [ Iniciar a noite ]                     │
│ / [ Encerrar a noite ]                  │
│ Estado, cobertura, taxa e envio         │
└─────────────────────────────────────────┘
Noites neste aparelho
[cartões com resumo e anotações]
```

**Antes:** selecionar uma de três posições; a ação fica indisponível enquanto falta posição ou estado nativo ainda não carregou. A interface orienta não carregar o celular dentro da fronha e informa encerramento a 45 °C.

**Durante e depois:** mostra ação de encerrar, épocas, cobertura, taxa, recusas, retomadas e temperatura quando disponíveis. Há mensagem para interrupção, retomada ou encerramento, botão para isenção de economia de bateria quando pertinente, épocas aguardando envio, progresso e resultado. A presença desses controles no código não demonstra que o Android manterá a coleta em toda condição.

**Lista de noites:** cartões em ordem recente, com posição, duração, épocas, cobertura, envio e alerta de término por temperatura. Para noites encerradas, anotações expansíveis incluem horário de deitar, adormecer e acordar, despertares lembrados e observações; o componente informa que as notas são salvas no aparelho. O link ao painel aparece quando há envio.

**No navegador:** a rota explica que a noite inteira exige o app Android, por causa do sensor quando a tela bloqueia.

**Avaliação:** testar se números técnicos são compreendidos e se os estados “gravada no aparelho”, “enviada” e “visível na conta” são distintos. A leitura de `ListaDeNoites.tsx` mostra que falha ao listar é convertida em lista vazia: isso pode apresentar “nenhuma noite” mesmo em erro; confirmar o comportamento no aparelho antes de propor correção. Arquivos: `pages/Noite.tsx`, `components/CartaoDaNoite.tsx`, `ListaDeNoites.tsx`.

## 11. Configurações — `/configuracoes`

*[Captura local, não versionada: Configurações em desktop no modo de demonstração — `09-configuracoes-demo.png`]*

*Sem sessão e sem backend local; o erro exibido é deste ambiente, não uma conclusão sobre produção.*

*[Captura local, não versionada: Configurações em tamanho móvel — `16-configuracoes-mobile-demo.png`]*

*Região inicial visível em janela móvel simulada.*

*[Captura local, não versionada: Configurações em tema escuro — `19-configuracoes-escuro-demo.png`]*

*[Captura local, não versionada: Formulário de edição do perfil em demonstração — `20-edicao-perfil-demo.png`]*

*[Captura local, não versionada: Confirmação de exclusão sem efetivar a ação — `21-confirmacao-exclusao-demo.png`]*

*Demonstração sem conta real; a confirmação não foi enviada.*

**Finalidade:** reunir preferências e controles de conta, dispositivos e dados.

```text
Configurações
Conta, dispositivos e seus dados
┌ Aparência ──────────────────────────────┐
│ [ Claro ] [ Escuro ] [ Sistema ]       │
└─────────────────────────────────────────┘
┌ Conta ──────────────────────────────────┐
│ Perfil e edição                         │
└─────────────────────────────────────────┘
┌ Meus dispositivos ─────────────────────┐
│ Lista e ações de gerenciamento          │
└─────────────────────────────────────────┘
┌ Seus dados ─────────────────────────────┐
│ Exportar CSV · Política de Privacidade  │
└─────────────────────────────────────────┘
[ Sair da conta ]
┌ Excluir conta ──────────────────────────┐
│ Explicação e confirmação própria        │
└─────────────────────────────────────────┘
```

**Design:** coluna de até `max-w-2xl`, blocos de cartão separados, cada um com ícone, título e texto de apoio. A exclusão ocupa seção final distinta, evitando proximidade imediata com a exportação. O seletor visual de tema é grade com três opções.

**Conta:** exibe e permite corrigir dados de perfil; o formulário contém nome, idade opcional e e-mail, com mensagens e ações de edição/salvamento. A idade é contextualizada na aplicação.

**Dispositivos:** componente lista e permite gerenciar dispositivos, incluindo nomeação e revogação; a interface também contém fluxo de token e cópia. Avaliar clareza das consequências antes da revogação e exposição do token.

**Dados:** botão para exportação CSV apresenta estado de preparo, vazio e erro; a consulta usa limite do painel. Política é acessível por link. Não afirmar exportação integral sem verificar paginação e histórico acima do limite.

**Sair:** ação independente que apresenta estado “Saindo...”.

**Excluir:** primeiro exibe explicação e botão; a confirmação abre painel com aviso de irreversibilidade, lista do que será eliminado, orientação para exportar e campo para digitar frase de confirmação. Há cancelar, processamento e tratamento de desfechos. O fluxo não deve ser testado em conta com dados que devam ser preservados.

**Avaliação:** testar teclado do seletor de tema, clareza de limites do CSV e compreensão de exclusão. Fontes: `pages/Settings.tsx`, `components/EditarPerfil.tsx`, `MeusDispositivos.tsx`, `ExcluirConta.tsx`, `SeletorDeTema.tsx`.

## 12. Estados transversais e navegação

| Situação | Tratamento encontrado | Verificação recomendada |
|---|---|---|
| Sessão sendo restaurada | Indicador central e texto para leitor de tela | Recarregar rota protegida com rede lenta |
| Sem sessão em área protegida | Redireciona para login e guarda o caminho interno | Confirmar retorno após login |
| URL desconhecida | Redireciona para `/` | Testar recuperação de link incorreto |
| Política carregando | Mensagem textual no `Suspense` | Testar rede lenta |
| Painel sem dados | Ícone, explicação e seletor de dispositivo | Testar conta nova e filtros |
| Painel com erro | Mensagem específica e nova tentativa | Simular falha de rede |
| Modo de demonstração | Faixa e dados de demonstração; disponível apenas em desenvolvimento conforme guarda | Evitar interpretar dados fictícios como reais |
| Tema | Claro, escuro ou sistema | Testar contraste real, persistência e ausência de flash |
| Movimento reduzido | CSS desativa animações declaradas | Verificar também spinners e componentes fora dessa lista |

## 13. Roteiro de revisão visual por tela

Para completar a documentação com evidência visual, capturar cada tela em **desktop e Moto E7**, sem dados pessoais, registrando data, dispositivo, tamanho, tema, versão e estado. Para cada rota, incluir ao menos: estado inicial; carregamento/vazio/erro quando existirem; estado após ação; e diálogo ou formulário aberto. Priorizar `login`, `cadastro`, `dashboard` vazio e com dados, `coletar` antes/durante/depois, consentimento, `noite` em cada fase e `configuracoes`.

Verificar largura pequena, rolagem, texto ampliado, navegação inferior, safe area, contraste, foco visível, teclado, leitor de tela e orientação. Usar contas e registros de teste autorizados; não criar ou apagar dados de terceiros. Registrar cada observação com tela, condição, passos, esperado, observado e evidência. Os esquemas deste documento não substituem essas capturas.

## 14. Procedência e verificação

Leitura de `App.tsx`, páginas e componentes referidos acima, `styles/theme.css`, `styles/animacoes.css`, código de navegação e backlog; capturas e relatos do usuário nesta conversa. A suíte do frontend executada nesta máquina em 10/11 teve **561 testes aprovados em 43 arquivos**. A suíte não mede compreensão, qualidade visual ou conformidade integral de acessibilidade. Revisado pelo Claude e versionado em 12/11, sem as capturas (ver o aviso no início).
