# tas — Claude Code 변증법 워크플로우 플러그인

[English](./README.md) · **한국어**

사용자 요청을 **정(正)–반(反)–합(合) 정반합** 구조의 멀티 에이전트 오케스트레이션으로 처리하는 Claude Code 플러그인입니다. 요청 복잡도에 따라 1~4단계의 적응형 워크플로우가 구성되고, 사용자가 반복(iteration) 횟수를 조절할 수 있으며, 반복 사이에 얻은 교훈(lessons learned)이 누적되어 다음 패스로 전달됩니다.

> 왜 써야 하나? 대부분의 AI 코딩 에이전트는 단일 패스 답변을 냅니다. `tas`는 두 에이전트를 강제로 맞붙입니다 — 하나는 제안하고, 하나는 공격합니다 — 수렴할 때까지. 모호하거나 실수 비용이 큰 작업에서, 단일 패스로는 놓칠 실패를 드러냅니다.

---

## 요구사항

- **Claude Code** 2.x 이상 (플러그인 시스템 지원)
- **Python 3.10 이상** (변증법 엔진 실행에 사용)
- **`claude-agent-sdk`** Python 패키지 — 아래 중 하나로 설치:
  ```bash
  pip install claude-agent-sdk
  # 또는
  pipx install claude-agent-sdk
  # 또는
  uv tool install claude-agent-sdk
  ```
- **`jq`** (`Stop` 훅의 산출물 무결성 검사용 — 선택 사항, 없으면 자동 스킵)

`SessionStart` 훅이 세션 시작 시 Python과 SDK 설치 여부를 점검하고, 없으면 설치 안내를 출력하므로 첫 실행에서 바로 확인할 수 있습니다.

---

## 설치

용도에 따라 세 가지 방식이 있습니다.

### 방식 A — 공개 마켓플레이스에서 설치 (권장)

```
/plugin marketplace add https://github.com/simsimhae91/tas.git
/plugin install tas@tas
```

세션이 바뀌어도 유지됩니다. 첫 번째 `tas`는 플러그인 이름, 두 번째는 마켓플레이스 이름입니다 (이름이 동일합니다).

제거 방법:
```
/plugin uninstall tas@tas
/plugin marketplace remove tas
```

### 방식 B — 로컬 개발 모드 (세션 한정)

리포지토리를 직접 클론해 수정하면서 쓰는 경우:

```bash
git clone https://github.com/simsimhae91/tas.git /path/to/tas
claude --plugin-dir /path/to/tas
```

해당 세션에서만 로드됩니다. `SKILL.md`나 에이전트 프롬프트를 편집하며 테스트할 때 유용합니다.

### 방식 C — 로컬 마켓플레이스 (클론본으로 영구 설치)

```bash
git clone https://github.com/simsimhae91/tas.git /path/to/tas
```
이후 Claude Code에서:
```
/plugin marketplace add /path/to/tas
/plugin install tas@tas
```

---

## 스킬

플러그인을 설치하면 다섯 개의 스킬이 등록됩니다.

| 명령어 | 목적 |
|--------|------|
| `/tas {요청}` | 메인 변증법 워크플로우 — 분류, 계획 승인, 실행 |
| `/tas-review [ref\|diff]` | git ref 또는 PR 대상 경량 변증법 코드 리뷰 |
| `/tas-verify [파일]` | 산출된 코드에 대한 합성 후 경계값 추적 검증 |
| `/tas-explain [run-id]` | 과거 변증법 대화를 일반 언어로 요약 |
| `/tas-workspace [list\|show\|clean]` | `_workspace/quick/` 조회 및 정리 |

다섯 스킬 모두 동일한 범위 제한을 공유합니다: 특정 작업이 명시적으로 요구하지 않는 한 프로젝트 소스 코드를 읽지 않습니다 (예: `/tas-review`는 리뷰 대상 diff만 읽음). 코드를 실제로 읽고 수정하는 것은 변증법 엔진이지 오케스트레이터가 아닙니다.

---

## 동작 방식

