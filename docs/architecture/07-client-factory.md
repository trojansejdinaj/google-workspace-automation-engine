# Client Factory: central builder for Gmail/Drive/Sheets clients

The **Client Factory** is the single point of construction for Google API clients. It encapsulates:
- Credential selection (Service Account vs OAuth)
- Scope assignment
- HTTP timeout and retry configuration
- Rate-limit-aware retry logic

This doc explains how it works and how to use it.

---

## What it is

**Location**: `src/gw_engine/clients.py`

A small module that builds **Google API clients** (Drive, Sheets, Gmail) with:
- **Automatic scope selection** based on API + auth method
- **Robust retries** on transient failures (429, 5xx, rate-limited 403)
- **Exponential backoff + jitter** to avoid thundering herd
- **Configurable timeouts** for slow networks

It's called by the Engine Runtime to get ready-to-use API clients.

---

## How to use it in workflows

```python
from gw_engine.clients import build_clients

# Build all three clients with same config
svc = build_clients(cfg=config)  # or pass settings=ClientSettings(...)

# Now use them:
sheet = svc.sheets.spreadsheets().get(spreadsheetId="...").execute()
files = svc.drive.files().list().execute()
profile = svc.gmail.users().getProfile(userId="me").execute()
```

That's it. The factory handles credentials, scopes, retries, and timeouts behind the scenes.

---

## Retry behavior (what gets retried)

The factory wraps requests in a **retry wrapper** that:

1. **Retries on these HTTP statuses**:
   - `429` (Too Many Requests) — standard rate limit
   - `500, 502, 503, 504` — server errors (transient)

2. **Retries on rate-limited 403**:
   - If the 403 response body contains reason `rateLimitExceeded` or `userRateLimitExceeded`
   - (Google sometimes uses 403 instead of 429 for rate limits)

3. **Does NOT retry**:
   - `401` — auth failed (not retryable; credentials are bad)
   - `403` without rate-limit reason — permission denied
   - `404` — file not found
   - Other 4xx errors

4. **Backoff strategy**:
   - Exponential backoff: starts at `GW_HTTP_INITIAL_BACKOFF_S`, doubles each retry
   - Capped at `GW_HTTP_MAX_BACKOFF_S`
   - Jitter applied: ±`GW_HTTP_JITTER_RATIO` (default ±20%)
   - Max retries: `GW_HTTP_MAX_RETRIES` (default 5)

### Backoff example
With defaults:
- Attempt 1: fails with 429
- Wait ~0.5s (initial backoff + jitter)
- Attempt 2: fails with 429
- Wait ~1.0s (doubled)
- Attempt 3: fails with 429
- Wait ~2.0s (doubled)
- ...up to 8.0s cap

If all retries exhausted, the error is raised to the workflow.

---

## Environment variables (tuning retry/timeout)

Set these in `.env` or your deployment env. **All are optional; defaults work well.**

| Variable | Default | Meaning |
|----------|---------|---------|
| `GW_HTTP_TIMEOUT_S` | `30` | Socket timeout (seconds) for each HTTP call |
| `GW_HTTP_MAX_RETRIES` | `5` | Maximum retry attempts per request |
| `GW_HTTP_INITIAL_BACKOFF_S` | `0.5` | Starting backoff (seconds) |
| `GW_HTTP_MAX_BACKOFF_S` | `8.0` | Maximum backoff cap (seconds) |
| `GW_HTTP_JITTER_RATIO` | `0.2` | Jitter range: ±ratio (0.2 = ±20%) |

### Example: conservative retry policy
```bash
# For slow/unreliable networks
GW_HTTP_TIMEOUT_S=60
GW_HTTP_MAX_RETRIES=10
GW_HTTP_INITIAL_BACKOFF_S=2.0
GW_HTTP_MAX_BACKOFF_S=30.0
```

### Example: aggressive retry policy
```bash
# For fast networks with strict rate limits
GW_HTTP_TIMEOUT_S=10
GW_HTTP_MAX_RETRIES=3
GW_HTTP_INITIAL_BACKOFF_S=0.1
GW_HTTP_MAX_BACKOFF_S=2.0
```

---

## Design: why wrap instead of subclass?

Early versions subclassed `googleapiclient.http.HttpRequest`. This caused:
- Type checker (`mypy`) complaints about subclassing untyped base classes
- Maintenance burden when `googleapiclient` updates its internals

**Solution**: Composition + Protocol typing.

