# Auditoria técnica de 31/10/2026

> **O que é:** uma auditoria de código, arquitetura e backlog pedida pelo autor em 31/10, feita
> lendo o código da branch `develop` daquele dia. Cada achado foi conferido no código, com
> arquivo e linha; o que não pôde ser conferido daqui está marcado.
> **O que NÃO é:** uma medição. Nada do firmware rodou na placa; os achados de firmware são
> **latentes** (o código faz isso, e ninguém viu acontecer).
> **Onde cada achado vive agora:** como item do backlog (`docs/BACKLOG-COMPLETO.md`), com o ID na
> tabela abaixo. Este arquivo é o registro da auditoria; o estado de cada item é o do backlog.
> **A triagem do backlog (Seção 4) é PROPOSTA:** nenhum item existente foi removido nem
> rebaixado. Cada linha espera decisão do autor.

## 1. Achados

| # | Sev. | Onde | O problema | Item |
|---|---|---|---|---|
| A1 | Alta, latente — ✅ corrigido 01/11 | `firmware/sketch.ino:308` e `:402` | A medição avisa o envio (`xTaskNotifyGive`, 308) antes de o envio ligar `wifi_ativo` (402). Na janela, a medição vê o Wi-Fi desligado e chama `esp_light_sleep_start()` (299), que para os dois núcleos e o rádio durante o `WiFi.begin()`. | `FW-09` |
| A2 | Alta | `sleep_data`, todas as migrações | Não há restrição de unicidade nem `on conflict`. O firmware reenvia o que não foi confirmado; se o servidor gravou e a resposta se perdeu (timeout, cold start), a época vira duas linhas. Em `features_noite.derivar_noite`, a duplicata gera `d_angulo = 0` artificial e puxa o `g_ref`. | `DATA-08` |
| A3 | Média | `web-app/database.py:123` (`validar_token_de_usuario`) | Toda exceção vira `None` e a rota responde 401; o frontend trata 401 como sessão morta e faz logout. Uma falha momentânea do Supabase Auth desloga o usuário. Custo extra: uma chamada remota ao Auth por requisição. | `AUTH-08` |
| A4 | Média | `web-app/routes.py:589`, `:627`, `:640` | Exceção interna vira `400` com `str(e)` no corpo. Para o firmware, 400 é recusa definitiva: a leitura sai da fila. Um bug do servidor apaga dado; e o texto da exceção vaza ao cliente. | `API-04` |
| A5 | Média, segurança | `firmware/sketch.ino:367` (e os outros sketches) | `setInsecure()`: o TLS não confere o certificado. Numa rede comprometida, o `X-Device-Token` é capturável, e com ele se injetam noites falsas na conta do dono. Não havia item. | `SEC-15` |
| A6 | Média | `web-app/database.py` e a Vercel | A ingestão rodava com a `service_role`: a `SUPABASE_INGESTAO_KEY` não estava configurada — e, ao configurá-la, o gateway a recusava. | `SEC-14` ✅ (01/11) |
| A7 | Baixa | `web-app/database.py:407` | Banco fora do ar responde `401 device nao autorizado`. Sem perda (o firmware recua no 401), mas o diagnóstico engana. | `AUTH-08` |
| A8 | Baixa, latente | `firmware/sketch.ino`, `tarefa_de_medicao` | O sono conta a partir do fim do processamento: o intervalo real é trabalho + ~1,7 s (o apagamento de um setor da flash vai a 400 ms pela folha). ~2,2 s contra 3,09 s de FIFO no pior oscilador: há margem, e ela encolhe à toa. | `FW-10` |
| A9 | Baixa | `frontend/src/contexts/AuthContext.tsx:53` | O 401 limpa a sessão no React e não no Supabase: ao recarregar, a sessão volta e repete o 401. | `AUTH-08` |
| A10 | Baixa | `firmware/sketch.ino:138` | `contadores` escritos pelos dois núcleos sem trava; só o log fica inconsistente. | `FW-10` |

