#!/usr/bin/env bash
function start () {
    #source .venv/bin/activate
    gunicorn -b 0.0.0.0:5000 --reload app.main:application --timeout 30 --workers=$WORKER_COUNT --max-requests 500 --max-requests-jitter 200
}

function stop () {
    ps -ef | grep gunicorn | awk '{print $2}' | xargs kill -9
}


case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    *)
    echo "Usage: run.sh {start|stop}"
    exit 1
esac
