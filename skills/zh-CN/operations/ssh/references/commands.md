# SSH 命令参考

与 [主技能](../SKILL.md) 配合使用，先确认目标用户名并遵循认证边界。只读取和使用当前环境对应的部分。

## 环境识别命令

按需参考下列命令，不必逐项执行所有探测：

| 当前 Shell                            | 识别环境与 SSH 客户端                                                             | 默认 SSH 目录                                                                               |
|---------------------------------------|-----------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| Windows PowerShell / PowerShell 7     | `$PSVersionTable`；`[System.Environment]::OSVersion`；`Get-Command ssh`；`ssh -V` | Windows 使用 `Join-Path $env:USERPROFILE '.ssh'`；Linux/macOS 使用 `Join-Path $HOME '.ssh'` |
| Windows cmd                           | `ver`；`where ssh`；`ssh -V`                                                      | `%USERPROFILE%\.ssh`                                                                        |
| Linux / macOS POSIX Shell             | `uname -s`；`command -v ssh`；`ssh -V`                                            | `"$HOME/.ssh"`                                                                              |
| WSL                                   | `uname -a`；`command -v ssh`                                                      | 所选发行版内部的 `"$HOME/.ssh"`，与 Windows 独立                                            |
| Git Bash / 其他 Windows 类 Unix Shell | `uname -s`；`command -v ssh`；`ssh -V`                                            | 确认该 Shell 实际使用的 SSH 程序和主目录                                                    |

PowerShell 7 也可运行在 Linux 和 macOS 上。引用规则由 Shell 决定，路径由操作系统决定。执行工具提供 Shell 信息时优先使用；不能仅凭
`$SHELL` 判断当前 Shell。所选客户端不是 OpenSSH 时，先查看其用法并转换连接选项，不直接传入不支持的 OpenSSH 参数。

## 按本地 Shell 选择命令

以下示例使用 OpenSSH，远端为 POSIX Shell。仅选择匹配当前本地 Shell 的示例，填入经过校验的实际
IP、已确认的用户名和端口，并根据客户端能力调整选项。占位符不能直接作为连接参数使用。仅端口默认 `22`，用户名没有默认值。

Windows PowerShell 或 PowerShell 7：

```powershell
$serverIp = '<server-ip>'
$sshUser = '<confirmed-user>'
$sshPort = 22
ssh -T -n -p $sshPort -o "HostName=$serverIp" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "${sshUser}@${serverIp}" "printf 'SSH_OK\n' && hostname && whoami"
$sshExitCode = $LASTEXITCODE
```

Windows cmd，逐行执行，不放在括号块中：

```bat
set "SERVER_IP=<server-ip>"
set "SSH_USER=<confirmed-user>"
set "SSH_PORT=22"
ssh -T -n -p %SSH_PORT% -o "HostName=%SERVER_IP%" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "%SSH_USER%@%SERVER_IP%" "printf 'SSH_OK\n' && hostname && whoami"
set "SSH_EXIT_CODE=%ERRORLEVEL%"
```

Linux、macOS、WSL 或 Git Bash 中兼容 POSIX 的本地 Shell：

```sh
server_ip='<server-ip>'
ssh_user='<confirmed-user>'
ssh_port=22
ssh -T -n -p "$ssh_port" -o "HostName=$server_ip" -o BatchMode=yes -o ConnectTimeout=10 -o ConnectionAttempts=1 -o StrictHostKeyChecking=accept-new -o RemoteCommand=none -o PermitLocalCommand=no -o ClearAllForwardings=yes "${ssh_user}@${server_ip}" "printf 'SSH_OK\n' && hostname && whoami"
ssh_exit_code=$?
```

SSH 执行后立即保存退出码，避免被后续命令覆盖。执行工具仅返回最后一条命令的状态时，还需让本次 Shell 调用显式返回已保存的 SSH
状态。检查实际远程输出是否包含标记；仅给退出码变量赋值不代表验证通过。若每次工具调用都会创建新 Shell，将变量赋值与 SSH
命令放在同一次调用中，或直接使用经过校验的字面量参数。

用户指定密钥时，添加 `-i` 和按当前 Shell 路径语法引用的密钥路径。不假设 Windows 路径可直接用于 WSL，也不假设 POSIX 路径可直接用于
cmd。

### 区分远端 Shell

本地与远端 Shell 的语法分别选择。无论本地操作系统是什么，上述连接示例都以 POSIX 远端 Shell 为目标。已知远端 Shell
不同时，仅替换验证命令：

| 远端 Shell         | 最小验证命令                              |
|--------------------|-------------------------------------------|
| POSIX Shell        | `printf 'SSH_OK\n' && hostname && whoami` |
| Windows cmd        | `echo SSH_OK && hostname && whoami`       |
| Windows PowerShell | `Write-Output 'SSH_OK'; hostname; whoami` |

将整个远程命令作为一个本地参数引用，包含可能被本地展开的字符时适配转义。远程命令语法错误不等于认证失败。客户端不支持首次主机密钥接纳选项，或该步骤需要交互时，给用户原生终端命令建立信任，不使用
`StrictHostKeyChecking=no` 绕过校验。

验证使用短暂 SSH 会话，不保留交互式终端或持久连接，报告时如实说明。

## 一条命令安装公钥

以下模板由用户自行执行，适用于 POSIX 远程账号。将 `<server-ip>`、`<port>`、`<user>` 替换为实际值，必要时调整公钥路径。下列所有
SSH 命令均保持显式目标，并按主技能的连接流程添加所需选项。安装命令不添加 `-n`：SSH 需要从标准输入接收公钥。

Windows PowerShell：

```powershell
Get-Content "$env:USERPROFILE\.ssh\id_ed25519.pub" | ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Windows cmd：

```bat
type "%USERPROFILE%\.ssh\id_ed25519.pub" | ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys"
```

Linux / macOS / WSL / POSIX 兼容 Shell，且存在 `ssh-copy-id` 时：

```sh
ssh-copy-id -i "$HOME/.ssh/id_ed25519.pub" -p <port> -o HostName=<server-ip> <user>@<server-ip>
```

否则：

```sh
ssh -T -p <port> -o HostName=<server-ip> <user>@<server-ip> "mkdir -p ~/.ssh && chmod 700 ~/.ssh && printf '\n' >> ~/.ssh/authorized_keys && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys" < "$HOME/.ssh/id_ed25519.pub"
```

远端追加前先写入换行，确保原文件即使没有末尾换行，也能保持公钥行边界。保留现有条目。这些简单追加命令不去重。使用
`ssh-copy-id` 时，也需注意已安装且带限制的公钥，不使用强制选项追加无限制副本。

提供给用户的验证命令优先保持一条且简短，必要时指定所选密钥：

```text
ssh -p <port> -o HostName=<server-ip> -o BatchMode=yes -o ConnectTimeout=10 <user>@<server-ip> "echo SSH_OK"
```

用户询问生成密钥与显示公钥的区别时，直接说明：`ssh-keygen` 创建密钥对；`Get-Content`、`type` 或 `cat` 读取已有公钥。Windows
PowerShell 5.1 中，常用 `-N '""'` 向原生 `ssh-keygen` 传递空口令；不可将该引用方式直接照搬到 PowerShell 7 或 POSIX
Shell。用户未要求空口令时，优先使用交互式生成；明确要求时，根据实际 PowerShell 版本和原生参数传递模式选择语法。
