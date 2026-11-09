package app.dormiosmart.coleta;

import android.content.Intent;
import android.os.Bundle;

import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    /**
     * So no build de depuracao: {@code adb shell am start -n
     * app.dormiosmart.coleta/.MainActivity --es roteiro iniciar} (ou {@code
     * encerrar}) liga a noite como o botao da tela liga. Existe para o roteiro
     * da retomada (APP-02, etapa 2): o servico tem de nascer no processo do app,
     * e nao no da instrumentacao, que o Android nao reinicia.
     */
    static final String EXTRA_ROTEIRO = "roteiro";

    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Plugins locais entram antes do super.onCreate, que monta a ponte.
        registerPlugin(NoitePlugin.class);
        super.onCreate(savedInstanceState);
        roteiro(getIntent());
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        roteiro(intent);
    }

    private void roteiro(Intent intent) {
        if (!BuildConfig.DEBUG || intent == null) return;
        final String r = intent.getStringExtra(EXTRA_ROTEIRO);
        if ("iniciar".equals(r)) {
            ContextCompat.startForegroundService(this,
                    new Intent(this, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_INICIAR));
        } else if ("encerrar".equals(r)) {
            startService(new Intent(this, ServicoDaNoite.class).setAction(ServicoDaNoite.ACAO_ENCERRAR));
        }
    }
}
