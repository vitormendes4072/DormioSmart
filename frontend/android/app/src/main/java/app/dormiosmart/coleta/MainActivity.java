package app.dormiosmart.coleta;

import android.os.Bundle;

import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        // Plugins locais entram antes do super.onCreate, que monta a ponte.
        registerPlugin(NoitePlugin.class);
        super.onCreate(savedInstanceState);
    }
}
