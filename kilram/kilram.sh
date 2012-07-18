#!/usr/bin/env bash

wdir="$(dirname $0)"

function get_cpu_usage {
  local pid=$1
  echo $(ps h -p $pid -o pcpu | sed 's/ \+//g; s/\..*//;')
}

function check_pid_alive {
  local pid=$1
  ps h -p $pid &> /dev/null
}

while sleep 5; do
  if [ -z "$kilram_pid" ] || ! check_pid_alive $kilram_pid; then
    high_cpu_time=0
    sudo -u kilram $wdir/kilram &
    kilram_pid=$!
    echo "Kilram spawned [$kilram_pid]" >> /tmp/kilram.log
  else
    if [ "$(get_cpu_usage $kilram_pid)" -gt 40 ]; then
      ((high_cpu_time++))
      echo "High CPU usage detected $high_cpu_time" >> /tmp/kilram.log
    fi
    if [ $high_cpu_time -gt 10 ]; then
      kill $kilram_pid
      kilram_pid=
      echo "Monitor killed Kilram due to high CPU usage" >> /tmp/kilram.log
    fi
  fi
done
