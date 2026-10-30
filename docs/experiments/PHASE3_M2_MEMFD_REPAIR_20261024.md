# M2登记期memfd兼容修复与原目录接续（2026-10-24）

状态：MEMFD_CHECKS_PASSED_SUBSEQUENT_M2_INCOMPLETE_STOPPED。修复执行提交：[b0200004f30a8d55eef2049ecdfb30ef97f3d034](https://github.com/66322/remote_sensing_frequency/commit/b0200004f30a8d55eef2049ecdfb30ef97f3d034)。不是科学配方失败或训练重跑。

## 最后服务器证据

来源为[用户粘贴终端副本](evidence/PHASE3_M2_MEMFD_FAILURE_20261023.txt)，未直接接收服务器日志原件。

- 查询时间2026-10-23 22:31:10+08:00；GPU0/1 H10080GB均无计算进程，0MiB；这是最后观测，不是当前状态。
- 合并目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225；原控制器PID2166328为Zs/defunct。
- 合并queue_status.json最后时间22:21:18.961108，STOPPED_NO_AUTOMATIC_RETRY，原因为M2 bootstrap failed。
- M2目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330；registration_failure.json最后时间22:21:18.850724。
- 原目标测试共16项，15通过，仅test_linux_process_memfd出错：os.memfd_create不存在。异常来自phase24_ipc.Packet.create，在bootstrap启动训练控制器之前。
- Torch已为2.2.2+cu121、CUDA可用，沿用原remote_sensing环境。原phase3_m2_common.environment已设置XFORMERS_DISABLED=1，xformers依赖冲突不是此次直接原因，无需为本次故障更换环境或继续换包。

## 原因与证据边界

Python未暴露os.memfd_create，不能单凭hasattr判断内核不支持；CPython的该接口受构建条件影响。修复优先绑定libc.memfd_create；旧libc没有符号时，仅在已核验的Linux x86_64调用同一memfd_create系统调用319。不在未知架构猜测系统调用号，不以磁盘文件或/dev/shm命名文件代替。

修复执行时必须实际创建匿名memfd，核验/proc/self/fd目标、CLOEXEC及内存映射读写，再通过原16项测试中的真实跨进程FD传递。内核不支持或被禁用时保持停止，不能保证仅凭兼容代码就一定通过目标服务器。

原理参考：[Linux memfd_create手册](https://man7.org/linux/man-pages/man2/memfd_create.2.html)、[Linux MFD_CLOEXEC定义](https://raw.githubusercontent.com/torvalds/linux/master/include/uapi/linux/memfd.h)、[CPython3.9 posixmodule](https://github.com/python/cpython/blob/3.9/Modules/posixmodule.c)。x86_64调用号同时核对了本地Linux发行版的/usr/include/x86_64-linux-gnu/asm/unistd_64.h，值319。

## 实现与接续约束

新增五文件载荷及独立执行清单，不修改冻结的phase24_ipc.py、M2/合并控制器、计划、代码清单或fold绑定：

- phase3_memfd_compat.py：只为缺失的OS接口安装同语义绑定；已有原生接口保持原样。
- phase3_memfd_entry.py：显式包装原16项测试及原M2/合并控制器，在进程内安装绑定，fork子进程继承；没有目录级sitecustomize、磁盘数组或重新实现模型。
- phase3_memfd_repair_common.py：核对原源码及注册哈希，仅接纳这一项登记检查失败。
- repair_phase3_m2_memfd.py：在原合并目录repairs/memfd_<修复SHA>/保存修复源码和证据；--apply明确请求全部检查通过后接回控制器。
- test_phase3_memfd_compat.py：兼容后端、errno/参数拒绝、不可跳过Linux门禁、已有作业/启动痕迹拒绝、原绑定保护。

脚本现场要求：原M2 jobs为空、launch/训练准备/控制器启动痕迹不存在，原失败严格匹配单一memfd目标检查，合并队列严格匹配M2登记失败，两处控制器锁均可获取；否则停止，不隐含选择其他run、不杀进程、不重跑科学任务。

通过真实内核探针及完整16项检查后，在原M2目录创建首次launch记录并启动原训练控制器；随后接回原合并监督器。仍是M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd与合并e65c6cb0830985461b3cd30e2f43158dd3d858cb，108×32k与总228作业/5,088,000更新不变。接口包装修复另以本提交绑定，不冒充原执行包字节。

原registration_failure.json、原失败target_checks.log、合并原nohup.log保留；新检查日志与合并接续日志在repair目录。M2新nohup.log用于首次训练控制器。两处runtime_repair.json记录修复文件SHA、原绑定与包装入口；重复修复命令检测launch意图后仅显示记录，不重复启动。检查失败则保存checks_failed.json，不自动重试。

## 已完成验证

从独立、无.git的五文件修复载荷运行9项兼容/接纳检查，全部通过；五个Python文件通过Python3.9语法解析。回执见[本地检查](evidence/PHASE3_M2_MEMFD_REPAIR_LOCAL_20261024.json)。

本地Windows的模拟检查不等于服务器Linux FD实测。另在旧WSL1/Python3.5中实际调用时，内核返回ENOSYS；兼容层按设计停止，没有创建文件替代。这是拒绝不支持内核的负向检查，不是Linux成功传输证据。目标服务器原16项测试仍待用户执行，任何一项失败都不派发训练。

## 用户执行

无需安装或升级包，不再运行bootstrap_phase3_combined.py或bootstrap_phase3_m2.py登记新队列。使用当前remote_sensing及本修复提交：

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
FIX=b0200004f30a8d55eef2049ecdfb30ef97f3d034
Q="$ROOT/records/research_phase3_combined_20261023T222112_2164225"
M2="$ROOT/records/research_phase3_m2_20261023T222114_2166330"
SCRIPT="$ROOT/records/repair_phase3_m2_memfd_${FIX}.py"

curl -fL --retry 2 "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/repair_phase3_m2_memfd.py" -o "$SCRIPT" &&
{
  REPAIR_LOG="$ROOT/records/phase3_memfd_repair_$(date +%Y%m%dT%H%M%S).log"
  nohup python -u -B "$SCRIPT" --commit "$FIX" --directory "$Q" --m2-directory "$M2" --apply </dev/null >"$REPAIR_LOG" 2>&1 &
  echo "$!" > "${REPAIR_LOG%.log}.pid"
  echo "$REPAIR_LOG"
  sleep 5
  tail -n 80 "$REPAIR_LOG"
}
```

成功检查标志ORIGINAL_M2_TARGET_CHECKS_PASSED；实际接续标志EXISTING_M2_MEMFD_REPAIR_LAUNCHED并返回两个新PID。后者也不等于已完成首个训练更新，须查看原M2 queue_status.json/nohup.log。修复目录target_checks.log应显示原16项全部通过；不要拿保留的旧失败日志判断新状态。

失败时只读新repair日志与checks_failed.json，不再次登记或重跑。结束验收时须额外同步runtime_repair.json及repair目录的execution_manifest、admission、target_checks_passed、launch等轻量证据；原M2上传器不自动保证包含独立修复包，不能声称这些服务器证据已上传。

服务器由用户执行，无SSH，仅物理GPU0/1；所有修复快照/日志在/home/jovyan/zzx原实验目录。无test访问，无额外seed/模型/训练，无全轮磁盘缓存。研究角色保持原决定。

## 2026-10-24服务器接续回执

用户2026-10-24回传的修复日志（文件名时间08:32:16，未提供完成时刻）证明：原16项目标检查通过，登记期training_jobs=0；修复启动器已完成，首次M2控制器PID2690788、合并监督器PID2690789已派发。尚无控制器存活、准备进度、GPU训练或首个更新回执，不能称训练已运行。

[用户终端输出节选](evidence/PHASE3_M2_MEMFD_SERVER_RECEIPT_20261024.txt)，保留启动器Done与新日志的派发标志；不是服务器原日志文件完整归档。原16项通过及training_jobs=0为修复脚本回执，尚未回传逐项完整日志、runtime_repair.json和launch.json原件。GPU watch没有粘贴屏幕内容，不能推断GPU是否在训练。

用户已执行上方一次性命令，不再执行本页历史启动块。接下来只读检查原M2状态/准备进度/GPU进度/失败回执及新日志。代码先执行prepare再创建GPU worker，prepare包含输入SHA及12个Fit12 tile的内存加载和边界统计，preparation_progress.json每完成一个tile更新，M2_INPUT打印进度。训练调度后M2状态约15秒刷新，合并WAIT_M2最长约300秒刷新；监督器等待是正常依赖行为。没有新增配方或改变门禁。
## 后续状态：M2执行不完整停止

最后服务器观测2026-10-24 08:38:13+08:00：M2 PID2690788和合并PID2690789均Zs/defunct，GPU0/1均0MiB且无计算进程。M2于08:36:44.670358报告INCOMPLETE_NO_RETRY；合并于08:37:36.280856报告STOPPED_NO_AUTOMATIC_RETRY，原因M2 did not finish as server-checked。12/12输入准备于08:35:40.299463完成。此为最后观测，不是实时状态。

最新[停止取证记录](PHASE3_M2_INCOMPLETE_20261024.md)覆盖上方派发后待核验状态。memfd与16项检查通过不等于训练链验收；先取真实作业堆栈，根因未知。已有失败作业/publication不符合登记期接纳条件，不再次执行历史修复命令。