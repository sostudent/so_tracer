#include <stdio.h>
#include <unistd.h>

int main(void){
	printf("sleeping\n");
	sleep(1);
	int pid1 = fork();
	printf("%d\n", pid1);
}
