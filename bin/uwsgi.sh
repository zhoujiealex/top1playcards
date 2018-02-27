#!/bin/bash
# chkconfig:   - 85 15
#
# uWSGI init Script - This script starts and stops python web server from a ini configuration.
#
# processname: uwsgi
# description: uWSGI is a program to run applications adhering to the
#              Web Server Gateway Interface.
#              Used to run python and wsgi web applciations.
# Author: karl(i@karlzhou.com)


# Source function library.
. /etc/rc.d/init.d/functions

# Source networking configuration.
. /etc/sysconfig/network

# Check that networking is up.
[ "$NETWORKING" = "no" ] && exit 0

# Vars
###########################
APP_DIR="//home/playcard/top1playcards"
PID_FILE="$APP_DIR/pid/clp.pid"
UWSGI_INI="$APP_DIR/conf/uwsgi_with_http.ini"

PROG="/usr/local/bin/uwsgi"
DESC=uWSGI
DAEMON_OPTS="--no-orphans --ini $UWSGI_INI" # Change this if needed!
lockfile=/var/lock/subsys/uwsgi

# Exit if the package is not installed
[ -x "$PROG" ] || { echo "Error: missing $PROG"; exit 0; }

# Exit if configuration ini doesn't existed
[ -f "$UWSGI_INI" ] || { echo "Error: missing configuration $UWSGI_INI"; exit 0; }

start () {
  echo -n "Starting $DESC: "
  daemon --pidfile="$PID_FILE" $PROG $DAEMON_OPTS
  retval=$?
  echo
  [ $retval -eq 0 ] && touch $lockfile
  return $retval
}

stop () {
  echo -n "Stopping $DESC: "
  killproc $PROG
  retval=$?
  echo
  [ $retval -eq 0 ] && rm -f $lockfile
  return $retval
}

reload () {
echo "Reloading $NAME"
  killproc $PROG -HUP
  RETVAL=$?
  echo
}

restart () {
    stop
    start
}

force-reload () {
    restart
}

rh_status () {
  status $PROG
}

rh_status_q() {
  rh_status >/dev/null 2>&1
}

case "$1" in
  start)
    if ! pidof $PROG >/dev/null; then
        rh_status_q && exit 0
        $1
    else
        echo -e "\n$DESC is already started...\n"
    fi
 ;;
  stop)
    if pidof $PROG >/dev/null; then
        rh_status_q || exit 0
        $1
    else
        echo -e "\n$DESC can not be stoped because its not running...\n"
    fi
    ;;
  restart|force-reload)
    $1
    ;;
  reload)
    rh_status_q || exit 7
    $1
    ;;
  status)
    rh_status
    ;;
  *)
    echo "Usage: $0 {start|stop|restart|reload|force-reload|status}" >&2
    exit 2
    ;;
esac
exit 0
