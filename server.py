from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO
import serial
import threading
import re
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Configuration
import argparse
parser = argparse.ArgumentParser(description='ESP32 Timer Monitor Server')
parser.add_argument('--serial', type=str, required=True, help='Serial port for Arduino (e.g., COM3 or /dev/ttyACM0)')
parser.add_argument('--baud', type=int, default=115200, help='Baud rate for serial communication')
SERIAL_PORT = args.serial  # Change this to your Arduino COM port
BAUD_RATE = args.baud

# Store recent data
data_records = []
MAX_RECORDS = 50

# Serial connection
ser = None
serial_thread = None
running = False

def parse_serial_line(line):
    """Parse the serial data format: ID: 42 | Time: 1.234 seconds"""
    pattern = r'ID:\s*(\d+)\s*\|\s*Time:\s*([\d.]+)\s*seconds'
    match = re.match(pattern, line)
    
    if match:
        id_num = int(match.group(1))
        time_val = float(match.group(2))
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        return {
            'id': id_num,
            'time': time_val,
            'timestamp': timestamp
        }
    return None

def read_serial():
    """Read data from serial port in a separate thread"""
    global running, ser
    
    while running:
        try:
            if ser and ser.in_waiting:
                line = ser.readline().decode('utf-8', errors='ignore').strip()
                print(f"Received: {line}")
                
                data = parse_serial_line(line)
                if data:
                    data_records.append(data)
                    if len(data_records) > MAX_RECORDS:
                        data_records.pop(0)
                    
                    # Send to all connected web clients
                    socketio.emit('new_data', data)
                    print(f"Parsed: ID={data['id']}, Time={data['time']}s")
                    
        except Exception as e:
            print(f"Error reading serial: {e}")

def connect_serial():
    """Connect to the serial port"""
    global ser, running, serial_thread
    
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT} at {BAUD_RATE} baud")
        
        running = True
        serial_thread = threading.Thread(target=read_serial, daemon=True)
        serial_thread.start()
        return True
    except Exception as e:
        print(f"Failed to connect to serial port: {e}")
        return False

@app.route('/')
def index():
    """Main web page"""
    return render_template('index.html')

@app.route('/api/data')
def get_data():
    """API endpoint to get all stored data"""
    return jsonify(data_records)

@app.route('/api/clear')
def clear_data():
    """API endpoint to clear all data"""
    data_records.clear()
    return jsonify({'status': 'cleared'})

@socketio.on('connect')
def handle_connect():
    """Handle new client connection"""
    print('Client connected')
    # Send existing data to newly connected client
    for record in data_records:
        socketio.emit('new_data', record)

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

if __name__ == '__main__':
    # Connect to serial port
    if connect_serial():
        print("\n" + "="*50)
        print("ESP32 Timer Monitor Server")
        print("="*50)
        print(f"Serial Port: {SERIAL_PORT}")
        print(f"Baud Rate: {BAUD_RATE}")
        print(f"Web Interface: http://localhost:5000")
        print("="*50 + "\n")
        
        # Start web server
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    else:
        print("\nFailed to start. Please check:")
        print("1. ESP32 is connected")
        print("2. Correct COM/ttyACM/cu.serialmodem port is specified")
        print("3. No other program is using the serial port")