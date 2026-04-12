#include <stdio.h>
#include <string.h>

#include "mini_db.h"

static void execute_select(const Plan *plan);
static void execute_insert(const Plan *plan);
static void print_columns(const TableMetadata *table);
static void write_newline_if_needed(FILE *file);
static void write_values(FILE *file, const Plan *plan);

void execute_plan(const Plan *plan) {
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

    if (table == NULL) {
        printf("실행할 수 없는 계획입니다\n");
        return;
    }

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
