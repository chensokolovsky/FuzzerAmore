#python script for fuzzer amore setup

import lldb
from FAKeystoneHelper import *
from FAWriter import *
from FATypes import *

""" ----- Configure the fuzzed function adress and length ------"""

def getFuzzedFunctionAddress():
    return getAddressOfSymbol("fuzzMeExample", "harness")

def getFuzzedFunctionLength():
    # number of instructions (offsets diff / 4)
    return 0x1c0


def getTrampolineAddress():
    # If the adress is less than 128mb away from playground return None
    return None

def getTempRegister():
    # If the adress is less than 128mb away from playground return None
    return None


""" ----  Example of a system library ------"""
"""
#If you uncomment this part, you need to comment the one above it
def getFuzzedFunctionAddress():
    return getAddressOfSymbol("-[NSPlaceholderString initWithBytes:length:encoding:]", "Foundation", verbose=False)

def getFuzzedFunctionLength():
    # number of instructions (offsets diff / 4)
    return 48

def getTrampolineAddress():
    #return an address that can we can overwrite for trampoline purposes. See docs. This is needed if distance between fuzzed target and playground is above 128Mb
    return getAddressByModuleAndOffset(0x048124, "Foundation", verbose=False)

def getTempRegister():
    #return a string of a register which is safe to use as a tmp storage of trampoline branching
    return "x17"

"""

"""  generic function for fetching addresses """
def getVCAddress():
    addr = getAddressOfSymbol("selfPtr", "harness")
    return read_ptr_value_from_addr(addr)

def getPlaygroundAddress():
    return getAddressOfSymbol("-[ViewController myCodePlayground]", "harness")


def getCalledRealAddress():
    return getAddressOfSymbol("-[ViewController myCodeReal]", "harness")


def _getTarget():
    target = lldb.debugger.GetSelectedTarget()
    return target


def getAddressByModuleAndOffset(offset_val, module_name, verbose=False):
    """ Expects an offset value (a number like 0xcafe) and the module name"""
    if verbose:
        print(f"Trying to obtain address of offset: {hex(offset_val)} from module: {module_name}")
    target = _getTarget()
    module = target.FindModule(lldb.SBFileSpec(module_name))
    base_address = module.sections[0].GetLoadAddress(target)
    if verbose:
        print(f"base address of module {module_name} is {hex(base_address)}")
    return base_address + offset_val

def getAddressOfSymbol(symbol_str, module_name, verbose=False):
    if verbose:
        print(f"Trying to obtain address of symbol: {symbol_str} from module: {module_name}")
    target = _getTarget()
    module = target.FindModule(lldb.SBFileSpec(module_name))
    symbol = module.FindSymbol(symbol_str)
    addr = symbol.GetStartAddress()
    if verbose:
        print(f"{symbol_str} address:", addr)
    p1 = addr.GetLoadAddress(target)
    if verbose:
        print("Load address: 0x%x" % p1)
    return p1


def read_ptr_value_from_addr(addr, verbose=False):
    target = _getTarget()
    error = lldb.SBError()
    process = target.GetProcess()
    pointer_value = process.ReadPointerFromMemory(addr, error)
    if verbose:
        print(f"Pointer value is: {hex(pointer_value)}")
    return pointer_value


def read_asm_command_bytes_from_addr(addr, verbose=False):
    process = _getTarget().GetProcess()
    error = lldb.SBError()
    data = process.ReadMemory(addr, 4, error)

    if error.Success():
        res = "Bytes:", ' '.join(f'{b:02X}' for b in data)
        if verbose:
            print(res)
        return data
    else:
        print("Read failed:", error.GetCString())


def print_disas(addr, lines):
    target = _getTarget()   

    sb_addr = target.ResolveLoadAddress(addr)
    instructions = target.ReadInstructions(sb_addr, lines, "arm64")

    for ins in instructions:
        print("0x%x:\t%s\t%s" % (
            ins.GetAddress().GetLoadAddress(target),
            ins.GetMnemonic(target),
            ins.GetOperands(target)
        ))


def find_mnemonics(mnemonics_list, from_address, lines) -> list[FAInstruction]:
    """
    returns a list of addresses and mnemonics from the provided mnemonics list 
    in the range of from_address to +lines
    return type is a list of tuples: (address, mnemonic, operands)
    """
    target = _getTarget()   

    sb_addr = target.ResolveLoadAddress(from_address)
    instructions = target.ReadInstructions(sb_addr, lines, "arm64")
    
    #instructions is a list of lldb.SBInstruction. Need to convert it so keystore can read

    results = []
    for ins in instructions:
        mnemonic = ins.GetMnemonic(target)
        if mnemonic.lower().startswith("aut"):
            print(f"Found PAC auth mnemonic. stopping here")
            break
        if ins.GetMnemonic(target) in mnemonics_list:
            a = ins.GetAddress().GetLoadAddress(target),
            b = ins.GetMnemonic(target),
            c = ins.GetOperands(target)
            results.append(FAInstruction(a[0],b[0],c))
    
    return results

    


def write_command_to_mem(command_str, dest_addr, verbose=False):
    command = create_command_from_str(command_str)
    FAWriter.write_command(command, dest_addr, verbose=verbose)


def write_report_edge_code(write_start_addr, edge_addresses, verbose=False):
    """
    write_start_addr - an address within the playground to which the report ASM code will be written to
    edge_addresses - a tuple with the from and to addresses to report.
    """
    
    # Store 4 values on the stack
    prolog_a = "stp     x0, x1, [sp, #-16]!"
    prolog_a_bytes = create_command_from_str(prolog_a)
    prolog_b = "stp     x2, x3, [sp, #-16]!"
    prolog_b_bytes = create_command_from_str(prolog_b)


    # Restore them at the end
    epilog_a = "ldp     x2, x3, [sp], #16"
    epilog_a_bytes = create_command_from_str(epilog_a)
    epilog_b = "ldp     x0, x1, [sp], #16"
    epilog_b_bytes = create_command_from_str(epilog_b)
    

    # The reporting function
    vc_address = getVCAddress()
    address_of_report_edge = getAddressOfSymbol("objc_msgSend$reportEdge:to:", "harness")
    
    if verbose:
        print(f"start address is {hex(write_start_addr)}")
        print(f"address of report edge: {edge_addresses}")


    writer = FAWriter(write_start_addr)

    # prolog
    writer.write_bytes(prolog_a_bytes)
    writer.write_bytes(prolog_b_bytes)

    # set edge from value
    long_command3 = load_imm64_to_reg("x2", edge_addresses[0])
    writer.write_bytes(long_command3)

    # set edge to value
    long_command4 = load_imm64_to_reg("x3", edge_addresses[1])
    writer.write_bytes(long_command4)

    # set ViewController
    long_command = load_address_into_register('x0', vc_address, writer.current_address)
    writer.write_bytes(long_command)

    # set ViewController to x1 too (not sure why, this is what I saw when called it myself)
    long_command2 = load_address_into_register('x1', vc_address, writer.current_address)
    writer.write_bytes(long_command2)

    # Call the objc msg send
    bl_inst = create_bl_instruction(writer.current_address, address_of_report_edge )
    writer.write_bytes(bl_inst)

    # Epilog
    writer.write_bytes(epilog_a_bytes)
    writer.write_bytes(epilog_b_bytes)


