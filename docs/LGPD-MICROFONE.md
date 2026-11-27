# Microfone e LGPD — estudo antes da implementação

**Estudo** · 2026-11-27 · item de backlog `LGPD-17` · experimento relacionado `EXP-01`

> **Estado em 27/11/2026: nada disto está implementado.** Nenhum aparelho do sistema usa
> microfone. O dispositivo do travesseiro não tem um, e o aplicativo para Android não pede a
> permissão de áudio (o `AndroidManifest.xml` não declara `RECORD_AUDIO`). Este documento
> existe **antes** do código, de propósito: decidir o que coletar, com que base e com que
> limites é mais barato agora do que depois.
>
> **Por que o microfone entrou na conversa.** A pesquisa que embasa o `EXP-01` mostrou que o
> REM se distingue pela respiração irregular, e que o som capta a respiração. As fontes e os
> números estão no documento de pesquisa do autor (fora do repositório). Aqui só entra o
> que afeta o tratamento de dados.
>
> ⚠️ **Não é parecer jurídico.** Os artigos citados foram conferidos no texto compilado da
> Lei nº 13.709/2018 no Planalto, em 27/11/2026, e não citados de memória. Isso garante que a
> citação existe e diz o que se afirma. Não garante que as medidas bastem.

---

## 1. O que está em estudo

Dois caminhos, que compartilham o mesmo processamento (o núcleo C++ que o app já compila
pelo NDK, como faz o `coletor_celular.h`):

| Caminho | Sensor | Onde fica | Quando |
|---|---|---|---|
| **App** | microfone do próprio celular | na fronha, no colchão ou na mesa de cabeceira | primeiro, porque não depende de compra |
| **Travesseiro** | INMP441 (MEMS, I²S), ligado ao ESP32 | dentro do travesseiro | quando o sensor chegar e passar no teste de bancada (`EXP-01`) |

**O que o processamento faz com o som, nos dois caminhos:** a cada bloco de 20 ms, calcula
**um número**, o nível sonoro (valor eficaz, RMS, em decibéis), e descarta as amostras.
Desses níveis saem as medidas por época de 30 s que interessam: frequência e regularidade
da respiração, presença de ronco, pausas. **O som em si nunca é gravado, guardado nem
enviado.**

---

## 2. Que dado é esse, para a lei

### 2.1 É dado pessoal sensível

A série de níveis sonoros de uma pessoa dormindo, e as medidas de respiração e ronco
derivadas dela, descrevem o corpo de uma pessoa identificada. A política já trata a série
de **movimento** como dado de saúde por precaução (seção 2.5). A série de **som da
respiração** está mais perto ainda de um dado de saúde: ronco e pausas respiratórias são
justamente o que se investiga na apneia.

> **Art. 5º, II:** *"dado pessoal sensível: dado pessoal sobre [...] dado referente à
> saúde [...] quando vinculado a uma pessoa natural"*.

**Conclusão:** tratar como **dado pessoal sensível (saúde)**, com o mesmo regime da série de
movimento.

### 2.2 Uma diferença de natureza em relação ao movimento

O acelerômetro mede só quem está deitado sobre o aparelho. **O microfone mede o quarto.**
Isso traz dois problemas que o movimento não tem:

1. **Pessoas que não consentiram.** Quem dorme junto, quem conversa no quarto, o ronco de
   outra pessoa. Elas são titulares de um dado que não consentiram em fornecer.
2. **Contaminação da medida.** O ronco de outra pessoa entra na série como se fosse do
   usuário. É um problema científico, não só jurídico. O estudo de Tran et al. (2023), sobre
   áudio de celular em casa, declara entre as limitações que os dados foram coletados com
   pessoas dormindo sozinhas no quarto.

**A mitigação principal é técnica (seção 4): sem amostra guardada, não há fala para ouvir
depois.** Ela não elimina o problema, porque o nível sonoro de outra pessoa ainda entra na
série. Por isso a política e a tela de consentimento devem dizer isso com clareza (seção 6).

