# Padrão visual das páginas públicas — Smart Dormio

> ✏️ **22/11 (`UI-39`):** a seção 10, e só ela, vale para o app depois do login: é o glossário das telas.

> **Criado em 2026-11-19 (`UI-34`).** Os logos, os ícones e a paleta, cada um em arquivo próprio,
> estão no manual da marca, [`docs/marca/README.md`](marca/README.md). Antes de criar ou mudar uma página pública, ler este
> arquivo. **O padrão é o da home** (`frontend/public/landing-prototipo.html`): quando este
> documento e a home divergirem, a home vale, e este documento é corrigido.
> Os números abaixo foram **medidos** na produção, no navegador, a 1280 px de largura, em
> 19/11. Não são intenção de projeto.

## Por que este documento existe

Em 19/11 o autor notou que a home e a lista de espera (`/lista-de-espera`, `UI-14`) usavam
fontes diferentes. As duas declaravam a mesma lista, `Inter, ui-sans-serif, system-ui, …`,
e o resultado divergia:

- **A home nunca baixou a Inter.** Sem `@font-face` nem link de fonte, o navegador caía na
  fonte do sistema. No Windows, a Segoe UI: a largura medida do texto é a da Segoe (1 030 px),
  e não a da Inter (931 px).
- **O app baixa a Inter do Google Fonts** (`src/styles/fonts.css`), só nos pesos 400 e 500.
  A lista de espera saía em Inter, e o título de peso 850, com negrito sintetizado.

A mesma declaração dava fontes diferentes conforme a página e o aparelho. Também havia dois
defeitos de peso na lista: os botões do formulário saíam em 400, e as caixas de confirmação
em 500.

## 1. Fonte

**A fonte do sistema, e nenhuma fonte baixada.**

```css
font: 14px/1.5 ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
```

- No Windows, sai a Segoe UI; no Mac e no iPhone, a San Francisco; no Android, a Roboto.
- **Nenhuma página pública cita a Inter**, nem outra fonte que ela não carregue. Fonte
  declarada e não carregada é a origem do problema acima: o resultado depende do que a
  pessoa tem instalado.
- **A exceção é o celular desenhado na landing** (`font: 12px/1.5 -apple-system, …`). Ele
  imita a interface do aparelho e não é texto da página.
- `src/padraoVisual.test.ts` reprova se a lista de fontes da lista de espera divergir da
  landing, ou se qualquer uma das duas citar a Inter.

## 2. Pesos

| Peso | Uso |
|---:|---|
| 400 | Texto corrido, notas, rótulos de campo, texto das caixas de confirmação |
| 650 | Links de navegação do cabeçalho |
| 700 | Números em destaque (a linha de três números do topo) |
| 750 | Títulos de seção |
| 800 | Botões, pílulas e rótulos curtos em maiúsculas |
| 850 | O título principal, o selo do topo e as sobrelinhas |

Peso de botão é sempre 800. **Nenhuma regra genérica** (`button { font: inherit }`, a base
de `label` do app) **pode vencer o peso de um componente**: o reset vai dentro de `:where(...)`,
que não tem especificidade.

## 3. Escala de tipos (medida na home, 1280 px)

| Elemento | Tamanho | Peso | Entre letras | Altura de linha | Classe na home | Classe na lista |
|---|---:|---:|---:|---:|---|---|
| Título principal | `clamp(42px, 5.2vw, 68px)` (66,6 px a 1280) | 850 | −3,1 px | 1,01 | `.lp-hero h1` | `.le-hero h1` |
| Texto de apoio do topo | 16 px | 400 | normal | 1,78 | `.lp-lead` | `.le-lead` |
| Título de seção | `clamp(28px, 3.5vw, 42px)` | 750 | −1,5 px | 1,12 | `.lp-section-heading h2` | — |
| Navegação | 13 px | 650 | normal | 1,5 | `.public-navlinks a` | — |
| Botão do cabeçalho | 12 px | 800 | normal | 1,5 | `.public-actions .public-btn` | `.le-acoes .le-btn` |
| Botão grande | 13 px | 800 | normal | 1,5 | `.public-btn.large` | `.le-btn.grande` |
| Selo do topo (pílula) | **11 px** ✏️ *(na home desde o `UI-35`; antes, 10)* | 850 | 0,9 px, maiúsculas | — | `.lp-kicker` | `.le-kicker` |
| Sobrelinha | **11 px** ✏️ *(na home desde o `UI-35`; antes, 10)* | 850 | 1,35 px, maiúsculas | — | `.lp-overline` | `.le-sobrelinha` |
| Número em destaque | 17 px | 700 | −0,5 px | 1,5 | `.lp-spec-row strong` | `.le-spec strong` |
| Legenda do número | **12 px** ✏️ *(na home desde o `UI-35`; antes, 10 a 1280 px e 11 em telas menores)* | 400 | normal | 1,5 | `.lp-spec-row span` | `.le-spec span` |
| Nota pequena | **12 px** ✏️ *(na home desde o `UI-35`; antes, 9 e 11)* | 400 | normal | 1,55 | `.lp-spec-note` | `.le-spec-nota` |
| Rodapé | **11,5 px** ✏️ *(na home desde o `UI-35`; antes, 9)* | 400 | normal | 1,5 | `.lp-footer-links a` | `.le-rodape-links a` |

