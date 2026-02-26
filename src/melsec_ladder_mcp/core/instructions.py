"""IL instruction validator."""

from __future__ import annotations

from melsec_ladder_mcp.errors import StackImbalanceError, ValidationError
from melsec_ladder_mcp.models.devices import DeviceAddress, DeviceType, OCTAL_DEVICES
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)

# Instructions that require a device operand
DEVICE_INSTRUCTIONS = {
    InstructionType.LD,
    InstructionType.LDI,
    InstructionType.AND,
    InstructionType.ANI,
    InstructionType.OR,
    InstructionType.ORI,
    InstructionType.OUT,
    InstructionType.SET,
    InstructionType.RST,
}

# Instructions that take no operands
NO_OPERAND_INSTRUCTIONS = {
    InstructionType.ORB,
    InstructionType.ANB,
    InstructionType.MPS,
    InstructionType.MRD,
    InstructionType.MPP,
    InstructionType.END,
}

# Application instructions (use operands field instead of device)
APPLICATION_INSTRUCTIONS = {
    InstructionType.MOV,
    InstructionType.DMOV,
    InstructionType.ADD,
    InstructionType.SUB,
    InstructionType.MUL,
    InstructionType.DIV,
    InstructionType.INC,
    InstructionType.DEC,
    InstructionType.CMP,
    InstructionType.BCD,
    InstructionType.BIN_INST,
    InstructionType.SMOV,
}

# Expected operand count per application instruction
_APP_OPERAND_COUNTS: dict[InstructionType, int] = {
    InstructionType.MOV: 2,
    InstructionType.DMOV: 2,
    InstructionType.BCD: 2,
    InstructionType.BIN_INST: 2,
    InstructionType.ADD: 3,
    InstructionType.SUB: 3,
    InstructionType.MUL: 3,
    InstructionType.DIV: 3,
    InstructionType.CMP: 3,
    InstructionType.INC: 1,
    InstructionType.DEC: 1,
    InstructionType.SMOV: 2,
}

# Valid device types for contact instructions
CONTACT_DEVICES = {DeviceType.X, DeviceType.Y, DeviceType.M, DeviceType.T, DeviceType.C}

# Valid device types for output instructions
OUTPUT_DEVICES = {DeviceType.Y, DeviceType.M, DeviceType.T, DeviceType.C}


class InstructionValidator:
    """Validates IL instruction sequences."""

    def validate(self, sequence: InstructionSequence) -> list[str]:
        """Validate an instruction sequence. Returns list of error messages."""
        errors: list[str] = []
        errors.extend(self._check_end(sequence))
        errors.extend(self._check_stack_balance(sequence))
        errors.extend(self._check_device_operands(sequence))
        return errors

    def _check_end(self, sequence: InstructionSequence) -> list[str]:
        """Check that the sequence ends with END."""
        errors: list[str] = []
        if not sequence.instructions:
            errors.append("Empty instruction sequence")
            return errors

        last = sequence.instructions[-1]
        if last.instruction != InstructionType.END:
            errors.append("Program must end with END instruction")

        # Check no END in middle
        for i, inst in enumerate(sequence.instructions[:-1]):
            if inst.instruction == InstructionType.END:
                errors.append(f"END instruction found at position {i} (not at end)")

        return errors

    def _check_stack_balance(self, sequence: InstructionSequence) -> list[str]:
        """Check MPS/MRD/MPP stack balance."""
        errors: list[str] = []
        stack_depth = 0

        for i, inst in enumerate(sequence.instructions):
            if inst.instruction == InstructionType.MPS:
                stack_depth += 1
            elif inst.instruction == InstructionType.MPP:
                stack_depth -= 1
                if stack_depth < 0:
                    errors.append(f"MPP at position {i} without matching MPS")
                    stack_depth = 0

        if stack_depth != 0:
            errors.append(
                f"MPS/MPP stack imbalance: {stack_depth} unmatched MPS"
            )

        return errors

    def _check_device_operands(self, sequence: InstructionSequence) -> list[str]:
        """Check device operand validity."""
        errors: list[str] = []

        for i, inst in enumerate(sequence.instructions):
            if inst.instruction in APPLICATION_INSTRUCTIONS:
                # Application instructions use operands field
                if not inst.operands:
                    errors.append(
                        f"{inst.instruction.value} at position {i} requires operands"
                    )
                    continue
                expected = _APP_OPERAND_COUNTS.get(inst.instruction)
                if expected is not None and len(inst.operands) != expected:
                    errors.append(
                        f"{inst.instruction.value} at position {i} requires "
                        f"{expected} operands, got {len(inst.operands)}"
                    )

            elif inst.instruction in DEVICE_INSTRUCTIONS:
                if inst.device is None:
                    errors.append(
                        f"{inst.instruction.value} at position {i} requires a device"
                    )
                    continue

                # Validate device string format
                try:
                    addr = DeviceAddress.from_string(inst.device)
                except ValueError as e:
                    errors.append(f"Invalid device at position {i}: {e}")
                    continue

                # Check timer/counter K value
                if addr.device_type in (DeviceType.T, DeviceType.C):
                    if inst.instruction == InstructionType.OUT and inst.k_value is None:
                        errors.append(
                            f"OUT {inst.device} at position {i} requires K value"
                        )

            elif inst.instruction in NO_OPERAND_INSTRUCTIONS:
                if inst.device is not None:
                    errors.append(
                        f"{inst.instruction.value} at position {i} should not have a device"
                    )

        return errors
