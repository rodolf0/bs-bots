#!/usr/bin/env python

import re
from datetime import datetime, date

class LoggerError(Exception):
  pass


class LogEntry(object):
  def __init__(self, args):
    fmt = "\[(?P<date>\d\d\d\d-\d\d-\d\d)? *(?P<time>\d\d:\d\d:\d\d)\]"
    r = re.search("^(?P<log>[^:]+): *(%s)? *(?P<text>.*)$" % fmt, args, re.I)
    if r:
      self.logname = r.group('log')
      self.logtext = r.group('text')
      try:
        tdate, ttime = None, None
        if r.group('time'):
          ttime = datetime.strptime(r.group('time'), '%H:%M:%S').time()
          if r.group('date'):
            tdate = datetime.strptime(r.group('date'), '%Y-%m-%d').date()
            self.timestamp = datetime.combine(tdate, ttime)
          else:
            self.timestamp = datetime.combine(date.today(), ttime)
        else:
          self.timestamp = datetime.now()
      except ValueError:
        raise LoggerError('Failed to parse timestamp.')
    else:
      raise LoggerError("Couldn't parse log text.")


class Logger(object):

  def __init__(self, logname):
    self.creation_tm = datetime.now()
    self.logname = logname
    self.entries = []

  def log(self, entry):
    self.entries.append(entry)

  @staticmethod
  def help():
    return \
'''
Try: logger logname: logtext
  logger cuentas: almuerzo $23
'''
