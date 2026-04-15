# Jungle Mini DB 프로젝트

## 프로젝트 개요

본 프로젝트는 C 언어로 구현한 Mini DB에 B+ Tree 인덱스를 연결하는 것을 목표로 합니다.

이 프로젝트는 단순히 SQL 문장을 파싱하고 출력하는 프로그램이 아니라, 다음과 같은 구조를 갖는 작은 DBMS 흐름을 구현하는 데 목적이 있습니다.

- SQL 입력 처리
- fixed-row 기반 데이터 파일 저장
- 파일 기반 B+ Tree 인덱스 관리
- `id` 조건 조회 시 인덱스 사용
- 대용량 데이터에서 선형 탐색과 인덱스 탐색 비교

* * *

## 전체 아키텍처

```text
[User SQL]
    |
    v
[REPL]
    |
    v
[SQL Parser]
    |
    v
[Execution Plan]
    |
    v
[Executor]
    |
    +--> [Data File: users.csv / posts.csv]
    |
    +--> [B+ Tree Index: *.idx / *.idx.boot]
```

`SELECT *`는 데이터 파일을 순차 스캔합니다.

`SELECT ... WHERE id = ?`는 B+ Tree에서 row offset을 찾고, 데이터 파일에서 해당 row만 읽습니다.

`INSERT`는 데이터 파일 끝에 row를 추가한 뒤, 새 row의 `id -> offset`을 B+ Tree에 등록합니다.

* * *

## 목표 기능

### 필수 기능

- SQL REPL 구현
- `users`, `posts` 테이블 지원
- `select * from <table>;`
- `select * from <table> where id = <integer>;`
- `insert into <table> values (...);`
- CSV 기반 데이터 파일 저장
- 64-byte fixed row 저장
- B+ Tree 기반 `id -> row offset` 인덱스
- 프로그램 시작 시 인덱스 파일 로드
- 인덱스 파일이 없거나 깨진 경우 데이터 파일 기준 재구성

### 추가 기능

- `select * from <table> where id between <start> and <end>;`
- B+ Tree leaf 연결을 활용한 range scan
- 파일 길이와 정적 복잡도 비교
- 대규모 데이터 벤치마크 방향 정리

* * *

## 지원 SQL

```sql
select * from users;
select * from users where id = 101;
select * from users where id between 101 and 103;
insert into users values (104,new-user);
```

지원 범위는 위 문법으로 제한됩니다.

지원하지 않는 문법:

- 일반 필드 조건 조회
- join
- update
- delete
- order by
- group by

* * *

## 핵심 데이터 구조

### RowLocation

```c
typedef struct {
    long offset;
} RowLocation;
```

`RowLocation`은 데이터 파일 안에서 row가 시작되는 byte offset을 의미합니다.

### 인덱스 매핑

```text
id -> row offset
```

B+ Tree는 row 전체를 저장하지 않습니다.

대신 `id`를 key로 사용하고, 해당 row가 데이터 파일에서 시작되는 위치를 value로 저장합니다.

예를 들어 id가 `101`이면 다음 흐름으로 조회합니다.

```text
id = 101
-> B+ Tree 검색
-> row offset 획득
-> 데이터 파일 시작점에서 offset만큼 이동
-> 64-byte row 하나 읽기
```

* * *

## 저장 방식

데이터는 `data/*.csv` 파일에 저장됩니다.

파일은 사람이 읽을 수 있는 CSV 형태를 유지하지만, 내부적으로는 각 row를 64 bytes로 고정합니다.

예시:

```text
101,project-user,______________________________________________
102,second-project-user,_______________________________________
103,no-header-user,____________________________________________
```

고정 길이 row를 사용하는 이유는 B+ Tree가 저장한 offset으로 정확히 한 row를 읽기 위해서입니다.

* * *

## 인덱스 파일

각 테이블은 데이터 파일과 인덱스 파일을 함께 사용합니다.

```text
data/users.csv       users 데이터 파일
data/users.idx       users B+ Tree 노드 파일
data/users.idx.boot  users B+ Tree 메타데이터 파일

data/posts.csv       posts 데이터 파일
data/posts.idx       posts B+ Tree 노드 파일
data/posts.idx.boot  posts B+ Tree 메타데이터 파일
```

인덱스 파일이 존재하면 프로그램 시작 시 다시 엽니다.

인덱스 파일이 없거나 데이터 파일과 맞지 않으면 데이터 파일을 순차적으로 읽어 인덱스를 다시 생성합니다.

* * *

## 주요 실행 흐름

### 전체 조회

```sql
select * from users;
```

```text
1. 데이터 파일을 연다.
2. 64 bytes 단위로 row를 읽는다.
3. padding을 제거한다.
4. 모든 row를 출력한다.
```

전체 row를 출력해야 하므로 B+ Tree를 사용하지 않습니다.

### id 단건 조회

```sql
select * from users where id = 101;
```

```text
1. B+ Tree에서 id를 검색한다.
2. id에 연결된 row offset을 얻는다.
3. 데이터 파일에서 offset 위치로 이동한다.
4. 64-byte row 하나를 읽는다.
5. padding을 제거하고 출력한다.
```

