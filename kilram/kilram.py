#!/usr/bin/env python

# http://pypi.python.org/pypi/pyjabberbot/0.6

import logging
import subprocess, re
from pyjabberbot import botcmd, PersistentJabberBot
from datetime import datetime, timedelta

from User import User, UserError
from Timer import Timer, TimerError
from Logger import Logger, LoggerError

class Kilram(PersistentJabberBot):

  def __init__(self, username, password):
    super(Kilram, self).__init__(username, password)
    self.spawntime = datetime.now()
    self._lastbeat = datetime.now()

  def check_timers(self):
    """Go over user timers and send alerts"""
    for usr in User.users.values():
      for desc, timer in usr.get_timers():
        if usr.status != self.OFFLINE and timer.done():
          if not timer.require_ack:
            self.send(usr.jid, "Timer '%s' done %s" % (desc,timer.target_str()))
            usr.del_timer(desc)
          elif timer.last_alert is None or \
               datetime.now() - timer.last_alert > timedelta(minutes=5):
            self.send(usr.jid,
              "Timer '%s' done %s. Ack the timer to stop alerts." % \
              (desc, timer.target_str()))
            timer.last_alert = datetime.now()

  def cron_heartbeat(self):
    if datetime.now() - self._lastbeat > timedelta(minutes=10):
      if subprocess.call('pgrep cron &>/dev/null', close_fds=True, shell=True):
        self.send('warlock.cc@gmail.com', "Cron is dead.")
      self._lastbeat = datetime.now()


########################### bot overloads ############################

  def idle_proc(self):
    self.check_timers()
    #self.cron_heartbeat()
    return super(Kilram, self).idle_proc()

  def status_type_changed(self, jid, new_status):
    # Use to load users state when they become online and track them
    user = User.jid2user(jid)
    user.status = new_status

  def callback_presence(self, conn, presence):
    # register a status-change handler
    return super(Kilram, self).callback_presence(
            conn, presence, self.status_type_changed)


########################### admin Bot cmds ###########################

  @botcmd(hidden=True)
  def whoami(self, mess, args):
    return mess.getFrom()

  @botcmd(hidden=True)
  def uptime(self, mess, args):
    ret, t = "", datetime.now() - self.spawntime
    r = {'d': t.days,
         'h': t.seconds/3600,
         'm': (t.seconds%3600)/60,
         's': t.seconds%3600%60}
    for k in ('d', 'h', 'm', 's'):
      if r[k]:
        ret += ", %s%s" % (r[k], k)
    return ret[2:]

  @botcmd(hidden=True)
  def die(self, mess, args):
    self.quit()

  @botcmd(hidden=True)
  def monitor(self, mess, args):
    return

########################### user Bot cmds ############################

  @botcmd
  def show(self, mess, args):
    """timer status, logs, etc"""
    r = re.match("^(?P<cmd>\S+) *(?P<cargs>.+)?$", args, re.I)
    if not r:
      return "What do you wan't me to show you?"
    ret, user = "", User.jid2user(mess.getFrom())
    cmd, cargs = r.group('cmd'), r.group('cargs')
    # timer commands
    if cmd == 'timers':
      for desc, timer in user.get_timers():
        ret += "\n- %s: %s (%s)" % (
                desc, timer.target_str(), timer.remaining_str())
      return ret or "No timers set."
    # log commands
    elif cmd == 'logs':
      if not cargs:
        for desc, ulog in user.get_logs():
          ret += "\n- %s" % desc
        return ret or "No logs available."
      else:
        try:
          entries = user.get_logs(cargs).entries
        except KeyError:
          return "Couldn't find log '%s'" % cargs
        else:
          ret = "%s:" % cargs
          for entry in entries:
            ret += "\n* %s: %s" % (
                entry.timestamp.strftime('%b %d, %T'), entry.logtext)
          return ret
    else:
      return "I don't know '%s' command." % cmd

  @botcmd
  def logger(self, mess, args):
    """keeps registers with timestamps"""
    if not args:
      return Logger.help()
    user = User.jid2user(mess.getFrom())
    r = re.match("^del +(?P<log>.*)$", args, re.I)
    if r: # delete log
      try:
        user.del_log(r.group('log'))
      except KeyError:
        return "Couldn't find log '%s'." % r.group('log')
      else:
        return "Log deleted."
    else: # append log
      try:
        l = user.log_entry(args)
      except LoggerError as e:
        return str(e)
      else:
        return "logged."

  @botcmd
  def timer(self, mess, args):
    """sets an alarm for you (or acks it)"""
    if not args:
      return Timer.help()
    user = User.jid2user(mess.getFrom())
    r = re.match("^ack +(?P<timer>.*)$", args, re.I)
    if r: # timer ack
      try:
        user.del_timer(r.group('timer'))
      except KeyError:
        return "Timer '%s' not found." % r.group('timer')
      else:
        return "Timer acknowledged."
    else: # timer set
      try:
        t = user.set_timer(args)
      except (UserError, TimerError) as e:
        return str(e)
      else:
        return "Timer '%s' %s (%s)" % \
            (t.description, t.target_str(), t.remaining_str())


def main():
  logging.basicConfig()
  username = 'kilram.axesmith@gmail.com'
  password = '********'
  bot = Kilram(username, password)
  bot.serve_forever()
  logging.shutdown()

if __name__ == '__main__': main()
