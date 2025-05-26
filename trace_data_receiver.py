#!/usr/bin/env python3
"""
FreeRTOS Tracer - Binary Data Packet Receiver
Receives binary trace packets over UART and converts them to a readable log format.

Format example:
    0 CC 32000000
    1233456 TC 1 defaultTask
    1234455 TC 2 taskA
    1234557 TC 3 taskB
    1234568 TI 1
    1234570 TI 2
    1236435 TO 1
    1268696 TI 3
    1301235 TI 1
    1325433 TO 1
    1335674 TO 2
"""

import serial
import struct
import time
import binascii
import argparse
import os
from datetime import datetime

# Constants
TRACE_MAGIC = b'RENO'
EVENT_SIZE = 9  # Size of one event record: timestamp(4) + type(1) + task_id(4)

# Event types
EVENT_CC = 0  # Clock Calibration
EVENT_TC = 1  # Task Create
EVENT_TI = 2  # Task In
EVENT_TO = 3  # Task Out

# Maps for system task names
task_names = {
    1: "defaultTask",
    5: "IDLE",
    6: "Tmr Svc"
}

event_type_names = ["CC", "TC", "TI", "TO"]

def format_timestamp(timestamp, width=7):
    """Format timestamp with consistent width for clean log alignment"""
    return f"{timestamp:{width}}"

