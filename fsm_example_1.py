#!/usr/bin/env python
""" fsm_example_1.py
    
    A simple two-state example using fsm.py
    State_1 and State_2 alternate based on a timer.
    The two states are contained in the composite state Example_1 that defines
    the state transition table.

"""
from fsm import *
from random import random, randrange

class Event(FSM.Event):
    """ Events are enumerated values of this class.  A and B are not used
        in this example """
    time_out, A, B  = range(3)

class State_1(State.Atomic):
    """ State_1 uses 'entry' to set a timer. """
    def entry(self):
        self.setTimer(1*SEC, Event.time_out)  # generate event based on timer
        self.log("State_1")
        
class State_2(State.Atomic):
    def entry(self):
        self.setTimer(2*SEC, Event.time_out)
        self.log("State_2")

class Example_1(State.Composite):
    subStates = (State_1, State_2)
    #          state    event     ->         nextState   actionList
    ttable = {(State_1, Event.time_out):     (State_2,    ()) ,
              (State_2, Event.time_out):     (State_1,    ())}


example = Example_1()
example.fsm.run()


