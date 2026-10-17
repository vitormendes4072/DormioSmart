# Lições aprendidas — Smart Dormio

> **Criado em 2026-10-17.** Organizado por **padrão de falha**, não por data.
>
> O `docs/DIARIO-DE-ENGENHARIA.md` registra *o que aconteceu*, em ordem cronológica, e é a
> procedência de tudo o que está aqui. Este arquivo responde a outra pergunta: **"já pisamos
> nessa pedra?"** — que é a pergunta que se faz *antes* de errar, e que ninguém responde
> relendo 29 entradas cronológicas.
>
> **Regra de entrada.** Uma lição só entra com **duas ocorrências reais** no projeto, ou com
> **uma cujo custo esteja medido**. Nada de boa prática genérica: se não houver commit, teste
> ou entrada de diário para apontar, não é lição deste projeto, é opinião.

---

## Como usar

**Antes de fechar um item**, passe pela seção §9 (checklist de revisão). São sete perguntas, e
cada uma existe porque o projeto já pagou por não a ter feito.

**Ao achar um padrão novo**, acrescente aqui com as quatro partes fixas, na ordem:

| Campo | O que registra |
|---|---|
| **O padrão** | Uma frase. Se não couber numa frase, provavelmente são dois padrões. |
| **Onde aconteceu** | Ocorrências reais, com entrada do diário e commit. Sem isto a lição não entra. |
| **O que custou** | O dano concreto e, onde houver, o número. "Quase deu errado" também conta, e diz-se assim. |
| **Como não repetir** | **Em forma verificável de preferência:** um teste, um alvo de `make`, uma verificação de CI, uma pergunta de revisão. Conselho sem mecanismo é a forma mais barata de não resolver. |

**O índice, por ordem de reincidência medida:**

| § | Padrão | Ocorrências |
|:-:|---|:-:|
| 1 | Alcance declarado que não alcança | **6** |
| 2 | Análise correta que não chega onde a decisão é tomada | **4** |
| 3 | Número herdado que ganha autoridade sem ter procedência | **4** |
| 4 | O instrumento de medida mede errado — e nada mede o instrumento | **4** |
| 5 | Premissa herdada da documentação, nunca conferida no artefato | **3** |
| 6 | Confirmação emitida antes da verificação | **3** |
| 7 | Degradação silenciosa é pior que falha ruidosa | **3** |
| 8 | A média esconde o caso que importa | **2** |

---

## §1 — Alcance declarado que não alcança

**O padrão.** Uma verificação existe, está bem escrita, passa — e o conjunto que ela de fato
cobre é menor que o conjunto que seu nome anuncia; a diferença não aparece lendo, só rodando.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **O `CI-05` como foi especificado não podia reprovar.** Um job que falha "quando há arquivo não rastreado em `docs/`" — mas `actions/checkout` monta a árvore a partir do commit, então arquivo não rastreado nunca chega ao runner. Devolveria vazio **sempre**. | Diário 2026-09-30; commit `6312267` |
| 2 | **O vetor dourado gravava a própria referência.** `test_gravar_vetor_dourado` gravava o arquivo e conferia que ele existia. Nunca podia falhar: o arquivo perseguia o código em vez de prendê-lo. | Diário 2026-09-30 (`DATA-07c`, item a); commit `0f22941` |
| 3 | **Os 5 casos do dourado eram todos de época única**, então `inclinacao_rel` e `d_angulo` valiam **0 em todos os cinco** — as duas features de definição mais delicada não tinham referência nenhuma. E zero é trivialmente invariante a rotação, então o teste de invariância delas passava sem testar nada. | Diário 2026-09-30; commit `4d1b5d2` |
| 4 | **`make sintaxe` tinha 2 dos 4 sketches**, e os dois de fora **não compilavam** — pelo mesmo defeito de string quebrada de 22/09. A lista era escrita à mão. | Diário 2026-10-16; commit `7feeef9` |
| 5 | **A guarda de coleta do `CI-04` estava 37 testes defasada:** piso em 70, suíte com 107. Toleraria perder **um terço da cobertura** sem reprovar — e é o próprio modo de falha que ela existia para pegar. | Diário 2026-10-16; commit `6359912` |
| 6 | **O aviso de captação foi escrito num arquivo gitignorado.** O `ROADMAP.md` não é versionado: o aviso não chegaria a um clone. | Backlog `GIT-05` (17/10) |

