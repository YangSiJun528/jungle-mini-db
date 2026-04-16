# B+Tree 발표 피드백 질문과 개념 정리

이 문서는 `hyun/` 아래 시연 코드를 기준으로, 발표 질의응답에서 나온 질문의 의도와 당시 답변의 한계, 그리고 이후에 가져가야 할 개념적 방향을 정리한다.

목적은 답변 스크립트를 만드는 것이 아니다. 다음 발표나 회고에서 어떤 뉘앙스와 논리 흐름으로 이해를 정리해야 하는지 잡는 것이다.

## 1. 현재 시연 코드 구조

현재 시연 코드는 `users`, `posts` 두 테이블을 고정 schema로 둔다.

| 테이블 | 컬럼 |
|---|---|
| `users` | `id`, `name` |
| `posts` | `id`, `title` |

각 테이블은 CSV 데이터 파일과 B+Tree index 파일을 가진다.

| 테이블 | 데이터 파일 | 인덱스 파일 |
|---|---|---|
| `users` | `data/users.csv` | `data/users.idx`, `data/users.idx.boot` |
| `posts` | `data/posts.csv` | `data/posts.idx`, `data/posts.idx.boot` |

row 저장 방식은 64 bytes fixed row다.

| 항목 | 값 |
|---|---|
| row 전체 크기 | `ROW_SIZE = 64` |
| 실제 데이터 영역 | `ROW_DATA_SIZE = 63` |
| 마지막 byte | `\n` |
| 남는 공간 | `_` padding |

B+Tree index entry는 다음 구조다.

| 구분 | 현재 구현 |
|---|---|
| key | `id` 정수 |
| value | CSV 파일 안의 byte offset + 1 |

`+ 1`을 하는 이유는 사용한 B+Tree 라이브러리에서 value `0`을 delete 의미로 사용하기 때문이다. 실제 첫 row의 offset은 `0`일 수 있으므로, index에는 `offset + 1`을 저장하고 읽을 때 `stored_offset - 1`로 복원한다.

현재 구현된 기능은 다음이다.

| 기능 | 현재 상태 |
|---|---|
| `WHERE id = n` | B+Tree에서 offset을 찾고 해당 row 하나만 읽음 |
| `WHERE id BETWEEN a AND b` | B+Tree leaf range scan으로 offset을 순회 |
| INSERT | id 직접 입력, 중복 id 확인, CSV append, index 갱신 |
| 재시작 | index 파일이 없거나 CSV와 불일치하면 CSV 기준으로 재생성 |

현재 구현하지 않은 것은 다음이다.

| 항목 | 현재 상태 |
|---|---|
| auto increment | 없음. INSERT 시 id 직접 입력 |
| next id 메타데이터 | 없음 |
| variable length row | 없음. 64 bytes fixed row만 지원 |
| binary row format | 없음. CSV text 기반 |
| 문자열 컬럼 인덱스 | 없음 |
| non-unique secondary index | 없음 |
| DELETE / UPDATE | 없음 |
| page/slot 기반 record manager | 없음 |

## 2. 질문: 고정 길이 row는 공간 낭비 아닌가

### 질문했던 것

질문자는 CSV row를 고정 길이로 만들면 짧은 값이 들어왔을 때 남는 공간이 전부 낭비되는 것 아니냐고 물었다.

질문의 초점은 두 가지였다.

- 왜 row 크기를 고정했는가
- 공간 낭비를 없애려면 어떤 구조가 필요한가

### 답변했던 것

당시 답변의 방향은 다음에 가까웠다.

- row 크기가 고정되어 있어야 offset으로 해당 row를 바로 읽을 수 있다고 봤다.
- MySQL row 최대 크기 사례를 근거처럼 언급했다.
- 공간 낭비를 줄이는 방법은 충분히 고민하지 못했다고 답했다.

이 답변에서 현재 구현 설명으로 맞는 부분은 있다. fixed row를 쓰면 offset 위치에서 항상 64 bytes만 읽으면 되므로 구현이 단순하다.

하지만 개념적으로 부족한 부분도 분명하다.

