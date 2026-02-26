"""Ladder IR to IL instruction compiler."""

from __future__ import annotations

from melsec_ladder_mcp.errors import CompilerError
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)
from melsec_ladder_mcp.models.ladder import (
    ApplicationElement,
    CoilElement,
    ContactElement,
    ContactMode,
    CounterElement,
    LadderProgram,
    ParallelBranch,
    Rung,
    SeriesConnection,
    SetResetElement,
    TimerElement,
)


class LadderCompiler:
    """Compiles Ladder IR (Rung-based) to IL instruction sequence."""

    def compile(self, program: LadderProgram) -> InstructionSequence:
        """Compile a complete ladder program to IL."""
        seq = InstructionSequence()
        for rung in program.rungs:
            instructions = self._compile_rung(rung)
            seq.extend(instructions)
        seq.append(Instruction(instruction=InstructionType.END))
        return seq

    def _compile_rung(self, rung: Rung) -> list[Instruction]:
        """Compile a single rung to IL instructions."""
        instructions: list[Instruction] = []

        # Compile input section
        input_instrs = self._compile_input_section(rung.input_section)
        instructions.extend(input_instrs)

        # Compile output section
        output_count = len(rung.output_section)
        if output_count == 0:
            raise CompilerError(f"Rung {rung.number} has no output elements")

        if output_count == 1:
            instructions.extend(self._compile_output(rung.output_section[0]))
        else:
            # Multiple outputs: use MPS/MRD/MPP stack
            for i, output in enumerate(rung.output_section):
                if i == 0:
                    instructions.append(Instruction(instruction=InstructionType.MPS))
                elif i < output_count - 1:
                    instructions.append(Instruction(instruction=InstructionType.MRD))
                else:
                    instructions.append(Instruction(instruction=InstructionType.MPP))
                instructions.extend(self._compile_output(output))

        return instructions

    def _compile_input_section(
        self, section: SeriesConnection | ParallelBranch
    ) -> list[Instruction]:
        """Compile the input section of a rung."""
        if isinstance(section, SeriesConnection):
            return self._compile_series(section, is_first=True)
        elif isinstance(section, ParallelBranch):
            return self._compile_parallel(section)
        else:
            raise CompilerError(f"Unknown input section type: {type(section)}")

    def _compile_series(
        self, series: SeriesConnection, is_first: bool = False
    ) -> list[Instruction]:
        """Compile a series connection (AND logic)."""
        instructions: list[Instruction] = []

        for i, elem in enumerate(series.elements):
            if isinstance(elem, ContactElement):
                if i == 0 and is_first:
                    # First element in the rung: use LD/LDI
                    if elem.mode == ContactMode.NC:
                        instructions.append(
                            Instruction(instruction=InstructionType.LDI, device=elem.device)
                        )
                    else:
                        instructions.append(
                            Instruction(instruction=InstructionType.LD, device=elem.device)
                        )
                elif i == 0 and not is_first:
                    # First element of a branch: use LD/LDI
                    if elem.mode == ContactMode.NC:
                        instructions.append(
                            Instruction(instruction=InstructionType.LDI, device=elem.device)
                        )
                    else:
                        instructions.append(
                            Instruction(instruction=InstructionType.LD, device=elem.device)
                        )
                else:
                    # Subsequent elements: use AND/ANI
                    if elem.mode == ContactMode.NC:
                        instructions.append(
                            Instruction(instruction=InstructionType.ANI, device=elem.device)
                        )
                    else:
                        instructions.append(
                            Instruction(instruction=InstructionType.AND, device=elem.device)
                        )
            elif isinstance(elem, ParallelBranch):
                # Nested parallel branch within series
                if i == 0 and is_first:
                    instructions.extend(self._compile_parallel(elem))
                else:
                    instructions.extend(self._compile_parallel(elem))
                    instructions.append(Instruction(instruction=InstructionType.ANB))

        return instructions

    def _compile_parallel(self, parallel: ParallelBranch) -> list[Instruction]:
        """Compile a parallel branch (OR logic).

        For simple parallels (each branch is a single contact), use OR/ORI.
        For complex parallels, use LD+ORB block approach.
        """
        # Check if all branches are simple single contacts
        all_simple = all(
            len(branch.elements) == 1 and isinstance(branch.elements[0], ContactElement)
            for branch in parallel.branches
        )

        if all_simple:
            instructions: list[Instruction] = []
            for i, branch in enumerate(parallel.branches):
                contact = branch.elements[0]
                assert isinstance(contact, ContactElement)
                if i == 0:
                    if contact.mode == ContactMode.NC:
                        instructions.append(
                            Instruction(instruction=InstructionType.LDI, device=contact.device)
                        )
                    else:
                        instructions.append(
                            Instruction(instruction=InstructionType.LD, device=contact.device)
                        )
                else:
                    if contact.mode == ContactMode.NC:
                        instructions.append(
                            Instruction(instruction=InstructionType.ORI, device=contact.device)
                        )
                    else:
                        instructions.append(
                            Instruction(instruction=InstructionType.OR, device=contact.device)
                        )
            return instructions

        # Complex parallel: use LD+ORB block approach
        instructions = []
        for i, branch in enumerate(parallel.branches):
            branch_instrs = self._compile_series(branch, is_first=True)
            instructions.extend(branch_instrs)
            if i > 0:
                instructions.append(Instruction(instruction=InstructionType.ORB))

        return instructions

    def _compile_output(
        self,
        output: CoilElement | TimerElement | CounterElement | SetResetElement | ApplicationElement,
    ) -> list[Instruction]:
        """Compile an output element."""
        if isinstance(output, CoilElement):
            return [Instruction(instruction=InstructionType.OUT, device=output.device)]
        elif isinstance(output, TimerElement):
            return [
                Instruction(
                    instruction=InstructionType.OUT,
                    device=output.device,
                    k_value=output.k_value,
                )
            ]
        elif isinstance(output, CounterElement):
            return [
                Instruction(
                    instruction=InstructionType.OUT,
                    device=output.device,
                    k_value=output.k_value,
                )
            ]
        elif isinstance(output, SetResetElement):
            if output.type == "set":
                return [Instruction(instruction=InstructionType.SET, device=output.device)]
            else:
                return [Instruction(instruction=InstructionType.RST, device=output.device)]
        elif isinstance(output, ApplicationElement):
            return [
                Instruction(
                    instruction=InstructionType(output.instruction),
                    operands=output.operands,
                )
            ]
        else:
            raise CompilerError(f"Unknown output element type: {type(output)}")
