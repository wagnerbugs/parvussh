"""The key-setup guide and the "how it works" text (pt-BR).

Keys are `guide.<section>.title` and `guide.<section>.body`, matching
`parvussh/data/guide.py`. Bodies are Pango markup: `<tt>` around commands and
file names, `<b>` for the one rule worth emphasising, nothing else. Any
literal `&` or `<` must be escaped.

The audience is a developer who runs a couple of VPSs and has never been told
*why* any of this is the way it is. Each section says what to do, and then the
one thing that usually goes wrong. Two habits come from that audience: say
which machine a command runs on, and never let "senha" stand for the account
password and the key's passphrase in the same breath.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    "guide.create.title": "1. Criar a chave (na sua máquina)",
    "guide.create.body": (
        "Uma chave SSH é um par de arquivos, criado no seu computador — nunca "
        "no servidor. O privado (<tt>~/.ssh/id_ed25519</tt>) nunca sai daqui. "
        "O público (<tt>~/.ssh/id_ed25519.pub</tt>) é o que você instala nos "
        "servidores — ele pode ser copiado à vontade.\n\n"
        '<tt>ssh-keygen -t ed25519 -C "seu-nome@notebook"</tt>\n\n'
        "O tipo <tt>ed25519</tt> é a escolha atual: curta, rápida e forte. "
        "Use <tt>rsa</tt> com 4096 bits só quando o servidor for antigo "
        "demais para aceitar ed25519.\n\n"
        "Coloque uma senha nessa chave. Repare no nome: é a senha da chave, "
        "que fica só no seu computador e não tem relação nenhuma com a senha "
        "do usuário lá no servidor. Ela protege o arquivo caso seu notebook "
        "seja perdido, e o agente (seção 5) faz você digitá-la uma vez por "
        "sessão, não a cada conexão."
    ),
    "guide.install.title": "2. Instalar a chave no servidor",
    "guide.install.body": (
        "O comando abaixo roda na sua máquina, não no servidor — é ele que "
        "leva a chave até lá.\n\n"
        "<tt>ssh-copy-id -i ~/.ssh/id_ed25519.pub usuario@servidor</tt>\n\n"
        "Ele pede a senha do usuário uma última vez e acrescenta sua chave "
        "pública ao arquivo <tt>~/.ssh/authorized_keys</tt> lá no servidor.\n\n"
        "Se o SSH do servidor não estiver na porta 22, a porta vai no "
        "comando:\n\n"
        "<tt>ssh-copy-id -p 2222 -i ~/.ssh/id_ed25519.pub usuario@servidor</tt>"
        "\n\n"
        "Dá para fazer à mão, e é exatamente isso: copiar o conteúdo do "
        "arquivo <tt>.pub</tt> e colar como uma nova linha em "
        "<tt>~/.ssh/authorized_keys</tt> do servidor. Uma chave por linha, sem "
        "quebra no meio — mesmo que o editor mostre a linha dobrada na "
        "tela.\n\n"
        "Antes de seguir para o próximo passo, confirme que funcionou: abra "
        "outro terminal e conecte. Se entrar sem pedir a senha do usuário, a "
        "chave está no lugar."
    ),
    "guide.permissions.title": "3. Ajustar as permissões no servidor",
    "guide.permissions.body": (
        "Esta é a causa mais comum de a chave não funcionar sem dar erro "
        "nenhum. O sshd ignora <tt>authorized_keys</tt> em silêncio quando as "
        "permissões estão abertas demais, e do lado de cá você só vê o pedido "
        "de senha voltar.\n\n"
        "<tt>chmod 700 ~/.ssh</tt>\n"
        "<tt>chmod 600 ~/.ssh/authorized_keys</tt>\n"
        "<tt>chown -R $USER:$USER ~/.ssh</tt>\n\n"
        "Rode isso logado como o próprio usuário que vai entrar. Se você "
        "criou o arquivo com <tt>sudo</tt>, o dono ficou sendo o root e a "
        "chave não vai funcionar — nesse caso escreva o nome na mão, como em "
        "<tt>chown -R maria:maria /home/maria/.ssh</tt>.\n\n"
        "A pasta pessoal também conta: se <tt>/home/maria</tt> puder ser "
        "gravada por outros usuários, o sshd recusa pelo mesmo motivo. "
        "<tt>chmod go-w ~</tt> tira só a escrita e resolve, sem abrir a pasta "
        "para quem não precisa.\n\n"
        "Quando nada explica a recusa, o servidor explica: o motivo aparece "
        "em <tt>/var/log/auth.log</tt>, ou em <tt>journalctl -u ssh</tt> — "
        "<tt>-u sshd</tt> em algumas distribuições."
    ),
    "guide.password.title": "4. Fechar a porta da senha",
    "guide.password.body": (
        "Com a chave funcionando, desligue o login por senha. É o que tira "
        "seu servidor da mira dos robôs que varrem a internet testando "
        "senhas.\n\n"
        "Antes de editar, guarde uma cópia:\n\n"
        "<tt>sudo cp /etc/ssh/sshd_config /etc/ssh/sshd_config.bak</tt>\n\n"
        "Em <tt>/etc/ssh/sshd_config</tt>, no servidor:\n"
        "<tt>PasswordAuthentication no</tt>\n"
        "<tt>PermitRootLogin prohibit-password</tt>\n\n"
        "A segunda linha libera o root apenas por chave: ele continua "
        "entrando, e senha nenhuma é aceita para essa conta.\n\n"
        "A armadilha das VPS: quase toda imagem de nuvem traz arquivos em "
        "<tt>/etc/ssh/sshd_config.d/</tt> que são lidos antes do arquivo "
        "principal. E vale a <b>primeira</b> definição encontrada, a mesma "
        "regra do lado do cliente — um <tt>PasswordAuthentication yes</tt> "
        "ali dentro anula o seu <tt>no</tt> sem avisar nada. Confira:\n\n"
        "<tt>sudo grep -r PasswordAuthentication /etc/ssh/sshd_config.d/</tt>"
        "\n\n"
        "Valide a sintaxe antes de recarregar. Se o primeiro comando acusar "
        "erro, não rode o segundo:\n\n"
        "<tt>sudo sshd -t</tt>\n"
        "<tt>sudo systemctl reload ssh</tt>\n\n"
        "Em algumas distribuições o serviço se chama <tt>sshd</tt> em vez de "
        "<tt>ssh</tt>.\n\n"
        "Agora confirme o que ficou valendo de verdade, que nem sempre é o "
        "que está escrito nos arquivos:\n\n"
        "<tt>sudo sshd -T | grep -i passwordauthentication</tt>\n\n"
        "Antes de fechar a sessão em que você fez isso, abra uma segunda "
        "sessão e confirme que ela entra. Se algo estiver errado, a primeira "
        "sessão ainda está aberta para você desfazer. Fechar a única sessão "
        "que você tinha é como trancar a porta com a chave do lado de "
        "dentro.\n\n"
        "Numa VPS há ainda o console do painel do provedor, que entra na "
        "máquina sem passar pelo SSH. Vale abrir o painel e achar onde ele "
        "fica antes de precisar dele."
    ),
    "guide.agent.title": "5. Usar o agente",
    "guide.agent.body": (
        "O <tt>ssh-agent</tt> guarda a chave destravada durante a sessão, "
        "para você digitar a senha dela uma vez só.\n\n"
        "<tt>ssh-add ~/.ssh/id_ed25519</tt>\n\n"
        "Melhor ainda: coloque <tt>AddKeysToAgent yes</tt> na conexão e a "
        "chave entra no agente sozinha na primeira vez que for usada.\n\n"
        "No GNOME o agente já sobe junto com a sua sessão gráfica, então não "
        "há nada para configurar além disso.\n\n"
        "Para ver o que o agente já tem carregado: <tt>ssh-add -l</tt>."
    ),
    "guide.debug.title": "Quando algo falha",
    "guide.debug.body": (
        "<tt>ssh -v apelido</tt>\n\n"
        "Mostra cada passo da negociação: quais chaves foram oferecidas, o "
        "que o servidor aceitou e onde parou. Se precisar de mais detalhe, "
        "<tt>-vv</tt> e <tt>-vvv</tt> abrem mais. Leia de baixo para cima — a "
        "última linha antes do erro costuma ser a resposta.\n\n"
        "Um erro que engana: <tt>Too many authentication failures</tt>. Não é "
        "o servidor recusando a sua chave. É o ssh oferecendo, uma a uma, "
        "todas as chaves que encontrou, até o servidor cortar a conexão por "
        "excesso de tentativas — muitas vezes antes de chegar na certa. "
        "Ligue <tt>IdentitiesOnly</tt> na conexão e ele passa a oferecer só a "
        "chave declarada ali.\n\n"
        "<tt>ssh -G apelido</tt>\n\n"
        "Mostra a configuração final que o ssh vai usar para esse apelido, "
        "já com tudo que veio dos blocos curinga. Útil quando uma opção "
        "parece não estar valendo: aqui você vê o valor que realmente "
        "conta.\n\n"
        "<tt>sudo sshd -T</tt>\n\n"
        "O mesmo, do lado do servidor: a configuração efetiva do sshd, já "
        "resolvida entre o arquivo principal e os de "
        "<tt>/etc/ssh/sshd_config.d/</tt>.\n\n"
        "E quando a chave é recusada sem explicação, o motivo está no "
        "servidor, em <tt>/var/log/auth.log</tt> ou em "
        "<tt>journalctl -u ssh</tt>."
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
        "específicos deixaram em branco, em vez de atropelá-los.\n\n"
        "Blocos <tt>Match</tt> são lidos e gravados de volta intactos, mas "
        "não aparecem nesta lista nem são editáveis por aqui. Edite-os no seu "
        "editor de texto — o aplicativo não vai atrapalhar."
    ),
}
