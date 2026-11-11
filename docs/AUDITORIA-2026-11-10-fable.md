# Auditoria técnica de 10/11/2026 (Fable 5.2)

> **O que é:** auditoria independente pedida pelo autor, sobre `develop` em `62c36a4`.
> Somente leitura e testes locais: nenhum arquivo versionado foi editado, nada foi commitado,
> e a produção não foi tocada.
> **Máquina:** Windows 11; Python 3.13.5 (backend e scripts); Python 3.11.9 (`ml/.venv`);
> Node 24.11.0; Docker com `postgres:17` (17.11) e `gcc:13`.
> **Convenção:** "executado" = rodei e vi o resultado; "lido" = li o código ou o documento, e
> a afirmação é hipótese até alguém rodar.
> **Onde cada achado vive agora** (✏️ 10/11, versionado a pedido do autor): como item do backlog, e o
> estado de cada um é o do backlog, não o deste arquivo. AUD-01 → `APP-10` ✅ · AUD-02 e AUD-03 →
> `SEC-18` · AUD-04 → `LGPD-11` · AUD-05 → `REL-01` (com o `LGPD-03`) · AUD-06 → `CI-09` · AUD-07 →
> `CI-10` · AUD-08 → corrigido no `CLAUDE.md` e no `UI-15` · AUD-09 → `CI-11` · AUD-10 → `SEC-19` ·
> AUD-11 → `DATA-14` · AUD-12 → `SEC-20`. A pergunta sobre `last_sign_in_at` (seção 7) foi para o
> `REL-01`, antes do `LGPD-09`.

## 1. Resumo executivo

Os cinco achados mais graves:

1. **AUD-01 (alta):** na latência medida da produção, um lote de 60 épocas do app grava 13 e
   devolve 47 como pendentes; o app para com mensagem de erro. Uma noite real (960 épocas)
   pede cerca de 74 toques em "enviar". Não há perda de dado.
2. **AUD-02 (média):** a validação de entrada vive só no Flask. A função
   `registrar_leitura_da_sessao` aceita chamada direta de qualquer usuário logado, sem
   validar nada: gravei `NaN`, `Infinity`, data de 2099 e época −5. Só afeta a própria conta.
3. **AUD-04 (média):** a política de privacidade não descreve o app nativo. Ela diz que o
   celular só coleta com a tela de coleta aberta; o app coleta a noite toda, com a tela apagada.
4. **AUD-05 (média):** o próximo release publica `GET /api/inferencia`, e a política ainda diz
   que nada infere. O `LGPD-03` registra o problema, mas nada o liga ao release.
5. **AUD-06 (baixa):** o CI não roda nenhum teste do app Android.

Veredito por camada:

| Camada | Veredito |
|---|---|
| Banco e RLS | Isolamento entre contas sólido (todas as tentativas cruzadas recusadas). Falta validação no banco (AUD-02, AUD-03). |
| Backend | Códigos de erro e autenticação corretos. O caminho por sessão é lento por leitura (AUD-01). |
| Frontend | Sem achado: pacote sem segredo, modo demonstração inalcançável na produção. |
| App Android | Serviço, trava e arquivo bem construídos (lido). O envio de uma noite inteira não escala (AUD-01). |
| Firmware | Sem achado: todas as contagens e mutações conferem. |
| ML | Sem achado: as métricas citadas batem com os artefatos; não retreinei nada. |
| LGPD | Política atrás do código em dois pontos (AUD-04, AUD-05); `LGPD-09` segue pendente. |
| Documentação | Divergências pequenas de contagem (AUD-08). |
| Processo | Lacunas de CI (AUD-06, AUD-07) e dois harnesses frágeis (AUD-09). |

## 2. Achados

