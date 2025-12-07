import os
import sys
import readline
import subprocess
import webbrowser
import urllib.parse
import tempfile


# Constants & Utilities
SPACE = " "
RED = "\033[31m"
RESET = "\033[0m"


def print_error(message, file=None):
    """
    Prints a message in red to indicate an error or wrong input.
    """
    outfile = file if file else sys.stderr
    print(f"{RED}{message}{RESET}", file=outfile)



# 1. History Manager
class HistoryManager:
    """Manages command history (loading, saving, persistence)."""

    def __init__(self):
        self.history = []
        self.written_count = 0

    def add(self, line):
        if line:
            self.history.append(line)

    def get_all(self):
        return self.history

    def get_histfile_path(self):
        return os.environ.get("HISTFILE")

    def load(self):
        path = self.get_histfile_path()
        if path and os.path.exists(path):
            try:
                with open(path, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self.history.append(line)
                self.written_count = len(self.history)
            except Exception:
                pass

    def save(self):
        path = self.get_histfile_path()
        if not path:
            return
        try:
            with open(path, 'a') as f:
                for i in range(self.written_count, len(self.history)):
                    f.write(self.history[i] + '\n')
            self.written_count = len(self.history)
        except Exception:
            pass

    def load_from_file(self, filename):
        try:
            with open(filename, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        self.history.append(line)
        except Exception as e:
            print_error(f"history: {e}")

    def write_to_file(self, filename):
        try:
            with open(filename, 'w') as f:
                for cmd in self.history:
                    f.write(cmd + '\n')
        except Exception as e:
            print_error(f"history: {e}")

    def append_to_file(self, filename):
        try:
            with open(filename, 'a') as f:
                for i in range(self.written_count, len(self.history)):
                    f.write(self.history[i] + '\n')
            self.written_count = len(self.history)
        except Exception as e:
            print_error(f"history: {e}")



# 2. Command Parser
class CommandParser:
    """Parses raw input strings into tokens and pipeline structures."""

    @staticmethod
    def tokenize(line: str):
        args = []
        cur = ""
        i = 0
        n = len(line)
        in_single = False
        in_double = False

        while i < n:
            ch = line[i]
            if in_single:
                if ch == "'":
                    in_single = False
                else:
                    cur += ch
                i += 1
                continue
            if in_double:
                if ch == '"':
                    in_double = False
                    i += 1
                    continue
                elif ch == "\\":
                    # Handle escapes inside double quotes
                    if i + 1 < n:
                        nxt = line[i + 1]
                        # Only escape specific characters inside double quotes
                        if nxt in ['"', '\\', '$', '`', '\n']:
                            cur += nxt
                            i += 2
                            continue
                        else:
                            # Preserve backslash for other chars (like \n, \t)
                            cur += ch  # Add the backslash
                            i += 1
                            continue
                    else:
                        cur += ch
                        i += 1
                        continue
                else:
                    cur += ch
                    i += 1
                    continue

            if ch == "'":
                in_single = True
            elif ch == '"':
                in_double = True
            elif ch == "\\":
                i += 1
                if i < n: cur += line[i]
            elif ch.isspace():
                if cur:
                    args.append(cur)
                    cur = ""
            else:
                cur += ch
            i += 1

        if cur:
            args.append(cur)
        return args

    @staticmethod
    def split_pipeline(tokens):
        if "|" not in tokens:
            return None
        commands = []
        current_cmd = []
        for token in tokens:
            if token == "|":
                if current_cmd: commands.append(current_cmd)
                current_cmd = []
            else:
                current_cmd.append(token)
        if current_cmd:
            commands.append(current_cmd)
        return commands



# 3. Builtin Handler
class BuiltinHandler:
    """Executes internal shell commands."""

    def __init__(self, shell_instance):
        self.shell = shell_instance
        self.registry = {
            "exit": self.cmd_exit,
            "echo": self.cmd_echo,
            "pwd": self.cmd_pwd,
            "cd": self.cmd_cd,
            "type": self.cmd_type,
            "history": self.cmd_history,
            "search": self.cmd_search,
            "ls": self.cmd_ls,
            "cat": self.cmd_cat,
            "grep": self.cmd_grep,
            "wc": self.cmd_wc,
        }

    def is_builtin(self, name):
        return name in self.registry

    def execute(self, name, args):
        if name in self.registry:
            self.registry[name](args)
            return True
        return False

    def cmd_exit(self, args):
        self.shell.history_manager.save()
        if not args: sys.exit(0)
        try:
            sys.exit(int(args[0]))
        except:
            sys.exit(0)

    def cmd_echo(self, args):
        # Support -e flag for escape sequences
        interpret_escapes = False
        if args and args[0] == "-e":
            interpret_escapes = True
            args = args[1:]

        output = SPACE.join(args)

        if interpret_escapes:
            # Manually handle common escape sequences
            # Note: codecs.decode(output, 'unicode_escape') is cleaner but can be risky with user input
            output = output.replace('\\n', '\n').replace('\\t', '\t').replace('\\\\', '\\')

        print(output)

    def cmd_pwd(self, args=None):
        print(os.getcwd())

    def cmd_cd(self, args):
        path = os.path.expanduser("~") if not args else os.path.expanduser(args[0])
        try:
            os.chdir(path)
        except Exception as e:
            print_error(f"cd: {e}")

    def cmd_type(self, args):
        if not args:
            print_error("type: missing argument")
            return
        name = args[0]
        if self.is_builtin(name):
            print(f"{name} is a shell builtin")
            return
        path = os.environ.get("PATH", "")
        for d in path.split(os.pathsep):
            try:
                full = os.path.join(d, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    print(f"{name} is {full}")
                    return
                if sys.platform == "win32":
                    if os.path.isfile(full + ".exe"):
                        print(f"{name} is {full}.exe")
                        return
            except:
                pass
        print_error(f"{name}: not found")

    def cmd_history(self, args):
        hist = self.shell.history_manager
        if args:
            if args[0] == '-r' and len(args) > 1:
                hist.load_from_file(args[1]);
                return
            if args[0] == '-w' and len(args) > 1:
                hist.write_to_file(args[1]);
                return
            if args[0] == '-a' and len(args) > 1:
                hist.append_to_file(args[1]);
                return

        full_history = hist.get_all()
        start = 0
        if args and args[0].isdigit():
            start = max(0, len(full_history) - int(args[0]))

        for i in range(start, len(full_history)):
            print(f"{i + 1:5}  {full_history[i]}")

    def cmd_search(self, args):
        if not args:
            print_error("search: missing query")
            return
        query = urllib.parse.quote_plus(" ".join(args))
        url = f"https://www.google.com/search?q={query}"
        print(f"Searching web for: '{' '.join(args)}'...")
        try:
            webbrowser.open(url)
        except Exception as e:
            print_error(f"search error: {e}")

    def cmd_ls(self, args):
        target = args[0] if args else "."
        try:
            for item in sorted(os.listdir(target)):
                print(item)
        except Exception as e:
            print_error(f"ls: {e}")

    def cmd_cat(self, args):
        if not args: return
        for fname in args:
            try:
                with open(fname, 'r') as f:
                    print(f.read(), end='')
            except Exception as e:
                print_error(f"cat: {e}")

    def cmd_grep(self, args):
        if not args:
            print_error("grep: missing search pattern")
            return

        pattern = args[0]
        files = args[1:]

        if files:
            # Read from files
            for filename in files:
                try:
                    with open(filename, 'r') as f:
                        for line in f:
                            if pattern in line:
                                print(line, end='')
                except Exception as e:
                    print_error(f"grep: {filename}: {e}")
        else:
            # Read from stdin
            try:
                # Iterate over sys.stdin (which might be redirected)
                for line in sys.stdin:
                    if pattern in line:
                        print(line, end='')
            except Exception:
                pass

    def cmd_wc(self, args):
        """
        Builtin command: wc [-l] [-w] [-c] [file...]
        Print newline, word, and byte counts for each file.
        """
        # Parse flags
        show_lines = show_words = show_bytes = False
        filenames = []

        for arg in args:
            if arg.startswith("-"):
                if 'l' in arg: show_lines = True
                if 'w' in arg: show_words = True
                if 'c' in arg: show_bytes = True
            else:
                filenames.append(arg)

        # Default if no flags
        if not (show_lines or show_words or show_bytes):
            show_lines = show_words = show_bytes = True

        def count_and_print(content, name=""):
            lines = content.count('\n')
            words = len(content.split())
            bytes_count = len(content.encode('utf-8'))

            parts = []
            if show_lines: parts.append(f"{lines:>7}")
            if show_words: parts.append(f"{words:>7}")
            if show_bytes: parts.append(f"{bytes_count:>7}")

            print(f"{' '.join(parts)} {name}")
            return lines, words, bytes_count

        if not filenames:
            # Read from stdin
            try:
                content = sys.stdin.read()
                count_and_print(content)
            except Exception as e:
                print_error(f"wc: {e}")
            return

        total_lines, total_words, total_bytes = 0, 0, 0
        for filename in filenames:
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    content = f.read()
                    l, w, b = count_and_print(content, filename)
                    total_lines += l
                    total_words += w
                    total_bytes += b
            except FileNotFoundError:
                print_error(f"wc: {filename}: No such file or directory")
            except PermissionError:
                print_error(f"wc: {filename}: Permission denied")
            except Exception as e:
                print_error(f"wc: {filename}: {e}")

        if len(filenames) > 1:
            parts = []
            if show_lines: parts.append(f"{total_lines:>7}")
            if show_words: parts.append(f"{total_words:>7}")
            if show_bytes: parts.append(f"{total_bytes:>7}")
            print(f"{' '.join(parts)} total")



# 4. Executor (Windows Compatible)
class Executor:
    """Handles execution, pipelines, and redirection without fork."""

    def __init__(self, builtin_handler):
        self.builtin_handler = builtin_handler

    def find_executable(self, name):
        if os.path.isabs(name) or os.path.dirname(name):
            if os.path.isfile(name): return name
        path_env = os.environ.get("PATH", "")
        for d in path_env.split(os.pathsep):
            try:
                full = os.path.join(d, name)
                if os.path.isfile(full): return full
                if sys.platform == "win32" and os.path.isfile(full + ".exe"): return full + ".exe"
            except:
                pass
        return None

    def parse_redirections(self, tokens):
        stdout_dest = None
        stderr_dest = None
        clean_tokens = list(tokens)
        file_out = None
        file_err = None

        try:
            # Stderr
            for op in ("2>>", "2>"):
                if op in clean_tokens:
                    idx = clean_tokens.index(op)
                    if idx + 1 < len(clean_tokens):
                        mode = 'a' if '>>' in op else 'w'
                        file_err = open(clean_tokens[idx + 1], mode)
                        stderr_dest = file_err
                        del clean_tokens[idx:idx + 2]
                    break

            # Stdout
            for op in ("1>>", ">>", "1>", ">"):
                if op in clean_tokens:
                    idx = clean_tokens.index(op)
                    if idx + 1 < len(clean_tokens):
                        mode = 'a' if '>>' in op else 'w'
                        file_out = open(clean_tokens[idx + 1], mode)
                        stdout_dest = file_out
                        del clean_tokens[idx:idx + 2]
                    break
        except Exception as e:
            print_error(f"Redirection error: {e}")
            return None, None, None, None, None

        return clean_tokens, stdout_dest, stderr_dest, file_out, file_err

    def run_single_command(self, tokens):
        if not tokens: return
        tokens, stdout, stderr, fout, ferr = self.parse_redirections(tokens)
        if tokens is None: return

        cmd = tokens[0]
        if self.builtin_handler.is_builtin(cmd):
            # Capture redirection for builtins manually
            old_out, old_err = sys.stdout, sys.stderr
            try:
                if stdout: sys.stdout = stdout
                if stderr: sys.stderr = stderr
                self.builtin_handler.execute(cmd, tokens[1:])
            except Exception as e:
                print_error(f"Error: {e}")
            finally:
                sys.stdout, sys.stderr = old_out, old_err
        else:
            exe = self.find_executable(cmd)
            if not exe:
                print_error(f"{cmd}: command not found")
            else:
                try:
                    subprocess.run(tokens, executable=exe, stdout=stdout, stderr=stderr)
                except Exception as e:
                    print_error(f"Execution error: {e}")

        if fout: fout.close()
        if ferr: ferr.close()

    def run_pipeline(self, commands):
        """Windows-compatible pipeline using subprocess and tempfiles for builtins."""
        if not commands: return

        # We chain processes. prev_stdin is the input for the current command.
        prev_stdin = None
        to_close = []

        for i, cmd_tokens in enumerate(commands):
            is_last = (i == len(commands) - 1)

            # Handle redirections per stage
            clean_tokens, f_out, f_err, fo_handle, fe_handle = self.parse_redirections(cmd_tokens)
            if not clean_tokens: break
            if fo_handle: to_close.append(fo_handle)
            if fe_handle: to_close.append(fe_handle)

            cmd_name = clean_tokens[0]

            # Determine Output
            if is_last:
                current_stdout = f_out if f_out else None  # None -> Console
            else:
                current_stdout = subprocess.PIPE

            # EXECUTION STRATEGY
            if self.builtin_handler.is_builtin(cmd_name):
                # Setup Stdin if coming from pipe
                old_stdin = sys.stdin
                if prev_stdin:
                    sys.stdin = prev_stdin

                # Setup Stdout (Temp file if not last, else redirection/console)
                old_stdout = sys.stdout
                temp_out = None

                if not is_last:
                    temp_out = tempfile.TemporaryFile(mode='w+')
                    sys.stdout = temp_out
                elif f_out:
                    sys.stdout = f_out

                try:
                    self.builtin_handler.execute(cmd_name, clean_tokens[1:])
                except Exception as e:
                    print_error(f"Pipeline error: {e}")
                finally:
                    sys.stdout = old_stdout
                    sys.stdin = old_stdin  # Restore stdin

                if not is_last:
                    temp_out.seek(0)
                    prev_stdin = temp_out
                    to_close.append(temp_out)
                else:
                    prev_stdin = None
            else:
                # External Command
                exe = self.find_executable(cmd_name)
                if not exe:
                    print_error(f"{cmd_name}: command not found")
                    break

                try:
                    proc = subprocess.Popen(
                        clean_tokens,
                        executable=exe,
                        stdin=prev_stdin,
                        stdout=current_stdout,
                        stderr=f_err,
                        text=True  # Ensure text mode for piping
                    )

                    if not is_last:
                        prev_stdin = proc.stdout  # Pipe output to next
                    else:
                        proc.wait()  # Wait for last command

                except Exception as e:
                    print_error(f"Pipeline error: {e}")
                    break

        # Cleanup
        for f in to_close:
            try:
                f.close()
            except:
                pass


# 5. Autocompleter
class AutoCompleter:
    def __init__(self, builtin_keys):
        self.builtin_keys = builtin_keys

    def complete(self, text, state):
        buf = readline.get_line_buffer()
        matches = []
        for b in sorted(self.builtin_keys):
            if b.startswith(text): matches.append(b)

        path_env = os.environ.get("PATH", "")
        for d in path_env.split(os.pathsep):
            try:
                for f in os.listdir(d):
                    if f.startswith(text): matches.append(f)
            except:
                pass

        matches = sorted(list(set(matches)))
        if state < len(matches): return matches[state]
        return None

    def display_matches(self, substitution, matches, longest_match_length):
        print()
        print("  ".join(matches))
        sys.stdout.write(f"$ {readline.get_line_buffer()}")
        sys.stdout.flush()

    def register(self):
        readline.set_completer(self.complete)
        if hasattr(readline, 'set_completion_display_matches_hook'):
            readline.set_completion_display_matches_hook(self.display_matches)
        readline.parse_and_bind("tab: complete")


# 6. Main Shell Controller
class Shell:
    def __init__(self):
        self.history_manager = HistoryManager()
        self.builtin_handler = BuiltinHandler(self)
        self.executor = Executor(self.builtin_handler)
        self.completer = AutoCompleter(self.builtin_handler.registry.keys())

    def start(self):
        self.history_manager.load()
        self.completer.register()

        while True:
            try:
                line = input("$ ")
                if line:
                    self.history_manager.add(line)
                    self.process_line(line)
            except EOFError:
                print()
                self.history_manager.save()
                break
            except KeyboardInterrupt:
                print()
                continue

    def process_line(self, line):
        if not line.strip(): return
        tokens = CommandParser.tokenize(line.strip())
        commands = CommandParser.split_pipeline(tokens)
        if commands:
            self.executor.run_pipeline(commands)
        else:
            self.executor.run_single_command(tokens)


if __name__ == "__main__":
    shell = Shell()
    shell.start()