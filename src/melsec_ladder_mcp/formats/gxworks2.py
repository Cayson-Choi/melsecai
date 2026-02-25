"""GX Works2 export formatter."""

from __future__ import annotations

import csv
import io

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.errors import ExportError
from melsec_ladder_mcp.models.devices import DeviceMap
from melsec_ladder_mcp.models.export import ExportOptions, ExportResult
from melsec_ladder_mcp.models.instructions import InstructionSequence
from melsec_ladder_mcp.models.ladder import LadderProgram


class GXWorks2Formatter:
    """Formats ladder programs for GX Works2 text import."""

    def __init__(self) -> None:
        self._compiler = LadderCompiler()
        self._validator = InstructionValidator()

    def format(
        self,
        program: LadderProgram,
        options: ExportOptions | None = None,
    ) -> ExportResult:
        """Format a ladder program for GX Works2 import."""
        if options is None:
            options = ExportOptions()

        # Compile to IL
        sequence = self._compiler.compile(program)

        # Validate
        errors = self._validator.validate(sequence)
        warnings: list[str] = []
        for error in errors:
            warnings.append(f"Validation: {error}")

        # Format program text
        program_text = self._format_program_text(sequence, options)

        # Format device comments
        comments_csv = self._format_device_comments(program.device_map)

        return ExportResult(
            program_text=program_text,
            device_comments_csv=comments_csv,
            warnings=warnings,
            instruction_count=len(sequence.instructions),
            rung_count=len(program.rungs),
        )

    def _format_program_text(
        self, sequence: InstructionSequence, options: ExportOptions
    ) -> str:
        """Format IL instructions as GX Works2 text."""
        lines: list[str] = []
        for inst in sequence.instructions:
            lines.append(inst.to_text())
        return "\n".join(lines)

    def _format_device_comments(self, device_map: DeviceMap) -> str:
        """Format device comments as CSV."""
        if not device_map.allocations:
            return ""

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Device", "Comment"])

        for alloc in device_map.allocations:
            addr_str = alloc.address.to_string()
            comment = alloc.comment or alloc.logical_name
            if alloc.timer_config and alloc.timer_config.comment:
                comment = f"{comment} ({alloc.timer_config.comment})"
            writer.writerow([addr_str, comment])

        return output.getvalue()
