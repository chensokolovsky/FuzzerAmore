#python script for fuzzer amore setup


from FAMainHelper import *
from FAKeystoneHelper import *
from FACapstoneHelper import *
from FAHooksWriter import *

def __lldb_init_module(debugger, dict):
    print('lldb init called')
    setup_hooks()


def setup_hooks():
    # This is the entry point

    # ----  Some initial prints of addresses ---- #
    playground_address = getPlaygroundAddress()
    playground_address_str = hex(playground_address)
    print(f"playground addresss is {playground_address_str}")
    if '0xffffffff' in playground_address_str:
        print("Error!!! could not find playground's address.")
        print("Check for previous error message in connecting lldb to the process")
        print("An possible reason is that you are running the harness via Xcode and you did not lauch it manually, which means XCode's debugger is attached to it and the container's lldb can't attach")
        print("Quit lldb, exit the container, and try running manually")
        lldb.SBDebugger.Terminate()
        return

    fuzzed_function_address = getFuzzedFunctionAddress()
    print(f"fuzzed function address is {hex(fuzzed_function_address)}")

    total_lines = getFuzzedFunctionLength()

    code_real_address = getCalledRealAddress()
    print(f"example report call function is {hex(code_real_address)}")

    vc_address = getVCAddress()
    print(f"VC address: {hex(vc_address)}")


    mnemonics_list = ('B.EQ', 'B.NE', 'B.CS', 'B.HS', 'B.CC', 'B.LO', 'B.MI', 'B.PL', 'B.VS', 'B.VC', 'B.HI', 'B.LS', 'B.GE', 'B.LT', 'B.GT', 'B.LE', 'tbz', 'tbnz', 'cbz', 'cbnz')
    ends_of_basic_blocks = find_mnemonics([s.lower() for s in mnemonics_list],fuzzed_function_address, total_lines)
    print("ends_of_basic_blocks:")
    for block in ends_of_basic_blocks:
        print(f"[{hex(block.address)}", end=', ')
        print(f"{block.mnemonic}", end=", ")
        print(f"{block.operands}]")


    playground_write_start_loc = playground_address + 0x5c
    trampoline_address = getTrampolineAddress()
    tmp_register = getTempRegister()
    print(f"Trampoline address is {trampoline_address}")
    hooksWriter = FAHooksWriter(
                                ends_of_basic_blocks,
                                playground_write_start_loc,
                                trampoline_address,
                                tmp_register,
                                verbose=False
                                )

    i = hooksWriter.writeAllHooks()

    if i == 0:
        print("Error. Somthing doesn't seem right")
        print("\nEither some error occured or there are not edges in the fuzzed function")
        print("Things to check:")
        print("Is the process running?")
        print("Did you already write hooks to this process in the previous run and didn't relauch since?")
        print("Did lldb connect to the process?")
        print("is the PID correct?")
        print("did the setup find the fuzzed function correctly?")
    else:
        print(f"\nWrote {i} instrumentation hooks. Looks good")
        print("***************************************************************")
        print("**  Now its time to continue the process, detaching, quitting the debugger, and running AFL")
        print("**  In the lldb console do the following:")
        print("**  (lldb) c")
        print("**  (lldb) proc deta")
        print("**  (lldb) q")
        print("**  you can also exit the lldb container:")
        print("**  /env# exit")
        print("**  Then in the host terminal:")
        print("**  $ ./build_and_run_afl_docker")
        print("***********  DONE. Follow the instructions above ^ *************")

    
