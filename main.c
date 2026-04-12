#include <stdio.h>
#include <string.h>

#define MAX_INPUT_SIZE 1024
#define MAX_TABLE_NAME_SIZE 32
#define MAX_VALUES 16
#define MAX_VALUE_SIZE 128
#define MAX_ERROR_SIZE 128

#ifndef PROJECT_ROOT_DIR
#define PROJECT_ROOT_DIR "."
#endif

#define PROJECT_CSV_PATH(path) PROJECT_ROOT_DIR "/" path

typedef enum {
    QUERY_INVALID = 0,
    QUERY_SELECT,
    QUERY_INSERT
} QueryType;

typedef struct {
    const char *name;
    const char *columns[MAX_VALUES];
    int column_count;
    const char *csv_file_path;
} TableMetadata;

typedef struct {
    QueryType type;
    char table_name[MAX_TABLE_NAME_SIZE];
    char values[MAX_VALUES][MAX_VALUE_SIZE];
    int value_count;
    char error_message[MAX_ERROR_SIZE];
} Plan;

static const TableMetadata GLOBAL_TABLES[] = {
    {"users", {"id", "name"}, 2, PROJECT_CSV_PATH("data/users.csv")},
    {"posts", {"id", "title"}, 2, PROJECT_CSV_PATH("data/posts.csv")},
};

static const int GLOBAL_TABLE_COUNT = sizeof(GLOBAL_TABLES) / sizeof(GLOBAL_TABLES[0]);

static char *trim(char *text) {
    char *end;

    while (*text == ' ' || *text == '\t' || *text == '\n' || *text == '\r') {
        text++;
    }

    if (*text == '\0') {
        return text;
    }

    end = text + strlen(text) - 1;
    while (end > text && (*end == ' ' || *end == '\t' || *end == '\n' || *end == '\r')) {
        *end = '\0';
        end--;
    }

    return text;
}

static int starts_with(const char *text, const char *prefix) {
    return strncmp(text, prefix, strlen(prefix)) == 0;
}

static void set_error(Plan *plan, const char *message) {
    plan->type = QUERY_INVALID;
    snprintf(plan->error_message, sizeof(plan->error_message), "%s", message);
}

static const TableMetadata *find_table(const char *table_name) {
    for (int i = 0; i < GLOBAL_TABLE_COUNT; i++) {
        if (strcmp(GLOBAL_TABLES[i].name, table_name) == 0) {
            return &GLOBAL_TABLES[i];
        }
    }

    return NULL;
}

static int is_ascii_text(const char *text) {
    const unsigned char *cursor = (const unsigned char *) text;

    while (*cursor != '\0') {
        if (*cursor > 127) {
            return 0;
        }
        cursor++;
    }

    return 1;
}

static void remove_trailing_semicolon(char *text) {
    size_t length = strlen(text);

    if (length > 0 && text[length - 1] == ';') {
        text[length - 1] = '\0';
    }
}

static Plan parse_select(const char *sql) {
    const char *prefix = "select * from";
    Plan plan = {0};
    char table_name[MAX_TABLE_NAME_SIZE];
    char *trimmed_table_name;

    snprintf(table_name, sizeof(table_name), "%s", sql + strlen(prefix));
    trimmed_table_name = trim(table_name);
    remove_trailing_semicolon(trimmed_table_name);
    trimmed_table_name = trim(trimmed_table_name);

    if (find_table(trimmed_table_name) == NULL) {
        set_error(&plan, "존재하지 않는 테이블입니다");
        return plan;
    }

    plan.type = QUERY_SELECT;
    snprintf(plan.table_name, sizeof(plan.table_name), "%s", trimmed_table_name);
    return plan;
}

