from bumpversion.engines import NumericEngine, ValuesEngine

class PartConfiguration(object):
    engine_cls = NumericEngine

    def __init__(self, *args, **kwds):
        self.engine = self.engine_cls(*args, **kwds)

    @property
    def first_value(self):
        return str(self.engine.first_value)

    @property
    def optional_value(self):
        return str(self.engine.optional_value)

    def bump(self, value=None):
        return self.engine.bump(value)


class ConfiguredVersionPartConfiguration(PartConfiguration):
    engine_cls = ValuesEngine


class NumericVersionPartConfiguration(PartConfiguration):
    engine_cls = NumericEngine


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
