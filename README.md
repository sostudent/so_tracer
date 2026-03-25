# tracer
tracer for running executables in linux
(it does't work on mac or windows)
# install and run instuctions
```
pip3 install python-ptrace
gcc ex_1.c
python3 trace_v1.py
```

ISO to install linux in a virtual machine: "https://mirrors.nxthost.com/rocky/9/isos/x86_64/Rocky-9.7-x86_64-minimal.iso"
# requirements
```
python3
python-ptrace (it can be installed with pip3 install python-ptrace)
```
# simple c program
```
#include <stdio.h>

int main(void){
	printf("sleeping\n");
	sleep(1);
	int pid1 = fork();
	printf("%d\n", pid1);
}
```
# output example from v2 for the tracer (it has collors + alignemnt, looks better in terminal)
```
--- Trace activ pe PID 9309 ---
[PID 9309] [WRITE] FD 1: b'sleeping\n'
sleeping
 └─ [PID 9311] [FORK ] (CHILD)  -> Rezultat: 0
[PID 9309] [FORK ] (PARENT) -> Rezultat: 9311
pid1 9311
[PID 9309] [WRITE] FD 1: b'pid1 9311\n'
[PID 9309] [EXIT ] Procesul s-a terminat.
   └─ [PID 9316] [FORK ] (CHILD)  -> Rezultat: 0
 └─ [PID 9311] [FORK ] (PARENT) -> Rezultat: 9316
pid2 9316
 └─ [PID 9311] [WRITE] FD 1: b'pid2 9316\n'
pid1 0
sleep 1
 └─ [PID 9311] [WRITE] FD 1: b'pid1 0\n'
   └─ [PID 9316] [WRITE] FD 1: b'sleep 1\n'
 └─ [PID 9311] [EXIT ] Procesul s-a terminat.
pid2 0
   └─ [PID 9316] [WRITE] FD 1: b'pid2 0\n'
pid1 0
   └─ [PID 9316] [WRITE] FD 1: b'pid1 0\n'
   └─ [PID 9316] [EXIT ] Procesul s-a terminat.
--- Trace finalizat ---
```
# output example for that simple c program from v1 of the tracer
```
--- Trace activ pe PID 72446 ---
[WRITE] PID 72446 (FD 1): b'sleeping\n'
sleeping
[FORK] PID 72447 (CHILD) -> Rezultat: 0
0
[WRITE] PID 72447 (FD 1): b'0\n'
[EXIT] PID 72447 s-a terminat.
[FORK] PID 72446 (PARENT) -> Rezultat: 72447
72447
[WRITE] PID 72446 (FD 1): b'72447\n'
[EXIT] PID 72446 s-a terminat.
--- Trace finalizat ---
```

# intrebari
- ce afiseaza daca se scoate \n de la printf
- cum se poate ca sa afiseze numarul mare inaintea numarului mic

