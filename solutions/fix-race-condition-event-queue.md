# Fix: Race Condition in Distributed Async Event Queue during High Concurrency

## Problem
Under high concurrency, multiple workers can claim the **same** event from the
queue simultaneously. The classic failure mode is a read-then-write claim:

```sql
SELECT * FROM events WHERE status = 'pending' LIMIT 1;   -- two workers read same row
UPDATE events SET status = 'processing' WHERE id = $1;   -- both claim it
```

Both workers process the same event -> duplicate side effects, double-charging,
and lost retry accounting. Additionally, a worker that crashes mid-processing
leaves the event stuck in `processing` forever (no reaper).

## Fix - four defensive changes

### 1. Atomic claim via `FOR UPDATE SKIP LOCKED` (Postgres)
Replace read-then-write with a **single atomic statement** so the DB, not the
application, arbitrates ownership:

```sql
UPDATE events
SET    status      = 'processing',
       claimed_by  = $1,
       claimed_at  = now(),
       attempts    = attempts + 1
WHERE  id = (
    SELECT id FROM events
    WHERE  status = 'pending'
       OR (status = 'processing' AND claimed_at < now() - interval '5 minutes')
    ORDER BY created_at
    FOR UPDATE SKIP LOCKED
    LIMIT 1
)
RETURNING id, payload, attempts;
```

`FOR UPDATE SKIP LOCKED` guarantees two concurrent workers can never select the
same row - the second skips it and takes the next. The `UPDATE ... RETURNING`
makes claim + state transition one atomic unit.

### 2. Idempotency guard on processing
Every event carries a stable `event_id`. Consumers must be idempotent:

```python
if not seen_recently(event_id):   # Redis SETNX with TTL, or a unique index
    process(event)
    mark_done(event_id)
```

Belt-and-suspenders: even if a duplicate is delivered, the side effect runs once.

### 3. Visibility-timeout reaper
A background job returns orphaned events to `pending` so a crashed worker does
not strand work:

```sql
UPDATE events
SET    status = 'pending', claimed_by = NULL
WHERE  status = 'processing'
  AND  claimed_at < now() - interval '5 minutes'
  AND  attempts < max_attempts;
```

Events exceeding `max_attempts` move to `dead_letter` for inspection.

### 4. Bounded retry with exponential backoff
On failure, requeue with backoff instead of immediate retry (prevents a poison
message from hot-looping all workers):

```python
delay = min(BASE * (2 ** attempts), MAX_BACKOFF)
schedule_retry(event_id, delay)
```

## Why this is correct
- **Atomicity**: claim is a single SQL statement; the row lock is held for the
  duration of the transaction, not the duration of processing.
- **No duplicate claims**: `SKIP LOCKED` is the canonical Postgres primitive for
  exactly this problem.
- **No stranded work**: the reaper bounds the worst case to one visibility window.
- **No poison loops**: backoff + dead-letter caps total damage.

## Test plan
1. Spawn N=50 concurrent workers against a queue seeded with 1,000 events.
2. Assert `SUM(claims) == 1000` and **no event claimed twice** (unique constraint
   on `(id, claimed_by)` during the test window).
3. Kill a worker mid-processing; assert the reaper requeues within 5 min.
4. Inject a permanently-failing event; assert it lands in `dead_letter` after
   `max_attempts` and does not block the queue.

## Files touched
- `queue/claim.sql` - atomic claim statement
- `queue/reaper.py` - visibility-timeout reaper + dead-letter
- `queue/consumer.py` - idempotency guard + backoff retry
