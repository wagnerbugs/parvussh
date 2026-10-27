"""Window, sidebar, editor, dialog and command line copy (pt-BR).

House style:

- Sentence case. "Criar chave", never "Criar Chave".
- A button names the action it performs, and the confirmation echoes the same
  verb: "Salvar" -> "Salvo em ~/.ssh/config".
- An error says what happened **and** what to do next. Never "Erro ao salvar."
- Empty states invite an action; they do not apologise.
- Field labels use the real OpenSSH option name, so the user can search the
  man page for what they see on screen.
- No exclamation marks, no "Ops!", no emoji.
"""

from __future__ import annotations

STRINGS: dict[str, str] = {
    # -- application ------------------------------------------------------
    "app.name": "ParvuSsh",
    "app.comments": "Gerencia o ~/.ssh/config sem esconder o ~/.ssh/config.",
    "app.developer": "wagnerbugs",
    # -- command line -----------------------------------------------------
    "cli.description": (
        "Gerencia as conexões do ~/.ssh/config. Sem argumentos, abre a janela."
    ),
    "cli.list_help": "lista as conexões do ~/.ssh/config e sai",
    "cli.no_hostname": "sem HostName",
    "cli.wildcard": "padrão curinga",
    "cli.no_config": (
        "Ainda não existe {path}. Abra o ParvuSsh para cadastrar a primeira conexão."
    ),
    "cli.empty": (
        "Nenhuma conexão em {path}. Abra o ParvuSsh para cadastrar a primeira."
    ),
    "cli.error.load": (
        "Não foi possível ler {path}: {detail}. Confira as permissões do arquivo."
    ),
    # -- menus ------------------------------------------------------------
    "menu.help": "Ajuda e dicas",
    "menu.reload": "Recarregar do disco",
    "menu.about": "Sobre o ParvuSsh",
    "menu.preferences": "Preferências",
    "menu.duplicate": "Duplicar",
    "menu.delete": "Excluir",
    "menu.order.title": "Ordenar",
    "menu.order.file": "Ordem do arquivo",
    "menu.order.name": "Nome (A-Z)",
    # -- sidebar ----------------------------------------------------------
    "sidebar.title": "Conexões",
    "sidebar.new_tooltip": "Nova conexão (Ctrl+N)",
    "sidebar.menu_tooltip": "Menu",
    "sidebar.filter_placeholder": "Filtrar conexões…",
    "sidebar.no_hostname": "sem HostName",
    "sidebar.wildcard_subtitle": "Padrão curinga",
    "sidebar.wildcard_tooltip": (
        "Bloco curinga: vale para todas as conexões que casarem com o padrão."
    ),
    "sidebar.empty": "Nenhuma conexão ainda. Use o + para cadastrar a primeira.",
    "sidebar.no_matches": "Nada encontrado para “{query}”.",
    # -- editor -----------------------------------------------------------
    "editor.title": "Conexão",
    "editor.save": "Salvar",
    "editor.test": "Testar",
    "editor.test_tooltip": "Tenta conectar sem salvar",
    "editor.connect": "Acessar",
    "editor.connect_tooltip": (
        "Abre um terminal rodando ssh com este apelido. O terminal se escolhe "
        "em Preferências."
    ),
    "editor.more_tooltip": "Mais ações",
    "editor.help_tooltip": "O que cada opção faz",
    "editor.empty.title": "Escolha uma conexão",
    "editor.empty.description": "Ou use o + para cadastrar a primeira.",
    "editor.group.connection": "Conexão",
    "editor.group.connection_description": (
        "Deixe em branco o que não usar: campos vazios não vão para o arquivo."
    ),
    # Labels carry the real OpenSSH option name so the user can look it up.
    "editor.field.host": "Host — o apelido que você digita",
    "editor.field.hostname": "HostName — endereço real",
    "editor.field.user": "User",
    "editor.field.port": "Port",
    "editor.group.extras": "Opções adicionais",
    "editor.group.extras_empty": (
        "Nenhuma opção extra. Use o + para procurar pelo nome."
    ),
    "editor.error.empty_alias": "O apelido em Host não pode ficar vazio.",
    "editor.error.port_not_a_number": "Port aceita apenas números.",
    # -- saving -----------------------------------------------------------
    "new.alias": "nova-conexao",
    "save.done": "Salvo em {path}",
    "save.nothing_changed": "Nada mudou desde o último salvamento.",
    "save.failed.heading": "O arquivo não foi gravado",
    "save.failed.body": (
        "O ssh recusou a configuração, então nada foi alterado no disco."
    ),
    "conflict.heading": "O {path} mudou desde que foi aberto",
    "conflict.body": (
        "Outro programa alterou o arquivo no mesmo trecho que você editou, "
        "então nada foi gravado. A lista foi recarregada com o {path} como "
        "está agora: confira e repita a sua edição."
    ),
    "backups.left": (
        "As cópias antigas continuam em {folder}, porque a Lixeira as recusou. "
        "O aplicativo tenta de novo no próximo salvamento."
    ),
    "unsaved.heading": "Alterações não salvas",
    "unsaved.body": ("“{alias}” tem mudanças que ainda não foram gravadas no arquivo."),
    "unsaved.discard": "Descartar",
    # -- add-option popover -----------------------------------------------
    "addoption.tooltip": "Adicionar opção",
    "addoption.placeholder": "Digite: ServerAlive…",
    "addoption.no_matches": "Nenhuma opção com esse nome.",
    # -- key picker -------------------------------------------------------
    "keypicker.tooltip": "Escolher uma chave de ~/.ssh",
    "keypicker.empty": "Nenhuma chave em ~/.ssh ainda.",
    "keypicker.create": "Criar chave…",
    "keypicker.browse": "Procurar arquivo…",
    "keypicker.summary": "{kind} · {bits} bits · {comment}",
    "keypicker.summary_no_comment": "{kind} · {bits} bits",
    "keypicker.undescribed": "Não deu para ler os detalhes desta chave.",
    "filepicker.tooltip": "Procurar arquivo",
    "filepicker.title": "Escolher {name}",
    # -- new key dialog ---------------------------------------------------
    "newkey.title": "Criar chave",
    "newkey.create": "Criar chave",
    "newkey.default_name": "id_ed25519_novo",
    "newkey.field.name": "Nome do arquivo",
    "newkey.field.kind": "Tipo",
    "newkey.field.kind_subtitle": "ed25519 é a escolha recomendada",
    "newkey.field.comment": "Comentário",
    "newkey.field.passphrase": "Senha da chave",
    "newkey.field.confirm": "Repita a senha",
    "newkey.note": (
        "A chave é gravada em ~/.ssh. Deixar a senha em branco cria uma chave "
        "sem proteção."
    ),
    "newkey.created": "Chave criada em {path}",
    "newkey.failed.heading": "Não deu para criar a chave",
    "newkey.error.empty_name": "Dê um nome ao arquivo da chave.",
    "newkey.error.mismatch": "As duas senhas não são iguais.",
    "newkey.error.exists": ("Já existe um arquivo em {path}. Escolha outro nome."),
    "newkey.error.no_tool": (
        "O ssh-keygen não foi encontrado. Instale o pacote openssh-client."
    ),
    # -- connection test --------------------------------------------------
    # One title/detail pair per status in parvussh/core/tester.py. Core hands
    # back a code; the wording is here.
    "test.running": "Testando {alias}…",
    "test.output_label": "Saída do ssh",
    "test.error.no_alias": "Informe o apelido antes de testar.",
    "test.error.wildcard": "Blocos com curinga não podem ser testados direto.",
    "test.auth.title": "Conectado",
    "test.auth.detail": (
        "Login concluído com a chave configurada. Está pronto para usar."
    ),
    "test.reachable.title": "Servidor respondeu",
    "test.reachable.detail": (
        "Endereço, porta e usuário estão válidos: o servidor chegou a pedir "
        "autenticação. Faltou só a senha ou a chave, que o teste não envia."
    ),
    "test.dns.title": "Nome não encontrado",
    "test.dns.detail": (
        "O endereço em HostName não foi resolvido. Confira se não há erro de "
        "digitação no domínio."
    ),
    "test.refused.title": "Conexão recusada",
    "test.refused.detail": (
        "A máquina respondeu, mas nada está escutando nessa porta. Confira o "
        "valor de Port e se o sshd está no ar."
    ),
    "test.timeout.title": "O servidor não respondeu",
    "test.timeout.detail": (
        "Sem resposta dentro do tempo limite. Costuma ser firewall, IP errado "
        "ou máquina desligada."
    ),
    "test.network.title": "Rede inacessível",
    "test.network.detail": (
        "Não há caminho até esse endereço a partir daqui. Verifique sua rede "
        "ou a necessidade de VPN."
    ),
    "test.hostkey.title": "A identidade do servidor mudou",
    "test.hostkey.detail": (
        "A chave do host não bate com a guardada em known_hosts. Pode ser "
        "reinstalação do servidor — ou alguém no meio do caminho. Confirme "
        "antes de remover a linha antiga."
    ),
    "test.config.title": "Configuração inválida",
    "test.config.detail": ("O ssh recusou uma das opções. A saída abaixo indica qual."),
    "test.no-ssh.title": "ssh não encontrado",
    "test.no-ssh.detail": ("Instale o pacote openssh-client para usar o teste."),
    "test.unknown.title": "Não deu para concluir o teste",
    "test.unknown.detail": (
        "O ssh terminou com código {code}. A saída completa está abaixo."
    ),
    # -- connecting -------------------------------------------------------
    # Statuses from parvussh/core/terminal.py. `connect.notice` is printed
    # inside the terminal itself, under ssh's own message.
    "connect.running": "Abrindo um terminal para {alias}…",
    "connect.error.unsaved": (
        "Salve antes de acessar: o terminal lê o arquivo, e esta alteração "
        "ainda não está nele."
    ),
    "connect.error.wildcard": (
        "Blocos com curinga valem para vários servidores, então não há um só "
        "para acessar."
    ),
    "connect.notice": (
        "A conexão falhou ou caiu, e o ssh disse por quê logo acima. O botão "
        "Testar do ParvuSsh explica o erro. Pressione Enter para fechar."
    ),
    "connect.no_terminal.heading": "Nenhum terminal encontrado",
    "connect.no_terminal.body": (
        "Nenhum destes está instalado: {names}. Escolha o seu em Preferências, "
        "ou rode ssh {alias} no terminal que você já usa."
    ),
    "connect.failed.heading": "O terminal não abriu",
    "connect.failed.body": (
        "O {terminal} encerrou logo ao iniciar, com código {code}. Se você o "
        "escolheu em Preferências, confira se ele precisa de um argumento antes "
        "do comando, como -e. Enquanto isso, rode ssh {alias} num terminal."
    ),
    "connect.missing.heading": "O terminal escolhido não foi encontrado",
    "connect.missing.body": (
        "{name} não está instalado, ou o caminho mudou. Corrija em Preferências, "
        "ou apague o campo para usar o terminal padrão do sistema."
    ),
    # -- preferences ------------------------------------------------------
    "prefs.title": "Preferências",
    "prefs.terminal.title": "Terminal",
    "prefs.terminal.description": (
        "O programa que o botão Acessar abre. Deixe vazio para usar o padrão do "
        "sistema, ou escreva o caminho de outro: /usr/bin/xterm. Se ele precisar "
        "de um argumento antes do comando, inclua-o: alacritty -e."
    ),
    "prefs.terminal.command": "Comando do terminal",
    "prefs.terminal.in_use": "Em uso",
    "prefs.terminal.checking": "Procurando…",
    "prefs.terminal.automatic": "{name}, o padrão do sistema",
    "prefs.terminal.custom": "{name}, o que você escolheu",
    "prefs.terminal.missing": (
        "{name} não foi encontrado. Confira o caminho, ou apague o campo para "
        "usar o padrão do sistema."
    ),
    "prefs.terminal.none": (
        "Nenhum terminal conhecido está instalado. Escreva acima o caminho do seu."
    ),
    "prefs.backups.title": "Cópias de segurança",
    "prefs.backups.description": (
        "Antes de cada gravação, o aplicativo deixa uma cópia ao lado do "
        "arquivo, como config.bak-20261024-131455. Ficam as mais novas; as mais "
        "velhas vão para a Lixeira. Vale também para os arquivos trazidos por "
        "Include. Cópias com o mesmo padrão de nome, feitas por outros "
        "programas, contam juntas."
    ),
    "prefs.backups.keep": "Cópias do ~/.ssh/config a guardar",
    "prefs.error.save": "A preferência não foi gravada em {path}: {detail}",
    # -- option rows ------------------------------------------------------
    "rows.remove_tooltip": "Remover {name}",
    "rows.hint_with_example": "{description}  ex.: {example}",
    # -- help dialog ------------------------------------------------------
    "help.title": "Ajuda",
    "help.page.options": "Opções",
    "help.page.keys": "Chaves",
    "help.page.about": "Como funciona",
    "help.with_example": "{description}\nExemplo: {example}",
    "help.with_values": "{description}\nValores: {values}",
    "help.copy_tooltip": "Copiar",
    "help.copied": "Copiado para a área de transferência",
    # -- duplicate and delete ---------------------------------------------
    "duplicate.alias": "{alias}-copia",
    "duplicate.alias_numbered": "{alias}-copia-{number}",
    "duplicate.done": "Conexão duplicada. Ajuste o apelido e salve.",
    "delete.heading": "Excluir “{alias}”?",
    "delete.body": (
        "O bloco sai do arquivo assim que você confirmar. Uma cópia do config "
        "anterior fica na mesma pasta, com a data no nome."
    ),
    "delete.done": "Conexão excluída.",
    # -- dialogs ----------------------------------------------------------
    "dialog.understood": "Entendi",
    "dialog.close": "Fechar",
    "dialog.cancel": "Cancelar",
    # -- errors -----------------------------------------------------------
    "error.read_config": "Não deu para ler o ~/.ssh/config",
}
