from __future__ import annotations

import json
import shutil
from pathlib import Path

import typer
import uvicorn

from helio.risk.checks import run_local_checks
from helio.schemas.account import AccountState
from helio.schemas.trade_intent import TradeIntent
from helio.service.deps import get_app_state

app = typer.Typer(help="Helio — deterministic risk/strategy/learning engines for LLM-assisted OKX trading.")

_CONFIG_DIR = Path("backend/config")


@app.command()
def init_config() -> None:
    """Copy the example risk/strategy configs to their real (gitignored) paths."""
    pairs = [
        (_CONFIG_DIR / "risk_config.example.yaml", _CONFIG_DIR / "risk_config.yaml"),
        (_CONFIG_DIR / "strategy_config.example.yaml", _CONFIG_DIR / "strategy_config.yaml"),
        (_CONFIG_DIR / "guard_config.example.yaml", _CONFIG_DIR / "guard_config.yaml"),
        (_CONFIG_DIR / "guard_profile_low.example.yaml", _CONFIG_DIR / "guard_profile_low.yaml"),
        (_CONFIG_DIR / "guard_profile_balanced.example.yaml", _CONFIG_DIR / "guard_profile_balanced.yaml"),
        (_CONFIG_DIR / "guard_profile_high.example.yaml", _CONFIG_DIR / "guard_profile_high.yaml"),
    ]
    for src, dst in pairs:
        if dst.exists():
            typer.echo(f"skip (already exists): {dst}")
            continue
        if not src.exists():
            typer.echo(f"error: example file not found: {src}")
            raise typer.Exit(code=1)
        shutil.copy(src, dst)
        typer.echo(f"created {dst}")
    typer.echo("Review the new config files and adjust limits before running Helio.")


@app.command()
def serve() -> None:
    """Run the local-only FastAPI service (binds 127.0.0.1 only)."""
    state = get_app_state()
    typer.echo(f"Helio serving on http://127.0.0.1:{state.settings.service_port} (mode={state.settings.mode})")
    uvicorn.run("helio.service.app:app", host="127.0.0.1", port=state.settings.service_port)


@app.command()
def verify() -> None:
    """Run the local portion of the verification checklist.

    The OKX CONNECTION, ACCOUNT, MARKET DATA, PORTFOLIO, and SPOT EXECUTION
    checks can only be performed by Claude Code calling MCP tools — see
    docs/runbooks/verify.md for the exact prompt to run those, then re-check
    `GET /verify` (or the dashboard) for the merged result.
    """
    state = get_app_state()
    all_passed = True
    for name, passed, detail in run_local_checks(state):
        status = "PASS" if passed else "FAIL"
        all_passed = all_passed and passed
        typer.echo(f"{name}: {status} — {detail}")

    typer.echo("")
    typer.echo("MCP-sourced checks (OKX CONNECTION, ACCOUNT, MARKET DATA, PORTFOLIO, SPOT EXECUTION)")
    typer.echo("must be run by Claude Code — see docs/runbooks/verify.md")

    if not all_passed:
        raise typer.Exit(code=1)


@app.command()
def risk_check(intent_file: Path, account_file: Path) -> None:
    """Evaluate a TradeIntent JSON file against an AccountState JSON file."""
    state = get_app_state()
    intent = TradeIntent.model_validate_json(intent_file.read_text())
    account = AccountState.model_validate_json(account_file.read_text())
    decision = state.risk_engine.evaluate(intent, account)
    typer.echo(json.dumps(decision.model_dump(mode="json"), indent=2))
    if not decision.approved:
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
