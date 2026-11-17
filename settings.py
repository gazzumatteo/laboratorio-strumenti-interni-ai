"""Configurazione salvata di ogni utenza (R14 di SPECIFICA.md).

Questo modulo non conosce Streamlit ed è l'unico a toccare `configurazione.json`:
gli altri moduli ricevono i valori già letti. Il file è JSON leggibile con un
editor di testo, con una voce per utenza. Una voce rovinata (o scritta male a
mano) non blocca le altre: si segnala e quell'utenza riparte dai valori predefiniti.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from benchmark import DEFAULT_MIN_VALID_DAYS, FixedBenchmark, MovingBenchmark
from indicators import Indicator, Input

CONFIG_VERSION = 1


class ConfigError(ValueError):
    """Una voce della configurazione non è valida: il messaggio è pensato per l'utente."""


@dataclass(frozen=True)
class IndicatorSettings:
    """Tutte le scelte di un'utenza: indicatore, benchmark, k, N e destinatari."""

    formula: str
    inputs: tuple[Input, ...]
    plausible_range: tuple[float, float]
    benchmark: FixedBenchmark | MovingBenchmark
    k: float
    persistence: int
    recipients: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        Indicator("", self.formula, self.inputs, self.plausible_range)  # stesse regole dell'indicatore
        if not (math.isfinite(self.k) and self.k > 0):
            raise ConfigError("k deve essere un numero maggiore di zero.")
        if isinstance(self.persistence, bool) or not isinstance(self.persistence, int) or self.persistence < 1:
            raise ConfigError("I giorni consecutivi per l'allarme (N) devono essere un intero maggiore di zero.")


@dataclass(frozen=True)
class LoadedSettings:
    """Le voci valide lette dal file, per nome di utenza, e gli avvisi su tutto il resto."""

    indicators: dict[str, IndicatorSettings]
    warnings: tuple[str, ...] = ()


# --- Lettura ---------------------------------------------------------------


def _mapping(value: Any, what: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigError(f"«{what}» deve essere un oggetto JSON.")
    return value


def _field(data: dict[str, Any], key: str) -> Any:
    if key not in data:
        raise ConfigError(f"manca «{key}».")
    return data[key]


def _number(value: Any, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ConfigError(f"«{what}» deve essere un numero.")
    return float(value)


def _integer(value: Any, what: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigError(f"«{what}» deve essere un numero intero.")
    return value


def _text(value: Any, what: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"«{what}» deve essere un testo non vuoto.")
    return value


def _day(value: Any, what: str) -> date:
    try:
        return date.fromisoformat(_text(value, what))
    except ValueError:
        raise ConfigError(f"«{what}» deve essere una data nel formato AAAA-MM-GG.") from None


def _parse_benchmark(raw: Any) -> FixedBenchmark | MovingBenchmark:
    data = _mapping(raw, "benchmark")
    min_valid_days = _integer(data.get("min_valid_days", DEFAULT_MIN_VALID_DAYS), "min_valid_days")
    kind = _field(data, "type")
    if kind == "fixed":
        return FixedBenchmark(_day(_field(data, "start"), "start"), _day(_field(data, "end"), "end"), min_valid_days)
    if kind == "moving":
        return MovingBenchmark(_integer(_field(data, "window_days"), "window_days"), min_valid_days)
    raise ConfigError("il tipo di benchmark deve essere «fixed» o «moving».")


def _parse_indicator(raw: Any) -> IndicatorSettings:
    data = _mapping(raw, "voce")
    raw_inputs = _field(data, "inputs")
    if not isinstance(raw_inputs, list):
        raise ConfigError("«inputs» deve essere una lista.")
    inputs = []
    for item in raw_inputs:
        item = _mapping(item, "inputs")
        inputs.append(Input(_text(_field(item, "column"), "column"), _number(_field(item, "factor"), "factor")))
    limits = _mapping(_field(data, "plausible_range"), "plausible_range")
    recipients = data.get("recipients", [])
    if not isinstance(recipients, list) or not all(isinstance(r, str) for r in recipients):
        raise ConfigError("«recipients» deve essere una lista di testi.")
    return IndicatorSettings(
        formula=_text(_field(data, "formula"), "formula"),
        inputs=tuple(inputs),
        plausible_range=(_number(_field(limits, "min"), "min"), _number(_field(limits, "max"), "max")),
        benchmark=_parse_benchmark(_field(data, "benchmark")),
        k=_number(_field(data, "k"), "k"),
        persistence=_integer(_field(data, "persistence_days"), "persistence_days"),
        recipients=tuple(recipients),
    )


def _read_document(path: Path) -> dict[str, Any]:
    """Il contenuto del file come dizionario; solleva `ConfigError` se non è utilizzabile."""
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ConfigError(f"il file non si può leggere ({exc}).") from exc
    document = _mapping(document, "il file")
    if document.get("version") != CONFIG_VERSION:
        raise ConfigError(f"versione del file non riconosciuta (attesa {CONFIG_VERSION}).")
    _mapping(document.get("indicators"), "indicators")
    return document


def load_settings(path: Path | str) -> LoadedSettings:
    """Legge la configurazione. File assente = nessuna voce e nessun avviso (valori predefiniti)."""
    path = Path(path)
    if not path.exists():
        return LoadedSettings({})
    try:
        document = _read_document(path)
    except ConfigError as exc:
        return LoadedSettings(
            {}, (f"{path.name}: {exc} Si usano i valori predefiniti; salvando, il file viene sostituito.",)
        )
    indicators: dict[str, IndicatorSettings] = {}
    warnings: list[str] = []
    for name, raw in document["indicators"].items():
        try:
            indicators[name] = _parse_indicator(raw)
        except ValueError as exc:  # ConfigError, ma anche gli errori di Input, Indicator e benchmark
            warnings.append(f"{path.name}, «{name}»: {str(exc).rstrip('.')}. Per questa utenza si usano i valori predefiniti.")
    return LoadedSettings(indicators, tuple(warnings))


# --- Scrittura -------------------------------------------------------------


def _to_json(settings: IndicatorSettings) -> dict[str, Any]:
    benchmark = settings.benchmark
    if isinstance(benchmark, FixedBenchmark):
        benchmark_json: dict[str, Any] = {
            "type": "fixed",
            "start": benchmark.start.isoformat(),
            "end": benchmark.end.isoformat(),
            "min_valid_days": benchmark.min_valid_days,
        }
    else:
        benchmark_json = {
            "type": "moving",
            "window_days": benchmark.window_days,
            "min_valid_days": benchmark.min_valid_days,
        }
    return {
        "formula": settings.formula,
        "inputs": [{"column": item.column, "factor": item.factor} for item in settings.inputs],
        "plausible_range": {"min": settings.plausible_range[0], "max": settings.plausible_range[1]},
        "benchmark": benchmark_json,
        "k": settings.k,
        "persistence_days": settings.persistence,
        "recipients": list(settings.recipients),
    }


def save_indicator_settings(path: Path | str, name: str, settings: IndicatorSettings) -> None:
    """Scrive la voce di un'utenza lasciando intatte le altre (anche quelle scritte a mano).

    Se il file non esiste o non è utilizzabile se ne crea uno nuovo. La scrittura è
    atomica: un file nuovo accanto a quello vero, poi sostituito, così un'interruzione
    non lo lascia a metà. Un errore del disco solleva `OSError`.
    """
    path = Path(path)
    try:
        document = _read_document(path) if path.exists() else {}
    except ConfigError:
        document = {}
    document = {"version": CONFIG_VERSION, "indicators": {**document.get("indicators", {}), name: _to_json(settings)}}
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)
