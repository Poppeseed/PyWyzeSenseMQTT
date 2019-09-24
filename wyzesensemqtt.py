#!/usr/bin/env python

"""Example of using WyzeSense USB bridge.

**Usage:** ::
  sample.py [options]

**Options:**

    -d, --debug         output debug log messages to stderr
    -v, --verbose       print and log more information
    --device PATH       USB device path [default: /dev/hidraw0]
    --broker Address    IP address or hostname of MQTT Broker

**Examples:** ::

  sample.py --device /dev/hidraw0   # Using WyzeSense USB bridge /dev/hidraw0

"""
#from __future__ import print_function
#from builtins import input
#import os
import re
import sys
import logging
import errno
import binascii
import time
import json

import wyzesense

import paho.mqtt.client as mqtt

mqtt_client = None

def main(args):
    global mqtt_client

    def List(unused_args):
        result = ws.List()
        print("%d sensor paired:" % len(result))
        logging.debug("%d sensor paired:", len(result))
        for mac in result:
            print("\tSensor: %s" % mac)
            logging.debug("\tSensor: %s", mac)

    def Pair(unused_args):
        result = ws.Scan()
        if result:
            print("Sensor found: mac=%s, type=%d, version=%d" % result)
            logging.debug("Sensor found: mac=%s, type=%d, version=%d", *result)
        else:
            print("No sensor found!")
            logging.debug("No sensor found!")

    def Unpair(mac_list):
        for mac in mac_list:
            if len(mac) != 8:
                print("Invalid mac address, must be 8 characters: %s", mac)
                logging.debug("Invalid mac address, must be 8 characters: %s", mac)
                continue

            print("Un-pairing sensor %s:" % mac)
            logging.debug("Un-pairing sensor %s:", mac)
            ws.Delete(mac)
            print("Sensor %s removed" % mac)
            logging.debug("Sensor %s removed", mac)

    def on_connect(client, userdata, flags, rc):
        if rc==0:
            print("connected OK Returned code=",rc)
            client.connected_flag=True #set flag
        else:
            print("Bad connection Returned code=",rc)
    
    def on_publish(client,userdata,result):             #create function for callback
        print("data published \n")

    def on_event(ws, e):
        global mqtt_client

        if e.Type == 'state':
            print("StateEvent: sensor_type=%s, state=%s, battery=%d, signal=%d" % e.Data)
            topic = "wyzesense/{}/update".format(e.MAC)
        
            payload = {
                "sensor_type" : e.Data[0],
                "state" : e.Data[1],
                "battery" : e.Data[2],
                "signal" : e.Data[3]
            }
            mqtt_client.publish(topic, json.dumps(payload), 0, False)

    if args['--debug']:
        loglevel = logging.DEBUG - (1 if args['--verbose'] else 0)
        logging.getLogger("wyzesense").setLevel(loglevel)
        logging.getLogger().setLevel(loglevel)

    device = args['--device']
    print("Opening wyzesense gateway [{}]".format(device))
    try:
        ws = wyzesense.Open(device, on_event)
        if not ws:
            print("Open wyzesense gateway failed")
            return 1
        print("Gateway info:")
        print("\tMAC:%s" % ws.MAC)
        print("\tVER:%s" % ws.Version)
        print("\tENR:%s" % binascii.hexlify(ws.ENR))
    except IOError:
        print("No device found on path %r" % device)
        return 2

    broker_addr = args['--broker']
    mqtt_client = mqtt.Client(client_id="wyze-mqtt-{}".format(ws.MAC), clean_session=True, userdata=None, protocol=4, transport="tcp")
    mqtt_client.connected_flag = False
    mqtt_client.on_connect = on_connect
    mqtt_client.on_publish = on_publish  

    mqtt_client.loop_start()
    if '--username' in args and '--password' in args:
        mqtt_client.username_pw_set(username=args['--username'],password=args['--password'])

    try:
        print('connecting to mqtt')
        mqtt_client.connect(broker_addr, 1883, 60)
    except:
        print("Unable to connect to mqtt broker @ {}:1883".format(broker_addr))
        return 2

    while not mqtt_client.connected_flag: #wait in loop
        print("In wait loop")
        time.sleep(1)

    try:
        while True:
            time.sleep(.1)
    finally:
        ws.Stop()

    return 0

    

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s')

    try:
        from docopt import docopt
    except ImportError:
        sys.exit("the 'docopt' module is needed to execute this program")

    # remove restructured text formatting before input to docopt
    usage = re.sub(r'(?<=\n)\*\*(\w+:)\*\*.*\n', r'\1', __doc__)
    sys.exit(main(docopt(usage)))