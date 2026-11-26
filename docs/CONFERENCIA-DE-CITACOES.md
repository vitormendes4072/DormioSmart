# Conferência das citações do texto do TCC (DOC-06b)

> **Feita em 05/11/2026** sobre o "Copy of Produto 5" (Google Docs, 30/09/2026), o texto vigente na
> data. As correções prontas para colar estão fora do Git, em
> `../documento/CORRECOES-CITACOES.md`.
>
> **Limite desta conferência:** quem leu as fontes foi a ferramenta, não os autores. O `DOC-06b`
> pede que os autores leiam o que citam; esta página diz **o que ler primeiro** e o que cada fonte
> sustenta.

## Método

1. As 22 referências da lista e as 35 frases do texto que as citam foram extraídas do documento.
2. Os artigos científicos foram localizados pelo DOI na Europe PMC: metadados e resumo pela API
   de busca; texto completo (`fullTextXML`) onde a afirmação dependia de detalhe. Os sítios das
   editoras recusaram acesso automatizado (403).
3. As fontes técnicas foram abertas no endereço da referência; a lei, no sítio do Planalto.
4. Cada frase recebeu um veredito: **confere**, **imprecisa** (a fonte sustenta parte, ou outra
   coisa), **contradiz** (a fonte afirma o contrário), **fonte inacessível** ou **não conferida**.

## Resultado

**Dados bibliográficos:** autores, revista, volume, número, páginas e DOI conferem em todos os
nove artigos.

| Referência | Onde é citada | Veredito | O que a fonte sustenta |
|---|---|---|---|
| SKARPSNO et al., 2017 | 5.2 | ❌ **Contradiz** | Movimento noturno associado a sexo, idade, IMC e tabagismo, em 664 trabalhadores. **Sem associação com sintomas de insônia** (discussão do artigo). O texto afirmava a associação. |
| TDK INVENSENSE, 2026 (página de produto) | 5.4, Quadro 1, 6.4.2, 6.4.3 | ❌ **Fonte inacessível** | O endereço responde "página não encontrada" (05/11). Os valores citados (16 bits, ±8 g, 0x68/0x69, FIFO de 1 024 B, correntes) estão na folha de dados PS-MPU-6000A-00, rev. 3.4 (2013), que o repositório já usa (`scripts/calculos_tcc.py`). |
| YUAN et al., 2024 | Introdução e 5.1 | ⚠️ **Imprecisa** | Revisão sistemática de **actigrafia de pulso** no estadiamento do sono (8 estudos). Não trata de combinar sinais, que é o que as duas frases afirmam. |
| YUAN et al., 2024 | 5.2 | ⚠️ **Imprecisa** | Conclui que o desempenho é baixo e que a evidência não sustenta nem refuta a validade. O texto particularizava "REM e sono profundo", o que a conclusão não faz. |
| SMITH et al., 2018 | 5.2 | ⚠️ **Imprecisa** | Dados objetivos consistentes **para alguns parâmetros**, em insônia, ritmo circadiano e outros distúrbios; não confiável para movimentos periódicos dos membros. "Método válido para avaliação de distúrbios" é mais largo. |
| ESPRESSIF SYSTEMS, 2026 (guia de modos de sono) | 6.4.1 (correntes) | ⚠️ **Imprecisa** | O guia descreve os modos e as fontes de despertar, sem valor de corrente. Os 10 µA e 0,8 mA estão na *ESP32 Series Datasheet*, Tabela 4-2. |
| SMITH et al., 2018 | 5.1 | ✅ Confere | Actigrafia infere repouso e atividade por acelerômetro. |
| DE FAZIO et al., 2022 | Introdução e 5.1 | ✅ Confere | Revisão de dispositivos e sinais para o sono, inclusive em casa: microfone, acelerômetro, ECG, EEG. |
| BLIWISE, 2023 | 5.2 | ✅ Confere pelo título | História da medição de movimentos no sono. Sem resumo público; não lido por inteiro. |
| LIU et al., 2025 | 5.2 e 5.8 | ✅ Confere | 8 acelerômetros sob o colchão, 30 estudantes, 98,42 % de acurácia média em seis posturas. |
| BOIKO et al., 2023 | 5.2 | ✅ Confere | Um acelerômetro num suporte sob o colchão; frequências cardíaca e respiratória em 23 pessoas. |
| YOSHIHI et al., 2021 | 5.2 | ✅ Confere | Acelerômetro preso à cabeça; 8 homens, duas noites; 74,6 % de acurácia em quatro classes. O texto não dá números; poderia. |
| WALCH et al., 2019 | 5.2 e 6.6 | ✅ Confere | Acelerometria bruta e frequência cardíaca do relógio, com rótulos de polissonografia. |
| ESPRESSIF SYSTEMS, 2026 (guia) | 1, 5.3, 5.5, Quadro 1, 6.4.2 | ✅ Confere | Modos de sono; o sono leve preserva memória e estado; EXT1 só em pinos RTC, e o GPIO27 está na lista. |
| BRASIL, 2018 | 6.3.3 | ✅ Confere | Art. 6º, III (necessidade); arts. 15 e 16 (término e eliminação, sem prazo fixo). |
| GIL, 2002, p. 17 | 6.1 | ✅ Confere | A passagem está na seção 1.2, que o sumário da 4.ª edição põe na p. 17 (cópia digitalizada). |
| GIL, 2002, p. 41; BELLO, 2005, p. 50 e p. 17; ELKINGTON, 1997 | 6.1 e 3 | Não conferida | Sem cópia acessível. Conferir no exemplar. |
| [AUTOR], 2026 | 1, 5.7, 6.3.6 | ✅ Confere | O repositório do projeto. |

