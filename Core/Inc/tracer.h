/*
 * tracer.h
 *
 *  Created on: Jan 10, 2023
 * 	Updated on: Mar 20, 2025
 *      Author: live, Michael Reno
 */

#ifndef INC_TRACER_H_
#define INC_TRACER_H_

#include <stdio.h>
#include <stdint.h>
#include <string.h>

// Rolling buffer size for trace records
#define TRACE_BUFFER_SIZE 1024

// Trace evemts for logging
typedef enum {
    TRACE_EVENT_CC,
    TRACE_EVENT_TC,
    TRACE_EVENT_TI,
    TRACE_EVENT_TO
} trace_event_type_t;

typedef struct {
    uint32_t timestamp;
    trace_event_type_t type;
    uint32_t task_id;
    char task_name[16]; // Only used for TC
} trace_record_t;

// Circular Buffer
static trace_record_t trace_buffer[TRACE_BUFFER_SIZE];
static volatile uint32_t trace_index = 0;

static void tracer_log(trace_event_type_t type, uint32_t task_id, const char* name) {
    trace_record_t* rec = &trace_buffer[trace_index];
    rec->timestamp = DWT->CYCCNT;
    rec->type = type;
    rec->task_id = task_id;
    if (name && type == TRACE_EVENT_TC) {
        strncpy(rec->task_name, name, sizeof(rec->task_name) - 1);
        rec->task_name[sizeof(rec->task_name) - 1] = '\0';
    } else {
        rec->task_name[0] = '\0';
    }

    // For real-time log viewing
    switch (type) {
        case TRACE_EVENT_CC:
            printf("%6lu CC %lu\n", rec->timestamp, SystemCoreClock);
            break;
        case TRACE_EVENT_TC:
            printf("%6lu TC %lu %s\n", rec->timestamp, task_id, rec->task_name);
            break;
        case TRACE_EVENT_TI:
            printf("%6lu TI %lu\n", rec->timestamp, task_id);
            break;
        case TRACE_EVENT_TO:
            printf("%6lu TO %lu\n", rec->timestamp, task_id);
            break;
    }

    trace_index = (trace_index + 1) % TRACE_BUFFER_SIZE;
}

static void tracer_init() {
    static int initialized = 0;
    if (initialized)
        return;
    initialized = 1;

    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    ITM->LAR = 0xC5ACCE55;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    DWT->CYCCNT = 0;

    tracer_log(TRACE_EVENT_CC, 0, NULL);
}

// Trace Macros
__STATIC_INLINE void tracer_TASK_CREATE(uint32_t uxTaskNumber, char* taskName) {
    tracer_init();
    tracer_log(TRACE_EVENT_TC, uxTaskNumber, taskName);
}

__STATIC_INLINE void tracer_TASK_SWITCHED_IN(uint32_t uxTaskNumber) {
    tracer_log(TRACE_EVENT_TI, uxTaskNumber, NULL);
}

__STATIC_INLINE void tracer_TASK_SWITCHED_OUT(uint32_t uxTaskNumber) {
    tracer_log(TRACE_EVENT_TO, uxTaskNumber, NULL);
}

// Connect with FreeRTOS Macros
#define traceTASK_CREATE(pxNewTCB)    tracer_TASK_CREATE(pxNewTCB->uxTCBNumber, pxNewTCB->pcTaskName);
#define traceTASK_SWITCHED_IN()       tracer_TASK_SWITCHED_IN(pxCurrentTCB->uxTCBNumber);
#define traceTASK_SWITCHED_OUT()      tracer_TASK_SWITCHED_OUT(pxCurrentTCB->uxTCBNumber);

#endif /* INC_TRACER_H_ */
