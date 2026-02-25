# PRD: GX Works2 래더 자동 생성 MCP 서버

## 1. 개요

### 1.1 프로젝트명
**MELSEC Ladder Generator MCP Server** (가칭: `melsec-ladder-mcp`)

### 1.2 목적
타이밍도(Timing Diagram) 이미지를 입력받아 동작 조건을 분석하고, 미쓰비시 MELSEC-Q 시리즈용 래더(Ladder) 프로그램을 자동 생성하여 GX Works2에서 Import 가능한 텍스트 파일로 출력하는 MCP 서버를 구축한다.

### 1.3 대상 사용자
- 폴리텍/직업훈련원 전기 실습 교육자
- 전기기능사/산업기사 수험생
- PLC 프로그래밍 학습자

### 1.4 핵심 가치
- 타이밍도만 주면 래더 프로그램이 자동 생성됨
- GX Works2에 바로 Import 가능한 파일 출력
- 교육 현장에서 빠른 예제 생성 및 검증 가능

---

## 2. 시스템 아키텍처

### 2.1 전체 흐름

```
[타이밍도 이미지]
    ↓
[Claude] — 이미지 분석, 동작 조건 추출
    ↓
[MCP 서버: melsec-ladder-mcp]
    ├── 1) 동작 조건 → 래더 로직 변환
    ├── 2) 디바이스 자동 할당
    ├── 3) GX Works2 텍스트 형식 파일 생성
    └── 4) 래더 다이어그램 시각화 (선택)
    ↓
[출력: .txt 또는 .csv (GX Works2 Import용)]
    ↓
[사용자: GX Works2에서 Import]
```

### 2.2 기술 스택

| 구분 | 기술 |
|------|------|
| MCP 서버 | Python (FastMCP) |
| 래더 로직 엔진 | Python 내부 모듈 |
| 출력 형식 | GX Works2 텍스트 Import 형식 (.txt) |
| 시각화 (선택) | SVG 또는 HTML 래더 다이어그램 |
| 통신 | MCP Protocol (stdio 또는 SSE) |

---

## 3. 기능 요구사항

### 3.1 Tool 목록

#### Tool 1: `analyze_timing_diagram`
- **설명**: 타이밍도에서 추출된 동작 조건(텍스트)을 구조화된 JSON으로 변환
- **입력**: 동작 조건 텍스트 (Claude가 이미지에서 추출한 내용)
- **출력**: 구조화된 동작 조건 JSON

```json
// 입력 예시 (Claude가 타이밍도에서 추출한 텍스트)
{
  "description": "PB1을 누르면 RL이 점등되고 5초 후 GL이 점등되며, 10초 후 BZ가 동작한다. PB2를 누르면 모든 동작이 정지한다.",
  "inputs": [
    { "name": "PB1", "type": "push_button", "mode": "momentary" },
    { "name": "PB2", "type": "push_button", "mode": "momentary" }
  ],
  "outputs": [
    { "name": "RL", "type": "lamp" },
    { "name": "GL", "type": "lamp" },
    { "name": "BZ", "type": "buzzer" }
  ],
  "sequences": [
    { "trigger": "PB1", "action": "RL ON" },
    { "trigger": "RL ON", "delay": 5, "action": "GL ON" },
    { "trigger": "RL ON", "delay": 10, "action": "BZ ON" },
    { "trigger": "PB2", "action": "ALL OFF" }
  ]
}
```

#### Tool 2: `generate_ladder`
- **설명**: 구조화된 동작 조건을 MELSEC-Q 래더 로직으로 변환
- **입력**: 동작 조건 JSON + 디바이스 할당 옵션(선택)
- **출력**: 래더 로직 JSON (내부 중간 표현)

