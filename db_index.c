#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "mini_db.h"

#define BPLUS_MAX_KEYS 31
#define INDEX_HEADER "JMDBIDX1"

typedef struct BPlusNode {
    int is_leaf;
    int key_count;
    int keys[BPLUS_MAX_KEYS + 1];
    long values[BPLUS_MAX_KEYS + 1];
    struct BPlusNode *children[BPLUS_MAX_KEYS + 2];
} BPlusNode;

typedef struct {
    BPlusNode *root;
    size_t size;
} BPlusTree;

typedef struct {
    const TableMetadata *table;
    BPlusTree tree;
} IndexHandle;

/* 파일 안에서만 사용: B+Tree 구현과 테이블별 인덱스 관리 함수 목록이다. */
static BPlusNode *create_node(int is_leaf);
static void bplus_tree_clear(BPlusTree *tree);
static void bplus_tree_free_node(BPlusNode *node);
static int bplus_tree_search(const BPlusTree *tree, int key, long *value);
static int bplus_tree_insert(BPlusTree *tree, int key, long value);
static int bplus_tree_insert_recursive(BPlusNode *node, int key, long value, int *promoted_key,
                                       BPlusNode **promoted_child);
static int bplus_tree_insert_into_leaf(BPlusNode *node, int key, long value, int *promoted_key,
                                       BPlusNode **promoted_child);
static int bplus_tree_insert_into_internal(BPlusNode *node, int child_index, int key, BPlusNode *right_child,
                                           int *promoted_key, BPlusNode **promoted_child);
static int bplus_tree_child_index(const BPlusNode *node, int key);
static int bplus_tree_write_entries(FILE *file, const BPlusNode *node);

static IndexHandle *find_index_handle(const char *table_name);
static IndexHandle *ensure_index_handle(const TableMetadata *table);
static int ensure_data_file(const TableMetadata *table, char *error_message, size_t error_size);
static int load_index_file(IndexHandle *handle, char *error_message, size_t error_size);
static int validate_index_against_data(IndexHandle *handle, char *error_message, size_t error_size);
static int rebuild_index_from_data_file(IndexHandle *handle, char *error_message, size_t error_size);
static int persist_full_index(IndexHandle *handle);
static int append_index_entry(IndexHandle *handle, int id, long offset);
static int read_data_row(FILE *file, const TableMetadata *table, long offset, char fixed_row[ROW_SIZE]);
static int extract_id_from_fixed_row(const char fixed_row[ROW_SIZE], int *id);
static int parse_int_text(const char *text, int *value);
static long get_file_size(FILE *file);
static void set_error(char *error_message, size_t error_size, const char *message);

static IndexHandle INDEX_HANDLES[MAX_VALUES];
static int INDEX_HANDLE_COUNT = 0;

/* 인덱스 준비: 기존 인덱스를 열고, 없거나 손상된 경우 데이터 파일 기준으로 다시 만든다. */
int db_index_open_table(const TableMetadata *table, char *error_message, size_t error_size) {
    IndexHandle *handle;
    int load_result;
    int validate_result;

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

    bplus_tree_clear(&handle->tree);
    load_result = load_index_file(handle, error_message, error_size);
    if (load_result < 0) {
        return -1;
    }

    if (load_result > 0) {
        validate_result = validate_index_against_data(handle, error_message, error_size);
        if (validate_result < 0) {
            return -1;
        }
        if (validate_result > 0) {
            return 0;
        }
    }

    bplus_tree_clear(&handle->tree);
    return rebuild_index_from_data_file(handle, error_message, error_size);
}

/* 종료 정리: 모든 테이블 인덱스 트리 메모리를 해제한다. */
void db_index_shutdown_all(void) {
    for (int i = 0; i < INDEX_HANDLE_COUNT; i++) {
        bplus_tree_clear(&INDEX_HANDLES[i].tree);
        INDEX_HANDLES[i].table = NULL;
    }

    INDEX_HANDLE_COUNT = 0;
}

/* B+Tree 조회: id에 연결된 fixed row byte offset을 반환한다. */
int db_index_get(const char *table_name, int id, RowLocation *location) {
    IndexHandle *handle = find_index_handle(table_name);
    long offset;

    if (handle == NULL) {
        return -1;
    }

    if (!bplus_tree_search(&handle->tree, id, &offset)) {
        return 0;
    }

    location->offset = offset;
    return 1;
}

