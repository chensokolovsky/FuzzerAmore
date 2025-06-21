

from FAEdgeHookWriter import *

class FAHooksWriter:

    def __init__(self, ends_of_basic_blocks: list, playground_write_start_loc: int, trampoline_address: int, tmp_register, verbose=False):
        """
        if trampoline address is none, the hooks will be writted straight to the playground and return straight to the playground
        If trampoline address is not none, everything will go through a trampoline. The trampoline should be set to a value if the fuzzed
        function address ia far away from the playground address by more than ±128 mb due to the B mnemonic limitation in ARM
        """
        
        self.ends_of_basic_blocks = ends_of_basic_blocks
        self.playground_write_start_loc = playground_write_start_loc
        self.trampoline_address = trampoline_address
        self.tmp_register = tmp_register
        self.verbose = verbose



    def writeAllHooks(self):

        if self.trampoline_address is None:
            if self.verbose:
                print("Will be writing hooks straight from target function to playground")

        else:
            if self.verbose:
                print("Will be writing hooks from target function to trampoline and from trampoline to background")

        i = 0
        total_hooks = len(self.ends_of_basic_blocks)
        print(f"writing {total_hooks} hooks. Please wait...");
        current_playground_write_loc = self.playground_write_start_loc

        if self.trampoline_address is None:
            for split_inst in self.ends_of_basic_blocks:
                hookWriter = FAEdgeHookWriter(split_inst, current_playground_write_loc, None, None, verbose=False)
                hookWriter.write_hook(via_trampoline=False)
                current_playground_write_loc += PLAYGROUND_GAP_SIZE * 2
                i += 1
                print(f"{i}|",end='')
            return i
        

        else:
            current_trampoline_write_loc = self.trampoline_address
            tmp_register = self.tmp_register
            for split_inst in self.ends_of_basic_blocks:
                hookWriter = FAEdgeHookWriter(split_inst, current_playground_write_loc, current_trampoline_write_loc, tmp_register, verbose=False)
                hookWriter.write_hook(via_trampoline=True)
                current_playground_write_loc += PLAYGROUND_GAP_SIZE * 2
                current_trampoline_write_loc += TRAMPOLINE_GAP_SIZE * 3
                i += 1
                print(f"{i}|",end='')
            return i

