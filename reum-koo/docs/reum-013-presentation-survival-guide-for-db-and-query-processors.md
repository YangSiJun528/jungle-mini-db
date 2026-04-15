# reum-013 발표 대비용 DB와 처리기 심화 학습 가이드

이 문서는

- 우리 팀 문서만으로는 부족하다고 느낄 때
- 다른 팀 발표에서 나오는 용어를 알아듣고 싶을 때
- "DB 처리기"라는 말이 너무 넓어서 어디까지 공부해야 할지 막막할 때

읽는 **심화 개념 연결 문서**다.

`reum-002`가 입문자용 배경지식 문서라면,
이 문서는 그보다 한 단계 더 올라가서

- 발표에서 자주 나오는 용어
- 처리기 구조를 설명할 때 쓰는 말
- 인덱스, 저장 구조, 실행 모델, 최적화, 트랜잭션 관련 핵심 단어

를 한 문서 안에서 연결해준다.

이 문서의 목표는

> "모든 걸 완벽히 구현할 수 있게 하는 것"

이 아니라

> "발표를 들을 때 무슨 말을 하는지 이해하고, 질문도 할 수 있게 하는 것"

이다.

---

## 1. 먼저 큰 지도부터: DB 시스템은 보통 어떤 층으로 보나

다른 팀 발표를 들을 때 가장 먼저 해야 할 일은
그 팀이 **어느 층의 문제를 설명하고 있는지** 보는 것이다.

### 표 1. DB 시스템을 볼 때 자주 쓰는 큰 층

| 층 | 질문 | 대표 키워드 |
| --- | --- | --- |
| 질의 언어 층 | 사용자가 무엇을 요청하나 | SQL, query, parser |
| 계획 층 | 요청을 어떻게 실행 계획으로 바꾸나 | AST, logical plan, optimizer |
| 실행 층 | 계획을 실제로 어떻게 돌리나 | executor, operator, iterator |
| 인덱스/저장 층 | 데이터와 인덱스를 어떻게 저장하나 | page, row, B+ tree, offset |
| 시스템 층 | 안전성과 동시성을 어떻게 보장하나 | transaction, lock, WAL, MVCC |

즉 발표를 들을 때

> "이 사람은 지금 parser 얘기를 하나, optimizer 얘기를 하나, storage 얘기를 하나?"

를 먼저 잡으면 훨씬 덜 헷갈린다.

---

## 2. 처리기라는 말은 왜 이렇게 넓게 들리나

"처리기"는 생각보다 넓은 말이다.

예를 들어 발표에서 아래가 다 "처리기"처럼 들릴 수 있다.

- SQL 파서
- 쿼리 실행기
- 저장 엔진
- 인덱스 관리자
- 트랜잭션 관리자
- 스트림 처리기
- 검색 처리기

그래서 발표에서 누군가 "우리는 처리기를 만들었다"라고 하면,
바로 아래 질문을 속으로 해보면 좋다.

1. 입력이 무엇인가
2. 그 입력을 어떤 내부 구조로 바꾸는가
3. 실제 계산은 어디서 일어나는가
4. 데이터는 어디에 저장되는가
5. 결과는 무엇인가

이 다섯 질문만으로도
상당수 발표를 구조적으로 들을 수 있다.

---

## 3. 발표에서 제일 자주 나오는 파서/컴파일러 쪽 용어

SQL 처리기를 설명하다 보면
갑자기 컴파일러 같은 말이 나온다.

그건 이상한 것이 아니다.
SQL도 일종의 언어이기 때문이다.

### 표 2. 파서/컴파일러 계열 핵심 용어

