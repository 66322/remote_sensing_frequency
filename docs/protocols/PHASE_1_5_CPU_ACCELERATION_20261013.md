# Phase1.5 当前CPU分析加速接管协议（2026-10-13）

状态 CPU_ACCELERATION_READY_NOT_APPLIED。用户明确要求现在优化当前分析，授权技术接管，不改变科学任务。最后D进度57/160（10:44:37），不是实时状态；GPU100批已在10:17回报完成。服务器由用户终端执行，无SSH。

## 固定范围与原件保护

只针对research_phase15_recoverability_20261012T233532_842792及执行45138f0f的原CPU D阶段。保持2 Val2 tile、20旧mask ID、四族、五expert、原CM/transition/conditional/bin/oracle定义，0训练、0新case/seed、0GPU重跑，无Test6/held4/final。原plan/code/code_manifest/全部GPU case、已完成D JSON保持。新增cpu_acceleration_<时间>_<pid>子目录保存修复源码、清单、CPU检查、接管前后状态、受控停止凭据、日志与真实等价回执，原绑定继续对应原模型/数据/推理；每个新D行额外标注acceleration代码manifest SHA。不能将新计算源码藏在原推理manifest下。

优化1：joint GT×reference×candidate 6×6×6 int64直方图替代重复按类扫描，精确导出clean/missing CM及逐类valid/reference_correct/reference_wrong/harmed/rescued/flips及相同率分母。按128行分块控制索引临时内存。
优化2：专家正确bitmask×bin联合直方图一次统计，预计算valid/disagreement，替代每bin×每expert重复全图扫描。
原oracle选择/patch边界/tie优先级、seam smoothing、distance EDT、4连通域及全部GT/可观测分箱不变。
优化3：默认2 CPU进程分派不同未完成case，单writer由各独占caseworker原子写入，父进程记录完成哈希；tile loader/clean/DSM/static feature bins在每个worker内复用。数值库线程仍1，避免多进程×线程超订阅。GPU空闲无需用新增训练填满，CPU整数统计等价优先。

## 验证与实测边界

4项CPU检查通过：完整oracle所有结果字段在17×19、129×133、260×257、empty/full/pixel/rectangle 12场景逐项一致；完全一致专家/无bin支持、无效预测拒绝；接管阶段/CPU affinity/RAM资源拒绝。4新增Python AST通过。local CPU，非服务器端到端运行确认。

768×768合成随机影像、全部可观测bin：旧统计5.725464s，新1.282079s，4.4658倍，所有result字段exact。此为一次本地功能基准，不能直接承诺6000×6000/磁盘解压/多进程整轮4.5倍。真实接管后还必须从既有完成pixel/matched各选固定首个case，以新算法复算并与原result字典逐字段完全相等；失败HOLD、不写新科学case。保存original SHA和real_equivalence.json。

## 接管顺序

1. 用户终端从固定Git发布commit提取accelerate_phase15.py，参数--root ROOT --directory DIR --commit COMMIT --workers 2。登记锁保证只有一次；已有cpu_acceleration目录则仅报告路径、不重复启动。预检原code/plan、CPU D阶段/100GPU全COMPLETE及原controller存活；若整轮已完成只回报无需接管。
2. 按/proc/MemAvailable及可读cgroup内存余量取更小值，CPU affinity限制，12GiB/worker+8GiB reserve保守政策（未声称实测峰值）。最多4worker、默认2，RAM不足自动减至1；不足20GiB则拒绝且保持旧任务。此政策不会预测未来所有动态内存争用。
3. 新不可变执行代码/manifest写入原目录子树，先跑同包CPU等价检查。CPU检查失败原controller不受影响。再次读状态；若D已完成让旧controller继续汇总。
4. 保存原状态/进度，严格核/proc cmdline对应原目录及analyze_phase15.py --phase D后，仅SIGTERM原D子进程；原controller按原协议收尾HOLD并退出。等待最多60秒且锁释放，保存before/after及技术停止回执。这是用户明确要求优化的受控停止，不能当新方法失败或隐藏原HOLD。当前未写完的一个case可能重算；已完成原子JSON不丢失。
5. 新nohup controller取得原锁，原queue_status写新的controllerPID及acceleration_directory。扫描已完成D行绑定/mask SHA、保留字节，固定pixel/matched真实等价通过后才并行剩余任务；progress报告completed_cases/160、parallel_workers、preserved_completed_cases、新完成数及耗时。新controller不得再自动登记GPU任务或训练。
6. 全160原计数齐全→complete哈希绑定→调用原summarize_phase15.py，原科学汇总不改→PHASE15_COMPLETE_AWAITING_REVIEW。原controller.log仍保留；新的日志在acceleration_directory/controller.log、summary.log。

## 查询、失败与交付

既有status_phase15.py及analysis/D/progress.json继续可用；真实等价检查时QUEUE=CPU_ACCELERATION_EQUIVALENCE_CHECK。随后CPU_ORACLE_AND_CONDITIONAL_COUNTS，末尾SUMMARIZING_ALL_FIVE_DIAGNOSTICS及COMPLETE。原nohup不再代表新controller；查看新返回CPU_ACCELERATION_LOG。

任何原件/等价/worker/summary错误TECHNICAL_FAILURE_HOLD，保留产物不自动retry。阶段技术限24h+summary6h，不是一天总截止。已完成D不能覆写；complete receipt若已存在也不覆写。临时文件/缓存/日志均留zzx原实验目录。完成且控制器/锁退出后原upload_phase15.py会递归包含新增轻量源码/等价/接管记录；数组仍server_only，原失败/受控停止要在结果审计中明示。

真实等价、资源并发和实际新case速度均需用户终端回报后核验；当前不声称已接管或实测缩短到特定小时。
