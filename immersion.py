#!/usr/bin/python3
 
# immersion.py
#
# Author: Martin Reed, martin@martinreed.co.uk

import sys
import socket
import struct
import time
import paho.mqtt.client as mqtt

MQTT_CLIENT_ID = "readtesla"
MQTT_SERVER_ADDR = "192.168.0.2"
MQTT_QOS_AT_MOST_ONCE = 0
MQTT_QOS_AT_LEAST_ONCE = 1
MQTT_QOS_EXACTLY_ONCE = 2
MQTT_BASE = "house/immersion"

# UDP settings
OWN_IP = '192.168.0.4'
TESLA_IP = '192.168.0.45'
UDP_PORT = 1337
DISCOVERY_PAYLOAD = bytes([0x01, 0x00, 0x00, 0x54])
CONFIGURATION_READ_PAYLOAD = bytes([0x21, 0x00, 0x00, 0x74])
CONTROL_READ_PAYLOAD = bytes([0xF1, 0x00, 0x00, 0xA4])

DATE_TIME_FMT = "%Y-%m-%d %H:%M:%S"

def discover(timeout=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.bind(("", 1337))
    s.settimeout(timeout)
    s.sendto(DISCOVERY_PAYLOAD, ('<broadcast>', UDP_PORT))
    try:
        data, addr = s.recvfrom(64)
        print(f"Discovered T‑Smart at {addr[0]}")
        return addr[0]
    except socket.timeout:
        print("Discovery timed out.")
    finally:
        s.close()
    return None

def read_control(ip, timeout=2):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.settimeout(timeout)
    s.bind((OWN_IP, 1337))
    s.sendto(CONTROL_READ_PAYLOAD, (ip, UDP_PORT))
    try:
        while True:
            data, addr = s.recvfrom(64)
            if addr[0] != OWN_IP:
                return data
    except socket.timeout:
        dprint("Control read timed out.")
    finally:
        s.close()
    return None

def parse_response(data):
    cur_temp = struct.unpack_from('<h', data, offset=7)[0] * 0.1
    set_point = struct.unpack_from('<h', data, offset=4)[0] * 0.1
    mode = data[6]
    heating = bool(data[9] & 0x01)
    power = bool(data[3] & 0x01)
    return {
        'current_temperature': cur_temp,
        'set_point': set_point,
        'mode': mode,
        'heating': heating,
        'power': power
    }

def on_mqtt_connect(client, userdata, flags, rc):
	dprint("connected %d" % rc)
 
def on_mqtt_publish(client, userdata, mid):
	#dprint("published %d" % mid)
        pass

def publish(state):
    mqtt_client.publish(MQTT_BASE + "/mode", state['mode'], MQTT_QOS_AT_LEAST_ONCE)
    mqtt_client.publish(MQTT_BASE + "/temperature", f"{state['current_temperature']:.1f}", MQTT_QOS_AT_LEAST_ONCE)
    mqtt_client.publish(MQTT_BASE + "/setpoint", f"{state['set_point']:.1f}", MQTT_QOS_AT_LEAST_ONCE)
    mqtt_client.publish(MQTT_BASE + "/heating", 1 if state['heating'] else 0, MQTT_QOS_AT_LEAST_ONCE)

def fmtiso8601(t=None):
    if t == None:
        return time.strftime(DATE_TIME_FMT)
    else:
        return time.strftime(DATE_TIME_FMT, t)


def dprint(msg):
    print(fmtiso8601() + ": " + str(msg))
    sys.stdout.flush()

def main():

    global mqtt_client
    mqtt_client = mqtt.Client()
    mqtt_client.username_pw_set("sensor", "sensor22")
    mqtt_client.connect(MQTT_SERVER_ADDR, 1883, 60)
    mqtt_client.on_connect = on_mqtt_connect
    mqtt_client.on_publish = on_mqtt_publish
    mqtt_client.loop_start()

    # ip = discover()
    # if not ip:
    #     return
    ip = TESLA_IP

    while True:
        dprint("Polling control data…")
        raw = read_control(ip)
        if not raw:
            time.sleep(1)
            continue

        state = parse_response(raw)
        dprint("TSmart Status:")
        print(f" • Current Temp: {state['current_temperature']:.1f}°C")
        print(f" • Set Point:     {state['set_point']:.1f}°C")
        print(f" • Mode:          {state['mode']}")
        print(f" • Heating On:    {state['heating']}")
        print(f" • Relay Power:   {state['power']}")
        publish(state)

        time.sleep(15)

if __name__ == "__main__":
    main()

