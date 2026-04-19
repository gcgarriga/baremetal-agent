"""Live trajectory visualization using rich."""

from typing import Any, TypedDict

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.text import Text

from baremetal_agent import config

console = Console(highlight=False)


class ToolCallResult(TypedDict):
    name: str
    args: dict[str, Any]
    result: str
    duration_ms: float
    denied: bool


def _fmt_args(args: dict[str, Any]) -> str:
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 60:
            v = v[:57] + "..."
        parts.append(f'{k}="{escape(str(v))}"' if isinstance(v, str) else f"{k}={v}")
    return ", ".join(parts)


def _fmt_result_summary(result: str) -> str:
    lines = result.splitlines()
    preview_lines = [escape(line) for line in lines[:3]]
    indented = "\n     ".join(preview_lines)
    if len(lines) > 3:
        indented += f"\n     ... ({len(lines) - 3} more lines)"
    return indented


def _fmt_ms(ms: float) -> str:
    if ms >= 1000:
        return f"{ms / 1000:.1f}s"
    return f"{int(ms)}ms"


def _fmt_tokens(metrics: dict[str, Any]) -> str:
    prompt = metrics.get("prompt_tokens", 0)
    completion = metrics.get("completion_tokens", 0)
    return f"{prompt + completion} tok"


def render_tool_call_step(
    iteration: int,
    tool_calls_with_results: list[ToolCallResult],
    api_duration_ms: float,
    metrics: dict[str, Any],
) -> None:
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


def render_response(text: str, api_duration_ms: float, metrics: dict[str, Any]) -> None:
    if config.VERBOSE:
        return

    header = Text()
    header.append("💬 Agent response", style="bold green")
    header.append(f"  {_fmt_ms(api_duration_ms)}  {_fmt_tokens(metrics)}", style="dim")

    panel = Panel(
        Text(text),
        title="[bold]Response[/bold]",
        title_align="left",
        subtitle=header,
        subtitle_align="left",
        border_style="green",
        padding=(0, 1),
    )
    console.print(panel)


def render_error(message: str) -> None:
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


def render_confirmation(name: str, args: dict[str, Any], approved: bool) -> None:
    if config.VERBOSE:
        return

    status = "[green]✓ approved[/green]" if approved else "[yellow]✗ denied[/yellow]"
    console.print(f"  ⚠️  {name}({_fmt_args(args)}) — {status}")


def render_trajectory_summary(iterations: int, total_tokens: int, total_ms: float) -> None:
    if config.VERBOSE:
        return

    line = (
        f"[dim]─── Trajectory: {iterations} step{'s' if iterations != 1 else ''}"
        f" │ {total_tokens} tokens"
        f" │ {_fmt_ms(total_ms)} total " + "─" * 20 + "[/dim]"
    )
    console.print(line)
    console.print()
