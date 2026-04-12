#ifndef JUNGLE_MINI_DB_H
#define JUNGLE_MINI_DB_H

#define MAX_INPUT_SIZE 1024
#define MAX_TABLE_NAME_SIZE 32
#define MAX_VALUES 16
#define MAX_VALUE_SIZE 128
#define MAX_ERROR_SIZE 128

/* 정의부: SQL 처리기가 공유하는 계획 타입이다. */
typedef enum {
    QUERY_INVALID = 0,
    QUERY_SELECT,
    QUERY_INSERT
} QueryType;

typedef struct {
    QueryType type;
    char table_name[MAX_TABLE_NAME_SIZE];
    char values[MAX_VALUES][MAX_VALUE_SIZE];
    int value_count;
    char error_message[MAX_ERROR_SIZE];
} Plan;

/* 정의부: 테이블 이름, 컬럼, CSV 파일 경로를 묶은 메타데이터 타입이다. */
typedef struct {
    const char *name;
    const char *columns[MAX_VALUES];
    int column_count;
    const char *csv_file_path;
} TableMetadata;

/* 선언부: 각 C 파일이 서로 호출하는 최소 public 함수 목록이다. */
Plan parse_sql(const char *sql);
void execute_plan(const Plan *plan);
const TableMetadata *find_table(const char *table_name);

#endif
