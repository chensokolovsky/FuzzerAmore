from capstone import *



def test_capstone():
    # Raw instruction bytes
    code = bytes.fromhex("E8 01 00 37")  # This is: tbz w8, #0, <offset>

    # Capstone setup for ARM64
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    for instr in md.disasm(code, 0x1000):
        print(f"0x{instr.address:x}:\t{instr.mnemonic}\t{instr.op_str}")


def bytes_to_string(bytes):
    return ' '.join(f'{b:02X}' for b in bytes)


def get_multiple_commands_from_bytes(bytes, pc, verbose=False):
    """
    expected input is a list of byte values ([255,0,16,32]) result is the mnemonic command with args
    could represent multiple commands
    returns a list of CsInst objects
    """
    s = bytes_to_string(bytes)
    code = bytes.fromhex(s)
    md = Cs(CS_ARCH_ARM64, CS_MODE_LITTLE_ENDIAN)

    results = []

    for instr in md.disasm(code, pc):
        if verbose:
            print(f"0x{instr.address:x}:\t{instr.mnemonic}\t{instr.op_str}")
        results.append(instr)

    return results

def get_command_for_bytes(bytes, pc, verbose=False):
    """ when the caller knows there are only 4 bytes and wants one command (or only the first four)
        Return value is CsInst
    """
    return get_multiple_commands_from_bytes(bytes, pc)[0]