```json
// 출력 예시
{
  "device_map": {
    "PB1": "X0", "PB2": "X1",
    "RL": "Y0", "GL": "Y1", "BZ": "Y2",
    "T0": { "type": "TON", "value": 50, "unit": "100ms", "comment": "5초 타이머" },
    "T1": { "type": "TON", "value": 100, "unit": "100ms", "comment": "10초 타이머" },
    "M0": { "comment": "운전 자기유지" }
  },
  "rungs": [
    {
      "number": 0,
      "comment": "PB1 자기유지 회로",
      "elements": [
        { "type": "contact", "device": "X0", "mode": "NO" },
        { "type": "parallel", "device": "M0", "mode": "NO" },
        { "type": "contact", "device": "X1", "mode": "NC" },
        { "type": "coil", "device": "M0" }
      ]
    },
    {
      "number": 1,
      "comment": "RL 출력",
      "elements": [
        { "type": "contact", "device": "M0", "mode": "NO" },
        { "type": "coil", "device": "Y0" }
      ]
    },
    {
      "number": 2,
      "comment": "5초 타이머 (GL용)",
      "elements": [
        { "type": "contact", "device": "M0", "mode": "NO" },
        { "type": "timer", "device": "T0", "value": 50 }
      ]
    },
    {
      "number": 3,
      "comment": "GL 출력",
      "elements": [
        { "type": "contact", "device": "T0", "mode": "NO" },
        { "type": "coil", "device": "Y1" }
      ]
    },
    {
      "number": 4,
      "comment": "10초 타이머 (BZ용)",
      "elements": [
        { "type": "contact", "device": "M0", "mode": "NO" },
        { "type": "timer", "device": "T1", "value": 100 }
      ]
    },
    {
      "number": 5,
      "comment": "BZ 출력",
      "elements": [
        { "type": "contact", "device": "T1", "mode": "NO" },
        { "type": "coil", "device": "Y2" }
      ]
    }
  ]
}
```

#### Tool 3: `export_gxworks2`
- **설명**: 래더 로직을 GX Works2 텍스트 Import 형식으로 변환
- **입력**: 래더 로직 JSON
- **출력**: GX Works2 Import용 텍스트 파일 내용

```
// GX Works2 텍스트 형식 예시 (구조화된 래더)
// 실제 형식은 GX Works2 텍스트 내보내기 스펙에 맞춰 구현
STEP 0
LD X0
OR M0
ANI X1
OUT M0

STEP 1
LD M0
OUT Y0

STEP 2
LD M0
OUT T0 K50

STEP 3
LD T0
OUT Y1

STEP 4
LD M0
OUT T1 K100

STEP 5
LD T1
OUT Y2

END
```

#### Tool 4: `render_ladder_diagram` (선택)
- **설명**: 래더 로직을 시각적 다이어그램(SVG/HTML)으로 렌더링
- **입력**: 래더 로직 JSON
- **출력**: SVG 또는 HTML 래더 다이어그램

---

## 4. 지원 패턴

### 4.1 Phase 1 (MVP)
기본적인 시퀀스 제어 패턴을 지원한다.

| 패턴 | 설명 | 사용 디바이스 |
|------|------|---------------|
| 자기유지 회로 | PB ON → 유지 → PB OFF | X, Y, M |
| 타이머 지연 | N초 후 동작 | T (TON) |
| 순차 제어 | A → B → C 순서대로 | T, M |
| 전체 리셋 | 정지 버튼으로 전체 OFF | X (NC 접점) |
| 플리커 (점멸) | N초 간격 반복 점멸 | T (2개 조합) |

### 4.2 Phase 2 (확장)

| 패턴 | 설명 | 사용 디바이스 |
|------|------|---------------|
| 카운터 제어 | N회 반복 후 동작 | C |
| 인터록 | 동시 동작 방지 | M (NC 접점) |
| 우선 회로 | 선입력/후입력 우선 | M 조합 |
| 신호등 제어 | 교대 점등 사이클 | T, M 조합 |
| 컨베이어 제어 | 센서 연동 모터 제어 | X, Y, T, C |
| 스텝 제어 | SFC 스타일 순차 진행 | M (스텝 릴레이) |

---

## 5. 디바이스 할당 규칙

### 5.1 기본 디바이스 매핑

| 구분 | 디바이스 | 범위 | 비고 |
|------|----------|------|------|
| 입력 (푸시버튼, 센서) | X | X0 ~ X1F | 순서대로 자동 할당 |
| 출력 (램프, 모터, 부저) | Y | Y0 ~ Y1F | 순서대로 자동 할당 |
| 보조 릴레이 | M | M0 ~ M99 | 자기유지, 내부 플래그 |
| 타이머 | T | T0 ~ T99 | 100ms 기본 (K값) |
| 카운터 | C | C0 ~ C99 | Phase 2 |
| 데이터 레지스터 | D | D0 ~ D99 | Phase 2 |

### 5.2 타이머 설정값 계산
- MELSEC-Q 기본 타이머: 100ms 단위
- 5초 = K50 (50 × 100ms)
- 10초 = K100 (100 × 100ms)
- 1초 = K10
- 0.5초 = K5

### 5.3 디바이스 코멘트 자동 생성
- 입력: `X0: PB1 (시작 버튼)`, `X1: PB2 (정지 버튼)`
- 출력: `Y0: RL (적색 램프)`, `Y1: GL (녹색 램프)`
- 타이머: `T0: 5초 지연 (GL 점등용)`

---

## 6. GX Works2 호환성

