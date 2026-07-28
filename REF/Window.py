"""Janela principal: lista de conexões à esquerda, formulário à direita."""

from __future__ import annotations

import threading
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk  # noqa: E402

from . import guide, keys, keywords, tester  # noqa: E402
from .keywords import BOOL, ENUM, IDENTITY, INT, PATH, Keyword  # noqa: E402
from .sshconfig import ConfigError, ConfigSet, Entry  # noqa: E402


# --------------------------------------------------------------------------
# Linha de opção: escolhe o widget conforme o tipo da keyword
# --------------------------------------------------------------------------
class OptionRow:
    def __init__(self, win: "ParvuSshWindow", kw: Keyword, value: str,
                 comments: list[str] | None = None):
        self.win = win
        self.kw = kw
        self.comments = comments or []
        hint = f"{kw.desc}  ex.: {kw.example}" if kw.example else kw.desc

        if kw.kind == BOOL:
            self.row = Adw.SwitchRow(title=kw.name, subtitle=kw.desc)
            self.row.set_active(value.strip().lower() in ("yes", "true", "1"))
            self.row.connect("notify::active", win.mark_dirty)

        elif kw.kind == ENUM:
            values = list(kw.values)
            if value and value not in values:
                values.append(value)
            self.model = Gtk.StringList.new(values)
            self.row = Adw.ComboRow(title=kw.name, subtitle=kw.desc,
                                    model=self.model)
            if value in values:
                self.row.set_selected(values.index(value))
            self.row.connect("notify::selected", win.mark_dirty)

        elif kw.kind == INT:
            self.row = Adw.SpinRow.new_with_range(kw.lo, kw.hi, 1)
            self.row.set_title(kw.name)
            self.row.set_subtitle(hint)
            try:
                self.row.set_value(int(value))
            except (TypeError, ValueError):
                self.row.set_value(kw.lo)
            self.row.connect("notify::value", win.mark_dirty)

        else:  # STR, PATH, IDENTITY
            self.row = Adw.EntryRow(title=kw.name)
            self.row.set_text(value)
            self.row.set_tooltip_text(hint)
            self.row.connect("changed", win.mark_dirty)
            if kw.kind == IDENTITY:
                self.row.add_suffix(self._keys_button())
            elif kw.kind == PATH:
                self.row.add_suffix(self._file_button())

        remove = Gtk.Button(icon_name="user-trash-symbolic",
                            valign=Gtk.Align.CENTER,
                            tooltip_text=f"Remover {kw.name}",
                            css_classes=["flat", "circular"])
        remove.connect("clicked", lambda *_: self.win.remove_option(self))
        self.row.add_suffix(remove)

    # -- seletores ---------------------------------------------------------
    def _keys_button(self) -> Gtk.MenuButton:
        button = Gtk.MenuButton(icon_name="dialog-password-symbolic",
                                valign=Gtk.Align.CENTER,
                                tooltip_text="Escolher uma chave de ~/.ssh",
                                css_classes=["flat", "circular"])
        popover = Gtk.Popover()
        button.set_popover(popover)
        popover.connect("show", lambda *_: self._fill_keys(popover))
        return button

    def _fill_keys(self, popover: Gtk.Popover) -> None:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12,
                      margin_top=12, margin_bottom=12,
                      margin_start=12, margin_end=12)
        found = keys.list_keys()
        if found:
            listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                  css_classes=["boxed-list"])
            for key in found:
                row = Adw.ActionRow(title=key.path.name, subtitle=key.summary,
                                    activatable=True)
                row.connect("activated", self._pick_key, key.display_path,
                            popover)
                listbox.append(row)
            scroller = Gtk.ScrolledWindow(
                min_content_width=340, max_content_height=260,
                propagate_natural_height=True, hscrollbar_policy=Gtk.PolicyType.NEVER)
            scroller.set_child(listbox)
            box.append(scroller)
        else:
            box.append(Gtk.Label(label="Nenhuma chave em ~/.ssh ainda.",
                                 css_classes=["dim-label"]))

        new_key = Gtk.Button(label="Criar chave…")
        new_key.connect("clicked", self._new_key, popover)
        box.append(new_key)

        browse = Gtk.Button(label="Procurar arquivo…", css_classes=["flat"])
        browse.connect("clicked", lambda *_: (popover.popdown(),
                                              self._browse()))
        box.append(browse)
        popover.set_child(box)

    def _pick_key(self, _row, path: str, popover: Gtk.Popover) -> None:
        self.row.set_text(path)
        popover.popdown()

    def _new_key(self, _button, popover: Gtk.Popover) -> None:
        popover.popdown()
        NewKeyDialog(self.win, on_created=self.row.set_text).present(self.win)

    def _file_button(self) -> Gtk.Button:
        button = Gtk.Button(icon_name="document-open-symbolic",
                            valign=Gtk.Align.CENTER,
                            tooltip_text="Procurar arquivo",
                            css_classes=["flat", "circular"])
        button.connect("clicked", lambda *_: self._browse())
        return button

    def _browse(self) -> None:
        dialog = Gtk.FileDialog(title=f"Escolher {self.kw.name}")
        ssh_dir = Path.home() / ".ssh"
        if ssh_dir.is_dir():
            dialog.set_initial_folder(Gio.File.new_for_path(str(ssh_dir)))

        def done(source, result):
            try:
                gfile = source.open_finish(result)
            except GLib.Error:
                return
            path = Path(gfile.get_path())
            try:
                self.row.set_text("~/" + str(path.relative_to(Path.home())))
            except ValueError:
                self.row.set_text(str(path))

        dialog.open(self.win, None, done)

    # -- leitura -----------------------------------------------------------
    def value(self) -> str:
        if self.kw.kind == BOOL:
            return "yes" if self.row.get_active() else "no"
        if self.kw.kind == ENUM:
            return self.model.get_string(self.row.get_selected()) or ""
        if self.kw.kind == INT:
            return str(int(self.row.get_value()))
        return self.row.get_text().strip()


