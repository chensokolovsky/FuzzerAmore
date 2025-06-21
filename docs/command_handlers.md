# Command Handlers

The following arm64 instructions are handeled by the FAHookWriter code   
The goal is to replace the condition with a jump to the hook code (playground) and perform the condition over there.   
In theory, branching does not change the flags or any registers, so moving the condition should "just work"   

Full list:
B.EQ
B.NE
B.CS
B.HS
B.CC
B.LO
B.MI
B.PL
B.VS
B.VC
B.HI
B.LS
B.GE
B.LT
B.GT
B.LE
tbz
tbnz
cbz
cbnz


Yet, the better approach is to test each case, which is represented in the following:

**tbnz**   
example:
```
BL              _open
TBNZ            W0, #0x1F, loc_1E2C0FFEC
```
This command checks if a bit index (0x1f) is set at W0.   
if the bit is non zero it will jump to the specified location   
if the bit is zero it will continue to the next instruction   

**tbz**   
example:
```
BL              0x1E2EF4208
TBZ             W0, #0, loc_1E2C10EF8
```
this command tests if the bit at index 0 of w0 is set.   
if it is zero (not set) it will jump to the specified location   
if the bit is set, it will continue to the next instruction   

**b.eq**   
example:
```
CMP             X1, #1
B.EQ            loc_1E2C11914
```
this command will depend on the previous line and branch if the comparison was equal   
if x1 is equal to 1 it will branch to the specified location   
if x1 is not 1, it will continue to the next line   

**b.hi**   
example:
```
CMP             W24, #3
B.HI            loc_1E2C13728
```
This command branches to the specified location if w24 is higher than 3 (unsigned comparison)   
It will continue to the next instruction if not   


**cbz**   
example:
```
CBZ             X0, loc_1E2C119E4
```
compares x0 to zero and branches to the specified location of zero   
if x != 0, continues to the next command   


### Todo
Some basic blocks may end with different branching, such as to a register, a calculated offset, switch conditions, jump tables, etc...   
The covered mnemonics so far are only those with dichotomous conditions