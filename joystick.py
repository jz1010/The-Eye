#!/usr/bin/python

#from evdev import InputDevice, categorize, ecodes
import pygame
import sys
import time
import os

class joystick_t(object):
    def __init__(self,debug=False):
        self.debug = debug
        #os.putenv('DISPLAY',':0.0')
        pygame.init()
        #size = [500, 700]
        #screen = pygame.display.set_mode(size)        
        pygame.joystick.init()
        joysticks = [pygame.joystick.Joystick(x) for x in range(pygame.joystick.get_count())]

        self.joystick = joysticks[0]
        self.joystick.init()
        
        self.name = self.joystick.get_name()
        self.num_axes = self.joystick.get_numaxes()
        self.num_buttons = self.joystick.get_numbuttons()
        self.num_hats = self.joystick.get_numhats()
        self.info()

        self.cnt_samples = 0

    def info(self):
        print ('joystick: {}'.format(self.name))
        print( "Number of axes: {}".format(self.num_axes) )
        print( "Number of buttons: {}".format(self.num_buttons) )
        print( "Number of hats: {}".format(self.num_hats) )

    def sample_nonblocking(self):
        sample = False
        for event in self.event():
            if event.type in [pygame.JOYBUTTONUP, pygame.JOYBUTTONDOWN,
                              pygame.JOYAXISMOTION, pygame.JOYHATMOTION]:
                sample = True

        if sample:
            self.do_sample()
            
    def do_sample(self):
        # Usually axis run in pairs, up/down for one, and left/right for
        # the other.
        print ('** Sample: {}'.format(self.cnt_samples))
        for i in range(self.num_axes):
            axis = self.joystick.get_axis(i)
            print("Axis {} value: {:>6.3f}".format(i, axis))

        for i in range(self.num_buttons):
            button = self.joystick.get_button(i)
            print("Button {:>2} value: {}".format(i,button))
            
        # Hat switch. All or nothing for direction, not like joysticks.
        # Value comes back in an array.
        for i in range(self.num_hats):
            hat = self.joystick.get_hat(i)
            print("Hat {} value: {}".format(i, str(hat)))

        self.cnt_samples += 1
        print ''
        
    def event(self):
        event = pygame.event.get()
        if len(event) > 0:
            print ('event: {}'.format(event))
        
        return event
            
    def shutdown(self):
        self.joystick.quit()
        pygame.quit()
        
if __name__ in "__main__":
    joystick = joystick_t()
    joystick.info()
    while True:
        sample = False
        for event in joystick.event():
            if event.type in [pygame.JOYBUTTONUP, pygame.JOYBUTTONDOWN,
                              pygame.JOYAXISMOTION, pygame.JOYHATMOTION]:
                sample = True

        if sample:
            joystick.do_sample()
    
