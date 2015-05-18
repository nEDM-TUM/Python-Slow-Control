# Reset any stop listening flags
import time as _ti
import requests as _req
import httplib as _http
from .utils import should_stop, _log

def _watch_changes_feed(adb, fd, verbose):
    """
    _watch_changes_feed is a hidden function that performs all the work
    watching the change feed
    """

    import threading as _th

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


    def _fire_single_thread(des, fd, label, args):
        try:
            retVal = fd[label](*args)
            des.put(upd, params=_get_response("'%s' success" % label, retVal, True))
        except Exception, e:
            des.put(upd, params=_get_response("Exception: '%s'" % repr(e)))
            pass

    def _heartbeat_thread(thedb):
        des = thedb.design("nedm_default")
        adoc = { "type" : "heartbeat" }
        now = _ti.time()
        while not should_stop():
            if _ti.time() - now >= 10:
                now = _ti.time()
                try:
                    des.post("_update/insert_with_timestamp/heartbeat", params=adoc)
                except:
                    des = thedb.design("nedm_default")
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
                                              heartbeat=2000,
                                              since='now',
                                              include_docs=True,
                                              only_commands=fd.keys(),
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
        except (_req.exceptions.ChunkedEncodingError, _http.IncompleteRead) as e:
            # Sometimes the changes feeds "stop" listening, so we can try restarting the feed
            _log("Ignoring exception {}".format(e))
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

