import {readFileSync, writeFileSync, mkdirSync, existsSync,} from "fs";
import Crypto from "crypto-js";
import {create} from "tar";
const {MD5} = Crypto;

const template = "../logger-programs/template/default.dld";
const config = [
    ["Ai1_36594", 1065], 
    // ["Ai1_36593", 1064], 
    // ["Ai1_36592", 1062]
];
const text = readFileSync(template, "utf8");

function station(name, address) {
    const directory = `../logger-programs/${name}`;
    if (!existsSync(directory)) mkdirSync(directory)

    const content = text
        .replace("$TEMPLATE_STATION_NAME", name)
        .replace("$TEMPLATE_PAKBUS_ADDRESS", `${address}`);
    const checksum = MD5(content).toString();
    
    const program = `${directory}/default.${checksum}.dld`;
    writeFileSync(program, content, "utf8");
    return create({
        gzip: true,
        file: `../logger-programs/${name}.CPU.web.obj.tar.gz`
    }, [directory])
}

config.forEach(([name, address])=>{
    (async function () {
        await station(name, address)
    })()
})
