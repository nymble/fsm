#!/usr/bin/env python
"""

    Tests and example usage of fsm.py to model stoplights

    Copyright Paul A. Lambert 2014
"""
from fsm import *
import unittest

# ---- Stoplight Example for testing
class Event(FSM.Event):
    Run, TimeOut, Exit  = range(3)
    
class Light(State.Atomic):
    """ Base class for the 3 atomic states in a stoplight (Red, Green, Yellow)
    """
    def entry(self):
        self.setTimer(self.lightDelay, Event.TimeOut)
        self.lightOn()
        
    def exit(self):
        self.lightOff()
        
    def lightOn(self):
        print "{:15.9f}".format(1.*self.fsm.clock.time()/SEC), "{:15.9f}".format(1.*self.clock.time()/SEC), self.parentId, self.color, "ON"
        
    def lightOff(self):
        print "{:15.9f}".format(1.*self.fsm.clock.time()/SEC), "{:15.9f}".format(1.*self.clock.time()/SEC), self.parentId, self.color, "OFF"
          
class Red(Light):
    lightDelay = 50*SEC
    color = "red"
class Yellow(Light):
    lightDelay = 10*SEC
    color = "yellow"
class Green(Light):
    lightDelay = 50*SEC
    color = "green"
    
class StopLight(State.Composite):
    subStates = (Red, Yellow, Green) # First in list is the initial state class
    
    #         state    event        -> nextState   actionList
    ttable = {(Red,    Event.TimeOut): (Green,      ()),
              (Green,  Event.TimeOut): (Yellow,     ()),
              (Yellow, Event.TimeOut): (Red,        ()) }

class StopLight2(State.Parallel):
    """ A parallel state predefined as two Stoplights """
    parallelStates = (StopLight, StopLight)
    
# --- start of tests ---

class TestFSM(unittest.TestCase):
    def setUp(self):
        self.fsm = FSM()

    def childDump(self,state,cnt=0):
        print cnt*"    ", state.name, "-", state.stateId, state.time()/float(1*SEC)
        cnt += 1
        for child in state.children():
            self.childDump(child,cnt)
 
    def test01_basic_local_clock(self):
        s1 = StopLight()
        s1.fsm.run(steps=1)
        self.assertEqual(s1.time(),0)
        
        s1.fsm.run(steps=1)
        self.assertEqual(s1.time(),50*SEC) # red to green

        s1.setClock( time=10, drift=-5*PPM )
        self.assertEqual(s1.time(),10) # testing clock changes with pending events
        s1.fsm.run(steps=2)
        # cleanup, remove state and test that it's gone
        self.fsm.deleteState(s1)
        self.assertEqual(len(self.fsm.stateDict),0)
        self.fsm.run(2)  # all states deleted, but events still in queue
        
    
    def test03_deep_nested_states(self):         
        s1 = StopLight()
        s2 = StopLight()
        s3 = State.Parallel(states=(s1,s2))       
        s4 = StopLight()
        s5 = State.Parallel(states=(s3,s4))
        # s2 uses reference clock, s1 drifts
        s1.setClock( time=10, drift=-5*PPM )
        self.fsm.run(steps=2) 
        self.childDump(s5)
        self.assertNotEqual(self.fsm.clock, s1.clock)
        self.assertNotEqual(s5.time(), s1.time())
        self.assertEqual(self.fsm.clock, s2.clock)
        self.assertEqual(self.fsm.time(), s2.time())

        # set top most state
        s5.setClock( time=1*SEC, drift= -100*PPM )
        self.assertEqual(s5.time(), s1.time())    
        s1.fsm.run(steps=12)        
        self.assertEqual(s5.clock.time(), s1.clock.time()) 
        self.assertEqual(s5.clock, s1.clock) 
        
        self.fsm.deleteState(s5)  # recursive delete
        self.assertEqual(len(self.fsm.stateDict),0)
        
      
if __name__ == '__main__':
    unittest.main()
    
