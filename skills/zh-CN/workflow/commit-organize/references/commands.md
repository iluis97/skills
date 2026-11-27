# 分组提交命令参考

配合 [主技能](../SKILL.md) 使用。按计划逐组执行，不一次性 `git add -A`。

## 查看与分类

```bash
# 已暂存与未暂存分开看
git status --short
git diff --staged --stat
git diff --stat

# 单个文件的完整差异
git diff -- <file>

# 近期提交风格
git log -n 20 --format='%s'
```

## 按文件分组

```bash
# 只暂存该组的文件
git add <file1> <file2>

# 提交
git commit -m "<提交信息>"
```

## 按 hunk 分组（同一文件属于多个变更单元）

```bash
# 新文件先登记，才能按块暂存
git add -N <new-file>

# 逐块选择：y 暂存 / n 跳过 / s 拆成更小的块 / e 手工编辑 / q 退出
git add -p <file>

# 查看已暂存内容是否就是想要的部分
git diff --staged -- <file>
```

单个 hunk 内混有多个目的时，`e` 手工删除不属于本组的行；无法干净编辑时按主技能说明取舍。

## 撤回误暂存

```bash
# 从暂存区撤回，保留工作区改动
git restore --staged <file>

# 全部撤回重新分组
git restore --staged .
```

## 执行顺序

按计划顺序逐组执行，每组提交后立即校验：

```bash
git add <group-files>
git diff --staged --stat          # 确认范围
git commit -m "<提交信息>"
git show --stat HEAD              # 复核本条提交
```

## 遗漏与残留检查

```bash
# 全部改动都已被提交时应无输出
git status --porcelain

# 逐条核对历史
git log --oneline <base>..HEAD
```

## 排除敏感文件

```bash
# 先确认是否已被跟踪
git ls-files -- <path>

# 不加入暂存；必要时补 .gitignore
echo "<pattern>" >> .gitignore
```

已进入历史的密钥需要专用历史过滤工具处理，不在本技能范围。

## 失败处理

```bash
# 钩子失败：修复后重新 add 并 commit，不使用 --no-verify
git commit -m "<提交信息>"

# 提交信息写错且尚未推送
git commit --amend
```

已推送的提交重写交给提交整理技能，本技能不处理。
