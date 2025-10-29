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
SERIAL_PORT = 'COM5'  # Change this to your Arduino COM port
BAUD_RATE = 115200

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

# HTML Template (save as templates/index.html or embed below)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ESP32 Timer Monitor</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.3);
            overflow: hidden;
        }
        
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        
        h1 {
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        
        .status {
            display: inline-block;
            padding: 8px 20px;
            background: rgba(255,255,255,0.2);
            border-radius: 20px;
            font-size: 0.9em;
        }
        
        .status.connected {
            background: #4CAF50;
        }
        
        .controls {
            padding: 20px 30px;
            background: #f8f9fa;
            border-bottom: 2px solid #e9ecef;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .stats {
            display: flex;
            gap: 30px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-label {
            font-size: 0.85em;
            color: #6c757d;
            margin-bottom: 5px;
        }
        
        .stat-value {
            font-size: 1.8em;
            font-weight: bold;
            color: #667eea;
        }
        
        button {
            padding: 12px 30px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            transition: all 0.3s;
        }
        
        button:hover {
            background: #c82333;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(220,53,69,0.3);
        }
        
        .table-container {
            padding: 30px;
            max-height: 600px;
            overflow-y: auto;
        }
        
        table {
            width: 100%;
            border-collapse: collapse;
        }
        
        thead {
            position: sticky;
            top: 0;
            background: white;
            z-index: 10;
        }
        
        th {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            text-transform: uppercase;
            font-size: 0.85em;
            letter-spacing: 0.5px;
        }
        
        td {
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
        }
        
        tr:hover {
            background: #f8f9fa;
        }
        
        .id-badge {
            display: inline-block;
            padding: 5px 15px;
            background: #667eea;
            color: white;
            border-radius: 20px;
            font-weight: bold;
        }
        
        .time-value {
            font-family: 'Courier New', monospace;
            font-weight: bold;
            color: #28a745;
            font-size: 1.1em;
        }
        
        .no-data {
            text-align: center;
            padding: 50px;
            color: #6c757d;
            font-size: 1.2em;
        }
        
        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-10px);
            }
            to {
                opacity: 1;
                transform: translateY(0);
            }
        }
        
        .new-row {
            animation: slideIn 0.3s ease;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🎯 ESP32 Timer Monitor</h1>
            <div class="status connected" id="status">● Connected</div>
        </div>
        
        <div class="controls">
            <div class="stats">
                <div class="stat-item">
                    <div class="stat-label">Total Records</div>
                    <div class="stat-value" id="totalRecords">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Last ID</div>
                    <div class="stat-value" id="lastId">-</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Last Time</div>
                    <div class="stat-value" id="lastTime">-</div>
                </div>
            </div>
            <button onclick="clearData()">Clear All Data</button>
        </div>
        
        <div class="table-container">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>ID</th>
                        <th>Time (seconds)</th>
                        <th>Timestamp</th>
                    </tr>
                </thead>
                <tbody id="dataTable">
                    <tr>
                        <td colspan="4" class="no-data">Waiting for data...</td>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const socket = io();
        let recordCount = 0;
        
        socket.on('connect', function() {
            console.log('Connected to server');
            document.getElementById('status').textContent = '● Connected';
            document.getElementById('status').classList.add('connected');
        });
        
        socket.on('disconnect', function() {
            console.log('Disconnected from server');
            document.getElementById('status').textContent = '● Disconnected';
            document.getElementById('status').classList.remove('connected');
        });
        
        socket.on('new_data', function(data) {
            console.log('New data:', data);
            addRow(data);
        });
        
        function addRow(data) {
            const tbody = document.getElementById('dataTable');
            
            // Remove "no data" message if present
            if (tbody.querySelector('.no-data')) {
                tbody.innerHTML = '';
            }
            
            recordCount++;
            
            const row = tbody.insertRow(0);
            row.className = 'new-row';
            
            row.innerHTML = `
                <td>${recordCount}</td>
                <td><span class="id-badge">${data.id}</span></td>
                <td><span class="time-value">${data.time.toFixed(3)}</span></td>
                <td>${data.timestamp}</td>
            `;
            
            // Update stats
            document.getElementById('totalRecords').textContent = recordCount;
            document.getElementById('lastId').textContent = data.id;
            document.getElementById('lastTime').textContent = data.time.toFixed(3) + 's';
        }
        
        function clearData() {
            if (confirm('Are you sure you want to clear all data?')) {
                fetch('/api/clear')
                    .then(response => response.json())
                    .then(data => {
                        document.getElementById('dataTable').innerHTML = 
                            '<tr><td colspan="4" class="no-data">Waiting for data...</td></tr>';
                        recordCount = 0;
                        document.getElementById('totalRecords').textContent = '0';
                        document.getElementById('lastId').textContent = '-';
                        document.getElementById('lastTime').textContent = '-';
                    });
            }
        }
        
        // Load existing data on page load
        fetch('/api/data')
            .then(response => response.json())
            .then(data => {
                data.forEach(record => addRow(record));
            });
    </script>
</body>
</html>
'''

if __name__ == '__main__':
    # Create templates directory and save HTML
    import os
    os.makedirs('templates', exist_ok=True)
    with open('templates/index.html', 'w', encoding='utf-8') as f:
        f.write(HTML_TEMPLATE)
    
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
        print("1. Arduino is connected")
        print("2. Correct COM port is specified")
        print("3. No other program is using the serial port")