**O que custou.** Nos casos 1, 4 e 5, **nada em produção — e só porque alguém foi rodar.** Os
três jobs tinham sido lidos e revisados em 30/09 e **nenhum dos três passava como estava
escrito**; os defeitos apareceram na primeira execução, em 16/10, dezesseis dias depois. O caso
4 é o mais caro em significado: dois sketches versionados **não compilavam em máquina nenhuma**,
e isso durou de 22/09 a 16/10 porque nada no repositório tentava compilá-los. O caso 2 é o mais
perigoso, porque um dourado que se regrava é indistinguível de um dourado que prende — até o dia
em que uma definição muda em silêncio.

**Como não repetir.**

1. ⚙️ **Controle positivo, sempre.** Nenhuma verificação é considerada pronta sem **provocar o
   defeito de propósito e confirmar que ela acusa.** É a regra de método que fechou os três
   jobs em 16/10 e a verificação (3) em 17/10. Está escrita no procedimento de reconferência do
   backlog (seção "Infraestrutura e qualidade").
2. ⚙️ **Alcance não se escreve à mão.** `SKETCHES` saiu de lista manual para `$(wildcard)`, com
   guarda para o caso de não casar nada. *"Alcance de verificação escrito à mão silenciosamente
   para de acompanhar a pasta."* — `firmware/nucleo/Makefile`.
3. ⚙️ **Piso de contagem com o motivo e a obrigação de atualizar ao lado.** `CI-04` confere o
   número de testes coletados *antes* de rodar, porque o modo de falha ali é coleta vazia ou
   parcial, que passa em silêncio.
4. ⚙️ **Isenção é impressa a cada execução.** `EXEMPLOS_EM_PROSA` e `PONTEIROS_ACEITOS` em
   `scripts/conferir_docs_versionados.py` imprimem a lista inteira toda vez. *Isenção silenciosa
   é como uma verificação deixa de verificar sem ninguém notar.*
5. ⚙️ **Verificação que nasce com as violações atuais dentro da isenção declara isso.** A
   verificação (3), criada em 17/10, entrou com os 8 ponteiros existentes isentos — e diz, no
   script, no `ci.yml` e no backlog, que **hoje não cobre nenhum deles; pega o nono.** É catraca,
   não cobertura, e confundir as duas é como o caso 5 acontece.
6. ❓ **Pergunta de revisão:** *se eu quebrasse de propósito a coisa que este teste protege, ele
   ficaria vermelho? Em que máquina?* A segunda metade da pergunta é a que pegou o `CI-05`.

---

## §2 — Análise correta que não chega onde a decisão é tomada

**O padrão.** O trabalho difícil foi feito, o número está certo e está escrito — no corpo de um
documento, no meio de uma entrada de diário, num parágrafo de estudo. E a lista que alguém
consulta para decidir o que fazer não o menciona.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **A recomendação de flash ficou órfã por 18 dias.** O estudo do buffer (29/09) dimensionou flash como registro durável: 1,5 MiB, 13,7 dias, desgaste de 3 741 anos, energia em centésimos de por cento. **A palavra "flash" não aparecia uma vez no backlog nem no diário.** Virou `FW-08` só em 17/10. | Commit `3f2cb87`; backlog `FW-08` |
| 2 | **O conflito de cadência existia em duas metades que nada ligava.** O `CALC-01` Z.4.3 (42 Hz > 40 Hz do modo de baixo consumo ⇒ 4,5× de corrente e fim do despertar por movimento) estava escrito desde 10/09; a inércia do caminho de features foi medida em 17/10. O `FW-05`, que é onde a cadência seria implementada, pedia *"≥ 42 Hz"* como requisito simples. Virou `ARQ-01`. | Diário 2026-09-10 e 2026-10-17; commit `4fb72e4` |
| 3 | **A dívida de não quantizar os picos estava no diário, não no backlog.** O motivo era bom (não misturar a mudança de precisão transmitida com a checagem de coerência da §5.1) e estava escrito só na entrada. Virou `DATA-07e`. | Diário 2026-10-17; commit `8ec2fa1` |
| 4 | **O ponto cego `C2` estava registrado como achado, não como limite.** O backlog dizia "1 ponto cego registrado" — e esse era o do lado Python. O limite quantificado (piso ~2× a sabotagem em toda a faixa) não estava no backlog nem no `LIMITACOES-TCC.md`, que é material de defesa. | Diário 2026-10-17; commit `7cddf66` |