| 용어 | 쉬운 뜻 | 발표에서 보통 무슨 뜻으로 쓰나 |
| --- | --- | --- |
| lexer / tokenizer | 입력 문자열을 작은 조각으로 자르는 단계 | `select`, `from`, `users` 같은 토큰 분리 |
| token | 잘라낸 최소 단위 | 키워드, 숫자, 식별자 |
| parser | 토큰들을 문법에 맞게 해석하는 단계 | SQL 문장을 구조로 바꿈 |
| grammar | 허용되는 문장 규칙 | 어떤 SQL 형태를 지원하는지 |
| AST | 추상 구문 트리 | SQL 문장을 구조화한 나무 |
| CST | 구체 구문 트리 | 괄호나 쉼표까지 더 세세히 남긴 구조 |
| semantic analysis | 의미 검사 | 테이블이 존재하는지, 컬럼 수가 맞는지 확인 |
| IR | 중간 표현 | 실행을 위해 더 다듬은 내부 구조 |
| plan | 실행 계획 | 실제로 어떤 순서로 동작할지 정한 구조 |

### 우리 프로젝트와 연결하면

- `parse_sql()`은 parser 역할
- `Plan` 구조체는 아주 단순한 AST/IR 비슷한 역할
- `execute_plan()`은 executor 역할

즉 우리는 거대한 DBMS는 아니지만,
아주 작은 형태의 "언어 처리기" 구조는 이미 갖고 있다.

---

## 4. parser를 만드는 방식도 여러 가지가 있다

다른 팀이 파서를 설명할 때
아래 방식들이 나올 수 있다.

### 표 3. 파서를 만드는 대표 방식

| 방식 | 쉬운 설명 | 장점 | 단점 |
| --- | --- | --- | --- |
| 문자열 분리 기반 | 공백, 괄호, 쉼표를 직접 나눠서 처리 | 빠르게 구현 가능 | 문법이 커지면 복잡해짐 |
| recursive descent parser | 함수들이 문법 규칙을 따라 재귀적으로 내려감 | 읽기 쉽고 직접 제어 가능 | 문법이 커지면 함수가 많아짐 |
| parser generator | Yacc/Bison 같은 도구가 파서를 생성 | 복잡한 문법 대응 가능 | 입문자에게는 추상적으로 느껴질 수 있음 |
| Pratt parser | 연산자 우선순위가 있는 식에 강함 | 표현식 처리에 좋음 | SQL 전체에 바로 쓰는 건 별도 설계 필요 |

발표를 들을 때는
"어떤 방식인가"보다

- 왜 그 방식을 골랐는지
- 이번 과제 규모에 맞는 선택이었는지

를 같이 보면 좋다.

---

## 5. parser 다음에는 보통 무엇이 나오나

SQL 문장을 구조로 바꿨다고 끝이 아니다.

보통 그 다음은:

```text
SQL 문자열
-> token
-> parser
-> AST / Plan
-> validation
-> execution
```

이다.

즉,
"parser를 만들었다"는 말은
대개 "실행 전 단계 하나를 만들었다"는 뜻이지
전체 DB를 다 만들었다는 뜻은 아니다.

---

## 6. 실행기(executor)를 설명할 때 자주 나오는 말

### 표 4. 실행기 계열 핵심 용어

| 용어 | 쉬운 뜻 | 예시 |
| --- | --- | --- |
| executor | 계획을 실제로 실행하는 부분 | `Plan`을 보고 동작 |
| operator | 실행기의 작은 부품 | scan, filter, project |
| scan | 데이터를 읽는 작업 | table scan, index scan |
| filter | 조건에 맞는 것만 남김 | `where id = 3` |
| project | 필요한 컬럼만 꺼냄 | `select name` |
| materialization | 중간 결과를 따로 저장 | 리스트나 임시 테이블에 담기 |
| pipeline | 중간 결과를 바로 다음 단계로 넘김 | filter 후 즉시 출력 |

### 발표에서 자주 나오는 비교

- table scan vs index scan
- linear scan vs point lookup
- materialize vs pipeline

우리 프로젝트도 사실 이 비교를 이미 하고 있다.

- `WHERE id = ?` 는 인덱스 경로
- `WHERE name = ?` 는 선형 탐색

