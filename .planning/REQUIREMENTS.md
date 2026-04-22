# REQUIREMENTS — tas M1

**마일스톤**: 실행 안정성 + 컨텍스트 효율성 + 프롬프트 군살제거
**날짜**: 2026-04-21
**상태**: v1 스코프 확정

---

## v1 Requirements

### A. Checkpoint Foundation

- [ ] **CHKPT-01** — MetaAgent가 각 스텝 완료 시점에 `{WORKSPACE}/checkpoint.json`을 atomic write(tempfile + os.fsync + os.replace)로 기록한다
- [ ] **CHKPT-02** — `checkpoint.json`은 `schema_version`, `workspace`, `plan_hash`, `current_step`, `completed_steps[]`, `current_chunk`, `completed_chunks[]`, `status`, `updated_at` 필드를 포함한다
- [ ] **CHKPT-03** — MetaAgent Classify 단계에서 승인된 plan이 `{WORKSPACE}/plan.json`에 영속화된다 (resume 시 재-classify 금지의 기반)
- [ ] **CHKPT-04** — `references/workspace-convention.md`에 Checkpoint Schema 섹션을 추가하고 기존 워크스페이스 구조 다이어그램을 갱신한다
- [ ] **CHKPT-05** — `CLAUDE.md`의 "Adding resume/pipeline mechanisms" 금지 조항을 폐기하고 opt-in resume 원칙으로 교체한다

### B. Resume Entry

- [ ] **RESUME-01** — 사용자가 `/tas --resume`을 호출하면 SKILL.md Phase 0b Resume Gate가 가장 최근 워크스페이스의 `checkpoint.json`을 감지한다
- [ ] **RESUME-02** — SKILL.md은 `checkpoint.json` 읽기만 하며, 내부 필드(verdict, rounds 등)를 UI에 노출하지 않는다 (info hiding 보존)
- [ ] **RESUME-03** — MetaAgent Execute Mode는 `MODE: resume` + `RESUME_FROM: step_N` 파라미터를 받아 완료된 스텝을 건너뛰고(`completed_steps[]` 기준) 재개한다
- [ ] **RESUME-04** — Resume 시 MetaAgent는 Classify를 다시 호출하지 않고 `plan.json`을 그대로 사용한다
- [ ] **RESUME-05** — `--resume` 실패 시(체크포인트 손상·plan 부재·worktree 소실) 명확한 halt_reason과 복구 가이드를 사용자에게 표시한다

### C. 2-Layer Hang Watchdog

- [x] **WATCH-01** — `dialectic.py`의 SDK 호출부를 `asyncio.wait_for` → `asyncio.timeout` 컨텍스트 매니저로 전환한다 (Python 3.10 fallback 유지)
- [x] **WATCH-02** — `dialectic.py`가 각 라운드 종료 시 `{LOG_DIR}/heartbeat.txt`에 `{round_n, timestamp, speaker}`를 atomic write한다
- [x] **WATCH-03** — `run-dialectic.sh`가 Bash `timeout(1)` + `--kill-after=30s`로 `dialectic.py` 서브프로세스를 래핑한다 (macOS `timeout` 부재 시 graceful degrade — Layer A는 계속 활성)
- [x] **WATCH-04** — MetaAgent Execute Mode가 각 스텝 Agent() 호출에 `timeout`을 명시하고, 타임아웃 시 `halt_reason: step_transition_hang`으로 기록한다
- [x] **WATCH-05** — SKILL.md의 halt_reason 표시 테이블에 `sdk_session_hang`, `step_transition_hang`, `bash_wrapper_kill`을 추가하고 각각의 복구 가이드를 기재한다

### C.1 Engine Invocation Topology

