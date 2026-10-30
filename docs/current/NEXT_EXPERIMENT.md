# 下一步：一次注册空间读出接续，保留Full原队列（2026-10-30）

新空间头接续入口已发布并完成本地17项检查，尚未收到服务器注册、profile或正式更新回执。不能写成已入队。这次执行下面一次即可，之后不再逐phase手动接续。Full无需停止、重装或重新profile；已有正常结束回执时可以直接交接。新入口不是旧Full bootstrap，也不是A0修复重跑。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
REL=5f2958ae8b7d3ac79901eb0261239d89e82b461e
TOOL="$ROOT/execution/a_spatial_followup_$REL.py"
mkdir -p "$ROOT/execution"

if [ ! -f "$TOOL" ]; then
  curl -fL --connect-timeout 10 --max-time 60 \
    "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$REL/scripts/queue_post_m2_a_spatial_20261030.py" \
    -o "$TOOL.part"
  mv -n "$TOOL.part" "$TOOL"
fi

/home/jovyan/miniconda3/envs/remote_sensing/bin/python -u -B \
  "$TOOL" start --commit "$REL"
)
```

FOLLOWUP_DISPATCHED_NOT_TRAINING_PROOF只证明后台接续程序已派发。实际等待状态为WAITING_FULL_NORMAL_COMPLETION或WAITING_FULL_WORKERS_TO_RELEASE；取得正常回执与锁、确认两卡释放后自动profile→各2k训练→校准→原screen→条件outer。若Full已收尾，会直接启动后续。正常交接不等Full上传。

新日志：ROOT/records/post_m2_a_spatial_followup_20261030_r1/followup.log；当前小状态为同目录state.json。只读查询使用同一个固定入口的status动作：

```bash
/home/jovyan/miniconda3/envs/remote_sensing/bin/python -B \
  /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/execution/a_spatial_followup_5f2958ae8b7d3ac79901eb0261239d89e82b461e.py status
```

原A0完成且已归档，不重跑；原Full d15最后19:38:20有Q2/3000与G1/1100真实更新，继续现有控制器。新空间头各4步粗测、正式各2k/seed42，沿已准备数据/权重，常驻复用骨干和拟合数组；正式预算不变。已有started/注册/失败不自动重试；工程失败只处理本入口拥有的工作进程，其他GPU进程不触碰。

接续完成先释放GPU，再归档并尝试上传小结果。没有认证时UPLOAD_PENDING，仅补传现成文件；不为上传重训或推理。后续读取Full与空间完整配对结果按[阶段复盘](../protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)判断。A1/A2、C/P/E/F与频率仍是各有前置的候选，未排队；M2清理暂缓，封存集不开。

[来源/检查/停止和保留边界](../experiments/POST_M2_A_SPATIAL_FOLLOWUP_20261030.md)。
