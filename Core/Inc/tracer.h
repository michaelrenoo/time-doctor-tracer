/*
 * tracer.h
 *
 *  Created on: Jan 10, 2023
 * 	Updated on: Mar 20, 2025 (modified from original)
 *      Author: live, Michael Reno
 */

#ifndef INC_TRACER_H_
#define INC_TRACER_H_

#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include "stm32l4xx_hal.h"

// TODO: move to config file
#define FLASH_LOG_PAGES       8               // Use 8 pages (16KB) as mentioned here: https://community.st.com/t5/stm32-mcus-products/eeprom-emulation-in-flash-with-nucleo-stm32l432kc-linker-file/td-p/103428
#define FLASH_LOG_SIZE        (FLASH_PAGE_SIZE * FLASH_LOG_PAGES)
#define FLASH_LOG_START_PAGE  120             // Starting from 8th-to-last page (out of 128 pages)
#define FLASH_LOG_ADDRESS     (0x08000000 + FLASH_PAGE_SIZE * FLASH_LOG_START_PAGE)

static volatile uint8_t flash_log_ready = 0;

// Flash write buffer (to minimize erase cycles)
static uint8_t flash_buffer[FLASH_PAGE_SIZE];
static uint32_t flash_buffer_index = 0;
static uint32_t flash_write_address = FLASH_LOG_ADDRESS;

#define TRACE_BUFFER_SIZE 1024  // Rolling buffer size for trace records
#define MAX_TASKS 32  // Maximum number of tasks to track

// Magic header for log file
// Best practice to ID log file and check for data integrity
#define TRACE_MAGIC "RENO"
#define TRACE_VERSION 1

// Trace events enum
// Add more events for more FreeRTOS events/macros
typedef enum
{
    TRACE_EVENT_CC, // Clock Calibration
    TRACE_EVENT_TC, // Task Create
    TRACE_EVENT_TI, // Task In
    TRACE_EVENT_TO  // Task Out
} trace_event_type_t;

// Trace event structure
// This would be how the log is stored
typedef struct
{
    uint32_t timestamp;
    uint8_t type;
    uint32_t task_id;
} trace_event_t;

// Task metadata structure to store task information (not in the circular buffer)
typedef struct
{
    uint32_t task_id;
    char task_name[16];
    uint8_t used;
} task_metadata_t;

// Binary header
typedef struct
{
    char magic[4];  // 4 chars for magic header title
    uint8_t version;
    uint16_t num_tasks;
} log_header_t;

// Circular Buffer for events
static trace_event_t trace_buffer[TRACE_BUFFER_SIZE];
static volatile uint32_t trace_index = 0;
static volatile uint32_t trace_count = 0;

static task_metadata_t task_table[MAX_TASKS];
static uint16_t task_count = 0;

extern UART_HandleTypeDef huart2;

/**
  * @brief  This function adds a task to the task metadata table.
  * @param  task_id: ID of the task to be added
  * @param  name: Name of the task to be added
  * @retval Index of the task in the task table, or 0xFFFF if failed
  * @note   This function checks if the task already exists in the table.
  *        If it does, it returns the index of the existing task.
  */
static uint16_t tracer_add_task(uint32_t task_id, const char *name)
{
    for (uint16_t i = 0; i < task_count; i++)
    {
        if (task_table[i].task_id == task_id)
        {
            return i;
        }
    }

    // Add new task only if space available
    if (task_count < MAX_TASKS)
    {
        task_table[task_count].task_id = task_id;
        if (name)
        {
            strncpy(task_table[task_count].task_name, name, sizeof(task_table[task_count].task_name) - 1);
            task_table[task_count].task_name[sizeof(task_table[task_count].task_name) - 1] = '\0';
        }
        else
        {
            snprintf(task_table[task_count].task_name, sizeof(task_table[task_count].task_name), "Task_%lu", task_id);
        }
        task_table[task_count].used = 1;
        return task_count++;
    }

    return 0xFFFF;
}

/**
  * @brief  This function logs a trace event.
  * @param  type: Type of the trace event
  * @param  task_id: ID of the task associated with the event
  * @param  name: Name of the task (if applicable)
  * @retval None
  */
static void tracer_log(trace_event_type_t type, uint32_t task_id, const char *name)
{
    trace_event_t *rec = &trace_buffer[trace_index];
    rec->timestamp = DWT->CYCCNT;
    rec->type = (uint8_t)type;
    rec->task_id = task_id;

    // Check for task creation and store separately
    if (type == TRACE_EVENT_TC)
    {
        tracer_add_task(task_id, name);
    }

    trace_index = (trace_index + 1) % TRACE_BUFFER_SIZE;
    if (trace_count < TRACE_BUFFER_SIZE)
    {
        trace_count++;
    }
}

