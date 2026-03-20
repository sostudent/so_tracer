import os, sys, struct, time
from ptrace.debugger import PtraceDebugger
from ptrace.binding.func import (PTRACE_O_TRACESYSGOOD, PTRACE_O_TRACEFORK, 
                                 PTRACE_O_TRACECLONE, PTRACE_O_TRACEEXEC)
from ptrace.binding import ptrace_traceme

# Track status per PID: 0 = Enter, 1 = Exit
syscall_state = {}

def trace_program(executable_path, args):
    debugger = PtraceDebugger()
    pid_parent = os.fork()
    
    if pid_parent == 0:
        ptrace_traceme()
        os.execv(executable_path, [executable_path] + args)
        sys.exit(1)

    time.sleep(0.2)
    process = debugger.addProcess(pid_parent, is_attached=True)
    options = (PTRACE_O_TRACESYSGOOD | PTRACE_O_TRACEFORK | 
               PTRACE_O_TRACECLONE | PTRACE_O_TRACEEXEC)
    process.setoptions(options)
    syscall_state[pid_parent] = 0
    process.syscall()

    print(f"--- Trace activ pe PID {pid_parent} ---")
    has_forked = False

    while debugger.list:
        try:
            event = debugger.waitProcessEvent()
            current_proc = event.process
            pid_curr = current_proc.pid
            
            if event.__class__.__name__ == "ProcessExit":
                print(f"[EXIT] PID {pid_curr} s-a terminat.")
                if pid_curr in syscall_state: del syscall_state[pid_curr]
                if has_forked and len(debugger.list) == 1 and pid_parent in debugger.dict:
                    debugger.dict[pid_parent].cont()
                continue

            if event.__class__.__name__ == "NewProcessEvent":
                has_forked = True
                current_proc.setoptions(options)
                # Copilul apare la ieșirea din fork/clone, deci result e în RAX (0)
                regs = current_proc.getregs()
                print(f"[FORK] PID {pid_curr} (CHILD) -> Rezultat: {regs.rax}")
                syscall_state[pid_curr] = 1 
                current_proc.syscall()
                continue

            # Alternăm între intrare (0) și ieșire (1)
            state = syscall_state.get(pid_curr, 0)
            syscall_state[pid_curr] = 1 - state

            # Procesăm DOAR la ieșire (state == 1)
            if syscall_state[pid_curr] == 1:
                regs = current_proc.getregs()
                sys_num = regs.orig_rax
                result = regs.rax

                if sys_num == 1: # write
                    data = current_proc.readBytes(regs.rsi, regs.rdx)
                    print(f"[WRITE] PID {pid_curr} (FD {regs.rdi}): {data!r}")
                
                elif sys_num == 0: # read
                    # Verificăm dacă s-a citit ceva (result > 0)
                    if 0 < result < 0xFFFFFFFFFFFFF000:
                        data = current_proc.readBytes(regs.rsi, result)
                        print(f"[READ] PID {pid_curr} (FD {regs.rdi}): {data!r}")

                elif sys_num in (56, 57): # fork/clone
                    if result < 0xFFFFFFFFFFFFF000:
                        print(f"[FORK] PID {pid_curr} (PARENT) -> Rezultat: {result}")
                    else:
                        # Resetăm starea dacă nu e gata (WAITING)
                        syscall_state[pid_curr] = 0

                elif sys_num in (22, 293): # pipe/pipe2
                    raw_fds = current_proc.readBytes(regs.rdi, 8)
                    fds = struct.unpack("ii", raw_fds)
                    print(f"[PIPE] PID {pid_curr} -> FDs: {fds}")

            current_proc.syscall()

        except Exception:
            break

    debugger.quit()
    print("--- Trace finalizat ---")

if __name__ == "__main__":
    trace_program("./a.out", [])
