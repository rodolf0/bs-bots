#!/usr/bin/env bash

function setup_env {
  wdir=$(dirname $0)
  NUMCPU=$(grep -c -w processor /proc/cpuinfo)
  USER_HZ=$(python -c 'import os; print os.sysconf(os.sysconf_names["SC_CLK_TCK"])')
}

setup_env


function graph_cpu_info {
  local cpudb="$1"
  local outdir="$2"
  local starttime="$3"

  color=(FDB813 F68B1F F17022 62C2CC)
  dsstr=
  for i in $(seq 0 $(($NUMCPU - 1))); do
    dsstr="$dsstr
    DEF:cu$i=$cpudb:cpu_user_$i:AVERAGE
    DEF:cs$i=$cpudb:cpu_sys_$i:AVERAGE
    DEF:cn$i=$cpudb:cpu_nice_$i:AVERAGE
    DEF:cw$i=$cpudb:cpu_iowt_$i:AVERAGE
    CDEF:user_perc$i=cu$i,cs$i,+,cn$i,+,cw$i,+,-100,*,${USER_HZ},/
    AREA:user_perc$i#${color[$i]}:$([ $i -eq 0 ] || echo :STACK)"
  done

  rrdtool graph "$outdir"/cpugraph_${starttime}.png -s $starttime \
    -t 'CPU Usage' -v "CPU % ($NUMCPU CPUs)" \
    DEF:cu=$cpudb:cpu_user:AVERAGE \
    DEF:cs=$cpudb:cpu_sys:AVERAGE \
    DEF:cn=$cpudb:cpu_nice:AVERAGE \
    DEF:cw=$cpudb:cpu_iowt:AVERAGE \
    CDEF:user_perc=cu,100,\*,${USER_HZ},/ \
    CDEF:sys_perc=cs,100,\*,${USER_HZ},/  \
    CDEF:nice_perc=cn,100,\*,${USER_HZ},/ \
    CDEF:iowt_perc=cw,100,\*,${USER_HZ},/ \
    VDEF:mcu=cu,MINIMUM \
    VDEF:acu=cu,AVERAGE \
    VDEF:xcu=cu,MAXIMUM \
    HRULE:0#000000 \
    AREA:user_perc#009ECE:"User" \
    AREA:nice_perc#FF9E00:"Nice":STACK \
    AREA:sys_perc#F7D708:"System":STACK \
    AREA:iowt_perc#CE0000:"IO Wait":STACK \
    LINE:xcu#9CCF31:"Max User" \
    $dsstr \
    GPRINT:mcu:"User min\: %.1lf%%" \
    GPRINT:acu:"User avg\: %.1lf%%" \
    GPRINT:xcu:"User max\: %.1lf%%"
}


function graph_net_info {
  local netdb="$1"
  local outdir="$2"
  local starttime="$3"

  rrdtool graph "$outdir"/netgraph_${starttime}.png -s $starttime \
    -t 'Network Usage' -v "bytes/s" \
    DEF:ei=$netdb:eth0_in:AVERAGE \
    DEF:eo=$netdb:eth0_out:AVERAGE \
    DEF:wi=$netdb:wlan0_in:AVERAGE \
    DEF:wo=$netdb:wlan0_out:AVERAGE \
    CDEF:nwi=wi,-1,\* \
    CDEF:nei=ei,-1,\* \
    AREA:nei#FFBE00:"eth0 In" \
    AREA:nwi#9DD52A:"wlan0 In":STACK \
    HRULE:0#000000 \
    AREA:eo#AC54AA:"eth0 Out" \
    AREA:wo#666666:"wlan0 Out":STACK \
    VDEF:meo=eo,MINIMUM \
    VDEF:aeo=eo,AVERAGE \
    VDEF:xeo=eo,MAXIMUM \
    VDEF:mei=ei,MINIMUM \
    VDEF:aei=ei,AVERAGE \
    VDEF:xei=ei,MAXIMUM \
    GPRINT:meo:"eth0-out min\: %.1lf%sb/s" \
    GPRINT:aeo:"eth0-out avg\: %.1lf%sb/s" \
    GPRINT:xeo:"eth0-out max\: %.1lf%sb/s\c" \
    GPRINT:mei:"eth0-in min\: %.1lf%sb/s" \
    GPRINT:aei:"eth0-in avg\: %.1lf%sb/s" \
    GPRINT:xei:"eth0-in max\: %.1lf%sb/s\c"
}



if [ $# -lt 2 ]; then
  echo "Usage: $0 <db> {cpu|net} <outdir:.> <starttime:-6h>"
  exit 1
else
  DBtype="$2"
  if [[ "$DBtype" = "cpu" ]]; then
    graph_cpu_info "$1" "${3:-.}" "${4:--6h}"
  elif [[ "$DBtype" = "net" ]]; then
    graph_net_info "$1" "${3:-.}" "${4:--6h}"
  fi
fi

# vim: set sw=2 sts=2 : #
