EXEC = paccap
CC = gcc
INC =
CFLAGS = -fPIC -Wall -O3 -std=gnu99 $(INC) $(CFCMD)
LIBS =

OBJS = paccap.o vdif.o

all: $(EXEC)

%.o: %.c
	$(CC) -c -o $@ $< $(CFLAGS)

$(EXEC): $(OBJS)
	$(CC) -o $@ $^

clean:
	rm -f *.o
	rm -f $(EXEC)