def process_events_packet(data, length, output_file=None, verbose=False):
    """Process events packet and save to output file"""
    global task_names
    
    events_count = length // EVENT_SIZE
    
    # Verify the data length is valid
    if length % EVENT_SIZE != 0:
        print(f"  Warning: Data length {length} is not a multiple of event size {EVENT_SIZE}")
        # Truncate to the nearest multiple
        length = (length // EVENT_SIZE) * EVENT_SIZE
        events_count = length // EVENT_SIZE
    
    if verbose:
        print(f"  Contains {events_count} events:")
        print(f"  Raw data: {binascii.hexlify(data[:length]).decode()}")
    
    for i in range(events_count):
        offset = i * EVENT_SIZE
        
        if offset + EVENT_SIZE > len(data):
            print(f"  Warning: Not enough data for event {i}")
            break
            
        try:
            # Unpack event: timestamp(4), type(1), task_id(4)
            timestamp, event_type, task_id = struct.unpack('<IBL', data[offset:offset+EVENT_SIZE])
            
            if event_type < len(event_type_names):
                event_name = event_type_names[event_type]
            else:
                event_name = f"UNK{event_type}"
            
            # Output to console in verbose mode
            if verbose:
                if event_type == EVENT_CC:  # Clock Calibration
                    print(f"    Event {i}: time={timestamp}, type=CC, CPU freq={task_id}")
                elif event_type == EVENT_TC:  # Task Create
                    task_name = task_names.get(task_id, f"Task_{task_id}")
                    print(f"    Event {i}: time={timestamp}, type=TC, task_id={task_id}, name={task_name}")
                else:  # TI, TO
                    task_name = task_names.get(task_id, f"Task_{task_id}")
                    print(f"    Event {i}: time={timestamp}, type={event_name}, task_id={task_id}, name={task_name}")
            
            if output_file:
                if event_type == EVENT_CC:
                    output_file.write(f"{format_timestamp(timestamp)} CC {task_id}\n")
                    output_file.flush()
                elif event_type == EVENT_TC:
                    # Store task name for future reference
                    if task_id not in task_names:
                        task_names[task_id] = f"Task_{task_id}"
                    task_name = task_names[task_id]
                    output_file.write(f"{format_timestamp(timestamp)} TC {task_id} {task_name}\n")
                    output_file.flush()
                elif event_type == EVENT_TI:
                    output_file.write(f"{format_timestamp(timestamp)} TI {task_id}\n")
                    output_file.flush()
                elif event_type == EVENT_TO:
                    output_file.write(f"{format_timestamp(timestamp)} TO {task_id}\n")
                    output_file.flush()
                else:
                    output_file.write(f"{format_timestamp(timestamp)} UNK{event_type} {task_id}\n")
                    output_file.flush()
                    
        except Exception as e:
            print(f"    Error parsing event {i}: {e}")
            if verbose:
                print(f"    Raw data: {binascii.hexlify(data[offset:offset+EVENT_SIZE])}")

def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='FreeRTOS Binary Trace Receiver')
    parser.add_argument('--port', type=str, required=True, help='Serial port')
    parser.add_argument('--baud', type=int, default=921600, help='Baud rate')
    parser.add_argument('--output', type=str, help='Output log file')
    parser.add_argument('--cpu-freq', type=int, default=32000000, help='CPU frequency in Hz')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--task-names', type=str, help='CSV file with task_id,name pairs')
    args = parser.parse_args()
    
    if args.task_names:
        try:
            with open(args.task_names, 'r') as f:
                for line in f:
                    if line.strip() and not line.startswith('#'):
                        parts = line.strip().split(',')
                        if len(parts) >= 2:
                            task_id = int(parts[0])
                            task_name = parts[1]
                            task_names[task_id] = task_name
            print(f"Loaded {len(task_names)} task names from {args.task_names}")
        except Exception as e:
            print(f"Error loading task names: {e}")
    
    output_file = None
    if args.output:
        try:
            output_dir = os.path.dirname(args.output)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
                
            output_file = open(args.output, 'w')
            # Write a CPU calibration event
            output_file.write(f"{format_timestamp(0)} CC {args.cpu_freq}\n")
            print(f"Log file opened: {args.output}")
        except Exception as e:
            print(f"Error opening output file: {e}")
            return
    
    # Open serial port
    print(f"Opening {args.port} at {args.baud} baud...")
    try:
        ser = serial.Serial(args.port, args.baud, timeout=0.1)
    except Exception as e:
        print(f"Error opening serial port: {e}")
        if output_file:
            output_file.close()
        return
    
    # Main processing loop
    buffer = bytearray()
    packet_count = 0
    event_count = 0
    last_byte_time = time.time()
    stats_time = time.time()
    
    print("Waiting for binary packets...")
    try:
        while True:
            data = ser.read(ser.in_waiting or 1)
            
            if data:
                last_byte_time = time.time()
                buffer.extend(data)
                
                while True:
                    # Find magic header
                    magic_pos = buffer.find(TRACE_MAGIC)
                    if magic_pos < 0:
                        if len(buffer) > 100:
                            # Keep only last bytes that might be part of a magic header
                            # In case the data is fragmented during transmission
                            buffer = buffer[-4:]
                        break
                    
                    # Discard any data before the magic header
                    if magic_pos > 0:
                        if args.verbose:
                            print(f"Discarding {magic_pos} bytes before magic header")
                        buffer = buffer[magic_pos:]
                        magic_pos = 0
                    
                    # Check if we have a complete header
                    if len(buffer) < 8:
                        break
                        
                    try:
                        # Parse header: magic(4) + version(1) + type(1) + length(2)
                        version = buffer[4]
                        packet_type = buffer[5]
                        data_length = buffer[6] | (buffer[7] << 8)  # Little-endian
                        
                        # For heartbeat packets, data_length is the counter value
                        is_heartbeat = (packet_type == 0x42)
                        if is_heartbeat:
                            data_length = 0
                        
                        # Sanity check for data length
                        if not is_heartbeat and (data_length > 1024 or data_length % EVENT_SIZE != 0):
                            print(f"  Warning: Suspicious data length {data_length}, skipping 4 bytes")
                            buffer = buffer[4:]
                            continue
                        
                        # Wait for complete packet
                        if len(buffer) < 8 + data_length:
                            break
                            
                        packet_data = buffer[8:8+data_length]
                        packet_count += 1
                        
                        if args.verbose:
                            print(f"\nPacket #{packet_count}: type=0x{packet_type:02X}, len={data_length}")
                        
                        if is_heartbeat:
                            counter_value = buffer[6] | (buffer[7] << 8)
                            if args.verbose:
                                print(f"  Heartbeat packet, counter={counter_value}")
                        elif packet_type == 0x02:
                            num_events = data_length // EVENT_SIZE
                            event_count += num_events
                            
                            process_events_packet(packet_data, data_length, output_file, args.verbose)
                        else:
                            if args.verbose:
                                print(f"  Unknown packet type: 0x{packet_type:02X}")
                                print(f"  Data: {binascii.hexlify(packet_data)}")
                        
                        # Remove processed packet from buffer
                        buffer = buffer[8 + data_length:]
                        
                    except Exception as e:
                        print(f"Error processing packet: {e}")
                        # Skip this magic header and try again
                        buffer = buffer[4:]
            else:
                if time.time() - last_byte_time > 5.0:
                    print(f"No data received for 5 seconds. Stats: {packet_count} packets, {event_count} events")
                    last_byte_time = time.time()
            
            # Print periodic stats
            if time.time() - stats_time > 10.0:
                print(f"Stats: {packet_count} packets, {event_count} events processed")
                stats_time = time.time()
            
            # Short delay
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\nStopped by user")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print(f"Final stats: {packet_count} packets, {event_count} events processed")
        ser.close()
        if output_file:
            output_file.close()
            print(f"Log saved to {args.output}")

if __name__ == "__main__":
    main()