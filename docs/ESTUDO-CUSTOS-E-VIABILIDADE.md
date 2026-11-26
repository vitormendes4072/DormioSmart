# Estudo de custos e viabilidade do Dormio (`VIA-03`)

> **Estado em 25/11/2026.** Levantamento feito nas sessões de 25/11 com o Claude Code, a partir das
> notas e anúncios das compras do `HW-02` e de pesquisa de preços na internet. Os números deste
> arquivo foram lidos da planilha de trabalho no dia 25/11; **a planilha é a fonte viva** e se
> recalcula sozinha quando uma premissa muda. Onde este arquivo e a planilha divergirem depois desta
> data, vale a planilha, e este arquivo deve ser atualizado com nova data.

## 0. Onde está o material

| Material | Onde | Observação |
|---|---|---|
| **Planilha "Dormio: componentes e custos do dispositivo"** | Google Drive do autor (Google Sheets) | **Fora do repositório**, porque registra compras pessoais (notas, pedidos e formas de pagamento). O link está com os autores. |
| Rascunhos de pedido de cotação para a homologação na Anatel (8) | Gmail do autor, pasta Rascunhos | **Não enviados.** Sem destinatário e com "[seu nome]" para preencher. |
| Este estudo | `docs/ESTUDO-CUSTOS-E-VIABILIDADE.md` | Resumo datado, para o texto do TCC. |
| Esquemático e lista de componentes | `docs/diagramas/DIAG-02-esquematico.py` (folha v4 na PR #288) e `docs/ESTUDO-ENERGIA.md` §8.1 | O que a planilha chama de U1, U2, U3, U4, B1, Q1, F1, S1, C1, C2, R1 e R2. |

**As abas da planilha:**

| Aba | Para que serve |
|---|---|
| Custo por unidade | O custo de componentes de 1 protótipo, com o preço pago (o número do RD-17). Quando a peça foi comprada em duas lojas, vale o menor preço pago. Tem o percentual de cada item no total. |
| Custo em lote | O custo de 1 unidade num lote de 100, comprando cada peça onde ela sai mais barata (AliExpress, Mercado Livre e lojas nacionais), com os impostos de importação. |
| Preço e margem | Preço de venda, margem, lucro, investimento, retorno, outros custos do negócio e cenários por tamanho de lote. |
| Concorrentes | Produtos parecidos à venda no Brasil, com preço conferido na página. |
| Homologação Anatel | O que é preciso para vender: enquadramento, ensaios, custos, etapas, documentos, certificadores e o texto do pedido de cotação. |
| Total gasto | Tudo o que saiu do bolso, por categoria e por loja, e quanto das peças sobrou como reserva. |
| Compras | As 27 linhas das notas e pedidos, com o desconto de cada loja rateado. |
| Lojas | Total da nota, desconto e valor pago em cada loja. |

## 1. Custo do protótipo (RD-17)

**Critério:** soma do que foi pago pelas peças de **um** aparelho. O desconto de cada loja foi
repartido entre os itens na proporção do valor. Peças compradas em pacote entram pela fração usada
(um adaptador de um pacote de 10 a R$ 30 entra como R$ 3,00). Reservas, ferramentas e itens de
bancada ficam fora. Quando a mesma peça foi comprada em duas lojas, vale o menor preço pago.

| Ref. | Componente | Loja | Custo na unidade | % do total |
|---|---|---|---:|---:|
| U1 | ESP32 DOIT DevKit V1 | Mamute | R$ 62,54 | 28,5% |
| B1 | Célula LiFePO4 18650 Rontek | Mercado Livre | R$ 45,00 | 20,5% |
| U3 | Placa de proteção LiFePO4 1S | Mercado Livre | R$ 30,90 | 14,1% |
| U4 | Carregador TP5000 (USB-C, 3,6 V), fora do travesseiro | Mercado Livre | R$ 28,90 | 13,2% |
| U2 | MPU6050 (GY-521) | Mercado Livre | R$ 23,00 | 10,5% |
| — | Suporte para 18650 | Mercado Livre | R$ 14,90 | 6,8% |
| — | Os outros 10 itens (Q1, adaptador, F1, porta-fusível, S1, C1, R1, R2, C2, termorretrátil, cabinho) | Santa Ifigênia Componentes e Mercado Livre | R$ 14,12 | 6,4% |
| — | Encapsulamento (`HW-04`) | a definir | — | — |
| | **Dentro do travesseiro** | | **R$ 190,46** | |
| | **Total, com o carregador** | | **R$ 219,36** | 100% |

- Os seis primeiros itens somam **93,6%** do custo.
- O C2 está com o preço do cerâmico de 1 nF comprado por engano, até a troca pelo de 100 nF.
- **Total gasto no projeto até 25/11: R$ 454,60** — Mamute R$ 225,00 (cupom de R$ 237,10 com
  R$ 12,10 de desconto), Santa Ifigênia Componentes R$ 19,00 (pedido 103530), Mercado Livre
  R$ 210,60 (dois pedidos). Desse total, R$ 131,05 são bancada e ferramentas (ferro de soldar,
  multímetro, estanho, protoboards e cabos) e R$ 103,90 são reservas e sobras de peças.

## 2. Custo em lote de 100 unidades

**Método:** para cada peça, o menor preço encontrado em 25/11 no AliExpress, no Mercado Livre, na
Mamute e na Eletrogate, para a mesma especificação. Os importados levam os impostos do Remessa
Conforme sobre o pedido inteiro.

**Premissas (editáveis na aba):** câmbio R$ 5,89 por US$ (PTAX de venda de 25/11, entre R$ 5,8825
e R$ 5,8940 conforme a fonte); imposto de importação de 60% acima de US$ 50, com desconto de
US$ 30 por remessa; ICMS de 20% calculado por dentro (a estimativa que o próprio AliExpress mostrava
nos anúncios; **a alíquota de SP está a confirmar**). Fator de impostos dos importados: **1,88**.

| Ref. | Componente | Onde | Custo por unidade (com impostos) | No protótipo |
|---|---|---|---:|---:|
| U1 | ESP32 DOIT DevKit V1 | Mercado Livre (R$ 35,28) | R$ 35,28 | R$ 62,54 |
| B1 | Célula LiFePO4 Rontek 2 000 mAh | Mercado Livre (R$ 31,90) | R$ 31,90 | R$ 45,00 |
| U2 | MPU6050 (GY-521) | AliExpress (pacote de 10) | R$ 14,71 | R$ 23,00 |
| U4 | Carregador TP5000 USB-C | AliExpress | R$ 6,84 | R$ 28,90 |
| — | Suporte para 18650 | AliExpress (pacote de 10) | R$ 2,77 | R$ 14,90 |
| — | Porta-fusível com fios | AliExpress (pacote de 5) | R$ 2,63 | R$ 3,45 |
| — | Fio de silicone 22 AWG (60 cm, estimativa) | AliExpress (rolo de 20 m) | R$ 2,01 | R$ 0,98 |
| U3 | Placa de proteção LiFePO4 1S (3 A) | AliExpress (pacote de 20) | R$ 1,77 | R$ 30,90 |
| — | Os outros 8 itens (S1, adaptador, C1, F1, termorretrátil, Q1, C2, R1/R2) | AliExpress | R$ 3,77 | |
| | **Custo de 1 unidade no lote** | | **R$ 101,69** | **R$ 219,36** |

**Redução: 53,6%.** Investimento em peças para o lote inteiro: R$ 10.169,43.

**Para a defesa, os cuidados que vão junto com esse número:**
1. **Preços da Black Friday do AliExpress** (até 03/12/2026). Vários são promocionais e limitados
   a uma compra por cliente. Fora da promoção, o custo tende a ser maior.
2. **A célula não pode ser importada:** o AliExpress não envia células LiFePO4 avulsas para o
   Brasil. Ela vem da Rontek pelo Mercado Livre, com cerca de 25 unidades em estoque no anúncio;
   para 100, é preciso cotar com a empresa.
3. **Célula genérica recusada de propósito.** Há kits de 10 células LiFePO4 sem marca a R$ 6,78
   cada. Ficaram fora porque célula sem fabricante identificado costuma ter capacidade inflada, e
   ela vai dentro de um travesseiro (mesmo critério do `docs/ESTUDO-ENERGIA.md`).
4. **O ESP32 nacional ganhou** do importado com impostos (R$ 38,65). Com isso o imposto de
   importação do pedido cai.
5. **Lojas nacionais de eletrônica** (Mamute e Eletrogate) vendem a preço de varejo: ESP32 de
   R$ 52 a R$ 63 e MPU6050 a R$ 18,90. Nenhuma vende célula LiFePO4.

## 3. Preço de venda, margem e retorno

**Premissas (todas editáveis, em amarelo na aba, a confirmar):** montagem e teste de 0,5 h a
R$ 25/h; embalagem e manual R$ 5; Simples Nacional 4,5% (primeira faixa do Anexo II, a confirmar
com contador); comissão de marketplace 14%; frete pago pelo vendedor R$ 20; o gasto do protótipo
(R$ 454,60) rateado no lote; preço de exemplo R$ 279,90, próximo do sugerido para 30% de margem.

**Custo total por unidade: R$ 123,74** (peças R$ 101,69 + montagem R$ 12,50 + embalagem R$ 5,00 +
rateio do protótipo R$ 4,55).

| A R$ 279,90, por unidade | Valor |
|---|---:|
| Preço | R$ 279,90 |
| (−) Impostos (4,5%) | R$ 12,60 |
| (−) Comissão (14%) | R$ 39,19 |
| (−) Frete | R$ 20,00 |
| (−) Custo total | R$ 123,74 |
| **Lucro antes dos outros custos do negócio** | **R$ 84,38 (30,1%)** |

**Outros custos do negócio, lote de 100 vendido em 6 meses:** abertura do CNPJ R$ 500; contador
R$ 150/mês (R$ 900); marketing R$ 1.000; garantia e trocas com 3% do lote (R$ 477,58); capital
parado a 1% ao mês, com compra em remessas de 100 (R$ 357,58); **homologação na Anatel R$ 10.000**
(meio da faixa de R$ 5.000 a R$ 15.000; ver §4); renovação do certificado a cada 24 meses,
R$ 3.000 cada (estimativa). Total: R$ 13.235,17.

| Lote de 100 a R$ 279,90 | Sem os outros custos | Com todos os custos |
|---|---:|---:|
| Investimento total | R$ 12.374,03 | R$ 25.609,19 |
| Lucro do lote | R$ 8.437,83 | **−R$ 4.797,34** |
| ROI | 68,2% | **−18,7%** |
| Vendas para recuperar o investimento | cerca de 60 | cerca de 123 (mais que o lote) |

**Cenários por tamanho de lote** (mesmo preço, todos os custos, compra em remessas de 100, peças ao
custo do lote de 100, o que é conservador):

| Lote | Meses para vender | Lucro final | ROI | Lucro por unidade |
|---:|---:|---:|---:|---:|
| 50 | 3 | −R$ 7.866,17 | −43,1% | −R$ 157,32 |
| 100 | 6 | −R$ 4.797,34 | −18,7% | −R$ 47,97 |
| 150 | 9 | −R$ 1.798,31 | −5,4% | −R$ 11,99 |
| **200** | 12 | **R$ 1.359,92** | **3,4%** | R$ 6,80 |
| 300 | 18 | R$ 7.517,18 | 13,7% | R$ 25,06 |
| 500 | 30 | R$ 16.831,70 | 19,3% | R$ 33,66 |
| 1 000 | 60 | R$ 44.618,00 | 27,3% | R$ 44,62 |

**Conclusão para a banca:** a homologação na Anatel é um custo fixo que um lote de 100 não paga a
R$ 279,90. O negócio dá lucro a partir de cerca de **200 unidades**, e o retorno melhora com a
escala, **desde que a compra seja feita em remessas**. Com tudo comprado de uma vez, o custo do
capital parado cresce com o quadrado do lote e derruba o retorno dos lotes grandes (na primeira
versão do modelo, 1 000 unidades davam ROI de 9,7%).

## 4. Homologação na Anatel

- **Vender exige homologação do produto final**, mesmo com o módulo ESP32-WROOM-32 homologado: o
  certificado é do produto completo (Resolução 715/2019, alterada pela 780/2025; Categoria II,
  radiação restrita, Ato 14.448/2017). As fontes divergem sobre quanto do ensaio de rádio do módulo
  ainda pode ser reaproveitado depois da 780/2025; concordam que o produto final é avaliado.
- **Ensaios que continuam:** compatibilidade eletromagnética (Ato 1.120/2018), segurança elétrica
  (IEC 62368-1) e, **possivelmente, SAR**, porque o aparelho fica perto da cabeça (Ato 1.630/2021).
  O SAR sozinho custa de R$ 15.000 a R$ 40.000 por modelo: é a pergunta mais importante da cotação.
- **O protótipo do TCC não precisa** enquanto não for vendido. A Declaração de Conformidade é para
  uso próprio e não autoriza venda.
- **Custo:** a Anatel não cobra taxa desde 2019; o custo é do laboratório e do organismo
  certificador (OCD). Referência de mercado para dispositivo IoT simples: R$ 5.000 a R$ 15.000.
  Reprovação: R$ 3.000 a R$ 20.000 por correção e reteste. Validade, em regra, de 2 anos.
- **Prazo:** cerca de 3 a 6 semanas (análise, ensaios, certificado e registro no Mosaico).
- **Falta para pedir:** CNPJ, amostras (normalmente 2 ou 3), manual em português, fotos e etiqueta,
  o número de homologação do módulo da placa comprada e a declaração técnica do módulo.
- **Certificadores listados** (lista do Teleco, sem data; confirmar na Anatel quais atendem radiação
  restrita): CPqD, IBRACE, CTCP, Master/NCC, TÜV Rheinland Brasil, ACTA, Fundação Vanzolini e TECPAR.
  Os rascunhos dos pedidos de cotação estão no Gmail do autor, sem enviar.
- **Limite:** os custos vêm de certificadoras, com interesse comercial; não há tabela oficial. O
  valor real só sai das cotações.

## 5. Concorrentes (preços conferidos nas páginas em 25/11/2026)

| Produto | Tipo | Preço | À venda? |
|---|---|---:|---|
| Persono Sense + travesseiro mmartan Fits You | Travesseiro com sensor | R$ 449 (lançamento, Abit, 30/08/2022) | **Não encontrado** no site da mmartan, no Mercado Livre nem na Amazon; o site da Persono não abre (certificado inválido) |
| Xiaomi Mijia Smart Pillow | Travesseiro com sensor | ~R$ 190 (259 yuan, notícia de 11/09/2022) | **Não encontrado**; nunca foi vendido no Brasil |
| Withings Sleep Analyzer | Sensor sob o colchão | R$ 1.876,18 (Amazon, importado) | Sim; R$ 1.943,18 na UAI Adventure |
| Beautyrest Sleeptracker | Sensor sob o colchão | R$ 966,20 (Amazon, importado) | Sim |
| EMFIT QS | Sensor sob o colchão | — | Indisponível na Amazon, sem previsão |
| Xiaomi Smart Band 9 | Pulseira | R$ 179,90 (Amazon, via Zoom) | Sim |
| Xiaomi Smart Band 9 Active | Pulseira | R$ 187,00 (Magazine Luiza, via Zoom) | Sim |

Mediana dos produtos à venda: **R$ 576,60**.

**Para a banca:**
- **Não há, em 25/11/2026, nenhum travesseiro com monitoramento de sono à venda no Brasil.** O único
  nacional (Persono com a mmartan) saiu do mercado.
- Quem quer medir o sono sem nada no corpo só encontra sensores de colchão importados, de R$ 966 a
  R$ 1.876. A R$ 279,90, o Dormio fica bem abaixo deles e pouco acima das pulseiras, que exigem
  dormir com algo no pulso.
- **Leitura honesta:** a saída do Persono também pode indicar pouca demanda. O Dormio tenta um nicho
  já testado que não se firmou, e por isso o custo baixo é essencial.
- Ao preço de lançamento do Persono (R$ 449), a margem do Dormio seria de 49,5%.
- **Erro corrigido no caminho:** a primeira versão da tabela usou preços dos resumos da busca, sem
  abrir as páginas. Conferidos depois, quatro estavam errados (Withings, Beautyrest, EMFIT e Band 9
  Active; o Beautyrest quase dobrou). Todos os preços acima foram lidos nas páginas.

## 6. O que levar para o texto do TCC

- [ ] RD-17 com o número: **R$ 219,36** por protótipo (R$ 190,46 sem o carregador), sem o
      encapsulamento.
- [ ] A tabela de custo por componente, com o percentual, e a observação de que seis itens somam
      93,6%.
- [ ] O custo em lote (R$ 101,69, −53,6%) com as quatro ressalvas da §2.
- [ ] A decisão de segurança de não usar célula genérica, e o motivo.
- [ ] Preço, margem e a tabela de cenários por lote, com a conclusão das 200 unidades.
- [ ] A homologação na Anatel como custo fixo e risco (o SAR em especial), e que o protótipo
      acadêmico não precisa dela.
- [ ] A comparação com os concorrentes e a ausência de travesseiro com sensor à venda.
- [ ] As premissas em amarelo como limitações declaradas.

## 7. Pendências (carregadas pelo `VIA-03` no backlog)

1. **Encapsulamento (`HW-04`):** sem preço; vai somar ao custo do protótipo e do lote.
2. **Cotações da Anatel:** enviar os rascunhos e trocar os R$ 10.000 e os R$ 3.000 de renovação
   pelos valores reais, e confirmar se o SAR se aplica.
3. **Cotação da Rontek para 100 células.**
4. **Confirmar** a alíquota de ICMS de SP, o enquadramento no Simples Nacional e os custos de abrir
   a empresa (com contador), a comissão do canal de venda e o frete.
5. **Trocar o C2** pelo cerâmico de 100 nF e atualizar o preço.
6. **Rever os preços do AliExpress depois da Black Friday** (depois de 03/12/2026).

## 8. Fontes

- Notas e pedidos das compras (Mamute, Santa Ifigênia Componentes, Mercado Livre), fotografados
  pelo autor em 25/11/2026 — na aba Compras da planilha.
- Anúncios do AliExpress, Mercado Livre, Mamute e Eletrogate consultados em 25/11/2026 — os links
  estão na aba Custo em lote.
- Remessa Conforme: [Senado Notícias, MP 1.357/2026](https://www12.senado.leg.br/noticias/materias/2026/05/13/medida-provisoria-zera-taxa-das-blusinhas-para-importacoes-de-ate-us-50); [Forbes Brasil](https://forbes.com.br/forbes-money/2026/09/taxa-das-blusinhas-veja-como-ficam-as-compras-internacionais/).
- Câmbio: [Captário](https://captario.com.br/cotacao/dolar); [Piranot, PTAX de 25/11](https://www.piranot.com.br/2026/11/25/noticias/economia/dolar-ptax-fecha-em-r-58825-nesta-quarta-feira-25-11-2026-veja-a/).
- Anatel: [Yes Certificações, custos](https://yescert.com.br/blog/anatel/quanto-custa-a-homologacao-anatel-guia-completo-de-custos/); [Yes Certificações, módulos IoT](https://yescert.com.br/blog/anatel/modulos-iot-2026-wifi-bluetooth-zigbee-lora-reaproveitamento/); [ABCP, módulos IoT](https://abcpcertificacao.com.br/certificacao-anatel/modulos-iot/); [Anatel, Resolução 680/2017](https://informacoes.anatel.gov.br/legislacao/index.php/component/content/article?id=936); [Teleco, lista de OCDs](https://www.teleco.com.br/cert.asp); [Tech in Brazil, uso próprio](https://techinbrazil.com.br/homologacao-da-anatel-para-produtos-de-uso-proprio).
- Concorrentes: [Abit, Persono e mmartan](https://www.abit.org.br/noticias/persono-e-mmartan-lancam-seu-primeiro-travesseiro-com-tecnologia-que-monitora-o-sono); [TecMundo/Estadão, Xiaomi Smart Pillow](https://www.estadao.com.br/tecmundo/produto-e-review/247407-xiaomi-lanca-travesseiro-inteligente-monitorar-sono/); [Amazon, Withings Sleep](https://www.amazon.com.br/Withings-Sleep-Rastreamento-colch%C3%A3o-an%C3%A1lise/dp/B078Z1B34S); [UAI Adventure, Withings](https://uaiadventure.com.br/produto/withings-sleep-analyzer/); [Amazon, Beautyrest](https://www.amazon.com.br/Beautyrest-Sleeptracker-Monitor-Rastreador-Aplicativo/dp/B06VXH15YC); [Amazon, EMFIT QS](https://www.amazon.com.br/EMFIT-QS-Monitor-sono-colch%C3%A3o/dp/B0158W3E2A); [Zoom, Mi Band 9](https://www.zoom.com.br/smartwatch/xiaomi-mi-band-9); [Zoom, Smart Band 9 Active](https://www.zoom.com.br/smartwatch/smartwatch-xiaomi-smart-band-9-active).
