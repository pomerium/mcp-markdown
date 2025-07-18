#!/usr/bin/env python3
"""
MCP Server for converting Google Drive URLs to Markdown
FastMCP implementation with Bearer token authentication and proper context handling
"""

import asyncio
import logging
import os
import re
import sys
import threading
from typing import Literal

import anyio
import structlog
from fastmcp import Context, FastMCP
from fastmcp.exceptions import ToolError

# Configure structlog for clean console output
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="%H:%M:%S"),
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.dev.ConsoleRenderer(colors=True),
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

# Configure Python's logging to work with structlog

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Only show the message since structlog handles formatting
    handlers=[logging.StreamHandler()],
)

logger = structlog.get_logger("mcp-markdown-server")


class GoogleDriveService:
    """Service for interacting with Google Drive API"""

    def __init__(self, access_token: str):
        """Initialize with access token from Authorization header"""
        self.access_token = access_token

        try:
            from google.oauth2.credentials import Credentials
            from googleapiclient.discovery import build

            self.credentials = Credentials(token=access_token)
            logger.info("Building Google Drive service")
            self.service = build("drive", "v3", credentials=self.credentials)
            logger.info("Google Drive service built successfully")

        except ImportError as e:
            logger.error(
                "Import error occurred", error=str(e), error_type=type(e).__name__
            )
            raise ValueError(
                "Google API client libraries not installed. Please run: pip install -r requirements.txt"
            ) from e
        except Exception as e:
            logger.error(
                "Error initializing Google Drive service",
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback

            logger.error("Full traceback", traceback=traceback.format_exc())

            error_str = str(e).lower()
            if any(
                auth_error in error_str
                for auth_error in [
                    "credentials",
                    "authentication",
                    "unauthorized",
                    "invalid_grant",
                    "token",
                ]
            ):
                raise ValueError(
                    "Authentication failed: Invalid or expired Google Drive credentials. Please provide a valid access token."
                ) from e

            raise ValueError(f"Failed to initialize Google Drive service: {e}") from e

    def extract_file_id(self, url: str) -> str | None:
        """Extract file ID from Google Drive URL"""
        patterns = [
            r"/d/([a-zA-Z0-9-_]+)",
            r"id=([a-zA-Z0-9-_]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)

        if re.match(r"^[a-zA-Z0-9-_]+$", url.strip()):
            return url.strip()

        return None

    async def export_to_markdown(self, file_id: str, ctx: Context | None = None) -> str:
        """Export Google Doc to markdown format (async)"""
        try:
            # Send initial progress notification
            if ctx:
                await ctx.report_progress(progress=0)

            # Start periodic progress notifications in the background
            progress_task = None
            stop_progress = threading.Event()

            if ctx:
                progress_task = asyncio.create_task(
                    self._send_periodic_progress(ctx, stop_progress)
                )

            try:
                content = await anyio.to_thread.run_sync(
                    self._export_to_markdown_sync, file_id
                )
                return str(content)
            finally:
                # Stop the progress notifications
                if progress_task:
                    stop_progress.set()
                    try:
                        await asyncio.wait_for(progress_task, timeout=1.0)
                    except TimeoutError:
                        progress_task.cancel()

        except Exception as e:
            logger.error(
                "Error exporting file",
                file_id=file_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback

            logger.error(
                "Export traceback", file_id=file_id, traceback=traceback.format_exc()
            )

            error_str = str(e).lower()
            if any(
                auth_error in error_str
                for auth_error in [
                    "credentials do not contain the necessary fields",
                    "refresh_token",
                    "invalid_grant",
                    "unauthorized",
                    "authentication",
                    "token",
                ]
            ):
                raise ValueError(
                    "Authentication failed: Invalid or expired Google Drive credentials. Please provide a valid access token."
                ) from e

            raise ValueError(f"Failed to export document: {str(e)}") from e

    def _export_to_markdown_sync(self, file_id: str) -> str:
        """Synchronous export method to run in thread"""
        try:
            logger.info("Starting export for file", file_id=file_id)

            logger.info("Attempting markdown export", export_type="markdown")
            request = self.service.files().export_media(
                fileId=file_id, mimeType="text/markdown"
            )

            logger.info("Executing markdown export request", file_id=file_id)
            markdown_content = request.execute()
            content_length = len(markdown_content) if markdown_content else 0
            logger.info(
                "Markdown export successful",
                file_id=file_id,
                content_length=content_length,
            )

            if isinstance(markdown_content, bytes):
                markdown_content = markdown_content.decode("utf-8")

            return str(markdown_content)

        except Exception as e:
            logger.error(
                "Markdown export failed",
                file_id=file_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            import traceback

            logger.error(
                "Markdown export traceback",
                file_id=file_id,
                traceback=traceback.format_exc(),
            )
            raise e

    async def _send_periodic_progress(
        self, ctx: Context, stop_event: threading.Event
    ) -> None:
        """Send progress notifications every 1 second until stopped"""
        progress_count = 1
        try:
            while not stop_event.is_set():
                await asyncio.sleep(1.0)
                if not stop_event.is_set():
                    await ctx.report_progress(progress=progress_count)
                    progress_count += 1
                    logger.debug(
                        "Sent periodic progress notification", count=progress_count
                    )
        except asyncio.CancelledError:
            logger.debug("Periodic progress notifications cancelled")
        except Exception as e:
            logger.warning("Error sending periodic progress notification", error=str(e))


def extract_bearer_token(ctx: Context) -> str | None:
    """Extract Bearer token from Authorization header

    This function extracts the Bearer token from the HTTP Authorization header
    by accessing the request context and parsing the headers.
    """
    try:
        request_context = ctx.request_context
        if not request_context:
            return None

        if hasattr(request_context, "request") and request_context.request:
            request = request_context.request

            if hasattr(request, "headers"):
                headers = request.headers

                auth_header = headers.get("authorization") or headers.get(
                    "Authorization"
                )
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header[7:]
                    return str(token)

        scope = getattr(request_context, "scope", None)
        if not scope:
            logger.warning("scope is None")
            return None

        if "headers" not in scope:
            logger.warning("No headers found in scope")
            return None

        logger.debug("Found headers in scope", header_count=len(scope["headers"]))

        for k, v in scope["headers"]:
            try:
                header_name = str(k.decode("utf-8")).lower()
                header_value = str(v.decode("utf-8"))

                logger.debug("Processing header", header_name=header_name)

                if header_name == "authorization":
                    if header_value.startswith("Bearer "):
                        token = header_value[7:]
                        return str(token)
                    else:
                        logger.warning(
                            "Authorization header does not start with 'Bearer'",
                            header_prefix=header_value[:7],
                        )

            except UnicodeDecodeError as e:
                logger.error(
                    "Failed to decode header", error=str(e), error_type=type(e).__name__
                )
                continue

        logger.warning("No Bearer token found in Authorization header")
        return None

    except Exception as e:
        logger.error(
            "Error extracting bearer token", error=str(e), error_type=type(e).__name__
        )
        import traceback

        logger.error(
            "Bearer token extraction traceback", traceback=traceback.format_exc()
        )
        return None


mcp: FastMCP = FastMCP("mcp-markdown-server")


@mcp.tool()
async def convert_to_markdown(ctx: Context, url: str) -> str:
    """
    Read the contents of a file from Google Drive. Supports URLs matching patterns:
    - https://docs.google.com/document/d/<file_id>/edit
    - https://drive.google.com/file/d/<file_id>/view
    """
    logger.info(
        "Processing convert_to_markdown request",
        url=url,
        request_id=ctx.request_id,
        client_id=ctx.client_id,
    )

    access_token = extract_bearer_token(ctx)
    if not access_token:
        logger.error("No Bearer token found in Authorization header")
        raise ToolError(
            "Authentication required: Please provide a valid Bearer token in the Authorization header."
        )

    try:
        logger.info("Initializing Google Drive service")
        drive_service = GoogleDriveService(access_token)

        file_id = drive_service.extract_file_id(url)
        if not file_id:
            logger.error("Could not extract file ID from URL", url=url)
            raise ToolError(
                f"Invalid URL format: Could not extract file ID from URL: {url}"
            )

        logger.info("Converting file to markdown", file_id=file_id)

        markdown_content = await drive_service.export_to_markdown(file_id, ctx)

        logger.info("Conversion completed successfully", file_id=file_id)

        return markdown_content

    except ToolError:
        raise
    except ValueError as e:
        logger.error(
            "Service error converting document",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ToolError(f"Document conversion failed: {str(e)}") from e
    except Exception as e:
        logger.error(
            "Unexpected error converting document",
            error=str(e),
            error_type=type(e).__name__,
        )
        raise ToolError(
            f"Internal server error during document conversion: {str(e)}"
        ) from e


if __name__ == "__main__":
    import importlib.util

    try:
        if not importlib.util.find_spec("fastmcp"):
            raise ImportError("fastmcp not found")
        if not importlib.util.find_spec("google.oauth2"):
            raise ImportError("google.oauth2 not found")
        if not importlib.util.find_spec("googleapiclient"):
            raise ImportError("googleapiclient not found")
    except ImportError as e:
        print(f"❌ Dependencies not installed: {e}")
        print("Please run: ./setup.sh")
        print("Or manually: pip install -r requirements.txt")
        sys.exit(1)

    host = os.getenv("HOST", "localhost")
    port = int(os.getenv("PORT", 8000))
    log_level = os.getenv("LOG_LEVEL", "INFO")
    transport = os.getenv("TRANSPORT", "http")

    # Cast transport to the correct literal type
    valid_transports: set[str] = {"stdio", "http", "sse", "streamable-http"}
    if transport not in valid_transports:
        logger.error(
            f"Invalid transport: {transport}. Must be one of {valid_transports}"
        )
        sys.exit(1)

    transport_typed: Literal["stdio", "http", "sse", "streamable-http"] = transport  # type: ignore

    logger.info(
        "Starting FastMCP Markdown server",
        host=host,
        port=port,
        log_level=log_level,
        transport=transport,
    )
    logger.info("Authentication: Bearer token extracted from Authorization header")

    logger.info("Server provides the following tools")
    logger.info(
        "Tool available: convert_to_markdown - Convert Google Drive URLs to markdown"
    )

    if transport == "http":
        logger.info("Server configuration", transport=transport, host=host, port=port)
        logger.info(f"Endpoint: http://{host}:{port}/mcp")
        logger.info("Authentication: Bearer token in Authorization header")

    mcp.run(
        transport=transport_typed,
        host=host,
        port=port,
        log_level=log_level.lower(),
        stateless_http=True,
    )
