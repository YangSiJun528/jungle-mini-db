#include <stdio.h>
#include <string.h>

#include "mini_db.h"

/* 선언부: executor.c 안에서만 사용하는 private 함수 원형이다. */
static void execute_select(const Plan *plan);
static void execute_insert(const Plan *plan);
static void print_columns(const TableMetadata *table);
static void write_newline_if_needed(FILE *file);
static void write_values(FILE *file, const Plan *plan);

/* 2.3 실행 분기: 파싱된 계획을 SELECT 또는 INSERT 실행으로 보낸다. */
void execute_plan(const Plan *plan) {
    if (plan->type == QUERY_SELECT) {
        /* 사용부 flow: 2.3 실행 분기 -> 3.3 SELECT 조회 */
        execute_select(plan);
        return;
    }

    if (plan->type == QUERY_INSERT) {
        /* 사용부 flow: 2.3 실행 분기 -> 3.2 INSERT 저장 */
        execute_insert(plan);
        return;
    }

    printf("실행할 수 없는 계획입니다\n");
}

/* 3.3 SELECT 조회: 테이블 CSV 파일을 읽어 컬럼명과 모든 행을 출력한다. */
static void execute_select(const Plan *plan) {
    /* 사용부 flow: 3.3 SELECT 조회 -> 3.1 테이블 파일 매핑 */
    const TableMetadata *table = find_table(plan->table_name);
    FILE *file;
    char row[MAX_INPUT_SIZE];

    if (table == NULL) {
        printf("실행할 수 없는 계획입니다\n");
        return;
    }

    /* 사용부 flow: 3.1 테이블 파일 매핑 -> 3.3 SELECT 조회 */
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

/* 3.2 INSERT 저장: 파싱된 값 목록을 테이블 CSV 파일 끝에 추가한다. */
static void execute_insert(const Plan *plan) {
    /* 사용부 flow: 3.2 INSERT 저장 -> 3.1 테이블 파일 매핑 */
    const TableMetadata *table = find_table(plan->table_name);
    FILE *file;

    if (table == NULL) {
        printf("실행할 수 없는 계획입니다\n");
        return;
    }

    /* 사용부 flow: 3.1 테이블 파일 매핑 -> 3.2 INSERT 저장 */
    file = fopen(table->csv_file_path, "a+");
    if (file == NULL) {
        printf("CSV 파일을 열 수 없습니다\n");
        return;
    }

    write_newline_if_needed(file);
    write_values(file, plan);
    fclose(file);
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

/* 기존 CSV 마지막 줄과 새 INSERT 행이 붙지 않도록 필요한 경우 개행을 추가한다. */
static void write_newline_if_needed(FILE *file) {
    long file_size;
    int last_char;

    fseek(file, 0, SEEK_END);
    file_size = ftell(file);
    if (file_size <= 0) {
        return;
    }

    fseek(file, -1, SEEK_END);
    last_char = fgetc(file);
    if (last_char != '\n') {
        fprintf(file, "\n");
    }
}

static void write_values(FILE *file, const Plan *plan) {
    for (int i = 0; i < plan->value_count; i++) {
        if (i > 0) {
            fprintf(file, ",");
        }
        fprintf(file, "%s", plan->values[i]);
    }
    fprintf(file, "\n");
}
