#!/usr/bin/python
#
#   OBS_OSC.py
#
#   by Claude Heintz
#   copyright 2014-2020 by Claude Heintz Design
#
#  see license included with this distribution or
#  https://www.claudeheintzdesign.com/lx/opensource.html
#

import socket
import threading
import time
from select import select
import math
import struct
import obspython as obs


OBS_OSC_PORT = 17999
OBS_OSC_AUTO_START = 1

#########################################
#
#   This script responds to OSC messages received from port OBS_OSC_PORT
#   in OSCListener's dispatch_message() method by calling the appropriate
#   functions from obspython
#
#   Note:
#   all OSC triggers require a 1.0 float argument so that
#   they are compatible with TouchOSC type buttons which
#   send 1.0 when pressed and 0.0 when released
#
#   -------------------------------------------
#
#   OBS OSC Messages:
#
#   /obs/transition/start
#       triggers the current transition
#
#   /obs/transition/NN/select
#       selects transition number NN (1 based)
#       /obs/transition/1/select chooses first transition (index 0 in obspython)
#
#   /obs/transition/NN/start
#       selects and executes transition number NN (1 based index)
#       /obs/transition/1/start chooses first transition (index 0 in obspython)
#
#   /obs/scene/NN/preview
#       selects scene number NN  (1 based)
#       /obs/scene/1/preview sets the preview to the first scene  (index 0 in obspython)
#
#   /obs/scene/NN/start
#       selects scene number NN  (1 based) and then transitions to that scene
#       following the transition, the next scene is selected for preview
#
#   /obs/scene/NN/go
#       selects scene number NN  (1 based) and then transitions to that scene
#       following the transition, the next scene is selected for preview
#
#       /obs/scene/1/go sets the preview to the first scene  (index 0 in obspython)
#       following the transition, the second scene is set to preview 
#
#   /obs/scene/NN/transition/MM/start
#       selects scene number NN  (1 based) and then transitions to that scene
#       using transition number MM (1 based)
#
#   /obs/scene/NN/transition/MM/go
#       selects scene number NN  (1 based) and then transitions to that scene
#       using transition number MM (1 based)
#       following the transition, the next scene is selected for preview
#
#       /obs/scene/2/transition/2/go sets the preview to the second scene in the list
#       (index 1 in obspython) then transitions to that scene using the second transition
#       (index 1 in obspython)
#       following the transition, the third scene is set to preview 
#
#   /obs/go
#       transitions to the current previewed scene using the current transition
#       following the transition, the scene following the former preview scene
#       in the scene list is selected for preview
#
#   /obs/recording/start
#       starts recording
#
#   /obs/recording/stop
#       stops recording
#
#   /obs/streaming/start
#       starts streaming
#
#   /obs/streaming/stop
#       stops streaming
#
#########################################


#########################################
#
#   OSCListener
#       implements basic OSC UDP receiving and parsing
#
#   start_listening(port)
#       starts a thread that listenes for UDP packets on the specified port
#
#   stop_listening()
#       terminates the listen loop/thread
#
#   dispatch_message()
#       is called when an OSC message is received, after
#       its addressPattern and args[] are extracted
#       obspython methods are called based on the addressPattern
#
#########################################

class OSCListener:
    
    def __init__(self):
        self.listen_thread = None 

#########################################
#
#   start_listening creates the listening socket
#   and creates a thread that runs the listen() method
#
#########################################
    
    def start_listening(self, port):
        self.udpsocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udpsocket.bind(('',port))
        self.udpsocket.setblocking(False)
        self.udpsocket.settimeout(1)
        self.listening = True
        if self.listen_thread is None:
            self.listen_thread = threading.Thread(target=self.listen)
            self.listen_thread.daemon = True
            self.listen_thread.start()

#########################################
#
#   stop_listening sets a flag which will cause the listen loop to end on the next pass
#
#########################################
            
    def stop_listening(self):
        self.listening = False
        self.udpsocket.close()
        self.udpsocket = None
        
#########################################
#
#   listen contains a loop that runs while the self.listening flag is True
#   listen uses select to determine if there is data available from the port
#   if there is, packet_received is called
#   if not, the thread sleeps for a tenth of a second
#
#########################################
        
    def listen(self):
        input = [self.udpsocket]

        while self.listening:
            if self.udpsocket != None and self.udpsocket.fileno() >= 0:
                inputready,outputready,exceptready = select(input,[],[],0)
                if ( len(inputready) == 1 ):
                    self.data,addr = self.udpsocket.recvfrom(256)
                    self.msglen = len(self.data)
                    self.packet_received()
                else:
                    time.sleep(0.1)
            else:
                self.listening = false
    
        self.listen_thread = None

