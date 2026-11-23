# Redesenho do app — o inventário antes de mudar (`UI-43`, etapa 0)

**Escrito em:** 23/11/2026, sobre `develop` `1c07d76`, antes de qualquer mudança de tela.

**O problema.** O celular de exemplo da landing (`frontend/public/landing-prototipo.html`, `#sd-phone`)
mostra um app com outro visual e outras telas: quatro abas (Início, Relatório, Eventos, Ajustes), um
número grande em destaque e cartões de métrica. O app real tem cinco destinos (Início, Noite, Histórico,
Dispositivos, Configurações) e um visual mais de painel. O autor quer levar o que a landing tem de
melhor para o app, **sem perder nenhuma função nem dado**, e fazer a landing mostrar o app de verdade.

**A regra deste redesenho.** Mudar a aparência, não o que o app faz. Cada função listada abaixo continua
existindo, e o teste que a protege continua passando. Um teste só muda junto com um texto que mudou de
propósito, e a mudança vai dita na PR. Função nova entra só com decisão do autor.

---

## 1. As duas versões, tela a tela

| Landing (exemplo) | App real | O que levar da landing | O que o app mantém |
|---|---|---|---|
| **Início**: cartão escuro "TEMPO MONITORADO 7h 24m", gráfico, cartões "18 eventos" e "96% de cobertura" | **Início** (`/dashboard`): resumo da última sessão em texto, gráfico, aparelho, sessões anteriores, detalhes técnicos | O número em destaque num cartão escuro; cartões de métrica lado a lado; etiqueta em maiúsculas e título curto; o cabeçalho com a marca | O resumo honesto (registrado de, paradas, movimento em % do tempo, maior período sem movimento) |
| **Relatório**: gráfico por período (noite toda, 23h–3h, 3h–7h), valor ao tocar, janela e cobertura | Não existe; o gráfico está no Início | A escolha do período e o valor ao tocar | — |
| **Eventos**: 18 "eventos" com filtros Leve/Moderado/Intenso e nomes como "Giro corporal" | Não existe | Só o formato de lista; os nomes de gesto não (o sensor não sabe o gesto) | — |
| **Ajustes**: aparelho "simulado", "sensibilidade", modo claro, avisos | **Configurações** | Os grupos em cartões, com linhas e o valor à direita | Tudo (seção 2.5) |
| Não existe | **Noite** (só no app) | — | Tudo (seção 2.2) |
| Não existe | **Histórico** | O estilo de cartão e de etiqueta | Tudo (seção 2.3) |
| Não existe | **Dispositivos** | O estilo de linha com ícone e etiqueta de estado | Tudo (seção 2.4) |

**O que a landing mostra e o app não faz**, e por isso não entra como está:
- **Nomes de gesto** ("Giro corporal", "Ajuste de posição"): o acelerômetro mede intensidade, não o
  gesto. Uma versão honesta seria "períodos com movimento", com horário e intensidade medida.
- **"Sensibilidade" ajustável:** o limite de movimento é fixo até o `DATA-06`, que espera o `VIA-02`.
- **"Eventos identificados" como contagem:** o app mede a fração do tempo com movimento, não eventos.

A comparação em imagem (as quatro abas da landing e as quatro telas do app em modo demonstração) foi
entregue ao autor em 23/11, fora do repositório.

---

## 2. Inventário das funções, com o teste que protege cada uma

Os arquivos de teste ficam em `frontend/src/`. "montagem" é o `montagem.test.ts`, que monta as telas de
verdade.

### 2.1 A casca (todas as telas depois do login)

| Função | Protegida por |
|---|---|
| Barra de baixo no celular: no app, Início, Noite, Histórico, Dispositivos, Configurações; no site, Coletar no lugar de Noite | `components/nav.test.ts`, montagem |
| Rótulos da barra inteiros a 360 px | conferido no navegador (o jsdom não mede texto); `UI-41` |
| Faixa de versão nova do app (`APP-19`), só no app, carregada à parte | `AvisoDeAtualizacao.test.tsx`, `useEnvioDoCelular.test.ts` |
| Tema claro, escuro ou do sistema | `SeletorDeTema.test.tsx` |
| Modo demonstração (`?demo=1`) só no build de desenvolvimento | `Guardas.test.tsx` |
| Toda rota monta; rota desconhecida volta ao início | montagem ("toda rota do App.tsx monta", "rotas esperadas") |
| Orçamento do pacote do painel (260 000 B comprimidos; 259 763 B em 23/11) | `scripts/conferir_pacote_frontend.py`, no CI |
| Linguagem sem jargão depois do login | `linguagem.test.ts` |

### 2.2 Noite (só no app)

| Função | Protegida por |
|---|---|
| Iniciar e encerrar a noite pelo serviço nativo | `CartaoDaNoite.test.tsx` |
| Escolher a posição do celular antes de iniciar; sem ela, não começa | `CartaoDaNoite.test.tsx` |
| Aviso de não carregar o celular dentro da fronha, antes do botão | `CartaoDaNoite.test.tsx` |
| Gravação de teste (fica só no aparelho, não é enviada) | `CartaoDaNoite.test.tsx`, `ListaDeNoites.test.tsx` |
| Consentimento antes da primeira noite (o portão) | `TelaDeConsentimento.test.tsx` |
| Pedido da isenção de bateria | `CartaoDaNoite.test.tsx` |
| Noite interrompida: avisa e oferece retomar | `CartaoDaNoite.test.tsx` |
| Cobertura, ritmo do sensor, retomadas, temperatura e calibração (Detalhes técnicos recolhidos) | `CartaoDaNoite.test.tsx` ("os números do sensor em Detalhes técnicos") |
| Envio automático e manual, serializado, com a falha à vista | `CartaoDaNoite.test.tsx`, `envioDaNoite.test.ts` |
| Versão do app enviada ao preparar o aparelho (`APP-19`) | `useEnvioDoCelular.test.ts` |
| Lista das noites do aparelho: posição, envio, cobertura, noite em andamento, encerrada pelo calor | `ListaDeNoites.test.tsx` |
| Anotações da noite (deitei, adormeci, acordei, despertares, observação), salvas no aparelho | `ListaDeNoites.test.tsx` |
| Apagar ou compartilhar uma gravação de teste | `ListaDeNoites.test.tsx` |
| "Ver no painel" só com algo enviado | `ListaDeNoites.test.tsx` |

