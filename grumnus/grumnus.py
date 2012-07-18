#!/usr/bin/env python

# http://pypi.python.org/pypi/PyRRD/0.0.7

from pyrrd.rrd import DataSource, RRA, RRD
from pyrrd.graph import DEF, CDEF, VDEF, LINE, AREA, GPRINT, Graph
from subprocess import Popen, PIPE
import time, shlex, re, os


class SysStat(object):

  @classmethod
  def cpu_usage(cls, cpu_num=""):
    """
    Return the time spent in user, nice, system, idle, iowait mode
    meassured in jiffies
    """
    s = Popen(shlex.split("grep -w cpu%s /proc/stat" % cpu_num), stdout=PIPE)
    out, err = s.communicate()
    return re.split(' +', out.strip())[1:6]

  @classmethod
  def io_usage(cls, io_dev="sda"):
    """
    Return io stats: (iostats.txt) a sector has 512 bytes normally
    1,5 - total successful reads/writes
    2,6 - reads/writes merged
    3,7 - sectors read/written
    4,8 - milliseconds spend reading/writing
    9   - current IOs in progress
    10  - time doing IO (time that field 9 is not 0)
    11  - weighted IO time (to estimate backlog)
    """
    s = Popen(shlex.split("grep -w %s /proc/diskstats" % io_dev), stdout=PIPE)
    out, err = s.communicate()
    return re.split(' +', out.strip())[3:14]

  @classmethod
  def num_cpu(cls):
    """
    Return the number of CPUs
    """
    s = Popen(shlex.split("grep -c -w processor /proc/cpuinfo"), stdout=PIPE)
    out, err = s.communicate()
    return int(out)

  @classmethod
  def jiffies(cls):
    """
    A jiffy is the duration of a tick of the system timer
    if the tick is 100 (meaning 100Hz) then there are 100
    jiffies per second => a jiffy is 0.01s

    This functions returns the number of jiffies per second
    """
    return os.sysconf(os.sysconf_names['SC_CLK_TCK'])



class RRDB(object):

  def __init__(self, filename):
    self.db = RRD(filename)

  def store(self, values):
    self.db.bufferValue(int(time.time()), *values)
    self.db.update()

  @classmethod
  def generate_archives(cls, step, rows=1440,
                        day_periods=[2, 14, 60, 180, 720]):
    rras = []
    for days in day_periods:
      # how many primary data points (we get one each step)
      # go into a consolidated data point
      PDPs = 86400 * days / step / rows
      rras.extend([
        RRA(cf='AVERAGE', xff=0.1, rows=rows, steps=PDPs),
        RRA(cf='MIN', xff=0.1, rows=rows, steps=PDPs),
        RRA(cf='MAX', xff=0.1, rows=rows, steps=PDPs),
      ])
    return rras

  @classmethod
  def create_db(cls):
    raise NotImplementedError("Create DB is not implemented")

  def graph(self, outfile):
    raise NotImplementedError("graph method should be overriden")



class NetDB(RRDB):
  @classmethod
  def create_db(cls, filename, step, start,
                interface_speeds={"eth0": 6 * 1024**2 / 8, # 6Mbit/s
                                  "wlan0": 300 * 1024**2 / 8 }):
    dss = []
    for iface, speed in interface_speeds.items():
      dss.extend([
        DataSource(dsName="%s_out" % iface, dsType='COUNTER',
                   heartbeat=3*step, minval=0, maxval=speed),
        DataSource(dsName="%s_in" % iface, dsType='COUNTER',
                   heartbeat=3*step, minval=0, maxval=speed)
      ])
    db = RRD(filename, ds=dss, rra=cls.generate_archives(step),
             start=start, step=step)
    db.create()
    return db


