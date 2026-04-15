#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory_bptree.h"
#include "mini_db.h"

typedef struct {
    const TableMetadata *table;
    MemoryBPlusTree *tree;
    int next_id;
} IndexHandle;

/* 내부 구현: 공개 인덱스 흐름을 구성하는 private 함수 목록이다. */
static int rebuild_index_from_data_file(IndexHandle *handle, char *error_message, size_t error_size);
static int read_data_row(FILE *file, const TableMetadata *table, long offset, char fixed_row[ROW_SIZE]);
static int extract_id_from_fixed_row(const char fixed_row[ROW_SIZE], int *id);
static IndexHandle *find_index_handle(const char *table_name);
static IndexHandle *ensure_index_handle(const TableMetadata *table);
static int ensure_data_file(const TableMetadata *table, char *error_message, size_t error_size);
static int parse_int_text(const char *text, int *value);
static long get_file_size(FILE *file);
static int update_next_id(IndexHandle *handle, int id, char *error_message, size_t error_size);
static void set_error(char *error_message, size_t error_size, const char *message);

static IndexHandle INDEX_HANDLES[MAX_VALUES];
static int INDEX_HANDLE_COUNT = 0;

/* 1.2/1.3 인덱스 준비: 프로그램 시작 시 테이블 CSV를 스캔해 메모리 B+Tree를 만든다. */
int db_index_open_table(const TableMetadata *table, char *error_message, size_t error_size) {
    IndexHandle *handle;

    if (table->row_size != ROW_SIZE) {
        set_error(error_message, error_size, "지원하지 않는 row size입니다");
        return -1;
    }

    if (!ensure_data_file(table, error_message, error_size)) {
        return -1;
    }

    handle = ensure_index_handle(table);
    if (handle == NULL) {
        set_error(error_message, error_size, "인덱스를 준비할 수 없습니다");
        return -1;
    }

    if (handle->tree != NULL) {
        memory_bptree_destroy(handle->tree);
        handle->tree = NULL;
    }

    handle->tree = memory_bptree_create();
    if (handle->tree == NULL) {
        set_error(error_message, error_size, "인덱스를 준비할 수 없습니다");
        return -1;
    }

    handle->next_id = 1;
    return rebuild_index_from_data_file(handle, error_message, error_size);
}

/* 2.3 특수 명령 처리: 종료 시 열린 B+Tree 인덱스 자원을 정리한다. */
void db_index_shutdown_all(void) {
    for (int i = 0; i < INDEX_HANDLE_COUNT; i++) {
        if (INDEX_HANDLES[i].tree != NULL) {
            memory_bptree_destroy(INDEX_HANDLES[i].tree);
            INDEX_HANDLES[i].tree = NULL;
        }
        INDEX_HANDLES[i].table = NULL;
        INDEX_HANDLES[i].next_id = 1;
    }

    INDEX_HANDLE_COUNT = 0;
}

/* 6.3 조회 경로 제공: id key로 메모리 B+Tree를 검색해 fixed row byte offset을 반환한다. */
int db_index_get(const char *table_name, int id, RowLocation *location) {
    IndexHandle *handle = find_index_handle(table_name);
    long offset;

    if (handle == NULL || handle->tree == NULL || location == NULL) {
        return -1;
    }

    if (!memory_bptree_get(handle->tree, id, &offset)) {
        return 0;
    }

    if (offset < 0 || offset % handle->table->row_size != 0) {
        return -1;
    }

    location->offset = offset;
    return 1;
}

/* 6.4 삽입 후 갱신: 새 id와 row 위치를 메모리 B+Tree 인덱스에 등록한다. */
int db_index_put(const char *table_name, int id, RowLocation location) {
    IndexHandle *handle = find_index_handle(table_name);

    if (handle == NULL || handle->tree == NULL || id <= 0 || location.offset < 0 ||
        location.offset % handle->table->row_size != 0) {
        return -1;
    }

    if (memory_bptree_put(handle->tree, id, location.offset) != 1) {
        return -1;
    }

    return update_next_id(handle, id, NULL, 0);
}

/* 4.4 자동 ID 부여: 현재 테이블에 다음으로 쓸 id 값을 알려준다. */
int db_index_next_id(const char *table_name, int *next_id) {
    IndexHandle *handle = find_index_handle(table_name);

    if (handle == NULL || handle->tree == NULL || next_id == NULL || handle->next_id <= 0) {
        return -1;
    }

    *next_id = handle->next_id;
    return 1;
}

/* 1.3 시작 시 재구축: 데이터 파일을 순차 스캔해 메모리 B+Tree를 채운다. */
static int rebuild_index_from_data_file(IndexHandle *handle, char *error_message, size_t error_size) {
    FILE *file;
    long file_size;

    file = fopen(handle->table->csv_file_path, "rb");
    if (file == NULL) {
        set_error(error_message, error_size, "CSV 파일을 열 수 없습니다");
        return -1;
    }

    file_size = get_file_size(file);
    if (file_size < 0 || file_size % handle->table->row_size != 0) {
        fclose(file);
        set_error(error_message, error_size, "데이터 파일이 올바르지 않습니다");
        return -1;
    }

    for (long offset = 0; offset < file_size; offset += handle->table->row_size) {
        char fixed_row[ROW_SIZE];
        int id;

        if (!read_data_row(file, handle->table, offset, fixed_row) || !extract_id_from_fixed_row(fixed_row, &id)) {
            fclose(file);
            set_error(error_message, error_size, "데이터 파일이 올바르지 않습니다");
            return -1;
        }

        if (memory_bptree_put(handle->tree, id, offset) != 1) {
            fclose(file);
            set_error(error_message, error_size, "데이터 파일에 중복 id가 있습니다");
            return -1;
        }

        if (update_next_id(handle, id, error_message, error_size) != 1) {
            fclose(file);
            return -1;
        }
    }

    fclose(file);
    return 0;
}

