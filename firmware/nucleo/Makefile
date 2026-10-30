# Nucleo do firmware Dormio -- build de HOST, com g++.
#
# Nao ha arduino-cli nem platformio aqui, e para esta camada nao faz falta: o
# nucleo nao inclui Arduino.h nem WiFi.h em lugar nenhum, entao compila e roda
# em qualquer maquina. O que se verifica aqui e logica de tempo, de buffer e
# de contrato -- e isso se verifica melhor em segundos no host do que em oito
# horas de espera na placa.
#
#   make          compila e roda a suite + a paridade do vetor dourado
#   make testes   so a suite do nucleo
#   make dourado  so a paridade contra ml/testes/vetor_dourado.json
#   make c2       as pecas da arquitetura C2 (FIFO, anti-aliasing, cadeia, lote)
#   make cadeia   a cadeia C2 inteira contra ml/testes/vetor_dourado_cadeia_c2.json
#   make mutacao-cadeia  sabota a cadeia C2 e exige que o dourado dela ACUSE
#   make mutacao  sabota o nucleo e exige que a paridade ACUSE
#   make capacidade  a medicao de capacidade do buffer
#   make limpar

CXX ?= g++

# -Wconversion e -Wsign-conversion sao caros de satisfazer e valem a pena numa
# camada que so manipula largura de bits e aritmetica de tempo: e exatamente
# onde uma promocao silenciosa vira um bug que so aparece as 3 da manha.
CXXFLAGS := -std=c++11 -Wall -Wextra -Wpedantic -Wshadow -O2 -g \
            -fno-exceptions -fno-rtti

FONTES := epoca.cpp payload.cpp filtro.cpp caracteristicas.cpp \
          fifo_mpu.cpp reamostragem.cpp cadeia_c2.cpp lote.cpp
CABECALHOS := epoca.h buffer.h cadencia.h reconexao.h relogio.h payload.h \
              filtro.h caracteristicas.h fifo_mpu.h reamostragem.h cadeia_c2.h lote.h

# O leitor de JSON NAO esta em FONTES de proposito: ele e instrumento de
# teste, mora em `testes/` e nao deve embarcar. Se um dia aparecer em FONTES,
# o nucleo passou a carregar um parser que nenhum sketch usa.
FONTES_TESTE := testes/leitor_json.cpp
CABECALHOS_TESTE := testes/leitor_json.h

# O dourado da fronteira A. E gravado pelo pytest do `ml/` e conferido aqui:
# os dois lados leem o MESMO arquivo, sem etapa de transcodificacao no meio.
DOURADO := ../../ml/testes/vetor_dourado.json
DOURADO_CADEIA := ../../ml/testes/vetor_dourado_cadeia_c2.json

.PHONY: todos testes dourado c2 cadeia mutacao mutacao-cadeia capacidade limpar

todos: testes dourado c2 cadeia

testes: bin/testes
	@./bin/testes

# A paridade Python<->C++. Separada de `testes` porque ela depende de um
# artefato de FORA do firmware (o JSON do ml/): se o dourado nao estiver
# gravado, o alvo falha com instrucao em vez de falhar misteriosamente.
dourado: bin/testes_dourado
	@test -f $(DOURADO) || { \
	  echo "  ERRO: $(DOURADO) nao existe."; \
	  echo "  O dourado e gravado pela suite do ml/. Rode:"; \
	  echo "    cd ../../ml && python -m pytest testes/test_vetor_dourado.py"; \
	  exit 1; }
	@./bin/testes_dourado $(DOURADO)

# Quem testa o teste de paridade. NAO entra em `todos` porque recompila o
# nucleo 15 vezes (~20 s) -- e verificacao de instrumento, nao de codigo, e
# roda quando o instrumento muda.
mutacao: bin/testes_dourado
	@sh testes/verificar_paridade_por_mutacao.sh

capacidade: bin/capacidade
	@./bin/capacidade

c2: bin/testes_c2
	@./bin/testes_c2

# Mesma regra do `dourado`: o arquivo vem do ml/, e a falta dele vira
# instrucao em vez de erro misterioso.
cadeia: bin/testes_cadeia_c2
	@test -f $(DOURADO_CADEIA) || { \
	  echo "  ERRO: $(DOURADO_CADEIA) nao existe."; \
	  echo "  Rode: cd ../../ml && python -m pytest testes/test_dourado_cadeia_c2.py"; \
	  exit 1; }
	@./bin/testes_cadeia_c2 $(DOURADO_CADEIA)

