/**
 * Unit test suite for OmniBlocks Linux Emulator Node.js implementation.
 */

const assert = require("assert");
const {
  VirtualMemory,
  VirtualFileSystem,
  LinuxShell,
  OmniLinuxVM,
  bootVM,
  computeBountySettlement,
} = require("../src/linux_emulator.js");

function testMemory() {
  const mem = new VirtualMemory(1048576);
  mem.writeByte(0x1000, 0x42);
  assert.strictEqual(mem.readByte(0x1000), 0x42);

  mem.writeU32(0x2000, 0x12345678);
  assert.strictEqual(mem.readU32(0x2000), 0x12345678);

  mem.writeCString(0x3000, "hello virtual linux");
  assert.strictEqual(mem.readCString(0x3000), "hello virtual linux");

  const oldBrk = mem.brk(0);
  assert.strictEqual(oldBrk, 0x00600000);
  const newBrk = mem.brk(0x00700000);
  assert.strictEqual(newBrk, 0x00700000);
}

function testFileSystem() {
  const vfs = new VirtualFileSystem();
  assert.ok(vfs.lookupInode("/etc/hostname") > 0);

  const hostname = vfs.readFile("/etc/hostname");
  assert.strictEqual(hostname.trim(), "omniblocks-host");

  vfs.mkdir("/home/testdir");
  vfs.writeFile("/home/testdir/sample.txt", "data payload");
  const readBack = vfs.readFile("/home/testdir/sample.txt");
  assert.strictEqual(readBack, "data payload");

  const list = vfs.listDir("/home/testdir");
  assert.deepStrictEqual(list, ["sample.txt"]);
}

function testShell() {
  const vfs = new VirtualFileSystem();
  const shell = new LinuxShell(vfs);

  const echoRes = shell.execute("echo testing 1 2 3");
  assert.strictEqual(echoRes.returncode, 0);
  assert.strictEqual(echoRes.stdout.trim(), "testing 1 2 3");

  shell.execute("echo redirected > /tmp/output.txt");
  const catRes = shell.execute("cat /tmp/output.txt");
  assert.strictEqual(catRes.stdout.trim(), "redirected");

  const pipeRes = shell.execute("cat /etc/passwd | grep root");
  assert.ok(pipeRes.stdout.includes("root:x:0:0:root"));

  const unameRes = shell.execute("uname -a");
  assert.ok(unameRes.stdout.includes("Linux"));
}

function testVMCoordinator() {
  const vm = bootVM({ ramMb: 128, cores: 2 });
  assert.strictEqual(vm.ramMb, 128);

  const res = vm.runCommand("pwd");
  assert.strictEqual(res.stdout.trim(), "/");

  vm.writeFile("/var/log/test.log", "operational ok");
  const logContent = vm.readFile("/var/log/test.log");
  assert.strictEqual(logContent, "operational ok");
}

function testBountySettlement() {
  const b = computeBountySettlement(9740486.0);
  assert.strictEqual(b.rewardUsd, 9740486.0);
  assert.strictEqual(b.platformCoins, 12175607.5);
  assert.strictEqual(b.contributorRatio, 0.85);
  assert.strictEqual(b.contributorCoins, 10349266.375);
  assert.strictEqual(b.contributorPayoutUsd, 7451471.79);
  assert.strictEqual(b.platformFeeUsd, 2289014.21);
}

function runAll() {
  testMemory();
  testFileSystem();
  testShell();
  testVMCoordinator();
  testBountySettlement();
  console.log("All Node.js tests passed successfully.");
}

runAll();