/**
  * @brief  This function initializes the tracer.
  * @retval None
  */
static void tracer_init()
{
    static int initialized = 0;
    if (initialized)
        return;
    initialized = 1;

    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    ITM->LAR = 0xC5ACCE55;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    DWT->CYCCNT = 0;

    memset(task_table, 0, sizeof(task_table));
    task_count = 0;

    trace_index = 0;
    trace_count = 0;

    tracer_log(TRACE_EVENT_CC, 0, NULL);
}

/**
  * @brief  This function dumps the trace logs to UART.
  * @retval None
  */
void tracer_dump()
{
    log_header_t header;
    memcpy(header.magic, TRACE_MAGIC, 4);
    header.version = TRACE_VERSION;
    header.num_tasks = task_count;

    // Send header
    // More info here: https://github.com/dekuNukem/STM32_tutorials/blob/master/lesson1_serial_helloworld/HAL_UART_Transmit_details.md
    HAL_UART_Transmit(&huart2, (uint8_t *)&header, sizeof(header), HAL_MAX_DELAY);

    // Send task metadata table
    HAL_UART_Transmit(&huart2, (uint8_t *)task_table, sizeof(task_metadata_t) * task_count, HAL_MAX_DELAY);

    // Send trace events - handle circular buffer correctly
    uint32_t start_idx = 0;
    if (trace_count == TRACE_BUFFER_SIZE)
    {
        // Buffer is full, start from oldest entry
        start_idx = trace_index;
    }

    for (uint32_t i = 0; i < trace_count; i++)
    {
        uint32_t idx = (start_idx + i) % TRACE_BUFFER_SIZE;
        HAL_UART_Transmit(&huart2, (uint8_t *)&trace_buffer[idx], sizeof(trace_event_t), HAL_MAX_DELAY);
    }
}

void tracer_flash_init(void) {
    FLASH_EraseInitTypeDef EraseInitStruct = {0};
    uint32_t PageError = 0;
    
    HAL_FLASH_Unlock();
    
    EraseInitStruct.TypeErase = FLASH_TYPEERASE_PAGES;
    EraseInitStruct.Banks = FLASH_BANK_1;
    EraseInitStruct.Page = FLASH_LOG_START_PAGE;
    EraseInitStruct.NbPages = FLASH_LOG_PAGES;
    
    if (HAL_FLASHEx_Erase(&EraseInitStruct, &PageError) != HAL_OK) {
        HAL_FLASH_Lock();
        return;
    }
    
    HAL_FLASH_Lock();
    
    // Resetting flash buffer and address
    flash_buffer_index = 0;
    flash_write_address = FLASH_LOG_ADDRESS;
    flash_log_ready = 1;
}

/**
 * Write data to flash
 * @param data Pointer to data to write
 * @param size Size of data in bytes
 */
void tracer_flash_write(uint8_t* data, uint32_t size) {
    uint32_t i;
    
    if (!flash_log_ready) {
        return; 
    }
    
    for (i = 0; i < size; i++) {
        flash_buffer[flash_buffer_index++] = data[i];
        
        if (flash_buffer_index >= FLASH_PAGE_SIZE || 
            i == size-1 ||
            flash_write_address + flash_buffer_index >= FLASH_LOG_ADDRESS + FLASH_LOG_SIZE) {
            
            // STM32L4 requires 8-byte alignment for flash programming
            // https://community.st.com/t5/stm32-mcus-products/eeprom-emulation-in-flash-with-nucleo-stm32l432kc-linker-file/td-p/103428
            if (flash_buffer_index % 8 != 0) {
                // Add padding to maintain 8-byte boundary
                uint32_t padding = 8 - (flash_buffer_index % 8);
                for (uint32_t p = 0; p < padding; p++) {
                    flash_buffer[flash_buffer_index++] = 0xFF;  // Erased state
                }
            }
            
            HAL_FLASH_Unlock();
            
            // Write buffer to flash in 8-byte (double-word) chunks
            for (uint32_t j = 0; j < flash_buffer_index; j += 8) {
                // STM32L4 requires double-word (64-bit) programming
                // More info here: https://community.st.com/t5/stm32-mcus-products/eeprom-emulation-in-flash-with-nucleo-stm32l432kc-linker-file/td-p/103428
                uint64_t data64 = 0;
                for (uint32_t k = 0; k < 8 && j+k < flash_buffer_index; k++) {
                    data64 |= (uint64_t)flash_buffer[j+k] << (k*8);
                }
                
                if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_DOUBLEWORD, 
                                    flash_write_address + j, 
                                    data64) != HAL_OK) {
                    HAL_FLASH_Lock();
                    flash_log_ready = 0;  // To mark as unavailable
                    return;
                }
            }
            
            HAL_FLASH_Lock();
            
            flash_write_address += flash_buffer_index;
            flash_buffer_index = 0;
            
            if (flash_write_address >= FLASH_LOG_ADDRESS + FLASH_LOG_SIZE) {
                flash_log_ready = 0;  // To mark as full
                break;
            }
        }
    }
}

