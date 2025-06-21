
from keystone import Ks, KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN



def test_keystone():
    """ Sanity check for importing keystone """
    print("Test keystone started")
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)

    # Example addresses (as if they were pc values)
    current_pc = 0x1000
    target_addr = 0x1100

    # Compute offset in instructions (not bytes)
    offset = (target_addr - current_pc) // 4  # must be word-aligned

    encoding, _ = ks.asm(f"B #{offset}", addr=current_pc)

    print("Bytes:", encoding)
    return encoding


def create_commands_for_branch(current_pc, target_addr, verbose=False):
    """ returns the bytes of a branch command to a specified address """
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    if verbose:
        print(f"Creating encoding for B #{hex(target_addr)}, from current_pc {hex(current_pc)}")
    encoding, _ = ks.asm(f"B #{target_addr}", addr=current_pc)
    return encoding

def create_command_from_str(command):
    """ 
    Returns the bytes of the provided command string. Works only for simple commands like mov x0, #1
    Note that 64 bit values mostly need two lined for branching, storing etc...
    """
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    encoding, _ = ks.asm(command)
    return encoding


def create_command_from_str_with_pc(command, pc):
    """ 
    Returns the bytes of the provided command string. Meant for commands with relative offsets that need pc as a parameter
    command should be a string with mnemonic and oerands
    """
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    encoding, _ = ks.asm(command, addr=pc)
    return encoding


def load_address_into_register(reg: str, addr: int, current_pc: int):
    """
    Stores an address to a register. Workes for 64 bit values.
    The value is an address and will be position independent and relative (ignoring ASLR)
    """

    page_base = addr & ~0xFFF
    page_off = addr & 0xFFF

    asm = f"""
    adrp {reg}, 0x{page_base:x}
    add  {reg}, {reg}, #{page_off}
    """

    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    encoding, _ = ks.asm(asm, addr=current_pc)
    return encoding


def create_bl_instruction(current_pc: int, target_addr: int):
    """
    Generates the ARM64 `bl` instruction to branch from current_pc to target_addr.
    Returns the assembled byte sequence.
    """
    # The branch immediate is word-aligned (scaled by 4)
    offset = target_addr - current_pc
    if offset % 4 != 0:
        raise ValueError("BL target address must be 4-byte aligned relative to current PC.")

    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    asm = f"bl #{target_addr}"
    encoding, _ = ks.asm(asm, addr=current_pc)
    return encoding


def load_imm64_to_reg(reg: str, value: int):
    """
    This stores a 64 bit value into a register. Note that this is a fixed value and not relative
    """

    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)
    asm = []

    # Load lower 16 bits using movz
    asm.append(f"movz {reg}, #{value & 0xFFFF}, lsl #0")

    # Fill remaining 48 bits using movk
    for shift in [16, 32, 48]:
        part = (value >> shift) & 0xFFFF
        #if part != 0:
        asm.append(f"movk {reg}, #{part}, lsl #{shift}")

    encoding, _ = ks.asm("\n".join(asm))
    return encoding


"""
This is currently from GPT, but should be split because it has both helper logic and ks logic here.
This can be something like a handler for TBNZ that will be written in the playground.
Each block will report the different edge
"""

def generate_branch_stub(base, addr_zero, addr_nonzero):
    ks = Ks(KS_ARCH_ARM64, KS_MODE_LITTLE_ENDIAN)

    # Offsets
    offset_zero = 8  # tbz + b = 8 bytes → offset to .Lzero_path
    offset_nonzero = 16  # .Lnonzero_path is at base + 8

    asm = [
        f"tbz w8, #0, #{offset_zero}",
        f"b #{offset_nonzero - 4}",  # jump to .Lnonzero_path (PC is at b+4)

        # .Lzero_path (at base + 8)
        "nop",
        "nop",
        f"b #{addr_zero - (base + 16)}",  # base + 16 = PC at this b

        # .Lnonzero_path (at base + 20)
        "nop",
        "nop",
        f"b #{addr_nonzero - (base + 28)}",  # PC at this b = base + 28
    ]

    encoding, _ = ks.asm("\n".join(asm), addr=base)
    return encoding