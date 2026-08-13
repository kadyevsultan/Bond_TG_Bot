import pytest

from bond_bot.config import Settings

TOKEN = "123:fake"


def build(value: str | None) -> Settings:
    if value is None:
        return Settings(BOT_TOKEN=TOKEN, _env_file=None)
    return Settings(BOT_TOKEN=TOKEN, ADMIN_IDS=value, _env_file=None)


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("", []),
        ("111", [111]),
        ("111,222", [111, 222]),
        ("111, 222 , 333", [111, 222, 333]),
        ("111;222", [111, 222]),
        (None, []),
    ],
)
def test_admin_ids_parsing(raw, expected):
    assert build(raw).admin_ids == expected


def test_is_admin_checks_membership():
    settings = build("111,222")
    assert settings.is_admin(111)
    assert settings.is_admin(222)
    assert not settings.is_admin(333)
    assert not settings.is_admin(None)


def test_no_admins_means_nobody():
    settings = build("")
    assert not settings.is_admin(111)


def test_legacy_admin_id_is_ignored():
    settings = Settings(BOT_TOKEN=TOKEN, ADMIN_ID="999", _env_file=None)
    assert settings.admin_ids == []
    assert not settings.is_admin(999)