/**
 * @brief Dump trace data to flash memory
 * This writes the current trace buffer to flash
 * @retfail None
 */
void tracer_dump_to_flash(void) {
    tracer_flash_init();
    
    log_header_t header;
    memcpy(header.magic, TRACE_MAGIC, 4);
    header.version = TRACE_VERSION;
    header.num_tasks = task_count;
    header.padding = 0;
    
    tracer_flash_write((uint8_t*)&header, sizeof(header));
    
    tracer_flash_write((uint8_t*)task_table, sizeof(task_metadata_t) * task_count);
    
    uint32_t start_idx = 0;
    if (trace_count == TRACE_BUFFER_SIZE) {
        start_idx = trace_index;
    }
    
    for (uint32_t i = 0; i < trace_count; i++) {
        uint32_t idx = (start_idx + i) % TRACE_BUFFER_SIZE;
        tracer_flash_write((uint8_t*)&trace_buffer[idx], sizeof(trace_event_t));
    }
}

/**
 * @brief Retrieve logs from flash via UART
 * This sends the stored log data over UART
 * @retval None
 */
void tracer_retrieve_logs(void) {
    uint32_t* magic_check = (uint32_t*)FLASH_LOG_ADDRESS;
    if (*magic_check != *(uint32_t*)TRACE_MAGIC) {
        const char* msg = "No valid log data found\r\n";
        HAL_UART_Transmit(&huart2, (uint8_t*)msg, strlen(msg), HAL_MAX_DELAY);
        return;
    }
    
    log_header_t* header = (log_header_t*)FLASH_LOG_ADDRESS;
    uint16_t num_tasks = header->num_tasks;
    
    uint32_t metadata_size = sizeof(log_header_t) + (num_tasks * sizeof(task_metadata_t));
    
    HAL_UART_Transmit(&huart2, (uint8_t*)FLASH_LOG_ADDRESS, metadata_size, HAL_MAX_DELAY);
    
    uint8_t* event_data = (uint8_t*)(FLASH_LOG_ADDRESS + metadata_size);
    uint32_t max_events = (FLASH_LOG_SIZE - metadata_size) / sizeof(trace_event_t);
    
    uint32_t valid_events = 0;
    for (uint32_t i = 0; i < max_events; i++) {
        uint8_t is_erased = 1;
        for (uint32_t j = 0; j < sizeof(trace_event_t); j++) {
            if (event_data[i * sizeof(trace_event_t) + j] != 0xFF) {
                is_erased = 0;
                break;
            }
        }
        
        if (is_erased) {
            break;
        }
        
        valid_events++;
    }
    
    if (valid_events > 0) {
        HAL_UART_Transmit(&huart2, event_data, valid_events * sizeof(trace_event_t), HAL_MAX_DELAY);
    }
}

// Trace Macros
__STATIC_INLINE void tracer_TASK_CREATE(uint32_t uxTaskNumber, char *taskName)
{
    tracer_init();
    tracer_log(TRACE_EVENT_TC, uxTaskNumber, taskName);
}

__STATIC_INLINE void tracer_TASK_SWITCHED_IN(uint32_t uxTaskNumber)
{
    tracer_log(TRACE_EVENT_TI, uxTaskNumber, NULL);
}

__STATIC_INLINE void tracer_TASK_SWITCHED_OUT(uint32_t uxTaskNumber)
{
    tracer_log(TRACE_EVENT_TO, uxTaskNumber, NULL);
}

// Connect with FreeRTOS Macros
#define traceTASK_CREATE(pxNewTCB) tracer_TASK_CREATE(pxNewTCB->uxTCBNumber, pxNewTCB->pcTaskName);
#define traceTASK_SWITCHED_IN() tracer_TASK_SWITCHED_IN(pxCurrentTCB->uxTCBNumber);
#define traceTASK_SWITCHED_OUT() tracer_TASK_SWITCHED_OUT(pxCurrentTCB->uxTCBNumber);

#endif /* INC_TRACER_H_ */
