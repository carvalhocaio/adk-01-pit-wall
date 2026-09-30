class F1Error(Exception):
    pass


class NoLapsError(F1Error):
    pass


class StintNotFoundError(F1Error):
    pass


class InvalidStintSelectorError(F1Error):
    pass
