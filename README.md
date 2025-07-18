# Overview

This is an HTTP MCP server that takes Google Drive URLs and converts them to Markdown.

This is not a standalone server and has to be placed behind Pomerium Proxy, that manages the OAuth2 flow with Google Drive, and additional user authentication enforcement.

This is not an official Pomerium product.

# Create OAuth2 App

You should have an account with Google Cloud.

1. Enable Google Drive API https://console.cloud.google.com/apis/api/drive.googleapis.com
2. Create OAuth2 application https://console.cloud.google.com/auth/clients
3. Set Redirect URL to `https://markdown.mcp.your-domain.com/.pomerium/mcp/oauth/callback`
4. Set Authorized Javascript Origins to `https://markdown.mcp.your-domain.com`

# Configure Pomerium Route

  - from: https://markdown.mcp.your-domain.com
    to: http://localhost:8000
    name: Markdown
    policy:
      allow:
        and:
          - domain:
              is: your-domain.com
    mcp:
      server:
        path: /mcp
        upstream_oauth2:
          client_id: OAUTH-CLIENT-ID
          client_secret: OAUTH-CLIENT-SECRET
          scopes: ["https://www.googleapis.com/auth/file.readonly"]
          endpoint:
            auth_url:  "https://accounts.google.com/o/oauth2/v2/auth"
            token_url: "https://oauth2.googleapis.com/token"
    timeout: 120s
