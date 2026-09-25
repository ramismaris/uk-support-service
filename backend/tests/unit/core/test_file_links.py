from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

from src.core.security import FILE_LINK_TTL, build_file_url, sign_file_link, verify_file_link

NOW = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def _expires_at(now: datetime = NOW) -> int:
    return int((now + timedelta(minutes=30)).timestamp())


def test_build_file_url_is_valid_for_ttl():
    url = build_file_url(5, NOW)
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    assert parsed.path == "/api/v1/files/5"
    assert int(params["exp"][0]) == int((NOW + FILE_LINK_TTL).timestamp())
    assert verify_file_link(5, int(params["exp"][0]), params["sig"][0], NOW) is True


def test_valid_signature_is_accepted():
    expires_at = _expires_at()

    assert verify_file_link(1, expires_at, sign_file_link(1, expires_at), NOW) is True


def test_tampered_signature_is_rejected():
    expires_at = _expires_at()
    sig = sign_file_link(1, expires_at)
    tampered = ("0" if sig[0] != "0" else "1") + sig[1:]

    assert verify_file_link(1, expires_at, tampered, NOW) is False


def test_signature_for_other_file_id_is_rejected():
    expires_at = _expires_at()

    assert verify_file_link(2, expires_at, sign_file_link(1, expires_at), NOW) is False


def test_expired_link_is_rejected():
    expires_at = int((NOW - timedelta(seconds=1)).timestamp())

    assert verify_file_link(1, expires_at, sign_file_link(1, expires_at), NOW) is False


def test_non_hex_signature_is_rejected():
    assert verify_file_link(1, _expires_at(), "z" * 64, NOW) is False


def test_wrong_length_signature_is_rejected():
    assert verify_file_link(1, _expires_at(), "abc", NOW) is False


def test_non_ascii_signature_is_rejected_without_raising():
    assert verify_file_link(1, _expires_at(), "абв", NOW) is False
