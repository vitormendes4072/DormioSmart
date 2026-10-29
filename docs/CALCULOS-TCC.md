# Modelos quantitativos — texto pronto para o TCC (`CALC-01` a `CALC-04`)

> **Como usar este arquivo.** O que está entre as linhas `── TEXTO ──` é redigido em tom
> acadêmico e pode ser colado no documento com ajustes mínimos de numeração e de referência.
> O que está fora delas são **notas para você**, não para o texto final. A convenção é a
> mesma de `docs/LIMITACOES-TCC.md` e de `docs/RESULTADOS-TCC.md`, e os três textos são
> feitos para conviver: este deriva os números do dispositivo, o de resultados apresenta o
> que foi medido, o de limitações declara os limites com que tudo deve ser lido.
>
> **Fundamentação.** Diferentemente do `RESULTADOS-TCC.md`, cujos números são todos
> **medidos**, e do `LIMITACOES-TCC.md`, cujos números vêm em boa parte da **literatura**,
> este arquivo mistura as três naturezas de número de propósito — e por isso **cada
> afirmação numérica do texto declara qual delas é**. A convenção está na abertura da seção
> Z e é o principal compromisso metodológico do capítulo.
>
> **Reprodutibilidade.** Todo número calculado neste arquivo sai de
> **`scripts/calculos_tcc.py`**. O script imprime o relatório completo e, ao final, **confere
> as asserções contra o que já estava escrito nos outros documentos do repositório** — se
> alguém mudar uma constante e um número publicado deixar de sair, ele falha:
>
> ```bash
> python3 scripts/calculos_tcc.py            # relatório completo + conferência
> python3 scripts/calculos_tcc.py --conferir # só a conferência; sai != 0 se divergir
> ```
>
> **Sugestão de posição:** no Desenvolvimento, logo após a apresentação da arquitetura
> (`DIAG-01`) e antes da seção de firmware. A ordem interna (física → índice → elétrica →
> energia) não é arbitrária: a seção de energia depende da taxa de amostragem derivada na
> seção de física, e a inverte quem quiser ler o capítulo de trás para frente.

---

## O mapeamento adotado, e por que ele não é o do backlog linha a linha

Do mesmo modo como foi feito em `docs/diagramas/README.md`, o mapeamento entre o que o
backlog pede e o que este arquivo entrega é declarado antes de qualquer número.

O `docs/BACKLOG-COMPLETO.md` define os quatro itens assim:

| Backlog | O que pede |
|---|---|
| `CALC-01` | Modelo de energia/autonomia: corrente por estado, *duty cycle*, `I_média`, `autonomia = C/I_média`. Expõe o limite do DevKit V1 → embasa o `HW-02`. É predição; a medição é o `VAL-02` |
| `CALC-02` | Física do acelerômetro: força específica, `\|a\|`, resolução, ruído, Nyquist. E **por que 21 Hz e não 260 Hz** (`FW-06`) |
| `CALC-03` | Índice de atividade e derivação do limiar `g ± k·σ`. **Nota do próprio backlog:** já resolvido pelo `ML-01`; o item *virou transpor para o texto, não decidir* |
| `CALC-04` | Análise elétrica: pull-down de 10 kΩ, pull-ups do I2C, níveis 3,3 V, fonte de despertar |

Decisão tomada: **preservar a numeração do backlog** — renumerar quebraria as referências
cruzadas no `ROADMAP.md`, no `SINTESE-PESQUISA-E-CAMINHOS.md` e no próprio backlog — mas
**reordenar a exposição** e **recortar um dos itens**:

| Seção do texto | Item | O que muda em relação ao backlog |
|---|---|---|
| `Z.1` Física da medição | `CALC-02` | Vem **primeiro**, e não segundo: a taxa de amostragem que ele deriva é premissa do `CALC-01`. Escopo ampliado com a comparação ±2 g × ±8 g, que o backlog não pede e que decide uma escolha de projeto |
| `Z.2` Índice de atividade | `CALC-03` | **Recortado.** A parte "transpor o índice de atividade" está entregue; a parte "derivar o limiar `g ± k·σ`" **não produz número útil**, e a seção Z.2.3 demonstra por quê em vez de produzi-lo. Ver a nota 🔧 1 ao final |
| `Z.3` Interfaces elétricas | `CALC-04` | Escopo ampliado: a janela de resistência do pull-up de I2C é derivada dos dois lados (dreno e tempo de subida), o que o backlog não pede e que é o que torna o `diagnostico-i2c.ino` interpretável |
| `Z.4` Energia e autonomia | `CALC-01` | Vem **por último**. Escopo ampliado com duas impossibilidades estruturais que a folha de dados impõe e que o backlog não antecipava, e **reduzido** onde faltam dados: a corrente de rádio e o consumo fixo da placa entram como **parâmetros declarados**, não como números citados. Ver a nota 🔧 3 |

**O que não está aqui:** o `CALC-05` (análise térmica com medição real) não entra — ele
depende da Etapa 0 (solda) e do protótipo energizado, e escrevê-lo agora seria inventar
número. Ele continua 🟡 no backlog, corretamente.

---

## Nota de enquadramento (leia antes de colar)

Três decisões estão embutidas no texto e conviria não desfazê-las na hora de colar:

1. **Nenhum número aparece sem sua natureza declarada.** Cálculo teórico, medição e
   estimativa são marcados no próprio texto. O projeto já perdeu números por essa confusão —
   o viés de −1,06 m/s² em Z, tratado como característica do sensor quando era medição
   através de contato ruim, é o exemplo registrado no `SINTESE-PESQUISA-E-CAMINHOS.md`.
2. **Valor de folha de dados vem com a condição de medição colada.** Os 400 µg/√Hz do
   MPU6050 são medidos **a 10 Hz, em fundo de escala ±2 g e taxa de saída de 1 kHz**; o
   projeto opera em ±8 g e com filtro de 21 Hz. A seção Z.1.3 usa esse valor e declara, no
   mesmo parágrafo, que a transposição é uma hipótese a ser verificada no `CAL-01`.
3. **Onde faltou dado, o texto diz que faltou.** A corrente de transmissão Wi-Fi e o consumo
   fixo da placa de desenvolvimento entram no modelo de energia como **faixas paramétricas
   declaradas**, com análise de sensibilidade, e não como valores citados. Uma predição com
   parâmetro honesto é defensável; uma predição com número inventado não sobrevive à primeira
   pergunta da banca.

---

── TEXTO ────────────────────────────────────────────────────────────────────

## Z. Modelos quantitativos do dispositivo

Este capítulo reúne os modelos quantitativos que fundamentam as decisões de projeto do
dispositivo. A exposição segue a ordem de dependência entre eles: estabelece-se primeiro o
que o transdutor mede e com que resolução e ruído (Z.1), deriva-se em seguida o índice de
atividade que resume cada época de observação (Z.2), analisam-se as interfaces elétricas que
ligam o transdutor ao microcontrolador (Z.3) e formula-se, por fim, o modelo de consumo e
autonomia, que depende da taxa de amostragem fixada em Z.1 (Z.4).

**Convenção de natureza dos valores.** Adota-se, em todo o capítulo, a distinção explícita
entre três naturezas de valor numérico, marcada no próprio texto:

- **Cálculo** — valor obtido por dedução a partir de parâmetros declarados. É exato em
  relação às premissas e só é tão válido quanto elas.
- **Especificação** — valor transcrito de folha de dados do fabricante, apresentado sempre
  com a **condição de medição** em que foi levantado. Especificação não é medição do exemplar
  utilizado: é o comportamento típico ou garantido de uma população de componentes.
