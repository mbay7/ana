"""Who may open the owner pages (Usage, Build).

Both must hold: ANA_ADMIN is switched on, and ANA_ADMIN_PASSWORD is set and was
entered correctly. With no password set, the owner pages stay off.
"""
import hmac
import os

_ON = ("1", "true", "yes", "on")


def admin_available(env=None) -> bool:
    env = os.environ if env is None else env
    return (env.get("ANA_ADMIN", "").strip().lower() in _ON) and bool(env.get("ANA_ADMIN_PASSWORD", ""))


def password_ok(given, env=None) -> bool:
    env = os.environ if env is None else env
    expected = env.get("ANA_ADMIN_PASSWORD", "")
    if not admin_available(env) or not given:
        return False
    return hmac.compare_digest(str(given).encode("utf-8"), expected.encode("utf-8"))
