#!/usr/bin/env python3
"""Unit tests for bearer token extraction functionality"""

from unittest.mock import Mock

import pytest
from fastmcp import Context

from server import extract_bearer_token


class TestExtractBearerToken:
    def create_mock_context_with_headers(
        self, headers_list: list[tuple[bytes, bytes]]
    ) -> Mock:
        ctx = Mock(spec=Context)

        request_context = Mock()
        request = Mock()
        headers_dict = {}

        for k, v in headers_list:
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            value = v.decode("utf-8") if isinstance(v, bytes) else v
            headers_dict[key] = value

        mock_headers = Mock()
        mock_headers.get = lambda key, default=None: headers_dict.get(
            key, headers_dict.get(key.lower(), default)
        )
        mock_headers.keys = lambda: headers_dict.keys()
        mock_headers.items = lambda: headers_dict.items()
        mock_headers.__iter__ = lambda: iter(headers_dict.keys())

        request.headers = mock_headers
        request_context.request = request
        ctx.request_context = request_context

        return ctx

    def test_extract_valid_bearer_token(self) -> None:
        test_token = "abc123xyz789"
        headers = [(b"authorization", f"Bearer {test_token}".encode())]
        ctx = self.create_mock_context_with_headers(headers)

        result = extract_bearer_token(ctx)

        assert result == test_token

    def test_no_authorization_header(self) -> None:
        headers = [(b"content-type", b"application/json")]
        ctx = self.create_mock_context_with_headers(headers)

        result = extract_bearer_token(ctx)

        assert result is None

    def test_authorization_header_without_bearer(self) -> None:
        headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
        ctx = self.create_mock_context_with_headers(headers)

        result = extract_bearer_token(ctx)

        assert result is None

    def test_context_without_request_context(self) -> None:
        ctx = Mock(spec=Context)
        ctx.request_context = None

        result = extract_bearer_token(ctx)

        assert result is None

    def test_request_without_headers(self) -> None:
        ctx = Mock(spec=Context)
        request_context = Mock()
        request = Mock()

        request.headers = None
        request_context.request = request
        ctx.request_context = request_context

        result = extract_bearer_token(ctx)

        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
