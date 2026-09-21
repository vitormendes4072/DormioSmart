# Limitações do trabalho — texto pronto para o TCC (`DOC-06`)

> **Como usar este arquivo.** O que está entre as linhas `── TEXTO ──` é redigido em tom
> acadêmico e pode ser colado no documento com ajustes mínimos de numeração e de referência.
> O que está fora delas são **notas para você**, não para o texto final.
>
> **Fundamentação:** todos os números vêm de `docs/ML-DATASETS-E-PLANO.md` §0, onde cada um
> está atrelado à sua fonte e à população em que foi medido. **Confira as citações contra o
> §0 antes de submeter.**
>
> ✅ **Atualizado em 2026-09-10.** Autoria, ano, veículo e DOI de todas as referências foram
> confirmados na fonte. Os marcadores `(REFERÊNCIA — …)` deste texto foram substituídos por
> citações autor-data. **Três coisas mudaram de conteúdo**, não só de forma — estão marcadas
> com 🔧 nas notas ao final e devem ser lidas antes de colar.
>
> ✅ **Atualizado em 2026-09-21 com números medidos.** As seções X.3 (lateralidade) e X.4
> (degradação entre coortes, ganho que atravessa coorte, nº de coortes) passaram a conter
> resultados **medidos neste trabalho**, não mais só limitações antecipadas. A procedência de
> cada número está em "O que entrou na medição de 2026-09-21", ao final. Diferentemente do
> restante do arquivo, esses números **não vêm da literatura**: vêm de
> `ml/experimentos/saida/*.json` e podem ser reproduzidos com os comandos ali listados.
>
> **Sugestão de posição:** seção própria ao final do desenvolvimento, antes das
> Considerações Finais. Declarar limitação num lugar só, de forma organizada, é sinal de
> maturidade metodológica — espalhá-las pelo texto parece tentativa de diluí-las.

---

## Nota de enquadramento (leia antes de colar)

O texto abaixo assume a **afirmação máxima honesta** do trabalho:

> O dispositivo registra eventos de movimento durante o repouso de forma não invasiva e, a
> partir deles, estima o período de repouso e sua fragmentação, com desempenho da ordem do
> que a literatura de actigrafia reporta — reconhecidamente limitado na discriminação de
> vigília quieta, com tendência conhecida a superestimar o tempo de sono, e sem qualquer
> estadiamento de sono.

Se o texto do TCC afirmar mais que isso em qualquer outro ponto, **é o outro ponto que
precisa mudar**, não esta seção.

---

── TEXTO ────────────────────────────────────────────────────────────────────

## X. Limitações

Esta seção reúne as limitações do trabalho de forma explícita. Parte delas decorre de
escolhas de escopo; parte decorre de restrições físicas do princípio de medição adotado e,
portanto, não seria superada por refinamento de implementação. A distinção entre as duas
naturezas é feita ao longo do texto, por ser relevante para a interpretação dos resultados
e para trabalhos futuros.

### X.1 Limitações do princípio de medição

O dispositivo baseia-se em acelerometria, isto é, no registro de movimento. A inferência de
estados de repouso a partir de movimento é a premissa da **actigrafia**, método consolidado
e reconhecido na literatura de medicina do sono, mas cujos limites são bem documentados e
se aplicam integralmente a este trabalho.

**Discriminação da vigília em repouso.** A limitação central da actigrafia é a
impossibilidade de distinguir vigília quieta de sono: um indivíduo desperto, deitado e
imóvel produz o mesmo sinal de aceleração que um indivíduo adormecido. Revisão sistemática
sobre o tema registra que a actigrafia "mede apenas movimento de membro periférico, usando
atividade como *proxy* de vigília e inatividade como *proxy* de sono e, por extensão, tem
capacidade limitada de inferir os estágios do sono, pela ausência de sinais fisiológicos"
(YUAN et al., 2024, tradução nossa).

