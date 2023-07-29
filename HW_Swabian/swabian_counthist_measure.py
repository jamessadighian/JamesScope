# -*- coding: utf-8 -*-
"""
Created on Tue Apr 26 11:35:17 2022

@author: James Sadighian
"""

from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
from PyQt5.QtWidgets import QMainWindow, QApplication, QFileDialog
from PyQt5.QtCore import QTimer
from PyQt5 import uic
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
import numpy as np
import time
import pyqtgraph as pg
import os
from TimeTagger import SynchronizedMeasurements, Counter, Histogram, Correlation, createTimeTagger, freeTimeTagger 
#from HW_Swabian.JamesCoincidence import JamesCoincidenc

class SwabianHistogram(Measurement):
    
    # this is the name of the measurement that ScopeFoundry uses when displaying your measurement and saving data related to it
    name='swabian_hist_measure'
    
    def setup(self):
        """
        Runs once during App initialization.
        This is the place to load a user interface file,
        define settings, and set up data structures. 
        """
        
        self.display_update_period = 0.1 #seconds
        
        S = self.settings                               #create variable S, which is all the settings
        #S.New('continuous', dtype=bool, initial=False)  #new variable in S called continuous
        #self.n_values = S.New("n_values", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("counter_n_values", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("counter_bin_width", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("histogram_n_values", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("histogram_bin_width", dtype=int, ro=False, vmin=0, vmax=100e6)
        # UI 
        self.ui_filename = sibling_path(__file__,"swabian_counthist_measure.ui")    #this whole section just loads the ui file
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        self.ui.setWindowTitle('histogram fuckery')

        self.elapsed_time = 0                               #creates a counter and empty data arrays
        #self.xdata = [] #array storing countrate data
        #self.ydata = [] #array storing time points
        
    
    def setup_figure(self):
        S = self.settings                           #creates instance of S within this function?
        self.tt_hw = self.app.hardware['timetagger'] #creates instance of the timetagger hw in this function?
        
        #self.counterbinwidth=100000000000
        #self.n_values=1000
        
        #connect events/settings to ui
        #S.progress.connect_bidir_to_widget(self.ui.progressBar)
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)
        #S.continuous.connect_to_widget(self.ui.continuous_checkBox)
        #tt_hw.settings.Tacq.connect_bidir_to_widget(self.ui.picoharp_tacq_doubleSpinBox)
        #tt_hw.settings.count_rate0.connect_to_widget(self.ui.ch0_label)
        #tt_hw.settings.count_rate1.connect_to_widget(self.ui.ch1_label)
        self.ui.save_data_pushButton.clicked.connect(self.save_hist_data)
        self.ui.clearplot_pushButton.clicked.connect(self.clear_plot)
        S.counter_n_values.connect_bidir_to_widget(self.ui.counter_numbins_doubleSpinBox)
        S.counter_bin_width.connect_bidir_to_widget(self.ui.counter_binwidth_doubleSpinBox)
        S.histogram_n_values.connect_bidir_to_widget(self.ui.hist_numbins_doubleSpinBox)
        S.histogram_bin_width.connect_bidir_to_widget(self.ui.hist_binwidth_doubleSpinBox)
        '''qtgraph figure'''
        '''
        self.graph_layout = pg.GraphicsLayoutWidget()    
        
        self.plot = self.graph_layout.addPlot()
        self.plotdata = self.plot.plot(pen='r')
        self.plot.setLogMode(False, True)
        
        # self.ui.plotWidget.layout().addWidget(self.graph_layout) commented out because this was for the g2 hist_test layout
        self.ui.plot_groupBox.layout().addWidget(self.graph_layout)
        '''
        
        '''matplotlib figure'''
        
        self.fig = Figure()
        self.counterAxis = self.fig.add_subplot(211)
        self.histogramAxis = self.fig.add_subplot(212)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, parent = None) #self)
        self.ui.plot_groupBox.layout().addWidget(self.toolbar)
        self.ui.plot_groupBox.layout().addWidget(self.canvas)
        
        self.counterAxis.set_xlabel('time (s)')
        self.counterAxis.set_xlim(0,100)
        self.counterAxis.set_ylabel('count rate (kEvents/s)')
        self.counterAxis.set_title('Count rate')
        # self.counterAxis.legend(['A', 'B', 'coincidences'])
        self.counterAxis.legend(['Channel 1'])
        self.counterAxis.grid(True)
        
        self.histogramAxis.set_xlabel('time (??)')

        self.histogramAxis.set_ylabel('counts')
        self.histogramAxis.set_title('Histogram')
        
        self.counterline, = self.counterAxis.plot([],[])
        self.counterline2, = self.counterAxis.plot([],[])
        self.histogramline, = self.histogramAxis.plot([],[])
        self.histogramline2, = self.histogramAxis.plot([],[])
        
        self.fig.tight_layout()
        
        
        
        
        
        ##self.ui.plotGroupBox.layout().addWidget(self.toolbar)
        ##self.ui.plotGroupBox.layout().addWidget(self.canvas)     #i don't know what this does
        '''
        Runs once during App initialization, after setup()
        This is the place to make all graphical interface initializations,
        build plots, etc.
        '''
    def getCounterNormalizationFactor(self):
        bin_index = self.counter.getIndex()
        # normalize 'clicks / bin' to 'kclicks / second'
        return 1e12 / bin_index[1] / 1e3
        
    def run(self):
        '''
        Runs when measurement is started. Runs in a separate thread from GUI.
        It should not update the graphical interface directly, and should only
        focus on data acquisition.
        '''
        self.tt_hw = self.app.hardware['timetagger']
        S = self.settings                      #initializes instance of the timetagger hardware
        #channels = [self.ui.channelA.value(), self.ui.channelB.value()]
        #self.tagger=self.scope.tagger
        #sw_hw = self.app.hardware['timetagger']
        #sw = self.swabian = sw_hw.tt
        
        #tt_hw = self.app.hardware['timetagger']
        #ph = self.picoharp = ph_hw.picoharp
        
        #sleep_time = self.display_update_period
        
        sleep_time = self.display_update_period
        
        t0 = time.time()
        
        print('Counter number of bins is '+str(self.settings['counter_n_values']))
        print('Counter bind width is '+str(self.settings['counter_bin_width']))
        print('Histogram number of bins is '+str(self.settings['histogram_n_values']))
        print('Histogram bin width is '+str(self.settings['histogram_bin_width']))
        
        self.tt_hw.tagger.setConditionalFilter(trigger=[-2,-3], filtered=[-1], hardwareDelayCompensation = True)
        
        self.synchronized = SynchronizedMeasurements(self.tt_hw.tagger)
        taggerSync = self.synchronized.getTagger()
        
        #self.counter = Counter(taggerSync, channels=[2, 3], binwidth=self.settings['counter_bin_width'], n_values=self.settings['counter_n_values'])
        self.counter = Counter(taggerSync, channels=[-2, -3], binwidth=100000000000, n_values=1000)
        self.histogram = Histogram(taggerSync, -2, -1, self.settings['histogram_bin_width'], self.settings['histogram_n_values'])
        
        self.histogram2 = Histogram(taggerSync, -3, -1, self.settings['histogram_bin_width'], self.settings['histogram_n_values'])
        
        self.synchronized.start()
        # while not self.interrupt_measurement_called:
        #     time.sleep(.01)
        
        
        while not self.interrupt_measurement_called: # and self.synchronized.isRunning()==True:
            time.sleep(.01)            
        else:
            self.synchronized.stop()
            print('Stopped!')
            print('we are no longer filtering channel'+str(self.tt_hw.tagger.getConditionalFilterFiltered()))
            self.tt_hw.tagger.clearConditionalFilter()
            print('also i turned the conditional filter off..feel free to move around scopefoundry')

        
    def update_display(self):
        '''
        Displays (plots) the data
        This function runs repeatedly and automatically during the measurement run.
        its update frequency is defined by self.display_update_period
        '''
        self.tt_hw = self.app.hardware['timetagger']
        '''
        #print(np.shape(self.xdata))
        #print(np.shape(self.ydata))
        d = self.counter.getData().T[:,0]
        print(np.shape(d))
        t = self.counter.getIndex() * 1e-12
        
        #print(self.ydata[0])
        self.plotdata.setData(t, d)
        
        #self.plotdata.setData(self.xdata, self.ydata)
        
        #self.plot.plot(self.xdata, self.ydata, pen='r')
        
        print("working")
        '''
        
        #self.counterAxis.clear()
        # self.plt_counter = self.counterAxis.plot(                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          self.counter.getIndex() * 1e-12,
        #       self.counter.getData().T * self.getCounterNormalizationFactor()
        #   )
        
        d = self.counter.getData().T[:,0] * self.getCounterNormalizationFactor()
        f = self.counter.getData().T[:,1] * self.getCounterNormalizationFactor()
        #print(np.shape(d))
        t = self.counter.getIndex() * 1e-12
        #self.counterAxis.plot(t, d)
        self.counterline.set_data(t, d)
        self.counterline2.set_data(t, f)
        #print('testing counter')
