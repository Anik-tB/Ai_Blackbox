"""
AI Black Box Debugger (AIBD) - Command Line Interface.
"""

from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional
import httpx
import typer
import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from aidbg.cli.formatters import console, format_diff, format_incidents_table, format_rca_report, format_test

app = typer.Typer(help="AI Black Box Debugger (AIBD) - Developer Observability and RCA Platform")

CONFIG_DIR = Path(".aidbg")
CONFIG_FILE = CONFIG_DIR / "config.yaml"


def load_config() -> dict:
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            pass
    return {}


def get_backend_url() -> str:
    cfg = load_config()
    return cfg.get("backend_url", "http://127.0.0.1:8765")


@app.command()
def init(
    service: str = typer.Option("demo-service", "--service", "-s", help="Application service name"),
    backend_url: str = typer.Option("http://127.0.0.1:8765", "--backend", "-b", help="AIBD Backend URL"),
    supabase_url: Optional[str] = typer.Option(None, "--supabase-url", help="Supabase Project URL"),
    supabase_key: Optional[str] = typer.Option(None, "--supabase-key", help="Supabase Anon/Service Key"),
):
    """Initialize AIBD configuration in the current project directory."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    config_data = {
        "service_name": service,
        "backend_url": backend_url,
        "environment": "development",
        "redaction": {
            "enabled": True,
            "patterns": ["password", "token", "secret", "cookie", "api_key"]
        },
        "supabase": {
            "url": supabase_url or "",
            "key": supabase_key or "",
            "db_url": ""
        },
        "ai": {
            "provider": "fallback"
        }
    }
    with open(CONFIG_FILE, "w") as f:
        yaml.dump(config_data, f, default_flow_style=False)

    console.print(Panel(
        f"[bold green]Initialized AIBD configuration at {CONFIG_FILE}[/bold green]\n\n"
        f"Service: [cyan]{service}[/cyan]\n"
        f"Backend: [cyan]{backend_url}[/cyan]\n\n"
        f"Run your app with: [bold yellow]aidbg run <your-command>[/bold yellow]",
        title="[bold cyan]AIBD Ready[/bold cyan]"
    ))


@app.command()
def status():
    """Check AIBD connection and recent incident summary."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=2.0) as client:
            resp = client.get(f"{backend_url}/api/v1/health")
            if resp.status_code == 200:
                data = resp.json()
                console.print(f"[bold green]✓ AIBD Backend is active[/bold green] ({backend_url})")
                console.print(f"  Database: [cyan]{data.get('database_type', 'SQLite')}[/cyan] ({data.get('database')})")
                console.print(f"  AI Provider: [cyan]{data.get('ai_provider')}[/cyan]")
            else:
                console.print(f"[bold red]Backend returned HTTP {resp.status_code}[/bold red]")
    except Exception as e:
        console.print(f"[bold red]✗ Could not reach AIBD Backend at {backend_url}[/bold red]")
        console.print(f"  Start backend server with: [bold yellow]python -m aidbg.backend.main[/bold yellow]")


