"""Testa uma conexão sem precisar salvar o config antes.

A ideia: grava o bloco em um arquivo temporário, chama o ssh em modo
não-interativo e lê o motivo da falha. Chegar até o pedido de senha já
significa que host, porta e rede estão corretos.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass

TIMEOUT = 25


@dataclass
class TestResult:
    ok: bool
    status: str
    title: str
    detail: str
    output: str


def _result(ok, status, title, detail, output):
    return TestResult(ok, status, title, detail, output)


def test(alias: str, config_text: str, timeout: int = TIMEOUT) -> TestResult:
    fd, tmp = tempfile.mkstemp(suffix=".sshconfig", prefix="parvussh-")
    try:
        with os.fdopen(fd, "w") as fh:
            fh.write(config_text)
        os.chmod(tmp, 0o600)
        cmd = [
            "ssh", "-F", tmp,
            "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=8",
            "-o", "NumberOfPasswordPrompts=0",
            "-o", "StrictHostKeyChecking=accept-new",
            alias, "true",
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=timeout)
        except FileNotFoundError:
            return _result(False, "no-ssh", "ssh não encontrado",
                           "Instale o pacote openssh-client para usar o teste.",
                           "")
        except subprocess.TimeoutExpired:
            return _result(False, "timeout", "O servidor não respondeu",
                           "Passou de {}s sem resposta. Verifique o endereço, "
                           "a porta e se há firewall no caminho."
                           .format(timeout), "")
        out = (proc.stdout + proc.stderr).strip()
        return _interpret(proc.returncode, out)
    finally:
        os.unlink(tmp)


def _interpret(code: int, out: str) -> TestResult:
    low = out.lower()

    if code == 0:
        return _result(True, "auth", "Conectado",
                       "Login concluído com a chave configurada. Está pronto "
                       "para usar.", out)

    if "permission denied" in low or "no supported authentication" in low:
        return _result(True, "reachable", "Servidor respondeu",
                       "Endereço, porta e usuário estão válidos: o servidor "
                       "chegou a pedir autenticação. Faltou só a senha ou a "
                       "chave, que o teste não envia.", out)

    if "could not resolve" in low or "name or service not known" in low:
        return _result(False, "dns", "Nome não encontrado",
                       "O endereço em HostName não foi resolvido. Confira se "
                       "não há erro de digitação no domínio.", out)

    if "connection refused" in low:
        return _result(False, "refused", "Conexão recusada",
                       "A máquina respondeu, mas nada está escutando nessa "
                       "porta. Confira o valor de Port e se o sshd está no ar.",
                       out)

    if "timed out" in low or "timeout" in low:
        return _result(False, "timeout", "O servidor não respondeu",
                       "Sem resposta dentro do tempo limite. Costuma ser "
                       "firewall, IP errado ou máquina desligada.", out)

    if "no route to host" in low or "network is unreachable" in low:
        return _result(False, "network", "Rede inacessível",
                       "Não há caminho até esse endereço a partir daqui. "
                       "Verifique sua rede ou a necessidade de VPN.", out)

    if "host key verification failed" in low or "remote host identification" in low:
        return _result(False, "hostkey", "A identidade do servidor mudou",
                       "A chave do host não bate com a guardada em "
                       "known_hosts. Pode ser reinstalação do servidor — ou "
                       "alguém no meio do caminho. Confirme antes de remover a "
                       "linha antiga.", out)

    if "bad configuration" in low or "line" in low and "invalid" in low:
        return _result(False, "config", "Configuração inválida",
                       "O ssh recusou uma das opções. A saída abaixo indica "
                       "qual.", out)

    return _result(False, "unknown", "Não deu para concluir o teste",
                   "O ssh terminou com código {}. A saída completa está "
                   "abaixo.".format(code), out)