Essa limitação manifesta-se de forma assimétrica nas métricas de desempenho. A
**sensibilidade** (capacidade de identificar corretamente épocas de sono) situa-se
consistentemente alta, enquanto a **especificidade** (capacidade de identificar corretamente
épocas de vigília) apresenta variação ampla. Meta-análise de 96 estudos reporta, no
agrupamento de 49 estudos com análise época a época (n = 1 582), sensibilidade média de 83%
(DP 12,0), especificidade média de 51% (DP 19) e acurácia média de 82% (DP 7) (CONLEY et
al., 2019). Nos estudos individuais, a dispersão da especificidade é ainda mais evidente: em
validação de actígrafo de grau clínico contra polissonografia, a especificidade relatada foi
de 33,1%, com sensibilidade de 94,8% (LI; HALAKI; CHOW, 2025); em abordagem baseada
exclusivamente em aceleração bruta, com extração de características derivadas do *jerk*,
foram relatadas sensibilidade de 96,13 ± 5,61% e especificidade de 80,18 ± 12,71% (ODE et
al., 2022) — cabendo observar que o desvio-padrão da especificidade indica desempenho
substancialmente inferior em parte dos indivíduos.

**Viés sistemático de superestimação.** Como consequência direta do exposto acima, a
actigrafia tende a superestimar o tempo total de sono, e o faz de modo desigual conforme a
população. Meta-análise que reuniu 96 estudos e 4 134 participantes relatou, em adultos com
condições crônicas, superestimação estatisticamente significativa do tempo total de sono
(+22,42 minutos; IC 95%: 11,92 a 32,91) e da eficiência do sono (+5,21%; IC 95%: 1,41 a
9,00). Em adultos saudáveis, os autores registram apenas uma **tendência não
estatisticamente significativa** de superestimação (+11,23 minutos; IC 95%: −3,98 a 26,44
para o tempo total de sono) (CONLEY et al., 2019). Em populações com insônia, síntese da
literatura reporta superestimação do tempo total de sono na faixa de 14 a 60 minutos
(PAQUET; KAWINSKA; CARRIER, 2007). Registra-se ainda que a acurácia do método declina
conforme aumenta a severidade do distúrbio de sono (LI; HALAKI; CHOW, 2025), o que configura
uma limitação de particular relevância: a precisão da medida é menor justamente na população
para a qual a medida seria mais informativa.

### X.2 Ausência de estadiamento do sono

O trabalho **não realiza estadiamento do sono** — isto é, não classifica os estágios N1, N2,
N3 e REM. Trata-se de uma limitação de natureza física, e não algorítmica, razão pela qual
não seria superada por modelos mais sofisticados aplicados ao mesmo sinal.

Os estágios do sono não invasivo definem-se por fenômenos que a acelerometria não capta. Os
estágios N1, N2 e N3 distinguem-se por padrões de **atividade cortical** — fusos do sono,
complexos K e ondas delta —, mensuráveis por eletroencefalografia na ordem de microvolts. O
estágio REM caracteriza-se pela combinação de **movimentos oculares rápidos**, registrados
por eletro-oculografia, com **atonia da musculatura esquelética**, registrada por
eletromiografia. Nenhum desses fenômenos possui assinatura mecânica detectável por um
acelerômetro acoplado ao travesseiro. Cabe destacar, adicionalmente, que os estágios REM e
N3 correspondem ambos a estados de baixa atividade motora, sendo portanto indistinguíveis
entre si por esse princípio de medição.

A literatura sustenta que a discriminação entre REM e NREM em dispositivos vestíveis se
apoia predominantemente em marcadores do **sistema nervoso autônomo**, notadamente a
variabilidade da frequência cardíaca. WALCH et al. (2019), ao avaliarem a contribuição de
diferentes modalidades de sensor, obtiveram acurácia de aproximadamente 72% na classificação
entre vigília, NREM e REM utilizando conjuntamente movimento, frequência cardíaca obtida por
fotopletismografia e um marcador do ritmo circadiano. O dispositivo desenvolvido neste
trabalho não dispõe de medição de frequência cardíaca, pela razão discutida na seção X.5.

### X.3 Limitações decorrentes da posição do sensor

O sensor é acoplado ao travesseiro, sem contato com o corpo do usuário. Essa escolha atende
ao requisito de não invasividade que orienta o trabalho, mas implica limitações que devem
ser declaradas.

