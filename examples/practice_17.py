"""실습 17 — 순차 점등, 역순 소등 프로그램.

LadderBuilder API로 수동 구축 → 컴파일 → CSV export.

동작:
  PB1 → RL ON 즉시 → 3초 후 GL ON → 2초 후 YL ON
  PB2 → YL OFF 즉시 → 2초 후 GL OFF → 3초 후 RL OFF

디바이스 맵:
  X1: PB1 (시작)     X2: PB2 (정지)
  Y20: RL (적색)     Y21: GL (녹색)     Y22: YL (황색)
  M0: 운전 릴레이     M1: 정지 시퀀스 릴레이
  T0: ON딜레이1 K30 (3초, M0→T0, GL ON 시점)
  T1: ON딜레이2 K20 (2초, T0→T1 체인, YL ON 시점)
  T2: OFF딜레이1 K20 (2초, M1→T2, GL OFF 시점)
  T3: OFF딜레이2 K30 (3초, T2→T3 체인, RL OFF 시점 + 전체 리셋)
"""

from __future__ import annotations

import os
import sys

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.core.ladder import LadderBuilder
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv
from melsec_ladder_mcp.models.ladder import (
    CoilElement,
    ContactElement,
    ContactMode,
    ParallelBranch,
    Rung,
    SeriesConnection,
    TimerElement,
)


def build_practice_17() -> LadderBuilder:
    """Build the practice 17 ladder program."""
    builder = LadderBuilder(name="MAIN")

    # Rung 0: 운전 자기유지 (M0)
    # LD X1 / OR M0 / ANI T3 / OUT M0
    parallel0 = ParallelBranch(branches=[
        SeriesConnection(elements=[
            ContactElement(device="X1", mode=ContactMode.NO),
        ]),
        SeriesConnection(elements=[
            ContactElement(device="M0", mode=ContactMode.NO),
        ]),
    ])
    rung0 = Rung(
        number=0,
        comment="운전 자기유지",
        input_section=SeriesConnection(elements=[
            parallel0,
            ContactElement(device="T3", mode=ContactMode.NC),
        ]),
        output_section=[CoilElement(device="M0")],
    )
    builder.add_rung(rung0)
    builder._rung_counter = 1

    # Rung 1: ON 딜레이 T0 (3초) — LD M0 / OUT T0 K30
    builder.add_timer_rung("M0", "T0", 30, comment="ON딜레이1 3초")

    # Rung 2: ON 딜레이 T1 (2초, T0에서 체인) — LD T0 / OUT T1 K20
    builder.add_timer_rung("T0", "T1", 20, comment="ON딜레이2 2초 체인")

    # Rung 3: 정지 시퀀스 (M1)
    # LD X2 / OR M1 / ANI T3 / OUT M1
    parallel1 = ParallelBranch(branches=[
        SeriesConnection(elements=[
            ContactElement(device="X2", mode=ContactMode.NO),
        ]),
        SeriesConnection(elements=[
            ContactElement(device="M1", mode=ContactMode.NO),
        ]),
    ])
    rung3 = Rung(
        number=3,
        comment="정지 시퀀스",
        input_section=SeriesConnection(elements=[
            parallel1,
            ContactElement(device="T3", mode=ContactMode.NC),
        ]),
        output_section=[CoilElement(device="M1")],
    )
    builder.add_rung(rung3)
    builder._rung_counter = 4

    # Rung 4: OFF 딜레이 T2 (2초) — LD M1 / OUT T2 K20
    builder.add_timer_rung("M1", "T2", 20, comment="OFF딜레이1 2초")

    # Rung 5: OFF 딜레이 T3 (3초, T2에서 체인) — LD T2 / OUT T3 K30
    builder.add_timer_rung("T2", "T3", 30, comment="OFF딜레이2 3초 체인")

    # Rung 6: RL 출력 — LD M0 / ANI T3 / OUT Y20
    builder.add_stage_gated_rung("M0", "T3", "Y20", comment="RL 적색")

    # Rung 7: GL 출력 — LD T0 / ANI T2 / OUT Y21
    builder.add_stage_gated_rung("T0", "T2", "Y21", comment="GL 녹색")

    # Rung 8: YL 출력 — LD T1 / ANI M1 / OUT Y22
    builder.add_stage_gated_rung("T1", "M1", "Y22", comment="YL 황색")

    return builder


def get_expected_il() -> str:
    """Return the expected IL text for verification."""
    return "\n".join([
        "LD X1",
        "OR M0",
        "ANI T3",
        "OUT M0",
        "LD M0",
        "OUT T0 K30",
        "LD T0",
        "OUT T1 K20",
        "LD X2",
        "OR M1",
        "ANI T3",
        "OUT M1",
        "LD M1",
        "OUT T2 K20",
        "LD T2",
        "OUT T3 K30",
        "LD M0",
        "ANI T3",
        "OUT Y20",
        "LD T0",
        "ANI T2",
        "OUT Y21",
        "LD T1",
        "ANI M1",
        "OUT Y22",
        "END",
    ])


if __name__ == "__main__":
    builder = build_practice_17()
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
        sys.exit(1)

    # Export CSV
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "practice_17.csv")
    csv_bytes = instructions_to_csv(seq.instructions)
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)
    print(f"\nCSV exported: {csv_path}")
