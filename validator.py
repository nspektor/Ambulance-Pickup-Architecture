#!/usr/bin/env python

import sys, os, re, fileinput

def timetake(a,b):
 return abs(a.x-b.x)+abs(a.y-b.y)


# Exception class
class ValidationError(ValueError): pass
class FormatSyntaxError(ValidationError): pass
class DataMismatchError(ValidationError): pass
class IllegalPlanError(ValidationError): pass


##  Person object
##
PID = 0
class Person:

  def __init__(self, x, y, st):
    global PID
    PID += 1
    self.pid = PID
    self.x = x
    self.y = y
    self.st = st
    self.rescued = False
    return
  
  def __repr__(self):
    return '%d: (%d,%d,%d)' % (self.pid, self.x, self.y, self.st)


##  Hostpital object
##
HID = 0
class Hospital:
  
  def __init__(self, x, y, namb):
    global HID
    HID += 1
    self.hid = HID
    self.x = x
    self.y = y
    # ambtime array represents the time each ambulance have already spent.
    # NOTE: this should be sorted in a decreasing order (larger value first).
    self.namb = namb
    self.ambtime = [0] * namb
    return
    
  def __repr__(self):
    return '%d: (%d,%d)' % (self.hid, self.x, self.y)
  
  def decamb(self, t):
    self.ambtime[t] -= 1
    if self.ambtime[t] == 0: del self.ambtime[t]
    return
  
  def incamb(self, t):
    if t not in self.ambtime: self.ambtime[t] = 0
    self.ambtime[t] += 1
    return
  
  def rescue(self, pers,hospitals):
    if 4 < len(pers):
      raise IllegalPlanError('Cannot rescue more than four people at once: %s' % pers)
    already_rescued = filter(lambda p: p.rescued, pers)
    if already_rescued:
      raise IllegalPlanError('Person already rescued: %s' % already_rescued)
    # t: time to take
    # note: we don't have to go back to the starting hospital
    # so go to the closest from the last student
    t = 0
    start = self
    for p in pers:
      t += timetake(start,p)
      start = p
    # look for closest hospital
    min_hosp = 0
    min_hosp_distance = None
    for hosp in hospitals:
      tmp_dist = timetake(start,hosp)
      if not min_hosp_distance:
        min_hosp_distance = tmp_dist
        min_hosp = hosp
      elif tmp_dist < min_hosp_distance:
        min_hosp_distance = tmp_dist
        min_hosp = hosp
    t += min_hosp_distance

    # try to schedule from the busiest ambulance at the hospital.
    for (i,t0) in enumerate(self.ambtime):
      if not filter(lambda p: p.st < t0+t, pers): break
    else:
      raise IllegalPlanError('Either person cannot make it: %s' % pers)
    # proceed the time.
    self.ambtime[i] += t
    # keep it sorted.
    self.ambtime.sort()
    self.ambtime.reverse()
    for p in pers:
      p.rescued = True
    print 'Rescued:', ' and '.join(map(str, pers)), 'taking', t, '|ended at hospital', min_hosp
    return


# readdata
def readdata(fname):
  print >>sys.stderr, 'Reading data:', fname
  persons = []
  hospitals = []
  mode = 0
  for line in file(fname):
    line = line.strip().lower()
    if line.startswith("person") or line.startswith("people"):
      mode = 1
    elif line.startswith("hospital"):
      mode = 2
    elif line:
      if mode == 1:
        (a,b,c) = map(int, line.split(","))
        persons.append(Person(a,b,c))
      elif mode == 2:
        (c,) = map(int, line.split(","))
        hospitals.append(Hospital(-1,-1,c))
  return (persons, hospitals)


# read_results
def readresults(persons, hospitals):
  print >>sys.stderr, 'Reading results...'
  p1 = re.compile(r'(\d+\s*:\s*\(\s*\d+\s*,\s*\d+(\s*,\s*\d+)?\s*\))')
  p2 = re.compile(r'(\d+)\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*\)')
  p3 = re.compile(r'(\d+)\s*:\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)')

  score = 0
  mode = 0 # 0: default, 1: hospital locations, 2: ambulance responses
  hospital_index = 0
  for line in fileinput.input():
    line = line.strip().lower()
    if not line: continue
    # check for hospital coordinates
    if line.startswith('hospital'):
      mode = 1
      # read in hospital coordinates and set on hospital object
      (x,y,z) = map(int,line.replace('hospital:','').split(','))
      print "Hospital #{idx}: coordinates ({x},{y})".format(x=x,y=y,idx=hospital_index+1)
      if not (x and y):
        raise ValidationError("Hospital coordinates not set: line".format(line))
      if z != hospitals[hospital_index].namb:
        raise ValidationError("Hospital's ambulance # does not match input (input={0}, results={1})".format(hospitals[hospital_index].namb,z))
      hospitals[hospital_index].x = x
      hospitals[hospital_index].y = y
      hospital_index += 1
      continue
      
    # check for ambulance records
    if not line.startswith('ambulance'):
      print >>sys.stderr, '!!! Ignored: %r' % line
      continue
    try:
      hos = None
      rescue_persons = []
      for (i,(w,z)) in enumerate(p1.findall(line)):
        m = p2.match(w)
        if m:
          # Hospital n:(x,y)
          if i != 0:
            raise FormatSyntaxError('Specify a person now: %r' % line)
          (a,b,c) = map(int, m.groups())
          if a <= 0 or len(hospitals) < a:
            raise FormatSyntaxError('Illegal hospital id: %d' % a)
          hos = hospitals[a-1]
          if hos.x != b or hos.y != c:
            raise DataMismatchError('Hospital mismatch: %s != %d:%s' % (hos, a,(b,c)))
          continue
        m = p3.match(w)
        if m:
          # Person n:(x,y,t)
          if i == 0:
            raise FormatSyntaxError('Specify a hospital first: %r' % line)
          (a,b,c,d) = map(int, m.groups())
          if a <= 0 or len(persons) < a:
            raise FormatSyntaxError('Illegal person id: %d' % a)
          per = persons[a-1]
          if per.x != b or per.y != c or per.st != d:
            raise DataMismatchError('Person mismatch: %s != %d:%s' % (per, a,(b,c,d)))
          rescue_persons.append(per)
          continue
        # error
        raise FormatSyntaxError('Expected "n:(x,y)" or "n:(x,y,t)": %r' % line)

      if not hos or not rescue_persons:
        print >>sys.stderr, '!!! Insufficient data: %r' % line
        continue
      hos.rescue(rescue_persons,hospitals)
      score += len(rescue_persons)
    except ValidationError, x:
      print >>sys.stderr, '!!!', x
  #
  print 'Total score:', score
  return


# main
if __name__ == "__main__":
  if len(sys.argv) < 2:
    print 'usage: validator.py datafile [resultfile]'
    sys.exit(2)
  (persons, hospitals) = readdata(sys.argv[1])
  del sys.argv[1]
  readresults(persons, hospitals)
