# 命令与恢复预案

配合 [主技能](../SKILL.md) 使用。改写历史前务必完成备份与树哈希记录。

## 准备

```bash
# 工作区必须干净
git status --short

# 备份当前分支
git branch backup/$(git branch --show-current)-$(date +%Y%m%d%H%M)

# 记录改写前的树哈希
ORIGINAL_TREE=$(git rev-parse HEAD^{tree})
echo $ORIGINAL_TREE
```

## 拆分一条提交

```bash
# 退回上一次提交，保留全部改动在暂存区
git reset --soft HEAD~1

# 或退回最近 3 条，重新组织
git reset --soft HEAD~3

# 按代码块挑选暂存（y 暂存 / n 跳过 / s 拆块 / e 手工编辑）
git add -p

# 新文件先登记再部分暂存
git add -N <new-file>
git add -p <new-file>

# 按单元提交
git commit -m "<第一条提交信息>"
git add -p
git commit -m "<第二条提交信息>"
```

`add -p` 无法在单个 hunk 内拆分时用 `e` 手工调整，或先提交整个文件再在后续提交中调整。

## 合并多条提交

```bash
# 交互式 rebase，把后续提交标记为 squash（合并并编辑信息）或 fixup（合并并丢弃信息）
git rebase -i HEAD~5

# 先建 fixup 提交，再自动合并
git commit --fixup=<target-sha>
git rebase -i --autosquash HEAD~5
```

净变更为零的 commit/revert：在 rebase 列表中删除这两条；若影响面广，用 `git rebase --onto` 跳过。

## 重排与更换基线

```bash
# rebase -i 中直接调整行顺序；先删后加可能冲突，必要时拆成两步
git rebase -i HEAD~5

# 把当前分支的提交移到新基线上
git rebase --onto <new-base> <old-base> <branch>
```

## 改写提交信息

```bash
# 最近一条
git commit --amend

# 历史中的某条
git rebase -i HEAD~5   # 该行改为 reword
```

## 冲突与中断

```bash
# 解决冲突后继续
git add <file>
git rebase --continue

# 放弃本次 rebase，回到开始前
git rebase --abort
```

冲突涉及语义取舍时停下询问，不按“他们的/我们的”机械选择。

## 失败恢复

```bash
# 回到备份分支
git reset --hard backup/<branch>-<time>

# 找回 rebase 前的状态
git reflog
git reset --hard HEAD@{<n>}
```

备份分支在用户确认交付后再删除。

## 特殊文件

```bash
# 仅大小写重命名（macOS 等不区分大小写的文件系统）
git mv --force <OldName> <NewName>

# 换行符导致整文件 diff：先统一属性，再重新拆分
git diff --ignore-all-space
```

子模块指针变化单独作为一个提交。

## 密钥与大文件

发现密钥、凭证或大文件进入历史时停止改写，说明风险并建议使用专用历史过滤工具；密钥需同时作废并轮换。改写历史不等于安全处理。

## 验证

```bash
# 内容必须与改写前完全一致
git rev-parse HEAD^{tree}
git diff backup/<branch>-<time> --stat

# 检查签名与 tag
git log --show-signature -n <n>
git tag --contains <rewritten-commit>
```

签名失效时需重新签名（`git rebase --exec 'git commit --amend --no-edit -S'`），由用户确认后再推送。
