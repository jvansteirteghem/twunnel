# Copyright (c) Jeroen Van Steirteghem
# See LICENSE

import inspect
import twisted.python.log

msg = twisted.python.log.msg

def msgWrapper(*args, **kwargs):
    kwargs["system"] = "-"
    
    stack = inspect.stack()
    frame = stack[1]
    module = inspect.getmodule(frame[0])
    
    if module is not None:
        if module.__name__ ==__name__:
            frame = stack[2]
            module = inspect.getmodule(frame[0])
            
            if module is not None:
                kwargs["system"] = module.__name__
            
            msg(*args, **kwargs)
        else:
            if module.__name__ == twisted.python.log.__name__:
                kwargs["system"] = module.__name__
                
                msg(*args, **kwargs)

twisted.python.log.msg = msgWrapper

def setDefaultConfiguration(configuration, keys):
    if "LOGGER" in keys:
        configuration.setdefault("LOGGER", {})
        configuration["LOGGER"].setdefault("LEVEL", 0)

loggerLevel = 0

def configure(configuration):
    global loggerLevel
    
    setDefaultConfiguration(configuration, ["LOGGER"])
    
    loggerLevel = configuration["LOGGER"]["LEVEL"]

def log(messageLevel, message):
    global loggerLevel
    
    if messageLevel <= loggerLevel:
        twisted.python.log.msg(message, messageLevel=messageLevel)