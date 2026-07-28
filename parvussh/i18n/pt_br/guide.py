"""The key-setup guide and the "how it works" text (pt-BR).

Keys are `guide.<section>.title` and `guide.<section>.body`, matching
`parvussh/data/guide.py`. Bodies are Pango markup: `<tt>` around commands and
file names, nothing else. Any literal `&` or `<` must be escaped.

The audience is a developer who runs a couple of VPSs and has never been told
*why* any of this is the way it is. Each section says what to do, and then the
one thing that usually goes wrong.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "guide.create.title": "1. Criar a chave (na sua máquina)",
    "guide.create.body": (
        "Uma chave SSH são dois arquivos. O privado "
        "(<tt>~/.ssh/id_ed25519</tt>) nunca sai do seu computador. O público "
        "(<tt>~/.ssh/id_ed25519.pub</tt>) é o que você instala nos servidores "
        "— ele pode ser copiado à vontade.\n\n"
        '<tt>ssh-keygen -t ed25519 -C "seu-nome@notebook"</tt>\n\n'
        "O tipo <tt>ed25519</tt> é a escolha atual: curta, rápida e forte. "
        "Use <tt>rsa</tt> com 4096 bits só quando o servidor for antigo "
        "demais para aceitar ed25519.\n\n"
        "Coloque uma senha na chave. Ela protege o arquivo caso seu notebook "
        "seja perdido, e o agente (seção 5) faz você digitá-la uma vez por "
        "sessão, não a cada conexão."
    ),
    "guide.install.title": "2. Instalar a chave no servidor",
    "guide.install.body": (
        "<tt>ssh-copy-id -i ~/.ssh/id_ed25519.pub usuario@servidor</tt>\n\n"
        "Ele pede a senha do usuário uma última vez e acrescenta sua chave "
        "pública ao arquivo <tt>~/.ssh/authorized_keys</tt> lá no servidor.\n\n"
        "Se preferir fazer à mão, é exatamente isso: copiar o conteúdo do "
        "arquivo <tt>.pub</tt> e colar como uma nova linha em "
        "<tt>~/.ssh/authorized_keys</tt> do servidor. Uma chave por linha."
    ),
    "guide.permissions.title": "3. Ajustar as permissões no servidor",
    "guide.permissions.body": (
        "Esta é a causa mais comum de a chave não funcionar sem dar erro "
        "nenhum. O sshd ignora <tt>authorized_keys</tt> em silêncio quando as "
        "permissões estão abertas demais.\n\n"
        "<tt>chmod 700 ~/.ssh</tt>\n"
        "<tt>chmod 600 ~/.ssh/authorized_keys</tt>\n"
        "<tt>chown -R $USER:$USER ~/.ssh</tt>\n\n"
        "A pasta e o arquivo precisam pertencer ao usuário que vai logar. Se "
        "você criou o arquivo com <tt>sudo</tt>, provavelmente o dono ficou "
        "sendo o root."
    ),
    "guide.password.title": "4. Fechar a porta da senha",
    "guide.password.body": (
        "Com a chave funcionando, desligue o login por senha. É o que tira "
        "seu servidor da mira dos robôs que varrem a internet testando "
        "senhas.\n\n"
        "Em <tt>/etc/ssh/sshd_config</tt>, no servidor:\n"
        "<tt>PasswordAuthentication no</tt>\n"
        "<tt>PermitRootLogin prohibit-password</tt>\n\n"
        "<tt>sudo systemctl reload ssh</tt>\n\n"
        "Antes de fechar a sessão em que você fez isso, abra uma segunda "
        "sessão e confirme que ela entra. Se algo estiver errado, a primeira "
        "sessão ainda está aberta para você desfazer. Fechar a única sessão "
        "que você tinha é como trancar a porta com a chave do lado de dentro."
    ),
    "guide.agent.title": "5. Usar o agente",
    "guide.agent.body": (
        "O <tt>ssh-agent</tt> guarda a chave destravada durante a sessão, "
        "para você digitar a senha dela uma vez só.\n\n"
        "<tt>ssh-add ~/.ssh/id_ed25519</tt>\n\n"
        "Melhor ainda: coloque <tt>AddKeysToAgent yes</tt> na conexão e a "
        "chave entra no agente sozinha na primeira vez que for usada.\n\n"
        "No GNOME o agente já sobe junto com a sua sessão gráfica, então não "
        "há nada para configurar além disso."
    ),
    "guide.debug.title": "Quando algo falha",
    "guide.debug.body": (
        "<tt>ssh -vvv apelido</tt>\n\n"
        "Mostra cada passo da negociação: quais chaves foram oferecidas, o "
        "que o servidor aceitou e onde parou. É verboso de propósito — leia "
        "de baixo para cima, a última linha antes do erro costuma ser a "
        "resposta.\n\n"
        "<tt>ssh -G apelido</tt>\n\n"
        "Mostra a configuração final que o ssh vai usar para esse apelido, "
        "já com tudo que veio dos blocos curinga. Útil quando uma opção "
        "parece não estar valendo: aqui você vê o valor que realmente conta."
    ),
    "guide.about.title": "O arquivo de configuração",
    "guide.about.body": (
        "Cada conexão desta lista é um bloco <tt>Host</tt> no seu "
        "<tt>~/.ssh/config</tt>. O apelido que você escolhe passa a valer em "
        "tudo que fala SSH: <tt>ssh apelido</tt>, <tt>scp arquivo "
        "apelido:/tmp</tt>, <tt>rsync</tt>, e o Git quando o repositório usa "
        "<tt>git@apelido:...</tt>.\n\n"
        "Um bloco com curinga, como <tt>Host *</tt> ou "
        "<tt>Host *.exemplo.com</tt>, vale para todas as conexões que casarem "
        "com o padrão. Serve para definir padrões uma vez só.\n\n"
        "A regra que surpreende: para cada opção, o OpenSSH usa a "
        "<b>primeira</b> definição que encontrar no arquivo, de cima para "
        "baixo. Não é a última que ganha. Por isso os blocos curinga "
        "costumam ficar no fim — assim eles preenchem o que os blocos "
        "específicos deixaram em branco, em vez de atropelá-los."
    ),
}
