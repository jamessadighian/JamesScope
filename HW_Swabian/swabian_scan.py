from HW_PI_PiezoStage.PiezoStage_Scan import PiezoStage_Scan
from ScopeFoundry import Measurement
from ScopeFoundry.helper_funcs import sibling_path, load_qt_ui_file
import pyqtgraph as pg
import numpy as np
import time
import pickle
import os.path
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
from pyqtgraph.Point import Point
import customplotting.mscope as cpm
from TimeTagger import Coincidences, Counter, Correlation, createTimeTagger, freeTimeTagger, Histogram


class Swabian_Scan(PiezoStage_Scan):

    name = "Swabian_Scan"

    def setup(self):
        PiezoStage_Scan.setup(self)

        self.tt_hw = self.app.hardware['timetagger']
        self.pi_device_hw = self.app.hardware['piezostage']

        self.settings.New("IntTime", unit="s", dtype=float, vmin=1e-3, vmax=100*60*60, initial=1)
        self.settings.New("histogram_n_values", dtype=int, ro=False, vmin=0, vmax=100e6, initial=1000)
        self.settings.New("histogram_bin_width", dtype=int, ro=False, vmin=0, vmax=100e6, initial=1000)#removed si=True to keep units from auto-changing
#        self.settings.New("Tacq", unit="s", dtype=float, vmin=1e-3, vmax=100*60*60, initial=1) #removed si=True to keep units from auto-changing
        #self.settings.New("Resolution", dtype=int, choices=[("4 ps", 4), ("8 ps", 8), ("16 ps", 16), ("32 ps", 32), ("64 ps", 64), ("128 ps", 128), ("256 ps", 256), ("512 ps", 512)], initial=4)
        #self.settings.New("count_rate0", dtype=int, ro=True, vmin=0, vmax=100e6)
        #self.settings.New("count_rate1", dtype=int, ro=True, vmin=0, vmax=100e6)

    def setup_figure(self):
        PiezoStage_Scan.setup_figure(self)

        #setup ui for picoharp specific settings
        #details_groupBox = self.set_details_widget(widget = self.settings.New_UI(include=["Tacq", "Resolution", "count_rate0", "count_rate1"]))
        details_groupBox = self.set_details_widget(widget = self.settings.New_UI(include=["IntTime"]))
        widgets = details_groupBox.findChildren(QtGui.QWidget)
        tacq_spinBox = widgets[1]
        #resolution_comboBox = widgets[4]
        #count_rate0_spinBox = widgets[6]
        #count_rate1_spinBox = widgets[9]
        #connect settings to ui
        
        print(self.settings.mychannel)
        temp = self.settings.mychannel.value
        print(temp)
        self.settings.IntTime.connect_to_widget(tacq_spinBox)
             
        self.settings.histogram_n_values.connect_bidir_to_widget(self.ui.hist_numbins_doubleSpinBox)
        self.settings.histogram_bin_width.connect_bidir_to_widget(self.ui.hist_binwidth_doubleSpinBox)
        
        #self.picoharp_hw.settings.Resolution.connect_to_widget(resolution_comboBox)
        #self.picoharp_hw.settings.count_rate0.connect_to_widget(count_rate0_spinBox)
        #self.picoharp_hw.settings.count_rate1.connect_to_widget(count_rate1_spinBox)

        tacq_spinBox.valueChanged.connect(self.update_estimated_scan_time)
        self.update_estimated_scan_time()

        #save data buttons
        self.ui.save_image_pushButton.clicked.connect(self.save_intensities_image)
        self.ui.save_array_pushButton.clicked.connect(self.save_intensities_data)
        self.ui.save_histo_pushButton.clicked.connect(self.save_histogram_arrays)
    
        #setup imageview
        self.imv = pg.ImageView()
        self.imv.getView().setAspectLocked(lock=False, ratio=1)
        self.imv.getView().setMouseEnabled(x=True, y=True)
        self.imv.getView().invertY(False)
        roi_plot = self.imv.getRoiPlot().getPlotItem()
        roi_plot.getAxis("bottom").setLabel(text="Time (ns)")

    def update_estimated_scan_time(self):
        try:
            self.overhead = self.x_range * self.y_range * .055 #determined by running scans and timing
            scan_time = self.x_range * self.y_range * self.settings["IntTime"] + self.overhead #need to figure out how to calculate acquisition time here
            self.ui.estimated_scan_time_label.setText("Estimated scan time: " + "%.2f" % scan_time + "s")
        except:
            pass
            
    def update_display(self):
        PiezoStage_Scan.update_display(self)
        if hasattr(self, 'sum_intensities_image_map'):
            #self.picoharp_hw.read_from_hardware() #will need to figure out what this does and replace it
            if not self.interrupt_measurement_called:
                seconds_left = ((self.x_range * self.y_range) - self.pixels_scanned) * self.settings["IntTime"] + self.overhead
                self.ui.estimated_time_label.setText("Estimated time remaining: " + "%.2f" % seconds_left + "s")
            self.img_item.setImage(self.sum_intensities_image_map) #update stage image

            #update imageview
            self.times = self.time_data[:, 0, 0]*1e-3
            self.imv.setImage(img=self.hist_data, autoRange=False, autoLevels=True, xvals=self.times)
            self.imv.show()
            self.imv.window().setWindowFlag(QtCore.Qt.WindowCloseButtonHint, False) #disable closing image view window

            #update progress bar
            progress = 100 * ((self.pixels_scanned+1)/np.abs(self.x_range*self.y_range))
            self.ui.progressBar.setValue(progress)
            self.set_progress(progress)
            pg.QtGui.QApplication.processEvents()

    def pre_run(self):
        try:
            PiezoStage_Scan.pre_run(self) #setup scan parameters
            #self.picoharp = self.picoharp_hw.picoharp
            self.check_filename("_raw_PL_hist_data.pkl")
    
            dirname = self.app.settings['save_dir']        
            self.check_filename('_histdata.dat')
            sample_filename = self.app.settings['sample']
            self.hist_filename = os.path.join(dirname, sample_filename + '_histdata.dat')
            self.check_filename('_timedata.dat')
            self.time_filename = os.path.join(dirname,  sample_filename + '_timedata.dat')
            
            #hist_len = self.num_hist_chans
            hist_len=self.settings['histogram_n_values'] #does this need to be equal to number of bins??? james...test this out.
            #hist_len=1000
            #Use memmaps to use less memory and store data into disk
            self.hist_data= np.memmap(self.hist_filename,dtype='float32',mode='w+',shape=(hist_len, self.x_range, self.y_range))
            self.time_data= np.memmap(self.time_filename,dtype='float32',mode='w+',shape=(hist_len, self.x_range, self.y_range))
    
            #Store histogram sums for each pixel
            self.sum_intensities_image_map = np.zeros((self.x_range, self.y_range), dtype=float)
    
            scan_time = self.x_range * self.y_range * self.settings["IntTime"] #* 1e-3 #s
            self.ui.estimated_scan_time_label.setText("Estimated scan time: " + "%.2f" % scan_time + "s")
        except:
            pass

    def scan_measure(self):
        """
        Data collection for each pixel.
        """
        print("before scan")
        #t0 = time.time()
        data = self.measure_hist()
        #print(str(time.time()-t0), " measure_hist")
        #t1 = time.time()
        self.time_data[:, self.index_x, self.index_y], self.hist_data[:, self.index_x, self.index_y] = data
        self.sum_intensities_image_map[self.index_x, self.index_y] = sum(data[1])