- **Medição** — valor obtido por instrumentação no sistema construído, com procedimento
  registrado.
- **Estimativa** — valor arbitrado dentro de faixa justificada, na ausência das duas
  anteriores. Aparece apenas com a faixa explícita e acompanhado de análise de sensibilidade.

Cada seção encerra-se com a declaração de sua **faixa de validade**, isto é, das condições
fora das quais o modelo deixa de descrever o sistema. Essa declaração é parte do modelo, e
não ressalva acessória: um modelo cuja faixa de validade não está escrita não é verificável.

### Z.1 Física da medição acelerométrica

#### Z.1.1 A grandeza medida

O transdutor empregado é um acelerômetro microeletromecânico triaxial. A grandeza que um
acelerômetro desse tipo mede não é a aceleração do referencial inercial, e sim a **força
específica** — a resultante por unidade de massa de todas as forças não gravitacionais
aplicadas à massa de prova. Em consequência, um sensor **em repouso** sobre uma superfície
horizontal não indica zero: indica a reação normal que o sustenta, de módulo igual à
aceleração da gravidade local.

A magnitude do vetor de aceleração é obtida das três componentes ortogonais por

> |**a**| = √(a<sub>x</sub>² + a<sub>y</sub>² + a<sub>z</sub>²)

e, em repouso, vale aproximadamente 9,81 m/s², e não zero. Essa distinção é registrada
porque determina a definição da grandeza transmitida pelo dispositivo e o critério de
classificação dele derivado, ambos apresentados na seção de contrato de dados: a intensidade
de movimento é definida como |‖**a**‖ − g|, isto é, como o **afastamento da condição de
repouso**, e não como a magnitude bruta.

Registra-se ainda que ‖**a**‖ é **invariante a qualquer rotação** do referencial do sensor,
propriedade que se torna decisiva na seção Z.2: o dispositivo é alojado no interior de um
travesseiro, cuja orientação é arbitrária e muda ao longo da noite, de modo que toda grandeza
dependente de eixo é, nessa aplicação, uma grandeza dependente de como o objeto está deitado.

#### Z.1.2 Resolução

O componente converte cada eixo com um conversor analógico-digital de 16 bits, sobre um fundo
de escala selecionável por registrador. O passo de quantização decorre do fator de escala de
sensibilidade publicado pelo fabricante (*especificação*):

| Fundo de escala | Fator de escala | Passo de quantização | Equivalente |
|---|---:|---:|---:|
| ±2 g | 16 384 LSB/g | 0,0610 mg/LSB | 0,599 mm/s² |
| ±4 g | 8 192 LSB/g | 0,1221 mg/LSB | 1,197 mm/s² |
| ±8 g | 4 096 LSB/g | 0,2441 mg/LSB | 2,394 mm/s² |
| ±16 g | 2 048 LSB/g | 0,4883 mg/LSB | 4,788 mm/s² |

Fonte: TDK InvenSense, PS-MPU-6000A-00 Rev. 3.4, §6.2, com V<sub>DD</sub> entre 2,375 V e
3,46 V e temperatura ambiente de 25 °C. A configuração adotada neste trabalho é **±8 g**, à
qual corresponde resolução de **0,244 mg/LSB** (*cálculo* a partir da especificação).

A escolha de ±8 g em detrimento de ±2 g multiplica o passo de quantização por quatro. A seção
seguinte demonstra que essa multiplicação **não tem custo efetivo**, por ficar o degrau de
quantização, nas duas configurações, muito abaixo do ruído próprio do transdutor.

#### Z.1.3 Ruído

O fabricante publica a densidade espectral de potência de ruído do acelerômetro como
**400 µg/√Hz**, valor típico. Registra-se a condição de medição, por ser determinante:
**a 10 Hz, com fundo de escala ±2 g e taxa de saída de 1 kHz**. Aplicar esse valor em outra
configuração é uma transposição, e é declarada como tal.

Para ruído de densidade aproximadamente constante na banda de interesse, o desvio-padrão do
sinal integrado numa banda de largura *B* é obtido por (*cálculo*)

> σ = e<sub>n</sub> · √B

de onde resultam, para as larguras de banda de interesse:

| Largura de banda | σ | Taxa de amostragem mínima (Nyquist) |
|---:|---:|---:|
| 16 Hz | 1,600 mg | 32 Hz |
| **21 Hz** (configuração adotada) | **1,833 mg** | **42 Hz** |
| 44 Hz | 2,653 mg | 88 Hz |
| 94 Hz | 3,878 mg | 188 Hz |
| 184 Hz | 5,426 mg | 368 Hz |
| 260 Hz (padrão da biblioteca) | 6,450 mg | 520 Hz |

A comparação com o degrau de quantização fecha a questão levantada em Z.1.2. O desvio-padrão
de uma quantização uniforme de passo *q* vale q/√12 (*cálculo*), o que produz 0,0176 mg em
±2 g e 0,0705 mg em ±8 g. Na banda de 21 Hz, o ruído próprio do transdutor é, portanto,
**104 vezes** o ruído de quantização em ±2 g e ainda **26 vezes** em ±8 g. Conclui-se que a
ampliação do fundo de escala para ±8 g **não degrada a resolução efetiva do sistema**, que
permanece limitada pelo ruído do transdutor e não pelo conversor — e que a ampliação é, por
isso, gratuita em termos de resolução, obtendo-se em troca margem contra saturação em eventos
de movimento brusco.

#### Z.1.4 Largura de banda e taxa de amostragem

O componente dispõe de filtro digital passa-baixa programável entre 5 Hz e 260 Hz, e de taxa
de saída programável entre 4 Hz e 1 000 Hz (*especificação*). A biblioteca empregada adota,
por omissão, a configuração de 260 Hz. O trabalho adota **21 Hz**, e a justificativa é
quantitativa em três frentes.

**Primeira — o conteúdo do sinal.** Movimento corporal em cama é fenômeno de poucos hertz. A
literatura de actigrafia opera sobre a banda de aproximadamente 0,25 Hz a 3,5 Hz, e é essa a
banda de passagem empregada no substituto de contagem descrito na seção de metodologia.
Entre 21 Hz e 260 Hz não há, portanto, sinal de interesse: há vibração de mobiliário, passos
no cômodo e ruído do próprio transdutor.

**Segunda — o custo em ruído.** Como σ cresce com √B, passar de 21 Hz a 260 Hz multiplica o
desvio-padrão do ruído por √(260/21) = **3,52** (*cálculo*), isto é, de 1,833 mg para
6,450 mg. A seção Z.2.2 mostra que o piso de indicação do índice de atividade é
**proporcional a σ**, de modo que esse fator de 3,52 se transfere integralmente para o piso —
o que significa que a configuração de fábrica da biblioteca elevaria em mais de três vezes o
menor movimento que o dispositivo é capaz de distinguir do próprio ruído.

**Terceira — o custo em amostragem.** O teorema da amostragem exige taxa superior ao dobro da
maior frequência presente. Com filtro de 21 Hz, a taxa mínima é de **42 Hz**; com o filtro de
260 Hz, seria de **520 Hz**. Sobre a época de 30 s adotada, isso corresponde a 1 260 amostras
por época contra 15 600 — mais de doze vezes o custo de aquisição e de processamento, para
adquirir exclusivamente ruído. A seção Z.4 mostra que esse fator tem consequência direta sobre
o modo de operação do transdutor e, por ele, sobre a autonomia.

