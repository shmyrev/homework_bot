class SendMessageError(Exception):
    """Обработка ошибки отправки сообщения."""

    def __init__(self, *args):
        """Инициализатор класса."""
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        """Объект в строку."""
        if self.message:
            return f'Ошибка отправки сообщения {self.message}'
        else:
            return 'Сообщение не удалось отправить'


class ConnectionError(Exception):
    """Обработка ошибки соединения."""

    def __init__(self, *args):
        """Инициализатор класса."""
        if args:
            self.message = args[0]
        else:
            self.message = None

    def __str__(self):
        """Объект в строку."""
        if self.message:
            return f'Ошибка при обращении к API. {self.message}'
        else:
            return 'Ошибка соединения с сервером.'
