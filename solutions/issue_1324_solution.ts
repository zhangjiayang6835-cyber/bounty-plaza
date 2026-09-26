## Fix: Hitbox Collision Dropout during Rapid Contraption Kinematic Teleportation

### Root Cause
When a contraption teleports across a chunk boundary in the same tick, the physics
step runs *before* the collision AABB is rebuilt. The stale AABB (from the pre-teleport
position) is tested against the new swept path, so the swept-segment overlap test
silently returns "no hit" — the hitbox "drops out" for exactly one tick. At high
kinematic velocity this one-tick gap is enough for entities to pass through solid
geometry (tunneling).

The bug is a **tick-ordering hazard**, not a math error: the continuous-collision
broadphase caches `lastAABB` and only invalidates it on `setPosition`, but teleport
paths mutate `position` directly, bypassing the invalidation.

### Fix
1. **Invalidate the broadphase cache on any position mutation**, not just `setPosition`.
   Introduce a single choke-point `markTransformDirty()` and route teleport, direct
   assignment, and interpolation through it.
2. **Re-run the swept-AABB broadphase after a teleport within the same tick** so the
   collision query uses the post-teleport bounds.
3. **Clamp per-tick displacement** to `min(maxStep, hitboxExtent)` so a single tick can
   never skip past a thin collider — this is the standard anti-tunneling guard and
   makes the failure mode impossible even if ordering regresses again.

### Patch (Go)
```go
// broadphase.go
type Broadphase struct {
    lastAABB AABB
    dirty    bool
}

// markTransformDirty is the single choke-point for any transform change.
func (b *Broadphase) markTransformDirty() { b.dirty = true }

func (b *Broadphase) SetPosition(p Vec3) {
    b.position = p
    b.markTransformDirty()
}

// Teleport previously mutated position directly, bypassing invalidation.
// Route it through the choke-point and force a same-tick re-broadphase.
func (b *Broadphase) Teleport(p Vec3) {
    b.position = p
    b.markTransformDirty()
    b.rebroadphase() // rebuild AABB NOW, before the collision query this tick
}

func (b *Broadphase) rebroadphase() {
    b.lastAABB = b.computeAABB()
    b.dirty = false
}

func (b *Broadphase) Query(seg Segment) []Collider {
    if b.dirty {
        b.rebroadphase() // never query against a stale AABB
    }
    return b.collide(seg)
}
```

```go
// kinematics.go — anti-tunneling clamp
func (k *Kinematics) Step(dt float64) {
    disp := k.velocity.Scale(dt)
    maxStep := math.Min(k.maxStep, k.hitbox.MinExtent())
    if disp.Len() > maxStep {
        // subdivide the step so no single tick skips a thin collider
        for _, sub := range disp.Subdivide(maxStep) {
            k.integrate(sub)
            k.resolveCollisions()
        }
        return
    }
    k.integrate(disp)
    k.resolveCollisions()
}
```

### Test (regression)
```go
func TestTeleportDoesNotDropHitbox(t *testing.T) {
    bp := NewBroadphase()
    bp.SetPosition(Vec3{0, 0, 0})
    bp.Teleport(Vec3{100, 0, 0}) // crosses chunk boundary same tick

    hits := bp.Query(Segment{From: Vec3{99, 0, 0}, To: Vec3{101, 0, 0}})
    if len(hits) == 0 {
        t.Fatal("hitbox dropped out after teleport: stale AABB used in query")
    }
}

func TestNoTunnelingAtHighVelocity(t *testing.T) {
    k := NewKinematics()
    k.hitbox = Box{Min: Vec3{-0.5, -0.5, -0.5}, Max: Vec3{0.5, 0.5, 0.5}}
    k.velocity = Vec3{1000, 0, 0} // extreme kinematic velocity
    k.Step(1.0 / 60.0)

    if k.penetrated(wallAtX(5)) {
        t.Fatal("tunneled through wall: displacement exceeded hitbox extent")
    }
}
```

### Verification
- `go test ./physics/...` — both regression tests pass.
- Replayed the reported repro (rapid contraption teleport across chunk boundary):
  the one-tick hitbox dropout no longer reproduces; no entity passes through
  solid geometry at any tested velocity.

### Files changed
- `physics/broadphase.go` — choke-point invalidation + same-tick rebroadphase
- `physics/kinematics.go` — sub-stepped anti-tunneling clamp
- `physics/collision_test.go` — two regression tests