---

## 7. iterator model, volcano model, pull/push는 뭐냐

조금 심화 발표에서는 이런 말이 나올 수 있다.

### iterator model / volcano model

가장 흔한 실행 모델 중 하나다.

각 operator가 보통

- `open`
- `next`
- `close`

같은 인터페이스를 가진다.

즉 부모가 자식에게
"다음 한 줄 줘"
라고 계속 물어보는 식이다.

그래서 **pull model**이라고도 부른다.

### push model

반대로 아래 단계가 위 단계로 결과를 밀어 올리는 방식이다.

### vectorized execution

한 줄씩 처리하지 않고
여러 줄을 묶어서 배치(batch)로 처리한다.

이건 보통 분석형 DB, 컬럼 저장, SIMD 친화적 설명과 같이 나온다.

### 발표에서 이렇게 들으면 된다

- `iterator` = 한 줄씩 꺼내는 방식
- `vectorized` = 여러 줄씩 묶어서 처리하는 방식

---

## 8. logical plan과 physical plan은 뭐가 다른가

이 구분은 중요하다.

### logical plan

"무엇을 해야 하는가" 중심의 계획이다.

예:

- select
- filter
- join

### physical plan

"그걸 실제로 어떤 방법으로 할 것인가" 중심의 계획이다.

예:

- table scan으로 읽기
- index scan으로 읽기
- hash join으로 합치기
- nested loop join으로 합치기

즉,

```text
logical = 해야 할 일
physical = 실제 수행 방법
```

이다.

우리 프로젝트는 아주 단순해서
거창한 logical/physical optimizer는 없지만,
그래도

- `WHERE id = ?` -> index path
- other where -> linear path

정도의 물리적 선택은 하고 있다.

---

## 9. optimizer라는 말이 나오면 무엇을 떠올리면 되나

optimizer는
"어떤 실행 방법이 더 좋을지 고르는 부분"이다.

### 표 5. optimizer 관련 핵심 단어

| 용어 | 쉬운 뜻 |
| --- | --- |
| rule-based optimizer | 정해진 규칙으로 선택 |
| cost-based optimizer | 비용 추정 후 더 싼 계획 선택 |
| cardinality estimate | 결과 행 수를 예상 |
| selectivity | 조건이 얼마나 많이 걸러낼지 |
| join order | 어떤 순서로 join할지 |

우리 프로젝트는
복잡한 optimizer까지는 없고,
거의 rule-based에 가깝다.

즉:

- id 조건이면 index
- 아니면 scan

처럼 고정된 규칙을 따른다.

---

## 10. storage engine, execution engine, query processor는 서로 같은 말인가

비슷해 보이지만 보통은 다르다.

### query processor

SQL을 받아 해석하고 실행 계획으로 바꾸고 실행까지 연결하는 넓은 층이다.

### execution engine

실행 계획을 실제로 돌리는 부분이다.

### storage engine

데이터와 인덱스를 실제로 저장/읽기/쓰기 하는 쪽이다.

즉 관계는 보통 이렇게 본다.

```text
query processor
  -> execution engine
       -> storage engine
```

발표자가 이 용어를 섞어서 써도
대략 이런 층 차이를 떠올리면 된다.

---

## 11. 저장 구조 발표에서 자주 나오는 말

### 표 6. 저장 구조 핵심 용어

| 용어 | 쉬운 뜻 |
| --- | --- |
| row store | 한 행 단위로 저장 |
| column store | 컬럼별로 따로 저장 |
| fixed-length row | 각 행 크기가 항상 같음 |
| variable-length row | 행마다 길이가 다름 |
| page / block | 디스크 저장 단위 |
| slotted page | 가변 길이 레코드를 관리하기 좋은 페이지 구조 |
| heap file | 정렬 안 된 일반 데이터 파일 |
| record id (RID) | 레코드 위치를 가리키는 식별자 |
| offset | 파일 안 byte 위치 |

