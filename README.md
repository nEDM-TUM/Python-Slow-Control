Python-Slow-Control
===================

pynedm provides a python module for communicating with the slow control
database.

Currently, one can define functions that can be exported to the Web interface
and then executed in your program.

# Install/Upgrade:

```
[sudo] pip install [--upgrade] git+https://github.com/nEDM-TUM/Python-Slow-Control#egg=pynedm
```

or (for those installing without git on their systems)

```
[sudo] pip install [--upgrade] https://github.com/nEDM-TUM/Python-Slow-Control/tarball/master#egg=pynedm
```

# Example usage:

```python
import pynedm

_server = "http://localhost:5984/"
_un = "ausername"
_pw = "apassword"
_db = "name_of_database"

po = pynedm.ProcessObject(_server, _un, _pw, _db)

def do_work:
    """
      do some work, can also write a document to the db
    """
	# Note that the following function squelches errors unless you pass in
    # ignoreErrors = False
	# If is not critical that you write every single value to the db, then keep
	# the default behavior.  If it *is* critical to write the document, then
	# pass in ignoreErrors=False and put the call in a try: except:.
	po.write_document_to_db({ "type" : "data",
                                 "value" : { "myvar" : 0 } })
    ...

execute_dict = {
    "do_work_key" : do_work,
}

# listen for commands listed in execute_dict
o = pynedm.listen(execute_dict, _db
              username=_un, password=_pw, uri=_server)

# Wait until listening ends
o.wait()

```

The above will wait and listen for documents that look like:

```javascript
{
  // ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [] // optional
  // ...
}
```
to be inserted into the database.  As soon as it sees a document with a
valid key in "execute", it will run the associated function and return a
success message back to the inserted document.  In other words, the above
document will become:

```javascript
{
  // ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [], // optional
  "response" : {
    "content" : "a msg",
    "timestamp" : "a timestamp",
    "return" : "Value returned by function", # can be NULL
    "ok" : True # only present if everything went ok
  }
  // ...
}
```

Where the message will indicate if the command was successful.

Stopping:
	```pynedm.listening``` From the command line, one may also
type CTRL-C to nicely end the program.

Threading, etc:
	Note, it is possible to send multiple messages and have them be executed
"simultaneously". This means you should take care either in your function or
when writing to the database if your command is thread sensitive (i.e. only one
version should be running at a time).

Long functions:
	pynedm begins listenings for further messages as soon as it executes the
requested function.  This means it does not wait for the end of the function,
but it is important that the function returns a value relatively quickly so
that the web control doesn't time out.  There is an example of how to handle
this in:

examples/long_run_process.py

