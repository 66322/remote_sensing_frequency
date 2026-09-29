# D21 后多方向实验：服务器执行说明

状态：代码与本地 CPU 检查已准备；**服务器数据/锚点/吞吐与正式训练尚未验证或启动**。全部新设置是重写版建议，结果只能在运行、归档及整数核验后报告为开发证据。计划与对照定义见[多方向方案](POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)。

## 范围与资源

- 物理 GPU0、GPU1，各一个进程；主计划 A/B/C/D 共42项、576k新优化更新，均为 seed42。E 的8项完整备用块仅在准备阶段的实测训练与训练 tile 推算的开发评价合计不足24小时、且未查看新开发准确率时纳入。
- 执行器先对最重的 D 路径比较物理微批 `2/4/8/16`，有效批次始终16；再对 A 冻结/解冻、B、C 固定/学习前端、D 六条路径各做20步短测并在训练 tile 上跑全图评价。记录 GPU 利用率、功率、设备占用、PyTorch allocated/reserved 峰值、进程 RSS 与主机可用内存。正式全组统一采用被选中的微批，精度为 FP32。
- 25 GiB 空闲磁盘、20 GiB 可用主机内存、70 GiB PyTorch 峰值是**启动保护阈值**，不是宣称实验实际消耗；服务器实测值存于预检、短测及遥测文件。长队列在每项前复查磁盘、内存、GPU UUID 和空闲状态。
- 吞吐估算在服务器短测后才有值；原 D21 F2 的六步计时不能推算本次时长。若服务器全部范围预计不足24小时，应明确报告并另立有研究问题的任务，不能用空转或追加随机种子凑时间。

## 数据与下载边界

只使用已有 Potsdam、Vaihingen、D18 DINO 源码和权重、D21 seed42 最终检查点。准备命令校验路径、哈希、环境、模型及 Test6 隔离；不会下载、安装或重建环境。缺项时保存错误和明确路径，先单独准备，再执行短测。服务器只已知 GitHub 和 Hugging Face 可直接尝试访问；需要其他来源时，可单独规划 Colab → Hugging Face 中转及 SHA256 核对。

Potsdam 训练 Train16、开发 Val2（主分数 NoBoundary fg5 mIoU）；Vaihingen 训练12块、开发同镶嵌图17块（主分数 FullGT fg5 mIoU）。Test6 与独立 final 不加载。所有 checkpoint 固定最终步，没有以开发集挑选中途权重。每 tile 存 int64 `6×6` 与逐类原始计数，预测和大 checkpoint 留服务器，紧凑 JSON/CSV 可以同步 GitHub。

## 服务器上的三个阶段

在已有服务器仓库 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`，先激活现有 `remote_sensing` 环境、拉取本分支。运行以下**准备阶段**；只做 CPU/文件和模型绑定核对，不启动训练：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_day_queue.sh --prepare-only
```

准备通过后执行**有界 GPU 短测**。它会使用物理 GPU0/1 的训练 tile，比较微批，记录吞吐并在 `records/post_d21_day_queue_20260929/scope.json` 冻结42或50项；不会启动正式队列，也不加载开发标签：

```bash
bash scripts/run_rebuild_v1_day_queue.sh --profile-only
cat records/post_d21_day_queue_20260929/scope.json
```

检查准备和短测结果后执行**正式队列**。命令启动已冻结范围的全任务训练区 smoke，然后按 A→B→C→D→E 自动推进；成功组之间无需逐组确认。建议在服务器持久会话中执行或用下面的后台方式：

```bash
nohup bash scripts/run_rebuild_v1_day_queue.sh --launch \
  > records/post_d21_day_queue_20260929/launcher.log 2>&1 < /dev/null &
echo $!
```

查看 `status.tsv`、`progress.json`、对应任务 `.log` 与 `queue_summary.json`。准备/短测/训练三阶段分开，是为了在新模型真实耗时与显存未知时避免直接排长队。代码和输入绑定在 `plan.json`，训练和评价可按原任务断点续跑；已有绑定变化会停止，不会覆盖旧证据。

需在当前任务结束后停止新任务时，可创建 `records/post_d21_day_queue_20260929/STOP`；这不强杀正在执行的训练。继续前将 STOP 移走并重跑 `--launch`。技术故障或数据不一致立即停止队列；某个方法效果差不会取消独立方向。已授权的两卡长时运行不用逐组再次确认。

## 归档与判定

服务器生成 `records/post_d21_day_compact_20260929/`：范围、遥测摘要、逐任务训练与评价摘要、原始整数计数重算、分方向配对差值与队列状态。完整预测、权重保留服务器；只按显式路径提交紧凑记录，不使用 `git add .`。A 报告继续训练对照；B 用预设 +0.2pp 宏平均及 clean/家族/逐 tile 保护门槛，并核对合成整幅辅助零填充与 D21 R0 预测完全相同；C/D 报告对应 LR 任务内的恢复目标和交互，不跨任务起点拼排行榜。合成零填充的等价性不代表真实缺失检测，单种子开发结果不代表最终论文确认。
