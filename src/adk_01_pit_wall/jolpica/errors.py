class JolpicaError(Exception):
    pass


class RaceNotFoundError(JolpicaError):
    pass


class RateLimitedError(JolpicaError):
    pass


class UnexpectedStatusError(JolpicaError):
    pass


class MalformedResponseError(JolpicaError):
    pass
