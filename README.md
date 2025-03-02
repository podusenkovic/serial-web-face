# Serial Port Web Interface

A web-based interface for interacting with serial ports (COM ports) via a browser. Allows sending commands, reading real-time data, and saving logs.

## Key Features
- 📡 Connect to COM ports with customizable parameters (baud rate, data bits, etc.)
- 📝 Manage a list of frequently used commands
- 📊 Real-time data visualization from serial port
- 💾 Save logs to files
- 🌐 Access via web interface from any network device

## Requirements
- Python 3.7+
- Access to a serial port (for physical devices)

## Installation
1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate.bat  # Windows
```

2. Install dependencies:
```bash
pip install flask flask-socketio pyserial
```

3. Copy project files to your working directory:
```
main.py
templates/
static/
```

## Running the Application
```bash
python main.py
```

The application will be available at: `http://localhost:5000`

## Usage
1. Select a port from the available list
2. Configure connection parameters (default: 9600 8N1)
3. Click "Open" to connect
4. Use:
   - Quick command buttons
   - Manual command input
   - Save logs via "Save Log" button

## File Structure
- `commands.json` - stored custom commands
- `config.json` - last used port configuration
- `logs/` - directory for saved logs

## Notes
- On Linux, you may need port access permissions: `sudo usermod -aG dialout $USER`
- For virtual ports, consider using `socat` or `com0com`
- In debug mode (default), the app auto-reloads when code changes are detected
