"""FastMCP server entry point for MELSEC Ladder Generator."""

from __future__ import annotations

import json

from fastmcp import FastMCP

from melsec_ladder_mcp.tools.analyzer import analyze_timing_diagram as _analyze
from melsec_ladder_mcp.tools.generator import generate_ladder as _generate
from melsec_ladder_mcp.tools.exporter import export_gxworks2 as _export
from melsec_ladder_mcp.tools.importer import import_to_gxworks2 as _import
from melsec_ladder_mcp.tools.renderer import render_ladder_diagram as _render

mcp = FastMCP(
    name="melsec-ladder-mcp",
    instructions="타이밍도 기반 MELSEC-Q 래더 프로그램 자동 생성 + GX Works2 자동 Import",
)


# ── Tools ────────────────────────────────────────────────────────────────


@mcp.tool()
def analyze_timing_diagram(
    description: str,
    inputs: list[dict],
    outputs: list[dict],
    sequences: list[dict],
) -> dict:
    """동작 조건을 구조화된 래더 생성용 JSON으로 변환합니다.

    Args:
        description: 타이밍도 동작 설명 텍스트
        inputs: 입력 디바이스 목록 [{"name": "PB1", "type": "push_button", "mode": "momentary"}]
        outputs: 출력 디바이스 목록 [{"name": "RL", "type": "lamp"}]
        sequences: 시퀀스 목록 [{"trigger": "PB1", "action": "RL ON", "delay": null}]

    Returns:
        구조화된 타이밍 분석 결과 (detected_patterns, has_self_hold, has_timer, ...)
    """
    return _analyze(description, inputs, outputs, sequences)


@mcp.tool()
def generate_ladder(
    description: str,
    inputs: list[dict],
    outputs: list[dict],
    sequences: list[dict],
    device_start: dict | None = None,
) -> dict:
    """구조화된 동작 조건을 MELSEC-Q 래더 로직으로 변환합니다.

    Args:
        description: 동작 설명 텍스트
        inputs: 입력 디바이스 목록
        outputs: 출력 디바이스 목록
        sequences: 시퀀스 스텝 목록
        device_start: 디바이스 시작 번호 (선택, 예: {"X": 0, "Y": 0})

    Returns:
        래더 프로그램 JSON (device_map, rungs, detected_patterns)
    """
    return _generate(description, inputs, outputs, sequences, device_start)


@mcp.tool()
def export_gxworks2(
    ladder: dict,
    output_path: str | None = None,
    output_format: str = "gxw",
) -> dict:
    """래더 로직을 GX Works2 파일로 저장합니다.

    output_format="gxw"이면 CSV를 생성하고 UIA 자동화로 .gxw 프로젝트 파일을 생성합니다.
    output_format="csv"이면 CSV 파일만 생성합니다 (수동 Import용).

    Args:
        ladder: 래더 프로그램 JSON (generate_ladder 출력)
        output_path: 저장 경로 (None이면 기본 경로 사용)
        output_format: 출력 포맷 ("gxw" = .gxw 프로젝트, "csv" = CSV만)

    Returns:
        program_text (IL 프로그램), file_path (저장 경로), output_format, warnings
    """
    return _export(ladder, output_path=output_path, output_format=output_format)


@mcp.tool()
def import_to_gxworks2(
    file_path: str,
    auto_open: bool = True,
) -> dict:
    """생성된 파일을 GX Works2에 자동 Import하고 래더 화면을 표시합니다.

    .gxw 파일은 os.startfile()로 직접 열고,
    .csv 파일은 UIA 자동화로 GX Works2에 Import합니다.

    자동 Import 실패 시 파일 경로와 수동 Import 안내를 반환합니다.

    Args:
        file_path: 파일 경로 (.gxw 또는 .csv, export_gxworks2에서 반환된 file_path)
        auto_open: GX Works2 자동 실행 여부 (False면 수동 안내만 반환)

    Returns:
        status (success/error/skipped), message, file_path, fallback (실패 시 수동 안내)
    """
    return _import(file_path, auto_open)


@mcp.tool()
def render_ladder_diagram(
    ladder: dict,
    format: str = "text",
    show_comments: bool = True,
) -> dict:
    """래더 로직을 시각적 다이어그램(텍스트/SVG)으로 렌더링합니다.

    Args:
        ladder: 래더 프로그램 JSON
        format: 출력 형식 (text/svg)
        show_comments: 코멘트 표시 여부

    Returns:
        렌더링된 콘텐츠 (content, format, rung_count)
    """
    return _render(ladder, format, show_comments)


