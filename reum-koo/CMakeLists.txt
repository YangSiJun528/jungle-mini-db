cmake_minimum_required(VERSION 3.20)
project(jungle_mini_db C)

set(CMAKE_C_STANDARD 11)
enable_testing()

add_executable(
        jungle_mini_db
        main.c
        parser.c
        executor.c
        db_index.c
        memory_bptree.c
)
target_compile_definitions(jungle_mini_db PRIVATE PROJECT_ROOT_DIR="${CMAKE_SOURCE_DIR}")

add_executable(
        memory_bptree_tests
        tests/test_memory_bptree.c
        memory_bptree.c
)
target_include_directories(memory_bptree_tests PRIVATE ${CMAKE_SOURCE_DIR})
add_test(NAME memory_bptree_tests COMMAND memory_bptree_tests)

find_package(Python3 COMPONENTS Interpreter REQUIRED)
add_test(
        NAME mini_db_requirements
        COMMAND ${Python3_EXECUTABLE} ${CMAKE_SOURCE_DIR}/tests/test_mini_db_requirements.py ${CMAKE_SOURCE_DIR}
)
