/*
 * tracer.h
 *
 *  Created on: Jan 10, 2023
 *  Updated on: May 27, 2025
 *      Author: live, Michael Reno
 */

#ifndef INC_TRACER_H_
#define INC_TRACER_H_

#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "stm32l4xx_hal.h"

// Configuration
#define TRACE_BUFFER_SIZE 1024  // Rolling buffer size for trace records
#define TRACE_MAGIC "RENO"      // Magic header for log file
#define TRACE_VERSION 1
#define TRACER_DEBUG 0          // Set to 0 to disable verbose debug messages

// Trace events enum
// TODO: Add more events for more FreeRTOS events/macros
typedef enum
{
    TRACE_EVENT_CC, // Clock Calibration
    TRACE_EVENT_TC, // Task Create
    TRACE_EVENT_TI, // Task In
    TRACE_EVENT_TO  // Task Out
} trace_event_type_t;

// Packed structure to remove padding for binary transmission
typedef struct __attribute__((packed))
{
    uint32_t timestamp;
    uint8_t type;
    uint32_t task_id;
} trace_event_t;

// Binary header - exactly 8 bytes
typedef struct __attribute__((packed))
{
    char magic[4];
    uint8_t version;
    uint8_t packet_type; // 0=header, 1=task_info, 2=events
    uint16_t data_length;
} uart_packet_header_t;

// Circular Buffer for events
static trace_event_t trace_buffer[TRACE_BUFFER_SIZE];
static volatile uint32_t trace_index = 0;
static volatile uint32_t trace_count = 0;

// UART transmission state
static volatile uint8_t uart_busy = 0;
static uint32_t last_sent_index = 0;

// Statistics and debugging
static volatile uint32_t trace_hook_calls = 0;
static volatile uint32_t sent_events = 0;
static volatile uint32_t packet_sequence = 0;

extern UART_HandleTypeDef huart2;

// Function declarations
static void tracer_log(trace_event_type_t type, uint32_t task_id, const char *name);
static void tracer_init(void);
static void tracer_send_events(void);
static void tracer_process(void);

// Debug function declarations
static void tracer_debug_buffer(void);
static void debug_binary_data(uint8_t* data, uint16_t length);

/**
 * @brief Debug function to display buffer contents
 */
static void tracer_debug_buffer()
{
    #if TRACER_DEBUG
        if (trace_count == 0)
        {
            HAL_UART_Transmit(&huart2, (uint8_t *)"Buffer empty\r\n", 14, HAL_MAX_DELAY);
            return;
        }

        char debug[100];
        snprintf(debug, sizeof(debug), "Buffer has %lu events, index=%lu, last_sent=%lu\r\n",
                trace_count, trace_index, last_sent_index);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);

        // Start index to view the buffer
        uint32_t start_idx;
        if (trace_count == TRACE_BUFFER_SIZE)
        {
            // Buffer is full, oldest event is at trace_index (next to be overwritten)
            start_idx = trace_index;
        }
        else
        {
            // Buffer is not full, oldest event is at index 0
            start_idx = 0;
        }

        // Show up to 5 events from the buffer
        uint32_t events_to_show = (trace_count > 5) ? 5 : trace_count;

        for (uint32_t i = 0; i < events_to_show; i++)
        {
            uint32_t event_idx = (start_idx + i) % TRACE_BUFFER_SIZE;
            trace_event_t *event = &trace_buffer[event_idx];

            const char *type_str = "??";
            switch (event->type)
            {
            case TRACE_EVENT_CC:
                type_str = "CC";
                break;
            case TRACE_EVENT_TC:
                type_str = "TC";
                break;
            case TRACE_EVENT_TI:
                type_str = "TI";
                break;
            case TRACE_EVENT_TO:
                type_str = "TO";
                break;
            }

            snprintf(debug, sizeof(debug), "  Event[%lu]: type=%s, task=%lu, time=%lu\r\n",
                    i, type_str, event->task_id, event->timestamp);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        }
    #endif
}

/**
 * @brief Debug function to display binary data
 * @param data Pointer to the binary data
 * @param length Length of the data
 */
