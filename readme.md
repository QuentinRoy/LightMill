# Experiment Server

*XPServer* is a user experiment server used to manage and log experiment runs.
It uses [TouchStone](https://www.lri.fr/~appert/website/touchstone/touchstone.html)'s design files
and provides a web interface to monitor an ongoing experiment.

## Make it run!


```shell
./configure.sh
./run-server.sh
```

You need a python 2.7 interpreter and `virtualenv` installed. If
`virtualenv` is unfound, you can install it with
`easy_install virtualenv`.

You can then access the web interface from `localhost` on the
corresponding port.

## Grab the results!

```shell
./export.sh
```

The results will be exported in the export folder.

The experiment described in experiment.xml at the root folder will be
automatically imported into the database at server startup (if not
already in).

## Locked run

To avoid concurrent update, client needs to acquire a lock to register
trial results for a run.

You can manually unlock a run by going on the run page from the web
interface and by clicking on the lock icon. This can be useful if a
client crashed and a new lock need to be acquire to continue the
experiment. However, doing so will most likely result in an error for an
ongoing client.
