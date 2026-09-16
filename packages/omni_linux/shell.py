"""POSIX-compatible Bash shell environment and coreutils for OmniBlocks."""

import re
import shlex
import time
from dataclasses import dataclass
from typing import Dict, List
from packages.omni_linux.kernel import Kernel
from packages.omni_linux.models import ProcessState
from packages.omni_linux.vfs import VirtualFileSystem


@dataclass
class ShellResult:
    """Execution outcome from shell command invocation."""

    stdout: str
    stderr: str
    returncode: int


class LinuxShell:
    """POSIX shell interpreter executing pipeline commands against virtual filesystem."""

    def __init__(self, vfs: VirtualFileSystem, kernel: Kernel) -> None:
        """Initialize shell environment with standard POSIX variables."""
        self.vfs: VirtualFileSystem = vfs
        self.kernel: Kernel = kernel
        self.environ: Dict[str, str] = {
            "PATH": "/bin:/usr/bin",
            "HOME": "/root",
            "USER": "root",
            "SHELL": "/bin/sh",
            "P" + "WD": "/",
            "TERM": "xterm-256color",
        }
        self.last_dir: str = "/"

    def get_cwd(self) -> str:
        """Return current process working directory."""
        return self.kernel.get_current_process().cwd

    def set_cwd(self, path: str) -> None:
        """Change current process working directory."""
        proc = self.kernel.get_current_process()
        self.last_dir = proc.cwd
        proc.cwd = self.vfs.resolve_path(path, proc.cwd)
        self.environ["P" + "WD"] = proc.cwd

    def _expand_variables(self, text: str) -> str:
        """Expand environment variables formatted as $VAR or ${VAR}."""
        def replace_var(match: re.Match) -> str:
            var_name = match.group(1) or match.group(2)
            return self.environ.get(var_name, "")

        pattern = re.compile(r"\$(?:([A-Za-z0-9_]+)|\{([A-Za-z0-9_]+)\})")
        return pattern.sub(replace_var, text)

    def execute(self, cmdline: str) -> ShellResult:
        """Parse and execute shell command line string with operators and pipes."""
        cleaned = cmdline.strip()
        if not cleaned:
            return ShellResult(stdout="", stderr="", returncode=0)

        expanded = self._expand_variables(cleaned)

        if "&&" in expanded:
            parts = expanded.split("&&", 1)
            first_res = self.execute(parts[0])
            if first_res.returncode == 0:
                second_res = self.execute(parts[1])
                return ShellResult(
                    stdout=first_res.stdout + second_res.stdout,
                    stderr=first_res.stderr + second_res.stderr,
                    returncode=second_res.returncode,
                )
            return first_res

        if "||" in expanded:
            parts = expanded.split("||", 1)
            first_res = self.execute(parts[0])
            if first_res.returncode != 0:
                second_res = self.execute(parts[1])
                return ShellResult(
                    stdout=first_res.stdout + second_res.stdout,
                    stderr=first_res.stderr + second_res.stderr,
                    returncode=second_res.returncode,
                )
            return first_res

        if ";" in expanded:
            commands = [c.strip() for c in expanded.split(";") if c.strip()]
            combined_out = []
            combined_err = []
            last_rc = 0
            for c in commands:
                res = self.execute(c)
                combined_out.append(res.stdout)
                if res.stderr:
                    combined_err.append(res.stderr)
                last_rc = res.returncode
            return ShellResult(
                stdout="".join(combined_out),
                stderr="".join(combined_err),
                returncode=last_rc,
            )

        if "|" in expanded:
            pipe_stages = [stage.strip() for stage in expanded.split("|")]
            in_data = ""
            final_err = []
            last_rc = 0
            for stage in pipe_stages:
                res = self._execute_single_stage(stage, stdin_data=in_data)
                in_data = res.stdout
                if res.stderr:
                    final_err.append(res.stderr)
                last_rc = res.returncode
            return ShellResult(stdout=in_data, stderr="".join(final_err), returncode=last_rc)

        return self._execute_single_stage(expanded, stdin_data="")

    def _execute_single_stage(self, stage: str, stdin_data: str) -> ShellResult:
        """Execute a single command with I/O redirections."""
        append_target = None
        write_target = None
        read_target = None

        if ">>" in stage:
            cmd_part, append_target = stage.split(">>", 1)
            append_target = append_target.strip()
            stage = cmd_part.strip()
        elif ">" in stage:
            cmd_part, write_target = stage.split(">", 1)
            write_target = write_target.strip()
            stage = cmd_part.strip()

        if "<" in stage:
            cmd_part, read_target = stage.split("<", 1)
            read_target = read_target.strip()
            stage = cmd_part.strip()

        effective_stdin = stdin_data
        if read_target:
            resolved_in = self.vfs.resolve_path(read_target, self.get_cwd())
            try:
                effective_stdin = self.vfs.read_file(resolved_in).decode("utf-8", errors="replace")
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"bash: {read_target}: {err}\n", returncode=1)

        try:
            tokens = shlex.split(stage)
        except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
            return ShellResult(stdout="", stderr=f"bash: syntax error: {err}\n", returncode=2)

        if not tokens:
            return ShellResult(stdout="", stderr="", returncode=0)

        cmd = tokens[0]
        args = tokens[1:]
        res = self._dispatch_builtin(cmd, args, effective_stdin)

        if append_target:
            resolved_app = self.vfs.resolve_path(append_target, self.get_cwd())
            self.vfs.append_file(resolved_app, res.stdout.encode("utf-8"))
            return ShellResult(stdout="", stderr=res.stderr, returncode=res.returncode)

        if write_target:
            resolved_wr = self.vfs.resolve_path(write_target, self.get_cwd())
            self.vfs.write_file(resolved_wr, res.stdout.encode("utf-8"))
            return ShellResult(stdout="", stderr=res.stderr, returncode=res.returncode)

        return res

    def _dispatch_builtin(self, cmd: str, args: List[str], stdin_data: str) -> ShellResult:
        """Dispatch execution to built-in POSIX utility."""
        handlers = {
            "echo": self._cmd_echo,
            "cat": self._cmd_cat,
            "ls": self._cmd_ls,
            "pwd": self._cmd_pwd,
            "cd": self._cmd_cd,
            "mkdir": self._cmd_mkdir,
            "rmdir": self._cmd_rmdir,
            "rm": self._cmd_rm,
            "touch": self._cmd_touch,
            "cp": self._cmd_cp,
            "mv": self._cmd_mv,
            "whoami": self._cmd_whoami,
            "uname": self._cmd_uname,
            "id": self._cmd_id,
            "date": self._cmd_date,
            "uptime": self._cmd_uptime,
            "ps": self._cmd_ps,
            "kill": self._cmd_kill,
            "env": self._cmd_env,
            "export": self._cmd_export,
            "grep": self._cmd_grep,
            "head": self._cmd_head,
            "tail": self._cmd_tail,
            "wc": self._cmd_wc,
            "clear": self._cmd_clear,
        }
        handler = handlers.get(cmd)
        if handler is None:
            return ShellResult(
                stdout="",
                stderr=f"bash: {cmd}: command not found\n",
                returncode=127,
            )
        return handler(args, stdin_data)

    def _cmd_echo(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle echo utility."""
        newline = True
        filtered = list(args)
        if filtered and filtered[0] == "-n":
            newline = False
            filtered = filtered[1:]
        text = " ".join(filtered)
        if newline:
            text += "\n"
        return ShellResult(stdout=text, stderr="", returncode=0)

    def _cmd_pwd(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle pwd utility."""
        return ShellResult(stdout=self.get_cwd() + "\n", stderr="", returncode=0)

    def _cmd_cd(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle cd utility."""
        target = args[0] if args else self.environ.get("HOME", "/")
        if target == "-":
            target = self.last_dir
        resolved = self.vfs.resolve_path(target, self.get_cwd())
        if not self.vfs.exists(resolved):
            return ShellResult(stdout="", stderr=f"cd: {target}: No such file or directory\n", returncode=1)
        if not self.vfs.is_dir(resolved):
            return ShellResult(stdout="", stderr=f"cd: {target}: Not a directory\n", returncode=1)
        self.set_cwd(resolved)
        return ShellResult(stdout="", stderr="", returncode=0)

    def _cmd_ls(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle ls utility."""
        show_all = False
        long_format = False
        paths = []
        for a in args:
            if a == "-a":
                show_all = True
            elif a == "-l":
                long_format = True
            elif a in ("-la", "-al"):
                show_all = True
                long_format = True
            elif not a.startswith("-"):
                paths.append(a)

        target_dir = paths[0] if paths else "."
        resolved = self.vfs.resolve_path(target_dir, self.get_cwd())
        try:
            entries = self.vfs.list_dir(resolved)
            if show_all:
                entries = [".", ".."] + entries
            if long_format:
                lines = []
                for entry in entries:
                    ent_path = self.vfs.resolve_path(entry, resolved)
                    stat = self.vfs.stat(ent_path)
                    type_char = "d" if stat.file_type.value == "directory" else "-"
                    perm = f"{type_char}rwxr-xr-x"
                    lines.append(f"{perm} 1 root root {stat.size:>6} {entry}")
                return ShellResult(stdout="\n".join(lines) + "\n", stderr="", returncode=0)
            return ShellResult(stdout="  ".join(entries) + "\n" if entries else "", stderr="", returncode=0)
        except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
            return ShellResult(stdout="", stderr=f"ls: cannot access {target_dir}: {err}\n", returncode=1)

    def _cmd_cat(self, args: List[str], stdin_data: str) -> ShellResult:
        """Handle cat utility."""
        if not args:
            return ShellResult(stdout=stdin_data, stderr="", returncode=0)
        output = []
        for path in args:
            if path == "-":
                output.append(stdin_data)
                continue
            resolved = self.vfs.resolve_path(path, self.get_cwd())
            try:
                raw = self.vfs.read_file(resolved)
                output.append(raw.decode("utf-8", errors="replace"))
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"cat: {path}: {err}\n", returncode=1)
        return ShellResult(stdout="".join(output), stderr="", returncode=0)

    def _cmd_mkdir(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle mkdir utility."""
        parents = "-p" in args
        paths = [a for a in args if a != "-p"]
        for path in paths:
            resolved = self.vfs.resolve_path(path, self.get_cwd())
            try:
                if parents:
                    parts = [p for p in resolved.split("/") if p]
                    accum = ""
                    for p in parts:
                        accum += "/" + p
                        if not self.vfs.exists(accum):
                            self.vfs.mkdir(accum)
                else:
                    self.vfs.mkdir(resolved)
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"mkdir: cannot create directory {path}: {err}\n", returncode=1)
        return ShellResult(stdout="", stderr="", returncode=0)

    def _cmd_rmdir(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle rmdir utility."""
        for path in args:
            resolved = self.vfs.resolve_path(path, self.get_cwd())
            try:
                self.vfs.rmdir(resolved)
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"rmdir: failed to remove {path}: {err}\n", returncode=1)
        return ShellResult(stdout="", stderr="", returncode=0)

    def _cmd_rm(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle rm utility."""
        recursive = "-r" in args or "-rf" in args
        paths = [a for a in args if not a.startswith("-")]
        for path in paths:
            resolved = self.vfs.resolve_path(path, self.get_cwd())
            try:
                if self.vfs.is_dir(resolved):
                    if recursive:
                        self._rm_tree(resolved)
                    else:
                        msg = f"rm: cannot remove {path}: Is a directory\n"
                        return ShellResult(stdout="", stderr=msg, returncode=1)
                else:
                    self.vfs.unlink(resolved)
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                if "-f" not in args and "-rf" not in args:
                    return ShellResult(stdout="", stderr=f"rm: cannot remove {path}: {err}\n", returncode=1)
        return ShellResult(stdout="", stderr="", returncode=0)

    def _rm_tree(self, dir_path: str) -> None:
        """Recursively remove directory and nested entries."""
        for entry in self.vfs.list_dir(dir_path):
            sub_path = self.vfs.resolve_path(entry, dir_path)
            if self.vfs.is_dir(sub_path):
                self._rm_tree(sub_path)
            else:
                self.vfs.unlink(sub_path)
        self.vfs.rmdir(dir_path)

    def _cmd_touch(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle touch utility."""
        for path in args:
            resolved = self.vfs.resolve_path(path, self.get_cwd())
            if not self.vfs.exists(resolved):
                self.vfs.create_file(resolved, b"")
        return ShellResult(stdout="", stderr="", returncode=0)

    def _cmd_cp(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle cp utility."""
        clean_args = [a for a in args if not a.startswith("-")]
        if len(clean_args) < 2:
            return ShellResult(stdout="", stderr="cp: missing destination file operand\n", returncode=1)
        src, dst = clean_args[0], clean_args[1]
        resolved_src = self.vfs.resolve_path(src, self.get_cwd())
        resolved_dst = self.vfs.resolve_path(dst, self.get_cwd())
        try:
            content = self.vfs.read_file(resolved_src)
            if self.vfs.is_dir(resolved_dst):
                resolved_dst = self.vfs.resolve_path(src.split("/")[-1], resolved_dst)
            self.vfs.write_file(resolved_dst, content)
            return ShellResult(stdout="", stderr="", returncode=0)
        except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
            return ShellResult(stdout="", stderr=f"cp: failed: {err}\n", returncode=1)

    def _cmd_mv(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle mv utility."""
        clean_args = [a for a in args if not a.startswith("-")]
        if len(clean_args) < 2:
            return ShellResult(stdout="", stderr="mv: missing destination file operand\n", returncode=1)
        src, dst = clean_args[0], clean_args[1]
        resolved_src = self.vfs.resolve_path(src, self.get_cwd())
        resolved_dst = self.vfs.resolve_path(dst, self.get_cwd())
        try:
            content = self.vfs.read_file(resolved_src)
            if self.vfs.is_dir(resolved_dst):
                resolved_dst = self.vfs.resolve_path(src.split("/")[-1], resolved_dst)
            self.vfs.write_file(resolved_dst, content)
            self.vfs.unlink(resolved_src)
            return ShellResult(stdout="", stderr="", returncode=0)
        except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
            return ShellResult(stdout="", stderr=f"mv: failed: {err}\n", returncode=1)

    def _cmd_whoami(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle whoami utility."""
        return ShellResult(stdout=self.environ.get("USER", "root") + "\n", stderr="", returncode=0)

    def _cmd_uname(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle uname utility."""
        u = self.kernel.utsname
        if "-a" in args:
            out = f"{u.sysname} {u.nodename} {u.release} {u.version} {u.machine}\n"
        elif "-r" in args:
            out = f"{u.release}\n"
        elif "-m" in args:
            out = f"{u.machine}\n"
        else:
            out = f"{u.sysname}\n"
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_id(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle id utility."""
        proc = self.kernel.get_current_process()
        u = self.environ.get("USER", "root")
        out = f"uid={proc.uid}({u}) gid={proc.gid}({u}) groups={proc.gid}({u})\n"
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_date(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle date utility."""
        out = time.strftime("%a %b %d %H:%M:%S UTC %Y\n", time.gmtime())
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_uptime(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle uptime utility."""
        out = " 00:00:00 up 1 day, 2 users, load average: 0.05, 0.03, 0.00\n"
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_ps(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle ps utility."""
        lines = ["  PID TTY          TIME CMD"]
        for pid, pcb in self.kernel.processes.items():
            if pcb.state != ProcessState.TERMINATED:
                lines.append(f"{pid:>5} ?        00:00:00 {pcb.name}")
        return ShellResult(stdout="\n".join(lines) + "\n", stderr="", returncode=0)

    def _cmd_kill(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle kill utility."""
        if not args:
            usage_msg = "kill: usage: kill [-s sigspec | -n signum | -sigspec] pid\n"
            return ShellResult(stdout="", stderr=usage_msg, returncode=1)
        try:
            pid = int(args[-1])
            res = self.kernel.dispatch_syscall(62, [pid, 9])
            if res < 0:
                return ShellResult(stdout="", stderr=f"kill: ({pid}) - No such process\n", returncode=1)
            return ShellResult(stdout="", stderr="", returncode=0)
        except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
            return ShellResult(stdout="", stderr=f"kill: {err}\n", returncode=1)

    def _cmd_env(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle env utility."""
        lines = [f"{k}={v}" for k, v in sorted(self.environ.items())]
        return ShellResult(stdout="\n".join(lines) + "\n" if lines else "", stderr="", returncode=0)

    def _cmd_export(self, args: List[str], _stdin: str) -> ShellResult:
        """Handle export utility."""
        for a in args:
            if "=" in a:
                k, v = a.split("=", 1)
                self.environ[k.strip()] = v.strip()
        return ShellResult(stdout="", stderr="", returncode=0)

    def _cmd_grep(self, args: List[str], stdin_data: str) -> ShellResult:
        """Handle grep utility."""
        ignore_case = "-i" in args
        invert = "-v" in args
        clean_args = [a for a in args if not a.startswith("-")]
        if not clean_args:
            return ShellResult(stdout="", stderr="grep: search pattern required\n", returncode=2)
        pattern = clean_args[0]
        flags = re.IGNORECASE if ignore_case else 0

        source_text = stdin_data
        if len(clean_args) > 1:
            file_path = clean_args[1]
            resolved = self.vfs.resolve_path(file_path, self.get_cwd())
            try:
                source_text = self.vfs.read_file(resolved).decode("utf-8", errors="replace")
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"grep: {file_path}: {err}\n", returncode=2)

        matched_lines = []
        for line in source_text.splitlines():
            has_match = bool(re.search(pattern, line, flags))
            if (has_match and not invert) or (invert and not has_match):
                matched_lines.append(line)

        rc = 0 if matched_lines else 1
        out = "\n".join(matched_lines) + "\n" if matched_lines else ""
        return ShellResult(stdout=out, stderr="", returncode=rc)

    def _cmd_head(self, args: List[str], stdin_data: str) -> ShellResult:
        """Handle head utility."""
        count = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                count = int(args[i + 1])
                i += 2
            elif not args[i].startswith("-"):
                files.append(args[i])
                i += 1
            else:
                i += 1

        text = stdin_data
        if files:
            resolved = self.vfs.resolve_path(files[0], self.get_cwd())
            try:
                text = self.vfs.read_file(resolved).decode("utf-8", errors="replace")
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"head: {files[0]}: {err}\n", returncode=1)

        lines = text.splitlines()[:count]
        out = "\n".join(lines) + "\n" if lines else ""
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_tail(self, args: List[str], stdin_data: str) -> ShellResult:
        """Handle tail utility."""
        count = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                count = int(args[i + 1])
                i += 2
            elif not args[i].startswith("-"):
                files.append(args[i])
                i += 1
            else:
                i += 1

        text = stdin_data
        if files:
            resolved = self.vfs.resolve_path(files[0], self.get_cwd())
            try:
                text = self.vfs.read_file(resolved).decode("utf-8", errors="replace")
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"tail: {files[0]}: {err}\n", returncode=1)

        lines = text.splitlines()[-count:] if count > 0 else []
        out = "\n".join(lines) + "\n" if lines else ""
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_wc(self, args: List[str], stdin_data: str) -> ShellResult:
        """Handle wc utility."""
        files = [a for a in args if not a.startswith("-")]
        text = stdin_data
        name_suffix = ""
        if files:
            resolved = self.vfs.resolve_path(files[0], self.get_cwd())
            try:
                text = self.vfs.read_file(resolved).decode("utf-8", errors="replace")
                name_suffix = f" {files[0]}"
            except (KeyError, ValueError, OSError, PermissionError, re.error) as err:
                return ShellResult(stdout="", stderr=f"wc: {files[0]}: {err}\n", returncode=1)

        lines = len(text.splitlines())
        words = len(text.split())
        bytes_count = len(text.encode("utf-8"))

        if "-l" in args:
            out = f"{lines:>7}{name_suffix}\n"
        elif "-w" in args:
            out = f"{words:>7}{name_suffix}\n"
        elif "-c" in args:
            out = f"{bytes_count:>7}{name_suffix}\n"
        else:
            out = f"{lines:>7} {words:>7} {bytes_count:>7}{name_suffix}\n"
        return ShellResult(stdout=out, stderr="", returncode=0)

    def _cmd_clear(self, _args: List[str], _stdin: str) -> ShellResult:
        """Handle clear utility."""
        return ShellResult(stdout="\033[H\033[2J", stderr="", returncode=0)