#########################################
#
#   packet_received
#   calls process_message_at for each complete OSC message
#   contained in the packet
#
#########################################
    
    def packet_received(self):
        dataindex = 0
        while ( (dataindex >= 0 ) and ( dataindex < self.msglen ) ):
            dataindex = self.process_message_at(dataindex);

#########################################
#
#   process_message_at
#   extracts the addressPattern and argument list from the OSC message
#
#   currently the only supported arguments are floats and integers and strings
#
#   returns the index at the end of the complete message
#
#########################################

    def process_message_at(self, si):
        oi = 0;
        dl = 0;
        zl = self.next_zero(si)
        
        #insure that string will terminate with room for 4 bytes of type definition
        if zl + 4 < self.msglen: 
            addressPattern = self.string_from_index(si)
            if addressPattern.startswith('/'):
                # determine the current index for the type character
                tl = self.next_index_for_string(addressPattern,si)
                
                # determine the current index for the data location
                dl = self.next_index_for_index(self.next_zero(tl))
                
                # if there's space for at least one argument, start a loop extracting
                # arguments defined in the type string an adding them to the args list
                if dl+4 <= self.msglen:
                    if self.data[tl] == ord(','):
                        tl += 1
                    args = []
                    done = False
                    while ( not done) and ( (dl+4) <= self.msglen ):
                        if self.data[tl] == 0:
                            done = True
                        elif self.data[tl] == ord('f'):
                            a = struct.unpack_from('>f', self.data, dl)
                            args.append(float(a[0]))
                            dl += 4
                        elif self.data[tl] == ord('i'):
                            a = struct.unpack_from('>i', self.data, dl)
                            args.append(int(a[0]))
                        elif self.data[tl] == ord('s'):
                            es = self.next_zero(dl)
                            if es <= self.msglen:
                                a = self.string_from_index(dl)
                                args.append(a)
                                dl = self.next_index_for_index(es)
                            else:
                                done = True
                                oi = -1
                        else:   #unrecognized argument don't know length
                            done = True
                            oi = -1
                        tl += 1
                    
                    # when done with the argument extraction loop, call dispatch_message
                    self.dispatch_message(addressPattern, args)

                else: # <- no arguments but an address pattern
                    oi = -1
                    self.dispatch_message(addressPattern, [])
        else:
            oi = -1
            
        if oi != -1:
            oi = dl     #dl could point to another message within the packet
        
        return oi   

#########################################
#
#   next_zero
#   searches for the next null character in the data starting at index si
#
#########################################
        
    def next_zero(self, si):
        i = si
        notfound = True
        s = ''
        while notfound and i<self.msglen:
            if self.data[i] == 0:
                notfound = False
            else:
                i += 1
        return i

#########################################
#
#   next_index_for_string
#   determines a 4 byte padded index for the
#   length of the string starting from si
#
#########################################
        
    def next_index_for_string(self, s, start):
        ml = math.trunc(len(s) / 4) + 1;
        return start + (ml*4);
        
#########################################
#
#   next_index_for_index 
#   determines a 4 byte padded index starting from i
#
#########################################
        
    def next_index_for_index(self, i):
        ml = math.trunc(i / 4) + 1;
        return ml*4;

#########################################
#
#   string_from_index
#   extracts a null terminated string starting at index si
#
#########################################
        
    def string_from_index(self, si):
        i = si
        noterm = True
        s = ''
        while noterm and i<len(self.data):
            if self.data[i] == 0:
                noterm = False
            else:
                s +=  chr(self.data[i])
                i += 1
        return s
 
 #########################################
#
#   check_arg_one()
#       Check for a single float argument equal to 1.0.
#
#       used for actions controlled by a push button
#       that sends 1.0 when pressed
#       0.0 when released
#
#########################################
       
    def check_arg_one(self, args):
        if len(args) == 1:
            if args[0] == 1.0:
                return True
        return False

#########################################
#
#  dispatch_message
#  called when OSC Message is received and processed
#
#########################################

    def dispatch_message(self, addressPattern, args):
        # break addressPattern into parts
        parts = addressPattern.split('/')
               
        if len(parts) > 2:
            if parts[1] == "obs":                       #/obs/...
                
                if  parts[2] == "source":               # /obs/source/...
                    self.dispatch_obs_source(parts, args)
                
                elif parts[2] == "transition":          # /obs/transition/...
                    self.dispatch_obs_transition(parts, args)
                
                elif parts[2] == "scene":               # /obs/scene/...
                    self.dispatch_obs_scene(parts, args)
                
                elif parts[2] == "go":                   # /obs/go
                    self.dispatch_obs_go(parts, args)
                
                elif parts[2] == "recording":            # /obs/recording/...
                    self.dispatch_obs_recording(parts, args)
                
                elif parts[2] == "streaming":            # /obs/streaming/...
                    self.dispatch_obs_streaming(parts, args)

