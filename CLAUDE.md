# MELSEC Ladder Generator MCP Server

## Project Overview
- **Purpose**: Timing diagram → MELSEC-Q ladder → GX Works2 auto-import (원스톱)
- **Target**: 폴리텍/직업훈련원 교육자, 전기기능사 수험생
- **Tech**: FastMCP 3.x, Pydantic 2.x, pywinauto (UIA), Python 3.12
- **교재**: `learningdata/PLC 프로그래밍 실습.pdf` (56p, 실습 1-20)

## Architecture
```
src/melsec_ladder_mcp/
├── server.py          # FastMCP server (5 Tools + 3 Resources)
├── errors.py          # Custom exception hierarchy
├── models/            # Pydantic models
├── tools/             # MCP tools (analyzer, generator, exporter, importer, renderer)
├── core/              # Engine (devices, compiler, validator, ladder builder)
│   └── patterns/      # Pattern engine (5 patterns)
├── automation/        # GX Works2 UI automation
│   ├── gxworks2_uia.py   # UIA backend controller (_reconnect 후 CSV import)
│   └── config.py          # YAML config loader
└── formats/           # GX Works2 formatters
    ├── gxworks2.py        # IL text formatter
    ├── csv_formatter.py   # CSV formatter (GX Works2 CSV import format)
    └── template.gxw       # Template GXW (Q03UDV, legacy — New Project 방식 권장)
config/
└── gxworks2_config.yaml
```

## Workflow: 프로그램 작성 요청 시
0. **먼저 사용자에게 CPU 타입을 물어볼 것** (기본: Q03UDE)
1. 래더 프로그램 생성 (generate_ladder)
2. CSV 파일 생성 (export_gxworks2, output_format="csv")
3. GX Works2 실행 → **New Project(cpu_type)** 또는 template.gxw 열기
4. 팝업 닫기 → CSV 임포트 → F4 컴파일 → Save As
5. **최종 .gxw 파일을 `out/` 디렉토리에 저장** (예: out/practice_17.gxw)
6. **`out/` 폴더에는 완성된 .gxw 파일만 유지** — 중간 산출물(CSV 등)은 작업 후 삭제

## Key Design Decisions
- X/Y: **hex** addressing in Q-series (X0..XF, X10..X1F); M/T/C/D: decimal
- Simple parallels → OR/ORI; complex → LD+ORB
- Multiple outputs → MPS/MRD/MPP stack
- Timer K-value = seconds × 10 (100ms resolution, T0-T199)
- **export_gxworks2**: `output_format="gxw"` (default) → CSV + UIA automation
- **import_to_gxworks2**: .gxw → os.startfile(); .csv → UIA
- **_reconnect()**: New Project 생성 후 pywinauto 윈도우 참조 갱신 필수

## CSV Format (GX Works2 Import)
- UTF-16 LE with BOM, tab-delimited, quoted fields
- Timer/Counter OUT → 2 CSV rows (instruction + K-value on separate line)
- Application instructions → N CSV rows (instruction + first operand, then one row per remaining operand)
- Step numbering: timer/counter OUT = 4 steps, app instructions = operands+1, END = 2 steps, others = 1 step

---

## GX Works2 래더 프로그래밍 패턴 (학습 완료: 실습 1-20)

> 출처: `learningdata/PLC 프로그래밍 실습.pdf` (2024 폴리텍 화성캠퍼스)

### 교재 디바이스 맵 (기본)
| 용도 | 디바이스 | 비고 |
|------|---------|------|
| 리셋/초기화 | X0 (PBS0) | NC 접점으로 사용 |
| 시작 버튼 | X1 (PBS1) | NO 접점 |
| 정지 버튼 | X2 (PBS2) | NC 접점 (자기유지 해제) |
| 추가 입력 | X3, X4 | |
| 내부 릴레이 | M0, M1, M2... | 자기유지, 중간 릴레이 |
| 타이머 | T0, T1, T2... | K-value = 초 × 10 |
| 출력 | Y20, Y21, Y22... | RL, GL, YL, BZ 등 |
| 특수릴레이 | SM400(항시ON), SM401(항시OFF), SM409-413(블링크) |