/* 5.4 위치 기반 읽기/쓰기: 지정한 byte offset에서 fixed row 하나를 읽는다. */
static int read_data_row(FILE *file, const TableMetadata *table, long offset, char fixed_row[ROW_SIZE]) {
    if (fseek(file, offset, SEEK_SET) != 0) {
        return 0;
    }

    if (fread(fixed_row, 1, table->row_size, file) != (size_t) table->row_size) {
        return 0;
    }

    return fixed_row[ROW_DATA_SIZE] == '\n';
}

/* 5.3 논리 row 변환: fixed row에서 padding을 제거하고 첫 번째 컬럼 id를 추출한다. */
static int extract_id_from_fixed_row(const char fixed_row[ROW_SIZE], int *id) {
    char logical_row[ROW_SIZE];
    int end = ROW_DATA_SIZE - 1;
    char *comma;

    if (fixed_row[ROW_DATA_SIZE] != '\n') {
        return 0;
    }

    memcpy(logical_row, fixed_row, ROW_DATA_SIZE);
    logical_row[ROW_DATA_SIZE] = '\0';

    while (end >= 0 && logical_row[end] == ROW_PADDING_CHAR) {
        logical_row[end] = '\0';
        end--;
    }

    if (end < 0 || logical_row[end] != ',') {
        return 0;
    }
    logical_row[end] = '\0';

    comma = strchr(logical_row, ',');
    if (comma != NULL) {
        *comma = '\0';
    }

    return parse_int_text(logical_row, id) && *id > 0;
}

/* 내부 구현: 테이블 이름에 해당하는 열린 인덱스 핸들을 찾는다. */
static IndexHandle *find_index_handle(const char *table_name) {
    for (int i = 0; i < INDEX_HANDLE_COUNT; i++) {
        if (strcmp(INDEX_HANDLES[i].table->name, table_name) == 0) {
            return &INDEX_HANDLES[i];
        }
    }

    return NULL;
}

/* 내부 구현: 테이블 인덱스 핸들을 재사용하거나 새 슬롯에 등록한다. */
static IndexHandle *ensure_index_handle(const TableMetadata *table) {
    IndexHandle *handle = find_index_handle(table->name);

    if (handle != NULL) {
        handle->table = table;
        handle->next_id = 1;
        return handle;
    }

    if (INDEX_HANDLE_COUNT >= MAX_VALUES) {
        return NULL;
    }

    handle = &INDEX_HANDLES[INDEX_HANDLE_COUNT];
    handle->table = table;
    handle->tree = NULL;
    handle->next_id = 1;
    INDEX_HANDLE_COUNT++;
    return handle;
}

/* 내부 구현: 빈 테이블도 시작할 수 있도록 데이터 파일을 준비한다. */
static int ensure_data_file(const TableMetadata *table, char *error_message, size_t error_size) {
    FILE *file = fopen(table->csv_file_path, "ab");

    if (file == NULL) {
        set_error(error_message, error_size, "CSV 파일을 열 수 없습니다");
        return 0;
    }

    fclose(file);
    return 1;
}

/* 내부 구현: id 문자열을 B+Tree key로 쓸 정수로 변환한다. */
static int parse_int_text(const char *text, int *value) {
    char *end;
    long parsed;

    if (text[0] == '\0') {
        return 0;
    }

    parsed = strtol(text, &end, 10);
    if (*end != '\0' || parsed < INT_MIN || parsed > INT_MAX) {
        return 0;
    }

    *value = (int) parsed;
    return 1;
}

/* 내부 구현: 현재 파일 크기를 byte 단위로 얻는다. */
static long get_file_size(FILE *file) {
    long file_size;

    if (fseek(file, 0, SEEK_END) != 0) {
        return -1;
    }

    file_size = ftell(file);
    if (file_size < 0) {
        return -1;
    }

    return file_size;
}

/* 내부 구현: 가장 큰 id 다음 값을 자동 부여용 next_id로 유지한다. */
static int update_next_id(IndexHandle *handle, int id, char *error_message, size_t error_size) {
    if (id <= 0) {
        set_error(error_message, error_size, "id는 1 이상의 정수여야 합니다");
        return -1;
    }

    if (id >= handle->next_id) {
        if (id == INT_MAX) {
            set_error(error_message, error_size, "더 이상 자동으로 부여할 id가 없습니다");
            return -1;
        }
        handle->next_id = id + 1;
    }

    return 1;
}

/* 내부 구현: 호출자에게 전달할 오류 메시지를 고정 크기 버퍼에 복사한다. */
static void set_error(char *error_message, size_t error_size, const char *message) {
    if (error_message == NULL || error_size == 0) {
        return;
    }

    snprintf(error_message, error_size, "%s", message);
}