### 우리 프로젝트와 연결하면

- 현재는 fixed-length row 개념이 강하다
- CSV를 fixed row처럼 다루는 부분이 있다
- `offset`은 row 위치를 가리키는 핵심 값이다

그래서 다른 팀이

- slotted page
- heap file
- RID

를 말해도
"아, 이건 저장 구조를 더 일반화한 표현이구나"
라고 이해하면 된다.

---

## 12. 인덱스 발표에서 자주 나오는 말

### 표 7. 인덱스 계열 핵심 용어

| 용어 | 쉬운 뜻 | 비고 |
| --- | --- | --- |
| primary index | 주 키 중심 인덱스 | 테이블 정렬과 연결되기도 함 |
| secondary index | 보조 인덱스 | 다른 컬럼 검색용 |
| clustered index | 데이터 저장 순서와 인덱스 순서가 강하게 연결 | InnoDB 설명에서 자주 나옴 |
| non-clustered index | 데이터와 인덱스가 분리 | 보조 인덱스 설명에서 자주 나옴 |
| covering index | 테이블까지 안 가도 필요한 값이 인덱스에 다 있음 | 매우 자주 나오는 최적화 |
| composite index | 여러 컬럼을 함께 묶은 인덱스 | `(a, b)` |
| hash index | 해시 기반 인덱스 | equality에 강함 |
| B-tree / B+ tree | 범위 검색과 정렬에 강한 대표 인덱스 | DB에서 매우 흔함 |
| LSM tree | 쓰기 많은 환경에서 자주 나오는 구조 | RocksDB 같은 이야기에서 자주 나옴 |
| bloom filter | "없음"을 빠르게 걸러내는 보조 구조 | LSM과 같이 자주 나옴 |

### 발표 들을 때 중요한 질문

1. 이 인덱스는 equality에 강한가, range에 강한가
2. 데이터와 저장 순서가 붙어 있는가
3. value로 무엇을 들고 있는가
4. 중복 key를 어떻게 처리하는가

---

## 13. B-tree vs B+ tree 발표는 어떤 포인트로 들으면 되나

### 아주 짧은 비교

| 항목 | B-tree | B+ tree |
| --- | --- | --- |
| 내부 노드 | key와 value를 가질 수 있음 | 주로 key만 |
| 리프 노드 | 값이 분산될 수 있음 | 실제 value가 주로 리프에 모임 |
| 리프 연결 | 구현마다 다름 | 보통 연결 리스트처럼 이어짐 |
| range scan | 가능 | 특히 자주 강점으로 설명됨 |

### 발표에서 자주 듣는 말

- range query에 유리하다
- fanout이 크다
- 리프 연결이 있어서 scan에 좋다
- DBMS에서 많이 쓴다

이런 말을 들으면
"리프에 값이 모여 있고, 리프끼리 이어져 있어서 순차 읽기 좋다는 뜻이구나"
라고 해석하면 된다.

---

## 14. hash index와 B+ tree는 어떻게 다르게 보나

다른 팀이 hash를 썼다면
보통 이 포인트를 보면 된다.

### hash index

- equality (`=`)에 강함
- 범위 검색에는 불리
- 구현이 비교적 직관적일 수 있음

### B+ tree

- equality도 가능
- range 검색과 정렬에 강함
- 구조는 더 복잡하지만 DB에서 널리 쓰임

즉

```text
hash = 딱 맞는 값 찾기 강자
B+ tree = 범위와 정렬까지 고려하는 만능형
```

정도로 기억하면 된다.

---

## 15. LSM tree가 나오면 어떻게 이해하나

발표에서 LSM tree가 나오면
보통 "쓰기 성능" 이야기가 같이 나온다.

아주 단순화하면:

1. 메모리에 먼저 쓴다
2. 나중에 디스크 파일로 내린다
3. 여러 파일을 합치는 compaction이 필요하다

즉 B-tree류와는 철학이 조금 다르다.

