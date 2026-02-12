<!-- 
G0 X50	Rapid move X to 50 mm (non-cutting)
G1 X50 F500	Linear move X at 500 mm/min
G90	Absolute positioning mode
G91	Relative positioning mode
G92 X0 Y0 Z0	Set current position as zero
G28	Move to machine home (if homing switches configured)
?	Request status report (TinyG returns JSON with positions)
$X	Unlock machine if it’s in alarm state 
-->

# 1️⃣ Create serial port (replace COM10 with your actual port)
$port = New-Object System.IO.Ports.SerialPort COM10,115200,None,8,one

# 2️⃣ Open the port
$port.Open()

# 3️⃣ Clear buffers
$port.DiscardInBuffer()
$port.DiscardOutBuffer()

# 4️⃣ Request status
$port.WriteLine("?")   # TinyG status request
Start-Sleep -Milliseconds 500

# 5️⃣ Read response
while ($port.BytesToRead -gt 0) {
    $line = $port.ReadLine()
    Write-Host $line
}

# 6️⃣ Close port when done
$port.Close()





import serial

port = "COM10"  # or COM3 on Windows
baud = 115200

with serial.Serial(port, baud, timeout=2) as ser:
    ser.write(b"\r\n")
    ser.flush()
    print("Sent wakeup newline")
    response = ser.read(100)
    print("Got:", response)