Registra-se uma ressalva sobre a taxa de 42 Hz. Ela é o **mínimo matemático**, válido sob a
hipótese de filtro ideal; o filtro do componente é de ordem baixa e apresenta transição
gradual, de modo que há conteúdo residual acima da frequência de corte nominal. Além disso, a
reamostragem de todos os sinais — os das bases públicas e o do dispositivo — para a grade
comum de 32 Hz adotada na parte experimental **exige filtragem digital anti-recobrimento antes
da decimação**, sob pena de o conteúdo acima de 16 Hz ser rebatido sobre a banda de interesse
de forma irreversível. Esse requisito está atendido na cadeia de análise, que aplica filtro
passa-baixa de fase zero a 12,8 Hz — 80 % da frequência de Nyquist da grade comum — antes de
interpolar para a nova grade. Registra-se que a filtragem é de **fase zero**, escolha exigida
pelo alinhamento com os rótulos: um filtro causal desloca o sinal no tempo, e deslocamento
inferior a um segundo já transfere amostras para a época vizinha.

#### Z.1.5 Faixa de validade

Os valores desta seção deixam de descrever o sistema nas seguintes condições. **(i)** Fora da
faixa de alimentação de 2,375 V a 3,46 V e da temperatura de referência de 25 °C, que são as
condições das especificações transcritas; a sensibilidade apresenta deriva declarada de
±0,02 %/°C. **(ii)** A densidade de ruído transposta da condição de ±2 g e 1 kHz para a
configuração efetivamente empregada é **hipótese**, e a verificação está prevista na
caracterização de bancada. **(iii)** O modelo de ruído supõe densidade constante na banda, o
que é válido acima do joelho de ruído de baixa frequência do componente; próximo à
componente contínua, a densidade cresce, e grandezas de muito longo prazo — deriva de
polarização, por exemplo — não são descritas por este modelo. **(iv)** A tolerância de
calibração de fábrica da saída em zero g, de ±50 mg nos eixos X e Y, é **uma ordem de
grandeza maior** que σ: o erro sistemático de um exemplar domina o ruído aleatório, e é por
isso que a calibração é pré-requisito do índice de atividade, e não refinamento posterior.

### Z.2 O índice de atividade por época

#### Z.2.1 Formulação e requisito de invariância

O sinal bruto é segmentado em épocas de 30 s — resolução dos rótulos polissonográficos de
todas as bases empregadas, conforme a seção de metodologia — e cada época é resumida por um
vetor de oito características. O requisito que governa a escolha dessas características é
específico da posição de instalação adotada: **o dispositivo é alojado no interior de um
travesseiro, cuja orientação é arbitrária e varia ao longo da noite**. Toda característica
dependente de eixo codificaria, nessa condição, a orientação de montagem em vez do movimento,
e um modelo ajustado sobre ela aprenderia a convenção de montagem da base de dados de origem.

Adotou-se, por isso, o critério de **invariância a rotação do referencial do sensor** como
condição de admissão de cada característica, verificado por teste automatizado. As oito
características são:

| Característica | Definição | Papel |
|---|---|---|
| ENMO médio | média de max(‖**a**‖ − 1, 0), com **a** em g | Índice de atividade consolidado na área; descarta a gravidade sem exigir conhecimento da orientação |
| ENMO — desvio | desvio-padrão do mesmo | Distingue movimento contínuo de pico isolado |
| ENMO — máximo | máximo do mesmo | Preserva o evento breve que a média dilui |
| Magnitude dinâmica média | média de ‖**a** − **ĝ**‖₂ | Medida de quantidade de movimento na época |
| Taxa de cruzamentos por zero | sobre a magnitude sem componente contínua | Conteúdo de frequência sem custo espectral |
| Fração acima do limiar | fração de amostras da época com ‖**a** − **ĝ**‖ acima do limiar | Compatibilidade com o critério de classificação do dispositivo |
| Inclinação relativa | arccos(**ĝ**<sub>t</sub> · **ĝ**<sub>ref</sub>) | Afastamento da orientação típica **da própria gravação** |
| Variação angular | arccos(**ĝ**<sub>t</sub> · **ĝ**<sub>t−1</sub>) | Evento de mudança de posição |

Duas escolhas merecem registro, por divergirem do que a literatura de actigrafia emprega com
mais frequência.

**A norma euclidiana em lugar da norma L1.** A *signal magnitude area*, de uso corrente na
área, é definida sobre a soma dos módulos das três componentes. Essa norma **não é invariante
a rotação**: para um vetor de módulo unitário, |a<sub>x</sub>| + |a<sub>y</sub>| +
|a<sub>z</sub>| vale 1,00 quando um eixo aponta na direção do vetor e √3 ≈ 1,73 quando o vetor
se reparte igualmente pelos três — **73 % de variação produzida exclusivamente pela
orientação do aparelho**, antes de qualquer movimento (*cálculo*). Computada sobre a
componente dinâmica, a variação residual medida em teste foi de aproximadamente 6 %, ainda
não nula, por ser propriedade da norma e não erro numérico. Adotou-se a norma euclidiana, que
satisfaz ‖R**v**‖₂ = ‖**v**‖₂ para toda matriz de rotação R e, portanto, passa o teste por
construção. Registra-se explicitamente que a característica resultante **não é a *signal
magnitude area*** da literatura, e não deve ser citada como tal.

**O ângulo relativo em lugar do ângulo absoluto.** A inclinação é medida contra a direção de
gravidade de referência **da própria gravação**, estimada pela mediana geométrica dos vetores
unitários ao longo da noite, e não contra um eixo do fabricante. A prova de invariância é
imediata: para R ortogonal, (R**ĝ**<sub>a</sub>) · (R**ĝ**<sub>b</sub>) =
**ĝ**<sub>a</sub><sup>T</sup> R<sup>T</sup> R **ĝ**<sub>b</sub> = **ĝ**<sub>a</sub> ·
**ĝ**<sub>b</sub>, de modo que o produto interno — e portanto o ângulo — não se altera. A
mediana geométrica, e não a mediana componente a componente, é exigida pela mesma razão:
esta última opera eixo a eixo e não é equivariante a rotação.

A inclusão de características angulares não é ornamental. Ela responde ao achado, discutido
na seção de limitações, de que a combinação de informação de postura com aceleração corporal
melhora a discriminação entre sono e vigília em relação ao uso isolado da aceleração
(RAZJOUYAN et al., 2017).

#### Z.2.2 O piso de indicação imposto pelo ruído

O índice ENMO é definido como max(‖**a**‖/g − 1, 0). O operador de máximo com zero é um
**retificador**, e daí decorre uma propriedade que condiciona a interpretação de todo valor
pequeno do índice: em repouso absoluto, o valor verdadeiro é zero, mas o ruído oscila para os
dois lados e **apenas o lado negativo é cortado**. O ruído, por conseguinte, não se cancela na
média — converte-se em **viés positivo**.

A magnitude desse viés é calculável. Para perturbação gaussiana de desvio-padrão σ e média
nula, o valor esperado da parte positiva é (*cálculo*)

> E[max(δ, 0)] = σ / √(2π) ≈ 0,399 · σ

e, para perturbação uniforme de passo q, característica da quantização com sinal de agitação
suficiente,

> E[max(δ, 0)] = q / 8

Aplicando à banda de 16 Hz — a banda efetiva da grade comum de 32 Hz sobre a qual todos os
sinais são reamostrados —, e comparando com os acelerômetros das bases públicas empregadas:

