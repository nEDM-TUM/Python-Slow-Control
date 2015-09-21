# Global to stop
import logging
import os
import json
from .fileutils import AttachmentFile
from .exception import CommandCollision, PynEDMException

_should_stop = False
def _log(*args):
    logging.info(*args)

def _exception(*args):
    logging.exception(*args)

class ProcessObject(object):
    def __init__(self, uri=None, username=None, password=None, adb=None, verbose=False, **kw):
        import cloudant as _ca
        self._currentInfo = {}
        acct = kw.get("acct", None)
        if acct is None:
            acct = _ca.Account(uri=uri)
            if username and password:
                res = acct.login(username, password)
                if res.status_code != 200:
                    raise PynEDMException("User credentials incorrect")
        self.isRunning = False
        self.verbose = verbose
        self.acct = acct
        self.db = adb

    def write_document_to_db(self, adoc, db=None, ignoreErrors=True):
        """
        Write a document to the database.
        """
        try:
          if db is None:
            db = self.acct[self.db]
          else:
            db = self.acct[db]
        except:
          raise PynEDMException("Cannot write while not listening")
        try:
          return db.design("nedm_default").post("_update/insert_with_timestamp",params=adoc).json()
        except Exception as e:
          if ignoreErrors:
            _log("Exception ({}) when posting doc({})".format(e,adoc))
            return {}
            pass
          else: raise

    def _attachment_path(self, docid, attachment_name, db=None):
        """
        Helper function to grab the attachment path
        """
        if db is None:
            db = self.db
        if db is None:
            raise PynEDMException("db must be defined")
        return '/'.join([self.acct.uri, '_attachments', db, docid, attachment_name])

    def delete_file(self, docid, attachment_name, db=None):
        """
        delete file associated with docid.

        Return json response from server.
        """
        delete_url = self._attachment_path(docid, attachment_name, db)
        return self.acct.delete(delete_url).json()

    def open_file(self, docid, attachment_name, db=None):
        """
		open file for reading, allows reading ranges of data. Example usage:

            o = ProcessObject(...)
            _fn = "temp.out"
            _doc = "no_exist"
            _db = "nedm%2Fhg_laser"

            x = o.open_file(_doc, _fn, db=_db)
            y = x.read(4)

            print len(y), y

            print x.read()
            x.seek(1)
            for i in x.iterate(10):
                print i
        """
        download_url = self._attachment_path(docid, attachment_name, db)
        return AttachmentFile(self.acct[download_url])


    def download_file(self, docid, attachment_name, db=None, chunk_size=100*1024, headers=None):
        """
		download file associated with docid, yields the data in chunks first
		data yielded is the total expected size, the rest is the data from the
        file.  Example usage:

            from clint.textui.progress import Bar as ProgressBar
            total_size = None
            x = process_object.download_file("docid", "attachment", "mydb")
            bar = ProgressBar(expected_size=x.next(), filled_char='=')
            total = 0
            with open("temp_file.out", "wb") as o:
                for ch in x:
                    total += len(ch)
                    bar.show(total)
                    o.write(ch)
                    o.flush()

        """
        download_url = self._attachment_path(docid, attachment_name, db)
        if headers is None: headers = {}
        r = self.acct.get(download_url, stream=True, headers=headers)
        yield int(r.headers['content-length'])
        for chunk in r.iter_content(chunk_size=chunk_size):
            if chunk: yield chunk

    def upload_file(self, file_or_name, docid, db=None,attachment_name=None,callback=None):
        """
        Upload file associated with a particular doc id

        file_or_name : full path to file or file-like object
        docid     : id of document
        db        : (*optional named*) name of database
        callback  : (*optional named*) upload callback, should be of form: func(size_read, total_size)
        attachment_name  : (*optional named*) name of attachment, otherwise name will be taken from file
        """
        actual_file = file_or_name
        if not hasattr(file_or_name, "read"):
            # Assume it's a file-like object
            if not attachment_name:
                attachment_name = os.path.basename(file_or_name)
            actual_file = open(file_or_name, "rb")
        elif not attachment_name:
            raise PynEDMException("Must include attachment name for file-like objects")

        # Get file size
        actual_file.seek(0, 2) 
        total_size = actual_file.tell()
        actual_file.seek(0) 

        post_to_url = self._attachment_path(docid, attachment_name, db)

        cookies = '; '.join(['='.join(x) for x in self.acct._session.cookies.items()])

        import pycurl
        from StringIO import StringIO



        class FileReader:
            def __init__(self, fp, callback = None):
                self.fp = fp
                self.total_read = 0
                self.cbck = callback
            def read_callback(self, size):
                x = self.fp.read(size)
                if x is not None:
                    self.total_read += len(x)
                    if self.cbck: self.cbck(self.total_read, total_size)
                return x

        c = pycurl.Curl()
        storage = StringIO()
        c.setopt(pycurl.URL, post_to_url)
        c.setopt(pycurl.PUT, 1)
        c.setopt(pycurl.READFUNCTION, FileReader(actual_file, callback).read_callback)
        c.setopt(pycurl.INFILESIZE, total_size)
        c.setopt(c.WRITEFUNCTION, storage.write)
        c.setopt(c.COOKIE, cookies)

        c.perform()
        c.close()
        content = storage.getvalue()
        try:
            return json.loads(content)
        except:
            return { "error" : True, "content" : content }


    def wait(self):
        """
        Wait until the current changes feed execution is complete.  Execution can
        be stopped also by calling stop_listening()
        """
        if "thread" not in self._currentInfo: return
        th = self._currentInfo["thread"]
        while th.isAlive():
          th.join(0.1)
          if should_stop():
            self.__remove_commands_doc()
        self.__remove_commands_doc()

    def __check_keys(self,docid):
        import json
        db = self.acct[self.db]
        r = db.design("execute_commands").view("export_commands").get(params=dict(group_level=1)).json()
        all_keys = dict([(x["key"],x["value"]) for x in r["rows"]])
        bad_keys = [k for k in all_keys if all_keys[k] > 1]
        if len(bad_keys) > 0:
            r = db.design("execute_commands").view("export_commands?reduce=false").post(
              params=dict(reduce=False),
              data=json.dumps(dict(keys=bad_keys))).json()
            url_to_use = db.uri_parts[0] + "://" + db.uri_parts[1] + "/_utils/document.html?" + db.uri_parts[2][1:] + "/"
            s = set([x["id"] for x in r["rows"] if (x["id"] != docid and x["key"] in bad_keys)])
            conflict_str = "\nKey conflicts:\n{}\n\ncheck the following documents:\n{}".format('\n'.join(bad_keys), '\n'.join(map(lambda x: url_to_use + x, s)))
            if len(s) == 1:
                conflict_str += """

You have tried to use command keys that are in use!
"""
            raise CommandCollision(conflict_str)

    def run(self, func_dic_copy, docid):
        if self.isRunning: return
        self.isRunning = True
        db = self.acct[self.db]
        from .listen import _watch_changes_feed
        import threading as _th
        self._currentInfo = {
          "doc_name": docid,
          "thread"  : _th.Thread(target=_watch_changes_feed, args=(db, func_dic_copy, self.verbose))
        }
        self.__check_keys(docid)

        self._currentInfo["thread"].daemon = True
        self._currentInfo["thread"].start()

    def stop_listening(self):
        self.__remove_commands_doc()

    def __remove_commands_doc(self):
        import requests as _req
        if not "doc_name" in self._currentInfo: return
        doc_name = self._currentInfo["doc_name"]
        db = self.acct[self.db]
        _log("Removing commands doc {}".format(doc_name))
        try:
            doc = db.document(doc_name)
            outp = doc.get().json()
            doc.delete(outp["_rev"]).raise_for_status()
        except _req.exceptions.ConnectionError:
            _log("Error removing document, did the server die?")
            pass
        except PynEDMException as e:
            _log("Unknown exception ({})".format(e))
            pass
        del self._currentInfo["doc_name"]

    def __del__(self):
        stop_listening(True)
        self.wait()

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

