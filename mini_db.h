#ifndef JUNGLE_MINI_DB_H
#define JUNGLE_MINI_DB_H

#include <stddef.h>

#define MAX_INPUT_SIZE 1024
#define MAX_TABLE_NAME_SIZE 32
#define MAX_VALUES 16
#define MAX_VALUE_SIZE 128
#define MAX_ERROR_SIZE 128
#define ROW_SIZE 64
#define ROW_DATA_SIZE (ROW_SIZE - 1)
#define ROW_PADDING_CHAR '_'

/* 공유 계약: SQL 처리기가 공유하는 계획 타입이다. */
typedef enum {
    QUERY_INVALID = 0,
    QUERY_SELECT,
    QUERY_INSERT
} QueryType;

typedef enum {
    SELECT_CONDITION_NONE = 0,
    SELECT_CONDITION_ID_EQUALS
} SelectConditionType;

typedef struct {
    SelectConditionType type;
    int id_value;
} SelectCondition;

typedef struct {
    long offset;
} RowLocation;

typedef struct {
    QueryType type;
    char table_name[MAX_TABLE_NAME_SIZE];
    SelectCondition condition;
    char values[MAX_VALUES][MAX_VALUE_SIZE];
    int value_count;
    char error_message[MAX_ERROR_SIZE];
} Plan;

/* 공유 계약: 테이블 이름, 컬럼, CSV 파일 경로를 묶은 메타데이터 타입이다. */
typedef struct {
    const char *name;
    const char *columns[MAX_VALUES];
    int column_count;
    const char *csv_file_path;
    const char *index_file_path;
    int row_size;
} TableMetadata;

/* 공유 계약: 각 C 파일이 서로 호출하는 최소 함수 목록이다. */
Plan parse_sql(const char *sql);
void execute_plan(const Plan *plan);
const TableMetadata *find_table(const char *table_name);
int db_index_open_table(const TableMetadata *table, char *error_message, size_t error_size);
void db_index_shutdown_all(void);
int db_index_get(const char *table_name, int id, RowLocation *location);
int db_index_put(const char *table_name, int id, RowLocation location);

#endif
