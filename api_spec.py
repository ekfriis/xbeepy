from construct import *

# XBee 2.5 API frames
xbee_api_frames = {
   "ModemStatus"                   : 0x8A,
   "ATCommand"                     : 0x08,
   "ATCommandQueueParameterValue"  : 0x09,
   "ATCommandResponse"             : 0x88,
   "RemoteATCommandRequest"        : 0x17,
   "RemoteCommandResponse"         : 0x97,
   "ZigBeeTransmitRequest"         : 0x10,
   "ExplAddrZigBeeCmdFrame"        : 0x11,
   "ZigBeeTransmitStatus"          : 0x8B,
   "ZigBeeReceivePacket"           : 0x90,
   "ZigBeeExplRXIndicator"         : 0x91,
   "ZigBeeIODataSampleRXIndicator" : 0x92,
   "XBeeSensorReadIndicator"       : 0x94,
   "NodeIdentificationIndicator"   : 0x95,
   "_default_"                     : "unknown_api_id"
}

# Standard XBee frame header - 2 bytes [MSB LSB] of the length of the entire frame
#  and a byte indicating the frame type
StandardPrelude = Struct("Prelude",
   UBInt16("length"),
   Union("api_id",
      Enum(Byte("name"), **xbee_api_frames),
      Byte("value")
   )
)

def DataUntilEndOfFrame(name):
   ''' macro to contstruct a field to collect data until the end of the 
   frame, as defined by the current position and the length field'''
   anchor_name = "%s_start_pos" % name
   output = Embed("%s_data",
      Anchor(anchor_name),
      MetaField(name, lambda ctx : ctx["length"] - 2 - ctx[anchor_name])
   )
   return output
)

# Common addressing for outbound XBee frames
TXAddressing = Struct("TXAddressing",
   UBInt64("destination_address"),
   UBInt16("destination_network_address"),
)

# Common addressing for inbound XBee frames
RXAddressing = Struct("RXAddressing",
   UBInt64("source_address"),
   UBInt16("source_network_addresss"),
)

# 
ModemStatusData = Struct("ModemStatus",
   Embed(StandardPrelude),
   Enum(Byte("status"),
      hardware_reset = 0,
      watchdog_reset = 1,
   )
)

ATCommandData = Struct("ATCommand",
   Embed(StandardPrelude),
   String("at_command", 2),
   OptionalGreedyRepeater(UBInt8("value"))
)

ATCommandResponseData = Struct("ATCommandResponse",
   Embed(StandardPrelude),
   String("at_command", 2),
   UBInt8("status"),
   OptionalGreedyRepeater(UBInt8("value"))
)

RemoteATCommandRequestData = Struct("RemoteATCommandRequest",
   Embed(StandardPrelude),
   Embed(TXAddressing),
   UBInt8("command_options"),
   String("command_name", 2),
   OptionalGreedyRepeater(UBInt8("command_data"))
)

RemoteCommandResponseData = Struct("RemoteCommandResponse",
   Embed(StandardPrelude),
   Embed(RXAddressing),
   String("command_name", 2),
   UBInt8("status"),
   OptionalGreedyRepeater(UBInt8("command_data"))
)

ZigBeeTransmitRequestData = Struct("ZigBeeTransmitRequest",
   Embed(StandardPrelude),
   Embed(TXAdressing),
   UBInt8("BroadcastRadius"),
   UBInt8("Options"),
   OptionalGreedyRepeater(UBInt8("RFData")),
)

ExplAddrZigBeeCmdFrameData = Struct("ExplAddrZigBeeCmdFrame",
   Embed(StandardPrelude),
   Embed(TXAddressing),
   UBInt8("SourceEndpoint"),
   UBInt8("DestinationEndpoint"),
   Const(UBInt8("Reserved"), 0),
   UBInt8("ClusterID"),
   Const(UBInt16("ProfileID"), 0xC105), # multiple profile IDs not supported
   UBInt8("BroadcastRadius"),
   OneOf(UBInt8("Options"), [0x00, 0x08]),
   OptionalGreedyRepeater(UBInt8("RFData"))
)

