#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gera `docs/CORRECOES-APLICADAS.md` e `docs/PENDENCIAS-ABERTAS.md` a partir das
duas tabelas de dados deste arquivo.

── POR QUE UM SCRIPT, E NÃO DOIS DOCUMENTOS ESCRITOS À MÃO ──────────────

Os dois documentos que este script emite são, antes de tudo, **contagens**: "N
defeitos", "M vieram de execução", "K itens dependem de decisão sua". O §3 de
`docs/LICOES-APRENDIDAS.md` ("número herdado que ganha autoridade sem ter
procedência") e a regra 2 dele ("número citado em documento tem de sair de um
script que roda") valem para esses números como valem para a autonomia do
buffer e para o σ do `FW-06`.

Escrever as contagens à mão criaria exatamente o padrão: um total no topo do
documento, autoridade de estar escrito num lugar formal, e nada que o recalcule
quando uma linha entra ou sai. Aqui o total **não existe** no texto — ele é
`len()` da tabela, e a distribuição por instrumento é um `Counter`. Mexer numa
linha move o número no documento seguinte, obrigatoriamente.

    python scripts/consolidar_registro.py            # grava os dois documentos
    python scripts/consolidar_registro.py --conferir  # exit != 0 se divergirem

O `--conferir` é o modo do CI: ele regenera em memória e compara com o que está
em disco. Se alguém editar os documentos à mão, ele reprova — porque documento
gerado e editado à mão é documento que mente sobre a própria procedência.

── O QUE ESTA TABELA É, E O QUE ELA NÃO É ───────────────────────────────

Cada linha de `DEFEITOS` é um defeito que **este repositório sustenta**: há
commit, ou há entrada de diário com procedência, ou há artefato que dá para
abrir. O campo `procedencia` separa os dois casos:

  * `completa` — commit **e** artefato reabrível (teste, script, seção de
    documento). Dá para reconferir sem acreditar em ninguém.
  * `parcial`  — só a mensagem de commit, ou só a entrada de diário. Entra
    porque omitir seria pior, e entra **marcado**, porque citar um defeito de
    procedência parcial como se fosse medido é o §3 de novo.

**O que foi deliberadamente deixado fora**, para a contagem não inflar:

  * Funcionalidade entregue (`AUTH-01..05`, `UI-01..07`, `DASH-01/02/05/06/10`,
    `APP-01/07/08`, `BRAND-01/03`, `DEMO-01`, `SEC-04`, `WEB-04`,
    `DATA-01/04/05`, `CI-01`, o bloco `ML-01..ML-08` como entrega). Entregar o
    que não existia não é corrigir defeito.
  * Otimização sem defeito de corretude (`8d67a1b`, `2f7669c`, `0736397`).
  * Endurecimento que não consertou comportamento errado (`SEC-02`, `SEC-03`,
    `SEC-06` como desenho, `FW-05` como requisito).

**O que foi deliberadamente deixado DENTRO**, e é escolha discutível: defeito
em **documento** e defeito em **instrumento de medida**. Os dois entram porque,
neste projeto, são a maior parte do que o registro tem de instrutivo — uma
afirmação falsa numa política de privacidade e um vetor dourado que se regrava
sozinho são defeitos com consequência, e tratá-los como "não é código" seria
perder justamente o §4 e o §6 das lições. Quem precisar da contagem só de
código tem o campo `area` para filtrar.

── O CAMPO `achado_por`, QUE É O QUE DÁ VALOR AO ARQUIVO ────────────────

Oito instrumentos, e a distinção entre eles é o produto deste documento:

  leitura            inspeção do código ou do documento, raciocinando sobre
                     ele, sem executar nada e sem conferir contra terceiro.
  cálculo            aritmética sobre os próprios números do projeto. Barato,
                     e neste projeto derrubou premissas grandes.
  execução           rodar código do projeto — suíte, job, compilador, script
                     de verificação — e a SAÍDA acusar. O defeito não estava
                     escondido: estava não exercitado.
  controle positivo  provocar o defeito de propósito e exigir que a
                     verificação acuse. Inclui verificação por mutação. É o
                     único instrumento que mede o ALCANCE de uma verificação.
  inventário         conferir estado declarado contra estado real: `grep` por
                     símbolo, `git ls-files` contra o disco, varredura de
                     afirmações em documentos. Não é execução (nada roda
                     contra dado) nem leitura (não se raciocina, se confere).
  terceiro           especificação, documentação oficial, artigo, issue ou API
                     de terceiro. O artefato que decide a resposta está fora
                     do repositório.
  dado real          só apareceu com o arquivo ou a medição real em mãos.
  uso real           alguém usou o produto como usuário.

A fronteira `execução` × `inventário` foi a mais difícil de traçar e está
traçada assim de propósito: o `grep` que mostrou que as features existiam só em
Python não rodou o pipeline, conferiu a ausência de um símbolo — é inventário.
A suíte do `ml/` que acusou o contrato 2.5.0 contra o documento em 2.5.1 rodou
e falhou — é execução. A distinção importa porque os dois custam coisas
diferentes: inventário custa um minuto e ninguém o faz; execução custa
infraestrutura e o projeto a montou.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

#: Hash abreviado ou completo, como aparece no campo `commit`.
HASH = re.compile(r"\b[0-9a-f]{7,40}\b")

LEITURA = "leitura"
CALCULO = "cálculo"
EXECUCAO = "execução"
CONTROLE = "controle positivo"
INVENTARIO = "inventário"
TERCEIRO = "terceiro"
DADO_REAL = "dado real"
USO_REAL = "uso real"

INSTRUMENTOS = [
    LEITURA, CALCULO, EXECUCAO, CONTROLE, INVENTARIO, TERCEIRO, DADO_REAL, USO_REAL,
]

SEG, UI, FW, ML, DOC, INFRA = (
    "Segurança", "Interface", "Firmware", "Dados e ML", "Documentação", "Infraestrutura",
)

AREAS = [SEG, UI, FW, ML, DOC, INFRA]


@dataclass
class Defeito:
    data: str
    area: str
    item: str
    defeito: str
    achado_por: str
    causa: str
    correcao: str
    commit: str
    procedencia: str = "completa"
    premissa: str = ""          # não vazio => a correção revelou premissa errada
    nota: str = ""
    # True quando a coisa defeituosa ERA uma verificação do projeto: um teste,
    # uma guarda de CI, um harness de mutação, um vetor de referência. Separado
    # porque "a verificação estava errada" é uma classe de dano diferente de
    # "o código estava errado", e é o §4 das lições em forma contável.
    instrumento: bool = False
    # A premissa em UMA frase, escrita para a tabela de premissas. Antes a
    # tabela pegava a primeira frase de `premissa`, e em cerca de metade das
    # linhas essa frase era comentário, não premissa ("A tentação era
    # afrouxar a tolerância"). Obrigatório quando há `premissa`.
    premissa_curta: str = ""
    # False quando a linha fica VISÍVEL mas fora de toda contagem — hoje, só o
    # `ML-04b`, em que a hipótese se confirmou e o que se corrigiu foi a
    # afirmação, não um defeito. Pela mesma regra que deixa fora "entregar o
    # que não existia", confirmar uma hipótese não é corrigir defeito.
    conta: bool = True
    # True quando a linha cobre uma FAMÍLIA de defeitos de mesma causa e mesma
    # correção (as dez armadilhas de formato, os quatro defeitos de
    # referência). Agrupar é deliberado: a correção foi uma só.
    familia: int = 1

    def __post_init__(self) -> None:
        if self.achado_por not in INSTRUMENTOS:
            raise ValueError(f"instrumento desconhecido: {self.achado_por}")
        if self.area not in AREAS:
            raise ValueError(f"área desconhecida: {self.area}")
        if self.procedencia not in ("completa", "parcial"):
            raise ValueError(f"procedência inválida: {self.procedencia}")
        if bool(self.premissa) != bool(self.premissa_curta):
            raise ValueError(f"{self.item} ({self.data}): `premissa` e "
                             "`premissa_curta` vêm juntas ou não vêm")
        if self.procedencia == "completa" and not HASH.findall(self.commit):
            raise ValueError(f"{self.item} ({self.data}): procedência completa "
                             "sem hash de commit")


@dataclass
class Pendencia:
    item: str
    grupo: str
    o_que: str
    peso: str
    decisao: str = ""           # obrigatório no grupo DECISAO
    camada_backlog: str = ""
    nota: str = ""


# Os cinco grupos do levantamento, na ordem em que foram pedidos.
SOFTWARE = "software"
DECISAO = "decisão"
ACAO = "ação"
HARDWARE = "hardware/coleta"
TERCEIRO_G = "terceiro"

GRUPOS = [SOFTWARE, DECISAO, ACAO, HARDWARE, TERCEIRO_G]

ROTULO_GRUPO = {
    SOFTWARE: "A — Depende só de software: dá para fazer a qualquer momento",
    DECISAO: "B — Depende de decisão do Vitor",
    ACAO: "C — Depende de ação do Vitor que não é decisão",
    HARDWARE: "D — Bloqueado por hardware ou coleta",
    TERCEIRO_G: "E — Bloqueado por terceiro",
}


# ══════════════════════════════════════════════════════════════════════════
#  DEFEITOS
#  Ordem: por área, e dentro da área por data. A ordem da lista é a ordem do
#  documento, então mexer aqui move o documento.
# ══════════════════════════════════════════════════════════════════════════

DEFEITOS: list[Defeito] = [

    # ─────────────────────────── SEGURANÇA ───────────────────────────────
    Defeito(
        data="2026-08-20", area=SEG, item="AUTH-03",
        defeito="A leitura de dados não exigia JWT e não aplicava RLS por dono.",
        achado_por=LEITURA,
        causa="O backend lia com privilégio de serviço; o dono da linha não "
              "entrava na consulta.",
        correcao="Leitura passa a exigir JWT e a aplicar RLS por dono.",
        commit="90e666c",
    ),
    Defeito(
        data="2026-08-25", area=SEG, item="SEC-06 / CALC-02",
        defeito="Sensor que responde ao I2C mas não mede virava movimento "
                "fabricado no banco.",
        achado_por=DADO_REAL,
        causa="Registradores zerados são leitura válida para o código: "
              "`‖a‖` calculado sobre zeros produz número, não erro.",
        correcao="Guarda de leitura zerada no sketch — a leitura ruim falha "
                 "em vez de virar dado.",
        commit="c4d1976",
        nota="Veio da sessão de 25/08: `‖a‖ = 56,5 m/s²` com a placa parada, "
             "`−11,6 °C`, ruído 30× o normal.",
    ),
    Defeito(
        data="2026-08-28", area=SEG, item="SEC-07",
        defeito="Havia um caminho de leitura de `sleep_data` que ignorava o RLS.",
        achado_por=LEITURA,
        causa="`get_latest_data` consultava com privilégio que contorna a policy.",
        correcao="O caminho foi removido, não corrigido — e a referência a ele "
                 "na documentação caiu no commit seguinte.",
        commit="b3b31c7, a0a7152",
    ),
    Defeito(
        data="2026-09-28", area=SEG, item="SEC-05",
        defeito="A suíte que afirmava isolamento entre usuários rodava contra "
                "Supabase mockado — e mock não exercita policy nenhuma.",
        achado_por=CONTROLE,
        causa="A hipótese de que mock cobriria RLS caiu de saída: não há "
              "policy a exercitar num dublê.",
        correcao="Suíte reescrita contra Postgres de verdade, e submetida a "
                 "verificação por mutação (o esquema é sabotado, uma vez por "
                 "sabotador, e exige-se que a suíte acuse cada um).",
        commit="f1ef319",
        premissa_curta='Que uma suíte contra Supabase mockado provava isolamento entre usuários.',
        premissa="O trabalho afirmava isolamento entre usuários, e a prova "
                 "disso era um mock. É o §4 das lições em sua forma mais grave: "
                 "o instrumento não tocava no mecanismo que dizia cobrir.",
        instrumento=True,
    ),
    Defeito(
        data="2026-09-28", area=SEG, item="SEC-05",
        defeito="Um teste de RLS olhava só a primeira linha do resultado e "
                "passava por acidente.",
        achado_por=CONTROLE,
        causa="A asserção sobre a primeira linha é satisfeita por um resultado "
              "que vaza nas seguintes.",
        correcao="Corrigido por causa de uma sabotagem do verificador por "
                 "mutação — não por revisão.",
        commit="f1ef319",
        nota="O defeito estava no instrumento, e o que o achou foi o "
             "instrumento que mede o instrumento.",
        instrumento=True,
    ),
    Defeito(
        data="2026-09-28", area=SEG, item="SEC-08 (primeiro)",
        defeito="A credencial do dispositivo vivia na tabela exposta ao cliente.",
        achado_por=LEITURA,
        causa="`devices` é lida pelo frontend; o segredo estava numa coluna dela.",
        correcao="Credencial movida para fora da tabela exposta (migração `007`).",
        commit="3e38c9f",
    ),
    Defeito(
        data="2026-10-17", area=SEG, item="PERFIL-01",
        defeito="A migração `008` ampliava o que o papel `dormio_ingestao` pode "
                "executar, e o `SEC-06` existe para mantê-lo mínimo.",
        achado_por=EXECUCAO,
        causa="`create function` concede `EXECUTE` a `PUBLIC` por padrão no "
              "PostgreSQL. A migração criava `tocar_updated_at()` e o papel "
              "herdava o privilégio sem que nada o concedesse.",
        correcao="`revoke` explícito na própria migração.",
        commit="778ec27",
        nota="Acusado por `test_o_papel_executa_exatamente_tres_funcoes` na "
             "primeira execução — o teste cujo docstring diz 'enumera o que "
             "ele PODE, para que ampliar apareça no diff'.",
    ),
    Defeito(
        data="2026-10-17", area=SEG, item="PERFIL-01",
        defeito="`test_ana_nao_cria_profile_para_o_bruno` barrava pela chave "
                "estrangeira, não pela policy — e passava com a policy de "
                "`insert` escancarada.",
        achado_por=CONTROLE,
        causa="O teste inseria com um uuid inventado, para não colidir com a "
              "linha que o gatilho cria. Uuid inventado não existe em "
              "`auth.users`: o comando morria em `profiles_id_fkey` e nunca "
              "chegava ao RLS.",
        correcao="Terceira usuária real, sem perfil, para que o cenário tenha "
                 "só um mecanismo capaz de recusar.",
        commit="778ec27",
        premissa_curta='Que o teste de inserção alheia era barrado pela policy — era pela chave estrangeira.',
        premissa="Medido, não suposto: com `profiles_insert_own` em "
                 "`with check (true)`, o teste continua passando — caem só os "
                 "dois testes estruturais. O cenário que o teste queria montar "
                 "era justamente o que o id falso tornava impossível.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-17", area=SEG, item="PERFIL-01",
        defeito="Dois barramentos em série escondiam um ao outro: o teste do "
                "`upsert` alheio anunciava cobrir duas policies e cobria uma.",
        achado_por=CONTROLE,
        causa="`upsert` contra vítima que já tem linha cai no ramo de `update`. "
              "Quem recusa é a policy de `update`, e a de `insert` escancarada "
              "passa despercebida.",
        correcao="Um teste por estado da linha de destino — um para a policy de "
                 "`insert`, outro para a de `update`.",
        commit="778ec27",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-17", area=SEG, item="PERFIL-01",
        defeito="Premissa de que policy de `UPDATE` sem `with check` seria mais "
                "frouxa — e não é.",
        achado_por=CONTROLE,
        causa="Sem `with check`, o PostgreSQL usa o `using` também como "
              "verificação da linha resultante. Remover a cláusula não abre a "
              "transferência de linha para outro dono.",
        correcao="A sabotagem ficou registrada com o alcance real: nenhum teste "
                 "de acesso pode cair, quem detecta é o teste estrutural.",
        commit="778ec27",
        premissa_curta='Que policy de `UPDATE` sem `with check` seria mais frouxa.',
        premissa="Era premissa de quem escreveu o sabotador, não conferida, e o "
                 "verificador por mutação a derrubou.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-19", area=SEG, item="PERFIL-01",
        defeito="A gravação do perfil apagaria o nome do titular num `PATCH` "
                "que só mandasse a idade — em silêncio, com `200`.",
        achado_por=TERCEIRO,
        causa="`upsert` do PostgREST é um `POST`, e a especificação v12.2 diz "
              "que coluna ausente do corpo é gravada como `null` salvo com "
              "`Prefer: missing=default` — header que o cliente Python só manda "
              "com `default_to_null=False`, que não é o padrão.",
        correcao="Não foi passar o header (o default de `profiles.nome` é nulo, "
                 "daria no mesmo): a gravação virou `update` e, só se ele "
                 "afetar zero linhas, `insert`. O `update` leva exatamente as "
                 "colunas do corpo — semântica de SQL, não de serviço de "
                 "terceiro.",
        commit="275665a",
        premissa_curta='Que o `upsert` não mexia nas colunas que o corpo da requisição não traz.',
        premissa="A hipótese de que o `upsert` não mexia no nome vinha da "
                 "docstring do cliente Python, que fala de `columns` e não de "
                 "`missing` — a camada errada, lida com atenção. E o ganho "
                 "maior da correção é de testabilidade: com `upsert` a "
                 "propriedade 'um PATCH de um campo não toca os outros' não "
                 "tinha onde ser testada neste repositório; com SQL, tem.",
    ),
    Defeito(
        data="2026-10-20", area=SEG, item="SEC-08",
        defeito="A tela de cadastro dizia quem tem conta: e-mail já cadastrado "
                "recebia 'Já existe uma conta com este e-mail.' — enumeração de "
                "e-mails com um formulário e nenhuma ferramenta.",
        achado_por=USO_REAL,
        causa="`traduzirErroDeAuth` decide por `codigo === c || "
              "texto.includes(t)`, e havia **dois** caminhos até a frase: por "
              "`code` (`user_already_exists`) e por `message` "
              "(`already registered`).",
        correcao="A frase saiu nos dois caminhos e virou condicional, no modelo "
                 "do `recuperarSenha`. Os dois testes que exigiam a frase foram "
                 "reescritos para afirmar o oposto, com controle positivo: "
                 "devolvida a frase ao código, os dois reprovam.",
        commit="fd89e55",
        premissa_curta='Que o cadastro não revelava quem tem conta, porque `cadastrar` não ramifica.',
        premissa="O `UI-19` havia concluído em 19/10, em negrito, que 'a "
                 "proteção existe e não há vazamento', raciocinando que "
                 "`cadastrar` não ramifica. O raciocínio está **correto sobre o "
                 "código** e **falso sobre este projeto**: a resposta idêntica "
                 "é o que o Supabase faz com a confirmação de e-mail LIGADA, e "
                 "aqui ela está DESLIGADA. A premissa não conferida não era "
                 "código — era o valor de uma chave num painel, artefato que "
                 "não está no repositório, não aparece em `grep` e não dá para "
                 "dublar.",
    ),
    Defeito(
        data="2026-10-20", area=SEG, item="SEC-08",
        defeito="A saída recomendada pelo próprio item — ligar a confirmação de "
                "e-mail — não fecha o cadastro, e abre dois canais novos.",
        achado_por=TERCEIRO,
        causa="Com a confirmação ligada, `signUp` devolve 200 com `identities` "
              "vazio para endereço existente e populado para novo: o oráculo "
              "muda de lugar (status HTTP → campo JSON), não desaparece. A doc "
              "oficial é ressalvada — 'an error message that **attempts to** "
              "hide this information' — e a qualificação foi lida como garantia.",
        correcao="A recomendação mudou para a saída (B′): confirmação desligada "
                 "até a banca, captcha no painel, sem proxy no Flask, e os "
                 "quatro canais declarados em `LIMITACOES-TCC.md` X.7 com fonte "
                 "e severidade calibrada (ASVS 5.0 § 6.3.8, Nível 3).",
        commit="4ca7fa3, 2fcb0f5",
        premissa_curta='Que ligar a confirmação de e-mail tornaria idênticas as respostas para endereço novo e existente.',
        premissa="É a ocorrência 10 do §1 das lições, e a variante mais "
                 "incômoda: o **veredito** da análise anterior vinha de medição "
                 "e estava certo; a **recomendação** vinha de uma frase de "
                 "documentação de terceiro sobre um regime que o projeto nunca "
                 "rodou, e estava errada. Mesmo parágrafo, mesmo negrito, "
                 "procedência incomparável — e a recomendação é a única metade "
                 "que alguém executa.",
    ),
    Defeito(
        data="2026-10-20", area=SEG, item="SEC-09",
        defeito="Dois comentários no código prometiam segurança inexistente.",
        achado_por=TERCEIRO,
        causa="O cabeçalho de `temSessaoImediata` afirmava que com a confirmação "
              "ligada 'os dois caminhos ficam indistinguíveis pelo cliente' "
              "(`identities` os distingue); o de `Login.tsx` afirmava que "
              "`recuperarSenha` 'responde idêntico com ou sem conta' (issue "
              "`supabase/auth` #2702 diz que não, em conteúdo, e a cheat sheet "
              "da OWASP exige uniformidade também em tempo).",
        correcao="Nenhuma linha de lógica mudou — o código já era o melhor "
                 "alcançável do lado do cliente. Mudou a **afirmação**, com a "
                 "frase da fonte citada inteira dentro do comentário.",
        commit="2fcb0f5",
        nota="Comentário que promete segurança inexistente encerra a análise de "
             "quem revisa, o que é pior que comentário nenhum.",
    ),
    Defeito(
        data="2026-10-20", area=SEG, item="SEC-10",
        defeito="A retenção de credencial em conta não confirmada estava "
                "classificada como nota de rodapé do custo de uma alternativa, "
                "e é uma classe de ataque com nome próprio.",
        achado_por=TERCEIRO,
        causa="Enumeração é divulgação de informação; isto é acesso indevido a "
              "conta, com os dados de sono do titular dentro. Enterrar a segunda "
              "num parágrafo sobre a primeira esconde a diferença de dano — e "
              "**muda o sinal da decisão**: a saída (A) deixa de ser 'ganho "
              "parcial por custo alto' e passa a ser trocar um vazamento de "
              "informação por uma via de acesso indevido.",
        correcao="Promovida a item próprio (`SEC-10`), com a pré-condição "
                 "explícita: se a saída (A) for adotada algum dia, isto se "
                 "resolve antes ou junto, nunca depois.",
        commit="2fcb0f5",
        procedencia="parcial",
        nota="Severidade declarada mais alta do projeto e evidência mais fraca: "
             "dois relatos de comunidade, um termo em doc oficial, um artigo "
             "para a classe, e **nada medido aqui**. A classificação 🟠 é da "
             "classe, não da confirmação, e está dito assim no item.",
    ),

    # ─────────────────────────── INTERFACE ───────────────────────────────
    Defeito(
        data="2026-06-03", area=UI, item="FIX-06",
        defeito="O painel prometia 'Fase do Sono' e dados de ambiente que o "
                "projeto não mede.",
        achado_por=LEITURA,
        causa="Rótulos herdados do protótipo visual, sem relação com o escopo "
              "declarado.",
        correcao="Fase do Sono → Status do Sensor; Ambiente → Do Chip; "
                 "Aceleração Total → Movimento.",
        commit="17f4515",
    ),
    Defeito(
        data="2026-08-20", area=UI, item="AUTH-02",
        defeito="A sidebar não mostrava a conta da sessão, e 'Sair' não encerrava "
                "a sessão de fato.",
        achado_por=EXECUCAO,
        causa="O estado exibido não vinha do provedor de sessão.",
        correcao="Sidebar lê a sessão, e 'Sair' encerra.",
        commit="6185c6e",
    ),
    Defeito(
        data="2026-08-21", area=UI, item="BRAND-02",
        defeito="Os contornos internos das letras viraram recortes na logo "
                "vetorial.",
        achado_por=EXECUCAO,
        causa="Regra de preenchimento do SVG tratando contorno interno como furo.",
        correcao="Caminhos refeitos.",
        commit="72c59d3",
    ),
    Defeito(
        data="2026-08-21", area=UI, item="BRAND-02",
        defeito="Um hex cru num comentário disparava a guarda de tokens de cor.",
        achado_por=EXECUCAO,
        causa="A guarda casava o padrão em qualquer posição do arquivo, "
              "inclusive em comentário.",
        correcao="O hex saiu do comentário.",
        commit="e2a8c36",
        nota="Falso positivo de uma verificação, e vale registrar como tal: a "
             "guarda estava certa no propósito e larga no alcance.",
        instrumento=True,
    ),
    Defeito(
        data="2026-08-21", area=UI, item="UI-08",
        defeito="O caminho dos estáticos servidos sob `/frontend` estava errado, "
                "e o escape do regex no `vercel.json` também.",
        achado_por=EXECUCAO,
        causa="Dois erros de roteamento no build duplo (SPA + Flask).",
        correcao="Caminho e escape corrigidos em dois commits.",
        commit="508d064, a1acd55",
    ),
    Defeito(
        data="2026-08-21", area=UI, item="UI-10 (mobile)",
        defeito="Rótulo que quebrava linha e eixo Y estreito no celular.",
        achado_por=EXECUCAO,
        causa="Largura do eixo calculada para desktop.",
        correcao="Polimento mobile.",
        commit="0d7cd32",
    ),
    Defeito(
        data="2026-08-21", area=UI, item="UI-13",
        defeito="A chamada principal da landing levava a um painel vazio.",
        achado_por=LEITURA,
        causa="O botão oferecia o painel a quem não tem dado nem conta.",
        correcao="A chamada deixou de oferecer painel vazio.",
        commit="146a2e7",
    ),
    Defeito(
        data="2026-08-22", area=UI, item="UI-16 (revelação)",
        defeito="A animação de revelação ficava presa ao recarregar a página no "
                "meio dela.",
        achado_por=EXECUCAO,
        causa="A varredura pós-restauração tinha um só gatilho, e ele não "
              "disparava quando o navegador restaurava a posição de rolagem.",
        correcao="Segundo gatilho para a varredura pós-restauração.",
        commit="ae4f8a4, 1373703",
    ),
    Defeito(
        data="2026-08-24", area=UI, item="APP-06",
        defeito="A coleta pelo celular falhava em silêncio em computador sem "
                "acelerômetro.",
        achado_por=EXECUCAO,
        causa="Ausência de sensor não produzia erro — produzia nada.",
        correcao="O caso passou a ser detectado e dito.",
        commit="efa5be0",
    ),
    Defeito(
        data="2026-08-24", area=UI, item="DASH-07",
        defeito="A média do repouso estava contaminada por épocas de movimento, "
                "e o limiar era invisível no gráfico.",
        achado_por=LEITURA,
        causa="A média era calculada sobre a série inteira, inclusive sobre o "
              "que ela deveria servir de referência para classificar.",
        correcao="Média do repouso recortada, e o limiar desenhado.",
        commit="a017551",
    ),
    Defeito(
        data="2026-08-25", area=UI, item="APP-10",
        defeito="O X vermelho de falha aparecia enquanto a época ainda estava "
                "sendo enviada.",
        achado_por=EXECUCAO,
        causa="O estado 'enviando' não existia: havia só enviado e falhou.",
        correcao="Estado de envio próprio.",
        commit="3cce0fa",
        nota="É o §6 das lições com o sinal invertido — desfecho anunciado antes "
             "de haver desfecho, só que para o lado pessimista.",
    ),
    Defeito(
        data="2026-08-25", area=UI, item="APP-12",
        defeito="A tela de coleta falava a língua do desenvolvedor.",
        achado_por=LEITURA,
        causa="Termos de implementação na interface do usuário.",
        correcao="Texto reescrito.",
        commit="826ea9f",
    ),
    Defeito(
        data="2026-08-28", area=UI, item="DASH-09",
        defeito="O painel tratava ausência de dado como dado.",
        achado_por=LEITURA,
        causa="Épocas sem medida entravam no cálculo como se tivessem medida.",
        correcao="Cobertura da medição explícita no painel.",
        commit="7407a05",
    ),
    Defeito(
        data="2026-08-28", area=UI, item="DASH-11",
        defeito="O painel misturava 'quanto foi medido' com 'o aparelho parou', "
                "e tratava movimento como instante em vez de intervalo.",
        achado_por=LEITURA,
        causa="Lacuna material e pausa por intervalo eram o mesmo estado no "
              "código.",
        correcao="Os dois separados, movimento como intervalo, recorte declarado.",
        commit="9d67bcf, 9d962f8",
    ),
    Defeito(
        data="2026-09-09", area=UI, item="APP-13",
        defeito="A mensagem de falha de rede acusava a internet do usuário.",
        achado_por=LEITURA,
        causa="Toda falha de requisição era atribuída à conexão de quem usa.",
        correcao="Mensagem que não atribui causa que não foi verificada.",
        commit="f4f77f5",
    ),
    Defeito(
        data="2026-10-17", area=UI, item="UI-10",
        defeito="A tela de exclusão de conta estava inalcançável: "
                "`ExcluirConta.tsx` estava commitado com 23 testes passando e "
                "**nenhum arquivo versionado o importava**.",
        achado_por=INVENTARIO,
        causa="As três linhas que o montam em `Settings.tsx` estavam presas numa "
              "árvore de trabalho não commitada desde 29/09, porque os *hunks* "
              "não se separavam do `DASH-13`.",
        correcao="Montado. E a correção de fundo é `frontend/src/alcance.test.ts`: "
                 "percorre os `import` a partir de `main.tsx` e reprova quando "
                 "um módulo de `src/` fica fora do grafo.",
        commit="22a9268",
        premissa_curta='Que componente commitado e testado estava ao alcance do usuário.',
        premissa="Por dezoito dias o backlog dizia `UI-10 ✅`, o "
                 "`LGPD-ELIMINACAO.md` dizia 'a interface existe desde 29/09' e "
                 "a **política de privacidade dizia ao titular onde clicar** "
                 "para exercer o art. 18, VI. Nada no repositório podia pegar: "
                 "`tsc` não reclama de módulo não importado, o `vite build` poda "
                 "o que não entra no grafo e segue verde, e os 23 testes são de "
                 "`lib/`, então passavam com o componente desmontado.",
    ),
    Defeito(
        data="2026-10-17", area=UI, item="DASH-12 / DASH-13",
        defeito="O painel versionado pedia 20 linhas ao backend e usava a hora de "
                "**chegada** como base de tempo — dez minutos de celular "
                "descritos como a noite.",
        achado_por=INVENTARIO,
        causa="Os dois itens estavam feitos só do lado do servidor. O backend "
              "está commitado e testado desde 10/09; o cliente ficou na árvore "
              "de trabalho.",
        correcao="Cliente commitado: `captured_at` em `LeituraSono`, "
                 "`instanteDaLeitura`, e `limite` enviado pelo painel e pela "
                 "exportação.",
        commit="a586b0b",
        premissa_curta='Que os dois itens estavam feitos, como dizia o `ROADMAP.md` — estavam só do lado do servidor.',
        premissa="O `ROADMAP.md` declarava os dois '✅ corrigido em 2026-09-10', "
                 "com descrição detalhada do que mudou. E o `ROADMAP.md` não é "
                 "versionado — é por não ser versionado que ele pôde carregar um "
                 "`✅` errado por seis semanas sem que nenhuma verificação o "
                 "alcançasse (`GIT-05`).",
    ),
    Defeito(
        data="2026-10-17", area=UI, item="DASH-08",
        defeito="O painel não dizia de que instrumento veio a série, e havia "
                "trabalho pronto para isso que ninguém mencionava.",
        achado_por=INVENTARIO,
        causa="`descreverDispositivo`, `descreverRecorte`, `tiposPresentes` e "
              "`serieMisturaTipos` estavam escritos e não commitados. A última "
              "era decisão documentada, com três testes, **ligada em lugar "
              "nenhum**.",
        correcao="Commitado. `serieMisturaTipos` foi ligada, mas não como porta "
                 "de entrada do aviso: quem decide se ele *aparece* continua "
                 "sendo `serieMisturaInstrumentos`; quem decide se ele *nomeia "
                 "as classes* passou a ser `serieMisturaTipos`.",
        commit="fea1c48",
        nota="Apareceu na leitura uma assimetria registrada de passagem: a "
             "justificativa escrita de `serieMisturaInstrumentos` fala de 'um "
             "travesseiro e um celular', e a implementação é só "
             "`dispositivos.length > 1` — o alcance do código é mais largo que o "
             "do comentário.",
    ),
    Defeito(
        data="2026-10-17", area=UI, item="UI-11",
        defeito="A especificação do item estava errada: ela mandava gravar o "
                "perfil numa tabela que nada lê.",
        achado_por=INVENTARIO,
        causa="A especificação dizia 'a policy de `update` em `profiles` já "
              "existe; falta a interface'. Um `grep` por `profiles` em código de "
              "produção devolveu **nada** — as únicas referências do repositório "
              "estavam em `web-app/tests/rls/`. O nome exibido vinha de "
              "`auth.users.raw_user_meta_data`.",
        correcao="Implementado pelo Supabase Auth, não pela tabela. A "
                 "sincronização de `profiles` foi recusada de propósito e virou "
                 "item próprio (`PERFIL-01`).",
        commit="2316b06",
        premissa_curta='Que bastava a interface sobre a policy de `update` em `profiles` — e nada lê `profiles`.',
        premissa="Implementado conforme especificado, o item teria entregado uma "
                 "tela em que a pessoa clica 'salvar', recebe 'dados "
                 "atualizados', e o nome continua o mesmo — confirmação falsa "
                 "(§6) produzida por premissa não conferida (§5), os dois "
                 "padrões em série, cada um invisível a partir do outro. A "
                 "conclusão prática do item ('é barato') estava certa **por "
                 "acidente e pelo motivo errado**.",
    ),
    Defeito(
        data="2026-10-19", area=UI, item="UI-17",
        defeito="A catraca de alcance provava `import` e o nome dela dizia "
                "'alcance': passava com o provedor fora do JSX, com o componente "
                "fora da tela e com a rota ausente.",
        achado_por=CONTROLE,
        causa="`alcance.test.ts` percorre o grafo de `import` e para aí. "
              "Componente importado e nunca usado no JSX passa.",
        correcao="`frontend/src/montagem.test.ts`, 16 testes, que monta pelo "
                 "`await import('./main.tsx')` — o ponto de entrada de produção. "
                 "A alternativa idiomática "
                 "(`render(<AuthProvider><PerfilProvider><App/></…>)`) "
                 "reproduziria o defeito que existe para pegar, porque "
                 "verificaria a composição escrita no teste.",
        commit="377482b",
        premissa_curta='Que provar o caminho de `import` provava que a tela é alcançável.',
        premissa="Medido por 11 sabotagens, 11 detectadas — e a coluna que "
                 "importa: **em 5 das 5 sabotagens em que foi medido, o "
                 "`alcance.test.ts` continuou verde**, inclusive com o "
                 "`<PerfilProvider>` fora do `main.tsx` e o `<ExcluirConta />` "
                 "fora do `Settings.tsx`, que é o defeito do `UI-10` refeito um "
                 "nível acima. A catraca não estava errada: afirmava exatamente "
                 "o que dizia afirmar, e o que dizia era menos do que se "
                 "precisava.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-19", area=UI, item="UI-17",
        defeito="Com o prazo padrão de 5 s, o primeiro teste de montagem "
                "estourava e o `createRoot` da montagem abandonada caía no "
                "`#root` do teste seguinte.",
        achado_por=EXECUCAO,
        causa="A primeira montagem paga a transformação de todo o grafo de "
              "`src/` pelo Vite (~13 s); o `import` em curso resolvia depois do "
              "`afterEach`.",
        correcao="Prazo de 60 s, com o motivo escrito ao lado da constante.",
        commit="377482b",
        nota="O sintoma foram oito falhas de 'useAuth precisa estar dentro de "
             "<AuthProvider>' **numa árvore em que o provedor estava lá** — um "
             "erro que manda procurar o defeito no lugar errado.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-19", area=UI, item="UI-16",
        defeito="A varredura de exports mortos sub-relatava código morto: "
                "acusou `nomeDoDispositivo` como vivo.",
        achado_por=CONTROLE,
        causa="A varredura contava **frequência de identificador** e colidiu com "
              "uma `useState` local de mesmo nome em `pages/Coletar.tsx`, que "
              "não importa a função.",
        correcao="Refeita por **nome importado**. A premissa do `UI-16` está "
                 "correta — e por pouco não ganhou uma 'correção' falsa.",
        commit="377482b, 9a40446",
        premissa_curta='Que a varredura de exports mortos não deixava escapar código morto.',
        premissa="O instrumento estava errado na direção perigosa: um falso "
                 "'está vivo' encerra a investigação, e aqui ele contradizia a "
                 "premissa de um item aberto.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-20", area=UI, item="UI-16",
        defeito="`nomeDoDispositivo` era export morto com três testes próprios.",
        achado_por=INVENTARIO,
        causa="O cabeçalho do painel passou a usar `descreverRecorte` "
              "(`DASH-08`), e a função antiga sobrou com uso só nos próprios "
              "testes.",
        correcao="Função e testes apagados — e não mantidos como 'a forma só o "
                 "nome', porque dois caminhos para o mesmo rótulo convidam as "
                 "duas redações a divergirem. O comentário que justificava "
                 "'Dispositivo desconhecido' migrou para o teste de "
                 "`descreverRecorte`, onde o rótulo sobreviveu.",
        commit="9a40446",
    ),

    # ─────────────────────────── FIRMWARE ────────────────────────────────
    Defeito(
        data="2026-08-20", area=FW, item="DATA-02",
        defeito="O critério de movimento era assimétrico: 52% menos sensível "
                "para baixo do que para cima.",
        achado_por=CALCULO,
        causa="`total > 11.0 || total < 8.0` sobre a magnitude bruta. Contra "
              "`g = 9,81`, o limite superior dispara a 1,19 m/s² de desvio e o "
              "inferior só a 1,81 m/s². Nada no código dizia que era "
              "intencional, porque não era.",
        correcao="Critério simétrico, `|‖a‖ − 9,81| > 1,2 m/s²`, preservando a "
                 "sensibilidade do lado que já era o mais sensível. Declarado "
                 "**provisório** no contrato de dados.",
        commit="9333359, c715f68",
        premissa_curta='Que os dois limites do critério de movimento representavam a mesma sensibilidade.',
        premissa="O enunciado de partida era 'ajustar os dois limites', sob a "
                 "premissa de que representavam a mesma sensibilidade. Uma "
                 "subtração a derrubou. E a correção plantou o problema "
                 "seguinte: o 1,2 herdou a autoridade de estar escrito num "
                 "contrato, e a nota de 'provisório' foi lida cada vez menos "
                 "— ver `CALC-03`.",
    ),
    Defeito(
        data="2026-08-25", area=FW, item="FW-08 (secrets)",
        defeito="O `secrets.h` estava dessincronizado entre as pastas dos "
                "sketches.",
        achado_por=LEITURA,
        causa="Cada sketch tinha a própria cópia.",
        correcao="Script de sincronização.",
        commit="68608da",
    ),
    Defeito(
        data="2026-09-10", area=FW, item="FW-06",
        defeito="O filtro passa-baixa do MPU6050 estava na banda padrão de "
                "260 Hz, e isso mudou o ruído de base.",
        achado_por=CALCULO,
        causa="O ruído cresce com `√B`: passar de 21 Hz para 260 Hz multiplica σ "
              "por 3,52, e o piso do ENMO médio é proporcional a σ.",
        correcao="Filtro para 21 Hz (`σ = 1,833 mg`).",
        commit="f58f52c (cabeçalho), docs/CALCULOS-TCC.md Z.1 e Z.2.2",
        procedencia="parcial",
        premissa_curta='Que mudar a banda do filtro não mexia no limiar de movimento.',
        premissa="A consequência não estava prevista: **o limiar de movimento é "
                 "definido sobre o ruído de base, e o ruído de base mudou** — o "
                 "que invalidou a caracterização de 25/08 pela segunda vez "
                 "(contato ruim *e* banda diferente) e virou o item `CAL-02`. E "
                 "21 Hz implica amostragem ≥ 42 Hz por Nyquist, que atravessa os "
                 "40 Hz do modo de baixo consumo: a desigualdade é estrita, e "
                 "custa 4,5× na corrente do transdutor. Foi daí que saiu, cinco "
                 "semanas depois, o `ARQ-01`.",
    ),
    Defeito(
        data="2026-09-22", area=FW, item="HW-05",
        defeito="A medição esperava pela rede, e a série continuava saindo com "
                "aparência normal e base de tempo derivada.",
        achado_por=LEITURA,
        causa="`conectarWiFi()` era chamada **dentro** do laço de amostragem e "
              "gastava até 20 s em `delay(500)`. Com intervalo de 10 s, uma "
              "queda de rede fazia cada ciclo levar 20–30 s.",
        correcao="Quatro regras, e a arquitetura saiu delas: nada na medição "
                 "espera por conectividade; perda de cadência vira campo no dado "
                 "(`EPOCA_INCOMPLETA`, `EPOCA_VAZIA`, e a época vazia ocupa "
                 "lugar no buffer); o buffer é de épocas, não de amostras, o que "
                 "permite degradar resolução em vez de descartar; e a grade é "
                 "absoluta (`t0 + k·período`, nunca `última + período`).",
        commit="846986a, c0725ca, 54504f6",
        premissa_curta='Que o prejuízo de uma queda de rede é a lacuna na série.',
        premissa="O enunciado de partida era 'acrescentar buffer', sob a "
                 "premissa de que o prejuízo de uma queda de rede é a lacuna na "
                 "série. Para actigrafia, cuja unidade *é* a época fixa de 30 s, "
                 "a deriva é pior que a lacuna: **a lacuna a análise vê; a "
                 "deriva, não.** A perda de dado era o problema menor.",
    ),
    Defeito(
        data="2026-09-22", area=FW, item="HW-05",
        defeito="Uma amostra em cada três desaparecia, e **toda época saía "
                "marcada `INCOMPLETA` com a medição perfeita**.",
        achado_por=EXECUCAO,
        causa="O fechamento de época era preguiçoso, e `amostrar` recusava "
              "amostra de um slot futuro por não ter como fechar o anterior — as "
              "dos instantes 30 000, 60 000, 90 000 ms.",
        correcao="Fechamento no lugar certo.",
        commit="846986a",
        nota="Na placa isso apareceria depois de uma noite de coleta; na suíte "
             "do host apareceu em 3 ms. A suíte pegou quatro defeitos nesse "
             "dia — este, o `fundir`, e duas expectativas de teste que estavam "
             "erradas, não o código.",
    ),
    Defeito(
        data="2026-09-22", area=FW, item="HW-05",
        defeito="`fundir` consultava `a->vazia()` **depois** de mesclar as "
                "flags: época com dado fundida com lacuna saía marcada como "
                "lacuna.",
        achado_por=EXECUCAO,
        causa="Ordem entre a consulta e a mesclagem.",
        correcao="Consulta antes da mesclagem.",
        commit="846986a",
    ),
    Defeito(
        data="2026-09-22", area=FW, item="HW-05",
        defeito="Duas expectativas da própria suíte estavam erradas — não o "
                "código.",
        achado_por=EXECUCAO,
        causa="Asserções escritas a partir do comportamento esperado por "
              "leitura, não do especificado.",
        correcao="Expectativas corrigidas.",
        commit="846986a",
        nota="Registrado porque é o modo de falha que faz mexer no código certo: "
             "um valor de referência errado reprova implementação correta.",
        instrumento=True,
    ),
    Defeito(
        data="2026-09-22", area=FW, item="(sem item)",
        defeito="O `envio-continuo.ino` tinha duas strings com quebra de linha "
                "literal no meio. **Não compilava em máquina nenhuma** — e era "
                "tratado como código em funcionamento, com o backlog discutindo "
                "melhorias nele.",
        achado_por=EXECUCAO,
        causa="Nada no repositório tentava compilar firmware: o CI olhava Python "
              "e frontend, e o sketch só era exercitado manualmente no Wokwi, "
              "onde o arquivo aberto era o da máquina de quem editava, não o "
              "versionado.",
        correcao="Alvo `make sintaxe` (`g++ -fsyntax-only` com stubs mínimos do "
                 "Arduino), que gera um `secrets.h` falso em `bin/` e o põe por "
                 "último no caminho de include — roda em qualquer clone sem "
                 "exigir credencial.",
        commit="846986a, c0725ca",
        premissa_curta='Que código versionado num repositório com CI ao menos compila.',
        premissa="A premissa era 'código versionado num repositório com CI é "
                 "código que ao menos compila'. E uma causa mais funda ficou "
                 "registrada na mesma revisão: `sketch.ino` e "
                 "`envio-continuo.ino` tinham chegado a **critérios de movimento "
                 "diferentes** antes do `FW-06`, porque o núcleo era duplicado "
                 "em cada sketch e as cópias divergiram na primeira correção. "
                 "Daí a unidade de tradução única.",
    ),
    Defeito(
        data="2026-09-22", area=FW, item="FW-07",
        defeito="O sketch de produto tira **uma amostra por boot** e dorme: não "
                "registraria uma noite nem com rede perfeita.",
        achado_por=LEITURA,
        causa="Não tem amostragem periódica nenhuma. O problema não era "
              "robustez, era ausência de estrutura.",
        correcao="Em 22/09 recebeu **só** a correção dos travamentos; o conserto "
                 "de verdade foi separado como `FW-07` e continua aberto.",
        commit="54504f6",
        premissa_curta='Que, tirados os travamentos, o sketch de produto serviria para captação noturna.',
        premissa="O enunciado do `HW-05` para ele era 'correção defensiva nos "
                 "travamentos', sob a premissa de que, tirados os travamentos, o "
                 "sketch serviria para captação noturna. Enquanto o `FW-07` "
                 "estiver aberto, o 'firmware de produto' do trabalho é o "
                 "`envio-continuo.ino`, que não dorme.",
    ),
    Defeito(
        data="2026-10-16", area=FW, item="CI-03",
        defeito="O `make sintaxe` tinha **dois dos quatro** sketches "
                "versionados, e na primeira vez que os outros dois foram "
                "compilados os **dois** tinham string com quebra de linha "
                "literal — o defeito exato que o alvo nasceu para pegar.",
        achado_por=EXECUCAO,
        causa="A lista `SKETCHES` era escrita à mão.",
        correcao="A lista deixou de ser escrita à mão: sai de `$(wildcard)`, com "
                 "guarda para o caso de não casar nada. Validado por controle "
                 "positivo nas duas direções — string quebrada devolvida "
                 "reprova; sketch novo com função inexistente reprova, provando "
                 "que o wildcard o pega.",
        commit="7feeef9",
        premissa_curta='Que a lista de sketches escrita à mão cobria os sketches versionados.',
        premissa="É a ocorrência 4 do §1 das lições: *alcance de verificação "
                 "escrito à mão silenciosamente para de acompanhar a pasta.* Os "
                 "dois sketches passaram de 22/09 a 16/10 sem compilar em "
                 "máquina nenhuma.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-16", area=FW, item="CI-03",
        defeito="`diagnostico-i2c.ino` tinha uma chave sobrando, fechando "
                "`setup()` no meio.",
        achado_por=EXECUCAO,
        causa="Nunca havia sido compilado.",
        correcao="Chave removida.",
        commit="7feeef9",
    ),
    Defeito(
        data="2026-10-16", area=FW, item="CI-03",
        defeito="`%lu` para um `uint32_t` — no ESP32 um `unsigned int`: o "
                "`printf` lia 8 bytes de um argumento de 4 e imprimia lixo em "
                "silêncio.",
        achado_por=EXECUCAO,
        causa="Especificador de formato incompatível com o tipo na plataforma de "
              "destino.",
        correcao="Especificador corrigido.",
        commit="7feeef9",
        nota="Achado **só** porque o stub do `Serial` tem "
             "`__attribute__((format))` — é o instrumento, e não o compilador "
             "da IDE, que pegou.",
    ),
    Defeito(
        data="2026-10-17", area=FW, item="DATA-07b",
        defeito="`features.h` sequestrou o `<features.h>` da glibc, e nada "
                "compilava.",
        achado_por=EXECUCAO,
        causa="Com o `-I.` do Makefile, todo cabeçalho de sistema que faz "
              "`#include <features.h>` passou a incluir o do projeto. O erro era "
              "`missing binary operator before token \"(\"` **dentro de "
              "`/usr/include/`**, apontando para a biblioteca padrão, sem "
              "mencionar o arquivo culpado — e atingia até `filtro.cpp`, que não "
              "o inclui.",
        correcao="Renomeado para `caracteristicas.h`, que além de não colidir "
                 "segue o padrão de nomes da casa (`epoca`, `cadencia`, "
                 "`relogio`, `payload`).",
        commit="6d328bb",
        nota="Seguir o padrão de nomes teria evitado o problema de graça.",
    ),
    Defeito(
        data="2026-10-17", area=FW, item="DATA-07b",
        defeito="Os coeficientes do filtro em `float32` enviesavam o estimador: "
                "o ganho em corrente contínua saiu 1,0000120 onde tem de ser "
                "exatamente 1.",
        achado_por=EXECUCAO,
        causa="Cancelamento catastrófico na própria expressão: "
              "`1 + a1 + a2 = 0,0023283`, uma soma que perde quase três ordens "
              "de grandeza, então 1e−7 de erro por coeficiente vira 4,3e−5 no "
              "ganho. Em termos físicos, injeta 1,2e−5 g em `‖a − ĝ‖` de forma "
              "**sistemática** — viés de estimador, não ruído, e portanto não se "
              "cancela no somatório.",
        correcao="Coeficientes em `double`, a custo **zero** — o laço interno já "
                 "acumulava em `double`, então eles eram `float` truncado "
                 "promovido a `double` em toda multiplicação, o pior dos dois "
                 "mundos. O ganho DC passou a fechar em 1e−16.",
        commit="6d328bb",
        premissa_curta='Que coeficientes do filtro em `float32` bastavam.',
        premissa="A tentação era afrouxar a tolerância de 1e−5. O teste estava "
                 "certo e o estimador estava errado — e nenhuma tolerância deste "
                 "item foi afrouxada: as duas que se mexeram foram apertadas ou "
                 "alinhadas com a régua já existente do outro lado.",
    ),
    Defeito(
        data="2026-10-17", area=FW, item="DATA-07b",
        defeito="Os coeficientes de referência escritos no teste estavam "
                "errados — escritos de memória.",
        achado_por=TERCEIRO,
        causa="`b0 ≈ 5,37e−4` e `a1 ≈ −1,93338` de memória, contra "
              "`b0 = 5,8207613e−4` e `a1 = −1,9306064` reais.",
        correcao="Conferido contra `scipy.signal.butter` de verdade: a forma "
                 "fechada do módulo e o scipy concordam em 2,2e−19 nos cinco "
                 "coeficientes.",
        commit="7cddf66",
        nota="Registrado porque é o modo de falha mais fácil de não notar: um "
             "valor de referência inventado faz o teste reprovar código correto, "
             "e a reação natural é mexer no código.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-17", area=FW, item="DATA-07b",
        defeito="A asserção `inclinacao_rel == 0` reprovou, e estava mais fina "
                "que a física.",
        achado_por=EXECUCAO,
        causa="Piso de condicionamento do `arccos`: com uma época só, `ĝ_ref` é "
              "o próprio `ĝ`, o produto interno é 1, e ali `dθ/dc = −1/√(1−c²)` "
              "explode, transformando 1 ulp em ~6e−7 grau.",
        correcao="Régua de 1e−5 grau — a **mesma** que "
                 "`test_angulo_entre_vetores_paralelos_nao_e_nan` usa do outro "
                 "lado.",
        commit="7cddf66",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-17", area=FW, item="DATA-07b",
        defeito="O harness de mutação do lado C++ tinha contaminação entre "
                "rodadas: uma sabotagem apareceu como **detectada**, e a detecção "
                "era resíduo da sabotagem anterior.",
        achado_por=CONTROLE,
        causa="A primeira versão restaurava só `caracteristicas.cpp` entre "
              "sabotagens, deixando `filtro.cpp` sabotado da rodada anterior.",
        correcao="Árvore nova (`mktemp -d`) por sabotagem, e exigência de que "
                 "cada trecho case **exatamente uma vez**, com erro alto quando "
                 "não casa — *um sabotador morto se lê como ponto cego.*",
        commit="7cddf66",
        premissa_curta='Que cada rodada do harness de mutação partia de uma árvore limpa.',
        premissa="É o **mesmo defeito** que o `DATA-07c` achou no instrumento do "
                 "Python, com outra roupa, e na mesma data pela manhã. A "
                 "reincidência é o argumento mais forte de o "
                 "`LICOES-APRENDIDAS.md` existir.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-17", area=FW, item="FW-06",
        defeito="O cabeçalho do `caracterizacao.ino` afirmava o contrário do "
                "código.",
        achado_por=INVENTARIO,
        causa="Edição de cabeçalho pendente de outra sessão, nunca commitada.",
        correcao="Cabeçalho alinhado ao código.",
        commit="f58f52c",
    ),

    # ─────────────────────────── DADOS E ML ──────────────────────────────
    Defeito(
        data="2026-09-14", area=ML, item="ML-01",
        defeito="As features herdadas da actigrafia clássica (`angulo_z` e a "
                "*signal magnitude area*) não eram invariantes a rotação.",
        achado_por=EXECUCAO,
        causa="Num travesseiro a orientação é arbitrária **e muda durante a "
              "noite**. `angulo_z` depende de qual eixo é 'z'; a norma L1 sobre "
              "gravidade bruta varia até **73% só por causa da montagem**, e "
              "mesmo restrita à componente dinâmica variou ~6%.",
        correcao="`angulo_z` saiu; entraram `inclinacao_rel` e `d_angulo`, "
                 "invariantes por construção (`(Rĝ_a)·(Rĝ_b) = ĝ_a·ĝ_b`). A SMA "
                 "L1 saiu; entrou `mag_din_media` (norma L2).",
        commit="38ae2a5",
        premissa_curta='Que features clássicas de punho servem para o travesseiro, mudando só a escala.',
        premissa="A premissa era que features clássicas de punho servem para o "
                 "travesseiro, e que o que muda é a escala, não a definição. "
                 "Risco que ficou: `mag_din_media` **não pode ser citada como "
                 "*signal magnitude area* no TCC** — é outra norma, e usar o nome "
                 "clássico atribuiria ao trabalho uma comparação com a "
                 "literatura que ele não faz.",
    ),
    Defeito(
        data="2026-09-14", area=ML, item="ML-01",
        defeito="`direcao_referencia` também não era invariante a rotação, na "
                "primeira escrita.",
        achado_por=EXECUCAO,
        causa="Defeito residual da mesma classe, no mesmo dia.",
        correcao="Corrigida, com teste de invariância próprio.",
        commit="11eb4b7",
    ),
    Defeito(
        data="2026-09-14", area=ML, item="DADOS-02",
        defeito="Dez divergências entre o que a documentação dos datasets "
                "declara e o que os arquivos têm. A pior: o Empatica em `g/64` "
                "onde a v1.0 declara `g/16` — **fator 4 de erro, silencioso**, "
                "no braço 'treina' do `ML-03`.",
        achado_por=DADO_REAL,
        causa="A premissa era que a documentação do dataset descreve o dataset. "
              "Outras do mesmo lote: `PSG_Manual_scor1` no `.tsv` contra "
              "`PSG_Manual_Scor1` no EDF (casamento sensível a maiúscula acha o "
              "acelerômetro e **perde o rótulo** — o sintoma não é exceção, é "
              "zero época); `scor2` declarado para 100 sujeitos e presente em "
              "**96**; nº de canais variando de **38 a 61** por sujeito.",
        correcao="Todo acesso passou a ser por nome, nunca por posição. O "
                 "carregador **aborta** se encontrar a declaração `g/16`, em vez "
                 "de converter pelo fator que achar. Um teste por armadilha em "
                 "`ml/testes/test_wearanize.py`.",
        commit="5c2720c",
        premissa_curta='Que a documentação do dataset descreve o dataset.',
        premissa="É o de maior potencial de dano do projeto: o fator 4 teria "
                 "contaminado em silêncio o braço 'treina' da matriz de "
                 "transferência, que é **o resultado original do trabalho**. Foi "
                 "pego por auditoria dos arquivos reais, não por leitura da "
                 "documentação — e a regra de método ficou escrita para o "
                 "próximo carregador (`ML-06b`): *escreva contra a documentação, "
                 "mas não confie até rodar.*",
        familia=10,
    ),
    Defeito(
        data="2026-09-14", area=ML, item="ML-02",
        defeito="O alinhamento PSG/acelerômetro no Newcastle estava errado, e o "
                "carregador não lia a estrutura real do zip nem aplicava a "
                "calibração.",
        achado_por=DADO_REAL,
        causa="Escrito contra a documentação, antes da primeira medição real.",
        correcao="Alinhamento e carregador corrigidos em dois commits.",
        commit="602bc44, 8006642",
    ),
    Defeito(
        data="2026-09-14", area=ML, item="ML-02",
        defeito="A acurácia não serve como métrica de decisão neste domínio: o "
                "classificador trivial 'sempre dormindo' é **competitivo em "
                "acurácia** e tem **κ exatamente 0**.",
        achado_por=EXECUCAO,
        causa="A prevalência de sono numa noite de PSG é alta. Aplicada a dois "
              "trabalhos da literatura que publicam sensibilidade, "
              "especificidade e acurácia, a identidade "
              "`acurácia = p·sens + (1−p)·espec` recupera a acurácia que o "
              "trivial teria alcançado *naquele mesmo estudo*, e a diferença "
              "contra a publicada é pequena.",
        correcao="κ de Cohen passou a ser a métrica primária em todo o trabalho, "
                 "e toda comparação é contra o trivial **medido na própria "
                 "coorte**, porque κ depende da prevalência e valores de coortes "
                 "diferentes não são comparáveis entre si.",
        commit="38ae2a5",
        premissa_curta='Que acurácia serviria como métrica de leitura.',
        premissa="A premissa era que acurácia serviria como métrica de leitura. "
                 "É o §8 das lições: a média esconde o caso que importa.",
    ),
    Defeito(
        data="2026-09-14", area=ML, item="ML-02",
        defeito="Cole-Kripke e Sadeh não podiam ser usados como publicados.",
        achado_por=TERCEIRO,
        causa="Exigem *activity counts* de Actiwatch, e não há função pública "
              "que converta aceleração em counts.",
        correcao="Substituto documentado (passa-banda 0,25–3 Hz, retificado, "
                 "integrado), com a obrigação de aparecer no texto como "
                 "'Cole-Kripke aplicado a um substituto de contagem' e com a "
                 "segunda diferença declarada (épocas de 30 s, não os 60 s "
                 "originais).",
        commit="38ae2a5",
        nota="É o tipo de atalho de redação que uma banca cobra, e está "
             "registrado como advertência, não como detalhe.",
    ),
    Defeito(
        data="2026-09-14", area=ML, item="ML-03",
        defeito="`ml03_transferencia.py` não calculava trivial/Sadeh por braço.",
        achado_por=EXECUCAO,
        causa="Baseline agregado onde a comparação exige um por posição.",
        correcao="Calculado por braço.",
        commit="fd215ff",
    ),
    Defeito(
        data="2026-09-15", area=ML, item="ML-03",
        defeito="A hipótese de que a transferência entre posições de sensor "
                "seria **simétrica** caiu.",
        achado_por=EXECUCAO,
        causa="Matriz 3×3 com o mesmo N nas nove células (N = 92, LOSO): pulso → "
              "qualquer posição dá κ ≈ 0,38; cabeça → cabeça fica em "
              "0,398–0,401; **cabeça → pulso cai a 0,046** e cabeça → cabeça "
              "degradada a **0,067** — quedas de 85% e 88% da diagonal de origem.",
        correcao="A hipótese foi abandonada e o achado virou o resultado original "
                 "do trabalho. A pergunta seguinte deixou de ser 'quanto se "
                 "perde' e passou a ser 'o que exatamente é perdido' (`ML-03b`).",
        commit="896abba",
        premissa_curta='Que a transferência entre posições de sensor seria simétrica.',
        premissa="A direção que interessa ao produto — treinar com dado de "
                 "cabeça — é justamente a que colapsa.",
    ),
    Defeito(
        data="2026-09-15", area=ML, item="ML-03b",
        defeito="A leitura fácil do resultado — 'a normalização recupera 70% a "
                "80%' — estava errada.",
        achado_por=EXECUCAO,
        causa="Os 71,0% e os 77,6% são **ambos de `cabeça → pulso`**. Em "
              "`cabeça → cabeça-E4` a recuperação é **metade**: 34,5% e 41,5%. A "
              "faixa é de **um par de posições, não da matriz**.",
        correcao="O texto de resultados teve de dizer isso com essas palavras "
                 "('cerca de três quartos […] e cerca de dois quintos'). Sem a "
                 "frase, o número parece valer para a matriz inteira e não vale.",
        commit="44de161",
        premissa_curta="Que 'a normalização recupera 70% a 80%' valia para a matriz inteira.",
        premissa="Autocorreção antes de o número sair do repositório, e as duas "
                 "ressalvas que ficaram declaradas: as frações são medidas contra "
                 "a diagonal de **origem** (contra a de **destino** sairia 83,3% "
                 "em vez de 77,6% — a adotada é a conservadora, e a escolha tem "
                 "de ser declarada); e a floresta aleatória **não é 'o modelo sem "
                 "normalizador'**, porque é insensível a deslocamento monotônico "
                 "de escala por construção.",
    ),
    Defeito(
        data="2026-09-18", area=ML, item="ML-04",
        defeito="A hipótese de que a degradação entre coortes seria **uniforme** "
                "caiu — e a validação interna, sozinha, teria escolhido a "
                "modificação errada.",
        achado_por=EXECUCAO,
        causa="Modelo ajustado nos 92 de desenvolvimento e aplicado a 27 de "
              "coorte independente, **sem reajuste de nada**. O ganho do HMM "
              "praticamente desapareceu (Δκ +0,123 → +0,036) **e** veio com "
              "perda de especificidade estatisticamente distinguível (−0,037); o "
              "da janela de contexto preservou magnitude e direção (+0,075 → "
              "+0,069).",
        correcao="A explicação é o que cada modificação aprende: a matriz de "
                 "transição do HMM é estimada sobre a **prevalência** da coorte "
                 "de treino; a janela de contexto não codifica prevalência "
                 "alguma — só muda a escala temporal, que é propriedade do "
                 "fenômeno, não da coorte.",
        commit="83382b2",
        premissa_curta='Que a degradação entre coortes seria uniforme entre as modificações.',
        premissa="Daí a limitação metodológica que o trabalho declara, e é o "
                 "achado mais forte dele: **seleção de modelo apoiada só em "
                 "validação cruzada interna é insuficiente neste domínio.** "
                 "Risco declarado: **uma única** coorte externa, então a "
                 "degradação relatada é estimativa pontual, não medida de "
                 "variabilidade.",
    ),
    Defeito(
        data="2026-09-18", area=ML, item="ML-03b item 8",
        defeito="A mediana móvel não sai do ruído.",
        achado_por=EXECUCAO,
        causa="Bootstrap pareado da diferença sobre os mesmos sujeitos.",
        correcao="Descartada. O HMM de 2 estados ficou como candidato — e "
                 "teria sido escolhido se a decisão parasse ali.",
        commit="2db4c08",
    ),
    Defeito(
        data="2026-09-21", area=ML, item="ML-04b", conta=False,
        defeito="Nenhum — a hipótese se confirmou, e o defeito estaria em "
                "declarar mais do que ela permite.",
        achado_por=EXECUCAO,
        causa="Comparação intraparticipante nos 26 com registro bilateral: "
              "Δκ = +0,009 (IC 95%: −0,014 a +0,031), e **todos os 24 IC 95% "
              "contêm zero**.",
        correcao="A ressalva é o valor da entrada: **com 26 participantes, "
                 "efeito menor que ~0,03 em κ não seria distinguível do ruído.** "
                 "O texto não pode dizer 'o lado não importa' sem o poder do "
                 "teste ao lado.",
        commit="d51fa66",
        nota="É o caso raro deste registro em que o resultado confirmou a "
             "hipótese. Entra porque o que se corrigiu foi a **afirmação** que "
             "se podia extrair dele.",
    ),
    Defeito(
        data="2026-09-28", area=ML, item="ML-05",
        defeito="A faixa de leitura dos Δκ do trabalho é [0; 0,61], não [0; 1].",
        achado_por=EXECUCAO,
        causa="As duas pontuações manuais do Wearanize+, comparadas entre si na "
              "mesma redução binária do pipeline, dão κ = 0,607 nos 96 sujeitos "
              "com as duas, e **0,612 nos 90** que também estão nos 92 da base — "
              "este é o divisor certo.",
        correcao="O capítulo de resultados foi reescrito contra esse teto.",
        commit="ab3d542",
        premissa_curta='Que a concordância entre dois humanos daria um teto próximo de 1.',
        premissa="A premissa era que a concordância entre dois humanos daria um "
                 "teto próximo de 1. Contra 1,0 um κ de 0,41 parece ruim; contra "
                 "0,61 é outra leitura. E o achado de brinde é desconfortável: o "
                 "pontuador 2 marca **7,8 pontos percentuais** mais de vigília "
                 "que o pontuador 1, e **a especificidade humana vale 0,958 ou "
                 "0,520 conforme qual dos dois se toma como referência** — o que "
                 "tira a especificidade externa do modelo (0,507) de parecer um "
                 "número isolado. Risco: **não há teto para o Newcastle**, e é "
                 "justamente o número que o trabalho declara como honesto.",
    ),
    Defeito(
        data="2026-09-29", area=ML, item="CALC-03",
        defeito="O limiar de 1,2 m/s² em uso **não foi derivado do ruído**, e a "
                "derivação clássica `g ± k·σ` não o gera nem o explica.",
        achado_por=CALCULO,
        causa="Uma divisão. Com `σ = 1,833 mg = 0,0180 m/s²` na banda de 21 Hz, "
              "`k = 1,2 / 0,0180 ≈ **67 σ**`. Limiares derivados de ruído operam "
              "tipicamente entre 3 σ e 5 σ: um limiar a 67 σ não pertence a essa "
              "família. A derivação honesta daria entre **0,054 e 0,090 m/s²** — "
              "de treze a vinte e duas vezes menor.",
        correcao="O item foi **recortado, não cumprido**: a seção Z.2.3 passou a "
                 "demonstrar *por que a derivação não produz número útil*, em vez "
                 "de produzir um número que pareceria derivado e não seria.",
        commit="4fb72e4",
        premissa_curta='Que o limiar de 1,2 m/s² vinha do ruído, e o item era só transpor a derivação.',
        premissa="O backlog dizia que o item já estava 'boa parte resolvido' e "
                 "que virara *transpor, não decidir*. De onde o 1,2 vem de "
                 "verdade está em 20/08: da correção da assimetria, herdado de "
                 "`11,0 − 9,81 = 1,19`. É número de engenharia, não de "
                 "estatística — e uma derivação escrita com `k = 67` implícito "
                 "seria **pior que a ausência dela**, porque daria ao 1,2 uma "
                 "procedência que ele não tem, num documento que vai à banca.",
    ),
    Defeito(
        data="2026-09-29", area=ML, item="DATA-07",
        defeito="`d_angulo` **não** é a diferença de `inclinacao_rel` entre "
                "épocas vizinhas, e guardar só uma das duas não reconstrói a "
                "outra.",
        achado_por=CALCULO,
        causa="São ângulos **numa esfera**, e entre eles não vale uma igualdade: "
              "vale a desigualdade triangular esférica "
              "`|θ_t − θ_{t−1}| ≤ d_angulo ≤ θ_t + θ_{t−1}`, que deixa **um grau "
              "de liberdade** que só `ĝ` fecha.",
        correcao="O dispositivo guarda **`ĝ`** por época, e as duas features "
                 "angulares são derivadas **no servidor**, sobre a noite "
                 "completa, pelo mesmo código que produziu os resultados do ML. "
                 "A reconstrução é exata.",
        commit="3f2cb87",
        premissa_curta='Que `d_angulo` é a diferença de `inclinacao_rel` entre épocas vizinhas.',
        premissa="Medido em **87 795 épocas**: a aproximação erra **0,01 grau na "
                 "mediana** e **149 graus no pior caso**, com o erro concentrado "
                 "nas viradas — que é tudo aquilo para o que a feature existe. "
                 "**A mediana boa era a armadilha:** tornava a hipótese plausível "
                 "exatamente onde nada acontece (§8). E resolveu de passagem um "
                 "problema que não estava sendo procurado: `ĝ_ref` é a mediana "
                 "geométrica da gravação **inteira**, e um dispositivo que drena "
                 "em tempo real não pode conhecê-la — a proposta anterior era um "
                 "'acumulador direcional com aquecimento', que é **estimador "
                 "diferente**, não aproximação com tolerância, e divergiria do "
                 "Python em silêncio.",
    ),
    Defeito(
        data="2026-09-29", area=ML, item="DATA-07b",
        defeito="A afirmação de que 'o item virou transcrever' estava errada: as "
                "8 features existiam **só em Python**.",
        achado_por=INVENTARIO,
        causa="Um `grep -rniE \"enmo|zcr|p_frac|inclinacao|d_angulo|mag_din\" "
              "firmware/` devolveu **vazio**. O que o projeto chamava de 'lado "
              "C++' era uma referência **escrita em Python** dentro de "
              "`test_vetor_dourado.py` — útil como especificação, e nenhuma "
              "linha de firmware.",
        correcao="O item foi reescrito com as cinco partes que faltavam de "
                 "verdade, e o peso reclassificado para comparável ao `FW-07`.",
        commit="85f573d, 3f2cb87",
        premissa_curta='Que as features já existiam em C++, e o item era transcrever.',
        premissa="**O item de maior peso do projeto foi subestimado por seis "
                 "dias porque ninguém rodou o grep.** O custo foi de "
                 "classificação: o item figurava como pequeno.",
    ),
    Defeito(
        data="2026-09-30", area=ML, item="DATA-07d",
        defeito="O vetor dourado **gravava a própria referência**: "
                "`test_gravar_vetor_dourado` gravava o arquivo e conferia que ele "
                "existia. Isso nunca falha.",
        achado_por=CONTROLE,
        causa="Qualquer mudança na definição de uma feature reescrevia o dourado "
              "e a suíte seguia verde: **o arquivo perseguia o código em vez de "
              "prendê-lo.**",
        correcao="Agora ele **confere**, e regravar exige dizer que se quer "
                 "regravar (`DORMIO_REGRAVAR_DOURADO=1`) e explicar no commit o "
                 "que mudou de definição.",
        commit="0f22941, 4d1b5d2",
        premissa_curta='Que uma suíte de paridade que passa verifica paridade.',
        premissa="A premissa era que uma suíte de paridade que passa é uma suíte "
                 "que verifica paridade. Um vetor dourado que se regrava sozinho "
                 "não é vetor dourado, é log — e é indistinguível de um que "
                 "prende, até o dia em que uma definição muda em silêncio.",
        instrumento=True,
    ),
    Defeito(
        data="2026-09-30", area=ML, item="DATA-07d",
        defeito="A tolerância do ENMO **reprovaria firmware correto**.",
        achado_por=EXECUCAO,
        causa="Estava em `rel = 1e−6`. Medido em **60 sementes** com a fórmula em "
              "float32 — que é o que o ESP32 calcula —, `enmo_media` diverge "
              "1,10e−6 relativo e `enmo_max` 3,51e−6. A causa é **cancelamento "
              "catastrófico** em `‖a‖ − 1` com `‖a‖ ≈ 1`. Trocar o acumulador "
              "para double **não resolve** (1,101e−6 contra 1,097e−6), porque o "
              "erro entra no `sqrt` **por amostra**, não na soma.",
        correcao="Tolerância **absoluta**, `1e−7 g` = 1 ULP de float32 em 1 g, "
                 "que fica 6 400× abaixo do piso de ruído do ENMO no MPU6050.",
        commit="0f22941",
        instrumento=True,
    ),
    Defeito(
        data="2026-09-30", area=ML, item="DATA-07d",
        defeito="Época incompleta não tem paridade nenhuma, e nada dizia isso.",
        achado_por=EXECUCAO,
        causa="O ramo degenerado de `estimar_gravidade` (n ≤ 9) não existe na "
              "referência estilo-firmware, e ali a divergência vai a **54%**. "
              "Mesmo passando desse ramo: n = 64 diverge 3% e n = 300, 0,8%.",
        correcao="Medido e declarado. **O contrato ainda precisa dizer que o "
                 "dispositivo não emite `f` de época truncada** — segue como "
                 "decisão pendente.",
        commit="0f22941",
    ),
    Defeito(
        data="2026-09-30", area=ML, item="DATA-07d",
        defeito="Os 5 casos do dourado eram **todos de época única**, então "
                "`inclinacao_rel` e `d_angulo` valiam **0 em todos os cinco**: as "
                "duas features de definição mais delicada não tinham referência "
                "nenhuma.",
        achado_por=CONTROLE,
        causa="E zero é trivialmente invariante a rotação, então o teste de "
              "invariância delas **passava sem testar nada**.",
        correcao="O dourado virou dois arquivos, um por fronteira do contrato, "
                 "com 8 sequências (mudança de postura, virada brusca de 140°, "
                 "deriva coerente sub-grau, retorno exato à orientação, faixa "
                 "cobrindo todos os bins, duas épocas, uma época, lacuna "
                 "temporal). As tolerâncias passaram a ser derivadas entre piso "
                 "medido e teto de decisão, e "
                 "`test_as_tolerancias_ainda_cercam_o_piso` **re-mede o piso a "
                 "cada execução**.",
        commit="4d1b5d2",
        premissa_curta='Que os casos do dourado davam referência a todas as features.',
        premissa="Era o mais silencioso dos quatro defeitos do instrumento: o "
                 "que devia pegar a divergência era cego exatamente onde ela "
                 "importa. *Uma tolerância medida uma vez e depois só comentada "
                 "envelhece.*",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-16", area=ML, item="(contrato)",
        defeito="O backend declarava contrato `2.5.0` com o `DATA-CONTRACT.md` em "
                "`2.5.1` desde 30/09.",
        achado_por=EXECUCAO,
        causa="Divergência introduzida ao versionar o documento sem tocar o "
              "backend.",
        correcao="Backend alinhado ao documento.",
        commit="fa34897",
        nota="`test_informa_a_versao_do_contrato_de_dados` não fixa a versão num "
             "literal — **lê do documento**, exatamente para que a divergência "
             "não fosse possível em silêncio. Funcionou: acusou na primeira "
             "execução da suíte do backend depois de 30/09. O teste estava certo "
             "e disponível por duas semanas sem ninguém rodar, **o que é o "
             "argumento do CI em uma frase.**",
    ),

    # ───────────────────────── DOCUMENTAÇÃO ──────────────────────────────
    Defeito(
        data="2026-06-03", area=DOC, item="(README)",
        defeito="O subtítulo do README não correspondia ao título, e o nome do "
                "produto não estava padronizado.",
        achado_por=LEITURA,
        causa="Deriva de redação entre revisões.",
        correcao="Subtítulo alinhado ('detecção de movimento') e nome "
                 "padronizado para 'Smart Dormio'.",
        commit="33000ee, 182f68e",
    ),
    Defeito(
        data="2026-09-29", area=DOC, item="REF-01",
        defeito="Quatro defeitos nas referências bibliográficas, sendo um de "
                "**autoria falsa**.",
        achado_por=TERCEIRO,
        causa="Conferência de 11 fontes **na fonte**: 1 autoria falsa "
              "(`Rocha et al.` → **Li, Halaki & Chow**), 1 tendência não "
              "significativa apresentada como achado, 1 número virado "
              "indevidamente em requisito técnico, 2 citações não localizadas.",
        correcao="Corrigidos. **Nenhuma referência permanece sem autoria "
                 "conferida.**",
        commit="fab1d95",
        premissa_curta='Que citação escrita por quem leu o material está certa.',
        premissa="A premissa era que citação escrita por quem leu o material "
                 "está certa, e que a conferência acharia erros de formatação. E "
                 "o que **não** foi fechado está registrado como `DOC-06b`: "
                 "**referência conferida ≠ artigo lido.** As 11 têm autoria "
                 "correta; quantas foram lidas além do resumo não está registrado.",
        familia=4,
    ),
    Defeito(
        data="2026-09-29", area=DOC, item="LGPD-01",
        defeito="O direito de eliminação estava citado como art. 18, **V** — e é "
                "o **VI**. A troca estava em **cinco lugares**, propagada por "
                "cópia.",
        achado_por=TERCEIRO,
        causa="O inciso V trata de *portabilidade a outro fornecedor*; a "
              "*eliminação dos dados tratados com consentimento* é o VI. Os cinco "
              "lugares: `LGPD-ELIMINACAO.md`, `DATA-CONTRACT.md` §6.2, "
              "`routes.py`, a migração `006` e o `BACKLOG-COMPLETO.md`.",
        correcao="Corrigido nos cinco, com varredura completa conferindo que "
                 "nenhuma outra citação de artigo da LGPD no repositório está "
                 "incorreta.",
        commit="7a5d21a, fab1d95",
    ),
    Defeito(
        data="2026-09-30", area=DOC, item="LGPD-01",
        defeito="O argumento de que 'dado pseudonimizado continua sendo dado "
                "pessoal' estava apoiado no art. 13, §4º, e o apoio era frouxo.",
        achado_por=TERCEIRO,
        causa="A citação **existe e é onde a pseudonimização é definida**, mas o "
              "artigo inteiro trata de *estudos em saúde pública*. Conferido no "
              "Planalto, o §4º abre com 'Para os efeitos deste artigo' — **a "
              "própria lei circunscreve a definição ao art. 13**, o que torna a "
              "objeção textual, e não apenas contextual.",
        correcao="O argumento passou a ser apoiado no **art. 12**, que retira do "
                 "escopo da lei apenas o dado **anonimizado** — de onde se segue, "
                 "por contraste, que o pseudonimizado permanece dentro.",
        commit="fab1d95",
        nota="É o caso em que a citação não estava 'errada' e ainda assim não "
             "sustentava o que lhe pediam.",
    ),
    Defeito(
        data="2026-10-17", area=DOC, item="DOC-10 / UI-10",
        defeito="**Quatro** documentos afirmavam que a tela de exclusão de conta "
                "existia, durante os dezoito dias em que ela estava inalcançável.",
        achado_por=INVENTARIO,
        causa="O backlog (`UI-10 ✅`), o `LGPD-ELIMINACAO.md` ('a interface existe "
              "desde 29/09'), a `POLITICA-DE-PRIVACIDADE.md` §6.4 (que **dizia ao "
              "titular onde clicar**) e o `DIAG-04`, que era o quarto e passou "
              "pela primeira varredura.",
        correcao="Os quatro corrigidos, com nota de procedência. Varredura por "
                 "termos ('ainda não existe', 'não há tela', 'existe como rota') "
                 "sobre `docs/`, `*.md`, `frontend/src/` e `web-app/`.",
        commit="22a9268, c80c2b8, fb2f18f",
        premissa_curta='Que a tela de exclusão existia, como afirmavam quatro documentos.',
        premissa="Detalhe que vale guardar: logo abaixo da afirmação falsa no "
                 "`LGPD-ELIMINACAO.md` estava a linha 'Falta a parte de "
                 "interface: hoje a eliminação existe como rota, e só', marcada "
                 "como obsoleta e mantida 'para o histórico ficar legível' — **a "
                 "linha dita obsoleta estava mais certa que a que a substituiu**, "
                 "por dezoito dias.",
    ),
    Defeito(
        data="2026-10-17", area=DOC, item="(iv)",
        defeito="A política de privacidade §6.3 **negava** a tela que o `UI-11` "
                "acabara de entregar, e mandava o titular escrever para um canal "
                "de contato.",
        achado_por=INVENTARIO,
        causa="O commit do `UI-11` (`2316b06`) não tocou a política. Mesmo dia, "
              "sinal invertido em relação ao caso do `UI-10`.",
        correcao="Corrigida horas depois, ao fechar o `PERFIL-01`.",
        commit="fb2f18f",
        premissa_curta='Que a política de privacidade acompanhava a tela entregue no mesmo dia.',
        premissa="A regra que os dois casos custaram — *o commit que entrega o "
                 "mecanismo atualiza o documento que fala dele, no mesmo commit* "
                 "— **não tem mecanismo**, e isso está dito: nada no repositório "
                 "liga uma afirmação da política de privacidade a um teste. O que "
                 "existe é a varredura à mão.",
    ),
    Defeito(
        data="2026-10-17", area=DOC, item="DOC-11",
        defeito="O `CLAUDE.md` dizia 'ainda não há suíte de testes nem CI' e "
                "'health check ainda não existe'. As duas eram falsas havia "
                "semanas.",
        achado_por=INVENTARIO,
        causa="Afirmação de estado em arquivo de instrução, sem número e sem "
              "data.",
        correcao="Corrigido com os números medidos e a tabela de como rodar cada "
                 "camada — e, como a correção envelheceu em dez dias dentro de um "
                 "arquivo gitignorado, o arquivo passou a ser versionado em 27/10, "
                 "com a parte pessoal em `CLAUDE.local.md`.",
        commit="4014798",
        nota="Até 27/10 esta linha era de procedência parcial: a correção de "
             "17/10 não tinha commit possível, porque o `CLAUDE.md` estava no "
             "`.gitignore`.",
        premissa_curta='Que o arquivo de instruções descrevia o estado do projeto.',
        premissa="O que distingue esta ocorrência das outras do §6: as outras "
                 "enganavam **sobre** o sistema; esta **instruía a não "
                 "verificá-lo** — é o arquivo que orienta cada sessão de trabalho "
                 "dizendo que não há o que rodar. Daí a regra: afirmação de "
                 "estado em arquivo de instrução traz o número e a data da "
                 "medição, porque número com data envelhece **visivelmente** e "
                 "adjetivo não.",
    ),
    Defeito(
        data="2026-10-27", area=DOC, item="UI-18",
        defeito="A parte (c) do item afirmava que o `vitest` não estava em "
                "nenhum job do `ci.yml` — e o job `frontend` o roda desde 19/08.",
        achado_por=INVENTARIO,
        causa="A frase repetia a lista de jobs do `CLAUDE.md` gitignorado, que "
              "estava errada (*'`documentos`, `rls` e os do firmware'*; são seis).",
        correcao="Riscada no backlog, com o commit de origem do job (`01a7faa`).",
        commit="4014798",
        nota="A conferência de 20/10 já tinha achado isto, e o achado ficou oito "
             "dias num arquivo sem commit; a correção de 27/10 foi redescoberta "
             "do zero. É o §2 das lições acontecendo com o próprio registro.",
    ),
    Defeito(
        data="2026-10-27", area=DOC, item="GIT-05",
        defeito="A previsão escrita no item — *'versionando o `CLAUDE.md`, a "
                "lista de ponteiros aceitos cai de 8 para 7'* — estava errada.",
        achado_por=EXECUCAO,
        causa="O arquivo versionado precisa apontar para o `CLAUDE.local.md`, e "
              "isso é ponteiro para arquivo ignorado: sai um, entra outro.",
        correcao="Medido com o `CLAUDE.md` no índice, num clone em Linux: continuam "
                 "8. Corrigido no backlog antes do commit.",
        commit="4014798",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="GIT-06",
        defeito="Cinco linhas deste registro, de procedência 'completa', citavam o "
                "commit `846966a`, que não existe.",
        achado_por=INVENTARIO,
        causa="Erro de digitação do hash `846986a` (o núcleo do firmware, 22/09), "
              "e nada conferia que um hash citado existe.",
        correcao="Hash corrigido, uma das linhas passou a citar também o "
                 "`c0725ca`, e o `--conferir` passou a reprovar hash inexistente e "
                 "histórico raso — com `fetch-depth: 0` no job `documentos`.",
        commit="16552bd",
        nota="Não é `instrumento`: o defeituoso era o registro, não uma "
             "verificação. Na primeira execução marcou-se `instrumento=True`, e a "
             "guarda de prosa do gerador reprovou — o texto da derivação (3) só "
             "admite duas verificações defeituosas achadas sem rodar.",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="GIT-06",
        defeito="A tabela 'A premissa que caiu' mostrava, em cerca de metade das "
                "linhas, uma frase que não era a premissa.",
        achado_por=LEITURA,
        causa="O gerador pegava a primeira frase do campo `premissa`, que muitas "
              "vezes é comentário (*'A tentação era afrouxar a tolerância'*).",
        correcao="Campo próprio `premissa_curta`, obrigatório quando há premissa.",
        commit="16552bd",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="GIT-06", familia=14,
        defeito="Catorze afirmações do backlog contrariadas pela conferência de "
                "20/10 continuavam no backlog oito dias depois: `DIAG-01` e "
                "`DIAG-03` como não começados, a frase velha do `CALC-03`, o "
                "`LGPD-02` contado duas vezes, `PWA-01` e `PERFIL-02` na camada "
                "errada, o item sem ID, `ML-04`/`ML-05` com ID repetido, os "
                "números do `GIT-03` e do `CI-06`, e três pendências sem item (o "
                "push, o projeto Supabase de teste, o conceito de noite).",
        achado_por=INVENTARIO,
        causa="A conferência foi escrita num documento gerado que nunca entrou no "
              "git, e o backlog não foi tocado.",
        correcao="Reconferidas em 28/10 e aplicadas. Os dois DIAG ficaram abertos, "
                 "com o que falta escrito; a contagem foi refeita linha a linha.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 28/10 do diário)", procedencia="parcial",
        premissa="A conferência de 20/10 dizia que o desenho estava pago: *'mitigado "
                 "com uma linha no `BACKLOG-COMPLETO.md`'*. A linha não existia, e a "
                 "conferência inteira não chegou a quem decide — o §2 das lições.",
        premissa_curta="Que uma conferência escrita chega ao backlog.",
    ),
    Defeito(
        data="2026-10-28", area=INFRA, item="DOCS-WIN-01",
        defeito="`conferir_docs_versionados.py` dava resultado errado no Windows: a "
                "verificação (3) não enxergava ponteiro nenhum, e a (2) acusava "
                "arquivos ignorados como pendentes.",
        achado_por=EXECUCAO,
        causa="O pipe em modo texto traduz `\\n` em `\\r\\n` no Windows; todo "
              "caminho menos o último chegava ao `git check-ignore` com `\\r` no "
              "fim e não casava regra nenhuma.",
        correcao="Entrada em bytes e `encoding` explícito — também no "
                 "`verificar_por_mutacao.py`, que morria em `cp1252`. Controle "
                 "positivo: a mesma árvore dá 8 ponteiros em Linux e 0 no Windows "
                 "antes; 8 nos dois depois.",
        commit="ca01355",
        instrumento=True,
        premissa="Uma verificação que passa no CI vale em qualquer máquina. O CI "
                 "(Ubuntu) estava verde e certo; a máquina de quem edita, que é "
                 "onde a (1) existe para rodar, media errado em silêncio.",
        premissa_curta="Que uma verificação que passa no CI vale em qualquer máquina.",
    ),
    Defeito(
        data="2026-10-28", area=INFRA, item="DOCS-WIN-02",
        defeito="`calculos_tcc.py` e `estudo_buffer.py` quebravam no console do "
                "Windows — o primeiro no `--conferir`, depois de as asserções "
                "baterem, de modo que o exit 1 parecia reprovação dos cálculos.",
        achado_por=EXECUCAO,
        causa="Saída com símbolos fora do `cp1252` (✓, ĝ, σ). Registrado em 28/10 "
              "só para o `calculos_tcc`; medir os dois scripts nos dois modos "
              "mostrou que o relatório do `estudo_buffer` também quebrava.",
        correcao="`sys.stdout.reconfigure(encoding='utf-8')` nos dois. Controle: "
                 "com um valor sabotado, o `--conferir` sai 1 e diz o que falhou.",
        commit="7016c81",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-28", area=ML, item="ML-WIN-01",
        defeito="Os dois testes de vetor dourado reprovavam no Windows por "
                "divergência no último dígito de 71 de 14 952 floats.",
        achado_por=EXECUCAO,
        causa="Comparação por igualdade exata de um JSON gravado em Linux: ordem "
              "de soma e libm diferem entre plataformas (pior caso medido: "
              "8,0e-13 relativo).",
        correcao="Estrutura exata e floats com tolerância derivada (1e-9 relativo) "
                 "entre o piso medido e o teto do verificador por mutação, 12/12 "
                 "em Linux e no Windows.",
        commit="7016c81",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-28", area=ML, item="ML-WIN-01",
        defeito="A régua de 1e-9 relativo que substituiu a igualdade exata do "
                "dourado reprovou no runner: `d_angulo` divergiu 5,7e-9.",
        achado_por=EXECUCAO,
        causa="O piso tinha sido medido num único par de plataformas, e régua "
              "relativa é a forma errada para `degrees(arccos(c))`, cujo erro "
              "relativo cresce como 1/θ² perto de 1.",
        correcao="Ângulos com régua absoluta de 1e-4°, derivada da condição do "
                 "`arccos`; 12/12 no verificador por mutação em Linux e no "
                 "Windows.",
        commit="58ae504",
        instrumento=True,
        premissa="Uma régua medida entre duas plataformas vale para as outras. O "
                 "runner do Actions muda de máquina entre execuções: a primeira "
                 "passou até com igualdade exata, a segunda reprovou.",
        premissa_curta="Que o piso medido em duas plataformas valia para todas.",
    ),
    Defeito(
        data="2026-10-28", area=ML, item="ML-WIN-01",
        defeito="O teste de retomada fazia mais de uma dobra por chamada no "
                "Windows com orçamento zero.",
        achado_por=EXECUCAO,
        causa="`elapsed > orcamento_s` com o relógio do Windows em degraus de "
              "~15,6 ms: duas leituras no mesmo degrau dão 0 s, e `0 > 0` é falso.",
        correcao="`>=`. Hipótese confirmada antes de corrigir: com um relógio em "
                 "degraus, o teste reprova 3 de 3 em Linux.",
        commit="7016c81",
        premissa="O relógio de parede mede tempo decorrido com resolução suficiente "
                 "para um orçamento zero. Em Linux mede; no Windows, não — e a "
                 "falha alternava entre execuções, o que a fazia parecer acaso.",
        premissa_curta="Que o relógio tinha resolução para um orçamento zero.",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="DIAG-03",
        defeito="Os diagramas de 29/09 omitiam as features em C++ de 17/10, a rota "
                "`/api/me/perfil` e o `/health`, e o `DIAG-03` rotulava o payload "
                "como `v2.4.0` sem dizer que o contrato estava em 2.5.1.",
        achado_por=INVENTARIO,
        causa="Diagrama datado que ninguém reconferiu depois que o código mudou.",
        correcao="Conferidos contra o código (55 afirmações do `DIAG-01` batem) e "
                 "atualizados pela convenção do próprio diagrama — `(NÃO "
                 "EXERCITADO)` para código que existe e não roda.",
        commit="7016c81",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="DOC-12",
        defeito="O diário dizia que o trabalho anterior a 29/04 não estava no "
                "repositório; estavam lá sete commits de 18–19/02.",
        achado_por=INVENTARIO,
        causa="29/04 é a data do clone no reflog, e a entrada de abertura a tomou "
              "pelo início do histórico — contra o aviso da própria seção 'Sobre "
              "as datas'.",
        correcao="Entrada reconstruída a partir dos sete commits; a lacuna real "
                 "ficou delimitada (nenhum commit de 20/02 a 30/05).",
        commit="7016c81",
        premissa="O registro do projeto é fonte confiável sobre o próprio "
                 "projeto. Tem a mesma autoridade de um documento de terceiro e a "
                 "mesma chance de estar errado — e um `git log --reverse` custava "
                 "um segundo.",
        premissa_curta="Que 29/04 marcava o início do versionamento.",
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="DOCS-WIN-01",
        defeito="A linha do `DOCS-WIN-01` no backlog estava partida em seis desde "
                "o commit `4014798`, com um CR solto no meio.",
        achado_por=LEITURA,
        causa="O texto citava `\\n`, `\\r\\n` e `\\r` como exemplo, e o script que o "
              "gravou os converteu em caracteres de controle.",
        correcao="Linha reconstruída a partir dos bytes; conferido que nenhuma "
                 "linha de tabela ficou sem `|` final.",
        commit="2254934",
        nota="Achado na revisão dos patches pedida pelo Vitor antes do commit.",
    ),
    Defeito(
        data="2026-10-28", area=SEG, item="SEC-12", familia=2,
        defeito="A chave pública (`anon`) executava as sete funções aplicadas na "
                "produção, e a `device_tokens` da 007 nasceria com todos os "
                "privilégios para o cliente.",
        achado_por=CONTROLE,
        causa="No Supabase, objeto criado pelo `postgres` em `public` nasce com "
              "privilégio NOMINAL para `anon` e `authenticated`; as migrações "
              "faziam `revoke ... from public`, que não alcança grant nominal.",
        correcao="Migração 009 (revoga nominalmente e muda o padrão de funções "
                 "futuras) e a 007 revogando a própria tabela e função. Impacto "
                 "medido localmente antes de corrigir: nenhum.",
        commit="040fe4b",
        premissa="Que objeto novo nasce sem privilégio. Verdade no Postgres puro, "
                 "falsa no Supabase — e a configuração que decidia isso "
                 "(`pg_default_acl`) não está no repositório.",
        premissa_curta="Que objeto novo nasce sem privilégio para o cliente.",
        nota="Achado porque uma sabotagem do verificador de migrações não foi "
             "acusada; a causa da cegueira levou à configuração da produção.",
    ),
    Defeito(
        data="2026-10-28", area=SEG, item="SEC-12",
        defeito="Catorze testes da suíte de RLS — os que afirmam o que `anon` e "
                "`authenticated` NÃO alcançam — passavam no vazio.",
        achado_por=CONTROLE,
        causa="A base de teste não reproduzia os privilégios padrão do "
              "Supabase: sem grant nominal para revogar, todo `revoke from "
              "public` parecia bastar.",
        correcao="`esquema_base.sql` passa a declarar os padrões medidos na "
                 "produção; sem a 009 os 14 reprovam, com ela os 151 passam. "
                 "Teste e dois sabotadores novos para o padrão: mutação 32/32.",
        commit="040fe4b",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-28", area=INFRA, item="SEC-13",
        defeito="O verificador de migrações reaplicava os GRANTs depois das "
                "migrações e não via uma migração que tirasse privilégio do "
                "código de main.",
        achado_por=CONTROLE,
        causa="O mesmo desenho do `conftest.py` da suíte de RLS, copiado.",
        correcao="GRANTs aplicados uma vez, logo depois da 001; a sabotagem "
                 "passou a ser acusada ('permission denied for table "
                 "sleep_data'). Na suíte de RLS ficou como item (`SEC-13`).",
        commit="040fe4b",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-28", area=DOC, item="PERFIL-02",
        defeito="O README das migrações não listava a 008, e a tabela estava fora "
                "de ordem (007, 006, 005, 004).",
        achado_por=LEITURA,
        causa="A 008 foi escrita depois do README, e nada confere um contra o "
              "outro.",
        correcao="Tabela em ordem, com a 008 e a 009, a seção de diagnóstico e a "
                 "armadilha dos privilégios padrão.",
        commit="040fe4b",
    ),
    Defeito(
        data="2026-10-30", area=ML, item="ML-12",
        defeito="Em todos os experimentos desde o `ML-02`, o contexto de ±2 épocas "
                "foi empilhado sobre a base concatenada, e nas fronteiras misturava "
                "features de dois sujeitos.",
        achado_por=LEITURA,
        causa="`empilhar_contexto` replica a borda da matriz que recebe; os "
              "experimentos passavam a base inteira, não um sujeito por vez.",
        correcao="O `ML-12` aplica o contexto por sujeito e mediu a diferença: "
                 "+0,001 a +0,002 de κ a favor do global, desprezível. Os "
                 "experimentos anteriores não foram refeitos, de propósito: o "
                 "efeito é uma ordem de grandeza menor que qualquer um deles.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (iv) do diário)", procedencia="parcial",
        nota="Achado ao escrever o `ML-12`, lendo `src/epocas.py` para reusar.",
    ),
    Defeito(
        data="2026-10-30", area=DOC, item="FW-07",
        defeito="A pendência gerada do `FW-07` seguiu descrevendo buffer no RTC e "
                "Deep Sleep depois de o `ARQ-01` decidir a C2 (sono leve).",
        achado_por=LEITURA,
        causa="A propagação da decisão atualizou a linha do `FW-07` no backlog e "
              "não a pendência em `consolidar_registro.py` — o mesmo padrão do "
              "`DOC-05` de 29/10, ao contrário.",
        correcao="Pendência reescrita na mesma leva do `API-03`, que ao fechar "
                 "precisou ler a linha vizinha.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (iii) do diário)", procedencia="parcial",
        nota="Dano: zero (a decisão ainda não tinha saído da branch). Mostra de "
             "novo o que o `DOC-13` registra: nada confere a linha do backlog "
             "contra a pendência gerada.",
    ),
    Defeito(
        data="2026-10-30", area=DOC, item="FW-07",
        defeito="O `firmware/nucleo/README.md` e o texto que o `make capacidade` "
                "imprime seguiam dizendo que o `sketch.ino` reescrito usaria 128 "
                "épocas no RTC, porque o heap não sobrevive ao Deep Sleep, e que o "
                "`API-03` era item aberto.",
        achado_por=LEITURA,
        causa="A propagação da C2 (30/10) passou pelo backlog, pelo `CLAUDE.md` e "
              "pelos documentos de decisão, e não pelos textos do núcleo — que são "
              "os que quem for escrever o sketch lê primeiro. O fechamento do "
              "`API-03` também não voltou a eles.",
        correcao="Os dois textos reescritos para a C2 (heap, flash do `FW-08`) e "
                 "para o `API-03` fechado, com nota de correção.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (v) do diário)", procedencia="parcial",
        nota="Achado ao escrever a parte (a) do `FW-07`, lendo o README para "
             "acrescentar a seção da cadeia. Dano: zero (o sketch não foi "
             "escrito). Terceira vez no mesmo dia que a propagação de uma decisão "
             "esquece um texto — o padrão que o `DOC-13` registra.",
    ),
    Defeito(
        data="2026-10-30", area=INFRA, item="ML-11",
        defeito="O commit do `ML-11` (PR #13) não chegou a `develop`: a PR foi "
                "mesclada na branch da #12, que já tinha entrado em `develop` 19 s "
                "antes.",
        achado_por=INVENTARIO,
        causa="A #13 foi aberta empilhada, com base na branch da #12, contando "
              "que o GitHub a redirecionaria para `develop` quando a #12 "
              "entrasse; o redirecionamento não acontece quando a base é "
              "mesclada e a PR de cima é mesclada logo em seguida, na base velha.",
        correcao="O trabalho seguinte partiu da branch que contém o `ML-11` e a "
                 "PR aponta para `develop`, levando os dois. Regra no `CLAUDE.md`: "
                 "PR sempre com base em `develop`.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (ii) do diário)", procedencia="parcial",
        nota="Achado ao conferir `gh pr view 13` antes de começar o trabalho "
             "seguinte; nenhum dado se perdeu, mas `develop` ficou sem o `ML-11` "
             "por algumas horas.",
    ),
    Defeito(
        data="2026-10-29", area=DOC, item="DOC-05",
        defeito="A linha do `DOC-05` no backlog dizia que o `CLAUDE.md` está no "
                "`.gitignore` e que toda correção nele fica fora do git — ele é "
                "versionado desde 27/10.",
        achado_por=LEITURA,
        causa="Fechar o `DOC-11` atualizou a pendência gerada do `DOC-05` e não "
              "a linha do item no backlog.",
        correcao="Linha corrigida, com a marca ✏️; o `DOC-13` ganhou a ressalva de "
                 "que a guarda proposta não pegaria este caso.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 29/10 (iv) do diário)", procedencia="parcial",
    ),
    Defeito(
        data="2026-10-29", area=DOC, item="DATA-03",
        defeito="O resumo, o quadro e o caminho crítico do backlog citavam como "
                "pendentes seis itens fechados — e o primeiro conselho do arquivo "
                "era rodar o `DATA-03`, fechado na véspera.",
        achado_por=LEITURA,
        causa="Fechar um item mexia na linha dele e na contagem; ninguém buscava "
              "o ID no resto do arquivo.",
        correcao="As três seções reconferidas contra as linhas dos itens e "
                 "corrigidas, com a marca ✏️ onde o texto mudou.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 29/10 (iii) do diário)", procedencia="parcial",
        nota="§6 das lições, ocorrência 8. Achado por leitura, ao responder o que "
             "fazer a seguir; a guarda que faltava virou o `DOC-13`.",
    ),
    Defeito(
        data="2026-10-17", area=DOC, item="(ii)",
        defeito="Uma afirmação da própria sessão saiu sem conferência: 'o "
                "`README.md` manda ler `METODOLOGIA.md`, `HARDWARE.md` e "
                "`DATASET.md`'.",
        achado_por=INVENTARIO,
        causa="Conferido, ele os lista **pelo nome, sem caminho**, na árvore de "
              "'Estrutura'. O efeito sobre quem clona é o mesmo; a afirmação não "
              "era — e a verificação (3) não os pegaria por ali.",
        correcao="Corrigida no mesmo dia, e registrada.",
        commit="3127c38",
        nota="É o §3 do próprio documento de lições, cometido enquanto ele era "
             "escrito.",
    ),
    Defeito(
        data="2026-10-17", area=DOC, item="(iii)",
        defeito="'Reportei duas afirmações falsas e eram três' — conferi o lugar "
                "errado do arquivo certo.",
        achado_por=INVENTARIO,
        causa="Procurei no `LGPD-ELIMINACAO.md` a tabela de citações da Lei, cuja "
              "coluna é *'Confere?'* — ela afirma que a **citação** do artigo "
              "está correta, não que o direito esteja implementado —, concluí que "
              "o arquivo estava certo e segui. A afirmação falsa estava trinta "
              "linhas abaixo, na lista de notas.",
        correcao="A terceira afirmação corrigida.",
        commit="c80c2b8",
        nota="É o §5 aplicado a quem escrevia o §5: o artefato que eu abri não "
             "era o que decidia a resposta, era o vizinho dele.",
    ),

    # ──────────────────────── INFRAESTRUTURA ─────────────────────────────
    Defeito(
        data="2026-02-18", area=INFRA, item="(bootstrap)",
        defeito="O `requirements.txt` não era UTF-8, e o import de `routes` "
                "quebrava no Vercel com `ModuleNotFoundError`.",
        achado_por=EXECUCAO,
        causa="Codificação do arquivo e `sys.path` do runtime serverless.",
        correcao="Conversão para UTF-8 e `sys.path` ajustado em dois commits.",
        commit="ac1a29e, 374e254, 16448e1",
    ),
    Defeito(
        data="2026-02-19", area=INFRA, item="(bootstrap)",
        defeito="Conflito de versão do cliente Supabase produzia erro de proxy, e "
                "o *lazy loading* era simulado.",
        achado_por=EXECUCAO,
        causa="`httpx` não pinado contra a versão do `supabase`.",
        correcao="`supabase` em 2.28.0, `httpx` fixado, e *lazy loading* real.",
        commit="739f24e, 5d2c513",
    ),
    Defeito(
        data="2026-06-02", area=INFRA, item="FIX-01",
        defeito="`/api/sleep-history` devolvia 500 quando o banco falhava.",
        achado_por=EXECUCAO,
        causa="Exceção da camada de banco subindo sem tratamento.",
        correcao="Resposta de erro própria, com teste cobrindo o caminho.",
        commit="eace580, 7b9e52a",
    ),
    Defeito(
        data="2026-06-02", area=INFRA, item="FIX-02",
        defeito="`POST /api/data` respondia **`201 Created` sem gravar**: o "
                "dispositivo recebia confirmação de um dado que não existia.",
        achado_por=LEITURA,
        causa="A resposta `201` era emitida **antes** de o resultado da escrita "
              "ser verificado, então a falha do Supabase não virava erro HTTP.",
        correcao="A resposta passou a depender do resultado da escrita, com "
                 "testes para 201 persistido, 503 sem persistir e 400 com JSON "
                 "inválido.",
        commit="42d543a, c92ed58",
        premissa_curta='Que o dado estava gravado e o problema era de leitura.',
        premissa="A hipótese de partida era 'problema de leitura' — o dado "
                 "estaria gravado e a consulta não o traria. É a **primeira "
                 "ocorrência registrada** do padrão que se repete em todo o "
                 "projeto, *confirmação emitida antes da verificação* (§6), e "
                 "que reaparece no `APP-10`, no `UI-10` e no `PERFIL-01`.",
    ),
    Defeito(
        data="2026-06-03", area=INFRA, item="FIX-03 / FIX-04",
        defeito="Faltava `load_dotenv()` no `app.py`, e o `teste_conexao.py` "
                "chamava uma API que não existia.",
        achado_por=EXECUCAO,
        causa="O `.env` não era carregado em desenvolvimento local; o script de "
              "diagnóstico usava uma interface antiga.",
        correcao="`load_dotenv()` acrescentado e o script reescrito sobre "
                 "`db.get_client()`.",
        commit="0ad144b, 21f3255",
    ),
    Defeito(
        data="2026-06-03", area=INFRA, item="FIX-05 / FIX-07",
        defeito="`charts.js` era código morto não referenciado, e o "
                "`fake_sensor.py` usava `requests` em vez do `httpx` já pinado.",
        achado_por=LEITURA,
        causa="Resíduo de versões anteriores.",
        correcao="`charts.js` removido; `fake_sensor.py` passou a `httpx`.",
        commit="2dfe5b5, 84f5a0c",
    ),
    Defeito(
        data="2026-08-19", area=INFRA, item="FIX-08",
        defeito="Log com emoji e ausência de garantia de não-500 na camada de "
                "banco.",
        achado_por=EXECUCAO,
        causa="Emoji quebrava a codificação do log no runtime; a camada de banco "
              "podia propagar exceção.",
        correcao="Log sem emoji e garantia de não-500.",
        commit="ec5f8b0",
    ),
    Defeito(
        data="2026-08-21", area=INFRA, item="(CI)",
        defeito="O CI **não disparava** em `chore`, `docs`, `security` e `ci` — "
                "cobria só `feature` e `bugfix`.",
        achado_por=LEITURA,
        causa="Lista de prefixos em `on.push.branches` incompleta, e descoberta "
              "depois de uma branch desse tipo passar sem verificação nenhuma.",
        correcao="Prefixos acrescentados.",
        commit="ba9f31a",
        nota="Vale registrar porque é o que torna a branch de trabalho atual "
             "(`chore/GIT-01-…`) coberta pelo gatilho — e é a única razão pela "
             "qual o push, quando sair, fará o CI rodar.",
    ),
    Defeito(
        data="2026-08-21", area=INFRA, item="(repo)",
        defeito="Material interno estava no repositório público, e o README da "
                "`web-app` descrevia um front Jinja já aposentado.",
        achado_por=INVENTARIO,
        causa="Conteúdo de trabalho versionado por inércia.",
        correcao="Material interno retirado; front Jinja aposentado e README "
                 "corrigido.",
        commit="9b4052e, 9b187ee",
    ),
    Defeito(
        data="2026-09-18", area=INFRA, item="GIT-01",
        defeito="`git status` acusava 144 arquivos modificados com **20 243 "
                "inserções e 20 243 remoções** — o mesmo número dos dois lados — "
                "e nenhuma mudança de conteúdo.",
        achado_por=EXECUCAO,
        causa="`git diff --ignore-cr-at-eol` devolveu **vazio**: editar no "
              "Windows salvava CRLF no disco enquanto o histórico guardava LF.",
        correcao="`.gitattributes` com `* text=auto`, tipos declarados "
                 "explicitamente para o caso de o heurístico hesitar, "
                 "`*.sh text eol=lf` (com CRLF o interpretador lê "
                 "`#!/bin/bash\\r` e não encontra o programa) e binários "
                 "marcados `binary`, porque uma única conversão corrompe o "
                 "arquivo.",
        commit="f188ec9",
        premissa_curta='Que alguma ferramenta havia reformatado o repositório.',
        premissa="A hipótese era que alguma ferramenta havia reformatado o "
                 "repositório. E o problema real não era a feiura do diff: era "
                 "que um ajuste de três linhas ficava indistinguível de vinte mil "
                 "linhas de nada, e **revisão que não se consegue fazer não se "
                 "faz**. Quantos diffs passaram sem revisão nesse período não é "
                 "recuperável.",
    ),
    Defeito(
        data="2026-09-22", area=INFRA, item="GIT-04",
        defeito="**Três documentos nunca commitados**, entre eles a fundamentação "
                "que os READMEs mandam ler.",
        achado_por=INVENTARIO,
        causa="Comparação de `git ls-files docs/` com o conteúdo da pasta — e o "
              "problema não estava sendo procurado. Os três: "
              "`BACKLOG-COMPLETO.md`, `ML-DATASETS-E-PLANO.md` e "
              "`SINTESE-PESQUISA-E-CAMINHOS.md`.",
        correcao="Versionados na mesma revisão. A prevenção ficou registrada como "
                 "`CI-05`.",
        commit="6264934, aae01f3",
        premissa_curta='Que o que está em `docs/` está versionado, salvo o que o `.gitignore` exclui.',
        premissa="A premissa era que o que está em `docs/` está versionado, "
                 "exceto o que o `.gitignore` exclui de propósito. Um clone feito "
                 "no dia anterior não traria a fundamentação junto, e quem "
                 "clonasse encontraria READMEs apontando para um arquivo "
                 "inexistente. E nada impedia que acontecesse de novo — o "
                 "`CI-05`, **como foi especificado naquele momento, não "
                 "impediria.**",
    ),
    Defeito(
        data="2026-09-30", area=INFRA, item="CI-05",
        defeito="A prevenção especificada **não podia reprovar**: um job que "
                "falha 'quando há arquivo não rastreado em `docs/`' devolveria "
                "vazio sempre.",
        achado_por=LEITURA,
        causa="Não foi uma execução, foi um raciocínio sobre o que o "
              "`actions/checkout` monta: o git envia **objetos commitados e nada "
              "mais**, então num runner **não existe** arquivo não rastreado em "
              "`docs/` — não porque o repositório esteja limpo, mas porque o "
              "arquivo não rastreado nunca sai da máquina de quem o escreveu.",
        correcao="Reimplementado com **duas** verificações de alcance declarado "
                 "em `scripts/conferir_docs_versionados.py`: (1) órfão na árvore, "
                 "**só detectável na máquina de quem edita**, e o script **diz "
                 "isso** quando roda com `CI` no ambiente; (2) referência "
                 "pendente — `docs/*.md` citado por arquivo rastreado e ausente "
                 "do git **e** do `.gitignore` —, que **roda e reprova no CI**, "
                 "porque tanto a citação quanto a ausência viajam no commit.",
        commit="6312267",
        premissa_curta='Que a especificação do job estava correta e o trabalho era de transcrição.',
        premissa="A premissa era que a especificação estava correta e o trabalho "
                 "era de transcrição. O resultado seria **um selo verde que não "
                 "verificou nada**, contra uma classe de problema que o `GIT-04` "
                 "já demonstrou ser real. A distinção que o script passou a usar "
                 "é a única que importa: **ignorado é decisão, não rastreado e "
                 "não ignorado é esquecimento.** E os outros dois itens do lote "
                 "mudaram de natureza na direção oposta — ficaram mais baratos: o "
                 "`CI-03` pedia uma toolchain de 300 MB e o repositório já tinha "
                 "a verificação; o `CI-04` parecia exigir os ~46 GB de dado e não "
                 "exige.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-16", area=INFRA, item="CI-05",
        defeito="Na primeira execução, **o verificador se acusava a si mesmo**: "
                "reprovou com três referências pendentes, e as três eram prosa.",
        achado_por=EXECUCAO,
        causa="`docs/FOO.md` e `docs/sub/FOO.md` estão no comentário do próprio "
              "`PADRAO_REFERENCIA`, para explicar o que o regex casa, e "
              "`docs/ORFAO-DE-TESTE.md` está no backlog, dentro do procedimento "
              "de validação **deste mesmo script**. Job vermelho desde o "
              "primeiro push.",
        correcao="`EXEMPLOS_EM_PROSA`, isenção estreita e **impressa a cada "
                 "execução** — porque isenção silenciosa é como uma verificação "
                 "deixa de verificar sem ninguém notar. Vale **só para a "
                 "verificação (2)**: na (1) o nome não tem isenção, senão o "
                 "próprio procedimento de validação ficaria incapaz de falhar.",
        commit="7feeef9",
        nota="Validado nas duas direções: órfão criado → a (1) acusa; doc "
             "inexistente citado de dentro de arquivo versionado → a (2) acusa; "
             "árvore limpa → exit 0, inclusive com `CI=true`.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-16", area=INFRA, item="CI-04",
        defeito="A guarda de coleta estava **37 testes defasada**: piso em 70, "
                "suíte com 107. Ela toleraria perder **um terço da cobertura** "
                "sem reprovar.",
        achado_por=EXECUCAO,
        causa="O piso foi medido em 22/09 e nada o reconferia.",
        correcao="Piso em 107, com o motivo e a obrigação de atualizar escritos "
                 "ao lado. Controle positivo real, não simulado: `import` "
                 "inexistente em `testes/test_avaliar.py` → coleta cai a 100 → a "
                 "guarda reprova.",
        commit="6359912",
        premissa_curta='Que a guarda de coleta, medida em 22/09, ainda tinha o piso certo.',
        premissa="**É o próprio modo de falha que ela existia para pegar**, com "
                 "piso alto o bastante para parecer que pegava. E ela é "
                 "necessária ali por um detalhe que vale registrar: o passo roda "
                 "o pytest com `|| true`, então o exit 2 da coleta sumiria — quem "
                 "acusa é a contagem.",
        instrumento=True,
    ),
    Defeito(
        data="2026-10-16", area=INFRA, item="CI-06",
        defeito="**Quatro** jobs nunca rodaram num runner, não três — e o CI não "
                "roda desde 2026-09-10.",
        achado_por=TERCEIRO,
        causa="Medido na API pública do Actions: a última execução é a **#131, de "
              "10/09**, em `develop`, com sucesso. O `ci.yml` que existia em "
              "`develop` naquela data tinha **dois** jobs (`test`, `frontend`); o "
              "da branch tem seis. O quarto é o `rls`, que entrou em 28/09 — "
              "dezoito dias depois da última execução.",
        correcao="A contagem foi corrigida no registro. **Nada foi executado**: "
                 "a tentativa de push foi recusada por ausência de credencial de "
                 "escrita no ambiente.",
        commit="6443005",
        premissa_curta='Que eram três, e não quatro, os jobs nunca rodados num runner.',
        premissa="A categoria 'escrito, não executado' sempre teve um item a mais "
                 "do que o backlog contava, **e o item a mais é justamente o que "
                 "carrega a afirmação de segurança do trabalho** (`SEC-05`, "
                 "isolamento entre usuários). Com a distinção que precisa ser "
                 "feita com cuidado: os testes de RLS **não são código nunca "
                 "executado** — rodaram localmente contra Postgres de verdade. O "
                 "que nunca aconteceu é o **job** rodar, isto é, a guarda contra "
                 "pulo silencioso ser exercitada no lugar onde ela precisa "
                 "funcionar; e a perna da **Postgres 16**, já que o harness foi "
                 "verificado na 14.",
    ),
    Defeito(
        data="2026-10-17", area=INFRA, item="GIT-05",
        defeito="O aviso de captação foi escrito num arquivo que **não chega a um "
                "clone**: o `ROADMAP.md` está no `.gitignore`. A varredura achou "
                "**oito** arquivos ignorados que arquivos rastreados mandam ler.",
        achado_por=EXECUCAO,
        causa="Descoberto porque `git status` **não acusou** a edição. O "
              "`ROADMAP.md` é citado por 8 arquivos rastreados, inclusive "
              "`frontend/src/lib/metricas.ts`.",
        correcao="O aviso foi para o `README.md`, que é versionado. E entrou a "
                 "verificação **(3)** em `scripts/conferir_docs_versionados.py`, "
                 "validada por controle positivo nas duas direções.",
        commit="688165c",
        premissa_curta='Que um aviso escrito no `ROADMAP.md` chega a quem clona.',
        premissa="O `CI-05` **não acusa isso, e não por defeito**: sua "
                 "verificação (2) trata *ignorado como decisão, não "
                 "esquecimento*, e a distinção está certa. O que faltava é que "
                 "ignorar é decisão sobre **distribuição** e não diz nada sobre o "
                 "**ponteiro** que ficou no texto. ⚠️ E a (3) **nasceu com os oito "
                 "dentro da isenção**, cada um com motivo impresso a cada "
                 "execução: **hoje não cobre nenhum dos oito; pega o nono.** É "
                 "catraca, não cobertura, e está dito assim no script, no "
                 "`ci.yml` e no backlog — porque uma verificação que estreia com "
                 "todas as violações atuais isentas é o §1 de novo se não se "
                 "disser isso.",
    ),
    Defeito(
        data="2026-10-17", area=INFRA, item="PERFIL-01",
        defeito="O ID do item novo colidia com um item fechado: `ML-07` já existe.",
        achado_por=INVENTARIO,
        causa="ID escolhido por lembrança. `ML-08` também estava tomado.",
        correcao="Renomeado para `LGPD-06` em todos os lugares que já o citavam.",
        commit="778ec27",
        nota="Achado por `grep` de conferência **depois** de escrever, não por "
             "lembrança.",
    ),
    Defeito(
        data="2026-10-17", area=INFRA, item="PERFIL-01",
        defeito="O `conferir_docs_versionados.py` reprovou duas vezes em dez "
                "minutos, contra quem o escreveu.",
        achado_por=EXECUCAO,
        causa="Caminho de arquivo abreviado com reticências no meio do nome: a "
              "verificação (2) lê isso como citação de arquivo que um clone não "
              "traz. E o erro foi repetido ao **descrever** o erro.",
        correcao="Caminhos escritos inteiros.",
        commit="778ec27",
        nota="Pequeno, e é a verificação (2) fazendo exatamente o que existe para "
             "fazer — o que vale registrar é que ela funcionou contra o autor, "
             "duas vezes seguidas.",
    ),
    Defeito(
        data="2026-10-17", area=INFRA, item="(iii)",
        defeito="208 linhas de conteúdo alheio entraram no diário, duplicando uma "
                "entrada.",
        achado_por=EXECUCAO,
        causa="O heredoc que escrevia o texto num arquivo temporário falhou por "
              "permissão, e o script seguinte leu um `/tmp/entrada.md` "
              "**pré-existente e de outro dono**.",
        correcao="Revertido e reescrito com ferramenta de arquivo. **A lição é de "
                 "método:** script que lê arquivo temporário precisa falhar "
                 "quando o arquivo não é o que ele acabou de escrever — "
                 "`set -euo pipefail` no heredoc teria interrompido antes.",
        commit="(revertido antes de commit)",
        procedencia="parcial",
        nota="Apareceu em `git diff --numstat` como `208 0`, que é um número "
             "impossível para uma inserção de entrada única. **Conferir o "
             "`numstat` antes de commitar foi o que pegou.**",
    ),
    Defeito(
        data="2026-10-31", area=DOC, item="FW-08",
        defeito="O estudo do buffer, o backlog, a pendência gerada e dois documentos "
                "de decisão diziam que a partição de dados padrão tem **1,5 MiB** e "
                "cobre **13,7 dias**. A tabela padrão do `arduino-esp32` tem "
                "0x160000 = **1 408 KiB** de dados.",
        achado_por=LEITURA,
        causa="O estudo de 29/09 citou `tools/partitions/default.csv` sem abrir o "
              "arquivo; o 1,5 MiB virou constante de `estudo_buffer.py` e de "
              "`capacidade.cpp`, e o 13,7 dias se propagou a partir dali. A "
              "`--conferir` do estudo testava a conta, não o dado de entrada.",
        correcao="Constante corrigida para 0x160000 nos dois lugares, com nota. A "
                 "tabela que o projeto usa passou a ser versionada "
                 "(`firmware/partitions.csv`) e `make capacidade` mede a cobertura "
                 "sobre ela, em vez de sobre uma constante.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (iii) do diário)", procedencia="parcial",
        premissa_curta="Que o tamanho da área de dados da tabela padrão era um dado conhecido e estável.",
        premissa="O número entrou como fato de folha e foi tratado como estável, "
                 "quando depende da versão do pacote `arduino-esp32` — que é "
                 "justamente o argumento para versionar a tabela.",
        nota="Dano: superestimava em 9 %. Nenhuma decisão mudou: mais de uma semana "
             "em qualquer das duas tabelas.",
    ),
    Defeito(
        data="2026-10-31", area=SEG, item="SEC-11",
        defeito="A seção X.7 de `LIMITACOES-TCC.md`, texto que vai ao documento "
                "final, dizia \"Adotou-se proteção contra automação (captcha)\" "
                "desde 20/10. O captcha nunca foi ligado, e o frontend não tem uma "
                "linha dele.",
        achado_por=LEITURA,
        causa="O parágrafo foi escrito junto com a decisão (B′) do `SEC-08`, no "
              "tempo verbal de quem já tinha feito, enquanto a ação ficava aberta "
              "como `SEC-11`. Nada conferia a afirmação do texto contra o estado do "
              "item.",
        correcao="Parágrafo reescrito: a mitigação vigente é o limite de taxa por IP "
                 "do serviço, com fonte; o captcha aparece como avaliado e não "
                 "adotado, com o motivo.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (iii) do diário)", procedencia="parcial",
        nota="Achado ao investigar o próprio `SEC-11`. É o §1 das lições na forma "
             "mais direta: uma defesa afirmada que não existe, no texto da banca.",
    ),
    Defeito(
        data="2026-10-31", area=SEG, item="SEC-11",
        defeito="O `SEC-11` mandava ligar o captcha no painel em \"~5 min, sem linha "
                "de código\", e o backlog o recomendava como a primeira coisa a fazer "
                "com cinco minutos. Com o captcha ligado o Supabase responde `400` a "
                "todo login e cadastro sem token, e o frontend não envia token.",
        achado_por=TERCEIRO,
        causa="A afirmação saiu da página de configuração do painel, sem ler o guia "
              "de integração nem o código do servidor. O guia diz que o frontend "
              "precisa mudar; o código mostra o `400`.",
        correcao="Item fechado sem fazer, com as fontes (`middleware.go`, `api.go`, o "
                 "guia de limites de taxa); a linha de conselho do backlog riscada.",
        commit="(o commit que introduz esta linha: um commit não cita o próprio "
               "hash — ver a entrada de 30/10 (iii) do diário)", procedencia="parcial",
        premissa_curta="Que ligar o captcha no painel era uma mudança só de configuração.",
        premissa="O item foi para L3, \"é por você\", sob a premissa de que não havia "
                 "software envolvido. Havia: as quatro chamadas de autenticação do "
                 "frontend.",
        nota="Dano evitado, não ocorrido: a chave nunca foi ligada. Se tivesse sido, "
             "a produção perderia login e cadastro até um deploy do frontend.",
    ),
]


# ══════════════════════════════════════════════════════════════════════════
#  PENDÊNCIAS
#  Conferidas item a item contra o repositório em 2026-10-20. O campo `nota`
#  registra o que a conferência mediu quando ela discordou do backlog.
# ══════════════════════════════════════════════════════════════════════════

PENDENCIAS: list[Pendencia] = [

    # ───────── A — SÓ SOFTWARE, A QUALQUER MOMENTO ───────────────────────
    Pendencia("CALC-01", SOFTWARE, "Modelo de energia/autonomia: corrente por "
              "estado, duty cycle, autonomia. É predição; a medição é o `VAL-02`.",
              "🔴", camada_backlog="L0"),
    Pendencia("CALC-02", SOFTWARE, "Física do acelerômetro: força específica, "
              "resolução, ruído, Nyquist — e por que 21 Hz e não 260 Hz.",
              "🔴", camada_backlog="L0"),
    Pendencia("CALC-03", SOFTWARE, "Índice de atividade e a derivação do limiar. "
              "Já **recortado** em 29/09: a seção demonstra por que `g ± k·σ` não "
              "produz número útil (k = 67). O que resta é a redação do índice por "
              "época.", "🔴", camada_backlog="L0",
              nota="O backlog ainda diz 'boa parte já está resolvida pelo `ML-01`' "
                   "e 'o item virou transpor, não decidir' — frase que o próprio "
                   "`CALC-03` de 29/09 desmentiu. O texto do item não foi "
                   "atualizado depois do achado dos 67 σ. ✏️ **28/10:** riscada no "
                   "backlog."),
    Pendencia("CALC-04", SOFTWARE, "Análise elétrica: pull-down, pull-ups do I2C, "
              "níveis 3,3 V, fonte de despertar.", "🟡", camada_backlog="L0"),
    Pendencia("DIAG-02", SOFTWARE, "Esquemático do circuito; v1 (1 sensor) e v2 "
              "(2, endereços I2C).", "🟡", camada_backlog="L0",
              nota="Confirmado aberto: não há `DIAG-02-*.md` em "
                   "`docs/diagramas/`."),
    Pendencia("DIAG-04", SOFTWARE, "Sequência do fluxo autenticado + modelo ER. "
              "Escrito e revisado em 17/10. **Falta só uma coisa:** os três blocos "
              "mermaid foram validados por **parser**, nunca por **renderização** "
              "— ninguém olhou as figuras.", "🟡", camada_backlog="L0"),
    Pendencia("DOC-05", SOFTWARE, "READMEs e `CLAUDE.md`. Falta só o `DIAG-04`. O "
              "`CLAUDE.md` é versionado desde 27/10 (`DOC-11`).", "🟡",
              camada_backlog="L0"),
    Pendencia("DOC-06b", SOFTWARE, "**Ler os artigos antes de citá-los** "
              "(referência conferida ≠ artigo lido) e converter para o padrão de "
              "citação do TCC.", "🔴", camada_backlog="L0"),
    Pendencia("DOC-09", SOFTWARE, "Diário de engenharia — registro corrente. O "
              "intervalo de junho a agosto segue esparso, porque o "
              "`HISTORICO.md` que o cobre não é versionado e não pode servir de "
              "procedência.", "🟡", camada_backlog="L0"),
    Pendencia("LGPD-01", SOFTWARE, "Política de privacidade e termos. Rascunho "
              "escrito. Faltam **(b)** a rota e a página que sirvam o texto — "
              "isto é software puro. **(a)** controlador e base legal e **(c)** "
              "revisão jurídica estão nos grupos B e E.", "🟡",
              camada_backlog="L0",
              nota="O item estava inteiro em L0; a conferência o divide, porque "
                   "as três partes dependem de coisas diferentes."),
    Pendencia("LGPD-02", SOFTWARE, "Não existe política de retenção: nenhum "
              "expurgo, nenhum prazo. Implementar um prazo, ou declarar "
              "formalmente que não haverá.", "🟡", camada_backlog="L0 e L2",
              nota="⚠️ **Item listado duas vezes no backlog**, em camadas "
                   "diferentes: na seção de documentação como L0 🟡, e na seção "
                   "L2 como ⚪ 'bloqueante da distribuição, não do "
                   "desenvolvimento'. É um item, e a contagem de 76 só fecha se "
                   "ele for contado uma vez. A **decisão** do prazo está no "
                   "grupo B. ✏️ **28/10:** **a contagem não fechava**: a recontagem "
                   "linha a linha mostrou que ele **estava** contado duas vezes. A "
                   "linha de L2 virou ponteiro, e o bloqueio de distribuição foi "
                   "para a de L0."),
    Pendencia("REQ-01", SOFTWARE, "Documentar requisitos: dimensões, conforto, "
              "autonomia, aquecimento, custo, segurança.", "🟡",
              camada_backlog="L0"),
    Pendencia("FW-07 (c)", HARDWARE, "Gravar o `sketch.ino` da C2 na placa e ver, "
              "no log serial: o I2C ler a FIFO, o sono leve acordar a cada ~1,7 s, a "
              "taxa medida dentro de ±20 %, épocas fechando com `f`, e o envio de "
              "10 em 10 min sem transbordo enquanto o Wi-Fi está ligado. As partes "
              "(a) e (b) estão no núcleo e no sketch desde 31/10, testadas no host; "
              "o sketch só foi compilado e ligado com stubs.", "🔴",
              camada_backlog="L1",
              nota="Anda junto com o `FW-05` e o `FW-08` (c): os três são a mesma "
                   "sessão de bancada."),
    Pendencia("FW-08 (c)", HARDWARE, "Exercitar na placa a ponte "
              "`firmware/midia_flash_esp32.h`: gravar com `firmware/partitions.csv`, "
              "ver `abrir()` achar a partição `dormio`, e medir o tempo da montagem "
              "(varre 2 MiB no boot) e do apagamento de setor. As partes (a) e (b) "
              "fecharam em 31/10: a fila na flash existe no núcleo, testada contra "
              "uma flash NOR simulada com corte de energia em cada byte, e cobre "
              "**11,4 dias** medidos sobre a tabela versionada.", "🟡",
              camada_backlog="L1",
              nota="Quem liga a fila ao laço é o `FW-07` (b)."),
    Pendencia("ML-12 (c)", HARDWARE, "Repetir a comparação 8 × 3 features com "
              "dado do travesseiro, quando o `VIA-01`/`VIA-02` o produzirem. As "
              "partes (a) e (b) fecharam em 30/10: no kappa a redução sobrevive; "
              "na especificidade custa de 1 a 5 pontos, e a recomendação é "
              "manter as 6 no dispositivo.", "🟡", camada_backlog="L1"),
    Pendencia("ML-06b", SOFTWARE, "Escrever `ml/src/carregar/walch.py`. A "
              "interface única garante que é só isso. ⚠️ Escrever carregador sem "
              "ver o arquivo real produziu as 10 armadilhas já catalogadas: "
              "escreva, mas **não confie até rodar**.", "🟡", camada_backlog="L0",
              nota="Confirmado aberto: `ml/src/carregar/` tem `base.py`, "
                   "`newcastle.py`, `sintetico.py` e `wearanize.py`. Não há "
                   "`walch.py`."),
    Pendencia("ML-08", SOFTWARE, "Combinação item 9 + HMM com LOSO interno "
              "(N=92). **Provavelmente esforço mal gasto** — a validação externa "
              "já mostrou que o ganho do HMM não atravessa coorte. Registrado "
              "para não parecer esquecimento.", "⚪", camada_backlog="L0"),
    Pendencia("DATA-06", SOFTWARE, "O limiar viaja com a leitura. **A coluna e o "
              "campo dão para criar já**; o *valor* do limiar do celular depende "
              "do `VIA-02` (grupo D).", "🔴", camada_backlog="L0",
              nota="Confirmado aberto: `grep` por `limiar` em "
                   "`web-app/migrations/*.sql` devolve vazio."),
    Pendencia("SEC-08 (declaração)", SOFTWARE, "Decidido em 20/10 — saída (B′). O "
              "que resta é **declaração**, e a seção X.7 de `LIMITACOES-TCC.md` "
              "já foi escrita. ⚠️ Obrigação de reconferir na semana da entrega: "
              "**se as issues #35844 e #2702 forem corrigidas antes, a seção "
              "passa a afirmar falha que não existe.**", "🟠",
              camada_backlog="L0",
              nota="Marcado ✅ DECIDIDO no backlog **e contado como aberto** na "
                   "soma de 76. Defensável — há resíduo declarado —, mas o `✅` é "
                   "exatamente o que o §6 das lições adverte."),
    Pendencia("SEC-09", SOFTWARE, "Dois canais de enumeração fora do cadastro "
              "(`email_exists` na troca de e-mail; `recuperarSenha`). **Declarado, "
              "não corrigível daqui** — os comentários falsos do código já foram "
              "corrigidos; o oráculo está na resposta do Supabase.", "🟡",
              camada_backlog="L0"),
    Pendencia("SEC-10", SOFTWARE, "Pré-sequestro por retenção de credencial. "
              "**Não explorável na configuração atual** (com a confirmação "
              "desligada não existe estado 'não confirmado' para ocupar): é "
              "**pré-condição** de qualquer adoção futura da saída (A), não "
              "pendência corrente.", "🟠", camada_backlog="L0",
              nota="Item de maior severidade declarada do projeto e evidência "
                   "mais fraca — dois relatos de comunidade, nada medido. A "
                   "classificação é da **classe**, não da confirmação."),
    Pendencia("LGPD-06", SOFTWARE, "Se a idade for usar em cálculo, é finalidade "
              "nova e precisa de declaração nova **antes**. Hoje ela decide um "
              "texto e não entra em conta nenhuma. ⚠️ Ordem obrigatória: política "
              "primeiro, código depois.", "⚪", camada_backlog="L0"),
    Pendencia("UI-18", SOFTWARE, "Duas partes, não três: **(a)** asserção nomeada "
              "por rota — hoje só `/configuracoes` tem, e por isso a varredura "
              "cobre rota nova mas **não rota removida**; **(b)** as três "
              "afirmações condicionais de honestidade científica "
              "(`AvisoDeLacuna`, `NotaDeInferencia`, `NotaDeEscopo`), uma "
              "asserção por condição com o par negativo de cada.", "🟡",
              camada_backlog="L0",
              nota="⚠️ **A parte (c) do item é falsa e caiu nesta conferência.** "
                   "Ela afirma que 'o `montagem.test.ts` não está em nenhum job "
                   "do `ci.yml` — e nem o `vitest` está: os jobs são "
                   "`documentos`, `rls` e os do firmware'. O `ci.yml` tem **seis** "
                   "jobs, e o `frontend` roda `npm test` → `vitest run` desde o "
                   "commit `01a7faa` (19/08), dois meses antes de a afirmação ser "
                   "escrita. Medido aqui: `npx vitest run` coleta **418 testes em "
                   "27 arquivos**, incluindo `src/montagem.test.ts` (16 testes). "
                   "O que é verdade é mais estreito e já é o `CI-06`: nenhum job "
                   "rodou em runner desde 10/09, e o `montagem.test.ts` é "
                   "posterior a essa data. ✏️ **Esta nota ficou oito dias num "
                   "arquivo sem commit**, e a parte (c) só foi riscada do backlog "
                   "em 27/10, por quem a redescobriu do zero sem saber desta."),
    Pendencia("UI-19 (classe)", SOFTWARE, "As duas instâncias fecharam em 20/10; "
              "**a classe não.** Não há verificação de alcance no nível do "
              "**símbolo** — export que ninguém importa, dentro de arquivo que "
              "está no grafo, passa pelo `alcance.test.ts` (arquivo) e pelo "
              "`montagem.test.ts` (render). Ferramenta pronta (`knip`, "
              "`ts-prune`) ou script próprio **com controle positivo**, porque o "
              "instrumento é a parte difícil e isso já foi medido.", "🟡",
              camada_backlog="L0"),
    Pendencia("FW-01", SOFTWARE, "Lógica atividade/repouso por época no firmware. "
              "**Parcialmente coberto:** o `envio-continuo` já classifica por "
              "época de 30 s desde o `HW-05`; falta levar ao `sketch.ino` "
              "(`FW-07`).", "🟡", camada_backlog="L0"),
    Pendencia("FW-03", SOFTWARE, "Empacotamento do dado conforme `DATA-01`.",
              "🟡", camada_backlog="L0"),
    Pendencia("HW-01", SOFTWARE, "Revisar o BOM: o que é andaime (botão, "
              "pull-down de 10 kΩ) e o que é produto. É análise, não montagem.",
              "🟡", camada_backlog="L0"),
    Pendencia("APP-03", SOFTWARE, "Armazenamento seguro do token. *Reavaliar: com "
              "o `APP-08`, o token pode deixar de existir no celular.*", "🟡",
              camada_backlog="L0"),
    Pendencia("APP-02", SOFTWARE, "Android nativo com foreground service. "
              "Fazível hoje; **caro e pós-banca**.", "⚪", camada_backlog="L0"),
    Pendencia("UI-15", SOFTWARE, "Bundle num único chunk; o Vite avisa a cada "
              "build. Code splitting por rota resolve.", "⚪", camada_backlog="L0",
              nota="Confirmado aberto: `vite.config.ts` não tem `manualChunks` "
                   "nem `rollupOptions`."),
    Pendencia("UI-20", SOFTWARE, "Aplicar a linguagem de "
              "blueprint também no app autenticado (hoje vive só na landing).",
              "⚪", camada_backlog="L0",
              nota="⚠️ **Item sem ID**, listado com '—' no backlog. Entra na "
                   "contagem de 46 para a soma fechar, e um item sem ID não dá "
                   "para citar, fechar nem rastrear. ✏️ **28/10:** ganhou o ID `UI-20`."),
    Pendencia("GIT-05", SOFTWARE, "Reduzir a lista de **8 ponteiros pendurados** "
              "— arquivo por arquivo: versionar, ou parar de citar. O "
              "`ROADMAP.md` é o primeiro a decidir (8 arquivos rastreados o "
              "citam). Só o `HISTORICO.md` é ponteiro legítimo.", "🟡",
              camada_backlog="L0",
              nota="Confirmado por execução: `conferir_docs_versionados.py` sai 0 "
                   "e imprime os 8 isentos. A verificação (3) **não cobre nenhum "
                   "dos oito; pega o nono.**"),
    Pendencia("DOC-13", SOFTWARE, "Nada confere o resumo, o quadro e o caminho "
              "crítico do backlog contra as linhas dos itens; em 29/10 eles citavam "
              "seis itens fechados como pendentes. Uma conferência que reprove ID "
              "fechado citado ali.", "⚪", camada_backlog="L0"),
    Pendencia("SEC-13", SOFTWARE, "A suíte de RLS reaplica os GRANTs das tabelas "
              "depois de todas as migrações, o que desfaz qualquer `revoke` que uma "
              "delas faça. Separar o arquivo das sabotagens do de GRANTs, e rodar "
              "estes logo depois da 001.", "🟡", camada_backlog="L0"),
    Pendencia("CI-02", SOFTWARE, "O CI **não roda linter** — não há ESLint nem "
              "Ruff/flake8. Pressupõe uma decisão de configuração que ninguém "
              "tomou, porque ligar linter sem configuração produz um job vermelho "
              "permanente.", "⚪", camada_backlog="L0",
              nota="Confirmado aberto: não há `.eslintrc*`, `eslint.config.*`, "
                   "`ruff.toml` nem `setup.cfg` em lugar nenhum do repositório. "
                   "A **decisão** de configuração está no grupo B."),

    # ───────── B — DECISÃO DO VITOR ──────────────────────────────────────
    Pendencia("LGPD-01 (a)", DECISAO, "Controlador e base legal da política de "
              "privacidade.", "🟡", camada_backlog="L0",
              decisao="O controlador é você pessoa física ou a instituição de "
                      "ensino? E a base legal é consentimento (art. 7º, I) ou "
                      "pesquisa (art. 7º, IV)? Muda a política inteira e **não "
                      "dá para inferir do repositório.**"),
    Pendencia("LGPD-02 (prazo)", DECISAO, "Política de retenção.", "🟡",
              camada_backlog="L0",
              decisao="Qual o prazo de retenção, ou se vai declarar "
                      "formalmente que não haverá expurgo. **As duas saídas são "
                      "defensáveis; o silêncio não.**"),
    Pendencia("LGPD-05", DECISAO, "Idade autodeclarada pode revelar que o titular "
              "é criança ou adolescente, e o art. 14 impõe tratamento próprio. "
              "Hoje o sistema não verifica e não trata diferente.", "🟡",
              camada_backlog="L0",
              decisao="(a) restringir o cadastro a maiores de 18, (b) implementar "
                      "o fluxo de consentimento de responsável, ou (c) manter a "
                      "lacuna declarada. **A defesa de (c) expira no dia em que "
                      "alguém além de você criar conta.**"),
    Pendencia("ARQ-02 — modos de registro", DECISAO, "Quatro modos analisados "
              "em `docs/ARQUITETURA-DE-CAPTACAO.md`: travesseiro com bateria "
              "máxima (WoM), travesseiro com análise completa (sono leve + FIFO), "
              "celular para teste rápido (navegador) e celular para a noite "
              "inteira (app nativo).", "⚪", camada_backlog="L0",
              decisao="Quais modos oferecer, e se o travesseiro terá um ou dois? "
                      "A análise recomenda um modo só no travesseiro antes da "
                      "banca."),
    Pendencia("FW-08 (a, b) — as escolhas", DECISAO, "Persistência em flash.",
              "🔴", camada_backlog="L0",
              decisao="LittleFS ou NVS? E versionar o `partitions.csv` — hoje o "
                      "esquema é o padrão implícito da IDE, e se a flash vira "
                      "armazenamento de dado de pesquisa o layout dela é parte "
                      "do projeto, não escolha de ferramenta."),
    Pendencia("UI-19 (ferramenta)", DECISAO, "Verificação de alcance no nível do "
              "símbolo.", "🟡", camada_backlog="L0",
              decisao="Ferramenta pronta (`knip` / `ts-prune`, mais uma "
                      "dependência) ou script próprio (mais código nosso, e o "
                      "instrumento é a parte difícil — a primeira tentativa "
                      "sub-relatou código morto)?"),
    Pendencia("CI-02 (configuração)", DECISAO, "Linter.", "⚪",
              camada_backlog="L0",
              decisao="Qual configuração de ESLint/Ruff adotar, e quantos "
                      "achados de estilo você aceita corrigir de uma vez — "
                      "porque ligar sem decidir isso produz um job vermelho "
                      "permanente, que é como se aprende a ignorar o CI."),
    Pendencia("HW-02", DECISAO, "Energia: LiPo + TP4056, e se o DevKit V1 fica ou "
              "sai. O DevKit **não atinge µA** — regulador e USB-serial dominam o "
              "consumo.", "🟡", camada_backlog="L3",
              decisao="O DevKit V1 fica (e a autonomia do trabalho é a dele) ou "
                      "sai (e há compra)? **Pode exigir compra.**"),
    Pendencia("ESC-01 — 'o conceito de noite'", DECISAO, "A decisão de escopo que "
              "atravessa o trabalho inteiro.", "🔴", camada_backlog="L3",
              decisao="O trabalho pode afirmar *'a noite de 27/08'* sem afirmar "
                      "que o dado é sono? Hoje o painel diz 'sessão de captação', "
                      "que é o teto honesto. É sua **e do orientador**.",
              nota="Está num parágrafo solto do backlog, não numa linha de item — "
                   "é a maior decisão em aberto sem ID próprio. ✏️ **28/10:** virou "
                   "o item `ESC-01`."),
    Pendencia("APP-04", DECISAO, "iOS: **investigação, não implementação.** Rota "
              "A (áudio em background) muda o escopo declarado e a conversa de "
              "LGPD; rota B (`CMSensorRecorder`) é coerente e **não "
              "verificada**.", "⚪", camada_backlog="L0",
              decisao="Vale gastar a investigação antes da banca, sabendo que a "
                      "rota A muda o escopo declarado do trabalho?"),

    # ───────── C — AÇÃO DO VITOR QUE NÃO É DECISÃO ───────────────────────
    Pendencia("Etapa 0 — soldar", ACAO, "**Soldar os 8 pinos do MPU6050.** Teste "
              "de aceitação: pose Z+ com ruído ~0,02. **Trava as camadas L1 e L2 "
              "inteiras.**", "🔴", camada_backlog="L3",
              nota="O contato por jumper produziu, em 25/08, registradores "
                   "zerados, `‖a‖ = 56,5 m/s²` com a placa parada, `−11,6 °C` e "
                   "ruído 30× o normal. O viés de Z, `−1,06 m/s²`, é **89% do "
                   "limiar de movimento inteiro.**"),
    Pendencia("INFRA-03 — monitor da produção", ACAO, "O job que chama o "
              "`/health` de produção a cada 3 dias está em `main` desde o release "
              "de 29/10, e a execução manual passou. Falta a primeira execução "
              "**agendada** (pelo cron, 31/10) — é ela que fecha o item.", "🟡",
              camada_backlog="L3",
              nota="A produção esteve fora do ar até 28/10 sem ninguém saber: o "
                   "projeto Supabase do plano gratuito pausa depois de uma semana "
                   "sem uso. Reativado pelo Vitor no mesmo dia."),
    Pendencia("INFRA-02 — projeto Supabase de teste", ACAO, "Criar um projeto Supabase de "
              "teste e rodar um punhado de `curl`. **Fecharia quatro itens de uma "
              "vez:** o ponto cego do `UI-11` (a troca de e-mail exige "
              "confirmação? `updateUser({data:{nome:null}})` apaga a chave?), o "
              "canal 2 do `SEC-08` (`identities`), o canal 4 / `SEC-09` "
              "(`/recover` em domínio real) e o `SEC-10` inteiro.", "🔴",
              camada_backlog="L3",
              nota="⚠️ **Não tem item próprio**, e o diário de 20/10 (iii) "
                   "registra isso textualmente: 'quatro itens esperando o mesmo "
                   "objeto, e ele não tem item'. É a terceira sessão seguida em "
                   "que o instrumento que falta é o mesmo. **Candidato número 1 a "
                   "item novo.** ✏️ **28/10:** virou o item `INFRA-02`."),
    Pendencia("GIT-03", ACAO, "Apagar o resíduo de sandbox no `.git`. Nada quebra "
              "enquanto ficar: `git fsck` dá exit 0 e os commits funcionam. "
              "**Exige um terminal na máquina.**", "⚪", camada_backlog="L0",
              nota="⚠️ **Número do backlog defasado.** Ele diz "
                   "'`.git/_lixo_sandbox/` (57 itens, 240 KB)' e "
                   "'`.git/_locks_orfaos/` (vazia)'. Medido agora: "
                   "`_lixo_sandbox/` tem **148 itens** e `_locks_orfaos/` tem "
                   "**9**. O item não mudou de natureza; o número citado como "
                   "medido envelheceu — é o §3 das lições no próprio backlog. "
                   "✏️ **28/10:** medido de novo (148 itens, 330 KB; 9) e corrigido "
                   "no backlog."),
    Pendencia("ML-06a", ACAO, "Baixar o Walch et al. 2019 (PhysioNet "
              "`sleep-accel`, 31 sujeitos). **Não é alcançável do ambiente de "
              "execução** — precisa ser baixado da sua máquina. Sem ela, a "
              "degradação entre coortes é **estimativa pontual, não medida de "
              "variabilidade**.", "🟡", camada_backlog="L3"),
    Pendencia("AUTH-06", ACAO, "SMTP próprio (Resend/Brevo) para 'esqueci minha "
              "senha'. Exige criar conta em serviço externo.", "⚪",
              camada_backlog="L3"),

    # ───────── D — BLOQUEADO POR HARDWARE OU COLETA ──────────────────────
    Pendencia("CAL-01", HARDWARE, "Caracterização de 6 posições. Sketch pronto. "
              "Produz viés e escala por eixo desta unidade.", "🔴",
              camada_backlog="L1"),
    Pendencia("CAL-02", HARDWARE, "**Repetir** a caracterização depois do "
              "`FW-06`. O filtro passou de 260 Hz para 21 Hz, o que muda o ruído "
              "de base — e o limiar é definido sobre esse ruído. **Número medido "
              "antes disso não transfere.**", "🔴", camada_backlog="L1"),
    Pendencia("VIA-01", HARDWARE, "Viabilidade de bancada: 2 min parado → 2 min "
              "mexendo a cabeça → 2 min virando o corpo. *Os três blocos se "
              "separam?*", "🔴", camada_backlog="L1"),
    Pendencia("VIA-02", HARDWARE, "O mesmo protocolo com **celular e travesseiro "
              "gravando ao mesmo tempo**. Produz o limiar do celular "
              "(`DATA-06`), a diferença de acoplamento medida e o grupo de "
              "controle.", "🔴", camada_backlog="L1"),
    Pendencia("ARQ-01 (c)", HARDWARE, "**Medir na placa**: os 18,8 KiB do "
              "acumulador, os ~29 000 MACs em `double` por época e o tempo de "
              "parede do fechamento são `sizeof` e aritmética no host. Se a "
              "escolha for o sono leve com FIFO: a latência e a corrente do sono "
              "leve na placa, o transbordo da FIFO (esvaziada a cada 1,70 s a "
              "50 Hz), a taxa real do MPU e a reassociação Wi-Fi (§8 do documento "
              "do `ARQ-01`). **O `ARQ-01` só fecha com (c).**",
              "🔴", camada_backlog="L1"),
    Pendencia("FW-05", HARDWARE, "Amostragem bruta para o ML, na arquitetura "
              "decidida no `ARQ-01` (C2, 30/10): MPU a 50 Hz pela FIFO, DLPF de "
              "21 Hz, ESP32 em sono leve, taxa medida e reamostragem para 32 Hz "
              "como o `ml/`. O lado C++ das features já existe e passa.", "🔴",
              camada_backlog="L1"),
    Pendencia("FW-02", HARDWARE, "Deep Sleep real testado na placa (hoje é mock "
              "do Wokwi).", "🟡", camada_backlog="L1"),
    Pendencia("FW-04", HARDWARE, "Portar o firmware para a placa sem dependências "
              "do Wokwi.", "🟡", camada_backlog="L1"),
    Pendencia("HW-03", HARDWARE, "Wake-on-Motion real: ligar o INT do MPU6050 a "
              "um GPIO RTC. Hoje o despertar é por EXT1 num **botão** — andaime "
              "de simulação. ⚠️ **30/10: deixou de ser pré-requisito** — com a "
              "C2 (`ARQ-01`) o ESP32 acorda por temporizador; o INT vira opcional "
              "(alarme de transbordo da FIFO).",
              "🟡", camada_backlog="L1"),
    Pendencia("HW-04", HARDWARE, "Encapsulamento e fixação para uso noturno; "
              "**segurança térmica do LiPo dentro do travesseiro**.", "🔴",
              camada_backlog="L1"),
    Pendencia("HW-06", HARDWARE, "Entregáveis físicos: esquema de ligação, "
              "diagrama de montagem, fotos.", "🟡", camada_backlog="L1",
              nota="Confirmado: `hardware/` está **vazio**."),
    Pendencia("CALC-05", HARDWARE, "Análise térmica com **medição real** — "
              "`P = V·I`, elevação de temperatura, limites do LiPo.", "🟡",
              camada_backlog="L1"),
    Pendencia("VAL-01", HARDWARE, "Uma noite captada. 🛑 **Com o firmware como "
              "está, a noite sai sem feature nenhuma e o modelo não a consome** "
              "— cadência de 0,1 Hz (3 amostras por época) e o acumulador recusa "
              "a época. O transporte do vetor existe desde 30/10 (`DATA-07b`); o "
              "que falta é firmware: `FW-05`, `FW-07` (b) e `FW-08` → **só "
              "então** captar.", "🔴",
              camada_backlog="L1",
              nota="Confirmado: `INTERVALO_AMOSTRA_MS = 10000` em "
                   "`envio-continuo.ino:109`. O `montar_payload` emite "
                   "`f`/`g`/`fs` desde o `DATA-07b`, mas nenhum sketch o chama com "
                   "o vetor."),
    Pendencia("VAL-02", HARDWARE, "Validação quantitativa: F1, matriz de "
              "confusão, curva de corrente×tempo medida.", "🔴",
              camada_backlog="L2"),
    Pendencia("DASH-04", HARDWARE, "Visualização de **noite completa**: linha do "
              "tempo e lacunas como indicador de repouso. O gráfico já está "
              "preparado; falta o dado.", "🔴", camada_backlog="L2"),
    Pendencia("ML-09 (calibração)", HARDWARE, "Calibração do modelo para o Dormio "
              "com dado próprio. **Ajuste de limiar, não re-treino** — n=1 não "
              "treina nada.", "🟡", camada_backlog="L2",
              nota="⚠️ **Colisão de ID:** `ML-04` também é o item de validação "
                   "externa, **fechado em 18/09**. Dois itens com o mesmo ID, um "
                   "fechado e um aberto, nas seções 'Concluído' e L2. O mesmo "
                   "vale para `ML-05`. ✏️ **28/10:** o aberto virou `ML-09`; os "
                   "documentos de plano, que numeram assim, ganharam a "
                   "correspondência ao lado."),
    Pendencia("ML-10 (devolução)", HARDWARE, "O que o modelo devolve ao usuário — "
              "e o que **não** devolver. **A especificidade externa de 0,507 é o "
              "que o produto deve assumir, não os 0,802 internos.**", "🟡",
              camada_backlog="L2",
              nota="⚠️ Mesma colisão de ID do `ML-04`: `ML-05` fechado é o teto "
                   "interavaliador (28/09). ✏️ **28/10:** virou `ML-10`."),
    Pendencia("ML-INF", HARDWARE, "Onde a inferência roda. Proposta: job em lote "
              "no backend Python ao fim de uma sessão, **não no ESP32**.", "🟡",
              camada_backlog="L2"),
    Pendencia("HW-07", HARDWARE, "Arquitetura v2 — fusão de 2 acelerômetros, **se "
              "o `VIA-01` mostrar** que o travesseiro subcapta movimento de "
              "corpo. Gatilho, não plano. **Implica rever a redação da RQ.**",
              "🟡", camada_backlog="L2"),
    Pendencia("APP-09", HARDWARE, "Continuidade quando o usuário troca celular "
              "por sensor. Instrumentos diferentes, limiares diferentes "
              "(`DATA-06`).", "🟡", camada_backlog="L2"),
    Pendencia("UI-14", HARDWARE, "Lista de espera na landing. 🔒 Gatilho: "
              "protótipo funcionando **e** `VIA-01`. Não fazer antes.", "⚪",
              camada_backlog="L2"),
    Pendencia("APP-05", HARDWARE, "Distribuição (loja ou APK). Depende de "
              "`LGPD-02` e `APP-04`.", "⚪", camada_backlog="L2"),
    Pendencia("PWA-01", HARDWARE, "**Exercitar a instalação de verdade.** O "
              "service worker não registra em desenvolvimento, então 'Adicionar à "
              "tela inicial' só aparece em produção — e ninguém testou. O "
              "comportamento do iOS com `display: standalone` também não foi "
              "verificado.", "🟡", camada_backlog="L3",
              nota="⚠️ **Reclassificado.** O backlog o põe em L0, e ele não é "
                   "software que dá para fazer hoje: exige um dispositivo e um "
                   "deploy de produção para exercitar. `public/sw.js` e "
                   "`lib/instalacao.ts` existem; o que falta é o teste em "
                   "aparelho. ✏️ **28/10:** movido para a seção L3 do backlog."),

    # ───────── E — BLOQUEADO POR TERCEIRO ────────────────────────────────
    Pendencia("RQ-01", TERCEIRO_G, "Confirmar RQ e hipótese com o **orientador "
              "metodológico**.", "🔴", camada_backlog="L3"),
    Pendencia("LGPD-03", TERCEIRO_G, "**O ML eleva a aposta.** Um modelo que "
              "infere sono sobre pessoa identificada muda a natureza do "
              "tratamento: passa a haver *inferência* sobre saúde, não só "
              "registro de movimento. Termo de consentimento e, se houver "
              "voluntários no `VIA-02`, **comitê de ética**. Agora é concreto, "
              "não hipotético — o modelo existe.", "🔴", camada_backlog="L3"),
    Pendencia("LGPD-01 (c)", TERCEIRO_G, "Revisão jurídica da política de "
              "privacidade.", "🟡", camada_backlog="L0"),
    Pendencia("SEC-09 / X.7 — issues de terceiro", TERCEIRO_G, "A seção X.7 "
              "depende de **duas issues em aberto** (`supabase/supabase` #35844 e "
              "`supabase/auth` #2702). **Se forem corrigidas antes da entrega, a "
              "seção passa a afirmar falha que não existe** — espelho exato do "
              "`DOC-11`. Reconferir na semana da entrega e registrar a data de "
              "consulta.", "🟡", camada_backlog="L0"),
    Pendencia("DUA do Wearanize+ restrito", TERCEIRO_G, "**Não está no caminho "
              "crítico, e isto é o que mudou de verdade no projeto.** A coleção "
              "aberta `Wearanize+ OA` tem tudo que o experimento precisa, sem "
              "cadastro. O DUA destrava só os questionários, e exige assinatura "
              "que **não é só sua**. Guia completo em "
              "`docs/WEARANIZE-ACESSO.md`.", "⚪", camada_backlog="(fechado)",
              nota="Entra na lista **porque o enunciado pediu os bloqueios de "
                   "terceiro**, e porque é o bloqueio de terceiro mais citado na "
                   "história do projeto. Hoje é caminho alternativo documentado, "
                   "**não pendência** — e por isso fica fora da contagem."),
]

# Itens que aparecem na lista para dar o quadro completo, e que NÃO são
# pendência: entram marcados e ficam fora de toda contagem. A lista é curta de
# propósito — tudo o mais que está listado conta.
FORA_DA_CONTAGEM = {"DUA do Wearanize+ restrito"}


# ══════════════════════════════════════════════════════════════════════════
#  RENDERIZAÇÃO
# ══════════════════════════════════════════════════════════════════════════

def _celula(texto: str) -> str:
    """Escapa o que quebraria uma célula de tabela markdown."""
    return texto.replace("|", "\\|").replace("\n", " ")


def _contados() -> list[Defeito]:
    return [d for d in DEFEITOS if d.conta]


def _contar(chave) -> Counter:
    return Counter(chave(d) for d in _contados())


def _pendencias_contadas() -> list[Pendencia]:
    return [p for p in PENDENCIAS if p.item not in FORA_DA_CONTAGEM]


def gerar_correcoes() -> str:
    por_instrumento = _contar(lambda d: d.achado_por)
    por_area = _contar(lambda d: d.area)
    por_procedencia = _contar(lambda d: d.procedencia)
    contados = _contados()
    premissas = [d for d in contados if d.premissa]
    fora = [d for d in DEFEITOS if not d.conta]
    total = len(contados)

    # Os três agrupamentos que sustentam a afirmação metodológica. Derivados,
    # não escritos: mudar uma linha da tabela muda estes números.
    so_lendo = por_instrumento[LEITURA] + por_instrumento[CALCULO]
    exercitando = (por_instrumento[EXECUCAO] + por_instrumento[CONTROLE]
                   + por_instrumento[USO_REAL])
    fora_do_repo = por_instrumento[TERCEIRO] + por_instrumento[DADO_REAL]
    conferindo = por_instrumento[INVENTARIO]

    L: list[str] = []
    A = L.append

    A("# Correções aplicadas — Smart Dormio")
    A("")
    A("> **Gerado por `scripts/consolidar_registro.py`.** Não edite este arquivo")
    A("> à mão: o `--conferir` do script reprova se ele divergir da tabela de")
    A("> dados, e documento gerado e editado à mão mente sobre a própria")
    A("> procedência. Para mudar o conteúdo, mude a tabela `DEFEITOS` no script.")
    A(">")
    A("> **Fonte:** `docs/DIARIO-DE-ENGENHARIA.md` (procedência primária),")
    A("> `docs/LICOES-APRENDIDAS.md` (o mesmo material por padrão de falha), o")
    A("> histórico do git e os itens fechados do `docs/BACKLOG-COMPLETO.md`.")
    A("> Onde este arquivo e o diário divergirem, **o diário vence.**")
    A("")
    A("Este arquivo existe para servir ao **capítulo de desenvolvimento**. A")
    A("pergunta que ele responde não é *o que foi consertado* — isso o `git log`")
    A("já responde — e sim **por qual instrumento cada defeito apareceu**, que é")
    A("a única coisa aqui que sustenta uma afirmação de método.")
    A("")
    A("---")
    A("")
    A("## Resumo quantitativo")
    A("")
    agrupadas = [d for d in contados if d.familia > 1]
    soma_familias = sum(d.familia for d in contados)

    A(f"**{total} correções registradas**, todas sustentadas no repositório.")
    A("")
    A("**A unidade de contagem, dita antes dos números, porque ela decide como")
    A("lê-los.** Uma linha deste arquivo é **uma correção**: um defeito, uma")
    f_ = ", ".join(f"`{d.item}` ({d.familia})" for d in agrupadas)
    A(f"causa, uma correção. Em {len(agrupadas)} linhas, porém, a causa e a correção foram")
    A(f"uma só e os defeitos foram vários — {f_} —, e agrupá-las foi deliberado,")
    A("porque separá-las contaria a mesma correção várias vezes. **Contando")
    A(f"defeito em vez de correção, o total seria {soma_familias}.** Este")
    A(f"arquivo usa **{total}**, que é o número menor e o mais defensável.")
    A("")
    if fora:
        nomes = ", ".join(f"`{d.item}`" for d in fora)
        A(f"**Fora da contagem, e visível:** {len(fora)} linha(s) — {nomes} —,")
        A("em que a hipótese se confirmou e o que se corrigiu foi a afirmação")
        A("que se podia extrair do resultado, não um defeito. Estão na seção da")
        A("área, marcadas ⛔, e não entram em número nenhum deste arquivo.")
        A("")
    A("### Por área")
    A("")
    A("| Área | Correções |")
    A("|---|---:|")
    for area in AREAS:
        A(f"| {area} | {por_area[area]} |")
    A(f"| **Total** | **{total}** |")
    A("")
    A("### Por instrumento — o campo que dá valor a este arquivo")
    A("")
    A("| Como foi encontrado | Correções | O que o instrumento é |")
    A("|---|---:|---|")
    GLOSSA = {
        LEITURA: "Inspeção do código ou do documento, raciocinando sobre ele. "
                 "Nada roda, nada se confere contra terceiro.",
        CALCULO: "Aritmética sobre os próprios números do projeto. O mais "
                 "barato de todos, e derrubou premissas grandes.",
        EXECUCAO: "Rodar código do projeto — suíte, job, compilador, script — e "
                  "a **saída** acusar. O defeito não estava escondido: estava "
                  "não exercitado.",
        CONTROLE: "Provocar o defeito de propósito e exigir que a verificação "
                  "acuse. Inclui verificação por mutação. **É o único "
                  "instrumento que mede o alcance de uma verificação.**",
        INVENTARIO: "Conferir estado declarado contra estado real: `grep` por "
                    "símbolo, `git ls-files` contra o disco, varredura de "
                    "afirmações em documentos.",
        TERCEIRO: "Especificação, documentação oficial, artigo, issue ou API de "
                  "terceiro. O artefato que decide a resposta está **fora** do "
                  "repositório.",
        DADO_REAL: "Só apareceu com o arquivo ou a medição real em mãos.",
        USO_REAL: "Alguém usou o produto como usuário.",
    }
    for inst in INSTRUMENTOS:
        A(f"| **{inst}** | {por_instrumento[inst]} | {_celula(GLOSSA[inst])} |")
    A(f"| **Total** | **{total}** | |")
    A("")
    A("### As três derivações que os números sustentam")
    A("")
    A("> ⚠️ **São derivação nossa, não medição de nada.** O denominador é a")
    A("> tabela deste arquivo, isto é, *o que o projeto registrou* — e o próprio")
    A("> `LICOES-APRENDIDAS.md` adverte, na seção do que não cobre, que os")
    A("> padrões de instrumento são **provavelmente subcontados, porque só se")
    A("> descobre instrumento defeituoso quem procura**. A mesma ressalva vale")
    A("> aqui, e com um agravante: defeito que nunca foi encontrado não aparece")
    A("> em tabela nenhuma. **Nenhuma destas três frases é uma taxa de defeitos")
    A("> do projeto; são proporções do que foi achado.**")
    A("")
    instr = [d for d in contados if d.instrumento]
    instr_lendo = [d for d in instr if d.achado_por in (LEITURA, CALCULO)]
    inst_instr = Counter(d.achado_por for d in instr)

    A("**(1) Exercitar achou perto do dobro do que ler.**")
    A(f"Execução, controle positivo e uso real somam **{exercitando} de {total}**")
    A(f"registros ({100*exercitando//total}%). Leitura e cálculo — os dois")
    razao = f"{exercitando / so_lendo:.1f}".replace(".", ",")
    A(f"instrumentos que não precisam rodar nada — somam **{so_lendo}**"
      f" ({100*so_lendo//total}%). A razão é de **{razao} para 1**.")
    A("")
    A("Com a ressalva que impede a leitura fácil: isto **não** diz que ler é")
    A("pouco útil. Diz que, neste projeto, leitura e execução acharam classes")
    A("**diferentes** de defeito — a leitura achou lógica errada (o `201` sem")
    A("gravar, a medição esperando pela rede, o sketch de uma amostra por boot),")
    A("e a execução achou **alcance** insuficiente. Alcance não se vê lendo, e é")
    A("por isso que a razão é essa e não o contrário.")
    A("")
    A(f"**(2) {fora_do_repo} correções tinham a causa fora do repositório.**")
    A(f"Fonte de terceiro e dado real somam **{fora_do_repo} de {total}**"
      f" ({100*fora_do_repo//total}%) — defeitos cuja causa não está em nenhuma")
    A("linha deste projeto, e que **nenhum teste daqui poderia pegar**: a")
    A("especificação do PostgREST, a unidade do Empatica em `g/64`, o valor de")
    A("uma chave num painel do Supabase, a API do Actions, os coeficientes do")
    A("`scipy`. É a justificativa quantitativa das regras 6 e 8 do §5 das lições")
    A("(*comportamento de serviço se confere na especificação do serviço*;")
    A("*conclusão condicionada a configuração não fecha por leitura*) — e o")
    A("motivo pelo qual o item mais repetido deste projeto é **um projeto")
    A("Supabase de teste**, que deve a quatro itens e desde 28/10 tem item próprio")
    A("(`INFRA-02`).")
    A("")
    rodando = inst_instr[EXECUCAO] + inst_instr[CONTROLE]
    A(f"**(3) As próprias verificações do projeto estavam defeituosas")
    A(f"{len(instr)} vezes — e {rodando} dessas {len(instr)} só apareceram")
    A("rodando ou sabotando.**")
    A(f"São **{len(instr)} de {total}** registros"
      f" ({100*len(instr)//total}%) em que a coisa errada era um teste, uma")
    A("guarda de CI, um harness de mutação ou um vetor de referência — não o")
    A("código. A distribuição:")
    A("")
    A("| Instrumento que achou | Verificações defeituosas |")
    A("|---|---:|")
    for i, n in inst_instr.most_common():
        A(f"| {i} | {n} |")
    A("")
    A("As duas que sobram da conta são as que valem mais. **Uma** foi pega por")
    A("leitura — o `CI-05`, cuja especificação não podia reprovar porque")
    A("`actions/checkout` monta a árvore a partir do commit; foi raciocínio, e")
    A("foi o mais barato de todos. **A outra** veio de fonte de terceiro: os")
    A("coeficientes de referência do filtro, escritos de memória, que faziam o")
    A("teste reprovar código correto até serem conferidos contra o `scipy`.")
    A("")
    A("**Então a regra honesta não é *não confie em leitura*.** É que leitura")
    A("pega alcance quando se faz a pergunta certa — *em que máquina isto")
    A("ficaria vermelho?* —, e essa pergunta funcionou exatamente uma vez em")
    A(f"{len(instr)}. Nas outras {len(instr) - 1}, o alcance só apareceu quando")
    A("alguém tentou fazer a verificação falhar.")
    A("")
    A("### Procedência")
    A("")
    A("| Procedência | Correções | O que significa |")
    A("|---|---:|---|")
    A(f"| `completa` | {por_procedencia['completa']} | Commit **e** artefato "
      "reabrível — teste, script, seção de documento. Dá para reconferir sem "
      "acreditar em ninguém. |")
    A(f"| `parcial` | {por_procedencia['parcial']} | Só a mensagem de commit, só "
      "a entrada de diário, ou correção em arquivo não versionado. Entra porque "
      "omitir seria pior, e entra **marcada**. |")
    A("")
    A(f"**{len(premissas)} dos {total} defeitos revelaram que a premissa estava")
    A("errada** — não que o código estava errado. É a seção mais instrutiva deste")
    A("arquivo e tem lugar próprio no fim.")
    A("")
    A("### O que foi deixado fora de propósito")
    A("")
    A("Para a contagem não inflar, **não** entraram: funcionalidade entregue")
    A("(`AUTH-01..05`, `UI-01..07`, `DASH-01/02/05/06/10`, `APP-01/07/08`,")
    A("`BRAND-01/03`, `DEMO-01`, `SEC-04`, `WEB-04`, `DATA-01/04/05`, `CI-01`, o")
    A("bloco `ML-01..ML-08` como entrega); otimização sem defeito de corretude;")
    A("e endurecimento que não consertou comportamento errado. **Entregar o que")
    A("não existia não é corrigir defeito.**")
    A("")
    A("**Entraram de propósito, e é escolha discutível:** defeito em *documento*")
    A("e defeito em *instrumento de medida*. Os dois entram porque, neste")
    A("projeto, são a maior parte do que o registro tem de instrutivo — uma")
    A("afirmação falsa numa política de privacidade e um vetor dourado que se")
    A("regrava sozinho são defeitos com consequência. Quem precisar da contagem")
    A("só de código filtra pela coluna de área.")
    A("")
    A("---")
    A("")

    for area in AREAS:
        da_area = [d for d in DEFEITOS if d.area == area]
        if not da_area:
            continue
        contados_area = [d for d in da_area if d.conta]
        inst_area = Counter(d.achado_por for d in contados_area)
        resumo = " · ".join(f"{n} {i}" for i, n in inst_area.most_common())
        A(f"## {area} — {len(contados_area)} defeitos")
        A("")
        A(f"*{resumo}*")
        A("")
        for d in da_area:
            marca = " 🔄" if d.premissa else ""
            if not d.conta:
                marca += " — ⛔ **fora da contagem**"
            A(f"### {d.data} · `{d.item}`{marca}")
            A("")
            A(f"**O defeito.** {d.defeito}")
            A("")
            A(f"**Como foi encontrado.** *{d.achado_por}* — {d.causa}")
            A("")
            A(f"**A correção.** {d.correcao}")
            A("")
            if d.premissa:
                A(f"**🔄 A premissa estava errada.** {d.premissa}")
                A("")
            if d.nota:
                A(f"**Nota.** {d.nota}")
                A("")
            A(f"**Commit.** `{d.commit}` · procedência **{d.procedencia}**")
            A("")
        A("---")
        A("")

    A("## Os defeitos que revelaram premissa errada")
    A("")
    A("É a seção que o capítulo de desenvolvimento deve usar, porque é a única")
    A("em que o trabalho aprende algo em vez de só consertar algo. Em cada um")
    A("destes casos o enunciado de partida estava errado, e seguir o enunciado")
    A("com competência teria produzido a coisa errada bem feita.")
    A("")
    A("| Data | Item | A premissa que caiu |")
    A("|---|---|---|")
    for d in premissas:
        A(f"| {d.data} | `{_celula(d.item)}` | {_celula(d.premissa_curta)} |")
    A("")
    A(f"**{len(premissas)} de {total}.** E a distribuição por instrumento dentro")
    A("deste subconjunto é a parte que vale registrar:")
    A("")
    inst_prem = Counter(d.achado_por for d in premissas)
    A("| Instrumento | Premissas derrubadas |")
    A("|---|---:|")
    for inst, n in inst_prem.most_common():
        A(f"| {inst} | {n} |")
    A("")
    prem_lendo = inst_prem[LEITURA] + inst_prem[CALCULO]
    prem_fora = len(premissas) - prem_lendo
    A(f"**{prem_fora} das {len(premissas)} premissas caíram quando alguém saiu")
    A("do próprio raciocínio** — rodando, sabotando, conferindo o artefato,")
    A("abrindo a especificação do fornecedor, ou preenchendo o formulário como")
    A(f"usuário. As outras {prem_lendo} caíram lendo e calculando, e vale")
    A("nomeá-las, porque são o contraexemplo da leitura fácil deste arquivo:")
    A("")
    for d in premissas:
        if d.achado_por in (LEITURA, CALCULO):
            A(f"- **`{d.item}`** ({d.achado_por}) — {_celula(d.defeito)}")
    A("")
    A(f"Os **{inst_prem[CALCULO]} de cálculo** são o detalhe que merece ficar: os")
    A("quatro saíram de **aritmética sobre números que já estavam escritos no")
    A("projeto** — uma subtração contra `g`, uma divisão por σ, uma desigualdade")
    A("triangular, uma raiz de banda. É o instrumento mais barato que existe")
    A("aqui, nenhum deles levou mais de um minuto, e os quatro derrubaram")
    A("premissa que estava em uso havia semanas. **Se há uma recomendação de")
    A("método que sai deste arquivo inteiro, é essa: antes de transpor um número")
    A("para o texto, divida-o por outro.**")
    A("")
    A(f"E os **{inst_prem[LEITURA]} de leitura** têm traços que valem contra a")
    A("conclusão apressada de que ler não serve. Em quatro deles, o que a")
    A("leitura achou não foi um erro de escrita, foi uma **estrutura ausente** —")
    A("a resposta emitida antes da verificação, a conexão dentro do laço de")
    A("amostragem, a amostragem periódica que não existia, o job que não tinha")
    A("como reprovar. Nenhum apareceria rodando, porque em três dos quatro casos")
    A("**não havia o que rodar**. O quinto (`FW-08`, 31/10) é de outra natureza:")
    A("um número citado de um arquivo de terceiro que ninguém tinha aberto. A")
    A("conferência do estudo rodava e passava, porque testava a conta, não o")
    A("dado de entrada — só abrir o arquivo o derrubava.")
    A("")
    A("---")
    A("")
    A("## O que este arquivo não cobre")
    A("")
    A("Registrado para que a ausência não passe por completude.")
    A("")
    A("| Lacuna | Por quê |")
    A("|---|---|")
    A("| Defeitos anteriores a 2026-02-18 | Anteriores ao primeiro commit "
      "(`d74aa01`). Não há procedência. ✏️ **Até 28/10 esta linha dizia "
      "29/04**, que é a data do clone no reflog, não do início do histórico — "
      "a mesma premissa estava no diário e nas lições, e foi corrigida lá no "
      "`DOC-12`. Entre 20/02 e 30/05 não há commit nenhum. |")
    A("| Grande parte de junho a agosto | O `HISTORICO.md` cobre o período e "
      "**não é versionado**, então não serve de procedência num capítulo de "
      "TCC. Os defeitos desse intervalo aqui saem de mensagem de commit, e por "
      "isso vários estão marcados `parcial`. |")
    A("| Todo defeito de hardware | **Nada foi medido no dispositivo físico.** "
      "Os 8 pinos do MPU6050 não estão soldados. A única medição de hardware do "
      "projeto é a de 25/08, que é a medição de um sensor mal conectado e serve "
      "só para dizer que não serve. Quando a bancada existir, é provável que "
      "esta seja a área mais cara do arquivo. |")
    A("| Defeitos que ninguém achou | Óbvio e precisa estar escrito, porque é o "
      "que invalida qualquer leitura das três derivações como taxa. |")
    A("| A fronteira `execução` × `inventário` | Traçada por critério declarado "
      "no cabeçalho do script, e há casos de fronteira. Quem discordar de uma "
      "classificação move uma linha na tabela e os números acompanham. |")
    A("")
    return "\n".join(L) + "\n"


def gerar_pendencias() -> str:
    contadas = _pendencias_contadas()
    por_grupo = Counter(p.grupo for p in contadas)
    total = len(contadas)

    L: list[str] = []
    A = L.append

    A("# Pendências em aberto — Smart Dormio")
    A("")
    A("> **Gerado por `scripts/consolidar_registro.py`.** Não edite à mão.")
    A(">")
    A("> **Conferido item a item contra o repositório em 2026-10-20**, na branch")
    A("> `chore/GIT-01-normalizar-fim-de-linha`, árvore limpa. O que a")
    A("> conferência mediu está no campo **Conferência** de cada item, e só")
    A("> aparece quando ela **discordou** do backlog ou acrescentou um número.")
    A(">")
    A("> **Em 2026-10-28** as discordâncias foram reconferidas e aplicadas ao")
    A("> backlog (`GIT-06`). Cada uma traz, no fim da nota, o que foi feito —")
    A("> inclusive as duas que **não** fecharam (`DIAG-01`, `DIAG-03`).")
    A("")
    A("## Por que em documento próprio, e não no topo do backlog")
    A("")
    A("Três razões, em ordem de peso.")
    A("")
    A("**(1) O eixo é outro.** O `BACKLOG-COMPLETO.md` organiza por **camada de")
    A("dependência** (L0–L3) e responde *'o que trava o quê?'*. Este arquivo")
    A("organiza por **natureza do desbloqueio** e responde *'o que eu faço, e o")
    A("que só sai se outra pessoa agir?'*. São perguntas diferentes, e as")
    A("respostas não se mapeiam uma na outra: o `ARQ-01` é um item de camada L0")
    A("cujas partes (a) e (b) são software e cuja parte (c) é bancada; o")
    A("`PERFIL-02` é L0 na tabela e L3 no título. Pôr as duas taxonomias no")
    A("mesmo arquivo cria **duas ordenações dos mesmos itens no mesmo lugar**, e")
    A("a que estiver no topo passa a parecer a que vale.")
    A("")
    A("**(2) O projeto já pagou por afirmação duplicada que divergiu.** É a")
    A("regra 7 do §1 das lições — *verificação não recompõe o que ela verifica* —")
    A("e a assimetria de `serieMisturaInstrumentos`, em que o comentário e a")
    A("implementação tinham alcances diferentes. Uma seção no topo do backlog")
    A("seria uma segunda cópia do estado de cada item, mantida à mão,")
    A("ao lado da primeira. **A cópia divergiria, e a de cima é a que se lê.**")
    A("")
    A("**(3) Este arquivo é gerado e conferível; uma seção não seria.** A")
    A("contagem por grupo sai de um `Counter`, e o `--conferir` reprova se o")
    A("arquivo em disco divergir dos dados. Uma seção escrita à mão no backlog")
    A("não tem como ficar vermelha — que é exatamente a ocorrência 5 do §6 das")
    A("lições (*o verde era um `✅` num arquivo de texto*).")
    A("")
    A("**O que a separação custa, e como está pago.** O risco é o §2 — *análise")
    A("correta que não chega onde a decisão é tomada*. Mitigado com uma linha no")
    A("`BACKLOG-COMPLETO.md`, logo abaixo da contagem, apontando para cá. Uma")
    A("linha, não um resumo: resumo é a cópia que diverge.")
    A("")
    A("---")
    A("")
    A("## Contagem")
    A("")
    A("| Grupo | Itens |")
    A("|---|---:|")
    for g in GRUPOS:
        A(f"| {ROTULO_GRUPO[g]} | **{por_grupo[g]}** |")
    A(f"| **Total** | **{total}** |")
    A("")
    A("⚠️ **Este total não é comparável à contagem do backlog, e a diferença não é")
    A("erro de nenhum dos dois.** São unidades de contagem diferentes: o backlog")
    A("conta **itens**, e aqui alguns itens aparecem **partidos**, porque suas")
    A("partes dependem de coisas diferentes e juntá-las esconde o que trava o")
    A("quê. Os partidos são `ARQ-01` (a,b software · a-escolha decisão · c")
    A("bancada), `LGPD-01` (a decisão · b software · c terceiro), `LGPD-02`")
    A("(prazo decisão · implementação software), `FW-08` (escolhas decisão ·")
    A("implementação software), `UI-19` (ferramenta decisão · classe software),")
    A("`CI-02` (configuração decisão · execução software), `DATA-07b`,")
    A("`DATA-06`, `ML-09` e `ML-10`. E entraram **três itens que o backlog não")
    A("tinha em 20/10**: o push, o projeto Supabase de teste e a decisão de")
    A("escopo do 'conceito de noite' — os três eram parágrafo solto dentro de")
    A("outro item. **Desde 28/10 têm ID no backlog:** `GIT-07`, `INFRA-02` e")
    A("`ESC-01`.")
    A("")
    A("---")
    A("")

    for g in GRUPOS:
        do_grupo = [p for p in PENDENCIAS if p.grupo == g]
        n = por_grupo[g]
        A(f"## {ROTULO_GRUPO[g]}")
        A("")
        A(f"**{n} itens.**")
        A("")
        if g == DECISAO:
            A("Cada linha traz a decisão em uma frase. Nenhum destes itens anda")
            A("sem uma resposta sua — e nenhum deles exige que você escreva")
            A("código para responder.")
            A("")
        if g == ACAO:
            A("Nada aqui é decisão: a decisão já foi tomada, ou nunca houve uma.")
            A("São ações que só você pode executar, porque exigem credencial,")
            A("terminal na máquina, ferro de solda ou uma conta num serviço.")
            A("")
        for p in do_grupo:
            fora = p.item in FORA_DA_CONTAGEM
            titulo = f"### `{p.item}` {p.peso}"
            if fora:
                titulo += " — ⛔ **não é pendência, fora da contagem**"
            A(titulo)
            A("")
            A(p.o_que)
            A("")
            if p.decisao:
                A(f"**A decisão.** {p.decisao}")
                A("")
            if p.camada_backlog:
                A(f"*Camada no backlog: {p.camada_backlog}.*")
                A("")
            if p.nota:
                A(f"**Conferência.** {p.nota}")
                A("")
        A("---")
        A("")

    A("## O que a conferência não conseguiu verificar")
    A("")
    A("Separado de propósito, porque *'não verificado'* e *'verificado e aberto'*")
    A("não são a mesma informação — é a distinção que o `LIMITACOES-TCC.md` faz")
    A("sobre a segunda coorte externa.")
    A("")
    A("| O que | Por quê |")
    A("|---|---|")
    A("| **Se o `DATA-03` e o `PERFIL-02` já rodaram no Supabase** | Exige acesso "
      "ao projeto. Os dois arquivos `.sql` estão em disco e mergeados; **se "
      "foram aplicados em produção não é observável daqui.** Os dois seguem "
      "listados como abertos porque é o que o backlog afirma, e isso é "
      "repetir status não conferido — está dito para que você possa fechá-los em "
      "dez segundos se já tiverem rodado. |")
    A("| **A suíte de RLS** | Exige Postgres de verdade, e este ambiente não tem "
      "`apt-get` nem root. Contado estaticamente: **125 funções de teste** em 6 "
      "arquivos, com 11 `parametrize`. ✏️ **A 'divergência' 146 × 149 que "
      "esta linha registrava foi resolvida em 28/10, e não era divergência:** "
      "contando a coleta em cada commit, são **146** em `778ec27` e `73c213f` "
      "(17/10) e **149** desde `275665a` (19/10), que acrescentou 3 testes. Os "
      "dois documentos estavam certos para as suas datas. |")
    A("| **O `vite build`** | `EPERM` ao esvaziar `frontend/dist/` neste "
      "ambiente — o sandbox não desvincula arquivo na pasta montada, mesma "
      "limitação do `GIT-03`. O `tsc --noEmit` roda e sai **limpo**. |")
    A("| **Qualquer número de hardware** | Os 8 pinos não estão soldados. |")
    A("")
    A("## O que a conferência mediu e confirmou")
    A("")
    A("Executado em **2026-10-20**, na branch `chore/GIT-01-normalizar-fim-de-linha`,")
    A("árvore limpa. **É fotografia daquela data**, não estado corrente — os")
    A("números atuais estão na seção \"Testes\" do `CLAUDE.md`:")
    A("")
    A("| Camada | Medido | Bate com o registro? |")
    A("|---|---|---|")
    A("| Núcleo C++ (`make`) | **341 verificações, 0 falhas** | sim |")
    A("| Paridade do dourado (`make dourado`) | **157 verificações, 0 falhas** | "
      "sim |")
    A("| Sketches (`make sintaxe`) | **4/4 compilam** | sim |")
    A("| `ml/` (`pytest testes`) | **107 passam** | sim — e é exatamente o piso "
      "da guarda do `CI-04` |")
    A("| Backend (`pytest --ignore=tests/rls`) | **293 passam** | sim |")
    A("| Frontend (`vitest run`) | **418 testes em 27 arquivos** | sim |")
    A("| `tsc --noEmit` | limpo | sim |")
    A("| `conferir_docs_versionados.py` | **exit 0**, 8 ponteiros isentos | sim |")
    A("| Commits sem push | **76** contra `origin/main` **e** `origin/develop` | "
      "**não** — o backlog diz 6 |")
    A("| Jobs no `ci.yml` | **6** (`test`, `rls`, `frontend`, `ml`, `firmware`, "
      "`documentos`) contra **2** em `develop` | sim — os quatro do `CI-06` |")
    A("| `.git/_lixo_sandbox/` | **148 itens**; `_locks_orfaos/` **9** | **não** "
      "— o backlog diz 57 e 'vazia' |")
    A("")
    return "\n".join(L) + "\n"


# ══════════════════════════════════════════════════════════════════════════

def _conferir_prosa() -> list[str]:
    """Frases do texto que NOMEIAM casos e por isso não podem ser derivadas.

    Um número puro sai da contagem. Uma frase como "as duas que sobram são o
    `CI-05` e os coeficientes do filtro" não: se a tabela mudar, derivar o
    número deixaria a explicação errada com o número certo, que é pior. Aqui
    cada frase dessas declara o que ela supõe; se a tabela deixar de bater, o
    gerador para e manda reescrever o parágrafo.
    """
    contados = _contados()
    inst = Counter(d.achado_por for d in contados)
    erros = []

    def exige(cond: bool, onde: str, o_que: str) -> None:
        if not cond:
            erros.append(f"{onde}: {o_que}")

    so_lendo = inst[LEITURA] + inst[CALCULO]
    exercitando = inst[EXECUCAO] + inst[CONTROLE] + inst[USO_REAL]
    exige(1.5 * so_lendo < exercitando < 2.5 * so_lendo, "derivação (1)",
          "o título diz 'perto do dobro' e a razão saiu de (1,5; 2,5)")
    instr = [d for d in contados if d.instrumento]
    sobram = {(d.item, d.achado_por) for d in instr
              if d.achado_por not in (EXECUCAO, CONTROLE)}
    exige(sobram == {("CI-05", LEITURA), ("DATA-07b", TERCEIRO)},
          "derivação (3)",
          f"o texto nomeia 'as duas que sobram' (CI-05 por leitura, DATA-07b "
          f"por terceiro), e a tabela tem {sorted(sobram)}")
    exige(sum(1 for d in instr if d.achado_por == LEITURA) == 1,
          "derivação (3)", "o texto diz que a pergunta 'funcionou exatamente "
          "uma vez' — isto é, uma verificação defeituosa achada por leitura")
    premissas = [d for d in contados if d.premissa]
    calc = {d.item for d in premissas if d.achado_por == CALCULO}
    exige(calc == {"DATA-02", "FW-06", "CALC-03", "DATA-07"}, "premissas",
          f"o parágrafo de cálculo descreve quatro operações (subtração, "
          f"divisão por σ, desigualdade triangular, raiz de banda), e a tabela "
          f"tem {sorted(calc)}")
    lend = {d.item for d in premissas if d.achado_por == LEITURA}
    exige(lend == {"FIX-02", "HW-05", "FW-07", "CI-05", "FW-08"}, "premissas",
          f"o parágrafo de leitura descreve quatro estruturas ausentes e um "
          f"dado de terceiro nunca conferido (FW-08), e a tabela tem {sorted(lend)}")
    return erros


def _conferir_commits() -> list[str]:
    """Todo hash citado tem de existir neste repositório.

    Nasceu do `846966a`: cinco linhas de procedência 'completa' citavam um
    commit que não existe — o real é `846986a`. Com histórico raso (checkout
    com `fetch-depth: 1`) a conferência seria impossível; aí ela REPROVA em
    vez de passar sem conferir, porque passar em silêncio é o §1 das lições.
    """
    raso = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        cwd=RAIZ, capture_output=True, encoding="utf-8")
    if raso.returncode != 0:
        return ["não consegui consultar o git: " + raso.stderr.strip()]
    if raso.stdout.strip() == "true":
        return ["histórico raso: não dá para conferir os hashes. No CI, use "
                "`fetch-depth: 0` no checkout."]
    hashes = sorted({h for d in DEFEITOS for h in HASH.findall(d.commit)})
    r = subprocess.run(
        ["git", "cat-file", "--batch-check"], cwd=RAIZ,
        input=("\n".join(f"{h}^{{commit}}" for h in hashes) + "\n").encode(),
        capture_output=True)
    # Uma resposta por hash, na ordem, e só "<sha> commit <tamanho>" passa.
    # Medido em 28/10 (git 2.47 e 2.50): prefixo que casa dois commits volta
    # como "missing", igual a hash inexistente — então ambíguo já reprova. A
    # regra "só commit passa", em vez de "missing reprova", é para que um
    # formato de resposta que esta versão não produz não passe em silêncio.
    respostas = r.stdout.decode("utf-8").splitlines()
    if len(respostas) != len(hashes):
        return [f"o git respondeu {len(respostas)} linhas para "
                f"{len(hashes)} hashes"]
    ruins = [(h, linha.split()[-1]) for h, linha in zip(hashes, respostas)
             if linha.split()[1:2] != ["commit"]]
    return [f"commit {estado}: {h} (em "
            f"{', '.join(sorted({d.item for d in DEFEITOS if h in d.commit}))})"
            for h, estado in ruins]


