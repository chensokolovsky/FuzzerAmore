//
//  ViewController.m
//  harness
//
//  Created by chenshalev on 31/03/2025.
//

#import "ViewController.h"
#import <sys/socket.h>
#import <netinet/in.h>
#import <arpa/inet.h>
#import <unistd.h>
#import <mach/mach.h>
#import <mach/mach_types.h>
#import <mach/thread_status.h>
#import <mach/mach_init.h>
#import <mach/task.h>
#import <pthread.h>


/*
 This is the listening port between the C harness and the iOS harness
 If you change this port number, make sure to change it also in config.cfg (HARNESS_DEVICE_PORT)
 */
#define PORT 59091

// Definitions
static id selfPtr;
int fuzzMeExample(char* buffer, int length);
int fuzzMeExample2(char* buffer, int length);

NSMutableArray* map;
NSString* convertReportToMap(NSMutableArray* report);
mach_port_t exceptionPort;
bool didCrash;



// crash handler so that the crash is reported to AFL and doesn't terminate the process.
void *exception_handler(void *arg) {
    while (1) {
        struct {
            mach_msg_header_t header;
            uint8_t data[1024];
        } msg;
        
        kern_return_t kr = mach_msg(&msg.header, MACH_RCV_MSG, 0, sizeof(msg), exceptionPort, MACH_MSG_TIMEOUT_NONE, MACH_PORT_NULL);
        if (kr == KERN_SUCCESS) {
            NSLog(@"crashing");
            didCrash = 1;
            sleep(2);
        }
    }
    return NULL;
}

// tell the process to use our own crash exception handler. This will be aproved if you submit to the app store
void setup_crash_catch(void) {
    
    kern_return_t kr = mach_port_allocate(mach_task_self(), MACH_PORT_RIGHT_RECEIVE, &exceptionPort);
    assert(kr == KERN_SUCCESS);
    
    kr = mach_port_insert_right(mach_task_self(), exceptionPort, exceptionPort, MACH_MSG_TYPE_MAKE_SEND);
    assert(kr == KERN_SUCCESS);
    
    
    exception_mask_t mask = EXC_MASK_BAD_ACCESS  | EXC_MASK_ARITHMETIC  ; //EXC_MASK_BREAKPOINT | EXC_MASK_SOFTWARE
    
    kr = task_set_exception_ports(mach_task_self(), mask, exceptionPort, EXCEPTION_DEFAULT, THREAD_STATE_NONE);
    assert(kr == KERN_SUCCESS);
    
    
    pthread_t thread;
    pthread_create(&thread, NULL, exception_handler, NULL);
}


// Incoming message from the C harness
NSString *handle_message(NSData *data) {

    [map removeAllObjects];
    map = nil;
    map = [NSMutableArray new];
    didCrash = 0;

    dispatch_group_t group = dispatch_group_create();
    dispatch_queue_t queue = dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0);

    dispatch_group_async(group, queue, ^{
        fuzzMeExample(data.bytes, data.length);
        //fuzzMeExample2(data.bytes, data.length);
    });

    // Poll until done or crash
    const int maxWaitMs = 1000;
    for (int waited = 0; waited < maxWaitMs; waited++) {
        if (dispatch_group_wait(group, DISPATCH_TIME_NOW) == 0) {
            break; // finished normally
        }
        if (didCrash) {
            return @"*CRASH*"; // crash detected
        }
        usleep(1000); // 1ms
    }

    if (didCrash) return @"*CRASH*";
    return convertReportToMap(map);
}


