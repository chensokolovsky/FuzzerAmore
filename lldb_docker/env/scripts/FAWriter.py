import lldb

class FAWriter:
    """
    Class for writing a sequence of commands into memory.
    The class maintains the current address as it writes
    """
    def __init__(self, initial_address):
        self.current_address = initial_address


    @staticmethod
    def write_command(from_bytes, to_mem_address, verbose=False):
        """
        Static method that writes an array of bytes to memory at the specified address
        This is used by the writer, but can also be used for ad-hoc writing which is not part as a sequence of commands
        """
        if verbose:
            print(f"Trying to write bytes {from_bytes} to mem: {to_mem_address}")
        target = lldb.debugger.GetSelectedTarget()
        process = target.GetProcess()
        error = lldb.SBError()
        written = process.WriteMemory(to_mem_address, bytes(from_bytes), error)
        if error.Success():
            if verbose:
                print(f"Wrote {written} bytes to {hex(to_mem_address)}")
                return 0
        else:
            print("Error!  Hook writing failed:", error.GetCString())
            return -1
            

    def write_bytes(self, b_arr):
        """
        Expects a list of bytes to write to the current location. should be multiple of 4. example: [0xaa, 0xbb, 0xcc, 0xdd]
        This will write and advance the current address
        """
        if len(b_arr) % 4 != 0:
            print("Error!!!!!! bytes array for writing must be multiple of 4")
        for k in  range(int(len(b_arr)/ 4)):
            i0 = k*4
            i1 = (k+1)*4
            FAWriter.write_command(b_arr[i0:i1], self.current_address)
            self.current_address += 4

            
