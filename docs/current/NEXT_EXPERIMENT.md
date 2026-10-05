# 下一步：上传两个已完成目录，回读原件后分析

最后服务器观测（用户2026-10-06回传）：queue_status观测时间2026-10-05T23:27:15.831648+08:00，诊断后继DIAGNOSTICS_COMPLETE_AWAITING_REVIEW，PID3591245 LIVE=False；E0/MASKS COMPLETE，E1_A0/B1及E2_N1-2/N2-0/N2-3五项全部COMPLETE，worker均LIVE=False，新增optimizer更新0。nohup已记录READY N2_COMPLETE_AWAITING_STAGE_PROTOCOL和完整派发/完成序列，无本次故障回报。POST_N2_DIAGNOSTICS_SCREEN True True对应N5问题触发=True、N3问题触发=True，不是两种训练方法有效。N2原科学gate、诊断数值/原件尚待上传回读；不可称已独立验收或确认贡献。

现在无需要启动的训练或诊断任务。执行下面串行上传；不重训、不改原科学快照。N2上传器补收修复目录和launch/PID轻量日志，语法检查通过；仅新建原实验目录upload_bootstrap并提取上传脚本。诊断上传仍使用原883fccc不可变快照内已运行配套脚本。两个上传器独立fetch当前分支、在各自实验目录下detached Git worktree构建evidence、非force推送；权重/.npy/.npz只建服务器SHA索引。

```bash
(
set -e
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
N2_DIR="$ROOT/records/research_post_ab_followup_n2_20261005T085829_3456726"
DIAG_DIR="$ROOT/records/research_post_n2_diagnostics_20261005T131434_3591073"
cd "$ROOT"
git fetch origin rebuild-v1-protocol-20260915
UPLOAD_COMMIT=$(git rev-parse FETCH_HEAD)
EXP_PY=$(python -c 'import json; print(json.load(open("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
UPLOAD_DIR="$N2_DIR/upload_bootstrap_$(date +%Y%m%dT%H%M%S)_$$"
mkdir -p "$UPLOAD_DIR"
git show "$UPLOAD_COMMIT":scripts/upload_post_ab_n2_records.py > "$UPLOAD_DIR/upload_post_ab_n2_records.py"
"$EXP_PY" -u -B "$UPLOAD_DIR/upload_post_ab_n2_records.py" --root "$ROOT" --directory "$N2_DIR"
"$EXP_PY" -u -B "$DIAG_DIR/code/scripts/upload_post_n2_diagnostics_records.py" --root "$ROOT" --directory "$DIAG_DIR"
)
```

如需GitHub认证由用户交互输入；不在代码/记录存密码。若某次上传失败，保留目录/日志，不重跑训练；先分析失败阶段，确认是否已推送再重试上传。prepare-only可独立查看体积，不作为自动重跑规避限制。

把两个POST_AB_GITHUB_COMMIT / GITHUB_RECORDS结果回传；两上传器当前都使用POST_AB输出前缀，以记录URL中目录区分阶段。上传后助手回读manifest/解码SHA、N2六组selected/fixed8000原整数矩阵/绑定/原gate、E0空间分母、E1所有H/L×方向及E2误报/漏报成本，保存完整结果分析，再决定N5或N3哪族先实现。N4等更新暴露证据，T不提前评价，不自动全跑13组。

E0读取已有预测完成，掩码准备完成；E1两worker分别436.28/441.19秒，E2三worker430.03/431.00/427.27秒，五任务实测均约7.1–7.4分钟。E1/E2三个派发波次从约23:05至23:27完成（起始按progress elapsed推算），新增60次tile推理/0训练。CPU E0最后进度23:05:12.250016，缺少CPU开始记录，不能据此推算E0总时长或原N2完成时间。

研究阶段仍为可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5为主、Full为诊断；单seed42开发证据。只用GPU0/1、nohup、全部产物留zzx对应目录；无SSH、无Test6/independent final、无追加种子、无失败配方自动追训，F/N6保持跳过。

[执行协议](../protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md)；[本次完成观测](../../records/research_post_n2_diagnostics_20261005T131434_3591073/completion_observation_20261006.json)。
