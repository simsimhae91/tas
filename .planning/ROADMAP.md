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
- [x] **Phase 3.1: Engine Invocation Topology Refactor (INSERTED)** - subagent `nohup + &` fire-and-forget + MetaAgent-owned polling (Scenario B) + EXIT trap atomic markers + Canary #7 2-Phase regression guard (orphan survival + real-chain integration via sed-copy mock injection)
- [x] **Phase 4: Chunk Decomposition** - Classify chunk sizing + worktree 격리 순차 릴레이 + cherry-pick 머지 + 통합 verify (2-chunk canary 포함)
- [x] **Phase 5: Prompt Slim** - `meta.md` 분리 + 중복 지시 정리 + 토큰 측정 스크립트 + behavioral-diff 3 canary

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
**Plans:** 7/7 plans complete

Plans:
- [x] 03.1-01-PLAN.md — Wave 0 scaffolding: REQUIREMENTS.md §C.1 TOPO family + 3 test stubs + canaries.md Canary #7 placeholder (TOPO-01..06, VERIFY-TOPO-01)
- [x] 03.1-02-PLAN.md — run-dialectic.sh EXIT trap (atomic engine.done + engine.exit markers) + test_exit_trap.sh 5-case unit+integration test (TOPO-01; Issue #1 fix: `exec` removed from Layer B)
- [x] 03.1-03-PLAN.md — engine-invocation-protocol.md 전면 rewrite (task-notification → file-marker polling 계약) (TOPO-04)
- [x] 03.1-04-PLAN.md — meta.md Execute Phase 2d step 7-8 rewrite (nohup spawn + Scenario B local polling & classify) (TOPO-02, TOPO-03)
- [x] 03.1-05-PLAN.md — SKILL.md Phase 0b halt_reason enum freeze bullet (Scenario B: no Phase 2.5 polling block added; info-hiding 9-match baseline preserved) (TOPO-05)
- [x] 03.1-06-PLAN.md — Canary #7 실제 구현 (simulate_subagent_orphan.py 2-Phase: orphan survival + real-chain integration via sed-copy mock injection) + canaries.md 등록 (VERIFY-TOPO-01)
- [x] 03.1-07-PLAN.md — CLAUDE.md Common Mistakes update + Phase 3.1 전체 회귀 최종 검증 (info-hiding + enum freeze + canary suite) (TOPO-06)

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
**Plans**: 7 plans

Plans:
- [x] 04-01-PLAN.md — Canary #8 Wave 0 scaffolding (PENDING stub + canaries.md placeholder) (VERIFY-01 c)
- [x] 04-02-PLAN.md — meta.md Classify Phase 2c Chunk Sizing + Phase 4 Output implementation_chunks (CHUNK-01, CHUNK-02)
- [x] 04-03-PLAN.md — SKILL.md Display Plan chunks UX + Handle User Response Adjust chunks row (CHUNK-02 UX)
- [x] 04-04-PLAN.md — meta.md Execute Phase 2d.5 Chunk Sub-loop + step 9.5 chunk payload + Within-Iter FAIL chunk branch (CHUNK-03, CHUNK-04, CHUNK-05, CHUNK-06, CHUNK-07)
- [x] 04-05-PLAN.md — meta.md Synthesis Context injection + SKILL.md halt_reason tables chunk_merge_conflict + worktree_backlog rows (CHUNK-06, CHUNK-05, CHUNK-07)
- [x] 04-06-PLAN.md — workspace-convention.md chunks/ + Chunk Merge Workflow + engine-invocation-protocol.md Sub-loop invocations + CLAUDE.md 2 Phase 4 bullets (CHUNK-03, CHUNK-04, CHUNK-05, CHUNK-06, CHUNK-07)
- [x] 04-07-PLAN.md — Canary #8 full 2-Phase implementation + canaries.md contract + 14-invariant regression suite (VERIFY-01 c)

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
**Plans**: 6 plans
- [x] 05-01-PLAN.md — Wave 0 scaffolding: scripts/ + measure-prompt-tokens.py skeleton + Canary #9 PENDING stub + canaries.md placeholders + fixtures/ dir (SLIM-01, SLIM-04)
- [x] 05-02-PLAN.md — Wave 1: pre-slim Canary #9 baselines committed BEFORE split + meta.md split → references/meta-{classify,execute}.md + developer token measurement checkpoint (SLIM-02, SLIM-04)
- [x] 05-03-PLAN.md — Wave 2: Mode-bound Reference Load + Final JSON Contract SSOT in meta.md + references_read attestation first-step in meta-{classify,execute}.md + SKILL.md Phase 3 extension + SCOPE dedup 3→≤2 (SLIM-02, SLIM-03)
- [x] 05-04-PLAN.md — Wave 3: thesis.md minimal dedup (antithesis.md UNCHANGED per D-07+D-08) + SSOT-1/2/3 lint block concrete in canaries.md (SLIM-03)
- [x] 05-05-PLAN.md — Wave 4: Canary #9 full 3-sub-canary body (stdlib-only deterministic mock) + canaries.md §Canary #9 concrete 15-assertion contract (SLIM-04)
- [x] 05-06-PLAN.md — Wave 5: final developer token measurement + CLAUDE.md Common Mistakes 2 Phase 5 bullets + ROADMAP/REQUIREMENTS close (SLIM-01..04)

## Progress

**Execution Order:**
Phase 1 → (Phase 2 ∥ Phase 3 병행 가능) → Phase 3.1 (Phase 3 완료 후 urgent 삽입) → Phase 4 → Phase 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Checkpoint Foundation | 0/TBD | Not started | - |
| 2. Resume Entry | 0/TBD | Not started | - |
| 3. 2-Layer Hang Watchdog | 7/7 | Complete | 2026-04-21 |
| 3.1 Engine Invocation Topology Refactor | 7/7 | Complete | 2026-04-21 |
| 4. Chunk Decomposition | 7/7 | Complete | 2026-04-22 |
| 5. Prompt Slim | 6/6 | Complete    | 2026-04-22 |

---

## Milestone v1.1 (M2) — Session Isolation & Commit Granularity

### Overview

TAS-M2는 M1 의 4계층 아키텍처 · 2계층 watchdog · chunk 분해 · prompt slim 이 전부 그대로 유지된다는 전제 하에, `/tas` 실행의 **출력 채널을 사용자 브랜치/트리에서 분리된 세션 브랜치로 이동**시키고 각 step 수렴 시점을 **atomic git 히스토리**로 남긴다. Phase 6 이 세션 worktree (`~/.cache/tas-sessions/{ts}/<project>/`) + named branch `tas/session-{ts}` + session index (`LATEST` symlink) + companion command 재조정 + Phase 4 chunk cherry-pick target 재정의를 도입하면, Phase 7 이 그 위에서 step-level atomic 커밋 + trailer schema + `pre_commit_hook_failed` 신규 halt_reason + manual merge 커맨드 stdout 출력을 얹는다. 두 Phase 모두 stdlib + git + bash 만 사용 (M1 제약 계승, `requirements.txt` 한 줄도 추가되지 않는다).

**마일스톤**: TAS-M2 (v1.1)
**Granularity**: standard (2 phases)
**배포 모델**: `--plugin-dir` 로컬 설치, 공개 레지스트리 없음
**M1 불변량 보존**: 4계층 info hiding · Phase 3.1 watchdog/hang enum freeze · Phase 4 chunk behaviors (worktree path, cherry-pick + git-apply fallback, 2 새 halt_reasons, MetaAgent-owned commits) 전 구간 byte-identical (ISO-05 cherry-pick target retarget 1건만 예외)

### Phases (v1.1)

- [ ] **Phase 6: Session Worktree Isolation** — `~/.cache/tas-sessions/{ts}/<project>/` named branch 세션 worktree + `LATEST` symlink session index + 동반 명령 세션 기반 조회 재조정 + Phase 4 chunk cherry-pick target session HEAD 재정의 + Canary #10 (dirty main tree 격리)
- [ ] **Phase 7: Step-Level Commit Granularity** — step 수렴 시점 atomic commit + empty-diff skip + trailer schema (Tas-Session/Step-Id/Dialectic-Verdict/Dialectic-Rounds/Iteration) + `pre_commit_hook_failed` 신규 halt_reason + manual merge stdout 출력 + CLAUDE.md 3 신규 불변량 + Canary #11 (4단 flow 커밋 카운트 + trailer 검증)

### Phase Details (v1.1)

### Phase 6: Session Worktree Isolation
**Goal**: `/tas` 실행을 사용자 작업 트리 · HEAD 브랜치와 완전히 분리된 **리뷰 가능한 세션 브랜치** (`tas/session-{ts}` @ `~/.cache/tas-sessions/{ts}/<project>/`) 로 격리하고, cold-resume chicken-and-egg 를 `LATEST` symlink session index 로 해소하며, 동반 명령(`/tas-explain`·`/tas-workspace`·`/tas-review`) 이 session index 기반으로 작동하도록 재조정하고, Phase 4 chunk cherry-pick target 을 session worktree HEAD 로 retarget 한다. 사용자는 자기 main 브랜치에 아무 변경 없이 `/tas` 실행 결과를 reviewable 단위로 받는다.
**Depends on**: Phase 4 (chunk 인프라 — Phase 6 의 ISO-05 retarget 이 Phase 4 cherry-pick 로직의 target 변수만 `${PROJECT_ROOT}` → `${SESSION_WORKTREE}` 로 바꾸며 기존 cherry-pick + `git apply --index --binary` fallback + `chunk_merge_conflict` HALT + `PRE_MERGE_SHA` 롤백 행동은 byte-identical 로 보존)
**Requirements**: ISO-01, ISO-02, ISO-03, ISO-04, ISO-05, ISO-06, DOC-02, VERIFY-ISO-01
**Success Criteria** (what must be TRUE — externally verifiable 5개):
  1. `/tas` 완주 후 `git -C <사용자 tree> status --porcelain` 출력이 실행 **전후 동일** 하다 (`ls -la ~/.cache/tas-sessions/{ts}/<project>/` 에 worktree 가 존재하고, `git branch --list "tas/session-*"` 에 named branch `tas/session-{ts}` 가 보이되 사용자 HEAD 는 원래 브랜치 그대로)
  2. `readlink ~/.cache/tas-sessions/LATEST` 가 최신 `{ts}` 디렉터리 절대경로를 반환하고, `/tas --resume` 이 이 symlink 를 통해 worktree 경로를 먼저 해석한 뒤에야 `{session}/_workspace/quick/{ts}/checkpoint.json` 을 읽는다 (chicken-and-egg 해소; SKILL.md Phase 0b Read scope 는 `checkpoint.json` + `plan.json` + `REQUEST.md` + `LATEST` symlink 만 — `dialogue.md` / `round-*.md` / `deliverable.md` / `lessons.md` 는 접근 금지 상태 유지)
  3. `/tas-explain`·`/tas-workspace`·`/tas-review` 세 명령이 `~/.cache/tas-sessions/LATEST` → session path 경로 로직으로 latest session 을 조회하며, 기존 `${PROJECT_ROOT}/_workspace/` 직접 탐색 코드 경로는 사라졌다 (grep 기준 3 명령 모두 session index 기반 1 곳 이상 match)
  4. Phase 4 chunk sub-loop 가 `${SESSION_WORKTREE}` HEAD 에 cherry-pick 하며 (원본 `${PROJECT_ROOT}` 아님), cherry-pick + `git apply --index --binary` fallback + `PRE_MERGE_SHA` 롤백 + `chunk_merge_conflict` HALT 경로는 모두 byte-identical 로 동작한다 (Canary #8 이 session worktree 위에서 fast + full 양 모드에서 exit 0 로 PASS)
  5. Canary #10 (`simulate_session_isolation.py` — `/tas-verify` 신규 등록, fast=30s / full=300s 2-Phase, stdlib-only) 가 dirty main tree + in-progress branch 상태를 셋업해 `/tas` 실행 을 시뮬레이션한 뒤 (a) 사용자 tree `git status --porcelain` 결과 delta=0, (b) `tas/session-{ts}` branch 존재, (c) stdout 에 manual merge 제안 커맨드 문자열 (Phase 7 에서 생성) 포함, (d) HALT/PASS 경로 모두 session worktree 유지됨 (ISO-06) 를 PASS 로 확인한다
**Plans**: 7 plans (estimate — M1 Phase 3/4/5 의 Wave 0 scaffolding → 핵심 behavior → UX → SSOT 문서 → canary 패턴 계승)
- [ ] 06-01-PLAN.md — Wave 0 scaffolding: `simulate_session_isolation.py` PENDING stub + `canaries.md` §Canary #10 placeholder + `tests/fixtures/` session-layer 준비 + REQUIREMENTS ISO-01..06/DOC-02/VERIFY-ISO-01 wiring (VERIFY-ISO-01 Wave 0)
- [ ] 06-02-PLAN.md — SKILL.md Phase 0 세션 부트스트랩 + dirty-tree 체크 교체 + Phase 0b `LATEST` symlink cold-resume 경로 해석 로직 (ISO-01, ISO-02, ISO-03; info-hiding Read scope 확장은 symlink + checkpoint.json + plan.json + REQUEST.md 로 엄격 한정)
- [ ] 06-03-PLAN.md — meta.md Execute Mode session bootstrap Phase 1.5 + `SESSION_WORKTREE` 변수 전파 + step-config.json `project_root` 동기화 + checkpoint schema `session_branch` + `session_worktree_path` 필드 추가 (workspace-convention.md 한 쪽에서 schema 갱신) (ISO-01, DOC-02 schema half)
- [ ] 06-04-PLAN.md — `/tas-explain` · `/tas-workspace` · `/tas-review` session-index 경로 재조정 (기존 `${PROJECT_ROOT}/_workspace/` 탐색 경로 교체) (ISO-04)
- [ ] 06-05-PLAN.md — Phase 4 chunk sub-loop cherry-pick target retarget `${PROJECT_ROOT}` → `${SESSION_WORKTREE}` (meta.md Phase 2d.5 + `engine-invocation-protocol.md` §Sub-loop invocations 변수 substitution 갱신; cherry-pick/apply fallback/`PRE_MERGE_SHA` rollback/`chunk_merge_conflict` HALT 행동은 byte-identical 검증) (ISO-05; Canary #8 smoke PASS 유지)
- [ ] 06-06-PLAN.md — `DOC-02` SSOT anchoring: `references/workspace-convention.md` 에 Session Layer 다이어그램 추가 (session worktree 내부에 `_workspace/quick/{ts}/` + `chunks/chunk-N/` 중첩 구조, index symlink 위치, `tas/session-{ts}` branch + `${SESSION_WORKTREE}` 경로 naming table) + `engine-invocation-protocol.md` Sub-loop invocations 변수 substitution 반영 (DOC-02, ISO-06 forensics 정책 문서화)
- [ ] 06-07-PLAN.md — Canary #10 full 2-Phase body 구현 + `canaries.md` §Canary #10 concrete contract (Phase 1 happy path: dirty fixture + session create + sentinel write + delta=0 확인; Phase 2 regression: HALT 경로 session worktree 생존 ISO-06) + Phase 4 regression (session retarget 후 Canary #8 PASS 유지) (VERIFY-ISO-01)

### Phase 7: Step-Level Commit Granularity
**Goal**: Phase 6 이 만든 session worktree 위에서 MetaAgent Execute 가 각 ACCEPT 된 step 수렴 시점에 `git -C "${SESSION_WORKTREE}" commit` 을 실행해 session branch 에 step-level atomic 히스토리를 남기고, empty-diff step 은 skip 하며, trailer schema (`Tas-Session: {ts}` / `Step-Id: {id}` / `Dialectic-Verdict` / `Dialectic-Rounds` / `Iteration`) 로 세션 추적 가능성을 확보하고, pre-commit hook 실패 시 **`pre_commit_hook_failed` 신규 halt_reason** 으로 HALT 하며 (`--no-verify` 자동 우회 **금지**), PASS 종료 시 `git merge tas/session-{ts}` 제안 커맨드를 stdout 에 출력한다 (auto-merge **금지**, "reviewable gate" 정체성 보존). CLAUDE.md Common Mistakes 에 3 신규 불변량 (top-level worktree 경로 규칙 · chunk cherry-pick target 재정의 · pre-commit hook 정책) 을 추가한다.
**Depends on**: Phase 6 (session worktree 가 존재해야 non-chunk step commit 이 의미 있음 — commit target path 가 `${SESSION_WORKTREE}` 로 고정된 상태에서만 trailer 의 `Tas-Session` 추적성과 manual merge 제안 UX 가 성립)
**Requirements**: COMMIT-01, COMMIT-02, COMMIT-03, COMMIT-04, COMMIT-05, DOC-01, VERIFY-COMMIT-01
**Success Criteria** (what must be TRUE — externally verifiable 5개):
  1. 4단 표준 flow 완주 후 `git -C "${SESSION_WORKTREE}" log --oneline tas/session-{ts}` 출력 커밋 수가 기대와 일치한다: 기획 step = 0 (COMMIT-02 empty-skip), 구현 step ≥ 1, 검증 step ∈ {0, 1} (대체로 empty-skip), 테스트 step ∈ {0, 1}; 모든 커밋 subject 가 `step-{id}-{slug}: {title}` 형식이다
  2. `git log --format='%B' tas/session-{ts}` 의 각 커밋에 trailer 5종이 전부 존재한다: `Tas-Session: {ts}`, `Step-Id: {id}`, `Dialectic-Verdict`, `Dialectic-Rounds`, `Iteration` (`git log --grep='Tas-Session: {ts}' --all | wc -l` 이 session commit 수와 정확히 같다)
  3. pre-commit hook 이 실패하는 fixture 에서 `/tas` 가 `halt_reason: pre_commit_hook_failed` 로 HALT 한 뒤 `{session}/_workspace/quick/{ts}/iteration-*/logs/step-*-precommit.log` 에 hook stderr 전문이 기록되고, `--no-verify` 호출이 코드/프롬프트 어디에도 등장하지 않는다 (grep `--no-verify` 결과 = `engine-invocation-protocol.md` / CLAUDE.md 의 **금지 bullet** 만 match)
  4. PASS 경로 종료 시 MainOrchestrator stdout 마지막 블록에 `git merge tas/session-{ts}` (또는 `git cherry-pick <range>`) 제안 문자열이 포함되어 있고 (사용자가 copy-paste 가능한 형식), auto-merge 호출 경로가 존재하지 않는다 (grep `git merge.*tas/session` 결과 = stdout 출력 템플릿 1곳 + 문서 예시만 — 실제 실행 `Bash(git merge ...)` 호출 0건)
  5. Canary #11 (`simulate_step_commits.py` — `/tas-verify` 신규 등록, fast=30s / full=300s 2-Phase, stdlib-only) 가 (a) 4단 flow 완주 후 session branch 커밋 카운트 검증, (b) 모든 커밋에 `Tas-Session: {ts}` trailer 존재 검증, (c) 기획/검증 step empty-commit 차단 검증, (d) pre-commit hook 강제 실패 fixture 에서 `pre_commit_hook_failed` HALT + hook 출력 로그 존재 + `--no-verify` 자동 우회 미발생 검증을 PASS 로 보고하며, **Phase 3.1 watchdog/hang enum freeze 존중** (신규 enum `pre_commit_hook_failed` 는 merge/hook 직교 도메인 — Phase 4 `chunk_merge_conflict` 선례 계승, watchdog/hang 도메인 과는 무관)
**Plans**: 7 plans (estimate)
- [ ] 07-01-PLAN.md — Wave 0 scaffolding: `simulate_step_commits.py` PENDING stub + `canaries.md` §Canary #11 placeholder + REQUIREMENTS COMMIT-01..05/DOC-01/VERIFY-COMMIT-01 wiring (VERIFY-COMMIT-01 Wave 0)
- [ ] 07-02-PLAN.md — meta.md Execute Phase 2d step 9.6 (ACCEPT commit hook) 추가 + `git -C "${SESSION_WORKTREE}" commit` + `git diff --quiet` empty-skip 로직 (Phase 4 chunk commit 패턴의 non-chunk step 확장) (COMMIT-01, COMMIT-02)
- [ ] 07-03-PLAN.md — Trailer schema 정의 + MetaAgent 커밋 메시지 composer (subject `step-{id}-{slug}: {title}` + 5 trailers) + `references/workspace-convention.md` §Commit Schema 섹션 추가 (COMMIT-03, DOC-02 연장)
- [ ] 07-04-PLAN.md — `pre_commit_hook_failed` 신규 halt_reason 추가 (SKILL.md HALT Reason Labels table + Recovery Guidance + meta.md Execute 분류표) + hook stderr `{session}/_workspace/quick/{ts}/iteration-*/logs/step-*-precommit.log` persist 로직 + `--no-verify` 자동 우회 금지 가드 + 문서 근거 `Phase 4 chunk_merge_conflict 선례` 주석 (Phase 3.1 D-TOPO-05 watchdog/hang enum freeze 존중 — merge/hook 직교 도메인 예외) (COMMIT-04)
- [ ] 07-05-PLAN.md — SKILL.md Phase 4 "Present Result" stdout 템플릿 확장 → PASS 경로 말미 `git merge tas/session-{ts}` 제안 블록 + 사용자 안내 문구 (manual only, auto-merge 호출 0건) (COMMIT-05)
- [ ] 07-06-PLAN.md — `DOC-01` CLAUDE.md Common Mistakes 3 신규 bullet: (a) session worktree top-level 경로 위반 (프로젝트 tree 내부 배치 금지 — ISO-01/Phase 6 D 참조), (b) chunk cherry-pick target 실수 (main repo HEAD 아닌 session HEAD — ISO-05 계승), (c) pre-commit hook `--no-verify` 자동 우회 금지 (COMMIT-04 계승) + M1 Phase 3.1/Phase 4 기존 bullet 들과의 배치 순서 및 md5 baseline 보존 (DOC-01)
- [ ] 07-07-PLAN.md — Canary #11 full 2-Phase body 구현 + `canaries.md` §Canary #11 concrete contract (Phase 1 happy path: 4단 flow 커밋 카운트 + trailer 5종 assertions + empty-skip; Phase 2 regression: pre-commit hook 강제 실패 fixture + `pre_commit_hook_failed` HALT + hook 로그 존재 + `--no-verify` 미호출 검증) + M2 전체 회귀 (Canary #1~#10 clean + Phase 3.1 enum freeze + Phase 4 chunk behavior byte-identical) (VERIFY-COMMIT-01)

### v1.1 Progress

**Execution Order (v1.1):**
Phase 6 → Phase 7 (순차; Phase 7 은 Phase 6 session worktree 존재를 전제로 commit 동작이 성립)

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Session Worktree Isolation | 0/7 | Not started | - |
| 7. Step-Level Commit Granularity | 0/7 | Not started | - |

### v1.1 Coverage

v1.1 (M2) 요구사항 **15/15 100% 매핑** (no orphans):

- **Phase 6 (8 REQs)**: ISO-01, ISO-02, ISO-03, ISO-04, ISO-05, ISO-06, DOC-02, VERIFY-ISO-01
- **Phase 7 (7 REQs)**: COMMIT-01, COMMIT-02, COMMIT-03, COMMIT-04, COMMIT-05, DOC-01, VERIFY-COMMIT-01

상세 Traceability 는 `.planning/REQUIREMENTS.md` §v1.1 (M2) Traceability 참조.

### v1.1 Invariant Audit (M1 계승)

Phase 6 + Phase 7 설계 전 구간에서 다음 M1 불변량이 **violation 없이** 보존된다:

1. **4계층 info hiding** — SKILL.md Phase 0b Read scope 는 M1 base (`checkpoint.json` / `plan.json` / `REQUEST.md`) + M2 추가 단 1종 (`LATEST` symlink) 으로 한정. `dialogue.md` / `round-*.md` / `deliverable.md` / `lessons.md` / `heartbeat.txt` 접근 금지 유지 (ISO-03 session index 조회도 symlink resolve 1회로 scope 종결)
2. **Phase 3.1 watchdog/hang enum freeze** — `pre_commit_hook_failed` 는 **merge/hook 직교 도메인** 에 속하며 (`sdk_session_hang` / `step_transition_hang` / `bash_wrapper_kill` / `engine_crash` 4종 watchdog/hang 도메인 과 무관), Phase 4 `chunk_merge_conflict` 선례 와 동일한 근거로 freeze 의 **정당한 예외**. 다른 watchdog/hang 계열 신규 enum 금지 원칙은 유지
3. **Phase 4 chunk behaviors byte-identical** — worktree 경로 (`$(cd ${WORKSPACE} && pwd)/chunks/chunk-{N}/`), cherry-pick + `git apply --index --binary` fallback, `PRE_MERGE_SHA` 롤백, `chunk_merge_conflict` + `worktree_backlog` 2 halt_reasons, MetaAgent-owned commits (thesis/antithesis role 순수성) 전부 byte-identical. ISO-05 **cherry-pick target 변수만** `${PROJECT_ROOT}` → `${SESSION_WORKTREE}` retarget — 그 외 모든 행동 그대로
4. **Zero new runtime deps** — stdlib + git + bash 만 사용, `requirements.txt` / `.claude-plugin/*.json` 런타임 의존성에 신규 패키지 0건 추가 (M1 제약 계승)
5. **범위 금지 (MainOrchestrator never reads project source)** — Phase 6/7 Canary #10/#11 는 stdlib-only fixture 합성, MainOrchestrator 쪽 변경 (SKILL.md Phase 0 부트스트랩 + Phase 4 stdout 템플릿) 은 session path 해석 + 출력 문자열 composition 한정

---

*Last updated: 2026-04-23 — Milestone v1.1 (Session Isolation & Commit Granularity) roadmap created. M1 전체 섹션 historical record 로 보존. Phase 6 (Session Worktree Isolation, 8 REQs) + Phase 7 (Step-Level Commit Granularity, 7 REQs) 추가 — 15/15 v1.1 requirements 100% 매핑. Phase 6 은 M1 Phase 4 chunk infra 의존 (ISO-05 cherry-pick target retarget), Phase 7 은 Phase 6 의존. 신규 halt_reason `pre_commit_hook_failed` 는 Phase 3.1 watchdog/hang enum freeze 직교 도메인 예외 (Phase 4 `chunk_merge_conflict` 선례).*
