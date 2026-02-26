"""세차기 코인 카운트 예제 프로그램.

INC, $MOV, 카운터(C), 타이머(T)를 모두 포함하는 예제.
LadderBuilder API로 수동 구축 → 컴파일 → CSV export.

디바이스 맵:
  X0: 코인센서    X1: 시작버튼    X2: 비상정지
  Y0: 물분사      Y1: 비누        Y2: 헹굼        Y3: 부저
  M0: 운전 릴레이  M1: 완료 릴레이
  C0: 코인카운터 (K3)
  T0: 물분사 (K100=10s)  T1: 비누 (K150=15s)  T2: 헹굼 (K100=10s)
  T10: 점멸ON (K5)       T11: 점멸OFF (K5)
  D0: 코인 누적 (INC)    D200: 상태표시 ($MOV)
"""

from __future__ import annotations

import os
import sys

from melsec_ladder_mcp.core.compiler import LadderCompiler
from melsec_ladder_mcp.core.instructions import InstructionValidator
from melsec_ladder_mcp.core.ladder import LadderBuilder, RungBuilder
from melsec_ladder_mcp.formats.csv_formatter import instructions_to_csv
from melsec_ladder_mcp.models.ladder import (
    ApplicationElement,
    CoilElement,
    ContactElement,
    ContactMode,
    ParallelBranch,
    Rung,
    SeriesConnection,
    TimerElement,
)


def build_coin_car_wash() -> LadderBuilder:
    """Build the coin car wash ladder program."""
    builder = LadderBuilder(name="MAIN")

    # Rung 0: 코인 투입 누적 (LD X0 / INC D0)
    builder.add_application_rung("X0", "INC", ["D0"], comment="코인 투입 누적")

    # Rung 1: 코인 3개 카운트 (LD X0 / OUT C0 K3)
    builder.add_counter_rung("X0", "C0", 3, comment="코인 3개 카운트")

    # Rung 2: 시작 자기유지
    # LD X1 / AND C0 / LD M0 / ORB / ANI X2 / ANI M1 / OUT M0
    parallel = ParallelBranch(branches=[
        SeriesConnection(elements=[
            ContactElement(device="X1", mode=ContactMode.NO),
            ContactElement(device="C0", mode=ContactMode.NO),
        ]),
        SeriesConnection(elements=[
            ContactElement(device="M0", mode=ContactMode.NO),
        ]),
    ])
    input_section = SeriesConnection(elements=[
        parallel,
        ContactElement(device="X2", mode=ContactMode.NC),
        ContactElement(device="M1", mode=ContactMode.NC),
    ])
    rung2 = Rung(
        number=2,
        comment="시작 자기유지",
        input_section=input_section,
        output_section=[CoilElement(device="M0")],
    )
    builder.add_rung(rung2)
    builder._rung_counter = 3

    # Rung 3~5: 순차 타이머 (chained)
    builder.add_timer_rung("M0", "T0", 100, comment="물분사 10초")
    builder.add_timer_rung("T0", "T1", 150, comment="비누 15초")
    builder.add_timer_rung("T1", "T2", 100, comment="헹굼 10초")

    # Rung 6~8: 스테이지 게이트 출력
    builder.add_stage_gated_rung("M0", "T0", "Y0", comment="물분사")
    builder.add_stage_gated_rung("T0", "T1", "Y1", comment="비누")
    builder.add_stage_gated_rung("T1", "T2", "Y2", comment="헹굼")

    # Rung 9: 완료 릴레이 (LD T2 / OUT M1)
    builder.add_output_rung("T2", "M1", comment="완료 릴레이")

    # Rung 10~12: 부저 점멸
    # Rung 10: LD M1 / ANI T11 / OUT T10 K5
    rung10 = Rung(
        number=builder._rung_counter,
        comment="점멸 ON 타이머",
        input_section=SeriesConnection(elements=[
            ContactElement(device="M1", mode=ContactMode.NO),
            ContactElement(device="T11", mode=ContactMode.NC),
        ]),
        output_section=[TimerElement(device="T10", k_value=5)],
    )
    builder.add_rung(rung10)
    builder._rung_counter += 1

    # Rung 11: LD T10 / OUT T11 K5
    builder.add_timer_rung("T10", "T11", 5, comment="점멸 OFF 타이머")

    # Rung 12: LD T10 / OUT Y3 (부저)
    builder.add_output_rung("T10", "Y3", comment="부저")

    # Rung 13~17: $MOV 상태 표시
    # Rung 13: LDI M0 / ANI M1 / $MOV "대기" D200
    rung13_input = SeriesConnection(elements=[
        ContactElement(device="M0", mode=ContactMode.NC),
        ContactElement(device="M1", mode=ContactMode.NC),
    ])
    rung13 = Rung(
        number=builder._rung_counter,
        comment='상태: 대기',
        input_section=rung13_input,
        output_section=[ApplicationElement(instruction="$MOV", operands=['"대기"', "D200"])],
    )
    builder.add_rung(rung13)
    builder._rung_counter += 1

    # Rung 14: LD M0 / ANI T0 / $MOV "물분사" D200
    rung14_input = SeriesConnection(elements=[
        ContactElement(device="M0", mode=ContactMode.NO),
        ContactElement(device="T0", mode=ContactMode.NC),
    ])
    rung14 = Rung(
        number=builder._rung_counter,
        comment='상태: 물분사',
        input_section=rung14_input,
        output_section=[ApplicationElement(instruction="$MOV", operands=['"물분사"', "D200"])],
    )
    builder.add_rung(rung14)
    builder._rung_counter += 1

    # Rung 15: LD T0 / ANI T1 / $MOV "비누" D200
    rung15_input = SeriesConnection(elements=[
        ContactElement(device="T0", mode=ContactMode.NO),
        ContactElement(device="T1", mode=ContactMode.NC),
    ])
    rung15 = Rung(
        number=builder._rung_counter,
        comment='상태: 비누',
        input_section=rung15_input,
        output_section=[ApplicationElement(instruction="$MOV", operands=['"비누"', "D200"])],
    )
    builder.add_rung(rung15)
    builder._rung_counter += 1

    # Rung 16: LD T1 / ANI T2 / $MOV "헹굼" D200
    rung16_input = SeriesConnection(elements=[
        ContactElement(device="T1", mode=ContactMode.NO),
        ContactElement(device="T2", mode=ContactMode.NC),
    ])
    rung16 = Rung(
        number=builder._rung_counter,
        comment='상태: 헹굼',
        input_section=rung16_input,
        output_section=[ApplicationElement(instruction="$MOV", operands=['"헹굼"', "D200"])],
    )
    builder.add_rung(rung16)
    builder._rung_counter += 1

    # Rung 17: LD M1 / $MOV "완료" D200
    rung17 = Rung(
        number=builder._rung_counter,
        comment='상태: 완료',
        input_section=SeriesConnection(elements=[
            ContactElement(device="M1", mode=ContactMode.NO),
        ]),
        output_section=[ApplicationElement(instruction="$MOV", operands=['"완료"', "D200"])],
    )
    builder.add_rung(rung17)
    builder._rung_counter += 1

    # Rung 18: 카운터 리셋 (LD M1 / RST C0)
    builder.add_counter_reset_rung("M1", "C0", comment="카운터 리셋")

    return builder


