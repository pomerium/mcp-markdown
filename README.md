# Overview

This is an HTTP MCP server that takes Google Drive URLs and converts them to Markdown.

This is not a standalone server and has to be placed behind Pomerium Proxy, that manages the OAuth2 flow with Google Drive, and additional user authentication enforcement.

This is not an official Pomerium product.

# Create OAuth2 App

You should have an account with Google Cloud.

1. Enable Google Drive API https://console.cloud.google.com/apis/api/drive.googleapis.com
2. Create OAuth2 application https://console.cloud.google.com/auth/clients
3. Set Redirect URL to `https://markdown.YOUR-DOMAIN.com/.pomerium/mcp/oauth/callback`
4. Set Authorized Javascript Origins to `https://markdown.YOUR-DOMAIN.com`

# Install To Kubernetes

### Deploy this MCP server

Install with Kustomize:
```shell
kubectl apply -k github.com/pomerium/mcp-markdown/k8s
```

check your deployment:
```shell
kubectl rollout status deployment/mcp-markdown -n pomerium-mcp-markdown
```

### Front it with Pomerium Ingress Controller

[Install and configure](https://main.docs.pomerium.com/docs/deploy/k8s/install) Pomerium Ingress controller that would front your HTTP MCP Servers.

Pomerium uses a dedicated `pomerium` `IngressClass` and does not interfere with your existing controllers.

### Deploy Ingress and Secret

Create [`Ingress`](./k8s/ingress-example.yaml) and [OAuth2 `Secret`](./k8s/secret-example.yaml) using examples provided and deploy them to your cluster in the `pomerium-mcp-markdown` namespace.

# Install on a VM or Docker Compose

```yaml
routes:
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
```
