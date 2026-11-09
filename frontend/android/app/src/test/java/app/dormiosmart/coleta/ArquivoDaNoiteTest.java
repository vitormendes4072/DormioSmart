package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** O arquivo da noite e o estado que sobrevive a morte do servico (APP-02). Roda na JVM. */
public class ArquivoDaNoiteTest {

    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void linhasGravadasSobrevivemAoFechamentoEAReabertura() throws IOException {
        final File pasta = new File(tmp.getRoot(), "noites");
        final String nome = ArquivoDaNoite.nomeDaNoite(1_794_096_000_000L);
        assertEquals("noite-1794096000000.jsonl", nome);

        try (ArquivoDaNoite a = new ArquivoDaNoite(pasta)) {
            a.abrir(nome);
            a.anexar("{\"epoca\":0}");
            a.anexar("{\"epoca\":1}");
        }
        // A retomada reabre o mesmo arquivo e acrescenta, sem apagar.
        try (ArquivoDaNoite a = new ArquivoDaNoite(pasta)) {
            a.abrir(nome);
            a.anexar("{\"epoca\":5}");
            assertEquals(Arrays.asList("{\"epoca\":0}", "{\"epoca\":1}", "{\"epoca\":5}"), a.linhas(nome));
        }
    }

    @Test
    public void payloadComQuebraDeLinhaERecusado() throws IOException {
        try (ArquivoDaNoite a = new ArquivoDaNoite(tmp.getRoot())) {
            a.abrir("x.jsonl");
            try {
                a.anexar("{\"a\":1}\n{\"b\":2}");
                fail("uma linha com quebra viraria duas epocas no envio");
            } catch (IOException esperado) {
                assertTrue(a.linhas("x.jsonl").isEmpty());
            }
        }
    }

    @Test
    public void anexarSemAbrirFalhaEmVezDePerderEmSilencio() {
        final ArquivoDaNoite a = new ArquivoDaNoite(tmp.getRoot());
        try {
            a.anexar("{}");
            fail("anexar sem abrir tem de falhar");
        } catch (IOException esperado) {
            // ok
        }
    }

    @Test
    public void estadoIdaEVolta() throws IOException {
        final File f = new File(tmp.getRoot(), ArquivoDaNoite.ESTADO);
        final EstadoDaNoite e = new EstadoDaNoite();
        e.ativa = true;
        e.inicioUtcMs = 1_794_096_000_000L;
        e.arquivo = ArquivoDaNoite.nomeDaNoite(e.inicioUtcMs);
        e.epocasGravadas = 960;
        e.recusadas = 3;
        e.recusadasPorTaxa = 1;
        e.semFeatures = 2;
        e.semPayload = 1;
        e.amostras = 1_440_000;
        e.foraDeOrdem = 4;
        e.taxaMiliHz = 49_987;
        e.retomadas = 2;
        e.ultimaEpocaUtcMs = 1_794_124_800_000L;
        e.temperaturaDecimos = 318;
        e.deslocamentoDoRelogioNs = 12_345L;
        e.salvar(f);

        final EstadoDaNoite l = EstadoDaNoite.ler(f);
        assertTrue(l.ativa);
        assertEquals(e.inicioUtcMs, l.inicioUtcMs);
        assertEquals(e.arquivo, l.arquivo);
        assertEquals(960, l.epocasGravadas);
        assertEquals(3, l.recusadas);
        assertEquals(1, l.recusadasPorTaxa);
        assertEquals(2, l.semFeatures);
        assertEquals(1, l.semPayload);
        assertEquals(1_440_000, l.amostras);
        assertEquals(4, l.foraDeOrdem);
        assertEquals(49_987, l.taxaMiliHz);
        assertEquals(2, l.retomadas);
        assertEquals(e.ultimaEpocaUtcMs, l.ultimaEpocaUtcMs);
        assertEquals(318, l.temperaturaDecimos);
        assertEquals(12_345L, l.deslocamentoDoRelogioNs);
        assertFalse(new File(f.getPath() + ".tmp").exists());
    }

    @Test
    public void semEstadoGravadoANoiteEstaInativa() throws IOException {
        final EstadoDaNoite l = EstadoDaNoite.ler(new File(tmp.getRoot(), "nao-existe"));
        assertFalse(l.ativa);
        assertEquals(Long.MIN_VALUE, l.temperaturaDecimos);
    }
}
