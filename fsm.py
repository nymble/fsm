#!/usr/bin/env python
""" fsm.py

    An object oriented finite state machine library based on UML state machines.
    The objective of this library is to provide compact readable definitions
    of complex state machines.
    
    State Types Supported:
        Atomic:    Single state, actions defined as class methods
        Composite  Multiple Atomic states.  Transitions and actions determined
                   by a state transition table. Only one state in composite is active at a time
        Parallel   Multiple parallel state machines. Events sent to paralel goes
                   to all internal states.
     
    Clock time of states may be made asynchronous to other states to support
    simulation of systems with clock drift.
     
    References:
        https://en.wikipedia.org/wiki/UML_state_machine
    
    to do:
     - timers cancel function
     - clock reset effect on timer
     - add logging
     - clarify real-time versus simulated time
       make simulated a special setup
     - more unit tests
 
    Copyright Paul A. Lambert 2014, 2021

"""
from heapq import heappush, heappop

# long integer is used to track time in nanoseconds
NSEC =          1 # nanoseconds are the base time unit in the simulation
USEC =  1000*NSEC # microsecond in units of nanoseconds
MSEC =  1000*USEC # miliseconds in units of nanonseconds
TU   =  1024*USEC # IEEE 802.11 Time Unit
SEC  =  1000*MSEC # seconds in nsec counts
HOUR =    60*SEC  # 
DAY  =    24*HOUR #
SPEED_OF_LIGHT = 299792458 # meters per second
NSEC_PER_METER = long(SEC/SPEED_OF_LIGHT)
PPM = 1000  # Parts Per Million, stored and used as PPB for long calc

class FSM(object):
    """ A singleton class to hold the collection of states and events """
    __instance = None
    def __new__(cls):
        if FSM.__instance is None:
            FSM.__instance = object.__new__(cls)
            self = FSM.__instance
            self.__eventQueue = []  # used as a heap 
            self.stateDict = {}    # holds all states indexed by Id
            self.stateIdNext = 0
            self.clock = MasterClock() # Master clock, no drift, no offset
            self.eventCount = 0
            self.maxEvents = 1000000L
        return FSM.__instance

    def addState(self, state):
        state.stateId = self.stateIdNext
        self.stateIdNext += 1
        self.stateDict[state.stateId] = state
        try:
            state.onCreation()   # state initialization
        except AttributeError:
            pass
        try:
            state.initVisual()
        except AttributeError:
            pass
        
    def deleteState(self, state):
        for child in state.children():
            self.deleteState(child)
        del self.stateDict[state.stateId]

    def _newEvent(self, deltatime, eventType, stateId=None):
        eventTime = long(self.time() + deltatime)
        raise "wrong time " # <<>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
        event = FSM.Event(eventType, stateId)
        pushEvent(eventTime, event)
        
    def pushEvent(self, eventTime, event):
        heappush(self.__eventQueue, (long(eventTime), event))   
        
    def run(self, steps=None, maxEvents=None):
        """ Run pops events and sends them to their target state """
        # activate and enter top level states
        if steps != None:
            self.maxEvents = self.eventCount + steps
        if maxEvents != None:    
            self.maxEvents = maxEvents
        if self.eventCount == 0:   # only the first time - propagate start
            self.eventCount += 1 # effectively the first event 
            for id in self.stateDict :  
                if self.stateDict[id].parentId == None:  # top level machines
                    self.stateDict[id]._activate()
        
        # run by poping events and handling them until empty queue or hit maximum
        while len(self.__eventQueue)>0 and self.eventCount < self.maxEvents:
            eventTime, event = heappop(self.__eventQueue)
            assert eventTime >= self.time()
            
            # adjust master and if required local clocks
            self.clock.updateTime(eventTime)  # master clock moves forward
            if event.origState.clock != self.clock:     # local clocks move by delta
                event.origState.clock.updateLocalTimeByDelta(event.delayTime)  
                
            if event.cancel == False:     # ignore if event canceled
                try: 
                    self.eventCount += 1
                    state = self.stateDict[event.targetId] # get target instance
                    #<log here>
                    state._handleEvent(event)  # each state handles it's own events
                except:
                    pass # ignore events to deleted states 
                
        
    def time(self):
        """ Time uses the attached clock, hiding the clock object """
        return self.clock.time()
           
    class Event():
        """ Events are placed in the FSM eventQueue """
        def __init__(self, eventType, targetId):
            self.type = eventType
            self.targetId = targetId
            self.cancel = False
    

