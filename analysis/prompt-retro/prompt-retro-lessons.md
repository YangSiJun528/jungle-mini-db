# Prompt Retro Lessons

## Scope

분석 대상 로그:

- `logs/sijun-yang-prompt-log.jsonl`
- `logs/HyunSeongLee-prompt-log.jsonl`
- `logs/Kyumin_Kim-prompt-log.jsonl`
- `logs/cloud-9-git-prompt-log.jsonl`

시간대 기준:

- 원본 timestamp: UTC offset 포함 ISO timestamp
- 보고 timestamp: `Asia/Seoul`
- primary 분석 범위: 2026-04-12 21:22:01 KST부터 2026-04-15 23:51:51 KST까지

산출물:

- 사용자별 정규화 CSV: `sijun-yang-normalized.csv`, `HyunSeongLee-normalized.csv`, `Kyumin_Kim-normalized.csv`, `cloud-9-git-normalized.csv`
- 사용자별 세션 CSV: `sijun-yang-sessions.csv`, `HyunSeongLee-sessions.csv`, `Kyumin_Kim-sessions.csv`, `cloud-9-git-sessions.csv`
- 전체 CSV: `combined-normalized.csv`, `combined-sessions.csv`
- 노이즈 제외 CSV: `combined-primary-normalized.csv`, `combined-primary-sessions.csv`

## Exclusions

`combined-primary-*` 산출물에서는 다음 7개 row를 제외했다.

- title-generation wrapper prompt: 2개
- skill command: `$prompt-logging-hook-setup`, `$prompt-retro-analysis`, `$prompt-retro-analysis logs 파일 보고 해줘.` 총 3개
- hook smoke test: `hook test` 1개
- bare test prompt: `내 말 들리냐` 1개

전체 원본 row는 277개이고, primary 분석 기준 row는 270개다.

## Key Observations

- primary 기준 사용자별 prompt 수는 `sijun-yang` 176개, `HyunSeongLee` 51개, `Kyumin_Kim` 24개, `cloud-9-git` 19개다.
- primary 기준 session은 22개다. context rating은 `explicit` 9개, `mostly_explicit` 9개, `mixed` 4개다.
- 사용 모델은 primary 기준 전부 `gpt-5.4`다. 제외된 title-generation wrapper에만 `gpt-5.4-mini`가 섞여 있었다.
- repair signal은 8개다. `sijun-yang` 6개, `HyunSeongLee` 2개이고, 대부분 빌드/벤치마크/예외처리 또는 개념 이해 막힘에서 발생했다.
- context dependency signal은 42개다. `sijun-yang` 35개, `HyunSeongLee` 7개다.
- 파일 참조는 `sijun-yang` 34개, `Kyumin_Kim` 24개, `cloud-9-git` 18개, `HyunSeongLee` 1개다. IDE context를 많이 붙인 사용자일수록 프롬프트가 길고 재현성도 높았다.
- 주제는 SQL 처리기와 저장 구조, B+ tree/index, 문서화, Git 작업, 빌드/테스트/디버깅이 반복해서 나타났다.

## Author Alignment

Git commit author 집합은 다음과 같다.

- `sijun-yang`
- `HyunSeongLee`
- `Kyumin_Kim`
- `cloud-9-git`
- `이현성`

prompt prefix는 `sijun-yang`, `HyunSeongLee`, `Kyumin_Kim`, `cloud-9-git` 모두 commit author와 exact match가 있었다. mismatch session은 없다.

단, Git history에는 `이현성` author도 있으나 prompt prefix는 `HyunSeongLee`로 기록되어 있다. exact match 기준으로는 문제가 없지만, 사람 단위 분석에서는 `HyunSeongLee`와 `이현성`을 alias로 묶을지 별도 정책을 정하는 편이 좋다.

## Strong Patterns

- 요구사항 전문을 붙이고 “핵심 구성 3가지만”, “문서 번호 016”, “sijun-yang 하위 README”처럼 산출물 범위를 지정한 프롬프트는 결과 검증이 쉽다.
- `Kyumin_Kim`과 `cloud-9-git` 로그처럼 IDE context가 포함된 프롬프트는 파일 경로와 현재 탭이 남아 있어 후속 분석에서 재현성이 높다.
- “이 README대로 실행하니까 다음 에러 발생”처럼 명령, stdout, stderr를 함께 준 프롬프트는 디버깅 전환이 빠르다.
- 벤치마크 프롬프트에서 실행 명령과 관측 수치를 같이 제공한 경우, 단순 구현 요청이 아니라 성능 해석과 버그 판별까지 이어질 수 있었다.
- 문서 작업은 “독자 수준”, “문서 번호”, “표와 그림 활용”, “발표 신경 안 써도 됨”처럼 제약을 붙였을 때 결과물 의도가 명확했다.

