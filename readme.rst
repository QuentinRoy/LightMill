=================
Experiment Server
=================

This project is a python server that follows Caroline Appert's
`TouchStone <https://www.lri.fr/~appert/website/touchstone/touchstone.html>`_
experiment design platform files to guide experiment runs through a web interface and log their results.

------------
Make it run!
------------

.. code:: shell

  ./configure.sh
  ./run-server.sh

You need a python 2.7 interpreter and *virtualenv* installed. If *virtualenv* is unfound, you can install it with :code:`easy_install virtualenv`.

You can then access the web interface from localhost on the corresponding port.

-----------------
Grab the results!
-----------------

.. code:: shell

  ./export.sh

The results will be exported in the export folder.


The experiment described in `experiment.xml`:code: at the root folder will be automatically imported into the database
at server startup (if not already in).


-------
Monitor
-------

A web interface is available by connecting to the server from a browser (by default, http://localhost:5000).

----------
Locked run
----------

To avoid concurrent update, client needs to acquire a run to register trial results.

You can manually unlock a run by going on the run page from the web interface and by clicking on the lock icon.
This can be useful if a client crashed and a new lock need to be acquire to continue the experiment.
However, doing so will most likely result in an error for an ongoing client.
