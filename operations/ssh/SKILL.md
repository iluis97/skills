---
name: ssh
description: Connect to a remote server over SSH when the user provides an IP or requests a connection. Confirm the target's login username before generating or executing commands; do not assume root. Adapt commands to the current operating system, shell, and SSH client; reuse existing authentication and verify access. If public key setup is needed, give the user instructions to execute themselves. Default port is 22. 中文触发：连接服务器、SSH 连接、配置免密登录。
---

# SSH

## Scope

Connect to the server specified by the user and verify access. Report the connection result briefly, for example, `SSH 连接成功`. If the user has already requested follow-up work, continue with that work after successful verification. If the user requested only a connection check, finish after reporting the result. Do not quote skill instructions or explain stopping in terms of this skill's scope.

This skill contains instructions only. Choose and execute native SSH commands appropriate to the available environment; do not depend on a bundled script or create a connection wrapper.

Use the IP supplied for this connection throughout authentication setup and verification. Do not substitute an IP from an example, a previous connection, or nearby conversation text. If several IPs could be the intended target, ask which one to use before connecting.

## Inputs

- Required: server IPv4 or IPv6 address and a user-confirmed login username for that target.
- Optional: port (default `22`), private key path.
- Reuse values explicitly supplied for the current connection. Do not ask the user to repeat them.
- Validate the IP, username, and port before constructing commands. Quote arguments for the actual local shell; do not interpolate untrusted text as shell code.

## Confirm the username first

Before generating any target-specific connection, public key installation, or verification command, or attempting to connect, confirm the login username for the supplied IP.

- If the user explicitly provides the username for this target in the request or has already confirmed it for this same target in the conversation, reuse it without asking again. An explicit `user@IP` counts as confirmation.
- If the user provides only an IP and no username has been confirmed for it, ask one short question: `这台服务器 <server-ip> 的 SSH 登录用户名是什么？` Wait for the answer before generating commands or connecting.
- Do not default to `root`, infer the remote username from the local account, copy a username from another server, or try several common usernames. A previous attempt made with an assumed username does not count as user confirmation.
- If the user corrects the username or says it is different, discard the previous value. Ask for the actual username if it remains unknown, then use the confirmed value consistently in every command, including public key installation.

## Detect the environment

1. Identify the operating system, shell, and available execution tools. Distinguish Windows PowerShell, PowerShell 7, cmd, POSIX shells, WSL, and containers rather than inferring the shell from the operating system alone.
2. Locate the SSH client using an appropriate command, such as `Get-Command ssh` in PowerShell, `where ssh` in cmd, or `command -v ssh` in a POSIX shell. Check client capabilities when relevant.
3. Use the current environment's home directory, path syntax, and quoting. Windows, WSL, and containers can have different keys, SSH agents, configuration, and network access. Do not silently switch between them to work around a failure.
4. If no usable SSH client or execution tool is available, explain what is missing and provide a suitable next step for that environment. Do not install software automatically.

Use these commands as environment-specific hints, not as a reason to run every probe:

| Current shell | Identify environment and SSH client | Default SSH directory |
| --- | --- | --- |
| Windows PowerShell / PowerShell 7 | `$PSVersionTable`; `[System.Environment]::OSVersion`; `Get-Command ssh`; `ssh -V` | On Windows, `Join-Path $env:USERPROFILE '.ssh'`; on Linux/macOS, `Join-Path $HOME '.ssh'` |
| Windows cmd | `ver`; `where ssh`; `ssh -V` | `%USERPROFILE%\.ssh` |
| Linux / macOS POSIX shell | `uname -s`; `command -v ssh`; `ssh -V` | `"$HOME/.ssh"` |
| WSL | `uname -a`; `command -v ssh` | `"$HOME/.ssh"` inside the selected distribution, independently of Windows |
| Git Bash / other Unix-like Windows shell | `uname -s`; `command -v ssh`; `ssh -V` | Determine which SSH binary and home directory that shell actually uses |

PowerShell 7 also runs on Linux and macOS. Choose quoting by shell and paths by operating system. Use the execution tool's shell metadata when available; `$SHELL` alone does not reliably identify the active shell. If the selected client is not OpenSSH, inspect its usage and translate the connection options instead of passing unsupported OpenSSH flags.

## Connect

1. Complete username confirmation first. Then reuse existing SSH configuration, ssh-agent, and default identities. Pass an identity path only when the user specifies it or available configuration clearly identifies it. Do not read private key contents.
2. Make a noninteractive connection attempt with a bounded timeout. For OpenSSH, use `BatchMode=yes`, `ConnectTimeout=10`, and `ConnectionAttempts=1`. Set the requested port and `HostName` explicitly to prevent an SSH alias from redirecting the supplied IP. Disable local commands and forwarding for this verification.
3. Execute a minimal remote command that prints a recognizable marker and, where supported, the hostname and username. Choose syntax appropriate to the remote shell. Require both a zero SSH exit status and the marker in remote output before reporting success.
4. On success, briefly report that the SSH connection succeeded. Include the target, username, or port only when useful to identify the verified connection. Continue with any follow-up work already requested by the user; otherwise, finish after reporting the result.

### Commands by local shell

These examples use OpenSSH and a POSIX remote shell. Choose only the matching local shell, substitute the actual validated IP, confirmed username, and port, and adjust options to the installed client. Placeholders are not literal connection values. Only the port defaults to `22`; there is no default username.

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