### 6.1 대상 버전
- GX Works2 Version 1.98A 이상
- 프로젝트 타입: Simple Project / Structured Project

### 6.2 Import 형식
GX Works2의 **프로그램 → 텍스트로 내보내기/가져오기** 기능을 활용한다.

- **출력 파일**: `.txt` (GX Works2 텍스트 형식)
- **인코딩**: Shift-JIS 또는 UTF-8 (GX Works2 호환 확인 필요)
- **명령어 형식**: 니모닉(Mnemonic) 기반

### 6.3 지원 명령어 (Phase 1)

| 명령어 | 설명 | 예시 |
|--------|------|------|
| LD | a접점 로드 | LD X0 |
| LDI | b접점 로드 | LDI X1 |
| AND | 직렬 a접점 | AND M0 |
| ANI | 직렬 b접점 | ANI X1 |
| OR | 병렬 a접점 | OR M0 |
| ORI | 병렬 b접점 | ORI X1 |
| OUT | 코일 출력 | OUT Y0 |
| OUT T | 타이머 출력 | OUT T0 K50 |
| OUT C | 카운터 출력 | OUT C0 K10 |
| SET | 셋 | SET Y0 |
| RST | 리셋 | RST Y0 |
| ORB | 병렬 블록 결합 | ORB |
| ANB | 직렬 블록 결합 | ANB |
| MPS | 분기 스택 푸시 | MPS |
| MRD | 분기 스택 읽기 | MRD |
| MPP | 분기 스택 팝 | MPP |
| END | 프로그램 종료 | END |

---

## 7. MCP 서버 설계

### 7.1 서버 정보

```json
{
  "name": "melsec-ladder-mcp",
  "version": "1.0.0",
  "description": "타이밍도 기반 MELSEC-Q 래더 프로그램 자동 생성기"
}
```

### 7.2 Tools 정의

```python
# FastMCP 기반 Tool 등록

@mcp.tool()
def analyze_timing_diagram(
    description: str,
    inputs: list[dict],
    outputs: list[dict],
    sequences: list[dict]
) -> dict:
    """동작 조건을 구조화된 래더 생성용 JSON으로 변환"""

@mcp.tool()
def generate_ladder(
    conditions: dict,
    device_start: dict = None  # 디바이스 시작 번호 옵션
) -> dict:
    """구조화된 조건을 래더 로직(중간 표현)으로 변환"""

@mcp.tool()
def export_gxworks2(
    ladder: dict,
    project_type: str = "simple",  # simple | structured
    encoding: str = "shift-jis"
) -> str:
    """래더 로직을 GX Works2 텍스트 Import 형식으로 출력"""

@mcp.tool()
def render_ladder_diagram(
    ladder: dict,
    format: str = "svg"  # svg | html
) -> str:
    """래더 로직을 시각적 다이어그램으로 렌더링"""
```

### 7.3 Resources (선택)

```python
@mcp.resource("melsec://device-list")
def get_device_list() -> str:
    """MELSEC-Q 디바이스 목록 및 범위 정보 제공"""

@mcp.resource("melsec://instruction-set")
def get_instruction_set() -> str:
    """지원 명령어 목록 및 사용법 제공"""

@mcp.resource("melsec://patterns")
def get_patterns() -> str:
    """지원되는 제어 패턴 목록 제공"""
```

---

## 8. 사용 시나리오

### 8.1 기본 워크플로우

```
사용자: [타이밍도 이미지 업로드]
        "이 타이밍도를 래더 프로그램으로 만들어줘"

Claude:  1) 이미지 분석 → 동작 조건 텍스트 추출
         2) analyze_timing_diagram 호출 → 구조화
         3) generate_ladder 호출 → 래더 로직 생성
         4) export_gxworks2 호출 → 텍스트 파일 생성
         5) render_ladder_diagram 호출 → 시각화 (선택)
         6) 파일 다운로드 링크 + 래더 설명 제공

사용자: GX Works2에서 텍스트 Import로 프로그램 로드
```

### 8.2 대화 예시

```
사용자: 실습 11 타이밍도를 래더로 만들어줘

Claude: 타이밍도를 분석했습니다.

[동작 조건]
- PB1 → RL 점등 (자기유지)
- 5초 후 GL 점등
- 10초 후 BZ 동작
- PB2 → 전체 정지

[디바이스 할당]
- X0: PB1, X1: PB2
- Y0: RL, Y1: GL, Y2: BZ
- T0: 5초, T1: 10초
- M0: 운전 자기유지

[래더 프로그램] (GX Works2 Import용 파일 첨부)

GX Works2에서 [프로젝트] → [프로그램 읽기] → [텍스트 파일]로
Import하시면 됩니다.
```

