# melsec-ladder-mcp

타이밍도 기반 MELSEC-Q 래더 프로그램 자동 생성 MCP 서버

## 개요

타이밍도(Timing Diagram)에서 추출한 동작 조건을 입력받아 미쓰비시 MELSEC-Q 시리즈용 래더(Ladder) 프로그램을 자동 생성하고, **GX Works2에서 바로 Import 가능한 IL 텍스트 파일**로 출력합니다.

### 대상 사용자

- 폴리텍/직업훈련원 전기 실습 교육자
- 전기기능사/산업기사 수험생
- PLC 프로그래밍 학습자

### 워크플로우

```
타이밍도 이미지 → Claude 이미지 분석 → MCP 서버 → GX Works2 Import용 .txt
```

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
      "args": ["--directory", "/path/to/melsecai", "run", "melsec-ladder-mcp"]
    }
  }
}
```

## MCP Tools

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

**출력:** 감지된 패턴 (self_hold, timer_delay, sequential, flicker, full_reset)

### 2. `generate_ladder`

동작 조건으로부터 래더 프로그램(IR)을 생성합니다. 패턴 매칭 → 디바이스 자동 할당 → 래더 구축.

### 3. `export_gxworks2`

래더 프로그램을 GX Works2 텍스트 Import 형식(IL)으로 변환합니다.

**출력:**

- `program_text` — IL 명령어 텍스트
- `device_comments_csv` — 디바이스 코멘트 CSV

### 4. `render_ladder_diagram`

래더 프로그램을 텍스트 또는 SVG 다이어그램으로 시각화합니다.

## MCP Resources

| URI | 설명 |
|-----|------|
| `melsec://device-list` | MELSEC-Q 디바이스 목록 및 범위 |
| `melsec://instruction-set` | 지원 IL 명령어 목록 |
| `melsec://patterns` | 지원 제어 패턴 목록 |

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

## GX Works2 Import 방법

1. GX Works2에서 새 프로젝트 생성 (QCPU, Simple Project)
2. **프로젝트** → **읽기(R)** → **텍스트 파일에서 읽기** 선택
3. 생성된 `.txt` 파일을 선택하여 Import
4. 디바이스 코멘트는 별도 CSV 파일로 제공 — **도구** → **디바이스 코멘트 일괄 변경**에서 적용

## 디바이스 주소 규칙

| 디바이스 | 범위 | 주소 형식 | 용도 |
|----------|------|-----------|------|
| X | X0 ~ X37 | 8진수 | 입력 (푸시버튼, 센서) |
| Y | Y0 ~ Y37 | 8진수 | 출력 (램프, 모터, 부저) |
| M | M0 ~ M99 | 10진수 | 보조 릴레이 |
| T | T0 ~ T99 | 10진수 | 타이머 (100ms 단위) |
| C | C0 ~ C99 | 10진수 | 카운터 |
| D | D0 ~ D99 | 10진수 | 데이터 레지스터 |

### 타이머 K값 계산

```
0.5초 = K5    1초 = K10    5초 = K50    10초 = K100
```

## 지원 IL 명령어

| 명령어 | 설명 | 예시 |
|--------|------|------|
| LD / LDI | a접점 / b접점 로드 | `LD X0`, `LDI X1` |
| AND / ANI | 직렬 a접점 / b접점 | `AND M0`, `ANI X1` |
| OR / ORI | 병렬 a접점 / b접점 | `OR M0`, `ORI X1` |
| OUT | 코일 / 타이머 / 카운터 출력 | `OUT Y0`, `OUT T0 K50` |
| SET / RST | 셋 / 리셋 | `SET Y0`, `RST M0` |
| ORB / ANB | 병렬 / 직렬 블록 결합 | `ORB`, `ANB` |
| MPS / MRD / MPP | 분기 스택 푸시 / 읽기 / 팝 | 복수 출력 분기 |
| END | 프로그램 종료 | `END` |

## 프로젝트 구조

```
src/melsec_ladder_mcp/
├── server.py                  # FastMCP 서버 진입점 (4 Tools + 3 Resources)
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
│   ├── exporter.py            #   export_gxworks2
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
└── formats/
    └── gxworks2.py            # GX Works2 텍스트 + CSV 포맷터
```

## 테스트

```bash
uv run pytest -v
```

**85개 테스트** — 모델 검증, 옥탈 주소, 컴파일러(직렬/병렬/MPS), IL 검증, 패턴 매칭/생성, GX Works2 포맷, MCP 도구, E2E 파이프라인

## 라이선스

MIT
