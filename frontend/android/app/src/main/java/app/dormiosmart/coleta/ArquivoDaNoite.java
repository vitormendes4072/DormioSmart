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

    /** As linhas de um arquivo de noite, na ordem gravada. */
    public List<String> linhas(String nomeDoArquivo) throws IOException {
        final List<String> saidaLida = new ArrayList<>();
        final File f = new File(pasta, nomeDoArquivo);
        if (!f.exists()) return saidaLida;
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(f), StandardCharsets.UTF_8))) {
            String l;
            while ((l = r.readLine()) != null) {
                if (!l.isEmpty()) saidaLida.add(l);
            }
        }
        return saidaLida;
    }

    @Override
    public void close() throws IOException {
        if (saida != null) {
            saida.close();
            saida = null;
        }
    }
}