class CpuDB(RRDB):
  @classmethod
  def create_db(cls, filename, step, start):
    dss = []
    for i in range(SysStat.num_cpu() + 1):
      # maxval is the total number of jiffies in the interval
      if i == 0:
        n, cpu_mul = "", SysStat.num_cpu()
      else:
        n, cpu_mul = "_%d" % (i-1), 1
      dss.extend([
        DataSource(dsName='cpu_user%s' % n, dsType='COUNTER', heartbeat=3*step,
                   minval=0, maxval=cpu_mul * SysStat.jiffies() * step),
        DataSource(dsName='cpu_nice%s' % n, dsType='COUNTER', heartbeat=3*step,
                   minval=0, maxval=cpu_mul * SysStat.jiffies() * step),
        DataSource(dsName='cpu_sys%s' % n, dsType='COUNTER', heartbeat=3*step,
                   minval=0, maxval=cpu_mul * SysStat.jiffies() * step),
        DataSource(dsName='cpu_idle%s' % n, dsType='COUNTER', heartbeat=3*step,
                   minval=0, maxval=cpu_mul * SysStat.jiffies() * step),
        DataSource(dsName='cpu_iowt%s' % n, dsType='COUNTER', heartbeat=3*step,
                   minval=0, maxval=cpu_mul * SysStat.jiffies() * step)
      ])
    db = RRD(filename, ds=dss, rra=cls.generate_archives(step),
             start=start, step=step)
    db.create()
    return db


  def collect(self):
    stats = SysStat.cpu_usage()
    for i in range(SysStat.num_cpu()):
      stats.extend(SysStat.cpu_usage("%d" % i))
    self.store(stats)


  def graph(self, outfile):
    elems = {
      "cu": DEF(rrdfile=self.db.filename, dsName="cpu_user", vname="cu"),
      "cn": DEF(rrdfile=self.db.filename, dsName="cpu_nice", vname="cn"),
      "cs": DEF(rrdfile=self.db.filename, dsName="cpu_sys", vname="cs"),
      "ci": DEF(rrdfile=self.db.filename, dsName="cpu_idle", vname="ci"),
      "cw": DEF(rrdfile=self.db.filename, dsName="cpu_iowt", vname="cw")
    }
    cpu_expr = "%%s,100,*,%s,/" % SysStat.jiffies()
    calc_elems = {
      "user": CDEF(vname="uperc", rpn=cpu_expr % elems["cu"].vname),
      "nice": CDEF(vname="nperc", rpn=cpu_expr % elems["cn"].vname),
      "sys": CDEF(vname="sperc", rpn=cpu_expr % elems["cs"].vname),
      "iowt": CDEF(vname="wperc", rpn=cpu_expr % elems["cw"].vname),
      #"max": VDEF(vname="maxcpu", rpn="%s,MINIMUM" % elems["ci"].vname),
    }
    graph_elems = {
      "max": LINE(value=100 * SysStat.num_cpu(), color="#000000"),
      "user": AREA(defObj=calc_elems["user"], color="#88ff88",
                   legend="User"),
      "nice": AREA(defObj=calc_elems["nice"], color="#aaffaa",
                   legend="Nice", stack=True),
      "sys": AREA(defObj=calc_elems["sys"], color="#ff8888",
                  legend="System", stack=True),
      "iowt": AREA(defObj=calc_elems["iowt"], color="#ffffaa",
                   legend="IO wait", stack=True),
    }
    g = Graph(outfile)
    g.data.extend(elems.values())
    g.data.extend(calc_elems.values())
    g.data.extend(graph_elems.values())
    g.write()



class Main(object):
  def __init__(self):
    args = self.parse_arguments()
    DB = { "cpu": CpuDB, "net": NetDB }[args.type]
    if args.create:
      DB.create_db(args.db, step=120, start=int(time.time()))
    elif args.collect:
      DB(args.db).collect()
    elif args.graph:
      DB(args.db).graph(args.graph)

  def parse_arguments(self):
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--db', metavar="db", required=True)
    p.add_argument('--type', metavar="db-type", required=True)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument('--create', action="store_true")
    g.add_argument('--collect', action="store_true")
    g.add_argument('--graph', metavar="image-name")
    args = p.parse_args()
    assert args.type in ('cpu', 'net')
    return args


def main():
  Main()

if __name__ == '__main__': main()
