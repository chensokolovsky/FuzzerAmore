import lldb
import time
import lldb_py_conf  # <- generated dynamically by generate_lldbinit

def __lldb_init_module(debugger, _):
    print("lldb py init started")
    command = "platform select remote-ios"
    print(f"will run lldb command: {command}")
    debugger.HandleCommand(command)


    target = debugger.CreateTarget("")
    error = lldb.SBError()
    process = target.ConnectRemote(
        debugger.GetListener(),
        lldb_py_conf.connect_info,
        None,
        error
    )

    if not error.Success():
        print("Connection failed:", error)
        return

    print("Connected to remote platform.")


    debugger.HandleCommand(f"process attach -p {lldb_py_conf.pid}")
    debugger.HandleCommand(f"command script import {lldb_py_conf.main_script}")