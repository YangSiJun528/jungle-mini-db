# 업데이트 내용
1. 테이블 포맷팅 
=> 출력 할때 테이블 보기 좋게 출력되게 
<img width="281" height="127" alt="image" src="https://github.com/user-attachments/assets/cb07b4f9-2b37-4d7b-92a7-c586bbd2619c" />

2. SQL 쿼리 case insensitive
<img width="289" height="258" alt="image" src="https://github.com/user-attachments/assets/92b356ad-4e46-4071-a4e7-986b3b8fe032" />

3. BETWEEN 절 작동하도록 구현 

<img width="1412" height="783" alt="image" src="https://github.com/user-attachments/assets/5f670ac2-de35-453a-8ccb-1c01f0f22267" />

### B+Tree BETWEEN 성능 비교

테스트 조건:

- 데이터 수: 1,000,000 rows
- Row 크기: 64 bytes fixed row
- 범위 조건: 서로 다른 위치의 `BETWEEN` 범위 10개
- 각 범위 결과 row 수: 10 rows
- 반복 횟수: 범위당 50회
- 총 쿼리 수: 방식별 500회
- 빌드 옵션: `clang -O2`

| 범위 | B+Tree 평균 | 선형 스캔 평균 | 차이 |
|---|---:|---:|---:|
| 1 ~ 10 | 0.206ms | 37.258ms | 181.2배 |
| 100001 ~ 100010 | 0.199ms | 42.998ms | 216.1배 |
| 200001 ~ 200010 | 0.197ms | 36.927ms | 187.1배 |
| 300001 ~ 300010 | 0.195ms | 36.302ms | 186.3배 |
| 400001 ~ 400010 | 0.199ms | 36.670ms | 183.9배 |
| 500000 ~ 500009 | 0.195ms | 37.877ms | 194.6배 |
| 600001 ~ 600010 | 0.191ms | 36.614ms | 191.7배 |
| 700001 ~ 700010 | 0.196ms | 37.302ms | 189.9배 |
| 800001 ~ 800010 | 0.191ms | 38.645ms | 202.3배 |
| 999991 ~ 1000000 | 0.198ms | 37.025ms | 186.7배 |

| 방식 | 전체 평균 실행 시간 |
|---|---:|
| B+Tree 인덱스 BETWEEN | 0.197ms |
| 선형 스캔 BETWEEN | 37.762ms |
| 평균 성능 차이 | 약 191.9배 빠름 |




