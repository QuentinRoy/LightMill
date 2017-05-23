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

----------------
Locked run issue
----------------

To avoid concurrent update, when an experiment run is being used, it is automatically locked so that only one client can modify it. Most of the time, run will automatically unlock when the client disconnects. However, it can happen that the client is 'killed' without the possibility to warn the server (in particular on mobile devices), and thus the run remains locked.

You can manually unlock a run by going on the run page from the web interface and add :code:`force_unlock` after the node id – e.g. http://localhost:5000/run/myxp/S0/force_unlock.

One day I'll add a button for that.