package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.util.Collections;
import java.util.HashMap;
import java.util.Map;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** As anotacoes da noite e o corte por calor (APP-02, etapa 4). Roda na JVM. */
public class NotasDaNoiteTest {

    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static Map<String, String> m(String... kv) {
        final Map<String, String> r = new HashMap<>();
        for (int i = 0; i < kv.length; i += 2) r.put(kv[i], kv[i + 1]);
        return r;
    }

    @Test
    public void gravaJuntaELeNaOrdemDasChaves() throws IOException {
        final File pasta = tmp.getRoot();
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("posicao", "fronha"));
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("deitou", "23:10", "acordou", "06:40"));
        final Map<String, String> l = NotasDaNoite.ler(pasta, "noite-1.jsonl");
        assertEquals("fronha", l.get("posicao"));
        assertEquals("23:10", l.get("deitou"));
        assertEquals("06:40", l.get("acordou"));
        assertEquals(java.util.Arrays.asList("posicao", "deitou", "acordou"), new java.util.ArrayList<>(l.keySet()));
    }

    @Test
    public void umaNoiteNaoMisturaComOutra() throws IOException {
        final File pasta = tmp.getRoot();
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("posicao", "fronha"));
        NotasDaNoite.salvar(pasta, "noite-2.jsonl", m("posicao", "colchao"));
        assertEquals("fronha", NotasDaNoite.ler(pasta, "noite-1.jsonl").get("posicao"));
        assertEquals("colchao", NotasDaNoite.ler(pasta, "noite-2.jsonl").get("posicao"));
    }

    @Test
    public void valorVazioApagaAChave() throws IOException {
        final File pasta = tmp.getRoot();
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("observacao", "acordei com barulho"));
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("observacao", "  "));
        assertFalse(NotasDaNoite.ler(pasta, "noite-1.jsonl").containsKey("observacao"));
    }

    @Test
    public void chaveDesconhecidaPosicaoInvalidaOuTextoLongoNaoGravamNada() throws IOException {
        final File pasta = tmp.getRoot();
        NotasDaNoite.salvar(pasta, "noite-1.jsonl", m("posicao", "fronha"));
        final Map<String, String>[] ruins = new Map[] {
            m("senha", "x"),
            m("posicao", "bolso"),
            m("observacao", new String(new char[NotasDaNoite.TAMANHO_MAXIMO + 1]).replace('\0', 'a')),
            m("deitou", "23:00", "token", "y"),
        };
        for (Map<String, String> r : ruins) {
            try {
                NotasDaNoite.salvar(pasta, "noite-1.jsonl", r);
                fail("devia recusar " + r.keySet());
            } catch (IllegalArgumentException esperado) {
                // ok
            }
        }
        assertEquals(Collections.singletonMap("posicao", "fronha"), NotasDaNoite.ler(pasta, "noite-1.jsonl"));
    }

    @Test
    public void nomeDeNoiteForaDoPadraoERecusado() throws IOException {
        for (String ruim : new String[] {"../estado.properties", "noite-1.jsonl/../x", "outra.jsonl", "noite-1.txt"}) {
            try {
                NotasDaNoite.ler(tmp.getRoot(), ruim);
                fail("devia recusar " + ruim);
            } catch (IllegalArgumentException esperado) {
                // ok
            }
        }
    }

    @Test
    public void asNotasNaoAparecemComoNoite() throws IOException {
        final ArquivoDaNoite a = new ArquivoDaNoite(tmp.getRoot());
        a.abrir("noite-1.jsonl");
        a.anexar("{}");
        a.close();
        NotasDaNoite.salvar(tmp.getRoot(), "noite-1.jsonl", m("posicao", "outra"));
        assertEquals(Collections.singletonList("noite-1.jsonl"), a.noites());
    }

    @Test
    public void corteDeTemperaturaNoLimite() {
        assertFalse(CorteDeTemperatura.deveEncerrar(250));
        assertFalse(CorteDeTemperatura.deveEncerrar(449));
        assertTrue(CorteDeTemperatura.deveEncerrar(450));
        assertTrue(CorteDeTemperatura.deveEncerrar(600));
        assertEquals(450, CorteDeTemperatura.LIMITE_DECIMOS);
    }
}
