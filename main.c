#include <stdio.h>
#include <string.h>

#include "mini_db.h"

#ifndef PROJECT_ROOT_DIR
#define PROJECT_ROOT_DIR "."
#endif

#define PROJECT_CSV_PATH(path) PROJECT_ROOT_DIR "/" path

static int run_repl(void);
static char *trim(char *text);

static const TableMetadata GLOBAL_TABLES[] = {
    {"users", {"id", "name"}, 2, PROJECT_CSV_PATH("data/users.csv")},
    {"posts", {"id", "title"}, 2, PROJECT_CSV_PATH("data/posts.csv")},
};

static const int GLOBAL_TABLE_COUNT = sizeof(GLOBAL_TABLES) / sizeof(GLOBAL_TABLES[0]);

int main(void) {
    return run_repl();
}

static int run_repl(void) {
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

const TableMetadata *find_table(const char *table_name) {
    for (int i = 0; i < GLOBAL_TABLE_COUNT; i++) {
        if (strcmp(GLOBAL_TABLES[i].name, table_name) == 0) {
            return &GLOBAL_TABLES[i];
        }
    }

    return NULL;
}

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