**Acoplamento mecânico.** O travesseiro constitui meio complacente e amortecedor, e registra
sobretudo o movimento que efetivamente o solicita — predominantemente movimentos de cabeça e
mudanças de posição que a envolvam. Movimentos corporais que não desloquem a cabeça tendem a
ser subcaptados. A magnitude dessa subcaptação constitui questão empírica em aberto,
endereçada pelo protocolo de bancada descrito na seção (REFERÊNCIA INTERNA — item VIA-01).

**Comparação com a posição de pulso.** A literatura de posicionamento de acelerômetros
indica que o punho apresenta acurácia superior a posições próximas ao centro de massa para a
tarefa de discriminação sono/vigília, tendo sido relatada acurácia majoritariamente superior
a 80% no punho contra valores geralmente inferiores a 80% em cintura, coxa e região lombar
(MEREDITH-JONES et al., 2024; ressalve-se que a população desse estudo é pediátrica, com 137
participantes de 8 a 16 anos). No mesmo estudo, a **sensibilidade** mostrou-se em geral
maior nas posições próximas ao centro de massa, ao passo que a **especificidade** foi
consideravelmente melhor no punho — resultado coerente com o mecanismo descrito na seção
X.1, visto que a discriminação da vigília depende do registro de movimento durante o período
desperto. Por esse mecanismo, é razoável antecipar que a posição adotada neste trabalho
apresente especificidade **inferior** à de dispositivos de punho, e não superior — hipótese
que o trabalho declara explicitamente e que orienta a interpretação dos resultados obtidos.

Em contrapartida, há evidência de que a incorporação de informação sobre **mudanças de
postura**, combinada à aceleração corporal, melhora a detecção de épocas de sono e vigília
em relação ao uso isolado da aceleração de punho: em comparação direta contra
polissonografia, sensor único posicionado no tórax alcançou acurácia de 85,8% na
identificação de épocas de sono e vigília, contra 79,8% da actigrafia de punho (RAZJOUYAN et
al., 2017). Essa constatação fundamentou a inclusão de características derivadas de ângulo
de inclinação no conjunto de atributos utilizado.

**Lateralidade do sensor.** A base empregada na validação externa dispõe de registros
simultâneos dos dois punhos do mesmo participante, o que permitiu isolar o efeito do lado do
corpo sobre o desempenho. A comparação foi conduzida **intraparticipante**, nos 26
participantes com registro bilateral: cada participante é seu próprio controle, uma vez que
a noite, a rotulagem polissonográfica e o modelo são os mesmos, variando apenas o lado em
que o acelerômetro foi acoplado. Sob essa formulação, a diferença entre os punhos esquerdo e
direito **não se distinguiu de zero** em nenhuma das configurações avaliadas: para a
configuração de melhor desempenho, obteve-se diferença de coeficiente kappa de +0,009
(IC 95%: −0,015 a +0,031) e de especificidade de −0,009 (IC 95%: −0,038 a +0,017); nas vinte
e quatro comparações realizadas, a maior diferença absoluta observada foi de 0,027 em kappa,
e todos os intervalos de confiança contiveram o valor nulo.

Esse resultado é interpretado como evidência favorável às decisões de representação adotadas
na seção (REFERÊNCIA INTERNA — extração de características): o conjunto de atributos foi
deliberadamente construído com grandezas invariantes a rotação — inclinação relativa à
gravidade de referência da própria gravação e norma euclidiana da componente dinâmica, em
substituição a atributos dependentes de eixo —, e a insensibilidade ao lado do corpo é uma
consequência previsível dessa invariância. Registra-se, contudo, que a ausência de efeito
detectável não equivale à demonstração de ausência de efeito: com 26 participantes, efeitos
de magnitude inferior a aproximadamente 0,03 em kappa não seriam distinguíveis do ruído
amostral pelo delineamento empregado.

### X.4 Limitações da validação

**Ausência de padrão-ouro.** A polissonografia constitui o padrão-ouro para avaliação do
sono e encontra-se fora do alcance material deste trabalho. A validação empregou, portanto,
referências alternativas viáveis, conforme descrito na seção de metodologia, e os resultados
devem ser interpretados à luz dessa substituição.

