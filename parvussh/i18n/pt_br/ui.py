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
    # -- editor -----------------------------------------------------------
    "editor.title": "Conexão",
    "editor.save": "Salvar",
    "editor.test": "Testar",
    "editor.test_tooltip": "Tenta conectar sem salvar",
    "editor.more_tooltip": "Mais ações",
    "editor.empty.title": "Escolha uma conexão",
    "editor.empty.description": "Ou use o + para cadastrar a primeira.",
    # -- dialogs ----------------------------------------------------------
    "dialog.understood": "Entendi",
    "dialog.close": "Fechar",
    "dialog.cancel": "Cancelar",
    # -- errors -----------------------------------------------------------
    "error.read_config": "Não deu para ler o ~/.ssh/config",
}