### 패턴 1: 자기유지 (Self-Hold)
```
LD X1          ; 시작 버튼 (NO)
OR M0          ; 자기유지
ANI X2         ; 정지 버튼 (NC) — 또는 ANI T_last (타이머 완료시 해제)
OUT M0
```
- **핵심**: 정지 조건은 목적에 따라 다름
  - 단순 정지: `ANI X2` (정지 버튼 NC)
  - 시퀀스 완료 후 자동 리셋: `ANI T_last` (마지막 타이머 NC)

### 패턴 2: 체인 타이머 (Chained Timer)
```
LD M0           ; 릴레이
OUT T0 K30      ; 3초 (첫 번째 딜레이)
LD T0           ; T0 완료 후
OUT T1 K20      ; 2초 (두 번째 딜레이, T0에서 체인)
LD T1           ; T1 완료 후
OUT T2 K50      ; 5초 (세 번째 딜레이, T1에서 체인)
```
- **절대로 누적(cumulative) 방식과 혼동하지 말 것!**
- 누적: M0→T0 K30, M0→T1 K50 (모두 M0에서 시작, T1은 5초 후)
- 체인: M0→T0 K30, T0→T1 K20 (T0 완료 후 T1 시작, 총 5초)
- **교과서에서는 체인 방식이 기본!** (실습 11, 12, 13, 14, 15, 17, 18)

### 패턴 3: 출력 게이팅 (Output Gating)
| 출력 조건 | IL | 설명 |
|----------|-----|------|
| 즉시 ON, 조건 OFF | `LD M0 / ANI T_off / OUT Y` | M0 활성~T_off까지 |
| 딜레이 ON, 끝까지 | `LD T_on / OUT Y` | T_on 완료부터 M0 해제까지 |
| 딜레이 ON, 딜레이 OFF | `LD T_on / ANI T_off / OUT Y` | T_on~T_off 구간 |
| 시프트 (한 구간만) | `LD T_prev / ANI T_next / OUT Y` | T_prev~T_next 구간만 |

### 패턴 4: 순차 점등 + 역순 소등 (실습 14, 17 핵심!)
두 단계의 독립적인 체인 타이머 + 게이트 출력:

**ON 체인** (시작 트리거 → 순차 점등):
```
M0 → T0 K30 → T1 K20    ; RL 즉시, GL 3초후, YL 5초후
```

**OFF 체인** (정지 트리거 → 역순 소등):
```
M1 → T2 K20 → T3 K30    ; YL 즉시OFF, GL 2초후OFF, RL 5초후OFF
```

**출력 게이팅** (ON 타이머 NO + OFF 타이머 NC):
```
LD M0  / ANI T3 / OUT Y0   ; RL: M0~T3 (마지막에 OFF)
LD T0  / ANI T2 / OUT Y1   ; GL: T0~T2 (중간)
LD T1  / ANI M1 / OUT Y2   ; YL: T1~M1 (먼저 OFF)
```

**자기유지 리셋**: M0/M1 모두 `ANI T3` (마지막 OFF 타이머)로 해제!
- **절대로** M1을 `AND M0`로 게이팅하지 말 것 → T3(NC)로 해제해야 함

### 패턴 5: 순환 타이머 (Cyclic, 실습 18)
마지막 타이머의 NC 접점을 첫 번째 타이머의 입력에 피드백:
```
LD M0  / ANI T2 / OUT T0 K20   ; T2 리셋 후 T0 재시작
LD T0  / OUT T1 K30
LD T1  / OUT T2 K40             ; T2 완료 → T0 리셋 → 반복
```

### 패턴 6: 인터록 (Interlock, 실습 5)
이전 릴레이의 NC 접점을 직렬 추가:
```
LD X1                    → M1, Y21
LD X2 / ANI M1           → M2, Y22
LD X3 / ANI M1 / ANI M2  → M3, Y23
```

