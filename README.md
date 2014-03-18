Python-Slow-Control
===================

pynedm provides a python module for communicating with the slow control
database.

Currently, one can define functions that can be exported to the Web interface
and then executed in your program.  

Example usage:

```python
import pynedm

def do_work:
    ...

execute_dict = {
    "do_work" : "",
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
  "execute" : "do_work",
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
  "execute" : "do_work",
  "arguments" : [] # optional
  "response" : {
    "msg" : "a msg",
    "timestamp" : "a timestamp"
  }
  ...
}
```

Where the message will indicate if the command was successful.


