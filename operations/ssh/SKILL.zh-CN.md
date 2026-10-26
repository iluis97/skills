---
name: ssh
description: 用户提供 IP 或要求连接服务器时，通过 SSH 连接远程服务器。生成或执行命令前，先确认目标服务器的登录用户名，不默认使用 root。根据当前操作系统、Shell 和 SSH 客户端选择命令，复用现有认证并验证访问。需要配置公钥时，提供由用户自行执行的步骤。默认端口为 22。适用于连接服务器、SSH 连接、配置免密登录等请求。
---

# SSH

## 1. 适用范围

连接用户指定的服务器并验证访问。报告连接结果后结束，不在本技能中执行额外的远程操作。

本技能仅包含说明。根据可用环境选择并执行原生 SSH 命令，不依赖配套脚本，也不创建连接包装脚本。

认证配置和验证始终使用用户本次指定的 IP。不替换为示例、上次连接或附近对话中的其他 IP。存在多个可能的目标 IP 时，先确认要连接哪一个。

## 2. 输入

- 必填：服务器 IPv4 或 IPv6 地址，以及用户为该目标确认的登录用户名。
- 可选：端口，默认 `22`；私钥路径。
- 复用用户为当前连接明确提供的值，不要求重复提供。
- 构造命令前校验 IP、用户名和端口；按实际本地 Shell 的规则引用参数，不将不可信文本直接拼接为 Shell 代码。

## 3. 前置确认用户名

生成任何针对目标服务器的连接、公钥安装或验证命令，以及尝试连接之前，先确认该 IP 对应的登录用户名。

- 用户在请求中明确提供了该目标的用户名，或已在当前对话中为同一目标确认过用户名时，直接复用，不重复询问。明确的 `user@IP` 也视为已确认。
- 用户只提供 IP，且尚未为它确认用户名时，仅简短询问：`这台服务器 <server-ip> 的 SSH 登录用户名是什么？` 收到回答后再生成命令或连接。
- 不默认使用 `root`，不从本地账号推断远程用户名，不沿用其他服务器的用户名，也不轮流尝试常见用户名。此前使用猜测用户名发起的连接不算用户确认。
- 用户纠正用户名或说明用户名不同后，弃用旧值。实际用户名仍未知时先询问，随后所有命令，包括公钥安装命令，都统一使用确认后的值。

## 4. 识别运行环境

1. 确认操作系统、Shell 和可用执行工具。区分 Windows PowerShell、PowerShell 7、cmd、POSIX Shell、WSL 和容器，不仅凭操作系统推断 Shell。
2. 使用适合当前环境的命令定位 SSH 客户端，例如 PowerShell 的 `Get-Command ssh`、cmd 的 `where ssh`、POSIX Shell 的 `command -v ssh`。必要时检查客户端能力。
3. 使用当前环境的主目录、路径语法和引用规则。Windows、WSL 和容器中的密钥、SSH agent、配置及网络访问可能不同，不为绕过失败而擅自切换环境。
4. 缺少可用 SSH 客户端或执行工具时，说明缺失项，并给出适合该环境的下一步，不自动安装软件。

按需参考下列命令，不必逐项执行所有探测：

| 当前 Shell | 识别环境与 SSH 客户端 | 默认 SSH 目录 |
| --- | --- | --- |
| Windows PowerShell / PowerShell 7 | `$PSVersionTable`；`[System.Environment]::OSVersion`；`Get-Command ssh`；`ssh -V` | Windows 使用 `Join-Path $env:USERPROFILE '.ssh'`；Linux/macOS 使用 `Join-Path $HOME '.ssh'` |
| Windows cmd | `ver`；`where ssh`；`ssh -V` | `%USERPROFILE%\.ssh` |
| Linux / macOS POSIX Shell | `uname -s`；`command -v ssh`；`ssh -V` | `"$HOME/.ssh"` |
| WSL | `uname -a`；`command -v ssh` | 所选发行版内部的 `"$HOME/.ssh"`，与 Windows 独立 |
| Git Bash / 其他 Windows 类 Unix Shell | `uname -s`；`command -v ssh`；`ssh -V` | 确认该 Shell 实际使用的 SSH 程序和主目录 |

