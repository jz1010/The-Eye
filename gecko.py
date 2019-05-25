#!/usr/bin/python

import os
import sys
import Adafruit_ADS1x15
import math
import pi3d
import random
import thread
import time
from svg.path import Path, parse_path
from xml.dom.minidom import parse
from gfxutil import *
import argparse
from joystick import joystick_t
import time

DISPLAY = pi3d.Display.create(samples=4)

class gecko_eye_t(object):
    def __init__(self,debug=False,EYE_SELECT=None):
        self.debug = debug
        self.init_cfg_db()
        self.EYE_SELECT = None
        if EYE_SELECT is not None:
            self.EYE_SELECT = EYE_SELECT
        elif self.EYE_SELECT is None:
            self.EYE_SELECT = os.getenv('EYE_SELECT','dragon')

        self.parse_args()
        self.init()

    def parse_args(self):
        self.parser = argparse.ArgumentParser(description="Parse arguments")
        self.parser.add_argument('--demo',default=self.cfg_db['demo'],
                                 action='store_true',help='Demo mode (headless, various eye animations)')
        self.parser.add_argument('--autoblink',default=self.cfg_db['AUTOBLINK'],
                                 action='store',help='Autoblink of eyelid')
        self.parser.add_argument('--eye_select',default=self.EYE_SELECT,
                                 action='store',help='Eye profile selection')
        self.parser.add_argument('--eye_shape',default=self.cfg_db[self.EYE_SELECT]['eye.shape'],
                                 action='store',help='Eye shape art file (.svg)')
        self.parser.add_argument('--iris_art',default=self.cfg_db[self.EYE_SELECT]['iris.art'],        
                                 action='store',help='Iris art file (.jpg)')
        self.parser.add_argument('--lid_art',default=self.cfg_db[self.EYE_SELECT]['lid.art'],        
                                 action='store',help='Lid art file (.png)')
        self.parser.add_argument('--sclera_art',default=self.cfg_db[self.EYE_SELECT]['sclera.art'],        
                                 action='store',help='Sclera art file (.png)')

        # Parse the arguments
        args = self.parser.parse_args()

        # Harvest and validate the arguments
        self.cfg_db['AUTOBLINK'] = (int(args.autoblink) != 0)
        if self.EYE_SELECT is None:
            self.EYE_SELECT = args.eye_select

        if args.eye_shape not in ["None"]:
            self.cfg_db[self.EYE_SELECT]['eye.shape'] = args.eye_shape
        if args.iris_art not in ["None"]:
            self.cfg_db[self.EYE_SELECT]['iris.art'] = args.iris_art
        if args.lid_art not in ["None"]:            
            self.cfg_db[self.EYE_SELECT]['lid.art'] = args.lid_art
        if args.sclera_art not in ["None"]:                        
            self.cfg_db[self.EYE_SELECT]['sclera.art'] = args.sclera_art
        self.cfg_db['demo'] = args.demo
        
        
    def init_cfg_db(self):
        self.cfg_db = {
            'demo': False, # Demo mode boolean
            'JOYSTICK_X_IN': -1,    # Analog input for eye horiz pos (-1 = auto)
            'JOYSTICK_Y_IN': -1,    # Analog input for eye vert position (")
            'PUPIL_IN': -1,    # Analog input for pupil control (-1 = auto)
            'JOYSTICK_X_FLIP': False, # If True, reverse stick X axis
            'JOYSTICK_Y_FLIP': False, # If True, reverse stick Y axis
            'PUPIL_IN_FLIP': False, # If True, reverse reading from PUPIL_IN
            #'TRACKING'        = True  # If True, eyelid tracks pupil
            'TRACKING': True,  # If True, eyelid tracks pupil
            'PUPIL_SMOOTH': 16,    # If > 0, filter input from PUPIL_IN
            'PUPIL_MIN': 0.0,   # Lower analog range from PUPIL_IN
            'PUPIL_MAX': 1.0,   # Upper "
            #PUPIL_MAX       = 2.0   # Upper "
            #PUPIL_MAX       = 0.5   # Upper "
            'AUTOBLINK' : True,  # If True, eye blinks autonomously
            #AUTOBLINK       = False  # If True, eye blinks autonomously
            'cyclops': {
		'eye.shape': 'graphics/cyclops-eye.svg',
		'iris.art': 'graphics/iris.jpg',
		'lid.art': 'graphics/lid.png',
		'sclera.art': 'graphics/sclera.png'
		},
            'dragon': {
		'eye.shape': 'graphics/dragon-eye.svg',
		'iris.art': 'graphics/dragon-iris.jpg',
		'lid.art': 'graphics/lid.png',
		'sclera.art': 'graphics/dragon-sclera.png'
            },
            'hack': {
#		'eye.shape': 'hack_graphics/cyclops-eye.svg',                
#		'eye.shape': 'hack_graphics/dragon-eye.svg',
		'eye.shape': 'hack_graphics/gecko-eye_0.svg',                
		'iris.art': 'hack_graphics/hack.jpg',
#		'iris.art': 'hack_graphics/dragon-iris.jpg',                
		'lid.art': 'hack_graphics/lid.png',
#		'sclera.art': 'hack_graphics/dragon-sclera.png',
#		'sclera.art': 'hack_graphics/dragon-iris.jpg'
#		'sclera.art': 'hack_graphics/gecko_s_eye_by_mchahine_d2en705-fullview.jpg'
                'sclera.art': 'hack_graphics/leopard-gecko-3381555_960_720.jpg',

                'sclera.art': 'hack_graphics/Ds4CWFgV4AAlhWK.jpg_large.jpg',                
		 }           
        }
        
    def init(self):
        self.init_svg()
        self.init_display()
        self.load_textures()
        self.init_geometry()
        self.init_globals()
        self.init_joystick()
        
    def init_joystick(self):
        #self.joystick = joystick_t()
        self.joystick = None
        self.joystick_polls = 0
        
        # Set up state kept from events sampled from joystick
        self.event_blink = 1
        self.update_eye_events(reset=True)
        
    def init_svg(self):
        # Load SVG file, extract paths & convert to point lists --------------------

        # Thanks Glen Akins for the symmetrical-lidded cyclops eye SVG!
        # Iris & pupil have been scaled down slightly in this version to compensate
        # for how the WorldEye distorts things...looks OK on WorldEye now but might
        # seem small and silly if used with the regular OLED/TFT code.
        dom                    = parse(self.cfg_db[self.EYE_SELECT]['eye.shape'])        
        self.vb                = getViewBox(dom)
        self.pupilMinPts       = getPoints(dom, "pupilMin"      , 32, True , True )
        self.pupilMaxPts       = getPoints(dom, "pupilMax"      , 32, True , True )
        self.irisPts           = getPoints(dom, "iris"          , 32, True , True )
        self.scleraFrontPts    = getPoints(dom, "scleraFront"   ,  0, False, False)
        self.scleraBackPts     = getPoints(dom, "scleraBack"    ,  0, False, False)
        self.upperLidClosedPts = getPoints(dom, "upperLidClosed", 33, False, True )
        self.upperLidOpenPts   = getPoints(dom, "upperLidOpen"  , 33, False, True )
        self.upperLidEdgePts   = getPoints(dom, "upperLidEdge"  , 33, False, False)
        self.lowerLidClosedPts = getPoints(dom, "lowerLidClosed", 33, False, False)
        self.lowerLidOpenPts   = getPoints(dom, "lowerLidOpen"  , 33, False, False)
        self.lowerLidEdgePts   = getPoints(dom, "lowerLidEdge"  , 33, False, False)

    def init_display(self):
        global DISPLAY
        self.DISPLAY = DISPLAY
        self.DISPLAY.set_background(0, 0, 0, 1) # r,g,b,alpha

        # eyeRadius is the size, in pixels, at which the whole eye will be rendered.
        if self.DISPLAY.width <= (self.DISPLAY.height * 2):
            # For WorldEye, eye size is -almost- full screen height
            self.eyeRadius   = self.DISPLAY.height / 2.1
        else:
            self.eyeRadius   = self.DISPLAY.height * 2 / 5

        # A 2D camera is used, mostly to allow for pixel-accurate eye placement,
        # but also because perspective isn't really helpful or needed here, and
        # also this allows eyelids to be handled somewhat easily as 2D planes.
        # Line of sight is down Z axis, allowing conventional X/Y cartesion
        # coords for 2D positions.
        self.cam    = pi3d.Camera(is_3d=False, at=(0,0,0), eye=(0,0,-1000))
        self.shader = pi3d.Shader("uv_light")
        self.light  = pi3d.Light(lightpos=(0, -500, -500), lightamb=(0.2, 0.2, 0.2))
        

    def load_textures(self):
        # Load texture maps --------------------------------------------------------

        self.irisMap   = pi3d.Texture(self.cfg_db[self.EYE_SELECT]['iris.art'],
                                      mipmap=False,
                                      filter=pi3d.GL_LINEAR)
        self.scleraMap = pi3d.Texture(self.cfg_db[self.EYE_SELECT]['sclera.art'],
                                      mipmap=False,
                                      filter=pi3d.GL_LINEAR,
                                      blend=True)
        self.lidMap    = pi3d.Texture(self.cfg_db[self.EYE_SELECT]['lid.art'],
                                      mipmap=False,
                                      filter=pi3d.GL_LINEAR,
                                      blend=True)
        # U/V map may be useful for debugging texture placement; not normally used
        #uvMap     = pi3d.Texture(self.cfg_db[self.EYE_SELECT]['uv.art'], mipmap=False,
        #              filter=pi3d.GL_LINEAR, blend=False, m_repeat=True)

    def init_geometry_iris(self):
        # Generate initial iris mesh; vertex elements will get replaced on
        # a per-frame basis in the main loop, this just sets up textures, etc.
        self.iris = meshInit(32, 4, True, 0, 0.5/self.irisMap.iy, False)
        self.iris.set_textures([self.irisMap])
        self.iris.set_shader(self.shader)
        self.irisZ = zangle(self.irisPts, self.eyeRadius)[0] * 0.99 # Get iris Z depth, for later

    def init_geometry_eyelids(self):
        # Eyelid meshes are likewise temporary; texture coordinates are
        # assigned here but geometry is dynamically regenerated in main loop.
        self.upperEyelid = meshInit(33, 5, False, 0, 0.5/self.lidMap.iy, True)
        self.upperEyelid.set_textures([self.lidMap])
        self.upperEyelid.set_shader(self.shader)
        self.lowerEyelid = meshInit(33, 5, False, 0, 0.5/self.lidMap.iy, True)
        self.lowerEyelid.set_textures([self.lidMap])
        self.lowerEyelid.set_shader(self.shader)

    def init_geometry_sclera(self):
        # Generate sclera for eye...start with a 2D shape for lathing...
        angle1 = zangle(self.scleraFrontPts, self.eyeRadius)[1] # Sclera front angle
        angle2 = zangle(self.scleraBackPts , self.eyeRadius)[1] # " back angle
        aRange = 180 - angle1 - angle2
        pts    = []
        for i in range(24):
            ca, sa = pi3d.Utility.from_polar((90 - angle1) - aRange * i / 23)
            pts.append((ca * self.eyeRadius, sa * self.eyeRadius))

        self.eye = pi3d.Lathe(path=pts, sides=64)
        self.eye.set_textures([self.scleraMap])
        self.eye.set_shader(self.shader)
        reAxis(self.eye, 0.0)
        
    def init_geometry(self):
        # Initialize static geometry -----------------------------------------------

        # Transform point lists to eye dimensions
        scalePoints(self.pupilMinPts      , self.vb, self.eyeRadius)
        scalePoints(self.pupilMaxPts      , self.vb, self.eyeRadius)
        scalePoints(self.irisPts          , self.vb, self.eyeRadius)
        scalePoints(self.scleraFrontPts   , self.vb, self.eyeRadius)
        scalePoints(self.scleraBackPts    , self.vb, self.eyeRadius)
        scalePoints(self.upperLidClosedPts, self.vb, self.eyeRadius)
        scalePoints(self.upperLidOpenPts  , self.vb, self.eyeRadius)
        scalePoints(self.upperLidEdgePts  , self.vb, self.eyeRadius)
        scalePoints(self.lowerLidClosedPts, self.vb, self.eyeRadius)
        scalePoints(self.lowerLidOpenPts  , self.vb, self.eyeRadius)
        scalePoints(self.lowerLidEdgePts  , self.vb, self.eyeRadius)

        # Regenerating flexible object geometry (such as eyelids during blinks, or
        # iris during pupil dilation) is CPU intensive, can noticably slow things
        # down, especially on single-core boards.  To reduce this load somewhat,
        # determine a size change threshold below which regeneration will not occur;
        # roughly equal to 1/2 pixel, since 2x2 area sampling is used.

        # Determine change in pupil size to trigger iris geometry regen
        irisRegenThreshold = 0.0
        a = pointsBounds(self.pupilMinPts) # Bounds of pupil at min size (in pixels)
        b = pointsBounds(self.pupilMaxPts) # " at max size
        maxDist = max(abs(a[0] - b[0]), abs(a[1] - b[1]), # Determine distance of max
                      abs(a[2] - b[2]), abs(a[3] - b[3])) # variance around each edge
        # maxDist is motion range in pixels as pupil scales between 0.0 and 1.0.
        # 1.0 / maxDist is one pixel's worth of scale range.  Need 1/2 that...
        if maxDist > 0: self.irisRegenThreshold = 0.5 / maxDist

        # Determine change in eyelid values needed to trigger geometry regen.
        # This is done a little differently than the pupils...instead of bounds,
        # the distance between the middle points of the open and closed eyelid
        # paths is evaluated, then similar 1/2 pixel threshold is determined.
        self.upperLidRegenThreshold = 0.0
        self.lowerLidRegenThreshold = 0.0
        p1 = self.upperLidOpenPts[len(self.upperLidOpenPts) / 2]
        p2 = self.upperLidClosedPts[len(self.upperLidClosedPts) / 2]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        d  = dx * dx + dy * dy
        if d > 0: self.upperLidRegenThreshold = 0.5 / math.sqrt(d)
        p1 = self.lowerLidOpenPts[len(self.lowerLidOpenPts) / 2]
        p2 = self.lowerLidClosedPts[len(self.lowerLidClosedPts) / 2]
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        d  = dx * dx + dy * dy
        if d > 0: self.lowerLidRegenThreshold = 0.5 / math.sqrt(d)

        self.init_geometry_iris()
        self.init_geometry_eyelids()
        self.init_geometry_sclera()

    def init_globals(self):
        # Init global stuff --------------------------------------------------------

        #self.mykeys = pi3d.Keyboard() # For capturing key presses
        self.mykeys = None
        
        self.startX       = random.uniform(-30.0, 30.0)
        n = math.sqrt(900.0 - self.startX * self.startX)
        self.startY       = random.uniform(-n, n)
        self.destX        = self.startX
        self.destY        = self.startY
        self.curX         = self.startX
        self.curY         = self.startY
        self.moveDuration = random.uniform(0.075, 0.175)
        self.holdDuration = random.uniform(0.1, 1.1)
        self.startTime    = 0.0
        self.isMoving     = False

        self.frames        = 0
        self.beginningTime = time.time()

        self.eye.positionX(0.0)
        self.iris.positionX(0.0)
        self.upperEyelid.positionX(0.0)
        self.upperEyelid.positionZ(-self.eyeRadius - 42)
        self.lowerEyelid.positionX(0.0)
        self.lowerEyelid.positionZ(-self.eyeRadius - 42)

        self.currentPupilScale  =  0.5
        self.prevPupilScale     = -1.0 # Force regen on first frame
        self.prevUpperLidWeight = 0.5
        self.prevLowerLidWeight = 0.5
        self.prevUpperLidPts    = pointsInterp(self.upperLidOpenPts, self.upperLidClosedPts, 0.5)
        self.prevLowerLidPts    = pointsInterp(self.lowerLidOpenPts, self.lowerLidClosedPts, 0.5)
        
        self.ruRegen = True
        self.rlRegen = True

        self.timeOfLastBlink = 0.0
        self.timeToNextBlink = 1.0
        self.blinkState      = 0
        self.blinkDuration   = 0.1
        self.blinkStartTime  = 0

        self.trackingPos = 0.3        

    def split(self, # Recursive simulated pupil response when no analog sensor
              startValue, # Pupil scale starting value (0.0 to 1.0)
              endValue,   # Pupil scale ending value (")
              duration,   # Start-to-end time, floating-point seconds
              range):     # +/- random pupil scale at midpoint
        do_exit = False
	startTime = time.time()
	if range >= 0.125: # Limit subdvision count, because recursion
		duration *= 0.5 # Split time & range in half for subdivision,
		range    *= 0.5 # then pick random center point within range:
		midValue  = ((startValue + endValue - range) * 0.5 +
		             random.uniform(0.0, range))
		do_exit |= self.split(startValue, midValue, duration, range)
                if not do_exit:
		    do_exit |= self.split(midValue  , endValue, duration, range)
	else: # No more subdivisons, do iris motion...
		dv = endValue - startValue
		while not do_exit:
			dt = time.time() - startTime
			if dt >= duration: break
                        if self.pupil_event_queued: break
                        if self.eye_context_next is not None: break                        
			v = startValue + dv * dt / duration
			if   v < self.cfg_db['PUPIL_MIN']: v = self.cfg_db['PUPIL_MIN']
			elif v > self.cfg_db['PUPIL_MAX']: v = self.cfg_db['PUPIL_MAX']
			self.frame(v) # Draw frame w/interim pupil scale value
                        self.do_joystick()
                        do_exit |= self.keyboard_sample()

        return do_exit

    # Generate one frame of imagery
    def frame(self,p):
	self.DISPLAY.loop_running()

	now = time.time()
	dt  = now - self.startTime

	self.frames += 1