**Consistência entre módulos (conferida):** contrato 2.7.0, validação de `f`/`g`/`fs`, colunas da
010 e `GET /api/features` batem entre si e com os vetores dourados; `ts` com resolução de segundo
passa pela tolerância de futuro de 5 min; `fs = 32` está em `(0, 200]`.

## 2. Correções propostas

- **A1 (`FW-09`):** quem avisa liga a flag; o envio a desliga se decidir não tentar.
  ```cpp
  if (agora_us >= proximo_envio_us && !wifi_ativo && tarefa_envio) {
    wifi_ativo = true;                 // antes do aviso: fecha a janela
    xTaskNotifyGive(tarefa_envio);
  }
  // envio: if (!fila_ok || !reconexao.deve_tentar(..)) { wifi_ativo = false; continue; }
  ```
- **A2 (`DATA-08`):** migração 011 com índice único parcial, e as duas funções de gravação com
  `on conflict ... do nothing` devolvendo o id existente — a duplicata conta como aceita no lote,
  que é o que o firmware precisa saber. Leitura sem `ts` não deduplica: declarar.
  ```sql
  create unique index if not exists sleep_data_epoca_unica
    on public.sleep_data (device_id, captured_at, epoca_segundos)
    where captured_at is not null;
  ```
- **A3, A7, A9 (`AUTH-08`):** 401 só quando o serviço recusa a credencial; exceção do Auth ou do
  banco vira 503, que o frontend não trata como logout. Opcional, e corta a latência: validar o
  JWT localmente pelo JWKS do projeto. No frontend, o callback do 401 chama também
  `supabase.auth.signOut({ scope: "local" })`.
- **A4 (`API-04`):** `logger.exception(...)` e `500` genérico; no lote, exceção num item vira
  **pendente**, não rejeitada.
- **A5 (`SEC-15`):** `setCACertBundle` com o pacote de certificados do ESP-IDF, ou a CA raiz da
  cadeia da Vercel. Validar na placa.
- **A8, A10 (`FW-10`):** sono pelo prazo absoluto (`prazo += intervalo; dormir(prazo − agora)`);
  `std::atomic<uint32_t>` nos contadores.

## 3. Parecer arquitetural

1. **O maior risco é o firmware sem placa.** Cerca de 2 000 linhas de C2, fila e envio testadas
   só no host, e as três hipóteses físicas (FIFO por I2C, sono leve, taxa real) nunca rodaram.
   Recomendação: parar o firmware até a bancada.
2. **O processo de documentação está grande demais para o tamanho do projeto.** O
   `consolidar_registro.py` tem mais de 3 300 linhas, gera prosa e guarda a prosa; o mesmo estado
   vive em cinco lugares (backlog, pendências, `CLAUDE.md`, READMEs, diagramas). Foi daí que
   vieram a X.7 que afirmava captcha, os diagramas desatualizados e o `DOC-13`. Recomendação:
   menos cópias de estado, em vez de mais guardas.
3. **Verificação forte por dentro, fraca na ponta.** Mutação em quase tudo, nenhum teste de ponta a
   ponta com login — o `AUTH-07` ficou dois dias em produção. Um teste de fumaça pós-deploy com
   conta de teste resolveria, e depende do `INFRA-02`.
4. **Operação sem visibilidade:** sem rastreamento de erro, e o monitor do `INFRA-03` só olha o
   `/health`.
5. **Dois caminhos de ingestão** (`/api/data` e `/api/data/lote`) com a mesma regra; a extração
   para `_gravar_leitura` foi o acerto. Decidir depois do `VIA-01` se o `envio-continuo` sai.
6. **Complexidade justificada:** a fila na flash, o CRC e a montagem depois de corte de energia
   são o mínimo correto para uma noite que sobrevive a reset.

## 4. Triagem do backlog — PROPOSTA, aguardando decisão do autor

