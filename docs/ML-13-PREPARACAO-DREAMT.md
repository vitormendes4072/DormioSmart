# ML-13 — preparação e integridade da DREAMT

**Etapa concluída em 05/11/2026:** preparação e conferência dos dados, autorizadas
pelo autor. A ML-13 permanece aberta: carregador, previsão aprovada e avaliação
externa ainda precisam das etapas seguintes. Base de integração: `origin/develop`
`16232bf`; branch `feature/ML-13-coorte-dreamt`.

## O que foi executado

Nesta máquina Windows local, PowerShell e Python 3.11.9:

1. Extração seletiva do ZIP v2.2.0 já disponível, preservando o arquivo original.
   Foram escolhidos somente `data_64Hz/`, `Metadata.txt`, `participant_info.csv`,
   `LICENSE.txt` e `SHA256SUMS.txt`. O grupo `data_100Hz/` ficou no ZIP.
2. Verificação de tamanho, CRC do ZIP e SHA-256 em fluxo durante a extração.
   O manifesto do ZIP foi comparado byte a byte com o manifesto local obtido antes:
   coincidiram. A extração usa uma pasta nova, arquivos exclusivos e caminhos
   limitados ao conjunto escolhido; não sobrescreve arquivos preexistentes.
3. Nova leitura independente dos arquivos já extraídos pelo conferidor corrigido,
   com `--pasta` apontando para o armazenamento externo ao checkout.
4. Varredura da worktree e do armazenamento dos dados por reparse points, sem
   seguir links. Nenhuma junction ou outro reparse point foi encontrado.

| Medição | Resultado |
|---|---:|
| CSVs extraídos de `data_64Hz/` | 100 |
| Metadados cobertos pelas somas oficiais | 3 |
| Manifesto `SHA256SUMS.txt`, separado dos alvos de seu próprio conteúdo | 1 |
| Arquivos físicos extraídos | 104 |
| CRCs dos membros selecionados conferidos | 104 |
| Bytes extraídos, incluindo o manifesto | 14.108.986.504 |
| SHA-256 dos alvos oficiais conferidos | **103/103** |
| Arquivos ausentes / somas diferentes | **0 / 0** |
| Junctions na worktree e nos dados | **0** |

O CRC de todo o ZIP **não** foi testado: foram lidos integralmente apenas os 104
membros selecionados. Os SHA-256 desses 103 alvos foram calculados duas vezes,
durante a extração e após ela. Isso não é uma avaliação do modelo.

## O defeito do conferidor e seus controles

A versão anterior de `ml/ferramentas/baixar_dreamt.py`, já commitada na branch em
`cb65881`, aceitava o conjunto que encontrasse no manifesto. Um arquivo vazio
produzia `conferem 0 · faltam 0 · diferem 0` e código de saída zero. Omissões de
CSV ou metadado também diminuíam o alcance da conferência sem reprovação.

Foram criados **13 testes em `ml/testes/test_baixar_dreamt.py`**, usando somente
arquivos artificiais. Antes da correção, **8 falharam e 5 passaram**. A execução
foi repetida contra uma cópia congelada do código anterior e deu a mesma contagem.
Essa é a base relevante do controle: o conferidor ainda não existe em
`origin/develop` `16232bf`, portanto uma falha de import nesse commit não provaria
o defeito. Os logs e JUnit preservam a comparação efetivamente executada.

Depois da correção, os 13 passaram. A suíte completa de ML passou **190 testes**.

| Controle executado | Antes | Corrigido |
|---|---|---|
| 103 arquivos íntegros | aceita | aceita |
| Arquivo ausente | reprova pelo caminho ausente | reprova pelo caminho ausente |
| Conteúdo adulterado | reprova pela soma | reprova pela soma |
| Manifesto ausente | reprova | reprova |
| Manifesto vazio | **aceitava indevidamente** | reprova |
| Manifesto omitindo um CSV existente | **aceitava indevidamente** | reprova |
| Manifesto omitindo cada um dos três metadados | **aceitava indevidamente** | reprova nos três casos |
| 103 entradas com um ID substituído | **aceitava indevidamente** | reprova |
| Linha malformada / entrada duplicada | **aceitava indevidamente** | reprova nos dois casos |
| Manifesto também listando o grupo de 100 Hz | aceita o escopo de 64 Hz | aceita o escopo de 64 Hz |

A correção exige os **103 caminhos esperados**, não apenas a quantidade. A lista
dos 100 CSVs vem do manifesto de v2.2.0: IDs de S002 a S103, exceto S041 e S060.
Entradas oficiais de `data_100Hz/` podem estar no manifesto completo, mas não
substituem nenhum desses alvos. Digest inválido, linha malformada, duplicata ou
entrada esperada ausente impedem o sucesso antes da leitura dos dados.

Conferir novamente, informando a pasta local explicitamente:

```sh
python ml/ferramentas/baixar_dreamt.py --pasta CAMINHO_DREAMT
python -m pytest ml/testes/test_baixar_dreamt.py -q
```

## Onde ficam os dados e a evidência local

- ZIP: mantido no armazenamento local de Downloads; não foi copiado para a worktree.
- Dados extraídos: pasta externa ao checkout, `dados-locais/dreamt-2.2.0`, sob a
  pasta de trabalho do projeto. O caminho absoluto foi informado ao autor.
- Logs, JUnit, cópia do conferidor anterior e JSON de extração/integridade:
  `ml/dados/processado/ml13_preparacao/` na worktree da ML-13, ignorado pelo Git.
- **Não há junctions** nesses diretórios. Nenhuma foi criada nesta etapa.
- CSVs, informações dos participantes e licença extraída permanecem locais,
  fora do Git. Os testes publicados usam dados artificiais.

Antes de copiar, mover ou remover pastas em qualquer etapa futura, repetir a
varredura por links; desfazer junctions com `rmdir` sem `/s`. Para copiar evidência,
usar `robocopy /E /XJ` e conferir o inventário.

## O que foi apenas lido e o que ainda falta

Foram lidos `Metadata.txt`, `LICENSE.txt`, o cabeçalho de um CSV e os caminhos
do código existente. A documentação declara grade de 64 Hz, aceleração E4 de
origem a 32 Hz e escala de 1/64 g; a correspondência efetiva dessas propriedades
com os sinais ainda exige inspeção. Preparação `P` e rótulos ausentes também
precisam de tratamento explícito no carregador.

Não foram extraídas features da DREAMT, calculadas prevalências empíricas dos
rótulos, treinados modelos, geradas previsões ou calculadas métricas de avaliação.
O carregador e `ml04 --coorte dreamt` não foram implementados nesta etapa.

O [plano e a previsão registrados](PLANO-ML-13-COORTE-DREAMT.md) seguem para
aprovação antes de avançar. O texto acadêmico e o Google Docs não foram alterados.
