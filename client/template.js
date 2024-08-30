import {readFileSync, writeFileSync, mkdirSync, existsSync} from "fs";
import Crypto from "crypto-js";
const {MD5} = Crypto;

const template = "../logger-programs/test.template.dld";
const config = [["Ai1_36594", 1065], ["Ai1_36593", 1064], ["Ai1_36592", 1062]];
const text = readFileSync(template, "utf8");

function station(name, address) {
    const directory = `../logger-programs/${name}`;
    const content = text
        .replace("$TEMPLATE_STATION_NAME", name)
        .replace("$TEMPLATE_PAKBUS_ADDRESS", `${address}`);
    const checksum = MD5(content).toString();
    if (!existsSync(directory)) mkdirSync(directory)
    const program = `${directory}/test.${checksum}.dld`;
    writeFileSync(program, content, "utf8");
}

config.forEach(([name, address])=>{
    station(name, address)
})
