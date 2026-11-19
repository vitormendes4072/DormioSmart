# Padrão visual das páginas públicas — Smart Dormio

> **Criado em 2026-11-19 (`UI-34`).** Antes de criar ou mudar uma página pública, ler este
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
| Selo do topo (pílula) | 10 px na home · **11 px** no padrão | 850 | 0,9 px, maiúsculas | — | `.lp-kicker` | `.le-kicker` |
| Sobrelinha | 10 px na home · **11 px** no padrão | 850 | 1,35 px, maiúsculas | — | `.lp-overline` | `.le-sobrelinha` |
| Número em destaque | 17 px | 700 | −0,5 px | 1,5 | `.lp-spec-row strong` | `.le-spec strong` |
| Legenda do número | 11 px na home · **12 px** no padrão | 400 | normal | 1,5 | `.lp-spec-row span` | `.le-spec span` |
| Nota pequena | 11 px na home · **12 px** no padrão | 400 | normal | 1,55 | `.lp-spec-note` | `.le-spec-nota` |
| Rodapé | 9 px na home · **11,5 px** no padrão | 400 | normal | 1,5 | `.lp-footer-links a` | `.le-rodape-links a` |

**O tamanho mínimo de texto é 11 px** (decisão do autor, 19/11, opção A). Onde a home usa
menos (rodapé com 9 px, legendas e notas com 10 e 11 px), **a página nova segue o mínimo, e
não a home**. Subir os textos pequenos da própria home é o `UI-35`. Texto de consentimento ou
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

## 7. Como conferir

- `cd frontend && npx vitest run src/padraoVisual.test.ts`. O teste reprova se:
  - a lista de fontes divergir ou citar a Inter;
  - o reset de botão vencer o peso do componente;
  - o peso do botão não for 800, ou o das caixas e rótulos não for 400;
  - o título fugir da escala da home.
- **No navegador:** `getComputedStyle` nos elementos da tabela da seção 3, nas duas páginas e na
  mesma largura.

## O que este documento não cobre

| Lacuna | Por quê |
|---|---|
| **O app depois do login** | Usa a fonte Outfit (`theme.css`, baixada pelo `fonts.css`) e outra paleta. Alinhar o app a este padrão, ou decidir que ele tem o seu, é o `UI-36`. |
| **A versão leve da landing** (`/?apresentacao=leve`) | É componente do app e herda a fonte e a paleta dele. Entra no `UI-36`. |
| **O celular desenhado na landing** | Imita a interface do aparelho, de propósito. |
| **Outros tamanhos de tela** | A escala foi medida a 1280 px. No celular, as regras `@media` da landing e da lista são as que valem. |