**O que custou.** O caso 1 é o mais caro e o mais fácil de medir: a autonomia caiu para **5,25 h**
ao implementar as features, abaixo de uma noite de 8 h, **com a saída já desenhada e
dimensionada havia 18 dias.** O caso 2 custou a classificação errada de um item no caminho
crítico — `FW-05` figurava como "configurar a taxa" quando é "escolher uma arquitetura". O caso
4 teria custado numa banca, que é onde o limite seria perguntado.

**Como não repetir.**

1. ⚙️ **Todo estudo termina com "o que isto vira na lista".** O próprio
   `DECISAO-BUFFER-E-FEATURES.md` tinha uma seção "Ordem de implementação" com três passos — e
   **nenhum dos três virou item**. A seção é necessária e não é suficiente: o passo que falta é
   abrir o backlog e criar a linha.
2. ⚙️ **Toda entrada de diário com "Risco em aberto" aponta o item que o carrega.** Risco sem
   item é observação solta, e observação solta é o insumo deste padrão. Onde não houver item,
   criar um — mesmo que ⛔ ("não é pendência"), como `PARID-C2`, porque registrar que *não há o
   que fazer* também impede retomada.
3. ⚙️ **Limite quantificado vai para o `LIMITACOES-TCC.md`, não só para o diário.** Foi o que
   faltou no caso 4. O arquivo tem seção de procedência por data para isso.
4. ❓ **Pergunta de revisão:** *quem precisa saber disto vai abrir o arquivo onde eu escrevi?*
   Se a resposta é "se ele ler o documento inteiro", a resposta é não.

---

## §3 — Número herdado que ganha autoridade sem ter procedência

**O padrão.** Um valor entra por um caminho qualquer — correção de outro defeito, arredondamento,
folheto de fabricante — e passa a ser tratado como derivado porque está escrito num lugar formal.
A nota de "provisório" é lida cada vez menos.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **O limiar de 1,2 m/s² é 67 σ.** Nasceu da correção da assimetria em 20/08 (`11,0 − 9,81 = 1,19`), virou constante no contrato de dados, e foi tratado por semanas como se fosse `g ± k·σ`. Com `σ = 1,833 mg`, **k = 67** — e limiares derivados de ruído vivem entre 3 σ e 5 σ. A derivação honesta daria **0,054 a 0,090 m/s²**, de 13 a 22 vezes menor. | Diário 2026-08-20 e 2026-09-29 |
| 2 | **Os 4 MiB de flash eram do chip, não do projeto.** O esquema de partições padrão reserva ~1,2 MB para duas fatias de OTA e deixa **1,5 MB**. Diferença de quase 3× entre o número de folheto e o número de projeto. | `DECISAO-BUFFER-E-FEATURES.md` §"Saída 1"; commit `3f2cb87` |
| 3 | **Os coeficientes de referência do filtro foram escritos de memória e estavam errados** (`b0 ≈ 5,37e−4` contra `5,8207613e−4` real). Um valor de referência inventado faz o teste reprovar código correto — e a reação natural é mexer no código. | Diário 2026-10-17 (item c); commit `7cddf66` |
| 4 | **"8,53 h de autonomia" continuou sendo citado como estado do projeto** depois que o registro com features passou a 52 B e a cobertura a 5,25 h. O número não estava errado — é o layout de 32 B — e estava no lugar errado. | Backlog, item 7 do "Estado do projeto" (corrigido em 17/10) |

