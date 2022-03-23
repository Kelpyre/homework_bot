"""Кастомные исключения для бота."""


class SendMessageError(Exception):
    """Исключение при попытке отправки сообщения."""

    pass


class Status500Error(Exception):
    """Исключение при статусе 500."""

    pass


class UnknownStatusError(Exception):
    """Исключение при статусе, не равном 200."""

    pass


class EmptyListError(KeyError):
    """Исключение при получении пустого списка."""

    pass
