from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg
import numpy as np
import time
import pickle
import os.path
from pyqtgraph.Qt import QtGui, QtCore
from pyqtgraph.Point import Point
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure
from TimeTagger import Counter

class PiezoStageControl(Measurement):
    name = 'piezostage_control'

    def setup(self):
        self.ui_filename = sibling_path(__file__, "stage_control.ui")
        
        #Load ui file and convert it to a live QWidget of the user interface
        self.ui = load_qt_ui_file(self.ui_filename)

        self.settings.New('step_size', dtype=float, unit='um', vmin=.001)

        self.pi_device_hw = self.app.hardware['piezostage']
        self.tt_hw = self.app.hardware['timetagger']
        self.display_update_period = 0.1
        
    def setup_figure(self):
        self.tt_hw = self.app.hardware['timetagger']
        #connecting settings to ui
        self.pi_device_hw.settings.x_position.connect_to_widget(self.ui.x_label)
        self.pi_device_hw.settings.y_position.connect_to_widget(self.ui.y_label)
        self.settings.step_size.connect_to_widget(self.ui.step_size_spinBox)
        
        #setup ui signals
        self.ui.start_pushButton.clicked.connect(self.start)
        self.ui.up_pushButton.clicked.connect(self.move_up)
        self.ui.right_pushButton.clicked.connect(self.move_right)
        self.ui.down_pushButton.clicked.connect(self.move_down)
        self.ui.left_pushButton.clicked.connect(self.move_left)

        #self.ui.clear_plot_pushButton.clicked.connect(self.clear_plot)

        #plot showing stage area
        self.stage_layout=pg.GraphicsLayoutWidget()
        self.ui.stage_groupBox.layout().addWidget(self.stage_layout)
        self.stage_plot = self.stage_layout.addPlot(title="Stage view")
        self.stage_plot.setXRange(0, 100)
        self.stage_plot.setYRange(0, 100)
        self.stage_plot.setLimits(xMin=0, xMax=100, yMin=0, yMax=100) 

        #arrow indicating stage position
        self.current_stage_pos_arrow = pg.ArrowItem()
        self.current_stage_pos_arrow.setZValue(100)
        self.current_stage_pos_arrow.setPos(0, 0)
        self.stage_plot.addItem(self.current_stage_pos_arrow)
        
        #plot showing counter        
        self.fig = Figure()
        self.counterAxis = self.fig.add_subplot(111)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.toolbar = NavigationToolbar2QT(self.canvas, parent = None) #self)
        self.ui.plot_groupBox.layout().addWidget(self.toolbar)
        self.ui.plot_groupBox.layout().addWidget(self.canvas)
        
        #self.counterAxis.set_xlabel('time (s)')
        self.counterAxis.set_xlim(0,100)
        #self.counterAxis.set_ylabel('count rate (kEvents/s)')
        #self.counterAxis.set_title('Count rate')
        # self.counterAxis.legend(['A', 'B', 'coincidences'])
        self.counterAxis.legend(['Channel 1'])
        self.counterAxis.grid(True)
              
        self.counterline, = self.counterAxis.plot([],[])
        self.counterline2, = self.counterAxis.plot([],[])
        
        self.fig.tight_layout()



    def move_up(self):
        if hasattr(self, 'pi_device') and hasattr(self, 'axes'):
            self.pi_device.MVR(axes=self.axes[2], values=[self.settings['step_size']])
            self.pi_device_hw.read_from_hardware()
            self.current_stage_pos_arrow.setPos(self.pi_device_hw.settings['x_position'], self.pi_device_hw.settings['y_position'])

    def move_right(self):
        if hasattr(self, 'pi_device') and hasattr(self, 'axes'):
            self.pi_device.MVR(axes=self.axes[0], values=[self.settings['step_size']])
            self.pi_device_hw.read_from_hardware()
            self.current_stage_pos_arrow.setPos(self.pi_device_hw.settings['x_position'], self.pi_device_hw.settings['y_position'])

    def move_down(self):
        if hasattr(self, 'pi_device') and hasattr(self, 'axes'):
            self.pi_device.MVR(axes=self.axes[2], values=[-self.settings['step_size']])
            self.pi_device_hw.read_from_hardware()
            self.current_stage_pos_arrow.setPos(self.pi_device_hw.settings['x_position'], self.pi_device_hw.settings['y_position'])

    def move_left(self):
        if hasattr(self, 'pi_device') and hasattr(self, 'axes'):
            self.pi_device.MVR(axes=self.axes[0], values=[-self.settings['step_size']])
            self.pi_device_hw.read_from_hardware()
            self.current_stage_pos_arrow.setPos(self.pi_device_hw.settings['x_position'], self.pi_device_hw.settings['y_position'])
    
    def getCounterNormalizationFactor(self):
        bin_index = self.counter.getIndex()
        # normalize 'clicks / bin' to 'kclicks / second'
        return 1e12 / bin_index[1] / 1e3
    
    
    def run(self):
        self.pi_device = self.pi_device_hw.pi_device
        self.axes = self.pi_device.axes
        
        self.tt_hw = self.app.hardware['timetagger']
        self.counter = Counter(self.tt_hw.tagger, channels=[2, 3], binwidth=100000000000, n_values=1000)
        while not self.interrupt_measurement_called:
            time.sleep(.01)
    def update_display(self):
        '''
        Displays (plots) the data
        This function runs repeatedly and automatically during the measurement run.
        its update frequency is defined by self.display_update_period
        '''
        self.tt_hw = self.app.hardware['timetagger']
        
        d = self.counter.getData().T[:,0] * self.getCounterNormalizationFactor()
        f = self.counter.getData().T[:,1] * self.getCounterNormalizationFactor()

        t = self.counter.getIndex() * 1e-12

        self.counterline.set_data(t, d)
        self.counterline2.set_data(t, f)

        self.counterAxis.set_ylim(0,max(max(d), max(f)))   #will this fix the error regarding the counter measure? why does it work here and not in triple measure?

        self.counterAxis.legend(['Channel 2', 'Channel 3'])
        self.counterAxis.relim()
        self.counterAxis.autoscale_view(True, True, True)
       
        self.canvas.draw()
        
    def clear_plot(self):
        self.counter.clear()