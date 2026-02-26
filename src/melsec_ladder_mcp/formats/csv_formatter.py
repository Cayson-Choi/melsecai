"""GX Works2 CSV format generator.

Generates CSV files compatible with GX Works2's
Edit > Read from CSV File / Write to CSV File feature.

Format: UTF-16 LE with BOM, tab-delimited, quoted fields.
"""

from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from melsec_ladder_mcp.models.instructions import Instruction, InstructionSequence


# Step size per instruction type (how many steps each instruction occupies)
# Timer/Counter OUT takes 4 steps, most others take 1
_STEP_SIZES = {
    "LD": 1, "LDI": 1, "AND": 1, "ANI": 1,
    "OR": 1, "ORI": 1, "ORB": 1, "ANB": 1,
    "MPS": 1, "MRD": 1, "MPP": 1,
    "SET": 1, "RST": 1, "END": 2,
}

_TIMER_COUNTER_PREFIXES = ("T", "C")


def _is_timer_or_counter_out(inst: Instruction) -> bool:
    """Check if instruction is OUT T* or OUT C* (timer/counter output)."""
    if inst.instruction.value != "OUT":
        return False
    return inst.device is not None and inst.device[0] in _TIMER_COUNTER_PREFIXES


def _step_size(inst: Instruction) -> int:
    """Return the number of steps an instruction occupies."""
    if _is_timer_or_counter_out(inst):
        return 4  # OUT T0 K50 = 4 steps
    return _STEP_SIZES.get(inst.instruction.value, 1)


def instructions_to_csv(
    instructions: list[Instruction],
    program_name: str = "MAIN",
    cpu_type: str = "QCPU (Q mode) Q03UDV",
) -> bytes:
    """Convert IL instructions to GX Works2 CSV format bytes (UTF-16 LE BOM).

    Args:
        instructions: List of IL instructions.
        program_name: Program name for the CSV header.
        cpu_type: PLC type string for the CSV header.

    Returns:
        UTF-16 LE encoded bytes with BOM, ready to write to a .csv file.
    """
    lines: list[str] = []

    # Header
    lines.append(f'"{program_name}"')
    lines.append(f'"PLC Information:"\t"{cpu_type}"')
    lines.append(
        '"Step No."\t"Line Statement"\t"Instruction"\t'
        '"I/O(Device)"\t"Blank"\t"PI Statement"\t"Note"'
    )

    # Instructions
    step = 0
    for inst in instructions:
        mnemonic = inst.instruction.value
        device = inst.device or ""

        if _is_timer_or_counter_out(inst):
            # Timer/Counter OUT: two CSV rows
            # Row 1: step, "", "OUT", "T0", "", "", ""
            lines.append(
                f'"{step}"\t""\t"OUT"\t"{device}"\t""\t""\t""'
            )
            # Row 2: "", "", "", "K50", "", "", ""
            k_val = f"K{inst.k_value}" if inst.k_value is not None else ""
            lines.append(
                f'""\t""\t""\t"{k_val}"\t""\t""\t""'
            )
        elif mnemonic in ("ORB", "ANB", "MPS", "MRD", "MPP"):
            # Stack ops: no device
            lines.append(
                f'"{step}"\t""\t"{mnemonic}"\t""\t""\t""\t""'
            )
        elif mnemonic == "END":
            lines.append(
                f'"{step}"\t""\t"END"\t""\t""\t""\t""'
            )
        else:
            # Normal instruction: LD, LDI, AND, ANI, OR, ORI, OUT, SET, RST
            lines.append(
                f'"{step}"\t""\t"{mnemonic}"\t"{device}"\t""\t""\t""'
            )

        step += _step_size(inst)

    text = "\r\n".join(lines) + "\r\n"

    # Encode as UTF-16 LE with BOM
    bom = b"\xff\xfe"
    encoded = text.encode("utf-16-le")
    return bom + encoded


def sequence_to_csv(
    sequence: InstructionSequence,
    program_name: str = "MAIN",
    cpu_type: str = "QCPU (Q mode) Q03UDV",
) -> bytes:
    """Convert an InstructionSequence to GX Works2 CSV bytes."""
    return instructions_to_csv(
        sequence.instructions,
        program_name=program_name,
        cpu_type=cpu_type,
    )
