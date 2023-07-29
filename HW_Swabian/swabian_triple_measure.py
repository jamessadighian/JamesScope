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

class SwabianTriple(Measurement):
    
    # this is the name of the measurement that ScopeFoundry uses when displaying your measurement and saving data related to it
    name='swabian_triple_measure'
    
    def setup(self):
        """0
        Runs once during App initialization.
        This is the place to load a user interface file,
        define settings, and set up data structures. 
        """
        
        self.display_update_period = 0.1 #seconds
        
        S = self.settings                               #create variable S, which is all the settings
        #S.New('continuous', dtype=bool, initial=False)  #new variable in S called continuous
        S.New("counter_n_values", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("counter_bin_width", dtype=int, ro=False, vmin=0, vmax=100e6)
        S.New("histogram_n_values", dtype=int, ro=False, vmin=0, vmax=100e12, initial=10000)
        S.New("histogram_bin_width", dtype=int, ro=False, vmin=0, vmax=100e12, initial=100)
        S.New("g2_n_values", dtype=int, ro=False, vmin=0, vmax=100e12, initial=1000)
        S.New("g2_bin_width", dtype=int, ro=False, vmin=0, vmax=100e12, initial=1000)
        # UI 
        self.ui_filename = sibling_path(__file__,"swabian_triple_measure.ui")    #this whole section just loads the ui file
        self.ui = load_qt_ui_file(self.ui_filename)
        self.ui.setWindowTitle(self.name)
        self.ui.setWindowTitle('TTTR-style bullshit')

        self.elapsed_time = 0                               #creates a counter and empty data arrays
        #self.xdata = [] #array storing countrate data
        #self.ydata = [] #array storing time points
        
    
    def setup_figure(self):
        S = self.settings                           #creates instance of S within this function?
        #self.tt_hw = self.app.hardware['timetagger'] #creates instance of the timetagger hw in this function?
        
        #self.corrbinwidth = 1000
        
        
        #connect events/settings to ui
        #S.progress.connect_bidir_to_widget(self.ui.progressBar)
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.interrupt_pushButton.clicked.connect(self.interrupt)
        #S.continuous.connect_to_widget(self.ui.continuous_checkBox)
        
        
        
        #self.corrbinwidth.connect_bidir_to_widget(self.ui.picoharp_tacq_doubleSpinBox)
        #self.corrbins.connect_bidir_to_widget(self.ui.picoharp_tacq_doubleSpinBox)
        #self.count_rate0.connect_to_widget(self.ui.ch0_label)
        #self.count_rate1.connect_to_widget(self.ui.ch1_label)
        #self.histbinwidth.connect_bidir_to_widget(self.ui.hist_binwidth_doubleSpinBox)
        #self.histbins.connect_bidir_to_widget(self.ui.hist_numbins_doubleSpinBox)
        S.counter_n_values.connect_bidir_to_widget(self.ui.counter_numbins_doubleSpinBox)
        S.counter_bin_width.connect_bidir_to_widget(self.ui.counter_binwidth_doubleSpinBox)        
        S.histogram_n_values.connect_bidir_to_widget(self.ui.hist_numbins_doubleSpinBox)
        S.histogram_bin_width.connect_bidir_to_widget(self.ui.hist_binwidth_doubleSpinBox)
        S.g2_n_values.connect_bidir_to_widget(self.ui.g2_numbins_doubleSpinBox)
        S.g2_bin_width.connect_bidir_to_widget(self.ui.g2_binwidth_doubleSpinBox)
        
        '''
        
        james come back and connect these later - 20220907
        '''
        self.ui.save_data_pushButton.clicked.connect(self.save_hist_data)
        self.ui.clearplot_pushButton.clicked.connect(self.clear_plot)
        
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
        #self.counterAxis = self.fig.add_subplot(211)
        #self.CorrelationAxis = self.fig.add_subplot(212)
        self.counterAxis = self.fig.add_subplot(311)
        self.CorrelationAxis = self.fig.add_subplot(312)
        self.histogramAxis = self.fig.add_subplot(313)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, parent = None) #self)
        self.ui.plot_groupBox.layout().addWidget(self.toolbar)
        self.ui.plot_groupBox.layout().addWidget(self.canvas)
        
        self.mylabelsize=8
        
        self.counterAxis.set_xlabel('time (s)', fontsize=self.mylabelsize)
        self.counterAxis.set_xlim(0,100)
        self.counterAxis.set_ylabel('count rate \n (kEvents/s)', fontsize=self.mylabelsize)
        self.counterAxis.set_title('Count rate', fontsize=self.mylabelsize)
        self.counterAxis.tick_params(axis='both', labelsize=8)
        
        self.CorrelationAxis.set_xlabel('time', fontsize=self.mylabelsize)
        self.CorrelationAxis.set_xlim(0,100)
        self.CorrelationAxis.set_ylim(0,1)
        self.CorrelationAxis.set_ylabel('g2(t)', fontsize=self.mylabelsize)
        self.CorrelationAxis.set_title('correlation', fontsize=self.mylabelsize)
        # self.counterAxis.legend(['A', 'B', 'coincidences'])
        self.CorrelationAxis.grid(True)
        self.CorrelationAxis.tick_params(axis='both', labelsize=8)
        
        self.histogramAxis.set_xlabel('time delay', fontsize=self.mylabelsize)

        self.histogramAxis.set_ylabel('intensity', fontsize=self.mylabelsize)
        self.histogramAxis.set_title('Histogram', fontsize=self.mylabelsize)
        self.histogramAxis.tick_params(axis='both', labelsize=8)
        
        self.counterline, = self.counterAxis.plot([],[])
        self.counterline2, = self.counterAxis.plot([],[])
        self.correlationline, = self.CorrelationAxis.plot([],[])
        self.histogramline, = self.histogramAxis.plot([],[])
        
        self.fig.tight_layout()
        
        
        
        
        
        ##self.ui.plotGroupBox.layout().addWidget(self.toolbar)
        ##self.ui.plotGroupBox.layout().addWidget(self.canvas)     #i don't know what this does
        '''
        Runs once during App initialization, after setup()
        This is the place to make all graphical interface initializations,
        build plots, etc.
        
        20220906 commented getCounterNormalizationFactor so i can swap the counteraxis to correlation
        
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
        #sw_hw = self.app.hardware['timetagger']
        #sw = self.swabian = sw_hw.tt
        
        #tt_hw = self.app.hardware['timetagger']

        #sleep_time = self.display_update_period
        
        sleep_time = self.display_update_period
        
        t0 = time.time()
        
        '''
        Version with no synchronizer
        '''

        # self.counter = Counter(self.tt_hw.tagger, channels=[2, 3], binwidth=100000000000, n_values=1000)
        
        # self.corrbinwidth=self.settings['g2_bin_width']
        # self.corrbins=self.settings['g2_n_values']
        

        # self.correlation = Correlation(self.tt_hw.tagger, 2, 3, self.corrbinwidth, self.corrbins)#binwidth=int(1e9), n_values=10000)

        # self.histogram = Histogram(self.tt_hw.tagger, 2, -1, self.settings['histogram_bin_width'], self.settings['histogram_n_values'])
        # while not self.interrupt_measurement_called:
        #     time.sleep(.01)


        '''
        version with synchronizer
        '''
        
        self.synchronized = SynchronizedMeasurements(self.tt_hw.tagger)

        # This FileWriter will not start automatically, it waits for 'synchronized'
        #self.filewriter = FileWriter(synchronized.getTagger(), tempdir.name + os.sep + "filewriter", [2, 3])
        taggerSync=self.synchronized.getTagger()

        self.counter = Counter(taggerSync, channels=[-2, -3], binwidth=100000000000, n_values=1000)

        self.corrbinwidth=self.settings['g2_bin_width']
        self.corrbins=self.settings['g2_n_values']

        self.correlation = Correlation(taggerSync, -2, -3, self.corrbinwidth, self.corrbins)

        self.histogram = Histogram(taggerSync, -2, -1, self.settings['histogram_bin_width'], self.settings['histogram_n_values'])
        
        
        self.synchronized.start()
        while not self.interrupt_measurement_called:
            time.sleep(.01)
        #self.elasped_time = 0
        
        # save_dict = {
        #              'time_histogram': countdata,
        #              'time_array': timedata
        #             }        
        
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
        

        self.count1 = self.counter.getData().T[:,0] * self.getCounterNormalizationFactor()
        

        self.count2 = self.counter.getData().T[:,1] * self.getCounterNormalizationFactor()        
#        print(np.shape(a))
        self.counttime = self.counter.getIndex() * 1e-12

        #print('test1.6')
        self.counterline.set_data(self.counttime, self.count1)
        self.counterline2.set_data(self.counttime, self.count2)
#        self.counterAxis.plot(                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          # self.counter.getIndex() * 1e-12,
#              self.counter.getData().T[:,0]* self.getCounterNormalizationFactor()
#              )
        #self.counterAxis.set_ylim(0,max(d))
        #print('test1.7')
        #self.counterAxis.set_ylim(0,abs(max(a)))
        self.counterAxis.set_ylim(0,max(max(self.count1), max(self.count2)))
        #print('test1.8')
        # self.counterAxis.set_xlabel('time (s)')
        # self.counterAxis.set_ylabel('count rate (kEvents/s)')
        # self.counterAxis.set_title('Count rate')
        # # self.counterAxis.legend(['A', 'B', 'coincidences'])
        self.counterAxis.legend(['Channel 2', 'Channel 3'])
        self.counterAxis.relim()
        self.counterAxis.autoscale_view(True, True, True)
       
        
        
        #print('test2')
        self.d = self.correlation.getDataNormalized()
        self.t = self.correlation.getIndex()

        self.correlationline.set_data(self.t, self.d)
        self.CorrelationAxis.set_xlim(min(self.t),max(self.t))
        
        self.CorrelationAxis.set_ylim(min(self.d),max(self.d)*1.1)
        #self.CorrelationAxis.set_ylim(abs(min(self.d)-(1.1*min(self.d))),abs(max(self.d))*1.1)
        self.CorrelationAxis.relim()
        self.CorrelationAxis.autoscale_view(True, True, True)
        
        self.b = self.histogram.getIndex()
        #print(np.shape(self.b))
        self.h = self.histogram.getData()
        #print(np.shape(self.h))
        
        self.histogramline.set_data(self.b,self.h)
        #self.histogramAxis.set_ylim(0,max(h))
        #self.histogramAxis.set_xlim(0,max(b))
        self.histogramAxis.relim()
        self.histogramAxis.autoscale_view(True, True, True)        
        
        self.canvas.draw()
        
        

        # self.correlationAxis.clear()
        # index = self.correlation.getIndex()
        # data = self.correlation.getDataNormalized()
        # self.plt_correlation  = self.correlationAxis.plot(
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
        print('daddy im saving as hard as i can')
        
        count_data = np.zeros((len(self.counttime), 2))
        count_data[:,0] = self.counttime #set first column with time data
        count_data[:,1] = (self.count1+self.count2) #set second column with countrate data
        append_count = '_count_data.txt' #string to append to sample name
        
        hist_data = np.zeros((len(self.b), 2))
        hist_data[:,0] = self.b #set first column with time data
        hist_data[:,1] = self.h #set second column with countrate data
        append = '_hist_data.txt' #string to append to sample name
        
        corr_data=np.zeros((len(self.d), 2))
        corr_data[:,0] = self.t
        corr_data[:,1] = self.d
        append_g2 = '_corr_data.txt' #string to append to sample name
        
        self.check_filename(append)
        np.savetxt(self.app.settings['save_dir']+"/"+ self.app.settings['sample'] + append_count, count_data, fmt='%f')
        np.savetxt(self.app.settings['save_dir']+"/"+ self.app.settings['sample'] + append, hist_data, fmt='%f')
        np.savetxt(self.app.settings['save_dir']+"/"+ self.app.settings['sample'] + append_g2, corr_data, fmt='%f')
        np.savetxt(r"C:\Users\Ginger Lab\Desktop\triplecountdata.txt", count_data, fmt='%f') 
        np.savetxt(r"C:\Users\Ginger Lab\Desktop\triplehistdata.txt", hist_data, fmt='%f')
        np.savetxt(r"C:\Users\Ginger Lab\Desktop\tripleg2data.txt", corr_data, fmt='%f')
        
        print('finished saving daddy')
    
    def clear_plot(self):
        self.synchronized.clear()
    
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
