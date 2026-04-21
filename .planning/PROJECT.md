# tas — 변증법 오케스트레이션 플러그인

## What This Is

`tas`는 Claude Code 위에서 돌아가는 **정반합(thesis-antithesis-synthesis) 변증법 오케스트레이션 플러그인**이다. 같은 문제를 Thesis(정)와 Antithesis(반) 두 에이전트가 서로 다른 관점에서 검토하며 수렴할 때까지 핑퐁하고, 그 과정을 Python 엔진이 결정론적으로 지휘해 단일 에이전트가 놓치는 결함을 구조적으로 드러낸다. 사용자는 "엄격한 품질 게이트를 가진 리뷰/구현 루프"를 원하는 Claude Code 사용 개발자.

## Core Value

**변증법적 품질 게이트** — 단일 에이전트 한 세션이 감지하지 못하는 결함(의미적·행위적·합성 무결성·값 흐름)을 두 관점의 구조적 반복 대화로 노출시키는 것. 다른 모든 기능이 실패해도 이 한 가지는 작동해야 한다.

## Requirements

### Validated

<!-- 기존 코드베이스에서 실제로 동작 중이며 tas의 정체성 일부 -->

- ✓ 4계층 컨텍스트 격리 아키텍처 — SKILL → MetaAgent(Agent 서브) → dialectic.py(subprocess) → Thesis/Antithesis(SDK session) — `existing`
- ✓ Python 결정론적 PingPong 루프 — thesis→antithesis 순서 구조적 강제 — `existing`
- ✓ 4단 표준 스텝(`기획` / `구현` / `검증` / `테스트`) + 복잡도 기반 스텝 선택 — `existing`
- ✓ 표준/역전 convergence 모델 — ACCEPT vs PASS/FAIL 판정 파싱 — `existing`
- ✓ 다중 이터레이션 + `lessons.md` append-only + focus_angle 로테이션 — `existing`
- ✓ 탈선 감지 HALT — rate-limit, degeneration, unparseable verdict — `existing`
- ✓ SDK 호출 600s timeout + CLI death 1회 reconnect — `existing`
- ✓ Attestation — `engine_invocations`, 스텝 디렉터리 필수 아티팩트 존재 검사 — `existing`
- ✓ Stop 훅 가드 — REQUEST 있고 DELIVERABLE 없으면 세션 종료 차단 — `existing`
- ✓ 동반 슬래시 명령 — `/tas-review`, `/tas-verify`, `/tas-explain`, `/tas-workspace` — `existing`
- ✓ 2계층 Hang Watchdog — Layer A (`asyncio.timeout` + heartbeat.txt) + Layer B (`timeout(1)` bash 래퍼, 2단 SIGTERM/SIGKILL) — `Validated in Phase 3 (2-Layer Hang Watchdog, 2026-04-21)`
- ✓ Scenario B Engine Invocation Topology — MetaAgent `nohup bash run-dialectic.sh ... & echo $!` fire-and-forget spawn + EXIT trap atomic markers (`engine.done` / `engine.exit`) + MetaAgent-owned 19×30s chunked polling 루프 (Claude Code harness subagent orphan reap 구조적 제거) — `Validated in Phase 3.1 (Engine Invocation Topology Refactor, 2026-04-21)`
- ✓ `halt_reason` enum freeze — `sdk_session_hang` / `step_transition_hang` / `bash_wrapper_kill` / `engine_crash` 4종 고정, Phase 3.1 에서 신규 enum 금지 원칙 SKILL.md Phase 0b 에 선언 — `Validated in Phase 3.1`
- ✓ `/tas-verify` Canary 스위트 — Canary #4 (Phase 2 info-hiding) + #5 (Layer A stdout-stall) + #6 (Layer B step-transition hang) + #7 (subagent orphan survival + run-dialectic.sh real-chain integration via sed-copy mock injection) — `Validated in Phase 3 + 3.1`

### Active

<!-- M1 — 실행 안정성 + 컨텍스트 효율성 + 프롬프트 군살제거 -->

**테마 A — 선택적 Resume**
- [ ] 스텝 경계 체크포인트 영속화 (진행 중이던 스텝까지 완료 여부 기록)
- [ ] dialectic.py 내부 SDK 세션 행그 감지 강화 (기존 600s timeout으로 놓치는 패턴 규명·차단)
- [ ] MetaAgent Execute Mode 스텝 전환 watchdog (계층간 행그 감지)
- [ ] `/tas --resume` 명령 — 가장 최근 워크스페이스의 진행 중이던 스텝부터 이어서 실행

**테마 B — 구현 세션 분해**
- [ ] MetaAgent Classify 단계에서 구현 작업 규모 추정 + chunk 분해 필요성 판단
- [ ] chunk별 독립 dialectic 세션 + git worktree 격리 (컨텍스트 포화 예방)
- [ ] chunk 결과물 머지 로직 (순차 릴레이: chunk_N의 deliverable을 chunk_N+1 컨텍스트로 전달)
- [ ] `verify`/`test` 스텝은 머지된 통합 결과물에 대해 단일 dialectic로 교차 검증

**테마 C — 프롬프트 군살제거**
- [ ] `meta.md` 토큰 예산 초과(>5,500 토큰 임계) 해소 — 섹션 분리·참조화
- [ ] `SKILL.md` / `agents/*` / `references/*` 프롬프트 중복·과잉 지시 정리

**공통 — 원칙 정합성**
- [ ] `CLAUDE.md`의 "resume/pipeline 추가 금지" 조항 폐기 및 새 원칙으로 갱신