```
/tas {요청}
  │
  ├── 사소(trivial)한가? → 바로 응답
  │
  └── MetaAgent Classify (Agent 서브에이전트)
        │ 계획 JSON 반환: {complexity, steps, loop_count, loop_policy}
        ▼
      사용자 승인 (loop_count, reentry_point 조정 가능)
        │
        ▼
      MetaAgent Execute (Agent 서브에이전트)
        │
        └── iteration i in 1..loop_count:
              └── 각 step마다 (기획→구현→검증→테스트 또는 부분집합):
                    python3 dialectic.py
                    正 제안 → 反 응답 → 수렴할 때까지 대화
                    │
                    └── 검증/테스트 FAIL 시 → 구현 재실행
                        (동일 블로커가 3회 연속 반복되면 HALT)
              └── iteration-{i}/DELIVERABLE.md 작성
              └── lessons.md에 교훈 추가
              └── 다음 iteration은 누적 교훈 + 초점 각도(focus angle) 수령
```

각 층에는 엄격한 컨텍스트 경계가 있습니다.

| 층 | 에이전트 | 경계 |
|----|----------|------|
| 0 | MainOrchestrator | 얇은 스케줄러 — 내부 변증법을 보지 않음 |
| 1 | MetaAgent (合) | `Agent()` 서브에이전트로 실행; 분류 후 실행 |
| 2 | ThesisAgent (正) / AntithesisAgent (反) | `dialectic.py`가 관리하는 Claude SDK 세션 |

컨텍스트 격리는 컨텍스트 윈도우 고갈을 방지합니다. MainOrchestrator는 입력을 전달하고 JSON 출력만 파싱합니다. 나머지는 모두 MetaAgent가 처리합니다.

---

## 사용법

```
/tas {요청}
```

모드는 **quick** 하나뿐입니다. MetaAgent의 분류기가 요청의 실제 복잡도에 따라 단계 수(1~4)를 결정합니다.

### 예시

```
/tas TypeScript retry 함수 설계해줘              # 단순 — 단일 스텝
/tas 이 코드의 에러 핸들링 리뷰                   # 리뷰 — 2~3 스텝
/tas 결제 버튼이 안 눌려요 고쳐주세요              # 중간 — 기획/구현/검증
/tas 대시보드에 실시간 알림 추가해줘               # 복잡 — 기획/구현/검증/테스트
```

### 복잡도 등급

| 등급 | 단계 수 | 예 |
|------|---------|----|
| `simple` | 1 | 단일 함수 설계, 좁은 질문, 소규모 수정 |
| `medium` | 2~3 | 다중 파일 변경, 기존 모듈 내 새 기능 |
| `complex` | 4 | 사용자 대면 새 동작, 광범위 통합 |

실행 전에 MetaAgent가 계획(단계 + 목표 + 통과 기준)을 제안하고 사용자가 승인·조정합니다.

### 정규 4단계 흐름

복잡한 구현 작업의 경우:

| 단계 | 역할 | 내용 |
|------|------|------|
| **1. 기획 (Plan)** | 正 제안, 反 반론 | 접근법, 영향 파일, 인터페이스, 제약 |
| **2. 구현 (Implement)** | 正 코드 작성, 反 리뷰 | 실제 디스크에 코드 반영 (`bypassPermissions` 경유) |
| **3. 검증 (Verify)** — *역할 반전* | 正 공격, 反 판정 | 정적 리뷰; 블로커 0 = PASS, 1개 이상 = FAIL → 구현 재시도 |
| **4. 테스트 (Test)** — *역할 반전* | 正 테스트 실행, 反 평가 | 정적 + 동적(웹의 경우 Playwright); PASS 또는 FAIL → 구현 재시도 |

iteration 내부에서는 FAIL → 구현 재시도가 PASS 되거나 지속 실패(persistent failure)까지 무제한 반복됩니다 (동일 블로커 3회 연속 발생 시 HALT). 고정된 재시도 상한은 없으며, 변증법이 자연스럽게 해소합니다.

### 반복 루프 (Ralph 패턴)

사용자가 계획 승인 시점에 `loop_count`를 지정합니다. 기본값은 1(단일 패스, 추가 다듬기 없음)입니다. 다듬기가 중요한 작업은 값을 늘리세요.

```
Iteration 1: 베이스라인 — 기획→구현→검증→테스트 풀 플로우
Iteration 2: 구현부터 재진입 + "초점 각도" + 누적 교훈
Iteration 3: 다음 초점 각도 + 이전까지의 모든 교훈
...
```