#########################################
#
#  dispatch_obs_source(self, parts, args)
#  /obs/source/...
#
#########################################

    def dispatch_obs_source(self, parts, args): 
        if len(parts) == 4:
            if  parts[3] == "volume":       # /obs/source/volume [NN, V.V]
                if len(args) == 2:
                    source_volume(args[0], args[1])
        if len(parts) == 5:
            if  parts[4] == "volume":       # /obs/source/NN/volume [V.V]
                if len(args) == 1:
                    source_volume(parts[3], args[0]) 
    
#########################################
#
#  dispatch_obs_transition(self, parts, args)
#  /obs/transition/...
#
#########################################                   
    def dispatch_obs_transition(self, parts, args):
        if len(parts) == 4: 
            if parts[3] == "start":         # /obs/transition/start [1.0]
                if self.check_arg_one(args):
                    transition()
            elif parts[3] == "duration":    # /obs/transition/duration [DD]
                    set_transition_duration(int(args[0]))
    
        if len(parts) == 5:                 # /obs/transition/NN/start [1.0]
            if parts[4] == "start":
                if self.check_arg_one(args):
                    transition(int(parts[3])-1)
            elif parts[4] == "select":      # /obs/transition/NN/select [1.0]
                if self.check_arg_one(args):    
                    set_transition(int(parts[3])-1)
            elif parts[4] == "duration":   # /obs/transition/NN/duration [DD]
                set_transition_duration(int(args[0]), int(parts[3])-1)
            elif parts[3] == "duration":   # /obs/transition/duration/DD [1.0]
                if self.check_arg_one(args): 
                    set_transition_duration(int(parts[4]))
    
#########################################
#
#  dispatch_obs_scene(self, parts, args)
#  /obs/scene/...
#
#########################################                   
    def dispatch_obs_scene(self, parts, args):
        if self.check_arg_one(args):
            if len(parts) == 5:
                if parts[4] == "preview":       # /obs/scene/n/preview
                    set_preview(int(parts[3])-1)
                elif parts[4] == "start":       # /obs/scene/n/start
                    set_preview(int(parts[3])-1)
                    time.sleep(0.2)
                    transition()
                elif parts[4] == "go":          # /obs/scene/n/go
                    set_preview(int(parts[3])-1)
                    time.sleep(0.2)
                    go()
            elif len(parts) == 7:
                if parts[4] == "transition":
                    if parts[6] == "start":
                        set_preview(int(parts[3])-1)
                        time.sleep(0.2)
                        transition(int(parts[5])-1)
                    elif parts[6] == "go":
                        set_preview(int(parts[3])-1)
                        time.sleep(0.2)
                        go(int(parts[5])-1)
    
#########################################
#
#  dispatch_obs_go(self, parts, args)
#  /obs/go [1.0]
#
#########################################                   
    def dispatch_obs_go(self, parts, args):
        if self.check_arg_one(args):
            go()
            
#########################################
#
#  dispatch_obs_recording(self, parts, args)
#  /obs/recording/...
#
#########################################                   
    def dispatch_obs_recording(self, parts, args):
        if self.check_arg_one(args):
            if len(parts) == 4:
                if parts[3] == "start":       # /obs/recording/start
                    obs.obs_frontend_recording_start()
                if parts[3] == "stop":       # /obs/recording/stop
                    obs.obs_frontend_recording_stop()
    
#########################################
#
#  dispatch_obs_streaming(self, parts, args)
#  /obs/streaming/...
#
#########################################                   
    def dispatch_obs_streaming(self, parts, args):
        if self.check_arg_one(args):
            if len(parts) == 4:
                if parts[3] == "start":       # /obs/streaming/start
                    obs.obs_frontend_streaming_start()
                if parts[3] == "stop":       # /obs/streaming/stop
                    obs.obs_frontend_streaming_stop()            

############################################
#^^^^^^^^^^ end class OSCListener ^^^^^^^^^^
#
#           begin main section
############################################

# global OSCListener object
oscin = None

#########################################
#
#  set_preview(idx)
#  sets the OBS preview to scene with index idx if it exists
#
#########################################

def set_preview(idx):
    scenes = obs.obs_frontend_get_scenes()
    if idx < len(scenes) and idx >= 0:
        obs.obs_frontend_set_current_preview_scene(scenes[idx])

#########################################
#
#  set_transition(idx)
#   selects the OBS transition with index idx if it exists
#
#########################################

def set_transition(idx):
    transitions = obs.obs_frontend_get_transitions()
    if idx < len(transitions) and idx >= 0:
        obs.obs_frontend_set_current_transition(transitions[idx])
        