PowerShell 7 也可运行在 Linux 和 macOS 上。引用规则由 Shell 决定，路径由操作系统决定。执行工具提供 Shell 信息时优先使用；不能仅凭 `$SHELL` 判断当前 Shell。所选客户端不是 OpenSSH 时，先查看其用法并转换连接选项，不直接传入不支持的 OpenSSH 参数。

## 5. 执行连接

1. 先完成用户名确认，再复用已有 SSH 配置、ssh-agent 和默认身份。仅在用户指定密钥，或现有配置明确标识密钥时传入身份文件路径。不读取私钥内容。
2. 发起有超时限制的非交互连接。OpenSSH 使用 `BatchMode=yes`、`ConnectTimeout=10` 和 `ConnectionAttempts=1`。显式设置目标端口与 `HostName`，避免 SSH 别名将指定 IP 重定向到其他服务器。验证时禁用本地命令和转发。
3. 执行最小远程命令，输出可识别的标记，并在支持时输出主机名和用户名。命令语法适配远端 Shell。只有 SSH 退出码为零，且远程输出包含验证标记，才能报告成功。
4. 成功后报告实际目标、用户名、端口，以及认证和远程命令执行已通过验证，然后结束。

### 按本地 Shell 选择命令

以下示例使用 OpenSSH，远端为 POSIX Shell。仅选择匹配当前本地 Shell 的示例，填入经过校验的实际 IP、已确认的用户名和端口，并根据客户端能力调整选项。占位符不能直接作为连接参数使用。仅端口默认 `22`，用户名没有默认值。

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

SSH 执行后立即保存退出码，避免被后续命令覆盖。执行工具仅返回最后一条命令的状态时，还需让本次 Shell 调用显式返回已保存的 SSH 状态。检查实际远程输出是否包含标记；仅给退出码变量赋值不代表验证通过。若每次工具调用都会创建新 Shell，将变量赋值与 SSH 命令放在同一次调用中，或直接使用经过校验的字面量参数。

用户指定密钥时，添加 `-i` 和按当前 Shell 路径语法引用的密钥路径。不假设 Windows 路径可直接用于 WSL，也不假设 POSIX 路径可直接用于 cmd。

### 区分远端 Shell

本地与远端 Shell 的语法分别选择。无论本地操作系统是什么，上述连接示例都以 POSIX 远端 Shell 为目标。已知远端 Shell 不同时，仅替换验证命令：

| 远端 Shell | 最小验证命令 |
| --- | --- |
| POSIX Shell | `printf 'SSH_OK\n' && hostname && whoami` |
| Windows cmd | `echo SSH_OK && hostname && whoami` |
| Windows PowerShell | `Write-Output 'SSH_OK'; hostname; whoami` |

将整个远程命令作为一个本地参数引用，包含可能被本地展开的字符时适配转义。远程命令语法错误不等于认证失败。客户端不支持首次主机密钥接纳选项，或该步骤需要交互时，给用户原生终端命令建立信任，不使用 `StrictHostKeyChecking=no` 绕过校验。

验证使用短暂 SSH 会话，不保留交互式终端或持久连接，报告时如实说明。

## 6. 处理首次认证与连接失败

检查失败时，先阅读 SSH 错误，再选择下一步：

- 超时、连接被拒绝或路由失败：报告连接问题，不归因于认证失败。
- 主机密钥变化：停止并说明不匹配，不删除 `known_hosts` 记录，不关闭主机密钥校验。
- 加密私钥需要口令：复用该密钥，让用户在自己的终端通过 `ssh-add` 解锁后重试，不替换为无口令密钥。
- 没有可用密钥导致认证失败：说明可能需要配置公钥，并提供下述手动步骤。不启动密码提示，不反复重试认证。

