"""Tests for utils.background module."""

from unittest.mock import MagicMock, patch

from utils.background import Background


class _FakeTimer:
    def __init__(self, delay, callback):
        self.delay = delay
        self.callback = callback
        self.started = False
        self.cancelled = False

    def start(self):
        self.started = True

    def cancel(self):
        self.cancelled = True


def test_initialization_schedules_timer_once():
    with patch("utils.background.Timer", side_effect=lambda d, c: _FakeTimer(d, c)) as mock_timer:
        callback = MagicMock()
        bg = Background(5, callback)

        assert bg._running is True
        assert bg._timer is not None
        assert bg._timer.started is True
        mock_timer.assert_called_once()


def test_schedule_does_not_create_new_timer_while_running():
    with patch("utils.background.Timer", side_effect=lambda d, c: _FakeTimer(d, c)) as mock_timer:
        callback = MagicMock()
        bg = Background(5, callback)

        first_timer = bg._timer
        bg.schedule()

        assert bg._timer is first_timer
        mock_timer.assert_called_once()


def test_run_reschedules_and_executes_callback():
    with patch("utils.background.Timer", side_effect=lambda d, c: _FakeTimer(d, c)) as mock_timer:
        callback = MagicMock()
        bg = Background(5, callback)

        initial_timer = bg._timer
        bg._run()

        assert bg._timer is not initial_timer
        assert bg._timer.started is True
        callback.assert_called_once()
        assert mock_timer.call_count == 2


def test_cancel_cancels_timer_and_stops_running():
    with patch("utils.background.Timer", side_effect=lambda d, c: _FakeTimer(d, c)):
        callback = MagicMock()
        bg = Background(5, callback)

        timer = bg._timer
        bg.cancel()

        assert timer.cancelled is True
        assert bg._running is False


def test_cancel_without_timer_is_safe():
    bg = Background.__new__(Background)
    bg._timer = None
    bg._running = True

    bg.cancel()

    assert bg._running is False
