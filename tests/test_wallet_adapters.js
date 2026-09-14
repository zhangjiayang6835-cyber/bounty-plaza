import test from "node:test";
import assert from "node:assert/strict";
import {
  SorobanClient,
  FreighterAdapter,
  StellarKitAdapter,
  WalletNotInstalledError,
  WalletConnectionError,
  WalletSigningError,
} from "../src/index.ts";

test("FreighterAdapter: throws WalletNotInstalledError when API is missing", async () => {
  const adapter = new FreighterAdapter();
  assert.equal(adapter.name, "Freighter");
  assert.equal(adapter.isAvailable(), false);

  await assert.rejects(
    async () => {
      await adapter.connect();
    },
    {
      name: "WalletNotInstalledError",
      message: /Freighter wallet extension is not installed/,
    }
  );

  await assert.rejects(
    async () => {
      await adapter.signTransaction("AAAAXDR==");
    },
    {
      name: "WalletNotInstalledError",
      message: /Freighter wallet extension is not installed/,
    }
  );
});

test("FreighterAdapter: connects and signs successfully with mock API", async () => {
  const mockApi = {
    isConnected: async () => true,
    getPublicKey: async () => "GBZXN7PIRZGNMHGA728RGRFZ46NUQWHK263RJB5R7PNQ22UHMAAXUSW7",
    signTransaction: async (xdr, opts) => `SIGNED_${xdr}_FOR_${opts?.networkPassphrase}`,
  };

  const adapter = new FreighterAdapter(mockApi);
  assert.equal(adapter.isAvailable(), true);

  const pubKey = await adapter.connect();
  assert.equal(pubKey, "GBZXN7PIRZGNMHGA728RGRFZ46NUQWHK263RJB5R7PNQ22UHMAAXUSW7");

  const signed = await adapter.signTransaction("TX_TEST_XDR", {
    networkPassphrase: "Public Global Stellar Network ; September 2015",
  });
  assert.equal(signed, "SIGNED_TX_TEST_XDR_FOR_Public Global Stellar Network ; September 2015");
});

test("FreighterAdapter: handles connection rejection gracefully", async () => {
  const mockApi = {
    isConnected: async () => false,
    getPublicKey: async () => "",
    signTransaction: async () => "",
  };

  const adapter = new FreighterAdapter(mockApi);
  await assert.rejects(
    async () => {
      await adapter.connect();
    },
    {
      name: "WalletNotInstalledError",
    }
  );
});

test("StellarKitAdapter: throws WalletNotInstalledError when kit is missing", async () => {
  const adapter = new StellarKitAdapter();
  assert.equal(adapter.name, "StellarWalletsKit");
  assert.equal(adapter.isAvailable(), false);

  await assert.rejects(
    async () => {
      await adapter.connect();
    },
    {
      name: "WalletNotInstalledError",
      message: /StellarWalletsKit wallet extension is not installed/,
    }
  );
});

test("StellarKitAdapter: connects and signs successfully with mock kit instance", async () => {
  let modalOpened = false;
  const mockKit = {
    openModal: async () => {
      modalOpened = true;
    },
    getPublicKey: async () => "GCEZWKCA5VLDANIKSI2AWMT4Q4IG47L5G3D3J22J7K3QGQXH2XW7Y2Z7",
    signTransaction: async (xdr, opts) => ({
      signedXDR: `KIT_SIGNED_${xdr}_PASS_${opts?.networkPassphrase}`,
    }),
  };

  const adapter = new StellarKitAdapter(mockKit);
  assert.equal(adapter.isAvailable(), true);

  const pubKey = await adapter.connect();
  assert.equal(modalOpened, true);
  assert.equal(pubKey, "GCEZWKCA5VLDANIKSI2AWMT4Q4IG47L5G3D3J22J7K3QGQXH2XW7Y2Z7");

  const signed = await adapter.signTransaction("SAMPLE_XDR", {
    networkPassphrase: "Test SDF Network ; September 2015",
  });
  assert.equal(signed, "KIT_SIGNED_SAMPLE_XDR_PASS_Test SDF Network ; September 2015");
});

test("SorobanClient: signAndSubmit signs with adapter and submits transaction", async () => {
  const mockApi = {
    isConnected: async () => true,
    getPublicKey: async () => "GPUBLIC123456",
    signTransaction: async (xdr, opts) => `AUTHSIGNED_${xdr}`,
  };
  const adapter = new FreighterAdapter(mockApi);

  const client = new SorobanClient({
    networkPassphrase: "Test SDF Future Network ; October 2024",
  });

  const res = await client.signAndSubmit("TEST_TX_PAYLOAD", adapter);
  assert.equal(res.status, "SUCCESS");
  assert.ok(res.txHash.startsWith("0x"));
  assert.equal(res.returnValueXdr, "AAAAAQ==");
});

test("SorobanClient: signAndSubmit fails closed if wallet is unavailable", async () => {
  const adapter = new FreighterAdapter();
  const client = new SorobanClient();

  await assert.rejects(
    async () => {
      await client.signAndSubmit("TEST_TX_PAYLOAD", adapter);
    },
    {
      name: "WalletNotInstalledError",
    }
  );
});
