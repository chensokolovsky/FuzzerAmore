/*
   american fuzzy lop++ - afl-proxy skeleton example
   ---------------------------------------------------

   Written by Marc Heuse <mh@mh-sec.de>

   Copyright 2019-2024 AFLplusplus Project. All rights reserved.

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at:

   http://www.apache.org/licenses/LICENSE-2.0


   HOW-TO
   ======

   You only need to change the while() loop of the main() to send the
   data of buf[] with length len to the target and write the coverage
   information to __afl_area_ptr[__afl_map_size]


*/

#ifdef __ANDROID__
  #include "android-ashmem.h"
#endif
#include "config.h"
#include "types.h"

#include <stdio.h>
#include <stdlib.h>
#include <signal.h>
#include <unistd.h>
#include <string.h>
#include <assert.h>
#include <stdint.h>
#include <errno.h>

#include <time.h>

#include <sys/mman.h>
#include <sys/shm.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <fcntl.h>

// Added for socket communication
#include <sys/socket.h>
#include <arpa/inet.h>
#include <stdarg.h>

u8 *__afl_area_ptr;

#ifdef __ANDROID__
u32 __afl_map_size = MAP_SIZE;
#else
__thread u32 __afl_map_size = MAP_SIZE;
#endif

/* Error reporting to forkserver controller */

void send_forkserver_error(int error) {
  printf("Sending Error 0x%X\n", error);
  u32 status;
  if (!error || error > 0xffff) return;
  status = (FS_OPT_ERROR | FS_OPT_SET_ERROR(error));
  if (write(FORKSRV_FD + 1, (char *)&status, 4) != 4) return;

}

/* SHM setup. */

static void __afl_map_shm(void) {

  char *id_str = getenv(SHM_ENV_VAR);
  char *ptr;

  /* NOTE TODO BUG FIXME: if you want to supply a variable sized map then
     uncomment the following: */

  /*
  if ((ptr = getenv("AFL_MAP_SIZE")) != NULL) {

    u32 val = atoi(ptr);
    if (val > 0) __afl_map_size = val;

  }

  */

  if (__afl_map_size > MAP_SIZE) {

    if (__afl_map_size > FS_OPT_MAX_MAPSIZE) {

      fprintf(stderr,
              "Error: AFL++ tools *require* to set AFL_MAP_SIZE to %u to "
              "be able to run this instrumented program!\n",
              __afl_map_size);
      if (id_str) {

        send_forkserver_error(FS_ERROR_MAP_SIZE);
        exit(-1);

      }

    } else {

      fprintf(stderr,
              "Warning: AFL++ tools will need to set AFL_MAP_SIZE to %u to "
              "be able to run this instrumented program!\n",
              __afl_map_size);

    }

  }

  if (id_str) {

#ifdef USEMMAP
    const char    *shm_file_path = id_str;
    int            shm_fd = -1;
    unsigned char *shm_base = NULL;

    /* create the shared memory segment as if it was a file */
    shm_fd = shm_open(shm_file_path, O_RDWR, 0600);
    if (shm_fd == -1) {

      fprintf(stderr, "shm_open() failed\n");
      send_forkserver_error(FS_ERROR_SHM_OPEN);
      exit(1);

    }

    /* map the shared memory segment to the address space of the process */
    shm_base =
        mmap(0, __afl_map_size, PROT_READ | PROT_WRITE, MAP_SHARED, shm_fd, 0);

    if (shm_base == MAP_FAILED) {

      close(shm_fd);
      shm_fd = -1;

      fprintf(stderr, "mmap() failed\n");
      send_forkserver_error(FS_ERROR_MMAP);
      exit(2);

    }

    __afl_area_ptr = shm_base;
#else
    u32 shm_id = atoi(id_str);

    __afl_area_ptr = shmat(shm_id, 0, 0);

#endif

    if (__afl_area_ptr == (void *)-1) {

      send_forkserver_error(FS_ERROR_SHMAT);
      exit(1);

    }

    /* Write something into the bitmap so that the parent doesn't give up */

    __afl_area_ptr[0] = 1;

  }

}

/* Fork server logic. */

static void __afl_start_forkserver(void) {

  u8  tmp[4] = {0, 0, 0, 0};
  u32 status = 0;

  if (__afl_map_size <= FS_OPT_MAX_MAPSIZE)
    status |= (FS_OPT_SET_MAPSIZE(__afl_map_size) | FS_OPT_MAPSIZE);
  if (status) status |= (FS_OPT_ENABLED);
  memcpy(tmp, &status, 4);

  /* Phone home and tell the parent that we're OK. */

  if (write(FORKSRV_FD + 1, tmp, 4) != 4) return;

}

static u32 __afl_next_testcase(u8 *buf, u32 max_len) {

  s32 status, res = 0xffffff;

  /* Wait for parent by reading from the pipe. Abort if read fails. */
  if (read(FORKSRV_FD, &status, 4) != 4) return 0;

  /* we have a testcase - read it */
  status = read(0, buf, max_len);

  /* report that we are starting the target */
  if (write(FORKSRV_FD + 1, &res, 4) != 4) return 0;

  return status;

}

static void __afl_end_testcase(void) {

  int status = 0xffffff;

  if (write(FORKSRV_FD + 1, &status, 4) != 4) exit(1);

}


/*
Up to this point in the code, the functions come from the example in aflplusplus/utils/afl-proxy.c
There are probably some imports for the code from here on to work, which are up in the beginning of the file
*/
///******** Below this lines are my additions for communicating with the iOS harness *********************////


/* Logging */

