"""Who may open the owner pages (Usage, Build).

Both must hold: ANA_ADMIN is switched on, and ANA_ADMIN_PASSWORD is set and was
entered correctly. With no password set, the owner pages stay off.
"""
import hmac
import logging
import os
import threading
import time
from collections import OrderedDict, deque

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


_log = logging.getLogger("ana.admin")


class LoginGuard:
    """Locks the owner password box after repeated wrong guesses.

    Failures are counted on the server per visitor (when the visitor's address is
    trusted) and for everyone together, so reloading the page does not reset them.
    After `per_visitor` wrong guesses within `window` seconds that visitor is
    locked out; after `global_limit` wrong guesses from anyone, the box is locked
    for everyone until the window passes. Memory is bounded to `max_keys` visitors.
    """

    def __init__(self, per_visitor=5, global_limit=20, window=900, max_keys=10000):
        self.per_visitor, self.global_limit, self.window, self.max_keys = per_visitor, global_limit, window, max_keys
        self._fails = OrderedDict()
        self._global = deque()
        self._lock = threading.Lock()

    def _recent(self, q, now):
        while q and not (0 <= now - q[0] < self.window):
            q.popleft()
        return len(q)

    def locked(self, visitor=None, now=None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            if self._recent(self._global, now) >= self.global_limit:
                return True
            q = self._fails.get(visitor) if visitor else None
            return bool(q) and self._recent(q, now) >= self.per_visitor

    def failure(self, visitor=None, now=None):
        now = time.time() if now is None else now
        with self._lock:
            self._global.append(now)
            while len(self._global) > self.global_limit:
                self._global.popleft()
            if visitor:
                q = self._fails.get(visitor)
                if q is None:
                    if len(self._fails) >= self.max_keys:
                        self._fails.popitem(last=False)
                    q = self._fails[visitor] = deque(maxlen=self.per_visitor)
                q.append(now)
                self._fails.move_to_end(visitor)
        # Never log what was typed.
        _log.warning("owner password: wrong attempt (visitor known: %s)", bool(visitor))

    def success(self, visitor=None):
        with self._lock:
            if visitor:
                self._fails.pop(visitor, None)


def try_login(given, guard, visitor=None, env=None, now=None) -> str:
    """Check an owner password attempt: returns "ok", "wrong" or "locked"."""
    if guard.locked(visitor, now):
        return "locked"
    if password_ok(given, env):
        guard.success(visitor)
        return "ok"
    guard.failure(visitor, now)
    return "wrong"
