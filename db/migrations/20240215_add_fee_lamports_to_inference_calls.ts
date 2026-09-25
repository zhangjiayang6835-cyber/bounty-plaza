import { Kysely, SqliteDialect } from 'kysely'
import { Db } from '../db'

export async function up(db: Db): Promise<void> {
  await db.schema
    .alterTable('inference_calls')
    .addColumn('fee_lamports', 'integer', (col) => col.nullable())
    .execute()
}

export async function down(db: Db): Promise<void> {
  // Forward-only migration; no rollback
}