**O que custou.** No caso 1, o `CALC-03` foi **recortado em vez de cumprido**: a seção Z.2.3 do
`CALCULOS-TCC.md` passou a demonstrar *por que a derivação não produz número útil*, em vez de
produzir um número que pareceria derivado e não seria. Escrever a derivação com `k = 67`
implícito teria sido **pior que a ausência dela** — daria ao 1,2 uma procedência que ele não
tem, num documento que vai à banca. O limiar continua em uso e continua provisório; o viés de Z
medido em 25/08 (`−1,06 m/s²`) é **89% dele**.

**Como não repetir.**

1. ⚙️ **Convenção de procedência por número.** `CALCULOS-TCC.md` e
   `DECISAO-BUFFER-E-FEATURES.md` marcam cada constante como *medição*, *especificação*,
   *cálculo* ou *estimativa*, e o que não pôde ser conferido na folha de dados entra como
   **parâmetro em faixa com sensibilidade**, nunca como número citado. Foi assim que a corrente
   de escrita da flash (4–20 mA) entrou honestamente.
2. ⚙️ **`scripts/calculos_tcc.py --conferir` e `scripts/estudo_buffer.py --conferir`** recalculam
   e saem != 0 se divergirem. Número citado em documento tem de sair de um script que roda.
3. ⚙️ **`make capacidade` roda no CI** — não é teste, é a medição de horas de buffer que o
   `firmware/nucleo/README.md` e o backlog citam como *medida*. Rodar no CI impede o número
   citado de descolar do código.
4. ❓ **Pergunta de revisão:** *de onde veio este número, e o que acontece se eu abrir a fonte
   agora?* Se a resposta começa com "ele sempre esteve aí", é este padrão.

---

## §4 — O instrumento de medida mede errado, e nada mede o instrumento

**O padrão.** O teste, o harness ou a referência têm um defeito próprio, que produz resultado
plausível — em geral um **verde** — e por isso ninguém o investiga.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **Suíte de RLS contra Supabase mockado.** Mock não exercita policy nenhuma: a suíte "de segurança" não tocava no mecanismo que dizia cobrir. Reescrita contra Postgres de verdade. | Diário 2026-09-28; commit `f1ef319` |
| 2 | **Teste de RLS que olhava só a primeira linha** do resultado passava por acidente. Foi corrigido **por causa de uma sabotagem da verificação por mutação**, não por revisão. | Diário 2026-09-28 |
| 3 | **A tolerância do ENMO reprovaria firmware correto.** `rel = 1e−6` contra divergência medida de 1,10e−6 em float32 — cancelamento catastrófico em `‖a‖ − 1` com `‖a‖ ≈ 1`. Trocar o acumulador para double **não resolve** (1,101e−6 vs 1,097e−6): o erro entra no `sqrt` por amostra. | Diário 2026-09-30 (item b) |
| 4 | **O harness de mutação do C++ tinha contaminação entre rodadas.** Restaurava só `caracteristicas.cpp`, deixando `filtro.cpp` sabotado da rodada anterior: uma sabotagem apareceu como **detectada**, e a detecção era resíduo da anterior. **Mesmo defeito que o `DATA-07c` achou no instrumento do Python, com outra roupa.** | Diário 2026-10-17 (item e); commit `7cddf66` |

**O que custou.** Direto, pouco; em risco evitado, muito. O caso 1 é o mais grave em natureza: o
trabalho afirma isolamento entre usuários, e a prova disso era um mock. Os casos 2 e 4 só
apareceram **porque existia verificação por mutação** — nenhum dos dois seria achado por
leitura, e o 4 é literalmente a reincidência do mesmo defeito, o que o torna o argumento mais
forte deste documento existir.

