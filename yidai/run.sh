#!/bin/bash

#BASE_PATH=$(cd `dirname $0`;pwd)
#echo "base_path is $BASE_PATH"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
echo $DIR

python $DIR/checkValid.py  > $DIR/out.log  2>&1  &

