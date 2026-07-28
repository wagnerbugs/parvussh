"""Descriptions and examples for the ssh option catalog (pt-BR).

Keys are `kw.<OptionName>.desc` and the optional `kw.<OptionName>.example`,
matching the structural catalog in `parvussh/data/keywords.py`. Every entry
there needs a `.desc` here; `tests/test_keywords.py` fails otherwise.

These descriptions are the app's teaching surface. Two rules, from CLAUDE.md
§7: say what the option does in the user's words, and where the option exists
to prevent a specific frustration, name that frustration — someone who has hit
"too many authentication failures" should recognise it in `IdentitiesOnly`.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "kw.unknown.desc": "Opção não catalogada, preservada como está.",
    # -- Conexão ----------------------------------------------------------
    "kw.HostName.desc": "Endereço real do servidor: IP ou domínio.",
    "kw.HostName.example": "203.0.113.10 ou vps.exemplo.com",
    "kw.User.desc": "Usuário usado no login remoto.",
    "kw.User.example": "deploy",
    "kw.Port.desc": "Porta do servidor SSH.",
    "kw.Port.example": "22",
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
    "kw.PubkeyAuthentication.desc": "Tenta autenticar por chave pública.",
    "kw.PasswordAuthentication.desc": "Permite autenticar por senha.",
    "kw.KbdInteractiveAuthentication.desc": (
        "Permite autenticação interativa, como 2FA e teclado-interativo."
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
        "Deixa o servidor usar as chaves do seu agente. Só ative em máquinas de "
        "confiança."
    ),
    # -- Sessão -----------------------------------------------------------
    "kw.ServerAliveInterval.desc": (
        "Envia um sinal de vida a cada N segundos para a sessão não cair sozinha."
    ),
    "kw.ServerAliveInterval.example": "60",
    "kw.ServerAliveCountMax.desc": (
        "Quantos sinais sem resposta antes de desistir da conexão."
    ),
    "kw.ServerAliveCountMax.example": "3",
    "kw.ConnectTimeout.desc": (
        "Tempo máximo, em segundos, esperando o servidor responder."
    ),
    "kw.ConnectTimeout.example": "10",
    "kw.ConnectionAttempts.desc": "Quantas vezes tentar antes de falhar.",
    "kw.ConnectionAttempts.example": "2",
    "kw.Compression.desc": "Comprime os dados. Ajuda em links lentos.",
    "kw.TCPKeepAlive.desc": (
        "Deixa o TCP detectar quedas de rede. Diferente de ServerAlive."
    ),
    "kw.RequestTTY.desc": "Se um terminal interativo deve ser alocado.",
    "kw.RemoteCommand.desc": "Comando executado logo após o login.",
    "kw.RemoteCommand.example": "cd /srv/app && bash -l",
    "kw.SetEnv.desc": "Define variáveis de ambiente no servidor.",
    "kw.SetEnv.example": "LANG=pt_BR.UTF-8",
    "kw.SendEnv.desc": "Envia variáveis locais para o servidor.",
    "kw.SendEnv.example": "LANG LC_*",
    "kw.EscapeChar.desc": "Caractere de escape da sessão.",
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
    "kw.CheckHostIP.desc": "Confere também o IP do host, além do nome.",
    "kw.HostKeyAlgorithms.desc": "Algoritmos de chave de host aceitos.",
    "kw.HostKeyAlgorithms.example": "ssh-ed25519,rsa-sha2-512",
    "kw.VisualHostKey.desc": (
        "Mostra um desenho em ASCII da chave do host ao conectar."
    ),
    # -- Rede -------------------------------------------------------------
    "kw.ProxyJump.desc": "Conecta passando por outro host, o bastion.",
    "kw.ProxyJump.example": "bastion ou user@bastion:22",
    "kw.ProxyCommand.desc": "Comando externo que cria o canal até o servidor.",
    "kw.ProxyCommand.example": "cloudflared access ssh --hostname %h",
    "kw.AddressFamily.desc": "Restringe a IPv4 ou IPv6.",
    "kw.BindAddress.desc": "Endereço local de origem da conexão.",
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
    "kw.DynamicForward.desc": "Abre um proxy SOCKS na porta indicada.",
    "kw.DynamicForward.example": "1080",
    "kw.ExitOnForwardFailure.desc": (
        "Encerra a conexão se algum encaminhamento falhar."
    ),
    "kw.GatewayPorts.desc": ("Deixa outras máquinas usarem suas portas encaminhadas."),
    "kw.ForwardX11.desc": "Encaminha aplicações gráficas X11.",
    "kw.ForwardX11Trusted.desc": (
        "Dá acesso total do X11 ao servidor. Use com cautela."
    ),
    # -- Outras -----------------------------------------------------------
    "kw.LogLevel.desc": "Quanta informação o ssh imprime.",
    "kw.BatchMode.desc": (
        "Nunca pergunta nada. Serve para scripts, não para uso interativo."
    ),
    "kw.Ciphers.desc": "Cifras aceitas, em ordem de preferência.",
    "kw.Ciphers.example": "chacha20-poly1305@openssh.com",
    "kw.MACs.desc": "Algoritmos de integridade aceitos.",
    "kw.MACs.example": "hmac-sha2-256-etm@openssh.com",
    "kw.KexAlgorithms.desc": "Algoritmos de troca de chaves.",
    "kw.KexAlgorithms.example": "curve25519-sha256",
    "kw.CanonicalizeHostname.desc": (
        "Completa nomes curtos com o domínio antes de conectar."
    ),
    "kw.Include.desc": "Lê outro arquivo de configuração neste ponto.",
    "kw.Include.example": "config.d/*.conf",
    # -- Group headings ---------------------------------------------------
    "group.connection": "Conexão",
    "group.auth": "Autenticação",
    "group.session": "Sessão",
    "group.hostkey": "Identidade do host",
    "group.network": "Rede",
    "group.other": "Outras",
}
