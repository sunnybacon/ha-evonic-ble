"""User-interaction regressions for overlapping requests, not Bluetooth mocks."""

import asyncio
import importlib.util
import sys
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "evonic_commands_test", Path(__file__).parents[1] / "custom_components/evonic_ble/commands.py"
)
commands = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = commands
spec.loader.exec_module(commands)


class SchedulerTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.calls = []
        self.changes = []
        self.started = asyncio.Event()
        self.release = asyncio.Event()
        self.failure = None

        async def execute(values, timeout):  # noqa: ASYNC109 - reproduce the executor's budget contract
            self.calls.append(dict(values))
            async with asyncio.timeout(timeout):
                if len(self.calls) == 1:
                    self.started.set()
                    await self.release.wait()
                    if self.failure is not None:
                        raise self.failure
            return dict(values)

        self.scheduler = commands.CommandScheduler(
            execute, lambda: self.changes.append(self.scheduler.attributes), asyncio.create_task
        )

    async def asyncTearDown(self):
        await self.scheduler.close()

    async def start_first(self):
        first = asyncio.create_task(self.scheduler.submit(brightness=40))
        await self.started.wait()
        return first

    async def test_three_adjustments_send_first_and_latest_only(self):
        first = await self.start_first()
        middle = asyncio.create_task(self.scheduler.submit(brightness=50))
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        self.assertEqual(self.calls, [{"brightness": 40}])
        self.assertTrue(self.scheduler.attributes["command_pending"])
        self.assertEqual(self.scheduler.attributes["pending_brightness"], 70)
        self.assertFalse(first.done())
        self.release.set()
        results = await asyncio.gather(first, middle, latest)
        self.assertEqual(self.calls, [{"brightness": 40}, {"brightness": 70}])
        self.assertEqual(results, [{"brightness": 40}, {"brightness": 70}, {"brightness": 70}])
        self.assertFalse(self.scheduler.busy)
        self.assertIsNone(self.scheduler.attributes["pending_brightness"])

    async def test_off_discards_waiting_brightness_and_blocks_new_brightness(self):
        first = await self.start_first()
        brightness = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        off = asyncio.create_task(self.scheduler.submit(power=False))
        await asyncio.sleep(0)
        with self.assertRaises(commands.RequestRejected):
            await brightness
        with self.assertRaises(commands.RequestRejected):
            await self.scheduler.submit(brightness=20)
        self.release.set()
        await asyncio.gather(first, off)
        self.assertEqual(self.calls, [{"brightness": 40}, {"power": False}])

    async def test_off_is_still_attempted_after_an_active_brightness_failure(self):
        self.failure = RuntimeError("Missing reply")
        first = await self.start_first()
        off = asyncio.create_task(self.scheduler.submit(power=False))
        await asyncio.sleep(0)
        self.release.set()
        results = await asyncio.gather(first, off, return_exceptions=True)
        self.assertIsInstance(results[0], RuntimeError)
        self.assertEqual(results[1], {"power": False})
        self.assertEqual(self.calls, [{"brightness": 40}, {"power": False}])

    async def test_failure_discards_pending_brightness_without_replay(self):
        self.failure = RuntimeError("Missing reply")
        first = await self.start_first()
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        self.release.set()
        results = await asyncio.gather(first, latest, return_exceptions=True)
        self.assertIsInstance(results[0], RuntimeError)
        self.assertIsInstance(results[1], commands.RequestRejected)
        self.assertEqual(self.calls, [{"brightness": 40}])
        self.assertFalse(self.scheduler.busy)
        # A future explicit request is allowed, but discarded work is never retried.
        self.assertEqual(await self.scheduler.submit(brightness=20), {"brightness": 20})
        self.assertEqual(self.calls, [{"brightness": 40}, {"brightness": 20}])

    async def test_non_brightness_overlap_is_rejected(self):
        first = await self.start_first()
        with self.assertRaises(commands.RequestRejected):
            await self.scheduler.submit(target=21)
        with self.assertRaises(commands.RequestRejected):
            await self.scheduler.submit(power=True)
        self.release.set()
        await first

    async def test_cancelled_pending_request_never_reaches_executor(self):
        first = await self.start_first()
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        latest.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await latest
        self.release.set()
        await first
        self.assertEqual(self.calls, [{"brightness": 40}])

    async def test_cancelling_one_coalesced_caller_preserves_the_other(self):
        first = await self.start_first()
        middle = asyncio.create_task(self.scheduler.submit(brightness=50))
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        middle.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await middle
        self.release.set()
        await asyncio.gather(first, latest)
        self.assertEqual(self.calls, [{"brightness": 40}, {"brightness": 70}])

    async def test_dragging_does_not_extend_pending_deadline(self):
        first = await self.start_first()
        middle = asyncio.create_task(self.scheduler.submit(brightness=50))
        await asyncio.sleep(0)
        deadline = self.scheduler._pending.deadline
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        self.assertEqual(self.scheduler._pending.deadline, deadline)
        self.release.set()
        await asyncio.gather(first, middle, latest)

    async def test_expired_pending_request_is_not_executed(self):
        first = await self.start_first()
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        self.scheduler._pending.deadline = asyncio.get_running_loop().time() - 1
        self.release.set()
        results = await asyncio.gather(first, latest, return_exceptions=True)
        self.assertIsInstance(results[1], commands.RequestRejected)
        self.assertEqual(self.calls, [{"brightness": 40}])

    async def test_executor_deadline_returns_failure_and_clears_busy(self):
        self.scheduler.operation_timeout = 0.02
        with self.assertRaises(TimeoutError):
            await self.scheduler.submit(brightness=40)
        self.assertFalse(self.scheduler.busy)
        self.assertEqual(self.calls, [{"brightness": 40}])

    async def test_poll_waits_for_the_control_burst_to_finish(self):
        first = await self.start_first()
        idle = asyncio.create_task(self.scheduler.wait_idle())
        await asyncio.sleep(0)
        self.assertFalse(idle.done())
        self.release.set()
        await asyncio.gather(first, idle)

    async def test_unload_cancels_active_and_pending_work(self):
        first = await self.start_first()
        latest = asyncio.create_task(self.scheduler.submit(brightness=70))
        await asyncio.sleep(0)
        await self.scheduler.close()
        results = await asyncio.gather(first, latest, return_exceptions=True)
        self.assertTrue(all(isinstance(result, commands.RequestRejected) for result in results))
        self.assertEqual(self.calls, [{"brightness": 40}])
        self.assertFalse(self.scheduler.busy)
        with self.assertRaises(commands.RequestRejected):
            await self.scheduler.submit(brightness=20)


if __name__ == "__main__":
    unittest.main()
