from unittest.mock import MagicMock


class MockRequest:
    GET = {}
    POST = {}
    path = ""
    _messages = MagicMock()

    def __init__(self, *args, **kwargs) -> None:
        self.GET = {}
        self.POST = {}
        self.META = {}
        self._messages = MagicMock()

    def get_full_path(self):
        return self.path