def get_expected_il() -> str:
    """Return the expected IL text for verification."""
    return "\n".join([
        "LD X0",
        "INC D0",
        "LD X0",
        "OUT C0 K3",
        "LD X1",
        "AND C0",
        "LD M0",
        "ORB",
        "ANI X2",
        "ANI M1",
        "OUT M0",
        "LD M0",
        "OUT T0 K100",
        "LD T0",
        "OUT T1 K150",
        "LD T1",
        "OUT T2 K100",
        "LD M0",
        "ANI T0",
        "OUT Y0",
        "LD T0",
        "ANI T1",
        "OUT Y1",
        "LD T1",
        "ANI T2",
        "OUT Y2",
        "LD T2",
        "OUT M1",
        "LD M1",
        "ANI T11",
        "OUT T10 K5",
        "LD T10",
        "OUT T11 K5",
        "LD T10",
        "OUT Y3",
        "LDI M0",
        "ANI M1",
        '$MOV "대기" D200',
        "LD M0",
        "ANI T0",
        '$MOV "물분사" D200',
        "LD T0",
        "ANI T1",
        '$MOV "비누" D200',
        "LD T1",
        "ANI T2",
        '$MOV "헹굼" D200',
        "LD M1",
        '$MOV "완료" D200',
        "LD M1",
        "RST C0",
        "END",
    ])


if __name__ == "__main__":
    builder = build_coin_car_wash()
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

    # Export CSV
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.join(out_dir, "coin_car_wash.csv")
    csv_bytes = instructions_to_csv(seq.instructions)
    with open(csv_path, "wb") as f:
        f.write(csv_bytes)
    print(f"\nCSV exported: {csv_path}")
