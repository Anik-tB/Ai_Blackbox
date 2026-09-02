"""
AI Black Box Debugger (AIBD) - Command Line Interface.
Provides daemon lifecycle management (up/down), telemetry exploration, and root cause reporting.
"""

from __future__ import annotations
import json
import os
import signal
import subprocess
import sys
import time
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
PID_FILE = CONFIG_DIR / "daemon.pid"
LOGS_DIR = CONFIG_DIR / "logs"


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
        f"Start platform with: [bold yellow]aidbg up[/bold yellow]\n"
        f"Run your app with: [bold yellow]aidbg run <your-command>[/bold yellow]",
        title="[bold cyan]AIBD Ready[/bold cyan]"
    ))


@app.command()
def up(
    port: int = typer.Option(8765, "--port", "-p", help="Backend API port"),
    dashboard_port: int = typer.Option(3000, "--dashboard-port", "-d", help="Web Dashboard port"),
):
    """Start AIBD Backend and Web Dashboard in the background."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    # Check if already running
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pids = json.load(f)
            backend_pid = pids.get("backend")
            if backend_pid and os.path.exists(f"/proc/{backend_pid}"):
                console.print("[yellow]AIBD is already running in background.[/yellow]")
                status()
                return
        except Exception:
            pass

    backend_log = open(LOGS_DIR / "backend.log", "a")
    frontend_log = open(LOGS_DIR / "frontend.log", "a")

    console.print("[dim]Starting AIBD Backend Server...[/dim]")
    backend_env = os.environ.copy()
    backend_env["AIDBG_PORT"] = str(port)
    backend_proc = subprocess.Popen(
        [sys.executable, "-m", "aidbg.backend.main"],
        stdout=backend_log,
        stderr=backend_log,
        env=backend_env,
        start_new_session=True
    )

    frontend_proc = None
    frontend_dir = Path("frontend")
    if frontend_dir.exists() and (frontend_dir / "package.json").exists():
        console.print("[dim]Starting Web Dashboard...[/dim]")
        cmd = ["npm", "start"] if (frontend_dir / ".next").exists() else ["npm", "run", "dev"]
        frontend_proc = subprocess.Popen(
            cmd,
            cwd=str(frontend_dir),
            stdout=frontend_log,
            stderr=frontend_log,
            start_new_session=True
        )

    # Save PIDs
    with open(PID_FILE, "w") as f:
        json.dump({
            "backend": backend_proc.pid,
            "frontend": frontend_proc.pid if frontend_proc else None,
            "backend_port": port,
            "dashboard_port": dashboard_port
        }, f)

    # Poll health check
    backend_url = f"http://127.0.0.1:{port}"
    healthy = False
    for _ in range(25):
        time.sleep(0.4)
        try:
            with httpx.Client(timeout=1.0) as client:
                res = client.get(f"{backend_url}/api/v1/health")
                if res.status_code == 200:
                    healthy = True
                    db_info = res.json().get("database_type", "Database Connected")
                    break
        except Exception:
            pass

    if healthy:
        console.print(Panel(
            f"[bold green]🚀 AIBD Observability Platform is Running![/bold green]\n\n"
            f"• [bold]Web Dashboard:[/bold]  [cyan]http://localhost:{dashboard_port}[/cyan]\n"
            f"• [bold]Backend API:[/bold]    [cyan]{backend_url}[/cyan]\n"
            f"• [bold]Database:[/bold]       [green]{db_info}[/green]\n\n"
            f"[dim]To observe your app:  [/dim][bold yellow]aidbg run <your-command>[/bold yellow]\n"
            f"[dim]To stop platform:     [/dim][bold red]aidbg down[/bold red]",
            title="[bold cyan]AI Black Box Debugger[/bold cyan]"
        ))
    else:
        console.print("[yellow]AIBD started. Verifying backend initialization...[/yellow]")
        console.print(f"[dim]Logs available at: {LOGS_DIR}/backend.log[/dim]")


@app.command()
def down():
    """Stop all background AIBD services (Backend and Web Dashboard)."""
    stopped_any = False
    if PID_FILE.exists():
        try:
            with open(PID_FILE, "r") as f:
                pids = json.load(f)
            for name, pid in pids.items():
                if pid and isinstance(pid, int):
                    try:
                        os.kill(pid, signal.SIGTERM)
                        stopped_any = True
                    except (ProcessLookupError, OSError):
                        pass
        except Exception:
            pass
        finally:
            PID_FILE.unlink(missing_ok=True)

    # Free ports if lingering
    subprocess.run(["fuser", "-k", "8765/tcp", "3000/tcp"], capture_output=True)
    console.print("[bold green]✓ All AIBD services stopped cleanly.[/bold green]")


@app.command()
def status():
    """Check AIBD connection, database health, and recent incidents."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=2.5) as client:
            resp = client.get(f"{backend_url}/api/v1/health")
            if resp.status_code == 200:
                data = resp.json()
                console.print(f"[bold green]✓ AIBD Backend is active[/bold green] ({backend_url})")
                console.print(f"  Database: [cyan]{data.get('database_type', 'SQLite')}[/cyan] ({data.get('database')})")
                console.print(f"  AI Provider: [cyan]{data.get('ai_provider')}[/cyan]")
                console.print(f"  Web Dashboard: [cyan]http://localhost:3000[/cyan]")
            else:
                console.print(f"[bold red]Backend returned HTTP {resp.status_code}[/bold red]")
    except Exception:
        console.print(f"[bold red]✗ AIBD Backend is not running at {backend_url}[/bold red]")
        console.print("  Start with: [bold yellow]aidbg up[/bold yellow]")


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
    incident_id: str = typer.Argument(..., help="6-character incident ID (e.g. A8F083)"),
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
    incident_id: str = typer.Argument(..., help="6-character incident ID (e.g. A8F083)"),
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
def export(
    incident_id: str = typer.Argument(..., help="6-character incident ID (e.g. A8F083)"),
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Output file path (.md or .json)"),
):
    """Export complete incident postmortem and fix report to Markdown or JSON."""
    backend_url = get_backend_url()
    try:
        with httpx.Client(timeout=5.0) as client:
            exp_resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/explain")
            if exp_resp.status_code == 404:
                console.print(f"[bold red]Incident {incident_id} not found.[/bold red]")
                return
            exp_data = exp_resp.json()

            fix_resp = client.get(f"{backend_url}/api/v1/incidents/{incident_id.upper()}/fix")
            fix_data = fix_resp.json() if fix_resp.status_code == 200 else {}

        target_path = Path(output_file) if output_file else Path(f"incident_{incident_id.upper()}_report.md")

        if target_path.suffix.lower() == ".json":
            combined = {**exp_data, **fix_data}
            with open(target_path, "w") as f:
                json.dump(combined, f, indent=2)
        else:
            md_content = f"""# Incident Postmortem: {exp_data.get('id')} ({exp_data.get('error_type')})

- **Severity:** {exp_data.get('severity', 'HIGH')}
- **Service:** {exp_data.get('service', 'default')}
- **Culprit:** `{exp_data.get('culprit', 'unknown')}`
- **Occurrences:** {exp_data.get('occurrences', 1)}
- **Confidence:** {int((exp_data.get('confidence') or 0.85) * 100)}%

## Root Cause Analysis
{exp_data.get('root_cause', 'N/A')}

## Confirmed Evidence
{chr(10).join(f"- {e}" for e in (exp_data.get('evidence') or []))}

## Suggested Action
{exp_data.get('suggested_fix', 'N/A')}

## Proposed Git Patch Diff
```diff
{fix_data.get('proposed_patch', '# No patch generated')}
```

## Generated Regression Test
```python
{fix_data.get('generated_test', '# No test generated')}
```
"""
            with open(target_path, "w") as f:
                f.write(md_content)

        console.print(f"[bold green]✓ Exported report to:[/bold green] [cyan]{target_path}[/cyan]")
    except Exception as e:
        console.print(f"[bold red]Failed to export incident:[/bold red] {e}")


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
        console.print("  [dim]Tip: Start the backend with 'aidbg up'[/dim]")


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
