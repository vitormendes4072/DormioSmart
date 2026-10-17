# Nucleo do firmware Dormio -- build de HOST, com g++.
#
# Nao ha arduino-cli nem platformio aqui, e para esta camada nao faz falta: o
# nucleo nao inclui Arduino.h nem WiFi.h em lugar nenhum, entao compila e roda
# em qualquer maquina. O que se verifica aqui e logica de tempo, de buffer e
# de contrato -- e isso se verifica melhor em segundos no host do que em oito
# horas de espera na placa.
#
#   make          compila e roda a suite
#   make testes   so a suite
#   make capacidade  a medicao de capacidade do buffer
#   make limpar

CXX ?= g++

# -Wconversion e -Wsign-conversion sao caros de satisfazer e valem a pena numa
# camada que so manipula largura de bits e aritmetica de tempo: e exatamente
# onde uma promocao silenciosa vira um bug que so aparece as 3 da manha.
CXXFLAGS := -std=c++11 -Wall -Wextra -Wpedantic -Wshadow -O2 -g \
            -fno-exceptions -fno-rtti

FONTES := epoca.cpp payload.cpp
CABECALHOS := epoca.h buffer.h cadencia.h reconexao.h relogio.h payload.h

.PHONY: todos testes capacidade limpar

todos: testes

testes: bin/testes
	@./bin/testes

capacidade: bin/capacidade
	@./bin/capacidade

bin/testes: testes/testes.cpp $(FONTES) $(CABECALHOS)
	@mkdir -p bin
	$(CXX) $(CXXFLAGS) -I. testes/testes.cpp $(FONTES) -o $@

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
