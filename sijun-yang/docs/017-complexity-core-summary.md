# 복잡도 비교 핵심 요약과 코드 구조 해석

이 문서는 `016-repository-complexity-comparison.md`의 핵심 요약판이다. 숫자 자체보다 용어를 쉽게 풀고, 실제 코드에서 차이가 잘 드러나는 영역을 비교한다.

## 1. 용어를 쉽게 풀어 보기

| 용어 | 뜻 | 읽는 방법 |
|---|---|---|
| `.c` 파일 | 실제 동작이 들어 있는 구현 파일 | 줄 수가 많을수록 실행 로직, 예외 처리, 분기가 많을 가능성이 크다. |
| `.h` 파일 | 외부에 공개하는 타입, 상수, 함수 선언 파일 | 줄 수가 많으면 모듈 사이 계약이 많거나 구조체가 복잡한 편이다. |
| 줄 수 | 파일의 물리적인 길이 | 코드 양의 1차 지표다. 단, 긴 주석과 테스트도 같이 늘릴 수 있다. |
| 함수 수 | 기능을 몇 개 단위로 나눴는지 | 함수 수가 많다고 나쁜 것은 아니다. 큰 함수를 쪼개면 오히려 좋아질 수 있다. |
| CC | Cyclomatic Complexity, 순환 복잡도 | `if`, `for`, `while`, `case`, `&&` 같은 분기 수를 기반으로 한 복잡도 추정치다. |
| 평균 CC | 함수 하나당 평균 분기 복잡도 | 전체 코드가 전반적으로 읽기 쉬운지 보는 데 좋다. |
| 최대 CC | 가장 복잡한 함수 하나의 복잡도 | 유지보수 위험이 몰린 함수를 찾는 데 좋다. |
| 핵심 구현 기준 | 테스트, 벤치마크, 도구 파일을 뺀 비교 | 실제 제품 코드끼리 비교할 때 더 공정하다. |

CC는 "함수를 읽을 때 머릿속으로 따라가야 하는 길의 수"에 가깝다. `if`가 많고, 루프 안에 조건이 겹치고, 여러 연산자가 붙으면 한 함수 안에서 가능한 실행 경로가 늘어난다.

## 2. 한눈에 보는 핵심 결론

| 레포 | 핵심 구현 줄 수 | 핵심 평균 CC | 가장 복잡한 핵심 함수 | 구조 요약 |
|---|---:|---:|---|---|
| `sijun-yang/jungle-mini-db` | 2,671 | 3.62 | `parser.c:read_integer` / 12 | 기능 범위가 좁고, B+Tree는 `db_index.c` 뒤에 감싼 구조 |
| `Wish-Upon-A-Star/SQL-B-Tree` | 6,216 | 9.77 | `executor.c:load_table_parse_snapshot` / 97 | SQL 기능과 인덱스 경로가 매우 넓고 `executor.c`에 집중 |
| `KYUJEONGLEE/-WEEK-7-B-tree-index-db` | 6,048 | 6.17 | `src/tokenizer.c:tokenizer_tokenize_sql` / 38 | 토크나이저, 파서, 스토리지, 인덱스가 분리되어 있지만 기능 범위가 큼 |
| `whiskend/BPTree_SQL_Engine` | 4,845 | 6.66 | `src/bptree.c:validate_node` / 22 | 파일 수는 많지만 책임이 잘게 나뉜 모듈형 구조 |
| `LJH098/week7_index` | 4,263 | 6.64 | `src/tokenizer.c:tokenizer_tokenize_sql` / 38 | `KYUJEONGLEE`와 비슷하나 범위가 조금 작음 |

핵심만 보면 내 프로젝트는 가장 작고 평균 복잡도도 가장 낮다. 이유는 명확하다.

- SQL 문법을 `SELECT * FROM table [WHERE id = n]`과 `INSERT INTO table VALUES ...` 중심으로 제한했다.
- 실행 경로가 `전체 조회`, `id 조회`, `insert`로 작게 갈라진다.
- B+Tree 구현은 직접 모든 곳에 흩뿌리지 않고 `db_index.c`에서 `db_index_get`, `db_index_put` 형태로 감쌌다.

반대로 외부 프로젝트들은 더 많은 SQL 기능을 다룬다. 그래서 코드가 길고 복잡한 것이 단순히 "나쁘다"는 뜻은 아니다. 지원 범위가 넓으면 파싱, 검증, 예외 처리, 인덱스 선택 로직이 자연스럽게 늘어난다.

## 3. 실제 코드 비교 1: SQL을 읽는 방식

### 내 프로젝트

흐름은 단순한 문자열 커서 방식이다.

```text
parse_sql
-> starts_with("select") 또는 starts_with("insert")
-> parse_select / parse_insert
-> Plan 생성
```

특징:

- 별도 토크나이저가 없다.
- `parser.c`가 입력 문자열을 직접 앞으로 이동시키며 읽는다.
- 지원 문법이 좁아서 코드가 짧다.
- 확장성은 낮다. 예를 들어 `SELECT name FROM users`나 `WHERE age >= 20` 같은 문법을 추가하려면 직접 커서 파싱 함수를 계속 늘려야 한다.

### Wish-Upon-A-Star/SQL-B-Tree

흐름은 렉서와 파서가 분리되어 있다.

```text
init_lexer
-> get_next_token
-> parse_statement
-> SELECT / INSERT / UPDATE / DELETE 분기
```

특징:

- `lexer.c`가 문자열을 토큰으로 바꾼다.
- `parser.c`는 토큰 타입으로 SQL 문장을 해석한다.
- `SELECT`, `INSERT` 외에 `UPDATE`, `DELETE`, `BETWEEN`, 여러 `WHERE` 조건까지 다룬다.
- 문법 범위가 넓어지는 만큼 파서보다 실행기 쪽 복잡도가 훨씬 커졌다.

### KYUJEONGLEE / LJH098

두 프로젝트는 구조가 매우 비슷하다.

```text
tokenizer_tokenize
-> parser_parse
-> parser_parse_insert / parser_parse_select / parser_parse_delete
-> executor_execute
```

특징:

- 토크나이저와 파서가 분리되어 있다.
- 토큰 캐시가 있어 같은 SQL을 다시 처리할 때 재사용할 수 있다.
- `INSERT (columns) VALUES (values)` 형태, `SELECT columns FROM ... WHERE ...`, `DELETE`를 다룬다.
- `tokenizer_tokenize_sql`의 CC가 38로 높다. 문자열, 숫자, 연산자, 따옴표 문자열, 구분자, 캐시 처리가 한 영역에 몰려 있기 때문이다.

### whiskend/BPTree_SQL_Engine

흐름은 가장 모듈형에 가깝다.

```text
tokenize_sql
-> parse_statement / parse_next_statement
-> Statement AST
-> execute_statement
```

특징:

- 토큰 배열, AST, 실행 결과, 에러 버퍼가 명확히 나뉜다.
- 문자열 리스트와 literal 리스트를 동적으로 할당한다.
- 파일 수는 많아지지만, 한 함수의 최대 복잡도는 상대적으로 낮다.
- 에러 메시지와 상태 코드를 모듈 사이에 넘기는 구조라 코드가 길어지는 대신 책임이 분산된다.

## 4. 실제 코드 비교 2: SELECT가 인덱스를 타는 방식

### 내 프로젝트

내 프로젝트는 조건이 `id = 값`일 때만 인덱스를 사용한다.

```text
execute_select
-> 조건 없음: execute_select_all_fixed_rows
-> id 조건: execute_select_by_id
-> db_index_get
-> fixed row offset으로 한 행 읽기
```

이 구조의 장점은 읽기 쉽다는 점이다. `executor.c`는 "인덱스를 쓸지 말지"를 복잡하게 판단하지 않는다. `id 조건이면 인덱스, 아니면 전체 스캔`이라는 규칙 하나만 있다.

대신 기능은 제한된다. `id` 외의 컬럼 검색, 범위 검색, 여러 조건 조합은 지원하지 않는다.

### Wish-Upon-A-Star/SQL-B-Tree

이 프로젝트는 인덱스 선택 로직이 가장 넓다.

```text
execute_select
-> choose_index_condition
-> PK B+Tree 조회
-> UK 문자열 B+Tree 조회
-> BETWEEN 범위 조회
-> 필요하면 tail scan 또는 linear scan
```

특징:

- 기본키 인덱스뿐 아니라 unique key 문자열 인덱스도 다룬다.
- `BETWEEN` 범위 검색이 있다.
- 캐시된 영역과 아직 캐시되지 않은 tail 영역을 나누어 처리한다.
- 그래서 `executor.c`가 4,448줄까지 커지고, 실행 경로가 한 파일에 많이 모였다.

### KYUJEONGLEE

`players` 테이블 중심으로 B+Tree 인덱스 세트를 캐시한다.

```text
executor_get_cached_player_indexes
-> index_build_player_indexes
-> id B+Tree / game_win_count B+Tree
-> executor_execute_select_with_mode
```

특징:

- `id`는 단일 row index 조회에 유리하다.
- `game_win_count`는 같은 값이 여러 개 나올 수 있어 row index list를 둔다.
- INSERT/DELETE 뒤에는 캐시 무효화가 필요하다.
- 내 프로젝트보다 조회 기능이 넓지만, 캐시와 row index 동기화 책임이 생긴다.

### LJH098

`SELECT ... WHERE`가 있으면 실행 시점에 테이블 인덱스를 만든다.

```text
executor_collect_indexed_rows
-> index_build
-> index_query_equals 또는 index_query_range
-> offset 목록으로 row 읽기
```

특징:

