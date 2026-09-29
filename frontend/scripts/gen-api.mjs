// Refreshes the API types from the backend contract before type checking.
// The Docker image is built from frontend/ alone: there it keeps the committed file.
import { execFileSync } from 'node:child_process'
import { existsSync } from 'node:fs'

const contract = '../backend/openapi.json'

if (existsSync(contract)) {
  // The package exports no path to its CLI, so run the file the `bin` entry points at.
  const cli = 'node_modules/openapi-typescript/bin/cli.js'
  execFileSync(process.execPath, [cli, contract, '-o', 'src/shared/api/schema.d.ts'], {
    stdio: 'inherit',
  })
} else {
  console.log(`${contract} not found: using the committed API types`)
}