**Como não repetir.**

1. ⚙️ **Verificação por mutação em todo instrumento que o trabalho cita como prova.** Três em
   operação: `web-app/tests/rls/verificar_por_mutacao.py` (18–25 sabotadores),
   `ml/testes/verificar_vetor_dourado_por_mutacao.py` (12/12 + 1 cego declarado) e
   `firmware/nucleo/testes/verificar_paridade_por_mutacao.sh` (`make mutacao`, 11/11 + 3 cegos
   declarados).
2. ⚙️ **Árvore nova por sabotagem.** `mktemp -d` a cada rodada, e exigência de que cada trecho
   sabotado case **exatamente uma vez**, com erro alto quando não casa — *um sabotador morto se
   lê como ponto cego.* É a correção do caso 4 e vale para qualquer harness futuro.
3. ⚙️ **Sabotagem nomeia o teste que deve cair** (campo `exige`), para que a suíte não acuse por
   acidente.
4. ⚙️ **Tolerância é derivada entre piso medido e teto de decisão, e re-medida a cada execução**
   — `test_as_tolerancias_ainda_cercam_o_piso`. *Uma tolerância medida uma vez e depois só
   comentada envelhece.*
5. ⚙️ **Ponto cego é declarado, não descoberto.** Os cegos conhecidos (`C1`, `C2`, e o do lado
   Python) estão nomeados no código e confirmados cegos a cada execução do harness. Para o caso
   em que o cego é **inerente** e não há o que fazer, ver `LIMITACOES-TCC.md` X.4, "Limite de
   detecção da verificação por paridade entre implementações", e o item `PARID-C2`.
6. ❓ **Pergunta de revisão:** *este teste já falhou alguma vez? Se nunca, eu sei fazê-lo falhar?*

---

## §5 — Premissa herdada da documentação, nunca conferida no artefato

**O padrão.** "A documentação do dataset descreve o dataset." "Existe um lado C++ das features."
"O que está em `docs/` está versionado." A premissa é razoável, ninguém a escreveu para ser
falsa, e ninguém a conferiu.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **Dez armadilhas de formato** entre o declarado e o gravado, nas duas bases. A pior: o Empatica em **`g/64`** onde a documentação v1.0 declara `g/16` — **fator 4 de erro**, silencioso, no braço "treina" do `ML-03`. Outra: `PSG_Manual_scor1` no `.tsv` contra `PSG_Manual_Scor1` no EDF — casamento sensível a maiúscula acha o acelerômetro e **perde o rótulo**, e o sintoma não é exceção, é **zero época**. | Diário 2026-09-14; commit `5c2720c` (é o que introduz o tratamento de `g/64`, conferido por `git log -S'g/64'`); `ml/testes/test_wearanize.py` |
| 2 | **"O item virou transcrever" estava errado.** O `DATA-07` afirmava que as features só faltavam passar para C++. Um `grep -rniE "enmo\|zcr\|p_frac\|…" firmware/` devolveu **vazio**: existiam só em Python, e o "lado C++" era uma referência escrita em Python dentro de um teste. **O item de maior peso do projeto foi subestimado por seis dias porque ninguém rodou o grep.** | Diário 2026-09-29; backlog `DATA-07b` |
| 3 | **Três documentos passaram semanas fora do git**, entre eles a fundamentação que os READMEs mandavam ler. Achado ao comparar `git ls-files docs/` com o disco — não estava sendo procurado. | Diário 2026-09-22 (`GIT-04`) |

**O que custou.** O caso 1 é o de maior potencial: o fator 4 teria contaminado em silêncio o
braço "treina" da matriz de transferência, que é **o resultado original do trabalho**. Foi
pego por auditoria dos arquivos reais, não por leitura da documentação. O caso 2 custou seis
dias de planejamento sobre uma premissa falsa, e o custo real foi de classificação: o item
figurava como pequeno.

