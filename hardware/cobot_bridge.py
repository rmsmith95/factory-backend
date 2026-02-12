#!/usr/bin/env python3
import socket
import json
from pymycobot.mycobot import MyCobot

# --- MyCobot setup ---
PORT = "/dev/ttyAMA0"
BAUD = 1000000
mc = MyCobot(PORT, BAUD)

# --- TCP server setup ---
HOST = "0.0.0.0"  # listen on all interfaces
PORT_TCP = 9000

def handle_connection(conn, addr):
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            try:
                cmd = json.loads(data.decode())
                command = cmd.get("command")
                resp = {"status": "error", "message": "Unknown Command"}
                if command == "set_angle":
                    jointIndex = cmd.get("jointIndex")
                    deltaValue = cmd.get("deltaValue")
                    angles = mc.get_angles()
                    angles[jointIndex] = angles[jointIndex] + deltaValue
                    speed = int(cmd.get("speed", 50))
                    if angles and len(angles) == 6:
                        print(f"Set angles: {angles}")
                        mc.send_angles(angles, speed)
                        resp = {"status": "ok", "angles": angles}
                
                elif command == "set_angles":
                    angles = mc.get_angles()
                    speed = int(cmd.get("speed", 50))
                    if angles and len(angles) == 6:
                        print(f"Set angles: {angles}")
                        mc.send_angles(angles, speed)
                        resp = {"status": "ok", "angles": angles}
                    else:
                        resp = {"status": "error", "message": "Must provide 6 angles"}

                elif command == "get_position":
                    angles = mc.get_angles()
                    print(f"angles:{angles}")
                    resp = {"status": "ok", "angles": angles}

                else:
                    resp = {"status": "error", "message": f"Unknown command '{command}'"}

                conn.sendall(json.dumps(resp).encode())

            except Exception as e:
                conn.sendall(json.dumps({"status":"error","message": str(e)}).encode())

    finally:
        conn.close()
        print(f"❌ Client disconnected: {addr}")

# --- Start TCP server ---
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind((HOST, PORT_TCP))
sock.listen(5)
print(f"🚀 Listening for commands on {HOST}:{PORT_TCP}")

while True:
    conn, addr = sock.accept()
    print(f"Client connected: {addr}")
    handle_connection(conn, addr)
