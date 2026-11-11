package app.dormiosmart.coleta;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.FileWriter;
import java.io.IOException;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.List;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** A calibracao da noite e os pontos guardados entre noites (CAL-03, etapa 2). Roda na JVM. */
public class CalibracaoTest {

    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static double[] resultado(boolean aceita, int pontos) {
        return new double[] {
            aceita ? 1 : 0,
            0.001, 0.0, -0.0075,     // desvio
            1.0, 1.0, 0.9884,        // escala
            0.0, 0.0, 0.0002,        // coef_temp
            22.5,                    // temp_ref
            0, 0, 2,                 // modos
            1,                       // usou_temperatura
            pontos, 0.0155, 0.0006, 7,
        };
    }

    @Test
    public void leOResultadoDoNucleoNaOrdemDaPonte() {
        final Calibracao c = Calibracao.doResultado(resultado(true, 120));
        assertTrue(c.aceita);
        assertEquals(-0.0075, c.desvio[2], 0);
        assertEquals(0.9884, c.escala[2], 0);
        assertEquals(0.0002, c.coefTemp[2], 0);
        assertEquals(22.5, c.tempRefC, 0);
        assertArrayEquals(new int[] {0, 0, 2}, c.modos);
        assertTrue(c.usouTemperatura);
        assertEquals(120, c.pontos);
        assertEquals(7, c.iteracoes);
    }

    @Test
    public void osParametrosVaoNaOrdemQueAPonteLe() {
        final double[] p = Calibracao.doResultado(resultado(true, 120)).parametros();
        assertArrayEquals(new double[] {1, 0.001, 0.0, -0.0075, 1.0, 1.0, 0.9884, 0, 0, 0.0002, 22.5}, p, 0);
    }

    @Test
    public void resultadoMalformadoNaoViraCalibracao() {
        try {
            Calibracao.doResultado(new double[5]);
            fail("aceitou um vetor de 5");
        } catch (IllegalArgumentException esperado) {
            // ok
        }
    }

    @Test
    public void gravaELeAoLadoDaNoite() throws IOException {
        final Calibracao c = Calibracao.doResultado(resultado(true, 120));
        final File f = Calibracao.arquivoDa(tmp.getRoot(), "noite-1.jsonl");
        assertEquals("noite-1.jsonl.calibracao", f.getName());
        c.salvar(f);
        final Calibracao l = Calibracao.ler(f);
        assertTrue(l.aceita);
        assertArrayEquals(c.parametros(), l.parametros(), 0);
        assertEquals(120, l.pontos);
    }

    @Test
    public void semArquivoOuEstragadoEAIdentidade() throws IOException {
        assertFalse(Calibracao.ler(new File(tmp.getRoot(), "nao-existe")).aceita);
        final File f = tmp.newFile("estragado.calibracao");
        try (Writer w = new FileWriter(f)) {
            w.write("aceita=true\nescala_0=abc\n");
        }
        final Calibracao l = Calibracao.ler(f);
        assertFalse(l.aceita);
        assertArrayEquals(new Calibracao().parametros(), l.parametros(), 0);
    }

    @Test
    public void escalaAbsurdaEIdentidade() throws IOException {
        final Calibracao c = Calibracao.doResultado(resultado(true, 120));
        c.escala[1] = 0.0;  // o `desfazer` dividiria por zero
        final File f = tmp.newFile("zero.calibracao");
        c.salvar(f);
        assertFalse(Calibracao.ler(f).aceita);
    }

    @Test
    public void oResumoDizOQueATelaMostra() {
        assertEquals("Calibrado: erro de 15,5 mg para 0,6 mg, com 120 épocas paradas",
                Calibracao.doResultado(resultado(true, 120)).resumo(40));
        assertEquals("Calibrando: 23 de 40 épocas paradas",
                Calibracao.doResultado(resultado(false, 23)).resumo(40));
        assertEquals("Calibração recusada: o erro ficou em 0,6 mg",
                Calibracao.doResultado(resultado(false, 120)).resumo(40));
    }

    // --- os pontos -------------------------------------------------------------

    @Test
    public void anexaELeOsPontos() throws IOException {
        final PontosDeCalibracao p = new PontosDeCalibracao(tmp.getRoot());
        assertTrue(p.ler().isEmpty());
        p.anexar(new double[] {0.001, -0.002, -1.0193, 18.5});
        p.anexar(new double[] {0.0, 0.0, 1.004, 19.0});
        final List<double[]> l = p.ler();
        assertEquals(2, l.size());
        assertArrayEquals(new double[] {0.001, -0.002, -1.0193, 18.5}, l.get(0), 1e-9);
    }

    @Test
    public void naoGuardaPontoComNaN() throws IOException {
        final PontosDeCalibracao p = new PontosDeCalibracao(tmp.getRoot());
        p.anexar(new double[] {Double.NaN, 0, 1, 20});
        assertTrue(p.ler().isEmpty());
    }

    @Test
    public void linhaRuimEPuladaEOResto() throws IOException {
        final PontosDeCalibracao p = new PontosDeCalibracao(tmp.getRoot());
        p.anexar(new double[] {0, 0, 1.0, 20});
        Files.write(p.arquivo().toPath(), "lixo\n1,2\n0,0,0.1,20\n".getBytes(StandardCharsets.UTF_8),
                java.nio.file.StandardOpenOption.APPEND);
        p.anexar(new double[] {0, 0, -1.0, 21});
        assertEquals(2, p.ler().size());
        assertNull(PontosDeCalibracao.interpretar("0,0,0.1,20"));  // 0,1 g nao e gravidade parada
    }

    @Test
    public void ficaSoComOsMaisRecentesEAparaOArquivo() throws IOException {
        final PontosDeCalibracao p = new PontosDeCalibracao(tmp.getRoot());
        for (int i = 0; i < PontosDeCalibracao.MAXIMO + 50; i++) {
            p.anexar(new double[] {0, 0, 1.0, i});
        }
        final List<double[]> l = p.ler();
        assertEquals(PontosDeCalibracao.MAXIMO, l.size());
        assertEquals(50.0, l.get(0)[3], 0);  // os 50 mais antigos sairam
        assertEquals(PontosDeCalibracao.MAXIMO,
                Files.readAllLines(p.arquivo().toPath(), StandardCharsets.UTF_8).size());
    }

    @Test
    public void paraEstimarIntercalaXyzESeparaATemperatura() {
        final double[][] v = PontosDeCalibracao.paraEstimar(java.util.Arrays.asList(
                new double[] {1, 2, 3, 20}, new double[] {4, 5, 6, 21}));
        assertArrayEquals(new double[] {1, 2, 3, 4, 5, 6}, v[0], 0);
        assertArrayEquals(new double[] {20, 21}, v[1], 0);
    }
}