**Transferência entre domínios.** Não existe, até o momento desta pesquisa, base de dados
pública que reúna acelerometria captada em travesseiro com rotulagem de sono validada por
polissonografia. Consequentemente, a validação apoiada em bases públicas atesta a
**abordagem** de detecção movimento/repouso, e não o desempenho do sensor **naquela
posição**. A distância entre os dois domínios — posição do sensor, acoplamento mecânico e
população — é declarada como limitação e foi objeto de quantificação específica, conforme
descrito na seção (REFERÊNCIA INTERNA — experimento de transferência entre posições).

**Degradação do desempenho entre coortes independentes.** A validação por
*leave-one-subject-out* controla o vazamento de informação entre participantes, mas não
controla nenhuma das demais fontes de homogeneidade de uma mesma coorte: aparelho, protocolo
de aquisição, critérios de pontuação polissonográfica, laboratório e perfil da população
permanecem constantes. Para quantificar essa limitação, conduziu-se validação externa em que
o modelo foi ajustado na totalidade dos 92 participantes da base de desenvolvimento e
aplicado, **sem qualquer reajuste**, a 27 participantes de coorte independente, adquirida com
acelerômetro de outro fabricante, em outro centro e com outra equipe de pontuação. Não houve
reestimação de parâmetros de normalização no domínio de teste, recalibração de limiar de
decisão ou qualquer acesso aos rótulos da coorte externa anterior à medição.

Na melhor configuração, o coeficiente kappa de Cohen decresceu de 0,414, obtido em validação
interna, para 0,334 (IC 95%: 0,254 a 0,416) na coorte externa, e a **especificidade decresceu
de 0,802 para 0,507** (IC 95%: 0,442 a 0,576). A perda concentra-se, portanto, exatamente na
métrica que a seção X.1 identifica como crítica neste domínio: aproximadamente trinta pontos
percentuais de especificidade não sobrevivem à troca de coorte. Considera-se, por
consequência, que **o desempenho externo, e não o interno, constitui a estimativa defensável
do comportamento esperado do método em população não observada**, e é nele que devem se
apoiar quaisquer afirmações de generalização.

Registra-se que os coeficientes kappa das duas condições **não são diretamente comparáveis
entre si**, uma vez que o kappa depende da prevalência da classe majoritária, que é de
aproximadamente 0,70 na coorte externa e de aproximadamente 0,85 na base de desenvolvimento.
Por essa razão, a leitura adotada não é a comparação absoluta entre os dois valores, mas a
comparação de cada um contra o classificador trivial medido **na própria coorte** — referência
que, por construção, apresenta kappa nulo. Sob esse critério, todas as configurações
avaliadas permaneceram com o intervalo de confiança de 95% integralmente acima de zero na
coorte externa, o que sustenta a afirmação de que o método generaliza, ainda que com
desempenho reduzido.

**Ganhos metodológicos que atravessam coortes e ganhos que não atravessam.** A validação
externa produziu um resultado de natureza metodológica que se julga relevante registrar,
por condicionar a interpretação de todo procedimento de seleção de modelo adotado neste
trabalho. Duas modificações foram avaliadas sobre a mesma configuração de referência: a
imposição de estrutura temporal às predições por meio de um modelo oculto de Markov de dois
estados, e a ampliação da janela de contexto de cada época de ±2 para ±11 épocas,
aproximando-se da escala temporal empregada por algoritmos clássicos de actigrafia.

Em validação interna, a primeira modificação apresentou-se nitidamente superior, com ganho de
kappa de +0,123 (IC 95%: +0,105 a +0,142), aproximadamente o dobro do ganho obtido pela
segunda. Em validação externa, contudo, essa vantagem praticamente desapareceu — o ganho
remanescente foi de +0,036 (IC 95%: +0,008 a +0,067) — e veio acompanhada de **perda
estatisticamente distinguível de especificidade** (−0,037; IC 95%: −0,058 a −0,014). A
ampliação da janela de contexto, ao contrário, preservou magnitude e direção do efeito na
coorte externa, com ganho de kappa de +0,069 (IC 95%: +0,039 a +0,102) e de especificidade de
+0,095 (IC 95%: +0,065 a +0,130).

