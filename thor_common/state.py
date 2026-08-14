"""Almacén clave-valor mínimo para estado persistente entre corridas.

Mismo concepto que la tabla app_state de sistema-precios
(thor_db.get_state/set_state), pero sin atarse a SQLite: acá el backend por
defecto es un JSON en disco, para que un agente sin DB propia (ej. uno que
corre en un runner efímero de CI) pueda usarlo igual, apuntando a un path
que persista entre corridas (un volumen montado, o restaurado vía cache
antes de correr). sistema-precios sigue usando thor_db para su propio
estado — esto es para todo lo nuevo que no tiene una DB propia todavía.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Protocol


class StateStore(Protocol):
    def get(self, key: str, default: Any = None) -> Any: ...
    def set(self, key: str, value: Any) -> None: ...


class JSONFileStateStore:
    """Backend por defecto: un único JSON en disco con todas las claves."""

    def __init__(self, path: Path | str):
        self.path = Path(path)

    def _read_all(self) -> dict:
        if not self.path.exists():
            return {}
        try:
            return json.loads(self.path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._read_all().get(key, default)

    def set(self, key: str, value: Any) -> None:
        data = self._read_all()
        data[key] = value
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )


class InMemoryStateStore:
    """Sin persistencia real — para tests, o para una corrida de un solo
    proceso donde no hace falta recordar nada entre ejecuciones distintas."""

    def __init__(self):
        self._data: dict[str, Any] = {}

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value