## Weak Patterns

- `Implement the plan.`, `ㄱㄱ`, `진행해줘`, `이름 변경해줘`, `해당 관련 내용 커밋 ㄱㄱ` 같은 짧은 후속 프롬프트는 같은 session 안에서는 빠르지만, 로그만 보고는 의도 복원이 어렵다.
- “그거”, “그런 부분”, “그것도” 같은 지시어는 IDE context가 없으면 대상이 사라진다. 특히 Git, 파일 이동, 커밋 범위 결정처럼 되돌리기 부담이 있는 작업에서는 위험하다.
- 일부 session은 긴 시간 동안 이어져서 session duration이 실제 작업 집중 시간을 과대평가한다. 예를 들어 하루를 넘긴 session은 중간 휴식까지 포함하므로 duration만으로 생산성을 판단하면 안 된다.
- `HyunSeongLee` 로그는 짧은 질문형 프롬프트가 많아 학습 흐름은 잘 보이지만, 파일 경로가 적게 남아 코드 위치 추적성은 낮다.
- `cloud-9-git` 로그는 IDE context 덕분에 파일 참조는 좋지만, “그럼 그런 부분 수정해 줄래?” 같은 요청은 실제 판단 기준을 assistant가 직전 답변에 의존하게 만든다.

## Context Management

세션 기반 context rating은 대체로 양호하다. 22개 primary session 중 18개가 `explicit` 또는 `mostly_explicit`이다.

`mixed`로 떨어진 session은 모두 `sijun-yang` prefix에 몰려 있다. 원인은 긴 작업 중 `Implement the plan.`, `ㄱㄱ`, `진행해줘` 같은 압축 지시가 반복된 것이다. 이 방식은 속도는 빠르지만, session이 끊기거나 다른 agent가 이어받으면 실패 가능성이 커진다.

좋은 흐름:

```text
요구사항 또는 에러 로그 제공
-> 산출물 기준 지정
-> 계획 수립
-> Implement the plan
-> 테스트 또는 커밋 범위 지정
```

취약한 흐름:

```text
짧은 후속 지시
-> 상태 변화
-> 다시 짧은 후속 지시
-> 커밋 또는 파일 변경 요청
```

특히 커밋 요청은 “전체 변경”, “문서 작업만”, “통계 결과 제외”, “sijun-yang 하위만”처럼 범위를 적은 경우가 좋았다. 이 패턴은 계속 유지할 만하다.

## User Notes

`sijun-yang`:

- 가장 많은 로그와 가장 넓은 작업 범위를 가진다. SQL 처리기, B+ tree, 벤치마크, 문서화, Git 커밋 작업이 모두 섞여 있다.
- context-dependent prompt가 35개로 많다. 빠른 진행에는 효과적이지만, 위험한 작업에서는 마지막 한 줄에 대상과 범위를 다시 쓰는 습관이 필요하다.

`HyunSeongLee`:

- 질문 중심 학습 흐름이 뚜렷하다. `handle`, `init_tree`, 실행 방법, 테스트 커맨드처럼 이해 막힘을 빠르게 해소하려는 패턴이다.
- 파일 경로와 코드 위치를 더 자주 넣으면 학습 로그가 나중에 문서화 자료로도 좋아진다.

`Kyumin_Kim`:

- primary 24개 모두 파일 참조가 있다. IDE context 기반 요청이 많아 재현성이 높다.
- prompt 수는 적지만 context rating은 `explicit`으로 좋다.

`cloud-9-git`:

- 문서화와 브랜치/커밋 작업 비중이 높다.
- IDE context가 풍부해서 추적성은 좋지만, 직전 assistant 답변을 가리키는 짧은 요청은 명시성을 조금 더 보강하는 편이 낫다.

## Reusable Rules

- 위험한 Git 작업은 마지막 문장에 포함 범위를 다시 적는다. 예: `sijun-yang 하위 변경만 커밋`, `통계 결과 제외`.
- `Implement the plan`을 쓰기 전에 plan이 같은 session 안에 있고, 파일 범위가 명확한지 확인한다.
- 디버깅 요청에는 실행 명령, 전체 에러, 기대 동작, 방금 바꾼 파일을 같이 넣는다.
- 문서 요청에는 문서 번호, 대상 독자, 포함할 근거 자료, 제외할 범위를 함께 쓴다.
- 학습 질문에는 파일명과 함수명을 같이 넣는다. 예: `db_index.c의 init_tree(handle, ...)`.
- “그거”, “이거”, “그런 부분”을 쓰더라도 뒤에 괄호로 실제 대상을 붙인다.
