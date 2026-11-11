# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Controlla che il PC sia pronto per il corso.

Si lancia dalla cartella del repository, in un terminale (PowerShell su Windows):

    uv run tools/verifica_ambiente.py

Verifica Python, Git, uv, Visual Studio Code, l'estensione dell'assistente AI,
la rete e la presenza dei dati del corso. Per ogni problema stampa cosa fare.
Usa solo la libreria standard di Python: non installa nulla.
"""

from __future__ import annotations

import os
import platform
import shutil
import ssl
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

# Radice del repository: la cartella sopra "tools", qualunque sia la cartella da cui si lancia.
REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = REPO_ROOT / "dati" / "set-dati.xlsx"

MIN_PYTHON = (3, 12)
COMMAND_TIMEOUT = 30  # secondi per ogni comando esterno
NETWORK_TIMEOUT = 5  # secondi per ogni sito

CLAUDE_EXTENSION = "anthropic.claude-code"
CODEX_EXTENSION = "openai.chatgpt"

# Siti da cui uv scarica i pacchetti Python: senza questi non si installa nulla.
PACKAGE_HOSTS = ["https://pypi.org/simple/", "https://files.pythonhosted.org/"]
# Servizi degli assistenti AI: ne basta uno, quello che usate.
AI_HOSTS = ["https://api.anthropic.com/", "https://chatgpt.com/"]

# Windows 11 24H2 con l'aggiornamento minimo per il sandbox di Codex senza diritti di amministratore.
CODEX_MIN_BUILD = 26100
CODEX_MIN_UBR = 9278

LABELS = {"ok": "[OK]", "warning": "[ATTENZIONE]", "error": "[ERRORE]"}


@dataclass
class CheckResult:
    name: str
    status: str  # "ok" | "warning" | "error"
    detail: str
    hint: str = ""


def run_command(args: list[str]) -> tuple[bool, str]:
    """Lancia un comando e restituisce (riuscito, prima riga dell'output)."""
    try:
        completed = subprocess.run(
            args, capture_output=True, text=True, timeout=COMMAND_TIMEOUT
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, str(exc)
    output = (completed.stdout or completed.stderr or "").strip()
    first_line = output.splitlines()[0] if output else ""
    return completed.returncode == 0, first_line


def check_python() -> CheckResult:
    version = ".".join(str(n) for n in sys.version_info[:3])
    if sys.version_info[:2] >= MIN_PYTHON:
        return CheckResult("Python", "ok", version)
    return CheckResult(
        "Python",
        "error",
        f"{version}, serve almeno 3.12",
        "Lanciate lo script con 'uv run tools/verifica_ambiente.py': uv usa la versione giusta.",
    )


def check_git() -> CheckResult:
    git = shutil.which("git")
    if git:
        ok, output = run_command([git, "--version"])
        if ok:
            return CheckResult("Git", "ok", output)
    return CheckResult(
        "Git",
        "error",
        "non trovato",
        "Installate Git for Windows da https://git-scm.com/download/win e aprite un terminale nuovo.",
    )


def check_git_identity() -> CheckResult:
    git = shutil.which("git")
    if not git:
        return CheckResult("Identità Git", "warning", "Git non trovato, controllo saltato")
    missing = [
        key
        for key in ("user.name", "user.email")
        if not run_command([git, "config", "--get", key])[0]
    ]
    if not missing:
        return CheckResult("Identità Git", "ok", "nome ed email impostati")
    return CheckResult(
        "Identità Git",
        "warning",
        "manca " + " e ".join(missing) + ": senza, i commit non si possono fare",
        'git config --global user.name "Nome Cognome"  e  git config --global user.email "nome@azienda.it"',
    )


def check_uv() -> CheckResult:
    uv = shutil.which("uv")
    if uv:
        ok, output = run_command([uv, "--version"])
        if ok:
            return CheckResult("uv", "ok", output)
    return CheckResult(
        "uv",
        "error",
        "non trovato",
        'Da PowerShell: powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    )


def find_vscode() -> str | None:
    # Su Windows il comando è "code.cmd": shutil.which lo trova, il nome semplice no.
    return shutil.which("code")


def check_vscode() -> CheckResult:
    code = find_vscode()
    if code:
        ok, output = run_command([code, "--version"])
        if ok:
            return CheckResult("Visual Studio Code", "ok", output)
    return CheckResult(
        "Visual Studio Code",
        "error",
        "comando 'code' non trovato",
        "Installate VS Code (User setup) con l'opzione 'Add to PATH', poi aprite un terminale nuovo.",
    )


def list_extensions() -> list[str]:
    code = find_vscode()
    if not code:
        return []
    try:
        completed = subprocess.run(
            [code, "--list-extensions"],
            capture_output=True,
            text=True,
            timeout=COMMAND_TIMEOUT,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [line.strip().lower() for line in completed.stdout.splitlines()]


def check_ai_extension(extensions: list[str]) -> CheckResult:
    found = [
        label
        for ext_id, label in ((CLAUDE_EXTENSION, "Claude Code"), (CODEX_EXTENSION, "Codex"))
        if ext_id in extensions
    ]
    if found:
        return CheckResult("Estensione AI", "ok", ", ".join(found))
    return CheckResult(
        "Estensione AI",
        "error",
        "né Claude Code né Codex installati in VS Code",
        "In VS Code: Ctrl+Shift+X, cercate 'Claude Code' (Anthropic) o 'Codex' (OpenAI), installate e fate l'accesso.",
    )


def check_api_key_env() -> CheckResult:
    # Si controlla solo se la variabile esiste: il valore non si legge e non si stampa.
    if "ANTHROPIC_API_KEY" in os.environ:
        return CheckResult(
            "ANTHROPIC_API_KEY",
            "warning",
            "la variabile è impostata: Claude Code userebbe le API a consumo invece dell'abbonamento",
            "Togliete la variabile d'ambiente ANTHROPIC_API_KEY e aprite un terminale nuovo.",
        )
    return CheckResult("ANTHROPIC_API_KEY", "ok", "non impostata")


def windows_ubr() -> int:
    """Numero di aggiornamento di Windows (UBR), letto dal registro. 0 se non disponibile."""
    try:
        import winreg

        key = winreg.OpenKey(
            winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion"
        )
        value, _ = winreg.QueryValueEx(key, "UBR")
        return int(value)
    except (ImportError, OSError, ValueError):
        return 0


def check_windows_build(extensions: list[str]) -> CheckResult:
    if platform.system() != "Windows":
        return CheckResult("Windows per Codex", "ok", "controllo solo per Windows")
    build = sys.getwindowsversion().build
    ubr = windows_ubr()
    detail = f"build {build}.{ubr}"
    recent = build > CODEX_MIN_BUILD or (build == CODEX_MIN_BUILD and ubr >= CODEX_MIN_UBR)
    if recent or CODEX_EXTENSION not in extensions:
        return CheckResult("Windows per Codex", "ok", detail)
    return CheckResult(
        "Windows per Codex",
        "warning",
        detail + ": Codex senza diritti di amministratore richiede Windows 11 24H2 aggiornato",
        "Usate Claude Code, oppure chiedete al vostro IT di aggiornare Windows.",
    )


def probe(url: str) -> tuple[str, str]:
    """Prova a raggiungere un sito. Restituisce (esito, dettaglio): esito è "ok", "cert" o "down"."""
    request = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "verifica-ambiente-corso"}
    )
    try:
        with urllib.request.urlopen(request, timeout=NETWORK_TIMEOUT) as response:
            return "ok", f"risponde ({response.status})"
    except urllib.error.HTTPError as exc:
        # Il sito ha risposto, anche se con un codice di errore: la rete funziona.
        return "ok", f"risponde ({exc.code})"
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, ssl.SSLError):
            return "cert", "errore di certificato"
        return "down", f"non raggiungibile ({exc.reason})"
    except ssl.SSLError:
        return "cert", "errore di certificato"
    except (TimeoutError, OSError) as exc:
        return "down", f"non raggiungibile ({exc})"


def network_hint(outcome: str) -> str:
    if outcome == "cert":
        return (
            "Probabile proxy aziendale che ispeziona il traffico. Provate a impostare "
            "UV_SYSTEM_CERTS=true e sentite il vostro IT."
        )
    return "Controllate la connessione; se siete in rete aziendale, sentite il vostro IT per proxy e firewall."


def check_network() -> list[CheckResult]:
    results = []
    for url in PACKAGE_HOSTS:
        outcome, detail = probe(url)
        host = url.split("/")[2]
        if outcome == "ok":
            results.append(CheckResult(f"Rete {host}", "ok", detail))
        else:
            results.append(CheckResult(f"Rete {host}", "error", detail, network_hint(outcome)))

    ai_results = []
    for url in AI_HOSTS:
        outcome, detail = probe(url)
        host = url.split("/")[2]
        hint = "" if outcome == "ok" else network_hint(outcome) + " Ne basta uno: quello del vostro assistente."
        ai_results.append(
            CheckResult(f"Rete {host}", "ok" if outcome == "ok" else "warning", detail, hint)
        )
    if all(r.status != "ok" for r in ai_results):
        for r in ai_results:
            r.status = "error"
    return results + ai_results


def check_course_data() -> CheckResult:
    if DATA_FILE.is_file():
        return CheckResult("Dati del corso", "ok", str(DATA_FILE.relative_to(REPO_ROOT)))
    return CheckResult(
        "Dati del corso",
        "error",
        f"non trovo {DATA_FILE}",
        "Lanciate lo script dalla cartella clonata: git clone ..., poi cd laboratorio-strumenti-interni-ai.",
    )


def print_result(result: CheckResult) -> None:
    print(f"{LABELS[result.status]} {result.name}: {result.detail}")
    if result.hint and result.status != "ok":
        print(f"    -> {result.hint}")


def main() -> int:
    # Su console che non supportano qualche carattere, meglio un "?" che un errore.
    sys.stdout.reconfigure(errors="replace")

    print("Verifica dell'ambiente per il corso")
    print("===================================")
    extensions = list_extensions()
    results = [
        check_python(),
        check_git(),
        check_git_identity(),
        check_uv(),
        check_vscode(),
        check_ai_extension(extensions),
        check_api_key_env(),
        check_windows_build(extensions),
        *check_network(),
        check_course_data(),
    ]
    for result in results:
        print_result(result)

    errors = sum(r.status == "error" for r in results)
    warnings = sum(r.status == "warning" for r in results)
    print()
    if errors:
        what = "un problema" if errors == 1 else f"{errors} problemi"
        print(f"Ci sono {what} da risolvere prima del corso.")
    elif warnings:
        what = "un avviso" if warnings == 1 else f"{warnings} avvisi"
        print(f"Si può partire, ma c'è da guardare {what}.")
    else:
        print("Tutto pronto per il corso.")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
