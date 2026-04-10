import sys, os, subprocess, re, argparse

# --- CULORI PENTRU TERMINAL ---
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RESET = '\033[0m'

pipe_read_fds = set()
pipe_write_fds = set()

def compile_code(source_file):
    print(f"{CYAN}[*] Compilare {source_file}...{RESET}")
    binary = "./test_exec"
    result = subprocess.run(["gcc", source_file, "-o", binary], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"{RED}[EROARE FATALĂ] Compilarea a eșuat!{RESET}\n{result.stderr}")
        sys.exit(1)
    return binary

def run_strace(binary):
    print(f"{CYAN}[*] Rulare sub strace (interceptare syscalls, semnale, pipes)...{RESET}")
    strace_out = "strace_output.txt"
    # Folosim trace=all pentru a vedea nanosleep/alarm si semnalele trimise/primite clar
    cmd = ["strace", "-f", "-e", "trace=all", "-o", strace_out, binary]
    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return strace_out

def parse_strace(strace_out):
    processes = {}
    unfinished = {}
    main_pid = None
    global pipe_read_fds, pipe_write_fds
    pipe_read_fds.clear()
    pipe_write_fds.clear()

    with open(strace_out, 'r') as f:
        for line in f:
            line = line.strip()
            if not line: continue
            
            # Match PID principal
            pid_match = re.match(r'^(\d+)\s+(.*)', line)
            if not pid_match: continue
            pid = int(pid_match.group(1))
            rest = pid_match.group(2)
            
            if main_pid is None: main_pid = pid
            if pid not in processes:
                processes[pid] = {'calls': [], 'children': []}

            # Reconstrucție linii întrerupte
            if "<unfinished" in rest:
                unfinished[pid] = rest.replace("<unfinished ...>", "").strip()
                continue
            if "resumed>" in rest:
                prev = unfinished.pop(pid, "")
                res_part = re.search(r'resumed>\s*(.*)', rest)
                rest = prev + (res_part.group(1) if res_part else "")

            # Detecție livrare semnal (ex: --- SIGALRM {si_signo=SIGALRM...} ---)
            if rest.startswith("--- SIG"):
                sig_match = re.search(r'---\s+(SIG[A-Z0-9_]+)', rest)
                if sig_match:
                    processes[pid]['calls'].append({
                        'type': 'SIGNAL_RECV',
                        'signal': sig_match.group(1),
                        'raw': rest
                    })
                continue

            # Detecție apel sistem normal
            sys_match = re.match(r'^([a-zA-Z0-9_]+)\((.*)', rest)
            if sys_match:
                syscall = sys_match.group(1)
                args_and_res = sys_match.group(2)
                processes[pid]['calls'].append({
                    'type': 'SYSCALL',
                    'syscall': syscall,
                    'raw': args_and_res
                })
                
                # Identificare copii creati
                if syscall in ('clone', 'fork', 'vfork'):
                    res_match = re.search(r'=\s+(\d+)', args_and_res)
                    if res_match:
                        child_pid = int(res_match.group(1))
                        processes[pid]['children'].append(child_pid)
                
                # Identificare FD-uri de pipe
                elif syscall in ('pipe', 'pipe2'):
                    res_match = re.search(r'=\s+0', args_and_res)
                    if res_match:
                        fds = re.findall(r'\d+', args_and_res.split(')')[0])
                        if len(fds) >= 2:
                            pipe_read_fds.add(fds[0])
                            pipe_write_fds.add(fds[1])

    return processes, main_pid

def has_written_pid(processes, pid, expected_val, target='stdout', after_signal=None):
    """
    Verifică dacă 'pid' a scris 'expected_val' către target ('stdout' sau 'pipe').
    Dacă 'after_signal' este specificat, ia în calcul DOAR write-urile făcute după primirea acelui semnal.
    """
    if pid not in processes: return False
    
    found_signal = False if after_signal else True
    
    for call in processes[pid]['calls']:
        if call['type'] == 'SIGNAL_RECV' and after_signal in call['signal']:
            found_signal = True
            
        if found_signal and call['type'] == 'SYSCALL' and call['syscall'] in ('write', 'writev'):
            fd_match = re.match(r'^(\d+),', call['raw'])
            if not fd_match: continue
            fd = fd_match.group(1)
            
            is_stdout = fd in ('1', '2')
            is_pipe = fd in pipe_write_fds
            
            if target == 'stdout' and not is_stdout: continue
            if target == 'pipe' and not is_pipe: continue
            
            if re.search(r'\b' + str(expected_val) + r'\b', call['raw']):
                return True
    return False

def has_sent_signal(processes, sender_pid, target_pid, signal_name):
    """Verifică dacă 'sender_pid' a apelat kill(target_pid, signal_name)"""
    if sender_pid not in processes: return False
    for call in processes[sender_pid]['calls']:
        if call['type'] == 'SYSCALL' and call['syscall'] in ('kill', 'tgkill'):
            if str(target_pid) in call['raw'] and signal_name in call['raw']:
                return True
    return False

def has_read_from_pipe(processes, pid):
    """Verifică dacă 'pid' a făcut un apel read dintr-un FD asociat unui pipe de citire"""
    if pid not in processes: return False
    for call in processes[pid]['calls']:
        if call['type'] == 'SYSCALL' and call['syscall'] == 'read':
            fd_match = re.match(r'^(\d+),', call['raw'])
            if fd_match and fd_match.group(1) in pipe_read_fds:
                return True
    return False

# ================= EVALUATORI SPECIFICI PE NIVEL =================

