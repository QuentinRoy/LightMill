=================
Experiment Server
=================

This project is a python server that follows Caroline Appert's
`TouchStone <https://www.lri.fr/~appert/website/touchstone/touchstone.html>`_
experiment design platform files to guide experiment runs through a web interface and log their results.

Make it run!
------------

To make it run, you just have to do something like::

    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r expserver/requirements.txt
    $ cd expserver
    $ python run.py

The experiment described in `experiment.xml`:code: at the root folder will be automatically imported into the database
at server startup.