@app.command(
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def run(
    ctx: typer.Context,
    command: str = typer.Argument(..., help="The executable to run (e.g. python3, uvicorn)"),
):
    """Run an application with AIBD automatic error capture enabled."""
    cmd = [command] + ctx.args
    backend_url = get_backend_url()
    cfg = load_config()
    env = os.environ.copy()
    env["AIDBG_ENDPOINT"] = f"{backend_url}/api/v1/incidents/ingest"
    env["AIDBG_SERVICE"] = cfg.get("service_name", "app")
    env["PYTHONPATH"] = f"{os.getcwd()}:{env.get('PYTHONPATH', '')}"

    console.print(f"[dim]aidbg supervisor active -> observing: {' '.join(cmd)}[/dim]")
    try:
        proc = subprocess.run(cmd, env=env)
        sys.exit(proc.returncode)
    except KeyboardInterrupt:
        console.print("\n[dim]Process terminated by user[/dim]")
        sys.exit(0)


@app.command()
def incidents(
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity (CRITICAL, HIGH, MEDIUM, LOW)"),
    status: Optional[str] = typer.Option(None, "--status", help="Filter by status (open, resolved)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """List deduplicated incidents captured by AIBD."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=3.0) as client:
            params = {}
            if severity:
                params["severity"] = severity
            if status:
                params["status"] = status
            resp = client.get(f"{backend_url}/api/v1/incidents", params=params)
            resp.raise_for_status()
            data = resp.json()

            if json_output:
                print(json.dumps(data, indent=2))
                return

            if not data:
                console.print("[dim]No incidents detected yet. Run your app and trigger an error to observe.[/dim]")
                return

            table = format_incidents_table(data)
            console.print(table)
    except Exception as e:
        console.print(f"[bold red]Failed to fetch incidents:[/bold red] {e}")


@app.command()
def explain(
    incident_id: str = typer.Argument(..., help="6-character incident ID (e.g. A7F82C)"),
    json_output: bool = typer.Option(False, "--json", help="Output raw JSON"),
):
    """Explain root cause, causal graph, and evidence for an incident."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=10.0) as client:
            resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/explain")
            if resp.status_code == 404:
                console.print(f"[bold red]Incident {incident_id} not found.[/bold red]")
                return
            resp.raise_for_status()
            data = resp.json()

            if json_output:
                print(json.dumps(data, indent=2))
                return

            format_rca_report(data)
    except Exception as e:
        console.print(f"[bold red]Failed to explain incident:[/bold red] {e}")


@app.command()
def fix(
    incident_id: str = typer.Argument(..., help="6-character incident ID (e.g. A7F82C)"),
    branch: bool = typer.Option(False, "--branch", "-b", help="Create a Git branch for the fix"),
):
    """View proposed fix patch, diff, and generated test suite."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=5.0) as client:
            resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/fix")
            if resp.status_code == 404:
                console.print(f"[bold red]Incident {incident_id} not found.[/bold red]")
                return
            data = resp.json()

            console.print(f"\n[bold green]PROPOSED FIX FOR {incident_id.upper()}[/bold green]\n")
            patch = data.get("proposed_patch")
            if patch:
                console.print(Panel(format_diff(patch), title="[bold cyan]PROPOSED PATCH DIFF[/bold cyan]"))
            else:
                console.print("[dim]No diff generated.[/dim]")

            test_code = data.get("generated_test")
            if test_code:
                console.print(Panel(format_test(test_code), title="[bold cyan]GENERATED REGRESSION TEST[/bold cyan]"))

            if branch:
                b_resp = client.post(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/branch")
                b_data = b_resp.json()
                if b_data.get("status") == "success":
                    console.print(f"[bold green]✓ Created git branch:[/bold green] [cyan]{b_data.get('branch')}[/cyan]")
                else:
                    console.print(f"[yellow]Branch notice:[/yellow] {b_data.get('detail')}")

    except Exception as e:
        console.print(f"[bold red]Failed to get fix:[/bold red] {e}")


@app.command()
def logs(incident_id: str = typer.Argument(..., help="Incident ID")):
    """View breadcrumbs leading up to an incident."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/logs")
            logs_data = resp.json()
            if not logs_data:
                console.print("[dim]No logs recorded for this incident.[/dim]")
                return
            console.print(f"[bold cyan]Logs for Incident {incident_id.upper()}:[/bold cyan]")
            for entry in logs_data:
                lvl = entry.get("level", "info").upper()
                msg = entry.get("message", "")
                cat = entry.get("category", "")
                console.print(f"  [dim]{cat}[/dim] [{lvl}] {msg}")
    except Exception as e:
        console.print(f"[bold red]Error fetching logs:[/bold red] {e}")


@app.command()
def trace(incident_id: str = typer.Argument(..., help="Incident ID")):
    """View execution trace and stack frames for an incident."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/trace")
            trace_data = resp.json()
            frames = trace_data.get("frames", [])
            if not frames:
                console.print("[dim]No stack trace recorded for this incident.[/dim]")
                return

            console.print(f"[bold cyan]Stack Trace for Incident {incident_id.upper()}:[/bold cyan]")
            for f in frames:
                fn = f.get("filename", "")
                line = f.get("lineno", 0)
                func = f.get("function", "")
                code = f.get("code_line", "")
                console.print(f"  [dim]{fn}:{line}[/dim] in [bold]{func}[/bold]")
                if code:
                    console.print(f"    [yellow]{code}[/yellow]")
    except Exception as e:
        console.print(f"[bold red]Error fetching trace:[/bold red] {e}")


@app.command()
def doctor():
    """Run diagnostics on environment, database, and backend connectivity."""
    backend_url = get_backend_url()
    console.print(Panel("[bold cyan]AI Black Box Debugger - System Diagnostics[/bold cyan]"))
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get(f"{backend_url}/api/v1/doctor")
            checks = resp.json().get("checks", [])
            for c in checks:
                icon = "[green]✓ PASS[/green]" if c["status"] == "pass" else "[red]✗ FAIL[/red]"
                console.print(f"  {icon} [bold]{c['name']}[/bold]: {c['details']}")
    except Exception:
        console.print("  [red]✗ FAIL[/red] [bold]Backend Connection[/bold]: Backend not reachable at " + backend_url)
        console.print("  [dim]Tip: Start the backend with 'python -m aidbg.backend.main'[/dim]")


@app.command()
def config():
    """View current local configuration."""
    cfg = load_config()
    if not cfg:
        console.print("[dim]No local config found. Run 'aidbg init' to create one.[/dim]")
        return
    console.print(Panel(yaml.dump(cfg, default_flow_style=False), title="[bold cyan].aidbg/config.yaml[/bold cyan]"))


if __name__ == "__main__":
    app()