---

## 3. Base legal

> **Art. 11, I:** o dado sensível só pode ser tratado *"quando o titular [...] consentir, de
> forma específica e destacada, para finalidades específicas"*.
>
> **Art. 8º, § 4º:** *"O consentimento deverá referir-se a finalidades determinadas, e as
> autorizações genéricas para o tratamento de dados pessoais serão nulas."*

**Conclusão: o microfone precisa de um consentimento próprio, separado do de movimento.**
O consentimento atual (`VERSAO_DO_CONSENTIMENTO = "2026-11-22"`) fala só em "o movimento
do aparelho". Usá-lo para cobrir o som seria estendê-lo a uma finalidade que ele não
nomeia.

Desenho proposto:

- **O microfone fica desligado por padrão** e é um opcional à parte. Quem não ligar usa o
  serviço exatamente como hoje.
- **Uma tela própria**, no mesmo padrão da de movimento (caixa "li e concordo", botão que
  só habilita depois), com a sua versão e a data registradas pelo servidor.
- **Duas permissões, as duas necessárias:** o consentimento no Smart Dormio e a permissão
  de microfone do Android (`RECORD_AUDIO`), que o sistema pede na hora. Uma não substitui a
  outra.
- **Revogar é desligar o microfone**, a qualquer momento, sem perder o resto da conta.

**Se o uso for em pesquisa** (participantes recrutados, com termo e CEP), vale o que a
política já diz na seção 3: só com termo de participação próprio. O áudio precisa constar
desse termo e do protocolo do CEP.

---

## 4. Minimização e segurança

> **Art. 6º, III (necessidade):** *"limitação do tratamento ao mínimo necessário para a
> realização de suas finalidades"*.
>
> **Art. 46:** os agentes de tratamento *"devem adotar medidas de segurança, técnicas e
> administrativas aptas a proteger os dados pessoais"*.

| Medida | Como | Onde se verifica |
|---|---|---|
| **Nenhuma amostra de som sai do processamento** | O núcleo recebe o bloco, calcula o nível e descarta o bloco. Nada vai para arquivo, memória persistente, rede ou registro de depuração | Teste do núcleo: dado um bloco, a única saída é o nível |
| **Só o mínimo sai da memória do aparelho** | No arquivo do celular, no servidor e na exportação, só as **medidas por época** (como já acontece com o movimento). A série de 50 níveis por segundo fica só na memória de trabalho (seção 4.1) | Contrato de dados (`DATA-CONTRACT.md`), versão nova; teste do núcleo |
| **Teste de bancada sem gravar o som** | O sketch do `EXP-01` imprime só o nível a cada 20 ms, nunca as amostras. Como o nível ainda revela quando alguém fala (seção 4.1), a bancada é feita **com o autor sozinho no quarto** | Código do sketch; protocolo |
| **Indicador visível** | O Android mostra o indicador de microfone em uso; a notificação fixa da noite deve dizer "medindo movimento e som" | Tela do app |
| **Mesmo armazenamento, mesma retenção** | Os arquivos locais seguem a regra da seção 2.3 da política, e os dados da conta a da seção 7 | Política |

### 4.1 O nível a cada 20 ms protege a fala? Conferido em 27/11: **não como estava escrito**

A primeira versão deste documento dizia que um nível a cada 20 ms "não deveria" permitir
reconstruir fala inteligível. Conferida na literatura no mesmo dia, a frase **não se
sustenta como garantia**:

