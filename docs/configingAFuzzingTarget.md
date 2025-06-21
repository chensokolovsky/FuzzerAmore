# Configuring A Fuzzing Target

### Selecting a target
Aside from the recommendation of selecting a target as appears in the [blog post](https://chensokolovsky.github.io/FuzzerAmoreBlog/posts/FuzzerAmore.html), the selected function should be reviewd to fit several parameters mentioned in this documentation.

## Python Configurations

### Entry point address
Configure the entry point of the fuzzing target using either a module + address, module + symbols, or absolute address.
The entry point is configured in ```FAMainHelper.py```, by returning it in the ```getFuzzedFunctionAddress``` function.
Helper functions are included such as ```getAddressOfSymbol``` or ```getAddressByModuleAndOffset``` in the same file.

### Size
The size of the target is set by number of instructions. In arm these are 4 bytes per opcode, so you can divide the range of the function by 4. This completes the range that the fuzzer will be searching for ends-of-basic-blocks to hook.
Note that is a PAC authentication mnemonic appears in the function the loop will stop, and no hooks will be placed after that. Configuring the size is done in ```FAMainHelper.py``` by returning the value in the ```getFuzzedFunctionLength``` method. There are not helpers here, and you will need to calulate it per target.

### Trampoline
When selecting a target function, it makes sense to load run the iOS harness and check the distance of the entry point from the playground address. A distance larger than ±128Mb needs a trampoline, since a ```B``` mnemonics is limited to relative addresses in that range, which make good practive when we want to replace a split command by a single opcode.
If the distance is longer, you will need to select a trampoline address within that range that you'll be able to execute code on. This could be some large function in the same library, or a library close by, that can be a temp playground for performing trampoline jumps to the playground in the iOS harness. The trampoline will just jump to an absolute address, ignoring the 128Mb limitation, and upon return will jump back to the selected branch/split. Dissassemblers can help you sort functions by size, and select a region for using as a trampoline. Note that the term trampoline here is a temporary trampoline from the fuzzing target to the playgoround. The playground may also considered a trampoline by definition, as it restore the original condition, creates its own temp stack, and cleans up afterwords, but in this case I just seperated the two using the terms Playgounrd as the instrumentation reporting code section and the trampoline region which is optional, and used only in cases the target is far from the playground.
The trampoline address is configured in ```FAMainHelper.py``` by returning a value in the ```getTrampolineAddress``` function. Retutning ```None``` means not trampoline is needed, and hooks will get written using ```B``` directly to the playground

### Temp Register
When using a trampoline, a register is needed to store the absolute address of the playground. ```x16``` or ```x17``` will mostly do the job. However, if observing the branhing conditions spots one of these as a condition it may become a problem, as the value will get overwritten before reaching the playground. In such case, select a register that is not used for any of the conditions at the ends of all the basic blocks in your fuzzing target.
The register must be configured if a trampoline is used. This is yet again performed in ```FAMainHelper.py``` by returning a value in ```getTempRegister```. When a trampoline is not needed it is recommended to return ```None```.


## iOS Harness configuration
Inputs from AFL++ come in the form of char* buffer and length.
These should be passed to a C function such as ```int fuzzMeExample(char* buffer, int length)``` within the ViewController, as the provided examples suggest. The C function can then call the fuzzing target by passing the buffer as is, or by creating the needed input format which is derived from the buffer.