#        self.counterAxis.plot(                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          # self.counter.getIndex() * 1e-12,
#              self.counter.getData().T[:,0]* self.getCounterNormalizationFactor()
#              )
        #self.counterAxis.set_ylim(0,max(d))
        self.counterAxis.set_ylim(0,max(max(d), max(f))*1.05)   #will this fix the error regarding the counter measure? why does it work here and not in triple measure?
        # self.counterAxis.set_xlabel('time (s)')
        # self.counterAxis.set_ylabel('count rate (kEvents/s)')
        # self.counterAxis.set_title('Count rate')
        # # self.counterAxis.legend(['A', 'B', 'coincidences'])
        #self.counterAxis.legend(['Channel 2', 'Channel 3'])
        # self.counterAxis.grid(True)
        
        self.counterAxis.relim()
        self.counterAxis.autoscale_view(True, True, True)
        
        
        b = self.histogram.getIndex()
        h = self.histogram.getData()

        b2 = self.histogram2.getIndex()
        h2 = self.histogram2.getData()

        self.histogramline.set_data(b,h)
        self.histogramline2.set_data(b2,h2)
        #self.histogramAxis.set_ylim(0,max(h))
        #self.histogramAxis.set_xlim(0,max(b))
        
        
        
        
        
        self.histogramAxis.relim()
        self.histogramAxis.autoscale_view(True, True, True)        
        
        self.canvas.draw()
        
        

        # self.correlationAxis.clear()
        # index = self.correlation.getIndex()
        # data = self.correlation.getDataNormalized()
        # self.plt_correlation = self.correlationAxis.plot(
        #     index * 1e-3,
        #     data
        # )
        # self.plt_gauss = self.correlationAxis.plot(
        #     index * 1e-3,
        #     data,
        #     linestyle='--'
        # )
        #self.correlationAxis.axvspan(
            #-coincidenceWindow/1000.,
            #coincidenceWindow/1000.,
            #color='green',
            #alpha=0.3
        #)
        # self.correlationAxis.set_xlabel('time (ns)')
        # self.correlationAxis.set_ylabel('normalized correlation')
        # self.correlationAxis.set_title('Correlation between A and B')
        # self.correlationAxis.grid(True)

        # Generate nicer plots
        

        # #self.measurements_dirty = False

        # # Update the plot with real numbers
        #self.updateCounterPlot()
    
    def save_hist_data(self):
        print('bloop')
        hist_data = np.zeros((len(self.bins), 2))
        hist_data[:,0] = self.getdata #set first column with time data
        hist_data[:,1] = self.bins #set second column with countrate data
        append = '_hist_data.txt' #string to append to sample name
        self.check_filename(append)
        np.savetxt(self.app.settings['save_dir']+"/"+ self.app.settings['sample'] + append, hist_data, fmt='%f')
        #np.savetxt(r"C:\Users\Ginger Lab\Desktop\JamesScope\data\histdata.txt", hist_data, fmt='%f')
    
    def clear_plot(self):
        self.synchronized.clear()
        # self.counter.clear()
        # self.histogram.clear()
    
    def check_filename(self, append):
        '''
        If no sample name given or duplicate sample name given, fix the problem by appending a unique number.
        append - string to add to sample name (including file extension)
        '''
        samplename = self.app.settings['sample']
        filename = samplename + append
        directory = self.app.settings['save_dir']
        if samplename == "":
            self.app.settings['sample'] = int(time.time())
        if (os.path.exists(directory+"/"+filename)):
            self.app.settings['sample'] = samplename + str(int(time.time()))
