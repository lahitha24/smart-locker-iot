
from flask import Flask, jsonify, send_from_directory
import serial
import threading
import time

app = Flask(__name__)

PORT = "COM6"
BAUD_RATE = 9600

state = {
    "locker": "LOCKED",
    "security": "SAFE",
    "otp": None,
    "events": []
}

lock = threading.RLock()


def add_event(message):
    with lock:
        state["events"].insert(0, {
            "message": message,
            "time": time.strftime("%d-%m-%Y %H:%M:%S")
        })
        state["events"] = state["events"][:30]


def read_arduino():
    while True:
        try:
            print(f"Connecting to Arduino on {PORT}...")

            arduino = serial.Serial(
                PORT,
                BAUD_RATE,
                timeout=1
            )

            time.sleep(2)
            print("Arduino connected successfully!")

            while True:
                line = arduino.readline().decode(
                    "utf-8", errors="ignore"
                ).strip()

                if not line:
                    continue

                print("Arduino:", line)

                with lock:
                    if line.startswith("OTP:"):
                        otp = line.split(":", 1)[1].strip()
                        if len(otp) == 4 and otp.isdigit():
                            state["otp"] = otp
                            add_event("Actual OTP received from Arduino.")

                    elif line == "STATUS:UNLOCKED":
                        state["locker"] = "UNLOCKED"
                        state["otp"] = None
                        add_event("Locker unlocked through hardware keypad.")

                    elif line == "STATUS:LOCKED":
                        state["locker"] = "LOCKED"
                        state["security"] = "SAFE"
                        state["otp"] = None
                        add_event("Locker locked through hardware keypad.")

                    elif line == "ALERT:TAMPER":
                        state["security"] = "ALERT"
                        state["otp"] = None
                        add_event("Tamper alert received from Arduino.")

        except serial.SerialException as error:
            print("Serial connection error:", error)
            print("Retrying in 3 seconds...")
            time.sleep(3)

        except Exception as error:
            print("Error:", error)
            time.sleep(3)


@app.route("/")
def home():
    return send_from_directory(".", "index.html")


@app.route("/style.css")
def css():
    return send_from_directory(".", "style.css")


@app.route("/script.js")
def javascript():
    return send_from_directory(".", "script.js")


@app.route("/api/state")
def get_state():
    with lock:
        return jsonify(state)


if __name__ == "__main__":
    thread = threading.Thread(
        target=read_arduino,
        daemon=True
    )
    thread.start()

    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False
    )
