package app.dormiosmart.coleta;

import java.io.BufferedReader;
import java.io.Closeable;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * As epocas de uma noite, no armazenamento interno do app (APP-02).
 *
 * <p>Uma linha por epoca, com o payload JSON exatamente como o nucleo o montou.
 * Cada linha e gravada e sincronizada com o disco na hora: a noite que o
 * sistema interromper perde no maximo a epoca em curso, nunca as gravadas. O
 * envio ao servidor (etapa 3) le daqui. Java puro, testado na JVM.
 */
public final class ArquivoDaNoite implements Closeable {

    public static final String ESTADO = "estado.properties";

    private final File pasta;
    private FileOutputStream saida;
    private String nome;

    public ArquivoDaNoite(File pasta) {
        this.pasta = pasta;
    }

    public File pasta() {
        return pasta;
    }

    public File estado() {
        return new File(pasta, ESTADO);
    }

    /** O nome do arquivo de uma noite que comecou em {@code inicioUtcMs}. */
    public static String nomeDaNoite(long inicioUtcMs) {
        return "noite-" + inicioUtcMs + ".jsonl";
    }

    /** Abre (ou reabre, na retomada) o arquivo da noite para acrescentar linhas. */
    public void abrir(String nomeDoArquivo) throws IOException {
        close();
        if (!pasta.isDirectory() && !pasta.mkdirs()) {
            throw new IOException("nao criou " + pasta);
        }
        nome = nomeDoArquivo;
        saida = new FileOutputStream(new File(pasta, nomeDoArquivo), true);
    }

    public String nome() {
        return nome;
    }

    /** Acrescenta uma epoca e so volta depois de ela estar no disco. */
    public void anexar(String payload) throws IOException {
        if (saida == null) throw new IOException("arquivo da noite nao esta aberto");
        if (payload.indexOf('\n') >= 0) throw new IOException("payload com quebra de linha");
        saida.write((payload + "\n").getBytes(StandardCharsets.UTF_8));
        saida.flush();
        saida.getFD().sync();
    }

    /**
     * As linhas COMPLETAS de um arquivo de noite, na ordem gravada.
     *
     * <p>A tela le o arquivo enquanto o servico ainda grava nele. Uma linha sem
     * a quebra final e uma epoca no meio da escrita: ela fica de fora, e entra
     * na leitura seguinte. Lida pela metade, viraria JSON quebrado no envio.
     */
    public List<String> linhas(String nomeDoArquivo) throws IOException {
        final List<String> saidaLida = new ArrayList<>();
        final File f = new File(pasta, nomeDoArquivo);
        if (!f.exists()) return saidaLida;
        final StringBuilder sb = new StringBuilder();
        try (InputStreamReader r = new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8)) {
            final char[] b = new char[8192];
            int n;
            while ((n = r.read(b)) > 0) sb.append(b, 0, n);
        }
        int ini = 0;
        for (int i = 0; i < sb.length(); i++) {
            if (sb.charAt(i) == '\n') {
                if (i > ini) saidaLida.add(sb.substring(ini, i));
                ini = i + 1;
            }
        }
        return saidaLida;
    }

    // ── O progresso do envio (APP-02, etapa 3) ─────────────────────────────

    /** Sufixo do arquivo que guarda ate onde o servidor confirmou a noite. */
    public static final String SUFIXO_ENVIADO = ".enviado";
    /** O teto de leituras por lote do backend (`web-app/lote.py`). */
    public static final int MAXIMO_POR_LOTE = 60;

    /** Os arquivos de noite da pasta, do mais antigo para o mais novo. */
    public List<String> noites() {
        final List<String> saidaLida = new ArrayList<>();
        final String[] nomes = pasta.list();
        if (nomes == null) return saidaLida;
        Arrays.sort(nomes);
        for (String n : nomes) {
            if (n.startsWith("noite-") && n.endsWith(".jsonl")) saidaLida.add(n);
        }
        return saidaLida;
    }

    /**
     * Quantas epocas do comeco da noite o servidor ja confirmou (aceitas ou
     * rejeitadas por invalidas). 0 se nada foi enviado.
     */
    public int enviadas(String nomeDoArquivo) throws IOException {
        final File f = new File(pasta, nomeDoArquivo + SUFIXO_ENVIADO);
        if (!f.exists()) return 0;
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            final String l = r.readLine();
            try {
                return l == null ? 0 : Math.max(0, Integer.parseInt(l.trim()));
            } catch (NumberFormatException ex) {
                return 0;
            }
        }
    }

    /**
     * Grava que as primeiras {@code ate} epocas estao confirmadas. O ponto so
     * avanca: um pedido para recuar e ignorado, porque recuar so faria reenviar
     * (o servidor deduplica, mas o trabalho e a duvida ficariam). Nunca passa
     * do total de linhas gravadas.
     *
     * @return o ponto que ficou gravado
     */
    public int marcarEnviadas(String nomeDoArquivo, int ate) throws IOException {
        final int atual = enviadas(nomeDoArquivo);
        final int total = linhas(nomeDoArquivo).size();
        final int novo = Math.min(Math.max(atual, ate), total);
        if (novo == atual) return atual;
        final File destino = new File(pasta, nomeDoArquivo + SUFIXO_ENVIADO);
        final File tmp = new File(destino.getPath() + ".tmp");
        try (FileOutputStream s = new FileOutputStream(tmp)) {
            s.write((novo + "\n").getBytes(StandardCharsets.UTF_8));
            s.flush();
            s.getFD().sync();
        }
        if (!tmp.renameTo(destino)) {
            if (!destino.delete() || !tmp.renameTo(destino)) {
                throw new IOException("nao trocou " + destino);
            }
        }
        return novo;
    }

    /** As linhas [de, de + quantas), com quantas limitado ao teto do lote. */
    public List<String> faixa(String nomeDoArquivo, int de, int quantas) throws IOException {
        final List<String> todas = linhas(nomeDoArquivo);
        final int ini = Math.max(0, Math.min(de, todas.size()));
        final int fim = Math.min(todas.size(), ini + Math.max(0, Math.min(quantas, MAXIMO_POR_LOTE)));
        return new ArrayList<>(todas.subList(ini, fim));
    }

    @Override
    public void close() throws IOException {
        if (saida != null) {
            saida.close();
            saida = null;
        }
    }
}
