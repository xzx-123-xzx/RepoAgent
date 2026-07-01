import pytest

from app.services.url_validator import parse_github_url, normalize_repo_url
from app.utils.exceptions import InvalidUrlError


def test_parse_github_url():
    owner, repo = parse_github_url("https://github.com/fastapi/fastapi")
    assert owner == "fastapi"
    assert repo == "fastapi"


def test_parse_github_url_invalid():
    with pytest.raises(InvalidUrlError):
        parse_github_url("https://gitlab.com/foo/bar")


def test_normalize_repo_url():
    assert normalize_repo_url("fastapi", "fastapi") == "https://github.com/fastapi/fastapi"
