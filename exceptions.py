class EmptyDictionaryError(Exception):
    """Пустой словарь или список."""
    pass


class RequestExceptionError(Exception):
    """Ошибка запроса."""
    pass


class TheAnswerIsNot200Error(Exception):
    """Сервер ответил кодом отличным от 200."""
    pass


class UnknownHomeWorkStatusError(Exception):
    """Неизвестный статус домашней работы ."""
    pass


class UnknownDictKeyError(Exception):
    """Неизвестный ключ домашней работы ."""
    pass


class ShitError(Exception):
    """Я ненавижу эти тесты."""
    pass