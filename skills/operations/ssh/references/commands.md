# SSH Command Reference

Use with the [entrypoint](../SKILL.md), after confirming the target username and applying its authentication boundaries.
Read and use only the sections matching the current environment.

## Environment Probes

Use these commands as environment-specific hints, not as a reason to run every probe:

| Current shell                            | Identify environment and SSH client                                               | Default SSH directory                                                                     |
|------------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------|
| Windows PowerShell / PowerShell 7        | `$PSVersionTable`; `[System.Environment]::OSVersion`; `Get-Command ssh`; `ssh -V` | On Windows, `Join-Path $env:USERPROFILE '.ssh'`; on Linux/macOS, `Join-Path $HOME '.ssh'` |
| Windows cmd                              | `ver`; `where ssh`; `ssh -V`                                                      | `%USERPROFILE%\.ssh`                                                                      |
| Linux / macOS POSIX shell                | `uname -s`; `command -v ssh`; `ssh -V`                                            | `"$HOME/.ssh"`                                                                            |
| WSL                                      | `uname -a`; `command -v ssh`                                                      | `"$HOME/.ssh"` inside the selected distribution, independently of Windows                 |
| Git Bash / other Unix-like Windows shell | `uname -s`; `command -v ssh`; `ssh -V`                                            | Determine which SSH binary and home directory that shell actually uses                    |

PowerShell 7 also runs on Linux and macOS. Choose quoting by shell and paths by operating system. Use the execution
tool's shell metadata when available; `$SHELL` alone does not reliably identify the active shell. If the selected client
is not OpenSSH, inspect its usage and translate the connection options instead of passing unsupported OpenSSH flags.

## Commands by Local Shell

These examples use OpenSSH and a POSIX remote shell. Choose only the matching local shell, substitute the actual
validated IP, confirmed username, and port, and adjust options to the installed client. Placeholders are not literal
connection values. Only the port defaults to `22`; there is no default username.

Windows PowerShell or PowerShell 7:

```powershell
$serverIp = '<server-ip>'
$sshUser = '<confirmed-user>'
$sshPort = 22
ssh -T -n -p $sshPort -o "HostName=$serverIp" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "${sshUser}@${serverIp}" "printf 'SSH_OK\n' && hostname && whoami"
$sshExitCode = $LASTEXITCODE
```

Windows cmd (execute each line separately, outside a parenthesized block):

```bat
set "SERVER_IP=<server-ip>"
set "SSH_USER=<confirmed-user>"
set "SSH_PORT=22"
ssh -T -n -p %SSH_PORT% -o "HostName=%SERVER_IP%" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "%SSH_USER%@%SERVER_IP%" "printf 'SSH_OK\n' && hostname && whoami"
set "SSH_EXIT_CODE=%ERRORLEVEL%"
```

Linux, macOS, WSL, or Git Bash with a POSIX-compatible local shell:

```sh
server_ip='<server-ip>'
ssh_user='<confirmed-user>'
ssh_port=22
ssh -T -n -p "$ssh_port" -o "HostName=$server_ip" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "${ssh_user}@${server_ip}" "printf 'SSH_OK\n' && hostname && whoami"
ssh_exit_code=$?
```

Capture SSH's exit code immediately, before any other command replaces it. If the execution tool reports only the final
command's status, explicitly return the saved SSH status from the shell invocation as well. Inspect the actual remote
output for the marker; assigning an exit-code variable alone is not verification. If separate tool calls create separate
shells, keep variable assignments and their SSH invocation in the same call or use validated literal arguments.

For a user-specified key, add `-i` with its quoted path, using the current shell's path syntax. Do not assume Windows
paths work in WSL or POSIX paths work in cmd.

### Remote shell differences

Local shell syntax and remote shell syntax are separate choices. The connection examples above target a POSIX remote
shell regardless of the local operating system. When the remote shell is known to differ, replace only the verification
command:

| Remote shell       | Minimal verification command              |
|--------------------|-------------------------------------------|
| POSIX shell        | `printf 'SSH_OK\n' && hostname && whoami` |
| Windows cmd        | `echo SSH_OK && hostname && whoami`       |
| Windows PowerShell | `Write-Output 'SSH_OK'; hostname; whoami` |

Quote the entire remote command as one local argument, adapting escaping if it contains local expansion characters. A
remote command syntax error does not by itself mean authentication failed. If first-time host key acceptance is
unsupported or requires interaction, give the user a native terminal command to establish trust; never bypass
verification with `StrictHostKeyChecking=no`.

The verification uses a short SSH session. It does not leave an interactive terminal or persistent connection open.
Describe the result accordingly.

## One-command Installation Examples

These are user-executed templates for a POSIX remote account. Replace `<server-ip>`, `<port>`, and `<user>` with the
actual values, and adapt the public key path if needed. For all SSH commands below, preserve the explicit target and add
any needed connection options from the entrypoint's connection workflow. Do not add `-n` to installation commands: SSH
must receive the public key on stdin.

Windows PowerShell:

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Windows cmd:

```bat
type "%USERPROFILE%\.ssh\id_ed25519.pub" | ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Linux / macOS / WSL / POSIX-compatible shell, if `ssh-copy-id` is available:

```sh
ssh-copy-id -i "$HOME/.ssh/id_ed25519.pub" -p <port> -o HostName=<server-ip> <user>@<server-ip>
```

Otherwise:

```sh
ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" < "$HOME/.ssh/id_ed25519.pub"
```

The leading newline in the remote append preserves a line boundary if the existing file lacks a trailing newline.
Existing entries remain intact. These simple append commands do not deduplicate keys. `ssh-copy-id` also needs care with
an already installed restricted key: do not use its force option to add an unrestricted copy.

For user verification, prefer one short command, adding the selected identity when needed:

```text
ssh -p <port> -o HostName=<server-ip> -o BatchMode=yes -o ConnectTimeout=10 <user>@<server-ip> "echo SSH_OK"
```

If the user asks about key generation versus displaying a public key, explain the difference directly: `ssh-keygen`
creates a key pair; `Get-Content`, `type`, or `cat` reads an existing public key. In Windows PowerShell 5.1, `-N '""'`
is commonly used to pass an empty passphrase to native `ssh-keygen`; its quoting must not be copied blindly to
PowerShell 7 or POSIX shells. Prefer interactive generation unless the user requests an empty passphrase, then choose
syntax for the actual PowerShell version and native argument-passing mode.