| Sensor | Fonte de ruído considerada | σ por amostra | Piso do ENMO médio |
|---|---|---:|---:|
| Componente deste trabalho | Térmico, 400 µg/√Hz × √16 Hz | 1,600 mg | **0,638 mg** |
| GENEActiv (coorte externa) | Quantização, 3,9 mg / √12 | 1,126 mg | ≥ 0,487 mg |
| Empatica E4 (base de desenvolvimento) | Quantização, 15,625 mg / √12 | 4,511 mg | ≥ 1,953 mg |

O resultado é contra-intuitivo e convém enunciá-lo: **o componente empregado neste trabalho
não é o elo fraco da cadeia**. Seu piso é aproximadamente **um terço** do piso do
acelerômetro de pulso da base de desenvolvimento, e da mesma ordem do piso do acelerômetro de
grau de pesquisa da coorte externa. A comparação, ressalve-se, **não é simétrica**: para os
dois aparelhos comerciais só foi possível considerar a quantização, por não publicarem
densidade de ruído, de modo que os pisos apresentados são **limites inferiores** e os valores
reais são superiores aos tabelados. A assimetria, portanto, opera **contra** a afirmação, e
não a favor dela — e a afirmação sobrevive assim mesmo.

Observa-se, por fim, que este cálculo fornece o critério de aceitação da calibração de
bancada: na banda de 21 Hz efetivamente configurada, o piso teórico de ruído do componente é
de 1,833 mg, ou 0,0180 m/s², contra o critério de 0,02 m/s² previamente registrado no
planejamento — coincidência que confirma que o critério estava bem escolhido.

#### Z.2.3 Sobre a derivação de um limiar a partir do ruído

O critério de classificação implementado no dispositivo é |‖**a**‖ − g| > 1,2 m/s². Formulado
assim, ele tem a aparência de um limiar do tipo g ± k·σ, isto é, de um limiar derivado do
ruído de base do transdutor. **Não é**, e o registro dessa constatação é preferível à
apresentação de uma derivação que o dado não sustenta.

A verificação é direta. Na banda de 21 Hz, σ vale 1,833 mg, equivalentes a 0,0180 m/s². O
limiar em uso corresponde, portanto, a (*cálculo*)

> k = 1,2 / 0,0180 ≈ **67 σ**

Um limiar de detecção derivado de ruído opera tipicamente entre três e cinco desvios-padrão,
faixa em que a probabilidade de acionamento espúrio é controlada sem sacrifício relevante de
sensibilidade. Um limiar a 67 σ não pertence a essa família: ele não foi derivado do ruído, e
não pode ser apresentado como se tivesse sido. Trata-se de um **limiar empírico de
movimento**, arbitrado para separar deslocamento efetivo do travesseiro de perturbações
ambientais, e é assim que deve ser declarado.

A distinção tem consequência que ultrapassa a nomenclatura. Um limiar derivado do ruído seria
uma propriedade do componente, transferível entre exemplares e entre configurações; um limiar
empírico de movimento é uma propriedade **do conjunto sensor–travesseiro–instalação**, e sua
transferência entre montagens é questão empírica, não dedutiva. É por essa razão que a
calibração do limiar está declarada como pendente de ensaio em bancada, e não como cálculo a
realizar.

Registra-se, por completude, que a arquitetura de classificação adotada na parte experimental
do trabalho **não emprega limiar algum como regra de decisão**: a decisão entre sono e vigília
é produzida por classificador ajustado sobre as oito características da seção Z.2.1. O limiar
sobrevive no sistema apenas como **parâmetro de uma das oito características** — a fração de
amostras acima dele —, condição em que um valor imperfeito degrada gradualmente uma
característica entre oito, em vez de deslocar uma fronteira de decisão. A substituição de uma
regra de limiar por um classificador multivariado é, ela própria, o resultado que torna
dispensável a derivação discutida nesta seção.

#### Z.2.4 Faixa de validade

**(i)** Os pisos da tabela pressupõem repouso: sob movimento, o termo de sinal domina e o
viés do retificador torna-se desprezível — o modelo descreve o comportamento do índice
**próximo de zero**, que é justamente onde a interpretação é delicada. **(ii)** O cálculo de
quantização pressupõe agitação suficiente para que o erro de arredondamento se comporte como
variável aleatória aproximadamente independente entre amostras; em repouso absoluto e sem
agitação térmica, a quantização degenera em deslocamento determinístico, e o modelo não se
aplica. **(iii)** Os pisos dos dois aparelhos comerciais são limites inferiores, pela razão
já declarada. **(iv)** Nada nesta seção descreve **erro sistemático**: um viés de calibração
de −1,06 m/s² em um eixo, da ordem de 11 % de g, não desloca o ENMO — ele o destrói, por
tornar ‖**a**‖/g − 1 permanentemente distinto de zero. A calibração é, por isso, pré-requisito
do índice, e não ajuste posterior.

### Z.3 Modelo elétrico das interfaces

#### Z.3.1 O ramo de acionamento por botão

O protótipo de bancada inclui um botão com resistor de 10 kΩ em configuração *pull-down*,
alimentado em 3,3 V. Com o contato fechado, o ramo conduz (*cálculo*)

> I = V / R = 3,3 / 10 000 = **0,330 mA** e P = V² / R = **1,089 mW**

Duas observações são necessárias para que esse número não seja mal empregado. **A primeira**
é que se trata de um **valor de pico, não de média**: com o contato aberto — a condição
predominante — o ramo não conduz, e sua contribuição para o balanço energético da seção Z.4 é
proporcional à fração de tempo em que o botão permanece pressionado, que é desprezível. **A
segunda** é que este ramo é **instrumento de simulação, e não parte do produto**: ele existe
para emular, em ambiente de simulação, o sinal de despertar que, no dispositivo real, provém
da própria interrupção de movimento do acelerômetro. A análise é apresentada por
completude do levantamento elétrico da bancada, e o ramo não integra o modelo de consumo do
dispositivo.

#### Z.3.2 O barramento I²C e a janela admissível de resistência de polarização

A comunicação entre microcontrolador e sensor emprega barramento I²C, cujas linhas são de
dreno aberto e exigem resistores de polarização para o nível alto. O valor desses resistores
não é livre: ele é limitado **por baixo** pela capacidade de dreno dos dispositivos e **por
cima** pelo tempo de subida do barramento.

**Limite inferior.** O dispositivo que impõe o nível baixo precisa levar a linha até a tensão
de saída em nível baixo especificada. Com dreno de 3 mA a 0,4 V (*especificação*, §6.6 da
folha de dados do componente), resulta (*cálculo*)

> R<sub>mín</sub> = (V<sub>DD</sub> − V<sub>OL</sub>) / I<sub>OL</sub> = (3,3 − 0,4) / 0,003 ≈ **967 Ω**

**Limite superior.** A especificação I²C limita o tempo de subida entre 0,3·V<sub>DD</sub> e
0,7·V<sub>DD</sub> a 1 000 ns no modo padrão (100 kHz) e a 300 ns no modo rápido (400 kHz).
Para a subida exponencial de constante RC, esse trecho corresponde a ln(0,7/0,3)·RC =
0,847·RC, de onde (*cálculo*)

> R<sub>máx</sub> = t<sub>r</sub> / (0,847 · C<sub>b</sub>)

com C<sub>b</sub> a capacitância total do barramento. Os valores resultantes:

| Capacitância do barramento | Modo padrão (100 kHz) | Modo rápido (400 kHz) |
|---:|---:|---:|
| 50 pF | 23,60 kΩ | 7,08 kΩ |
| 100 pF | 11,80 kΩ | 3,54 kΩ |
| 200 pF | — | 1,77 kΩ |

