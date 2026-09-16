/**
 * OmniBlocks Linux Emulator - JavaScript Cross-Runtime Engine.
 */

const PAGE_SIZE = 4096;
const TEXT_START = 0x00400000;
const DATA_START = 0x00500000;
const HEAP_START = 0x00600000;
const STACK_TOP = 0x7ffff000;

class VirtualMemory {
  /**
   * Initializes virtual memory buffer and segment mappings.
   * @param {number} sizeBytes
   */
  constructor(sizeBytes = 67108864) {
    this.sizeBytes = sizeBytes;
    this.buffer = new Uint8Array(1048576);
    this.currentBrk = HEAP_START;
  }

  /**
   * Reads a byte from virtual memory.
   * @param {number} address
   * @returns {number}
   */
  readByte(address) {
    const offset = address % this.buffer.length;
    return this.buffer[offset];
  }

  /**
   * Writes a byte to virtual memory.
   * @param {number} address
   * @param {number} value
   */
  writeByte(address, value) {
    const offset = address % this.buffer.length;
    this.buffer[offset] = value & 0xff;
  }

  /**
   * Reads a 32-bit unsigned integer from memory.
   * @param {number} address
   * @returns {number}
   */
  readU32(address) {
    let val = 0;
    for (let i = 0; i < 4; i++) {
      val |= this.readByte(address + i) << (i * 8);
    }
    return val >>> 0;
  }

  /**
   * Writes a 32-bit unsigned integer to memory.
   * @param {number} address
   * @param {number} value
   */
  writeU32(address, value) {
    for (let i = 0; i < 4; i++) {
      this.writeByte(address + i, (value >> (i * 8)) & 0xff);
    }
  }

  /**
   * Reads null-terminated string from memory.
   * @param {number} address
   * @returns {string}
   */
  readCString(address) {
    const chars = [];
    for (let i = 0; i < 4096; i++) {
      const b = this.readByte(address + i);
      if (b === 0) break;
      chars.push(String.fromCharCode(b));
    }
    return chars.join("");
  }

  /**
   * Writes null-terminated string to memory.
   * @param {number} address
   * @param {string} str
   * @returns {number}
   */
  writeCString(address, str) {
    for (let i = 0; i < str.length; i++) {
      this.writeByte(address + i, str.charCodeAt(i));
    }
    this.writeByte(address + str.length, 0);
    return str.length + 1;
  }

  /**
   * Adjusts the heap break address.
   * @param {number} newBrk
   * @returns {number}
   */
  brk(newBrk) {
    if (newBrk === 0) return this.currentBrk;
    if (newBrk >= HEAP_START && newBrk <= 0x04000000) {
      this.currentBrk = newBrk;
    }
    return this.currentBrk;
  }
}

class VirtualFileSystem {
  /**
   * Initializes hierarchical virtual filesystem tree.
   */
  constructor() {
    this.nextInode = 1;
    this.inodes = new Map();
    this.dirEntries = new Map();
    this.initRoot();
  }

  /**
   * Allocates a new filesystem inode.
   * @param {string} type
   * @param {number} mode
   * @returns {number}
   */
  allocateInode(type, mode) {
    const ino = this.nextInode++;
    this.inodes.set(ino, {
      inodeNumber: ino,
      type,
      mode,
      content: new Uint8Array(0),
      size: 0,
    });
    if (type === "directory") {
      this.dirEntries.set(ino, new Map());
    }
    return ino;
  }

  /**
   * Builds baseline filesystem directories and standard files.
   */
  initRoot() {
    const rootIno = this.allocateInode("directory", 0o755);
    const rootMap = this.dirEntries.get(rootIno);
    rootMap.set(".", rootIno);
    rootMap.set("..", rootIno);

    const dirs = ["/bin", "/dev", "/etc", "/home", "/proc", "/root", "/tmp", "/usr", "/var", "/var/log"];
    for (const d of dirs) {
      this.mkdir(d);
    }

    this.writeFile("/etc/hostname", "omniblocks-host\n");
    this.writeFile("/etc/passwd", "root:x:0:0:root:/root:/bin/sh\nuser:x:1000:1000:user:/home/user:/bin/sh\n");
    this.writeFile("/proc/version", "Linux version 6.8.0-omniblocks (gcc 13.2.0)\n");
  }

  /**
   * Resolves normalized absolute path.
   * @param {string} path
   * @param {string} cwd
   * @returns {string}
   */
  resolvePath(path, cwd = "/") {
    if (!path) return cwd;
    const target = path.startsWith("/") ? path : cwd.replace(/\/+$/, "") + "/" + path;
    const parts = target.split("/").filter((p) => p && p !== ".");
    const stack = [];
    for (const p of parts) {
      if (p === "..") {
        if (stack.length > 0) stack.pop();
      } else {
        stack.push(p);
      }
    }
    return "/" + stack.join("/");
  }

