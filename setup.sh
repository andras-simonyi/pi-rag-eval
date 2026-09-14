#!/usr/bin/env bash
#
# setup.sh — install everything this lab needs, in a blank Codespace.
#
#   ./setup.sh
#
# Idempotent: safe to re-run after a disconnect.

set -uo pipefail

# --- pin these before the course -------------------------------------------
PI_PACKAGE="${PI_PACKAGE:-@mariozechner/pi-coding-agent}"
PI_VERSION="${PI_VERSION:-}"          # e.g. 0.84.0 — leave empty for latest
MCP_ADAPTER_VERSION="${MCP_ADAPTER_VERSION:-}"   # e.g. 2.33.0
NODE_MIN_MAJOR=22
NODE_MIN_MINOR=19
# ---------------------------------------------------------------------------

say() { printf '\n\033[1m--> %s\033[0m\n' "$1"; }

say "Checking Node"
node_ok=false
if command -v node >/dev/null 2>&1; then
  raw=$(node --version)              # v22.19.0
  major=$(echo "${raw#v}" | cut -d. -f1)
  minor=$(echo "${raw#v}" | cut -d. -f2)
  echo "    found $raw"
  if [ "$major" -gt "$NODE_MIN_MAJOR" ] || \
     { [ "$major" -eq "$NODE_MIN_MAJOR" ] && [ "$minor" -ge "$NODE_MIN_MINOR" ]; }; then
    node_ok=true
  fi
fi

if [ "$node_ok" = false ]; then
  echo "    need >= ${NODE_MIN_MAJOR}.${NODE_MIN_MINOR}; installing via nvm"
  export NVM_DIR="${NVM_DIR:-$HOME/.nvm}"
  # shellcheck disable=SC1091
  [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"
  if command -v nvm >/dev/null 2>&1; then
    nvm install 22 >/dev/null && nvm use 22 >/dev/null
    nvm alias default 22 >/dev/null
    echo "    now $(node --version)"
  else
    echo "    nvm not found. Install Node 22 manually, then re-run." >&2
    exit 1
  fi
fi

say "Installing Pi"
spec="$PI_PACKAGE"
[ -n "$PI_VERSION" ] && spec="${PI_PACKAGE}@${PI_VERSION}"
npm install -g --ignore-scripts "$spec" 2>&1 | tail -2
command -v pi >/dev/null || { echo "pi did not land on PATH" >&2; exit 1; }
pi --version

say "Installing the MCP adapter"
# Gives Pi a single ~200-token proxy tool instead of every server's full schema.
adapter="npm:pi-mcp-adapter"
[ -n "$MCP_ADAPTER_VERSION" ] && adapter="npm:pi-mcp-adapter@${MCP_ADAPTER_VERSION}"
pi install "$adapter" || echo "    (install failed — Part 9 of the guide has the manual route)"

say "Python dependencies"
pip install --quiet --no-input -r tools/requirements.txt && echo "    ok"

say "Convenience wrapper"
mkdir -p "$HOME/.local/bin"
cat > "$HOME/.local/bin/corpus-search" <<WRAP
#!/usr/bin/env bash
exec python3 "$(pwd)/tools/corpus_search.py" "\$@"
WRAP
chmod +x "$HOME/.local/bin/corpus-search"
grep -q 'HOME/.local/bin' "$HOME/.bashrc" 2>/dev/null || \
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
export PATH="$HOME/.local/bin:$PATH"

cat <<'DONE'

===========================================================================
Setup complete.

Next:
  1. export CORPUS_URL="https://xxxxxxxxxxxx.gradio.live"
  2. export ANTHROPIC_API_KEY="..."      (or run `pi` then `/login`)
  3. python tools/corpus_search.py "dagasztógép" --top-k 3

A blank Codespace is not attached to a repository, so nothing here is
backed up. Before you finish, push your work:

  gh repo create pi-rag-eval --private --source=. --push
===========================================================================
DONE