- offset 기반 조회와 fixed row는 같은 말이 아니다.
- 가변 길이 row도 offset, length, record header, page directory가 있으면 index로 찾을 수 있다.
- MySQL의 row size limit은 fixed row 크기를 정하는 설계 근거가 아니다.
- 공간 낭비 문제는 단순히 row 크기를 몇 bytes로 잡을지의 문제가 아니라 record layout 문제다.

### 가져가야 할 흐름

이 질문에는 먼저 현재 구현의 단순화 목적을 인정하는 흐름이 맞다.

- 현재 구현은 B+Tree index가 `id -> row 위치`를 가리키는 경로를 보여주는 데 집중했다.
- fixed row는 그 경로를 가장 단순하게 만들기 위한 선택이다.
- 대신 이 선택은 저장 공간 낭비를 만든다.
- 실제 DBMS 구조로 가려면 fixed row 나열보다 page 기반 record manager가 필요하다.

핵심 주장은 다음이다.

> fixed row는 B+Tree의 필수 조건이 아니라, 현재 구현을 단순하게 만들기 위한 제한이다.

가변 길이 row를 지원하려면 row 위치를 더 풍부하게 표현해야 한다.

| 방식 | 개념 |
|---|---|
| `offset` + row header | offset 위치에서 row header를 읽고 length 확인 |
| `offset` + `length` | index value 또는 별도 metadata에 길이를 함께 저장 |
| `RID(page_id, slot_id)` | index는 page와 slot만 가리키고, page 내부 slot directory가 실제 위치와 길이를 관리 |

실제 DBMS에 가까운 방향은 page 기반 저장 구조다.

| 영역 | 맡는 역할 |
|---|---|
| B+Tree leaf | key를 `RID(page_id, slot_id)` 같은 row locator에 연결 |
| data page header | page 상태와 free space 정보 관리 |
| slot directory | slot별 실제 record offset과 length 관리 |
| record area | variable length record 저장 |

이 구조에서는 row가 page 안에서 이동해도 index entry를 매번 바꾸지 않아도 된다. slot directory만 갱신하면 RID는 유지될 수 있다.

### 조심할 점

MySQL row size limit을 근거로 fixed row를 설명하면 개념이 어긋난다.

MySQL의 약 65KB row size limit은 row를 65KB fixed length로 저장한다는 뜻이 아니다. SQL 계층의 row 크기 제한에 가깝고, 실제 InnoDB 저장은 row format, page, overflow page 규칙을 따른다.

이 질문에서 방어적으로 말하기보다, 현재 구현이 storage engine의 단순화 버전이라는 점을 명확히 두는 것이 중요하다.

### 직접 확인한 자료

- MySQL 8.4 Reference Manual, Limits on Table Column Count and Row Size: MySQL row size limit이 65,535 bytes이며 storage overhead를 포함한다고 설명한다. <https://dev.mysql.com/doc/refman/en/column-count-limit.html>
- MySQL 8.4 Reference Manual, InnoDB Row Formats: InnoDB table data와 secondary index가 B-tree 구조를 쓰고, 긴 variable-length column이 overflow page에 저장될 수 있다고 설명한다. <https://dev.mysql.com/doc/refman/en/innodb-row-format.html>
- SQLite Database File Format, B-tree Pages: SQLite도 page-oriented 저장 장치 위에서 B-tree page와 overflow page를 사용한다. <https://www.sqlite.org/fileformat.html>

## 3. 질문: binary로 저장하면 어떤가

### 질문했던 것

질문자는 CSV 대신 binary로 저장하면 어떤 차이가 있을지 물었다.

질문의 초점은 text CSV의 사람이 읽기 쉬운 형식보다, DB 내부에 맞춘 compact한 표현을 쓰면 저장 공간과 처리 비용을 줄일 수 있지 않느냐는 것이었다.

### 답변했던 것

당시 답변의 방향은 다음에 가까웠다.

- binary가 더 빠를 수는 있을 것 같다고 봤다.
- 다만 시연에서 실제 동작 확인이 중요해서 CSV를 선택했다고 설명했다.
- binary는 눈으로 보기 어렵고 CSV는 디버깅하기 쉽다고 말했다.
- 차이가 아주 클 것 같지는 않다고 판단했다.

