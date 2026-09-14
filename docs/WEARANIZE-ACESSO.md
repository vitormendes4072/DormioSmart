# Wearanize+ — como obter acesso ao dataset

> **Pesquisa feita em 2026-09-14. Verificação no arquivo feita em 2026-09-14 (2ª rodada).**
> Todas as afirmações abaixo têm a fonte colada ao lado. O que **não** foi possível confirmar
> está marcado com ⛔ e dito como tal — não foi inferido.
>
> Complementa o `docs/ML-DATASETS-E-PLANO.md` §3 (Wearanize+) e **corrige coisas** que aquele
> documento afirmava. Ver o §0 e o §6.
>
> ## 🔴 VEREDITO: o DUA SAI do caminho crítico do TCC
>
> **Verificado abrindo os arquivos, não inferido.** Foram lidos os 100 `channels.tsv` da
> coleção aberta (100/100 baixados sem autenticação, zero falhas) e o cabeçalho EDF completo
> de `sub-005`. O experimento `ML-03` inteiro — treinar em pulso, testar em cabeça, medir Δκ —
> **roda com N = 92 na coleção aberta, sob CC-BY-4.0, sem cadastro e sem espera.**
>
> O DUA destrava **exclusivamente os questionários** (PSQI, MADRE, PHQ-9). Nada mais.

---

## §0. A coleção aberta, verificada arquivo por arquivo

O `ML-DATASETS-E-PLANO.md` §3 dizia que o Wearanize+ tem "acesso em duas partes: a coleção
*Wearanize+ OA* é aberta e baixa direto; a completa exige assinar um DUA". **A frase está
certa, mas subestimava brutalmente o que a parte aberta contém** — e a versão aberta é, em
três aspectos, *melhor* que a restrita.

| | **Wearanize+ OA** (aberta) | **Wearanize+** (restrita) |
|---|---|---|
| DOI | `10.34973/xrmf-5726` | `10.34973/j6jf-9e62` |
| Nível de acesso | ✅ **Open access** (`filesOpenAccess: true`) | 🔒 **Restricted access** |
| Licença / DUA | ✅ **CC-BY-4.0** | 🔒 `RUMC-RA-DUA-1.0` (template) |
| Participantes — versão `raw` | ✅ **130** *(conferido: 130 diretórios `Sub001s1`…`Sub130s1`)* | 130 |
| Participantes — versão `PlugNPlay` | ✅ **100** *(conferido: 100 linhas em `participants.tsv`)* | 100 |
| Acelerômetro Zmax (**cabeça**) | ✅ **100/100** *(lido no `channels.tsv` de cada um)* | ✅ |
| Acelerômetro Empatica E4 (**pulso**) | ✅ **92/100** *(idem)* | ⛔ não verificável |
| Acelerômetro ActivPAL (coxa) | ✅ **93/100** *(idem)* | ⛔ não verificável |
| PSG pontuada manualmente | ✅ **dois pontuadores** (`Scor1` 100/100 · `Scor2` **96**/100, contado no EDF) | ⚠️ **um só** |
| PSG por USleep v2.0 | ✅ 96/100 | ✅ |
| Postura corporal (`PSG_Pos.`) | ✅ 96/100 | ⛔ não verificável |
| Questionários (PSQI, MADRE, PHQ-9) | ❌ **não inclui** | ✅ **inclui — é o único motivo do DUA** |
| Unidade do acelerômetro E4 | ✅ **`g/64`** (correta, lida no arquivo) | 🔴 **`g/16`** (errada por fator 4 — §6) |
| Granularidade de download | ✅ **por arquivo**, um EDF por sujeito | ❌ **3 zips monolíticos** de 33–51 GB |
| Tamanho | 138,8 GB total · 1 594 arquivos | 120,9 GB · 3 arquivos |
| Botão "Request access" | ❌ não existe | ✅ existe |

### §0.1 · Os N que importam para o `ML-03`

Contados na interseção real dos canais presentes, sujeito a sujeito:

| Experimento | N disponível |
|---|:---:|
| **Treina pulso → testa cabeça** (a célula do `ML-03`) | **92** |
| Idem, restrito a quem tem as **duas** pontuações manuais | **90** |
| Matriz 3×3 completa (cabeça, pulso, coxa) | **86** |
| Idem, com as duas pontuações manuais | **84** |

> **Para comparar:** Newcastle 2015 tem N=28 e Walch 2019 tem N=31. A coleção **aberta** do
> Wearanize+ entrega **92 sujeitos** para o experimento que é a contribuição original do
> trabalho — mais que as duas outras bases somadas, e a única com sensor na cabeça.

**Quem fica de fora, e por quê** *(listas completas, não amostras)*:

- **Sem Empatica (8):** `sub-001`, `sub-002`, `sub-004`, `sub-063`, `sub-064`, `sub-100`,
  `sub-129`, `sub-130`
- **Sem ActivPAL (7):** `sub-004`, `sub-072`, `sub-075`, `sub-076`, `sub-095`, `sub-096`,
  `sub-106`
- **Sem 2ª pontuação manual, sem `PSG_Pos.` e sem USleep (4):** `sub-115`, `sub-124`,
  `sub-129`, `sub-130` — **exatamente os quatro gravados com Mentalab** em vez de SOMNOscreen.
  Os três conjuntos coincidem perfeitamente, o que confirma a causa.

**Recomendação:** baixar a OA e começar. Pedir o DUA só se os questionários virarem parte da
análise — e sabendo que o processo é o do §3, que é pesado e leva meses.

**Link da coleção aberta:** <https://data.ru.nl/collections/di/dcmn/DSC_wrnzpoa_t0000925a_195>

---

## §1. O caminho fácil: baixar a Wearanize+ OA (sem DUA, sem cadastro)

### §1.1 · Como baixar só o que interessa, e não 138 GB

O detalhe que salva a banda: a coleção OA está organizada em **EEG-BIDS, um diretório por
participante**, e cada arquivo é baixável individualmente (`downloadAccess: true` em cada um).
Não é um zip monolítico como a coleção restrita.

```
Wearanize+_OA_PlugNPlay_v1.1/
├── derivatives/
├── sub-001/
│   └── eeg/
│       ├── sub-001_task-sleep_eeg.edf        ← ~342 MB (todos os canais da noite)
│       ├── sub-001_task-sleep_channels.tsv   ← 3,3 KB (lista de canais)
│       ├── sub-001_task-sleep_channels.json
│       └── sub-001_task-sleep_eeg.json
├── sub-002/
├── ...                                       (exatamente 100 diretórios sub-*)
├── participants.tsv                          ← id, idade, sexo, lateralidade (BIDS)
├── participants.json
├── dataset_description.json
└── README.txt
```

**Tamanho real dos EDFs, medido** (20 sujeitos amostrados por requisição de faixa):
média **486 MB**, mínimo 285 MB, máximo 553 MB. Portanto:

| Alvo | Volume |
|---|---|
| Piloto de 10 sujeitos | **~5 GB** |
| Piloto de 20 sujeitos | ~10 GB |
| Os 92 do experimento pulso→cabeça | **~45 GB** |
| Os 100 do PlugNPlay | ~49 GB |

As versões `raw` e `Parquet` existem em paralelo e não são necessárias — **use a PlugNPlay**,
que é a sincronizada e truncada. *(A `raw` só interessa se você quiser os 30 participantes
extras que não têm Zmax ou pontuação manual, ou os arquivos de pontuação avulsos.)*

> ✅ **Conferido na listagem (2026-09-14):** exatamente **100** diretórios `sub-*` no
> PlugNPlay e **130** no `raw` (`Sub001s1`…`Sub130s1`). E há `participants.tsv` no padrão
> BIDS, com `age`, `gender` e `handedness` — metadados que o `ML-DATASETS-E-PLANO.md` não
> previa ter.

