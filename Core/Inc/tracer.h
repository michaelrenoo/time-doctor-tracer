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