A explicação para a assimetria é atribuível ao objeto que cada modificação aprende. A matriz
de transição do modelo de Markov é estimada sobre a estrutura temporal de sono e vigília da
coorte de desenvolvimento e, por isso, incorpora a prevalência dessa coorte; transposta para
população com prevalência substancialmente distinta, a mesma matriz passa a penalizar
indevidamente as transições para vigília. A janela de contexto ampliada, por sua vez, não
codifica prevalência alguma: apenas altera a escala temporal sobre a qual as características
são computadas, e essa escala é propriedade do fenômeno fisiológico, não da coorte.

Deriva-se daí a limitação metodológica que se declara: **procedimentos de seleção de modelo
apoiados exclusivamente em validação cruzada interna são insuficientes neste domínio**. Neste
trabalho, especificamente, a validação interna teria selecionado a modificação cujo ganho não
se reproduz fora da coorte de origem, e apenas a validação externa permitiu distinguir o
ganho atribuível ao método do ganho atribuível à coorte. Essa distinção é registrada como
recomendação para trabalhos futuros na área, e não apenas como característica deste estudo.

**Número de coortes independentes.** A validação externa apoiou-se em **uma única** coorte
independente. Estava prevista a utilização de uma segunda base, com acelerometria de punho
obtida por dispositivo de consumo e rotulagem polissonográfica, o que permitiria distinguir o
que, na degradação observada, é atribuível à troca de coorte em geral e o que é atribuível às
particularidades daquela coorte específica. Essa segunda validação **não foi realizada**, por
indisponibilidade de acesso ao repositório que hospeda a base no ambiente de execução
empregado. Registra-se explicitamente que se trata de procedimento não executado, e não de
procedimento executado com resultado desfavorável. Com uma única coorte externa, a magnitude
da degradação relatada deve ser lida como estimativa pontual, não como medida da variabilidade
esperada entre coortes.

**Amostra própria.** As captações realizadas com o protótipo constituem amostra reduzida,
insuficiente para inferência estatística sobre população. Prestam-se à demonstração de
viabilidade técnica e à calibração de parâmetros, não à validação do método.

**Sobre a métrica de acurácia.** Registra-se, por rigor metodológico, que a acurácia global
não constitui métrica informativa neste domínio. Dado que a proporção de épocas de sono em
um registro noturno é elevada, um classificador trivial que atribuísse a totalidade das
épocas à classe "sono" alcançaria acurácia próxima àquela reportada por métodos
estabelecidos. Por essa razão, os resultados deste trabalho são apresentados acompanhados de
sensibilidade, especificidade, coeficiente kappa de Cohen e da comparação explícita com
classificadores de referência, conforme a seção de metodologia.

### X.5 Limitações de escopo deliberadas

As limitações a seguir decorrem de decisões de projeto, tomadas e registradas ao longo do
desenvolvimento.

**Não incorporação de fotopletismografia.** A medição de frequência cardíaca aumentaria
substancialmente a capacidade de discriminação do sistema, conforme a seção X.2. A
fotopletismografia, contudo, requer contato óptico com tecido perfundido, condição
incompatível com um dispositivo alojado no interior de um travesseiro. Avaliou-se
alternativa mecânica, pela captação de balistocardiografia; verificou-se, entretanto, que os
sinais de balistocardiografia e sismocardiografia possuem energia concentrada abaixo de
30 Hz e amplitude da ordem de 10 mg pico a pico, e que acelerômetros
microeletromecânicos comerciais, com densidade de ruído acima de 98 µg/√Hz, resultam em
resolução de aquisição de aproximadamente 0,54 mg — cerca de cinco bits — o que, conforme os
autores, compromete fortemente a análise do sinal; o sistema de alta resolução desenvolvido
naquele trabalho emprega acelerômetro com densidade de ruído inferior a 6,5 µg/√Hz (LEITÃO
et al., 2018). O componente adotado neste trabalho apresenta densidade de ruído de
400 µg/√Hz, medida a 10 Hz, em fundo de escala de ±2 g e taxa de amostragem de 1 kHz (TDK
INVENSENSE, 2013) — valor aproximadamente quatro vezes superior ao dos acelerômetros
comerciais mencionados e cerca de sessenta vezes superior ao do sensor dedicado. Registra-se
ainda que os trabalhos revisados que obtêm sinal cardiorrespiratório
em ambiente de cama empregam sensores piezoelétricos posicionados sob o colchão, e não
acelerômetros alojados no travesseiro. A incorporação dessa modalidade exigiria,
simultaneamente, substituição do transdutor, alteração da posição de instalação e
desenvolvimento de cadeia de processamento de sinal cardíaco, o que extrapola o escopo
delimitado.

