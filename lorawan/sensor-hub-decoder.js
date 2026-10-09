function Decoder(bytes, port) {
  var decoded = {};
  var str = bin2HexStr(bytes);
  var i = 0;
  while (i < str.length) {
    var channelId = parseShort(str.slice(i, i + 4), 16);
    var value = parseShort(str.slice(i + 4, i + 8), 16);
    i += 8;
    switch (channelId) {
      case 0x01BE:
        decoded.wind_speed = value / 100;
        break;
      case 0x02BF:
        decoded.wind_direction = value;
        break;
      case 0x0367:
        decoded.temperature = value / 10.0;
        break;
      case 0x0470:
        decoded.humidity = value / 10.0;
        break;
      case 0x0573:
        decoded.pressure = value / 10.0;
        break;
      default:
        break;
    }
  }

  try {
    decoded.lorawan_rssi = (port && port.metadata && port.metadata.rssi) || 0;
    decoded.lorawan_snr = (port && port.metadata && port.metadata.snr) || 0;
    decoded.lorawan_datarate = (port && port.metadata && port.metadata.data_rate) || '';
  } catch (e) {
    console.log('Failed to read gateway metadata');
  }

  return decoded;
}

function bin2HexStr(bytesArr) {
  var str = '';
  for (var i = 0; i < bytesArr.length; i++) {
    var tmp = (bytesArr[i] & 0xff).toString(16);
    if (tmp.length == 1) {
      tmp = '0' + tmp;
    }
    str += tmp;
  }
  return str;
}

// convert string to short integer  
function parseShort(str, base) {
  var n = parseInt(str, base);
  return (n << 16) >> 16;
}

// convert string to triple bytes integer  
function parseTriple(str, base) {
  var n = parseInt(str, base);
  return (n << 8) >> 8;
}
