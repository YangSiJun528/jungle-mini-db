#ifndef JUNGLE_MINI_DB_H
#define JUNGLE_MINI_DB_H

#define MAX_INPUT_SIZE 1024
#define MAX_TABLE_NAME_SIZE 32
#define MAX_VALUES 16
#define MAX_VALUE_SIZE 128
#define MAX_ERROR_SIZE 128

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

typedef struct {
    const char *name;
    const char *columns[MAX_VALUES];
    int column_count;
    const char *csv_file_path;
} TableMetadata;

Plan parse_sql(const char *sql);
void execute_plan(const Plan *plan);
const TableMetadata *find_table(const char *table_name);

#endif