def eval_level_0(processes, main_pid):
    errors = []
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    if not has_written_pid(processes, p2, main_pid, target='stdout'):
        errors.append(f"P2 (PID {p2}) NU a afisat PID-ul lui P1 (PID {main_pid}).")
    return errors

def eval_level_1(processes, main_pid):
    errors = []
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    if p2 not in processes or not processes[p2]['children']: return ["P2 nu a creat P3."]
    p3 = processes[p2]['children'][0]
    
    if not has_written_pid(processes, p3, main_pid, target='stdout'):
        errors.append(f"P3 (PID {p3}) NU a afisat PID-ul lui P1 (PID {main_pid}).")
    if not has_written_pid(processes, p3, p2, target='stdout'):
        errors.append(f"P3 (PID {p3}) NU a afisat PID-ul lui P2 (PID {p2}).")
    return errors

def eval_level_2(processes, main_pid):
    errors = []
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    # 1. Verificare semnal trimis
    if not has_sent_signal(processes, p2, main_pid, 'SIGALRM'):
        errors.append(f"P2 (PID {p2}) nu a trimis kill() cu SIGALRM catre P1.")
        
    # 2. Verificare print DUPA semnal
    if not has_written_pid(processes, main_pid, p2, target='stdout', after_signal='SIGALRM'):
        errors.append(f"P1 (PID {main_pid}) NU a afisat PID-ul lui P2 ({p2}) DUPĂ ce a primit SIGALRM.")
        errors.append(f"(Hint: Ai prins SIGALRM folosind signal/sigaction in P1? P1 trebuie sa existe destul timp ca sa il primeasca.)")
        
    return errors

def eval_level_3(processes, main_pid):
    errors = []
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    if p2 not in processes or not processes[p2]['children']: return ["P2 nu a creat P3."]
    p3 = processes[p2]['children'][0]
    
    # Acceptam SIGUSR1 sau SIGUSR2
    sent_sigusr = has_sent_signal(processes, p3, main_pid, 'SIGUSR1') or has_sent_signal(processes, p3, main_pid, 'SIGUSR2')
    if not sent_sigusr:
        errors.append(f"P3 (PID {p3}) nu a trimis SIGUSR1/SIGUSR2 catre P1.")
        
    if not has_written_pid(processes, main_pid, p3, target='stdout', after_signal='SIGUSR'):
        errors.append(f"P1 (PID {main_pid}) NU a afisat PID-ul lui P3 ({p3}) DUPĂ ce a primit SIGUSR.")
        
    return errors

def eval_level_4(processes, main_pid):
    errors = []
    if not pipe_read_fds: errors.append("Nu a fost detectat niciun apel la pipe().")
    
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    if not has_written_pid(processes, p2, main_pid, target='pipe'):
        errors.append(f"P2 (PID {p2}) NU a scris PID-ul lui P1 ({main_pid}) in pipe.")
        
    if not has_read_from_pipe(processes, main_pid):
        errors.append(f"P1 (PID {main_pid}) nu a citit din pipe.")
        
    if not has_written_pid(processes, main_pid, main_pid, target='stdout'):
        errors.append(f"P1 (PID {main_pid}) NU a afisat la stdout PID-ul sau dupa ce l-a citit.")
        
    return errors

def eval_level_5(processes, main_pid):
    errors = []
    if not pipe_read_fds: errors.append("Nu a fost detectat niciun apel la pipe().")
    
    if not processes[main_pid]['children']: return ["P1 nu a creat P2."]
    p2 = processes[main_pid]['children'][0]
    
    if p2 not in processes or not processes[p2]['children']: return ["P2 nu a creat P3."]
    p3 = processes[p2]['children'][0]
    
    if not has_written_pid(processes, p3, main_pid, target='pipe'):
        errors.append(f"P3 (PID {p3}) NU a scris PID-ul lui P1 ({main_pid}) in pipe.")
        
    if not has_read_from_pipe(processes, main_pid):
        errors.append(f"P1 (PID {main_pid}) nu a citit din pipe.")
        
    if not has_written_pid(processes, main_pid, main_pid, target='stdout'):
        errors.append(f"P1 (PID {main_pid}) NU a afisat la stdout PID-ul sau (care trebuia primit prin pipe).")
        
    return errors

def main():
    parser = argparse.ArgumentParser(description="Validator implementari IPC & Semnale via strace")
    parser.add_argument("-l", "--level", required=True, choices=["0", "1", "2", "3", "4", "5"], help="Nivelul problemei")
    parser.add_argument("source", help="Calea catre fisierul .c")
    args = parser.parse_args()

    binary = compile_code(args.source)
    strace_out = run_strace(binary)
    processes, main_pid = parse_strace(strace_out)

    print(f"\n{CYAN}[*] Evaluare Soluție - Nivelul {args.level}{RESET}")
    print(f"    PID Principal identificat: {main_pid}")

    # Apelam functia de test potrivita dinamici
    eval_func = globals()[f"eval_level_{args.level}"]
    errors = eval_func(processes, main_pid)

    # Afisare Rezultat
    if not errors:
        print(f"\n{GREEN}[+] IMPLEMENTARE CORECTĂ! Toate condițiile logice și temporale au fost îndeplinite.{RESET}")
    else:
        print(f"\n{RED}[-] IMPLEMENTARE GREȘITĂ. S-au identificat următoarele probleme:{RESET}")
        for err in errors:
            print(f"    - {err}")
            
    # Cleanup
    if os.path.exists("test_exec"): os.remove("test_exec")
    if os.path.exists("strace_output.txt"): os.remove("strace_output.txt")

if __name__ == "__main__":
    main()
