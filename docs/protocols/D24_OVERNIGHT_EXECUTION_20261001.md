# D24十五组：固定版本nohup执行

> 2026-10-02更新：本轮15/15已完成，完整轻量记录已上传acd2dbf。A1/A3的Pair损失开关未生效，见[纠错报告](../experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)。本页为历史执行说明，不重新启动/恢复；新工作按[D25计划](D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)。

更新2026-10-02 12:10（Asia/Shanghai）。**用户回传队列04:06:59 COMPLETE 15/15；所有4000步及汇总完成。** [完成观测](../../records/research_d24_completion_observation_20261002/observation.json)已保存，完整轻量原件已上传至acd2dbf，已完成离线指标复核；A1/A3的Pair科学消融无效，详见上方纠错报告。不要再次启动/恢复已完成队列。无服务器连接，以下由用户服务器终端执行。复用已知GPU0/1、两H10080GB、充足RAM/硬盘，不新增安装、资源审计或预算探针。

固定执行提交：[cf1955d966163978b5c8af433f3845b5ca05da9e](https://github.com/66322/remote_sensing_frequency/commit/cf1955d966163978b5c8af433f3845b5ca05da9e)；[科学协议](D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)、[15组机器计划](../../records/research_d24_overnight_plan_20261001/plan.json)、[本地检查](../../records/research_d24_overnight_plan_20261001/local_validation.json)。

## 历史启动方法（本轮已执行，不重复）

目的：单seed开发筛选任务目标/表示、类别语义、光学知识迁移及普通增强四个角度。GPU0/1各一个job，训练物理batch16无累积，每组4000步，共60000更新；单job6h上限，技术失败留证并继续其他job。控制器与worker都有锁，nohup与独立worker会话防终端断开；全部快照、cache、临时文件、日志、PID、checkpoint和预测在本次zzx目录。主Git工作副本仅fetch，不切换/覆盖。

以下仅保存历史启动命令；包含已知Pair开关问题，不用于未来新运行，也不再复制启动块：

```bash
(
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915

D24_COMMIT=cf1955d966163978b5c8af433f3845b5ca05da9e
D24_DIR="$PWD/records/research_d24_overnight_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$D24_DIR"
git show "$D24_COMMIT":scripts/launch_rebuild_v1_d24.py > "$D24_DIR/launch.py"
D24_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
test -x "$D24_PY"

nohup "$D24_PY" -u -B "$D24_DIR/launch.py" \
  --root "$PWD" --commit "$D24_COMMIT" --directory "$D24_DIR" \
  > "$D24_DIR/nohup.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$D24_DIR/controller.pid"
printf 'D24_DIRECTORY=%s\nD24_LOG=%s/nohup.log\n' "$D24_DIR" "$D24_DIR"
sleep 5
tail -n 12 "$D24_DIR/nohup.log"
)
```

正常首先看到GPU0 A0、GPU1 A2的D24_STARTED。随后读取权重和12个fit tile常驻缓存，再出现D24_TRAIN；初始缓存阶段GPU可能暂时空闲，这是实际输入准备，不是资源测量。nohup返回PID不等于首步成功，真实首步/梯度检查在对应job日志和gradient_check.json。不重复粘贴启动块创建第二队列。

## 查询实际阶段与近似结束时间

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/status_rebuild_v1_d24.py" --directory "$D24_DIR"
```

显示最后记录时间、完成数、逐job状态、phase、step和全图windows。队列结束时间只参考已经正常完成的同路线/同更新范围job；首次没有对应观测时明确显示未知，不另跑探针。跨路线估计标为近似，不能保证全部15组明早结束。

## 队列完成后上传轻量记录

控制器自动产出screen_result.json/results.csv；本命令也允许上传失败/部分完成记录。终端保留Git凭据交互，uploader不会启动训练，不把密码写进日志：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/upload_rebuild_v1_d24_records.py" --root "$PWD" --directory "$D24_DIR"
```

它只提交计划/配置绑定、状态、原计数、选模、轻量日志及二进制索引；预测/权重留服务器。新Git worktree及所有上传准备文件也在本次实验目录，非强制推送。贴回D24_GITHUB_COMMIT和记录链接即可，无需贴长JSON。

## 控制器意外结束才精确恢复

先查询状态；仍在后台工作的controller/worker不需要恢复。以下命令复用同目录、同执行提交并拒绝活着的旧worker；已完成组跳过，未完成匹配checkpoint恢复，不自动重跑TECHNICAL_FAILURE/TIMEOUT：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
D24_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
D24_COMMIT=$(cat "$D24_DIR/execution_commit.txt")
D24_STAMP=$(date +%Y%m%dT%H%M%S)_$$
nohup "$D24_PY" -u -B "$D24_DIR/launch.py" --root "$PWD" --commit "$D24_COMMIT" --directory "$D24_DIR" --resume-queue > "$D24_DIR/nohup_resume_$D24_STAMP.log" 2>&1 < /dev/null &
printf '%s\n' "$!" > "$D24_DIR/controller_resume_$D24_STAMP.pid"
```

单个技术失败须先读对应log并修正；不能改变已冻结科学预算/阈值来“挽救”结果。若controller已完成整个队列，不再恢复。

## 科学和实现边界

本地合成CPU共15项检查，Python3.13.3/Torch2.7.1+cpu；含Python3.10语法/执行快照依赖和实际15组目标的梯度链，不是服务器Torch2.2.2+cu121的GPU效果证明。正式首步必要梯度检查随job执行；遇到运行错误保留证据，无额外预算门禁。

2000/4000 clean Val2选checkpoint，选定后14条件/双tile记录，int64原矩阵可重算。C光学学生仅DSM变化条件复用clean预测；D3共享A2。固定R0/M0_safe参考复用已完成D23 T0原预测及SHA，不重新训练或推理旧gate。Test6禁读，所有结果仅开发筛选；最终贡献未采纳。
