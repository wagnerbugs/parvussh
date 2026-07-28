"""Testes do parser. Rode com: python3 -m pytest -q  (ou python3 tests/...)"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from parvussh.sshconfig import Block, Entry, parse_text  # noqa: E402

SAMPLE = """\
# Configuração pessoal
# não mexer sem café

Host vps-blog
    HostName 203.0.113.10
    User deploy
    Port 2222
    # essa chave é a antiga
    IdentityFile ~/.ssh/id_blog

Host github.com
    User git
    IdentityFile=~/.ssh/id_github
    IdentitiesOnly yes

Match host *.interno
    ProxyJump bastion

Host *
    ServerAliveInterval 60
    AddKeysToAgent yes
"""


def render(blocks):
    lines = []
    for b in blocks:
        lines.extend(b.render())
    return "\n".join(lines).strip("\n") + "\n"


def test_roundtrip_sem_edicao():
    blocks = parse_text(SAMPLE, Path("config"))
    assert render(blocks) == SAMPLE, "arquivo intocado deve sair idêntico"


def test_encontra_hosts():
    blocks = parse_text(SAMPLE, Path("config"))
    hosts = [b for b in blocks if b.kind == "host"]
    assert [h.title for h in hosts] == ["vps-blog", "github.com", "*"]


def test_le_valores_com_igual_e_espaco():
    blocks = parse_text(SAMPLE, Path("config"))
    gh = next(b for b in blocks if b.title == "github.com")
    assert gh.get("IdentityFile") == "~/.ssh/id_github"
    assert gh.get("User") == "git"
    assert gh.get("Port") == ""


def test_match_preservado():
    blocks = parse_text(SAMPLE, Path("config"))
    match = next(b for b in blocks if b.kind == "match")
    assert match.get("ProxyJump") == "bastion"
    assert render([match]).startswith("Match host *.interno")


def test_edicao_toca_so_o_bloco_alterado():
    blocks = parse_text(SAMPLE, Path("config"))
    vps = next(b for b in blocks if b.title == "vps-blog")
    comentario = vps.comments_for("IdentityFile")
    vps.entries = [
        Entry("HostName", "198.51.100.7"),
        Entry("User", "deploy"),
        Entry("Port", "2222"),
        Entry("IdentityFile", "~/.ssh/id_blog", comentario),
    ]
    vps.dirty = True
    saida = render(blocks)

    assert "198.51.100.7" in saida
    assert "203.0.113.10" not in saida
    # comentário de cabeçalho e o comentário interno sobrevivem
    assert "# não mexer sem café" in saida
    assert "    # essa chave é a antiga" in saida
    # os outros blocos saem byte a byte iguais
    assert "    IdentityFile=~/.ssh/id_github" in saida
    assert "Match host *.interno" in saida


def test_bloco_novo_recebe_linha_em_branco():
    blocks = parse_text(SAMPLE, Path("config"))
    novo = Block(kind="host", patterns=["vps-novo"], lead=[""], dirty=True,
                 entries=[Entry("HostName", "10.0.0.1"), Entry("User", "root")])
    blocks.append(novo)
    saida = render(blocks)
    assert saida.endswith("Host vps-novo\n    HostName 10.0.0.1\n    User root\n")


def test_curinga_detectado():
    blocks = parse_text(SAMPLE, Path("config"))
    assert next(b for b in blocks if b.title == "*").is_pattern
    assert not next(b for b in blocks if b.title == "vps-blog").is_pattern


def test_subtitulo_do_card():
    blocks = parse_text(SAMPLE, Path("config"))
    vps = next(b for b in blocks if b.title == "vps-blog")
    assert vps.subtitle() == "deploy@203.0.113.10:2222"


def test_arquivo_vazio_nao_quebra():
    blocks = parse_text("", Path("config"))
    assert render(blocks) == "\n"
    assert [b for b in blocks if b.kind == "host"] == []


def test_linha_estranha_preservada():
    texto = "Host x\n    HostName a\n    !!! lixo aqui\n"
    blocks = parse_text(texto, Path("config"))
    assert render(blocks) == texto


if __name__ == "__main__":
    falhas = 0
    for nome, func in sorted(globals().items()):
        if not nome.startswith("test_"):
            continue
        try:
            func()
            print(f"  ok  {nome}")
        except AssertionError as erro:
            falhas += 1
            print(f"FALHA  {nome}: {erro}")
    print("\n" + ("tudo verde" if not falhas else f"{falhas} falha(s)"))
    raise SystemExit(1 if falhas else 0)