**Como não repetir.**

1. ⚙️ **Um teste por armadilha**, em `ml/testes/test_wearanize.py`. A armadilha que não vira
   teste volta no próximo carregador.
2. ⚙️ **Acesso por nome, nunca por posição** — o nº de canais varia de 38 a 61 por sujeito.
3. ⚙️ **O carregador aborta em vez de converter** quando encontra a declaração `g/16`. Falhar
   alto é melhor que aplicar o fator que se achar.
4. ⚙️ **Regra escrita para o próximo carregador** (`ML-06b`, Walch et al., que **será** escrito
   contra documentação sem o arquivo em mãos): *escreva contra a documentação, mas não confie
   até rodar.* Está no backlog, no próprio item, com o ⚠️.
5. ⚙️ **`conferir_docs_versionados.py`**, três verificações, para o caso 3 — e ele mesmo é
   exemplo de §1: a primeira especificação não podia reprovar.
6. ❓ **Pergunta de revisão:** *eu abri o artefato, ou li sobre ele?* Vale para dataset, folha de
   dados, artigo (`DOC-06b`: **referência conferida ≠ artigo lido**) e código do próprio
   repositório.

---

## §6 — Confirmação emitida antes da verificação

**O padrão.** O sistema responde "feito" antes de saber se foi feito. É o modo de falha mais
antigo do projeto e o primeiro a ter sido nomeado como padrão, na entrada de 2026-06-03.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **`POST /api/data` respondia `201 Created` sem conferir a escrita.** A falha do Supabase não virava erro HTTP: **o dispositivo recebia confirmação de um dado que não existia.** | Diário 2026-06-03 (`FIX-02`) |
| 2 | **Exclusão de conta com desfecho parcial.** O `200` com `conta_de_acesso_removida: false` é um estado em que **dado pessoal do titular continua existindo**. Ganhou tela própria, com cor e ícone de alerta — e `interpretarRecibo` é pessimista de propósito: ausente, nulo ou `"true"` viram parcial. | Backlog `UI-10`; commit `916e210` |
| 3 | **`pytest.skip` não falha o job.** Se a variável de ambiente sumisse, se o serviço não subisse, se o `psycopg2` deixasse de instalar, os testes de RLS seriam **pulados e o CI ficaria verde, anunciando cobertura de segurança que não rodou.** | Diário 2026-09-28; `.github/workflows/ci.yml`, job `rls` |

**O que custou.** O caso 1 produziu o sintoma clássico — dashboard vazio com tudo "funcionando"
— e levou à hipótese errada (problema de leitura) antes de a causa aparecer. O caso 3 é o mesmo
padrão num nível acima: **o verde é a confirmação, e ninguém investiga o verde.**

**Como não repetir.**

1. ⚙️ **A resposta depende do resultado da operação.** Regra do caso 1, aplicada desde então.
2. ⚙️ **Interpretação de recibo é pessimista por omissão.** Campo ausente ou ambíguo ⇒ o pior
   desfecho, não o melhor.
3. ⚙️ **`--ignore` em vez de deixar pular.** Pulo aparece como "s" no relatório e vira ruído que
   se aprende a ignorar; e há etapa explícita *"Conferir que os testes de RLS não foram
   pulados"*, com os três cenários exercitados à mão.
4. ❓ **Pergunta de revisão:** *este "sucesso" foi verificado, ou foi assumido? Como ele se
   pareceria se tivesse falhado?*

---

## §7 — Degradação silenciosa é pior que falha ruidosa

