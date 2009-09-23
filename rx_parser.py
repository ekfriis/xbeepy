'''
        xbee.py

        Copyright 2009 Evan Friis (ekfriis@gmail.com)

        An XBee inbound data stream parser (escaped API mode)

        Based on code from:
          http://eli.thegreenplace.net/2009/08/20/frames-and-protocols-for-the-serial-port-in-python/
          http://www.dabeaz.com/coroutines/index.html
'''

import struct
from coroutine import coroutine

@coroutine 
def XBeeApiFrameCatcher(start_frame = '\x7e', target = None):
   ''' Waits until the start of an XBee frame, and then passes data to the target '''
   while True:                  # wait until we catch the start frame flag
      byte = (yield)
      if byte == start_frame:
         while True:
            # we've caught the frame, now send it to the escaper
            target.send( (yield) )

@coroutine 
def XBeeApiEscaper(escape_char = '\x7d', escape_func = lambda x : chr(ord(x) ^ 0x20), target = None):
   ''' Escapes data in XBee serial stream.  Any data after this coroutine can be directly interpreted '''
   while True:
      byte = (yield)
      if byte == escape_char:
         byte = escape_func( (yield) )
      target.send(byte)

@coroutine 
def XBeeApiParser(target = None):
   while True:
      uint16_t = struct.Struct('>H') # To unpack the length
      length = ''
      # get the length
      length += ( yield ) # msb
      length += ( yield ) # lsb
      length = uint16_t.unpack(length)[0]

      frame    = ''
      checksum = 0

      while len(frame) < length:
         # add bytes to the frame
         byte      = ( yield )
         frame    += byte
         checksum += ord(byte)

      # Add the checksum from the data, if correct, will equal 0xFF.
      checksum += ord( (yield) )
      checksum &= 0xFF

      if checksum == 0xFF:
         target.send(frame)

@coroutine
def XBeeApiIdParser(frameSwitcher = None):
   while True:
      frame = (yield)
      # pull the apiID off the frame
      apiID = ord(frame[0])
      # get the correct target for this apiID
      frameSwitcher(apiID).send(frame)

@coroutine 
def GenericCmdDataSink(name):
   while True:
      frame = (yield)
      print "Got frame: %s with data: %s" % (name, frame)

def GenericFrameSwitcher(apiID):
   return GenericCmdDataSink("%s" % apiID)

@coroutine
def GenericFrame():
   return XBeeApiFrameCatcher(target = 
         XBeeApiEscaper(target =
            XBeeApiParser(target =
               XBeeApiIdParser(frameSwitcher = 
                  GenericFrameSwitcher
                  )
               )
            )
         )

if __name__ == "__main__":
   myHandler = GenericFrame()

   example = [0x7E,0x00,0x16,0x10,0x01,0x00,0x7D,0x33,0xA2,0x00,0x40,0x0A,0x01,0x27,
              0xFF,0xFE,0x00,0x00,0x54,0x78,0x44,0x61,0x74,0x61,0x30,0x41,0x7D,0x33]

   test = ''.join([ chr(b) for b in example ])
   print test

   for char in test:
      myHandler.send(char)