**O tamanho mínimo de texto é 11 px** (decisão do autor, 19/11, opção A). Onde a home usa
menos (rodapé com 9 px, legendas e notas com 10 e 11 px), **a página nova segue o mínimo, e
não a home**. ✏️ *21/11, `UI-35`: a home também segue o mínimo.* Um bloco de estilo próprio, o último da landing (`<style id="ui-35-textos-minimos">`), sobe para 11 px (12 e 11,5 px onde a tabela pede) todo texto da home que saía menor, a 1280 e a 390 px; o `padraoVisual.test.ts` confere o bloco. **Fica de fora o celular desenhado** (`#sd-phone`): é uma ilustração na escala do aparelho, e os textos dele seguem com 7 a 10 px. Texto de consentimento ou
de aviso legal: no mínimo 11,5 px; a caixa de consentimento usa 13 px.

## 4. Cores

- **A paleta é a da landing**, com dois ajustes de contraste medidos em 17/11. O cinza do texto
  passou a dar 5:1 sobre o fundo, e não 3,71:1, abaixo do mínimo de 4,5:1. O azul e o verde
  dos rótulos pequenos ficaram mais escuros no tema claro.
- **Os valores ficam no `frontend/src/styles/theme.css`**, nos tokens `--le-*`, claro e escuro.
  Nenhum outro arquivo do app tem cor crua: o `tema.test.ts` reprova.
- **A landing tem a paleta dela no próprio HTML**, porque vive num iframe isolado e não lê o
  `theme.css`. Mudar uma cor do padrão é mudar nos dois lugares.

## 5. Componentes

| Componente | Raio | Detalhe |
|---|---:|---|
| Botão | 10 px | Primário com fundo azul; contorno com fundo da superfície; sobe 1 px no hover |
| Cartão principal | 19 px | Borda fina e sombra larga e suave |
| Campo de texto | 11 px | Fundo da página; anel azul de 4 px no foco |
| Selo em pílula | 999 px | Ponto verde com halo |
| Caixa de aviso | 16 px | Marca "i" redonda e sobrelinha |

## 6. Movimento

- **Entrada:** blocos que sobem 14 px em sequência, 90 ms entre um e outro.
- **Hover:** elevação de 1 px.
- **Halo e órbitas** no topo.
- **Com `prefers-reduced-motion: reduce`**, nada se move, e a página funciona igual.

## 7. Os ícones: a aba e o app

Duas marcas, cada uma onde se lê. Escolha do autor em 19/11, depois de ver as duas nos
tamanhos reais.

| Onde | Marca | Arquivos em `frontend/public/` | Fonte em `docs/marca/icones/` |
|---|---|---|---|
| **Aba do navegador** (favicon) | O travesseiro com o traçado de movimento, branco sobre o azul da marca, cantos arredondados | `favicon.ico` (16, 32 e 48 px), `favicon-32.png` | `favicon-travesseiro.svg` |
| **App instalado e tela inicial** (PWA, iPhone, prévia de link) | "SMART" sobre "Dormio", empilhados como a marca da Dormio Labs, azul sobre branco | `icone-192.png`, `icone-512.png` | `icone-app.svg` |
| **Ícone recortado do Android** (`maskable`) | A mesma marca empilhada, com margem para o círculo de 80% do sistema | `icone-maskable-512.png` | `icone-app-maskable.svg` |

- **O texto não vai para a aba.** Medido em 19/11: em 16 px a marca empilhada vira uma faixa
  azul sem letra legível, e em 32 px o "SMART" vira pontos.
- **Os ícones do app são quadrados cheios, sem cantos transparentes.** O sistema arredonda
  sozinho, e no iPhone o canto transparente sai preto.
- **A marca empilhada usa os desenhos originais das letras** do `smart-dormio.svg`, sem
  redesenho: "SMART" na altura do "LABS" e o mesmo espaço entre as palavras.
- **Para gerar de novo:** abrir o SVG da fonte no navegador, no tamanho exato de cada arquivo,
  e salvar em PNG. O `.ico` junta os PNGs de 16, 32 e 48 px. Toda página pública declara o
  `.ico` e o PNG de 32 px.
- **O app Android (APK) tem ícones próprios** (`frontend/android/…/mipmap-*`), que não seguem
  esta seção ainda: ver `APP-17` no backlog.