# --------------------------------------------------------------------------
# Popover do "+": digita e a lista filtra
# --------------------------------------------------------------------------
class AddOptionPopover(Gtk.Popover):
    def __init__(self, on_pick):
        super().__init__()
        self.on_pick = on_pick
        self.used: set[str] = set()

        self.search = Gtk.SearchEntry(placeholder_text="Digite: ServerAlive…")
        self.search.connect("search-changed", lambda *_: self._refresh())
        self.search.connect("activate", self._activate_first)

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.NONE,
                                   css_classes=["boxed-list"])
        self.listbox.connect("row-activated", self._on_activated)

        scroller = Gtk.ScrolledWindow(min_content_height=320,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(self.listbox)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10,
                      margin_top=10, margin_bottom=10,
                      margin_start=10, margin_end=10)
        box.set_size_request(420, -1)
        box.append(self.search)
        box.append(scroller)
        self.set_child(box)
        self.connect("show", self._on_show)

    def _on_show(self, *_):
        self.search.set_text("")
        self._refresh()
        self.search.grab_focus()

    def _refresh(self):
        while (child := self.listbox.get_first_child()) is not None:
            self.listbox.remove(child)
        for kw in keywords.search(self.search.get_text(), self.used):
            row = Adw.ActionRow(title=kw.name, subtitle=kw.desc,
                                activatable=True, subtitle_lines=2)
            row.keyword = kw
            self.listbox.append(row)

    def _activate_first(self, *_):
        row = self.listbox.get_row_at_index(0)
        if row is not None:
            self._on_activated(self.listbox, row)

    def _on_activated(self, _listbox, row):
        self.popdown()
        self.on_pick(row.keyword)


