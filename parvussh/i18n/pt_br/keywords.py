"""Descriptions and examples for the ssh option catalog (pt-BR).

Keys are `kw.<OptionName>.desc` and the optional `kw.<OptionName>.example`,
matching the structural catalog in `parvussh/data/keywords.py`. Every entry
there needs a `.desc` here; `tests/test_keywords.py` fails otherwise.

These descriptions are the app's teaching surface. Two rules, from CLAUDE.md
§7: say what the option does in the user's words, and where the option exists
to prevent a specific frustration, name that frustration — someone who has hit
"too many authentication failures" should recognise it in `IdentitiesOnly`.

Three of these options exist in `sshd_config` too, with a different meaning:
`PasswordAuthentication`, `KbdInteractiveAuthentication` and
`PubkeyAuthentication`. Nothing here touches the server, and the wording says
so — a reader coming from a hardening tutorial must not think otherwise.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "kw.unknown.desc": "Opção não catalogada, preservada como está.",
    # -- Conexão ----------------------------------------------------------
    "kw.HostName.desc": "Endereço real do servidor: IP ou domínio.",
    "kw.HostName.example": "203.0.113.10 ou vps.exemplo.com",
    "kw.User.desc": (
        "Usuário com quem entrar no servidor. Sem isso, o ssh usa o seu nome de "
        "usuário local."
    ),
    "kw.User.example": "deploy",
    "kw.Port.desc": (
        "Porta do servidor SSH. O padrão é 22 — preencha só se o seu escuta em outra."
    ),
    "kw.Port.example": "2222",
    # -- Autenticação -----------------------------------------------------
    "kw.IdentityFile.desc": "Chave privada usada nesta conexão.",
    "kw.IdentityFile.example": "~/.ssh/id_ed25519",
    "kw.IdentitiesOnly.desc": (
        "Usa só a chave declarada aqui, ignorando as demais do agente. Evita o "
        "erro de muitas tentativas quando você tem várias chaves."
    ),
    "kw.AddKeysToAgent.desc": (
        "Adiciona a chave ao ssh-agent depois de destravá-la, para não pedir a "
        "senha de novo."
    ),
    "kw.PubkeyAuthentication.desc": (
        "Tenta autenticar por chave. Desligue só para forçar outro método em um teste."
    ),
    "kw.PasswordAuthentication.desc": (
        "Oferece senha ao servidor se a chave falhar. Desligado, a conexão falha "
        "em vez de pedir senha."
    ),
    "kw.KbdInteractiveAuthentication.desc": (
        "Responde a perguntas do servidor, como códigos 2FA. Vale só para esta conexão."
    ),
    "kw.PreferredAuthentications.desc": (
        "Ordem em que os métodos de autenticação são tentados."
    ),
    "kw.PreferredAuthentications.example": "publickey,password",
    "kw.CertificateFile.desc": "Certificado de usuário assinado por uma CA.",
    "kw.CertificateFile.example": "~/.ssh/id_ed25519-cert.pub",
    "kw.IdentityAgent.desc": (
        "Socket do agente a consultar. Use none para ignorar o agente."
    ),
    "kw.IdentityAgent.example": "~/.1password/agent.sock",
    "kw.ForwardAgent.desc": (
        "Deixa o servidor usar as chaves do seu agente. Quem for root lá pode "
        "usá-las também."
    ),
    # -- Sessão -----------------------------------------------------------
    "kw.ServerAliveInterval.desc": (
        "Envia um sinal de vida a cada N segundos para a sessão não cair sozinha."
    ),
    "kw.ServerAliveInterval.example": "60",
    "kw.ServerAliveCountMax.desc": (
        "Quantos sinais sem resposta antes de desistir. Multiplique pelo intervalo "
        "para o tempo total."
    ),
    "kw.ServerAliveCountMax.example": "3",
    "kw.ConnectTimeout.desc": (
        "Tempo máximo, em segundos, esperando o servidor responder."
    ),
    "kw.ConnectTimeout.example": "10",
    "kw.ConnectionAttempts.desc": "Quantas vezes tentar antes de falhar.",
    "kw.ConnectionAttempts.example": "2",
    "kw.Compression.desc": (
        "Comprime os dados. Ajuda em links lentos e atrapalha em rápidos."
    ),
    "kw.TCPKeepAlive.desc": (
        "Deixa o TCP detectar quedas de rede. Age fora do canal cifrado, ao "
        "contrário de ServerAlive."
    ),
    "kw.RequestTTY.desc": (
        "Força ou dispensa o terminal interativo. Use force quando um comando "
        "remoto precisa de tela."
    ),
    "kw.RemoteCommand.desc": "Comando executado logo após o login.",
    "kw.RemoteCommand.example": "cd /srv/app && bash -l",
    "kw.SetEnv.desc": "Define variáveis de ambiente no servidor.",
    "kw.SetEnv.example": "LANG=pt_BR.UTF-8",
    "kw.SendEnv.desc": (
        "Envia variáveis locais para o servidor, que só as aceita se estiver "
        "configurado para isso."
    ),
    "kw.SendEnv.example": "LANG LC_*",
    "kw.EscapeChar.desc": (
        "Caractere que abre comandos da sessão. Com o padrão, ~. no começo da "
        "linha encerra uma conexão travada."
    ),
    "kw.EscapeChar.example": "~",
    # -- Identidade do host -----------------------------------------------
    "kw.StrictHostKeyChecking.desc": (
        "O que fazer quando a identidade do servidor é nova ou mudou. O valor "
        "accept-new aceita hosts novos, mas ainda alerta se a chave mudar."
    ),
    "kw.UserKnownHostsFile.desc": (
        "Arquivo onde as chaves de host conhecidas são guardadas."
    ),
    "kw.UserKnownHostsFile.example": "~/.ssh/known_hosts",
    "kw.CheckHostIP.desc": (
        "Confere também o IP, além do nome. Avisa quando o DNS passa a apontar "
        "para outro servidor."
    ),
    "kw.HostKeyAlgorithms.desc": "Algoritmos de chave de host aceitos.",
    "kw.HostKeyAlgorithms.example": "ssh-ed25519,rsa-sha2-512",
    "kw.VisualHostKey.desc": (
        "Mostra um desenho da chave do host ao conectar. Uma mudança salta aos olhos."
    ),
    # -- Rede -------------------------------------------------------------
    "kw.ProxyJump.desc": (
        "Conecta passando por outro host, o bastion. Pode ser o apelido de outra "
        "conexão daqui."
    ),
    "kw.ProxyJump.example": "bastion ou user@bastion:22",
    "kw.ProxyCommand.desc": "Comando externo que cria o canal até o servidor.",
    "kw.ProxyCommand.example": "cloudflared access ssh --hostname %h",
    "kw.AddressFamily.desc": (
        "Restringe a IPv4 ou IPv6. Útil quando um dos dois está quebrado na sua rede."
    ),
    "kw.BindAddress.desc": (
        "Endereço local de origem da conexão. Serve em máquinas com mais de uma "
        "placa de rede."
    ),
    "kw.BindAddress.example": "192.168.0.10",
    "kw.ControlMaster.desc": (
        "Reaproveita uma conexão já aberta para as próximas. Deixa tudo bem mais "
        "rápido."
    ),
    "kw.ControlPath.desc": "Onde o socket da conexão compartilhada fica.",
    "kw.ControlPath.example": "~/.ssh/cm-%r@%h:%p",
    "kw.ControlPersist.desc": (
        "Por quanto tempo a conexão mestre continua viva depois de fechar."
    ),
    "kw.ControlPersist.example": "10m",
    "kw.LocalForward.desc": "Encaminha uma porta local para o servidor.",
    "kw.LocalForward.example": "8080 localhost:80",
    "kw.RemoteForward.desc": "Encaminha uma porta do servidor para você.",
    "kw.RemoteForward.example": "9000 localhost:9000",
    "kw.DynamicForward.desc": (
        "Abre um proxy SOCKS na porta indicada, para o navegador sair pelo servidor."
    ),
    "kw.DynamicForward.example": "1080",
    "kw.ExitOnForwardFailure.desc": (
        "Encerra a conexão se algum encaminhamento falhar, em vez de conectar sem ele."
    ),
    "kw.GatewayPorts.desc": (
        "Deixa outras máquinas da rede usarem suas portas encaminhadas. Fechado "
        "por padrão."
    ),
    "kw.ForwardX11.desc": "Encaminha aplicações gráficas X11.",
    "kw.ForwardX11Trusted.desc": (
        "Dá acesso total do X11 ao servidor, que passa a poder ler o seu teclado."
    ),
    # -- Outras -----------------------------------------------------------
    "kw.LogLevel.desc": (
        "Quanta informação o ssh imprime. Use DEBUG para descobrir por que uma "
        "conexão falha."
    ),
    "kw.BatchMode.desc": (
        "Nunca pergunta nada. Serve para scripts, não para uso interativo."
    ),
    "kw.Ciphers.desc": (
        "Cifras aceitas, em ordem de preferência. Deixe vazio a menos que o "
        "servidor exija outra."
    ),
    "kw.Ciphers.example": "chacha20-poly1305@openssh.com",
    "kw.MACs.desc": (
        "Algoritmos de integridade aceitos. Só preencha para falar com servidores "
        "antigos."
    ),
    "kw.MACs.example": "hmac-sha2-256-etm@openssh.com",
    "kw.KexAlgorithms.desc": (
        "Algoritmos de troca de chaves. Mexer aqui pode impedir a conexão de fechar."
    ),
    "kw.KexAlgorithms.example": "curve25519-sha256",
    "kw.CanonicalizeHostname.desc": (
        "Completa nomes curtos com o domínio antes de conectar."
    ),
    "kw.Include.desc": (
        "Lê outro arquivo de configuração neste ponto. Vale sempre a primeira "
        "definição encontrada, não a última."
    ),
    "kw.Include.example": "config.d/*.conf",
    # -- Group headings ---------------------------------------------------
    "group.connection": "Conexão",
    "group.auth": "Autenticação",
    "group.session": "Sessão",
    "group.hostkey": "Identidade do host",
    "group.network": "Rede",
    "group.other": "Outras",
}