O modelo explica dois comportamentos observáveis. **Primeiro**, por que a resistência de
polarização usualmente embarcada nos módulos de avaliação, da ordem de alguns quilo-ohms,
satisfaz simultaneamente os dois limites nas duas velocidades para capacitâncias típicas de
montagem em placa de ensaio. **Segundo**, e de utilidade diagnóstica direta, por que uma
montagem pode operar sem falhas a 100 kHz e falhar a 400 kHz: a janela admissível estreita-se
por um fator superior a três ao mudar de modo, e uma polarização fraca, ou uma capacitância
elevada por condutores longos, atravessa o limite superior no modo rápido antes de
atravessá-lo no modo padrão. O procedimento de diagnóstico do barramento adotado neste
trabalho — repetir o mesmo conjunto de verificações nas duas velocidades — apoia-se
precisamente nessa assimetria.

Registra-se a consequência energética, que a seção Z.4 incorpora: enquanto uma linha é
mantida em nível baixo, a corrente que atravessa o resistor de polarização vale
(V<sub>DD</sub> − V<sub>OL</sub>)/R, o que dá 0,617 mA por linha com resistência de 4,7 kΩ, ou
1,234 mA nas duas linhas simultaneamente (*cálculo*). Esse valor é **maior que o consumo do
próprio acelerômetro** em modo de acelerômetro exclusivo, apresentado na seção Z.4, e é
frequentemente omitido dos balanços energéticos.

#### Z.3.3 Compatibilidade de níveis lógicos

O sensor especifica limiares de entrada proporcionais à sua tensão de referência lógica:
V<sub>IH</sub> ≥ 0,7·V<sub>LOGIC</sub> e V<sub>IL</sub> ≤ 0,3·V<sub>LOGIC</sub>
(*especificação*). Com referência lógica em 3,3 V, os limiares valem 2,31 V e 0,99 V, ambos
folgadamente atendidos pelas saídas do microcontrolador, que opera na mesma tensão.

Cabe, contudo, um registro que a leitura direta da folha de dados não fornece: **em barramento
de dreno aberto, o nível alto não é imposto por nenhum dos dispositivos, e sim pela tensão a
que os resistores de polarização estão referenciados**. A compatibilidade de níveis é, por
conseguinte, uma propriedade da montagem, não dos componentes. Se os resistores de
polarização do módulo estiverem referenciados à entrada de alimentação não regulada, e esta
for de 5 V, as entradas do microcontrolador — especificadas para 3,3 V — serão submetidas a
5 V, ainda que ambos os circuitos integrados sejam compatíveis entre si. A montagem adotada
neste trabalho alimenta o módulo a partir da saída regulada de 3,3 V do microcontrolador,
condição sob a qual a questão não se coloca; a verificação da tensão de referência dos
resistores de polarização é, ainda assim, item do procedimento de conferência de montagem.

#### Z.3.4 A fonte de despertar

Na configuração de bancada, o despertar do microcontrolador é produzido por transição em
pino de entrada de uso geral com retenção em domínio de tempo real, acionada pelo botão
descrito em Z.3.1. Na configuração de produto, essa função cabe à **saída de interrupção do
próprio acelerômetro**, configurada para detecção de movimento, que dispensa o botão e o
resistor associado.

A substituição tem consequência que ultrapassa a economia de dois componentes, e é
desenvolvida em Z.4.3: o modo de detecção de movimento do acelerômetro opera com **taxa de
atualização limitada a 40 Hz**, inferior à taxa mínima de amostragem derivada em Z.1.4, de
modo que as duas arquiteturas — despertar por movimento e amostragem contínua por época — são
**mutuamente exclusivas** nos termos em que foram especificadas.

#### Z.3.5 Faixa de validade

**(i)** Todos os valores pressupõem alimentação de 3,3 V; em 5 V, os limiares proporcionais
deslocam-se e a corrente pelos resistores de polarização cresce na mesma proporção. **(ii)**
A capacitância do barramento é **estimativa**: ela depende do comprimento dos condutores, do
número de dispositivos e da montagem, e a tabela de Z.3.2 é por isso apresentada como função
dela, e não como valor único. A medição direta do tempo de subida com osciloscópio substitui
toda a tabela e é o procedimento recomendado. **(iii)** A resistência dos polarizadores
embarcados no módulo de avaliação empregado **não é especificação de fabricante** e deve ser
verificada com ohmímetro no exemplar em uso. **(iv)** O modelo de subida exponencial supõe
carga puramente resistiva-capacitiva; polarização ativa ou aceleradores de subida, se
presentes, invalidam-no.

### Z.4 Modelo de consumo e autonomia

#### Z.4.1 Formulação

O dispositivo alterna entre estados de consumo distinto. Sendo I<sub>i</sub> a corrente
média do estado *i* e t<sub>i</sub> sua duração dentro de um ciclo completo, a corrente média
do ciclo é (*cálculo*)

> I<sub>média</sub> = Σ (I<sub>i</sub> · t<sub>i</sub>) / Σ t<sub>i</sub>

e a autonomia estimada, para uma bateria de capacidade C, é

> autonomia = C / I<sub>média</sub>

Registra-se desde já que **este é um modelo de predição, e não uma medição**. Seu propósito é
ordenar alternativas de arquitetura e identificar qual parâmetro domina o resultado, não
antecipar um número que será verificado em bancada. A medição correspondente está prevista na
validação do protótipo físico.

#### Z.4.2 Correntes por estado

Os valores a seguir são **especificação de fabricante**, transcritos com suas condições.

*Acelerômetro* (TDK InvenSense, PS-MPU-6000A-00 Rev. 3.4, §6.4; V<sub>DD</sub> de 2,375 V a
3,46 V, 25 °C):

| Modo | Corrente |
|---|---:|
| Giroscópio + acelerômetro + processador de movimento | 3,9 mA |
| Giroscópio + acelerômetro | 3,8 mA |
| **Acelerômetro exclusivo** (giroscópio e processador desligados) | **500 µA** |
| Acelerômetro em baixo consumo, 1,25 Hz / 5 Hz / 20 Hz / 40 Hz | 10 / 20 / 60 / 110 µA |
| Repouso completo do circuito integrado | 5 µA |
| Referência lógica, corrente de operação | 100 µA |
| Tempo de partida para leitura e escrita de registrador | 20 ms típico, 100 ms máximo |

*Microcontrolador* (Espressif, folha de dados da série, tabela de consumo por modo de
energia). Registra-se a condição, e ela é determinante: **a tabela refere-se ao circuito
integrado, não ao módulo nem à placa de desenvolvimento**.

| Modo | Corrente |
|---|---:|
| Rádio desligado, processador ativo a 80 MHz, dois núcleos | 20 a 31 mA |
| Rádio desligado, processador ativo a 240 MHz, dois núcleos | 30 a 68 mA |
| Sono leve | 0,8 mA |
| Sono profundo, temporizador e memória de tempo real | 10 µA |
| Sono profundo, coprocessador de ultrabaixo consumo ativo | 150 µA |
| Hibernação | 5 µA |
| Desligado | 1 µA |

Dois parâmetros do modelo **não** são especificação transcrita e entram declaradamente como
**estimativa em faixa**: a corrente durante transmissão por rádio, arbitrada entre 100 mA e
240 mA, e o **consumo fixo da placa de desenvolvimento** — regulador linear e ponte de
comunicação serial —, arbitrado entre 1 mA e 20 mA. O tratamento de ambos é feito por análise
de sensibilidade em Z.4.5.

#### Z.4.3 Duas impossibilidades estruturais

Antes de qualquer conta de autonomia, a comparação entre as especificações de Z.4.2 e a taxa
de amostragem derivada em Z.1.4 elimina duas arquiteturas que, de outro modo, pareceriam
disponíveis.