/* B+Tree 삽입: 새 id와 fixed row byte offset을 인덱스에 등록하고 파일에도 기록한다. */
int db_index_put(const char *table_name, int id, RowLocation location) {
    IndexHandle *handle = find_index_handle(table_name);
    int insert_result;

    if (handle == NULL || location.offset < 0 || location.offset % handle->table->row_size != 0) {
        return -1;
    }

    insert_result = bplus_tree_insert(&handle->tree, id, location.offset);
    if (insert_result <= 0) {
        return insert_result;
    }

    if (!append_index_entry(handle, id, location.offset)) {
        return -1;
    }

    return 1;
}

static BPlusNode *create_node(int is_leaf) {
    BPlusNode *node = calloc(1, sizeof(BPlusNode));

    if (node == NULL) {
        return NULL;
    }

    node->is_leaf = is_leaf;
    return node;
}

static void bplus_tree_clear(BPlusTree *tree) {
    bplus_tree_free_node(tree->root);
    tree->root = NULL;
    tree->size = 0;
}

static void bplus_tree_free_node(BPlusNode *node) {
    if (node == NULL) {
        return;
    }

    if (!node->is_leaf) {
        for (int i = 0; i <= node->key_count; i++) {
            bplus_tree_free_node(node->children[i]);
        }
    }

    free(node);
}

static int bplus_tree_search(const BPlusTree *tree, int key, long *value) {
    BPlusNode *node = tree->root;

    while (node != NULL && !node->is_leaf) {
        node = node->children[bplus_tree_child_index(node, key)];
    }

    if (node == NULL) {
        return 0;
    }

    for (int i = 0; i < node->key_count; i++) {
        if (node->keys[i] == key) {
            *value = node->values[i];
            return 1;
        }
    }

    return 0;
}

static int bplus_tree_insert(BPlusTree *tree, int key, long value) {
    int promoted_key;
    BPlusNode *promoted_child = NULL;
    int result;

    if (tree->root == NULL) {
        tree->root = create_node(1);
        if (tree->root == NULL) {
            return -1;
        }

        tree->root->keys[0] = key;
        tree->root->values[0] = value;
        tree->root->key_count = 1;
        tree->size = 1;
        return 1;
    }

    result = bplus_tree_insert_recursive(tree->root, key, value, &promoted_key, &promoted_child);
    if (result < 0 || result == 0) {
        return result;
    }

    if (result == 2) {
        BPlusNode *new_root = create_node(0);
        if (new_root == NULL) {
            return -1;
        }

        new_root->keys[0] = promoted_key;
        new_root->children[0] = tree->root;
        new_root->children[1] = promoted_child;
        new_root->key_count = 1;
        tree->root = new_root;
    }

    tree->size++;
    return 1;
}

static int bplus_tree_insert_recursive(BPlusNode *node, int key, long value, int *promoted_key,
                                       BPlusNode **promoted_child) {
    int child_index;
    int child_promoted_key;
    BPlusNode *child_promoted_node = NULL;
    int result;

    if (node->is_leaf) {
        return bplus_tree_insert_into_leaf(node, key, value, promoted_key, promoted_child);
    }

    child_index = bplus_tree_child_index(node, key);
    result = bplus_tree_insert_recursive(node->children[child_index], key, value, &child_promoted_key,
                                         &child_promoted_node);
    if (result != 2) {
        return result;
    }

    return bplus_tree_insert_into_internal(node, child_index, child_promoted_key, child_promoted_node, promoted_key,
                                           promoted_child);
}