void FALog(const char *fmt, ...) {

    u8 verbose = 1;
    if (verbose) {
      va_list args;
      char buffer[256];
      va_start(args, fmt);
      vsnprintf(buffer, sizeof(buffer), fmt, args);
      va_end(args);
      printf("[#C_PROXY#]%s", buffer);
    }

}


/* Socket*/
#define SERVER_IP "host.docker.internal"  // For troubleshooting, this could be the replaced by your device's local LAN ip 
#define BUFFER_SIZE 1024

int sock;
struct sockaddr_in server;
char test_message[] = "Hello, Server!";
char buffer[BUFFER_SIZE];

int create_socket() {
  // Create socket
    sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock == -1) {
        perror("Socket creation failed");
        return 1;
    }

    int server_port = atoi(getenv("SERVER_PORT"));
    FALog("The server port is %d\n", server_port);

    server.sin_family = AF_INET;
    server.sin_port = htons(server_port);
    server.sin_addr.s_addr = inet_addr(SERVER_IP);

    // Connect to server
    if (connect(sock, (struct sockaddr *)&server, sizeof(server)) < 0) {
        perror("Connection failed");
        close(sock);
        return 1;
    }
  return 0;
}

int send_message(u8* buffer,  s32 len ) {

    // Send message
    if (send(sock, buffer, len, 0) < 0) {
        perror("Send failed\n");
        close(sock);
        return 1;
    }
    FALog("Message sent %d bytes\n", len);
    return 0;
}


/* Converting the coverage from sent format from iOS harness to a shm format */
int set_coverage_data_to_shm(char buffer[]) {
  
  //FALog("Setting coverage data: %s\n", buffer);
  
  char* token = strtok(buffer, "|");
    while (token != NULL) {
        //FALog("Token: %s\n", token);

        char indexBuf[5] = {0};
        strncpy(indexBuf, token, 4);
        u16 index =(u16)strtoul(indexBuf, NULL, 16);
        char countBuf[3] = {0};
        strncpy(countBuf, token + 4, 2);
        u8 count =(u8)strtoul(countBuf, NULL, 16);
        
        //FALog("split token to 0x%X and 0x%X\n", index, count);
        __afl_area_ptr[index] = count;

        //FALog("added SHM entry \n");
        token = strtok(NULL, "|");

    }

}

// set up a fake map so that AFL thinks this is a unique crash
void spoof_afl_coverage() {
  srand(time(NULL));  // Seed random once per run

  for (int i = 0; i < 5; i++) {
      uint16_t index = rand() & 0xFFFF;                 // random index 0–0xFFFF
      uint8_t value = 20 + rand() % (100 - 20 + 1);      // random value 20–100
      __afl_area_ptr[index] = value;
  }
}



/* you just need to modify the while() loop in this main() */

int main(int argc, char *argv[]) {
  FALog("C proxy main called\n");

  int server_port = atoi(getenv("SERVER_PORT"));
  FALog("The server port is %d\n", server_port);


  int socket_result = create_socket();
  FALog("Socket result: %d\n", socket_result);

  /* This is were the testcase data is written into */
  u8  buf[1024];  // this is the maximum size for a test case! set it!
  s32 len;

  /* here you specify the map size you need that you are reporting to
     afl-fuzz.  Any value is fine as long as it can be divided by 32. */
  __afl_map_size = 0xffff; //MAP_SIZE;  // default is 65536

  /* then we initialize the shared memory map and start the forkserver */
  __afl_map_shm();
  __afl_start_forkserver();

  while ((len = __afl_next_testcase(buf, sizeof(buf))) > 0) {
  

    if (len > 4) {  // the minimum data size you need for the target
      FALog("C proxy for input from afl\n");
      int send_result = send_message(buf, len);
      FALog("C proxy send result: %d\n", send_result);

      /* here you have to create the magic that feeds the buf/len to the
         target and write the coverage to __afl_area_ptr */

      // ... the magic ...

      // remove this, this is just to make afl-fuzz not complain when run
      /*
      if (buf[0] == 0xff)
        __afl_area_ptr[1] = 1;
      else
        __afl_area_ptr[2] = 2;
      */


      // Receive response
      FALog("Waiting for coverage response\n");

      ssize_t recv_size = recv(sock, buffer, BUFFER_SIZE - 1, 0);
      printf("recv_size: %zd\n", recv_size);  // Debugging output

      if (recv_size < 0) {
          perror("Receive failed");
          abort();
      } else if (recv_size == 0) {
          FALog("Server closed connection\n");
      } else {
          buffer[recv_size] = '\0';  // Null-terminate received data
          FALog("Server response: %s\n", buffer);

          // found a crash
          if (strcmp(buffer, "*CRASH*") == 0) {
            FALog("Crash occured, reporting to AFL++\n");

            int should_spoof = 1;

            // let's pretend we want to mark all crashes as unique, so fill some rnadom data
            if (getenv("IAFL_SKIP_RANDOM_MAP") != NULL) {
              should_spoof = 0;
            }

            if (should_spoof) spoof_afl_coverage();

            send_forkserver_error(-2);
            continue;

          }

          else {

            // Convert the format to coverage map
            // The selected format is this:
            // "AABBCC|00aa22|00A402" - each 6 hex digit represents an entry
            // First entry exampe: index 0xAABB of shm, a count of 0xCC
            // Second: index 0x00aa, a value of 0x22 etc..
            set_coverage_data_to_shm(buffer);
          }


      }

    }

    FALog("Coverage is done\n");

    /* report the test case is done and wait for the next */
    __afl_end_testcase();

  }

  close(sock);

  return 0;

}