#########################################
#
#  set_transition_duration(idx)
#   selects the OBS transition with index idx if it exists
#
#########################################

def set_transition_duration(d, idx=-1):
    trans = None
    if idx == -1:
        trans = obs.obs_frontend_get_current_transition()
    else:
        transitions = obs.obs_frontend_get_transitions()
        if idx < len(transitions) and idx >= 0:
            trans = transitions[idx]
    if trans != None:
        obs.obs_transition_enable_fixed(trans, True, d)
   
#########################################
#
#  nextScene()
#   returns the next scene after the current preview scenes
#   returns the first scene if reached the end of the list or otherwise
#   (must have at least one scene or index error will throw)
#
#########################################     
def nextScene():
    scenes = obs.obs_frontend_get_scenes()
    if len(scenes) > 1:
        c_scene = obs.obs_frontend_get_current_preview_scene()
        if c_scene != None:
            i = scenes.index(c_scene) + 1
            if i < len(scenes):
                return scenes[i]
    return scenes[0]
    
#########################################
#
#   transition(idx)
#       executes the transition with index idx
#
#   transition()
#       executes the currently selected transition
#
#########################################
      
def transition(idx = -1):
    trans = None
    if idx >= 0 :
        set_transition(idx)
    trans = obs.obs_frontend_get_current_transition()
    mode = obs.OBS_TRANSITION_MODE_AUTO
    duration = 0
    p_scene = obs.obs_frontend_get_current_preview_scene()
    obs.obs_transition_start(trans, mode, duration, p_scene)
    obs.obs_frontend_set_current_scene(p_scene)

#########################################
#
#  go()
#   executes the currently selected transition
#   then selects the next scene for preview
#
#  go(idx)
#   executes the transition with index idx
#   then selects the next scene for preview
#
######################################### 

def go(idx = -1):
    n_scene = nextScene()
    transition(idx)
    time.sleep(2)
    obs.obs_frontend_set_current_preview_scene(n_scene)
    
def source_volume(src, volume):
    #n_scene = nextScene()
    sources = obs.obs_enum_sources()
    found = None
    if sources is not None:
        for source in sources:
            source_id = obs.obs_source_get_id(source)
            name = obs.obs_source_get_name(source)
            if name == src:
                found = source
    if found != None:
        obs.obs_source_set_volume(found, float(volume))

######################################### 
#   start_osc
#       create OSCListener if needed and start listening
######################################### 
    
def start_osc():
    global oscin
    global OBS_OSC_PORT
    if oscin == None:
        oscin = OSCListener()
        oscin.start_listening(OBS_OSC_PORT)
        print("OSC started on port " + str(OBS_OSC_PORT))

######################################### 
#   stop_osc
#       if OSCListener exists, stop listening & release
######################################### 
   
def stop_osc():
    global oscin
    if oscin != None:
        oscin.stop_listening()
        oscin = None
        print("OSC stopped.")

######################################### 
#   listen_pressed
#       callback when start button clicked
######################################### 
  
def listen_pressed(props, prop):
    start_osc()

######################################### 
#   stop_pressed
#       callback when start button clicked
######################################### 

def stop_pressed(props, prop):
    stop_osc()
    
######################################### 
#   port_field_changed
#       callback when the port number is changed
######################################### 
        
def port_field_changed(props, prop_id, settings_data):
    global oscin
    global OBS_OSC_PORT
    global OBS_OSC_AUTO_START
    pport = obs.obs_data_get_int(settings_data, "osc-port")
    if pport != 0:
        OBS_OSC_PORT = pport
        if oscin != None:
            stop_osc()
            print("restarting...")
            start_osc()
    
######################################### 
#       obspython functions
######################################### 

def script_defaults(settings_data):
    global OBS_OSC_PORT
    obs.obs_data_set_int(settings_data, "osc-port", OBS_OSC_PORT)

def script_update(settings):
    global OBS_OSC_AUTO_START
    if OBS_OSC_AUTO_START == 1:
        start_osc()
        OBS_OSC_AUTO_START = 0  #only first time

def script_unload():
    stop_osc()
    
def script_description():
    return '''Control OBS preview, transitions and start/stop via OSC.''' 
    
def script_properties():
    props = obs.obs_properties_create()
    
    obs.obs_properties_add_button(props, "start-button", "Start OSC", listen_pressed)
    obs.obs_properties_add_button(props, "stop-button", "Stop OSC", stop_pressed)
    
    port_field = obs.obs_properties_add_int(props, "osc-port",  "OSC Port", 1001, 99999, 1)
    obs.obs_property_set_modified_callback(port_field, port_field_changed)
    
    return props