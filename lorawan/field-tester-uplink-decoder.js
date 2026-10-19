/**
 * Rak Field Tester decoder, using the old style, which seems to work
 * more reliably. Must be in ECMAScript 5.1; not use `let` or `const`.
 * 
 * TTN web interface expects 2 spaces per indent when formatting the web
 * editor.
 */
function Decoder(bytes, port) {
  if (port !== 1) {
    return null
  }
  var lonSign = (bytes[0] >> 7) & 0x01 ? -1 : 1;
  var latSign = (bytes[0] >> 6) & 0x01 ? -1 : 1;
  var encLat = ((bytes[0] & 0x3f) << 17) +
    (bytes[1] << 9) +
    (bytes[2] << 1) +
    (bytes[3] >> 7);
  var encLon = ((bytes[3] & 0x7f) << 16) +
    (bytes[4] << 8) +
    bytes[5];
  var alt = (bytes[6] << 8) + bytes[7];
  var hdop = bytes[8] / 10;
  var sats = bytes[9];
  return {
    latitude: latSign * (encLat * 108 + 53) / 10000000,
    longitude: lonSign * (encLon * 215 + 107) / 10000000,
    altitude: alt - 1000,
    accuracy: (hdop * 5 + 5) / 10,
    hdop,
    sats
  };
}
