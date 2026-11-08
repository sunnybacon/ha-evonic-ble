"""Bounded single-device command scheduling, independent of HA/Bluetooth."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass


class RequestRejected(RuntimeError):
    """A request was not executed; device availability is unaffected."""


@dataclass
class Request:
    values: dict
    deadline: float
    result: asyncio.Future
    waiters: int = 0


class CommandScheduler:
    """At most one active and one pending operation; no mutation retries.

    Coalesced brightness callers await the result of the latest pending value.
    Superseded intermediate values are not claimed to have reached the fire.
    """

    def __init__(
        self,
        execute: Callable[[dict, float], Awaitable],
        changed: Callable[[], None],
        create_task: Callable,
        request_timeout: float = 60,
        operation_timeout: float = 40,
    ):
        self.execute = execute
        self.changed = changed
        self.create_task = create_task
        self.request_timeout = request_timeout
        self.operation_timeout = operation_timeout
        self._active: Request | None = None
        self._pending: Request | None = None
        self._task: asyncio.Task | None = None
        self._idle = asyncio.Event()
        self._idle.set()
        self._closed = False

    @property
    def busy(self) -> bool:
        return self._active is not None or self._pending is not None

    @property
    def attributes(self) -> dict:
        current = self._active or self._pending
        desired = self._pending or self._active
        return {
            "command_pending": self.busy,
            "pending_command": next(iter(current.values), None) if current else None,
            "pending_brightness": desired.values.get("brightness") if desired else None,
            "pending_power": desired.values.get("power") if desired else None,
        }

    async def wait_idle(self) -> None:
        await self._idle.wait()

    @staticmethod
    def _failed(request: Request, message: str) -> None:
        if not request.result.done():
            request.result.set_exception(RequestRejected(message))

    async def submit(self, **values):
        if self._closed:
            raise RequestRejected("The fire integration is shutting down")
        loop = asyncio.get_running_loop()
        is_brightness = set(values) == {"brightness"}
        is_off = values == {"power": False}
        if self.busy:
            if is_off:
                if self._pending and self._pending.values == values:
                    request = self._pending
                else:
                    if self._pending:
                        self._failed(self._pending, "Pending change cancelled by power off")
                    request = self._new(values, loop.time())
                    self._pending = request
            elif is_brightness:
                if any(
                    item and item.values == {"power": False}
                    for item in (self._active, self._pending)
                ):
                    raise RequestRejected("The fire is being switched off")
                if self._pending:
                    if set(self._pending.values) != {"brightness"}:
                        raise RequestRejected("Wait for the current fire control to finish")
                    request = self._pending
                    request.values = dict(values)
                    # A continuous drag cannot keep old work queued indefinitely.
                else:
                    request = self._new(values, loop.time())
                    self._pending = request
            else:
                raise RequestRejected("Wait for the current fire control to finish")
        else:
            request = self._new(values, loop.time())
            self._pending = request
        request.waiters += 1
        self._idle.clear()
        self.changed()
        if self._task is None or self._task.done():
            self._task = self.create_task(self._run())
        try:
            # One caller cancelling must not cancel another caller's shared result.
            return await asyncio.shield(request.result)
        finally:
            request.waiters -= 1
            if request.waiters == 0 and self._pending is request:
                self._pending = None  # Cancelled callers leave no late unsent work.
                request.result.cancel()
                self.changed()

    def _new(self, values, now) -> Request:
        future = asyncio.get_running_loop().create_future()
        # Consume unobserved exceptions if all HTTP callers disconnect.
        future.add_done_callback(lambda result: None if result.cancelled() else result.exception())
        return Request(dict(values), now + self.request_timeout, future)

    async def _run(self) -> None:
        try:
            while self._pending is not None:
                request = self._active = self._pending
                self._pending = None
                self.changed()
                remaining = request.deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    self._failed(request, "Pending fire control expired; please try again")
                    self._active = None
                    continue
                try:
                    # The executor enforces this deadline inside its error boundary.
                    result = await self.execute(
                        dict(request.values), min(remaining, self.operation_timeout)
                    )
                except asyncio.CancelledError:
                    self._failed(request, "Fire control cancelled during integration shutdown")
                    raise
                except Exception as error:
                    if not request.result.done():
                        request.result.set_exception(error)
                    if self._pending and self._pending.values == {"power": False}:
                        # This is a separate explicit Off request, not a replay.
                        continue
                    if self._pending:
                        self._failed(
                            self._pending,
                            "Pending change discarded after the previous control failed",
                        )
                        self._pending = None
                    break
                else:
                    if not request.result.done():
                        request.result.set_result(result)
                finally:
                    self._active = None
        finally:
            if self._pending:
                self._failed(self._pending, "Pending change cancelled")
                self._pending = None
            self._active = None
            self._task = None
            self._idle.set()
            self.changed()

    async def close(self) -> None:
        self._closed = True
        if self._pending:
            self._failed(self._pending, "Pending change cancelled during integration shutdown")
            self._pending = None
        task = self._task
        if task is not None:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        self._task = None
        self._active = None
        self._idle.set()
        self.changed()