Capture SSH's exit code immediately, before any other command replaces it. If the execution tool reports only the final command's status, explicitly return the saved SSH status from the shell invocation as well. Inspect the actual remote output for the marker; assigning an exit-code variable alone is not verification. If separate tool calls create separate shells, keep variable assignments and their SSH invocation in the same call or use validated literal arguments.

For a user-specified key, add `-i` with its quoted path, using the current shell's path syntax. Do not assume Windows paths work in WSL or POSIX paths work in cmd.

### Remote shell differences

Local shell syntax and remote shell syntax are separate choices. The connection examples above target a POSIX remote shell regardless of the local operating system. When the remote shell is known to differ, replace only the verification command:

| Remote shell | Minimal verification command |
| --- | --- |
| POSIX shell | `printf 'SSH_OK\n' && hostname && whoami` |
| Windows cmd | `echo SSH_OK && hostname && whoami` |
| Windows PowerShell | `Write-Output 'SSH_OK'; hostname; whoami` |

Quote the entire remote command as one local argument, adapting escaping if it contains local expansion characters. A remote command syntax error does not by itself mean authentication failed. If first-time host key acceptance is unsupported or requires interaction, give the user a native terminal command to establish trust; never bypass verification with `StrictHostKeyChecking=no`.

The verification uses a short SSH session. It does not leave an interactive terminal or persistent connection open. Describe the result accordingly.

## First-time authentication

If the check fails, read the SSH error before choosing the next step:

- Timeout, refused connection, or routing failure: report the connection problem. Do not treat it as an authentication failure.
- Changed host key: stop and report the mismatch. Do not delete `known_hosts` entries or disable host key verification.
- An encrypted key requiring its passphrase: reuse the key and have the user unlock it with `ssh-add` in their terminal, then retry the check. Do not replace it with an unencrypted key.
- Authentication failure without a usable key: explain that public key setup may be needed and provide the manual steps below. Do not start a password prompt or repeatedly retry authentication.

## User-executed public key setup

Give the user concise, ready-to-run commands tailored to their local operating system and shell and the remote account. Complete username confirmation before generating these commands. Fill in the actual IP, confirmed username, port, and appropriate paths. These are instructions for the user to execute themselves: do not generate keys, install public keys, or change authentication configuration on their behalf.

Keep the normal response to two commands when a key pair already exists: one public key installation command, then one verification command. Add key generation only when needed. Show only the detected environment's commands, with actual values filled in. Do not make the user display and copy the public key, open a remote editor, or run separate permission commands when a single installation command is suitable.

1. Check whether the key files exist without reading the private key. Reuse an existing pair and explicitly say key generation is unnecessary. If neither file exists, ensure the local SSH directory exists and give an interactive `ssh-keygen -t ed25519 -f <key-path>` command. Never overwrite a key; if an overwrite prompt appears, tell the user to answer `n`. If only the public key is missing, provide `ssh-keygen -y` with shell-appropriate output redirection to recover it.
2. Prefer a single `ssh-copy-id` command where available and suitable. Otherwise, for a POSIX remote account, use one local public-key pipe into SSH as shown below. Keep remote directory creation, permissions, and installation in that command. Do not assume `ssh-copy-id` exists on Windows or use POSIX authorization paths on a Windows SSH server.
3. The simple pipe appends a key and is intended for one-time setup. State briefly that it should be executed once. If the key may already be installed, especially with authorization options, do not recommend appending an unrestricted duplicate; inspect the authorization situation or offer a suitable deduplicating method instead. Do not turn the normal first-time setup into a long manual editing procedure.
4. Tell the user to enter the server password at the terminal prompt. Never request credentials in chat or embed them in commands, environment variables, or files.
5. Include a noninteractive verification command for the same target. Mention unlocking an encrypted key with the appropriate SSH agent only when relevant.

### One-command installation examples

These are user-executed templates for a POSIX remote account. Replace `<server-ip>`, `<port>`, and `<user>` with the actual values, and adapt the public key path if needed. For all SSH commands below, preserve the explicit target and add any needed connection options from the connection workflow. Do not add `-n` to installation commands: SSH must receive the public key on stdin.

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

The leading newline in the remote append preserves a line boundary if the existing file lacks a trailing newline. Existing entries remain intact. These simple append commands do not deduplicate keys. `ssh-copy-id` also needs care with an already installed restricted key: do not use its force option to add an unrestricted copy.

For user verification, prefer one short command, adding the selected identity when needed:

```text
ssh -p <port> -o HostName=<server-ip> -o BatchMode=yes -o ConnectTimeout=10 <user>@<server-ip> "echo SSH_OK"
```

If the user asks about key generation versus displaying a public key, explain the difference directly: `ssh-keygen` creates a key pair; `Get-Content`, `type`, or `cat` reads an existing public key. In Windows PowerShell 5.1, `-N '""'` is commonly used to pass an empty passphrase to native `ssh-keygen`; its quoting must not be copied blindly to PowerShell 7 or POSIX shells. Prefer interactive generation unless the user requests an empty passphrase, then choose syntax for the actual PowerShell version and native argument-passing mode.

Report that the connection has not yet succeeded while setup is pending. Once the user confirms setup is complete, retry the connection check. Do not claim that the selected public key works merely because another configured identity authenticated successfully.

## Boundaries

- Connection verification may record a new server host key in `known_hosts` using `StrictHostKeyChecking=accept-new` when supported. Key creation and public key installation are always user-executed steps.
- Keep private keys and credentials local. Do not print, upload, or copy private key contents.
- Keep connection errors visible and distinguish failed authentication from a failed remote verification command.
- Connection verification itself must not change SSH server settings or restart services. After successful verification, perform further remote operations only within the user's requested scope.