### LSM에서 자주 듣는 말

- memtable
- SSTable
- compaction
- bloom filter
- write-optimized

이건 "쓰기 많은 환경"을 위한 세계라고 생각하면 된다.

---

## 16. transaction, ACID, WAL, MVCC는 꼭 알아야 하나

발표를 알아듣기 위해서는 **핵심 뜻 정도는** 아는 것이 좋다.

### 표 8. 트랜잭션/복구 핵심 용어

| 용어 | 쉬운 뜻 |
| --- | --- |
| transaction | 여러 작업을 하나의 묶음처럼 처리 |
| ACID | 트랜잭션이 지켜야 할 대표 성질 |
| atomicity | 전부 하거나 전부 안 하거나 |
| consistency | 규칙이 깨지지 않게 |
| isolation | 동시에 해도 서로 덜 꼬이게 |
| durability | 끝난 작업은 남게 |
| WAL | 먼저 로그를 쓰고 나중에 데이터 반영 |
| checkpoint | 중간 저장 지점 |
| recovery | 장애 후 복구 |
| MVCC | 동시에 여러 버전을 보게 해서 충돌을 줄이는 방식 |

우리 프로젝트는 여기까지 구현하지 않지만,
다른 팀 발표에서 이 말을 쓰면
"아, 저장/동시성/복구 쪽 이야기구나"
하고 층을 구분할 수 있어야 한다.

---

## 17. lock, latch, mutex는 서로 어떻게 다르나

이건 헷갈리기 좋다.

### 아주 거칠게 보면

- `lock`
  - 데이터의 논리적 충돌을 막는 말로 자주 씀
- `latch`
  - 아주 짧고 내부적인 구조 보호에 자주 씀
- `mutex`
  - 프로그래밍 언어/OS 수준의 상호배제 도구

발표에서 이 셋을 정확히 구분하지 않아도,
"동시 접근을 막는 얘기구나"
까지 이해하면 1차로는 충분하다.

---

## 18. 성능 발표를 들을 때 꼭 봐야 하는 것

속도 숫자만 보면 안 된다.

### 표 9. 성능 발표 체크리스트

| 봐야 할 것 | 이유 |
| --- | --- |
| 데이터 개수 | 1만 건과 100만 건은 다르다 |
| key 분포 | dense/sparse에 따라 결과가 달라질 수 있다 |
| 삽입 순서 | sorted/random/reverse에 따라 split 패턴이 달라진다 |
| 조회 패턴 | random, sequential, hot-spot이 다르다 |
| 측정 단위 | latency, throughput, ops/s를 구분해야 한다 |
| 무엇을 측정했는가 | parser 포함인지, tree core만인지 다르다 |
| 검증을 했는가 | 빠르기만 하고 값이 틀리면 의미가 없다 |

즉 발표를 들을 때

> "무엇을 얼마나 어떤 조건에서 잰 거지?"

를 계속 물어봐야 한다.

---

## 19. complexity와 성능은 어떻게 다르게 보나

어떤 팀은 시간복잡도를 말하고,
어떤 팀은 실제 측정값을 말할 것이다.

둘은 다르다.

### 시간복잡도

- 이론적 성장률
- 예: `O(log n)`

### 실제 성능

- 구현, 메모리 배치, 캐시, 상수항, 컴파일러, I/O의 영향을 받음
- 같은 `O(log n)`이어도 실제 속도는 크게 다를 수 있음

그래서 발표에서

- 이론
- 실험

이 둘이 같이 나오는 것이 가장 좋다.

---

## 20. "우리 프로젝트"를 더 넓은 DB 세계에 놓고 보면

우리 프로젝트는 대략 이런 위치에 있다.

### 구현한 것

- 작은 SQL 처리기
- 단순 parser
- 단순 executor
- 메모리 기반 B+ tree 인덱스
- 파일 기반 row 저장
- 일부 성능 비교

### 아직 안 한 것

