import {readFileSync, writeFileSync, mkdirSync} from "fs";
import Crypto from "crypto-js";
const {MD5} = Crypto;

const template = "../logger-programs/default.template.dld";
const station = "Ai1_36594";
const pakbus = 1065;
const directory = `../logger-programs/${station}`;

const text = readFileSync(template, "utf8")
    .replace("$TEMPLATE_STATION_NAME", station)
    .replace("$TEMPLATE_PAKBUS_ADDRESS", `${pakbus}`);
const checksum = MD5(text).toString();
console.log({checksum})
mkdirSync(directory)
const program = `${directory}/default.dld`;
writeFileSync(program, text, "utf8");
