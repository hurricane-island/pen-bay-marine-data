function Decoder(bytes, port) {
  
	var i = 0;
  var output = {};
  var device_address = bytes[i++];
  var function_code = bytes[i++];
	var data_length = bytes[i++];
  var data_type = bytes[i++];
    
	// Parsing only real time data from sensor   
	if ((0x41 == function_code) && (0x01 == data_type)) {
      
  	// id
		output.device = device_address;

    // timestamp
    output.timestamp = (bytes[i] << 24) + (bytes[i+1] << 16) + (bytes[i+2] << 8) + bytes[i+3];
    i+=4;

    // temperature
    output.temperature = ((bytes[i] * 16) + (bytes[i+1] >> 4) - 500) / 10.0;
    output.humidity = (256 * (bytes[i+1] & 0x0F) + bytes[i+2]) / 10.0;
    i+=5;

    // battery
    output.battery = bytes[i];

	}

  return output;

}
