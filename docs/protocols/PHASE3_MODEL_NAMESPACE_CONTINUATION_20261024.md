# 已登记但未放行队列的model包路径修复与接续（2026-10-24）

状态：SERVER_CHECKS_PASSED_FORMAL_CUDA_UPDATES_OBSERVED。补丁提交25b124a0cf69ececb6841b55ed90b19fae5b9a08；沿用用户“继续，把实验启动”的授权。此次发生在控制器启动前，没有作业/失败配方/优化更新，允许修复启动工程继续既有尝试，不再次请求训练重试授权。

## 最后证据与根因

用户[原始终端副本](../experiments/evidence/PHASE3_MODEL_NAMESPACE_FAILURE_20261024.txt)最后查询2026-10-24 09:30:32+08:00：GPU0/1均0MiB、无计算进程，两个新目录均no_launch_release=true、jobs/failures为空、无PID字段。是最后观测，不是实时状态。

基线修订752d3835a18a15a04d83b1dcc1841bff98bf0b07已于09:28:14登记：

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345。
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345。
- 全局回执records/phase3_engineering_restart_20261024_once.json，09:28:23 FAILED_NO_AUTOMATIC_RETRY。

新目录CPU真实模型构造/公共权重、原M2全16项、combined_plan6项均通过。J头测试导入失败：ModuleNotFoundError: No module named model.phase3_j_heads；FAILED(errors=1)，Ran1test，控制器从未放行。