class State(object):
    """ State machine class based on selected aspects of UML modeling """
    class State(object):
        """ Abstract base class for all state types """
        def __init__(self, parentId):
            self.active = False
            self.stateId = None # usually set later by FSM.addState()
            self.fsm = FSM() # singleton context for all states, event queue, etc
            self.fsm.addState(self)   # also sets state stateId of this instance
            self.parentId = parentId
            self.name = self.__class__.__name__  # default to class name
            self.clock = self.fsm.clock  # use the master fsm clock by default
            self.realTime = False # default to simulation mode versus realTime
            # logging will go here for state creation  <<>>
        
        def entry(self):
            """ An optional behavior that is executed when entered """
            pass
      
        def exit(self):
            """ An optional behavior executed whenever this state is exited """
            pass
        
        def defaultAction():
            raise "Unrecognized event"
 
        def time(self):
            """ Every state maintains a time reference
                self.time() is local machine time which may be offset or drifting
                self.fsm.time() is global referene master clock
            """
            return self.clock.time()
             
        def setClock(self, time=0, drift=0, _clock=None):
            """ Sets the local clock.  Once set, clock is no longer tied to the
                parent clock and all substates are changed to the new clock """
            if _clock == None:
                _clock = Clock(time, drift) # create and set
            self.clock = _clock
            # propagate the new clock to all contained states
            for child in self.children():
                child.setClock(_clock=_clock)
         
        def setTimer(self, delayTime, eventType):
            """ Timers send a event of 'evenType' to the states parentId """
            assert delayTime >= 0
            assert self.parentId != None
            event = FSM.Event(eventType, self.parentId)
            self.queueEvent(delayTime, event)
            return event
            
        def queueEvent(self, delayTime, event):
            """ queue event based on attached clock """
            event.clock = self.clock  # carry clock used for event so it can be updated on pop
            event.origState = self
            event.delayTime = delayTime
            if event.clock == self.fsm.clock:
                eventTime = self.time() + delayTime
            else: # correct for drift and offset
                eventTime = event.clock.masterTime(self.time() + delayTime)
            self.fsm.pushEvent(eventTime, event)                   
        
        def log(self, text):
            print "{:4d} {:14.9f} {}".format(self.parentId, (1.*self.fsm.clock.time()/SEC), text )
           
    
    class Type:   # enumeration of state types
        Atomic, Composite, Parallel = range(3)
        
    class Atomic(State):
        """ """
        def __init__(self, parentId):
            self.stateType = State.Type.Atomic
            super(State.Atomic,self).__init__(parentId)   # common State.Base init
            
        def start(self):
            if self.active == False:
                self.active = True
                self.entry() # execute option entry method
            
        def _activate(self):
            self.active = True
            self.entry()
            
        def _deactivate(self):
            self.exit()
            self.active = False

        def children(self):
            return () # Atomic states have no children
            
    class Composite(State):
        """ A state containing multiple states with only one active at a time
            Class variable subStates must be set to a list of contained class types.
            The class types are used at inititalization to create subSates
            Class variable ttable must be set to define the transition table
        """
        def __init__(self, parentId=None):
            self.stateType = State.Type.Composite
            super(State.Composite,self).__init__(parentId)   # common State.Base init
            self.compositeStates = {}  # dictionary of instances indexed by state type
            # first substate in the list is the initial state   
            StateClassType = self.__class__.subStates[0]  
            self.initialState = StateClassType(parentId=self.stateId)
            self.currentState = self.initialState # <<>>  should this be None?  are composite states active from creation?
            self.compositeStates[self.initialState.__class__] = self.initialState            # make instances of the remaining list
            # make remaining instances
            for StateClassType in self.__class__.subStates[1:]:
                instance = StateClassType(parentId=self.stateId)
                self.compositeStates[instance.__class__] = instance
        
        def _activate(self):
            if self.active == False:
                self.active = True
                self.currentState = self.initialState
                self.entry()
                self.initialState._activate()
            else:
                pass # do not reactivate a running machine
                     # ... perhaps should map to a "start" event <<>> !!!
                     # start would be a default defined event and action
            
        def _handleEvent(self, event): 
            # use class transition table for Composite states
            tt = type(self).ttable
            if (self.currentState.__class__, event.type) in tt:
                nextStateClass, actionList = tt[(self.currentState.__class__, event.type)]
                for action in actionList:
                    action(self, event) 
                # state transition ------------------------------------    
                if nextStateClass != self.currentState.__class__ :
                    self.currentState._deactivate()  # leave the state
                    self.currentState = self.compositeStates[nextStateClass] 
                    self.currentState._activate()    # move to next
            else:
                self.defaultAction()
        
        def children(self):
            """ Iterator to return children list of subState instances """
            for stateType in self.compositeStates:
                yield self.compositeStates[stateType]
   
            
    class Parallel(State):
        """ A state consisting of multiple independent states """
        def __init__(self, parentId=None, states=()):
            self.stateType = State.Type.Parallel
            super(State.Parallel,self).__init__(parentId)   # common State.Base init
            self.parallelStateDict = {}
            # if available, create instance from default list of classes
            try:         
                for StateClassType in self.__class__.parallelStates:
                    instance = StateClassType(parentId=self.stateId)
                    self.parallelStateDict[instance.stateId] = instance           
            except AttributeError:
                pass
            # if called directly, list of instances is used to initialize
            for instance in states :
                self.addState(instance)
            
        def addState(self, instance):
            self.parallelStateDict[instance.stateId] = instance
            instance.parentId = self.stateId

        def _activate(self):
            if self.active == False:
                self.active = True
                self.entry()
                for stateId in self.parallelStateDict:
                    self.parallelStateDict[stateId]._activate()
                
        def _deactivate(self):
            self.active = False
            self.exit()
                    
        def _handleEvent(self, event): 
            """ send event to all contained states """
            assert self.active == True # not sure this is right ... <<>>
                                       # does sending an event to a stopped parallel machine start the machine?
            for stateId in self.parallelStateDict:
                self.parallelStateDict[stateId]._handleEvent(event)
        
        def children(self):
            """ Iterator to return children list of parallel states """
            for stateId in self.parallelStateDict:
                yield self.parallelStateDict[stateId]


