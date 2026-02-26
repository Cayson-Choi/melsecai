"""실습 15 — 순환(시프트) 점등 프로그램.

LadderBuilder API로 수동 구축 → 컴파일 → CSV export.

동작:
  PB1(X1) → RL ON → 5초 후 GL ON, RL OFF → 5초 후 BZ ON, GL OFF
  PB2(X2) → 전체 정지

디바이스 맵:
  X1: PB1 (시작)     X2: PB2 (정지)
  Y20: RL (적색)     Y21: GL (녹색)     Y22: BZ (부저)
  M0: 운전 릴레이
  T0: 체인타이머1 K50 (5초, M0→T0)
  T1: 체인타이머2 K50 (5초, T0→T1)
"""

from __future__ import annotations

import os
import sys

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv


def build_practice_15() -> LadderBuilder:
    """Build the practice 15 ladder program."""
    builder = LadderBuilder(name="MAIN")

    # Rung 0: 자기유지 (M0) — LD X1 / OR M0 / ANI X2 / OUT M0
    builder.add_self_hold_rung("X1", "X2", "M0", comment="운전 자기유지")

    # Rung 1: 체인타이머 T0 (5초) — LD M0 / OUT T0 K50
    builder.add_timer_rung("M0", "T0", 50, comment="체인타이머1 5초")

    # Rung 2: 체인타이머 T1 (5초, T0→T1) — LD T0 / OUT T1 K50
    builder.add_timer_rung("T0", "T1", 50, comment="체인타이머2 5초")

    # Rung 3: RL 출력 — LD M0 / ANI T0 / OUT Y20
    builder.add_stage_gated_rung("M0", "T0", "Y20", comment="RL 적색")

    # Rung 4: GL 출력 — LD T0 / ANI T1 / OUT Y21
    builder.add_stage_gated_rung("T0", "T1", "Y21", comment="GL 녹색")

    # Rung 5: BZ 출력 — LD T1 / OUT Y22
    builder.add_output_rung("T1", "Y22", comment="BZ 부저")

    return builder


def get_expected_il() -> str:
    """Return the expected IL text for verification."""
    return "\n".join([
        "LD X1",
        "OR M0",
        "ANI X2",
        "OUT M0",
        "LD M0",
        "OUT T0 K50",
        "LD T0",
        "OUT T1 K50",
        "LD M0",
        "ANI T0",
        "OUT Y20",
        "LD T0",
        "ANI T1",
        "OUT Y21",
        "LD T1",
        "OUT Y22",
        "END",
    ])


if __name__ == "__main__":
    builder = build_practice_15()
    program = builder.build()

    # Compile
    compiler = LadderCompiler()
    seq = compiler.compile(program)

    # Validate
    validator = InstructionValidator()
    errors = validator.validate(seq)
    if errors:
        print("Validation errors:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)

    # Print IL
    il_text = seq.to_text()
    print("=== IL Program ===")
    print(il_text)
    print(f"\n=== {len(program.rungs)} rungs, {len(seq.instructions)} instructions ===")

    # Verify
    expected = get_expected_il()
    if il_text == expected:
        print("\nIL verification: PASS")
    else:
        print("\nIL verification: FAIL")
        print("Expected:")
        print(expected)
        print("\nActual:")
        print(il_text)
        sys.exit(1)

    # Export CSV
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "practice_15.csv")
    csv_bytes = instructions_to_csv(seq.instructions)
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)
    print(f"\nCSV exported: {csv_path}")