**Não incorporação de captação de áudio.** A análise de sinal acústico permitiria abordar
fenômenos como ronco e padrão respiratório. Optou-se por não incorporá-la, por três razões:
alteraria o escopo declarado do trabalho, que se define como acelerométrico; elevaria
substancialmente a sensibilidade do dado tratado, com implicações relevantes sob a Lei Geral
de Proteção de Dados; e demandaria fundamentação adicional quanto à sua pertinência a um
trabalho fundamentado em actigrafia.

**Não medição de temperatura ambiente.** O sensor empregado disponibiliza leitura de
temperatura referente ao próprio circuito integrado, e não ao ambiente. Tal grandeza não é
apresentada ao usuário como temperatura ambiente, sendo esta uma distinção explicitamente
mantida na interface do sistema.

### X.6 Limitações de aplicação

O sistema **não constitui dispositivo médico** e não se destina a diagnóstico, triagem ou
acompanhamento clínico de distúrbios do sono. Não foi submetido a validação clínica, e as
informações que apresenta ao usuário limitam-se ao registro de movimento e a métricas dele
derivadas. O sistema não substitui polissonografia nem avaliação por profissional de saúde.

── FIM DO TEXTO ─────────────────────────────────────────────────────────────

---

## Checklist antes de colar no documento

- [x] ~~Substituir os marcadores `(REFERÊNCIA — ...)` pelas citações~~ — **feito em
      2026-09-10.** O texto usa agora citações autor-data. Resta apenas conferir se esse é o
      padrão adotado no TCC (se for numérico, converter) e montar a lista de referências
      final a partir de `docs/ML-DATASETS-E-PLANO.md` → "Fontes", onde cada entrada já traz
      autores, ano, título, periódico, volume, páginas e DOI.
- [x] ~~Montar as referências a partir dos artigos~~ — **autoria, ano, veículo, volume,
      páginas e DOI de todas as referências deste texto foram conferidos na fonte** em
      2026-09-10 (PubMed / Europe PMC / texto completo). A ressalva anterior de que "o único
      com autoria verificada é WALCH et al. (2019)" **não vale mais**.
- [ ] Substituir os marcadores `(REFERÊNCIA INTERNA — ...)` pelos números de seção
      corretos do próprio TCC.
- [ ] Ajustar `X` para o número da seção.
- [ ] **Ler os artigos citados antes de citá-los.** Isto **continua obrigatório**: ter a
      referência conferida não é o mesmo que ter lido o trabalho. `METODOLOGIA.md` é
      explícito: *sugestão de busca ≠ citação*. Todos os DOIs estão no §0.
- [ ] 🔧 **Ler as três notas de alteração de conteúdo** na seção "O que mudou na verificação
      de 2026-09-10", logo abaixo. Duas frases que estavam neste texto foram **removidas por
      não terem sido localizadas nas fontes**.
- [ ] Conferir se nenhum outro trecho do TCC afirma mais do que a seção X.2 permite —
      especialmente resumo, introdução e considerações finais.
- [ ] Verificar a coerência com o `README.md` público e com a nota de escopo exibida
      permanentemente na interface (`WEB-03`).

## O que entrou na medição de 2026-09-21

Notas para você, não para o texto. Todos os números abaixo saem dos JSONs versionados em
`ml/experimentos/saida/` e podem ser reconferidos sem rodar nada pesado:

```bash
cd ml
python -m experimentos.ml03b_otimizacoes --item resumo        # validação interna, N=92
python -m experimentos.ml04_validacao_externa --comparar      # validação externa, n=27
python -m experimentos.ml04_validacao_externa --lados         # efeito do lado, n=26
```