class MasterClock():
    """ Reference clock. Must be updeted by event queue """
    def __init__(self, time=0):
        self.__time = long(time)
        
    def time(self):
        return self.__time
        
    def set(self, time=None, drift=None):
        raise "You can not change master time clock"
    
    def offset(self): return 0 # Master time is never offset
       
    def updateTime(self, newTime):
        """ move time forward to newTime"""
        assert newTime >= self.__time
        self.__time = newTime
        

class Clock():
    """ Clock holds the drift and offset realtive to fsm event queue time """
    def __init__(self, time=None, drift=0):
        self.fsm = FSM()    # singleton context containing reference clock
        if time == None:    # default to current reference clock time
            time = self.fsm.time()
        self.timeEventDict = {}
        self.set(time=time, drift=drift)

    def time(self):
        """ time for clock is based on zeroOffset and drift from reference """
        return self.__time
        
    def set(self, time=None, drift=None):
        """ Resets offset relative fsm.clock """
        if drift != None:        # default to not change drift if only time set
            self.drift = drift
        if time != None:         # default to not change time if only drift set
            self.__time = time
        #zeroOffset = localTime - time*(1+drift/1E+9)
        self.zeroOffset = long(self.__time - (self.fsm.time() * ( 1000000000L + self.drift))/1000000000L )

    def cancelEvent(self, event):
        event.cancel = True
        
    def cancelClockEvents(self, clock): #<<>> use on delete of state? or just let events drop
        for event in clock.timeEventDict:
            cancelEvent(event)
        
    def offset(self):
        """ return current offset of clock from reference time """
        return self.time() - self.fsm.time()
    
    def updateLocalTimeByDelta(self, deltaTime):
        """ move local time forward by deltaTime and reference to newTime
            if cock has been reset, delta is still full duration
        """
        assert deltaTime >= 0
        self.__time += deltaTime

    def masterTime(self, localTime):
        """ Calculates the master reference time for a localTime """
        # time is long int nano seconds, drift is integer PPB
        # localTime = time*(1+drift/1E+9)+zeroOffset
        # time = (localTime -zeroOffset)/(1+drift/1E+9)
        return long( 1000000000L * (localTime- self.zeroOffset)/(1000000000L + self.drift) )
            
