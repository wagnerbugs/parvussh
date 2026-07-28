# ParvuSsh

Gerencia suas conexões SSH lendo e escrevendo o seu `~/.ssh/config` de verdade.
Sem banco paralelo, sem formato proprietário, sem etapa de importação.

*Parvus*, do latim: pequeno. O nome é a lista de não-objetivos em uma palavra.

> **Em construção.** Esta página é um marcador — o texto completo (capturas de
> tela, instalação, o contrato de escrita do arquivo e a lista de
> não-objetivos) entra no marco M14. Acompanhe o andamento em
> [`BUILD_PLAN.md`](BUILD_PLAN.md) e as decisões em
> [`docs/DECISIONS.md`](docs/DECISIONS.md).

## Requisitos

Ubuntu 26.04 ou equivalente, GNOME 50, Python 3.11+, GTK 4.12+, libadwaita 1.5+.

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
                 openssh-client
```

## Desenvolvimento

Uma vez só, no primeiro clone:

```bash
make setup
```

Instala os pacotes do sistema (`python3-gi`, GTK 4, libadwaita, `openssh-client`,
`xvfb`) e cria o `.venv` com `--system-site-packages` — o PyGObject vem da
distribuição de propósito, é o caminho que funciona sem dor de compilação.

Depois disso, os cinco comandos do dia a dia:

| Comando | O que faz | Precisa de tela? |
|---|---|---|
| `make run` | abre o aplicativo | sim |
| `make test` | testes de lógica pura, rápidos | não |
| `make test-gui` | testes de interface, sob `xvfb` | não |
| `make lint` | `ruff check` + `ruff format --check` | não |
| `make check` | os três acima, em ordem | não |

Rode `make check` antes de cada commit.

### Testando sem arriscar o seu `~/.ssh/config`

`make run` abre contra o seu arquivo de verdade. Para brincar à vontade, aponte
o aplicativo para um `HOME` descartável:

```bash
mkdir -p /tmp/parvussh-teste/.ssh && chmod 700 /tmp/parvussh-teste/.ssh
cp ~/.ssh/config /tmp/parvussh-teste/.ssh/config    # opcional: uma cópia real
HOME=/tmp/parvussh-teste .venv/bin/python -m parvussh
```

O aplicativo resolve tudo a partir de `Path.home()`, então ele lê e grava
apenas dentro de `/tmp/parvussh-teste/.ssh`. Seu arquivo real fica intocado.

### Se algo der errado no arquivo real

Toda gravação faz uma cópia datada antes de tocar no arquivo:

```bash
ls -lt ~/.ssh/config.bak-*              # da mais recente para a mais antiga
diff ~/.ssh/config ~/.ssh/config.bak-20260728-183000
cp ~/.ssh/config.bak-20260728-183000 ~/.ssh/config   # voltar atrás
```

As cópias nunca são apagadas pelo aplicativo. Limpe-as quando quiser.

## Licença

GPL-3.0-or-later. Veja [`LICENSE`](LICENSE).