- 등호 검색은 hash 기반 equality index를 쓴다.
- 범위 검색은 정렬된 range entry와 lower/upper bound를 쓴다.
- B+Tree라기보다는 "조회 시점에 만드는 보조 인덱스"에 가깝다.
- 매번 인덱스를 만들면 구현은 단순하지만, 큰 테이블에서는 반복 SELECT 비용이 커질 수 있다.

### whiskend/BPTree_SQL_Engine

`id` 조건만 B+Tree 인덱스를 사용하고, 나머지는 full scan으로 보낸다.

```text
can_use_id_index
-> execute_select_with_id_index
-> bptree_search
-> read_row_at_offset
```

특징:

- 내 프로젝트와 비슷하게 `id` 조건을 핵심 인덱스 경로로 둔다.
- 차이는 모듈 경계다. `ExecutionContext`, `TableRuntime`, `ExecResult`, `errbuf`를 통해 실행 상태와 에러를 명확히 전달한다.
- 기능은 내 프로젝트보다 일반화되어 있지만, Wish 프로젝트처럼 여러 종류의 인덱스를 선택하지는 않는다.

## 5. 실제 코드 비교 3: B+Tree / 인덱스의 위치

| 레포 | 인덱스 구현 방식 | 장점 | 부담 |
|---|---|---|---|
| `sijun-yang` | `thirdparty/bplustree.c`를 `db_index.c`가 감싼다 | 실행기는 `db_index_get/put`만 알면 된다 | B+Tree 내부는 외부 코드라 구조 이해가 별도 필요 |
| `Wish-Upon-A-Star` | 숫자 B+Tree와 문자열 B+Tree를 직접 구현 | PK, UK, range까지 넓게 지원 | B+Tree와 executor가 함께 커져 복잡도가 집중된다 |
| `KYUJEONGLEE` | B+Tree + player 전용 index manager | 특정 테이블 요구사항에 맞춘 최적화가 가능 | 범용 DB라기보다 과제 도메인에 묶인다 |
| `whiskend` | `src/bptree.c`와 runtime/executor를 분리 | B+Tree 모듈을 독립적으로 검증하기 쉽다 | status, errbuf, runtime 구조가 늘어난다 |
| `LJH098` | hash equality + sorted range index | 구현이 직관적이고 WHERE 비교가 넓다 | 전통적인 B+Tree 인덱스 구조는 아니다 |

내 프로젝트의 핵심 장점은 "실행기에서 인덱스 내부를 몰라도 된다"는 점이다. `executor.c`는 `db_index_get`, `db_index_put`만 호출한다. 실제 B+Tree 파일 포맷, boot 파일, node split 같은 세부사항은 `db_index.c`와 `thirdparty/bplustree.c`에 갇혀 있다.

## 6. 어떤 코드가 더 좋은가?

단순히 줄 수가 적다고 항상 더 좋은 코드는 아니다. 비교 기준은 목적에 따라 달라진다.

내 프로젝트처럼 학습용 미니 DB에서 `id` 인덱스의 원리를 보여주는 것이 목적이면, 현재 구조가 좋다.

- 읽을 파일이 적다.
- 실행 흐름이 짧다.
- `id -> offset -> row` 관계가 잘 보인다.
- 평균 CC가 낮아 설명하기 쉽다.

반대로 SQL 엔진처럼 기능 범위를 넓히는 것이 목적이면 `whiskend` 방식이 더 확장하기 좋다.

- lexer, parser, executor, storage, runtime, result가 분리되어 있다.
- 에러와 실행 결과를 구조체로 주고받는다.
- 파일 수는 많지만 책임이 분산된다.

`Wish-Upon-A-Star`는 기능 폭은 가장 넓지만, `executor.c`에 많은 책임이 몰려 있다. 기능 시연에는 강하지만 유지보수 관점에서는 가장 먼저 분리하고 싶은 구조다.

## 7. 내 프로젝트 기준 개선 포인트

현재 코드의 장점을 유지하면서 개선한다면 우선순위는 다음이 적당하다.

1. `parser.c`는 당장 토크나이저로 갈아엎기보다, 지원 SQL을 늘릴 때만 분리한다.
2. `executor.c`는 지금처럼 `SELECT all`, `SELECT by id`, `INSERT` 흐름을 유지한다.
3. `db_index.c`는 좋은 경계다. B+Tree 세부사항이 실행기로 새지 않게 유지한다.
4. 기능을 추가한다면 `WHERE id = n` 다음 단계로 `WHERE id BETWEEN a AND b`가 가장 자연스럽다.
5. 여러 컬럼 인덱스를 넣기 전에는 인덱스 메타데이터 구조를 먼저 설계해야 한다.

요약하면, 내 프로젝트는 "작고 읽기 쉬운 B+Tree 인덱스 미니 DB"로는 가장 설명하기 쉽다. 외부 프로젝트들은 더 많은 SQL 기능과 인덱스 경로를 담고 있어 복잡도가 높다. 특히 차이는 파서보다 SELECT 실행기와 인덱스 선택 로직에서 크게 드러난다.