| ID | Camada | Sev. | Título | Evidência | Tipo | No backlog? |
|---|---|---|---|---|---|---|
| AUD-01 | App / backend | Alta | Lote de 60 não cabe no orçamento de 6 s na latência da produção, e o app para | `web-app/database.py:236` e `:415`; `web-app/lote.py:49`; `frontend/src/lib/envioDaNoite.ts:91`; controle da seção 4.1 | Executado | Não |
| AUD-02 | Banco | Média | Validação só no Flask: a função de gravação por sessão aceita qualquer valor por chamada direta | `web-app/migrations/014_id_da_leitura_uuid.sql` (função `registrar_leitura_da_sessao`); controle da seção 4.2 | Executado | Não |
| AUD-03 | Banco | Baixa | Sem limite de tamanho nem de quantidade em dispositivos por chamada direta | `parear_dispositivo` (007); policy `devices_update_own`; controle da seção 4.3 | Executado | Não |
| AUD-04 | LGPD | Média | A política de privacidade não descreve o app nativo | `docs/POLITICA-DE-PRIVACIDADE.md:151-154` e `:156-160`; `ServicoDaNoite.java`; `AndroidManifest.xml:4-6` | Lido | Não (a linha do `APP-02` não cita a política) |
| AUD-05 | LGPD / release | Média | O próximo release publica a inferência com a política dizendo que nada infere | `web-app/routes.py:212`; `docs/POLITICA-DE-PRIVACIDADE.md:170-171`; `origin/main` em `5fa9ab6` | Lido | Sim, `LGPD-03` e `DASH-04`: registro incompleto |
| AUD-06 | Processo | Baixa | O CI não roda nenhum teste do app Android | `.github/workflows/ci.yml` (nenhuma linha com `gradle` ou `android` além de um comentário) | Lido | Não |
| AUD-07 | Processo | Baixa | O Python do CI não é o da produção | `ci.yml:37` (3.11), `ci.yml:225` (3.10); log da Vercel de 09/11 (`runtime=python3.12`) | Lido | Não |
| AUD-08 | Documentação | Baixa | Três contagens dos documentos não batem com a execução | Seção 3 | Executado | — |
| AUD-09 | Processo | Baixa | Dois harnesses de mutação quebram por causa do ambiente, com mensagem enganosa | `web-app/tests/rls/conftest.py:213-221`; `ml/testes/verificar_vetor_dourado_por_mutacao.py:265-273` | Executado | Não |
| AUD-10 | Backend | Baixa | O código ainda cai para a `service_role` se a chave de ingestão faltar | `web-app/database.py:73-77` | Lido | `SEC-14` fechado: registro incompleto |
| AUD-11 | Dados | Baixa | O campo `t` do app é a temperatura da bateria, e o contrato diz que é a do chip do sensor | `firmware/nucleo/coletor_celular.h:31-32`; `web-app/validacao.py:15-16`; `docs/DATA-CONTRACT.md` (sem a palavra "bateria" nesse sentido) | Lido | Não |
| AUD-12 | Frontend / deploy | Informativa | Sem cabeçalhos de segurança (CSP) no `vercel.json` | `vercel.json` (sem bloco `headers`) | Lido | Não |

### AUD-01: o envio de uma noite inteira não escala

- **O que acontece:** cada leitura do caminho por sessão monta um cliente Supabase novo
  (`cliente_do_usuario` chama `create_client`, `database.py:236`, a partir de `:415`). Isso
  abre uma conexão nova por leitura.
- **A latência medida:** nos logs da Vercel de 09/11, 22:00:51 a 22:00:55 UTC, as 8 chamadas
  a `registrar_leitura_da_sessao` saíram a cada 0,49 s em média.
- **O orçamento:** o lote para aos 6 s (`lote.py:49`) e devolve o resto como pendente.
- **O app:** ao ver pendentes, o laço para e mostra "N épocas ficaram pendentes no servidor.
  Tente de novo em instantes." (`envioDaNoite.ts:91-94`). Ele só tenta sozinho uma vez, ao
  abrir o app.
- **Impacto:** uma noite de 8 h tem 960 épocas. A 13 por tentativa, são cerca de 74
  tentativas manuais. O teste de 8 épocas de 09/11 passou porque 8 cabe nos 6 s.
- **Por que os testes não pegam:** `test_noite_do_app.py` usa um banco falso instantâneo, e os
  lotes de 60 saem todos aceitos (§1 das lições: a verificação recompõe a produção).
- **Sem perda de dado:** as épocas ficam no aparelho, e o reenvio é idempotente (011).
- **Correção proposta, em ordem de custo:**
  1. um cliente por requisição, e não por leitura (reusa a conexão);
  2. o app continua o laço enquanto houver progresso, em vez de parar na primeira pendente;
  3. uma função no banco que receba o lote inteiro numa chamada.

### AUD-02: a validação é contornável por chamada direta

- **O que acontece:** `registrar_leitura_da_sessao` tem `EXECUTE` para `authenticated` e não
  valida o JSON. O endereço do Supabase e a chave anon são públicos por desenho, então quem
  tem conta chama a função sem passar pelo Flask.