### §1.2 · Três formas de baixar

| Via | Quando usar | Como |
|---|---|---|
| **Portal web** | Poucos arquivos | Aba *Files* → ícone de download por arquivo/pasta |
| **WebDAV anônimo** ✅ **testado** | Recomendado para volume | Servidor `webdav.data.ru.nl`, porta 443, **Anonymous Login**. Caminho: `/dcmn/DSC_wrnzpoa_t0000925a_195_v1`. Cliente sugerido: Cyberduck |
| **repocli** (linha de comando) | Batch / script | ⚠️ **Não funciona anônimo** — exige perfil RDR e *data access credentials* |

> ✅ **Teste ponta a ponta feito em 2026-09-14, sem cadastro, sem login, sem cookie de sessão:**
>
> | O que foi testado | Resultado |
> |---|---|
> | 100 `channels.tsv` (um por sujeito) | **HTTP 200 nos 100. Zero falhas.** |
> | `participants.tsv` | HTTP 200 |
> | `PROPFIND` de diretórios (listagem WebDAV) | **HTTP 207** |
> | `sub-005_task-sleep_eeg.edf` (**480 MB**), requisição de faixa `bytes=0-24575` | **HTTP 206 Partial Content** — cabeçalho EDF lido e decodificado |
>
> **Os arquivos grandes de dados também são abertos**, não só a documentação. E o servidor
> aceita *range requests* — ou seja, **download retomável**, o que importa para 45 GB.
>
> ⚠️ Um detalhe que custou tempo e vale registrar: o endpoint do **portal**
> (`/api/collectionfiles/.../files/download?path=…`) **não respondeu** sem sessão iniciada.
> **O caminho que funciona anônimo é o WebDAV**, não a API do portal. Se o download pelo
> navegador travar, é isso.

> ⚠️ Cliente WebDAV inativo por 2 h é desconectado pelo servidor. Para 45 GB, use script com
> retomada — e o servidor suporta (HTTP 206 confirmado acima).

