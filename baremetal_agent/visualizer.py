"""Live trajectory visualization using rich.

Renders agent loop steps as they happen: tool call panels, response panels,
error displays, and a trajectory summary footer. Used by agent.py in place
of raw JSON dumps when config.VERBOSE is False.
"""

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from baremetal_agent import config

console = Console(highlight=False)


def _fmt_args(args: dict) -> str:
    """Format tool arguments as a compact one-liner."""
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 60:
            v = v[:57] + "..."
        parts.append(f'{k}="{escape(str(v))}"' if isinstance(v, str) else f"{k}={v}")
    return ", ".join(parts)


def _fmt_result_summary(result: str) -> str:
    """Summarize a tool result: first 3 lines + truncation notice."""
    lines = result.splitlines()
    preview_lines = [escape(line) for line in lines[:3]]
    indented = "\n     ".join(preview_lines)
    if len(lines) > 3:
        indented += f"\n     ... ({len(lines) - 3} more lines)"
    return indented


def _fmt_ms(ms: float) -> str:
    """Format milliseconds for display."""
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{int(ms)}ms"


def _fmt_tokens(metrics: dict) -> str:
    """Format token count from API response metrics."""
    prompt = metrics.get("prompt_tokens", 0)
    completion = metrics.get("completion_tokens", 0)
    total = prompt + completion
    return f"{total} tok"


def render_tool_call_step(
    iteration: int,
    tool_calls_with_results: list[dict],
    api_duration_ms: float,
    metrics: dict,
) -> None:
    """Render a complete tool-call step panel.

    tool_calls_with_results is a list of dicts:
        {"name": str, "args": dict, "result": str, "duration_ms": float,
         "confirmed": bool | None, "denied": bool}
    """
    if config.VERBOSE:
        return

    header = Text()
    header.append("🧠 Agent → tool_calls", style="bold cyan")
    header.append(f"  {_fmt_ms(api_duration_ms)}  {_fmt_tokens(metrics)}", style="dim")

    lines = []
    for i, tc in enumerate(tool_calls_with_results, 1):
        circled = "①②③④⑤⑥⑦⑧⑨⑩"[i - 1] if i <= 10 else f"({i})"
        lines.append("")
        lines.append(f"  [bold]{circled}[/bold] [bold green]{escape(tc['name'])}[/bold green]({_fmt_args(tc['args'])})")

        if tc.get("denied"):
            lines.append("     [yellow]⚠️  denied by user[/yellow]")
        else:
            summary = _fmt_result_summary(tc["result"])
            timing = f"  [dim italic]{_fmt_ms(tc['duration_ms'])}[/dim italic]" if tc["duration_ms"] > 0 else ""
            lines.append(f"     [dim]→ {summary}[/dim]{timing}")
        lines.append("")

    panel = Panel(
        "\n".join(lines),
        title=f"[bold]Step {iteration}[/bold]",
        title_align="left",
        subtitle=header,
        subtitle_align="left",
        border_style="cyan",
        padding=(0, 1),
    )
    console.print(panel)


def render_response(text: str, api_duration_ms: float, metrics: dict) -> None:
    """Render the agent's final text response panel."""
    if config.VERBOSE:
        return

    header = Text()
    header.append("💬 Agent response", style="bold green")
    header.append(f"  {_fmt_ms(api_duration_ms)}  {_fmt_tokens(metrics)}", style="dim")

    body = Text(text)

    panel = Panel(
        body,
        title="[bold]Response[/bold]",
        title_align="left",
        subtitle=header,
        subtitle_align="left",
        border_style="green",
        padding=(0, 1),
    )
    console.print(panel)


def render_error(message: str) -> None:
    """Render an error panel. Always shown (errors matter in both modes)."""
    if config.VERBOSE:
        print(f"\n❌ {message}\n")
        return

    panel = Panel(
        Text(message, style="red"),
        title="[bold red]❌ Error[/bold red]",
        title_align="left",
        border_style="red",
        padding=(0, 1),
    )
    console.print(panel)


def render_confirmation(name: str, args: dict, approved: bool) -> None:
    """Render a confirmation result (shown after user responds)."""
    if config.VERBOSE:
        return

    status = "[green]✓ approved[/green]" if approved else "[yellow]✗ denied[/yellow]"
    console.print(f"  ⚠️  {name}({_fmt_args(args)}) — {status}")


def render_trajectory_summary(
    iterations: int,
    total_tokens: int,
    total_ms: float,
) -> None:
    """Render the trajectory footer summary after a turn completes."""
    if config.VERBOSE:
        return

    line = (
        f"[dim]─── Trajectory: {iterations} step{'s' if iterations != 1 else ''}"
        f" │ {total_tokens} tokens"
        f" │ {_fmt_ms(total_ms)} total " + "─" * 20 + "[/dim]"
    )
    console.print(line)
    console.print()
