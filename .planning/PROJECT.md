# tas — 변증법 오케스트레이션 플러그인

## What This Is

`tas`는 Claude Code 위에서 돌아가는 **정반합(thesis-antithesis-synthesis) 변증법 오케스트레이션 플러그인**이다. 같은 문제를 Thesis(정)와 Antithesis(반) 두 에이전트가 서로 다른 관점에서 검토하며 수렴할 때까지 핑퐁하고, 그 과정을 Python 엔진이 결정론적으로 지휘해 단일 에이전트가 놓치는 결함을 구조적으로 드러낸다. 사용자는 "엄격한 품질 게이트를 가진 리뷰/구현 루프"를 원하는 Claude Code 사용 개발자.

## Core Value

**변증법적 품질 게이트** — 단일 에이전트 한 세션이 감지하지 못하는 결함(의미적·행위적·합성 무결성·값 흐름)을 두 관점의 구조적 반복 대화로 노출시키는 것. 다른 모든 기능이 실패해도 이 한 가지는 작동해야 한다.

## Current Milestone: v1.1 Session Isolation & Commit Granularity

**Goal:** `/tas` 실행을 사용자 브랜치·작업 트리와 완전히 분리된 **리뷰 가능한 세션 브랜치**로 옮기고, 각 iteration의 step 단위 진행을 **atomic git 히스토리**로 남긴다.

**Target features:**
- 세션 worktree 격리 — `~/.cache/tas-sessions/{ts}/<project>/` 경로에 named branch `tas/session-{ts}` 자동 생성·관리·정리
- Session index — cold-resume chicken-and-egg 해결을 위한 `~/.cache/tas-sessions/LATEST` symlink
- Step-level atomic 커밋 — 각 ACCEPT step 수렴 시점 커밋, empty-diff skip, `pre_commit_hook_failed` 신규 halt_reason
- Manual merge UX — run 종료 시 `git merge tas/session-{ts}` 제안 텍스트 출력 (auto-merge 없음)
- Companion command 경로 재조정 — `/tas-explain`·`/tas-workspace`·`/tas-review`가 session index 기반으로 workspace 조회
- CLAUDE.md 신규 불변량 3종 — top-level worktree 경로 규칙, chunk cherry-pick target 재정의, pre-commit hook 정책

**Key context:**
- M1 Phase 3.1 watchdog/hang enum freeze 존중 — 신규 halt_reason은 merge/pre-commit 직교 도메인 한정 (Phase 4 `chunk_merge_conflict` 선례 적용)
- 4-layer info hiding 보존 — SKILL.md는 여전히 agent 내부 읽지 않음
- 2 phases: Phase 6 (Session Worktree Isolation) + Phase 7 (Step-Level Commit Granularity, Phase 6에 의존)
- Canary 확장 — 신규 Canary #9 (2-level worktree: session + chunk), 기존 Canary #8이 session worktree 위에서도 PASS 유지

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
- ✓ `/tas-verify` Canary 스위트 — Canary #4 (Phase 2 info-hiding) + #5 (Layer A stdout-stall) + #6 (Layer B step-transition hang) + #7 (subagent orphan survival + run-dialectic.sh real-chain integration via sed-copy mock injection) + #8 (2-chunk 머지 + 통합 verify + chunk 1 regression 감지) — `Validated in Phase 3 + 3.1 + 4`
- ✓ Chunk Decomposition — MetaAgent Classify Phase 2c가 복잡도 + 수직 레이어 heuristic으로 `implementation_chunks[]` (6-field schema, cap 5) 분해 판단 → Execute Phase 2d.5 Chunk Sub-loop이 `${WORKSPACE}/chunks/chunk-{N}/` 절대경로 worktree에서 각 chunk를 Scenario B 프로토콜로 독립 dialectic 실행 → MetaAgent-owned 5KB 구조화 summary로 순차 릴레이 → 각 chunk 완료 후 MetaAgent가 commit + cherry-pick 머지 (실패 시 `git apply --index --binary` fallback, 둘 다 실패 시 `chunk_merge_conflict` HALT + `git reset --hard PRE_MERGE_SHA` + `git clean -fd`) → 머지된 통합 상태에서 `검증`/`테스트` 단일 dialectic (Synthesis Context 4 focus items 주입). Canary #8 2-Phase (fast 30s / full 300s) PASS. 신규 halt_reason 2종 (`chunk_merge_conflict` + `worktree_backlog`) 은 Phase 3.1 watchdog/hang enum freeze와 orthogonal 도메인 예외. `checkpoint.py` / `dialectic.py` / `run-dialectic.sh` / thesis.md / antithesis.md 무변경 — Phase 1 D-03 예약 slot (`current_chunk` / `completed_chunks[]` / `implementation_chunks`) 그대로 수용 — `Validated in Phase 4 (Chunk Decomposition, 2026-04-22)`

