"""Interfaz común para avisar a un humano, con cooldown/dedup incorporado.

Nace del patrón de sistema-precios (DECISIONS.md, "Cooldown de 1 hora en
alertas de fallo de sync"): sin esto, un fallo persistente manda una alerta
por cada ciclo del bot y entrena al usuario a ignorarlas. Ese cooldown vive
acá una sola vez, en la clase base — cualquier canal de salida nuevo
(email, webhook, lo que sea) lo hereda gratis con solo implementar
`send_raw`.
"""

from __future__ import annotations

import time
from abc import ABC, abstractmethod

from .state import InMemoryStateStore, StateStore


class Notifier(ABC):
    """Envolvé un canal de salida concreto implementando `send_raw`. El
    cooldown se aplica en `notify`, no en `send_raw` — así `send_raw` se
    puede llamar directo (en un test, por ejemplo) sin el filtro de
    cooldown de por medio."""

    def __init__(self, state: StateStore | None = None, cooldown_seconds: float = 3600):
        self.state = state or InMemoryStateStore()
        self.cooldown_seconds = cooldown_seconds

    @abstractmethod
    def send_raw(self, subject: str, body: str) -> None:
        ...

    def notify(self, key: str, subject: str, body: str, *, force: bool = False) -> bool:
        """Manda el aviso, salvo que ya se haya mandado uno con la misma
        `key` dentro de la ventana de cooldown. Devuelve True si mandó algo,
        False si lo saltó por cooldown.

        `key` identifica DE QUÉ es la alerta (ej. "sync_fallo_stock"), no un
        id de mensaje puntual — todas las alertas con la misma key comparten
        el cooldown, igual que `sync_alerta_ultima_{script}` en
        sistema-precios. El cooldown se registra recién después de un envío
        exitoso: si send_raw lanza una excepción, no se guarda el timestamp,
        así el próximo ciclo reintenta en vez de quedar en falso silencio.
        """
        cooldown_key = f"notify_cooldown::{key}"
        last_sent = self.state.get(cooldown_key)
        now = time.time()

        if not force and last_sent is not None and (now - last_sent) < self.cooldown_seconds:
            return False

        self.send_raw(subject, body)
        self.state.set(cooldown_key, now)
        return True


class EmailNotifier(Notifier):
    """Envío por Gmail SMTP — mismo mecanismo que
    bot-ofertas-bebidas/email_notify.py, ahora con cooldown/dedup opcional
    heredado de Notifier en vez de mandar todo de nuevo en cada corrida."""

    def __init__(
        self,
        *,
        sender: str,
        app_password: str,
        recipient: str | None = None,
        smtp_host: str = "smtp.gmail.com",
        smtp_port: int = 465,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.sender = sender
        self.app_password = app_password
        self.recipient = recipient or sender
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port

    def send_raw(self, subject: str, body: str) -> None:
        import smtplib
        from email.mime.text import MIMEText

        message = MIMEText(body, "plain", "utf-8")
        message["Subject"] = subject
        message["From"] = self.sender
        message["To"] = self.recipient

        with smtplib.SMTP_SSL(self.smtp_host, self.smtp_port) as server:
            server.login(self.sender, self.app_password)
            server.sendmail(self.sender, [self.recipient], message.as_string())


class WebhookNotifier(Notifier):
    """Para canales tipo Discord/Slack que aceptan un webhook URL simple.
    No asume un formato de payload fijo — `payload_builder` arma el JSON
    que espera el canal elegido (Discord y Slack difieren en la forma)."""

    def __init__(self, *, webhook_url: str, payload_builder=None, **kwargs):
        super().__init__(**kwargs)
        self.webhook_url = webhook_url
        self.payload_builder = payload_builder or (
            lambda subject, body: {"content": f"**{subject}**\n{body}"}
        )

    def send_raw(self, subject: str, body: str) -> None:
        import requests

        response = requests.post(
            self.webhook_url, json=self.payload_builder(subject, body), timeout=10
        )
        response.raise_for_status()
