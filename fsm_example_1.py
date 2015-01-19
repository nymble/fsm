#!/usr/bin/env python
""" fsm_example_1.py
    
    A simple example using fsm.py
    State_1 and State_2 alternate based on a timer.
    The two states are contained in the composite state Example_1 that defines
    the state transition table.

"""
from fsm import *
from random import random, randrange

class Event(FSM.Event):
    Next_State, A, B  = range(3)

class State_1(State.Atomic):
    def entry(self):
        self.setTimer(1*SEC, Event.Next_State)  # generate event based on timer
        self.log("State_1")
        
class State_2(State.Atomic):
    def entry(self):
        self.setTimer(1*SEC, Event.Next_State)
        self.log("State_2")

class Example_1(State.Composite):
    subStates = (State_1, State_2)
    #              state    event     ->    nextState   actionList
    ttable = {(State_1, Event.Next_State):   (State_2,    ()) ,
              (State_2, Event.Next_State):   (State_1,    ())}    


example = Example_1()
example.fsm.run()