CSV가 디버깅에 유리하다는 점은 맞다. 과제 시연에서 파일을 직접 열어보고 확인하기 쉬운 것도 장점이다.

부족했던 부분은 binary와 CSV의 차이를 너무 작게 본 것이다.

- 정수의 ASCII 표현과 binary integer 표현은 크기가 다르다.
- delimiter 기반 parsing과 length-prefix 기반 decode는 비용이 다르다.
- binary format은 단순히 빠른 저장 방식이 아니라 record format 설계 문제다.

### 가져가야 할 흐름

이 질문의 핵심은 CSV와 binary의 trade-off다.

- CSV는 사람이 읽고 디버깅하기 쉽다.
- binary는 저장 효율과 parsing 효율이 좋다.
- DBMS 내부 저장 방식으로 갈수록 binary record format이 자연스럽다.
- 다만 binary로 바꾼다고 자동으로 좋은 구조가 되는 것은 아니고, record header와 field layout 설계가 필요하다.

핵심 주장은 다음이다.

> CSV는 시연과 디버깅을 위한 선택이고, DBMS 내부 저장 구조로 확장하려면 binary record format이 더 적절하다.

CSV와 binary의 차이는 다음처럼 볼 수 있다.

| 항목 | CSV text | binary |
|---|---|---|
| 정수 `100000000` | ASCII 9 bytes | int32 4 bytes |
| 컬럼 구분 | comma 필요 | schema 또는 length metadata로 구분 |
| 문자열 길이 | delimiter 탐색 필요 | length prefix로 바로 확인 |
| parsing | 문자열 파싱 필요 | 타입별 decode |
| 사람이 직접 확인 | 쉬움 | 어려움 |
| 저장 효율 | 낮은 편 | 높은 편 |

binary row format을 제대로 설계하려면 이런 요소가 필요하다.

| 구성 요소 | 역할 |
|---|---|
| record header | row의 상태, 길이, schema version 등 |
| null bitmap | NULL 여부 표시 |
| fixed area | int, fixed char 같은 고정 길이 값 |
| variable area | varchar 같은 가변 길이 값 |
| offset/length table | 가변 길이 field 위치 확인 |

### 조심할 점

binary를 단순히 “눈으로 보기 어려운 CSV 대체재” 정도로만 설명하면 부족하다. 질문자는 저장 형식 자체를 DBMS 내부 표현으로 바꾸는 관점을 물은 것이다.

또한 binary가 항상 모든 면에서 낫다고 말하는 것도 단순하다. 과제 초반에는 CSV가 디버깅과 시연에 유리하고, DBMS 구조로 발전할수록 binary page format이 필요해진다는 균형이 맞다.

### 직접 확인한 자료

- MySQL InnoDB Row Formats: row format이 row의 물리 저장 방식과 성능에 영향을 준다고 설명한다. <https://dev.mysql.com/doc/refman/en/innodb-row-format.html>
- SQLite Database File Format: B-tree page 안의 cell, payload, overflow page 등 binary file layout을 문서화한다. <https://www.sqlite.org/fileformat.html>

## 4. 질문: auto increment의 next id는 어떻게 관리하는가

### 질문했던 것

질문자는 auto increment ID라면 프로그램이 다음에 발급할 id를 계속 알고 있어야 하지 않느냐고 물었다.

질문의 초점은 다음이다.

- 현재 id가 5까지 있으면 다음 insert는 6이어야 한다.
- 프로그램을 껐다 켜도 6부터 시작해야 한다.
- 그렇다면 `next_id` 같은 metadata는 어디에 저장되는가.

### 답변했던 것

당시 답변의 방향은 다음에 가까웠다.

- 처음에는 질문을 정확히 이해하지 못했다.
- 현재 코드에 next id 관리는 없는 것으로 알고 있다고 답했다.
- 요구사항에 있었는지 되물었다.
- 테스트에서는 id 값을 직접 넣었다고 설명했다.

사실관계만 보면 현재 구현에 auto increment가 없는 것은 맞다. `hyun/` 시연 코드는 INSERT 시 id를 직접 입력하고, 같은 id가 이미 있는지만 B+Tree에서 확인한다.

