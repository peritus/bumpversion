import re
import datetime


class NumericEngine(object):

    """
    This is a class that provides a numeric engine for version parts.
    It simply starts with the provided first_value (0 by default) and
    increases it following the sequence of integer numbers.

    The optional value of this engine is equal to the first value.

    This engine also supports alphanumeric parts, altering just the numeric
    part (e.g. 'r3' --> 'r4'). Only the first numeric group found in the part is
    considered (e.g. 'r3-001' --> 'r4-001').
    """

    FIRST_NUMERIC = re.compile('([^\d]*)(\d+)(.*)')

    def __init__(self, first_value=None):

        if first_value is not None:
            try:
                part_prefix, part_numeric, part_suffix = self.FIRST_NUMERIC.search(
                    first_value).groups()
            except AttributeError:
                raise ValueError(
                    "The given first value {} does not contain any digit".format(first_value))
        else:
            first_value = 0

        self.first_value = str(first_value)
        self.optional_value = self.first_value

    def bump(self, value):
        part_prefix, part_numeric, part_suffix = self.FIRST_NUMERIC.search(
            value).groups()
        bumped_numeric = int(part_numeric) + 1

        return "".join([part_prefix, str(bumped_numeric), part_suffix])


class ValuesEngine(object):

    """
    This is a class that provides a values list based engine for version parts.
    It is initialized with a list of values and iterates through them when
    bumping the part.

    The default optional value of this engine is equal to the first value,
    but may be otherwise specified.

    When trying to bump a part which has already the maximum value in the list
    you get a ValueError exception.
    """

    def __init__(self, values, optional_value=None, first_value=None):

        if len(values) == 0:
            raise ValueError("Version part values cannot be empty")

        self._values = values

        if optional_value is None:
            optional_value = values[0]

        if optional_value not in values:
            raise ValueError("Optional value {0} must be included in values {1}".format(
                optional_value, values))

        self.optional_value = optional_value

        if first_value is None:
            first_value = values[0]

        if first_value not in values:
            raise ValueError("First value {0} must be included in values {1}".format(
                first_value, values))

        self.first_value = first_value

    def bump(self, value):
        try:
            return self._values[self._values.index(value)+1]
        except IndexError:
            raise ValueError(
                "The part has already the maximum value among {} and cannot be bumped.".format(self._values))


class DateEngine(object):

    """
    This is a class that provides a date based engine for version parts.
    It is initialized with a format according to the strftime() and strptime()
    rules (see https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
    or https://docs.python.org/3/library/datetime.html#strftime-and-strptime-behavior).

    The first value and the default value of this field are equal to the Unix
    Epoch (00:00:00 1st January 1970) but given the meaning of the data should
    be never used (either that or you are Emmett Brown).

    When bumped, this field returns always the current date and time formatted
    with the given format.
    """

    def __init__(self, fmt='%Y%m%d%H%M%S'):
        self._format = fmt

        unix_epoch = datetime.datetime.strptime(
            '19700101000000', '%Y%m%d%H%M%S')
        self.first_value = unix_epoch.strftime(self._format)
        self.optional_value = self.first_value

    def bump(self, value=None):
        return datetime.datetime.now().strftime(self._format)
