#!/usr/bin/python3
__author__ = "Ehab Hussein"
__credits__ = ['Josep Pi Rodriguez',    'Dani Martinez']
__version__ = "1.0"
__twitter__ = "@0xRaindrop"
__status__ = "Development"
##################### Imports
import xmltodict
import platform
import binascii
from sys import exit
from os import geteuid
from sqlalchemy import MetaData, create_engine, String, Integer, Table, Column, inspect
import pprint
from time import time,sleep
import json
import threading


###################### Pre-Checks

if int(platform.python_version()[0]) < 3:
    print ("Python 2.x or older are not supported. Make sure you are using python3\n")
    exit(-1)
if geteuid() != 0:
    print("Don't forget that this needs root privileges!")
    exit(-1)
if int(platform.uname()[2][0]) < 4:
    print("Seems like you have an incompatible kernel, upgrade to something >= 4.x\nThis might not work properly..You have been warned!!!\n")
    print("GadgetFS might not work!!\n")
try:
    import usb.core
    import usb.util
except:
    print ("Seems like you done have pyusb installed.\n[-]install it via pip:\n\t[-]pip3 install pyusb")
    exit(-1)
try:
    import pika
except:
    print("Man in the middle for USB will not work. install pika")

############auto gadgetFS class

class agfs():
    def __init__(self):
        print("""
*******************************************************************************
*AutoGadgetFS: Automated USB testing based on gadgetfs*************************
*******************************************************************************     
        """)

    def createdb(self, name):
        '''create the sqlite table and columns for usblyzer dumps'''

        try:
            meta = MetaData()
            db = create_engine('sqlite:///%s.db' %(name.strip()))
            db.echo = False
            self.usblyzerdb = Table(
            name.strip(),
            meta,
            Column('Type',String),
            Column('seq', Integer),
            Column('io', String),
            Column('cie', String),
            Column('Duration', String),
            Column('DevObjAddr', String),
            Column('irpaddr', String),
            Column('RawDataSize', Integer),
            Column('RawData', String),
            Column('RawBinary',String),
            Column('replyfrom', Integer)
                                    )
            meta.create_all(db)
            return db, self.usblyzerdb
        except:
            print("[Error] cannot create db\n")

    def releasedev(self):
        '''releases the device and re-attaches the kernel driver'''
        print("[-] Releasing the Interface")
        usb.util.release_interface(self.device, self.interfaces.bInterfaceNumber)
        print("[-] Attaching the kernel driver")
        self.device.attach_kernel_driver(self.interfaces.bInterfaceNumber)
        print("[-] Device released!")

    def deviceInfo(self):
        '''gets the complete info only for any usb connected to the host'''
        getusbs = usb.core.find(find_all=True)
        devices = dict(enumerate(str(dev.manufacturer) + ":" + str(dev.idProduct) + ":" + str(dev.idVendor) for dev in getusbs))
        for key, value in devices.items():
            print(key, ":", value)
        hook = input("---> Select a device: ")
        idProd, idVen = devices[int(hook)].split(':')[1:]
        device = usb.core.find(idVendor=int(idVen), idProduct=int(idProd))
        print(device)

    def deviceInterfaces(self):
        '''get all interfaces and endpoints on the device
        Thanks to the pyusb tutorial'''
        self.leninterfaces = 0
        for cfg in self.device:
            print("Configuration Value: "+str(int(cfg.bConfigurationValue)) + '\n')
            for intf in cfg:
                self.leninterfaces += 1
                print('\tInterface number: ' + \
                                 str(int(intf.bInterfaceNumber)) + \
                                 ',Alternate Setting: ' + \
                                 str(intf.bAlternateSetting) + \
                                 '\n')
                for ep in intf:
                    print('\t\tEndpoint Address: ' + \
                                     hex(ep.bEndpointAddress) + \
                                     '\n')
    def changeintf(self):
        '''will allow you to change the interfaces you use with the device '''
        self.deviceInterfaces()
        self.precfg = int(input("which Configuration would you like to use: "))
        self.interfacenumber = int(input("which Interface would you like to use: "))
        self.Alternate = int(input("which Alternate setting would you like to use: "))
        self.epin = int(input("which Endpoint IN would you like to use:[0x??] "), 16)
        self.epout = int(input("which Endpoint OUT would you like to use:[0x??] "), 16)
        try:
            if self.device.is_kernel_driver_active(self.interfacenumber):
                self.device.detach_kernel_driver(self.interfacenumber)
                print("[-] Kernel driver detached from interface")
            else:
                print("[-] Kernel driver not detached from interface!!!!")
            self.device.set_configuration(self.precfg)
            self.devcfg = self.device.get_active_configuration()
            self.interfaces = self.devcfg[(self.interfacenumber, self.Alternate)]
            usb.util.claim_interface(self.device, self.interfacenumber)
        except Exception as e:
            print("Something went wrong while changing the interface\nError: ", e)

    def findSelect(self):
        '''find your device and select it'''
        self.getusbs = usb.core.find(find_all=True)
        self.devices = dict(enumerate(str(dev.manufacturer)+":"+str(dev.idProduct)+":"+str(dev.idVendor) for dev in self.getusbs))
        for key,value in self.devices.items():
            print(key,":",value)
        self.hook = input("---> Select a device: ")
        self.idProd,self.idVen = self.devices[int(self.hook)].split(':')[1:]
        self.device = usb.core.find(idVendor=int(self.idVen),idProduct=int(self.idProd))
        print(str(self.device))
        detachKernel = str(input("do you want to detach the device from it's kernel driver: [y/n] "))
        if detachKernel.lower() == 'y':
            try:
                '''https://stackoverflow.com/questions/23203563/pyusb-device-claimed-detach-kernel-driver-return-entity-not-found'''
                confer = 1
                for configurations in self.device:
                    print("Disabling Interfaces on configuration: %d" %confer)
                    print("Disabling interfaces :\n\t%s" %configurations.bNumInterfaces)
                    for inter in range(configurations.bNumInterfaces+1):
                        try:
                            if self.device.is_kernel_driver_active(inter):
                                self.device.detach_kernel_driver(inter)
                                print("Disabled interface: %d" %inter)
                        except:
                            pass
                print("[-] Kernel driver detached")
                self.device.set_configuration()
            except Exception as e:
                    print("Failed to detach the kernel driver from the interfaces.",e )
            self.deviceInterfaces()
            if input("Do you want to reset the device? [y/n]: ").lower() == 'y':
                self.device.reset()
            try:
                self.precfg = int(input("which Configuration would you like to use: "))
                self.devcfg = self.device.get_active_configuration()
                self.interfacenumber = int(input("which Interface would you like to use: "))
                self.Alternate = int(input("which Alternate setting would you like to use: "))
                self.epin = int(input("which Endpoint IN would you like to use: "), 16)
                self.epout = int(input("which Endpoint OUT would you like to use: "), 16)
                self.interfaces = self.devcfg[(self.interfacenumber, self.Alternate)]
                self.killthread = 0
            except Exception as e:
                print(e)
                print("Couldn't get device configuration!")

            claim = str(input("Do you want pyUSB to claim the device interface: [y/n] "))
            if claim.lower() == 'y':
                    usb.util.claim_interface(self.device, self.interfaces.bInterfaceNumber)
                    print("Checking HID report retrieval\n")
                    print(self.leninterfaces)
                    try: 
                        self.device_hidrep = []
                        '''Thanks https://wuffs.org/blog/mouse-adventures-part-5'''
                        for i in range(0,self.leninterfaces+1):
                            try:
                                self.device_hidrep.append(binascii.hexlify(self.device.ctrl_transfer(self.epin,6,0x2200,i,0x400)))
                                print(self.device_hidrep)
                            except usb.core.USBError:
                                pass
                        if self.device_hidrep:
                            print(self.device_hidrep)
                        else:
                            self.device_hidrep = []
                    except Exception as e:
                        print (e)
                        self.device_hidrep = []
                        print("Couldn't get a hid report but we have claimed the device.")
        if type(self.device.manufacturer) is type(None):
            self.manufacturer = "UnkManufacturer"
        else:
            self.manufacturer = self.device.manufacturer
        self.SelectedDevice = self.manufacturer + "-" + str(self.device.idVendor) + "-" + str(self.device.idProduct) + "-" + str(time())
        cloneit = input("Do you want to save this device's information?[y/n]")
        if cloneit.lower() == 'y':
            self.clonedev()

    def monInterfaceChng(self):
        while True:
            if self.monIntKill == 1:
                break
        if self.tmpInterfaces != str(self.device):
            self.tmpInterfaces = str(self.device)
            print("Device Interfaces have changed!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")

    def startMonInterfaceChng(self):
        self.tmpInterfaces = None
        self.monIntKill = 0
        self.monIntThread = threading.Thread(target=self.monInterfaceChng)
        self.monIntThread.start()

    def stopMonInterfaceChang(self):
        self.monIntKill = 1
        self.monIntThread.join()
        print("Monitoring of interface changes has stopped")

    def stopSniffing(self):
        '''Kills the sniffing thread'''
        self.killthread = 1
        self.readerThread.join()
        print("Sniffing has stopped successfully!")
        self.killthread = 0

    def startSniffReadThread(self,endpoint):
       '''This is a thread to continuously read the replies from the device'''
       mypts = input("Open a new terminal and type 'tty' and input the pts number: (/dev/pts/X) ")
       input("Press Enter when ready..on %s" % mypts)
       self.readerThread = threading.Thread(target=self.sniffdevice, args=(endpoint,mypts))
       self.readerThread.start()

    def sniffdevice(self, endpoint,pts):
        ''' read the communication between the device to host
         This is mostly taken from:
        https://www.orangecoat.com/how-to/read-and-decode-data-from-your-mouse-using-this-pyusb-hack
        Works like a charm '''
        with open('%s'%(pts.strip()), 'w') as ptsx:
            while True:
                if self.killthread == 1:
                    ptsx.write("Thread Terminated Successfully")
                    break
                try:

                        ptsx.write(str(binascii.hexlify(bytearray(self.device.read(endpoint, self.device.bMaxPacketSize0))))+"\r\n")
                        ptsx.write("-----------------^^^FROM DEVICE^^^----------------\r\n")
                        sleep(0.5)
                except usb.core.USBError as e:
                    if e.args == ('Operation timed out\r\n',):
                        pass
                    pass

    def startMITMusbWifi(self):
        self.isQconnected = 0
        self.startMITMProxyThread = threading.Thread(target=self.MITMproxy)
        self.startMITMProxyThread.start()

    def stopMITMusbWifi(self):
        self.isQconnected = 1
        self.startMITMProxyThread.join()
        print("MITM Proxy has now been terminated!")


    def MITMproxyRQueues(self, ch, method, properties, body):
        response = self.device.write(self.epin,binascii.unhexlify(body))
        if response:
            self.qchannel2.basic_publish(exchange='agfs', routing_key='tohst',
                                     body=binascii.hexlify(bytearray(response)))
        ch.basic_ack(delivery_tag=method.delivery_tag)
        if self.isQconnected:
            self.qchannel.close()
            self.qchannel2.close()



    def MITMproxyRead(self):
        try:
            self.qcreds = pika.PlainCredentials('autogfs', 'usb4ever')
            self.qpikaparams = pika.ConnectionParameters('localhost', 5672, '/', self.qcreds)
            self.qconnect = pika.BlockingConnection(self.qpikaparams)
            self.qchannel = self.qconnect.channel()
            self.qchannel.basic_qos(prefetch_count=1)
            self.qchannel.basic_consume(on_message_callback=self.MITMproxyRQueues, queue='todevice')
            print("Connected to RabbitMQ, starting consumption!")
            self.qcreds2 = pika.PlainCredentials('autogfs', 'usb4ever')
            self.qpikaparams2 = pika.ConnectionParameters('localhost', 5672, '/', self.qcreds2)
            self.qconnect2 = pika.BlockingConnection(self.qpikaparams2)
            self.qchannel2 = self.qconnect2.channel()
            print("Connected to exchange sending to host!")
            self.qchannel.start_consuming()
        except Exception as e:
            print(e)


    def replaymsgs(self, direction=None, sequence=None , message=None):
        '''This method searches the USBLyzer parsed database and give you the option replay a message or all messages from host to device or vise versa

        @direction: in or out
        @sequence: the sequence number you would like to select to reply
        @message: will allow you to send your selected message
        '''
        count = 0
        try:
            if self.device:
                if sequence is None and direction is not None and message is None:
                    self.searchResults = self.connection.execute('select RawBinary from "%s" where io="%s"'%(self.dbname,direction)).fetchall()
                    for i in self.searchResults:
                                count += 1
                                try:
                                    print("[%d] ++++++++++v TO DEVICE v+++++++++++++"%count)
                                    self.device.write(self.epout, i[0],self.device.bMaxPacketSize0)
                                    print(i[0])
                                    print("[%d]++++++++++^ TO DEVICE ^+++++++++++++"%count)
                                    sleep(0.5)
                                except usb.core.USBError as e:
                                    print("[%d] ++++++++++v TO DEVICE v+++++++++++++"%count)
                                    print(e)
                                    if e.args == ('Operation timed out',):
                                        print("timedout\n")
                                        continue
                                    print("[%d]++++++++++^ TO DEVICE ^+++++++++++++"%count)
                elif sequence is not None and direction is not None and message is None:
                    count += 1
                    #Not implemented yet
                    self.searchResults = self.connection.execute('select RawBinary from "%s" where io="%s" and seq=%d' %(self.dbname, direction,sequence)).fetchall()
                    pprint.pprint(self.searchResults[0][0])
                elif message is not None:
                    print("[-] Sending your custom message.")
                    self.device.write(self.epout, message)
        except Exception as e:
            print("[-] Can't find messages with your search\n",e)


    def searchmsgs(self):
        '''
        This method allows you to search and select all messages for a pattern

        this method does not return anything
        '''
        _cols = inspect(self.dbObj)
        _coldict = {}
        self._names= _cols.get_columns(self.dbname)
        print("id->Column")
        for i,j in enumerate(self._names):
            _coldict[i] = j['name']
        pprint.pprint(_coldict)
        self.colSelection = int(input("Search in which column id: "))
        self.searcher = input("Enter search text: ")
        self.searchResults = self.connection.execute('select * from "%s" where %s like "%%%s%%"'\
                                                     %(self.dbname, _coldict[self.colSelection], self.searcher)).fetchall()
        self.searchdict = {}
        for i,j in enumerate(self.searchResults):
            self.searchdict[i] = j
        pprint.pprint(self.searchdict)
        self.msgSelected = self.searchdict[int(input("Which message id to select: "))]
        print (self.msgSelected)


    def usblyzerparse(self,dbname):
        '''This method will parse your xml exported from usblyzer and then import them into a database

        @dbname: this parameter is used to create a sqlite database in the folder ./databases with the specified name passed.

        this method returns nothing
        '''
        try:
            self.dbname = "databases/"+dbname+"_"+self.SelectedDevice
            print("Creating Tables")
            self.dbObj,_table = self.createdb(self.dbname)
            self.connection = self.dbObj.connect()
            self.transaction = self.connection.begin()
            self.xmlfile = input("Enter  Path to USBlyzer xml dump: ")
            print("Parsing the file..")
            with open(self.xmlfile) as fd:
                self.xmlobj = xmltodict.parse(fd.read())
            print ("Inserting into database..")
            for i in self.xmlobj['USBlyzerXmlReport']['Items']['Item']:
                    try:
                        _type = i['Type']
                    except:
                        _type = ""
                    try:
                        _duration = i['Duration'].split(' ')[0]
                    except:
                        _duration = '0.0'
                    if "-" in i['Seq']:
                        _seq, _replyfrom  = map(int,i['Seq'].split("-"))
                    else:
                        _seq = int(i['Seq']) #seq
                        _replyfrom = 0
                    try:
                        _io = i['IO'] #IO
                    except:
                        _io = ""
                    try:
                        _cie = i['CIE'] #CIE
                    except:
                        _cie = ""
                    try:
                        _devObj = i['DevObjAddr'] #devobjaddr
                    except:
                        _devObj = ""
                    try:
                        _irpAddr= i['IrpAddr']  # irpaddr
                    except:
                        _irpAddr = ""
                    try:
                        _mSize = int(i['RawDataSize']) # raw size
                    except:
                        _mSize = 0
                    try:
                       _mData = ''.join(i['RawData'].split())
                       _mDataAscii = binascii.unhexlify(_mData)
                    except Exception as e:
                        _mData = ""
                        _mDataAscii = ""
                    try:
                            _insert = _table.insert().values(
                                Type = _type,
                                seq=_seq,
                                io=_io,
                                cie=_cie,
                                Duration=_duration,
                                DevObjAddr =_devObj,
                                irpaddr=_irpAddr,
                                RawDataSize = _mSize,
                                RawData =_mData,
                                RawBinary = _mDataAscii,
                                replyfrom =_replyfrom)
                            self.connection.execute(_insert)
                    except Exception as e:
                        print("unable to insert data into database!",e)
                        break
            self.transaction.commit()
        except Exception as e:
            print("Unable to create or parse!",e)


    def clonedev(self):
        '''
        This method does not need any parameters it only saves a backup of the device incase you need to share it or use it later.
        saves the device information in the ./clones/ directory.

        The best option is to allow Agfs to claim the interfaces prior to cloning it as we need to gather more info on the device
        before we clone it.

        This method returns nothing.
        '''
        try:
            try:
                self.device_hidrep
            except:
                print("Claim the interfaces before trying to clone the device. We need some info")
                return "Cloning Failed"
            try:
                self.devcfg.bmAttributes
            except:
                print("Claim the interfaces before trying to clone the device. We need some info")
                return "Cloning Failed"
            try:
                self.devcfg.bMaxPower
            except:
                print("Claim the interfaces before trying to clone the device. We need some info")
                return "Cloning Failed"
            cloner = open("clones/%s" % self.SelectedDevice, 'w')
            print("setting up: %s" % self.manufacturer)
            print("Creating backup of device\n")
            self.devJson = json.dumps({"idVen":'0x{:04X}'.format(self.device.idVendor),\
                                  "idProd":'0x{:04X}'.format(self.device.idProduct),\
                                  "manufacturer":self.manufacturer,\
                                  "bcdDev":'0x{:04X}'.format(self.device.bcdDevice),\
                                  "bcdUSB":'0x{:04X}'.format(self.device.bcdUSB),\
                                  "serial":self.device.serial_number,\
                                  "bDevClass":'0x{:02X}'.format(self.device.bDeviceClass),\
                                  "bDevSubClass":'0x{:02X}'.format(self.device.bDeviceSubClass),\
                                  "protocol":'0x{:02X}'.format(self.device.bDeviceProtocol),\
                                  "MaxPacketSize":'0x{:02X}'.format(self.device.bMaxPacketSize0),\
                                  "hidreport":','.join([i.decode('utf-8') for i in self.device_hidrep]),\
                                  "bmAttributes":'0x{:02X}'.format(self.devcfg.bmAttributes),\
                                  "MaxPower":'0x{:02X}'.format(self.devcfg.bMaxPower),
                                  "product":self.device.product})
            cloner.write(self.devJson)
            cloner.write('\n++++++\n')
            cloner.write(str(self.device)+"\n\n")
            print("- Done: Device settings copied to file.\n")
            cloner.close()
        except Exception as e:
            print("Cannot clone the device!\n",e)

    def setupGadgetFS(self):
        ''' setup variables for gadgetFS : Linux Only, on Raspberry Pi Zero best option
        This method does not require any parameters.
        calling this method creates a bash script file inside the directory ./gadgetscripts/ which can then be pushed
        and executed on the pi Zero to emulate the device being tested.

        This method returns nothing.
        '''
        try:
            agfsscr = open("gadgetscripts/"+self.SelectedDevice+".sh",'w')
            print("setting up: "+self.manufacturer)
            print("Aquiring info about the device for Gadetfs\n")
            idVen = '0x{:04X}'.format(self.device.idVendor)
            idProd = '0x{:04X}'.format(self.device.idProduct)
            manufacturer = self.manufacturer
            bcdDev = '0x{:04X}'.format(self.device.bcdDevice)
            bcdUSB = '0x{:04X}'.format(self.device.bcdUSB)
            serial = self.device.serial_number
            bDevClass = '0x{:02X}'.format(self.device.bDeviceClass)
            bDevSubClass = '0x{:02X}'.format(self.device.bDeviceSubClass)
            protocol = '0x{:02X}'.format(self.device.bDeviceProtocol)
            MaxPacketSize = '0x{:04X}'.format(self.device.bMaxPacketSize0)
            if len(self.device_hidrep) != 0:
                for i,j in enumerate(self.device_hidrep):
                    print(i,"] ",j)
                hidq = int(input("Which report would you like to use? "))
                hidreport = self.device_hidrep[hidq]
            else:
                hidreport=''.encode('utf-8')
            bmAttributes = '0x{:02X}'.format(self.devcfg.bmAttributes)
            MaxPower = '0x{:02X}'.format(self.devcfg.bMaxPower)
            product = self.device.product
            basedir = "/sys/kernel/config/usb_gadget"
            print("- Creating Bash script!\n")
            agfsscr.write("#!/bin/bash\n")
            agfsscr.write("rmmod g_serial\n")
            agfsscr.write("modprobe libcomposite\n")
            agfsscr.write("cd /sys/kernel/config/usb_gadget/\n")
            agfsscr.write("mkdir g && cd g\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/strings/0x409/\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/functions/hid.usb0/\n")
            agfsscr.write("mkdir -p /sys/kernel/config/usb_gadget/g/configs/c.1/strings/0x409/\n")
            agfsscr.write("echo %s > %s/g/idVendor\n"%(idVen,basedir))
            agfsscr.write("echo %s > %s/g/idProduct\n" % (idProd, basedir))
            agfsscr.write("echo %s > %s/g/bcdDevice\n" % (bcdDev, basedir))
            agfsscr.write("echo %s > %s/g/bcdUSB\n" % (bcdUSB, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceClass\n" % (bDevClass, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceSubClass\n" % (bDevSubClass, basedir))
            agfsscr.write("echo %s > %s/g/bDeviceProtocol\n" % (protocol, basedir))
            agfsscr.write("echo %s > %s/g/bMaxPacketSize0\n" % (MaxPacketSize, basedir))
            agfsscr.write("echo '%s' > %s/g/strings/0x409/serialnumber\n" % (serial, basedir))
            agfsscr.write("echo '%s' > %s/g/strings/0x409/manufacturer\n" % (manufacturer, basedir))
            agfsscr.write("echo '%s' > %s/g/strings/0x409/product\n" % (product, basedir))
            agfsscr.write("echo %s > %s/g/configs/c.1/MaxPower\n" % (MaxPower, basedir))
            agfsscr.write("echo %s > %s/g/configs/c.1/bmAttributes\n" % (bmAttributes, basedir))
            agfsscr.write("echo 'Default Configuration' > %s/g/configs/c.1/strings/0x409/configuration\n" %(basedir))
            agfsscr.write("echo %s > %s/g/functions/hid.usb0/protocol\n" %(protocol,basedir))
            agfsscr.write("echo %s > %s/g/functions/hid.usb0/report_length\n" % (len(hidreport),basedir))
            agfsscr.write("echo %s > %s/g/functions/hid.usb0/subclass\n" % (bDevSubClass,basedir))
            agfsscr.write("echo '%s' | xxd -r -ps > %s/g/functions/hid.usb0/report_desc\n" % (hidreport.decode("utf-8") ,basedir))
            agfsscr.write("ln -s %s/g/functions/hid.usb0 %s/g/configs/c.1\n"%(basedir,basedir))
            agfsscr.write("udevadm settle -t 5 || :\n")
            agfsscr.write("ls /sys/class/udc/ > %s/g/UDC\n"%(basedir))
            agfsscr.close()
            print("- Done wrote bash script. Try testing your gadget\n")
        except Exception as e:
            print("You need to call FindSelect() then clonedev() method method prior to setting up GadgetFS", e)
