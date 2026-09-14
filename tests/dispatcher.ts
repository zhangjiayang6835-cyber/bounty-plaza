import * as anchor from "@coral-xyz/anchor";
import { Program } from "@coral-xyz/anchor";
import { Keypair, SystemProgram, PublicKey } from "@solana/web3.js";
import { expect } from "chai";

describe("dispatcher", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Core;

  const [vaultAuthorityPda] = PublicKey.findProgramAddressSync(
    [Buffer.from("vault_authority")],
    program.programId
  );

  let targetVault: Keypair;
  const initialLiquidity = new anchor.BN(5000);

  beforeEach(async () => {
    targetVault = Keypair.generate();
    await program.methods
      .initializeVault(initialLiquidity)
      .accounts({
        targetAccount: targetVault.publicKey,
        vaultAuthority: vaultAuthorityPda,
        payer: provider.wallet.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .signers([targetVault])
      .rpc();
  });

  it("successfully dispatches CPI when account ownership and has_one constraints match", async () => {
    const dispatchAmount = new anchor.BN(1000);

    await program.methods
      .cpiDispatch(dispatchAmount)
      .accounts({
        vaultAuthority: vaultAuthorityPda,
        targetAccount: targetVault.publicKey,
        systemProgram: SystemProgram.programId,
      })
      .rpc();

    const vaultAccount = await program.account.vaultState.fetch(targetVault.publicKey);
    expect(vaultAccount.totalLiquidity.toNumber()).to.equal(4000);
    expect(vaultAccount.vaultAuthority.toBase58()).to.equal(vaultAuthorityPda.toBase58());
  });

  it("rejects invalid account ownership when counterfeit unowned account is supplied", async () => {
    const counterfeitAccount = Keypair.generate();

    try {
      await program.methods
        .cpiDispatch(new anchor.BN(500))
        .accounts({
          vaultAuthority: vaultAuthorityPda,
          targetAccount: counterfeitAccount.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();
      expect.fail("Expected transaction to fail due to invalid account owner");
    } catch (err: any) {
      expect(err).to.exist;
      const errMsg = err.toString();
      const isOwnerOrDiscriminatorError =
        errMsg.includes("AccountOwnedByWrongProgram") ||
        errMsg.includes("AccountNotInitialized") ||
        errMsg.includes("AccountDiscriminatorMismatch") ||
        err.name === "AnchorError";
      expect(isOwnerOrDiscriminatorError).to.be.true;
    }
  });

  it("rejects dispatch when vault authority violates has_one constraint", async () => {
    const unauthorizedAuthority = Keypair.generate().publicKey;

    try {
      await program.methods
        .cpiDispatch(new anchor.BN(500))
        .accounts({
          vaultAuthority: unauthorizedAuthority,
          targetAccount: targetVault.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();
      expect.fail("Expected transaction to fail due to has_one authority mismatch");
    } catch (err: any) {
      expect(err).to.exist;
      const errMsg = err.toString();
      const isConstraintError =
        errMsg.includes("InvalidAuthority") ||
        errMsg.includes("ConstraintHasOne") ||
        errMsg.includes("ConstraintSeeds") ||
        err.name === "AnchorError";
      expect(isConstraintError).to.be.true;
    }
  });

  it("rejects dispatch when requested amount exceeds available liquidity", async () => {
    const excessiveAmount = new anchor.BN(10000);

    try {
      await program.methods
        .cpiDispatch(excessiveAmount)
        .accounts({
          vaultAuthority: vaultAuthorityPda,
          targetAccount: targetVault.publicKey,
          systemProgram: SystemProgram.programId,
        })
        .rpc();
      expect.fail("Expected transaction to fail due to insufficient liquidity");
    } catch (err: any) {
      expect(err).to.exist;
      const errMsg = err.toString();
      const isInsufficientLiquidity =
        errMsg.includes("InsufficientLiquidity") ||
        err.name === "AnchorError";
      expect(isInsufficientLiquidity).to.be.true;
    }
  });
});
