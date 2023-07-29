# -*- coding: utf-8 -*-
"""
Created on Thu Apr 21 09:27:17 2022

@author: James Sadighian
"""

from ScopeFoundry import BaseMicroscopeApp
from TimeTagger import (Scope, createTimeTagger, freeTimeTagger)

class JamesScope(BaseMicroscopeApp):

    # this is the name of the microscope that ScopeFoundry uses 
    # when storing data
    name = 'james_microscope'
    
    # You must define a setup function that adds all the 
    #capablities of the microscope and sets default settings
    def setup(self):
        #Add App wide settings

        #Add hardware components
        #Notice that ScopeFoundry Hardware components always have the suffix “HW”.
        #from ScopeFoundryHW.virtual_function_gen.vfunc_gen_hw import VirtualFunctionGenHW #tells python where to find the hardware component folder.file.py.class
        #self.add_hardware(VirtualFunctionGenHW(self)) #creates an instance of the hardware (an active copy in memory), and then adds it to your App
        from HW_Swabian.SwabianTT import TimeTaggerHW
        self.add_hardware(TimeTaggerHW(self, name='timetagger'))
        from HW_PI_PiezoStage.PiezoStage_hardware import PiezoStageHW
        self.add_hardware(PiezoStageHW(self))
        print("Adding Hardware Components")
        
        
        #Add measurement components
        #Notice that ScopeFoundry Measurement class names always have the suffix “Measure”.
        from HW_Swabian.swabian_counthist_measure import SwabianHistogram
        self.add_measurement(SwabianHistogram(self))       
        from HW_Swabian.swabian_triple_measure import SwabianTriple
        self.add_measurement(SwabianTriple(self))
        from HW_Swabian.swabian_filewriter_measure import SwabianFilewriter
        self.add_measurement(SwabianFilewriter(self))
        
      
        from HW_Swabian.swabian_scan import Swabian_Scan
        self.add_measurement(Swabian_Scan(self))        
        
        from HW_PI_PiezoStage.PiezoStage_independent_movement import PiezoStageIndependentMovement
        self.add_measurement(PiezoStageIndependentMovement)
        from HW_PI_PiezoStage.PiezoStage_control import PiezoStageControl
        self.add_measurement(PiezoStageControl)
        from HW_PI_PiezoStage.particle_selection import ParticleSelection
        self.add_measurement(ParticleSelection)
        #from HW_OceanOptics.particle_spectra import ParticleSpectra
        #self.add_measurement(ParticleSpectra)
        
        
        print("Create Measurement objects")

        # Connect to custom gui

        # load side panel UI

        # show ui
        self.ui.show()
        self.ui.activateWindow()


if __name__ == '__main__':
    import sys
    
    app = JamesScope(sys.argv)
    sys.exit(app.exec_())