Here's the step-by-step solution:

1. Replace raw AccountInfo with Anchor Account wrapper.
2. Enforce has_one constraint for the PDA.

```rust
// Replace AccountInfo with Account wrapper
let account = Account::<'info, T>::new(&info);
account.validate();

// For PDA validation
has_one!(account, [b"vault", ...]);
```

```typescript
describe('test'), () => {
  it('should pass when the account is a PDA with correct seeds', async () => {
    const [programId] = [programIds()];
    const accounts = [new Account([1])];
    const instructions = [new MyCpiInstruction([1], [programId, ...])];
    const result = await program().run账单([programId], accounts, instructions);
    assert(result);
  });
});
```