#!/bin/sh

SOURCE="${BASH_SOURCE[0]}"
while [ -h "$SOURCE" ]; do # resolve $SOURCE until the file is no longer a symlink
  DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
  SOURCE="$(readlink "$SOURCE")"
  [[ $SOURCE != /* ]] && SOURCE="$DIR/$SOURCE" # if $SOURCE was a relative symlink, we need to resolve it relative to the path where the symlink file was located
done

# Absolute path this script is in, thus /home/user/bin.
DIR="$( cd -P "$( dirname "$SOURCE" )" && pwd )"
# Argument list for the experiment server.
serverArgList=' '
# Argument list for python.
pyArgList=''
# Check if debug mode, else activate python optimization.
debug=false



# Idiomatic parameter and option handling in sh.
while test $# -gt 0
do
    case "$1" in
        --debug) debug=true
                 serverArgList+=" $1"
            ;;
        *) serverArgList+=" $1"
            ;;
    esac
    shift
done

if [ "$debug" = false ] ; then
    pyArgList+=" -O"
fi

source $DIR/venv/bin/activate && python $pyArgList $DIR/start.py $serverArgList
