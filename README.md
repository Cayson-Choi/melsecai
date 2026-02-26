# melsec-ladder-mcp

타이밍도 기반 MELSEC-Q 래더 프로그램 자동 생성 + GX Works2 자동 Import MCP 서버

## 개요

타이밍도(Timing Diagram)에서 추출한 동작 조건을 입력받아 미쓰비시 MELSEC-Q 시리즈용 래더(Ladder) 프로그램을 자동 생성하고, **CSV + UIA 자동화**를 통해 GX Works2 프로젝트(.gxw)까지 원스톱으로 생성합니다.

### 대상 사용자

- 폴리텍/직업훈련원 전기 실습 교육자
- 전기기능사/산업기사 수험생
- PLC 프로그래밍 학습자

### 전체 흐름

```
1. 타이밍도 이미지 업로드 (또는 동작 조건 텍스트 입력)
   "이 타이밍도를 래더로 만들어줘"
        ↓ (이 아래는 전부 자동)
2. Claude가 이미지 분석
   → "PB1 누르면 RL 점등, 5초 후 GL, 10초 후 BZ, PB2로 정지"
        ↓
3. MCP 서버가 래더 로직 생성
   → 디바이스 할당 (X0, Y0, T0 등)
   → 니모닉 코드 생성 (LD X0 / OR M0 / ANI X1 / OUT M0...)
        ↓
4. CSV 파일 생성
   → GX Works2 CSV Import 형식 (UTF-16 LE, 탭 구분)
        ↓
5. UIA 자동화로 GX Works2에 Import
   → 빈 프로젝트 열기 → [편집] → [CSV 파일에서 읽기] → 저장
        ↓
6. GX Works2에 래더가 떠있음
        ↓
7. 사용자는 래더 확인하고 시뮬레이션 돌리면 끝
```

## 환경 요구사항

| 항목 | 요구사항 |
|------|----------|
| OS | Windows 10/11 (64bit) |
| GX Works2 | Version 1.98A 이상 |
| Python | 3.11 이상 |
| 디스플레이 | DPI 100% 권장 |

## 설치

```bash
# uv 사용 (권장)
uv sync

# pip 사용
pip install -e .
```

## 실행

### MCP 서버 기동

```bash
uv run melsec-ladder-mcp
```

### Claude Desktop 연동

`claude_desktop_config.json`에 추가:

```json
{
  "mcpServers": {
    "melsec-ladder-mcp": {
      "command": "uv",
      "args": ["--directory", "D:/Antigravity/melsecai", "run", "melsec-ladder-mcp"]
    }
  }
}
```

## MCP Tools (5종)

### 1. `analyze_timing_diagram`

동작 조건 텍스트를 구조화된 JSON으로 변환하고 패턴을 감지합니다.

**입력:**

```json
{
  "description": "PB1을 누르면 RL이 점등되고 5초 후 GL이 점등된다. PB2를 누르면 정지.",
  "inputs": [
    { "name": "PB1", "type": "push_button", "mode": "momentary" },
    { "name": "PB2", "type": "push_button", "mode": "momentary" }
  ],
  "outputs": [
    { "name": "RL", "type": "lamp" },
    { "name": "GL", "type": "lamp" }
  ],
  "sequences": [
    { "trigger": "PB1", "action": "RL ON" },
    { "trigger": "RL ON", "delay": 5, "action": "GL ON" },
    { "trigger": "PB2", "action": "ALL OFF" }
  ]
}
```

### 2. `generate_ladder`

동작 조건으로부터 래더 프로그램(IR)을 생성합니다. 패턴 매칭 → 디바이스 자동 할당 → 래더 구축.

### 3. `export_gxworks2`

래더 프로그램을 GX Works2 파일로 저장합니다.

- `output_format="gxw"` (기본): CSV 생성 → UIA 자동화 → .gxw 프로젝트 생성
- `output_format="csv"`: CSV 파일만 생성 (수동 Import용)
- 기본 저장 경로: `D:\Antigravity\melsecai\melseccode\`

### 4. `import_to_gxworks2`

생성된 파일을 GX Works2에 자동 Import합니다.

- `.gxw` 파일: `os.startfile()`로 직접 열기
- `.csv` 파일: UIA 자동화로 GX Works2에 Import 후 .gxw 저장
- 자동 Import 실패 시 수동 안내를 fallback으로 반환

### 5. `render_ladder_diagram`

래더 프로그램을 텍스트 또는 SVG 다이어그램으로 시각화합니다.

## MCP Resources (3종)

| URI | 설명 |
|-----|------|
| `melsec://device-list` | MELSEC-Q 디바이스 목록 및 범위 |
| `melsec://instruction-set` | 지원 IL 명령어 목록 |
| `melsec://patterns` | 지원 제어 패턴 목록 |

