import { createReadStream, existsSync, statSync } from "node:fs";
import { createServer } from "node:http";
import { extname, join, normalize, resolve } from "node:path";

const root = resolve(process.argv[2]);
const port = Number(process.argv[3]);
const types = { ".css": "text/css", ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".json": "application/json", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon" };

createServer((request, response) => {
  const url = new URL(request.url ?? "/", "http://localhost");
  let pathname = decodeURIComponent(url.pathname);
  if (pathname.startsWith("/r/")) pathname = "/r/__token/index.html";
  else if (pathname.startsWith("/i/")) pathname = "/i/__token/index.html";
  else if (pathname.endsWith("/")) pathname += "index.html";
  else if (!extname(pathname)) pathname += "/index.html";
  const file = normalize(join(root, pathname));
  if (!file.startsWith(root) || !existsSync(file) || !statSync(file).isFile()) {
    response.writeHead(404).end("Not found");
    return;
  }
  response.setHeader("content-type", types[extname(file)] ?? "application/octet-stream");
  createReadStream(file).pipe(response);
}).listen(port, "127.0.0.1");
