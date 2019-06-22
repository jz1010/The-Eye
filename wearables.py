#!/usr/bin/env python

import os
import socket
import sys
import time
import struct
import fcntl
import errno

class wearables_client_t(object):
    def __init__(self,debug=False,mcaddr='239.255.223.01',port=0xDF0D,demo=False):
        self.debug = debug
        self.mcaddr = mcaddr
        self.port = port
        self.demo = demo
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((self.mcaddr, self.port))
        mreq = struct.pack("4sl", socket.inet_aton(self.mcaddr), socket.INADDR_ANY)
        self.s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
        if not self.demo:
            fcntl.fcntl(self.s,fcntl.F_SETFL, os.O_NONBLOCK)

    def get_msg_nonblocking(self):
        msg = None
        try:
            data, addr = self.s.recvfrom(1024)
    	    (msgcode,
             reserved,
             effect,
             elapsed,
             beat,
             hue_med,
             hue_dev) = \
                 struct.unpack("!I12s16sIIBB", data)

            msg = {
    	        'msgcode' : msgcode,
                'reserved' : reserved,
                'effect' : effect,
                'elapsed' : elapsed,
                'beat' : beat,
                'hue_med' : hue_med,
                'hue_dev' : hue_dev
            }

            if self.debug:
    	        print "RX %s:%s   %-16s elapsed: %04d beat: %04d hue_med: %03d hue_dev: %03d" % (addr[0], addr[1], effect.rstrip('\0'), elapsed, beat, hue_med, hue_dev)
        except socket.error, e:
            if e.args[0] == errno.EWOULDBLOCK:
                pass
            elif e.args[0] == errno.EGAIN:
                pass
            else:
                raise
        except Exception as err:
            print ('Error: {}'.format(err))
    	    #print "RX %d bytes, %s" % (len(data), err)
            
        return msg
    
    def run_demo(self):
        while True:
            data, addr = self.s.recvfrom(1024)
            try:
    	        (msgcode,
                reserved,
                 effect,
                 elapsed,
                 beat,
                 hue_med,
                 hue_dev) = \
                     struct.unpack("!I12s16sIIBB", data)
            
    	        print "RX %s:%s   %-16s elapsed: %04d beat: %04d hue_med: %03d hue_dev: %03d" % (addr[0], addr[1], effect.rstrip('\0'), elapsed, beat, hue_med, hue_dev)
            except Exception as err:
    	        print "RX %d bytes, %s" % (len(data), err)
        
if __name__ == "__main__":
    if False:
        wearables_client = wearables_client_t(debug=False,demo=True)
        wearables_client.run_demo()
    else:
        wearables_client = wearables_client_t(debug=False,demo=False)
        while True:
            msg = wearables_client.get_msg_nonblocking()
            if msg is not None:
                print ('msg: {}'.format(msg))
    
