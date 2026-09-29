# `docs/diagramas/` — as figuras do TCC

Todos os diagramas são **Mermaid em arquivo versionado**, não imagem binária: dá para
revisar em *diff* e regerar. Cada arquivo traz, no topo, o item do backlog a que
corresponde, onde entra no texto do TCC e a data em que foi conferido contra o código.

---

## O mapeamento adotado, e por que ele não é o do backlog linha a linha

O `docs/BACKLOG-COMPLETO.md` define os quatro itens assim:

| Backlog | O que pede |
|---|---|
| `DIAG-01` | Diagrama de blocos da arquitetura |
| `DIAG-02` | Esquemático do circuito; v1 (1 sensor) e v2 (2, endereços I2C) |
| `DIAG-03` | Fluxograma do firmware / máquina de estados |
| `DIAG-04` | Diagrama de sequência do fluxo autenticado + modelo ER |

Essa lista foi levantada em `2026-09-10` e revisada em `22/09` — **antes de o bloco de ML
fechar** (`ML-05` fechou em `28/09`). Ela não prevê figura para o pipeline experimental,
que hoje é o bloco de maior valor acadêmico já executado do trabalho. E o `DIAG-02` é um
**esquemático elétrico**, que Mermaid não desenha (ver abaixo).

Decisão tomada: **preservar a numeração do backlog** — renumerar quebraria as referências
cruzadas no `ROADMAP.md` e no próprio backlog — entregar os três itens que cabem em
Mermaid, acrescentar um `DIAG-05` para o pipeline de ML, e deixar o `DIAG-02` aberto com
uma proposta de ferramenta. O conjunto entregue cobre as quatro frentes exigidas:

| Arquivo | Frente coberta | Item do backlog |
|---|---|---|
| [`DIAG-01-arquitetura.md`](DIAG-01-arquitetura.md) | Arquitetura ponta a ponta: sensor → firmware → API → banco → painel | `DIAG-01`, escopo ampliado |
| [`DIAG-03-firmware-e-fluxo-do-dado.md`](DIAG-03-firmware-e-fluxo-do-dado.md) | Fluxo do dado e os pontos onde ele é transformado (amostra → época de 30 s → features → classificação), mais o laço e a máquina de estados do firmware | `DIAG-03`, escopo ampliado |
| [`DIAG-04-modelo-de-dados-e-seguranca.md`](DIAG-04-modelo-de-dados-e-seguranca.md) | Modelo de dados, RLS e quem acessa o quê com qual privilégio; sequência do fluxo autenticado | `DIAG-04`, escopo ampliado; fecha o resíduo do `DOC-05` |
| [`DIAG-05-pipeline-de-ml.md`](DIAG-05-pipeline-de-ml.md) | Pipeline experimental de ML: datasets, divisão por sujeito, três braços, validação externa | **novo** — sem item no backlog |
| — | Esquemático do circuito v1/v2 | `DIAG-02` — **não entregue**, ver abaixo |

---

## O que cada diagrama mostra, e onde ele entra no texto

### `DIAG-01` — Arquitetura do sistema, ponta a ponta

Uma figura. Blocos reais com nome de arquivo: `firmware/nucleo/`,
`firmware/envio-continuo/envio-continuo.ino`, `web-app/routes.py`, as funções
`security definer` do Postgres, `frontend/src/lib/metricas.ts`. Mostra as duas fontes de
dado (ESP32 e navegador) com credenciais diferentes, e mostra `ml/` **fora** do produto.

**Entra em:** Desenvolvimento, primeira figura. É o mapa que as seções seguintes
referenciam. Também serve à apresentação (`ROTEIRO-APRESENTACAO.md`) como slide único de
visão geral.

### `DIAG-03` — Firmware: laço, política de rede e transformações do dado

Três figuras. (A) o laço de `envio-continuo.ino`, cujo ponto é que o bloco de medição não
depende do bloco de rede; (B) a máquina de estados do backoff de reconexão
(`firmware/nucleo/reconexao.h`); (C) a cadeia de transformação do dado, das duas pontas —
produto e pesquisa — mostrando que hoje elas não se tocam.

**Entra em:** Desenvolvimento, seção de firmware (A e B) e seção de tratamento do dado (C).
A figura C é também a ponte para o capítulo de Metodologia. A figura A é a evidência
visual do `HW-05` e a justificativa do `FW-07`.

### `DIAG-04` — Modelo de dados, sequência autenticada e privilégio

Três figuras. (A) ER com `auth.users`, `profiles`, `devices`, `device_tokens`,
`sleep_data`; (B) papéis × funções × tabelas, que é onde `SEC-06` (papel de ingestão de
privilégio mínimo) e `SEC-07` (direito de eliminação) ficam visíveis; (C) sequência dos
três caminhos autenticados — token de dispositivo, sessão de celular e leitura do painel.

**Entra em:** Desenvolvimento, seção de persistência e segurança (A e B) e seção de
autenticação (C). A figura B sustenta a seção de conformidade com a LGPD e dialoga com
`docs/LGPD-ELIMINACAO.md`.

### `DIAG-05` — Pipeline experimental de ML

Três figuras. (A) do sinal bruto ao JSON de resultado, com a divisão por sujeito e o
bootstrap; (B) os três braços e a matriz de transferência, que é o resultado original do
trabalho; (C) validação externa e a conclusão metodológica.

**Entra em:** Metodologia, seção de procedimento experimental. Deve estar à vista do
leitor durante o capítulo de Resultados (`docs/RESULTADOS-TCC.md`, Y.2 a Y.7) e é a figura
que torna legível a seção X.4 de `docs/LIMITACOES-TCC.md`.

---

