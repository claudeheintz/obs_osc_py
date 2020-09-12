# obs_osc_py

OBS_OSC is a python script for OBS that allows it to be controlled by OSC.

OBS_OSC.py includes a bare-bones OSC class that implements enough OSC to extract the address patteren and float, int and string arguments from an OSC message received on a UDP port.

   OBS OSC Messages:

   `/obs/transition/start`
       triggers the current transition

   `/obs/transition/NN/select`
       selects transition number NN (1 based)<br/>
       `/obs/transition/1/select` chooses first transition (index 0 in obspython)

   `/obs/transition/NN/start`
       selects and executes transition number NN (1 based index)<br/>
       `/obs/transition/1/start` chooses first transition (index 0 in obspython)

   `/obs/scene/NN/preview`
       selects scene number NN  (1 based)<br/>
       '/obs/scene/1/preview' sets the preview to the first scene  (index 0 in obspython)

   `/obs/scene/NN/start`
       selects scene number NN  (1 based) and then transitions to that scene
       following the transition, the next scene is selected for preview

   `/obs/scene/NN/go`
       selects scene number NN  (1 based) and then transitions to that scene
       following the transition, the next scene is selected for preview<br/>
       `/obs/scene/1/go` sets the preview to the first scene  (index 0 in obspython)
       following the transition, the second scene is set to preview 

   `/obs/scene/NN/transition/MM/start`
       selects scene number NN  (1 based) and then transitions to that scene
       using transition number MM (1 based)

   `/obs/scene/NN/transition/MM/go`
       selects scene number NN  (1 based) and then transitions to that scene
       using transition number MM (1 based)
       following the transition, the next scene is selected for preview<br/>
       `/obs/scene/2/transition/2/go` sets the preview to the second scene in the list
           (index 1 in obspython) then transitions to that scene using the second transition
           (index 1 in obspython)
           following the transition, the third scene is set to preview 

   `/obs/go`
       transitions to the current previewed scene using the current transition
       following the transition, the scene following the former preview scene
       in the scene list is selected for preview

   `/obs/recording/start`
       starts recording

   `/obs/recording/stop`
       stops recording

   `/obs/streaming/start`
       starts streaming

   `/obs/streaming/stop`
       stops streaming