---

## 9. 개발 로드맵

### Phase 1: MVP (2주)
- [ ] 프로젝트 초기 설정 (FastMCP + Python)
- [ ] GX Works2 텍스트 형식 파서/생성기 구현
- [ ] 기본 래더 패턴 엔진 (자기유지, 타이머, 순차, 리셋)
- [ ] `analyze_timing_diagram` Tool 구현
- [ ] `generate_ladder` Tool 구현
- [ ] `export_gxworks2` Tool 구현
- [ ] 실습 11 예제로 검증
- [ ] GX Works2에서 실제 Import 테스트

### Phase 2: 확장 (2주)
- [ ] 추가 패턴 지원 (카운터, 인터록, 플리커, 스텝)
- [ ] `render_ladder_diagram` Tool 구현
- [ ] 디바이스 코멘트 파일 생성 기능
- [ ] 복수 프로그램(MAIN, SUB) 지원
- [ ] 에러 검증 (디바이스 중복, 타이머 충돌 등)

### Phase 3: 고도화 (선택)
- [ ] 다양한 시험 유형 패턴 라이브러리
- [ ] CBT 플랫폼 연동 (문제 출제 → 래더 자동 생성)
- [ ] GX Works3 (iQ-R/iQ-F) 형식 지원
- [ ] 시뮬레이션 결과 검증 기능

---

## 10. 파일 구조

```
melsec-ladder-mcp/
├── README.md
├── pyproject.toml
├── src/
│   └── melsec_ladder_mcp/
│       ├── __init__.py
│       ├── server.py              # MCP 서버 진입점
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── analyzer.py        # 동작 조건 분석기
│       │   ├── generator.py       # 래더 로직 생성기
│       │   ├── exporter.py        # GX Works2 텍스트 출력기
│       │   └── renderer.py        # 래더 다이어그램 시각화
│       ├── core/
│       │   ├── __init__.py
│       │   ├── devices.py         # 디바이스 관리 (X, Y, M, T, C)
│       │   ├── instructions.py    # 명령어 정의 (LD, OUT, AND 등)
│       │   ├── patterns.py        # 제어 패턴 (자기유지, 타이머 등)
│       │   └── ladder.py          # 래더 중간 표현 (IR)
│       └── formats/
│           ├── __init__.py
│           └── gxworks2.py        # GX Works2 텍스트 형식 변환
├── tests/
│   ├── test_analyzer.py
│   ├── test_generator.py
│   ├── test_exporter.py
│   └── fixtures/
│       └── practice_11.json       # 실습 11 테스트 데이터
└── examples/
    ├── practice_11_input.json     # 실습 11 입력
    └── practice_11_output.txt     # 실습 11 GX Works2 출력
```

---

## 11. 검증 기준

### 11.1 MVP 완료 조건
1. 실습 11 타이밍도를 입력하면 올바른 래더 로직이 생성된다
2. 생성된 텍스트 파일을 GX Works2에서 Import 시 에러 없이 로드된다
3. Import된 래더를 GX Simulator로 실행 시 타이밍도와 동일하게 동작한다

### 11.2 테스트 케이스

| # | 테스트 | 기대 결과 |
|---|--------|-----------|
| 1 | 실습 11 (자기유지+타이머) | RL→5초→GL→10초→BZ, PB2 정지 |
| 2 | 단순 ON/OFF | PB1→Y0 ON, PB2→Y0 OFF |
| 3 | 플리커 1초 점멸 | Y0가 1초 간격 ON/OFF 반복 |
| 4 | 3단 순차 제어 | A→3초→B→5초→C→2초→전체OFF |
| 5 | 카운터 조합 | 5회 반복 후 정지 (Phase 2) |

---

## 12. 제약 사항 및 참고

### 12.1 제약 사항
- GX Works2 텍스트 형식은 공식 문서가 제한적이므로, 실제 Export된 파일을 리버스 엔지니어링하여 형식을 파악해야 한다
- 복잡한 분기(MPS/MRD/MPP) 구조는 Phase 1에서 기본적인 수준만 지원한다
- 이미지 분석은 Claude의 비전 기능에 의존하며, MCP 서버는 텍스트 기반 입력만 처리한다

### 12.2 참고 자료
- GX Works2 Operating Manual (프로그램 텍스트 내보내기/가져오기 섹션)
- MELSEC-Q 프로그래밍 매뉴얼 (명령어 레퍼런스)
- MCP Protocol Specification (https://modelcontextprotocol.io)
- FastMCP Python SDK
