# 当前Phase3队列遇到机器重启或需释放GPU0/1时的操作

适用对象仅为M2目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345`及配对的`research_phase3_combined_revision_20261024T092814_2738345`。最后已知用户回执为2026-10-25 22:12:38+08:00，M2 45/108、失败0、F0评价在途；这是历史观测，执行前必须重新只读核实。服务器由用户操作，本文件与辅助脚本本身不会远程执行。

## 关键结论：目前只能中止，不能无损暂停后续跑

冻结的M2控制器在内存中维护`completed`、`evaluated`及故障评价的`Sink`状态；`Sink`以独占创建模式打开计数流。训练函数也以`exist_ok=False`创建作业目录，从未加载`last_resume.pth`。后者每1000步保存模型/优化器/RNG，但没有已经接入的控制器重建、数据流恢复和故障评价恢复流程。因此**不能把`last_resume.pth`当现成续跑入口**；直接重启控制器会重新调度且与既有目录冲突，重复bootstrap被单次登记回执挡住。先前其他实验的`release/rejoin`命令属于不同队列，不适用于本次M2。

终端断线通常不影响这次已用`nohup`启动的两个控制器。**机器重启**则杀死控制器、GPU/CPU子进程与匿名内存包；若`/home/jovyan/zzx`持久挂载，已落盘的`complete.json`、端点、训练轨迹、`last_resume.pth`和轻量计数仍在，但中途作业、F0在途评价与最后写入可能不完整。重启后旧`queue_status.json`可能仍写`RUNNING`，必须同时核对PID是否真的存在及GPU进程，不得把旧JSON当实时存活。机器或文件系统故障是否损坏原件须逐项核验。

## 先只读确认

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
python -B "$ROOT/records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py" --tail 20
```

如果机器重启后两个登记PID都不存在，GPU0/1也没有本队列计算进程，就**不要再次运行bootstrap、repair --apply或旧nohup启动命令**，也不要删除单次登记回执、锁文件或部分作业目录。保存上述状态输出，并清点每项`complete.json`、端点SHA、各年龄四tile轨迹、`last_resume.pth`、计数流和失败回执。之后需要单独版本化的恢复/延续实现及目标验收，明确哪些完整作业可复用、如何处理被打断的训练与评价；原108作业、评价案例和科学门禁未完整通过前不得宣称阶段完成。无需为只读诊断访问Test6/held4/final。

## 确实需要立刻释放两张卡：显式中止本次运行

这会停止当前M2及其后续J/R/T/V自动队列，**不保证中途训练或F0在途评价能接续**。若还希望保留继续执行的可能，应先完成并验收专门的恢复机制，再安排中断。若决定终止，使用[当前运行专用辅助脚本](../../scripts/stop_phase3_m2_owned_workers.py)；它先比对单次回执、当前运行目录、两个控制器命令行、登记GPU UUID与GPU计算进程父PID，要求两张卡各只有一个本M2拥有的计算进程。任何不符即拒绝发信号。`--inspect`只读；`--abort-current-run`写入意向回执并向**已核验的GPU0 worker**发送SIGTERM，让原M2控制器检测子进程退出，走其自身失败清理链，释放它拥有的另一worker、CPU池和匿名内存包。合并监督器最多下一次约5分钟轮询才写停止状态。此动作在原系统里记为`FAILED_NO_RETRY`/`STOPPED_NO_AUTOMATIC_RETRY`，应连同意向回执解释为**用户主动中止**，不是研究阴性或未知工程故障。

把`FIX`填为发布本协议时给出的**固定40位提交SHA**，脚本只保存到本M2记录目录；先运行只读预检，确定确实是当前运行后才执行第二条：

```bash
ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
M2="$ROOT/records/research_phase3_m2_revision_20261024T092814_2738345"
FIX='<本协议发布提交的40位SHA>'
SCRIPT="$M2/stop_phase3_m2_owned_workers_${FIX}.py"
curl -fL --retry 2 \
  "https://raw.githubusercontent.com/66322/remote_sensing_frequency/$FIX/scripts/stop_phase3_m2_owned_workers.py" \
  -o "$SCRIPT" &&
echo 'd666c4e39b59ef8bac5f2a912ada1e68f4f77f96de0697a412bd2ffecc562526  '"$SCRIPT" | sha256sum -c - &&
python -B "$SCRIPT" --inspect

# 仅在你决定放弃本次运行的自动接续、需要立即释放两卡时执行：
python -B "$SCRIPT" --abort-current-run
```

第二条返回后再只读检查：

```bash
python -B "$ROOT/records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py" --tail 20
nvidia-smi -i 0,1
```

只有确认本次两个GPU worker都退出、GPU0/1不再被本队列占用后，才可给其他任务使用。如果预检拒绝、120秒内没有显示`OWNED_GPU_WORKERS_RELEASED`、控制器未写出停止状态或GPU仍有不明进程，就停止操作并保留输出诊断；不按进程名批量`kill`，不运行`kill -9`或对旧PID盲目发信号。终止以后要再继续研究，应先基于保留原件设计明确的人工接续合同；不能通过删除回执重启同一目录。

## 实现与验证边界

辅助脚本是外部操作工具，不热改当前冻结执行快照。源码静态核对了Linux `/proc`、NVIDIA UUID和原控制器拥有的进程关系；本地单元测试验证两卡单一归属、拒绝其他父PID/额外计算进程、仅向核验后的GPU0 worker发送SIGTERM，并通过Python3.9语法解析。尚未在服务器目标环境运行此辅助脚本；目标`--inspect`及实际终止结果均须由用户终端回执确认。本协议不授权默认终止当前运行，也不声称已经具备安全续跑。
