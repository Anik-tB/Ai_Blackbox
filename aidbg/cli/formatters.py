"""
Rich terminal output formatters for aidbg CLI.
Provides clean Sentry/Datadog developer aesthetic for incidents, RCA, diffs, and trees.
"""

from __future__ import annotations
import json
from typing import Any, Dict, List
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.tree import Tree
from rich.text import Text

console = Console()


def format_incidents_table(incidents: List[Dict[str, Any]]) -> Table:
    """Render a clean incident table."""
    table = Table(title="AI Black Box Debugger - Incidents", show_header=True, header_style="bold cyan")
    table.add_column("ID", style="bold yellow", width=10)
    table.add_column("ERROR", style="bold white", width=28)
    table.add_column("COUNT", justify="right", style="cyan", width=8)
    table.add_column("SEVERITY", style="bold", width=12)
    table.add_column("SERVICE", style="dim", width=18)
    table.add_column("LAST SEEN", style="dim", width=18)

    severity_colors = {
        "CRITICAL": "[bold red]CRITICAL[/bold red]",
        "HIGH": "[bold yellow]HIGH[/bold yellow]",
        "MEDIUM": "[bold blue]MEDIUM[/bold blue]",
        "LOW": "[green]LOW[/green]",
    }

    for inc in incidents:
        sev = inc.get("severity", "LOW").upper()
        sev_styled = severity_colors.get(sev, sev)
        table.add_row(
            inc.get("id", "UNKNOWN"),
            inc.get("error_type", "UnknownError")[:26],
            str(inc.get("occurrences", 1)),
            sev_styled,
            inc.get("service", "default")[:16],
            inc.get("status", "open")
        )
    return table


def format_rca_report(explanation: Dict[str, Any]) -> None:
    """Render structured Root Cause Analysis in clean terminal format."""
    inc_id = explanation.get("incident_id", "UNKNOWN")
    root_cause = explanation.get("root_cause", "No root cause identified.")
    confidence = explanation.get("confidence", 0.0)
    conf_pct = int(confidence * 100) if confidence <= 1.0 else int(confidence)
    evidence = explanation.get("evidence", [])
    hypotheses = explanation.get("hypotheses", [])
    fix = explanation.get("recommended_fix", "No fix available.")
    causal_data = explanation.get("causal_chain", {})

    console.print(f"\n[bold green]INCIDENT {inc_id} EXPLANATION[/bold green]\n")

    # 1. ROOT CAUSE
    console.print(Panel(f"[bold white]{root_cause}[/bold white]", title="[bold red]ROOT CAUSE[/bold red]", border_style="red"))

    # 2. CONFIDENCE
    conf_color = "green" if conf_pct >= 85 else ("yellow" if conf_pct >= 60 else "red")
    console.print(f"\n[bold]CONFIDENCE[/bold]\n[{conf_color} bold]{conf_pct}%[/{conf_color} bold]\n")

    # 3. CAUSAL CHAIN
    console.print("[bold cyan]CAUSAL CHAIN[/bold cyan]")
    nodes = causal_data.get("nodes", []) if isinstance(causal_data, dict) else []
    edges = causal_data.get("edges", []) if isinstance(causal_data, dict) else []

    if edges:
        for idx, edge in enumerate(edges):
            u_node = next((n for n in nodes if n["id"] == edge["from"]), {"label": edge["from"]})
            v_node = next((n for n in nodes if n["id"] == edge["to"]), {"label": edge["to"]})
            if idx == 0:
                console.print(f"  [bold]{u_node.get('label')}[/bold]")
            console.print(f"      [dim]↓ ({edge.get('reason', 'caused')})[/dim]")
            console.print(f"  [bold]{v_node.get('label')}[/bold]")
    else:
        console.print("  [dim]No causal edges reconstructed[/dim]")

    # 4. EVIDENCE
    console.print("\n[bold cyan]EVIDENCE (VERIFIED FACTS)[/bold cyan]")
    if evidence:
        for item in evidence:
            console.print(f"  [green]✓[/green] {item}")
    else:
        console.print("  [dim]No verified evidence recorded[/dim]")

    # 5. HYPOTHESES
    if hypotheses:
        console.print("\n[bold cyan]HYPOTHESES[/bold cyan]")
        for h in hypotheses:
            desc = h.get("description", "") if isinstance(h, dict) else str(h)
            h_conf = h.get("confidence", 0.0) if isinstance(h, dict) else 0.0
            console.print(f"  • {desc} [dim]({int(h_conf*100)}% confidence)[/dim]")

    # 6. RECOMMENDED FIX
    console.print(Panel(f"[bold white]{fix}[/bold white]", title="[bold green]RECOMMENDED FIX[/bold green]", border_style="green"))


def format_diff(diff_text: str) -> Syntax:
    """Colorize a unified diff."""
    return Syntax(diff_text, "diff", theme="monokai", line_numbers=True)


def format_test(test_code: str) -> Syntax:
    """Colorize generated pytest code."""
    return Syntax(test_code, "python", theme="monokai", line_numbers=True)
