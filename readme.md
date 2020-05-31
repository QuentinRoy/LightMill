# LightMill

_LightMill_ is a user experiment web server used to manage and log experiments running in browsers.
It uses [TouchStone](https://www.lri.fr/~appert/website/touchstone/touchstone.html)'s design files
and provides a web interface to monitor an ongoing experiment. The touchstone design platform
can be downloaded from [here](https://github.com/jdfekete/touchstone-platforms/tree/master/design-platform).

## Make it run!

```shell
./configure.sh
./start.sh
```

You need a python 3.7 interpreter and `virtualenv` installed. If
`virtualenv` is unfound, you can install it with `easy_install virtualenv`.
`virtualenv` ensures the project's dependencies are installed locally and
do not pollute your python global libraries.

You can then access the web interface from `localhost` on the
corresponding port.

The experiment described in `experiment.xml` at the root folder will be
automatically imported into the database at server startup (if not
already in). You can also specify another experiment design path with
the `--experiment-design` command line option.

## Build Your experiment

[`lightmill-runner`](https://github.com/QuentinRoy/lightmill-js/tree/master/packages/lightmill-runner) is a JavasCript library that is used to interface your experiment application with `LightMill`.

Additionally [`lightmill-app`](https://github.com/QuentinRoy/lightmill-js/tree/master/packages/lightmill-app) provides a set of standard views such as `blockInit` or `end` for you to use in your application.

## Grab the results!

The trial results can be downloaded from the bottom of the experiment page from web API.

Currently, the only way to export the event logs is by using the
`./export.sh` script (slow and hopefully deprecated soon).

## Locked run

To avoid concurrent update, client needs to acquire a lock to register
trial results for a run.
When a run is locked, it cannot be acquired again.

You can manually unlock a run by going on the run page from the web
interface and by clicking on the lock icon. This can be useful if a
client crashed and a new lock needs to be acquired to continue the
experiment. However, doing so will most likely result in an error for an
ongoing client.

The lock protection can be lifted using the `--unprotected-runs` command line argument.
This is useful during the development of experiment clients.
However this option allows a client to "steal" the run of another and thus, it is unsafe when
running the actual experiment and should never be used in production.

## Other options?

```shell
./start.sh --help
```

## Run with docker

A docker file is provided to create a docker image that can be used both to create
the server and grab the results.

### Creating the image

```sh
docker build -t lightmill .
```

### Starting the server

```sh
docker run \
  --mount source=lightmill,target=/data \
  -dp 5000:80 \
  --name lightmill_server \
  lightmill start.sh
```

Note: this is using the "lightmill" volume to store the data.
It is automatically managed by docker.

### Grab the results

```sh
docker run --mount source=lightmill,target=/data lightmill export.sh
docker cp lightmill_server:/data/export ./export
```

Note: the lightmill_server container must exist for this to work.

### Backup the database

```sh
docker cp lightmill:/data/experiments.db .
```

### Clear the data

Once the experiment is finished, you may want to remove the volume allocated by
docker to free up some space.

```sh
docker volume rm lightmill
```

## API

TODO