# ── Resources ────────────────────────────────────────────────────────────


@mcp.resource("melsec://device-list")
def get_device_list() -> str:
    """MELSEC-Q 디바이스 목록 및 범위 정보를 제공합니다."""
    return json.dumps({
        "devices": [
            {"type": "X", "name": "입력", "range": "X0-X37", "format": "octal",
             "description": "푸시버튼, 센서 등 외부 입력"},
            {"type": "Y", "name": "출력", "range": "Y0-Y37", "format": "octal",
             "description": "램프, 모터, 부저 등 외부 출력"},
            {"type": "M", "name": "보조릴레이", "range": "M0-M99", "format": "decimal",
             "description": "자기유지, 내부 플래그"},
            {"type": "T", "name": "타이머", "range": "T0-T99", "format": "decimal",
             "description": "100ms 단위 (K10=1초, K50=5초)"},
            {"type": "C", "name": "카운터", "range": "C0-C99", "format": "decimal",
             "description": "카운트 동작"},
            {"type": "D", "name": "데이터레지스터", "range": "D0-D99", "format": "decimal",
             "description": "수치 데이터 저장"},
        ],
    }, ensure_ascii=False, indent=2)


@mcp.resource("melsec://instruction-set")
def get_instruction_set() -> str:
    """지원 명령어 목록 및 사용법을 제공합니다."""
    return json.dumps({
        "instructions": [
            {"name": "LD", "description": "a접점 로드", "example": "LD X0"},
            {"name": "LDI", "description": "b접점 로드", "example": "LDI X1"},
            {"name": "AND", "description": "직렬 a접점", "example": "AND M0"},
            {"name": "ANI", "description": "직렬 b접점", "example": "ANI X1"},
            {"name": "OR", "description": "병렬 a접점", "example": "OR M0"},
            {"name": "ORI", "description": "병렬 b접점", "example": "ORI X1"},
            {"name": "OUT", "description": "코일 출력", "example": "OUT Y0"},
            {"name": "OUT T", "description": "타이머 출력", "example": "OUT T0 K50"},
            {"name": "OUT C", "description": "카운터 출력", "example": "OUT C0 K10"},
            {"name": "SET", "description": "셋", "example": "SET Y0"},
            {"name": "RST", "description": "리셋", "example": "RST Y0"},
            {"name": "ORB", "description": "병렬 블록 결합", "example": "ORB"},
            {"name": "ANB", "description": "직렬 블록 결합", "example": "ANB"},
            {"name": "MPS", "description": "분기 스택 푸시", "example": "MPS"},
            {"name": "MRD", "description": "분기 스택 읽기", "example": "MRD"},
            {"name": "MPP", "description": "분기 스택 팝", "example": "MPP"},
            {"name": "END", "description": "프로그램 종료", "example": "END"},
        ],
    }, ensure_ascii=False, indent=2)


@mcp.resource("melsec://patterns")
def get_patterns() -> str:
    """지원되는 제어 패턴 목록을 제공합니다."""
    return json.dumps({
        "patterns": [
            {
                "name": "self_hold",
                "description": "자기유지 회로",
                "detail": "PB ON → 릴레이 유지 → PB OFF로 해제",
                "devices": ["X", "Y", "M"],
            },
            {
                "name": "timer_delay",
                "description": "타이머 지연",
                "detail": "N초 후 동작 (100ms 단위 타이머)",
                "devices": ["T"],
            },
            {
                "name": "sequential",
                "description": "순차 제어",
                "detail": "A → B → C 순서대로 동작 (자기유지 + 타이머 복합)",
                "devices": ["T", "M"],
            },
            {
                "name": "full_reset",
                "description": "전체 리셋",
                "detail": "정지 버튼으로 모든 출력 OFF",
                "devices": ["X"],
            },
            {
                "name": "flicker",
                "description": "플리커 (점멸)",
                "detail": "N초 간격 반복 ON/OFF (교차 타이머 2개)",
                "devices": ["T"],
            },
        ],
    }, ensure_ascii=False, indent=2)


def main() -> None:
    """Run the MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
