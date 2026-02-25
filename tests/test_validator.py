"""Tests for InstructionValidator."""

import pytest

from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.models.instructions import (
    Instruction,
    InstructionSequence,
    InstructionType,
)


@pytest.fixture
def validator():
    return InstructionValidator()


class TestEndCheck:
    def test_valid_end(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert not errors

    def test_missing_end(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
        ])
        errors = validator.validate(seq)
        assert any("END" in e for e in errors)

    def test_end_in_middle(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="X0"),
            Instruction(instruction=InstructionType.END),
            Instruction(instruction=InstructionType.LD, device="X1"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("not at end" in e for e in errors)


class TestStackBalance:
    def test_balanced_mps_mpp(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MPS),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
            Instruction(instruction=InstructionType.MPP),
            Instruction(instruction=InstructionType.OUT, device="Y1"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert not errors

    def test_unbalanced_mps(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MPS),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("imbalance" in e for e in errors)

    def test_unbalanced_mpp(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.MPP),
            Instruction(instruction=InstructionType.OUT, device="Y0"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("without matching MPS" in e for e in errors)


class TestDeviceOperands:
    def test_ld_without_device(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("requires a device" in e for e in errors)

    def test_timer_without_k(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.OUT, device="T0"),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert any("K value" in e for e in errors)

    def test_timer_with_k(self, validator):
        seq = InstructionSequence(instructions=[
            Instruction(instruction=InstructionType.LD, device="M0"),
            Instruction(instruction=InstructionType.OUT, device="T0", k_value=50),
            Instruction(instruction=InstructionType.END),
        ])
        errors = validator.validate(seq)
        assert not errors
