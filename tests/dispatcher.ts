import * as anchor from "@project-serum/anchor";
import { Program, BN } from "@project-serum/anchor";
import { assert, expect } from "chai";

describe("dispatcher", () => {
  const provider = anchor.AnchorProvider.env();
  anchor.setProvider(provider);

  const program = anchor.workspace.Core as Program;

  const authority = anchor.web3.Keypair.generate();

  async function createVault(bump: number): Promise<anchor.web3.PublicKey> {
    return program.methods
      .initializeVault(bump)
      .accounts({
        vaultAuthority: authority.publicKey,
        authority: provider.wallet.publicKey,
      })
      .signers([authority])
      .rpc()
      .then(() => {
        const [vault] = anchor.web3.PublicKey.findProgramAddressSync(
          [Buffer.from("vault"), authority.publicKey.toBuffer()],
          program.programId
        );
        return vault;
      });
  }

  it("mints when the vault is owned by the program and has_one passes", async () => {
    const vault = await createVault(255);

    await program.methods
      .mint(new BN(1_000_000))
      .accounts({
        vault,
        vaultAuthority: authority.publicKey,
        authority: provider.wallet.publicKey,
      })
      .signers([authority])
      .rpc();

    const state = await program.account.vault.fetch(vault);
    assert.equal(state.minted.toNumber(), 1_000_000);
  });

  it("rejects a counterfeit vault not owned by the program", async () => {
    const counterfeit = anchor.web3.Keypair.generate();
    const vault = counterfeit.publicKey;

    await expect(
      program.methods
        .mint(new BN(1_000_000))
        .accounts({
          vault,
          vaultAuthority: authority.publicKey,
          authority: provider.wallet.publicKey,
        })
        .signers([authority])
        .rpc()
    ).to.be.rejectedWith("AccountOwnedByWrongProgram");
  });

  it("enforces the has_one constraint on the vault authority PDA", async () => {
    const vault = await createVault(255);
    const attacker = anchor.web3.Keypair.generate();

    await expect(
      program.methods
        .mint(new BN(1_000_000))
        .accounts({
          vault,
          vaultAuthority: attacker.publicKey,
          authority: provider.wallet.publicKey,
        })
        .signers([attacker])
        .rpc()
    ).to.be.rejectedWith("ConstraintHasOne");
  });
});