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

```bash
make setup    # dependências do sistema + venv
make run      # abre o aplicativo
make check    # lint + testes + testes de interface
```

## Licença

GPL-3.0-or-later. Veja [`LICENSE`](LICENSE).
