package app.dormiosmart.coleta;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Properties;

/**
 * As anotacoes de uma noite: a posicao do celular e o diario de sono (APP-02, etapa 4).
 *
 * <p>Ficam num arquivo ao lado da noite ({@code noite-<ts>.jsonl.notas}) e NAO
 * vao ao servidor: o contrato de dados nao tem esses campos, e mandar mais um
 * dado de saude pediria a politica de privacidade (LGPD-03). Servem ao
 * protocolo da noite real (etapa 5) e sao lidos na analise, com o autor.
 *
 * <p>So as chaves de {@link #CHAVES} sao aceitas: o arquivo nao vira deposito
 * de qualquer coisa que a tela mande. Java puro, testado na JVM.
 */
public final class NotasDaNoite {

    public static final String SUFIXO = ".notas";

    /** posicao: fronha | colchao | outra. fim: usuario | temperatura | sem_sensor. Horas em "HH:MM". */
    public static final List<String> CHAVES = Collections.unmodifiableList(Arrays.asList(
            "posicao", "deitou", "adormeceu", "acordou", "despertares", "observacao", "fim"));

    public static final List<String> POSICOES = Collections.unmodifiableList(
            Arrays.asList("fronha", "colchao", "outra"));

    /** Teto de cada valor: anotacao, nao relatorio. */
    public static final int TAMANHO_MAXIMO = 500;

    private NotasDaNoite() {}

    private static File arquivo(File pasta, String noite) {
        if (noite == null || !noite.startsWith("noite-") || !noite.endsWith(".jsonl") || noite.contains("/")
                || noite.contains("\\")) {
            throw new IllegalArgumentException("nome de noite invalido: " + noite);
        }
        return new File(pasta, noite + SUFIXO);
    }

    /** As anotacoes gravadas da noite, na ordem de {@link #CHAVES}; vazio se nao ha. */
    public static Map<String, String> ler(File pasta, String noite) throws IOException {
        final Map<String, String> m = new LinkedHashMap<>();
        final File f = arquivo(pasta, noite);
        if (!f.exists()) return m;
        final Properties p = new Properties();
        try (InputStream s = new FileInputStream(f)) {
            p.load(s);
        }
        for (String k : CHAVES) {
            final String v = p.getProperty(k);
            if (v != null) m.put(k, v);
        }
        return m;
    }

    /**
     * Junta {@code novas} as anotacoes gravadas e salva. Chave fora de
     * {@link #CHAVES}, posicao fora de {@link #POSICOES} ou valor longo demais
     * sao recusados inteiros, sem gravar nada. Valor vazio apaga a chave.
     */
    public static Map<String, String> salvar(File pasta, String noite, Map<String, String> novas)
            throws IOException {
        for (Map.Entry<String, String> e : novas.entrySet()) {
            if (!CHAVES.contains(e.getKey())) {
                throw new IllegalArgumentException("anotacao desconhecida: " + e.getKey());
            }
            final String v = e.getValue() == null ? "" : e.getValue();
            if (v.length() > TAMANHO_MAXIMO) {
                throw new IllegalArgumentException("anotacao longa demais: " + e.getKey());
            }
            if (e.getKey().equals("posicao") && !v.isEmpty() && !POSICOES.contains(v)) {
                throw new IllegalArgumentException("posicao invalida: " + v);
            }
        }
        final Map<String, String> m = ler(pasta, noite);
        for (Map.Entry<String, String> e : novas.entrySet()) {
            final String v = e.getValue() == null ? "" : e.getValue().trim();
            if (v.isEmpty()) m.remove(e.getKey());
            else m.put(e.getKey(), v);
        }
        final Properties p = new Properties();
        for (Map.Entry<String, String> e : m.entrySet()) p.setProperty(e.getKey(), e.getValue());
        if (!pasta.isDirectory() && !pasta.mkdirs()) throw new IOException("nao criou " + pasta);
        final File destino = arquivo(pasta, noite);
        final File tmp = new File(destino.getPath() + ".tmp");
        try (OutputStream s = new FileOutputStream(tmp)) {
            p.store(s, "Dormio APP-02 - anotacoes da noite");
        }
        if (!tmp.renameTo(destino)) {
            if (!destino.delete() || !tmp.renameTo(destino)) throw new IOException("nao trocou " + destino);
        }
        return m;
    }
}
