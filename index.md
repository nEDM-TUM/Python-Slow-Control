---
layout: basic
title: pynedm
---

pynedm
======

`pynedm` provides a python module for communicating with the slow control
database.

Currently, one can define functions that can be exported to the Web interface
and then executed in your program.

For the API reference see [here](api/html).

## Contents:

* [Install](#installupgrade)
* [Example usage](#example-usage)
* [Document attachments](#dealing-with-files-on-documents)

## Install/Upgrade:

{% highlight bash %}
[sudo] pip install [--upgrade] https://github.com/nEDM-TUM/Python-Slow-Control/tarball/master#egg=pynedm
{% endhighlight %} 

#### Notes for the `pycurl` dependency

`pynedm` depends on [`pycurl`](http://pycurl.sourceforge.net/), but sometimes pip has some issues installing on Mac OS X because of 32/64-bit issues.  (For more information see [here](http://stackoverflow.com/questions/18752405/cannot-install-pycurl-on-mac-os-x-get-errors-1-and-2).)

To get around this, install `pycurl` separately with the command:

{% highlight bash %}
sudo env ARCHFLAGS="-arch x86_64" pip install pycurl
{% endhighlight %} 

## Example usage:

{% highlight python %}
import pynedm

_server = "http://localhost:5984/"
_un = "ausername"
_pw = "apassword"
_db = "name_of_database"

po = pynedm.ProcessObject(uri=_server, username=_un, password=_pw, adb=_db)

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

# execute_dict can also be tuples of functions and JSON-parsable objects, e.g.:
# execute_dict = {
#   "do_work_key" : (do_work, "this is a function that does blah)
# }
#
# execute_dict = {
#  "do_work_key" : (do_work, { "extrainfo" : 123, "help_msg" : "Hi" }))
# }

# listen for commands listed in execute_dict
o = pynedm.listen(execute_dict, _db
              username=_un, password=_pw, uri=_server)

# Wait until listening ends
o.wait()
{% endhighlight %} 

The above will wait and listen for documents that look like:

{% highlight javascript %}
{
  // ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [] // optional
  // ...
}
{% endhighlight %} 

to be inserted into the database.  As soon as it sees a document with a
valid key in "execute", it will run the associated function and return a
success message back to the inserted document.  In other words, the above
document will become:

{% highlight javascript %}
{
  // ...
  "type" : "command",
  "execute" : "do_work_key",
  "arguments" : [], // optional
  "response" : {
    "content" : "a msg",
    "timestamp" : "a timestamp",
    "return" : "Value returned by function", // can be NULL
    "ok" : true // only present if everything went ok
  }
  // ...
}
{% endhighlight %} 

Where the message will indicate if the command was successful.

Stopping:
From the command line, one may also type `CTRL-C` to nicely end the program.

###In the database

Calling `pynedm.listen` inserts a document into the database of type `"export_commands"`.
The content of this document depends upon the what was passed into `listen`:

{% highlight javascript %}
{
  // ...
  "type" : "export_commands",
  "uuid" : "uuidofprogram", // defined by pynedm
  "keys" : {
      "do_work_key" : {
          "Info" : "this is the help string" // This is either the pydoc help string,
                                             // or the second object in the tuple passed in to listen
      },
      "other_work_key" : {
          "Info" : { 
            "extrainfo" : 123,
            "help_msg" : "this is the help string" // This is interpreted as the help string
                                                   // Other info here way be interpreted, e.g. by the web interface.
          }
      }      
  }
  // ...
}
{% endhighlight %} 


###Threading, etc.
Note, it is possible to send multiple messages and have them be executed
"simultaneously". This means you should take care either in your function or
when writing to the database if your command is thread sensitive (i.e. only one
version should be running at a time).

###Long functions
`pynedm` begins listenings for further messages as soon as it executes the
requested function.  This means it does not wait for the end of the function,
but it is important that the function returns a value relatively quickly so
that the web control doesn't time out.  There is an example of how to handle
this in:

examples/long_run_process.py

## Dealing with files on documents

[`pynedm.ProcessObject`](api/html/utils.html#pynedm.utils.ProcessObject) has
functions for dealing with files associated with documents in the database that
are being served using the [FileServer]({{ site.url }}/FileServer-Docker).
Example usages are given:

### Uploading

{% highlight python %}
import pynedm
from clint.textui.progress import Bar as ProgressBar
import json

o = pynedm.ProcessObject(uri="http://server",
  username="username",
  password="password") 

bar = None
def callback(read, total):
    global bar
    if bar is None:
        bar = ProgressBar(expected_size=total, filled_char='=')
    bar.show(read)

_fn = "temp.out"
_doc = "no_exist"
_db = "nedm%2Fhg_laser"

uploading = o.upload_file(_fn, _doc, db=_db, callback=callback)
# During run, outputs progress bar e.g.: 
#
# [================================] 20971520/20971520 - 00:00:00

print("\n{}".format(json.dumps(uploading, indent=4)))
# Outputs:
#
# {
#    "ok": true, 
#    "attachments": {
#        "temp.out": {
#            "size": 20971520, 
#            "ondiskname": "temp.out", 
#            "time": {
#                "atime": 1438354911.5317702, 
#                "ctime": 1438354912.698768, 
#                "crtime": 1438354912.698768, 
#                "mtime": 1438354912.691768
#            }
#        }
#    }, 
#    "id": "no_exist"
# }
{% endhighlight %} 
### Downloading 

{% highlight python %}
x = o.download_file(_doc, _fn, db=_db)
bar = ProgressBar(expected_size=x.next(), filled_char='=')
total = 0
for i in x:
    total += len(i)
    bar.show(total)
# Outputs progress bar, e.g.:
#
# [================================] 20971520/20971520 - 00:00:00
# 
print("\n")
{% endhighlight %} 

### Open as file-like object

{% highlight python %}
x = o.open_file(_doc, _fn, db=_db)
y = x.read(4)

print len(y), y

print x.read()
x.seek(1)
for i in x.iterate(10):
    print i
{% endhighlight %} 

### Delete file  

{% highlight python %}
print(json.dumps(o.delete_file(_doc, _fn, db=_db), indent=4))
# Outputs remaining attachments:
#
# {
#    "ok": true, 
#    "attachments": {}, 
#    "id": "no_exist"
# }
{% endhighlight %} 

