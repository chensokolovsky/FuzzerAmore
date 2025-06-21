
from FATypes import *
from FAWriter import *
from FAKeystoneHelper import *
from FAMainHelper import *


class FAEdgeHookWriter:

    def __init__(self, instruction: FAInstruction, playground_start_address: int, trampoline_address: int, tmp_register, verbose=False):
        self.instruction = instruction
        self.playground_start_address = playground_start_address
        self.playground_jmp_addr_if_result_a = playground_start_address + 0x4
        self.playground_jmp_addr_if_result_b = playground_start_address + PLAYGROUND_GAP_SIZE
        self.trampoline_address = trampoline_address
        self.trampoline_return_addr_if_result_a = 0
        self.trampoline_return_addr_if_result_b = 0
        if trampoline_address is not None:
            self.trampoline_return_addr_if_result_a = trampoline_address + TRAMPOLINE_GAP_SIZE
            self.trampoline_return_addr_if_result_b = trampoline_address + TRAMPOLINE_GAP_SIZE * 2
        self.tmp_register = tmp_register
        self.final_destination_result_a = instruction.address + 0x4
        self.final_destination_result_b = 'err'
        self.new_asm_command = 'err'
        self.verbose = verbose

        ## For B.XX cases (see docs command_handlers.md)
        if instruction.mnemonic.startswith("b."):
            self.final_destination_result_b = int(self.instruction.operands.replace('#', ''), 16)
            self.new_asm_command = f"{self.instruction.mnemonic} {hex(self.playground_jmp_addr_if_result_b)}"
        
        ##  TBZ, TBNZ (3 operands)
        elif instruction.mnemonic.startswith("tb"):
            end_of_block_command_operands_split = self.instruction.operands.split(', ')
            self.final_destination_result_b = int(end_of_block_command_operands_split[2].replace('#', ''), 16)
            self.new_asm_command = f"{self.instruction.mnemonic} {end_of_block_command_operands_split[0]}, {end_of_block_command_operands_split[1]}, {hex(self.playground_jmp_addr_if_result_b)}"
        
        ##  CBZ, CBNZ (2 operands)
        elif instruction.mnemonic.startswith("cb"):
            end_of_block_command_operands_split = self.instruction.operands.split(', ')
            self.final_destination_result_b = int(end_of_block_command_operands_split[1].replace('#', ''), 16)
            self.new_asm_command = f"{self.instruction.mnemonic} {end_of_block_command_operands_split[0]}, {hex(self.playground_jmp_addr_if_result_b)}"


    def write_hook(self, via_trampoline):
        """ via_trampoline is a boolean"""
        if not via_trampoline:
            self.write_direct_hook()
        else:
            self.write_trampoline_hook()
    

    def write_direct_hook(self):
        if self.trampoline_address is not None:
            print("Error!!! trampoline address is not none, yet you are asking for a direct hook. please configure this properly in FAMainHelper.py")
            return 
        if self.verbose:
            print(f"""
                    We want to do the following:
                    
                    1. replace the {self.instruction.mnemonic} command at {hex(self.instruction.address)} with barnching to playground at {hex(self.playground_start_address)}.
                    
                    2. create a split at the playground with the same condition - {self.instruction.mnemonic} {self.instruction.operands}, that either continues to {hex(self.playground_jmp_addr_if_result_a)} or jumps to {hex(self.playground_jmp_addr_if_result_b)}

                    3. if we continue, report the edge {hex(self.instruction.address)} to {hex(self.final_destination_result_a)}, and branch to {hex(self.final_destination_result_a)} when done.

                    4. if we jump, then report the edge {hex(self.instruction.address)} to {hex(self.final_destination_result_b)}, and branch to {hex(self.final_destination_result_b)} when done
                    """)

        # 1.
        jmp_command_a = create_commands_for_branch(self.instruction.address, self.playground_start_address)
        if self.verbose:
            print(f"Creating the first jump, branch from {hex(self.instruction.address)} to {hex(self.playground_start_address)}")
            print(f"Created the command: {jmp_command_a}")
        FAWriter.write_command(jmp_command_a, self.instruction.address, verbose=self.verbose)

        # 2.
        if self.verbose:
            print(f"creating new condition: {self.new_asm_command}")
        new_condition_bytes = create_command_from_str_with_pc(self.new_asm_command, self.playground_start_address)
        FAWriter.write_command(new_condition_bytes, self.playground_start_address)


        # let's fill nops before 3
        nop_command = create_command_from_str("nop")
        nops_amount = int((PLAYGROUND_GAP_SIZE / 4) - 1)

        nop_writer = FAWriter(self.playground_jmp_addr_if_result_a)
        for i in range(nops_amount):
            nop_writer.write_bytes(nop_command)

        nop_writer2 = FAWriter(self.playground_jmp_addr_if_result_b)
        for i in range(nops_amount):
            nop_writer2.write_bytes(nop_command)


        # write the jumps back: (3 & 4)
        jmp_back_a_command_address = self.playground_jmp_addr_if_result_b - 8
        branch_back_a = create_commands_for_branch(jmp_back_a_command_address, self.final_destination_result_a)
        FAWriter.write_command(branch_back_a, jmp_back_a_command_address)

        jmp_back_b_command_address = self.playground_jmp_addr_if_result_b + PLAYGROUND_GAP_SIZE - 8
        branch_back_b = create_commands_for_branch(jmp_back_b_command_address, self.final_destination_result_b)
        FAWriter.write_command(branch_back_b, jmp_back_b_command_address)

        # verify nops and jumps
        if self.verbose:
            print_disas(self.playground_start_address, 40)

        # reporting an edge (3 & 4)
        write_report_edge_code(self.playground_jmp_addr_if_result_a, (self.instruction.address, self.final_destination_result_a))
        write_report_edge_code(self.playground_jmp_addr_if_result_b, (self.instruction.address, self.final_destination_result_b))

        if self.verbose:
            print("Wrote report instructions. printing new code:")
            print_disas(self.playground_start_address, 40)



    def write_trampoline_hook(self):
        if self.trampoline_address is None:
            print("Error!!! trampoline address is none, yet you are asking for a trampoline hook. please configure this properly in FAMainHelper.py")
            return 
        if self.verbose:
            print(f"""
                    We want to do the following:
                    
                    1. replace the {self.instruction.mnemonic} command at {hex(self.instruction.address)} with barnching to trampoline address at {hex(self.trampoline_address)}
                    
                    2. Store the value of {self.tmp_register} for later reconstruction

                    3. Set the playground address to x16 as an absolute address of the current playground address (using load_imm64_to_reg) at {hex(self.playground_start_address)}

                    4. branch to {self.tmp_register}
                    
                    5. create a split at the playground with the same condition - {self.instruction.mnemonic} {self.instruction.operands}, that either continues to {hex(self.playground_jmp_addr_if_result_a)} or jumps to {hex(self.playground_jmp_addr_if_result_b)}

                    6. if we continue, report the edge {hex(self.instruction.address)} to {hex(self.final_destination_result_a)}, and first branch back to trampolie return at {hex(self.trampoline_return_addr_if_result_a)}, and then to {hex(self.final_destination_result_a)} when done.

                    7. if we jump, then report the edge {hex(self.instruction.address)} to {hex(self.final_destination_result_b)}, and first branch back to trampoline return at {hex(self.trampoline_return_addr_if_result_b)}, and then to {hex(self.final_destination_result_b)} when done.
                    
                    8. from trampoline result a return, restore {self.tmp_register} and return to final destination a 

                    9. from trampoline result b return, restore {self.tmp_register} and return to final destination b
                    
                    """)
            
            #1
            jmp_command_a = create_commands_for_branch(self.instruction.address, self.trampoline_address)
            if self.verbose:
                print(f"Creating the first jump, branch from {hex(self.instruction.address)} to {hex(self.trampoline_address)}")
                print(f"Created the command: {jmp_command_a}")
            FAWriter.write_command(jmp_command_a, self.instruction.address, verbose=self.verbose)

            # let's fill trampoline nops before 2
            nop_command = create_command_from_str("nop")
            nops_amount = int(3 * TRAMPOLINE_GAP_SIZE / 4) # the 3 is one for the intro and 2 more for each split result

            trampoline_nop_writer = FAWriter(self.trampoline_address)
            for i in range(nops_amount):
                trampoline_nop_writer.write_bytes(nop_command)
            

            #2
            if self.verbose:
                print(f"Writing commands for saving {self.tmp_register} on the stack so we can restore it upon return")
                print(f"This is writing two commands to {hex(self.trampoline_address)}")
            allocate_stack = "sub   sp, sp, #16"
            store_in_stack = f"str   {self.tmp_register}, [sp]"
            allocate_stack_bytes = create_command_from_str(allocate_stack)
            store_in_stack_bytes = create_command_from_str(store_in_stack)
            writer = FAWriter(self.trampoline_address)
            writer.write_bytes(allocate_stack_bytes)
            writer.write_bytes(store_in_stack_bytes)

            #3
            if self.verbose:
                print(f"Storing the playground start address ({hex(self.playground_start_address)}) in {self.tmp_register} for branching to absolute address")
            zero_x16 = f"mov {self.tmp_register}, xzr"
            zero_x16_bytes = create_command_from_str(zero_x16)
            branch_to_playground_start_bytes = load_imm64_to_reg(self.tmp_register, self.playground_start_address)
            writer.write_bytes(zero_x16_bytes)
            writer.write_bytes(branch_to_playground_start_bytes)

            #4
            if self.verbose:
                print(f"branching to current playground address: {hex(self.playground_start_address)}")
            branch_to_x16 = f"br {self.tmp_register}"
            branch_to_x16_bytes = create_command_from_str(branch_to_x16)
            writer.write_bytes(branch_to_x16_bytes)


            #5  write the condition at the top of the playground current segment
            if self.verbose:
                print(f"creating new condition: {self.new_asm_command} at the playground address: {hex(self.playground_start_address)}")
            new_condition_bytes = create_command_from_str_with_pc(self.new_asm_command, self.playground_start_address)
            FAWriter.write_command(new_condition_bytes, self.playground_start_address)

            # let's fill nops before 6
            nop_command = create_command_from_str("nop")
            nops_amount = int(PLAYGROUND_GAP_SIZE / 4)

            nop_writer = FAWriter(self.playground_jmp_addr_if_result_a)
            for i in range(nops_amount):
                nop_writer.write_bytes(nop_command)

            nop_writer2 = FAWriter(self.playground_jmp_addr_if_result_b)
            for i in range(nops_amount):
                nop_writer2.write_bytes(nop_command)


            #6 write the jumps back to the trampoline

            # common to both jumps
            zero_x16 = f"mov {self.tmp_register}, xzr"
            zero_x16_bytes = create_command_from_str(zero_x16)
            branch_to_x16 = f"br {self.tmp_register}"
            branch_to_x16_bytes = create_command_from_str(branch_to_x16)
            

            # first jump (a)
            jmp_back_a_command_address = self.playground_jmp_addr_if_result_b - 0x18
            if self.verbose:
                print(f"Writing the jump (a) from playground {hex(jmp_back_a_command_address)} to trampoline {hex(self.trampoline_return_addr_if_result_a)}")

            branch_back_to_trampoline_result_a = load_imm64_to_reg(self.tmp_register, self.trampoline_return_addr_if_result_a)

            writer = FAWriter(jmp_back_a_command_address)
            writer.write_bytes(zero_x16_bytes)
            writer.write_bytes(branch_back_to_trampoline_result_a)
            writer.write_bytes(branch_to_x16_bytes)
            
            # second jump (b)
            jmp_back_b_command_address = self.playground_jmp_addr_if_result_b + PLAYGROUND_GAP_SIZE - 0x18

            if self.verbose:
                print(f"Writing the jump (b) from playground {hex(jmp_back_b_command_address)} to trampoline {hex(self.trampoline_return_addr_if_result_b)}")

            branch_back_to_trampoline_result_b = load_imm64_to_reg(self.tmp_register, self.trampoline_return_addr_if_result_b)

            writer = FAWriter(jmp_back_b_command_address)
            writer.write_bytes(zero_x16_bytes)
            writer.write_bytes(branch_back_to_trampoline_result_b)
            writer.write_bytes(branch_to_x16_bytes)

            # reporting an edge (6 & 7)
            write_report_edge_code(self.playground_jmp_addr_if_result_a, (self.instruction.address, self.final_destination_result_a))
            write_report_edge_code(self.playground_jmp_addr_if_result_b, (self.instruction.address, self.final_destination_result_b))       
            

            # 8 & 9 write the trampoline result a back jump

            # comon to both jumps
            restore_x16 = f"ldr {self.tmp_register}, [sp]"
            restore_sp_value = "add sp, sp, #16"
            restore_x16_bytes = create_command_from_str(restore_x16)
            restore_sp_value_bytes = create_command_from_str(restore_sp_value)

            
            # this is return if (a)
            if self.verbose:
                print(f"Writing the trampoline return in case of result a. this will restore {self.tmp_register}, and jump from {hex(self.trampoline_return_addr_if_result_a)} to {hex(self.final_destination_result_a)}")
            
            writer = FAWriter(self.trampoline_return_addr_if_result_a)
            writer.write_bytes(restore_x16_bytes)
            writer.write_bytes(restore_sp_value_bytes)

            currentAddress = self.trampoline_return_addr_if_result_a + 0x8
            branch_back_a = create_commands_for_branch(currentAddress, self.final_destination_result_a)
            writer.write_bytes(branch_back_a)

            # this is return if (b)
            if self.verbose:
                print(f"Writing the trampoline return in case of result b. this will restore {self.tmp_register}, and jump from {hex(self.trampoline_return_addr_if_result_b)} to {hex(self.final_destination_result_b)}")
            
            writer = FAWriter(self.trampoline_return_addr_if_result_b)
            writer.write_bytes(restore_x16_bytes)
            writer.write_bytes(restore_sp_value_bytes)

            currentAddress = self.trampoline_return_addr_if_result_b + 0x8
            branch_back_b = create_commands_for_branch(currentAddress, self.final_destination_result_b)
            writer.write_bytes(branch_back_b)
