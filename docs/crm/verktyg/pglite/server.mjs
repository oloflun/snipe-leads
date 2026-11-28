// Lokal Postgres utan Docker: PGlite (Postgres 17 som WebAssembly) bakom en
// vanlig TCP-port, för att prova migrationen och CRM-lagrets SQL. Bara i minnet.
import { PGlite } from '@electric-sql/pglite'
import { PGLiteSocketServer } from '@electric-sql/pglite-socket'

const port = Number(process.argv[2] || 54329)
const db = await PGlite.create()
const server = new PGLiteSocketServer({ db, port, host: '127.0.0.1', maxConnections: 1 })
await server.start()
console.log('READY ' + port)
process.on('SIGTERM', async () => { await server.stop(); process.exit(0) })
