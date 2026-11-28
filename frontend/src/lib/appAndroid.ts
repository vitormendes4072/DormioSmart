// APP-17: onde o APK do app Android beta é baixado.
// O endereço "latest" do GitHub Releases aponta sempre para a versão mais nova publicada, então a
// landing não muda a cada APK. A versão tem de ser a mesma do `versionName` do
// `android/app/build.gradle` e a escrita na landing completa (`public/landing-prototipo.html`,
// que é HTML estático e não importa este módulo): o `appAndroid.test.ts` reprova a divergência.
export const VERSAO_DO_APP_ANDROID = "1.1.9";
export const URL_DO_APK =
  "https://github.com/vitormendes4072/DormioSmart/releases/latest/download/smart-dormio.apk";