### 2.3 Início e Histórico

| Função | Protegida por |
|---|---|
| Resumo da última sessão: registrado de, paradas, movimento em % do tempo, maior período sem movimento, sem dar nota | `ResumoDaSessao.test.tsx` |
| O aparelho da sessão, mesmo com todos selecionados | montagem ("o painel em camadas") |
| A ordem: resumo, gráfico, sessões anteriores, detalhes e escopo | montagem ("o painel em camadas") |
| Gráfico de intensidade com o limite de movimento | montagem |
| Avisos de lacuna, de duração estimada e de escopo | montagem ("avisos no painel") |
| Travesseiro pausado avisado no painel vazio | montagem |
| Detalhes técnicos recolhidos, com a fórmula, o limite e a tabela | montagem |
| Histórico paginado até o teto | montagem |
| A escolha da janela (24 h, 7 dias, 30 dias) | ⚠️ **sem teste de tela**: escrever antes de mexer |
| Cartões no celular com a situação (Completa, Com pausas, Incompleta) | `Historico.test.tsx` |
| Excluir uma sessão com confirmação modal; Esc não cancela no meio | `Historico.test.tsx` |
| Marcar e desmarcar como bancada; a seção das marcadas | `Historico.test.tsx` |
| Excluir e marcar só a sessão mostrada; divergência avisa (`DATA-17`) | `Historico.test.tsx` |

### 2.4 Dispositivos

| Função | Protegida por |
|---|---|
| Lista com tipo, último envio e estado | montagem |
| Parear o travesseiro, com o código mostrado uma vez, copiar ou selecionar à mão | montagem |
| O celular não precisa de pareamento: a explicação com o link para Noite ou Coletar (`UI-42`, PR aberta) | montagem |
| Pausar (com confirmação do descarte) e retomar o recebimento | montagem |
| Esperar o primeiro envio, com consulta periódica e verificação manual | montagem |
| Renomear e revogar | ⚠️ **sem teste de tela**: escrever antes de mexer |

### 2.5 Configurações

| Função | Protegida por |
|---|---|
| Tema | `SeletorDeTema.test.tsx` |
| Conta: nome, e-mail, editar o perfil e a idade, com o aviso de aplicabilidade | montagem |
| Lembrete de dormir, só no app (`APP-20`, PR aberta) | `LembreteDeDormir.test.tsx` |
| Dispositivos | montagem |
| Exportar o histórico inteiro em CSV | montagem, `exportar.test.ts` |
| Política de privacidade | montagem |
| Sair | ⚠️ **sem teste de tela**: escrever antes de mexer |
| Excluir a conta, em duas etapas | montagem |

---

**Quatro funções sem teste de tela** (contadas em 23/11, por busca nos testes): a escolha da janela do
Histórico, renomear, revogar e sair. Elas ganham teste **antes** de a tela delas mudar, contra o código
de hoje, para que o redesenho não as perca em silêncio.

## 3. As decisões do autor, antes da etapa 1

1. **As abas.** ✅ **Decidido pelo autor em 23/11: as cinco do app** (Início, Noite, Histórico,
   Dispositivos, Configurações), com o visual da barra da landing. O "Relatório" da landing vira a parte
   de baixo do Início, ou uma tela aberta pelo gráfico.
2. **"Períodos com movimento"** (a versão honesta dos "Eventos"). ✅ **Decidido pelo autor em 23/11:
   depois do redesenho**, como item próprio (`UI-44`). O redesenho muda só a aparência.
3. **A fonte** (`UI-36`). ✅ **Decidido pelo autor em 23/11: a do sistema**, a mesma da landing e das
   páginas públicas (`docs/PADRAO-VISUAL.md`, seção 1). A Outfit sai do app na etapa 1, e com ela a
   chamada ao Google Fonts a cada abertura.

## 4. As etapas

| Etapa | O quê | Como se confere |
|---|---|---|
| 0 | Este inventário e a comparação em imagem | — |
| 1 | A base visual: cores, cantos, escala de texto e estilos de cartão da landing, no claro e no escuro; a fonte | Contraste, as duas cores, o orçamento do pacote |
| 2–6 | Uma tela por vez: Início, Noite, Histórico, Dispositivos, Configurações | Os testes da seção 2 passando; imagens antes e depois a 360 e 390 px; a Noite no emulador |
| 7 | A landing mostra as telas novas, com as mesmas abas e textos | Um teste que compara as abas e os rótulos da landing com os do app |

**Riscos.** ~~O orçamento do painel tem 237 B de folga~~: resolvido na etapa 1 pela troca do gráfico do
recharts por SVG próprio (156 131 B de 260 000 B, 23/11). A tela Noite só aparece no app, e a conferência
visual dela é no emulador.
