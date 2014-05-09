import pynedm

_my_process = None
_should_stop = False

def long_function(*args):
    """
    Simulated a long function, for example a measurement process
    """
    import time
    i = 0
    while not _should_stop:    
        print i, args 
        time.sleep(1)
        i += 1
    return i
        

def start_process(*args):
    """
    Start the long process
    """
    global _my_process
    if _my_process is not None:    
        raise Exception("Process already running!")

    _my_process = pynedm.start_process(long_function, *args)
    return True

def stop_process():
    """
    Stop the long process and return the value
    """ 
    global _should_stop, _my_process
    if _my_process is None:
        raise Exception("Process not running!")
    _should_stop = True
    return _my_process.result.get()


# The following is simply to simulate the submission of commands from an
# external location
def command_process(url,un,pw,db):
    """
    This simply simulates the submission of commands,
    while is normally performed by a separate script
    """
    import cloudant
    import time
    # Authentication
    acct = cloudant.Account(uri=url)
    res = acct.login(un, pw)
    assert res.status_code == 200
    
    # Grab the correct database
    db = acct[db]
    des = db.design("nedm_default")
    
    # Define the document 
    adoc = {
            "type" : "command", 
            "execute" : "start_process", 
            "arguments" : ["I got sent"]
           } 
    # Push to the database
    # Start the process
    r = des.post("_update/insert_with_timestamp", params=adoc)
    print "Command: ", r.json()
    
    del adoc["arguments"]
    time.sleep(5)

    # Stop the process
    adoc["execute"] = "stop_process"
    r = des.post("_update/insert_with_timestamp", params=adoc)
    print "Command: ", r.json()

    time.sleep(1)

    # Stop the program 
    adoc["execute"] = "stop"
    r = des.post("_update/insert_with_timestamp", params=adoc)
    print "Command: ", r.json()


if __name__ == '__main__':
    un = "username"
    pw = "password"
    db = "test"
    pynedm.listen({ "start_process" : start_process,  "stop_process" : stop_process }, db,
           username=un, password=pw, verbose=True)
    import threading
    # Start control (normally run on another machine)
    t = threading.Thread(target=command_process, args=("http://127.0.0.1:5984", un, pw, db))
    t.start()
    #######

    pynedm.wait()

    t.join()