#        self.time_data.flush()
#        self.hist_data.flush()
        #print(str(time.time()-t1), " rest of scan_measure")
        
        
        #print("LOOK index_y: {}".format(self.index_y))
        #print("LOOK index_x: {}".format(self.index_x))
        
        
        '''
        i think helen added the part below to switch to the numpy save...how do i go back to sarthak's pickle? look at old scan_measure function
        '''
        
        # save a 2D numpy array of data arrays after scanning all indices
        # save a 2D numpy array of time arrays after scanning all indices
        if (self.index_y == self.y_range-1) and (self.index_x == self.x_range-1):
            w, h = self.x_range, self.y_range
            matrix = [[0 for x in range(w)] for y in range(h)]
            self.save_data = np.array(matrix, dtype=object)
            self.save_time = np.array(matrix, dtype=object)
            
            for row in range(h):
                for col in range(w):
                    self.save_data[row][col] = self.hist_data[:, row, col]
                    self.save_time[row][col] = self.time_data[:, row, col]
        
        print("after scan")

    def post_run(self):
        """
        Export data.
        """
        PiezoStage_Scan.post_run(self)
        save_dict = {"Histogram data": self.hist_data, "Time data": self.time_data,
                 "Scan Parameters":{"X scan start (um)": self.x_start, "Y scan start (um)": self.y_start,
                                    "X scan size (um)": self.x_scan_size, "Y scan size (um)": self.y_scan_size,
                                    "X step size (um)": self.x_step, "Y step size (um)": self.y_step},
                                    "PicoHarp Parameters":{"Acquisition Time (s)": self.settings['IntTime']}}#,
                                                              #"Resolution (ps)": self.settings['Resolution']} }
        print('about to save daddy')
        pickle.dump(save_dict, open(self.app.settings['save_dir']+"/"+self.app.settings['sample']+"_raw_PL_hist_data.pkl", "wb"))
        print('just saved daddy')
    def measure_hist(self):
        """ Read from Swabian """
        print(self.settings.mychannel)
        
        #self.tt_hw = self.app.hardware['timetagger']   
        #ph = self.picoharp_hw.picoharp           
        self.histogram = Histogram(self.tt_hw.tagger, -1*self.settings.mychannel.value, -1, self.settings['histogram_bin_width'], self.settings['histogram_n_values'])
        #        self.histogram = Histogram(self.tt_hw.tagger*-1, self.settings.mychannel.value, 1, 1000, 1000)
# =============================================================================
#         while not self.interrupt_measurement_called:
#             print("while")
#             time.sleep(1)
# =============================================================================
        
        #while not ph.check_done_scanning():
        #    if self.interrupt_measurement_called:
        #        break
        #    ph.read_histogram_data()
        
        
        
        #time.sleep(1)
        
        
        '''
        '''
        time.sleep(self.settings['IntTime'])
        print('IntTime =' +str(self.settings['IntTime']))
        '''
        '''
        
        
        
        #print(self.settings.mychannel.value)
        #ph.stop_histogram()
        #ph.read_histogram_data()
        
        self.histogram_data=self.histogram.getData()
        self.time_array=self.histogram.getIndex()
        
        #print("time array")
        #print(self.time_array)
        #print("histogram array")
        #print(self.histogram_data)
        #print("printed all arrays")
        
        return self.time_array, self.histogram_data

    def save_intensities_data(self):
        transposed = np.transpose(self.sum_intensities_image_map) #transpose so data visually makes sense
        PiezoStage_Scan.save_intensities_data(self, transposed, 'swabian')

    def save_intensities_image(self):
        PiezoStage_Scan.save_intensities_image(self, self.sum_intensities_image_map, 'swabian')
        
    def save_histogram_arrays(self):
        PiezoStage_Scan.save_histogram_arrays(self, self.save_data, self.save_time, 'swabian')