# --------------------------------------------------------------------------
# Diálogo de criação de chave
# --------------------------------------------------------------------------
class NewKeyDialog(Adw.Dialog):
    def __init__(self, win, on_created=None):
        super().__init__(title="Criar chave", content_width=460)
        self.win = win
        self.on_created = on_created

        self.name = Adw.EntryRow(title="Nome do arquivo")
        self.name.set_text("id_ed25519_novo")
        self.kind = Adw.ComboRow(
            title="Tipo", subtitle="ed25519 é a escolha recomendada",
            model=Gtk.StringList.new(list(keys.KEY_TYPES)))
        self.comment = Adw.EntryRow(title="Comentário")
        self.comment.set_text(f"{GLib.get_user_name()}@{GLib.get_host_name()}")
        self.passphrase = Adw.PasswordEntryRow(title="Senha da chave")
        self.confirm = Adw.PasswordEntryRow(title="Repita a senha")

        group = Adw.PreferencesGroup()
        for row in (self.name, self.kind, self.comment, self.passphrase,
                    self.confirm):
            group.add(row)

        note = Gtk.Label(
            label="A chave é gravada em ~/.ssh. Deixar a senha em branco cria "
                  "uma chave sem proteção.",
            wrap=True, xalign=0, css_classes=["dim-label", "caption"],
            margin_top=6)
        group.add(note)

        page = Adw.PreferencesPage()
        page.add(group)

        cancel = Gtk.Button(label="Cancelar")
        cancel.connect("clicked", lambda *_: self.close())
        create = Gtk.Button(label="Criar chave",
                            css_classes=["suggested-action"])
        create.connect("clicked", self._create)

        header = Adw.HeaderBar(show_end_title_buttons=False,
                               show_start_title_buttons=False)
        header.pack_start(cancel)
        header.pack_end(create)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(page)
        self.set_child(view)

    def _create(self, *_):
        name = self.name.get_text().strip()
        if not name:
            self.win.toast("Dê um nome ao arquivo da chave.")
            return
        if self.passphrase.get_text() != self.confirm.get_text():
            self.win.toast("As duas senhas não são iguais.")
            return
        path = Path.home() / ".ssh" / name
        kind = keys.KEY_TYPES[self.kind.get_selected()]
        ok, message = keys.generate(path, kind, self.comment.get_text().strip(),
                                    self.passphrase.get_text())
        if not ok:
            self.win.show_message("Não deu para criar a chave", message)
            return
        self.close()
        self.win.toast(f"Chave criada: ~/.ssh/{name}")
        if self.on_created:
            self.on_created(f"~/.ssh/{name}")


# --------------------------------------------------------------------------
# Ajuda
# --------------------------------------------------------------------------
class HelpDialog(Adw.PreferencesDialog):
    def __init__(self):
        super().__init__(title="Ajuda", search_enabled=True)

        options = Adw.PreferencesPage(title="Opções", icon_name="view-list-symbolic")
        for group_name in keywords.GROUPS:
            group = Adw.PreferencesGroup(title=group_name)
            for kw in keywords.KEYWORDS:
                if kw.group != group_name:
                    continue
                subtitle = kw.desc
                if kw.example:
                    subtitle += f"\nExemplo: {kw.example}"
                elif kw.values:
                    subtitle += "\nValores: " + ", ".join(kw.values)
                group.add(Adw.ActionRow(title=kw.name, subtitle=subtitle,
                                        subtitle_lines=4))
            options.add(group)
        self.add(options)

        chaves = Adw.PreferencesPage(title="Chaves",
                                     icon_name="dialog-password-symbolic")
        for title, text in guide.GUIDE:
            group = Adw.PreferencesGroup(title=title)
            group.add(Gtk.Label(label=text, wrap=True, xalign=0,
                                use_markup=True, selectable=True))
            chaves.add(group)
        self.add(chaves)

        sobre = Adw.PreferencesPage(title="Como funciona",
                                    icon_name="help-about-symbolic")
        group = Adw.PreferencesGroup(title="O arquivo de configuração")
        group.add(Gtk.Label(label=guide.ABOUT_CONFIG, wrap=True, xalign=0,
                            use_markup=True, selectable=True))
        sobre.add(group)
        self.add(sobre)