**O padrão.** O sistema continua produzindo saída de aparência normal depois que a premissa
quebrou. Diferente de §6: aqui não há confirmação falsa, há **dado plausível e errado**.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **A medição esperava pela rede.** `conectarWiFi()` era chamada dentro do laço de amostragem e gastava até 20 s em `delay(500)`. Com intervalo de 10 s, uma queda de rede fazia cada ciclo levar 20–30 s — **e a série continuava saindo, com aparência normal, com a base de tempo derivada.** Para actigrafia, cuja unidade *é* a época fixa de 30 s, **a lacuna a análise vê; a deriva, não.** A perda de dado era o problema menor. | Diário 2026-09-22 (`HW-05`); commit `c0725ca` |
| 2 | **Uma amostra em cada três desaparecia**, e **toda época saía marcada `INCOMPLETA` com a medição perfeita.** Fechamento preguiçoso de época. Na placa apareceria depois de uma noite; no host apareceu em 3 ms. | Diário 2026-09-22; `firmware/nucleo/testes/testes.cpp` |
| 3 | **`%lu` para um `uint32_t`** — que no ESP32 é `unsigned int`. O `printf` lia 8 bytes de um argumento de 4 e **imprimia lixo em silêncio**. Achado só porque o stub do `Serial` tem `__attribute__((format))`. | Diário 2026-10-16; commit `7feeef9` |

**O que custou.** O caso 1 teria produzido uma noite inteira de dado inutilizável com aparência
de dado bom — e a deriva não é recuperável na análise, porque não há como distingui-la de
movimento. O caso 2 teria aparecido só depois de uma noite de coleta na placa.

**Como não repetir.** As quatro regras que saíram do `HW-05` e viraram arquitetura:

1. ⚙️ **Nada na medição espera por conectividade.** Saíram `while (!Serial)`, o `while(1)` no
   `mpu.begin()` falho e a conexão síncrona no laço.
2. ⚙️ **Perda de cadência vira campo no dado.** `EPOCA_INCOMPLETA` e `EPOCA_VAZIA`, e a época
   vazia **ocupa lugar no buffer** — custa 32 bytes dizer "aqui não houve medida", e sem isso a
   análise veria duas épocas encostadas e concluiria que a noite foi medida sem falha.
3. ⚙️ **A grade de tempo é absoluta:** `t0 + k·período`, nunca `última + período`. Na segunda
   forma todo atraso de execução entra permanentemente na base de tempo e nunca mais sai.
4. ⚙️ **Recusar é melhor que emitir plausível.** `AcumuladorDeFeatures::fechar()` **recusa a
   época** a 3 amostras, em vez de emitir um vetor plausível e errado — e é por isso que a
   cadência de 0,1 Hz apareceu como ausência de feature, e não como feature ruim (`ARQ-01`).
5. ⚙️ **Degradação exata ou nenhuma.** O buffer funde épocas por `pico-da-magnitude`, que é
   associativo, então a fusão é exata. E as features ficaram **fora** do `Epoca` justamente
   porque 3 das 7 grandezas **não** fundem exato — embuti-las criaria três números que a
   degradação corromperia em silêncio, dentro de todas as faixas do contrato.
6. ❓ **Pergunta de revisão:** *se a premissa quebrar em campo, o dado fica ausente ou fica
   errado-com-cara-de-certo?* Só a primeira é aceitável.

---

## §8 — A média esconde o caso que importa

**O padrão.** Uma estatística agregada favorável torna plausível uma hipótese que falha
exatamente onde o fenômeno acontece.

**Onde aconteceu.**

| # | Ocorrência | Procedência |
|:-:|---|---|
| 1 | **`d_angulo ≈ \|Δinclinacao_rel\|`** tem correlação 0,904 e erro mediano de **0,010 grau** — e erro máximo de **149,4 graus**, crescendo monotonicamente com o tamanho da virada (31,1 graus de erro médio na faixa de 60–180°). A aproximação é excelente onde não há virada e falha nas **5,16 %** de épocas que *são* viradas — que é tudo o que a feature existe para capturar. **A mediana boa era a armadilha:** tornava a hipótese plausível exatamente onde nada acontece. | Diário 2026-09-29; `ml/testes/test_redundancia_angular.py` |
| 2 | **A acurácia global não é informativa neste domínio.** Um classificador trivial que atribua tudo a "sono" alcança acurácia próxima à de métodos estabelecidos, e tem **κ exatamente 0**. | Diário 2026-09-14 (`ML-02`); `LIMITACOES-TCC.md` X.4 |