static int bplus_tree_insert_into_leaf(BPlusNode *node, int key, long value, int *promoted_key,
                                       BPlusNode **promoted_child) {
    int insert_index = 0;
    int split_index;
    BPlusNode *new_leaf;

    while (insert_index < node->key_count && node->keys[insert_index] < key) {
        insert_index++;
    }

    if (insert_index < node->key_count && node->keys[insert_index] == key) {
        return 0;
    }

    for (int i = node->key_count; i > insert_index; i--) {
        node->keys[i] = node->keys[i - 1];
        node->values[i] = node->values[i - 1];
    }

    node->keys[insert_index] = key;
    node->values[insert_index] = value;
    node->key_count++;

    if (node->key_count <= BPLUS_MAX_KEYS) {
        return 1;
    }

    new_leaf = create_node(1);
    if (new_leaf == NULL) {
        return -1;
    }

    split_index = node->key_count / 2;
    new_leaf->key_count = node->key_count - split_index;
    for (int i = 0; i < new_leaf->key_count; i++) {
        new_leaf->keys[i] = node->keys[split_index + i];
        new_leaf->values[i] = node->values[split_index + i];
    }

    node->key_count = split_index;
    *promoted_key = new_leaf->keys[0];
    *promoted_child = new_leaf;
    return 2;
}

static int bplus_tree_insert_into_internal(BPlusNode *node, int child_index, int key, BPlusNode *right_child,
                                           int *promoted_key, BPlusNode **promoted_child) {
    int split_index;
    BPlusNode *new_internal;

    for (int i = node->key_count; i > child_index; i--) {
        node->keys[i] = node->keys[i - 1];
    }

    for (int i = node->key_count + 1; i > child_index + 1; i--) {
        node->children[i] = node->children[i - 1];
    }

    node->keys[child_index] = key;
    node->children[child_index + 1] = right_child;
    node->key_count++;

    if (node->key_count <= BPLUS_MAX_KEYS) {
        return 1;
    }

    new_internal = create_node(0);
    if (new_internal == NULL) {
        return -1;
    }

    split_index = node->key_count / 2;
    *promoted_key = node->keys[split_index];
    new_internal->key_count = node->key_count - split_index - 1;
    for (int i = 0; i < new_internal->key_count; i++) {
        new_internal->keys[i] = node->keys[split_index + 1 + i];
    }
    for (int i = 0; i <= new_internal->key_count; i++) {
        new_internal->children[i] = node->children[split_index + 1 + i];
    }

    node->key_count = split_index;
    *promoted_child = new_internal;
    return 2;
}

static int bplus_tree_child_index(const BPlusNode *node, int key) {
    int index = 0;

    while (index < node->key_count && key >= node->keys[index]) {
        index++;
    }

    return index;
}

static int bplus_tree_write_entries(FILE *file, const BPlusNode *node) {
    if (node == NULL) {
        return 1;
    }

    if (node->is_leaf) {
        for (int i = 0; i < node->key_count; i++) {
            if (fprintf(file, "%d %ld\n", node->keys[i], node->values[i]) < 0) {
                return 0;
            }
        }

        return 1;
    }

    for (int i = 0; i <= node->key_count; i++) {
        if (!bplus_tree_write_entries(file, node->children[i])) {
            return 0;
        }
    }

    return 1;
}

static IndexHandle *find_index_handle(const char *table_name) {
    for (int i = 0; i < INDEX_HANDLE_COUNT; i++) {
        if (strcmp(INDEX_HANDLES[i].table->name, table_name) == 0) {
            return &INDEX_HANDLES[i];
        }
    }

    return NULL;
}

static IndexHandle *ensure_index_handle(const TableMetadata *table) {
    IndexHandle *handle = find_index_handle(table->name);

    if (handle != NULL) {
        return handle;
    }

    if (INDEX_HANDLE_COUNT >= MAX_VALUES) {
        return NULL;
    }

    handle = &INDEX_HANDLES[INDEX_HANDLE_COUNT];
    handle->table = table;
    handle->tree.root = NULL;
    handle->tree.size = 0;
    INDEX_HANDLE_COUNT++;
    return handle;
}

static int ensure_data_file(const TableMetadata *table, char *error_message, size_t error_size) {
    FILE *file = fopen(table->csv_file_path, "ab");

    if (file == NULL) {
        set_error(error_message, error_size, "CSV 파일을 열 수 없습니다");
        return 0;
    }

    fclose(file);
    return 1;
}