**A primeira: não é possível desligar o sensor entre amostras.** À taxa mínima de 42 Hz, o
intervalo entre amostras é de **23,8 ms**. O tempo de partida do acelerômetro para leitura de
registrador é de **20 ms típicos e 100 ms máximos**. O tempo de recuperação é, portanto, da
ordem do intervalo de amostragem no caso típico e várias vezes maior no caso de pior
comportamento: um ciclo de desligar e religar o sensor a cada amostra **não cabe no intervalo
entre amostras**. A conclusão não é de engenharia de implementação, e sim aritmética.

**A segunda: a taxa exigida proíbe o modo de baixo consumo do sensor.** O modo de baixo
consumo do acelerômetro oferece taxas de atualização de até **40 Hz**, a 110 µA. A taxa
mínima derivada em Z.1.4 é de **42 Hz**. Os dois valores são próximos, mas a desigualdade é
estrita e a consequência é discreta: a amostragem exigida pela cadeia de processamento
**obriga o modo normal de acelerômetro exclusivo, a 500 µA**, o que representa fator de
**4,5×** na corrente do transdutor (*cálculo*). Registra-se que esse é um custo do teorema da
amostragem, e não uma ineficiência de implementação — e que ele é consequência direta da
escolha de banda documentada em Z.1.4, o que ilustra o acoplamento entre os modelos deste
capítulo.

Da segunda impossibilidade decorre a incompatibilidade anunciada em Z.3.4. A arquitetura de
**despertar por movimento** exige que o acelerômetro permaneça em modo de baixo consumo, e
esse modo não atinge a taxa que a extração de características requer. As duas arquiteturas
não se combinam: o despertar por movimento é compatível com o registro de **eventos** de
movimento e com o critério de limiar de Z.2.3, mas não com o vetor de oito características de
Z.2.1, que exige a época inteira amostrada.

#### Z.4.4 As duas arquiteturas, quantificadas

Avaliaram-se duas arquiteturas sobre o mesmo conjunto de premissas, considerando apenas os
circuitos integrados, isto é, **sem** o consumo fixo da placa:

- **Amostragem contínua por época** — o processador permanece ativo com rádio desligado
  durante toda a época, o acelerômetro opera em modo exclusivo a 500 µA, e o rádio é acionado
  uma vez por época para entrega.
- **Despertar por movimento** — o processador permanece em sono profundo, o acelerômetro
  opera em modo de baixo consumo a 20 Hz, e ambos são acionados apenas quando há evento.

Com o rádio arbitrado em 100 mA, transmissão de 1 s e uma entrega por época, e considerando
o limite inferior da faixa de consumo do processador, obtém-se (*cálculo* sobre
*especificação* e *estimativa*)

| Arquitetura | I<sub>média</sub> (só circuitos integrados) |
|---|---:|
| Amostragem contínua por época | 23,9 mA |
| Despertar por movimento | 1,91 mA |

A varredura da faixa dos dois parâmetros estimados, para a arquitetura contínua, produz
corrente média entre 22,6 mA e 46,2 mA e autonomia entre 43 h e 89 h para bateria hipotética
de 2 000 mA·h. **A dispersão é de fator dois**, o que delimita a precisão útil desta predição:
ela ordena arquiteturas, não antecipa uma autonomia.

Observa-se um resultado que a formulação inicial do modelo não antecipava. Na arquitetura de
despertar por movimento, **aproximadamente 87 % da corrente média é consumida pelo rádio**, e
não pelos estados de repouso (*cálculo*). Segue-se que, nessa arquitetura, a grandeza que
controla a autonomia não é o modo de sono adotado, e sim o **número de transmissões**. A
consequência de projeto é direta e é registrada: agregar entregas em lote reduz mais a
corrente média do que qualquer refinamento adicional da política de sono.

#### Z.4.5 O que a placa de desenvolvimento faz com o modelo

Os valores de Z.4.4 referem-se aos circuitos integrados. A placa de desenvolvimento
empregada acrescenta consumo fixo, oriundo do regulador linear de tensão e da ponte de
comunicação serial, **presente em todos os estados, inclusive em sono profundo**. Tratando
esse consumo como parâmetro e varrendo a faixa declarada:

| Consumo fixo da placa | Contínua | Despertar por movimento | Razão |
|---:|---:|---:|---:|
| 0 (somente circuitos integrados) | 23,9 mA | 1,91 mA | 12,5× |
| 0,1 mA | 24,0 mA | 2,01 mA | 12,0× |
| 1 mA | 24,9 mA | 2,91 mA | 8,6× |
| 5 mA | 28,9 mA | 6,91 mA | 4,2× |
| 10 mA | 33,9 mA | 11,9 mA | 2,9× |
| 20 mA | 43,9 mA | 21,9 mA | 2,0× |

Invertendo a relação, obtém-se o consumo fixo que reduz a vantagem a um dado fator
(*cálculo*): basta **0,54 mA** para que a razão caia de 12,5× para 10×, **3,6 mA** para que
caia a 5× e **20,1 mA** para que caia a 2×.

A leitura correta desse quadro é precisa, e convém não exagerá-la. O consumo fixo da placa
**não inverte o sinal da vantagem**: a arquitetura de sono continua sendo a melhor em toda a
faixa examinada. O que ele faz é **comprimir a ordem de grandeza**: a diferença de quatro
ordens de grandeza que a folha de dados do circuito integrado promete entre o estado ativo e
o sono profundo — de dezenas de miliampères para 10 µA — não se materializa numa placa cujo
consumo de repouso é de miliampères, porque o piso deixa de ser o do circuito integrado e
passa a ser o da placa.

Segue-se a recomendação de projeto que este modelo fundamenta: **o consumo fixo da placa de
desenvolvimento é o parâmetro que decide a autonomia do dispositivo, e é ele que a etapa de
definição de alimentação precisa medir**, antes de qualquer decisão sobre bateria ou sobre
política de sono. Enquanto ele não for medido, a autonomia do sistema não é conhecida dentro
de melhor que uma ordem de grandeza — e nenhuma afirmação de "baixo consumo" é sustentável.

#### Z.4.6 A autonomia sem conectividade

Distinta da autonomia energética, e independentemente medida, está a autonomia de
**armazenamento**: por quanto tempo o dispositivo continua registrando sem entregar nada.
Diferentemente dos valores da seção anterior, esta grandeza foi **medida**, por execução do
próprio código de armazenamento em ambiente de teste, e não estimada.

O registro de época ocupa **32 bytes**, tamanho travado por asserção de compilação. Daí
resultam, em resolução plena de 30 s:

| Orçamento de memória | Épocas | Cobertura em resolução plena |
|---|---:|---:|
| 4 KiB — memória de tempo real, sobrevive ao sono profundo | 128 | 1,07 h |
| 6 KiB — memória de tempo real, limite prático | 192 | 1,60 h |
| 32 KiB — memória dinâmica | 1 024 | **8,53 h** |
| 128 KiB — memória dinâmica, orçamento amplo | 4 096 | 34,1 h |

A configuração adotada no sketch de bancada emprega 1 024 épocas, o que cobre uma noite de
oito horas **sem degradar a resolução uma única vez**. Registra-se que a política de
armazenamento adotada, ao atingir a ocupação limite, **funde épocas adjacentes em vez de
descartá-las**, de modo que o que se perde ao ultrapassar a capacidade é resolução temporal, e
não cobertura — e que essa fusão **não introduz erro de agregação**, por ser o método de
resumo o máximo da magnitude, que é associativo: o máximo de duas épocas adjacentes de 30 s
é, exatamente, o máximo da época de 60 s que as cobre.