def stop_listening(stop=True):
    """
    Request the listening to stop.  Code blocked on wait() will proceed.
    """
    global _should_stop
    if not type(stop) == type(True):
      raise PynEDMException("Expected bool, received (%s)" % type(stop))
    if stop and not _should_stop: _log("Stop Requested")
    _should_stop = stop

def should_stop():
    return _should_stop

def listen(function_dict,database,username=None,
           password=None, uri="http://localhost:5984", verbose=False,
           **kw
           ):
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
       actually references to functions.
    """

    stop_listening(False)
    # Handle interruption signals
    def _builtin_sighandler(sig, frame):
        _log("Handler called {}, {}".format(sig, frame))
        stop_listening()
    import signal
    try:
        signal.signal(signal.SIGINT, _builtin_sighandler)
    except ValueError:
        _log("Not handling signals")

    # Now we start with the listen function
    import inspect as _ins
    import pydoc as _pyd
    import uuid as _uuid

    # Get the database information
    process_object = ProcessObject(uri, username, password, database)

    # build_dictionary
    document = { "uuid" : _uuid.getnode(),
                 "type" : "export_commands",
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

    r = process_object.write_document_to_db(document)
    if not "ok" in r:
        raise PynEDMException("Error seen: {}".format(r))

    process_object.run(func_dic_copy, r["id"])
    return process_object
