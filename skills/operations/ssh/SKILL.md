---
name: ssh
description: Verify SSH access to a specified server and guide user-executed public key setup when needed.
disable-model-invocation: true
---

# SSH

## Scope

Connect to the server specified by the user and verify access. Report the connection result briefly, for example,
`SSH 连接成功`. If the user has already requested follow-up work, continue with that work after successful verification.
If the user requested only a connection check, finish after reporting the result. Do not quote skill instructions or
explain stopping in terms of this skill's scope.

This skill contains instructions only. Choose and execute native SSH commands appropriate to the available environment;
do not depend on a bundled script or create a connection wrapper.

Use the IP supplied for this connection throughout authentication setup and verification. Do not substitute an IP from
an example, a previous connection, or nearby conversation text. If several IPs could be the intended target, ask which
one to use before connecting.

## Inputs

- Required: server IPv4 or IPv6 address and a user-confirmed login username for that target.
- Optional: port (default `22`), private key path.
- Reuse values explicitly supplied for the current connection. Do not ask the user to repeat them.
- Validate the IP, username, and port before constructing commands. Quote arguments for the actual local shell; do not
  interpolate untrusted text as shell code.

## Confirm the username first

Before generating any target-specific connection, public key installation, or verification command, or attempting to
connect, confirm the login username for the supplied IP.

- If the user explicitly provides the username for this target in the request or has already confirmed it for this same
  target in the conversation, reuse it without asking again. An explicit `user@IP` counts as confirmation.
- If the user provides only an IP and no username has been confirmed for it, ask one short question:
  `这台服务器 <server-ip> 的 SSH 登录用户名是什么？` Wait for the answer before generating commands or connecting.
- Do not default to `root`, infer the remote username from the local account, copy a username from another server, or
  try several common usernames. A previous attempt made with an assumed username does not count as user confirmation.
- If the user corrects the username or says it is different, discard the previous value. Ask for the actual username if
  it remains unknown, then use the confirmed value consistently in every command, including public key installation.

## Detect the environment

1. Identify the operating system, shell, and available execution tools. Distinguish Windows PowerShell, PowerShell 7,
   cmd, POSIX shells, WSL, and containers rather than inferring the shell from the operating system alone.
2. Locate the SSH client using an appropriate command, such as `Get-Command ssh` in PowerShell, `where ssh` in cmd, or
   `command -v ssh` in a POSIX shell. Check client capabilities when relevant.
3. Use the current environment's home directory, path syntax, and quoting. Windows, WSL, and containers can have
   different keys, SSH agents, configuration, and network access. Do not silently switch between them to work around a
   failure.
4. If no usable SSH client or execution tool is available, explain what is missing and provide a suitable next step for
   that environment. Do not install software automatically.

Before constructing connection or public-key setup commands, read the sections matching the local and remote shells
in [references/commands.md](references/commands.md). Use only examples appropriate to the detected environment.

## Connect

1. Reuse existing SSH configuration, ssh-agent, and default identities. Pass an identity path only when the user
   specifies it or available configuration clearly identifies it. Do not read private key contents.
2. Make a noninteractive connection attempt with a bounded timeout. For OpenSSH, use `BatchMode=yes`,
   `ConnectTimeout=10`, and `ConnectionAttempts=1`. Set the requested port and `HostName` explicitly to prevent an SSH
   alias from redirecting the supplied IP. Disable local commands and forwarding for this verification.
3. Execute a minimal remote command that prints a recognizable marker and, where supported, the hostname and username.
   Choose syntax appropriate to the remote shell. Require both a zero SSH exit status and the marker in remote output
   before reporting success.
4. Briefly report the connection result. Continue with follow-up work already requested by the user; otherwise, finish
   after reporting. Include the target, username, or port only when useful to identify the connection.

Capture SSH's exit status immediately and inspect the actual verification marker; if the tool reports only the final
command status, explicitly return the saved SSH status. A remote command syntax error does not itself mean
authentication failed. If initial host-key acceptance needs interaction, provide a native terminal command; never bypass
verification with `StrictHostKeyChecking=no`. Verification is a short session, not a persistent connection.

## First-time authentication

If the check fails, read the SSH error before choosing the next step:

- Timeout, refused connection, or routing failure: report the connection problem. Do not treat it as an authentication
  failure.
- Changed host key: stop and report the mismatch. Do not delete `known_hosts` entries or disable host key verification.
- An encrypted key requiring its passphrase: reuse the key and have the user unlock it with `ssh-add` in their terminal,
  then retry the check. Do not replace it with an unencrypted key.
- Authentication failure without a usable key: explain that public key setup may be needed and provide the user-executed
  setup steps below. Do not start a password prompt or repeatedly retry authentication.

## User-executed public key setup

Give the user concise, ready-to-run commands tailored to their local operating system and shell and the remote account.
Fill in the IP supplied for the current target, confirmed login username, port, and appropriate paths. These are
instructions for the user to execute themselves: do not generate keys, install public keys, or change authentication
configuration on their behalf.

Keep the normal response to two commands when a key pair already exists: one public key installation command, then one
verification command. Add key generation only when needed. Show only the detected environment's commands, with actual
values filled in. Do not make the user display and copy the public key, open a remote editor, or run separate permission
commands when a single installation command is suitable.

1. Check whether the key files exist without reading the private key. Reuse an existing pair and explicitly say key
   generation is unnecessary. If neither file exists, ensure the local SSH directory exists and give an interactive
   `ssh-keygen -t ed25519 -f <key-path>` command. Never overwrite a key; if an overwrite prompt appears, tell the user
   to answer `n`. If only the public key is missing, provide `ssh-keygen -y` with shell-appropriate output redirection
   to recover it.
2. Prefer a single `ssh-copy-id` command where available and suitable. Otherwise, for a POSIX remote account, use one
   local public-key pipe into SSH as shown in [references/commands.md](references/commands.md#one-command-installation-examples). Keep remote
   directory creation, permissions, and installation in that command. Do not assume `ssh-copy-id` exists on Windows or
   use POSIX authorization paths on a Windows SSH server.
3. The simple pipe appends a key and is intended for one-time setup. State briefly that it should be executed once. If
   the key may already be installed, especially with authorization options, do not recommend appending an unrestricted
   duplicate; inspect the authorization situation or offer a suitable deduplicating method instead. Do not turn the
   normal first-time setup into a long manual editing procedure.
4. Tell the user to enter the server password at the terminal prompt. Never request credentials in chat or embed them in
   commands, environment variables, or files.
5. Include a noninteractive verification command for the same target. Mention unlocking an encrypted key with the
   appropriate SSH agent only when relevant.

Report that the connection has not yet succeeded while setup is pending. Once the user confirms setup is complete, retry
the connection check. Do not claim that the selected public key works merely because another configured identity
authenticated successfully.

## Boundaries

- Connection verification may record a new server host key in `known_hosts` using `StrictHostKeyChecking=accept-new`
  when supported.
- Keep private keys and credentials local. Do not print, upload, or copy private key contents.
- Connection verification itself must not change SSH server settings or restart services. After successful verification,
  perform further remote operations only within the user's requested scope.
