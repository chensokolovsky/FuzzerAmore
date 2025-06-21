all:	afl-proxy

afl-proxy:	afl-proxy.c
	$(CC) -I/AFLplusplus/ -I./include -o afl-proxy afl-proxy.c

clean:
	rm -f afl-proxy *~ core
