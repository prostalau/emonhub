import time
import json
import Cargo
import os
import glob
from emonhub_interfacer import EmonHubInterfacer

"""
[[UF50]]
    Type = EmonHubMinimalModbusInterfacer
    [[[init_settings]]]
        device = /dev/ttyUSB0
        baud = 9600
    [[[runtimesettings]]]
        pubchannels = ToEmonCMS,
        read_interval = 10
        nodename = UF50
        # prefix = uf50_
        registers = 2,4,6,8,10,11,12,14,16
        names = V,I,P,VA,PF,FR,EI,EE,RI
        precision = 2,3,1,1,3,3,3,3,3
"""

"""class EmonHubUF50Interfacer

UF50 interfacer for use in development

"""

class EmonHubMinimalModbusInterfacer(EmonHubInterfacer):

    def __init__(self, name, device="/dev/modbus", baud=9600):
        """Initialize Interfacer

        """
        # Initialization
        super(EmonHubMinimalModbusInterfacer, self).__init__(name)

        # This line will stop the default values printing to logfile at start-up
        # self._settings.update(self._defaults)

        # Interfacer specific settings
        self._modbus_settings = {
            'read_interval': 10.0,
            'nodename':'uf50',
            'prefix':'',
            'registers': [2,4,6,8,10,11,12,14,16],
            'names': ['V','I','P','VA','PF','FR','EI','EE','RI'],
            'precision': [2,3,1,1,3,3,3,3,3]
        }
        
        self.next_interval = True
        
        # Only load module if it is installed         
        try: 
            import minimalmodbus
            # import serial
            self._log.info("Connecting to Modbus device="+str(device)+" baud="+str(baud))
            
            self._rs485 = minimalmodbus.Instrument(device, 1)
            self._rs485.serial.baudrate = baud
            self._rs485.serial.bytesize = 8
            self._rs485.serial.parity = minimalmodbus.serial.PARITY_NONE
            self._rs485.serial.stopbits = 1
            self._rs485.serial.timeout = 1
            self._rs485.debug = False
            self._rs485.mode = minimalmodbus.MODE_RTU  
            
        except ModuleNotFoundError as err:
            self._log.error(err)
            self._rs485 = False
                    

    def read(self):
        """Read data and process

        Return data as a list: [NodeID, val1, val2]

        """
        
        if int(time.time())%self._settings['read_interval']==0:
            if self.next_interval: 
                self.next_interval = False

                c = Cargo.new_cargo()
                c.names = []
                c.realdata = []
                c.nodeid = self._settings['nodename']
             
                if self._rs485:
                    for i in range(0,len(self._settings['registers'])):
                        valid = True
                        try:
                            value = self._rs485.read_float(int(self._settings['registers'][i]), functioncode=4, number_of_registers=2)
                        except Exception as e:
                            valid = False
                            self._log.error("Could not read register @ "+self._settings['registers'][i]+": " + str(e))  
                        
                        if valid:
                            # replace datafield name with custom name
                            if i<len(self._settings['names']):
                                name = self._settings['names'][i]
                            else:
                                name = "r"+str(self._settings['registers'][i])
                            # apply rounding if set
                            if i<len(self._settings['precision']):
                                value = round(value,int(self._settings['precision'][i]))
                            
                            c.names.append(self._settings['prefix']+name)
                            c.realdata.append(value)
                            # self._log.debug(str(name)+": "+str(value))
                            
                    if len(c.realdata)>0:
                        self._log.debug(c.realdata)
                        return c
                else:
                     self._log.error("Not connected to modbus device")
                    
        else:
            self.next_interval = True
            
        return False


    def set(self, **kwargs):
        for key, setting in self._modbus_settings.items():
            # Decide which setting value to use
            if key in kwargs:
                setting = kwargs[key]
            else:
                setting = self._modbus_settings[key]
                
            if key in self._settings and self._settings[key] == setting:
                continue
            elif key == 'read_interval':
                self._log.info("Setting %s read_interval: %s", self.name, setting)
                self._settings[key] = float(setting)
                continue
            elif key == 'nodename':
                self._log.info("Setting %s nodename: %s", self.name, setting)
                self._settings[key] = str(setting)
                continue
            elif key == 'prefix':
                self._log.info("Setting %s prefix: %s", self.name, setting)
                self._settings[key] = str(setting)
                continue
            elif key == 'registers':
                self._log.info("Setting %s datafields: %s", self.name, ",".join(setting))
                self._settings[key] = setting
                continue
            elif key == 'names':
                self._log.info("Setting %s names: %s", self.name, ",".join(setting))
                self._settings[key] = setting
                continue
            elif key == 'precision':
                self._log.info("Setting %s precision: %s", self.name, ",".join(map(str,setting)))
                self._settings[key] = setting
                continue
            else:
                self._log.warning("'%s' is not valid for %s: %s", setting, self.name, key)

        # include kwargs from parent
        super().set(**kwargs)
