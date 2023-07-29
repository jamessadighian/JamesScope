# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 12:49:03 2022

@author: James Sadighian
"""

from ScopeFoundry import HardwareComponent


try:
    import TimeTagger
    #from TimeTagger import (createTimeTagger, Countrate, Coincidences, ChannelEdge, SynchronizedMeasurements, Correlation, freeTimeTagger)
except Exception as err:
    print("could not load modules for TimeTagger: {}".format(err))

class TimeTaggerHW(HardwareComponent):
    
    #name = 'timetagger'
    def setup(self):
        
        self.name = 'timetagger'
        self.timetagger=0
        # Define your hardware settings here.
        # These settings will be displayed in the GUI and auto-saved with data files
        #self.count_rate0 = self.settings.New("count_rate0", dtype=int, ro=True, vmin=0, vmax=100e6)
        #self.count_rate1 = self.settings.New("count_rate1", dtype=int, ro=True, vmin=0, vmax=100e6)
        #self.settings.New("IntTime", dtype=float, unit="s", vmin=1e-3, vmax=100*60*60) #remove si=True to keep units from autochanging #
        
        self.settings.New("InputDelay2", dtype=int, unit="ps", vmin=0, vmax=2e7) #remove si=True to keep units
        #print(str(self.settings['InputDelay2']))
        #self.settings.New("InputDelay3", dtype=int, unit="ps", vmin=0, vmax=2e7)
        
    def connect(self):
                
        TT = self.tagger = TimeTagger.createTimeTagger()
        
        LQ = self.settings.as_dict()
        
        #LQ["InputDelay2"].hardware_set_func = TT.setDelayHardware(2, 400000)
        LQ["InputDelay2"].hardware_set_func = TT.setDelayHardware(-2, self.settings['InputDelay2'])
        LQ["InputDelay2"].hardware_read_func = TT.getInputDelay(-2)
        
        # connect logged quantities
        
        #for TTL triggered APDs
#        self.tagger.setTriggerLevel(1, -.4)
#        self.tagger.setTriggerLevel(2, 1.75)
#        self.tagger.setTriggerLevel(3, 1.75)
        
        #for NIM triggered APDs
        self.tagger.setTriggerLevel(1, -.4)
        self.tagger.setTriggerLevel(2, -.4)
        self.tagger.setTriggerLevel(3, -.4)
        
        print('laser trigger level is '+str(self.tagger.getTriggerLevel(-1)))
        print('APD0 trigger level is '+str(self.tagger.getTriggerLevel(-2)))
        print('APD1 trigger level is '+str(self.tagger.getTriggerLevel(-3)))
        print('APD1 Delay is '+str(self.tagger.getInputDelay(-2)))
        
        
    def disconnect(self):
        print('abc')
        if hasattr(self, 'timetagger'):
            print('def')
            #disconnect hardware
            TimeTagger.freeTimeTagger(self.tagger)
            
            
            #clean up hardware object
            #del self.tagger