### Out of Scope

- **자동 resume 데몬(파이프라인)** — `--resume`은 사용자가 명시할 때만. 무한 자동 재시작은 통제권 침해 + 실패 루프 위험
- **클라우드 영속화(S3/DB)** — 로컬 `_workspace/` 파일 기반으로 충분. 외부 의존성·프라이버시 비용 대비 효용 낮음
- **chunk 병렬 실행** — M1에서는 worktree 격리 + 순차 릴레이만. 동시 실행은 레이스·머지 복잡성 유발 → 후속 마일스톤에서 재검토
- **네이티브 UI/대쉬보드** — CLI 피드백 루프로 충분. 진행 상황은 워크스페이스 파일 갱신 + stderr 로그로 관찰

## Context

- **플러그인 구조**: 코드의 대부분은 Markdown 프롬프트 — 다른 Claude 인스턴스가 실행하는 지시문. Python은 dialectic 엔진(`skills/tas/runtime/dialectic.py`, ~830줄) 단 하나.
- **배포 방식**: 로컬 클론 + `--plugin-dir` 설치. 공개 마켓플레이스 배포는 하지 않음.
- **이전 사이클**: `tas/enhancement-20260414` 브랜치에서 UX 마찰 5개 중 3개 해결 → main 머지 완료. 남은 프롬프트 리팩토링이 M1 테마 C로 승계됨.
- **실측 행그 사례**: `ait_shooting` 프로젝트에서 기획 스텝 round-1-antithesis가 REFINE 응답 후 thesis 재응답이 시작조차 안 됨(10분+ 무반응). dialectic.py의 600s timeout을 넘긴 것으로 보여 **행그 위치가 dialectic.py 외부(상위 계층 또는 SDK 레이어)** 일 가능성이 높음. 원인 규명이 A1의 선행 과제.
- **User pain**: "그냥 돌다가 멈춥니다" — 에러가 아니라 무반응. 사용자 입장에선 언제 Ctrl-C를 쳐야 할지 판단 어려움.
- **컨텍스트 포화**: thesis/antithesis는 현재 각자 하나의 stateful SDK 세션으로 구현을 수행. 큰 작업에서 컨텍스트 창이 포화되며 품질이 급락하거나 응답이 끊김.

## Constraints

- **Runtime**: Python 3.10+ (PEP 604 `X | None` 사용), `claude-agent-sdk>=0.1.50`, Claude Code ≥2.x, bash, git
- **정보 은닉**: SKILL.md은 MetaAgent 내부(thesis/antithesis 역할/리뷰 렌즈/convergence)를 참조하지 않는다. 4계층 경계 무결성 유지 필수
- **턴 순서 구조화**: thesis→antithesis 순서는 Python `while True:` 루프로만 강제. 프롬프트 지시로 재현 금지(회귀 방지)
- **파일 경계**: 스텝/이터레이션 간 상태는 명시 파일(`deliverable.md`, `lessons.md`, 체크포인트 파일)로만 전달. 인메모리 크로스바운더리 공유 금지
- **범위 금지**: MainOrchestrator는 프로젝트 소스 코드를 읽지 않는다. Trivial Gate는 요청 텍스트만으로 판단
- **배포**: `--plugin-dir` 로컬 설치. 공개 레지스트리·자동 업데이트 메커니즘 없음

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| 선택적 `--resume` opt-in (자동 파이프라인 아님) | 사용자 통제권 유지 + quick-only 정체성과의 타협 | — Pending |
| Resume 입자리 = 스텝 경계 | 라운드 경계는 구현 복잡도 상·손실 허용 범위, 이터레이션 경계는 복구 효율 낮음 | — Pending |
| 2계층 행그 감지 (dialectic.py + MetaAgent) | 단일 계층 감지로는 실제 행그 위치 포괄 불가 (ait_shooting 사례 증거) | — Pending |
| 구현 chunk: worktree 격리 + 순차 릴레이 | 병렬 대비 단순하며 컨텍스트 포화 방지 목적에 충분 | — Pending |
| `verify`/`test`: 통합 dialectic | 머지 후 결과물에 대한 교차 검증이 chunk별 검증보다 실질 결함 포착에 효과적 | — Pending |
| `CLAUDE.md` "resume 금지" 조항 폐기 | 이 마일스톤의 전제 — 원칙 자체가 바뀌는 것을 문서로 반영 | — Pending |

## Evolution

이 문서는 페이즈 전환과 마일스톤 경계에서 진화한다.

**페이즈 전환마다** (`/gsd-transition` 시):
1. 무효화된 요구사항? → Out of Scope로 이동 (이유 기록)
2. 검증된 요구사항? → Validated로 이동 (페이즈 참조)
3. 새로 드러난 요구사항? → Active에 추가
4. 기록할 결정? → Key Decisions에 추가
5. "What This Is"가 여전히 정확한가? → 드리프트 시 업데이트

**마일스톤 종료마다** (`/gsd-complete-milestone` 시):
1. 전체 섹션 리뷰
2. Core Value 재확인 — 여전히 올바른 우선순위인가?
3. Out of Scope 감사 — 이유가 여전히 유효한가?
4. Context 업데이트 — 현재 상태(사용자/피드백/지표) 반영

---
*Last updated: 2026-04-21 after Phase 3.1 (Engine Invocation Topology Refactor) completion — Scenario B topology live, 7/7 plans, VERIFICATION 6/7 passed + TOPO-06 `/tas` e2e smoke awaits human UAT*
