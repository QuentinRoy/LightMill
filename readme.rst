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

You can then access the web interface from localhost on the corresponding port.

-----------------
Grab the results!
-----------------

.. code:: shell

  ./export.sh

The results will be exported in the export folder.


The experiment described in `experiment.xml`:code: at the root folder will be automatically imported into the database
at server startup (if not already in).