#### Z.4.7 Faixa de validade

**(i)** O modelo é **preditivo**: nenhum de seus valores foi medido no sistema construído, e
sua verificação está prevista na validação do protótipo físico. **(ii)** Duas de suas
entradas são estimativas em faixa, e a dispersão resultante é de fator dois; o modelo ordena
arquiteturas, não antecipa autonomia. **(iii)** A relação autonomia = C/I ignora o efeito da
corrente de descarga sobre a capacidade efetiva da bateria, a tensão de corte do circuito de
proteção e a dependência da capacidade com a temperatura; para correntes baixas em relação à
capacidade nominal, como é o caso, a aproximação é razoável, mas ela é aproximação.
**(iv)** As correntes transcritas são especificação a 25 °C; um dispositivo alojado no
interior de um travesseiro opera acima da temperatura ambiente, e a caracterização térmica
está registrada como trabalho não executado. **(v)** O consumo fixo da placa, que a seção
Z.4.5 identifica como parâmetro dominante, **não foi medido**, e é por isso que o resultado
desta seção é uma recomendação de medição, e não um valor de autonomia.

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Procedência de cada número

Notas para você, não para o texto. A regra deste arquivo é a mesma do `RESULTADOS-TCC.md`:
nada foi escrito de memória. Todo número calculado sai de `scripts/calculos_tcc.py`; todo
número de folha de dados traz a condição; todo número recuperado de outro documento do
repositório foi **reconferido** antes de entrar aqui.

### Os três cálculos que já existiam, e o resultado da conferência

O enunciado da tarefa avisava que três contas já haviam sido feitas informalmente ao longo do
projeto e **não deviam ser refeitas de cabeça**. Elas foram recuperadas, reconferidas pelo
script, e **as três batem**:

| Cálculo | Onde estava | Valor no documento | Recalculado | Veredito |
|---|---|---:|---:|:---:|
| Piso do ENMO, MPU6050 | `ML-DATASETS-E-PLANO.md` §2.2 | ≈ 0,64 mg | 0,638 mg | ✅ |
| Piso do ENMO, GENEActiv | idem | ≥ 0,49 mg | 0,487 mg | ✅ |
| Piso do ENMO, Empatica E4 | idem | ≥ 1,95 mg | 1,953 mg | ✅ |
| σ do MPU a 21 Hz | idem | 1,8 mg | 1,833 mg | ✅ |
| σ_q do E4 | idem | 4,5 mg | 4,511 mg | ✅ (arredondamento) |
| Capacidade do buffer, 1 024 épocas | `firmware/nucleo/README.md` | 8,53 h | 8,53 h | ✅ |
| Capacidade do buffer, 128 épocas | idem | 1,07 h | 1,07 h | ✅ |
| Custo de drenar 8 h | idem | 960 POSTs | 960 | ✅ |
| Identidade da acurácia, Li 2025 | `RESULTADOS-TCC.md` Y.1.3 e §0.2 | p = 0,878 | 0,878 | ✅ |
| Identidade da acurácia, Walch 2019 | idem | p = 0,910 | 0,910 | ✅ |
| Pull-down, corrente e potência | `BACKLOG-COMPLETO.md` `CALC-04` | 0,33 mA / 1,1 mW | 0,330 mA / 1,089 mW | ✅ |
| Resolução em ±8 g | `ML-DATASETS` §2.1 e `SINTESE` | 0,244 mg/LSB | 0,2441 | ✅ |
| Limiar em g | `ml/src/features.py` | ≈ 0,1224 g | 0,12237 | ✅ |

Essas linhas estão **travadas como asserções** em `scripts/calculos_tcc.py`, função
`conferir()`. Se alguém mudar uma constante e um desses números deixar de sair, o script sai
com código diferente de zero e diz qual documento foi contrariado. É a única forma de este
arquivo não virar uma terceira versão divergente dos mesmos números.

### O que é cálculo, o que é medição, o que é estimativa

| Número do texto | Natureza | Fonte |
|---|---|---|
| Resoluções, correntes, tempo de partida, I<sub>OL</sub>, limiares lógicos do sensor | **Especificação** | TDK InvenSense, PS-MPU-6000A-00 Rev. 3.4, §6.2, §6.4 e §6.6. Condição: V<sub>DD</sub> 2,375–3,46 V, 25 °C |
| 400 µg/√Hz | **Especificação**, e a condição importa | Idem, §6.2: **a 10 Hz, AFS_SEL = 0 (±2 g), ODR = 1 kHz**, valor típico. O projeto usa ±8 g e filtro de 21 Hz — a transposição está declarada no texto |
| Correntes por modo do ESP32 | **Especificação** | Espressif, ESP32 Series Datasheet, Tabela 4-2. Condição: **consumo do chip**, não do módulo nem da placa |
| σ por banda, pisos de ENMO, janela do pull-up, k = 67, razão √(260/21) | **Cálculo** | `scripts/calculos_tcc.py` |
| Capacidade do buffer (1,07 h / 8,53 h / 960 POSTs) | **Medição** | `firmware/nucleo/capacidade.cpp`, via `make capacidade`; `sizeof(Epoca)` travado por `static_assert` |
| Invariância a rotação das features; 73 % da L1; 6 % residual | **Medição** | `ml/testes/test_vetor_dourado.py::test_features_invariantes_a_rotacao` |
| Corrente de rádio (100–240 mA) | **Estimativa em faixa** | ⚠️ ver 🔧 3 |
| Consumo fixo da placa (1–20 mA) | **Estimativa em faixa** | ⚠️ ver 🔧 3 |
| Capacitância do barramento I²C | **Estimativa em faixa** | Depende da montagem; a tabela é função dela, de propósito |
| Bateria de 2 000 mA·h | **Hipótese de trabalho** | Nenhuma bateria foi escolhida; é ilustração de ordem de grandeza |

### Como reproduzir

```bash
python3 scripts/calculos_tcc.py            # relatório completo + conferência
python3 scripts/calculos_tcc.py --conferir # só a conferência

cd firmware/nucleo && make capacidade      # a capacidade do buffer, medida
cd ml && python -m pytest testes/test_vetor_dourado.py -k invariantes
```

---

## 🔧 O que mudou de natureza em relação ao backlog

Três itens não sobreviveram intactos à redação. São mudanças **de conteúdo**, não de forma.

🔧 **1. O `CALC-03` perdeu metade do enunciado, e isso é o resultado — não uma pendência.**

O backlog já registrava que o item havia mudado de natureza com o fechamento do `ML-01`:
*"virou transpor para o texto, não decidir"*. A redação confirma a primeira metade e
**elimina a segunda**. A parte "índice de atividade por época" está transposta em Z.2.1, a
partir de `ml/src/features.py`. A parte **"derivação do limiar `g ± k·σ`" não produz número
útil, e não foi produzida**.

A razão está em Z.2.3 e é verificável em uma linha: o limiar em uso, de 1,2 m/s², corresponde
a **k ≈ 67 σ** na banda de 21 Hz. Um limiar derivado de ruído vive entre 3 σ e 5 σ. Os 1,2
m/s² **nunca foram derivados do ruído** — são um limiar empírico de movimento, e a fórmula
`g ± k·σ` não os gera nem os explica. Escrever a derivação assim mesmo produziria um valor
entre 0,054 e 0,090 m/s² (3 σ a 5 σ) — **de treze a vinte e duas vezes menor** que o em uso —,
e um TCC que apresentasse os dois lado a lado teria de explicar por que ignora o que acabou
de derivar.

