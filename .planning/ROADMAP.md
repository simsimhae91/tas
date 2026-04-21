# Roadmap: tas — M1 (TAS-M1)

## Overview

TAS-M1은 기존 4계층 변증법 오케스트레이션 아키텍처 위에 **실행 안정성 · 컨텍스트 효율성 · 프롬프트 군살제거**를 추가한다. Phase 1이 체크포인트 인프라를 세우면 Phase 2(Resume)와 Phase 3(2계층 Watchdog)는 병행 가능하고, Phase 4(Chunk 분해)가 컨텍스트 포화를 해소한 뒤 Phase 5(Prompt Slim)가 독립 PR로 마무리한다. Phase 3+4 조합이 PROJECT.md 최상위 성공 기준인 "Hang 사례 제로수렴"의 달성 경로다. 전 구간이 stdlib + git + bash만 사용하며 `requirements.txt`에 한 줄도 추가되지 않는다.

**마일스톤**: TAS-M1
**Granularity**: standard (5 phases)
**배포 모델**: `--plugin-dir` 로컬 설치, 공개 레지스트리 없음

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

- [ ] **Phase 1: Checkpoint Foundation** - 스텝 경계 체크포인트 + `plan.json` 영속화 + CLAUDE.md "resume 금지" 조항 교체 + schema 회귀 테스트
- [ ] **Phase 2: Resume Entry** - `/tas --resume` 진입 Gate + MetaAgent Execute의 RESUME_FROM 스킵 + info hiding 보존
- [x] **Phase 3: 2-Layer Hang Watchdog** - `asyncio.timeout` 전환 + heartbeat.txt + Bash `timeout(1)` 래퍼 + halt_reason 확장 (Layer A/B canary 2종 포함)
- [ ] **Phase 3.1: Engine Invocation Topology Refactor (INSERTED)** - subagent `nohup + &` fire-and-forget + SKILL.md 폴링 루프 + EXIT trap atomic markers (Canary #7 포함)
- [ ] **Phase 4: Chunk Decomposition** - Classify chunk sizing + worktree 격리 순차 릴레이 + cherry-pick 머지 + 통합 verify (2-chunk canary 포함)
- [ ] **Phase 5: Prompt Slim** - `meta.md` 분리 + 중복 지시 정리 + 토큰 측정 스크립트 + behavioral-diff 3 canary

## Phase Details

### Phase 1: Checkpoint Foundation
**Goal**: 모든 후속 기능이 의존할 crash-safe 체크포인트 인프라와 `plan.json` 영속화를 구축한다
**Depends on**: Nothing (first phase)
**Requirements**: CHKPT-01, CHKPT-02, CHKPT-03, CHKPT-04, CHKPT-05, VERIFY-02
**Success Criteria** (what must be TRUE):
  1. 임의 스텝 완료 직후 `_workspace/quick/{ts}/checkpoint.json`이 atomic write로 존재하며 `schema_version`, `current_step`, `completed_steps[]`, `status`, `updated_at` 필드를 포함한다
  2. Classify 승인 시점에 `_workspace/quick/{ts}/plan.json`이 영속화되고 이후 run 내내 mtime이 바뀌지 않는다
  3. `references/workspace-convention.md`에 Checkpoint Schema 섹션이 추가되고 디렉터리 다이어그램에 `checkpoint.json`/`plan.json`이 반영되어 있다
  4. `CLAUDE.md`의 "Adding resume/pipeline mechanisms or hardcoding loop_count" 조항이 단순 삭제가 아닌 "manual `/tas --resume`만 허용, auto-retry/daemon 여전히 금지"로 명시 교체되어 있다
  5. `python3 dialectic.py --self-test`가 `checkpoint.json` 스키마 회귀 테스트를 포함해 성공한다
**Plans**: 2 plans
- [x] 01-01-PLAN.md — runtime/checkpoint.py 신설 + dialectic.py --self-test 5번째 블록 (CHKPT-01, CHKPT-02, VERIFY-02)
- [x] 01-02-PLAN.md — meta.md Execute Phase 1 Initialize + step 9.5 + workspace-convention.md + CLAUDE.md line 127 교체 (CHKPT-01, CHKPT-03, CHKPT-04, CHKPT-05)

### Phase 2: Resume Entry
**Goal**: 사용자가 `/tas --resume`으로 진행 중이던 스텝부터 이어서 실행할 수 있고, 이 과정에서 SKILL.md는 체크포인트만 읽어 info hiding을 보존한다
**Depends on**: Phase 1
**Requirements**: RESUME-01, RESUME-02, RESUME-03, RESUME-04, RESUME-05
**Success Criteria** (what must be TRUE):
  1. 사용자가 `/tas --resume`을 호출하면 가장 최근 워크스페이스의 `checkpoint.json`이 감지되고 "Iteration N / Step M 완료. 다음: Step M+1. 계속할까요?" 요약과 함께 y/n 확인 프롬프트가 표시된다
  2. Resume 경로에서 SKILL.md가 `checkpoint.json` / `plan.json` / `REQUEST.md` 외의 파일(dialogue.md, round-*.md, deliverable.md, lessons.md)을 Read하지 않는다 (grep 회귀 테스트 0 matches)
  3. MetaAgent Execute Mode가 `MODE: resume` + `RESUME_FROM: step_N` 파라미터를 받아 `completed_steps[]`에 포함된 스텝을 재실행 없이 skip하고, 기존 `deliverable.md`가 그대로 신뢰원으로 재주입된다
  4. Resume 시 Classify Mode Agent() 호출은 발생하지 않고 `plan.json`이 그대로 소비된다 (Phase 0b의 Agent() 호출 횟수 == 1)
  5. 체크포인트 손상 · plan 부재 · worktree 소실 시 명확한 halt_reason과 "`/tas`로 새로 시작하거나 `/tas-workspace`로 정리" 수준의 사용자 복구 가이드가 표시된다

**Plans**: 2 plans
- [x] 02-01-PLAN.md — SKILL.md Phase 0b Resume Gate + Phase 3 halt_reason 테이블 확장 × 7 (RESUME-01, RESUME-02 Layer 1, RESUME-04, RESUME-05)
- [x] 02-02-PLAN.md — meta.md MODE:resume branch + CLAUDE.md Common Mistakes bullet + tas-verify Canary #4 + Wave 0 harnesses (RESUME-02 Layer 2/3, RESUME-03, RESUME-04)

### Phase 3: 2-Layer Hang Watchdog
**Goal**: SDK 세션 내부 hang과 상위 계층 stdout-stall hang을 각각 다른 계층에서 감지해 "그냥 돌다가 멈추는" 사례를 halt_reason과 함께 복구 가능한 상태로 전환한다
**Depends on**: Phase 1
**Requirements**: WATCH-01, WATCH-02, WATCH-03, WATCH-04, WATCH-05, VERIFY-01 (canaries a + b)
**Success Criteria** (what must be TRUE):
  1. `dialectic.py`의 SDK 호출부가 `asyncio.timeout()` 컨텍스트 매니저로 동작하고 (Python 3.10 환경에서는 `wait_for` fallback), TimeoutError가 stdout 마지막 라인 JSON `{"status":"halted","halt_reason":"sdk_session_hang",...}`로 반드시 emit된다
  2. 매 라운드 경계에 `{LOG_DIR}/heartbeat.txt`가 `{timestamp, round_n, speaker}` 4필드 스키마로 atomic write되며 대화 본문은 섞이지 않는다
  3. `run-dialectic.sh`가 `timeout --kill-after=30s` 2단 kill로 `dialectic.py`를 래핑하고, macOS에서 `timeout`/`gtimeout` 둘 다 없으면 stderr 경고 후 Layer A만 활성 상태로 graceful degrade한다
  4. MetaAgent Execute Mode가 각 스텝 Agent() 호출에 timeout을 명시하고, 상위 계층 hang 발생 시 `halt_reason: step_transition_hang` + `last_heartbeat` 정보가 HALT JSON에 포함된다
  5. SKILL.md Phase 3 halt_reason 테이블에 `sdk_session_hang` / `step_transition_hang` / `bash_wrapper_kill` 3종과 각 복구 가이드가 기재되어 있으며, VERIFY-01 canary (a) mock SDK stdout-stall Layer A 트립 + (b) step-transition hang Layer B 트립 2개가 `/tas-verify`에서 PASS한다
**Plans**: 7 plans
- [x] 03-01-PLAN.md — Wave 0 scaffolding: tests/ dir + 3 canary stubs (VERIFY-01 a/b)
- [x] 03-02-PLAN.md — Layer A transition: _sdk_timeout helper + query_and_collect swap (WATCH-01)
- [x] 03-03-PLAN.md — heartbeat helpers + 8 call-sites + state trackers (WATCH-02)
- [x] 03-04-PLAN.md — _build_halt_payload + outer try/except/finally + halted JSON emit (WATCH-01 defense)
- [x] 03-05-PLAN.md — run-dialectic.sh Layer B wrapper + graceful degrade + macOS human-verify (WATCH-03)
- [x] 03-06-PLAN.md — meta.md step 7/8 classification reference + Within-Iter halt_reason enum (WATCH-04)
- [x] 03-07-PLAN.md — SKILL.md tables + engine-invocation-protocol.md rows + ARCHITECTURE.md snapshot + canary wiring (WATCH-05, VERIFY-01 a+b)

### Phase 03.1: Engine invocation topology refactor (INSERTED)

**Goal:** MetaAgent 서브에이전트가 `nohup bash run-dialectic.sh ... & echo $!` fire-and-forget 으로 엔진을 기동하고, `run-dialectic.sh` EXIT trap 이 `engine.done` + `engine.exit` atomic marker 를 생성하며, SKILL.md Phase 2 가 `test -f engine.done || ! kill -0 $PID` 폴링 루프로 완료를 관측해 Claude Code harness 의 subagent orphan reap 으로 인한 dialectic 조기 종료를 구조적으로 제거한다. Canary #7 (subagent orphan survival 자동화) 추가로 회귀 방지. 신규 halt_reason enum 금지 · 4계층 info hiding 보존 · stdlib-only.
**Requirements**: TOPO-01, TOPO-02, TOPO-03, TOPO-04, TOPO-05, TOPO-06, VERIFY-TOPO-01
**Depends on:** Phase 3
**Plans:** 7 plans

Plans:
- [x] 03.1-01-PLAN.md — Wave 0 scaffolding: REQUIREMENTS.md §C.1 TOPO family + 3 test stubs + canaries.md Canary #7 placeholder (TOPO-01..06, VERIFY-TOPO-01)
- [ ] 03.1-02-PLAN.md — run-dialectic.sh EXIT trap (atomic engine.done + engine.exit markers) + test_exit_trap.sh 4-case unit test (TOPO-01)
- [ ] 03.1-03-PLAN.md — engine-invocation-protocol.md 전면 rewrite (task-notification → file-marker polling 계약) (TOPO-04)
- [ ] 03.1-04-PLAN.md — meta.md Execute Phase 2d step 7-8 rewrite (nohup spawn + 5-field return JSON) (TOPO-02)
- [ ] 03.1-05-PLAN.md — SKILL.md Phase 2.5 polling loop + halt_reason enum freeze + info-hiding 9-match baseline 유지 (TOPO-03, TOPO-05)
- [ ] 03.1-06-PLAN.md — Canary #7 실제 구현 (simulate_subagent_orphan.py mock orphan harness + canaries.md 등록) (VERIFY-TOPO-01)
- [ ] 03.1-07-PLAN.md — CLAUDE.md Common Mistakes update + Phase 3.1 전체 회귀 최종 검증 (info-hiding + enum freeze + canary suite) (TOPO-06)

### Phase 4: Chunk Decomposition
**Goal**: Classify 단계에서 구현 규모를 판단해 chunk로 쪼개고, worktree 격리된 독립 dialectic을 순차 릴레이로 실행한 뒤 통합 verify로 합성 경계 결함까지 잡는다 (컨텍스트 포화 방지 + 값 흐름 무결성)
**Depends on**: Phase 1, Phase 2
**Requirements**: CHUNK-01, CHUNK-02, CHUNK-03, CHUNK-04, CHUNK-05, CHUNK-06, CHUNK-07, VERIFY-01 (canary c)
**Success Criteria** (what must be TRUE):
  1. MetaAgent Classify Phase 2c가 구현 작업 규모를 판단해 `plan.json`의 `implementation_chunks[]`에 각 chunk의 `id` / `scope` / `pass_criteria` / `dependencies_from_prev_chunks`를 기록하고, 수직 레이어 중심의 분해 근거가 사용자 approve 화면에 표시된다
  2. Chunk sub-loop가 `${WORKSPACE}/chunks/chunk-{c}/` 경로의 git worktree(`--detach`, 절대경로)에서 각 chunk를 독립 dialectic으로 실행하고, chunk_N의 deliverable 요약이 구조화 템플릿으로 chunk_N+1의 `step_context`에 전달된다 (전문 append 금지 · 상한 존재)
  3. 모든 chunk 완료 후 cherry-pick 머지가 성공하고 (conflict 시 `git apply` fallback, 둘 다 실패 시 HALT + 사용자 가이드), `verify` / `test` 스텝은 머지된 통합 결과물에 대해 **단일 dialectic**로 실행된다 (chunk별 verify 금지)
  4. 정상 · HALT · Ctrl-C 어느 경로로 끝나도 `${WORKSPACE}/chunks/` 와 `.git/worktrees/` 엔트리가 orphan으로 남지 않는다 (sub-loop 진입 전 `git worktree prune` 수행 + 종료 시 remove, `/tas-workspace clean` 레시피 제공)
  5. VERIFY-01 canary (c) "2-chunk 시나리오 머지 + 통합 verify 성공" 및 chunk 1 의도적 regression 심어 integrated verify가 이를 FAIL로 감지하는 하위 테스트가 `/tas-verify`에서 PASS한다
**Plans**: TBD

### Phase 5: Prompt Slim
**Goal**: `meta.md`를 5,500 토큰 임계 아래(목표 4,500)로 줄이되 behavioral-diff 3 canary로 동일한 plan/verdict가 나옴을 보장한다 (독립 PR)
**Depends on**: Phase 1, Phase 2, Phase 3, Phase 4
**Requirements**: SLIM-01, SLIM-02, SLIM-03, SLIM-04
**Success Criteria** (what must be TRUE):
  1. `scripts/measure-prompt-tokens.py`가 Anthropic `count_tokens` API를 사용해 프롬프트 파일 토큰 수를 출력하고, `requirements.txt`와 `.claude-plugin/*.json` 런타임 의존성에 `anthropic` 패키지가 추가되지 않는다 (dev-only 격리)
  2. `meta.md`가 `references/meta-classify.md` + `references/meta-execute.md`로 분리되어 측정 토큰 수가 5,500 이하이며, 각 references 파일이 해당 Phase 시작 첫 actionable step에서 `Read(...)`로 강제 로드된다 (MetaAgent final JSON `references_read` 필드로 attestation)
  3. 동일한 load-bearing 규칙(engine_invocations 스키마, convergence verdict, attestation 필드)이 `meta.md`와 `references/meta-*.md`에 동시 등장하지 않는다 (`/tas-verify` grep lint 1 파일만 매치)
  4. SLIM-04 behavioral-diff 3 canary — trivial classify / chunked classify / full execute — 가 prompt slim 전후로 동일한 plan 구조와 verdict를 생성해 `/tas-verify`에서 PASS한다
  5. `SKILL.md` / `agents/thesis.md` / `agents/antithesis.md` / `references/*`에서 중복·과잉 지시가 제거되어 동일 규칙의 출처가 단일 파일로 확정되어 있다
**Plans**: TBD

## Progress

**Execution Order:**
Phase 1 → (Phase 2 ∥ Phase 3 병행 가능) → Phase 3.1 (Phase 3 완료 후 urgent 삽입) → Phase 4 → Phase 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Checkpoint Foundation | 0/TBD | Not started | - |
| 2. Resume Entry | 0/TBD | Not started | - |
| 3. 2-Layer Hang Watchdog | 7/7 | Complete | 2026-04-21 |
| 3.1 Engine Invocation Topology Refactor | 1/7 | In progress | - |
| 4. Chunk Decomposition | 0/TBD | Not started | - |
| 5. Prompt Slim | 0/TBD | Not started | - |