**O que custou.** No caso 1, nada — a medição foi feita antes de a aproximação ser adotada, e
derrubou a hipótese que teria encolhido o registro. É o exemplo de um acerto, e está aqui porque
o que o produziu é replicável: **medir a aproximação estratificada por faixa, não só no
agregado.**

**Como não repetir.**

1. ⚙️ **Erro estratificado por faixa**, não só mediana e correlação. A tabela por faixa de
   `d_angulo` é o formato.
2. ⚙️ **Baseline trivial medido na própria coorte**, sempre, e κ ao lado de acurácia. Toda
   comparação do trabalho é contra o trivial da própria coorte, porque κ depende da prevalência
   e os valores de coortes diferentes **não são comparáveis entre si**.
3. ❓ **Pergunta de revisão:** *onde esta média erra mais, e esse lugar é justamente o que me
   interessa?*

---

## §9 — Checklist de revisão

Sete perguntas, uma por padrão. Cada uma existe porque o projeto pagou por não a ter feito.

- [ ] **§1** — Se eu quebrasse de propósito a coisa que esta verificação protege, ela ficaria
      vermelha? **Em que máquina?**
- [ ] **§2** — Quem precisa saber disto vai abrir o arquivo onde eu escrevi? Este achado virou
      **item**, ou ficou observação?
- [ ] **§3** — De onde veio este número? Ele é *medição*, *especificação*, *cálculo* ou
      *estimativa* — e isso está escrito ao lado dele?
- [ ] **§4** — Este teste já falhou alguma vez? Eu sei fazê-lo falhar?
- [ ] **§5** — Eu abri o artefato, ou li sobre ele?
- [ ] **§6** — Este "sucesso" foi verificado ou assumido? Como ele se pareceria se tivesse
      falhado?
- [ ] **§7** — Se a premissa quebrar em campo, o dado fica **ausente** ou fica
      **errado-com-cara-de-certo**?

---

## O que este documento não cobre

Registrado para que a ausência não passe por completude.

| Lacuna | Por quê |
|---|---|
| Padrões anteriores a 2026-04-29 | Mesmo motivo do diário: anterior ao versionamento. |
| Qualquer padrão de hardware | Nada foi medido no dispositivo físico. Os 8 pinos do MPU6050 não estão soldados, e **não há uma só lição deste documento que venha de bancada.** Quando houver, é provável que esta seja a seção mais cara do arquivo. |
| Padrões de frontend | Os 15 arquivos modificados e não commitados em `frontend/` são de outra sessão de trabalho, não foram lidos, e não estão no histórico. O que há de frontend aqui (`UI-10`) entrou pelo lado do backend. |
| Frequência real dos padrões | A contagem de ocorrências do índice é sobre **o que está registrado**, não sobre o que aconteceu. Os padrões §1 e §4 são provavelmente subcontados, porque só se descobre instrumento defeituoso quem procura. |

---

## Fontes

- `docs/DIARIO-DE-ENGENHARIA.md` — procedência de toda ocorrência citada aqui. Onde este
  arquivo e o diário divergirem, **o diário vence**: ele é o registro primário.
- `docs/BACKLOG-COMPLETO.md` — os itens nomeados (`ARQ-01`, `FW-08`, `DATA-07e`, `PARID-C2`,
  `GIT-05`) e o procedimento de reconferência local.
- `docs/LIMITACOES-TCC.md` — onde o limite medido vira material de defesa.
- Instrumentos citados: `scripts/conferir_docs_versionados.py`, `scripts/calculos_tcc.py`,
  `scripts/estudo_buffer.py`, `firmware/nucleo/Makefile` (alvos `sintaxe`, `capacidade`,
  `dourado`, `mutacao`), `ml/testes/verificar_vetor_dourado_por_mutacao.py`,
  `web-app/tests/rls/verificar_por_mutacao.py`.