A saída adotada é declarar o limiar pelo que ele é e registrar que **a arquitetura de decisão
do trabalho não usa limiar algum** — quem decide é o classificador sobre as oito
características, e o limiar sobreviveu apenas como parâmetro de uma delas. Isso transforma a
ausência da derivação em consequência de uma decisão de projeto, que é defensável, em vez de
lacuna, que não é.

**Consequência para o backlog:** o `CALC-03` pode ser fechado. O que restou dele —
*calibrar* o limiar — não é cálculo, é o `VIA-01`/`CAL-01`, e já está lá.

🔧 **2. O `CALC-04` estava enunciado com um erro de natureza, e o texto o corrige.**

O backlog escreve o pull-down como `I = V/R ≈ 0,33 mA`, `P ≈ 1,1 mW`, sem qualificação. A
conta está **certa**, e o script confirma os dois valores. O que está errado é o **estatuto**
dela: 0,33 mA é a corrente **com o botão fechado**. Com o botão aberto — que é a condição
quase o tempo todo — o ramo não conduz e a contribuição é zero.

Isso importa porque o número tem tamanho suficiente para poluir o `CALC-01`: 0,33 mA é
comparável ao consumo do acelerômetro em modo normal (500 µA) e seria, se somado como
corrente permanente, um erro de balanço energético de ordem relevante. Some-se que o botão é
**andaime de simulação** (`HW-01`), e o valor correto a levar para o modelo de energia do
produto é **zero**. Z.3.1 diz as três coisas.

🔧 **3. O `CALC-01` foi entregue com dois parâmetros abertos, de propósito.**

Dois números que o modelo de energia precisa **não puderam ser obtidos de folha de dados
nesta sessão**:

- **Corrente de transmissão Wi-Fi.** Está na **Tabela 5-4** da folha de dados do ESP32, que a
  versão HTML publicada por Espressif **não reproduz**. A Tabela 4-2, de consumo por modo de
  energia, foi obtida e está citada. Faixa usada: 100–240 mA.
- **Consumo fixo da placa DevKit V1** — regulador linear e ponte USB-serial. **Não existe
  folha de dados da placa**; existem folhas dos componentes, que variam por fabricante e por
  revisão do clone. Faixa usada: 1–20 mA.

A escolha foi entrar com os dois como **faixa paramétrica declarada e varrer a faixa**, em vez
de citar valor de terceiro sem procedência. O resultado é melhor do que pareceria: a análise
de sensibilidade de Z.4.5 mostra que o segundo parâmetro **é o resultado do `CALC-01`** — a
recomendação para o `HW-02` não é "use tal bateria", é **"meça o consumo de repouso da placa,
porque é ele que decide"**. Um modelo cuja saída é qual medição fazer é um modelo útil.

⚠️ **Não substituir essas faixas por números encontrados em tutoriais ou em fóruns.** O
`METODOLOGIA.md` é explícito quanto a isso, e este é exatamente o tipo de número que circula
sem fonte. Ou sai de folha de dados aberta, ou sai de multímetro.

---

## Uma divergência técnica que fica registrada para decisão sua

**A taxa de ≥ 42 Hz do `FW-05` é o mínimo matemático, e o mínimo matemático supõe filtro
ideal.** O documento manda, e por isso o texto do TCC mantém os 42 Hz como a taxa derivada.
Mas Z.1.4 acrescenta uma observação que conviria decidir **antes** de implementar o `FW-05`.

O filtro do MPU6050 é de ordem baixa e a transição é gradual. Amostrar **exatamente** no dobro
da frequência de corte nominal deixa passar conteúdo residual acima dela, que se rebate sobre
a banda útil. Sobreamostrar — 64 Hz ou 100 Hz, que a taxa de saída programável do componente
suporta folgadamente — e decimar em software é barato e elimina a questão. Custa corrente no
sensor? **Não**: Z.4.3 mostra que a decisão relevante já foi tomada ao ultrapassar os 40 Hz do
modo de baixo consumo — de 42 Hz para 100 Hz o sensor continua em modo normal, nos mesmos
500 µA. O que sobreamostrar custa é ciclo de processador e tráfego de I²C, não corrente de
transdutor.

✅ **O lado do ML já está resolvido, e isso foi conferido — não presumido.** A dúvida natural
seria se a reamostragem para a grade comum de 32 Hz filtra antes de decimar. Ela filtra:
`ml/src/sinal.py` existe exatamente para isso, aplica Butterworth de fase zero em
`0,8 × Nyquist` — **12,8 Hz** para a grade de 32 Hz — e o cabeçalho do módulo documenta o
erro que ele previne. **A lacuna não está no `ml/`, está no firmware**, que precisará calcular
as mesmas oito características **na placa**, sem passar por esse reamostrador. É lá que a
margem entre 21 Hz de filtro analógico e 12,8 Hz de banda útil precisa ser fechada por
decisão explícita: ou sobreamostrar e filtrar em software no ESP32, ou baixar o filtro do
componente abaixo de 21 Hz — a faixa programável desce até 5 Hz, e o degrau imediatamente
abaixo já ficaria coerente com a banda que o `ml/` efetivamente usa.

**O que decidir no `FW-05`:** a banda do MPU e a taxa de amostragem da placa devem ser
escolhidas **juntas e contra os 12,8 Hz do `ml/`**, não contra os 21 Hz de hoje. Caso
contrário, a mesma característica terá valores diferentes na placa e no `ml/`, e o vetor
dourado (`ml/testes/vetor_dourado.json`) vai acusar a divergência sem que fique claro que a
causa é de banda, e não de implementação.

---

## Checklist antes de colar no documento

- [ ] Substituir `Z` pelo número da seção e ajustar as remissões internas
      (`Z.1.4`, `Z.2.1`, `Z.3.4`, `Z.4.3` são referenciadas cruzadamente dentro do texto).
- [ ] Trocar as remissões em prosa — "a seção de metodologia", "a validação do protótipo
      físico", "a caracterização de bancada" — pelos números de seção do próprio TCC.
- [ ] **Abrir as duas folhas de dados antes de citá-las.** As condições de medição estão
      transcritas corretamente aqui, mas o `METODOLOGIA.md` vale: ter a condição conferida
      não é o mesmo que ter lido a folha. As referências são
      TDK InvenSense, PS-MPU-6000A-00 Rev. 3.4 (19/08/2013) e a folha de dados da série ESP32
      da Espressif — **anotar a revisão desta última**, que não foi registrada nesta sessão.
- [ ] Decidir se folhas de dados entram na lista de referências ou em nota de rodapé. São
      documentos técnicos de fabricante, não literatura revisada por pares; a ABNT admite as
      duas formas, mas o TCC deve ser consistente.
- [ ] Rodar `python3 scripts/calculos_tcc.py --conferir` e confirmar que sai limpo, antes de
      considerar qualquer número deste arquivo final.
- [ ] Conferir se nenhum outro trecho do TCC afirma "baixo consumo" com número — Z.4.5 diz,
      com derivação, que a autonomia **não é conhecida** enquanto o consumo de repouso da
      placa não for medido. O resumo e a introdução são os lugares em que essa afirmação
      costuma escapar.
- [ ] Verificar a coerência com `docs/LIMITACOES-TCC.md` X.5, que cita os mesmos 400 µg/√Hz
      com a mesma condição — os dois textos precisam dizer o mesmo número e a mesma condição.
- [ ] Resolver a divergência da seção acima (banda do firmware × 12,8 Hz do `ml/`) **antes**
      do `FW-05`, não depois.