#	if(now > beginningTime):
#		print(frames/(now-beginningTime))

	if self.cfg_db['JOYSTICK_X_IN'] >= 0 and self.cfg_db['JOYSTICK_Y_IN'] >= 0:
            # Eye position from analog inputs
            self.curX = adcValue[self.cfg_db['JOYSTICK_X_IN']]
            self.curY = adcValue[self.cfg_db['JOYSTICK_Y_IN']]
            if self.cfg_db['JOYSTICK_X_FLIP']: self.curX = 1.0 - self.curX
            if self.cfg_db['JOYSTICK_Y_FLIP']: self.curY = 1.0 - self.curY
            self.curX = -30.0 + self.curX * 60.0
            self.curY = -30.0 + self.curY * 60.0
	else :
            # Autonomous eye position
            if self.isMoving == True:
                if dt <= self.moveDuration:
                    scale        = (now - self.startTime) / self.moveDuration
                    # Ease in/out curve: 3*t^2-2*t^3
                    scale = 3.0 * scale * scale - 2.0 * scale * scale * scale
                    self.curX         = self.startX + (self.destX - self.startX) * scale
                    self.curY         = self.startY + (self.destY - self.startY) * scale
                else:
                    self.startX       = self.destX
                    self.startY       = self.destY
                    self.curX         = self.destX
                    self.curY         = self.destY
                    self.holdDuration = random.uniform(0.15, 1.7)
                    self.startTime    = now
                    self.isMoving     = False
            elif self.event_eye_queued:
                if self.event_eye_up:
                    self.destX = 0.0
                    n = math.sqrt(900.0 - self.destX * self.destX)
                    self.destY = n
                elif self.event_eye_down:
                    self.destX = 0.0                    
                    n = math.sqrt(900.0 - self.destX * self.destX)
                    self.destY = -n
                elif self.event_eye_left:
                    self.destX = 30.0
                    self.destY = 0.0
                elif self.event_eye_right:
                    self.destX = -30.0
                    self.destY = 0.0
                elif self.event_eye_center:
                    self.destX = 0.0
                    self.destY = 0.0
                else:
                    raise
                self.moveDuration = 0.12
                self.startTime    = now
                self.isMoving     = True
                self.update_eye_events(reset=True)
            elif True:
                if dt >= self.holdDuration:
                    self.destX        = random.uniform(-30.0, 30.0)
                    n            = math.sqrt(900.0 - self.destX * self.destX)
                    self.destY        = random.uniform(-n, n)
                    # Movement is slower in this version because
                    # the WorldEye display is big and the eye
                    # should have some 'mass' to it.
                    self.moveDuration = random.uniform(0.12, 0.35)
                    self.startTime    = now
                    self.isMoving     = True


	# Regenerate iris geometry only if size changed by >= 1/2 pixel
	if abs(p - self.prevPupilScale) >= self.irisRegenThreshold:
		# Interpolate points between min and max pupil sizes
		interPupil = pointsInterp(self.pupilMinPts, self.pupilMaxPts, p)
		# Generate mesh between interpolated pupil and iris bounds
		mesh = pointsMesh(None, interPupil, self.irisPts, 4, -self.irisZ, True)
		self.iris.re_init(pts=mesh)
		self.prevPupilScale = p

	# Eyelid WIP

	if self.cfg_db['AUTOBLINK'] and (now - self.timeOfLastBlink) >= self.timeToNextBlink:
		# Similar to movement, eye blinks are slower in this version
		self.timeOfLastBlink = now
		duration        = random.uniform(0.06, 0.12)
		if self.blinkState != 1:
			self.blinkState     = 1 # ENBLINK
			self.blinkStartTime = now
			self.blinkDuration  = duration
                self.timeToNextBlink = duration * 3 + random.uniform(0.0, 4.0)

	if self.blinkState: # Eye currently winking/blinking?
		# Check if blink time has elapsed...
		if (now - self.blinkStartTime) >= self.blinkDuration:
			# Yes...increment blink state, unless...
			if (self.blinkState == 1 and # Enblinking and...
                            self.event_blink == 0):
				# Don't advance yet; eye is held closed
				pass
			else:
				self.blinkState += 1
				if self.blinkState > 2:
					self.blinkState = 0 # NOBLINK
				else:
					self.blinkDuration *= 2.0
					self.blinkStartTime = now
	else:
            if self.event_blink == 0:
                self.blinkState     = 1 # ENBLINK
                self.blinkStartTime = now
                self.blinkDuration  = random.uniform(0.035, 0.06)

	if self.cfg_db['TRACKING']:
		# 0 = fully up, 1 = fully down
		n = 0.5 - self.curY / 70.0
		if   n < 0.0: n = 0.0
		elif n > 1.0: n = 1.0
		self.trackingPos = (self.trackingPos * 3.0 + n) * 0.25

	if self.blinkState:
		n = (now - self.blinkStartTime) / self.blinkDuration
		if n > 1.0: n = 1.0
		if self.blinkState == 2: n = 1.0 - n
	else:
		n = 0.0
        self.newUpperLidWeight = self.trackingPos + (n * (1.0 - self.trackingPos))
	self.newLowerLidWeight = (1.0 - self.trackingPos) + (n * self.trackingPos)

	if (self.ruRegen or (abs(self.newUpperLidWeight - self.prevUpperLidWeight) >=
                             self.upperLidRegenThreshold)):
            self.newUpperLidPts = pointsInterp(self.upperLidOpenPts,
                                               self.upperLidClosedPts,
                                               self.newUpperLidWeight)
            if self.newUpperLidWeight > self.prevUpperLidWeight:
                self.upperEyelid.re_init(pts=pointsMesh(
                    self.upperLidEdgePts, self.prevUpperLidPts,
                    self.newUpperLidPts, 5, 0, False, True))
            else:
                self.upperEyelid.re_init(pts=pointsMesh(
                    self.upperLidEdgePts, self.newUpperLidPts,
                    self.prevUpperLidPts, 5, 0, False, True))
            self.prevUpperLidWeight = self.newUpperLidWeight
            self.prevUpperLidPts    = self.newUpperLidPts
            self.ruRegen = True
	else:
            self.ruRegen = False

	if (self.rlRegen or (abs(self.newLowerLidWeight - self.prevLowerLidWeight) >=
                             self.lowerLidRegenThreshold)):
            self.newLowerLidPts = pointsInterp(self.lowerLidOpenPts,
                                          self.lowerLidClosedPts, self.newLowerLidWeight)
            if self.newLowerLidWeight > self.prevLowerLidWeight:
                self.lowerEyelid.re_init(pts=pointsMesh(
                    self.lowerLidEdgePts, self.prevLowerLidPts,
                    self.newLowerLidPts, 5, 0, False, True))
            else:
                self.lowerEyelid.re_init(pts=pointsMesh(
                    self.lowerLidEdgePts, self.newLowerLidPts,
                    self.prevLowerLidPts, 5, 0, False, True))
            self.prevLowerLidWeight = self.newLowerLidWeight
            self.prevLowerLidPts    = self.newLowerLidPts
            self.rlRegen = True
	else:
            self.rlRegen = False

	# Draw eye
	self.iris.rotateToX(self.curY)
	self.iris.rotateToY(self.curX)
	self.iris.draw()
	self.eye.rotateToX(self.curY)
	self.eye.rotateToY(self.curX)
	self.eye.draw()
        self.upperEyelid.draw()
        self.lowerEyelid.draw()

    def keyboard_sample(self):
        if self.mykeys is not None:
            k = self.mykeys.read()
            if k==27:
                self.mykeys.close()
                #self.eye_context_next = None
                return True
        return False

    def update_eye_events(self,reset=False):
        if reset:
            self.eye_context_next = None
            self.event_eye_up = False
            self.event_eye_down = False
            self.event_eye_left = False
            self.event_eye_right = False
            self.event_eye_center = False
            self.event_eye_queued = False
            self.eye_event_last = None
            self.pupil_event_queued = False
            self.pupil_event_last = None
            
        self.event_eye_joystick = self.event_eye_up or \
                                  self.event_eye_down or \
                                  self.event_eye_left or \
                                  self.event_eye_right or \
                                  self.event_eye_center

    def set_eye_event(self,eye_event):
        if self.event_eye_queued:
            return

        if eye_event is self.eye_event_last:
            return
        
        if eye_event in ['eye_up']:
            self.event_eye_up = True
        elif eye_event in ['eye_down']:
            self.event_eye_down = True                
        elif eye_event in ['eye_left']:
            self.event_eye_left = True
        elif eye_event in ['eye_right']:
            self.event_eye_right = True
        elif eye_event in ['eye_center']:
            self.event_eye_center = True

        self.event_eye_queued = True
        self.eye_event_last = eye_event
        
    def handle_events(self,events):
        if len(events) == 0:
            return
        
        for event in events:
            print ('event: {}'.format(event))
            if event in ['eye_up','eye_down','eye_left','eye_right','eye_center']:
                self.set_eye_event(event)
            elif event in ['pupil_widen','pupil_narrow']:
                if not self.pupil_event_queued:
                    self.event_pupil = event
                    self.pupil_event_queued = True
            elif event in ['blink']:
                self.event_blink ^= 1
            elif event in ['eye_context_9']:
                self.eye_context_next = 'dragon'
            elif event in ['eye_context_11']:
                self.eye_context_next = 'cyclops'
            elif event in ['eye_context_12']:
                self.eye_context_next = 'hack'                
            else:
                print ('Unhandled event: {}'.format(event))
                raise
        self.update_eye_events()

    def do_joystick(self):
        if self.joystick is not None:
            gecko_events = self.joystick.sample_nonblocking()
            self.handle_events(gecko_events)
            self.joystick_polls +=1
        
        if self.debug:
            print ('joystick_polls: {}'.format(self.joystick_polls))

    def run(self):
        global eye_context_ptr
        do_exit = False
        last_time_sec = time.time()
        while not do_exit:
            if self.cfg_db['PUPIL_IN'] >= 0: # Pupil scale from sensor
		v = adcValue[self.cfg_db['PUPIL_IN']]
		if self.cfg_db['PUPIL_IN_FLIP']: v = 1.0 - v
		# If you need to calibrate PUPIL_MIN and MAX,
		# add a 'print v' here for testing.
		if   v < self.cfg_db['PUPIL_MIN']: v = self.cfg_db['PUPIL_MIN']
		elif v > self.cfg_db['PUPIL_MAX']: v = self.cfg_db['PUPIL_MAX']
		# Scale to 0.0 to 1.0:
		v = (v - self.cfg_db['PUPIL_MIN']) / (self.cfg_db['PUPIL_MAX'] -
                                                      self.cfg_db['PUPIL_MIN'])
		if self.cfg_db['PUPIL_SMOOTH'] > 0:
			v = ((currentPupilScale * (self.cfg_db['PUPIL_SMOOTH'] - 1) + v) /
			     self.cfg_db['PUPIL_SMOOTH'])
                self.frame(v)
            else: # Fractal auto pupil scale
                if self.eye_context_next is not None:
                    break
                elif self.pupil_event_queued:
                    self.pupil_event_queued = False
                    self.eye_event_last = self.event_pupil
                    if self.event_pupil in ['pupil_widen']:
                        v = 1.0
                    elif self.event_pupil in ['pupil_narrow']:
                        v = 0.0
                    else:
                        raise
                    duration = 0.25
                else:
                    v = random.random()
                    duration = 4.0
                do_exit |= self.split(self.currentPupilScale, v, duration, 1.0)
                

            self.currentPupilScale = v
            #do_exit = self.keyboard_sample()
            now_time_sec = time.time()
            eye_tenure_sec = 10
            if int(now_time_sec - last_time_sec) > eye_tenure_sec:
                do_exit |= True
    
            
        if do_exit:
            #print ('exiting')
            if self.cfg_db['demo']:
                eye_contexts = ['cyclops','hack','dragon']
                self.eye_context_next = eye_contexts[eye_context_ptr]
                eye_context_ptr += 1
                eye_context_ptr %= len(eye_contexts)
            else:
                self.eye_context_next = None

        return self.eye_context_next

    def shutdown(self):
        #self.joystick.shutdown()
        pass
    
        
if __name__ == "__main__":
    eye_context_ptr = 0
    eye_context = None
    while True:
        gecko_eye = gecko_eye_t(EYE_SELECT=eye_context)
        eye_context = gecko_eye.run()
        #print ('main loop')
        gecko_eye.shutdown()
        if eye_context is None:
            break

    DISPLAY.destroy()
        
    sys.exit(0)