# --------------------------------------------------------------------------
# Janela
# --------------------------------------------------------------------------
class ParvuSshWindow(Adw.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_title("ParvuSsh")
        self.set_default_size(1020, 700)

        self.config: ConfigSet | None = None
        self.current = None
        self.options: list[OptionRow] = []
        self.dirty = False
        self._loading = False

        self.toasts = Adw.ToastOverlay()
        self.split = Adw.NavigationSplitView(min_sidebar_width=280,
                                             max_sidebar_width=360)
        self.toasts.set_child(self.split)
        self.set_content(self.toasts)

        self._install_actions()
        self._build_sidebar()
        self._build_editor()
        self.reload()

    # -- ações -------------------------------------------------------------
    def _install_actions(self):
        for name, callback in (
            ("help", lambda *_: HelpDialog().present(self)),
            ("reload", lambda *_: self.reload()),
            ("new", lambda *_: self.new_host()),
            ("save", lambda *_: self.save_current()),
            ("test", lambda *_: self.test_current()),
            ("delete", lambda *_: self.delete_current()),
            ("duplicate", lambda *_: self.duplicate_current()),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", callback)
            self.add_action(action)
        app = self.get_application()
        if app:
            app.set_accels_for_action("win.save", ["<Control>s"])
            app.set_accels_for_action("win.new", ["<Control>n"])
            app.set_accels_for_action("win.help", ["F1"])

    # -- coluna da esquerda ------------------------------------------------
    def _build_sidebar(self):
        self.search = Gtk.SearchEntry(placeholder_text="Filtrar conexões…",
                                      margin_start=12, margin_end=12,
                                      margin_bottom=6)
        self.search.connect("search-changed",
                            lambda *_: self.listbox.invalidate_filter())

        self.listbox = Gtk.ListBox(selection_mode=Gtk.SelectionMode.SINGLE,
                                   css_classes=["boxed-list"],
                                   margin_start=12, margin_end=12,
                                   margin_bottom=12, valign=Gtk.Align.START)
        self.listbox.set_filter_func(self._filter_row)
        self.listbox.connect("row-selected", self._on_row_selected)

        scroller = Gtk.ScrolledWindow(vexpand=True,
                                      hscrollbar_policy=Gtk.PolicyType.NEVER)
        scroller.set_child(self.listbox)

        menu = Gio.Menu()
        menu.append("Ajuda e dicas", "win.help")
        menu.append("Recarregar do disco", "win.reload")

        header = Adw.HeaderBar()
        add = Gtk.Button(icon_name="list-add-symbolic",
                         tooltip_text="Nova conexão (Ctrl+N)",
                         action_name="win.new")
        header.pack_start(add)
        header.pack_end(Gtk.MenuButton(icon_name="open-menu-symbolic",
                                       menu_model=menu,
                                       tooltip_text="Menu"))

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        box.append(self.search)
        box.append(scroller)

        view = Adw.ToolbarView()
        view.add_top_bar(header)
        view.set_content(box)
        self.split.set_sidebar(Adw.NavigationPage(title="Conexões", child=view))

    def _filter_row(self, row) -> bool:
        query = self.search.get_text().strip().lower()
        if not query:
            return True
        block = row.block
        haystack = f"{block.title} {block.get('HostName')} {block.get('User')}"
        return query in haystack.lower()

    # -- coluna da direita -------------------------------------------------
    def _build_editor(self):
        self.title_widget = Adw.WindowTitle(title="ParvuSsh")

        test_button = Gtk.Button(label="Testar", action_name="win.test",
                                 tooltip_text="Tenta conectar sem salvar")
        self.save_button = Gtk.Button(label="Salvar", action_name="win.save",
                                      css_classes=["suggested-action"])

        row_menu = Gio.Menu()
        row_menu.append("Duplicar", "win.duplicate")
        row_menu.append("Excluir", "win.delete")

        self.editor_header = Adw.HeaderBar(title_widget=self.title_widget)
        self.editor_header.pack_end(self.save_button)
        self.editor_header.pack_end(test_button)
        self.editor_header.pack_end(
            Gtk.MenuButton(icon_name="view-more-symbolic", menu_model=row_menu,
                           tooltip_text="Mais ações"))

        # formulário
        self.e_host = Adw.EntryRow(title="Host — o apelido que você digita")
        self.e_hostname = Adw.EntryRow(title="HostName — endereço real")
        self.e_user = Adw.EntryRow(title="User")
        self.e_port = Adw.EntryRow(title="Port")
        self.e_port.set_input_purpose(Gtk.InputPurpose.DIGITS)
        for row in (self.e_host, self.e_hostname, self.e_user, self.e_port):
            row.connect("changed", self.mark_dirty)

        basics = Adw.PreferencesGroup(
            title="Conexão",
            description="Deixe em branco o que não usar: campos vazios não vão "
                        "para o arquivo.")
        for row in (self.e_host, self.e_hostname, self.e_user, self.e_port):
            basics.add(row)

        self.add_popover = AddOptionPopover(self.add_option)
        add_button = Gtk.MenuButton(icon_name="list-add-symbolic",
                                    popover=self.add_popover,
                                    tooltip_text="Adicionar opção",
                                    css_classes=["flat"])
        help_button = Gtk.Button(icon_name="help-about-symbolic",
                                 action_name="win.help",
                                 tooltip_text="O que cada opção faz",
                                 css_classes=["flat"])
        suffix = Gtk.Box(spacing=6)
        suffix.append(help_button)
        suffix.append(add_button)

        self.extras = Adw.PreferencesGroup(title="Opções adicionais")
        self.extras.set_header_suffix(suffix)
        self.empty_extras = Gtk.Label(
            label="Nenhuma opção extra. Use o + para procurar pelo nome.",
            wrap=True, xalign=0, css_classes=["dim-label"])
        self.extras.add(self.empty_extras)

        self.form = Adw.PreferencesPage()
        self.form.add(basics)
        self.form.add(self.extras)

        self.placeholder = Adw.StatusPage(
            icon_name="network-server-symbolic",
            title="Escolha uma conexão",
            description="Ou use o + para cadastrar a primeira.")

        self.stack = Gtk.Stack()
        self.stack.add_named(self.placeholder, "empty")
        self.stack.add_named(self.form, "form")

        view = Adw.ToolbarView()
        view.add_top_bar(self.editor_header)
        view.set_content(self.stack)
        self.split.set_content(Adw.NavigationPage(title="Conexão", child=view))

    # -- carga da lista ----------------------------------------------------
    def reload(self):
        try:
            self.config = ConfigSet.load()
        except OSError as error:
            self.show_message("Não deu para ler o ~/.ssh/config", str(error))
            return
        self.current = None
        self.dirty = False
        self._fill_list()
        self._show_block(None)

    def _fill_list(self, select=None):
        self._loading = True
        while (child := self.listbox.get_first_child()) is not None:
            self.listbox.remove(child)
        target_row = None
        for block in self.config.hosts:
            row = Adw.ActionRow(title=GLib.markup_escape_text(block.title),
                                subtitle=block.subtitle())
            row.block = block
            icon = "emblem-system-symbolic" if block.is_pattern \
                else "network-server-symbolic"
            row.add_prefix(Gtk.Image.new_from_icon_name(icon))
            self.listbox.append(row)
            if block is select:
                target_row = row
        self._loading = False
        if target_row is not None:
            self.listbox.select_row(target_row)

    def _row_for(self, block):
        index = 0
        while (row := self.listbox.get_row_at_index(index)) is not None:
            if row.block is block:
                return row
            index += 1
        return None

    # -- seleção -----------------------------------------------------------
    def _on_row_selected(self, _listbox, row):
        if self._loading:
            return
        block = row.block if row is not None else None
        if self.dirty and self.current is not None and block is not self.current:
            self._ask_unsaved(block)
            return
        self._show_block(block)

    def _ask_unsaved(self, pending):
        dialog = Adw.AlertDialog(
            heading="Alterações não salvas",
            body=f"“{self.current.title}” tem mudanças que ainda não foram "
                 f"gravadas no arquivo.")
        dialog.add_response("discard", "Descartar")
        dialog.add_response("save", "Salvar")
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        def answered(_dialog, response):
            if response == "save" and not self.save_current(silent=True):
                return
            self.dirty = False
            self._show_block(pending)

        dialog.connect("response", answered)
        dialog.present(self)

    def _show_block(self, block):
        self.current = block
        self.dirty = False
        if block is None:
            self.stack.set_visible_child_name("empty")
            self.title_widget.set_title("ParvuSsh")
            self.title_widget.set_subtitle("")
            self.editor_header.set_sensitive(False)
            return

        self.editor_header.set_sensitive(True)
        self.stack.set_visible_child_name("form")
        self._loading = True

        self.e_host.set_text(block.title)
        self.e_hostname.set_text(block.get("HostName"))
        self.e_user.set_text(block.get("User"))
        self.e_port.set_text(block.get("Port"))

        for option in self.options:
            self.extras.remove(option.row)
        self.options = []

        for entry in block.entries:
            if entry.keyword.lower() in {b.lower() for b in keywords.BASIC}:
                continue
            kw = keywords.get(entry.keyword) or Keyword(
                entry.keyword, "str", "Opção não catalogada, preservada como "
                                      "está.")
            self.options.append(OptionRow(self, kw, entry.value, entry.comments))
        for option in self.options:
            self.extras.add(option.row)

        self._sync_extras_state()
        self.title_widget.set_title(block.title)
        source = self.config.file_of(block).path
        self.title_widget.set_subtitle(
            str(source).replace(str(Path.home()), "~"))
        self._loading = False

    def _sync_extras_state(self):
        self.empty_extras.set_visible(not self.options)
        self.add_popover.used = {o.kw.name.lower() for o in self.options}

    # -- edição ------------------------------------------------------------
    def mark_dirty(self, *_):
        if self._loading or self.current is None:
            return
        self.dirty = True
        self.title_widget.set_title("• " + self.e_host.get_text().strip())

    def add_option(self, kw: Keyword):
        option = OptionRow(self, kw, "")
        self.options.append(option)
        self.extras.add(option.row)
        self._sync_extras_state()
        self.mark_dirty()
        option.row.grab_focus()

    def remove_option(self, option: OptionRow):
        self.extras.remove(option.row)
        self.options.remove(option)
        self._sync_extras_state()
        self.mark_dirty()

    def new_host(self):
        block = self.config.add_host()
        self._fill_list(select=block)
        self.e_host.grab_focus()

    def duplicate_current(self):
        if self.current is None:
            return
        copy = self.config.duplicate(self.current)
        self._fill_list(select=copy)
        self.toast("Conexão duplicada. Ajuste o apelido e salve.")

    def delete_current(self):
        if self.current is None:
            return
        block = self.current
        dialog = Adw.AlertDialog(
            heading=f"Excluir “{block.title}”?",
            body="O bloco sai do arquivo assim que você confirmar. Um backup "
                 "do config anterior fica na mesma pasta.")
        dialog.add_response("cancel", "Cancelar")
        dialog.add_response("delete", "Excluir")
        dialog.set_response_appearance("delete",
                                       Adw.ResponseAppearance.DESTRUCTIVE)

        def answered(_dialog, response):
            if response != "delete":
                return
            self.config.remove(block)
            try:
                self.config.save()
            except ConfigError as error:
                self.show_message("O arquivo não foi gravado", str(error))
                self.reload()
                return
            self.dirty = False
            self._fill_list()
            self._show_block(None)
            self.toast("Conexão excluída.")

        dialog.connect("response", answered)
        dialog.present(self)

    # -- gravação ----------------------------------------------------------
    def _collect(self) -> bool:
        alias = self.e_host.get_text().strip()
        if not alias:
            self.toast("O apelido em Host não pode ficar vazio.")
            return False
        port = self.e_port.get_text().strip()
        if port and not port.isdigit():
            self.toast("Port aceita apenas números.")
            return False

        block = self.current
        old_comments = {e.keyword.lower(): e.comments for e in block.entries}
        entries = []
        for name, widget in (("HostName", self.e_hostname),
                             ("User", self.e_user),
                             ("Port", self.e_port)):
            value = widget.get_text().strip()
            if value:
                entries.append(Entry(name, value,
                                     old_comments.get(name.lower(), [])))
        for option in self.options:
            value = option.value()
            if value:
                entries.append(Entry(option.kw.name, value, option.comments))

        block.patterns = alias.split()
        block.entries = entries
        block.dirty = True
        return True

    def save_current(self, silent: bool = False) -> bool:
        if self.current is None or not self._collect():
            return False
        try:
            saved = self.config.save()
        except ConfigError as error:
            self.show_message(
                "O arquivo não foi gravado",
                f"O ssh recusou a configuração, então nada foi alterado no "
                f"disco.\n\n{error}")
            return False
        except OSError as error:
            self.show_message("O arquivo não foi gravado", str(error))
            return False

        self.dirty = False
        self._fill_list(select=self.current)
        self.title_widget.set_title(self.current.title)
        if not silent and saved:
            where = str(saved[0]).replace(str(Path.home()), "~")
            self.toast(f"Salvo em {where}")
        return True

    # -- teste -------------------------------------------------------------
    def test_current(self):
        alias = self.e_host.get_text().strip().split(" ")[0]
        if not alias:
            self.toast("Informe o apelido antes de testar.")
            return
        if any(c in alias for c in "*?"):
            self.toast("Blocos com curinga não podem ser testados direto.")
            return

        lines = [f"Host {alias}"]
        for name, widget in (("HostName", self.e_hostname),
                             ("User", self.e_user),
                             ("Port", self.e_port)):
            value = widget.get_text().strip()
            if value:
                lines.append(f"    {name} {value}")
        for option in self.options:
            value = option.value()
            if value:
                lines.append(f"    {option.kw.name} {value}")
        config_text = "\n".join(lines) + "\n"

        toast = Adw.Toast(title=f"Testando {alias}…", timeout=0)
        self.toasts.add_toast(toast)

        def work():
            result = tester.test(alias, config_text)
            GLib.idle_add(finish, result)

        def finish(result):
            toast.dismiss()
            self._show_test_result(result)
            return False

        threading.Thread(target=work, daemon=True).start()

    def _show_test_result(self, result):
        dialog = Adw.AlertDialog(heading=result.title, body=result.detail)
        if result.output:
            buffer = Gtk.TextView(editable=False, monospace=True,
                                  wrap_mode=Gtk.WrapMode.WORD_CHAR,
                                  top_margin=6, bottom_margin=6,
                                  left_margin=6, right_margin=6)
            buffer.get_buffer().set_text(result.output)
            scroller = Gtk.ScrolledWindow(min_content_height=120,
                                          max_content_height=220,
                                          propagate_natural_height=True,
                                          css_classes=["card"])
            scroller.set_child(buffer)
            expander = Gtk.Expander(label="Saída do ssh", child=scroller,
                                    margin_top=6)
            dialog.set_extra_child(expander)
        dialog.add_response("ok", "Fechar")
        dialog.present(self)

    # -- utilidades --------------------------------------------------------
    def toast(self, text: str):
        self.toasts.add_toast(Adw.Toast(title=text))

    def show_message(self, heading: str, body: str):
        dialog = Adw.AlertDialog(heading=heading, body=body)
        dialog.add_response("ok", "Entendi")
        dialog.present(self)