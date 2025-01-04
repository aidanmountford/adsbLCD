import time
from st7920 import ST7920
import RPi.GPIO as GPIO
import psutil
import time
import socket
import json
import sys
import signal
import inotify.adapters
import threading
import re



############################################################
# Some really basic setup 
# Set the GPIOs for the LEDs
LED = {	"red":5, "orange":22, "yellow":27, "green":17	}

# Our statistics
stats = {} 

# What is the name of the stats JSON file
STATS_DIRECTORY = "/var/run/readsb"
STATS_FILENAME = "stats.json"

# My Name
NAME = "adsbexchange"

# What is our LCD
LCD = ST7920()

# Filesystem events
FSWATCHER = inotify.adapters.Inotify()


#  Flash an LED
def flashLED(led, seconds):
  GPIO.output (LED[led], True)
  if seconds > 0:
    time.sleep (seconds)
    GPIO.output (LED[led], False)

#  Now flash it in background

def asyncFlashLED (led, seconds):
  ledThread = threading.Thread (target = flashLED, args=(led,seconds))
  ledThread.start()


def setup():
  # Setup the GPIOs. 
  GPIO.setmode (GPIO.BCM)
  GPIO.setup ( LED["red"], GPIO.OUT )     #  Error 
  GPIO.setup ( LED["orange"], GPIO.OUT )  # Once per message (100ms)
  GPIO.setup ( LED["yellow"], GPIO.OUT )  # Once per update (500ms)
  GPIO.setup ( LED["green"], GPIO.OUT )   # Heartbeat - Every Second

  ## Monitor for stats updates 
  signal.signal(signal.SIGUSR1, updateADSBStatsSignal)


  # Start the FS Monitor
  FSWATCHER.add_watch (STATS_DIRECTORY)  

  # Initialize the LCD
  LCD.clear()
  LCD.redraw

  # Draw the screen structure
  LCD.put_text("    ADSB Receiver", 0, 0)
  LCD.put_text('Aircraft',4,11)
  LCD.put_text(' ADSB:',1,22)
  LCD.put_text(' MLAT:',1,31)
  LCD.put_text(' TOTAL:',1,40)
  LCD.put_text('RF ',80,11)
  LCD.put_text(' S:',77,22)
  LCD.put_text(' N:',77,31)

  LCD.set_rotation(0)
  LCD.line(0,8,128,8)
  LCD.line(75,8,75,54)
  LCD.line(0,54,128,54)
  LCD.redraw()

def updateADSBStats():
  global stats
  print ("      Updating Stats!")
  # open the provided JSON file
  with  open(STATS_DIRECTORY + "/" + STATS_FILENAME, 'r') as inputFile:
    stats = json.load(inputFile)
    inputFile.close()


def updateADSBStatsSignal (sig, frame):
  print ("Got signal!")
  updateADSBStats ()



def checkStatsFileChange():
  print ("Starting Stats Update")
  for fsEvent in FSWATCHER.event_gen(yield_nones=True):
    if fsEvent is not None:
      (header, type_names, watch_path, filename) = fsEvent
      if filename == STATS_FILENAME and "IN_MOVED_TO" in type_names:
        print ("Statsfile Changed")
        updateADSBStats()
        updateLCD_stats()
    time.sleep(1)


def updateLCD_CPU():
  LCD.put_text('CPU: {cpu:.0%}    '.format(cpu = psutil.cpu_percent(4)/100), 0, 56)
  LCD.put_text('{}'.format(NAME.rjust(12)), 50, 56)
  LCD.redraw()

def updateLCD_stats():
  global stats
  asyncFlashLED ("yellow", 0.5)
  if stats.get("aircraft_with_pos") is not None:
    LCD.put_text( "{:4>}".format(stats["aircraft_with_pos"]-stats["aircraft_count_by_type"]["mlat"]), 48, 22)
    LCD.put_text( "{:4>}".format(stats["aircraft_count_by_type"]["mlat"]), 48, 31)
    LCD.put_text( "{:4>}".format(stats["aircraft_with_pos"]+stats["aircraft_without_pos"]), 48, 40)
    LCD.put_text( "{:5>}".format(stats["last1min"]["local"]["signal"]), 95, 22)
    LCD.put_text( "{:5>}".format(stats["last1min"]["local"]["noise"]), 95, 31)
    stats = {}
    LCD.redraw()


def updateLCD():
  print ("Starting LCD Update")
  while True:  
    print ("LCD Update")
    updateLCD_CPU()
    time.sleep (1)
    asyncFlashLED ("green",0.5)


def run():
  # Create tasks
  lcdThread = threading.Thread ( target=updateLCD )
  statsThread = threading.Thread ( target=checkStatsFileChange )

  lcdThread.start()
  statsThread.start()

  lcdThread.join()
  statsThread.join()


## Main Program
if __name__ =="__main__":
  setup()
  run()