static int load_index_file(IndexHandle *handle, char *error_message, size_t error_size) {
    FILE *file = fopen(handle->table->index_file_path, "r");
    char line[MAX_INPUT_SIZE];

    (void) error_message;
    (void) error_size;

    if (file == NULL) {
        return 0;
    }

    if (fgets(line, sizeof(line), file) == NULL ||
        (strcmp(line, INDEX_HEADER "\n") != 0 && strcmp(line, INDEX_HEADER "\r\n") != 0)) {
        fclose(file);
        return 0;
    }

    while (fgets(line, sizeof(line), file) != NULL) {
        char *offset_text;
        char *newline;
        int id;
        long offset;

        newline = strchr(line, '\n');
        if (newline != NULL) {
            *newline = '\0';
        }

        offset_text = strchr(line, ' ');
        if (offset_text == NULL) {
            fclose(file);
            return 0;
        }

        *offset_text = '\0';
        offset_text++;
        if (!parse_int_text(line, &id)) {
            fclose(file);
            return 0;
        }

        offset = strtol(offset_text, &newline, 10);
        if (*offset_text == '\0' || *newline != '\0' || offset < 0 || offset % handle->table->row_size != 0) {
            fclose(file);
            return 0;
        }

        if (bplus_tree_insert(&handle->tree, id, offset) != 1) {
            fclose(file);
            return 0;
        }
    }

    fclose(file);
    return 1;
}

static int validate_index_against_data(IndexHandle *handle, char *error_message, size_t error_size) {
    FILE *file = fopen(handle->table->csv_file_path, "rb");
    long file_size;
    size_t row_count = 0;

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
        long indexed_offset;

        if (!read_data_row(file, handle->table, offset, fixed_row) || !extract_id_from_fixed_row(fixed_row, &id)) {
            fclose(file);
            set_error(error_message, error_size, "데이터 파일이 올바르지 않습니다");
            return -1;
        }

        if (!bplus_tree_search(&handle->tree, id, &indexed_offset) || indexed_offset != offset) {
            fclose(file);
            return 0;
        }

        row_count++;
    }

    fclose(file);
    return row_count == handle->tree.size;
}

static int rebuild_index_from_data_file(IndexHandle *handle, char *error_message, size_t error_size) {
    FILE *file = fopen(handle->table->csv_file_path, "rb");
    long file_size;

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

        if (!read_data_row(file, handle->table, offset, fixed_row) || !extract_id_from_fixed_row(fixed_row, &id) ||
            bplus_tree_insert(&handle->tree, id, offset) != 1) {
            fclose(file);
            set_error(error_message, error_size, "데이터 파일이 올바르지 않습니다");
            return -1;
        }
    }

    fclose(file);
    if (!persist_full_index(handle)) {
        set_error(error_message, error_size, "인덱스를 갱신할 수 없습니다");
        return -1;
    }

    return 0;
}

static int persist_full_index(IndexHandle *handle) {
    FILE *file = fopen(handle->table->index_file_path, "w");
    int ok;

    if (file == NULL) {
        return 0;
    }

    ok = fprintf(file, "%s\n", INDEX_HEADER) >= 0 && bplus_tree_write_entries(file, handle->tree.root) &&
         fflush(file) == 0;
    fclose(file);
    return ok;
}

static int append_index_entry(IndexHandle *handle, int id, long offset) {
    FILE *file = fopen(handle->table->index_file_path, "a+");
    long file_size;
    int ok;

    if (file == NULL) {
        return 0;
    }

    fseek(file, 0, SEEK_END);
    file_size = ftell(file);
    if (file_size < 0) {
        fclose(file);
        return 0;
    }

    ok = 1;
    if (file_size == 0) {
        ok = fprintf(file, "%s\n", INDEX_HEADER) >= 0;
    }

    ok = ok && fprintf(file, "%d %ld\n", id, offset) >= 0 && fflush(file) == 0;
    fclose(file);
    return ok;
}

static int read_data_row(FILE *file, const TableMetadata *table, long offset, char fixed_row[ROW_SIZE]) {
    if (fseek(file, offset, SEEK_SET) != 0) {
        return 0;
    }

    if (fread(fixed_row, 1, table->row_size, file) != (size_t) table->row_size) {
        return 0;
    }

    return fixed_row[ROW_DATA_SIZE] == '\n';
}

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

    return parse_int_text(logical_row, id);
}

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

static void set_error(char *error_message, size_t error_size, const char *message) {
    if (error_size == 0) {
        return;
    }

    snprintf(error_message, error_size, "%s", message);
}