## 설정

`config/gxworks2_config.yaml`에서 GX Works2 환경을 설정합니다:

```yaml
gxworks2:
  install_path: "C:\\Program Files (x86)\\MELSOFT\\GPPW2\\GD2.exe"
  language: "ko"
  default_cpu: "Q03UDE"
  default_project_type: "simple"
  output_dir: "D:\\Antigravity\\melsecai\\melseccode"
  encoding: "shift-jis"
  timeouts:
    launch: 10
    dialog: 5
    import_wait: 10
```

## 지원 패턴

| 패턴 | 설명 | 예시 |
|------|------|------|
| **자기유지** (self_hold) | PB ON → 릴레이 유지 → PB OFF 해제 | `LD X0 / OR M0 / ANI X1 / OUT M0` |
| **타이머 지연** (timer_delay) | N초 후 동작 | `LD M0 / OUT T0 K50` |
| **순차 제어** (sequential) | 자기유지 + 타이머 복합 | Practice 11 전체 |
| **전체 리셋** (full_reset) | 정지 버튼으로 전체 OFF | ANI 접점으로 구현 |
| **플리커** (flicker) | N초 간격 반복 점멸 | 교차 결합 타이머 2개 |

## 예제: 실습 11

### 동작 조건

> PB1을 누르면 RL이 점등되고 5초 후 GL이 점등되며, 10초 후 BZ가 동작한다. PB2를 누르면 모든 동작이 정지한다.

### 디바이스 할당

| 디바이스 | 코멘트 |
|----------|--------|
| X0 | PB1 (시작 버튼) |
| X1 | PB2 (정지 버튼) |
| M0 | 운전 자기유지 |
| Y0 | RL (적색 램프) |
| Y1 | GL (녹색 램프) |
| Y2 | BZ (부저) |
| T0 | 5초 지연 (K50) |
| T1 | 10초 지연 (K100) |

### 생성된 IL 프로그램

```
LD X0
OR M0
ANI X1
OUT M0
LD M0
OUT Y0
LD M0
OUT T0 K50
LD T0
OUT Y1
LD M0
OUT T1 K100
LD T1
OUT Y2
END
```

## 프로젝트 구조

```
src/melsec_ladder_mcp/
├── server.py                  # FastMCP 서버 진입점 (5 Tools + 3 Resources)
├── errors.py                  # 커스텀 예외 계층
├── models/                    # Pydantic 데이터 모델
│   ├── timing.py              #   입력: TimingDescription, TimingAnalysis
│   ├── devices.py             #   디바이스: DeviceAddress (옥탈), DeviceMap
│   ├── ladder.py              #   래더 IR: Rung, SeriesConnection, ParallelBranch
│   ├── instructions.py        #   IL: Instruction, InstructionSequence
│   ├── export.py              #   내보내기: ExportOptions, ExportResult
│   └── rendering.py           #   렌더링: RenderOptions, RenderResult
├── tools/                     # MCP 도구 구현
│   ├── analyzer.py            #   analyze_timing_diagram
│   ├── generator.py           #   generate_ladder
│   ├── exporter.py            #   export_gxworks2 (CSV/GXW 저장)
│   ├── importer.py            #   import_to_gxworks2 (GX Works2 자동 Import)
│   └── renderer.py            #   render_ladder_diagram
├── core/                      # 코어 엔진
│   ├── devices.py             #   DeviceAllocator (옥탈 순차 할당)
│   ├── compiler.py            #   LadderCompiler (IR → IL)
│   ├── instructions.py        #   InstructionValidator (스택 균형 등)
│   ├── ladder.py              #   LadderBuilder (플루언트 API)
│   └── patterns/              #   패턴 엔진
│       ├── base.py            #     BasePattern ABC + PatternRegistry
│       ├── self_hold.py       #     자기유지 회로
│       ├── timer_delay.py     #     타이머 지연
│       ├── sequential.py      #     순차 제어 (복합)
│       ├── full_reset.py      #     전체 리셋
│       └── flicker.py         #     플리커 점멸
├── automation/                # GX Works2 UI 자동화
│   ├── gxworks2_uia.py        #   UIA 백엔드 컨트롤러
│   └── config.py              #   YAML 설정 로더
└── formats/                   # GX Works2 포맷터
    ├── gxworks2.py            #   IL 텍스트 포맷터
    ├── csv_formatter.py       #   CSV 포맷터 (GX Works2 Import 형식)
    └── template.gxw           #   템플릿 GXW (Q03UDV 빈 프로젝트)
config/
└── gxworks2_config.yaml       # GX Works2 환경 설정
```

## 테스트

```bash
uv run pytest -v
```

## 라이선스

MIT