**1. O que é medido e o que é antecipado.** Até esta atualização, X.3 e X.4 diziam o que se
*esperava* que acontecesse. Agora há medição, e em dois pontos ela é mais dura que a
expectativa. Convém não amaciar na hora de colar: a queda de especificidade de 0,802 para
0,507 é o número honesto do trabalho, e declará-lo antes que a banca o extraia é a diferença
entre rigor e defesa.

**2. Procedência dos números de X.4.** Validação interna: *leave-one-subject-out* sobre 92
participantes da base de desenvolvimento. Validação externa: modelo ajustado nos 92 de uma
vez e aplicado a 27 participantes do Newcastle 2015, sem reajuste. Braço citado no texto:
treino com acelerometria de punho, teste no punho esquerdo. Os intervalos de confiança de
comparações entre configurações são de **bootstrap pareado da diferença** sobre os mesmos
participantes, e não da sobreposição de intervalos individuais — os dois critérios estão
implementados lado a lado, e o texto reporta o pareado.

**3. Procedência dos números de X.3 (lateralidade).** A diferença entre punhos é medida
**dentro de cada participante**, nos 26 com registro bilateral. Um participante (`ncl010`)
não possui registro do punho direito e, por isso, o pareamento fecha 26 e não 27. As 53
gravações **não** foram empilhadas como observações independentes: os dois punhos de um mesmo
participante são a mesma noite e a mesma pontuação, e empilhá-los estreitaria o intervalo de
confiança em cerca de 30% sem que nenhuma evidência nova tivesse entrado. O número incorreto
está calculado no JSON, sob a chave `d_INCORRETO_empilhado`, apenas para documentar o tamanho
do viés — **não use esse valor em tabela**.

**4. O achado metodológico é o parágrafo mais forte da seção.** A distinção entre ganho que
atravessa coorte e ganho que não atravessa não é uma limitação no sentido usual: é um
resultado. Se o texto do TCC tiver seção de contribuições, vale referenciá-lo de lá, porque
um trabalho de graduação que demonstra, com número, por que validação interna não basta está
fazendo afirmação metodológica defensável — e essa afirmação é independente do desempenho
absoluto do protótipo.

**5. O que continua pendente.** A segunda coorte externa (Walch et al., 2019 — acelerometria
de punho por dispositivo de consumo, PhysioNet) não foi baixada nem processada: o repositório
não é alcançável do ambiente de execução. Falta o dado **e** o carregador
(`ml/src/carregar/walch.py` não existe). O parágrafo "Número de coortes independentes" declara
isso como não executado, de propósito — se a situação mudar, é esse parágrafo que muda.

---

## O que mudou na verificação de 2026-09-10

Três alterações são **de conteúdo**, não de forma. Leia antes de colar.

> ⚠️ **Por que estas notas não reproduzem o texto removido.** Duas citações foram retiradas
> por não existirem nas fontes. Um aviso que repete a frase errada entre aspas **vira ele
> próprio a origem do erro** — basta alguém copiá-la do aviso. Por isso as notas abaixo
> descrevem *o que* estava errado e *onde*, sem reproduzir o texto. A versão anterior das
> frases está no histórico do git, se algum dia for preciso auditar.

🔧 **1. A citação da revisão sistemática de estadiamento foi substituída (seção X.1).** O
texto trazia uma frase **entre aspas**, atribuída à revisão sistemática sobre estadiamento
por actigrafia, afirmando em substância que o método confunde vigília quieta com sono e por
isso superestima o sono. **Essa frase não foi localizada no artigo publicado**
(YUAN et al., 2024, *Journal of Sleep Research* 33(4) e14143) — o documento anterior citava
o **preprint** de medRxiv, e a redação não corresponde à do texto revisado por pares. A
citação atual foi conferida palavra por palavra no texto completo da versão publicada.
**Use a que está lá; não reintroduza nenhuma outra formulação entre aspas sem abrir o
artigo.**