static void debug_binary_data(uint8_t* data, uint16_t length) {
    #if TRACER_DEBUG
        char debug[100];
        snprintf(debug, sizeof(debug), "Binary data (%u bytes): ", length);
        HAL_UART_Transmit(&huart2, (uint8_t*)debug, strlen(debug), HAL_MAX_DELAY);
        
        for (uint16_t i = 0; i < length && i < 20; i++) {
            snprintf(debug, sizeof(debug), "%02X ", data[i]);
            HAL_UART_Transmit(&huart2, (uint8_t*)debug, strlen(debug), HAL_MAX_DELAY);
        }
        
        if (length > 20) {
            HAL_UART_Transmit(&huart2, (uint8_t*)"...", 3, HAL_MAX_DELAY);
        }
        
        HAL_UART_Transmit(&huart2, (uint8_t*)"\r\n", 2, HAL_MAX_DELAY);
    #endif
}

/**
 * @brief Log a trace event
 * @param type Type of the trace event
 * @param task_id ID of the task associated with the event
 * @param name Name of the task (if applicable)
 * @retval None
 */
static void tracer_log(trace_event_type_t type, uint32_t task_id, const char *name)
{
    trace_hook_calls++;

    #if TRACER_DEBUG
        char debug[100];
        snprintf(debug, sizeof(debug), "LOGGING: type=%d, task=%lu\r\n", type, task_id);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    // Record in the circular buffer
    trace_event_t *rec = &trace_buffer[trace_index];
    rec->timestamp = DWT->CYCCNT;
    rec->type = (uint8_t)type;
    rec->task_id = task_id;

    // Update circular buffer pointers
    trace_index = (trace_index + 1) % TRACE_BUFFER_SIZE;
    if (trace_count < TRACE_BUFFER_SIZE)
    {
        trace_count++;
    }

    #if TRACER_DEBUG
        // Debug buffer state after adding event
        snprintf(debug, sizeof(debug), "Buffer: count=%lu, index=%lu\r\n",
                trace_count, trace_index);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif
}

/**
 * @brief Initialize the tracer
 */
static void tracer_init()
{
    static uint8_t initialized = 0;
    if (initialized)
    {
        return;
    }
    initialized = 1;

    #if TRACER_DEBUG
        char msg[] = "Initializing tracer...\r\n";
        HAL_UART_Transmit(&huart2, (uint8_t *)msg, strlen(msg), HAL_MAX_DELAY);
    #endif

    // Cycle counter for timestamps
    CoreDebug->DEMCR |= CoreDebug_DEMCR_TRCENA_Msk;
    ITM->LAR = 0xC5ACCE55;
    DWT->CTRL |= DWT_CTRL_CYCCNTENA_Msk;
    DWT->CYCCNT = 0;

    // Clear data structures
    trace_index = 0;
    trace_count = 0;
    uart_busy = 0;
    last_sent_index = 0;
    trace_hook_calls = 0;
    sent_events = 0;
    packet_sequence = 0;

    // Log initialization event
    uint32_t cpu_freq = SystemCoreClock;

    #if TRACER_DEBUG
        char debug[100];
        snprintf(debug, sizeof(debug), "CC event created at t=%lu\r\n", DWT->CYCCNT);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    tracer_log(TRACE_EVENT_CC, cpu_freq, NULL);

    #if TRACER_DEBUG
        HAL_UART_Transmit(&huart2, (uint8_t *)"Tracer init complete\r\n", 22, HAL_MAX_DELAY);
    #endif
}

/**
 * @brief Send trace events over UART
 * Sends a batch of events from the circular buffer
 */