```python
# Protocol defines the "request-like" interface
class _ExecRequest(Protocol):
    def execute(self, http=None, num_retries=0) -> Any: ...

# Wrapper delegates to real request object
class _RetryingRequest:
    def __init__(self, inner: _ExecRequest, retry_policy: RetryPolicy) -> None:
        self._inner = inner
        self._policy = retry_policy

    def execute(self, http=None, num_retries=0) -> Any:
        # Our retry logic here
        return self._inner.execute(http=http, num_retries=0)
```

Benefits:
- Clean separation of concerns
- Mypy-friendly (no subclassing untyped code)
- Easy to test (mock `_inner`)
- Works with any request-like object

---

## Scope selection (automatic)

The factory calls `scopes_for_api(api=..., use_service_account=...)` to pick the right scopes.

| API | Service Account | OAuth User |
|-----|-----------------|------------|
| Drive | `https://www.googleapis.com/auth/drive` | `https://www.googleapis.com/auth/drive.file` |
| Sheets | `https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/drive` | `https://www.googleapis.com/auth/spreadsheets`, `https://www.googleapis.com/auth/drive.file` |
| Gmail | (not used; always OAuth) | `https://www.googleapis.com/auth/gmail.readonly` |

**Note**: You don't pick scopes in workflows. The factory does it for you based on `config.google_auth.service_account_json`.

---

## What it does NOT do

- **No infinite retries**: capped at `GW_HTTP_MAX_RETRIES`
- **No silent failures**: non-retryable errors fail fast and raise
- **No circuit breaker**: retries are per-request, not per-service
- **No metrics/tracing**: retries are silent (logged via structured logs, not separately)
- **No credential refresh**: credentials are loaded before the client is built; refresh happens at auth time

---

## Internal flow (diagram)

```
build_clients(cfg, settings)
  ↓
  for api in ["drive", "sheets", "gmail"]:
    ↓
    build_service(api=..., cfg=..., settings=...)
      ↓
      scopes_for_api(api, use_service_account)
      ↓
      choose_creds (SA or OAuth based on config)
      ↓
      AuthorizedHttp(creds, timeout=...)
      ↓
      build(api, version, http=..., requestBuilder=...)
        ↓
        requestBuilder called for each request
          ↓
          returns _RetryingRequest(inner=HttpRequest(...), policy=...)
      ↓
      return cast(ServiceType, svc)
  ↓
  return Services(drive=..., sheets=..., gmail=...)
```

When you call `.execute()` on a request:
1. `_RetryingRequest.execute()` is called
2. It tries `_inner.execute()` (the real `HttpRequest`)
3. If `HttpError` occurs and is retryable:
   - Increment attempt counter
   - If retries remaining: sleep + exponential backoff, then loop
   - Else: raise the error
4. If success: return response

---

## Testing the client factory

See `tests/test_clients_factory.py` for:
- Mock credential creation
- Retry logic (simulated 429 errors)
- Timeout behavior
- Settings parsing from env

Example:
```python
def test_retry_on_429():
    cfg = AppConfig(...)
    svc = build_clients(cfg=cfg, settings=ClientSettings(retry=RetryPolicy(max_retries=3)))

    # Simulate a 429 error via mock
    # Verify: request retried 3 times before raising
```

---

## Troubleshooting

### "429 Too Many Requests" errors keep happening
- Increase `GW_HTTP_MAX_RETRIES` or `GW_HTTP_MAX_BACKOFF_S`
- Check if your workflow is doing large batch operations; consider adding delays between API calls
- Verify Service Account is not quota-limited (GW_SA_TEST_SHEET_ID test can help)

### "Request timeout" (default 30s)
- Increase `GW_HTTP_TIMEOUT_S` (default 30)
- This usually means your network is slow or the API is slow; not a problem with the factory

### "401 Unauthorized"
- Not retried; your credentials are invalid/expired
- Check `GOOGLE_REFRESH_TOKEN`, `GOOGLE_SERVICE_ACCOUNT_JSON`, etc.
- See [docs/architecture/05-auth.md](05-auth.md) for setup

### "403 Forbidden" (non-rate-limit)
- Not retried; you don't have permission to access the resource
- Check that the file/sheet is shared with your Service Account email (if using SA)
- Check that your OAuth scopes include the necessary permissions

---

## Summary

The Client Factory is a thin but essential layer:
- **For you**: one import (`build_clients`), done
- **For reliability**: retries handle transient failures, timeout handles slow networks
- **For maintainability**: centralized scope/timeout/retry logic, easy to tune or update

Use it. Don't reinvent HTTP request logic in workflows.