### Active

<!-- M2 v1.1 — 세션 격리 & 커밋 단위 -->

**테마 D — 세션 격리 & 커밋 단위 (M2 v1.1)**
- [ ] `/tas` 진입 시 `~/.cache/tas-sessions/{ts}/<project>/` 경로에 named branch `tas/session-{ts}` worktree 자동 생성 (Phase 6)
- [ ] Session index (`~/.cache/tas-sessions/LATEST` symlink) + `/tas --resume`의 cold-resume 경로 재조정 (Phase 6)
- [ ] `/tas-explain`·`/tas-workspace`·`/tas-review`가 session index 기반으로 workspace 조회 (Phase 6)
- [ ] Chunk cherry-pick target을 session worktree HEAD로 재정의 (Phase 6, 기존 Phase 4 로직 재조정)
- [ ] Step 수렴 시점 atomic commit + empty-diff skip + trailer 메타데이터 (Phase 7)
- [ ] Manual merge 커맨드 출력 (auto-merge 없음) — PASS 종료 시 `git merge tas/session-{ts}` 제안 (Phase 7)
- [ ] `pre_commit_hook_failed` 신규 halt_reason (Phase 7, merge/pre-commit 직교 도메인)
- [ ] CLAUDE.md 신규 불변량 3종 — top-level worktree 경로, chunk target 재정의, pre-commit 정책 (Phase 7 마무리)
- [ ] Canary #9 (2-level worktree: session + chunk) + 기존 Canary #8이 session worktree 위에서 PASS (Phase 7)

<!-- M1 완결 요약 (2026-04-07 ~ 2026-04-22) — 상세 불변량은 Validated 목록 및 CLAUDE.md Common Mistakes 참조 -->