SAIDAS = {
    "docs/CORRECOES-APLICADAS.md": gerar_correcoes,
    "docs/PENDENCIAS-ABERTAS.md": gerar_pendencias,
}


def main() -> int:
    for fluxo in (sys.stdout, sys.stderr):
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--conferir", action="store_true",
                    help="não grava; sai != 0 se o disco divergir dos dados")
    args = ap.parse_args()

    # Guardas do próprio instrumento. Um gerador que aceita dado incoerente
    # produz documento coerente sobre dado errado, que é pior.
    sem_decisao = [p.item for p in PENDENCIAS
                   if p.grupo == DECISAO and not p.decisao]
    if sem_decisao:
        print("ERRO: item no grupo de decisão sem a decisão escrita: "
              f"{sem_decisao}", file=sys.stderr)
        return 2
    if not DEFEITOS or not PENDENCIAS:
        print("ERRO: tabela vazia — o gerador não deve produzir documento "
              "vazio em silêncio.", file=sys.stderr)
        return 2
    prosa = _conferir_prosa()
    if prosa:
        print("ERRO: o texto do gerador afirma o que a tabela já não "
              "sustenta. Reescreva o parágrafo, não a guarda:", file=sys.stderr)
        for e in prosa:
            print(f"  - {e}", file=sys.stderr)
        return 2
    commits = _conferir_commits()
    if commits:
        print("ERRO: procedência que não confere com o repositório:",
              file=sys.stderr)
        for e in commits:
            print(f"  - {e}", file=sys.stderr)
        return 2

    divergiu = False
    for rel, gerar in SAIDAS.items():
        destino = RAIZ / rel
        novo = gerar()
        if args.conferir:
            atual = destino.read_text(encoding="utf-8") if destino.exists() else ""
            if atual != novo:
                print(f"DIVERGE: {rel} não corresponde aos dados do script.",
                      file=sys.stderr)
                divergiu = True
            else:
                print(f"  ok  {rel}")
        else:
            # newline="\n": sem isto o Windows grava CRLF, e o arquivo gerado
            # passa a depender da máquina que o gerou.
            with open(destino, "w", encoding="utf-8", newline="\n") as f:
                f.write(novo)
            print(f"  gravado  {rel}  ({len(novo.splitlines())} linhas)")

    if args.conferir and divergiu:
        print("\nRegenere com: python scripts/consolidar_registro.py",
              file=sys.stderr)
        return 1
    if args.conferir:
        print(f"\nOK — {len(_contados())} defeitos "
              f"(+{len(DEFEITOS) - len(_contados())} fora da contagem), "
              f"{len(_pendencias_contadas())} pendências.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