# Fora de `todos` pelo mesmo motivo do `mutacao`: recompila a cadeia uma vez
# por sabotador.
mutacao-cadeia:
	@sh testes/verificar_cadeia_por_mutacao.sh

bin/testes: testes/testes.cpp $(FONTES) $(CABECALHOS)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. testes/testes.cpp $(FONTES) -o $@

bin/testes_dourado: testes/testes_dourado.cpp $(FONTES) $(CABECALHOS) \
                    $(FONTES_TESTE) $(CABECALHOS_TESTE)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. testes/testes_dourado.cpp $(FONTES) $(FONTES_TESTE) -o $@

bin/testes_c2: testes/testes_c2.cpp $(FONTES) $(CABECALHOS)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. testes/testes_c2.cpp $(FONTES) -o $@

bin/testes_cadeia_c2: testes/testes_cadeia_c2.cpp $(FONTES) $(CABECALHOS) \
                      $(FONTES_TESTE) $(CABECALHOS_TESTE)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. testes/testes_cadeia_c2.cpp $(FONTES) $(FONTES_TESTE) -o $@

bin/capacidade: capacidade.cpp $(FONTES) $(CABECALHOS)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. capacidade.cpp $(FONTES) -o $@

limpar:
	rm -rf bin

# ── Verificacao de sintaxe dos .ino ───────────────────────────────────────
#
# Nao ha arduino-cli aqui, entao os sketches nao sao compilados de verdade.
# Com stubs minimos do Arduino, o g++ ainda consegue abrir o .ino e conferir
# sintaxe, tipos e formatos de printf.
#
# Isto nao e luxo: ate 2026-09-22 o `envio-continuo.ino` versionado tinha duas
# strings com quebra de linha literal no meio, e portanto NAO COMPILAVA em
# maquina nenhuma. Ninguem percebeu porque nada no repositorio tentava
# compilar. Agora tenta.

STUBS := testes/stubs-arduino

.PHONY: sintaxe

# `secrets.h` e ignorado pelo git de proposito (credencial nao se versiona), e
# o sketch o inclui. Para a verificacao de sintaxe rodar em qualquer clone,
# geramos um falso em bin/ e o colocamos por ULTIMO no caminho de include: se
# houver um secrets.h de verdade na pasta do sketch, e ele que vence.
bin/secrets-falso/secrets.h:
	@mkdir -p bin/secrets-falso
	@printf '// Gerado pelo Makefile. Nao e credencial: so existe para o\n' > $@
	@printf '// `make sintaxe` rodar sem um secrets.h de verdade.\n' >> $@
	@printf '#define WIFI_SSID "x"\n#define WIFI_PASSWORD "y"\n#define DEVICE_TOKEN "z"\n' >> $@

# A LISTA E A PARTE FRAGIL DESTE ALVO, e ja falhou por isso.
#
# De 22/09 a 16/10 ela tinha dois dos quatro sketches versionados. Os outros
# dois -- `caracterizacao.ino` e `diagnostico-i2c.ino` -- nao estavam aqui, e
# na primeira vez que foram compilados (16/10) os DOIS tinham exatamente o
# defeito que este alvo nasceu para pegar: string com quebra de linha literal
# no meio. Ficaram semanas no repositorio sem compilar em maquina nenhuma.
#
# A licao nao e "conferir sintaxe": e que uma verificacao vale pelo seu
# ALCANCE, e lista escrita a mao e alcance que silenciosamente para de
# acompanhar a pasta. Por isso a lista agora sai de um `wildcard`: sketch novo
# entra sozinho. Se o novo nao compilar com os stubs, o alvo reclama -- que e
# o resultado certo, e e mais barato do que descobrir na placa.
SKETCHES := $(wildcard ../*.ino) $(wildcard ../*/*.ino)

sintaxe: bin/secrets-falso/secrets.h
	@echo "verificando sintaxe dos sketches (stubs do Arduino, sem hardware)..."
	@test -n "$(SKETCHES)" || { echo "  ERRO: nenhum .ino encontrado -- o wildcard parou de casar."; exit 1; }
	@for s in $(SKETCHES); do \
	  echo "  $$s"; \
	  $(CXX) -std=c++11 -fsyntax-only -Wall -Wextra -x c++ \
	    -I$(STUBS) -Ibin/secrets-falso -include Arduino.h "$$s" || exit 1; \
	done
	@echo "  ok -- os $(words $(SKETCHES)) sketches compilam."
