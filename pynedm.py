__all__ = [ "wait", "stop_listening", "listen", "should_stop" ]

# Global to stop 
_should_stop = False
_currentThread = None

def wait():
    """
    Wait until the current changes feed execution is complete.  Execution can
    be stopped also by calling stop_listening() 
    """
    if not _currentThread: return
    while _currentThread.isAlive(): _currentThread.join(0.5)


def stop_listening():
    """
    Request the listening to stop.  Code blocked on wait() will proceed.
    """
    global _should_stop
    print "Stop Requested"
    _should_stop = True

def should_stop():
    return _should_stop

def listen(function_dict,database,username=None,
           password=None, uri="http://localhost:5984", verbose=False): 
    """
     function_dict should look like the following:

       adict = {
          "func_name1" : func1,
          "func_name2" : func2,
       }

       where of course the names can be more creative and func1/2 should be
       actually references to functions.  A special key "stop" will be inserted
       to ensure that the changes feed listening may be stopped by documents in
       the DB. 
    """
 
    def _get_response(msg, retVal=None, ok = False):
        """
         _get_response returns a dictionary with a msg and a timestamp for
         insertion into the db 
        """
        import time as _ti 
        ad = { "response" : {
           "content" : msg,
           "timestamp" : _ti.strftime("%a, %d %b %Y %H:%M:%S +0000", _ti.gmtime()),
           "return" : retVal
          }
        }
        if ok: ad["response"]["ok"] = True
        return ad
 
    def _watch_changes_feed(adb, changes, fd):
        """
	_watch_changes_feed is a hidden function that performs all the work
        watching the change feed 
        """
   
        import threading as _th
        def _fire_single_thread(des, fd, label, args):
            try:
                retVal = fd[label](*args)
                des.put(upd, params=_get_response("'%s' success" % label, retVal, True))
            except Exception, e:
                des.put(upd, params=_get_response("Exception: '%s'" % repr(e)))
                pass

        all_threads = []
        des = adb.design("nedm_default")
        if verbose: print "Waiting for command..."
        for line in changes: 
            if line is None and should_stop(): break
            if line is None: continue 
            try: 
                doc = adb.get(line["id"]).json()
                
                upd = "_update/insert_with_timestamp/" + line["id"]
                
                label = doc["execute"]
                args = doc.get("arguments", [])
                if verbose: print "    command (%s) received" % label
                
                if type(args) != type([]):
                    raise Exception("'arguments' field must be a list")

                new_th = _th.Thread(target=_fire_single_thread, args=(des, fd, label, args))
                new_th.start()
                all_threads.append(new_th)
            except Exception, e:
                des.put(upd, params=_get_response("Exception: '%s'" % repr(e)))
                pass
            if verbose: print "Waiting for command..."

        for th in all_threads:
            while th.isAlive(): th.join(0.1)

    # Handle interruption signals
    def _builtin_sighandler(sig, frame):
        stop_listening()
    import signal
    signal.signal(signal.SIGINT, _builtin_sighandler)

    # Now we start with the listen function
    global _currentThread
    import cloudant as _ca
    import threading as _th

    # Get the database information
    acct = _ca.Account(uri=uri)
    if username and password:
        res = acct.login(username, password)
        assert res.status_code == 200
    db = acct[database]

    # Introduce stop command
    function_dict["stop"] = stop_listening

    # build_dictionary 
    document = { "_id" : "commands", 
                 "keys" : dict([(k,"") for k in function_dict.keys()]) } 
  
    if verbose:
        print "Tracking the following commands: \n" + '\n   '.join(function_dict.keys())

    r = db.get("commands") 
    des = db.design("nedm_default")

    func = des.post
    location = "_update/insert_with_timestamp"
    if "error" not in r.json():
        func = des.put
        location += "/commands"
        del document["_id"]

    r = func(location,params=document)
    assert("ok" in r.json())
    
    # Get changes feed and begin thread
    change = db.changes(params=dict(feed='continuous',
                                    heartbeat=5000,
                                    since='now',
                                    filter="execute_commands/execute_commands"),
                        emit_heartbeats=True
                       )
    _currentThread = _th.Thread(target=_watch_changes_feed, args=(db, change, function_dict))
    _currentThread.start()


