#!/usr/bin/env python

import pickle, sys, os
from Timer import Timer
from Logger import Logger, LogEntry

class UserError(Exception):
  pass

class User(object):

  # Global container for users
  users = {}

  def __init__(self, jid):
    # place where we store all user data
    self.jid = jid
    self._datafile = "%s/data/%s" % (sys.path[0], jid.getStripped())
    self._timers = {}
    self._logs = {}
    self.status = None
    self._load()

  @classmethod
  def jid2user(cls, jid):
    """cache user data read from disk"""
    sjid = jid.getStripped()
    if sjid not in cls.users:
      cls.users[sjid] = User(jid)
    return cls.users[sjid]

######################################################################

  def _load(self):
    if os.path.exists(self._datafile):
      with open(self._datafile, 'rb') as ufile:
        self._timers = pickle.load(ufile)
        self._logs = pickle.load(ufile)

  def save(self):
    with open(self._datafile, 'wb') as ufile:
      pickle.dump(self._timers, ufile, -1)
      pickle.dump(self._logs, ufile, -1)

#################### timer manipulation ##############################

  def get_timers(self):
    return self._timers.items()

  def set_timer(self, args):
    """add a timer for this user"""
    t = Timer(args)
    if t.description in self._timers:
      raise UserError("Timer already exists.")
    self._timers[t.description] = t
    self.save() # commit data
    return t

  def del_timer(self, desc):
    del self._timers[desc]
    self.save() # commit data

#################### logs manipulation ##############################

  def get_logs(self, logname=None):
    if logname:
      return self._logs[logname]
    else:
      return self._logs.items()

  def log_entry(self, args):
    e = LogEntry(args)
    if e.logname not in self._logs:
      self._logs[e.logname] = Logger(e.logname)
    self._logs[e.logname].log(e)
    self.save()
    return e

  def del_log(self, logname):
    del self._logs[logname]
    self.save() # commit data

######################################################################