ZigBeeTransmitStatusData = Struct("ZigBeeTransmitStatusData",
   Embed(StandardPrelude),
   UBInt16("SourceNetworkAddress"),
   UBInt8("TransmitRetryCount"),
   UBInt8("DeliveryStatus"),
   UBInt8("DiscoveryStatus"),
)

ZigBeeReceivePacketData = Struct("ZigBeeReceivePacket",
   Embed(StandardPrelude),
   Embed(RXAddressing)
   OneOf(UBInt8("Options"), [0x01, 0x02]),
   OptionalGreedyRepeater(UBInt8("RFData"))
)

ZigBeeExplRXIndicatorData = Struct("ZigBeeExplRXIndicator",
   Embed(StandardPrelude),
   Embed(RXAddressing),
   UBInt8("SourceEndpoint"),
   UBInt8("DestinationEndpoint"),
   UBInt16("ClusterID"),
   UBInt16("ProfileID"),
   UBInt8("Options"),
   OptionalGreedyRepeater(UBInt8("RFData"))
)

def UBInt16IfFlagIsSet( ctxGetter, flagName):
   ''' Return an if statement to add at UBInt16 with name "flagName" if 
       a corresponding Flag("flagName") is set.  The ctx getter should be a lambda
       that translates the destination context to the context of the BitSetFlag '''
   getter = If( lambda ctx : ctxGetter(ctx)[flagName], UBInt16(flagName) )
   return getter

ZigBeeIODataSampleRXIndicatorData = Struct("ZigBeeIODataSampleRXIndicator",
   Embed(StandardPrelude),
   Embed(RXAddressing),
   UBInt8("RecieveOptions"),
   UBInt8("NumSamples"),
   Union("DigitalChannelMask",
      BitStruct("Pins",
         Padding(3),
         Flag("DIO12"),
         Flag("DI011"),
         Flag("DIO10"),
         Padding(2),
         Flag("DIO7"),
         Flag("DIO6"),
         Flag("DIO5"),
         Flag("DIO4"),
         Flag("DIO3"),
         Flag("DIO2"),
         Flag("DIO1"),
         Flag("DIO0")
      ),
      UBInt16("Raw")
   ),
   BitStruct("AnalogChannelMask",
      Flag("SupplyVoltage"),
      Padding(3),
      Flag("AD3"),
      Flag("AD2"),
      Flag("AD1"),
      Flag("AD0"),
   ),
      # Get digital samples if they exist
   If( lambda ctx : ctx.DigitalChannelMask.Raw > 0,
      BitStruct("DigitalSamples",
         Padding(3),
         Flag("DIO12"),
         Flag("DI011"),
         Flag("DIO10"),
         Padding(2),
         Flag("DIO7"),
         Flag("DIO6"),
         Flag("DIO5"),
         Flag("DIO4"),
         Flag("DIO3"),
         Flag("DIO2"),
         Flag("DIO1"),
         Flag("DIO0")
      )
   ),
   # Read two bytes for each existing analog sample
   Struct("AnalogSamples",
      UBInt16IfFlagIsSet(lambda ctx : ctx._.AnalogChannelMask, "SupplyVoltage"),
      UBInt16IfFlagIsSet(lambda ctx : ctx._.AnalogChannelMask, "AD3"),
      UBInt16IfFlagIsSet(lambda ctx : ctx._.AnalogChannelMask, "AD2"),
      UBInt16IfFlagIsSet(lambda ctx : ctx._.AnalogChannelMask, "AD1"),
      UBInt16IfFlagIsSet(lambda ctx : ctx._.AnalogChannelMask, "AD0")
   )
)


if __name__ == "__main__":
   doot = ZigBeeIODataSampleRXIndicatorData
   c = doot.parse('\x00\x00\x00\x00\x00\x00\x00\x00\x69\x69\x00\x01\xff\xff\x01\xff\xff\x00\xff')
   print c

   c = StandardPrelude.parse('\x00\x00\x11')
   print c
   
             