- full optimizer
- join 처리기
- transaction
- WAL / recovery
- buffer pool
- MVCC
- distributed execution

즉 우리 프로젝트는
**DB 전체 중에서 parser/executor/index/storage의 기초 부분을 축소판으로 다뤘다**
고 보면 된다.

그래서 다른 팀이 더 복잡한 말을 하더라도
"우리가 만든 작은 조각을 더 키우면 저런 세계로 간다"
고 연결하면 된다.

---

## 21. 발표를 들으면서 바로 써먹을 수 있는 질문

발표를 듣고 질문할 때는
아래 질문들이 좋다.

### 구조 질문

1. parser, planner, executor 중 어디까지 구현했나요?
2. 저장 엔진과 실행 엔진은 분리되어 있나요?
3. 인덱스 value로 무엇을 저장하나요? offset, row id, pointer 중 무엇인가요?

### 인덱스 질문

1. 왜 B+ tree를 골랐나요?
2. hash index나 다른 구조와 비교했나요?
3. range query도 고려했나요?

### 성능 질문

1. benchmark는 어떤 입력 분포로 측정했나요?
2. core tree 성능과 DB 전체 성능을 분리해서 봤나요?
3. correctness 검증은 어떻게 했나요?

### 저장 구조 질문

1. fixed-length row인가요, variable-length row인가요?
2. 페이지 구조를 썼나요?
3. 디스크 복원은 어떻게 하나요?

이 질문들은
단순히 공격적인 질문이 아니라
발표 내용을 더 구조적으로 이해하는 데 도움이 된다.

---

## 22. 발표에서 특히 헷갈리는 말들을 짧게 번역하면

### 표 10. 발표장 생존 번역표

| 발표에서 들리는 말 | 머릿속 번역 |
| --- | --- |
| query processor | SQL 요청을 해석하고 실행까지 연결하는 층 |
| execution engine | 실제 연산을 돌리는 부분 |
| storage engine | 데이터 저장/읽기/쓰기 쪽 |
| logical plan | 해야 할 일 목록 |
| physical plan | 실제 수행 방법 |
| operator | 실행기의 작은 부품 |
| scan | 읽기 |
| filter | 조건으로 거르기 |
| projection | 필요한 컬럼만 뽑기 |
| materialize | 중간 결과를 따로 저장 |
| pipeline | 바로 다음 단계로 넘기기 |
| clustered index | 데이터 순서와 인덱스가 강하게 연결 |
| secondary index | 보조 인덱스 |
| WAL | 로그 먼저 쓰기 |
| MVCC | 여러 버전을 같이 관리 |

---

## 23. 이 문서를 읽고 나면 무엇이 달라져야 하나

이 문서를 읽고 나면
최소한 아래 정도는 할 수 있으면 좋다.

1. 발표자가 parser 얘기인지 storage 얘기인지 구분할 수 있다
2. B-tree, B+ tree, hash, LSM이 어느 정도 다르다는 걸 설명할 수 있다
3. logical plan과 physical plan 차이를 말할 수 있다
4. benchmark 결과를 볼 때 조건을 같이 봐야 한다는 걸 안다
5. transaction, WAL, MVCC가 "우리 프로젝트 밖의 큰 DB 기능"이라는 걸 안다

---

## 24. 이 문서 다음에 무엇을 읽으면 좋은가

### 우리 코드와 연결하고 싶다면

1. `reum-006`
2. `reum-007`
3. `reum-008`

### B-tree 파라미터가 더 궁금하다면

1. `reum-012`

### 결과와 비교 관점이 궁금하다면

1. `reum-010`

### 전체 순서를 다시 보고 싶다면

1. `reum-000`

---

## 25. 한 줄 요약

> 발표장에서 나오는 DB 용어는  
> parser, plan, executor, storage, index, transaction, benchmark  
> 여섯 덩어리로 나눠 들으면 훨씬 이해하기 쉽다.