**테마 A — 선택적 Resume** ✓ (Phase 1+2 완료 2026-04-16)
- [x] 스텝 경계 체크포인트 영속화 (`checkpoint.json` atomic write + schema v1.0)
- [x] dialectic.py SDK 세션 hang 감지 강화 (`asyncio.timeout` + heartbeat.txt, Phase 3 Layer A)
- [x] MetaAgent Execute Mode 스텝 전환 watchdog (Phase 3 Layer B `timeout(1)` bash 래퍼 + 2단 kill)
- [x] `/tas --resume` 명령 (Phase 2, info-hiding 보존 + Canary #4)

**테마 B — 구현 세션 분해** ✓ (Phase 4 완료 2026-04-22)
- [x] MetaAgent Classify 단계에서 구현 작업 규모 추정 + chunk 분해 필요성 판단 (수직 레이어 heuristic, cap 5)
- [x] chunk별 독립 dialectic 세션 + git worktree 격리 (`${WORKSPACE}/chunks/chunk-{N}/` 절대경로 + prune-on-entry + remove-on-exit)
- [x] chunk 결과물 머지 로직 (구조화 5KB summary 순차 릴레이 + MetaAgent commit + cherry-pick → git apply fallback → `chunk_merge_conflict` HALT)
- [x] `verify`/`test` 스텝은 머지된 통합 결과물에 대해 단일 dialectic로 교차 검증 (Synthesis Context 4 focus items)

**테마 C — 프롬프트 군살제거** ✓ (Phase 5 완료 2026-04-22)
- [x] `meta.md` 토큰 예산 초과(>5,500 토큰 임계) 해소 — Classify/Execute 모드별 references/ 분리 + SSOT-1/2/3 lint
- [x] `SKILL.md` / `agents/*` / `references/*` 프롬프트 중복·과잉 지시 정리 (Canary #9 behavioral-diff 3건 PASS)

**공통 — 원칙 정합성** ✓ (Phase 1 Plan 02 완료 2026-04-13)
- [x] `CLAUDE.md`의 "resume/pipeline 추가 금지" 조항을 "manual `/tas --resume`만 허용, auto-retry/daemon 여전히 금지"로 교체

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
| 선택적 `--resume` opt-in (자동 파이프라인 아님) | 사용자 통제권 유지 + quick-only 정체성과의 타협 | ✓ Phase 2 |
| Resume 입자리 = 스텝 경계 | 라운드 경계는 구현 복잡도 상·손실 허용 범위, 이터레이션 경계는 복구 효율 낮음 | ✓ Phase 1+2 |
| 2계층 행그 감지 (dialectic.py + MetaAgent) | 단일 계층 감지로는 실제 행그 위치 포괄 불가 (ait_shooting 사례 증거) | ✓ Phase 3 |
| 구현 chunk: worktree 격리 + 순차 릴레이 | 병렬 대비 단순하며 컨텍스트 포화 방지 목적에 충분 | ✓ Phase 4 |
| `verify`/`test`: 통합 dialectic | 머지 후 결과물에 대한 교차 검증이 chunk별 검증보다 실질 결함 포착에 효과적 | ✓ Phase 4 |
| `CLAUDE.md` "resume 금지" 조항 폐기 | 이 마일스톤의 전제 — 원칙 자체가 바뀌는 것을 문서로 반영 | ✓ Phase 1 Plan 02 |
| **M2** 세션 worktree 위치 = `~/.cache/tas-sessions/{ts}/<project>/` | XDG-style cache로 프로젝트 tree 무오염, 일괄 정리 용이, `_workspace/` 격리 보존 | — Pending (Phase 6) |
| **M2** 세션 branch = named `tas/session-{ts}` (detached 아님) | "reviewable PR" 정체성의 필수 조건 — detached로는 머지/리뷰 불가 | — Pending (Phase 6) |
| **M2** 머지 정책 = manual (PASS 시 커맨드만 출력) | "변증법 품질 게이트" 정체성 보존 — 자동 머지는 automation tool로의 정체성 drift | — Pending (Phase 7) |
| **M2** 커밋 granularity = step-level (iteration 아님) | user 명시 요구 + chunk pattern 일관성; empty-diff skip으로 기획/검증 step 소음 제거 | — Pending (Phase 7) |
| **M2** 신규 halt_reason = `pre_commit_hook_failed` (merge/hook 직교 도메인) | Phase 3.1 watchdog freeze 존중 — Phase 4 `chunk_merge_conflict` 선례 적용 | — Pending (Phase 7) |
| **M2** Chunk cherry-pick target = session worktree HEAD (main repo HEAD 아님) | 세션 격리의 핵심 — 사용자 main 브랜치 동시성 안전성 확보 | — Pending (Phase 6) |
| **M2** Cold-resume 경로 해결 = session index symlink (`~/.cache/tas-sessions/LATEST`) | `checkpoint.json`이 worktree 내부라 resume이 worktree 경로를 먼저 알아야 함 (chicken-and-egg) | — Pending (Phase 6) |

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
*Last updated: 2026-04-23 — Milestone v1.1 (Session Isolation & Commit Granularity) started. M1 (v1.0) 전체 5개 phase + Phase 3.1 INSERTED 포함 6/6 phase PASS (147 commits, 2026-04-07 ~ 2026-04-22). v1.1 목표: `/tas` 출력을 `~/.cache/tas-sessions/{ts}/<project>/` named branch worktree로 격리 + step 단위 atomic 커밋. 2 phase 구조 (Phase 6 Session Worktree Isolation + Phase 7 Step-Level Commit Granularity, 7→6 의존). 신규 halt_reason `pre_commit_hook_failed`는 Phase 3.1 watchdog freeze의 직교 도메인 예외 (Phase 4 `chunk_merge_conflict` 선례).*