- **O que gravei no controle:** `movimento_total = NaN`, `accel_x = Infinity`,
  `accel_y = 1e300`, `temp = −9999`, `status = "<script>"`, `captured_at = 2099`,
  `epoca_segundos = −5`, `amostras = −1`, num dispositivo do tipo `travesseiro`.
- **Volume:** 2 000 leituras numa chamada, em 4,6 s, sem limite.
- **O que não acontece:** não cruza contas. A mesma chamada no dispositivo de outro usuário
  devolve nulo e não grava.
- **Impacto:** a frase "o backend valida antes de persistir" (`CLAUDE.md`, `validacao.py`) não
  vale para este caminho. Uma leitura de 2099 vira "a mais recente" para sempre, e `NaN`
  contamina médias.
- **Correção proposta:** restrições `CHECK` em `sleep_data` (valores finitos, faixas da
  `validacao.py`, `captured_at` não futuro, época de 1 a 3600), ou a validação dentro da função.
- **Não verificado:** o que o painel e a `/api/inferencia` fazem com essas linhas.

### AUD-03: dispositivos sem limite por chamada direta

- `parear_dispositivo` aceitou um nome de 100 000 caracteres, 500 dispositivos numa chamada e
  um `token_hash` escolhido pelo cliente (`"abc"`).
- Um `update` direto em `devices` aceitou nome de 100 000 caracteres e desfez uma revogação.
- O backend limita o nome (`dispositivos.py:61`), mas o banco não.
- **Correção proposta:** `CHECK` de tamanho em `devices.nome` e um teto de dispositivos por conta.

### AUD-04: a política não descreve o app nativo

A política foi escrita para a coleta pelo navegador. O `APP-02` mudou o que acontece:

| A política diz | O app faz |
|---|---|
| O celular coleta "somente enquanto a tela de coleta estiver aberta" (§2.2) | Coleta a noite toda, com a tela apagada, por serviço em primeiro plano |
| No aparelho ficam só a sessão e o tema (§2.3) | Ficam também os arquivos das noites e as anotações (hora de deitar, de dormir, de acordar, despertares, posição) |
| A série de movimento "não é tratada aqui como dado de saúde" (§2.4) | O manifesto do app justifica o `allowBackup="false"` dizendo que as noites "são dado de saúde" |

- **Impacto:** hoje só o autor usa o app. Vira problema real antes de outra pessoa instalar.
- **Não verificado:** se as anotações saem do aparelho. Pela leitura, `envioDaNoite.ts` só envia épocas.

### AUD-05: a inferência chega à produção no próximo release

- `develop` tem `GET /api/inferencia` (sono ou vigília por época, para o dono dos dados).
  `main` ainda não: está em `5fa9ab6`, 33 merges atrás.
- A política diz que nada "pede, guarda ou infere condição de saúde" (§2.4).
- O `LGPD-03` e o `DASH-04` dizem que a **tela** não deve mostrar a inferência antes de a
  política mudar. A **rota** já a entrega a quem chamar a API, com ou sem tela.
- A única trava de release registrada é a do `LGPD-09` (a 013). Falta uma para a inferência.

### AUD-08: contagens que não batem

| Onde | O documento diz | Medido |
|---|---|---|
| `CLAUDE.md`, linha do frontend | 546 testes, **43 arquivos** | 546 testes, **42 arquivos** (`git ls-files` também conta 42) |
| `CLAUDE.md`, linha do firmware | mutação da fila **13/13** | `make mutacao-fila`: **14/14 como esperado** |
| Backlog, `UI-15` | pacote de **876 kB** | **925 kB** (264 kB gzip), mais 199 kB da política |

### AUD-09: harnesses frágeis

- **RLS:** `conftest.py` apaga os papéis com `drop owned by` e `drop role`. O comentário
  (linha 214) diz que `drop owned by` cobre outros bancos do cluster; não cobre. Com um
  segundo banco no mesmo servidor com permissões para esses papéis, os 196 testes dão erro de
  preparação, e a mutação diz "a suíte não passa nem sem sabotagem".
- **Dourado do ML:** com `PYTHONIOENCODING=utf-8` no Windows, o script morre com
  `TypeError: unsupported operand type(s) for +: 'NoneType' and 'str'` (linha 273), porque lê
  a saída do filho sem declarar a codificação. Sem a variável, dá 12/12.

## 3. Suítes executadas

