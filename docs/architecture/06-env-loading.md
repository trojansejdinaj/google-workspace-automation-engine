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

## Alternative: manual (works but annoying)
set -a
source .env
set +a


---

If you want, I can also produce a tiny `docs/00-index.md` that links these docs in order, but the above is the minimum “clean set” to reflect what you actually built in T4.
::contentReference[oaicite:7]{index=7}
