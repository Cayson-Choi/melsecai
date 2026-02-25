"""render_ladder_diagram tool implementation."""

from __future__ import annotations

from melsec_ladder_mcp.models.ladder import (
    ContactElement,
    ContactMode,
    CoilElement,
    CounterElement,
    LadderProgram,
    ParallelBranch,
    Rung,
    SeriesConnection,
    TimerElement,
    SetResetElement,
)
from melsec_ladder_mcp.models.rendering import RenderFormat, RenderOptions, RenderResult


def render_ladder_diagram(
    ladder: dict,
    format: str = "text",
    show_comments: bool = True,
) -> dict:
    """Render a ladder program as a visual diagram.

    Args:
        ladder: 래더 프로그램 JSON
        format: 출력 형식 (text/svg)
        show_comments: 코멘트 표시 여부

    Returns:
        렌더링 결과
    """
    program = LadderProgram(**ladder)
    options = RenderOptions(
        format=RenderFormat(format),
        show_comments=show_comments,
    )

    if options.format == RenderFormat.TEXT:
        content = _render_text(program, options)
    else:
        content = _render_svg(program, options)

    return RenderResult(
        content=content,
        format=options.format,
        rung_count=len(program.rungs),
    ).model_dump()


def _render_text(program: LadderProgram, options: RenderOptions) -> str:
    """Render as ASCII text ladder diagram."""
    lines: list[str] = []

    for rung in program.rungs:
        if options.show_comments and rung.comment:
            lines.append(f"// Rung {rung.number}: {rung.comment}")

        # Render input section
        input_str = _render_input_text(rung.input_section)

        # Render output section
        for output in rung.output_section:
            output_str = _render_output_text(output)
            lines.append(f"|--{input_str}--{output_str}--|")

        lines.append("|" + " " * 40 + "|")

    lines.append("|" + "=" * 40 + "| END")
    return "\n".join(lines)


def _render_input_text(section) -> str:
    """Render input section as text."""
    if isinstance(section, SeriesConnection):
        parts = []
        for elem in section.elements:
            if isinstance(elem, ContactElement):
                if elem.mode == ContactMode.NC:
                    parts.append(f"[/{elem.device}]")
                else:
                    parts.append(f"[ {elem.device}]")
            elif isinstance(elem, ParallelBranch):
                branch_strs = []
                for branch in elem.branches:
                    branch_strs.append(_render_input_text(branch))
                parts.append("(" + " | ".join(branch_strs) + ")")
        return "--".join(parts) if parts else "---"

    elif isinstance(section, ParallelBranch):
        branch_strs = []
        for branch in section.branches:
            branch_strs.append(_render_input_text(branch))
        return "(" + " | ".join(branch_strs) + ")"

    return "---"


def _render_output_text(output) -> str:
    """Render output element as text."""
    if isinstance(output, CoilElement):
        return f"({output.device})"
    elif isinstance(output, TimerElement):
        return f"[T {output.device} K{output.k_value}]"
    elif isinstance(output, CounterElement):
        return f"[C {output.device} K{output.k_value}]"
    elif isinstance(output, SetResetElement):
        op = "SET" if output.type == "set" else "RST"
        return f"({op} {output.device})"
    return "(???)"


def _render_svg(program: LadderProgram, options: RenderOptions) -> str:
    """Render as SVG ladder diagram."""
    rung_height = 60
    width = 800
    total_height = len(program.rungs) * rung_height + 40

    svg_parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_height}">',
        '<style>',
        '  text { font-family: monospace; font-size: 12px; }',
        '  .contact { stroke: #333; fill: none; stroke-width: 2; }',
        '  .coil { stroke: #333; fill: none; stroke-width: 2; }',
        '  .wire { stroke: #333; stroke-width: 2; }',
        '  .comment { fill: #666; font-size: 10px; }',
        '</style>',
    ]

    y_offset = 20
    for rung in program.rungs:
        y = y_offset + rung.number * rung_height

        # Left rail
        svg_parts.append(f'<line x1="20" y1="{y}" x2="20" y2="{y + 40}" class="wire"/>')

        # Comment
        if options.show_comments and rung.comment:
            svg_parts.append(
                f'<text x="30" y="{y - 5}" class="comment">'
                f'// {rung.comment}</text>'
            )

        # Horizontal wire
        svg_parts.append(
            f'<line x1="20" y1="{y + 20}" x2="{width - 20}" '
            f'y2="{y + 20}" class="wire"/>'
        )

        # Right rail
        svg_parts.append(
            f'<line x1="{width - 20}" y1="{y}" '
            f'x2="{width - 20}" y2="{y + 40}" class="wire"/>'
        )

        # Render elements (simplified)
        x = 50
        if isinstance(rung.input_section, SeriesConnection):
            for elem in rung.input_section.elements:
                if isinstance(elem, ContactElement):
                    if elem.mode == ContactMode.NC:
                        svg_parts.append(
                            f'<text x="{x}" y="{y + 15}">{elem.device}</text>'
                        )
                        svg_parts.append(
                            f'<line x1="{x}" y1="{y + 18}" '
                            f'x2="{x + 40}" y2="{y + 22}" class="contact"/>'
                        )
                        svg_parts.append(
                            f'<line x1="{x}" y1="{y + 22}" '
                            f'x2="{x + 40}" y2="{y + 18}" class="contact"/>'
                        )
                    else:
                        svg_parts.append(
                            f'<text x="{x}" y="{y + 15}">{elem.device}</text>'
                        )
                    x += 80

        # Output
        for output in rung.output_section:
            ox = width - 120
            if isinstance(output, CoilElement):
                svg_parts.append(
                    f'<circle cx="{ox + 20}" cy="{y + 20}" r="12" class="coil"/>'
                )
                svg_parts.append(
                    f'<text x="{ox + 10}" y="{y + 24}">{output.device}</text>'
                )
            elif isinstance(output, TimerElement):
                svg_parts.append(
                    f'<rect x="{ox}" y="{y + 8}" width="60" height="24" class="coil"/>'
                )
                svg_parts.append(
                    f'<text x="{ox + 5}" y="{y + 24}">'
                    f'{output.device} K{output.k_value}</text>'
                )

    svg_parts.append('</svg>')
    return "\n".join(svg_parts)