| Suíte | Comando | Resultado | `CLAUDE.md` diz | Bate? |
|---|---|---|---|---|
| Backend | `pytest --ignore=tests/rls` (Python 3.13.5) | 500 passam | 500 | Sim |
| Frontend | `npx vitest run` (Node 24.11; o CI usa 22) | 546 passam, 42 arquivos | 546, 43 arquivos | Não (AUD-08) |
| Tipos e build | `npx tsc --noEmit`; `npx vite build` para pasta temporária | `tsc` limpo; build ok, com o aviso do chunk | idem | Sim |
| RLS | `pytest tests/rls` contra `postgres:17` | 196 passam | 196 | Sim |
| Mutação do RLS | `verificar_por_mutacao.py`, `postgres:17` | 36/36 | 36/36 (medido na 16) | Sim |
| Migrações | `verificar_migracoes.py`, `postgres:17` | 15 estados e a ordem real | 15 estados | Sim |
| ML | `ml/.venv`, `pytest testes` (Python 3.11.9) | 299 passam | 299 | Sim |
| Mutação do dourado | `verificar_vetor_dourado_por_mutacao.py` | 12/12, 1 ponto cego confirmado | 12/12 | Sim |
| Firmware | `make todos` em `gcc:13`, numa cópia | 341 + 157 + 152 + 456 + 84 + 288, 0 falhas | idem | Sim |
| Firmware, demais alvos | `sintaxe`, `capacidade`, `mutacao`, `mutacao-cadeia`, `mutacao-fila`, `mutacao-coletor`, `laco` | todos com código 0; cadeia 29/29; fila 14/14; coletor 12 sabotadores; laço 4/4 | fila 13/13 | Fila não (AUD-08) |
| Documentos | os 7 scripts de `scripts/` | todos OK | todos passam | Sim |
| Dependências | `npm audit --audit-level=high`; `pip-audit -r web-app/requirements.txt` | 0 vulnerabilidades; nenhuma conhecida | — | — |

Duas execuções falharam por causa do meu ambiente, e não do projeto. Estão descritas no AUD-09.

**Não rodei:** os testes do app Android (`gradlew testDebugUnitTest` e os instrumentados).

## 4. Controles positivos

Todos num Postgres 17 descartável ou com banco falso. Nada na árvore real.

### 4.1 Lote com a latência da produção (AUD-01)

`POST /api/data/lote` pelo cliente de teste do Flask, com 60 épocas da fixture do emulador e
a gravação falsa esperando 0,49 s por leitura.

- **Resultado:** `200`, 13 aceitas, 47 pendentes, 0 rejeitadas, em 6,4 s.

### 4.2 Chamada direta à função de gravação (AUD-02)

Esquema montado com as migrações 001 a 015 na ordem da produção; papel `authenticated` com
o `sub` de uma usuária.

| Tentativa | Resultado |
|---|---|
| Leitura com `NaN`, `Infinity`, 2099, época −5 no próprio dispositivo | **Gravou** |
| A mesma leitura no dispositivo de outro usuário | Devolveu nulo, não gravou |
| 2 000 leituras numa chamada | **Gravou**, em 4,6 s |

### 4.3 Acesso direto às tabelas e funções (AUD-03 e o isolamento)

| Tentativa, como usuária logada | Resultado |
|---|---|
| Trocar o dono de um dispositivo para outro usuário | Recusado (RLS) |
| `insert` direto em `sleep_data` | Recusado (RLS) |
| `update` em `sleep_data` | 0 linhas (sem policy de update) |
| Ler `device_tokens` | Recusado (sem permissão) |
| Perfil com idade 5; nome de 201 caracteres | Recusados (`CHECK`) |
| Chamar `_eliminar_titular` de outro usuário; chamar `expurgar_contas_inativas` | Recusados (sem permissão) |
| Parear com nome de 100 000 caracteres; 500 dispositivos; hash `"abc"` | **Aceitos** |
| Renomear dispositivo para 100 000 caracteres; desfazer a revogação | **Aceitos** |

### 4.4 Catálogo de segurança

Lido do catálogo do banco montado: RLS ligado nas 4 tabelas; as 5 funções `SECURITY DEFINER`
com `search_path = ''`; `anon` sem `EXECUTE` em nenhuma função; `_eliminar_titular` e
`expurgar_contas_inativas` só para `postgres`. Bate com o que o autor colou da produção em 09/11.

## 5. Consultas para o autor rodar na produção (só leitura)

**5.1 Leituras que não passariam na validação** (AUD-02). Esperado: tudo zero.