## `DIAG-02` — o que não cabe em Mermaid, e a alternativa

**O esquemático do circuito não foi feito aqui, e não deve ser.** Mermaid desenha grafos:
nós, arestas e rótulos. Um esquemático elétrico precisa de símbolos normalizados
(resistor, capacitor de desacoplamento, barramento, terra), de designadores de referência
(`R1`, `U1`, `J1`), de pinagem nomeada em posição fixa no símbolo e de roteamento que
distingue cruzamento de conexão. Forçar isso num `flowchart` produz uma figura que parece
um esquemático e não é — e um esquemático que não é conferível é pior que nenhum, porque
alguém vai montar a partir dele.

Três caminhos, em ordem de preferência:

1. **KiCad** (gratuito, multiplataforma). O `.kicad_sch` é **texto** e versiona em git com
   *diff* legível — atende o mesmo critério que motivou escolher Mermaid. Exporta SVG e
   PDF para o documento. É o que se recomenda para v1 e v2, com as duas variantes como
   duas folhas do mesmo projeto.
2. **`circuitikz`** (LaTeX), se o TCC já for escrito em LaTeX: o esquemático vira fonte no
   próprio documento, versionada junto, sem binário nenhum.
3. **Fritzing**, só se a figura pretendida for a **vista de protoboard** (fios coloridos,
   aparência física) em vez do esquemático — é material de divulgação, não de documento
   técnico, e não substitui o item 1.

**O que precisa estar decidido antes de desenhar:** o `DIAG-02` do backlog pede v1 (um
MPU6050) **e** v2 (dois, em `0x68` e `0x69` via pino `AD0`). A v2 é contingência projetada,
não pivô executado — quem decide é o `VIA-01`, que depende da Etapa 0 (soldar os 8 pinos).
Desenhar as duas folhas hoje é possível e defensável desde que a folha v2 seja rotulada
como projeto, do mesmo modo que as caixas tracejadas dos diagramas desta pasta. O
`HW-01` (revisar o BOM: o que é andaime de simulação e o que é produto — o push button e
o pull-down de 10 kΩ existem por causa do Wokwi) deveria ser resolvido antes, para que o
esquemático não normalize o andaime.

---

## Convenções, e por que elas são assim

O critério é **legibilidade impressa em preto e branco, numa página A4**. Daí:

| Aparência | Significado |
|---|---|
| Caixa de traço contínuo | Existe no código de hoje e roda |
| Caixa de traço tracejado + rótulo `(FUTURO)` | Projetado, não implementado; o item do backlog está no rótulo |
| Caixa contínua + `(NÃO EXERCITADO)` | O código existe, mas nunca rodou no cenário que o justifica |
| Seta cheia `-->` | Fluxo que acontece hoje |
| Seta tracejada `-.->` | Fluxo projetado, ou caminho de exceção |

**Nenhuma informação depende de cor.** O traço tracejado é um reforço visual; quem carrega
a informação é o texto do rótulo. Um diagrama impresso em escala de cinza, ou lido por
alguém com deficiência de visão de cores, não perde nada. Por isso também não há
`style ... fill:#...` em nenhum arquivo: a única `classDef` usada é `stroke-dasharray`.

**Sobre acentuação dentro dos diagramas.** Os rótulos Mermaid estão sem acento de
propósito. Os renderizadores variam no tratamento de caracteres não-ASCII dentro de
rótulos entre aspas, e um acento perdido no PDF final é pior que a ausência dele. Todo o
texto **fora** dos blocos — títulos, notas, tabelas — está em português acentuado normal.

---

## Como gerar as imagens para o documento

```bash
# PDF vetorial (preferível: escala sem perder nitidez no A4)
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/DIAG-01-arquitetura.md -o DIAG-01.pdf

# PNG em alta resolução, se o editor do documento não aceitar PDF
npx -y @mermaid-js/mermaid-cli -i docs/diagramas/DIAG-01-arquitetura.md -o DIAG-01.png -s 3
```

Arquivo com mais de um bloco `mermaid` gera `DIAG-03-1.pdf`, `DIAG-03-2.pdf` e assim por
diante, na ordem em que aparecem. **Não versione as imagens geradas** — a fonte é o `.md`.

Para conferir rapidamente sem instalar nada: o GitHub renderiza blocos ` ```mermaid ` no
próprio arquivo, e <https://mermaid.live> aceita colar o bloco.

---

## Regra de manutenção

Todo diagrama desta pasta afirma coisas sobre o sistema. **Se a afirmação deixar de ser
verdadeira no código, o diagrama está errado, não desatualizado** — e um diagrama errado
na banca custa mais que um diagrama ausente. Ao fechar qualquer destes itens, revisar a
figura correspondente e atualizar a data de conferência no topo do arquivo:

| Item aberto | Diagrama afetado |
|---|---|
| `FW-07` (reescrita do `sketch.ino`) | `DIAG-01`, `DIAG-03` |
| `API-03` (endpoint de lote) | `DIAG-01`, `DIAG-03`, `DIAG-04` |
| `DATA-07` (8 features no contrato) | `DIAG-03`, `DIAG-04` |
| `DATA-03` (backfill do dono) | `DIAG-04` |
| `DATA-06` (limiar por dispositivo) | `DIAG-03` |
| `UI-10` (tela de exclusão de conta) | `DIAG-04` |
| `ML-06a`/`ML-06b` (segunda coorte externa) | `DIAG-05` |
| `VIA-01` (bancada: v1 basta, ou aciona v2?) | `DIAG-02` quando ele existir |
| Etapa 0 (solda) + `VAL-02` (noite real) | `DIAG-01` (nota 5), `DIAG-05` (nota 1) |
