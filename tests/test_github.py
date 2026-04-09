"""Tests for GitHub connector module."""

import pytest

from genalphacli.github import parse_github_url


class TestParseGithubUrl:
    def test_full_https_url(self):
        assert parse_github_url("https://github.com/tiangolo/fastapi") == ("tiangolo", "fastapi")

    def test_url_with_git_suffix(self):
        assert parse_github_url("https://github.com/owner/repo.git") == ("owner", "repo")

    def test_shorthand(self):
        assert parse_github_url("owner/repo") == ("owner", "repo")

    def test_shorthand_with_git_suffix(self):
        assert parse_github_url("owner/repo.git") == ("owner", "repo")

    def test_trailing_slash(self):
        assert parse_github_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_whitespace_stripped(self):
        assert parse_github_url("  owner/repo  ") == ("owner", "repo")

    def test_rejects_http(self):
        with pytest.raises(ValueError, match="HTTPS"):
            parse_github_url("http://github.com/owner/repo")

    def test_rejects_non_github(self):
        with pytest.raises(ValueError, match="github.com"):
            parse_github_url("https://gitlab.com/owner/repo")

    def test_rejects_port(self):
        with pytest.raises(ValueError, match="port"):
            parse_github_url("https://github.com:8443/owner/repo")

    def test_rejects_fragment(self):
        with pytest.raises(ValueError, match="fragment"):
            parse_github_url("https://github.com/owner/repo#readme")

    def test_rejects_query(self):
        with pytest.raises(ValueError, match="fragment|query"):
            parse_github_url("https://github.com/owner/repo?tab=code")

    def test_rejects_invalid_path(self):
        with pytest.raises(ValueError, match="Invalid"):
            parse_github_url("https://github.com/onlyowner")
