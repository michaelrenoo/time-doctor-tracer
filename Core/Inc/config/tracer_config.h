/*
 * tracer_config.h
 *
 *  Created on: May 27, 2025
 *      Author: Michael Reno
 */

#ifndef INC_CONFIG_TRACER_CONFIG_H_
#define INC_CONFIG_TRACER_CONFIG_H_

// Debug settings
#define TRACER_DEBUG 0          // Set to 0 to disable verbose tracer debug messages
#define MAIN_DEBUG 1            // Set to 0 to disable debug messages in main.c

// Tracer buffer configuration
#define TRACE_BUFFER_SIZE 1024  // Rolling buffer size for trace records
#define MAX_EVENTS_PER_BATCH 8  // Maximum events to send in one transmission

// Protocol constants - Note: DO NOT change these values as they're expected by the trace receiver
#define TRACE_MAGIC "RENO"      // Magic header for log file
#define TRACE_VERSION 1         // Protocol version
#define HEARTBEAT_PACKET_TYPE 0x42 // Heartbeat marker
#define EVENTS_PACKET_TYPE 0x02    // Events packet type

// Timing constants
#define HEARTBEAT_INTERVAL 50   // Send heartbeat every N iterations (50 = 500ms at 10ms task delay)
#define CLOCK_CALIB_INTERVAL 500 // Resend clock calibration every N iterations
#define TRACER_TASK_DELAY 10    // Delay between tracer task cycles (ms)

// Event queue thresholds
#define FORCE_SEND_THRESHOLD 3  // Force send if buffer has this many events
#define BUFFER_ALMOST_FULL (TRACE_BUFFER_SIZE - 5) // Consider buffer almost full at this point

#endif /* INC_CONFIG_TRACER_CONFIG_H_ */