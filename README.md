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
```sql
select * from users where id = 104;
```
```text
1. 입력 값을 파싱한다.
2. row 크기가 64 bytes를 넘지 않는지 확인한다.
3. 데이터 파일 끝에 row를 추가한다.
4. 새 row의 offset을 계산한다.
5. B+ Tree에 id와 offset을 등록한다.
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

## 벤치마크
### 메모리 벤치마크
<img width="600" height="960" alt="image (1)" src="https://github.com/user-attachments/assets/abd68d49-ec31-49af-8ed4-4f6f3b9cc6dc" />

B+Tree 인덱스를 메모리에 직접 유지하는 방식과 파일 기반으로 유지하는 방식을 비교했다.
측정값은 key insert 이후 프로세스의 RSS(Resident Set Size, 실제 메모리에 올라간 프로세스 메모리) 증가량 기준이다.

| Insert key 수 | Memory 기반 인덱스 RSS 증가량 | File 기반 인덱스 RSS 증가량 |
|---:|---:|---:|
| 100,000 | 5.30 MiB | 0.03 MiB |
| 500,000 | 26.27 MiB | 0.03 MiB |
| 1,000,000 | 52.56 MiB | 0.03 MiB |
| 2,000,000 | 105.09 MiB | 0.05 MiB |
| 5,000,000 | 262.64 MiB | 0.03 MiB |
| 10,000,000 | 525.25 MiB | 0.03 MiB |

### between & where 벤치마크
<img width="480" alt="Gemini_Generated_Image_he81uohe81uohe81" src="https://github.com/user-attachments/assets/add6cd3e-a0be-47e4-a2b4-adf85efef4bb" />
<img width="480" alt="Code_Generated_Image (3)" src="https://github.com/user-attachments/assets/1b30964c-7198-4841-aa12-fd808282ea71" />

`WHERE id = ?` 단건 조회에서 B+Tree 인덱스를 사용하는 방식과 인덱스 없이 선형 탐색하는 방식을 비교했다.
측정값은 SQL parsing, 출력 formatting, 인덱스 생성, 인덱스 검증 시간을 제외한 순수 조회 경로의 평균 시간 기준이다.

단건 조회는 앞쪽 5%, 20%, 50%, 75%, 뒤쪽 95%, 존재하지 않는 id 조회 케이스를 포함한다.
각 케이스는 반복 실행했으며, 아래 표는 케이스별 `average` 값을 다시 평균낸 요약이다.

| 데이터 개수 | B+Tree 사용 평균 시간 | B+Tree 미사용 평균 시간 | 성능 차이 |
|---:|---:|---:|---:|
| 100,000 | 0.0015 ms | 0.0182 ms | 약 12배 |
| 500,000 | 0.0016 ms | 0.0996 ms | 약 61배 |
| 1,000,000 | 0.0016 ms | 0.1918 ms | 약 122배 |
| 2,000,000 | 0.0020 ms | 0.4118 ms | 약 202배 |
| 5,000,000 | 0.0016 ms | 1.0683 ms | 약 667배 |
| 10,000,000 | 0.0065 ms | 2.0461 ms | 약 313배 |


`WHERE id BETWEEN start AND start + 9` 범위 조회에서 B+Tree 인덱스를 사용하는 방식과 인덱스 없이 선형 탐색하는 방식을 비교했다.
측정값은 SQL parsing, 출력 formatting, 인덱스 생성, 인덱스 검증 시간을 제외한 순수 조회 경로의 평균 시간 기준이다.

범위 조회는 앞쪽 5%, 20%, 50%, 75%, 뒤쪽 95% 케이스를 포함한다.
각 케이스는 항상 10개 row가 나오도록 `start ~ start + 9` 범위를 사용했고, 반복 실행 후 케이스별 `average` 값을 다시 평균냈다.

| 데이터 개수 | B+Tree 사용 평균 시간 | B+Tree 미사용 평균 시간 | 성능 차이 |
|---:|---:|---:|---:|
| 100,000 | 0.0016 ms | 0.0180 ms | 약 11배 |
| 500,000 | 0.0017 ms | 0.0917 ms | 약 55배 |
| 1,000,000 | 0.0024 ms | 0.3036 ms | 약 127배 |
| 2,000,000 | 0.0016 ms | 0.3847 ms | 약 243배 |
| 5,000,000 | 0.0016 ms | 0.9605 ms | 약 593배 |
| 10,000,000 | 0.0021 ms | 2.0099 ms | 약 944배 |

성능 차이는 `B+Tree 미사용 평균 시간 / B+Tree 사용 평균 시간`으로 계산했다.
* * *

## 코드 복잡도 비교


| 레포 | 파일(.c/.h) | .c 줄 | .h 줄 | 총 줄 | 함수 | CC(Cyclomatic Complexity, 순환 복잡도) 합계 | 평균 CC | 최대 CC |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `sijun-yang/jungle-mini-db` | 7 (5/2) | 2,466 | 205 | 2,671 | 116 | 420 | 3.62 | 12 (`parser.c:read_integer`) |
| `Wish-Upon-A-Star/SQL-B-Tree` | 13 (8/5) | 7,163 | 277 | 7,440 | 240 | 2,252 | 9.38 | 97 (`executor.c:load_table_parse_snapshot`) |
| `KYUJEONGLEE/-WEEK-7-B-tree-index-db` | 22 (15/7) | 6,613 | 452 | 7,065 | 165 | 1,056 | 6.40 | 39 (`tests/test_storage.c:main`) |
| `whiskend/BPTree_SQL_Engine` | 32 (19/13) | 6,073 | 374 | 6,447 | 219 | 1,069 | 4.88 | 22 (`src/bptree.c:validate_node`) |
| `LJH098/week7_index` | 17 (11/6) | 4,351 | 365 | 4,716 | 104 | 705 | 6.78 | 38 (`src/tokenizer.c:tokenizer_tokenize_sql`) |

전체 기준으로 보면 내 프로젝트는 가장 작다. 줄 수는 `Wish-Upon-A-Star/SQL-B-Tree`의 약 36%, `KYUJEONGLEE`의 약 38%, `whiskend`의 약 41%, `LJH098`의 약 57% 수준입니다.

복잡도 합계도 내 프로젝트가 가장 낮다. `Wish-Upon-A-Star/SQL-B-Tree`는 내 프로젝트보다 CC(Cyclomatic Complexity, 순환 복잡도) 합계가 약 5.36배 높고, 평균 CC도 9.38로 가장 높다. 특히 `executor.c` 하나에 구현과 분기 처리가 크게 집중되어 있습니다.

* * *

