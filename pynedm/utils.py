# Global to stop
_should_stop = False
_currentThread = None
_currentInfo = {}

def _log(*args):
    print str(*args)

def start_process(func, *args, **kwargs):
    import Queue as _q
    import threading as _th
    def wrap_f(q, *args, **kwargs):
        ret = func(*args, **kwargs)
        q.put(ret)

    q = _q.Queue()
    t = _th.Thread(target=wrap_f, args=(q,)+args, kwargs=kwargs)
    t.start()
    t.result = q
    return t

def wait():
    """
    Wait until the current changes feed execution is complete.  Execution can
    be stopped also by calling stop_listening()
    """
    if not _currentThread: return
    while _currentThread.isAlive(): _currentThread.join(0.1)

def write_document_to_db(adoc):
    try:
      db = _currentInfo['db']
    except:
      raise Exception("Cannot write while not listening")
    db.design("nedm_default").post("_update/insert_with_timestamp",params=adoc)


def stop_listening(stop=True):
    """
    Request the listening to stop.  Code blocked on wait() will proceed.
    """
    global _should_stop
    if stop: _log("Stop Requested")
    _should_stop = stop

def should_stop():
    return _should_stop

def listen(function_dict,database,username=None,
           password=None, uri="http://localhost:5984", verbose=False,
           force=False):
    """
     function_dict should look like the following:

       adict = {
          "func_name1" : func1,
          "func_name2" : func2,
       }

       *or*, if explicitly passing in documentation strings

       adict = {
          "func_name1" : (func1, "my doc string"),
          "func_name2" : (func2, "my doc string for func2")
       }

       where of course the names can be more creative and func1/2 should be
       actually references to functions.  A special key "stop" will be inserted
       to ensure that the changes feed listening may be stopped by documents in
       the DB.
    """

    # Reset any stop listening flags
    import time as _ti
    import requests as _req
    stop_listening(False)
    def _get_response(msg, retVal=None, ok = False):
        """
         _get_response returns a dictionary with a msg and a timestamp for
         insertion into the db
        """
        ad = { "response" : {
           "content" : msg,
           "timestamp" : _ti.strftime("%a, %d %b %Y %H:%M:%S +0000", _ti.gmtime()),
           "return" : retVal
          }
        }
        if ok: ad["response"]["ok"] = True
        return ad

    def _watch_changes_feed(adb, fd):
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

        def _heartbeat_thread(adb):
            des = adb.design("nedm_default")
            adoc = { "type" : "heartbeat" }
            now = _ti.time()
            while not should_stop():
                if _ti.time() - now >= 10:
                    now = _ti.time()
                    try:
                        des.post("_update/insert_with_timestamp/heartbeat", params=adoc)
                    except:
                        des = adb.design("nedm_default")
                _ti.sleep(0.1)

        all_threads = []

        des = adb.design("nedm_default")
        # Start Heartbeat thread
        heartbeat = _th.Thread(target=_heartbeat_thread, args=(adb,))
        heartbeat.start()
        all_threads.append(heartbeat)
        ####

        connection_error = 0
        if verbose: _log("Waiting for command...")
        while 1:
            try:
                # Get changes feed and begin thread
                changes = adb.changes(params=dict(feed='continuous',
                                                  heartbeat=5000,
                                                  since='now',
                                                  include_docs=True,
                                                  filter="execute_commands/execute_commands"),
                                    emit_heartbeats=True
                                   )
                for line in changes:
                    if line is None and should_stop(): break
                    if line is None: continue
                    try:
                        doc = line["doc"]

                        upd = "_update/insert_with_timestamp/" + line["id"]

                        label = doc["execute"]
                        args = doc.get("arguments", [])
                        if verbose: _log("    command (%s) received" % label)

                        if type(args) != type([]):
                            raise Exception("'arguments' field must be a list")

                        new_th = _th.Thread(target=_fire_single_thread, args=(des, fd, label, args))
                        new_th.start()
                        all_threads.append(new_th)
                    except Exception, e:
                        des.put(upd, params=_get_response("Exception: '%s'" % repr(e)))
                        pass
                    if verbose: _log("Waiting for next command...")
                break
            except _req.exceptions.ChunkedEncodingError:
                # Sometimes the changes feeds "stop" listening, so we can try restarting the feed
                pass
            except _req.exceptions.ConnectionError:
                if connection_error >= 4:
                  _log("Seen too many connection errors, exiting")
                  break
                connection_error += 1
                _ti.sleep(1)
                pass

        if not should_stop():
            stop_listening()

        for th in all_threads:
            while th.isAlive(): th.join(0.1)

    # Handle interruption signals
    def _builtin_sighandler(sig, frame):
        stop_listening()
    import signal
    try:
        signal.signal(signal.SIGINT, _builtin_sighandler)
    except ValueError:
        _log("Not handling signals")

    # Now we start with the listen function
    global _currentThread, _currentInfo
    import cloudant as _ca
    import threading as _th
    import inspect as _ins
    import pydoc as _pyd
    import atexit as _ate
    import uuid as _uuid

    # Get the database information
    acct = _ca.Account(uri=uri)
    if username and password:
        res = acct.login(username, password)
        assert res.status_code == 200
    db = acct[database]
    _currentInfo['db'] = db
    _currentInfo['acct'] = acct

    # Introduce stop command
    function_dict["stop"] = stop_listening
    # build_dictionary
    document = { "_id" : "commands",
                 "uuid" : _uuid.getnode(),
                 "keys" : {} }

    # Copy function dictionary
    func_dic_copy = function_dict.copy()
    for k in function_dict:
        o = function_dict[k]
        exp_dic = {}
        if _ins.isfunction(o):
            # If we just have a function, use the doc string
            exp_dic = dict(Info=_pyd.plain(_pyd.text.document(o, k)))
        else:
            exp_dic = dict(Info=o[1])
            func_dic_copy[k] = o[0]
        document["keys"][k] = exp_dic


    if verbose:
        _log("Tracking the following commands: \n" + '\n   '.join(function_dict.keys()))

    r = db.get("commands")
    des = db.design("nedm_default")

    func = des.post
    location = "_update/insert_with_timestamp"
    outp = r.json()
    if "error" not in outp:
        msg = """
**********************************
'commands' document already exists.
"""
        if _uuid.getnode() != outp.get("uuid"):
            msg += """    uuid (%s) does not match this uuid (%s).
    Ensure no other program is running on another machine!""" % (str(outp.get("uuid")), str(_uuid.getnode()))
        else:
            msg += """    Ensure no other program is running on this machine"""
        msg += """
**********************************
"""
        _log(msg)
        if not force:
            _log("""
**********************************
Call 'listen' with 'force=True' to force removal of 'commands' document.
**********************************
""")
            raise Exception("'commands' document present")
        func = des.put
        location += "/commands"
        del document["_id"]

    r = func(location,params=document)
    assert("ok" in r.json())

    def remove_commands_doc_at_exit():
        try:
            doc = db.document("commands")
            outp = doc.get().json()
            doc.delete(outp["_rev"]).raise_for_status()
        except _req.exceptions.ConnectionError:
            _log("Error removing document, did the server die?")
            pass


    _ate.register(remove_commands_doc_at_exit)

    _currentThread = _th.Thread(target=_watch_changes_feed, args=(db, func_dic_copy))
    _currentThread.start()


