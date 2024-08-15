import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext
import serial.tools.list_ports
from serial import Serial
import xml.etree.ElementTree as ET
import csv
import threading
from datetime import datetime
import time
import ttkbootstrap as ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import matplotlib.animation as animation
from matplotlib import style

style.use("ggplot")
fig = Figure(figsize=(8,3), dpi=100)

class SerialMonitor:
    def __init__(self, master):
        self.master = master
        self.window = ttk.Style(theme='united')
        self.master.title("FLE Serial Monitor")
        self.master.geometry("1400x600")

        self.cTableContainer = tk.Canvas(self.master)
        self.fTable = tk.Frame(self.cTableContainer)
        sbHorizontalScrollBar = tk.Scrollbar(self.master)
        sbVerticalScrollBar = tk.Scrollbar(self.master)
        self.cTableContainer.config(xscrollcommand=sbHorizontalScrollBar.set,
        yscrollcommand=sbVerticalScrollBar.set, highlightthickness=0)
        sbHorizontalScrollBar.config(orient=tk.HORIZONTAL, command=self.cTableContainer.xview)
        sbVerticalScrollBar.config(orient=tk.VERTICAL, command=self.cTableContainer.yview)

        sbHorizontalScrollBar.pack(fill=tk.X, side=tk.BOTTOM, expand=tk.FALSE)
        sbVerticalScrollBar.pack(fill=tk.Y, side=tk.RIGHT, expand=tk.FALSE)
        self.cTableContainer.pack(fill=tk.BOTH, side=tk.LEFT, expand=tk.TRUE)
        self.cTableContainer.create_window(0, 0, window=self.fTable, anchor=tk.NW)

        ######################FRAMES
        #Voltage Frame
        self.cell_frame = tk.LabelFrame(self.fTable, text="Voltage (V)", bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.cell_frame.grid(row=3, column=0, sticky='nsew')
        #Temp Frame
        self.temp_frame = tk.LabelFrame(self.fTable, text="Temperature (C)", bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.temp_frame.grid(row=3, column=1, sticky='nsew')
        #Cell SOC Frame
        self.soc_frame = tk.LabelFrame(self.fTable, text="State of Charge(SOC) (%)", bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.soc_frame.grid(row=3, column=2, sticky='nsew')
        #Pack Frame
        self.pack_frame = tk.LabelFrame(self.fTable, bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.pack_frame.grid(row=3, column=3, padx=20, columnspan=2, sticky='nsew', pady=10)
        #Log Frame
        self.log_frame = tk.LabelFrame(self.fTable, bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.log_frame.grid(row=4, column=6, sticky='ew')
        #Error Frame
        self.error_frame =tk.LabelFrame(self.fTable, bd=3, padx=10, pady=10, relief=tk.RIDGE)
        self.error_frame.grid(row=4, column=7, padx=11)
        #########################

        #Making equal size columns and adding weight and uniformity to them
        columns = []
        for i in range(7):
            frame = tk.Frame(self.fTable)
            columns.append(frame)

        self.master.grid_rowconfigure(0, weight=1)
        for column, f in enumerate(columns):
            f.grid(row=0, column=column, sticky="nsew")
            self.fTable.grid_columnconfigure(column, weight=1, uniform="column")

        self.create_widgets()
            
        #Flag to indicate if the serial connection is active
        self.connection_active = False
        #Container for each cell connected to BMS along with information related to each cell
        self.cells_update = {}
        self.cells = {}
        self.cells_update['Timestamp'] = datetime.now().strftime("%m-%d-%y-%H:%M:%S")
        #List of error codes
        self.error_codes = set()

        #CSV Logging
        self.csv_header = []
        self.firstLog_Flag = True
        self.parse_data = []
        
        #Set logging time
        self.delta_t = 5
         
    def create_widgets(self):
        ############# ALL LABELS AND SCROLLABLE TEXT ###################

        #This function inserts all ports into port combobox
        self.populate_ports()

        #Cell data label
        self.cell_data_label =ttk.Label(self.fTable, text="Cell Data", font=("Arial",16,'bold'), relief='solid', anchor='center')
        self.cell_data_label.grid(row=2, column=0, ipadx=5, ipady=0, columnspan=3, sticky='nsew')

        #Pack data label
        self.cell_data_label =ttk.Label(self.fTable, text="Pack Data", font=("Arial",16,'bold'), relief='solid', anchor='center')
        self.cell_data_label.grid(row=2, column=3, ipadx=5, pady=0, columnspan=2, sticky='nsew')

        ################## CELL LABELS AND TEXTFIELDS ########################

        ############ PACK CURRENT
        #Current 0 Label
        self.cell1_label = ttk.Label(self.pack_frame, text='Current (mA)')
        self.cell1_label.pack()
        #Current 0 scrollable text
        self.c0_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.c0_textField.pack()
        #Max Current Label
        self.maxCurr_label = ttk.Label(self.pack_frame, text='Max Current (mA)')
        self.maxCurr_label.pack()
        #Max Current scrollable text
        self.maxCurr_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.maxCurr_textField.pack()
        ############

        ############ PACK SOC
        #Pack SOC Label
        self.packSOC_label = ttk.Label(self.pack_frame, text='Pack SOC (%)')
        self.packSOC_label.pack()
        #Pack SOC scrollable text
        self.packSOC_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.packSOC_textField.pack()
        #############

        ############ PACK CAPACITY
        #Pack Capapcity Label
        self.packCap_label = ttk.Label(self.pack_frame, text='Total Capacity (Ah)')
        self.packCap_label.pack()
        #Pack SOC scrollable text
        self.packCap_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.packCap_textField.pack()
        #############


        ################## VOLTAGE
        #Voltage 0 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 1')
        self.cell0_label.pack()
        #Voltage 0 scrollable text
        self.v0_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v0_textField.pack()
        #Voltage 1 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 2')
        self.cell0_label.pack()
        #Voltage 1 scrollable text
        self.v1_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v1_textField.pack()
        #Voltage 2 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 3')
        self.cell0_label.pack()
        #Voltage 2 scrollable text
        self.v2_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v2_textField.pack()
        #Voltage 3 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 4')
        self.cell0_label.pack()
        #Voltage 3 scrollable text
        self.v3_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v3_textField.pack()
        #Voltage 4 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 5')
        self.cell0_label.pack()
        #Voltage 4 scrollable text
        self.v4_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v4_textField.pack()
        #Voltage 5 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 6')
        self.cell0_label.pack()
        #Voltage 5 scrollable text
        self.v5_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v5_textField.pack()
        #Voltage 6 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 7')
        self.cell0_label.pack()
        #Voltage 6 scrollable text
        self.v6_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v6_textField.pack()
        #Voltage 7 Label
        self.cell0_label = ttk.Label(self.cell_frame, text='Voltage 8')
        self.cell0_label.pack()
        #Voltage 7 scrollable text
        self.v7_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.v7_textField.pack()
        #Mean Voltage Label
        self.meanVoltage_label = ttk.Label(self.cell_frame, text='Mean Voltage', font=('bold'))
        self.meanVoltage_label.pack()
        #Mean Voltage scrollable text
        self.meanVoltage_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.meanVoltage_textField.pack()
        #Pack Voltage Label
        self.packVoltage_label = ttk.Label(self.pack_frame, text='Pack Voltage (V)')
        self.packVoltage_label.pack()
        #Pack Voltage scrollable text
        self.packVoltage_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.packVoltage_textField.pack()
        #Terminal Voltage Label
        self.termVolt_label = ttk.Label(self.pack_frame, text='Terminal Voltage (V)')
        self.termVolt_label.pack()
        #Terminal Voltage scrollable text
        self.termVolt_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.termVolt_textField.pack()
        #Drain Voltage Label
        self.drainVolt_label = ttk.Label(self.pack_frame, text='Drain Voltage (V)')
        self.drainVolt_label.pack()
        #Drain Voltage scrollable text
        self.drainVolt_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.drainVolt_textField.pack()
        #Safe Voltage Label
        self.vSafe_label = ttk.Label(self.pack_frame, text='Safe Voltage (V)')
        self.vSafe_label.pack()
        #Safe Voltage scrollable text
        self.vSafe_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.vSafe_textField.pack()
        #Vbus Label
        self.vBus_label = tk.Label(self.cell_frame, text='Vbus', font=('bold'))
        self.vBus_label.pack()
        #Vbus scrollable text
        self.vBus_textField = tk.Label(self.cell_frame, height=1, width=10)
        self.vBus_textField.pack()
        #############################

        ############### TEMPERATURE
        #Temperature 0 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 1')
        self.temp0_label.pack()
        #Temperature 0 scrollable text
        self.temp0_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp0_textField.pack()
        #Temperature 1 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 2')
        self.temp0_label.pack()
        #Temperature 1 scrollable text
        self.temp1_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp1_textField.pack()
        #Temperature 2 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 3')
        self.temp0_label.pack()
        #Temperature 2 scrollable text
        self.temp2_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp2_textField.pack()
        #Temperature 3 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 4')
        self.temp0_label.pack()
        #Temperature 3 scrollable text
        self.temp3_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp3_textField.pack()
        #Temperature 4 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 5')
        self.temp0_label.pack()
        #Temperature 4 scrollable text
        self.temp4_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp4_textField.pack()
        #Temperature 5 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 6')
        self.temp0_label.pack()
        #Temperature 5 scrollable text
        self.temp5_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp5_textField.pack()
        #Temperature 6 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 7')
        self.temp0_label.pack()
        #Temperature 6 scrollable text
        self.temp6_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp6_textField.pack()
        #Temperature 7 label
        self.temp0_label = ttk.Label(self.temp_frame, text='Temperature 8')
        self.temp0_label.pack()
        #Temperature 7 scrollable text
        self.temp7_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.temp7_textField.pack()
        #Temperature Gradient label
        self.tempGrad_label = ttk.Label(self.temp_frame, text='Temperature Gradient', font=('bold'))
        self.tempGrad_label.pack()
        #Temperature Gradient scrollable text
        self.tempGrad_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.tempGrad_textField.pack()
        #Mean temperature label
        self.meanTemp_label = ttk.Label(self.temp_frame, text='Mean Temperature', font=('bold'))
        self.meanTemp_label.pack()
        #Mean temperature scrollable text
        self.meanTemp_textField = tk.Label(self.temp_frame, height=1, width=5)
        self.meanTemp_textField.pack()
        ###################

        ############## SOC
        #SOC 1 Label
        self.soc0_label = ttk.Label(self.soc_frame, text='SOC 1')
        self.soc0_label.pack()
        #SOC 1 scrollable text
        self.soc0_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc0_textField.pack()
        #SOC 2 Label
        self.soc1_label = ttk.Label(self.soc_frame, text='SOC 2')
        self.soc1_label.pack()
        #SOC 2 scrollable text
        self.soc1_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc1_textField.pack()
        #SOC 3 Label
        self.soc2_label = ttk.Label(self.soc_frame, text='SOC 3')
        self.soc2_label.pack()
        #SOC 3 scrollable text
        self.soc2_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc2_textField.pack()
        #SOC 4 Label
        self.soc3_label = ttk.Label(self.soc_frame, text='SOC 4')
        self.soc3_label.pack()
        #SOC 4 scrollable text
        self.soc3_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc3_textField.pack()
        #SOC 5 Label
        self.soc4_label = ttk.Label(self.soc_frame, text='SOC 5')
        self.soc4_label.pack()
        #SOC 5 scrollable text
        self.soc4_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc4_textField.pack()
        #SOC 6 Label
        self.soc5_label = ttk.Label(self.soc_frame, text='SOC 6')
        self.soc5_label.pack()
        #SOC 6 scrollable text
        self.soc5_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc5_textField.pack()
        #SOC 7 Label
        self.soc6_label = ttk.Label(self.soc_frame, text='SOC 7')
        self.soc6_label.pack()
        #SOC 7 scrollable text
        self.soc6_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc6_textField.pack()
        #SOC 8 Label
        self.soc7_label = ttk.Label(self.soc_frame, text='SOC 8')
        self.soc7_label.pack()
        #SOC 8 scrollable text
        self.soc7_textField = tk.Label(self.soc_frame, height=1, width=10)
        self.soc7_textField.pack()
        ################################

        ##### TIME INFORMATION
        #Time remaining label
        self.timeRem_label = tk.Label(self.pack_frame, text='Time Remaining (Hrs)')
        self.timeRem_label.pack()
        #Time remaining scrollable text
        self.timeRem_textField = tk.Label(self.pack_frame, height=1, width=10)
        self.timeRem_textField.pack()

        ##### Charging Mode(s) label
        self.chargeMode_label = tk.Label(self.pack_frame, text='Charging Mode', font=('bold'))
        self.chargeMode_label.pack()
        ##### Charging Mode(s) scrollable text
        self.chargeMode_textField = tk.Label(self.pack_frame, height=1, width=10, relief='sunken')
        self.chargeMode_textField.pack()

        ###################### ALL COMBOBOXES AND BUTTONS ########################

        #Baud combobox
        self.baud_combobox = ttk.Combobox(self.fTable, values=["2400","4800","9600","14400", "115200"], state="readonly")
        self.baud_combobox.set("115200")
        self.baud_combobox.grid(row=1, column=1, sticky='nsew')

        #Connect button
        self.connect_button = ttk.Button(self.fTable, text="Connect", command=self.connect)
        self.connect_button.grid(row=1, column=2, sticky='nsew')

        #Disconnect button
        self.disconnect_button = ttk.Button(self.fTable, text="Disconnect", command=self.disconnect, state=tk.DISABLED)
        self.disconnect_button.grid(row=1, column=3, sticky='nsew')

        #Set Log Time Button
        self.interval_label = tk.Label(self.log_frame, text="Logging Interval (s)")
        self.interval_label.pack()
        self.log_input = tk.Text(self.log_frame, height=1, width=4)
        self.log_input.pack()

        self.log_button = ttk.Button(self.log_frame, text='Set', command=self.set_deltaT)
        self.log_button.pack()

        #All export buttons
        self.export_txt_button = ttk.Button(self.fTable, text="Export as TXT", command=self.export_txt, state=tk.DISABLED)
        self.export_txt_button.grid(row=1, column=4, sticky='nsew', ipady=10)

        self.export_csv_button = ttk.Button(self.fTable, text="Export as CSV", command=self.export_csv, state=tk.DISABLED)
        self.export_csv_button.grid(row=1, column=5, sticky='nsew', )

        self.export_xml_button = ttk.Button(self.fTable, text="Export as XML", command=self.export_xml, state=tk.DISABLED)
        self.export_xml_button.grid(row=1, column=6, sticky='nsew')
        #################################

        #Output BMS readouts into textfield
        self.log_text = scrolledtext.ScrolledText(self.fTable, wrap=tk.WORD, width=80, height=20)
        self.log_text.grid(row=3, column=5, columnspan=3, sticky='nsew', pady=12)

        #Error log Readout textfield and label
        self.errorLog_label = tk.Label(self.error_frame, height=1, width=10, text='Error Codes', font=('bold'))
        self.errorLog_label.pack()
        self.errorLog = scrolledtext.ScrolledText(self.error_frame, wrap=tk.WORD, width=15, height=5)
        self.errorLog.pack()

        #Theme Combobox
        self.theme_label = tk.Label(self.fTable, text='Theme:', font=('Arial', 8, 'bold'))
        self.theme_label.grid(row=0, column=7, sticky='e')
        self.theme_combobox = ttk.Combobox(self.fTable, values=[value for value in self.window.theme_names()], state="readonly")
        self.theme_combobox.grid(row=1, column=7, sticky='nsew')
        self.theme_combobox.bind('<<ComboboxSelected>>', self.theme_set)

        ################################# END OF WIDGETS ##################################

    def updateScrollRegion(self):
        self.cTableContainer.update_idletasks()
        self.cTableContainer.config(scrollregion=self.fTable.bbox())

    def theme_set(self, event):
        self.window.theme_use(self.theme_combobox.get())
            
    def populate_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combobox = ttk.Combobox(self.fTable, values=ports, state="readonly")
        self.port_combobox.set('COM3')
        self.port_combobox.grid(row=1, column=0, sticky='nsew')

    def connect(self):
        port = self.port_combobox.get()
        baud = int(self.baud_combobox.get())
        try:
            self.ser = Serial(port, baud, timeout=1)
            self.log_text.delete(1.0, tk.END)
            self.log_text.insert(tk.END, f"Connected to {port} at {baud} baud\n")
            self.disconnect_button["state"] = tk.NORMAL
            self.connect_button["state"] = tk.DISABLED
            self.export_txt_button["state"] = tk.NORMAL
            self.export_csv_button["state"] = tk.NORMAL
            self.export_xml_button["state"] = tk.NORMAL

            self.connection_active = True

            self.thread = threading.Thread(target=self.read_from_port)
            self.thread.start()
            self.t_ref = time.time()
        except Exception as e:
            self.log_text.insert(tk.END, f"Error: {str(e)}\n")

    def disconnect(self):
        self.connection_active = False  # Set the flag to False to stop the reading thread
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
        self.connect_button["state"] = tk.NORMAL
        self.disconnect_button["state"] = tk.DISABLED
        self.export_txt_button["state"] = tk.DISABLED
        self.export_csv_button["state"] = tk.DISABLED
        self.export_xml_button["state"] = tk.DISABLED
        self.log_text.insert(tk.END, "Disconnected\n")

    def read_from_port(self):
        while self.connection_active:  # Check the flag in the reading loop
                try:
                    line = self.ser.readline().decode("utf-8")
                    lineCopy = line
                    lineCopy = lineCopy.replace('\r', '')
                    lineCopy = lineCopy.replace('\n', '')
                    lineCopy = lineCopy.split(' ')
                    if line:
                        self.populate_cells(lineCopy) #Passes each line into a function to check if the line contains desired information
                        self.log_text.insert(tk.END, str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')) + ': ' + line)
                        self.log_text.see(tk.END)
                except Exception as e:
                    if self.connection_active:  # Only log errors if the connection is still active
                        self.log_text.insert(tk.END, f"Error reading from port: {str(e)}\n")
                        continue
                    #break

    def set_deltaT(self):
            try:
                input_val = int(self.log_input.get(1.0, "end-1c"))
                self.delta_t = input_val
                self.log_text.insert(tk.END, "Logging data every: " + str(self.delta_t) + ' seconds\n')
                self.log_text.see(tk.END)
            except Exception as e:
                self.log_text.insert(tk.END, f"Value must be an integer: {str(e)}\n")
                self.log_text.see(tk.END)

    def populate_cells(self, line: list):
        self.cells_update['Timestamp'] = datetime.now().strftime("%m-%d-%y-%H:%M:%S")

        if (("cell" in line) and ("volt" in line) and (not "dev" in line) and (not "pack" in line)):
            self.cells_update['volt' + line[1]] = line[3]
        elif (('mean' in line) and ('cell' in line) and ('voltage' in line)):
            self.cells_update['mean_cell_voltage'] = line[7]
            self.cells_update['pack_volt'] = line[3]
        elif ("term" in line):
            self.cells_update['term_volt'] = line[2]
        elif ("drain" in line):
            self.cells_update['drain_volt'] = line[2]
        elif (("current" in line) and (not 'Charging' in line)):
            self.cells_update['current'] = line[2]
        elif (("soc" in line) and (not "zp" in line) and (not "total" in line)):
            self.cells_update[line[0] + line[1]] = line[3]
        elif (("total" in line) and ("soc" in line) and (not 'volt' in line)):
            self.cells_update['total_soc'] = line[2]
            self.cells_update['time_remaining'] = line[7]
            self.cells_update['capacity'] = line[4]
        elif ('deviation' in line):
            self.cells_update['temperature_gradient'] = line[3]
            self.cells_update['mean_temp'] = line[6]
        elif ('Vsafe' in line):
            self.cells_update['Vsafe'] = line[1].partition('=')[2]
        elif ('Charging' in line):
            self.cells_update['Charging_Mode'] = line[2]
            self.cells_update['max_current'] = line[5].partition('=')[2]
            self.cells_update['Vbus'] = line[3].partition('=')[2]
        elif ("adc" in line):
            self.cells_update[line[0] + line[1]] = line[3]
        elif ('DTC' in line):
            self.cells_update['Error_Codes'] = line[1]
        #Updating global cells dictionary with freshly grabbed information
        if not (self.cells == self.cells_update):
            self.cells.update(self.cells_update)
            self.update_data()
        #If self.cells has all of the data needed, start writing to log
        if len(self.cells) >= 40:
            self.write_to_parsed_log()

    def update_data(self):
        #Check that self.cells is unempty
        if self.cells:
            #Live update of the temperature
            if 'adc0' in self.cells:
                self.temp0_textField.configure(text=self.cells["adc0"])
            if 'adc1' in self.cells:
                self.temp1_textField.configure(text=self.cells["adc1"])
            if 'adc2' in self.cells:
                self.temp2_textField.configure(text=self.cells["adc2"])
            if 'adc3' in self.cells:
                self.temp3_textField.configure(text=str(self.cells["adc3"]))
            if 'adc4' in self.cells:
                self.temp4_textField.configure(text=str(self.cells["adc4"]))
            if 'adc5' in self.cells:
                self.temp5_textField.configure(text=str(self.cells["adc5"]))
            if 'adc6' in self.cells:
                self.temp6_textField.configure(text=str(self.cells["adc6"]))
            if 'adc7' in self.cells:
                self.temp7_textField.configure(text=str(self.cells["adc7"]))
            if 'mean_temp' in self.cells:
                self.meanTemp_textField.configure(text=str(self.cells["mean_temp"]))
            if 'temperature_gradient' in self.cells:
                self.tempGrad_textField.configure(text=str(self.cells["temperature_gradient"]))

            #Live update of the voltage
            if 'volt0' in self.cells:
                self.v0_textField.configure(text=int(self.cells["volt0"])/10000)
            if 'volt1' in self.cells:
                self.v1_textField.configure(text=int(self.cells["volt1"])/10000)
            if 'volt2' in self.cells:
                self.v2_textField.configure(text=int(self.cells["volt2"])/10000)
            if 'volt3' in self.cells:
                self.v3_textField.configure(text=int(self.cells["volt3"])/10000)
            if 'volt4' in self.cells:
                self.v4_textField.configure(text=int(self.cells["volt4"])/10000)
            if 'volt5' in self.cells:
                self.v5_textField.configure(text=int(self.cells["volt5"])/10000)
            if 'volt6' in self.cells:
                self.v6_textField.configure(text=int(self.cells["volt6"])/10000)
            if 'volt7' in self.cells:
                self.v7_textField.configure(text=int(self.cells["volt7"])/10000)
            if 'mean_cell_voltage' in self.cells:
                self.meanVoltage_textField.configure(text=int(self.cells["mean_cell_voltage"])/1000)
            if 'pack_volt' in self.cells:
                self.packVoltage_textField.configure(text=int(self.cells["pack_volt"])/10000)
            if 'term_volt' in self.cells:
                self.termVolt_textField.configure(text=int(self.cells["term_volt"])/10000)
            if 'drain_volt' in self.cells:
                self.drainVolt_textField.configure(text=int(self.cells["drain_volt"])/10000)
            if 'Vsafe' in self.cells:
                self.vSafe_textField.configure(text=int(self.cells["Vsafe"])/1000)
            if 'Vbus' in self.cells:
                self.vBus_textField.configure(text=int(self.cells["Vbus"])/10000)

            #Live update of the current
            if 'current' in self.cells:
                self.c0_textField.configure(text=str(self.cells["current"]))
            if 'max_current' in self.cells:
                self.maxCurr_textField.configure(text=str(self.cells["max_current"]))
            #Live update of the SOC
            if 'soc0' in self.cells:
                self.soc0_textField.configure(text=int(self.cells['soc0'])/10)
            if 'soc1' in self.cells:
                self.soc1_textField.configure(text=int(self.cells["soc1"])/10)
            if 'soc2' in self.cells:
                self.soc2_textField.configure(text=int(self.cells["soc2"])/10)
            if 'soc3' in self.cells:
                self.soc3_textField.configure(text=int(self.cells["soc3"])/10)
            if 'soc4' in self.cells:
                self.soc4_textField.configure(text=int(self.cells["soc4"])/10)
            if 'soc5' in self.cells:
                self.soc5_textField.configure(text=int(self.cells["soc5"])/10)
            if 'soc6' in self.cells:
                self.soc6_textField.configure(text=int(self.cells["soc6"])/10)
            if 'soc7' in self.cells:
                self.soc7_textField.configure(text=int(self.cells["soc7"])/10)
            if 'total_soc' in self.cells:
                self.packSOC_textField.configure(text=int(self.cells["total_soc"])/10)

            #Live update of Total Capacity
            if 'capacity' in self.cells:
                self.packCap_textField.configure(text=int(self.cells["capacity"])/10000)
            #Live update of time remaining
            if 'time_remaining' in self.cells:
                self.timeRem_textField.configure(text=int(self.cells["time_remaining"])/10000)
            #Live update of charging mode
            if 'Charging_Mode' in self.cells:
                self.chargeMode_textField.configure(text=str(self.cells["Charging_Mode"]))

        #Error Code Live Update
            if 'Error_Codes' in self.cells:
                self.errorLog.delete('1.0', tk.END)
                self.errorLog.insert(tk.END, self.cells['Error_Codes'])
                self.errorLog.see(tk.END)

    #Writes parsed data into a log file
    def write_to_parsed_log(self):
        if self.firstLog_Flag == True:
            self.csv_header = [key for key in self.cells.keys()]
            self.parse_data.extend(self.csv_header)
            self.parse_data.append("\n")
            self.firstLog_Flag = False
        if (time.time() - self.t_ref) > self.delta_t:
            self.parse_data.extend([value for value in self.cells.values()])
            self.parse_data.append("\n")
            self.t_ref = time.time()

    def plot_animate(self):
        navFrame = tk.LabelFrame(self.fTable, bd=3, padx=10, pady=10)
        navFrame.pack_propagate(False)
        plot1 = fig.add_subplot(111)
        canvas = FigureCanvasTkAgg(fig, master = self.fTable)
        canvas.draw()
        canvas.get_tk_widget().grid(row=4,column=2, columnspan=4, pady=10, sticky='ns', padx=20)
        toolbar = NavigationToolbar2Tk(canvas, navFrame)
        toolbar.update()
        navFrame.grid(row=4,column=0, sticky='nsew', pady=10, columnspan=2)

        xar = []
        yar = []
        self.plot_data = self.parse_data
        for data in self.plot_data:
            if isinstance(data, datetime):
                xar.append(data)
            elif isinstance(data, int):
                yar.append(data)
                
        plot1.clear()
        plot1.plot(xar,yar)

    def export_txt(self):
        data = self.log_text.get(1.0, tk.END)
        filename = f"serial_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
        with open(filename, "w") as file:
            file.write(data)
        self.log_text.insert(tk.END, f"Log exported as TXT: {filename}\n")

    def export_csv(self):
        data = ' '.join(self.parse_data)
        filename = f"serial_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.csv"
        with open(f"CSV Exports/{filename}", "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerows([line.split() for line in data.splitlines()])
        self.log_text.insert(tk.END, f"Log exported as CSV: {filename}\n")

    def export_xml(self):
        data = self.log_text.get(1.0, tk.END)
        filename = f"serial_log_{datetime.now().strftime('%Y%m%d%H%M%S')}.xml"
        root = ET.Element("LogData")
        lines = data.splitlines()
        for line in lines:
            entry = ET.SubElement(root, "Entry")
            ET.SubElement(entry, "Data").text = line
        tree = ET.ElementTree(root)
        tree.write(filename)
        self.log_text.insert(tk.END, f"Log exported as XML: {filename}\n")

if __name__ == "__main__":
    root = tk.Tk()
    app = SerialMonitor(root)
    app.plot_animate()
    app.updateScrollRegion()
    root.mainloop()