Python-Slow-Control
===================

pynedm provides a python module for communicating with the slow control
database.

Currently, one can define functions that can be exported to the Web interface
and then executed in your program.  

# Install:

```
[sudo] pip install git+https://github.com/nEDM-TUM/Python-Slow-Control#egg=pynedm
```

# Example usage:

```python
import pynedm

def do_work:
    ...

execute_dict = {
    "do_work_key" : do_work,
}
pynedm.listen(execute_dict, "name_of_database", 
              username="un", password="pw", uri="http://raid.nedm1:5984")  

pynedm.wait()

```

The above will wait and listen for documents that look like: 

```json 
{
  ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [] # optional
  ...
}
```
to be inserted into the database.  As soon as it sees a document with a
valid key in "execute", it will run the associated function and return a
success message back to the inserted document.  In other words, the above
document will become:

```json 
{
  ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [], # optional
  "response" : {
    "content" : "a msg",
    "timestamp" : "a timestamp",
    "return" : "Value returned by function", # can be NULL
    "ok" : True # only present if everything went ok
  }
  ...
}
```

Where the message will indicate if the command was successful.

Stopping:
	```pynedm.listening``` automatically adds a function "stop" to the set of
functions it is listening for.  This means a document with an execute "stop"
field will request the program to end.  From the command line, one may also
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

