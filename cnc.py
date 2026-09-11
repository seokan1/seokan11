import socket
import threading
import json
import datetime
import paramiko
from funnel.funnel import send_phone_request, send_discord_webhook

with open("logs/logs.json", "r") as f:
    user_logs = json.load(f)
discord_webhook_url = user_logs[0]["discord_webhook"]

with open("assets/branding/clear.tfx", "r", encoding="utf-8") as f:
    CLEAR_BANNER = f.read()
with open("assets/branding/help.tfx", "r", encoding="utf-8") as f:
    HELP_TEXT = f.read()
with open("assets/branding/prompt.tfx", "r", encoding="utf-8") as f:
    PROMPT_TEMPLATE = f.read()
with open("assets/branding/methods.tfx", "r", encoding="utf-8") as f:
    METHODS_TEXT = f.read()

HOST_KEY = paramiko.RSAKey.generate(2048)

with open("users/users.json", "r") as f:
    USERS = json.load(f)

class SSHServer(paramiko.ServerInterface):
    def __init__(self):
        self.authed_user = None

    def check_auth_password(self, username, password):
        for user in USERS:
            if user["username"] == username and user["password"] == password:
                self.authed_user = user
                return paramiko.AUTH_SUCCESSFUL
        return paramiko.AUTH_FAILED

    def get_allowed_auths(self, username):
        return "password"

    def check_channel_request(self, kind, chanid):
        if kind == "session":
            return paramiko.OPEN_SUCCEEDED
        return paramiko.OPEN_FAILED_ADMINISTRATIVELY_PROHIBITED

    def check_channel_shell_request(self, channel):
        return True

    def check_channel_pty_request(self, channel, term, width, height, pixelwidth, pixelheight, modes):
        return True
    
def safe_send(chan, data):
    try:
        if chan.closed or chan.exit_status_ready():
            return False
        chan.send(data)
        return True
    except:
        return False

def make_title(user):
    now = datetime.datetime.now().strftime("%H:%M")
    return f"\033]0;{now} | Logged as {user['username']} | Max {user['max_send']} | Time {user['time_limit']}\007"

def handle_connection(client, addr):
    transport = paramiko.Transport(client)
    transport.add_server_key(HOST_KEY)
    server = SSHServer()

    try:
        transport.start_server(server=server)
    except:
        return

    chan = transport.accept(10)
    if chan is None:
        return

    user = server.authed_user
    safe_send(chan, make_title(user))
    safe_send(chan, CLEAR_BANNER + "\n")

    username = user["username"]
    prompt = PROMPT_TEMPLATE.replace("<user>", username).replace("user", username)
    safe_send(chan, prompt)

    buffer = ""

    while True:
        try:
            data = chan.recv(1024)
        except:
            break
        if not data:
            break

        txt = data.decode("utf-8", errors="ignore")

        for ch in txt:

            if ch in ["\r", "\n"]:
                cmd = buffer.strip()
                buffer = ""
                safe_send(chan, "\r\n")

                if cmd == "":
                    pass

                elif cmd == "help":
                    for line in HELP_TEXT.split("\n"):
                        safe_send(chan, "\r" + line + "\r\n")

                elif cmd == "methods":
                    for line in METHODS_TEXT.split("\n"):
                        safe_send(chan, "\r" + line + "\r\n")

                elif cmd == "clear":
                    safe_send(chan, "\033[2J\033[H")
                    for line in CLEAR_BANNER.split("\n"):
                        safe_send(chan, "\r" + line + "\r\n")

                elif cmd == "exit":
                    safe_send(chan, "Bye.\n")
                    chan.close()
                    return

                elif cmd.startswith("boom"):
                    parts = cmd.split()

                    if len(parts) < 2:
                        safe_send(chan, "Usage: boom <phone_number> <count>\r\n")
                    else:
                        phone_number = parts[1]
                        count = 1

                        if len(parts) >= 3:
                            try:
                                count = int(parts[2])
                            except:
                                count = 1

                        safe_send(chan, f"[+] {phone_number} with {count} attacking..\r\n")

                        for _ in range(count):
                            success, msg = send_phone_request(phone_number)  # ← 여기 고침
                            safe_send(chan, msg + "\r\n")


                else:
                    safe_send(chan, f"Unknown command: {cmd}\r\n")

                safe_send(chan, prompt)
                continue

            elif ch == "\x7f":
                if len(buffer) > 0:
                    buffer = buffer[:-1]
                    safe_send(chan, "\b \b")
                continue
            else:
                buffer += ch
                safe_send(chan, ch)

    try:
        chan.close()
        transport.close()
    except:
        pass


def start_ssh_server(host="0.0.0.0", port=2222):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind((host, port))
    sock.listen(200)
    print(f"[SSH] Blaze SSH Server Running on {host}:{port}")

    while True:
        client, addr = sock.accept()
        threading.Thread(target=handle_connection, args=(client, addr), daemon=True).start()

if __name__ == "__main__":
    start_ssh_server()
