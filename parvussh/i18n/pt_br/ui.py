"""Window, sidebar, editor and dialog copy (pt-BR).

House style, from CLAUDE.md §7:

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
    # -- menus ------------------------------------------------------------
    "menu.help": "Ajuda e dicas",
    "menu.reload": "Recarregar do disco",
    "menu.about": "Sobre o ParvuSsh",
    "menu.duplicate": "Duplicar",
    "menu.delete": "Excluir",
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
    "editor.more_tooltip": "Mais ações",
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
    "unsaved.heading": "Alterações não salvas",
    "unsaved.body": ("“{alias}” tem mudanças que ainda não foram gravadas no arquivo."),
    "unsaved.discard": "Descartar",
    # -- add-option popover -----------------------------------------------
    "addoption.tooltip": "Adicionar opção",
    "addoption.placeholder": "Digite: ServerAlive…",
    "addoption.no_matches": "Nenhuma opção com esse nome.",
    # -- option rows ------------------------------------------------------
    "rows.remove_tooltip": "Remover {name}",
    "rows.hint_with_example": "{description}  ex.: {example}",
    # -- dialogs ----------------------------------------------------------
    "dialog.understood": "Entendi",
    "dialog.close": "Fechar",
    "dialog.cancel": "Cancelar",
    # -- errors -----------------------------------------------------------
    "error.read_config": "Não deu para ler o ~/.ssh/config",
}
