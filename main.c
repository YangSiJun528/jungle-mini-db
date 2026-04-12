#include <stdio.h>
#include <string.h>

#include "mini_db.h"

#ifndef PROJECT_ROOT_DIR
#define PROJECT_ROOT_DIR "."
#endif

#define PROJECT_CSV_PATH(path) PROJECT_ROOT_DIR "/" path

/* 선언부: 이 파일 안에서만 사용하는 private 함수 원형이다. */
static int run_repl(void);
static char *trim(char *text);

/* 정의부: 하드코딩된 테이블, 컬럼, CSV 파일 경로다. */
static const TableMetadata GLOBAL_TABLES[] = {
    {"users", {"id", "name"}, 2, PROJECT_CSV_PATH("data/users.csv")},
    {"posts", {"id", "title"}, 2, PROJECT_CSV_PATH("data/posts.csv")},
};

static const int GLOBAL_TABLE_COUNT = sizeof(GLOBAL_TABLES) / sizeof(GLOBAL_TABLES[0]);

int main(void) {
    /* 사용부: 프로그램 시작점을 REPL 흐름으로 연결한다. */
    return run_repl();
}

/* 1. CLI SQL 입력 처리: REPL에서 SQL 한 줄을 받아 파서와 실행기로 넘긴다. */
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

        /* 사용부 flow: 1. CLI SQL 입력 처리 -> 2.1 SQL 타입 판별 */
        plan = parse_sql(sql);
        if (plan.type == QUERY_INVALID) {
            printf("%s\n", plan.error_message);
            continue;
        }

        /* 사용부 flow: 2.2 SQL 파싱 결과 -> 2.3 실행 분기 */
        execute_plan(&plan);
    }
}

/* 3.1 테이블 파일 매핑: 테이블 이름을 컬럼 정보와 CSV 파일 경로로 바꾼다. */
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
