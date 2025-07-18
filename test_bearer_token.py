#!/usr/bin/env python3
"""
Unit tests for bearer token extraction functionality
"""

from unittest.mock import Mock

import pytest
from fastmcp import Context

# Import the function we want to test
from server import extract_bearer_token


class TestExtractBearerToken:
    """Essential test cases for the extract_bearer_token function"""

    def create_mock_context_with_headers(
        self, headers_list: list[tuple[bytes, bytes]]
    ) -> Mock:
        """Helper method to create a mock context with specified headers"""
        ctx = Mock(spec=Context)

        # Mock the request_context with a Starlette-like request object
        request_context = Mock()
        request = Mock()
        headers_dict = {}

        # Convert headers list to a dict for the mock
        for k, v in headers_list:
            key = k.decode("utf-8") if isinstance(k, bytes) else k
            value = v.decode("utf-8") if isinstance(v, bytes) else v
            headers_dict[key] = value

        # Mock headers object that supports get() method and iteration
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
        """Test extracting a valid Bearer token from Authorization header"""
        # Arrange
        test_token = "abc123xyz789"
        headers = [(b"authorization", f"Bearer {test_token}".encode())]
        ctx = self.create_mock_context_with_headers(headers)

        # Act
        result = extract_bearer_token(ctx)

        # Assert
        assert result == test_token

    def test_no_authorization_header(self) -> None:
        """Test when Authorization header is missing"""
        # Arrange
        headers = [(b"content-type", b"application/json")]
        ctx = self.create_mock_context_with_headers(headers)

        # Act
        result = extract_bearer_token(ctx)

        # Assert
        assert result is None

    def test_authorization_header_without_bearer(self) -> None:
        """Test Authorization header with non-Bearer value"""
        # Arrange
        headers = [(b"authorization", b"Basic dXNlcjpwYXNz")]
        ctx = self.create_mock_context_with_headers(headers)

        # Act
        result = extract_bearer_token(ctx)

        # Assert
        assert result is None

    def test_context_without_request_context(self) -> None:
        """Test when context has no request_context attribute"""
        # Arrange
        ctx = Mock(spec=Context)
        ctx.request_context = None

        # Act
        result = extract_bearer_token(ctx)

        # Assert
        assert result is None

    def test_request_without_headers(self) -> None:
        """Test when request object exists but has no headers"""
        # Arrange
        ctx = Mock(spec=Context)
        request_context = Mock()
        request = Mock()

        # Mock request without headers attribute
        del request.headers  # This will make hasattr return False
        request_context.request = request
        ctx.request_context = request_context

        # Act
        result = extract_bearer_token(ctx)

        # Assert
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
