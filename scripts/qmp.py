#!/usr/bin/env python3
"""Send a QEMU monitor command for local ISO boot testing."""
import json
import socket
import sys
import time


def request(stream, command, arguments, request_id):
    payload = {"execute": command, "arguments": arguments, "id": request_id}
    stream.write((json.dumps(payload) + "\n").encode())
    stream.flush()
    while True:
        line = stream.readline()
        if not line:
            raise RuntimeError("QEMU closed the monitor connection")
        reply = json.loads(line)
        if reply.get("id") == request_id:
            if "error" in reply:
                raise RuntimeError(reply["error"])
            return reply["return"]


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit("Usage: qmp.py SOCKET COMMAND [ARGUMENTS_JSON]")
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
        connection.settimeout(10)
        connection.connect(sys.argv[1])
        with connection.makefile("rwb") as stream:
            greeting = json.loads(stream.readline())
            if "QMP" not in greeting:
                raise RuntimeError("Unexpected monitor greeting")
            request(stream, "qmp_capabilities", {}, 1)
            args = json.loads(sys.argv[3]) if len(sys.argv) == 4 else {}
            if sys.argv[2] == "type-text":
                keys = {" ": "spc", "\n": "ret", "-": "minus", "_": "shift-minus",
                        "/": "slash", ".": "dot", ":": "shift-semicolon",
                        ";": "semicolon", "=": "equal", "'": "apostrophe",
                        '"': "shift-apostrophe", ">": "shift-dot", "|": "shift-backslash"}
                for number, char in enumerate(args["text"], 2):
                    key = keys.get(char, "shift-" + char.lower() if char.isupper() else char)
                    request(stream, "human-monitor-command", {"command-line": f"sendkey {key} 10"}, number)
                    time.sleep(0.06)
            else:
                print(json.dumps(request(stream, sys.argv[2], args, 2)))
