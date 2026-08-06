import logging

import bot  # noqa: F401 - importing the entrypoint configures production logging


def test_http_clients_do_not_log_request_urls_at_info_level():
    assert logging.getLogger("httpx").getEffectiveLevel() >= logging.WARNING
    assert logging.getLogger("httpcore").getEffectiveLevel() >= logging.WARNING
