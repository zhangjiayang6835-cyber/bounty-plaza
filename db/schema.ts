import { Kysely, SqliteDialect } from 'kysely'

interface InferenceCalls {
  // ... existing fields
  fee_micro: number
  fee_lamports: number | null  // New nullable field
}

export interface Database extends Kysely<{ sqlite: SqliteDialect }> {
  // ... existing tables
  inference_calls: InferenceCalls
}