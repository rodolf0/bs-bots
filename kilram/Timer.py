#!/usr/bin/python

import re
from datetime import datetime, timedelta, date

class TimerError(Exception):
  pass

class Timer(object):
  """Hold alarm information"""

  def __init__(self, args):
    self.creation_tm = datetime.now()
    self.callback_tm = None
    self.description = None
    self.require_ack = False
    self.last_alert = None

    datetime_regex = {
      "countdn" : # in 2d 3h 4m 5s
      ("in( +(?P<days>\d+) *(d|days))?"
         "( +(?P<hours>\d+) *(h|hs))?"
         "( +(?P<mins>\d+) *(m|min))?"
         "( +(?P<secs>\d+) *(s|sec))?"),
      "day-cd" : # in 2d at 6pm
      ("in +(?P<days>\d+) *(d|days) +"
       "at +(?P<time>\d\d?([:.]\d\d)?(am|pm)?)"),
      "weekday-cd" : # on Sun at 6pm
      ("(on|next) +(?P<wday>\w+) +"
       "at +(?P<time>\d\d?([:.]\d\d)?(am|pm)?)"),
      "month-cd" : # on May 6 at 4am
      ("(on|next) +(?P<month>\w+ +\d\d?) +"
       "at +(?P<time>\d\d?([:.]\d\d)?(am|pm)?)"),
      "tomorrow-cd" : # tomorrow at 4pm
      ("tomorrow +at +(?P<time>\d\d?([:.]\d\d)?(am|pm)?)"),
      "today-cd" : # today at 4pm
      ("at +(?P<time>\d\d?([:.]\d\d)?(am|pm)?)"),
    }

    for dtre in datetime_regex:
      r = re.search("^(?P<desc>[^:]+) *: *%s( +(?P<flags>req-ack))? *$" % \
                      datetime_regex[dtre], args, re.I)
      if r:
        self.description = r.group('desc')
        if r.group('flags') == 'req-ack':
          self.require_ack = True

        if dtre == 'countdn':
          self.callback_tm = datetime.now() + \
              timedelta(days=int(r.group("days") or 0),
                        hours=int(r.group("hours") or 0),
                        minutes=int(r.group("mins") or 0),
                        seconds=int(r.group("secs") or 0))
        else:
          for fmt in ('%I:%M%p', '%I.%M%p', '%I%p', '%H:%M', '%H.%M', '%H'):
            try:
              tm = datetime.strptime(r.group('time'), fmt).time()
              break
            except ValueError:
              pass
          else:
            raise TimerError("Failed to parse time '%s'" % r.group('time'))

          if dtre == 'day-cd':
            dt = date.today() + timedelta(days=int(r.group('days')))
            self.callback_tm = datetime.combine(dt, tm)

          elif dtre == 'tomorrow-cd':
            dt = date.today() + timedelta(days=1)
            self.callback_tm = datetime.combine(dt, tm)

          elif dtre == 'today-cd':
            if datetime.combine(date.today(), tm) > datetime.now():
              self.callback_tm = datetime.combine(date.today(), tm)
            else:
              dt = date.today() + timedelta(days=1)
              self.callback_tm = datetime.combine(dt, tm)

          elif dtre == 'weekday-cd':
            for fmt in ('%a %U', '%A %U'):
              try:
                wd = datetime.strptime(r.group('wday')+' 01', fmt).isoweekday()
                daydiff= (wd - date.today().isoweekday() + 7) % 7
                dt = date.today() + timedelta(days=daydiff)
                if datetime.combine(dt, tm) <= datetime.now():
                  dt += timedelta(days=7)
                break
              except ValueError:
                pass
            else:
              raise TimerError("Failed to parse weekday '%s'" % r.group('wday'))
            self.callback_tm = datetime.combine(dt, tm)

          elif dtre == 'month-cd':
            thisy, nexty = str(date.today().year), str(date.today().year + 1)
            for fmt in ('%b %d %Y', '%B %d %Y'):
              try:
                d = datetime.strptime(
                      "%s %s" % (r.group('month'), thisy), fmt).date()
                if datetime.combine(d, tm) <= datetime.now():
                  d = datetime.strptime(
                        "%s %s" % (r.group('month'), nexty), fmt).date()
                break
              except ValueError:
                pass
            else:
              raise TimerError("Failed to parse day '%s'" % r.group('month'))
            self.callback_tm = datetime.combine(d, tm)
        break
    else:
      raise TimerError("Unable to parse timer for '%s'" % args)


  def target(self):
    return self.callback_tm

  def remaining(self):
    return self.target() - datetime.now()

  def done(self):
    r = self.remaining()
    return (r.days * 24 * 3600 + r.seconds) <= 0

  def target_str(self):
    if self.callback_tm.date() == date.today():
      return "at %s" % self.callback_tm.strftime('%I:%M:%S%p')
    else:
      return "on %s" % self.callback_tm.strftime('%a %d %b %Y, %I:%M:%S%p')

  def remaining_str(self):
    fmt, ret = 'in %s', ''
    t = self.remaining()
    if t < timedelta(0):
      t = -t
      fmt = '%s ago'
    r = {'d': t.days,
         'h': t.seconds/3600,
         'm': (t.seconds%3600)/60,
         's': t.seconds%3600%60}
    for k in ('d', 'h', 'm', 's'):
      if r[k]:
        ret += ", %s%s" % (r[k], k)
    return fmt % ret[2:]

  @staticmethod
  def help():
    return \
'''
Try: timer description: timespec [req-ack]
Try: timer ack description
  timer fideos con tuco: in 8min
  timer dentista: on thursday at 6pm
  timer reunion: in 2 days at 3:30pm
  timer cumple: on Feb 14 at 5pm
'''