Fonte: [Downloading collection content](https://rdr.tutorials.ru.nl/a/1946519-downloading-collection-content).

### §1.2b · Os canais, exatamente como estão no arquivo

Lido de `sub-005_task-sleep_channels.tsv` e confirmado no cabeçalho EDF do mesmo sujeito.
**As colunas do `.tsv` são:** `name`, `type`, `units`, `sampling_frequency`, `max_val`,
`min_val`, `duration`, `description`.

| Canal | `type` | `units` | `sampling_frequency` | Dispositivo (campo `description`) |
|---|---|---|:---:|---|
| `Zmax_ACCX` / `ACCY` / `ACCZ` | `ACCEL` | **`g`** | **256.0** | Zmax (Hypnodyne) — **cabeça** |
| `Emp_ACCX` / `ACCY` / `ACCZ` | `ACCEL` | **`g/64`** | **32.0** | Empatica E4 (Empatica) — **pulso** |
| `ActivPal_ACCX` / `ACCY` / `ACCZ` | `ACCEL` | **`g`** | **20.0** | ActivPAL (PAL Technologies) — **coxa** |
| `PSG_Manual_scor1` | `MISC` | `Unitless` | **0,03333 (= 1/30 Hz)** | SOMNOscreen |
| `PSG_Manual_scor2` | `MISC` | `Unitless` | **1/30 Hz** | SOMNOscreen |
| `PSG_USleep_score` | `MISC` | `Unitless` | **1/30 Hz** | SOMNOscreen |
| `PSG_Pos.` | `POS` | `position` | **4.0** | SOMNOscreen — postura |
| `PSG_Move.` | `ACCEL` | `mg` | **128.0** ⚠️ | SOMNOscreen |

Os três canais de pontuação têm `min_val = -1` e `max_val = 4`, batendo com o mapa de rótulos
(`-1` não-pontuável … `4` REM).

> 🔴 **Armadilha de nomenclatura — vai quebrar seu código se você não souber.**
> O nome do canal **difere entre o `channels.tsv` e o EDF**:
>
> | `channels.tsv` | dentro do EDF |
> |---|---|
> | `PSG_Manual_scor1` | **`PSG_Manual_Scor1`** (S maiúsculo) |
> | `PSG_Manual_scor2` | **`PSG_Manual_Scor2`** (S maiúsculo) |
>
> **Case-insensitive matching, ou o rótulo some.** O EDF de `sub-005` tem **48 canais**,
> incluindo um `EDF Annotations` ao final (formato EDF+).

> ⚠️ **Discrepância com o README oficial, verificada em 12 sujeitos:** a tabela de canais do
> README declara `PSG_Move.` a **4 Hz**. No arquivo ele está a **128 Hz** em 12/12 sujeitos
> conferidos. *(A taxa de 4 Hz do README bate com `PSG_Pos.`, que de fato é 4 Hz — parece
> troca de linha na tabela.)* **Confie no `channels.tsv`, não no README.**

### §1.2c · A estrutura do EDF já é epocada em 30 s — e isso é um presente

Do cabeçalho EDF de `sub-005`:

```
número de registros de dados : 974
duração de cada registro     : 30 s          ← EXATAMENTE a época da PSG
974 × 30 s                   = 29 220 s      ← bate com o campo duration do channels.tsv
```

Amostras por registro, por canal:

| Canal | amostras / registro de 30 s | ⇒ taxa |
|---|:---:|:---:|
| `Zmax_ACC*` | **7 680** | 256 Hz ✓ |
| `Emp_ACC*` | **960** | 32 Hz ✓ |
| `ActivPal_ACC*` | **600** | 20 Hz ✓ |
| `PSG_Manual_Scor1` / `Scor2` / `USleep_score` | **1** | 1 rótulo por época ✓ |
| `PSG_Pos.` | 120 | 4 Hz ✓ |

> **O janelamento de 30 s do §7 do `ML-DATASETS-E-PLANO.md` já vem pronto na estrutura do
> arquivo.** Um registro EDF = uma época = um rótulo. Não há alinhamento a fazer, não há
> *off-by-one* a depurar. Isso elimina a classe de bug mais comum deste tipo de pipeline.

### §1.3 · O que a licença CC-BY-4.0 da OA obriga

**CC-BY-4.0 é permissiva.** Para um TCC, o que ela exige é **atribuição** — e só. Ela
permite explicitamente redistribuir, adaptar, e usar comercialmente.

**Mas há duas condições declaradas pelos autores que vão além da licença**, na descrição
da própria coleção e no README do GitHub, e que valem para a OA também:

> "both the Wearanize+ and Wearanize+ OA datasets **may only be used for scientific research
> purposes**. By using either dataset, you agree that **you will not attempt to identify any
> participant**."
> — descrição da coleção OA no RDR, e `README.md` do repositório oficial

⚠️ **Note a tensão:** CC-BY-4.0 não restringe a uso científico; a frase dos autores restringe.
Na prática, para um TCC isso é irrelevante — é uso científico e você não vai tentar
reidentificar ninguém. Mas **não redistribua o dataset** (por exemplo, subindo os EDFs para o
GitHub do projeto) sem antes resolver essa contradição com os autores.

**Citação obrigatória** (explícita no README e na descrição da coleção — vale mesmo usando só
a OA):

1. **O artigo de referência:** Sikder, N., Verkaar, L., Paltarzhytskaya, A., Acan, S., Bovy, L.,
   Almazova, T., Krugliakova, E., Rosenblum, Y., Krauledat, M., Dresler, M., & Zerr, P. (2026).
   *Wearanize+: a multimodal dataset for evaluating wearable technologies in sleep research.*
   SLEEP Advances, 7(1), zpaf094. <https://doi.org/10.1093/sleepadvances/zpaf094>
2. **O dataset primário** (`10.34973/j6jf-9e62`) — **mesmo usando a OA.** O README é explícito:
   *"Even if you use data from Wearanize+ OA (the open-access collection), please cite the
   primary dataset mentioned above for consistency."*
3. Se usar os scripts do GitHub: `10.5281/zenodo.14892764`.

**As duas entradas BibTeX prontas estão no README oficial** — copiar de lá, não redigitar.

---

## §2. Antes de qualquer coisa: criar o ORCID

**Sim, o ORCID é exigido** para a via restrita. As instruções oficiais dos autores são
explícitas:

> "Create an [ORCID account](https://orcid.org/) using **the same email address you provided
> in the DUA**. If you use an existing ORCID account, please include the intended email
> address and **make it visible**."
> — `README.md`, seção *Access Instructions*

E a ajuda do RDR acrescenta o detalhe técnico que quebra o login se for ignorado:

> "If you use your ORCID account to log in, you must allow **'trusted parties' (at least)** to
> be able to see your **email address and name**."
> — [Accessing a collection](https://rdr.tutorials.ru.nl/a/1946517-accessing-a-collection)

**Checklist do ORCID:**

- [ ] Conta em <https://orcid.org/> com o **mesmo e-mail** que vai no DUA
- [ ] Visibilidade do **e-mail** = "Trusted parties" ou "Everyone"
- [ ] Visibilidade do **nome** = idem
- [ ] Anotar o ORCID iD (formato `0000-0000-0000-0000`)

> 📌 O login do RDR oferece três vias: **SURFconext** (federação holandesa — não serve),
> **ORCID**, e **eduID**. Para quem está fora da Holanda, ORCID é a via indicada pelos
> autores. *(Confirmado na tela de login do RDR, 2026-09-14.)*
>
> **Criar a conta ORCID é você quem faz** — eu não crio contas nem preencho credenciais.

---

## §3. O caminho difícil: o DUA da coleção restrita

Só siga este caminho se os **questionários** (PSQI, MADRE, PHQ-9) forem realmente
necessários. Para o `ML-03`, não são.

### §3.1 · A ordem correta dos passos

Os autores publicaram a sequência exata, e ela **não** é a genérica do RDR — o DUA vai por
e-mail *antes*, e o clique no portal é só registro:

1. **Baixar o template de DUA correto** (do repositório oficial no GitHub, pasta `DUA_forms/`):
   - **Para o Brasil → `DTA_Wearanize_nonEU_v1.docx`** (a versão "outside the EEA", 242 KB)
   - *(A versão `Wearanize+_Radboudumc_DUA_v2.0.docx` é para países do EEE — **não é a sua**)*
2. **Preencher** a seção de informações do recebedor e **descrever claramente o plano de
   pesquisa** → é exatamente o arquivo `docs/WEARANIZE-PLANO-PESQUISA.md` deste repositório.
3. **Enviar o formulário preenchido por e-mail** para **Dr. Martin Dresler**
   — `martin.dresler@donders.ru.nl`
4. **Criar/ajustar o ORCID** (§2), com o mesmo e-mail do DUA.
5. Abrir a [coleção restrita](https://data.ru.nl/collections/di/dcmn/DSC_wearanize_t0000657a_579)
   e **fazer login via ORCID**.
6. Clicar em **"Request access"**. Isso registra as credenciais no RDR — *não* é o pedido em si.
7. Se mais alguém (orientador, colega) precisar de acesso sob o mesmo DUA, **cada pessoa faz o
   próprio "Request access" com o próprio ORCID**.

Fonte: `README.md` do [repositório oficial](https://github.com/Niloy333/Wearanize_plus),
seção *Access Instructions → Wearanize+ (primary/original dataset, restricted access)*.

### §3.2 · O que o formulário de "Request access" do portal pede

A ajuda do RDR manda preparar isto **antes** de clicar:

> "Make sure you know **the organisation and position within that organisation for each
> person** who wants to gain access to the data. Prepare to provide information on the
> **project type, project partners, project title and project description (including
> background, research question, planned methods, relevance of requested data, and intended
> deliverables)**."
> — [Accessing a collection](https://rdr.tutorials.ru.nl/a/1946517-accessing-a-collection), passo 2

Tudo isso está coberto pelo rascunho em `docs/WEARANIZE-PLANO-PESQUISA.md`.

⛔ **Não confirmado:** os **rótulos exatos dos campos** do formulário. A tela de pedido só
aparece **depois do login**, e eu não crio contas nem faço login em nome de ninguém. A lista
acima é a descrição oficial do que o formulário pede, não uma cópia da tela.

### §3.3 · Quem precisa assinar — e a resposta é: não é você sozinho

Esta é a parte que mais atrasa, e é preciso entendê-la antes de começar.

**O DUA não é um clique de aceite. É um contrato entre duas instituições.** O template
`RUMC-RA-DUA-1.0`, cujo texto integral está aberto em <https://data.ru.nl/dua/RUMC-RA-DUA-1.0>,
é celebrado entre:

- **PROVIDER:** Stichting Radboud universitair medisch centrum, *"legally represented by the
  undersigned"*
- **RECIPIENT:** `<a sua instituição>`, *"having its principal office at …, **legally
  represented by the undersigned**"*

E há dois papéis distintos do lado do recebedor:

| Papel | Quem é | O que faz |
|---|---|---|
| **RECIPIENT** | A **instituição** (sua faculdade/universidade) | Assina o contrato por representante legal autorizado |
| **RECIPIENT SCIENTIST** | **Você** | Assina "READ AND ACKNOWLEDGED" — reconhece, não contrata |

A cláusula 18 fecha a questão:

> "Both Parties acknowledge that **the signatories to this Agreement are authorized
> representatives** of each of the Parties and **legally authorized to sign** this Agreement."

**Portanto: sim, exige assinatura institucional.** Um aluno de graduação não é representante
legal da instituição. Você precisa de:

- [ ] **Orientador** a bordo — como RECIPIENT SCIENTIST ou co-signatário científico
- [ ] Alguém com **poder de assinatura institucional** — coordenação de curso, pró-reitoria de
      pesquisa, ou o setor jurídico. *Quem exatamente depende da sua instituição.*

> Do lado holandês o paralelo é explícito: o RDR determina que, na Radboud University, quem
> assina é o **diretor de pesquisa** — não o pesquisador.
> — [Restricted access - access requests](https://rdr.tutorials.ru.nl/a/1945343-restricted-access-access-requests), passo 4

⚠️ **Comece a conversa com o orientador e com a coordenação AGORA, não quando o DUA chegar.**
Em faculdade brasileira, descobrir quem assina um contrato internacional de dados leva
semanas. Este é o gargalo real — não o lado holandês.

### §3.4 · A questão da transferência internacional (e a boa notícia de 2026)

O RDR tem uma regra dura para transferências fora da Europa:

> "If you want to share data with a party **outside of the European Union or countries that
> offer an adequate level of data protection** according to the European Union …, you **cannot
> use a standard DUA (nor the RDR templates)**. Instead, you must make **specific agreements**
> with the data access applicant."
> — [Restricted access - access requests](https://rdr.tutorials.ru.nl/a/1945343-restricted-access-access-requests), passo 3

Isso **seria** um bloqueio grave para um recebedor brasileiro. Só que:

> ✅ **A Comissão Europeia adotou a decisão de adequação para o Brasil em 26 de janeiro de
> 2026.** O Brasil consta hoje na lista oficial de países reconhecidos como oferecendo nível
> adequado de proteção de dados.
> — [Adequacy decisions, Comissão Europeia](https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en)
> (documento *"Adequacy Decision for Brazil"*, 26 JAN 2026)

**Consequência:** a restrição acima, lida literalmente, **não se aplica mais ao Brasil** — o
país está entre os "countries that offer an adequate level of data protection".

> ⚠️ **Duas ressalvas honestas, e importam:**
>
> 1. **A decisão é recente.** Vale a pena mencioná-la no e-mail ao Dr. Dresler, com o link,
>    porque o pessoal do RDR pode não ter atualizado o procedimento interno.
> 2. **Os autores separam por EEE, não por adequação.** O README oferece um template
>    específico *"outside the EEA"* — e o Brasil, mesmo com adequação, **não é** do EEE.
>    Então o caminho continua sendo o `DTA_Wearanize_nonEU_v1.docx`. A adequação torna o
>    processo *possível e mais simples*; não o dispensa.
>
> ⛔ **Não confirmado:** o **conteúdo** do `DTA_Wearanize_nonEU_v1.docx`. É um `.docx` de
> 242 KB (contra 29 KB da versão EEE — o tamanho sugere anexos, provavelmente as Cláusulas
> Contratuais-Padrão da UE), e eu não consegui ler o texto dele. **Abra o arquivo e confira**
> os pontos do §4 diretamente nele; o que está no §4 vem do template `RUMC-RA-DUA-1.0`, que
> é o referenciado nos metadados da coleção, e pode diferir do não-EEE.

### §3.5 · Prazo de resposta

⛔ **Não confirmado — e provavelmente não existe.** Procurei em: página da coleção, ajuda do
RDR (*Accessing a collection*, *Restricted access - access requests*), Policies & Guidelines,
e o README oficial. **Nenhum documento publica um prazo, um SLA ou um tempo médio de resposta
para pedidos de acesso restrito.**

O que dá para dizer com base no processo documentado, e é estimativa declarada como tal:

| Etapa | Quem depende | Ordem de grandeza *(estimativa minha, não publicada)* |
|---|---|---|
| Avaliação do pedido pelo gestor da coleção | Dr. Dresler | dias a semanas |
| Consulta ao *data steward* do instituto | RDR/Donders | dias |
| Preparação do DUA específico + jurídico | jurídico de **ambos** os lados | **semanas** |
| Assinatura pelos representantes legais | ambos | **semanas** |
| Concessão do acesso no portal | Dr. Dresler | imediato, após assinatura |

O RDR é explícito em que **cada pedido gera um DUA próprio** ("the selected DUA … is a
**template**; there is **no one-size-fits-all** DUA for these collection types") e que ele
passa por revisão jurídica. **Isso não é rápido em lugar nenhum.** Para um TCC com prazo,
planeje meses, não semanas — e é exatamente por isso que o §0 recomenda começar pela OA.

> 📌 Um sinal indireto de que o processo funciona: a coleção restrita registra **43
> *downloaders*** e 58 downloads desde a publicação (18/12/2025) — ou seja, pedidos vêm sendo
> aprovados. *(Contadores lidos nos metadados da coleção em 2026-09-14.)*

---

## §4. As restrições de uso que afetam um TCC, cláusula por cláusula

Base: texto integral do `RUMC-RA-DUA-1.0` em <https://data.ru.nl/dua/RUMC-RA-DUA-1.0>.
**Aplica-se apenas à coleção restrita.** A OA é CC-BY-4.0 (§1.3).

### §4.1 · Os dados podem aparecer em figuras da monografia?

**Sim — mas há um passo obrigatório antes de publicar, e ele tem prazo.**

A cláusula 12(b) cria um direito de revisão prévia:

> "**At least thirty (30) days before** RECIPIENT submits a paper or abstract for Disclosure,
> RECIPIENT shall provide such paper or abstract to PROVIDER, who will have **thirty (30) days
> to review proposed manuscripts** and fifteen (15) days to review proposed abstracts to
> assure that its CONFIDENTIAL INFORMATION is protected."

O objeto da revisão é **proteger a informação confidencial do PROVIDER**, não censurar
resultado. Na prática: eles conferem se você não vazou método ou dado não publicado deles.

⛔ **Não confirmado: se uma monografia de TCC conta como "paper … for Disclosure".** O texto
fala em *paper*, *abstract* e *press release*. Uma monografia depositada em repositório
institucional é, em substância, divulgação pública. **Pergunte isso explicitamente no e-mail
ao Dr. Dresler** — é uma pergunta de uma linha e resolve um risco de cronograma de 30 dias.

**Não há nenhuma cláusula proibindo figuras.** Gráficos agregados (matriz de confusão,
Bland-Altman, kappa por sujeito) são resultados derivados, não os dados. O que a cláusula 3
proíbe é procedimento que permita derivar a identidade do participante:

> "RECIPIENT shall **not carry out any procedures with the DATA, such as linking, comparison,
> processing, with which the identity of the Subject could be derived**."

> ⚠️ **Regra prática:** figura de resultado agregado, sem problema. Plotar o traçado bruto de
> uma noite de um participante nomeado (`sub-047`) é menos óbvio — é dado pseudonimizado
> exibido inteiro. Se for fazer, use rótulo genérico ("participante exemplo") e mencione no
> pedido de revisão.

### §4.2 · Há citação obrigatória?

**Sim, e é dupla.**

1. **Pelo DUA, cláusula 12(c)** — obrigação contratual:
   > "In every Disclosure by RECIPIENT based upon results obtained from the research through
   > the help of the received DATA provided by PROVIDER, RECIPIENT shall **appropriately
   > acknowledge PROVIDER and PROVIDER'S SCIENTIST as contributor of the DATA**."

   Ou seja: **agradecimento nominal** ao Radboudumc e ao cientista responsável, além da citação.

2. **Pelos autores** — citar o artigo + o dataset primário, BibTeX no README (§1.3).

3. **Pela política do RDR** — a Repository Policy exige que usuários citem qualquer dado usado
   de coleções do RDR.

**Também vale ler a cláusula 12(a):** autoria de publicações deve seguir as recomendações do
ICMJE. Isso não te obriga a colocá-los como coautores — mas se a colaboração crescer, é a
régua acordada.

### §4.3 · Proíbe redistribuição?

**Sim, e de forma ampla.** Cláusula 3:

> "RECIPIENT shall **not allow third parties that are not expressly mentioned in the Annexes**
> to access or otherwise process the DATA without prior written approval of PROVIDER."

Exceção única: prestadores de serviço de TI em operação normal (hospedagem, manutenção de
infraestrutura) — e mesmo assim com contrato vinculante de conformidade com o GDPR.

Há uma cláusula **opcional** que o PROVIDER pode ou não ativar, permitindo transferir os dados
a terceiros acadêmicos **exclusivamente para replicação**, conforme política de um periódico
que publique o resultado, e só sob acordo escrito com termos ao menos tão estritos.

> 🔴 **Consequências diretas para o projeto:**
> - ❌ Os EDFs **não entram no git**, em hipótese alguma. (O `ml/dados/` já está no
>   `.gitignore` pelo §7 do `ML-DATASETS-E-PLANO.md` — **este é o motivo contratual**, não só
>   higiene.)
> - ❌ Nada de subir para Drive compartilhado, Colab público, ou bucket aberto.
> - ⚠️ **Treinar em Colab/Kaggle é processamento por terceiro.** O `"service providers in the
>   context of the standard business operations"` provavelmente cobre isso — mas é ambíguo, e
>   o Anexo I do DUA tem um campo explícito *"Authorized processors"*. **Declare ali onde vai
>   rodar.** Se for só a sua máquina, diga isso e o problema some.
> - ✅ Publicar **código** que lê os dados: sem problema. Código não é dado.
> - ✅ Publicar **modelo treinado**: ⛔ não confirmado. Pesos não são "os dados", mas derivam
>   deles. Não há cláusula tratando disso. **Pergunte, se pretender publicar pesos.**

### §4.4 · Exige apagar o dado ao fim do projeto?

**Provavelmente sim — mas o template deixa em aberto, e isso é negociável.** Cláusula 13:

> "This Agreement will become effective on the EFFECTIVE DATE and will terminate **[…] years
> after** the EFFECTIVE DATE …
> Upon expiration or termination …, the right to use the DATA … will automatically end.
> **[OPTION 1: After expiration or termination of this Agreement, RECIPIENT will destroy all
> DATA received from PROVIDER.** Upon request from PROVIDER, RECIPIENT shall confirm **in
> writing the complete deletion**…] **[OPTION 2: However, RECIPIENT may retain one copy of the
> DATA** solely to comply with DATA transfer requests that third party academic institutions
> may make for replication…]"

Três coisas a notar:

1. **O prazo de vigência é um campo em branco** (`[…] years`). **Você propõe.** Peça folga:
   a defesa atrasa, a banca pede análise extra. Sugestão: **3 anos**.
2. **OPTION 1 vs. OPTION 2 é escolha das partes.** A OPTION 2 (guardar uma cópia para
   replicação) é a mais saudável para reprodutibilidade científica e vale ser pedida.
3. **Há uma obrigação de deleção que independe do prazo** — cláusula 2(e): se um participante
   retirar o consentimento, você deve **cessar o uso imediatamente e apagar as cópias
   daquele dado**, confirmando por escrito se solicitado.

**Outras obrigações com efeito de prazo:**

| Cláusula | Obrigação |
|---|---|
| 11 | Confidencialidade da informação do PROVIDER por **5 anos** após o término |
| 2(c) | Implementar medidas técnicas e organizacionais de proteção — você é **controlador de dados independente** sob o GDPR |
| 2(d) | Notificar o PROVIDER **prontamente** em caso de vazamento |
| 4 | Manter o cientista do PROVIDER informado dos resultados, **quando solicitado** |
| 5 | **Reportar qualquer invenção** decorrente do uso dos dados |
| 9 | Dados vêm **sem garantia** de exatidão ou adequação; você assume o risco e indeniza o PROVIDER |
| 10 | Cumprir toda a legislação aplicável — no seu caso, **LGPD** também |
| 14 | **Lei holandesa**, foro nos Países Baixos |
| 7 | Pode haver **taxa de transmissão** — campo em branco. Provavelmente zero, mas **confirme** |

> 🟡 **A cláusula 2(b)/(c) é a mais subestimada.** Ela te torna *"a separate data controller
> under the APPLICABLE DATA PROTECTION LAW"*. Numa faculdade brasileira, isso significa que
> alguém institucionalmente precisa assumir esse papel — e é mais um motivo para envolver a
> coordenação cedo (§3.3).

---

## §5. Como escrever o e-mail ao Dr. Dresler

Contato único para tudo (acesso, dúvidas, colaboração): **`martin.dresler@donders.ru.nl`**
(confirmado nos metadados da coleção e no README).

⚠️ A ajuda genérica do RDR diz *"Do not contact this person to request access"* — mas os
**autores do Wearanize+ instruem exatamente o contrário** no README: mandar o DUA preenchido
por e-mail para ele. **Siga os autores**; a instrução deles é específica para este dataset.

**Anexe:** o `DTA_Wearanize_nonEU_v1.docx` preenchido, com o plano de pesquisa
(`docs/WEARANIZE-PLANO-PESQUISA.md`, versão em inglês) na seção do plano ou como anexo.

**Inclua no corpo do e-mail estas quatro perguntas** — todas são pontos que este documento
não conseguiu fechar na fonte:

1. Uma **monografia de graduação** (depositada no repositório da instituição) conta como
   *Disclosure* para efeito da revisão de 30 dias da cláusula 12(b)?
2. Dado que o Brasil recebeu **decisão de adequação da Comissão Europeia em 26/01/2026**, o
   `DTA_Wearanize_nonEU_v1.docx` continua sendo o formulário correto, ou há um caminho
   simplificado?
3. Há **taxa de transmissão** (cláusula 7)?
4. Publicar **pesos de um modelo** treinado sobre os dados é permitido?

E declare que você **já está usando a coleção OA** — isso mostra que o pedido é focado
(questionários) e não um pedido genérico de "me dá o dataset".

---

## §6. Armadilhas técnicas — leia antes de escrever código

### §6.1 · O bug de unidade do Empatica E4 — onde está documentado e o que o arquivo diz

**Onde está documentado.** Rodapé da tabela de canais do `README.md` do
[repositório oficial](https://github.com/Niloy333/Wearanize_plus), marcador ⚠️ aplicado às
três linhas `Emp_ACCX/Y/Z`:

> "**Files in PlugNPlay v1.0 state this unit as ⓖ/16. However, the actual unit is ⓖ/64**
> (same as the source). The units were fixed in PlugNPlay v1.1."

**O que o arquivo confirma.** Nos 100 `channels.tsv` da coleção OA (PlugNPlay **v1.1**), os
276 canais `Emp_ACC*` existentes declaram, sem uma única exceção:

```
units                = g/64          ← a unidade CORRETA
sampling_frequency   = 32.0
min_val (global)     = -128
max_val (global)     = +127
```

`−128…+127` é **exatamente um inteiro de 8 bits com sinal**. Em `g/64`, isso dá
**±2 g** e LSB = 1/64 g = **15,625 mg** — batendo casa por casa com o manual do E4
(`Resolution: 8 bits of the selected range`, `Default range ±2g`) e com a derivação do
§2.1 do `ML-DATASETS-E-PLANO.md`. **A coleção aberta está correta.**

> 🔴 **O que isso significa na prática.** Se você usasse a v1.0 (coleção restrita) sem saber,
> toda aceleração de pulso sairia **4× maior** que a real. O pulso é justamente o braço
> "treina" do `ML-03`: o experimento inteiro mediria um artefato de escala em vez da
> transferência entre posições. **Este é, sozinho, um argumento suficiente para usar a OA.**
>
> ⛔ **Não verificado diretamente:** que a v1.0 realmente declare `g/16`. A coleção restrita
> não é acessível sem DUA. A fonte da afirmação é o aviso dos próprios autores, acima —
> que é a melhor fonte possível, mas não é leitura do arquivo.

### §6.2 · Zmax: taxa, faixa, bits e resolução — a célula ⛔ do §2.1, fechada

Do `channels.tsv` dos 100 sujeitos (300 canais `Zmax_ACC*`, sem exceção):

| Propriedade | Valor | Como foi obtido |
|---|---|---|
| **Taxa** | **256 Hz** | `sampling_frequency = 256.0` em **300/300** canais. Confirmado de forma independente pelo EDF: **7 680 amostras** por registro de 30 s = 256 Hz |
| **Unidade** | **`g`** | campo `units`, 300/300 |
| **Faixa** | **±2 g** | `min_val` global nos 100 sujeitos = **exatamente −2.0**; `max_val` global = **1.999023** — saturação nos dois extremos |
| **Resolução** | **1/1024 g = 0,977 mg/LSB** | derivada: `2 − 1,999023 = 0,000977 = 1/1024`; **todos** os extremos observados caem na grade de 1/1024 g |
| **Bits** | **12** | derivado: 4 g ÷ (1/1024 g) = 4096 níveis = 2¹² |

> ✅ **A taxa de 256 Hz está agora confirmada em fonte primária** — o próprio arquivo, em
> 300 canais. Não depende mais nem do preprint de Esfahani et al. nem da frase ambígua do
> artigo. **Isso fecha a célula 🟡 do §2.1** e resolve a nota ᵉ.
>
> ⚠️ **Sobre faixa/resolução/bits, seja preciso na redação do TCC.** Estes três **não** são
> declarados por ninguém: a Hypnodyne não publica ficha técnica, e o cabeçalho EDF **não
> serve** para isso (ver a caixa abaixo). São **derivados por nós** da grade de quantização
> observada em 100 gravações. A evidência é forte — saturação exata em −2,0 e grade de
> 1/1024 em todos os extremos — mas **é derivação, não especificação de fabricante.**
> Escreva "derivado dos dados", não "segundo a folha de dados".

> 🔴 **O cabeçalho EDF NÃO declara a faixa do sensor — não caia nessa.**
> A nota ⁱ do §2.1 do `ML-DATASETS-E-PLANO.md` dizia que abrir o cabeçalho EDF resolveria
> faixa e resolução, porque o EDF guarda `physical/digital min-max` por canal. **Abri, e não
> resolve.** No `sub-005`:
>
> ```
> digital  min/max = -32768 / 32767      ← o span do contêiner EDF de 16 bits, não do sensor
> physical min/max = -2 / 1.144531  (Zmax_ACCX)   ← os EXTREMOS DAQUELA GRAVAÇÃO
> physical min/max = -1.56835 / 1.999023 (Zmax_ACCY)  ← diferentes por canal!
> ```
>
> O pipeline de conversão **reescalou tudo para o span cheio de 16 bits do EDF** e gravou nos
> campos físicos os extremos observados de cada canal. Ou seja: os campos do EDF descrevem a
> *gravação*, não o *sensor*. **A via que funciona é a grade de quantização**, e foi a que
> usei. A nota ⁱ precisa ser corrigida.

### §6.3 · ActivPAL: o que dá para afirmar e o que não dá

| Propriedade | Valor | Estado |
|---|---|---|
| **Taxa** | **20 Hz** | ✅ confirmado — `sampling_frequency = 20.0` em 279/279 canais; 600 amostras/registro de 30 s |
| **Unidade** | **`g`** | ✅ confirmado, 279/279 |
| **Resolução** | **1/128 g = 7,8125 mg/LSB** | ✅ derivado — todos os extremos observados caem na grade de 1/128 g |
| **Faixa** | observada: **−3,969 g a +3,984 g** | 🟡 compatível com **±4 g**, mas nenhum extremo encosta na trava |
| **Bits** | provavelmente **10** | 🟡 derivado: 8 g ÷ (1/128 g) = 1024 = 2¹⁰ — **coerente, não confirmado** |
| **Modelo do aparelho** | — | ⛔ continua não documentado |

**Consequência prática: mínima.** A coxa é a posição mais distante do caso do Dormio, e as
features do §7 são invariantes à escala do LSB.

### §6.4 · As pontuações de sono — e uma ressalva que ninguém documentou

**Canais presentes**, a **1/30 Hz** (um rótulo por época de 30 s), `min_val = -1`,
`max_val = 4`. **Censo lido nos cabeçalhos EDF dos 100 sujeitos** — que é a fonte que o
carregador usa:

| Canal | Presença nos 100 do PlugNPlay |
|---|:---:|
| `PSG_Manual_Scor1` (pontuador 1) | **100/100** |
| `PSG_Manual_Scor2` (pontuador 2) | **96/100** |
| `PSG_USleep_score` (automático, U-Sleep v2.0) | **96/100** |

**Mapa de rótulos:** `-1` não-pontuável · `0` vigília · `1` N1 · `2` N2 · `3` N3 · `4` REM.
Para sono×vigília: `0` → vigília; `1–4` → sono; `-1` → **descartar a época**.

> 🔴 **O `channels.tsv` MENTE sobre o segundo pontuador.** *(Corrigido em 2026-09-14 — a
> versão anterior desta seção dizia 100/100 e estava errada, porque tinha lido o sidecar em
> vez do EDF.)*
>
> | Fonte | Declara `Manual_scor2` para |
> |---|:---:|
> | `sub-NNN_task-sleep_channels.tsv` (sidecar BIDS) | **100**/100 |
> | **o próprio EDF** | **96**/100 |
>
> Os 4 ausentes são `sub-115`, `sub-124`, `sub-129`, `sub-130` — os **mesmos quatro do
> Mentalab**, e exatamente os mesmos que não têm `PSG_Pos.` nem `PSG_USleep_score`. Bate
> com a versão `raw`, cujo `2.Sleep_scores/2.PSG_manual_scores_scorer2/` tem 96 arquivos
> contra 103 do pontuador 1.
>
> *(Três sujeitos têm pontuação do pontuador 1 mas não entram no PlugNPlay: `sub-077`,
> `sub-078`, `sub-098` — daí 103 e não 100.)*
>
> **Consequências:**
> - **O teto inter-avaliador é N = 96.**
> - **Nunca monte a lista de sujeitos a partir do `channels.tsv`** — ela quebra em 4.
>   O `src/carregar/wearanize.py` lê a disponibilidade **do EDF**, e
>   `testes/test_wearanize.py` tem um caso que fixa essa divergência.
> - A ressalva anterior ("o canal existe nos 100 EDFs, não sei o que tem dentro nos 4")
>   **está resolvida: o canal não existe nesses 4.** Não há conteúdo a investigar.

### §6.5 · Demais armadilhas

1. ⚠️ **Nome de canal difere entre `channels.tsv` e EDF.** `PSG_Manual_scor1` no `.tsv` vs.
   `PSG_Manual_Scor1` no EDF. **Use comparação case-insensitive.** Detalhe em §1.2b.

2. ⚠️ **`PSG_Move.` está a 128 Hz, não a 4 Hz** como diz o README. Verificado em 12/12
   sujeitos. **Confie no `channels.tsv`.**

3. ⚠️ **Quatro participantes usaram outro PSG.** `sub-115`, `sub-124`, `sub-129`, `sub-130`
   foram gravados com **Mentalab**, não SOMNOscreen — nomes de canal diferentes, sem postura,
   sem USleep, sem 2ª pontuação. **Excluir é a decisão mais limpa**, e custa 4 de 100.

4. 📌 **Postura já vem pronta** em `PSG_Pos.` (SOMNOscreen, **4 Hz**, 96/100 sujeitos):
   `1` prono, `2` ereto, `3` esquerdo, `4` direito, `5` ereto (cabeça), `6` supino.
   Referência independente para validar as features `angulo_z` / `d_angulo` do §7 —
   **isto não estava no plano e é um presente.**

5. ✅ **Metadados demográficos abertos.** `participants.tsv` traz `age`, `gender`,
   `handedness` dos 100. A versão `raw` tem ainda
   `4.Demographic_info/Wearanize+_participant_demographic_information.xlsx`.
   ⚠️ **Lateralidade importa aqui**: o E4 fica no pulso, e há canhotos na amostra — vale
   checar se o lado do aparelho é documentado antes de assumir homogeneidade.

6. 📌 **Ler como Float32.** O README avisa: se for lido como Float64, converter, para não
   estourar memória.

7. 📌 **Código de leitura pronto:** `read_PlugNPlay_EDF.py` (e `.m`) no repositório oficial.
   Não escreva o leitor de EDF do zero.

8. 📌 **Os EDFs são EDF+** — têm um canal `EDF Annotations` ao final (48 canais no `sub-005`).
   Bibliotecas que só leem EDF clássico podem tropeçar.

---

## §7. Resumo executivo

| Pergunta | Resposta |
|---|---|
| **Onde se cadastra?** | Só precisa se for a coleção restrita: ORCID em orcid.org → login no RDR via ORCID. A **OA não exige cadastro nenhum**. |
| **O que o formulário pede?** | Organização e cargo de cada pessoa; tipo, parceiros, título e descrição do projeto (contexto, pergunta de pesquisa, métodos, relevância dos dados, entregáveis). |
| **Exige ORCID?** | **Sim** para a via restrita (instrução explícita dos autores), com e-mail visível e igual ao do DUA. Não para a OA. |
| **Exige assinatura institucional?** | **Sim.** É contrato instituição↔instituição, assinado por representantes legais autorizados. Orientador entra como RECIPIENT SCIENTIST. |
| **Prazo de resposta?** | ⛔ **Não publicado em lugar nenhum.** Estimativa: semanas a meses, pelo caminho jurídico envolvido. |
| **Dado pode ir em figura da monografia?** | Sim. Mas há **revisão prévia de 30 dias** pelo PROVIDER antes de divulgar. ⛔ Se TCC conta como *Disclosure*: perguntar. |
| **Citação obrigatória?** | **Sim** — artigo + dataset primário, e **agradecimento nominal** ao PROVIDER pela cláusula 12(c). Vale mesmo usando só a OA. |
| **Proíbe redistribuição?** | **Sim**, amplamente. Nada de git, Drive ou bucket. Código pode; dado não. |
| **Exige apagar no fim?** | Provavelmente. Prazo de vigência e a escolha destruir-vs-guardar-uma-cópia **são campos em branco que você negocia**. Deleção imediata é obrigatória se um participante retirar consentimento. |
| **O DUA está no caminho crítico?** | 🔴 **NÃO.** Verificado no arquivo: o `ML-03` roda com **N = 92** na coleção aberta, CC-BY-4.0, sem cadastro. O DUA destrava **só os questionários**. |
| **👉 O que fazer primeiro?** | **Configurar o WebDAV anônimo** (`webdav.data.ru.nl`, Anonymous Login, `/dcmn/DSC_wrnzpoa_t0000925a_195_v1`) e baixar 10 sujeitos (~5 GB) para o piloto. Começar pelo `ML-02` (baseline trivial), como o §0.2 do `ML-DATASETS-E-PLANO.md` manda. |

---

## Fontes

Todas verificadas em **2026-09-14**.

- **Coleção Wearanize+ (restrita)** — Radboud Data Repository, DOI `10.34973/j6jf-9e62`.
  <https://data.ru.nl/collections/di/dcmn/DSC_wearanize_t0000657a_579>
- **Coleção Wearanize+ OA (aberta)** — Radboud Data Repository, DOI `10.34973/xrmf-5726`,
  licença CC-BY-4.0. <https://data.ru.nl/collections/di/dcmn/DSC_wrnzpoa_t0000925a_195>
- **Texto integral do DUA `RUMC-RA-DUA-1.0`** — *Agreement on the sharing of pseudonymized
  personal data (for academic research)*. <https://data.ru.nl/dua/RUMC-RA-DUA-1.0>
  · PDF: <https://data.ru.nl/files/dua-pdfs/RUMC-RA-DUA-1.0.pdf>
- **Instruções oficiais de acesso e documentação técnica** — `README.md` do repositório
  oficial do dataset. <https://github.com/Niloy333/Wearanize_plus>
  · Templates de DUA: `DUA_forms/` (`DTA_Wearanize_nonEU_v1.docx`,
  `Wearanize+_Radboudumc_DUA_v2.0.docx`, `RUMC-RA-DUA-1.0.pdf`)
- **RDR — Accessing a collection** (fluxo de pedido, exigências de ORCID, preparação).
  <https://rdr.tutorials.ru.nl/a/1946517-accessing-a-collection>
- **RDR — Restricted access, access requests** (lado do gestor, assinatura, jurídico,
  transferência internacional).
  <https://rdr.tutorials.ru.nl/a/1945343-restricted-access-access-requests>
- **RDR — Access levels and licences** (definição dos níveis, templates de DUA).
  <https://rdr.tutorials.ru.nl/a/1945331-access-levels-and-licences>
- **RDR — Downloading collection content** (portal, WebDAV, Cyberduck, repocli).
  <https://rdr.tutorials.ru.nl/a/1946519-downloading-collection-content>
- **Comissão Europeia — Adequacy decisions** (Brasil, decisão de 26/01/2026).
  <https://commission.europa.eu/law/law-topic/data-protection/international-dimension-data-protection/adequacy-decisions_en>
- **Artigo de referência** — Sikder et al. (2026), *SLEEP Advances* 7(1), zpaf094.
  <https://doi.org/10.1093/sleepadvances/zpaf094>

### O que foi confirmado na 2ª rodada (2026-09-14), abrindo os arquivos

| # | Afirmação | Evidência |
|:-:|---|---|
| 1 | Os **três acelerômetros** estão na coleção aberta | 100 `channels.tsv` lidos: Zmax 100/100, Empatica 92/100, ActivPAL 93/100 |
| 2 | **PSG pontuada** incluída, 1 rótulo por época de 30 s | `PSG_Manual_Scor1`, `PSG_Manual_Scor2`, `PSG_USleep_score` a 1/30 Hz, `min=-1`/`max=4`; 1 amostra por registro EDF de 30 s |
| 3 | **Download funciona sem cadastro** | 100 `.tsv` a HTTP 200 + EDF de 480 MB a **HTTP 206** via WebDAV anônimo |
| 4 | **Quantos participantes** | `raw` = **130**; `PlugNPlay` = **100** (`participants.tsv`) |
| 5 | **Zmax: 256 Hz**, `g`, ±2 g, 12 bits, 0,977 mg/LSB | 300/300 canais para a taxa; faixa e resolução **derivadas** da grade de quantização |
| 6 | **Bug de unidade do E4** | README declara `g/16` (v1.0) → `g/64` (v1.1); a OA declara **`g/64`** em 276/276 canais, extremos −128/+127 (8 bits) |

### O que foi confirmado na 3ª rodada (2026-09-14), decodificando o dado

Feito ao escrever `ml/src/carregar/wearanize.py`, para que o carregador fosse escrito sobre
medição e não sobre documentação.

| # | Afirmação | Evidência |
|:-:|---|---|
| 7 | **O EDF decodifica corretamente** | Registro 500 do `sub-005` lido byte a byte: \|a\| = **1,009 g** (Zmax), **1,025 g** (Empatica ÷64), **1,054 g** (ActivPAL). Sem a divisão por 64, o Empatica daria 65,6 g |
| 8 | **A estrutura prevê o tamanho do arquivo** | `12 544 + 974 × 513 300 = 499 966 744 B` = o tamanho exato do `sub-005` |
| 9 | **Um registro = uma época = um rótulo** | `duração do registro = 30 s` nos 100; `Zmax_ACC*` 7 680 am/reg (256 Hz), `Emp_ACC*` 960 (32 Hz), `ActivPal_ACC*` 600 (20 Hz), canais de pontuação **1** |
| 10 | **Os dois pontuadores discordam** | Mesma época do `sub-005`: `Scor1 = 2` (N2), `Scor2 = 1` (N1), `USleep = 2`. É o teto inter-avaliador em ação |
| 11 | 🔴 **O `channels.tsv` declara `scor2` que o EDF não tem** | `.tsv`: 100/100 · **EDF: 96/100**. Corrige o §6.4 e a 2ª rodada |
| 12 | **O nº de canais varia por sujeito** | 38, 41, 45, 47, 48, 49, 54, 61 — indexar por posição fixa quebra |
| 13 | **A grafia do rótulo difere entre sidecar e EDF** | EDF: `PSG_Manual_Scor1` (S maiúsculo) · `.tsv`: `PSG_Manual_scor1`. Nos 100, sem exceção |

### Pendências que permanecem

1. ⛔ **Rótulos exatos dos campos** do formulário "Request access" — só visíveis após login.
2. ✅ **RESOLVIDO em 2026-09-14 (4ª rodada):** conteúdo do `DTA_Wearanize_nonEU_v1.docx` aberto
   e lido por inteiro. Ver §8 abaixo — difere do `RUMC-RA-DUA-1.0` em pontos que importam.
3. ⛔ **Prazo típico de resposta** — não publicado em nenhuma fonte oficial.
4. ⛔ **Se uma monografia de TCC conta como *Disclosure*** (cláusula 12(b), revisão de 30 dias).
5. ⛔ **Se publicar pesos de modelo treinado é permitido** — o DUA não trata do assunto.
6. ✅ **RESOLVIDO em 2026-09-14 (4ª rodada):** não há taxa de transmissão. Ver §8.
7. ⛔ **Que a v1.0 realmente declare `g/16`** — a coleção restrita não é acessível. A fonte é
   o aviso dos próprios autores no README.
8. ✅ **RESOLVIDO em 2026-09-14 (3ª rodada):** o canal `PSG_Manual_Scor2` **não existe** no EDF
   dos 4 sujeitos Mentalab — quem declarava 100/100 era o `channels.tsv`, não o dado. Não há
   conteúdo a investigar. Teto inter-avaliador = **N = 96**. Ver §6.4.

Os itens 1, 3, 4, 5 e 7 são todos da via restrita e **não bloqueiam nada**, porque o DUA saiu do
caminho crítico. Os itens 1, 4 e 5 estão no e-mail sugerido no §5, caso você decida pedir os
questionários.

> ✅ **O carregador já está escrito** (`ml/src/carregar/wearanize.py`), com as cinco
> armadilhas desta seção tratadas e uma suíte de testes que as fixa
> (`ml/testes/test_wearanize.py`). O script de download anônimo com retomada está em
> `ml/ferramentas/baixar_wearanize.py`. **Nada disso foi executado** — ver `ml/README.md`.

---

## §8. O `DTA_Wearanize_nonEU_v1.docx` de verdade — lido por inteiro (2026-09-14, 4ª rodada)

O §4 acima descreve o template genérico `RUMC-RA-DUA-1.0` (o que está publicado nos metadados
da coleção restrita). **O arquivo que o Brasil de fato usa é outro** — baixado do GitHub oficial
e lido por completo (242 KB, `DUA_forms/DTA_Wearanize_nonEU_v1.docx`) — e ele **difere do
genérico em quatro pontos que mudam o que você escreve e assina.**

### §8.1 · O Anexo II tem limite de palavras — e não é sutil

> "ANNEX II — **Recipient's research plan (maximum 300 words)**"
> — texto literal do `DTA_Wearanize_nonEU_v1.docx` (idêntico no `Wearanize+_Radboudumc_DUA_v2.0.docx`, a versão EEE)

**Isto não está em lugar nenhum do `RUMC-RA-DUA-1.0` genérico nem no §3.2 acima**, e o
`docs/WEARANIZE-PLANO-PESQUISA.md` §A tem várias páginas — não cabe. O §A continua correto e
útil para o orientador, para a introdução do TCC e para o campo *project description* do
portal RDR (que é texto livre, sem limite conhecido). **Mas o que vai colado no Anexo II do
`.docx` precisa ser outra coisa, de até 300 palavras.** Rascunho pronto em
`docs/WEARANIZE-PLANO-PESQUISA.md` §C.

### §8.2 · O prazo de vigência NÃO é um campo em branco nesta versão

O §4.4 acima (lendo o `RUMC-RA-DUA-1.0`) diz que o prazo é `[…] years` — um campo aberto para
propor. **No `DTA_Wearanize_nonEU_v1.docx` já vem preenchido:**

> "This Agreement will become effective on the EFFECTIVE DATE and will terminate **ten (10)
> years** after the EFFECTIVE DATE, unless mutually extended in writing by both Parties."

Dez anos já cobre qualquer atraso de TCC com folga; **não há necessidade de negociar prazo**
nesta via — item removido da lista de coisas a decidir.

### §8.3 · Não há opção de guardar cópia para replicação — só destruir

O §4.4 apresenta OPTION 1 (destruir) vs. OPTION 2 (guardar uma cópia para replicação) como
escolha das partes, lendo o template genérico. **No `DTA_Wearanize_nonEU_v1.docx` só a OPTION 1
está no texto final** — não há colchete, não há escolha:

> "Upon expiration or termination of this Agreement, the right to use the DATA and
> CONFIDENTIAL INFORMATION will automatically end. **After expiration or termination of this
> Agreement, RECIPIENT will destroy all DATA received from PROVIDER.** Upon request from
> PROVIDER, RECIPIENT shall confirm in writing the complete deletion of such DATA and
> CONFIDENTIAL INFORMATION."

Consistente com o Artigo 3 também não trazer a cláusula opcional de transferência para
replicação acadêmica que a versão EEE tem — a versão não-EEE, lida por inteiro, **não permite
retransferir o dado a ninguém, nem para replicação**, sem acordo separado.

### §8.4 · Sem taxa de transmissão — resolve a pendência nº 6

O template genérico deixa um valor de taxa em branco (cláusula 7). **No `DTA_Wearanize_nonEU_v1.docx` a frase já vem fechada, sem opção de cobrança:**

> "The DATA will be provided **at no cost**."

### §8.5 · Por que o arquivo tem 242 KB contra 29 KB da versão EEE

A suspeita do §3.4 (*"o tamanho sugere anexos, provavelmente as Cláusulas Contratuais-Padrão da
UE"*) **está confirmada**: o `.docx` não-EEE anexa o texto integral das **Standard Contractual
Clauses (SCC)** da UE para transferência internacional (Módulo "controller to controller"),
mais um "Appendix to SCC" com:

- **A. List of Parties** — exportador = Radboudumc; importador = `<sua instituição>` (campo
  em branco, a preencher)
- **B. Description of Transfer** — transferência única (*"Single transfer"*), retenção = pela
  duração do Acordo
- **C. Competent Supervisory Authority** — **Autoriteit Persoonsgegevens** (a autoridade
  holandesa de proteção de dados), com endereço postal completo
- **Annex II das SCC** — "Technical and organisational measures" — **em branco, a preencher**
  pelo recebedor (é aqui que você declara como vai proteger o dado: disco criptografado,
  acesso restrito, sem nuvem — o que o `WEARANIZE-PLANO-PESQUISA.md` já descreve na tabela
  "Tratamento, segurança e retenção dos dados")

Isso não muda nenhuma decisão prática — só explica o arquivo e confirma que **a tabela de
segurança do plano de pesquisa não é enfeite: é o conteúdo literal de um campo que o contrato
exige preencher.**

### §8.6 · Signatários do lado Radboudumc, pelo nome

Não é mais "o diretor de pesquisa" genérico — o arquivo já traz os nomes:

| Papel | Nome |
|---|---|
| Assinatura 1 (PROVIDER) | Joram Sjoerts, MSc — *Director of Knowledge Strategy* |
| Assinatura 2 (PROVIDER) | Prof. dr. Barbara Franke — *Head of Dept. MNS* |
| PROVIDER'S SCIENTIST | Dr. Martin Dresler — `martin.dresler@donders.ru.nl` · +31 24 361-0986 |

Do lado do RECIPIENT, o arquivo só tem campos vazios para preencher (nome, título, e-mail,
assinatura, data) — confirma o §3.3: **precisa ser alguém com poder de assinatura
institucional**, não o aluno.

### §8.7 · O que isso muda no resumo executivo do §7

Nada na linha "**O DUA está no caminho crítico?**" — continua **não**. Muda duas linhas:

- "**Prazo de resposta?**" — o prazo de *vigência do contrato* (não de resposta) já vem
  fixado em 10 anos; segue sem SLA publicado para quanto tempo a aprovação leva.
- Uma linha nova: **"O Anexo II tem limite de 300 palavras"** — use
  `docs/WEARANIZE-PLANO-PESQUISA.md` §C, não o §A completo, para preencher o `.docx`.

Fonte desta seção: leitura integral, via `python-zipfile` sobre o XML do `.docx` (sem
depender de Word), de `DUA_forms/DTA_Wearanize_nonEU_v1.docx` e
`DUA_forms/Wearanize+_Radboudumc_DUA_v2.0.docx`, baixados de
<https://github.com/Niloy333/Wearanize_plus/tree/base/DUA_forms> em 2026-09-14.