  /**
   * Looks up inode number for given path.
   * @param {string} path
   * @param {string} cwd
   * @returns {number|null}
   */
  lookupInode(path, cwd = "/") {
    const resolved = this.resolvePath(path, cwd);
    if (resolved === "/") return 1;
    const parts = resolved.split("/").filter(Boolean);
    let currentIno = 1;
    for (const p of parts) {
      const entries = this.dirEntries.get(currentIno);
      if (!entries || !entries.has(p)) return null;
      currentIno = entries.get(p);
    }
    return currentIno;
  }

  /**
   * Creates directory at path.
   * @param {string} path
   * @param {string} cwd
   * @returns {number}
   */
  mkdir(path, cwd = "/") {
    const resolved = this.resolvePath(path, cwd);
    if (this.lookupInode(resolved) !== null) {
      throw new Error("Directory exists: " + resolved);
    }
    const idx = resolved.lastIndexOf("/");
    const parentPath = idx === 0 ? "/" : resolved.substring(0, idx);
    const baseName = resolved.substring(idx + 1);

    const parentIno = this.lookupInode(parentPath);
    if (parentIno === null) {
      throw new Error("Parent directory not found: " + parentPath);
    }

    const dirIno = this.allocateInode("directory", 0o755);
    const dirMap = this.dirEntries.get(dirIno);
    dirMap.set(".", dirIno);
    dirMap.set("..", parentIno);
    this.dirEntries.get(parentIno).set(baseName, dirIno);
    return dirIno;
  }

  /**
   * Writes string data to file.
   * @param {string} path
   * @param {string} data
   * @param {string} cwd
   * @returns {number}
   */
  writeFile(path, data, cwd = "/") {
    const resolved = this.resolvePath(path, cwd);
    let ino = this.lookupInode(resolved);
    if (ino === null) {
      const idx = resolved.lastIndexOf("/");
      const parentPath = idx === 0 ? "/" : resolved.substring(0, idx);
      const baseName = resolved.substring(idx + 1);
      const parentIno = this.lookupInode(parentPath);
      if (parentIno === null) {
        throw new Error("Parent directory not found: " + parentPath);
      }
      ino = this.allocateInode("regular", 0o644);
      this.dirEntries.get(parentIno).set(baseName, ino);
    }
    const encoder = new TextEncoder();
    const encoded = encoder.encode(data);
    const inode = this.inodes.get(ino);
    inode.content = encoded;
    inode.size = encoded.length;
    return encoded.length;
  }

  /**
   * Reads file contents as string.
   * @param {string} path
   * @param {string} cwd
   * @returns {string}
   */
  readFile(path, cwd = "/") {
    const resolved = this.resolvePath(path, cwd);
    if (resolved === "/dev/null") return "";
    const ino = this.lookupInode(resolved);
    if (ino === null) {
      throw new Error("File not found: " + resolved);
    }
    const inode = this.inodes.get(ino);
    const decoder = new TextDecoder();
    return decoder.decode(inode.content);
  }

  /**
   * Lists directory entry names.
   * @param {string} path
   * @param {string} cwd
   * @returns {string[]}
   */
  listDir(path, cwd = "/") {
    const resolved = this.resolvePath(path, cwd);
    const ino = this.lookupInode(resolved);
    if (ino === null) throw new Error("Directory not found: " + resolved);
    const entries = this.dirEntries.get(ino);
    if (!entries) throw new Error("Not a directory: " + resolved);
    const names = [];
    for (const k of entries.keys()) {
      if (k !== "." && k !== "..") names.push(k);
    }
    return names.sort();
  }
}

class LinuxShell {
  /**
   * Initializes shell environment.
   * @param {VirtualFileSystem} vfs
   */
  constructor(vfs) {
    this.vfs = vfs;
    this.cwd = "/";
    this.env = {
      USER: "root",
      HOME: "/root",
      SHELL: "/bin/sh",
      PATH: "/bin:/usr/bin",
    };
  }

  /**
   * Executes a shell command line.
   * @param {string} cmdline
   * @returns {{ stdout: string, stderr: string, returncode: number }}
   */
  execute(cmdline) {
    const trimmed = cmdline.trim();
    if (!trimmed) return { stdout: "", stderr: "", returncode: 0 };

    if (trimmed.includes(" | ")) {
      const stages = trimmed.split(" | ");
      let stdinData = "";
      for (const stage of stages) {
        const res = this.executeSingle(stage, stdinData);
        stdinData = res.stdout;
      }
      return { stdout: stdinData, stderr: "", returncode: 0 };
    }

    return this.executeSingle(trimmed, "");
  }

  /**
   * Executes single pipeline stage with redirection.
   * @param {string} stage
   * @param {string} stdinData
   * @returns {{ stdout: string, stderr: string, returncode: number }}
   */
  executeSingle(stage, stdinData) {
    let writeTarget = null;
    let cmdPart = stage;
    if (stage.includes(" > ")) {
      const parts = stage.split(" > ");
      cmdPart = parts[0].trim();
      writeTarget = parts[1].trim();
    }

    const tokens = cmdPart.split(/\s+/).filter(Boolean);
    if (tokens.length === 0) return { stdout: "", stderr: "", returncode: 0 };

    const cmd = tokens[0];
    const args = tokens.slice(1);
    const res = this.dispatchBuiltin(cmd, args, stdinData);

    if (writeTarget) {
      this.vfs.writeFile(writeTarget, res.stdout, this.cwd);
      return { stdout: "", stderr: res.stderr, returncode: res.returncode };
    }

    return res;
  }