## 8. Como conferir

- `cd frontend && npx vitest run src/padraoVisual.test.ts`. O teste reprova se:
  - a lista de fontes divergir ou citar a Inter;
  - o reset de botão vencer o peso do componente;
  - o peso do botão não for 800, ou o das caixas e rótulos não for 400;
  - o título fugir da escala da home;
  - uma página pública ficar sem favicon, ou ele apontar para um arquivo que não existe;
  - o manifest apontar para ícone que não existe, ou usar o mesmo arquivo como `any` e `maskable`.
- **No navegador:** `getComputedStyle` nos elementos da tabela da seção 3, nas duas páginas e na
  mesma largura.

## 9. Preferência de composição (UI-37)

O autor prefere uma interface sóbria e com identidade própria. Evitar a repetição de pontos
com halo, selos em pílula e cartões arredondados para informações rotineiras. Preferir hierarquia
por tipografia, espaço e divisórias; manter caixas e indicadores quando ajudarem a organizar,
comunicar estado real ou identificar controles. Não apagar a identificação de dados fictícios.

A revisão do `UI-37` reduziu o título do topo em desktop; os valores da seção 3 são as medidas
anteriores de 19/11, preservadas como referência histórica, não medições da versão revisada.

## 10. A linguagem do app (`UI-39`)

Vale para Início, Noite, Histórico, Dispositivos, Coletar e Configurações. O nome técnico continua
no código, no contrato de dados e no CSV.

| Não escrever na tela | Escrever | O que significa |
|---|---|---|
| época, leitura, amostra | **registro** | O que o aparelho grava a cada 30 s (ou no intervalo que ele declara) |
| tempo medido | **tempo registrado** | A soma do que foi medido, sem o que ficou sem registro |
| cobertura | **registrado X de Y** | Tempo registrado dentro do período, do início ao fim |
| leituras com movimento (contagem) | **com movimento: N% do tempo registrado** | Fração de tempo, e não de contagem |
| maior intervalo sem movimento | **maior período sem movimento registrado** | Não atravessa pausa do aparelho |
| com lacunas | **com pausas** | Só quando o aparelho parou (interrupção) |
| com lacunas, sem parada | **incompleta** | Faltou registro, mas o aparelho não parou |
| sem medição | **sem registro** | Não se sabe se houve movimento |
| desvio do repouso, magnitude | **intensidade do movimento** | O desvio absoluto em relação ao repouso |
| limiar | **limite de movimento** | O critério do próprio aparelho |
| token, credencial | **código de conexão** (o aparelho fica "vinculado") | O segredo que o travesseiro usa para enviar |
| sessão de captação | **sessão** | Nunca "noite", no painel e no Histórico, até o `ESC-01` |
| janela | **período** | O intervalo exibido |
| taxa do sensor | **ritmo do sensor** | Medidas por segundo |

- **Nenhum rótulo afirma mais do que a conta:** registro é do aparelho, e não da pessoa. Nada de
  "você se mexeu", sono, qualidade ou diagnóstico.
- **Porcentagem:** "<1%" entre zero e um, ">99%" entre 99 e 100.
- **Termo técnico necessário** fica num bloco "Detalhes técnicos". Aviso de falha, nunca.
- **Não mudam:** o texto do consentimento (pede versão e aceite novos) e os nomes de botão que a
  política de privacidade cita.
- `src/linguagem.test.ts` reprova os termos da primeira coluna nas telas.

### As camadas do Início e da Noite (`UI-40`)

1. **O que está errado**, se algo estiver: pausa, mistura de aparelhos, período incompleto, falta de registro.
2. **O resumo da sessão**, em frases: quando, registrado X de Y, quantas vezes parou, movimento em % do tempo,
   maior período sem movimento registrado. Sem nota e sem interpretação.
3. **O gráfico**, sem número no eixo e com a linha do limite, e o estado do envio.
4. **As sessões anteriores.**
5. **"Detalhes técnicos", recolhido:** fórmula, limite, contagens, amostras e números do sensor.
6. **A nota de escopo**, sempre visível.

Um número técnico que passe a significar falha vira aviso fora dos detalhes.

## O que este documento não cobre

| Lacuna | Por quê |
|---|---|
| **O visual do app depois do login** (a linguagem está na seção 10) | Usa a fonte Outfit (`theme.css`, baixada pelo `fonts.css`) e outra paleta. Alinhar o app a este padrão, ou decidir que ele tem o seu, é o `UI-36`. |
| **A versão leve da landing** (`/?apresentacao=leve`) | É componente do app e herda a fonte e a paleta dele. Entra no `UI-36`. |
| **O celular desenhado na landing** | Imita a interface do aparelho, de propósito. |
| **Outros tamanhos de tela** | A escala foi medida a 1280 px. No celular, as regras `@media` da landing e da lista são as que valem. |
