import sys, re

COLORS = ['\033[96m', '\033[92m', '\033[93m', '\033[95m', '\033[94m', '\033[91m']
RESET_COLOR = '\033[0m'

pid_colors = {}
pid_depth = {}
color_idx = 0

def log_event(pid, tag, message):
    global color_idx
    if pid not in pid_colors:
        pid_colors[pid] = COLORS[color_idx % len(COLORS)]
        color_idx += 1
    color = pid_colors[pid]
    depth = pid_depth.get(pid, 0)
    indent = "  " * (depth - 1) + " └─ " if depth > 0 else ""
    print(f"{color}{indent}[PID {pid}] [{tag:<5}] {message}{RESET_COLOR}", flush=True)

def main():
    print("--- Parser activ (Aștept date...) ---", flush=True)
    
    for line in sys.stdin:
        line = line.strip()
        if not line: continue

        # 1. Extragere PID (Căutăm orice număr după "[pid " sau la începutul liniei)
        pid = "MAIN"
        pid_search = re.search(r'\[pid\s+(\d+)\]', line)
        if pid_search:
            pid = pid_search.group(1)
        else:
            # Dacă nu are [pid ], s-ar putea să fie prima cifră din linie (dacă strace e rulat cu -f)
            start_pid = re.match(r'^(\d+)\s+', line)
            if start_pid: pid = start_pid.group(1)

        # 2. Detectare WRITE (Căutăm write(fd, "text"...)
        if "write(" in line:
            # Prinde textul dintre ghilimele, inclusiv caractere speciale ca \n
            content = re.search(r'write\(\d+,\s*"(.*?)"', line)
            if content:
                log_event(pid, "WRITE", f"Text: {content.group(1)}")
            else:
                # Dacă e un write mare sau cu buffer binar
                log_event(pid, "WRITE", "Buffer de date (detectat)")
            continue

        # 3. Detectare READ
        if "read(" in line:
            content = re.search(r'read\(\d+,\s*"(.*?)"', line)
            msg = content.group(1) if content else "..."
            log_event(pid, "READ", f"Data: {msg[:50]}")
            continue

        # 4. Detectare FORK/CLONE (Căutăm rezultatul de după '=')
        if any(x in line for x in ["clone(", "fork(", "vfork("]) and "=" in line:
            res_match = re.search(r'=\s+(\d+)', line)
            if res_match:
                child_pid = res_match.group(1)
                pid_depth[child_pid] = pid_depth.get(pid, 0) + 1
                log_event(pid, "FORK", f"Părintele a creat copilul: {child_pid}")
            continue

        # 5. Detectare EXIT
        if "exited with" in line or "+++ exited" in line:
            log_event(pid, "EXIT", "Proces finalizat.")

if __name__ == "__main__":
    main()