// Convers the edges reports to values that AFL's proxy expects as coverage data
NSString* convertReportToMap(NSMutableArray* report) {
    NSMutableDictionary<NSNumber *, NSNumber *> *edgeHits = [NSMutableDictionary dictionary];
    
    NSUInteger prevLoc = 0;
    UInt16 i = 0;
        
    int total = [report count];
    
    for (int n = 0; n < total; n++ ) {
        NSArray* pair = [report objectAtIndex:n];
        NSUInteger curLoc = (NSUInteger)[pair objectAtIndex:0];
        if (i > 0) {
            prevLoc = (NSUInteger)[pair objectAtIndex:1];
        }

        uint16_t edgeId = (curLoc ^ (prevLoc >> 1)) & 0xFFFF;
        NSNumber *key = @(edgeId);
        uint8_t count = [[edgeHits objectForKey:key] unsignedCharValue];
        count = (count + 1) % 256;

        if (count == 0) {
            [edgeHits removeObjectForKey:key];
        } else {
            [edgeHits setObject:@(count) forKey:key];
        }
        i++;
    }
    
    // Build final_bitmap
    NSMutableArray<NSString *> *parts = [NSMutableArray array];
    for (NSNumber *key in edgeHits) {
        [parts addObject:[NSString stringWithFormat:@"%04x%02x", [key unsignedShortValue], [edgeHits[key] unsignedCharValue]]];
    }
    NSString *finalBitmap = [parts componentsJoinedByString:@"|"];
    [parts removeAllObjects];
    parts = nil;
    [edgeHits removeAllObjects];
    edgeHits = nil;
    [report removeAllObjects];
    report = nil;
    
    NSLog(@"reporting bitmap: %@", finalBitmap);
    return finalBitmap;
    
}


// start tcp server
void start_tcp_server(void) {
    dispatch_async(dispatch_get_global_queue(DISPATCH_QUEUE_PRIORITY_DEFAULT, 0), ^{
        int server_fd, new_socket;
        struct sockaddr_in address;
        socklen_t addrlen = sizeof(address);
        char buffer[1024] = {0};

        server_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (server_fd == 0) {
            perror("socket failed");
            return;
        }

        int opt = 1;
        setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

        address.sin_family = AF_INET;
        address.sin_addr.s_addr = INADDR_ANY;  // Or inet_addr("127.0.0.1") if you want local only
        address.sin_port = htons(PORT);

        if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
            perror("bind failed");
            close(server_fd);
            return;
        }

        if (listen(server_fd, 3) < 0) {
            perror("listen");
            close(server_fd);
            return;
        }

        NSLog(@"Listening on port %d...", PORT);

        while (1) {
            new_socket = accept(server_fd, (struct sockaddr *)&address, &addrlen);
            if (new_socket < 0) {
                perror("accept");
                continue;
            }
            while (1) {
                @autoreleasepool {
                    
                    ssize_t valread = recv(new_socket, buffer, sizeof(buffer) - 1, 0);
                    if (valread > 0) {
                        NSData *receivedData = [NSData dataWithBytes:buffer length:valread];
                        NSString *response = handle_message(receivedData);
                        
                        send(new_socket, [response UTF8String], (int)[response lengthOfBytesUsingEncoding:NSUTF8StringEncoding], 0);
                        if ([response isEqualToString:@"Echo: EXIT\n"]) {
                            break;
                        }
                        response = nil;
                        receivedData = nil;
                    }
                }
            }
            NSLog(@"closing socket");
            close(new_socket);
        }
    });
}


void handler(int sig);

@interface ViewController ()

@property IBOutlet UILabel* label;
@property IBOutlet UITextView* reportTextView;


@end

@implementation ViewController

- (void)viewDidLoad {
    [super viewDidLoad];
    // Do any additional setup after loading the view.
    
    // Init some stuff
    selfPtr = self;
    [map removeAllObjects];
    map = nil;
    map = [NSMutableArray new];
    setup_crash_catch();
    
    // This makes sure that the playground is not being optimized-out from the binary,
    // and yet isen't invoked
    int randA = arc4random_uniform(100) + 1;
    int randB = arc4random_uniform(30) + 1;
    int randC = randA + randB;
    if (randC < randA) [self myCodePlayground];
    else if (randC < randB) [self myCodePlayground];
    else [self myCodeReal];
    
    // start listening
    start_tcp_server();
    
}

