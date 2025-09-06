# COMMANDS Queue

Write shell commands to `scripts/commands.todo`, one per line. The Auto Approver will execute NEW lines automatically.

**Rules**
- Use only allow-listed tools: `git`, `pnpm`, `npm`, `node`, `python|py|pip|pytest`, `uvicorn`, `ruff`, `black`, `mypy`, `esbuild`, `electron`, `playwright`.
- No interactive prompts; include flags to run non-interactively.
- Assume Python venv at `.venv` may be active.
- Do not write destructive commands.

**Examples**
git status
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
corepack enable; corepack prepare pnpm@9 --activate
pnpm i
pnpm -C apps/desktop/renderer dev
uvicorn services.asr.app:app --port 7031 --reload
