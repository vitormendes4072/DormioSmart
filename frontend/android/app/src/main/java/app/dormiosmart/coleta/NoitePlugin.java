package app.dormiosmart.coleta;

import android.Manifest;
import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.provider.Settings;

import androidx.core.content.ContextCompat;

import com.getcapacitor.JSArray;
import com.getcapacitor.JSObject;
import com.getcapacitor.PermissionState;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;
import com.getcapacitor.annotation.Permission;
import com.getcapacitor.annotation.PermissionCallback;

import java.io.File;
import java.io.IOException;

/**
 * A ponte entre a tela (o frontend React) e o {@link ServicoDaNoite} (APP-02).
 *
 * <p>Quatro operacoes: iniciar, encerrar, estado e pedir a isencao da
 * otimizacao de bateria. A interface e de proposito independente de Android:
 * um app iOS (APP-04) implementaria o mesmo plugin "Noite".
 */
@CapacitorPlugin(
        name = "Noite",
        permissions = {
            @Permission(strings = {Manifest.permission.POST_NOTIFICATIONS}, alias = "notificacoes")
        })
public class NoitePlugin extends Plugin {

    @PluginMethod
    public void iniciar(PluginCall call) {
        // Android 13+: sem a permissao, o servico roda, mas a notificacao fica
        // escondida -- e o usuario perde o unico sinal de que a noite esta sendo
        // registrada. Pede antes; se negar, inicia assim mesmo e diz na resposta.
        if (Build.VERSION.SDK_INT >= 33 && getPermissionState("notificacoes") != PermissionState.GRANTED) {
            requestPermissionForAlias("notificacoes", call, "aposPermissao");
            return;
        }
        iniciarServico(call);
    }

    @PermissionCallback
    private void aposPermissao(PluginCall call) {
        iniciarServico(call);
    }

    private void iniciarServico(PluginCall call) {
        final Context c = getContext();
        final Intent i = new Intent(c, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_INICIAR);
        ContextCompat.startForegroundService(c, i);
        final JSObject r = new JSObject();
        r.put("notificacoes", Build.VERSION.SDK_INT < 33
                || getPermissionState("notificacoes") == PermissionState.GRANTED);
        call.resolve(r);
    }

    @PluginMethod
    public void encerrar(PluginCall call) {
        final Context c = getContext();
        c.startService(new Intent(c, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_ENCERRAR));
        call.resolve();
    }

    @PluginMethod
    public void estado(PluginCall call) {
        try {
            final EstadoDaNoite e = EstadoDaNoite.ler(
                    new File(ServicoDaNoite.pasta(getContext()), ArquivoDaNoite.ESTADO));
            final JSObject r = new JSObject();
            r.put("ativa", e.ativa);
            r.put("rodando", ServicoDaNoite.emExecucao());
            r.put("inicioUtcMs", e.inicioUtcMs);
            r.put("epocasGravadas", e.epocasGravadas);
            r.put("recusadas", e.recusadas);
            r.put("recusadasPorTaxa", e.recusadasPorTaxa);
            r.put("semFeatures", e.semFeatures);
            r.put("amostras", e.amostras);
            r.put("taxaHz", e.taxaMiliHz / 1000.0);
            r.put("retomadas", e.retomadas);
            r.put("ultimaEpocaUtcMs", e.ultimaEpocaUtcMs);
            if (e.temperaturaDecimos != Long.MIN_VALUE) r.put("temperaturaC", e.temperaturaDecimos / 10.0);
            r.put("isentoDeBateria", isento());
            call.resolve(r);
        } catch (IOException ex) {
            call.reject("nao leu o estado da noite", ex);
        }
    }

    // ── O envio (APP-02, etapa 3) ──────────────────────────────────────────
    //
    // O envio fica no lado web: e la que esta a sessao, que o Supabase renova.
    // O nativo so le o arquivo e guarda ate onde o servidor confirmou.

    private ArquivoDaNoite arquivo() {
        return new ArquivoDaNoite(ServicoDaNoite.pasta(getContext()));
    }

    /** As noites gravadas: arquivo, total de epocas e quantas ja foram confirmadas. */
    @PluginMethod
    public void noites(PluginCall call) {
        try {
            final ArquivoDaNoite a = arquivo();
            final JSArray lista = new JSArray();
            for (String nome : a.noites()) {
                final JSObject n = new JSObject();
                n.put("arquivo", nome);
                n.put("epocas", a.linhas(nome).size());
                n.put("enviadas", a.enviadas(nome));
                lista.put(n);
            }
            final JSObject r = new JSObject();
            r.put("noites", lista);
            call.resolve(r);
        } catch (IOException ex) {
            call.reject("nao listou as noites", ex);
        }
    }

    /** Ate 60 epocas de {@code arquivo}, a partir de {@code de}, como texto JSON. */
    @PluginMethod
    public void lerEpocas(PluginCall call) {
        final String nome = call.getString("arquivo");
        final Integer de = call.getInt("de");
        if (nome == null || de == null || !nome.startsWith("noite-") || nome.contains("/")) {
            call.reject("arquivo e de sao obrigatorios");
            return;
        }
        try {
            final JSArray linhas = new JSArray();
            for (String l : arquivo().faixa(nome, de, ArquivoDaNoite.MAXIMO_POR_LOTE)) linhas.put(l);
            final JSObject r = new JSObject();
            r.put("epocas", linhas);
            call.resolve(r);
        } catch (IOException ex) {
            call.reject("nao leu as epocas", ex);
        }
    }

    /** Grava que as primeiras {@code ate} epocas de {@code arquivo} estao confirmadas. */
    @PluginMethod
    public void marcarEnviadas(PluginCall call) {
        final String nome = call.getString("arquivo");
        final Integer ate = call.getInt("ate");
        if (nome == null || ate == null || !nome.startsWith("noite-") || nome.contains("/")) {
            call.reject("arquivo e ate sao obrigatorios");
            return;
        }
        try {
            final JSObject r = new JSObject();
            r.put("enviadas", arquivo().marcarEnviadas(nome, ate));
            call.resolve(r);
        } catch (IOException ex) {
            call.reject("nao gravou o progresso do envio", ex);
        }
    }

    @PluginMethod
    public void pedirIsencaoDeBateria(PluginCall call) {
        if (!isento()) {
            final Intent i = new Intent(Settings.ACTION_REQUEST_IGNORE_BATTERY_OPTIMIZATIONS)
                    .setData(Uri.parse("package:" + getContext().getPackageName()));
            getActivity().startActivity(i);
        }
        final JSObject r = new JSObject();
        r.put("isentoDeBateria", isento());
        call.resolve(r);
    }

    private boolean isento() {
        final PowerManager pm = getContext().getSystemService(PowerManager.class);
        return pm.isIgnoringBatteryOptimizations(getContext().getPackageName());
    }
}
