```typescript
// db/migrations/20240101-add-fee-lamports.ts
import { Drizzle} from 'drizzle-orm';

export default async function (schema: typeof Drizzle) {
  return schema('inference_calls', (table) => {
    table.uuid('id');
    table.text('result');
    table.string('fee_currency', 255);
    table.integer('fee_amount');
    table.integer('fee_micro');
    table.string('status');
    table.timestamp('created_at');
    table.timestamp('updated_at');
  });
}
```