  /**
   * Dispatches built-in commands.
   * @param {string} cmd
   * @param {string[]} args
   * @param {string} stdinData
   * @returns {{ stdout: string, stderr: string, returncode: number }}
   */
  dispatchBuiltin(cmd, args, stdinData) {
    if (cmd === "echo") {
      return { stdout: args.join(" ") + "\n", stderr: "", returncode: 0 };
    }
    if (cmd === "pwd") {
      return { stdout: this.cwd + "\n", stderr: "", returncode: 0 };
    }
    if (cmd === "cd") {
      const target = args[0] || this.env.HOME || "/";
      const resolved = this.vfs.resolvePath(target, this.cwd);
      if (this.vfs.lookupInode(resolved) === null) {
        return { stdout: "", stderr: "cd: no such directory: " + target + "\n", returncode: 1 };
      }
      this.cwd = resolved;
      return { stdout: "", stderr: "", returncode: 0 };
    }
    if (cmd === "ls") {
      try {
        const entries = this.vfs.listDir(args[0] || ".", this.cwd);
        return { stdout: entries.join("  ") + "\n", stderr: "", returncode: 0 };
      } catch (err) {
        return { stdout: "", stderr: "ls: " + err.message + "\n", returncode: 1 };
      }
    }
    if (cmd === "cat") {
      if (args.length === 0) {
        return { stdout: stdinData, stderr: "", returncode: 0 };
      }
      try {
        const out = args.map((a) => this.vfs.readFile(a, this.cwd)).join("");
        return { stdout: out, stderr: "", returncode: 0 };
      } catch (err) {
        return { stdout: "", stderr: "cat: " + err.message + "\n", returncode: 1 };
      }
    }
    if (cmd === "uname") {
      if (args.includes("-a")) {
        return { stdout: "Linux omniblocks-vm 6.8.0-omniblocks x86_64\n", stderr: "", returncode: 0 };
      }
      return { stdout: "Linux\n", stderr: "", returncode: 0 };
    }
    if (cmd === "whoami") {
      return { stdout: this.env.USER + "\n", stderr: "", returncode: 0 };
    }
    if (cmd === "grep") {
      const pattern = args[0] || "";
      const lines = stdinData.split("\n").filter((l) => l.includes(pattern));
      return { stdout: lines.join("\n") + (lines.length ? "\n" : ""), stderr: "", returncode: lines.length ? 0 : 1 };
    }
    return { stdout: "", stderr: "bash: " + cmd + ": command not found\n", returncode: 127 };
  }
}

class OmniLinuxVM {
  /**
   * High-level JavaScript VM coordinator.
   * @param {object} options
   */
  constructor(options = {}) {
    this.ramMb = options.ramMb || 64;
    this.cores = options.cores || 1;
    this.memory = new VirtualMemory(this.ramMb * 1024 * 1024);
    this.vfs = new VirtualFileSystem();
    this.shell = new LinuxShell(this.vfs);
  }

  /**
   * Executes shell command in guest.
   * @param {string} cmd
   * @returns {{ stdout: string, stderr: string, returncode: number }}
   */
  runCommand(cmd) {
    return this.shell.execute(cmd);
  }

  /**
   * Writes file in guest filesystem.
   * @param {string} path
   * @param {string} content
   * @returns {number}
   */
  writeFile(path, content) {
    return this.vfs.writeFile(path, content, this.shell.cwd);
  }

  /**
   * Reads file from guest filesystem.
   * @param {string} path
   * @returns {string}
   */
  readFile(path) {
    return this.vfs.readFile(path, this.shell.cwd);
  }
}

/**
 * Computes bounty financial reward breakdown according to REWARD_POLICY.md.
 * @param {number} rewardUsd
 * @returns {object}
 */
function computeBountySettlement(rewardUsd = 9740486.0) {
  const exchangeRate = 1.25;
  const redemptionRate = 0.72;
  const ratio = rewardUsd >= 1000.0 ? 0.85 : rewardUsd >= 100.0 ? 0.8 : 0.7;

  const totalCoins = rewardUsd * exchangeRate;
  const contributorCoins = totalCoins * ratio;
  const payoutUsd = Math.round(contributorCoins * redemptionRate * 100) / 100;
  const platformFeeUsd = Math.round((rewardUsd - payoutUsd) * 100) / 100;

  return {
    rewardUsd,
    platformCoins: totalCoins,
    contributorRatio: ratio,
    contributorCoins,
    redemptionRateUsd: redemptionRate,
    contributorPayoutUsd: payoutUsd,
    platformFeeUsd,
  };
}

module.exports = {
  VirtualMemory,
  VirtualFileSystem,
  LinuxShell,
  OmniLinuxVM,
  bootVM: (opts) => new OmniLinuxVM(opts),
  computeBountySettlement,
};
