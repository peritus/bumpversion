from bumpversion.functions import NumericFunction, ValuesFunction, DateFunction

class PartConfiguration(object):
    function_cls = NumericFunction

    def __init__(self, *args, **kwds):

        functions_dict = {
            'numeric': NumericFunction,
            'values': ValuesFunction,
            'date': DateFunction
        }

        # Get the function to be used, if set
        try:
            function = kwds.pop('function')

            try:
                self.function_cls = functions_dict[function]
            except KeyError:
                raise ValueError("Function '{}' is not supported".format(function))
        except KeyError:
            if 'values' in kwds:
                self.function_cls = ValuesFunction
            else:
                # This is the default function
                self.function_cls = NumericFunction

        self.function = self.function_cls(*args, **kwds)

    @property
    def first_value(self):
        return str(self.function.first_value)

    @property
    def optional_value(self):
        return str(self.function.optional_value)

    def bump(self, value=None):
        return self.function.bump(value)


class VersionPart(object):

    """
    This class represents part of a version number. It contains a self.config
    object that rules how the part behaves when increased or reset.
    """

    def __init__(self, value, config=None):
        self._value = value

        if config is None:
            self.config = PartConfiguration()
        else:
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
