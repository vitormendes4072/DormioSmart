// As chaves reproduzem a API. Os valores são as frases que aparecem na tela.
const frases: Record<string, string> = {
  "e-mail invalido": "Confira o endereço de e-mail.",
  "informe o e-mail": "Informe o e-mail.",
  "nome invalido": "Digite um nome válido.",
  "o nome passa de {} caracteres": "O nome tem mais caracteres do que o permitido.",
  "o consentimento e obrigatorio": "Marque o aceite para continuar.",
  "a lista e so para maiores de 18 anos": "A lista é só para maiores de 18 anos.",
  "dados nao persistidos (fonte indisponivel)": "Não foi possível gravar os dados. Tente novamente em instantes.",
  "erro interno": "Não foi possível concluir o pedido.",
  "fonte de dados indisponivel": "Não foi possível acessar os dados agora. Tente novamente em instantes.",
  "consulta indisponivel": "Não foi possível consultar os dados agora. Tente novamente em instantes.",
  "modelo indisponivel": "A análise está indisponível. Tente novamente em instantes.",
  "epocas insuficientes na janela": "Não há registros suficientes no período para fazer a análise.",
  "Não foi possível carregar as leituras.": "Não foi possível carregar os registros.",
  "servico de autenticacao indisponivel": "O serviço de acesso está indisponível. Tente novamente em instantes.",
  "autenticacao necessaria": "Entre na sua conta para continuar.",
  "sessao invalida ou expirada": "Sessão expirada. Entre novamente.",
  "versao do texto desatualizada": "O texto mudou. Recarregue a página e confira a versão atual.",
  "consentimento nao registrado (fonte indisponivel)": "Não foi possível salvar o consentimento. Tente novamente em instantes.",
  "consentimento para dado de saude pendente": "Revise e aceite o consentimento para continuar.",
  "nao foi possivel parear o dispositivo": "Não foi possível vincular o aparelho. Tente novamente.",
  "nao foi possivel preparar o dispositivo": "Não foi possível preparar o aparelho. Tente novamente.",
  "dispositivo nao encontrado": "Aparelho não encontrado. Confira seus aparelhos vinculados.",
  "nome nao pode ficar vazio": "O nome não pode ficar vazio.",
  "nome deve ser texto": "Digite um nome válido.",
  "campo nome ausente": "Informe o nome.",
  "nome deve ter no maximo {} caracteres": "O nome tem mais caracteres do que o permitido.",
  "idade deve ser um numero inteiro ou nulo": "Informe a idade em anos completos ou deixe o campo em branco.",
  "idade deve estar entre {} e {}": "A idade informada está fora do intervalo permitido.",
  "a meta deve ser um numero inteiro de minutos ou nulo": "Informe uma meta válida ou deixe o campo em branco.",
  "a meta deve estar entre 60 e 960 minutos": "A meta deve ficar entre 1 e 16 horas.",
  "perfil nao atualizado (fonte indisponivel)": "Não foi possível atualizar o perfil. Tente novamente em instantes.",
  "confirmacao necessaria": "Confirme o pedido para continuar.",
  "trecho acima de {} h": "Esta sessão ultrapassa o limite de duração para ser alterada de uma só vez.",
  "trecho acima de 48 h": "Esta sessão ultrapassa 48 horas e não pode ser alterada de uma só vez.",
  "A sessão mudou desde que a tela carregou. Recarregue e confira antes de tentar de novo.": "A sessão mudou desde que a tela carregou. Recarregue e confira antes de tentar de novo.",
  "Atualize o aplicativo para excluir ou marcar esta sessão.": "Atualize o aplicativo para excluir ou marcar esta sessão.",
  "campo ts esta no futuro": "O horário do aparelho está adiantado. Confira a data e a hora antes de enviar novos registros.",
  "campo ts precisa de fuso horario": "Confira o fuso horário configurado no aparelho.",
  "campo ts deve ser um instante ISO 8601": "O horário do registro não é válido. Confira a data e a hora do aparelho.",
  "aparelho_pausado": "O recebimento está pausado. Retome em Dispositivos antes de enviar novos registros.",
  "device nao autorizado": "O aparelho não tem acesso. Confira se ele está vinculado à sua conta.",
  "pedido grande demais": "O pedido é grande demais. Reduza a quantidade e tente novamente.",
  "muitas inscricoes agora; tente de novo daqui a pouco": "Há muitas inscrições agora. Tente novamente em instantes.",
  "campo {} fora da faixa fisica ([{}, {}]): {}": "O aparelho enviou um valor fora da faixa esperada.",
  "os tres eixos vieram exatamente zero: assinatura de sensor que responde mas nao mede (confira a alimentacao do MPU6050)": "O sensor respondeu sem medir. Confira a alimentação do aparelho."
};

const modelos = Object.keys(frases).filter((chave) => chave.includes("{}")).map((chave) => ({
  chave,
  padrao: new RegExp("^" + chave.split("{}").map((parte) => parte.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join(".+?") + "$"),
}));

export function mensagemDoServidor(original: unknown, padrao = "Não foi possível concluir o pedido.") {
  if (typeof original !== "string" || !original.trim()) return { mensagem: padrao };
  const chave = Object.prototype.hasOwnProperty.call(frases, original) ? original : modelos.find(({ padrao }) => padrao.test(original))?.chave;
  return chave ? { mensagem: frases[chave] } : { mensagem: padrao, detalhe: original };
}