```sql
select
  count(*) filter (where movimento_total in ('NaN','Infinity','-Infinity')
                      or accel_x in ('NaN','Infinity','-Infinity')) as nao_finitas,
  count(*) filter (where captured_at > now() + interval '5 minutes') as no_futuro,
  count(*) filter (where epoca_segundos is not null
                     and (epoca_segundos < 1 or epoca_segundos > 3600)) as epoca_fora,
  count(*) filter (where movimento_total < 0 or movimento_total > 175) as total_fora,
  count(*) filter (where status is not null
                     and status not in ('Repouso','Movimento')) as status_livre
from public.sleep_data;
```

**5.2 Quantas contas a 013 apagaria na primeira execução** (antes do `LGPD-09`). Esperado: 0.

```sql
select count(*) as contas_que_sairiam
from auth.users u
where greatest(u.created_at, u.last_sign_in_at,
               (select max(s.created_at) from public.sleep_data s where s.user_id = u.id))
      < now() - interval '12 months';
```

**5.3 Dispositivos por conta e maior nome** (AUD-03). Esperado: poucos por conta, nome curto.

```sql
select max(n) as max_dispositivos_por_conta, max(maior_nome) as maior_nome
from (select user_id, count(*) as n, max(length(nome)) as maior_nome
        from public.devices group by user_id) t;
```

Fora do banco: conferir no painel da Vercel a versão do Python do projeto (AUD-07) e que a
`SUPABASE_SERVICE_ROLE_KEY` continua ausente (AUD-10).

## 6. A auditoria de 31/10 e o estado de hoje

| # | Item | Estado declarado | O que conferi hoje |
|---|---|---|---|
| A1 | `FW-09` | Corrigido | `make laco` 4/4 (executado). Na placa: nunca rodou. |
| A2 | `DATA-08` | Corrigido | Suíte de idempotência passa no Postgres 17 (executado). |
| A3, A7 | `AUTH-08` | Corrigido | `INDISPONIVEL` distinto de recusa em `database.py` (lido); 500 testes passam. |
| A4 | `API-04` | Corrigido | `_resposta_de_falha` responde 500 sem o texto da exceção (lido). |
| A5 | `SEC-15` | Corrigido no código | `setCACert` em `sketch.ino:428` e no `envio-continuo`; nenhum `setInsecure` fora dos stubs (lido). Handshake na placa: pendente. |
| A6 | `SEC-14` | Fechado | O código prefere a chave de ingestão, mas mantém a queda para a `service_role` (AUD-10). |
| A8, A10 | `FW-10` | Corrigido | `std::atomic` nos contadores (lido); `make laco` (executado). |
| A9 | `AUTH-08` | Corrigido | `signOut({ scope: "local" })` em `AuthContext.tsx:60` (lido). |

Do parecer arquitetural de 31/10, dois pontos continuam valendo, e os defeitos de 09/11 os confirmam:

- **"Verificação forte por dentro, fraca na ponta":** o `DATA-10`, o `DATA-12` e o AUD-01 só
  aparecem com a produção ou com a latência dela. O `INFRA-02` segue aberto.
- **"Operação sem visibilidade":** o `DATA-10` foi achado lendo o log da Vercel à mão.

## 7. Perguntas em aberto e o que não verifiquei

- **Testes do app Android:** não rodei. Não sei se os 20 de JVM passam hoje.
- **Latência do caminho por token (firmware):** não medida. Ele reusa um cliente, então deve
  ser mais rápido; se cada leitura passar de 0,1 s, o lote de 60 também estoura os 6 s.
- **`last_sign_in_at` e a 013:** a função de expurgo usa esse campo. Não conferi se o Supabase
  o atualiza quando a sessão é só renovada. Se não atualizar, quem consulta o painel por 12
  meses sem novo login e sem leitura nova seria apagado.
- **ML:** conferi números contra os artefatos versionados. Não retreinei, nem tenho os dados
  brutos para refazer as métricas.
- **Produção:** nada foi conferido lá hoje. As afirmações sobre ela vêm dos resultados que o
  autor colou em 09/11 e 10/11 e dos logs lidos em 09/11.
- **Histórico do git:** procurei padrões de chave nos arquivos versionados e em todos os
  commits (JWT, chave privada, chaves de serviço) e não achei nada. Não li o conteúdo de `.env`.
- **A noite real (etapa 5 do `APP-02`):** o comportamento do Moto E7 por 8 h não é auditável daqui.