static void tracer_send_events()
{
    #if TRACER_DEBUG
    char debug[100];
    snprintf(debug, sizeof(debug), "tracer_send_events: count=%lu, index=%lu\r\n", 
             trace_count, trace_index);
    HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    if (trace_count == 0)
    {
        #if TRACER_DEBUG
            char debug[] = "No events to send\r\n";
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        #endif
        return;
    }

    // Calculate events to send at once
    uint32_t max_events_per_batch = 8;
    uint32_t events_to_send = (trace_count > max_events_per_batch) ? max_events_per_batch : trace_count;
    uint16_t data_length = events_to_send * sizeof(trace_event_t);

    #if TRACER_DEBUG
        // Debug output of events
        char debug[100];
        snprintf(debug, sizeof(debug),
                "Sending %lu events, each %lu bytes, total %lu bytes\r\n",
                events_to_send, (uint32_t)sizeof(trace_event_t), data_length);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    // Create a buffer for header + all events
    uint8_t packet_buffer[8 + (5 * sizeof(trace_event_t))];
    memset(packet_buffer, 0, sizeof(packet_buffer));

    // Header
    packet_buffer[0] = 'R';
    packet_buffer[1] = 'E';
    packet_buffer[2] = 'N';
    packet_buffer[3] = 'O';
    packet_buffer[4] = TRACE_VERSION;
    packet_buffer[5] = 0x02;                      // Events packet
    packet_buffer[6] = data_length & 0xFF;        // LSB
    packet_buffer[7] = (data_length >> 8) & 0xFF; // MSB

    uint32_t start_idx;
    if (trace_count >= TRACE_BUFFER_SIZE)
    {
        // Buffer is full, the oldest entry is at the next position to be overwritten
        start_idx = trace_index;
    }
    else if (last_sent_index < trace_index)
    {
        // Not wrapped around yet, start from last_sent_index
        start_idx = last_sent_index;
    }
    else
    {
        // All data up to the end of buffer and wrapped around
        start_idx = 0;
    }

    #if TRACER_DEBUG
        snprintf(debug, sizeof(debug), "Buffer: count=%lu, start_idx=%lu, index=%lu, last_sent=%lu\r\n", 
                trace_count, start_idx, trace_index, last_sent_index);
        HAL_UART_Transmit(&huart2, (uint8_t*)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    // Copy events data AFTER header
    for (uint32_t i = 0; i < events_to_send; i++)
    {
        uint32_t event_idx = (start_idx + i) % TRACE_BUFFER_SIZE;
        trace_event_t *event = &trace_buffer[event_idx];

        #if TRACER_DEBUG
            // Debug each event
            const char *type_str = "??";
            switch (event->type)
            {
            case TRACE_EVENT_CC:
                type_str = "CC";
                break;
            case TRACE_EVENT_TC:
                type_str = "TC";
                break;
            case TRACE_EVENT_TI:
                type_str = "TI";
                break;
            case TRACE_EVENT_TO:
                type_str = "TO";
                break;
            }
            snprintf(debug, sizeof(debug), "  Event[%lu]: type=%s, task=%lu, time=%lu\r\n",
                    i, type_str, event->task_id, event->timestamp);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        #endif

        uint8_t* dest = &packet_buffer[8 + (i * sizeof(trace_event_t))];
        memcpy(dest, event, sizeof(trace_event_t));

        #if TRACER_DEBUG
            // Verify binary data for this event
            debug_binary_data(dest, sizeof(trace_event_t));
        #endif
    }

    // Send the entire packet at once
    HAL_StatusTypeDef status = HAL_UART_Transmit(&huart2, packet_buffer, 8 + data_length, HAL_MAX_DELAY);

    #if TRACER_DEBUG
        // Debug transmission status
        if (status != HAL_OK)
        {
            snprintf(debug, sizeof(debug), "UART transmission error: %d\r\n", status);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
            return;
        }
    #endif

    if (status != HAL_OK)
    {
        return;
    }

    // Update statistics
    sent_events += events_to_send;
    packet_sequence++;

    // Update the last sent index - we sent events from start_idx to start_idx+events_to_send-1
    last_sent_index = (start_idx + events_to_send) % TRACE_BUFFER_SIZE;

    // Update trace count
    if (trace_count >= events_to_send)
    {
        trace_count -= events_to_send;
    }
    else
    {
        trace_count = 0;
    }

    #if TRACER_DEBUG
        // Debug confirmation message
        snprintf(debug, sizeof(debug), "After send: trace_count=%lu, last_sent_index=%lu\r\n",
                trace_count, last_sent_index);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif
}

/**
 * @brief Process tracing operations
 * This should be called periodically from a low-priority task
 */
static void tracer_process()
{
    static uint32_t counter = 0;
    counter++;

    // Send heartbeat every 50 iterations (500ms at 10ms task delay)
    if (counter % 50 == 0)
    {
        uint8_t packet[8] = {0};

        // Magic header
        packet[0] = 'R';
        packet[1] = 'E';
        packet[2] = 'N';
        packet[3] = 'O';

        // Version and type
        packet[4] = TRACE_VERSION;
        packet[5] = 0x42; // Heartbeat marker

        // 16-bit counter value
        uint16_t heartbeat_counter = counter;
        packet[6] = heartbeat_counter & 0xFF;
        packet[7] = (heartbeat_counter >> 8) & 0xFF;

        HAL_UART_Transmit(&huart2, packet, 8, HAL_MAX_DELAY);
        
        // Resend CC every 5 seconds
        if (counter % 500 == 0) {
            tracer_log(TRACE_EVENT_CC, SystemCoreClock, NULL);
            
            #if TRACER_DEBUG
                char debug[60];
                snprintf(debug, sizeof(debug), "Periodic CC event added (counter=%lu)\r\n", counter);
                HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
            #endif
        }
    }

    if (trace_count > 0)
    {
        tracer_send_events();
    }

    #if TRACER_DEBUG
        // Generate test events periodically to ensure we have data to send
        if (counter % 300 == 0)
        { // Every 3 seconds
            uint32_t test_task_id = 0xABCD0000 + (counter & 0xFFFF);

            // Generate a simple task in/out sequence
            tracer_log(TRACE_EVENT_TI, test_task_id, NULL);
            tracer_log(TRACE_EVENT_TO, test_task_id, NULL);

            char debug[60];
            snprintf(debug, sizeof(debug), "Generated test events for task 0x%08lX\r\n", test_task_id);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        }
    #endif

    // Send events every 10 iterations (100ms) if available
    if (trace_count > 0)
    {
        #if TRACER_DEBUG
            char debug[60];
            snprintf(debug, sizeof(debug), "Sending %lu events from buffer\r\n", trace_count);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        #endif

        tracer_send_events();
    }

    #if TRACER_DEBUG
        // Status message every 1000 iterations (10 seconds)
        if (counter % 1000 == 0)
        {
            char debug[100];
            snprintf(debug, sizeof(debug),
                    "Tracer: %lu events logged, %lu in buffer, %lu sent\r\n",
                    trace_hook_calls, trace_count, sent_events);
            HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
        }
    #endif
}

/**
 * @brief Debug output for FreeRTOS hooks to confirm they're being called
 * Called by FreeRTOS when a task is created
 */
__STATIC_INLINE void tracer_TASK_CREATE(uint32_t uxTaskNumber, char *taskName)
{
    tracer_init();

    #if TRACER_DEBUG
        // Debug message to verify hook is called
        char debug[100];
        snprintf(debug, sizeof(debug), "TC hook: Task %lu (%s) created\r\n",
                uxTaskNumber, taskName ? taskName : "unnamed");
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    tracer_log(TRACE_EVENT_TC, uxTaskNumber, taskName);
    
    // Force sending events now - don't wait for the tracer task
    tracer_send_events();
}

__STATIC_INLINE void tracer_TASK_SWITCHED_IN(uint32_t uxTaskNumber)
{
    #if TRACER_DEBUG
        // Debug message to verify hook is called
        char debug[100];
        snprintf(debug, sizeof(debug), "TI hook: Task %lu switched in\r\n", uxTaskNumber);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    tracer_log(TRACE_EVENT_TI, uxTaskNumber, NULL);
    
    // Only force send if buffer is nearly full
    if (trace_count > 3 || trace_count > (TRACE_BUFFER_SIZE - 5)) {
        tracer_send_events();
    }
}

__STATIC_INLINE void tracer_TASK_SWITCHED_OUT(uint32_t uxTaskNumber)
{
    #if TRACER_DEBUG
        // Debug message to verify hook is called
        char debug[100];
        snprintf(debug, sizeof(debug), "TO hook: Task %lu switched out\r\n", uxTaskNumber);
        HAL_UART_Transmit(&huart2, (uint8_t *)debug, strlen(debug), HAL_MAX_DELAY);
    #endif

    tracer_log(TRACE_EVENT_TO, uxTaskNumber, NULL);
    
    // Only force send if buffer is nearly full
    if (trace_count > 3 || trace_count > (TRACE_BUFFER_SIZE - 5)) {
        tracer_send_events();
    }
}
#endif /* INC_TRACER_H_ */