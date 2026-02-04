# Environment loading (dev): stop manually sourcing `.env`

Bash does NOT automatically load `.env` files.
A `.env` file is just text unless something loads it.

If you run `uv run ...` without exporting variables, your app won’t see them.

## Recommended: direnv (auto-load per repo)
direnv loads env vars automatically when you `cd` into the repo and unloads them when you leave.

### Install
```bash
sudo apt update && sudo apt install -y direnv
echo 'eval "$(direnv hook bash)"' >> ~/.bashrc
source ~/.bashrc
```

### Enable in this repo

From repo root:

cd ~/projects/google-workspace-automation-engine
echo 'dotenv' > .envrc
direnv allow


Now, any time you cd into this repo, .env loads automatically.

### Verify
cd ~
cd ~/projects/google-workspace-automation-engine
echo "$GOOGLE_CLIENT_ID"


If it prints a value, you’re good.

### Why this is safe

direnv requires explicit approval: direnv allow

.env should be gitignored (secrets stay local)

.envrc can be committed because it contains only dotenv

---

## Client factory env vars (HTTP timeout + retry behavior)

These control retry/timeout behavior in `gw_engine.clients.settings_from_env()`:

- `GW_HTTP_TIMEOUT_S` (default: 30) — HTTP timeout for API calls
- `GW_HTTP_MAX_RETRIES` (default: 5) — maximum retry attempts
- `GW_HTTP_INITIAL_BACKOFF_S` (default: 0.5) — initial backoff in seconds
- `GW_HTTP_MAX_BACKOFF_S` (default: 8.0) — cap on backoff in seconds
- `GW_HTTP_JITTER_RATIO` (default: 0.2) — jitter as ±ratio (0.2 = ±20%)

Example `.env`:
```bash
GW_HTTP_TIMEOUT_S=60
GW_HTTP_MAX_RETRIES=3
GW_HTTP_INITIAL_BACKOFF_S=1.0
```

## Alternative: manual (works but annoying)
set -a
source .env
set +a


---

If you want, I can also produce a tiny `docs/00-index.md` that links these docs in order, but the above is the minimum “clean set” to reflect what you actually built in T4.
::contentReference[oaicite:7]{index=7}
