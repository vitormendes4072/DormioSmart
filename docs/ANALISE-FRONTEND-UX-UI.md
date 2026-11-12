# Análise e documentação do frontend — DormioSmart

**Data:** 10/11/2026 · **Base examinada:** `0a86de1` (conteúdo de `develop` levado à produção pela release #121). Documento elaborado pela leitura do código e dos registros da sessão. Não é um laudo de acessibilidade, estudo com usuários nem confirmação de cada fluxo em produção. As capturas compartilhadas cobrem a coleta web e o consentimento; a análise das demais telas é principalmente estática.

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

**Catálogo complementar:** [telas, composição visual, controles e estados](CATALOGO-TELAS-FRONTEND.md).

## 1. Visão geral e conclusão

O frontend combina uma página pública de apresentação, uma aplicação autenticada para consultar e coletar dados e uma versão Android construída com Capacitor. A linguagem procura relacionar tecnologia e sono: azul, superfícies escuras ou claras, traçado de movimento e elementos de desenho técnico. A interface declara limites relevantes: movimento e estimativas não constituem diagnóstico nem estadiamento clínico.

O produto já possui bases de UX importantes: rotas protegidas, mensagens de carregamento e erro, uma tela específica de consentimento, avisos para coleta, modo noturno, histórico, controle dos dados e confirmação de exclusão. A implementação tem testes automatizados. As prioridades de melhoria são validar com pessoas reais os percursos completos, reforçar o comportamento de teclado e leitor de tela do diálogo de consentimento, tornar mais claras as etapas e o resultado da coleta e verificar a experiência móvel e offline no Android.

**Limites da análise:** nenhuma entrevista, teste de usabilidade, auditoria automatizada de acessibilidade ou medição de desempenho em rede real foi feita para este documento. Avaliações como “claro” ou “complexo” são hipóteses de design, não resultados medidos em usuários. O funcionamento nativo da noite e o envio de uma leitura após a instalação recente ainda não foram observados nesta sessão.

## 2. Produto, público e contexto de uso

- **Finalidade:** apresentar informações sobre movimento durante o repouso e oferecer uma estimativa de sono/vigília por época onde disponível, dentro dos limites declarados pelo projeto.
- **Contextos:** visitante que conhece o TCC; pessoa autenticada que consulta o histórico; pessoa que usa o navegador para coleta curta; pessoa que usa o Android para registrar a noite; autora ou autor que administra perfil e dados.
- **Condições de uso relevantes:** leitura em telas pequenas, eventualmente à noite, permissões de sensor e bateria, conectividade variável e necessidade de compreender o alcance do sistema antes de compartilhar dados sensíveis.
- **Distinção científica:** repouso não é sinônimo de sono; movimento não mede, sozinho, estágios de sono ou diagnóstico. A linguagem da interface deve manter essa distinção em gráficos, rótulos, explicações e mensagens de erro.

## 3. Arquitetura de informação e navegação

| Endereço | Acesso | Objetivo | Implementação principal |
|---|---|---|---|
| `/` | Público | Apresentação, limites, funcionamento e estágio do projeto; no Android nativo redireciona para noite | `pages/Landing.tsx`, `App.tsx` |
| `/login` | Visitante | Entrar e solicitar recuperação de senha | `pages/Login.tsx` |
| `/cadastro` | Visitante | Criar conta, declarar maioridade e acessar a política | `pages/Register.tsx` |
| `/nova-senha` | Por link de recuperação | Definir senha; inclui estados de sucesso e link inválido | `pages/NovaSenha.tsx` |
| `/privacidade` | Público | Ler política antes ou depois do cadastro | `pages/Privacidade.tsx` |
| `/dashboard` | Autenticado | Explorar leituras, métricas e gráficos | `pages/Dashboard.tsx` |
| `/coletar` | Autenticado | Coleta curta com sensor no navegador | `pages/Coletar.tsx` |
| `/noite` | Autenticado | Coleta noturna no Android; no navegador explica a limitação | `pages/Noite.tsx` |
| `/configuracoes` | Autenticado | Tema, perfil, dispositivos, exportação, saída e exclusão | `pages/Settings.tsx` |

A navegação autenticada usa barra lateral em telas maiores e barra inferior fixa no celular, com espaço reservado no conteúdo e consideração da área segura do aparelho. Web: Início, Coletar, Configurações. Android nativo: acrescenta Noite no início. A barra inferior contém destinos; Sair fica em Configurações. Guardas aguardam a recuperação da sessão antes de redirecionar, e a rota protegida registra o destino anterior para retorno após login. Caminhos desconhecidos retornam à página inicial.

**Fontes:** `frontend/src/App.tsx`, `components/nav.ts`, `Layout.tsx`, `Sidebar.tsx`, `MobileNav.tsx` e `Guardas.tsx`. O comentário em `Layout.tsx` que afirma ausência de proteção está desatualizado: o próprio `App.tsx` envolve o layout em `RotaProtegida`. Isso é uma inconsistência documental, não evidência de rota desprotegida.

## 4. Jornadas e estados

### 4.1 Primeiro acesso e conta

1. Na web, a pessoa chega à landing e pode ir para login ou cadastro; quem já tem sessão recebe acesso ao painel.
2. O cadastro coleta nome, e-mail e senha, apresenta a declaração de maioridade e um link para a política. Há feedback de envio e de erro; o código também contempla confirmação de e-mail.
3. Login oferece mostrar/ocultar senha e recuperação. A tela de nova senha trata formulário, sucesso e link inválido ou expirado.
4. Na abertura de rota protegida, uma espera impede redirecionamento prematuro enquanto a sessão é restaurada.

**Avaliação:** o acesso à política antes do cadastro e a nomeação dos campos ajudam a decisão informada. O roteiro de recuperação deve ser testado de ponta a ponta com uma conta apropriada: o backlog aponta restrição do SMTP para pessoas externas (`AUTH-06`). Não se deve inferir que todo testador receberá o e-mail apenas porque a tela existe.

### 4.2 Consentimento e coleta curta na web

A tela `/coletar` alerta que o navegador pode interromper o sensor quando a tela bloqueia e que o percurso é para sessões curtas. Sem consentimento vigente, a ação abre diálogo específico com explicação, link para política, caixa de concordância, opção “Agora não” e botão que depende da marcação. Após consentir há preparação do dispositivo, início, duração e contagem, parada, feedback de falhas e acesso ao painel. Detalhes técnicos ficam recolhidos.

**Evidência da sessão:** o usuário mostrou a tela autenticada, confirmou que o botão desabilita sem marcação e relatou que o aceite liberou o início. Uma captura mostrou coleta em 1 segundo com zero registros. A persistência após recarga e o salvamento de uma leitura não foram confirmados. As capturas fornecidas não estabelecem que todos os passos ocorreram na mesma conta.

**Oportunidades:** deixar explícito, após aceitar, se é necessário tocar novamente em “Começar a registrar”; distinguir “contagem local” de “leitura salva no servidor”; explicar tempo esperado até a primeira leitura e como agir se ele não aparecer. Validar as mensagens de permissão, perda de rede, falha de preparo e recuperação sem induzir a criar dados de teste desnecessários.

### 4.3 Noite no Android

No app, a rota inicial é Noite. A pessoa escolhe a posição do celular, recebe orientação térmica e pode iniciar a noite após consentimento. Durante e depois da coleta, o cartão oferece encerramento, estado de interrupção e retomada, épocas gravadas, cobertura, taxa do sensor, recusas, temperatura quando disponível, envio pendente e progresso. A lista de noites contempla anotações e estados locais. O código tenta enviar épocas pendentes ao abrir o app quando não há noite ativa e o envio está disponível.

**Avaliação:** a separação entre web de curta duração e Android noturno é coerente com as limitações descritas. Entretanto, termos como “época”, “taxa”, “cobertura” e “recusadas” podem exigir explicação contextual para quem não conhece o TCC. A existência de mensagens e lógica no código não comprova o registro durante toda uma noite, a retomada em todos os aparelhos ou o envio após perda de rede. O Moto E7 recebeu o APK atualizado nesta sessão, mas o fluxo nativo ainda precisa ser exercitado.

### 4.4 Consulta e configuração

O painel usa seleção de dispositivo e de sessão, estados de carregamento, erro com nova tentativa e ausência de dados. A tela apresenta métricas, série de intensidade, repouso versus movimento e tabela de leituras recentes; o processamento de cobertura e lacunas procura não tratar ausência de amostras como repouso. A tabela e os rótulos complementam a cor dos gráficos.

Configurações reúne tema claro/escuro/sistema, edição do perfil, dispositivos, exportação CSV, acesso à política, saída e exclusão em seção própria com confirmação. A exportação usa o limite do painel: antes de descrevê-la como cópia completa do histórico, conferir a limitação efetiva e comunicá-la com precisão.

## 5. Linguagem visual e sistema de interface

| Elemento | Implementação observada | Papel de design |
|---|---|---|
| Identidade | `--brand: #35a2ef`; logo e elementos gráficos | Reconhecimento da marca |
| Ação no tema claro | `--primary: #0b6db5` | Links e ações em contraste com superfícies claras |
| Ação no tema escuro | `--primary: #4fb3f5` | Interação em fundo escuro |
| Superfícies | Claro `#f4f7fb` / cartão `#ffffff`; escuro `#070d18` / cartão `#0e1726` | Hierarquia entre fundo e conteúdo |
| Risco | Vermelho de destruição e alertas; texto acompanha cor em diversos estados | Diferenciar exclusão/erro |
| Gráficos | Azul para repouso e âmbar para movimento | Separação visual complementada por texto e tabela |
| Tipografia | Outfit como fonte principal, com fontes de sistema de reserva; CSS importa Outfit e Inter | Legibilidade e identidade |
| Formas | Raio base `0.875rem`, cartões e botões arredondados | Continuidade visual |
| Ícones | Lucide React | Reforço visual de destinos, estados e ações |
| Movimento | Revelação e traçado animado, com tratamento de `prefers-reduced-motion` para as animações declaradas | Feedback e apresentação sem depender do movimento |

Os valores e razões de contraste declarados em `styles/theme.css` são documentação dos tokens; não constituem auditoria de todos os pares efetivamente renderizados. A fonte é importada do Google Fonts: testar carregamento sem rede e a experiência com fontes de reserva. O CSS e componentes usam classes responsivas, incluindo mudança para navegação lateral em `md`; isso não substitui verificação em tamanhos, zoom e fontes ampliadas.

### Padrões recorrentes

- Cartões delimitam áreas de tarefa; títulos curtos e texto secundário explicam contexto.
- Ação primária usa preenchimento azul; ações secundárias tendem a contorno; exclusão usa tratamento próprio e confirmação.
- `role="alert"`, `role="status"` e `aria-live` aparecem em estados selecionados; ícones decorativos recebem `aria-hidden` em vários componentes.
- A landing utiliza molduras, cotas e traçado para sugerir um projeto de engenharia. O backlog `UI-20` já registra a extensão dessa linguagem à área autenticada como ideia pós-banca; não pressupõe que seja prioritária.

## 6. Avaliação crítica: achados e hipóteses

| Prioridade sugerida | Achado e evidência | Impacto possível | Próxima verificação |
|---|---|---|---|
| Alta | O diálogo declara `role="dialog"` e `aria-modal`, mas `TelaDeConsentimento.tsx` não implementa gestão explícita de foco, retorno ao controle de origem ou restrição de Tab ao diálogo. | Pessoas que usam teclado ou leitor de tela podem alcançar conteúdo atrás do diálogo ou perder o contexto. | Reproduzir abertura, Tab/Shift+Tab, Escape, recusa e retorno do foco em navegador e Android; definir comportamento antes de corrigir. |
| Alta | A confirmação visual da sessão mostra início da coleta, mas nenhuma leitura persistida; a tela indica 0 registros em 1 s. | Iniciar um cronômetro pode ser confundido com gravação concluída. | Medir uma coleta autorizada até envio e retorno no painel; avaliar mensagem “aguardando primeira leitura” e estados local/enviado/salvo. |
| Alta | O fluxo Android atualizado foi instalado, mas ainda não foi percorrido nesta sessão. | Permissões, interrupção, economia de bateria e envio podem ter diferenças reais no dispositivo. | Roteiro no Moto E7, com pessoa presente, consentimento e dados de teste claramente identificados; não inferir resultado de testes web. |
| Média | O seletor de tema usa botões com papéis de rádio e `aria-checked`, sem tratamento explícito de teclas direcionais no componente. | O comportamento de teclado pode divergir do esperado para um grupo de rádio. | Testar setas, Tab e anúncio por leitor de tela; considerar controles nativos ou padrão acessível completo. |
| Média | A coleta web, o registro noturno e o dispositivo no travesseiro são meios distintos. | O usuário pode esperar que a coleta no navegador funcione a noite toda. | Testar se usuários conseguem explicar a diferença antes de iniciar; melhorar orientação e nomes se necessário. |
| Média | Termos técnicos no cartão noturno e no painel exigem familiaridade com medição. | A pessoa pode interpretar cobertura como qualidade do sono ou confundir ausência de sinal com repouso. | Testar compreensão e acrescentar definições, unidades e limites junto às métricas. |
| Média | O componente de exportação busca leituras com `LIMITE_DO_PAINEL`. | “Meus dados” pode sugerir um histórico completo sem demonstrar que o limite cobre tudo. | Examinar o contrato de paginação e testar conta com histórico acima do limite; explicitar escopo ou oferecer exportação completa. |
| Média | O link para política sai do diálogo de consentimento pela rota interna. | A pessoa pode perder o contexto e precisar reiniciar a ação. | Verificar ida e volta na web e no Android; estudar retorno previsível sem presumir comportamento atual. |
| Média | O bundle de produção do build Android da sessão gerou aviso do Vite para chunk principal acima de 500 kB; o backlog já contém `UI-15`. | Pode afetar carregamento em dispositivos ou redes lentas. | Medir tempo real em aparelho e rede lenta; tratar com base em medição, sem deduzir lentidão apenas pelo tamanho. |
| Baixa | Comentário de `Layout.tsx` diz que rotas não são protegidas, enquanto `App.tsx` usa guardas. | Pode confundir futuras análises e manutenção. | Atualizar comentário em mudança própria e confirmar testes de guardas. |

Prioridades são uma proposta desta análise, não itens oficialmente criados ou fechados no backlog. A avaliação não garante conformidade legal ou com qualquer norma de acessibilidade.

## 7. Plano de validação de UX e acessibilidade

1. **Orientação inicial:** pedir à pessoa que explique o que o Dormio mede, o que não mede e qual opção usaria para uma noite completa. Observar se identifica diferenças entre navegador, app e protótipo físico.
2. **Conta e consentimento:** criar ou usar conta apropriada; testar caixa desmarcada, aceite, recusa, política, erro de rede e retorno à coleta. Recarregar e verificar se o consentimento persiste, sem expor informações pessoais.
3. **Coleta curta:** permitir sensor, iniciar, aguardar a primeira janela e confirmar uma leitura salva e visível; testar permissão negada e rede interrompida. Dados de teste devem ser identificados e tratados conforme o projeto.
4. **Android:** testar posição, permissões, início, tela apagada, interrupção/retomada, encerramento, envio, anotações e recuperação de falhas no aparelho real; não prometer uma noite completa a partir de teste breve.
5. **Painel:** pedir que a pessoa localize dispositivo/sessão, explique movimento, repouso, cobertura e lacunas e encontre leituras recentes. Verificar vazio, carregamento, falha e histórico longo.
6. **Dados e controle:** testar editar perfil, exportar e sair. Exclusão de conta somente em conta de teste apropriada, com autorização e dados descartáveis.
7. **Acessibilidade:** percorrer por teclado, leitor de tela, ampliação, tema claro/escuro, preferência por menos movimento e diferentes tamanhos; verificar contraste de pares reais, foco, ordem e tamanho dos alvos. Registrar dispositivo, navegador, tecnologia assistiva, passos e resultado.
8. **Estudo com usuários:** preparar roteiro, tarefas e critérios; coletar dificuldades e tempo sem interpretar amostra pequena como representativa. Qualquer uso de dados de terceiros para pesquisa depende das decisões e autorizações do projeto.

## 8. Arquitetura técnica para manutenção

- **Interface:** React 18, TypeScript, Vite, Tailwind CSS, React Router, Lucide e Recharts; versões em `frontend/package.json`.
- **Estado e dados:** `AuthProvider` envolve `PerfilProvider`; hooks específicos coordenam histórico, coleta, dispositivos, tema, consentimento e envio; `lib/api.ts` e módulos adjacentes encapsulam comunicação.
- **Android:** Capacitor envolve o mesmo frontend; o plugin nativo de noite e seu serviço suportam funções indisponíveis no navegador. `vite.config.ts` define o endereço de backend para build `app`.
- **Privacidade:** política é carregada sob demanda; controle de consentimento também depende de backend/banco, não apenas da caixa na interface.
- **PWA:** registro de service worker existe; seus limites e comportamento offline precisam de teste próprio.
- **Comandos:** `npm ci`, `npm test`, `npm run build` para web; `npm run build:app` e `gradlew assembleDebug` para a variante Android de desenvolvimento. Variáveis locais e chaves não devem entrar no repositório.

## 9. Evidências e verificações

- Leitura das rotas, páginas, componentes, tokens de estilo e backlog sobre a base indicada. Não foi feita inspeção visual individual de todas as telas.
- Capturas e relatos do usuário nesta conversa: consentimento na coleta web e início da coleta, com as limitações descritas na seção 4.2.
- Nesta máquina Windows, `npm test -- --reporter=dot`: **43 arquivos e 561 testes passaram** em 10/11/2026 após repetição com acesso adequado. A primeira tentativa não iniciou testes: falhou com `EPERM` no diretório temporário do sandbox. Os testes automatizados não são prova de usabilidade nem de acessibilidade integral.
- Em etapa anterior desta mesma sessão, `npm run build:app` e `assembleDebug` passaram e o APK foi instalado no Moto E7; isso não testa o percurso em uso.
- Documentos e fontes internas: `frontend/src/App.tsx`, `frontend/src/pages/`, `frontend/src/components/`, `frontend/src/styles/theme.css`, `frontend/src/styles/animacoes.css`, `frontend/src/lib/`, `docs/BACKLOG-COMPLETO.md`, `docs/DISTRIBUICAO-DO-APP.md` e `docs/DIARIO-DE-ENGENHARIA.md`.
