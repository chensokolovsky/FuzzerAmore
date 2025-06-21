from collections import namedtuple

FAInstruction = namedtuple('Instruction', ['address', 'mnemonic', 'operands'])


PLAYGROUND_GAP_SIZE = 0x70
TRAMPOLINE_GAP_SIZE = 0x20