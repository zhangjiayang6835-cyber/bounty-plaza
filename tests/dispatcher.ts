import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { PublicKey, Keypair, SystemProgram } from "@solana/web3.js";
import { TOKEN_PROGRAM_ID, createMint, createAccount, mintTo } from "@solana/spl-token";
import { expect } from "chai";

describe("dispatcher security integration tests", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.AnchorDispatcher as Program<any>;

  it("Blocks counterfeit state account not owned by program", async () => {
    const fakeStateKeypair = Keypair.generate();
    // Simulate passing an external account as state_account
    try {
      await program.methods
        .dispatchLiquidity(new anchor.BN(100_000))
        .accounts({
          stateAccount: fakeStateKeypair.publicKey,
        })
        .rpc();
      expect.fail("Expected transaction to fail with AccountOwnedByWrongProgram");
    } catch (err: any) {
      expect(err.toString()).to.include("AccountOwnedByWrongProgram");
    }
  });

  it("Blocks unauthorized authority with has_one check", async () => {
    const unauthorizedSigner = Keypair.generate();
    try {
      await program.methods
        .dispatchLiquidity(new anchor.BN(100_000))
        .accounts({
          authority: unauthorizedSigner.publicKey,
        })
        .signers([unauthorizedSigner])
        .rpc();
      expect.fail("Expected has_one constraint violation");
    } catch (err: any) {
      expect(err.toString()).to.include("UnauthorizedAuthority");
    }
  });
});