각 iteration은 다음을 수행합니다:
- **초점 각도(focus angle)** 적용 (UX 다듬기, 접근성, 성능, 엣지 케이스 등)
- 이전 iteration의 산출물 위에서 이어 작업 (처음부터 새로 짜지 않음)
- 누적된 `lessons.md` 전체를 컨텍스트로 수령
- 자체 `iteration-{N}/DELIVERABLE.md` 생성
- `lessons.md`에 엔트리 추가 (개선점, 해소된 블로커, 열린 관찰, 기각된 대안)

**조기 종료**: 두 에이전트가 추가 다듬기가 무익하다는 데 동의하면 `loop_count` 도달 전에 루프가 종료됩니다.

### 도메인별 테스트 전략

테스트 단계는 분류 단계에서 감지된 프로젝트 도메인에 따라 달라집니다.

| 도메인 | 전략 |
|--------|------|
| `web-frontend` | 단위 테스트 + Playwright 네비게이션 + 스크린샷 + UI/UX 평가 |
| `web-backend` / `api` | 단위 테스트 + 실제 엔드포인트 대상 통합 테스트 |
| `cli` | 단위 테스트 + 실제 인자로 서브프로세스 실행 |
| `library` | 단위 테스트 + 사용 예제 검증 |

### 워크스페이스 구조

**0.2.5** 부터 모든 `/tas` 실행은 XDG cache 아래의 **세션 격리 git worktree** 에서 진행됩니다 — 변증법 엔진이 사용자의 프로젝트 트리를 직접 수정하는 일은 더 이상 없습니다.

```
~/.cache/tas-sessions/
  LATEST → 20260423T060506Z/myproject/           # 가장 최근 세션을 가리키는 심볼릭 링크
  20260423T060506Z/
    myproject/                                   # git worktree (named branch tas/session-20260423T060506Z)
      _workspace/
        quick/
          {YYYYmmdd_HHMMSS}/
            REQUEST.md
            DELIVERABLE.md                       # iteration 전체 최종 합성
            lessons.md                           # 누적 교훈
            checkpoint.json                      # resume 상태 (11-field 스키마)
            plan.json                            # 분류된 계획
            iteration-1/
              DELIVERABLE.md                     # 이 iteration의 출력
              logs/
                step-1-plan/
                  round-1-thesis.md, round-1-antithesis.md, ...
                  deliverable.md
                step-2-implement/
                step-3-verify/
                step-3-verify-retry-1/           # iteration 내부 FAIL 재시도
                step-4-test/
            iteration-2/                         # loop_count > 1 일 때만
              ...
```

각 세션은 이름 있는 브랜치 (`tas/session-{ts}`) 위에 올라가므로, 작업 전체를 하나의 단위로 리뷰하고 병합할 수 있습니다: `git merge tas/session-{ts}`. `LATEST` 심볼릭 링크는 `/tas --resume` 과 동반 명령 (`/tas-explain`, `/tas-workspace`, `/tas-review`) 모두의 단일 진입점입니다. PASS/HALT 이후에도 세션은 포렌식용으로 보존되며, 오래된 세션 정리는 `/tas-workspace clean` 으로 수행합니다.

`/tas` 가 중단된 경우 (컨텍스트 리셋, HALT, 네트워크 등) `/tas --resume` 으로 마지막 step 체크포인트부터 이어서 실행할 수 있습니다.

---

## 훅

플러그인은 `hooks/hooks.json`에 등록된 두 개의 훅을 제공합니다.

| 훅 | 이벤트 | 동작 |
|----|--------|------|
| `session-start.sh` | `SessionStart` | 읽기 전용 프리플라이트 — Python + `claude-agent-sdk` 점검, 없으면 설치 힌트 출력 |
| `stop-check.sh` | `Stop` | `/tas`가 실행됐지만 `DELIVERABLE.md`가 없거나 비어 있으면 세션 종료 차단. 변증법이 여전히 돌고 있으면 스킵(프로세스 감지 + mtime 체크) |

두 훅 모두 `tas`가 아닌 세션에서는 no-op이며, 재귀 방지를 위해 `stop_hook_active`를 존중합니다.

---

## 설정