Base: os 68 itens abertos de 31/10. Nada abaixo foi aplicado.

**Manter (na ordem):** Etapa 0 → `FW-05` + `FW-07` (c) + `FW-08` (c) + `ARQ-01` (c) → `CAL-01`
→ `VIA-01` → `VIA-02` → `VAL-01`; `RQ-01` e `HW-02` (com o VCC do GY-521); `INFRA-02`
(**subir de prioridade**: destrava o teste de login de ponta a ponta); `LGPD-01`, `LGPD-02`,
`LGPD-03`, `DOC-06b`, `REQ-01`, `CALC-02`, `CALC-03`, `ESC-01`, `UI-18`, `SEC-13`; em L2,
`HW-04`, `CALC-05`, `VAL-02`, `DASH-04`, `ML-09`, `ML-10`, `ML-INF`, `ML-12` (c).

**Ajustar / redefinir:**

| Item | Proposta | Por quê |
|---|---|---|
| `CALC-01` | Refazer para a C2: sono leve, drenagem a 1,7 s, Wi-Fi a cada 10 min, flash | O modelo de Deep Sleep e WoM não existe mais |
| `CALC-04` | Tirar o pull-down de 10 kΩ; centrar em pull-ups do I2C, 3V3 × 5 V no VCC, níveis lógicos | O resistor era andaime do Wokwi; a questão real é a do `DIAG-02` |
| `CAL-02` | Fundir no `CAL-01` | Mesma sessão de bancada, já com o filtro de 21 Hz |
| `HW-01` | Fechar como feito pelo `DIAG-02`; o resto vai para o `HW-02` | O esquemático já separou andaime de produto |
| `HW-06` | Reduzir a fotos e montagem | O esquema existe (`DIAG-02`) |
| `LGPD-05`, `LGPD-06` | **Remover o campo idade** | Hoje só decide um texto; tirá-lo elimina os dois itens |
| `DATA-06` | Para L2, depois do `VIA-02` | Só faz sentido com o limiar medido do celular |
| `ML-06a`, `ML-06b` | Decidir se a defesa precisa; se não, pós-banca | Melhoram a variância, não bloqueiam nada |
| `DOC-13` | Apagar o resumo de estado do backlog, ou conferi-lo por script | Texto de estado escrito à mão envelhece sempre |
| `SEC-09` | Fechar como "declarado na X.7" | Não há código a escrever; a correção é de arquitetura, fora do escopo |

**Remover / deprecar:**

- **Superados:** `FW-02` (Deep Sleep; a C2 usa sono leve — está no `FW-07` (c)); `FW-04` (o sketch
  da C2 não depende do Wokwi); `FW-03` (payload e lote fazem o empacotamento); `DATA-02`
  (decidido, 30 s); `FW-01` (o rótulo é limiar no payload; a classificação é do `ML-INF`);
  `HW-03` (deixou de ser pré-requisito com a C2); `SEC-08` (decidido); `SEC-10` (só existe com a
  confirmação de e-mail ligada, e ela não está); `UI-19` (as duas ocorrências foram corrigidas);
  `GIT-03` (resíduo operacional); `DOC-09` (o diário é prática contínua, não item).
- **Prematuros para um TCC:** `APP-02`, `APP-03`, `APP-04`, `APP-05`, `APP-09`, `UI-14`, `UI-15`,
  `UI-20`, `PWA-01`, `AUTH-06`, `ARQ-02`, `ML-08`; `HW-07` fica como contingência do `VIA-01`.
- **Baratos, quando sobrar tempo:** `CI-02` (linter), `GIT-05`.

## 5. O que esta auditoria não cobriu

- Nada rodou na placa; logs de produção só foram lidos pelo autor, por captura de tela.
- `ml/` e `scripts/` não foram auditados em profundidade (o bloco de ML está fechado e tem
  suíte e mutação próprias).
- O frontend foi lido nos caminhos de autenticação e de chamada à API, não tela a tela.