static Plan parse_insert(const char *sql) {
    const char *prefix = "insert into";
    Plan plan = {0};
    char rest[MAX_INPUT_SIZE];
    char values_text[MAX_INPUT_SIZE];
    char *values_keyword;
    char *table_name;
    char *values;
    char *token;
    const TableMetadata *table;

    snprintf(rest, sizeof(rest), "%s", sql + strlen(prefix));
    values_keyword = strstr(rest, "values");

    if (values_keyword == NULL) {
        set_error(&plan, "지원하지 않는 SQL");
        return plan;
    }

    *values_keyword = '\0';
    table_name = trim(rest);
    values = trim(values_keyword + strlen("values"));

    remove_trailing_semicolon(values);
    values = trim(values);

    if (*values == '(') {
        values++;
    }

    values = trim(values);
    if (strlen(values) > 0 && values[strlen(values) - 1] == ')') {
        values[strlen(values) - 1] = '\0';
    }

    values = trim(values);

    table = find_table(table_name);
    if (table == NULL) {
        set_error(&plan, "존재하지 않는 테이블입니다");
        return plan;
    }

    snprintf(values_text, sizeof(values_text), "%s", values);
    token = strtok(values_text, ",");

    while (token != NULL && plan.value_count < MAX_VALUES) {
        char *value = trim(token);

        if (!is_ascii_text(value)) {
            set_error(&plan, "ASCII 텍스트만 입력할 수 있습니다");
            return plan;
        }

        snprintf(plan.values[plan.value_count], sizeof(plan.values[plan.value_count]), "%s", value);
        plan.value_count++;
        token = strtok(NULL, ",");
    }

    if (token != NULL || plan.value_count != table->column_count) {
        set_error(&plan, "컬럼 개수와 값 개수가 맞지 않습니다");
        return plan;
    }

    plan.type = QUERY_INSERT;
    snprintf(plan.table_name, sizeof(plan.table_name), "%s", table_name);
    return plan;
}

static Plan parse_sql(const char *sql) {
    Plan plan = {0};

    if (starts_with(sql, "select * from")) {
        return parse_select(sql);
    }

    if (starts_with(sql, "insert into")) {
        return parse_insert(sql);
    }

    set_error(&plan, "지원하지 않는 SQL");
    return plan;
}

static void print_columns(const TableMetadata *table) {
    for (int i = 0; i < table->column_count; i++) {
        if (i > 0) {
            printf(",");
        }
        printf("%s", table->columns[i]);
    }
    printf("\n");
}

static void execute_select(const Plan *plan) {
    const TableMetadata *table = find_table(plan->table_name);
    FILE *file;
    char row[MAX_INPUT_SIZE];

    if (table == NULL) {
        printf("실행할 수 없는 계획입니다\n");
        return;
    }

    file = fopen(table->csv_file_path, "r");
    if (file == NULL) {
        printf("CSV 파일을 열 수 없습니다\n");
        return;
    }

    print_columns(table);
    while (fgets(row, sizeof(row), file) != NULL) {
        printf("%s", row);
        if (strlen(row) > 0 && row[strlen(row) - 1] != '\n') {
            printf("\n");
        }
    }

    fclose(file);
}

static void execute_insert(const Plan *plan) {
    const TableMetadata *table = find_table(plan->table_name);
    FILE *file;
    long file_size;

    if (table == NULL) {
        printf("실행할 수 없는 계획입니다\n");
        return;
    }

    file = fopen(table->csv_file_path, "a+");
    if (file == NULL) {
        printf("CSV 파일을 열 수 없습니다\n");
        return;
    }

    fseek(file, 0, SEEK_END);
    file_size = ftell(file);
    if (file_size > 0) {
        int last_char;

        fseek(file, -1, SEEK_END);
        last_char = fgetc(file);
        if (last_char != '\n') {
            fprintf(file, "\n");
        }
    }

    for (int i = 0; i < plan->value_count; i++) {
        if (i > 0) {
            fprintf(file, ",");
        }
        fprintf(file, "%s", plan->values[i]);
    }
    fprintf(file, "\n");

    fclose(file);
}

static void execute_plan(const Plan *plan) {
    if (plan->type == QUERY_SELECT) {
        execute_select(plan);
        return;
    }

    if (plan->type == QUERY_INSERT) {
        execute_insert(plan);
        return;
    }

    printf("실행할 수 없는 계획입니다\n");
}

int main(void) {
    char input[MAX_INPUT_SIZE];

    while (1) {
        char *sql;
        Plan plan;

        printf("mini-db> ");
        if (fgets(input, sizeof(input), stdin) == NULL) {
            printf("\n");
            return 0;
        }

        sql = trim(input);

        if (strcmp(sql, "exit") == 0 || strcmp(sql, "quit") == 0) {
            return 0;
        }

        plan = parse_sql(sql);
        if (plan.type == QUERY_INVALID) {
            printf("%s\n", plan.error_message);
            continue;
        }

        execute_plan(&plan);
    }
}
