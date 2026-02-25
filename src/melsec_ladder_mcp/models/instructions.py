"""IL (Instruction List) models for MELSEC-Q."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class InstructionType(str, Enum):
    LD = "LD"
    LDI = "LDI"
    AND = "AND"
    ANI = "ANI"
    OR = "OR"
    ORI = "ORI"
    OUT = "OUT"
    SET = "SET"
    RST = "RST"
    ORB = "ORB"
    ANB = "ANB"
    MPS = "MPS"
    MRD = "MRD"
    MPP = "MPP"
    END = "END"


class Instruction(BaseModel):
    """A single IL instruction."""

    instruction: InstructionType
    device: str | None = Field(default=None, description="디바이스 (예: X0, M0, T0)")
    k_value: int | None = Field(default=None, description="K값 (타이머/카운터)")

    def to_text(self) -> str:
        """Convert to GX Works2 text format."""
        parts = [self.instruction.value]
        if self.device is not None:
            parts.append(self.device)
        if self.k_value is not None:
            parts.append(f"K{self.k_value}")
        return " ".join(parts)


class InstructionSequence(BaseModel):
    """A sequence of IL instructions forming a complete program."""

    instructions: list[Instruction] = Field(default_factory=list)

    def to_text(self) -> str:
        """Convert entire sequence to GX Works2 text format."""
        return "\n".join(inst.to_text() for inst in self.instructions)

    def append(self, instruction: Instruction) -> None:
        self.instructions.append(instruction)

    def extend(self, instructions: list[Instruction]) -> None:
        self.instructions.extend(instructions)
