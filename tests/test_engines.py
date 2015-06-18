import pytest

from bumpversion.engines import *


# NumericEngine

def test_numeric_init_wo_first_value():
    engine = NumericEngine()
    assert engine.first_value == '0'


def test_numeric_init_w_first_value():
    engine = NumericEngine(first_value='5')
    assert engine.first_value == '5'


def test_numeric_init_non_numeric_first_value():
    with pytest.raises(ValueError):
        engine = NumericEngine(first_value='a')


def test_numeric_bump_simple_number():
    engine = NumericEngine()
    assert engine.bump('0') == '1'


def test_numeric_bump_prefix_and_suffix():
    engine = NumericEngine()
    assert engine.bump('v0b') == 'v1b'


# ValuesEngine

def test_values_init():
    engine = ValuesEngine([0, 1, 2])
    assert engine.optional_value == 0
    assert engine.first_value == 0


def test_values_init_w_correct_optional_value():
    engine = ValuesEngine([0, 1, 2], optional_value=1)
    assert engine.optional_value == 1
    assert engine.first_value == 0


def test_values_init_w_correct_first_value():
    engine = ValuesEngine([0, 1, 2], first_value=1)
    assert engine.optional_value == 0
    assert engine.first_value == 1


def test_values_init_w_correct_optional_and_first_value():
    engine = ValuesEngine([0, 1, 2], optional_value=0, first_value=1)
    assert engine.optional_value == 0
    assert engine.first_value == 1


def test_values_init_w_empty_values():
    with pytest.raises(ValueError):
        engine = ValuesEngine([])


def test_values_init_w_incorrect_optional_value():
    with pytest.raises(ValueError):
        engine = ValuesEngine([0, 1, 2], optional_value=3)


def test_values_init_w_incorrect_first_value():
    with pytest.raises(ValueError):
        engine = ValuesEngine([0, 1, 2], first_value=3)


def test_values_bump():
    engine = ValuesEngine([0, 5, 10])
    assert engine.bump(0) == 5


def test_values_bump():
    engine = ValuesEngine([0, 5, 10])
    with pytest.raises(ValueError):
        engine.bump(10)


# DateEngine

def test_date_init():
    engine = DateEngine()
    assert engine.optional_value == '19700101000000'
    assert engine.first_value == '19700101000000'


def test_date_init_w_format():
    engine = DateEngine('%Y%m%d')
    assert engine.optional_value == '19700101'
    assert engine.first_value == '19700101'


def test_date_bump():
    engine = DateEngine()
    bump = engine.bump()
    assert bump != engine.first_value
    assert len(bump) == 14


def test_date_bump_w_format():
    engine = DateEngine('%Y%m%d')
    bump = engine.bump()
    assert bump != engine.first_value
    assert len(bump) == 8