- **A informação da fala que o ouvido usa no tempo está justamente nas variações lentas.**
  Xu e Pfingst (2008, *Hearing Research* 242:132–140, [PMC2610393](https://pmc.ncbi.nlm.nih.gov/articles/PMC2610393/),
  texto lido) resumem: o reconhecimento da fala em inglês *"só se beneficia das frequências
  do envelope abaixo de 16 a 20 Hz"*. Um nível a cada 20 ms é o envelope amostrado a 50 Hz,
  e **cobre essa faixa inteira**.
- **O que falta ao nosso sinal é a divisão em faixas de frequência.** O nível é um só, para
  todo o espectro. Na literatura de *vocoders*, a fala volta a ser bem entendida com **três
  ou quatro faixas** de envelope: Dorman, Loizou e Rainey (1997, *JASA* 102:2403, texto lido)
  resumem Shannon et al. (1995) como "escores quase perfeitos" com *"três ou quatro faixas de
  ruído"*; Xu e Pfingst, como "4 canais bastam" para ≥ 85% de acerto em consoantes, vogais e
  frases. **Com uma faixa só, o caso do Dormio, não encontrei o número de inteligibilidade
  de frases em fonte lida.** O artigo original de Shannon et al. (1995) não pôde ser aberto
  (servidor recusou a conexão).
- **Inteligibilidade não é a única coisa que vaza.** Mesmo sem palavras, a série mostra
  **quando alguém fala, por quanto tempo e em que ritmo**. Trabalhos de segurança mostram
  que sensores de baixa taxa revelam mais do que se espera: Michalevsky, Boneh e Nakibly
  (2014, USENIX Security, "Gyrophone") relatam identificar quem fala e dígitos falados a
  partir do giroscópio de celular, a cerca de 200 Hz. 🟡 *Visto só em resumo; e é uma forma
  de onda a 200 Hz, não um envelope de faixa única, então não se transfere diretamente.*

**Conclusão:** o nível a cada 20 ms **reduz muito** o que se pode extrair da fala, mas **não
é garantia** de que nada se extraia. Portanto, a série de 50 valores por segundo **não deve
sair da memória do aparelho**:

| Onde | O que existe |
|---|---|
| Memória de trabalho do aparelho, por segundos | O nível a cada 20 ms, só para calcular a época |
| Arquivo no celular, servidor, CSV de exportação | **Só as medidas por época de 30 s** (frequência e regularidade da respiração, ronco, pausas) |
| Bancada (`EXP-01`) | O nível a cada 20 ms vai para o computador do autor, **com o autor sozinho no quarto**, porque é preciso para medir o pico respiratório. Nunca em participante |

Resumir meio minuto num punhado de números elimina a faixa do envelope que importa à fala
(abaixo de 16–20 Hz), porque a época é amostrada uma vez a cada 30 s. *Isso é dedução do
próprio raciocínio, não resultado de fonte lida.* É isso que a política poderá dizer, depois
do teste abaixo, e não "o nível de 20 ms protege".

> ⚠️ **O que ainda falta:** um teste próprio que confirme que as medidas por época não
> distinguem "silêncio", "fala" e "respiração" além do que se pretende (por exemplo, marcar
> fala como ruído a descartar). Fica no `EXP-01`.

---

## 5. Regras do Android (conferidas na documentação, 27/11/2026)

Fontes: *developer.android.com*, páginas "Foreground service types", "Restrictions on
starting foreground services from the background" e `MediaRecorder.AudioSource`.

- O serviço da noite hoje é do tipo `health`. Para o microfone, precisa também do tipo
  **`microphone`**, da permissão **`FOREGROUND_SERVICE_MICROPHONE`** e da permissão
  **`RECORD_AUDIO`**, concedida pelo usuário.
- **Não se pode iniciar o serviço com microfone com o app em segundo plano.** No Android 14 ou
  superior, a tentativa lança `SecurityException`. Também não se pode iniciá-lo pelo aviso de
  inicialização do sistema (`BOOT_COMPLETED`). Hoje a noite começa por um toque do usuário
  (`MainActivity` e `NoitePlugin`), o que é permitido. **Um início automático futuro, pelo
  lembrete de dormir por exemplo, não poderia ligar o microfone.**
- A fonte de áudio `UNPROCESSED` entrega o som bruto *"se disponível"*. Se não estiver,
  *"se comporta como `DEFAULT`"*. O aplicativo deve **registrar qual fonte usou**, porque o
  processamento do sistema altera os níveis.

---

## 6. O que muda nos documentos, e em que ordem

> **Art. 9º, § 2º:** se houver mudança de finalidade incompatível com o consentimento
> original, *"o controlador deverá informar previamente o titular sobre as mudanças"*.
>
> **Art. 8º, § 6º:** em alteração das informações do art. 9º, o controlador deve *"informar
> ao titular, com destaque de forma específica do teor das alterações"*.
>
> **Art. 6º, VI (transparência):** *"informações claras, precisas e facilmente acessíveis"*.

A política tem uma regra própria (notas de redação): **descrever o que o sistema faz hoje,
não o que se pretende.** Por isso a mudança vai em duas etapas.

### Etapa 1 — agora (`LGPD-17`)

- **Corrigir a seção 2.4.** Ela diz *"O aparelho não tem microfone"*. É verdade para o
  travesseiro, mas o celular tem microfone, só que o app não o usa. A frase passa a dizer as
  duas coisas.
- **Anunciar a mudança em estudo**, como a seção 10 da própria política exige para mudança
  material ("serão anunciadas antes de entrarem em vigor"), sem descrevê-la como existente.
- **Este documento**, com o texto da etapa 2 já redigido (seção 7).

Nada muda no consentimento: a versão continua `2026-11-22`, e ninguém vê a tela de novo.

### Etapa 2 — no release que ligar o microfone

Na mesma PR do recurso, nunca antes:

1. Política: seções 2.2, 2.3, 2.4, 2.5, 3, 4 e 10 com o texto da seção 7 deste documento,
   ajustado ao que o código fizer de fato.
2. Consentimento: uma **tela e uma versão próprias para o microfone**. O consentimento de
   movimento não muda de versão só por isso.
3. `DATA-CONTRACT.md`: as medidas de som por época, versão nova.
4. Migração com número reservado, se as medidas forem para o servidor, e o
   `test_politica_cobre_as_colunas.py` cobrindo as colunas novas.
5. `AndroidManifest.xml`: o tipo `microphone`, as duas permissões novas.
6. Se houver participantes de pesquisa: o termo de participação e o protocolo do CEP com o
   áudio.

---

## 7. Texto preparado para a etapa 2 (não publicar antes)

> Rascunho. Só entra na política junto com o código, e cada frase deve ser conferida contra
> o que o código fizer de fato. Onde houver `[ ]`, o valor depende da implementação.

**Seção 2.2 — acrescentar:**

> **O som, se você ligar o microfone.** Desligado por padrão. Com ele ligado, o aplicativo
> usa o microfone do celular durante a noite [e o dispositivo do travesseiro, se tiver
> microfone, o dele]. **O som não é gravado.** O aparelho calcula o volume do som, instante a
> instante, e descarta o som em si; os volumes ficam só na memória, por alguns segundos.
> Deles, o aparelho calcula por época de 30 segundos [a frequência e a regularidade da
> respiração, a presença de ronco e as pausas], e **é só isso que é guardado e enviado**.

**Seção 2.4 — trocar a primeira linha por:**

> - **Gravação de áudio, imagem ou vídeo.** Nenhum aparelho grava som, imagem ou vídeo.
>   Com o microfone ligado (seção 2.2), o aparelho mede o volume do som e descarta o som em
>   si.

**Seção 2.5 — acrescentar:**

> As medidas de respiração e ronco também são tratadas como **dado de saúde**. E elas têm
> uma diferença importante em relação ao movimento: **o microfone mede o quarto, não só
> você.** Se outra pessoa dormir ou falar perto do aparelho, o volume dos sons dela entra nas
> medidas. O que foi dito não é guardado, porque nem o som nem os volumes instante a instante
> saem da memória do aparelho, mas a presença dela pode alterar as medidas. Se você não
> dorme sozinho, considere deixar o microfone desligado.

**Seção 4 — acrescentar:**

> **O microfone tem consentimento próprio**, separado do de movimento, numa tela própria,
> com a data e a versão registradas. Sem ele, o microfone não liga. Você o revoga
> desligando o microfone.

---

## 8. Relatório de impacto

> **Art. 38:** a autoridade nacional *"poderá determinar ao controlador que elabore relatório
> de impacto à proteção de dados pessoais, inclusive de dados sensíveis"*. O parágrafo único
> lista o conteúdo mínimo: os tipos de dados, a metodologia de coleta e de segurança, e as
> medidas de mitigação.

A lei diz que a autoridade **pode determinar** o relatório. Isto **não é** uma afirmação de
que ele é obrigatório aqui. Mas as seções 2 a 5 deste documento já cobrem o conteúdo mínimo
do parágrafo único. Se o orientador ou o CEP pedirem um relatório, ele sai daqui.

---

## 9. Riscos em aberto

| Risco | Situação | Item |
|---|---|---|
| O escopo do TCC diz "acelerométrico" (`LIMITACOES-TCC.md`, X.5) | Decisão do autor e do orientador | `EXP-01` |
| O CEP ainda não cobre áudio | Pendente com o orientador | — |
| A série de níveis a cada 20 ms cobre a faixa do envelope que carrega a fala (abaixo de 16–20 Hz) | **Conferido em 27/11 (seção 4.1).** Decisão: a série não sai da memória; só medidas por época são guardadas e enviadas. Falta o teste próprio de que as medidas por época não revelam fala | `EXP-01` |
| Outras pessoas no quarto | Mitigado (sem amostra guardada), não eliminado. Declarado no texto da etapa 2 | `LGPD-17` |
| Revisão jurídica da política | A política diz no topo "Não publicar sem revisão jurídica" | `LGPD-01` |
| Início automático da noite com microfone (lembrete) | O Android proíbe. Se um dia o lembrete iniciar a noite, o microfone fica fora | — |

---

## Procedência

- **Lei nº 13.709/2018**, texto compilado em
  `https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709compilado.htm`, lido em
  27/11/2026: arts. 5º (II, XII e XVII), 6º (I a VI), 7º (I), 8º (§§ 4º e 6º), 9º (*caput* e
  § 2º), 11 (I), 38 e 46.
- **Android**, *developer.android.com*, lido em 27/11/2026: "Foreground service types"
  (seção *Microphone*), "Restrictions on starting foreground services from the background"
  e `MediaRecorder.AudioSource`.
- **Código**, lido em 27/11/2026 sobre `develop` `7a21e9f`:
  `frontend/android/app/src/main/AndroidManifest.xml` (tipo `health`, sem `RECORD_AUDIO`),
  `ServicoDaNoite.java`, `NoitePlugin.java`, `MainActivity.java`,
  `ReceptorDeInicializacao.java` (só reagenda o lembrete), `firmware/nucleo/coletor_celular.h`,
  `frontend/src/lib/consentimento.ts` (versão `2026-11-22`).
- **Xu e Pfingst (2008)**, *Hearing Research* 242:132–140, DOI 10.1016/j.heares.2007.12.010,
  PMC2610393, lido em 27/11/2026: o envelope abaixo de 16–20 Hz; 4 canais bastam.
- **Dorman, Loizou e Rainey (1997)**, *J Acoust Soc Am* 102:2403, DOI 10.1121/1.419603, lido
  em 27/11/2026: o resumo de Shannon et al. (1995), três ou quatro faixas. **Shannon et al.
  (1995), *Science* 270:303–304, não foi lido** (o servidor da cópia recusou a conexão).
- **Michalevsky, Boneh e Nakibly (2014)**, "Gyrophone", USENIX Security: **visto só em
  resumo de busca**, não lido.
- **Tran et al. (2023)**, *J Med Internet Res* 25:e46216, DOI 10.2196/46216, texto completo
  lido em 27/11/2026: a limitação de os dados terem sido coletados com pessoas dormindo
  sozinhas.
