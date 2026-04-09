'use strict';

const net = require('net');

const host = process.env.WAIT_MYSQL_HOST || 'mysql';
const port = Number(process.env.WAIT_MYSQL_PORT || 3306);
const maxAttempts = Number(process.env.WAIT_MYSQL_ATTEMPTS || 90);
const delayMs = Number(process.env.WAIT_MYSQL_DELAY_MS || 1000);

function tryConnect() {
  return new Promise((resolve, reject) => {
    const socket = net.createConnection(
      { host, port, timeout: 5000 },
      () => {
        socket.end();
        resolve();
      },
    );
    socket.on('error', (err) => {
      socket.destroy();
      reject(err);
    });
    socket.on('timeout', () => {
      socket.destroy();
      reject(new Error('connect timeout'));
    });
  });
}

async function main() {
  for (let i = 1; i <= maxAttempts; i++) {
    try {
      await tryConnect();
      console.log(`wait-for-mysql-tcp: ${host}:${port} OK (attempt ${i})`);
      process.exit(0);
    } catch (err) {
      const msg = err instanceof Error ? err.message : String(err);
      console.log(`wait-for-mysql-tcp: attempt ${i}/${maxAttempts} — ${msg}`);
      if (i === maxAttempts) {
        console.error(`wait-for-mysql-tcp: giving up on ${host}:${port}`);
        process.exit(1);
      }
      await new Promise((r) => setTimeout(r, delayMs));
    }
  }
}

main();
