from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import threading
import time
from typing import Callable, Protocol

from .macro_model import KeyStep, MacroProfile, WaitStep


class InputBackend(Protocol):
    def is_target_foreground(self) -> bool: ...

    def key_down(self, key: str) -> None: ...

    def key_up(self, key: str) -> None: ...


class MacroState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPING = "stopping"
    DISABLED = "disabled"
    BLOCKED_FOCUS = "blocked_focus"
    COMPLETED = "completed"
    TRIGGER_RELEASED = "trigger_released"
    STOPPED = "stopped"
    TIME_LIMIT = "time_limit"
    ERROR = "error"


@dataclass(frozen=True)
class MacroStatus:
    profile_id: str
    state: MacroState
    detail: str = ""


class MacroController:
    """Threaded macro runner with foreground, timeout and key-release guarantees."""

    def __init__(
        self,
        backend: InputBackend,
        status_callback: Callable[[MacroStatus], None] | None = None,
        *,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._backend = backend
        self._status_callback = status_callback or (lambda _status: None)
        self._monotonic = monotonic
        self._lock = threading.RLock()
        self._workers: dict[str, tuple[threading.Thread, threading.Event]] = {}
        self._trigger_down: dict[str, bool] = {}
        self._pressed_keys: dict[str, set[str]] = {}
        self._closed = False

    def update_trigger(self, profile: MacroProfile, pressed: bool) -> MacroState:
        """Apply the current physical trigger state and return the immediate decision."""
        with self._lock:
            if self._closed or not profile.enabled:
                self._trigger_down[profile.id] = pressed
                self._publish(profile.id, MacroState.DISABLED)
                return MacroState.DISABLED

            previous = self._trigger_down.get(profile.id, False)
            self._trigger_down[profile.id] = pressed
            rising = pressed and not previous
            falling = previous and not pressed

            if profile.trigger.mode == "hold_repeat" and falling:
                self._request_stop_locked(profile.id)
                return MacroState.STOPPING
            if not rising:
                return self.state(profile.id)

            if profile.trigger.mode == "toggle_repeat" and profile.id in self._workers:
                self._request_stop_locked(profile.id)
                return MacroState.STOPPING
            if profile.id in self._workers:
                return MacroState.RUNNING
            if not self._backend.is_target_foreground():
                self._publish(profile.id, MacroState.BLOCKED_FOCUS)
                return MacroState.BLOCKED_FOCUS

            stop_event = threading.Event()
            worker = threading.Thread(
                target=self._run_profile,
                name=f"macro-{profile.id}",
                args=(profile, stop_event),
                daemon=True,
            )
            self._workers[profile.id] = (worker, stop_event)
            self._publish(profile.id, MacroState.RUNNING)
            worker.start()
            return MacroState.RUNNING

    def state(self, profile_id: str) -> MacroState:
        with self._lock:
            return MacroState.RUNNING if profile_id in self._workers else MacroState.IDLE

    def stop(self, profile_id: str) -> None:
        with self._lock:
            self._request_stop_locked(profile_id)

    def stop_all(self, detail: str = "emergency_stop") -> None:
        with self._lock:
            for _thread, stop_event in self._workers.values():
                stop_event.set()
            profile_ids = tuple(self._workers)
        self._release_every_key()
        for profile_id in profile_ids:
            self._publish(profile_id, MacroState.STOPPING, detail)

    def close(self) -> None:
        with self._lock:
            self._closed = True
        self.stop_all("controller_closed")

    def wait_for_idle(self, profile_id: str, timeout: float = 2.0) -> bool:
        deadline = self._monotonic() + timeout
        while self._monotonic() < deadline:
            with self._lock:
                worker = self._workers.get(profile_id)
            if worker is None:
                return True
            worker[0].join(timeout=min(0.02, max(0.0, deadline - self._monotonic())))
        return self.state(profile_id) == MacroState.IDLE

    def _request_stop_locked(self, profile_id: str) -> None:
        worker = self._workers.get(profile_id)
        if worker is not None:
            worker[1].set()
            self._publish(profile_id, MacroState.STOPPING)

    def _run_profile(self, profile: MacroProfile, stop_event: threading.Event) -> None:
        deadline = self._monotonic() + profile.limits.max_runtime_ms / 1000.0
        final_state = MacroState.COMPLETED
        detail = ""
        try:
            while True:
                interruption = self._interruption(profile, stop_event, deadline)
                if interruption is not None:
                    final_state = interruption
                    break
                for step in profile.steps:
                    interruption = self._interruption(profile, stop_event, deadline)
                    if interruption is not None:
                        final_state = interruption
                        break
                    if isinstance(step, KeyStep):
                        if step.action == "down":
                            self._press(profile.id, step.key)
                        elif step.action == "up":
                            self._release(profile.id, step.key)
                        else:
                            self._press(profile.id, step.key)
                            interruption = self._interruptible_wait(
                                step.hold_ms / 1000.0, profile, stop_event, deadline
                            )
                            self._release(profile.id, step.key)
                            if interruption is not None:
                                final_state = interruption
                                break
                    elif isinstance(step, WaitStep):
                        interruption = self._interruptible_wait(
                            step.duration_ms / 1000.0, profile, stop_event, deadline
                        )
                        if interruption is not None:
                            final_state = interruption
                            break
                if final_state is not MacroState.COMPLETED:
                    break
                if profile.trigger.mode == "once":
                    break
                if profile.trigger.mode == "hold_repeat":
                    with self._lock:
                        if not self._trigger_down.get(profile.id, False):
                            final_state = MacroState.TRIGGER_RELEASED
                            break
                interruption = self._interruptible_wait(
                    profile.limits.repeat_delay_ms / 1000.0,
                    profile,
                    stop_event,
                    deadline,
                )
                if interruption is not None:
                    final_state = interruption
                    break
        except Exception as exception:
            final_state = MacroState.ERROR
            detail = type(exception).__name__
        finally:
            self._release_profile_keys(profile.id)
            with self._lock:
                self._workers.pop(profile.id, None)
            self._publish(profile.id, final_state, detail)

    def _interruption(
        self, profile: MacroProfile, stop_event: threading.Event, deadline: float
    ) -> MacroState | None:
        if stop_event.is_set():
            return MacroState.STOPPED
        if self._monotonic() >= deadline:
            return MacroState.TIME_LIMIT
        if not self._backend.is_target_foreground():
            return MacroState.BLOCKED_FOCUS
        if profile.trigger.mode == "hold_repeat":
            with self._lock:
                if not self._trigger_down.get(profile.id, False):
                    return MacroState.TRIGGER_RELEASED
        return None

    def _interruptible_wait(
        self,
        duration: float,
        profile: MacroProfile,
        stop_event: threading.Event,
        deadline: float,
    ) -> MacroState | None:
        wait_deadline = self._monotonic() + duration
        while self._monotonic() < wait_deadline:
            interruption = self._interruption(profile, stop_event, deadline)
            if interruption is not None:
                return interruption
            stop_event.wait(min(0.02, max(0.0, wait_deadline - self._monotonic())))
        return self._interruption(profile, stop_event, deadline)

    def _press(self, owner: str, key: str) -> None:
        with self._lock:
            owners = self._pressed_keys.setdefault(key, set())
            if owner in owners:
                return
            if not owners:
                self._backend.key_down(key)
            owners.add(owner)

    def _release(self, owner: str, key: str) -> None:
        with self._lock:
            owners = self._pressed_keys.get(key)
            if not owners or owner not in owners:
                return
            owners.discard(owner)
            if owners:
                return
            try:
                self._backend.key_up(key)
            finally:
                self._pressed_keys.pop(key, None)

    def _release_profile_keys(self, owner: str) -> None:
        with self._lock:
            keys = tuple(
                key for key, owners in self._pressed_keys.items() if owner in owners
            )
        for key in reversed(keys):
            self._release(owner, key)

    def _release_every_key(self) -> None:
        with self._lock:
            keys = tuple(self._pressed_keys)
            self._pressed_keys.clear()
        for key in reversed(keys):
            try:
                self._backend.key_up(key)
            except Exception:
                # Emergency stop is best-effort across every owned key. One
                # backend failure must not prevent releasing the remaining keys.
                continue

    def _publish(self, profile_id: str, state: MacroState, detail: str = "") -> None:
        self._status_callback(MacroStatus(profile_id, state, detail))