### 패턴 7: 우선 회로 (Priority, 실습 6-7)
- **선입력 우선**: M_any(NC) + X_n(NO) → M_n (with self-hold)
- **후입력 우선**: X0(NC) + X_n(NO) + 다른_M(NC) → M_n

### 패턴 8: 비교 명령 (Comparison, 대안 방식)
단일 타이머 + 비교로 다중 시점 제어:
```
LD M0 / OUT T0 K150           ; 15초 total
[>=] T0 K30                   ; 3초 이상이면
[<=] T0 K120                  ; 12초 이하이면
→ OUT Y21                     ; GL: 3~12초 구간 ON
```
- `>=`, `<=`, `<`, `>` 비교 접점 사용
- 교과서에서 "프로그램 - 1" 또는 "-2" 대안으로 제시

### 패턴 9: 전동기 제어 (Motor Control, 실습 8-10)
- EOCR: 과부하 보호 접점 (X0/X10)
- MC (전자접촉기): M0 → Y20
- FR (고장 릴레이): EOCR 동작시 활성, 플리커 출력
- 정역 운전: MC1(M1)/MC2(M2) + 인터록

### 실습별 정답 IL 요약

| 실습 | 핵심 패턴 | 타이머 | 비고 |
|------|---------|--------|------|
| 1 | 자기유지 | - | X2(NC)+[X1∥M0]→M0, M0→Y20 |
| 2 | 2릴레이 조합 | - | M1,M2 조합→Y20 |
| 3 | ON딜레이 | T0 K20 | M0→T0, T0→Y20, T0(NC)→Y21 |
| 4 | 체인 타이머 | T1 K20→T2 K40 | T2→M0(완료), M2+M0(NC)→Y20 |
| 5 | 인터록 | - | NC 직렬 추가 |
| 6-7 | 우선 회로 | - | 선입력/후입력 우선 |
| 8 | 전동기 기본 | - | EOCR, MC, FR |
| 9-10 | 전동기+플리커 | T0/T1 교번 | 정역 운전 |
| 11 | 순차 점등 | T0 K50→T1 K50 | 체인, RL즉시/GL 5s/BZ 10s |
| 12 | 순차 점등 (3단) | T0→T1→T2 | RL 2s/GL 5s/BZ 9s |
| 13 | 순차 소등 | T0→T1→T2 | 전부ON→RL 5sOFF→GL 10sOFF→BZ 15sOFF |
| 14 | **순차 점등+역순 소등 (자동)** | T0→T1→T2→T3→T4 | 5체인, 게이트 출력 |
| 15 | 시프트 | T0→T1 | RL→GL→BZ 교대 |
| 16 | 교번 | T0→T1 | RL↔GL 교대 + T1→RL 복귀 |
| **17** | **순차 점등+역순 소등 (PB2 트리거)** | M0→T0→T1, M1→T2→T3 | **2세트 체인, ANI T3로 리셋** |
| 18 | 순환 | T0→T1→T2→T0 | T2(NC)→T0 피드백 |
| 19 | 복합 블링크 | T0-T4 다중 | 각 출력 다른 ON/OFF 주기 |
| 20 | 교번 블링크 | T0→T1→T2 순환 | GL 2sOFF-3sON, BZ 3sON-3sOFF |

---

## Important Gotchas
- FastMCP 3.0.2: use `instructions` param, not `description`
- Self-hold relay must be timer source in sequential (not output Y)
- pywinauto `child_window()` on `main.children()` UIAWrapper → use `main.child_window()` instead
- Menu `found_index=0` needed when multiple "Edit" menus exist
- E2E tests using default "gxw" format crash pywinauto UIA when GX Works2 not running; use output_format="csv" in tests
- **체인 타이머 vs 누적 타이머 혼동 주의!** 교과서는 체인이 기본
- **M1(정지 릴레이)의 자기유지 해제는 반드시 ANI T_last** (AND M0 아님!)
- **RL 출력에도 ANI T_last 필요** (단순 LD M0 / OUT Y0 아님!)
