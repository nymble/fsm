#fsm.py

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
        http://www.slideshare.net/erant/uml-statechart-diagrams
    
    to do:
     - timers cancel function
     - clock reset effect on timer
     - add logging
     - clarify real-time versus simulated time
       make simulated a special setup
     - more unit tests