// These were used for troubleshooting during development,
// enable the buttons in the UI if you plan on using them
/*
-(IBAction)buttonAPressed:(id)sender {
    [self fuzzedFunction:(char*)"aaaa" size:4];
    NSMutableArray* arr = [NSMutableArray arrayWithObjects:@[@11111, @11114], @[@41238, @41023], @[@31245,@41215], nil];
    convertReportToMap(arr);
}

-(IBAction)buttonBPressed:(id)sender {
    [self fuzzedFunction:(char*)"FUPPP" size:5];

    
}
-(IBAction)buttonCPRessed:(id)sender {
    [self fuzzedFunction:(char*)"GOOGLET" size:7];

}
*/

// For testing. This should crash after a few minutes, or sometimes seconds (depends on random corpus)
// To configure a different fuzzing function use the FAMainHelper.py in the lldb docker
int fuzzMeExample(char* buffer, int length) {

    void (*crashMe)() = 0;

    if (length < 3)
    return 0;

    if (length > 9)
    return 0;

    if (buffer[0] == 'F')
        if (buffer[1] == 'U')
            if (buffer[2] == 'Z')
                if (buffer[3] == 'Z')
                    crashMe();

    if (buffer[0] == 'a')
        if (buffer[1] == 'b')
            if (buffer[2] == 'c')
                if (buffer[3] == '!')
                    crashMe();


    if (buffer[0] == 'A')
        if (buffer[1] == 'M')
            if (buffer[2] == 'O')
                if (buffer[3] == 'R')
                    if (buffer[4] == 'E')
                        if (buffer[5] == '_')
                            crashMe();


    /* fuzzer_amore_!!! */
    /*
    if (buffer[0] == 'f')
        if (buffer[1] == 'u')
            if (buffer[2] == 'z')
                if (buffer[3] == 'z')
                    if (buffer[4] == 'e')
                        if (buffer[5] == 'r')
                            if (buffer[6] == '_')
                                if (buffer[7] == 'a')
                                    if (buffer[8] == 'm')
                                        if (buffer[9] == 'o')
                                            if (buffer[10] == 'r')
                                                if (buffer[11] == 'e')
                                                    if (buffer[12] == '_')
                                                        if (buffer[13] == '!')
                                                            if (buffer[14] == '!')
                                                                if (buffer[15] == '!')
                                                                    crashMe();
    */
    
    return 0;

}


int fuzzMeExample2(char* buffer, int length) {
    NSString *str = [[NSString alloc] initWithBytes:buffer length:length encoding:NSUTF8StringEncoding];
    return 0;
}



// simulate receiving a buffer from AFL. you can use these with the UI buttons
/*
-(void)fuzzedFunction:(char*)buffer size:(uint32_t)size {
    fuzzMeExample(buffer, size);
    
}
*/

-(void)reportEdge:(void*)from to:(void*)to {
    NSLog(@"reporting edge %lx -> %lx", (long)from, (long)to);
    @autoreleasepool {
        [map addObject:[NSArray arrayWithObjects:[NSNumber numberWithUnsignedLong:from], [NSNumber numberWithUnsignedLong:to], nil]];
    }
}


-(void)myCodeReal {
    NSLog(@"done with conditions");
    // Do not remove this line.
    // calling the selfPtr instead of self so it can be detected dynamically
    [selfPtr reportEdge:(void*)2222 to:(void*)3333];
}


/* ----- PLAYGROUND ------ */
// lldb will write the hooks to jump here, filling these lines with calls to reportEdge per case



// Note: this is currently 5712 bytes, which is suitable for ±34 edges
// This is the case when having 128 of these pairs:
//     NSLog(@"%@ %d", playground, i);
//     i++;
//
// so about 4 pairs per edge
//


- (void)myCodePlayground {
    
    NSString* playground = @"My Playground";
    int i = 0x10;
    
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    NSLog(@"%@ %d", playground, i);
    i++;
    
}



@end