## 7. 用户自行配置公钥

提供适合用户本地操作系统、Shell 和远程账号的简短、可直接执行的命令。生成命令前完成用户名确认，填入实际 IP、已确认的用户名、端口和适用路径。这些步骤由用户自行执行；不代替用户生成密钥、安装公钥或修改认证配置。

已有密钥对时，通常仅给两条命令：一条安装公钥，一条验证连接。仅在需要时补充生成密钥。只展示适合已识别环境且填入实际参数的命令。单条命令能够完成安装时，不要求用户显示并复制公钥、打开远程编辑器或单独执行权限命令。

1. 检查密钥文件是否存在，不读取私钥。复用现有密钥对，并明确说明无需重新生成。两个文件都不存在时，确保本地 SSH 目录存在，并给出交互式 `ssh-keygen -t ed25519 -f <key-path>` 命令。不覆盖密钥；出现覆盖提示时，告诉用户回答 `n`。仅缺公钥时，提供 `ssh-keygen -y`，并使用适合当前 Shell 的输出重定向恢复公钥。
2. 存在且适用时，优先使用一条 `ssh-copy-id` 命令。否则，对 POSIX 远程账号，按下述示例将本地公钥通过管道传给 SSH；远端目录创建、权限设置和安装包含在同一条命令内。不假设 Windows 自带 `ssh-copy-id`，也不对 Windows SSH 服务器套用 POSIX 授权路径。
3. 简单管道会追加公钥，适用于首次配置，简短说明仅执行一次。密钥可能已安装，尤其存在授权选项时，不建议追加无限制的重复公钥；先检查授权情况，或给出适当的去重方法。不将普通首次配置变成长篇手动编辑流程。
4. 告诉用户在终端提示时输入服务器密码。不在聊天中索要凭据，不将凭据写入命令、环境变量或文件。
5. 附上同一目标的非交互验证命令。仅在相关时提示通过适用的 SSH agent 解锁加密密钥。

### 一条命令安装公钥

以下模板由用户自行执行，适用于 POSIX 远程账号。将 `<server-ip>`、`<port>`、`<user>` 替换为实际值，必要时调整公钥路径。下列所有 SSH 命令均保持显式目标，并按连接流程添加所需选项。安装命令不添加 `-n`：SSH 需要从标准输入接收公钥。

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

远端追加前先写入换行，确保原文件即使没有末尾换行，也能保持公钥行边界。保留现有条目。这些简单追加命令不去重。使用 `ssh-copy-id` 时，也需注意已安装且带限制的公钥，不使用强制选项追加无限制副本。

提供给用户的验证命令优先保持一条且简短，必要时指定所选密钥：

```text
ssh -p <port> -o HostName=<server-ip> -o BatchMode=yes -o ConnectTimeout=10 <user>@<server-ip> "echo SSH_OK"
```

用户询问生成密钥与显示公钥的区别时，直接说明：`ssh-keygen` 创建密钥对；`Get-Content`、`type` 或 `cat` 读取已有公钥。Windows PowerShell 5.1 中，常用 `-N '""'` 向原生 `ssh-keygen` 传递空口令；不可将该引用方式直接照搬到 PowerShell 7 或 POSIX Shell。用户未要求空口令时，优先使用交互式生成；明确要求时，根据实际 PowerShell 版本和原生参数传递模式选择语法。

配置待完成时，如实说明连接尚未成功。用户确认完成后，再次执行连接验证。不能仅因其他已配置身份认证成功，就声称所选公钥已验证可用。

## 8. 操作边界

- 客户端支持时，连接验证可通过 `StrictHostKeyChecking=accept-new` 将新服务器主机密钥记录到 `known_hosts`。密钥生成和公钥安装始终由用户执行。
- 私钥与凭据保留在本地，不打印、上传或复制私钥内容。
- 保留连接错误信息，区分认证失败与远程验证命令失败。
- 不修改 SSH 服务端设置，不重启服务，不执行无关操作。
