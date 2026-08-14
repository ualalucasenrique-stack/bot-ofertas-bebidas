"""Retry con backoff exponencial para llamadas a servicios externos frágiles.

Generaliza un patrón ya probado en sistema-precios/odoo_utils.py: reintentar
errores transitorios (red, timeouts, 5xx), pero fallar inmediato ante errores
lógicos (credenciales inválidas, 4xx, una excepción propia de la API) porque
reintentar eso no cambia el resultado — solo demora que alguien se entere de
que algo está mal. bot-ofertas-bebidas/vtex_client.py resolvía esto con su
propia implementación, sin esa distinción; este módulo es el punto único
para no volver a resolverlo distinto cada vez.
"""

from __future__ import annotations

import functools
import time
from typing import Callable, Iterable, TypeVar

T = TypeVar("T")


class RetryExhausted(Exception):
    """Se agotaron los reintentos sin éxito. Envuelve el último error real
    para que quien llama pueda inspeccionarlo (`error.last_error`) en vez de
    perder el motivo original detrás de un mensaje genérico."""

    def __init__(self, attempts: int, last_error: Exception):
        super().__init__(f"Falló después de {attempts} intentos: {last_error}")
        self.attempts = attempts
        self.last_error = last_error


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_attempts: int = 3,
    initial_backoff_seconds: float = 5.0,
    backoff_multiplier: float = 2.0,
    retryable_exceptions: Iterable[type[Exception]] = (Exception,),
    fatal_exceptions: Iterable[type[Exception]] = (),
) -> T:
    """Ejecuta fn() reintentando ante errores transitorios.

    fatal_exceptions se chequea primero: si el error es instancia de alguna
    de esas clases, se relanza de inmediato sin consumir reintentos. Todo lo
    que matchea retryable_exceptions (por defecto, cualquier Exception) se
    reintenta con backoff exponencial hasta max_attempts.
    """
    backoff = initial_backoff_seconds
    last_error: Exception | None = None
    fatal = tuple(fatal_exceptions)
    retryable = tuple(retryable_exceptions)

    for attempt in range(1, max_attempts + 1):
        try:
            return fn()
        except fatal:
            raise
        except retryable as error:
            last_error = error
            if attempt == max_attempts:
                break
            time.sleep(backoff)
            backoff *= backoff_multiplier

    raise RetryExhausted(max_attempts, last_error)


def with_retry(
    *,
    max_attempts: int = 3,
    initial_backoff_seconds: float = 5.0,
    backoff_multiplier: float = 2.0,
    retryable_exceptions: Iterable[type[Exception]] = (Exception,),
    fatal_exceptions: Iterable[type[Exception]] = (),
):
    """Versión decorador de retry_with_backoff, para reemplazar directo una
    función que hoy hace su propio try/except manual (como
    vtex_client._get_with_retries)."""

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_attempts=max_attempts,
                initial_backoff_seconds=initial_backoff_seconds,
                backoff_multiplier=backoff_multiplier,
                retryable_exceptions=retryable_exceptions,
                fatal_exceptions=fatal_exceptions,
            )

        return wrapper

    return decorator