하지만 이 질문은 요구사항 확인 문제가 아니라 DBMS metadata의 기본 문제였다.

### 가져가야 할 흐름

이 질문에는 구현 범위를 먼저 분리하는 흐름이 맞다.

- 현재 구현은 auto increment가 아니라 user-provided id 방식이다.
- 따라서 next id persistence는 구현되어 있지 않다.
- DBMS처럼 auto increment를 지원하려면 table metadata가 필요하다.
- 파일 기반 DB라면 metadata도 파일이나 header page, catalog table 등에 persistent하게 저장해야 한다.

핵심 주장은 다음이다.

> auto increment는 단순히 `max(id) + 1` 계산이 아니라, 재시작 이후에도 유지되어야 하는 table metadata 문제다.

가능한 설계 방향은 다음과 같다.

| 방식 | 특징 |
|---|---|
| 시작 시 max id scan | 구현은 단순하지만 시작 비용이 커짐 |
| 별도 `.meta` 파일 | 빠르게 next id를 읽을 수 있지만 crash consistency 고려 필요 |
| data file header page | data file 내부에 table metadata를 같이 저장 |
| catalog table | DB 내부 시스템 테이블로 metadata 관리 |

현재 코드도 시작 시 CSV 전체를 읽어 index validation을 수행하므로, 단순 확장이라면 그 과정에서 max id를 같이 계산할 수 있다. 다만 이것은 대용량 데이터에서 시작 비용을 더 크게 만든다.

### 조심할 점

auto increment에는 crash consistency 문제가 따라온다.

| 상황 | 문제 |
|---|---|
| row append 성공 후 next id 갱신 전 종료 | 재시작 후 같은 id를 다시 발급할 수 있음 |
| next id 먼저 증가 후 row append 전 종료 | id gap이 생길 수 있음 |

실제 DBMS는 transaction, WAL, lock, sequence cache 같은 구조로 이 문제를 다룬다. 과제 수준에서는 그 전체를 구현하지 않더라도, auto increment가 metadata와 durability 문제라는 점은 짚어야 한다.

### 직접 확인한 자료

- MySQL InnoDB Row Formats: table data와 index가 B-tree 구조로 관리되며, table/index 메타데이터가 별도로 필요하다는 점을 이해하는 배경 자료다. <https://dev.mysql.com/doc/refman/en/innodb-row-format.html>
- SQLite Database File Format: database header, page header, b-tree page처럼 파일 내부에 구조화된 메타데이터를 둔다는 점을 확인할 수 있다. <https://www.sqlite.org/fileformat.html>

## 5. 질문: string index와 중복은 어떻게 처리하는가

### 질문했던 것

질문자는 ID는 integer이고 unique하게 다루기 쉽지만, 사람 이름 같은 string 컬럼을 index로 걸면 어떻게 할 것인지 물었다.

질문의 초점은 두 가지였다.

- string을 B+Tree key로 어떻게 표현하고 정렬할 것인가
- name처럼 unique하지 않은 값이 중복되면 어떻게 저장할 것인가

### 답변했던 것

당시 답변의 방향은 다음에 가까웠다.

- 모든 데이터는 binary로 표현 가능하니 integer 형태로 변환해 사용할 수 있을 것 같다고 말했다.
- 같은 이름이 있으면 별도 구분자를 추가할 수 있을 것 같다고 말했다.
- 구체적인 설계는 생각하지 못했다고 답했다.

이 답변의 문제는 B+Tree key의 핵심을 binary 표현 자체로 본 것이다.

B+Tree index에서 중요한 것은 어떤 값이 binary로 표현 가능하다는 사실이 아니라, 비교 가능한 정렬 순서와 중복 처리 규칙이다.

### 가져가야 할 흐름

먼저 현재 구현의 한계를 분리해야 한다.

- 현재 사용한 B+Tree 라이브러리는 `key_t`가 `int`다.
- 현재 wrapper도 첫 번째 컬럼 `id`를 int로 파싱해서 key로 사용한다.
- 따라서 현재 구현은 int id primary key index에 맞춰져 있다.
- string secondary index는 key type과 comparator부터 바꿔야 한다.