| 항목 | 기본값 | 조정 방법 |
|------|--------|-----------|
| MetaAgent 모델 | `opus` | 고정 — 분류/실행은 최고 성능 모델에서 |
| 변증법 모델 (Thesis/Antithesis) | `claude-sonnet-4-6` | `agents/meta.md` step-config `model` 필드 + `runtime/dialectic.py` 폴백 |
| 워크스페이스 | `~/.cache/tas-sessions/{ts}/<project>/_workspace/quick/{timestamp}/` | 실행마다 세션 worktree + 타임스탬프로 분리 (0.2.5+); `LATEST` 심볼릭 링크가 최신 세션을 가리킴 |
| Loop count | 1 | 계획 승인 시 사용자 지정 (`loop_count`) |
| Reentry point | `구현` | 계획 승인 시 사용자 지정 (`loop_policy.reentry_point`) |
| 지속 실패 HALT | 동일 블로커 3회 연속 FAIL 후 | `loop_policy.persistent_failure_halt_after` |
| 조기 종료 | 에이전트 합의 시 허용 | `loop_policy.early_exit_on_no_improvement` |
| 출력 언어 | 영어 (사용자가 다른 언어를 명시 요청하지 않는 한) | 분류 시점에 감지 |

변증법 모델을 바꾸려면 (예: 품질을 위해 opus로, 속도를 위해 haiku로) 아래 두 곳을 모두 수정:
- `skills/tas/agents/meta.md` — step-config JSON 템플릿의 `model` 필드
- `skills/tas/runtime/dialectic.py` — `config.get("model", ...)` 폴백

---

## 파일 구조

```
tas/
├── .claude-plugin/
│   ├── plugin.json                 # 플러그인 매니페스트 (훅 등록)
│   └── marketplace.json            # 마켓플레이스 카탈로그 (단일 플러그인)
├── hooks/
│   ├── hooks.json                  # SessionStart + Stop 훅 등록
│   ├── session-start.sh            # Python/SDK 프리플라이트
│   └── stop-check.sh               # DELIVERABLE.md 무결성 가드
├── skills/
│   ├── tas/                        # 메인 변증법 워크플로우
│   │   ├── SKILL.md                # MainOrchestrator (얇은 스케줄러)
│   │   ├── agents/
│   │   │   ├── meta.md             # MetaAgent (合) — 분류 + 실행
│   │   │   ├── thesis.md           # ThesisAgent (正)
│   │   │   └── antithesis.md       # AntithesisAgent (反)
│   │   ├── runtime/
│   │   │   ├── dialectic.py        # PingPong 변증법 엔진
│   │   │   ├── run-dialectic.sh    # 셸 래퍼
│   │   │   └── requirements.txt    # claude-agent-sdk 버전 고정
│   │   └── references/
│   │       ├── workflow-patterns.md   # 4단계 정규 + 적응형 템플릿
│   │       ├── workspace-convention.md
│   │       └── recommended-hooks.md
│   ├── tas-review/SKILL.md         # 변증법 코드 리뷰
│   ├── tas-verify/SKILL.md         # 합성 후 경계값 추적
│   ├── tas-explain/SKILL.md        # 대화 요약기
│   └── tas-workspace/SKILL.md      # 워크스페이스 관리
├── CLAUDE.md                       # 개발 메타 가이드 (기여자용)
└── README.md
```

---

## 문제 해결

| 증상 | 원인 | 해결 |
|------|------|------|
| 세션 시작 시 `claude-agent-sdk is not installed` | Python SDK 미설치 | `pip install claude-agent-sdk` (또는 `pipx` / `uv`), 이후 세션 재시작 |
| `/tas`가 아무것도 안 하거나 멈춤 | 변증법 엔진 서브프로세스 사망 | `_workspace/quick/{최신}/logs/step-*/`에서 에러 확인 |
| "DELIVERABLE.md is missing"로 세션 종료 차단 | `/tas` 실행됐으나 미완료 | `/tas` 재실행, 또는 다시 종료해 오버라이드, 또는 `/tas-workspace clean` |
| 훅이 발동하지 않음 | `plugin.json`에 `"hooks"` 키 누락 | `.claude-plugin/plugin.json`에 `"hooks": "./hooks/hooks.json"` 확인 |
| `/plugin install` 이후 "Plugin not found" | 마켓플레이스 등록 시 `marketplace.json` 누락 | 리포지토리에 `.claude-plugin/marketplace.json`이 있어야 함 — 최신 pull |

---

## 라이선스

MIT
