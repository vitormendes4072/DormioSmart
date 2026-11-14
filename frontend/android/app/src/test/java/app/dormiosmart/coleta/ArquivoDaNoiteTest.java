package app.dormiosmart.coleta;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** O arquivo da noite e o estado que sobrevive a morte do servico (APP-02). Roda na JVM. */
public class ArquivoDaNoiteTest {

    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    @Test
    public void marcaAntesDaPrimeiraEpocaESobreviveAReabertura() throws IOException {
        final File pasta = tmp.getRoot();
        final String nome = ArquivoDaNoite.nomeDaNoite(1);
        try (ArquivoDaNoite a = new ArquivoDaNoite(pasta)) {
            a.abrirNovaGravacao(nome, true);
            assertTrue(a.deTeste(nome));
            assertTrue(a.linhas(nome).isEmpty());
            a.anexar("{}");
        }
        try (ArquivoDaNoite reaberto = new ArquivoDaNoite(pasta)) {
            reaberto.abrir(nome);
            assertTrue(reaberto.deTeste(nome));
            reaberto.anexar("{}");
            assertEquals(2, reaberto.linhas(nome).size());
            try {
                reaberto.faixaParaEnvio(nome, 0, 60);
                fail("teste entrou no caminho do plugin");
            } catch (IOException esperado) {
                assertEquals("gravacao de teste fica no aparelho", esperado.getMessage());
            }
        }
        final ArquivoDaNoite a = new ArquivoDaNoite(pasta);
        a.apagarTeste(nome);
        assertFalse(a.noites().contains(nome));
        assertFalse(a.deTeste(nome));
    }

    @Test
    public void gravacaoNormalEAntigaContinuamDisponiveisParaEnvio() throws IOException {
        try (ArquivoDaNoite a = new ArquivoDaNoite(tmp.getRoot())) {
            final String normal = ArquivoDaNoite.nomeDaNoite(1);
            final String antiga = ArquivoDaNoite.nomeDaNoite(2);
            a.abrirNovaGravacao(normal, false);
            a.anexar("{}");
            a.abrir(antiga);
            a.anexar("{}");
            assertEquals(1, a.faixaParaEnvio(normal, 0, 60).size());
            assertEquals(1, a.faixaParaEnvio(antiga, 0, 60).size());
        }
    }

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

    // ── O progresso do envio (etapa 3) ─────────────────────────────────────

    private ArquivoDaNoite noiteCom(int epocas, String nome) throws IOException {
        final ArquivoDaNoite a = new ArquivoDaNoite(new File(tmp.getRoot(), "noites"));
        a.abrir(nome);
        for (int i = 0; i < epocas; i++) a.anexar("{\"epoca\":" + i + "}");
        return a;
    }

    @Test
    public void semEnvioOPontoEZero() throws IOException {
        try (ArquivoDaNoite a = noiteCom(3, "noite-1.jsonl")) {
            assertEquals(0, a.enviadas("noite-1.jsonl"));
        }
    }

    @Test
    public void oPontoAvancaPersisteENuncaRecua() throws IOException {
        try (ArquivoDaNoite a = noiteCom(100, "noite-1.jsonl")) {
            assertEquals(60, a.marcarEnviadas("noite-1.jsonl", 60));
            // Outra instancia (o app reaberto) le o mesmo ponto.
            assertEquals(60, new ArquivoDaNoite(a.pasta()).enviadas("noite-1.jsonl"));
            assertEquals(60, a.marcarEnviadas("noite-1.jsonl", 20));
            assertEquals(60, a.enviadas("noite-1.jsonl"));
            // Nunca passa do que foi gravado.
            assertEquals(100, a.marcarEnviadas("noite-1.jsonl", 500));
        }
    }

    @Test
    public void aFaixaRespeitaOTetoDoLote() throws IOException {
        try (ArquivoDaNoite a = noiteCom(100, "noite-1.jsonl")) {
            assertEquals(ArquivoDaNoite.MAXIMO_POR_LOTE, a.faixa("noite-1.jsonl", 0, 999).size());
            final List<String> f = a.faixa("noite-1.jsonl", 50, 999);
            assertEquals(50, f.size());
            assertEquals("{\"epoca\":50}", f.get(0));
            assertEquals("{\"epoca\":99}", f.get(49));
            assertEquals(40, a.faixa("noite-1.jsonl", 60, 60).size());
            assertTrue(a.faixa("noite-1.jsonl", 100, 60).isEmpty());
            assertTrue(a.faixa("noite-1.jsonl", 500, 60).isEmpty());
        }
    }

    @Test
    public void asNoitesSaoListadasEmOrdemSemOEstadoNemOProgresso() throws IOException {
        final File pasta = new File(tmp.getRoot(), "noites");
        try (ArquivoDaNoite a = new ArquivoDaNoite(pasta)) {
            for (String n : new String[] {"noite-200.jsonl", "noite-100.jsonl"}) {
                a.abrir(n);
                a.anexar("{}");
            }
            a.marcarEnviadas("noite-100.jsonl", 1);
            new EstadoDaNoite().salvar(a.estado());
            assertEquals(new ArrayList<>(Arrays.asList("noite-100.jsonl", "noite-200.jsonl")), a.noites());
        }
    }

    @Test
    public void linhaPelaMetadeFicaDeForaAteTerminar() throws IOException {
        final File pasta = new File(tmp.getRoot(), "noites");
        try (ArquivoDaNoite a = new ArquivoDaNoite(pasta)) {
            a.abrir("noite-1.jsonl");
            a.anexar("{\"epoca\":0}");
        }
        // O servico no meio da escrita da proxima epoca.
        try (java.io.FileOutputStream s = new java.io.FileOutputStream(new File(pasta, "noite-1.jsonl"), true)) {
            s.write("{\"epoca\":1,\"ax\":".getBytes(java.nio.charset.StandardCharsets.UTF_8));
        }
        final ArquivoDaNoite leitor = new ArquivoDaNoite(pasta);
        assertEquals(Arrays.asList("{\"epoca\":0}"), leitor.linhas("noite-1.jsonl"));
        assertEquals(1, leitor.marcarEnviadas("noite-1.jsonl", 2));
    }
}