根因：M2源码有常规model/__init__.py，合并快照仅列出3个新增model/*.py，属于命名空间目录。Python仍选择常规M2包，单调PYTHONPATH不能合并两处model；本地单仓库恰有全部模块，先前41项未覆盖该分包布局。这是助手打包/测试覆盖遗漏，不是模型机制或研究失败。

## 有限修复与门禁

不改752d冻结代码、代码清单、runtime_revision或旧检查日志，不添加/覆盖model/__init__.py。新增phase3_model_namespace.py只在进程内将model.__path__和spec搜索路径绑定到两处已核验模型目录，M2优先，合并新增模块可见；拒绝同名异内容源、外部已加载包/子模块。M2/J/R及测试均经同一额外包装入口，fork子进程继承；模型数学、权重、种子、预算和科学门禁不变。

repair_phase3_model_namespace.py只接纳上述精确两目录和752d全局失败回执；原runtime全部源/兼容副本哈希、CPU成功回执在原revision绑定内，须完整通过。现场要求两jobs/failures目录为空，无launch.json、runtime_entry_ready、namespace_entry_ready及launch_release；停止状态no_launch_release必须为真，原J测试必须匹配这一条导入失败。已有训练/其他错误即拒绝，不自动恢复失败训练。

新补丁快照位于现有M2 repairs/model_namespace_<补丁SHA>；保留全局失败快照、两状态副本、新检查日志、补丁manifest和receipt。两目录model_namespace_repair.json绑定额外代码及原runtime SHA；原752d文件逐字节保持。接续只更新运行状态/首次launch记录和全局单次回执，不新建M2或合并实验目录，不删除回执绕过重复保护。

先跑补丁8项，再在实际分包布局重跑原M2全16项和合并三套11项；不跳过失败项，无额外GPU训练探针。双方额外包装和原入口ready、PID/修订一致、GPU0/1及UUID复核后才放行原控制器。修复器在放行前解开两控制器锁，仅持补丁登记锁，避免控制器锁竞争。首个正式更新仍是CUDA准入。

重复补丁命令发现model_namespace_repair.json即只显示EXISTING_NAMESPACE_REPAIR_NO_DUPLICATE；检查/部分启动失败保留材料，不自动重试。放行前故障只清理本修复器创建、尚在等待的入口；不按名称/PID搜索其他任务。旧63条失败及原两个旧run不触碰。

## 历史执行命令：已于09:46完成，不再执行

```bash
conda activate remote_sensing
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
FIX=25b124a0cf69ececb6841b55ed90b19fae5b9a08
SCRIPT="$ROOT/records/repair_phase3_model_namespace_${FIX}.py"
curl -fL --retry 2 \
  "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/repair_phase3_model_namespace.py" \
  -o "$SCRIPT" &&
{
  NAMESPACE_LOG="$ROOT/records/phase3_model_namespace_$(date +%Y%m%dT%H%M%S).log"
  nohup python -u -B "$SCRIPT" --commit "$FIX" --apply </dev/null >"$NAMESPACE_LOG" 2>&1 &
  echo "$!" > "${NAMESPACE_LOG%.log}.pid"
  echo "$NAMESPACE_LOG"
  sleep 10
  tail -n 100 "$NAMESPACE_LOG"
}
```

成功派发标志REGISTERED_REVISION_NAMESPACE_FIXED_LAUNCHED，返回新PID但目录仍为09:28:14这两个。CHECK_PASSED/启动器Done不是训练更新证明，须查M2_TRAIN ...1和progress step≥1。

```bash
tail -n 100 "$NAMESPACE_LOG"
python -B "$ROOT/records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py" --tail 40
```

不要再次执行原bootstrap_phase3_engineering_restart.py或memfd --apply。完整状态助手仍可用，它按保留的全局回执读取这两个新目录及当前状态/准备/进度/失败/PID/GPU。首次Fit12准备先CPU读取12tiles，GPU可暂时空闲；不能以nvidia-smi空闲单独判断失败。

## 本地验证与发布时剩余边界

[本地回执](../experiments/evidence/PHASE3_MODEL_NAMESPACE_LOCAL_20261024.json)：8项路径/接纳/重复保护检查通过；在分开的M2常规model包与原18文件合并快照中，补丁前真实复现同一错误，补丁后三套原检查6+2+3=11项通过。独立无.git补丁包8项通过，七文件Python3.9语法解析通过，Git原件SHA核验通过。不是只在单仓库环境宣称通过。

目标服务器补丁尚未执行，原16项/合并11项和首次CUDA更新仍待实际回执。原M2上传器不保证包含额外补丁，结束需另验收model_namespace_repair、补丁manifest/checks/repair_receipt/launch以及752d runtime材料和训练轨迹。GPU0/1、test封存、有界内存、原228作业/5,088,000更新及研究角色保持，不新增seed/配方或开放B/C。
## 前一服务器回执：09:48已放行并准备输入

最后服务器观测2026-10-24 09:48:32+08:00：路径补丁已完成全部目标检查并于09:46:44放行两个控制器；M2 PID2754693为Rs、合并PID2754694为Ss，均存活。M2 LAUNCHED_PREPARING，输入准备7/12（tile6_9，09:48:31），无progress、无作业失败；合并WAIT_M2。GPU0/1均0MiB/无计算进程，符合尚在CPU准备的阶段。不是当前实时状态，尚无首个优化更新或CUDA训练成功证据。

[完整运行说明及用户副本](../experiments/PHASE3_REVISION_PREPARING_20261024.md)。上方待目标执行描述为补丁发布时状态，现由本段更新：8项、原16项和合并11项全部通过，原两目录接续成功。当前只读查询，禁止重跑本页历史启动块。尚无首个训练更新或正式结果。

## 最新服务器回执：09:54双GPU真实训练

最后服务器观测2026-10-24 09:54:39+08:00：M2为RUNNING，输入12/12已于09:49:45完成；GPU0的F0_s42_T3推进到2600/32000，GPU1的F0_s42_T1推进到2620/32000。两个控制器2754693/2754694存活，作业失败0、完成端点0；合并WAIT_M2为正常依赖等待。此为最后观测，不是实时状态。

[训练更新与原样终端副本](../experiments/PHASE3_REVISION_TRAINING_STARTED_20261024.md)。此前待首更描述已由本段更新；尚无完整端点或科学性能结论。当前继续已有队列，只读查询，不再执行历史启动块。
