#!/usr/bin/python

from evdev import InputDevice, categorize, ecodes
import sys
import time
import os

class joystick_t(object):
    def __init__(self,joystick_dev='/dev/input/event1',debug=False):
        self.joystick_dev = joystick_dev
        self.debug = debug
        try:
            print ('Called init joystick for device: {}'.format(self.joystick_dev))
            self.joystick = InputDevice(self.joystick_dev)
        except:
            self.joystick = None
            print ('joystick init failed')
            
        
        #self.name = self.joystick.get_name()
#       self.num_axes = self.joystick.get_numaxes()
#        self.num_buttons = self.joystick.get_numbuttons()
#        self.num_hats = self.joystick.get_numhats()
#        self.info()

        self.cnt_samples = 0
        self.buttons = {
            288: {'button': 'trigger'},
            289: {'button': '2'},
            290: {'button': '3'},
            291: {'button': '4'},            
            292: {'button': '5'},            
            293: {'button': '6'},            
            294: {'button': '7'},            
            295: {'button': '8'},            
            296: {'button': '9'},            
            297: {'button': '10'},            
            298: {'button': '11'},
            299: {'button': '12'}
        }

    def info(self):
        print ('joystick: {}'.format(self.joystick))
        print( "Number of axes: {}".format(self.num_axes) )
        print( "Number of buttons: {}".format(self.num_buttons) )
        print( "Number of hats: {}".format(self.num_hats) )

    def get_status(self):
        return (self.joystick is not None)
        
    def sample_nonblocking(self):
        gecko_events = []
        if self.joystick is None:
            return gecko_events
        
        sample = False
        events = []
        while True:
            try:
                event = self.joystick.read_one()
            except:
                self.joystick = None
                event = None
                
            if event is None:
                break
            events.append(event)
            
        for event in events:
            if event.type in [ecodes.EV_KEY]:
                if event.code not in self.buttons:
                    continue # unhandled event
                
                button_name = self.buttons[event.code]['button']
                button_val = event.value
                #print ('button: {} state: {}'.format(button_name,button_val))
                if button_name in ['trigger']:
                    gecko_events.append('blink')
                elif button_name in ['2']:
                    gecko_events.append('eye_center')
                elif button_name in ['9']:
                    gecko_events.append('eye_context_9')                    
                elif button_name in ['11']:
                    gecko_events.append('eye_context_11')                    
                elif button_name in ['12']:
                    gecko_events.append('eye_context_12')
                else:
                    pass
            elif event.type in [ecodes.EV_ABS]: # stick handle
                total_range = 1024
                t_lo = total_range / 4
                t_hi = total_range / 4 * 3
                if self.debug:
                    #print ('analog value: {}'.format(event.value))
                    pass
                    
                if event.code in [0]: # stick left/right
                    #print ('ABS_0: {}'.format(event))
                    if event.value >= 0 and event.value < t_lo: # left
                        gecko_events.append('eye_left')
                    elif event.value >= t_hi and event.value <= total_range: # right
                        gecko_events.append('eye_right')
                elif event.code in [1]: # stick forward/back
                    #print ('ABS_1: {}'.format(event))
                    if event.value >= 0 and event.value < t_lo: # forward
                        gecko_events.append('eye_up')
                    elif event.value >= t_hi and event.value <= total_range: # back
                        gecko_events.append('eye_down')
                elif event.code in [5]: # stick twist
                    #print ('ABS_5: {}'.format(event))                                  
                    pass
                elif event.code in [17]: # Hat forward/back
                    if event.value in [-1]: # hat forward
                        gecko_events.append('pupil_widen')
                    elif event.value in [0]: # hat middle
                        pass
                    elif event.value in [1]: # hat back
                        gecko_events.append('pupil_narrow')                        
                    else:
                        raise
                elif event.code in [16]: # Hat left/right
                    if event.value in [-1]: # hat left
                        pass
                    elif event.value in [0]: # hat middle
                        pass
                    elif event.value in [1]: # hat right
                        pass
                    else:
                        raise
                else:
                    print ('Analog unhandled event: {}'.format(event))
                    
            elif event.type in [0]: # UNKNOWN
                pass
            elif event.type in [4]: # UNKNOWN - maybe relates to button press
                pass
            else:
                print ('Unhandled event type: {}'.format(event.type))

        return gecko_events

    def shutdown(self):
        pass
        
if __name__ in "__main__":
    joystick = joystick_t(debug=True)
    while True:
        gecko_events = joystick.sample_nonblocking()
        for event in gecko_events:
            print ('event: {}'.format(event))