🔧 **2. Uma afirmação sobre a conclusão dos autores do estudo pediátrico foi removida
(seção X.3).** O texto atribuía aos autores, **entre aspas**, uma conclusão que **inverte a
métrica**: dava ao punho a vantagem pela métrica errada. **A afirmação não foi localizada no
artigo**, e o que ele de fato relata é o oposto naquele ponto — no estudo, é nas posições
próximas ao centro de massa que a **sensibilidade** é maior; a vantagem do punho está na
**especificidade**. A seção X.3 foi reescrita para dizer apenas o que está publicado, e o
argumento ficou **mais forte**, porque a especificidade é exatamente a métrica em jogo para
este trabalho.

🔧 **3. O número de ruído de 6,5 µg/√Hz foi reenquadrado.** O texto o apresentava como um
requisito de sistemas de balistocardiografia. **O artigo não enuncia esse requisito**: os
6,5 µg/√Hz são a especificação do acelerômetro que os próprios autores desenvolveram. A
seção X.5 foi reescrita com o que o artigo de fato sustenta — a comparação com os
acelerômetros comerciais de 98 µg/√Hz e a resolução de ~5 bits que eles produzem. O
argumento sobrevive intacto e agora é defensável linha a linha.

Além disso, a atribuição do estudo do MotionWatch8 a *"Rocha et al., 2025"*, feita por
inferência numa sessão anterior, **era falsa**. A autoria correta é LI; HALAKI; CHOW (2025).

## O que NÃO está neste texto, e por quê

- **A faixa de 14 a 60 min de superestimação em insônia** — ✅ **entrou.** Foi rastreada até
  PAQUET; KAWINSKA; CARRIER (2007), *Sleep* 30(10):1362–1369, onde aparece textualmente. É
  **síntese secundária** de seis estudos primários (listados no §0.3 do
  `ML-DATASETS-E-PLANO.md`), e está citada como tal — nenhum estudo primário isolado reporta
  a faixa. Se quiser um número único e primário, escolha um dos seis e cite o valor dele.
- **Números de dispositivos comerciais** (Fitbit, Jawbone). A faixa que circula em revisões
  não foi rastreada até o estudo original nesta pesquisa; citá-la seria atribuir número sem
  fonte.
- **Limitações de hardware ainda não medidas** — autonomia, aquecimento, estabilidade
  mecânica. Dependem da validação em protótipo físico e devem ser escritas depois, com os
  números reais em mãos.

## A leitura positiva, para as Considerações Finais

Uma seção de limitações honesta não enfraquece o trabalho — mas convém que o texto explicite
o enquadramento que a acompanha, preferencialmente nas Considerações Finais:

> O trabalho não se propõe a superar a actigrafia de punho em desempenho. Propõe-se a
> investigar **quanto se perde** ao substituir um sensor vestido por um sensor que o usuário
> não percebe. Trata-se de questão de engenharia específica, mensurável e ainda não
> respondida na literatura — não há base pública que reúna acelerometria em travesseiro com
> rotulagem validada —, e é precisamente a questão de pesquisa aqui formulada. O resultado é
> informativo em qualquer direção: perda pequena valida o conceito; perda expressiva
> quantifica um limite até então não quantificado e fundamenta as alternativas de
> arquitetura discutidas.

E há um segundo enquadramento, de natureza metodológica, que a validação externa tornou
disponível e que convém não deixar enterrado na seção de limitações:

> A avaliação conduzida em coorte independente permitiu separar, entre as melhorias
> investigadas, aquelas cujo ganho se reproduz fora da base de desenvolvimento daquelas cujo
> ganho não se reproduz. A modificação que apresentava o maior ganho sob validação cruzada
> interna mostrou-se, em coorte independente, praticamente sem efeito e acompanhada de perda
> de especificidade; a modificação de ganho interno mais modesto preservou magnitude e
> direção. Conclui-se que, neste domínio, a seleção de modelo apoiada exclusivamente em
> validação interna é insuficiente, e que a distinção entre ganho atribuível ao método e
> ganho atribuível à coorte requer avaliação externa explícita.

Essa é uma afirmação **independente do desempenho absoluto do protótipo**: vale mesmo que os
números do dispositivo sejam modestos, e é o tipo de contribuição que uma banca reconhece
como maturidade metodológica.
