# Post-D30评价接口故障与同目录恢复

最后服务器观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。修复已实现并通过本地检查，尚未收到服务器恢复启动证据。

来源：[用户服务器终端原件](../../records/research_post_d30_mechanisms_20261004T000812_2446364/failure_terminal_20261004.txt)及[紧凑观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/failure_observation_20261004T060404.json)。记录来自用户回传，不是助手实时SSH查询。

根因：runtime_plan深拷贝D30/D27完整评价协议，其中继承present_zero/present_shift_half两个诊断。新处理器基于D26实现，缺少这两个条件，6组A在完成8000训练及fixed8000评价后，selected评价抛出同一ValueError。此前本地接口覆盖从D26基础计划构造，未覆盖真实D27/D30继承计划，这是工程验收遗漏，不是资源瓶颈。完整有效协议为32条件。

恢复在同一目录建立独立、带SHA清单的评价补丁快照，原plan和code快照保持不变。补丁按D27原语义支持present_zero及present_shift_half：DSM虽坏，但两侧可用性mask仍为True，不把未知坏数据当已知缺失。A必须加载8000步保存状态，新增优化器更新数为0，补评价前后核对selected/step8000权重SHA；相同checkpoint的已有评价可校验后复用。补齐A后仍按A→B→C→条件F；F仅由固定B3全部gate通过触发，不新增多seed、D29或新模块。

显式恢复仅重排已知失败A；每项要求错误匹配、最后步数8000、原快照SHA一致、无活跃旧进程和锁可获取。A绑定记录新增optimizer_updates=0及不可变权重SHA。complete.json及新诊断/summary附evaluation_patch，指向修复manifest及repair commit；原source/plan签名仍对应真实训练代码。相同selected=fixed8000权重时，缺失的非主条件记录校验后复用预测硬链接；不同选模步数不复用。原评价与权重不删除、不覆盖。

修复包括未来实际计划条件检查；上传器归档补丁代码、manifest、旧queue备份及检查日志；修复版ETA排除A评价-only耗时。原immutable code内的启动器/状态/上传器均保留，恢复覆盖层执行新worker，未来任务B/C/F也支持同一诊断条件。

本地验证：5项回归测试（旧条件语义、真实32条件接口、控制器两个恢复点、已知失败限定、相同checkpoint缓存复用）＋10项原模型/机制测试通过；8个修改Python文件通过3.10语法解析。服务器环境须在nohup恢复时执行小张量接口/回归检查并接受真实CUDA评价；本地通过不等于已恢复。

D30终端汇总：P综合86.092396，R84.037805，PR_area85.986496，PR_pixel84.759540，四项continue均False。相对S0综合86.051214，PR_area−0.064718pp、PR_pixel−1.291674pp；不同归一化未达到预设增量门槛。P的小改善与R的信息取舍仍成立，但不能据此认定唯一根因或整个双模态问题无效。指标为Potsdam开发Val2、native512/stride256、NoBoundary fg5的selected口径，来自用户终端；完整原矩阵尚待上传与独立重算。

结论分级：D30终端完成与筛选未通过属于有运行回传的实验阶段证据，完整原件待上传独立重算；A训练完成与评价异常属于工程证据，不能宣称A效果失败。评价修复属于代码已实现，尚无服务器恢复成功观测；不变更研究问题或gate。

下一步见[NEXT](../current/NEXT_EXPERIMENT.md)。