핵심 주장은 다음이다.

> 문자열 인덱스는 string을 int로 바꾸는 문제가 아니라, string key의 정렬 규칙과 non-unique key의 row locator 저장 방식을 정하는 문제다.

문자열 index에 필요한 요소는 다음이다.

| 요소 | 의미 |
|---|---|
| key bytes | 문자열의 저장 표현 |
| key length | 가변 길이 key 처리 |
| comparator | 정렬 순서 결정 |
| collation | 대소문자, locale, byte order 규칙 |
| row locator | 같은 key가 가리키는 실제 row 위치 |

중복 처리는 크게 두 방향이 있다.

### 방식 A: composite key

secondary key 뒤에 primary key를 붙여 전체 key를 unique하게 만든다.

| B+Tree key | value |
|---|---|
| `(name, primary_id)` | row location |

예를 들어 `kim`이라는 이름이 여러 번 나와도 `(kim, 1)`, `(kim, 7)`, `(kim, 9)`는 서로 다른 key다.

이 방식에서는 `name = kim` 조회가 `(kim, minimum id)`부터 `(kim, maximum id)`까지의 range scan으로 바뀐다.

### 방식 B: posting list / RID list

하나의 key가 여러 row location을 가진다.

| B+Tree key | value |
|---|---|
| `name` | `[row location 1, row location 7, row location 9]` |

이 방식은 같은 key가 많아질수록 value list가 커진다. list가 leaf 안에 다 들어가지 않으면 overflow page 같은 추가 구조가 필요하다.

### 조심할 점

문자열을 hash나 dictionary id로 바꾸는 방식도 가능하지만, 이것이 B+Tree range scan이나 정렬 요구와 항상 맞지는 않는다.

| 방식 | 주의점 |
|---|---|
| hash | equality 검색에는 가능하지만 range/order에는 부적합 |
| dictionary id | id 부여 순서와 문자열 정렬 순서가 다를 수 있음 |
| fixed length string | prefix 충돌과 긴 문자열 처리 필요 |
| generic key | 구현 난이도가 높지만 DB index에 더 자연스러움 |

질문자가 지적한 핵심은 unique하지 않은 column도 index로 만들 수 있어야 하며, 그때 B+Tree가 중복을 어떻게 표현하는지였다고 보면 된다.

### 직접 확인한 자료

- PostgreSQL Documentation, Unique Indexes: unique index가 column 또는 여러 column 조합의 uniqueness를 강제한다고 설명한다. <https://www.postgresql.org/docs/current/indexes-unique.html>
- PostgreSQL Documentation, Multicolumn Indexes: table의 여러 column으로 index를 만들 수 있고, B-tree가 multicolumn index를 지원한다고 설명한다. <https://www.postgresql.org/docs/current/indexes-multicolumn.html>
- SQLite Database File Format, B-tree Pages: SQLite index b-tree는 arbitrary key를 사용하고 table b-tree는 integer key를 사용한다고 설명한다. <https://www.sqlite.org/fileformat.html>

## 6. 전체 피드백의 핵심

질문자가 짚은 핵심은 B+Tree 알고리즘 자체보다, B+Tree를 DB index로 쓰기 위해 필요한 주변 구조다.

현재 구현에서 보여준 것은 다음이다.

- B+Tree index를 파일로 유지했다.
- `id -> offset`으로 단건 조회를 전체 scan에서 분리했다.
- `BETWEEN`을 B+Tree leaf range scan으로 연결했다.
- INSERT 후 index를 갱신했다.
- 재시작 시 index 파일을 재사용하거나 CSV 기준으로 복구했다.

하지만 DBMS index 관점에서 빠진 것은 다음이다.

- fixed row 공간 낭비 해결
- binary record format
- auto increment와 next id persistence
- string secondary index
- non-unique key 처리
- page/slot 기반 row locator
- update/delete/free space/crash recovery

정리하면, 현재 구현은 `id` 기반 B+Tree 조회 경로를 보여주는 MVP다. 실제 DBMS 인덱스로 보려면 B+Tree 외에도 record format, metadata, row locator, secondary index, duplicate handling을 함께 설계해야 한다.
