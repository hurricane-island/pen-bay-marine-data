import {readFileSync, writeFileSync, mkdirSync, existsSync,} from "fs";

function station(template, name, address, clientId) {
    const source = `../logger-programs/template/${template}.dld`;
    const text = readFileSync(source, "utf8");
    const directory = `../logger-programs/firmware/${name}`;
    if (!existsSync(directory)) mkdirSync(directory)
    const content = text
        .replace("$STATION_NAME", name)
        .replace("$PAKBUS_ADDRESS", `${address}`)
        .replace("$CLIENT_ID", `${clientId}`);
    const program = `${directory}/${name}.dld`;
    writeFileSync(program, content, "utf8");
}

function main() {
    const args = process.argv.slice(4);
    station(...args);
}

main();