- [x] **TOPO-01** — `run-dialectic.sh`가 EXIT trap으로 `engine.done` / `engine.exit` atomic marker를 기록한다 (tempfile + `mv -f` POSIX rename). 정상 종료, `timeout 124/137`, Python raise 모든 경로에서 trap 통과.
- [x] **TOPO-02** — MetaAgent Execute Phase 2d step 7이 `nohup bash run-dialectic.sh <config> > <log> 2>&1 & echo $!` 형태 + `run_in_background: false`로 엔진을 기동하고, stdout으로 단일 정수 PID를 캡처한다 (`timeout:` 파라미터 사용 금지). Scenario B 전환 후 이 PID + 4종 path는 MetaAgent-internal scratch state로만 유지되며, MainOrchestrator에는 노출되지 않는다 (Plan 03.1-04 Scenario B 실현).
- [x] **TOPO-03** — **Scenario B (Plan Review Issue #2 resolution)**: MetaAgent 가 engine lifecycle polling 을 내부에서 소유한다 (`until test -f $DONE_PATH || ! kill -0 $PID` 폴링 루프를 10분 Bash cap-safe 단위 19 × 30s 로 chunk 호출). MainOrchestrator (SKILL.md Phase 2) 는 MetaAgent 가 반환하는 pre-Phase-3.1 계약 `status: completed | halted` JSON 만 소비하며, 엔진 lifecycle 에 직접 관여하지 않는다. Info-hiding 경계 보존 (`dialogue.md` / `round-*.md` / `deliverable.md` / `lessons.md` / `heartbeat.txt` 은 MetaAgent 전용 — SKILL.md 접근 금지).
- [x] **TOPO-04** — `references/engine-invocation-protocol.md`가 file-marker polling 계약으로 전면 재작성된다 (task-notification 계약 제거, 금지 bullet 3종 추가).
- [x] **TOPO-05** — `step_transition_hang` enum이 "PID 사망 + engine.done 부재" 경로를 흡수하며, 신규 halt_reason enum 추가 없이 Phase 3 분류표 (03-CONTEXT.md D-05) 가 재사용된다.
- [x] **TOPO-06** — Approach B (subagent nohup fire-and-forget) 경로가 end-to-end `/tas` 실행에서 dialectic 첫 round를 정상 완주시킨다 (사후 검증 단계; CLAUDE.md Common Mistakes bullet + engine-invocation-protocol.md 가이드 반영). **Documentation-side complete (Plan 03.1-07):** CLAUDE.md Common Mistakes 3 bullets 추가/교체 (Scenario B nohup+& paradigm + 3-element load-bearing 규칙 + exec keyword ban). End-to-end 실측은 `/tas-verify` + 사용자 실행 경로에서 사후 검증.
- [x] **VERIFY-TOPO-01** — `/tas-verify`에 Canary #7 (subagent orphan survival + real-chain integration) 이 등록되고, 기본 `$T=120` / 확장 `$T=1800` 모드에서 exit 0 반환한다. 2-Phase 구현 (Plan 03.1-06): Phase 1 PASS 조건 (subagent duration < 10s, `$MARKER=survived`, PID PPID=1 로 $T 생존) + Phase 2 PASS 조건 (real `run-dialectic.sh` sed-copy mock injection 후 `engine.done` 존재 + `engine.exit=='0'` — Plan Review Issue #1 regression guard; SKIP allowed with explicit reason, Plan 07 invariant 6 static backstop).

### D. Chunk Decomposition

- [x] **CHUNK-01** — MetaAgent Classify Phase 2c에서 구현 작업의 규모(추정 파일 수/스코프 범위) 기반으로 chunk 분해 필요성을 판단한다
- [x] **CHUNK-02** — chunk 분해 시 `plan.json`의 `implementation_chunks[]` 배열에 각 chunk의 `id`, `scope`, `pass_criteria`를 기록한다
- [x] **CHUNK-03** — MetaAgent Execute Phase 2d.5 Chunk Sub-loop가 각 chunk를 `{WORKSPACE}/chunks/chunk-{c}/` 경로의 git worktree에서 독립 dialectic으로 실행한다 (`project_root`를 해당 worktree로 설정)
- [x] **CHUNK-04** — chunk_N의 deliverable 요약이 chunk_N+1의 `step_context`로 전달된다 (순차 릴레이)
- [x] **CHUNK-05** — 모든 chunk 완료 후 MetaAgent가 chunk worktree 커밋을 원본 `project_root`에 cherry-pick으로 머지한다 (충돌 시 `git apply` fallback, 둘 다 실패 시 HALT)
- [x] **CHUNK-06** — 머지 완료 후 `verify`/`test` 스텝은 통합된 결과물에 대해 **단일 dialectic**로 실행한다 (chunk별 verify 금지)
- [x] **CHUNK-07** — chunk 실행이 FAIL/HALT로 끝나면 해당 chunk worktree와 체크포인트를 정리하고 상위 에러 경로로 전파한다 (orphan worktree 방지)

### E. Prompt Slim

- [x] **SLIM-01** — `scripts/measure-prompt-tokens.py`를 추가한다 (Anthropic `count_tokens` API 사용, 개발자 전용, `requirements.txt`에 의존성 추가 금지)
- [x] **SLIM-02** — `meta.md`를 `references/meta-classify.md` + `references/meta-execute.md`로 분리하여 meta.md 토큰을 5,500 임계 이하(목표 4,500)로 축소한다
- [x] **SLIM-03** — `SKILL.md` / `agents/thesis.md` / `agents/antithesis.md` / `references/*` 프롬프트의 중복·과잉 지시를 정리한다 (references drift 방지를 위해 동일 지시는 단일 위치에만)
- [x] **SLIM-04** — behavioral diff canary 3개(trivial classify / chunked classify / full execute)를 작성하여 prompt slim 전후 동일한 plan/verdict가 나오는지 검증한다

### F. Verification

- [x] **VERIFY-01** — `/tas-verify`에 M1 전용 canary를 추가한다: [x] (a) 의도적 stdout-stall을 유발하는 mock SDK로 Layer A watchdog 트립 검증 (Plan 03-07), [x] (b) MetaAgent step-transition hang 시뮬레이션으로 Layer B 트립 검증 (Plan 03-07), [x] (c) 2-chunk 시나리오의 머지+통합 verify 성공 검증 — Canary #8 full 2-Phase body (5 Phase 1 + 4 Phase 2 assertions, stdlib-only) + canaries.md contract + 14-invariant regression suite (Plan 04-07)
- [ ] **VERIFY-02** — `python3 dialectic.py --self-test`에 `checkpoint.json` 스키마 호환성 회귀 테스트를 추가한다

---

## v2 Requirements (deferred)

- chunk 병렬 실행 (M1은 순차 릴레이만)
- chunk boundary 자동 최적화 (M1은 MetaAgent의 heuristic 판단)
- Prompt A/B 테스트 프레임워크

---

## Out of Scope

- **자동 resume 데몬(파이프라인)** — 사용자 통제권 침해 + 실패 루프 위험. `--resume`은 명시적 opt-in만
- **클라우드 영속화 (S3/DB)** — 로컬 `_workspace/` 충분. 외부 의존성·프라이버시 비용 대비 효용 낮음
- **chunk 병렬 실행** — M1에서는 worktree 격리 + 순차 릴레이만. 동시 실행은 레이스·머지 복잡성 유발
- **네이티브 UI/대쉬보드** — CLI 피드백으로 충분
- **`--force-resume` 옵션** — 손상된 체크포인트를 무시하고 강제 재개하는 플래그는 만들지 않는다 (정책 위반 위험)
- **smart prompt compression** — meta.md를 LLM으로 자동 압축하는 기능. M1은 수동·분할만
- **런타임 토큰 측정** — end user에게 API 키를 요구하지 않기 위해 `count_tokens`는 개발자 스크립트 전용
- **라운드/이터레이션 경계 체크포인트** — 체크포인트는 스텝 경계에서만

---

## Traceability

<!-- 각 요구사항이 어떤 페이즈에서 구현되는지. gsd-roadmapper가 채움 -->

| REQ-ID | Phase | Status |
|--------|-------|--------|
| CHKPT-01 | Phase 1 (Checkpoint Foundation) | Pending |
| CHKPT-02 | Phase 1 (Checkpoint Foundation) | Pending |
| CHKPT-03 | Phase 1 (Checkpoint Foundation) | Pending |
| CHKPT-04 | Phase 1 (Checkpoint Foundation) | Pending |
| CHKPT-05 | Phase 1 (Checkpoint Foundation) | Pending |
| RESUME-01 | Phase 2 (Resume Entry) | Pending |
| RESUME-02 | Phase 2 (Resume Entry) | Pending |
| RESUME-03 | Phase 2 (Resume Entry) | Pending |
| RESUME-04 | Phase 2 (Resume Entry) | Pending |
| RESUME-05 | Phase 2 (Resume Entry) | Pending |
| WATCH-01 | Phase 3 (2-Layer Hang Watchdog) | Complete |
| WATCH-02 | Phase 3 (2-Layer Hang Watchdog) | Complete |
| WATCH-03 | Phase 3 (2-Layer Hang Watchdog) | Complete |
| WATCH-04 | Phase 3 (2-Layer Hang Watchdog) | Complete |
| WATCH-05 | Phase 3 (2-Layer Hang Watchdog) | Complete (Plan 03-07) |
| CHUNK-01 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-02) |
| CHUNK-02 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-02 schema + Plan 04-03 SKILL.md chunks UX + Adjust chunks override) |
| CHUNK-03 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-04 Phase 2d.5 worktree add --detach + chunk-ID path resolution + pre-flight prune ritual; Plan 04-06 workspace-convention.md chunks/ subtree + Chunk worktree Naming Rules row + Chunk Merge Workflow Pre-flight & Per-chunk cycle steps 1-2 documentation layer) |
| CHUNK-04 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-04 cumulative_chunk_context sequential relay + prior-chunk-summary injection into next chunk's step_assignment; Plan 04-06 workspace-convention.md Chunk Merge Workflow Per-chunk cycle step 5 summary-generation ≤5KB + cumulative_chunk_context iteration-scoped relay documentation layer) |
| CHUNK-05 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-04 cherry-pick primary + git apply --index --binary fallback + PRE_MERGE_SHA rollback + chunk_merge_conflict HALT execution layer; Plan 04-05 SKILL.md Labels row + Recovery Guidance Korean message with D-08 `/tas --resume` prohibition + merge.log forensic path + plan.json re-review/chunks:1 override UX layer; Plan 04-06 workspace-convention.md Chunk Merge Workflow Per-chunk cycle step 6 merge procedure documentation + halted mid-chunk checkpoint example + SSOT boundary anchoring) |
| CHUNK-06 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-04 verify/test remain single-dialectic outside Phase 2d.5; sub-loop activates only for S.name == 구현 with implementation_chunks non-null; Plan 04-05 meta.md Prepare Dialectic Config step 4 Synthesis Context injection with 4 focus items [Public API / Shared file / Value flow / Regression] + Not to be re-audited boundary — antithesis.md UNCHANGED per D-07 Phase 5 slim protection; Plan 04-06 engine-invocation-protocol.md Sub-loop invocations addendum + workspace-convention.md Chunk Merge Workflow SSOT boundary documenting per-file ownership preventing verify/test surface drift) |
| CHUNK-07 | Phase 4 (Chunk Decomposition) | Complete (Plan 04-04 Phase 2d.5 FAIL branch inline cleanup + HALT propagate + checkpoint write with current_chunk/completed_chunks forensic fields + NO re-chunking / NO within-iter retry execution layer; Plan 04-05 SKILL.md worktree_backlog Labels row + Recovery Guidance Korean message routing `git worktree prune` + `/tas-workspace clean` with environment-cleanup-signal clarification UX layer; Plan 04-06 workspace-convention.md FAIL/HALT path documentation + Chunk Merge Workflow Pre-flight worktree-count ≥10 HALT worktree_backlog + CLAUDE.md 2 Phase 4 Common Mistakes bullets encoding anti-patterns + engine-invocation-protocol.md Sub-loop invocations tagging chunk_merge_conflict/worktree_backlog as MetaAgent-synthesized-not-engine-emitted preserving Phase 3.1 D-TOPO-05 freeze) |
| SLIM-01 | Phase 5 (Prompt Slim) | Complete (Plan 05-01 scripts/measure-prompt-tokens.py skeleton with fail-loud ImportError + ANTHROPIC_API_KEY guard + MODEL constant claude-opus-4-7 + per-file count_tokens(system=) pattern + Plan 05-06 final developer-measured token count confirmed ≤ 5,500 via char÷4 provisional fallback = ~2,675 tokens meta.md; authoritative count_tokens() re-measurement deferred to developer-local run per D-04 dev-only boundary) |
| SLIM-02 | Phase 5 (Prompt Slim) | Complete (Plan 05-02 meta.md split 1123→~218 lines to references/meta-{classify,execute}.md with pre-slim baselines captured BEFORE split per Pitfall 1 + Plan 05-03 Mode-bound Reference Load + Final JSON Contract SSOT + references_read attestation at first actionable step of each references file per Pitfall 5 + Plan 05-06 final token measurement gate verdict PASS provisional; cumulative additions (Waves 2-4: +83 lines Mode-bound Reference Load + Final JSON Contract) still well under 5,500 threshold with ~2,000-token margin) |
| SLIM-03 | Phase 5 (Prompt Slim) | Complete (Plan 05-03 SKILL.md SCOPE PROHIBITION / information hiding dedup 3→≤2 mentions + Plan 05-03 SKILL.md Phase 3 Validate Attestation references_read warning-only extension with Pitfall 9 info-hiding preservation + Plan 05-04 thesis.md minimal dedup [zero-diff outcome — no verbatim cross-file duplicates; antithesis.md byte-identical per D-07+D-08 Phase 4 boundary extension] + Plan 05-04 SSOT-1/2/3 lint block concrete in canaries.md §SSOT Invariants with count==1 anchoring on meta.md §Final JSON Contract + meta-execute.md §Convergence Model) |
| SLIM-04 | Phase 5 (Prompt Slim) | Complete (Plan 05-01 Canary #9 PENDING stub simulate_prompt_slim_diff.py + Plan 05-02 pre-slim baseline fixtures canary-9-baseline-{a,b,c}.json captured against pre-split meta.md SHA 2f3ad87e per Pitfall 1 + Plan 05-05 full 3-sub-canary body 257 LOC stdlib-only deterministic mock with 15 total assertions [4+4+6+1] + canaries.md §Canary #9 concrete contract Wave-4-complete STATUS + Fail signals regression-class table + Integration with Canary #4/#5/#6/#7/#8 + SSOT lint) |
| VERIFY-01 (a) | Phase 3 (2-Layer Hang Watchdog) | Complete (Plan 03-07) |
| VERIFY-01 (b) | Phase 3 (2-Layer Hang Watchdog) | Complete (Plan 03-07) |
| VERIFY-01 (c) | Phase 4 (Chunk Decomposition) | Complete (Plan 04-07, Canary #8 full 2-Phase body 502 LOC stdlib-only: Phase 1 happy path 5 assertions [worktree add x 2 / chunk-N commits / cherry-pick x 2 / Synthesis Context injection / post-cleanup clean] + Phase 2 regression 4 assertions [Phase 1 under regression fixture / integrated verify FAIL / FAIL keyword regex / re-Classify structural guard]; canaries.md §Canary #8 header [PENDING] suffix removed + 4 PENDING markers replaced with 9-Assertion contract + 9-row Fail signals FAIL→regression mapping; 14-invariant Phase 4 regression suite 12/14 clean + 2 pre-existing-baseline observations documented; fast ~0.24s full ~0.35s both exit 0 with exact stdout match) |
| VERIFY-02 | Phase 1 (Checkpoint Foundation) | Pending |
| TOPO-01 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete |
| TOPO-02 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete (Plan 03.1-04) |
| TOPO-03 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete (Plan 03.1-04, Scenario B: MetaAgent-owned polling) |
| TOPO-04 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete |
| TOPO-05 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete (Plan 03.1-05, SKILL.md Phase 0b halt_reason enum freeze bullet) |
| TOPO-06 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete (Plan 03.1-07, CLAUDE.md Common Mistakes 3 bullets + 7-invariant regression suite verified; canonical automated verify block exits 0) |
| VERIFY-TOPO-01 | Phase 3.1 (Engine Invocation Topology Refactor) | Complete (Plan 03.1-06, 2-Phase canary: orphan survival + real-chain integration via sed-copy mock injection) |

**Coverage:** 35/35 v1 requirements mapped (VERIFY-01 split into 3 canaries: a+b → Phase 3, c → Phase 4; Phase 3.1 adds TOPO-01..06 + VERIFY-TOPO-01 family)

---

## Core Value Alignment

**Core Value**: 변증법적 품질 게이트 — 단일 에이전트가 놓치는 결함을 두 관점의 구조적 반복으로 드러내기.

**M1이 Core Value에 기여하는 방식**:
- 실행 안정성 확보 → 품질 게이트가 "완료됨"을 신뢰할 수 있게 됨 (현재는 hang으로 미완료도 "끝났나?" 불명)
- Chunk 분해 → 큰 작업에서 컨텍스트 포화로 게이트 자체가 무력화되는 것 방지
- 프롬프트 군살제거 → agent가 자기 역할에 집중 (토큰 임계 초과로 역할 지시가 희석되는 것 방지)

세 테마 모두 "품질 게이트가 기대대로 작동함"을 보존·확장하는 방향이며 Core Value와 정합.

---

*Last updated: 2026-04-21 — Phase mappings assigned by gsd-roadmapper (TAS-M1 initialization)*
