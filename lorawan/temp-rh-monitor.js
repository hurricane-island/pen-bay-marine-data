/**
 * Qingping Temperature and Relative Humidity sesnor
 */
function Decoder(bytes, port) {

  var i = 0;
  var output = {};
  var device_address = bytes[0];
  var function_code = bytes[1];
  var data_length = bytes[2];
  var data_type = bytes[3];

  if (device_address == 0x01 && function_code == 0x41 && data_length == 0x10 && data_type == 0x01) {
    output.temperature = ((bytes[8] * 16) + (bytes[9] >> 4) - 500) / 10.0;
    output.humidity = (256 * (bytes[9] & 0x0F) + bytes[10]) / 10.0;
    output.battery = bytes[13];
    output.device = device_address;
    output.timestamp = (bytes[4] << 24) + (bytes[5] << 16) + (bytes[6] << 8) + bytes[7];
  }
  return output;
}
