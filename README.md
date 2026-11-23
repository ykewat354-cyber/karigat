# Karigat

An open-source, Termux-first coding harness. Status: release candidate. See [verified milestones and remaining work](ROADMAP.md). Requires Python 3.11+ and Git. From a clone, install with `python -m pip install .`.

## How Karigat works

Experimental `--team` delegates files to parallel workers. See the [20-family research review](docs/agent-research.md) and [design and live trial](docs/team-trial.md) before choosing it over a single builder.

`prompt → selected context → plan + frozen checks → generate → verify → repair once → report`

The model proposes files. Karigat writes them to a candidate folder or detached Git worktree and checks the result locally. You decide whether to apply a project patch. Inference is hosted; the phone runs the harness and its checks.

| Start here | What you'll find |
| --- | --- |
| [Agent workflow](docs/workflow.md) | Run diagram, ownership of each step, failure paths and a worked example |
| [Implementation](src/karigat/) · [prompt packs](src/karigat/packs/) | CLI orchestration, provider calls, workspace and verifier code |
| [Offline tests](tests/) · [calibration cases](evals/) | Harness regressions versus checks run against generated artifacts |
| [Contributing](CONTRIBUTING.md) · [roadmap](ROADMAP.md) | How to change the harness and which milestones still need evidence |

## Quick start

Install with `python -m pip install -e ~/karigat`. Run `karigat providers` to check which credentials are present (this does not test connectivity). Set just the API key you want in your own terminal: `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, or `OLLAMA_API_KEY`. OpenRouter uses its free router. For Gemini and Ollama Cloud verify your account has billing disabled / is on a free-only plan, then set `export KARIGAT_FREE_ACCOUNT=1`. The CLI cannot verify your account's billing settings itself.

```sh
karigat run --provider openrouter 'Design a tactile alphabet and produce a printable reference in SVG.'
karigat run --planner gemini --provider ollama --context brief.txt 'Fulfil the attached brief.'
```

## Build, review, repair

OpenCode CLI routes: `karigat run --provider deepseek 'make a habit tracker'` uses OpenCode's free DeepSeek model. `--provider chatgpt` uses the GPT model through your configured OpenCode OpenAI login (subscription quota). Both support `--planner` and explicit `--fallback`; neither is automatically selected by credential discovery. OpenCode manages its own sessions and login.

From any folder, `karigat` opens the interactive prompt. `karigat init` writes optional user defaults for the provider, planner and workflow pack. `karigat doctor` checks local dependencies. Use `karigat --help` for all commands.

### Change an existing project

```sh
karigat context 'fix invoice rounding'   # local ranking; shows suggested files
karigat commands                        # discover available build/test commands
karigat run --repo . --edit src/invoice.py --verify 'python -m unittest discover -s tests' 'Fix invoice rounding'
karigat diff RUN_ID
karigat apply RUN_ID
```

The approved `--verify` command runs against committed HEAD in a temporary baseline worktree and then against the candidate. Reports include exit codes and bounded output. Use this only with trusted projects and commands: worktrees isolate edits, not arbitrary program execution. `--auto-context` explicitly allows Karigat to choose and send matching source files. Apply requires a passing candidate, unchanged HEAD and a clean original working tree. No merge or commit happens automatically. `karigat serve OUTPUT_FOLDER` starts a loopback static preview.

Default runs derive a short plan and independent checks in parallel. `--quick` skips these extra calls. Provide `--checks file.json` for frozen local assertions not included in the generation prompt. Supported checks: file existence, exact JSON values, CSV rows, text, SVG/XML root and SQL behavior in a disposable in-memory database. HTML checks detect unfinished copy, broken anchors and some inert controls. Findings go back to the editor for one repair; first and second attempts remain available. A passing check applies only to the behavior it measures.

`--fallback NAME` permits another hosted service to receive that task on failure. No implicit paid or local route. `--repo DIR --edit path/to/file` includes selected tracked source files and writes to a detached Git worktree pinned to committed HEAD. The original branch and uncommitted changes are left alone. `karigat report ID` includes the diff and check evidence. Without `--repo`, each candidate is in its own `karigat-run-*` directory.

`karigat runs`, `karigat resume ID` and `karigat report ID` use a SQLite journal under `$XDG_STATE_HOME/karigat` (default `~/.local/state/karigat`). Interrupted build/repair stages checkpoint task context and the candidate before writing. A divergent partial write stops for inspection. `--jsonl` emits machine-readable CLI activity. The interactive prompt supports `/models`, `/runs`, `/checks ID`, `/diff ID`, `/resume ID`, `/exit`.

For trusted generated HTML, `karigat browser-check OUTPUT_FOLDER --screenshot mobile.png` opens a fresh headless Chromium in a Termux proot Debian installation (Node 22+, Chromium and proot-distro needed). `--browser` includes the check during generation. It samples a 390×844 viewport, heading, overflow, exceptions and one internal navigation target. External requests are blocked in the inspected page; integrations and form delivery require separate checks.

`python -m unittest discover -s tests` runs offline checks; `python evals/pilot.py --provider openrouter` runs three short paid-account-independent OpenRouter free-router checks on live outputs. Optional cloud use remains subject to provider account terms. The benchmark is preliminary and not a frontier comparison.
