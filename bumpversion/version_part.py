from bumpversion.functions import NumericFunction, ValuesFunction

class PartConfiguration(object):
    function_cls = NumericFunction

    def __init__(self, *args, **kwds):
        self.function = self.function_cls(*args, **kwds)

    @property
    def first_value(self):
        return str(self.function.first_value)

    @property
    def optional_value(self):
        return str(self.function.optional_value)

    def bump(self, value=None):
        return self.function.bump(value)


class ConfiguredVersionPartConfiguration(PartConfiguration):
    function_cls = ValuesFunction


class NumericVersionPartConfiguration(PartConfiguration):
    function_cls = NumericFunction


class VersionPart(object):

    """
    This class represents part of a version number. It contains a self.config
    object that rules how the part behaves when increased or reset.
    """

    def __init__(self, value, config=None):
        self._value = value

        if config is None:
            config = NumericVersionPartConfiguration()

        self.config = config

    @property
    def value(self):
        return self._value or self.config.optional_value

    def copy(self):
        return VersionPart(self._value)

    def bump(self):
        return VersionPart(self.config.bump(self.value), self.config)

    def is_optional(self):
        return self.value == self.config.optional_value

    def __format__(self, format_spec):
        return self.value

    def __repr__(self):
        return '<bumpversion.VersionPart:{}:{}>'.format(
            self.config.__class__.__name__,
            self.value
        )

    def __eq__(self, other):
        return self.value == other.value

    def null(self):
        return VersionPart(self.config.first_value, self.config)
