package app.dormiosmart.coleta;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStreamReader;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;

/**
 * Os pontos de calibracao guardados entre noites (CAL-03, etapa 2).
 *
 * <p>Cada epoca parada vira uma linha {@code x,y,z,temp} (g e graus C) em
 * {@code calibracao-pontos.csv}, na pasta das noites. O vetor e o BRUTO: o
 * nucleo ja desfaz a calibracao da noite antes de entregar o ponto
 * ({@code ColetorCelular::ponto_parado}), entao pontos de noites com
 * calibracoes diferentes ficam na mesma escala.
 *
 * <p>So os {@link #MAXIMO} mais recentes contam, e o arquivo e aparado ao ler:
 * variedade de posicao e de temperatura sem crescer para sempre. Uma linha que
 * nao se le e pulada, nao derruba a estimativa.
 */
public final class PontosDeCalibracao {

    public static final String ARQUIVO = "calibracao-pontos.csv";
    /** ~16 h de epocas paradas de 30 s. */
    public static final int MAXIMO = 2000;

    private final File arquivo;

    public PontosDeCalibracao(File pasta) {
        this.arquivo = new File(pasta, ARQUIVO);
    }

    public File arquivo() {
        return arquivo;
    }

    /** Acrescenta um ponto. {@code ponto} e {x, y, z, temp_c}. */
    public void anexar(double[] ponto) throws IOException {
        if (ponto == null || ponto.length != 4) throw new IllegalArgumentException("ponto malformado");
        for (double v : ponto) {
            if (Double.isNaN(v) || Double.isInfinite(v)) return;  // nao guarda lixo
        }
        try (Writer w = new OutputStreamWriter(new FileOutputStream(arquivo, true), StandardCharsets.UTF_8)) {
            w.write(String.format(Locale.ROOT, "%.6f,%.6f,%.6f,%.1f%n", ponto[0], ponto[1], ponto[2], ponto[3]));
        }
    }

    /**
     * Os pontos guardados, os mais recentes ate {@link #MAXIMO}, como
     * {x, y, z, temp}. Se havia mais, o arquivo e reescrito so com eles.
     */
    public List<double[]> ler() throws IOException {
        final List<double[]> todos = new ArrayList<>();
        if (!arquivo.exists()) return todos;
        try (BufferedReader r = new BufferedReader(
                new InputStreamReader(new FileInputStream(arquivo), StandardCharsets.UTF_8))) {
            String linha;
            while ((linha = r.readLine()) != null) {
                final double[] p = interpretar(linha);
                if (p != null) todos.add(p);
            }
        }
        if (todos.size() <= MAXIMO) return todos;
        final List<double[]> recentes = new ArrayList<>(todos.subList(todos.size() - MAXIMO, todos.size()));
        reescrever(recentes);
        return recentes;
    }

    static double[] interpretar(String linha) {
        final String[] partes = linha.trim().split(",");
        if (partes.length != 4) return null;
        final double[] p = new double[4];
        try {
            for (int i = 0; i < 4; i++) p[i] = Double.parseDouble(partes[i]);
        } catch (NumberFormatException e) {
            return null;
        }
        for (double v : p) {
            if (Double.isNaN(v) || Double.isInfinite(v)) return null;
        }
        // Um vetor de gravidade fora de 0,5..1,5 g nao e epoca parada de verdade.
        final double norma = Math.sqrt(p[0] * p[0] + p[1] * p[1] + p[2] * p[2]);
        if (norma < 0.5 || norma > 1.5) return null;
        return p;
    }

    private void reescrever(List<double[]> pontos) throws IOException {
        final File tmp = new File(arquivo.getPath() + ".tmp");
        try (Writer w = new OutputStreamWriter(new FileOutputStream(tmp), StandardCharsets.UTF_8)) {
            for (double[] p : pontos) {
                w.write(String.format(Locale.ROOT, "%.6f,%.6f,%.6f,%.1f%n", p[0], p[1], p[2], p[3]));
            }
        }
        if (!tmp.renameTo(arquivo)) {
            if (!arquivo.delete() || !tmp.renameTo(arquivo)) throw new IOException("nao trocou " + arquivo);
        }
    }

    /** Os pontos no formato da ponte: xyz intercalado e as temperaturas. */
    public static double[][] paraEstimar(List<double[]> pontos) {
        final double[] xyz = new double[3 * pontos.size()];
        final double[] temps = new double[pontos.size()];
        for (int i = 0; i < pontos.size(); i++) {
            final double[] p = pontos.get(i);
            xyz[3 * i] = p[0];
            xyz[3 * i + 1] = p[1];
            xyz[3 * i + 2] = p[2];
            temps[i] = p[3];
        }
        return new double[][] {xyz, temps};
    }
}
