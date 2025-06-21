# Troubleshooting

## Common setup problems
### Single device
Make sure there is only one device connected to the host. There is no configuration in this project to use a UUID for ```iproxy -u``` style. Either add such configuration in your fork/branch, or use one device

### USB data cable
Make sure the device is connected via USB to the device. The LAN and wifi doesn't play a role here (could be used just to install the iOS harness). iproxy needs a physical connection. The cable should support data and not just charging. A good indication of a proper cable is that you can see the device in your Finder, and upon first connection your device is requesting you to trust this computer.

### Launch ios Harness manually
Once you sign and install the iOS harness (via Xcode) stop the process and launch the harness manually. This is required because the lldb container will try to attach to the process, and when Xcode is running it, it sets up its own lldb, and a process can have only one tracer at a time. Alternatively turn off the debugging option in the scheme editor of Xcode.

### Host network tools
iProxy and port forwarding rely on certain tools on the host. They are usually included with xcode-select tools, but some are needed to be installed seperately (brew is probably best). Full list of tools is in the README, but iproxy, socat, netstat are crutial.

### iOS version
This project is set up for iOS 17 and above, and connecting the tunnel and finding the harness PID + launching debugserver + obtaining the connection details could differ. Read pymobiledevice3 docs for more info (17.4 may differ from 17.5 and so on)
It is advice that different iOS version should be tested and change the current scripts accordingly.


## What it looks like when it is working properly?
In the current docs folder there are example of logs of a successful run for each docker:   
[lldb docker](./successful_logs_of_lldb_docker.txt)   
[afl docker](./successful_logs_of_afl_docker.txt)   


## More complext issues
### configuration ports
If you have changes the configuration ports of communicating from the C harness to the iOS harness, you will need to change it in the ViewController of the harness and recompile. The rest of the ports should be a single source of truth from the config file

### cmd parsing
Some of the script extract PIDs and similar data by parsing the output of tools like netstat. Different hosts and different versions may place the PID columns in a different location, which will need to be adjusted accordingly. For example ```{print \$11}``` might need to become ```{print \$9}```

### AFL not starting
If you run into AFL issues, go to the AFL's [init script](../afl_docker/env/init) and run the ```afl-fuzz``` with the additional env vars: ```#AFL_DEBUG=1 AFL_NO_UI=1```. Such a line is commented in that script, which should be relaced by the line above it. Using these flags will cause AFL to print the C harness logs to console.


### iOS harness hooking problems
Python scripts should get loaded and handle the hooking of the fuzzing target. If that doesn't happen some possible reasons will be logged to the console. Other reasons should be looked at seperately, per stage, by adding log messages, and/or using the UI buttons to test basic functionality of the harness.   
It is possible to run the lldb part via xcode, but some special setup is needed, which involves installing the python dependencies like Capstone and Keystone in a python path that Xcode's lldb interpreter can import (some more info on that in the README)
When running via Xcode you you can add NSLog messages to key points like "reportEdge", before/after the fuzzing target, etc.
Note that when setting up the hooks via Xcode instead of the lldb docker, once the hooks are written, don't detach Xcode, just hit ```c``` to continue the debugger. If crashes occur and Xcode points the crash to the playground, better read the pc and the disas to clarify the crash reason.
Also note that when changing python scripts you may need to quit Xcode, reopen it, and import FuzzerAmore.py again.


### Python Verbosity
Many of the python classes contain verbosity options that can be manually changed to help resolve issues. These python print statements will be printed into the lldb console (or Xcode's console) when setting up the hooks.


### Configuration
Configuring the right parameters is not easy. It should start with a static analysis to select a good fuzzing target which is not to big to instrument. Read the [configuration](./configingAFuzzingTarget.md) guide carefully to check this was done right.

### Crashing the test case
There could be several reasong for crashing. Most common I encountered so far were not using a trampoline when it was needed (see configuration doc), or PAC protected functions that do not exit properly upon inputs. In the second case it might be worth checking if the AUT mnemonic made the loop exit, or that the length of the target matches the wanted offset.
