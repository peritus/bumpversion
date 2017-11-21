import pytest

from bumpversion.version_part import *

@pytest.fixture(params=[None, (('0', '1', '2'),), (('0', '3'),)])
def confvpc(request):
    if request.param is None:
        return NumericVersionPartConfiguration()
    else:
        return ConfiguredVersionPartConfiguration(*request.param)


# VersionPart

def test_version_part_init(confvpc):
    assert VersionPart(
        confvpc.first_value, confvpc).value == confvpc.first_value


def test_version_part_copy(confvpc):
    vp = VersionPart(confvpc.first_value, confvpc)
    vc = vp.copy()
    assert vp.value == vc.value
    assert id(vp) != id(vc)


def test_version_part_bump(confvpc):
    vp = VersionPart(confvpc.first_value, confvpc)
    vc = vp.bump()
    assert vc.value == confvpc.bump(confvpc.first_value)


def test_version_part_check_optional_false(confvpc):
    assert not VersionPart(confvpc.first_value, confvpc).bump().is_optional()


def test_version_part_check_optional_true(confvpc):
    assert VersionPart(confvpc.first_value, confvpc).is_optional()


def test_version_part_format(confvpc):
    assert "{}".format(
        VersionPart(confvpc.first_value, confvpc)) == confvpc.first_value


def test_version_part_equality(confvpc):
    assert VersionPart(confvpc.first_value, confvpc) == VersionPart(
        confvpc.first_value, confvpc)


def test_version_part_null(confvpc):
    assert VersionPart(confvpc.first_value, confvpc).null() == VersionPart(
        confvpc.first_value, confvpc)