### id 범위 조회

```sql
select * from users where id between 101 and 103;
```

```text
1. B+ Tree에서 시작 id가 포함된 leaf를 찾는다.
2. leaf 연결을 따라 범위 안의 key를 순회한다.
3. 각 key에 연결된 row offset을 얻는다.
4. offset 위치의 row를 읽어 출력한다.
```

### 삽입

```sql
insert into users values (104,new-user);
```

```text
1. 입력 값을 파싱한다.
2. row 크기가 64 bytes를 넘지 않는지 확인한다.
3. 데이터 파일 끝에 row를 추가한다.
4. 새 row의 offset을 계산한다.
5. B+ Tree에 id와 offset을 등록한다.
```

* * *

## 디렉토리 구조

```text
.
├── CMakeLists.txt
├── main.c
├── parser.c
├── executor.c
├── db_index.c
├── mini_db.h
├── data/
│   ├── users.csv
│   └── posts.csv
├── docs/
│   ├── 001-core-components.md
│   ├── 004-bplus-tree-index.md
│   └── 012-bplustree-c-ascii-operation-map.md
└── thirdparty/
    ├── bplustree.c
    ├── bplustree.h
    └── bplusEZtree.c
```

주요 파일:

- `main.c`: REPL 실행, 테이블 메타데이터 관리
- `parser.c`: SQL 문자열 파싱
- `executor.c`: SELECT, INSERT 실행
- `db_index.c`: B+ Tree 인덱스 파일 관리
- `mini_db.h`: 공통 타입과 함수 선언
- `thirdparty/bplustree.c`: 파일 기반 B+ Tree 구현

* * *

## 빌드 및 실행

### 빌드

```bash
cmake -S . -B cmake-build-debug
cmake --build cmake-build-debug
```

### 실행

```bash
./cmake-build-debug/jungle_mini_db
```

### 종료

```text
.exit
```

* * *

## 실행 예시

```text
mini-db> select * from users;
id,name
101,project-user
102,second-project-user
103,no-header-user

mini-db> select * from users where id = 101;
id,name
101,project-user

mini-db> select * from users where id between 101 and 103;
id,name
101,project-user
102,second-project-user
103,no-header-user

mini-db> insert into users values (104,new-user);

mini-db> select * from users where id = 104;
id,name
104,new-user
```

* * *

## 테스트 시나리오

- `select *`가 전체 row를 출력하는지 확인
- `where id = ?`가 단일 row만 출력하는지 확인
- 존재하지 않는 id 조회 시 header만 출력하는지 확인
- `between` 범위 조회가 범위 안의 row만 출력하는지 확인
- `insert` 이후 같은 id를 인덱스로 조회할 수 있는지 확인
- 중복 id insert를 거부하는지 확인
- 64-byte를 넘는 row를 거부하는지 확인
- 잘못된 SQL 문법을 거부하는지 확인

* * *

## 벤치마크 방향

대규모 데이터 테스트는 다음 기준으로 진행합니다.

- 1,000,000개 이상의 레코드 준비
- `id` 기준 SELECT는 B+ Tree 인덱스 사용
- 다른 필드 기준 SELECT는 데이터 파일 선형 탐색
- 두 방식의 실행 시간 비교

핵심은 단순한 실행 시간 수치가 아니라, 데이터가 많아질수록 전체 스캔과 인덱스 조회의 경로 차이가 어떻게 드러나는지 확인하는 것입니다.

* * *

## 코드 복잡도 비교

공통 구현 기준으로 다른 B-Tree, B+ Tree SQL 구현들과 코드 규모와 정적 복잡도를 비교했습니다.

| 항목 | 값 |
| --- | ---: |
| `.c/.h` 파일 수 | 7 |
| 전체 줄 수 | 2,671 |
| 함수 수 | 116 |
| 순환 복잡도 합계 | 420 |
| 평균 순환 복잡도 | 3.62 |
| 최대 순환 복잡도 | 12 |

이 수치는 단순히 코드가 짧다는 의미가 아니라, B+ Tree 인덱스의 핵심 흐름을 설명 가능한 크기로 유지했다는 의미로 해석했습니다.

* * *

## 발표 포인트

### 1. 파일 기반 B+ Tree 인덱스

메모리 기반 인덱스에 그치지 않고, 인덱스를 파일로 저장해 프로그램 재실행 후에도 다시 열 수 있도록 구현했습니다.

### 2. `id -> row offset` 구조

B+ Tree에 row 전체를 저장하지 않고 row 위치만 저장해, 필요한 row를 데이터 파일에서 직접 찾아 읽도록 구성했습니다.

### 3. 전체 스캔과 인덱스 조회의 분리

`select *`는 순차 스캔, `where id = ?`는 B+ Tree 조회로 실행 경로를 분리했습니다.

### 4. 범위 조회 확장

B+ Tree leaf 연결을 이용해 `between` 범위 조회까지 확장했습니다.

* * *

## 한 줄 요약

Mini DB를 단순한 SQL 파서로 끝내지 않고, B+ Tree 인덱스를 통해 row 위치를 찾아가는 DBMS의 핵심 조회 흐름을 구현한 프로젝트입니다.
