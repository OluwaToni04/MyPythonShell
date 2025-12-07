# MyPythonShell
# 🐚 Shell Usage & Visual Walkthrough

This document provides a detailed visual guide to the capabilities of the Python Shell.

---

## 1. Basic Navigation & Built-ins
The shell implements standard POSIX commands internally to ensure cross-platform compatibility (working on Windows without requiring WSL).

**Key Commands:**
- `pwd`: Print Working Directory.
- `cd <path>`: Change Directory (supports `~` for home).
- `echo <text>`: Print text to stdout.

**Visual Demo:**
> *Screenshot shows startup, verifying current directory, changing to `/tmp`, and printing a success message.*

![Basic Navigation Demo](basic_nav.png)

---

## 2. Command Type Inspection
The `type` command is critical for understanding how the shell interprets inputs. It distinguishes between:
1.  **Shell Built-ins**: Functions defined within `shell.py` (e.g., `cd`, `history`).
2.  **External Executables**: Binaries found in the system `$PATH` (e.g., `git`, `python`).
3.  **Unknown Commands**: Returns a specific error message.

**Visual Demo:**
> *Screenshot shows `type` identifying built-ins vs. external paths and handling missing commands in red.*

![Type Command Demo](type.png)

---

## 3. Input/Output Redirection
The shell manually manages file descriptors to redirect streams, allowing users to save command output to files or capture errors separately.

**Supported Operators:**
- `>`: Overwrite standard output to a file.
- `>>`: Append standard output to a file.
- `2>`: Redirect standard error to a file.

**Visual Demo:**
> *Screenshot shows creating a file via echo, reading it back with cat, and capturing a "file not found" error log.*

![IO Redirection Demo](redirection_Io.png)

---

## 4. Multi-Stage Pipelines
This is the most complex feature. The shell chains multiple processes together, connecting the `stdout` of one command to the `stdin` of the next. On Windows, this is achieved using `subprocess` and temporary files/pipes, avoiding Unix-specific `fork()` calls.

**Example Command:**
```bash
echo -e "apple\nbanana\ncherry" | grep "a" | wc -l