**Na lista, sem citação no texto:** W3C (*DeviceOrientation*), SUPABASE (*Auth*), META PLATFORMS
(*React*); também as duas normas da ABNT e as regras do curso. As três primeiras documentam coisas
que o texto usa (coleta pelo celular, autenticação, interface), e a correção é citá-las ali.

**Afirmação sem citação, nas inserções a colar:** o ENMO, na 6.4.4 nova (`CALC-03`). A fonte que
define a métrica é VAN HEES et al. (2013), *PLoS ONE* 8(4): e61691, conferida na Europe PMC; a
inserção já foi ajustada.

## Roteiro de leitura dos autores (checklist)

> ✏️ **16/11/2026.** Esta seção substitui a lista "O que os autores precisam ler antes da banca",
> de 05/11, mantendo a mesma ordem de risco. O `DOC-06b` fecha quando todas as linhas abaixo
> estiverem marcadas.
>
> **Estado em 16/11:** o "Copy of Produto 5" não é editado desde 30/09 (metadado do Drive, conferido
> em 16/11). As correções de citação de 05/11, entre elas a do Skarpsno, **ainda não estão no
> texto**. Elas estão em `../documento/CORRECOES-CITACOES.md`, fora do Git, prontas para colar.

**Como usar.** Para cada fonte: abrir no endereço indicado, ler só o trecho apontado e responder à
pergunta. Se a resposta for diferente da esperada, o texto do TCC está errado nesse ponto, e não o
roteiro. Ao terminar, escrever quem leu e a data na última coluna e fazer o commit. Os links foram
abertos em 16/11 e responderam.

| # | Fonte | Onde abrir | Ler | Pergunta (resposta esperada) | Lido por / data |
|---|---|---|---|---|---|
| 1 | SKARPSNO et al., 2017, *Nat Sci Sleep*, DOI `10.2147/NSS.S145777` | https://pmc.ncbi.nlm.nih.gov/articles/PMC5677378/ | Resultados e Discussão | O movimento noturno se associou a sintomas de insônia? (**Não.** Se associou a sexo, idade, IMC e tabagismo.) Conferir também o número de participantes que o texto cita (664). | |
| 2 | YUAN et al., 2024, *J Sleep Res*, DOI `10.1111/jsr.14143` | https://pmc.ncbi.nlm.nih.gov/articles/PMC7618292/ | Resumo, Discussão e Conclusão | A revisão trata de combinar sinais de vários sensores? (**Não**, só actigrafia de pulso.) Ela conclui que a actigrafia falha especificamente em REM e sono profundo, ou que o desempenho no estadiamento é baixo e a evidência é insuficiente? (**A segunda.**) | |
| 3 | SMITH et al., 2018, *J Clin Sleep Med*, revisão sistemática e meta-análise, DOI `10.5664/jcsm.7228` | https://pmc.ncbi.nlm.nih.gov/articles/PMC6040804/ | Resumo e Conclusões | A revisão diz que a actigrafia é "método válido" em geral, ou que dá dados consistentes para alguns parâmetros, e não serve para movimentos periódicos dos membros? (**A segunda.**) Atenção: a diretriz clínica da AASM é outro artigo (`10.5664/jcsm.7230`); conferir qual dos dois está na lista de referências. | |
| 4a | Folha de dados do MPU-6000/MPU-6050, PS-MPU-6000A-00, rev. 3.4 (2013) | Site da TDK InvenSense, buscando `PS-MPU-6000A-00` (o endereço antigo da página de produto não abre mais) | §6.2 (sensibilidade, ruído, filtro, taxa) e §6.4 (correntes) | Os números do texto (16 bits, ±8 g, endereços 0x68/0x69, FIFO de 1 024 B, correntes) estão lá? (**Sim.**) Conferir a revisão do PDF baixado: o `docs/CALCULOS-TCC.md` cita a rev. 3.4 e, num trecho, a rev. 3.2. | |
| 4b | *ESP32 Series Datasheet*, Espressif | https://documentation.espressif.com/esp32_datasheet_en.pdf | A tabela de consumo por modo de energia | Os ~10 µA em *Deep Sleep* e ~0,8 mA em sono leve estão lá? (**Sim, segundo a conferência de 05/11.**) Anotar a versão e o ano da capa: entram na referência nova (correção 6 do arquivo de correções). | |
| 5 | VAN HEES et al., 2013, *PLoS ONE*, DOI `10.1371/journal.pone.0061691` | https://pmc.ncbi.nlm.nih.gov/articles/PMC3634007/ | Métodos, onde o ENMO é definido | O ENMO é a norma do vetor menos 1 g, com os negativos zerados? (**Sim.**) É a métrica que a 6.4.4 nova descreve. | |
| 6 | GIL, 2002, p. 41; BELLO, 2005, p. 17 e p. 50; ELKINGTON, 1997 | Exemplar físico ou digital | As páginas citadas | A frase do TCC está na página indicada? (Não conferido em 05/11: não havia cópia acessível.) | |

**O que este roteiro não faz.** Não resume os artigos: resumo não substitui leitura, e a banca
pergunta a quem escreveu. Também não altera o texto do TCC: colar as correções continua sendo
passo dos autores, começando pela do Skarpsno.
