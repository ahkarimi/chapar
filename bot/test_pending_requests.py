from handlers.message_utils import MessageUtilsMixin


class PendingState(MessageUtilsMixin):
    def __init__(self):
        self.pending_requests = {}


def test_chart_and_news_pending_states_are_independent():
    state = PendingState()

    state.add_pending(123, "analysis")

    assert state.is_pending(123, "analysis") is True
    assert state.is_pending(123, "news") is False

    state.add_pending(123, "news")
    state.remove_pending(123, "analysis")

    assert state.is_pending(123, "analysis") is False
    assert state.is_pending(123, "news") is True


def test_pending_state_is_scoped_by_user():
    state = PendingState()

    state.add_pending(123, "analysis")

    assert state.is_pending(456, "analysis") is False
