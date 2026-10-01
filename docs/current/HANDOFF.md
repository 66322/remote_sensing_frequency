# 当前交接：D23-A通过投入门槛，B进入实现准备

更新2026-10-01，分支rebuild-v1-protocol-20260915；实验快照1a8a840，A脚本来自961c719。用户通过服务器终端执行，本轮无直连。研究仍是可行性探索，频率/语义可靠性为优先候选，C1旁支，部分解冻强基线，方向/章节未冻结。

最新用户回传观测2026-10-01T12:44:35.075903+08:00，D23-A COMPLETE，10pair，20个既有预测。Potsdam Val2、D21 R0/M0 seed42固定16000步、NoBoundary fg5不可部署互补诊断相对每条件较强同回退专家：clean1.5927371494/rgb_down4 2.4155417779/noise1.6570893077pp，平均1.8884560784pp，满足准备B规则。实际114.1585秒/RSS584.1758MiB，Test6/独立final false，无新训练或推理。详见[A结果](../experiments/D23_A_COMPLEMENTARITY_RESULTS_20261001.md)。

原件仍在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_feasibility_20261001_20261001T124227_658274；当前归档仅用户粘贴摘要、均值复算，不是全部联合张量已离线复核。用户已在服务器打包profile/full与日志，SHA041bc0ad79c3c5f11fdbf4a29479b2c3cf68d60f898b5125d8cf2211e59084b1；本地尚未收到，不重跑A。原Post-D21归档缺口仍存在。

B核心model/rebuild_v1_d23_gate.py与tests/test_d23_gate.py已实现，本地PyTorch2.7.1 CPU8项合成测试PASS，每gate18145参数。真实专家接入、服务器CPU兼容已通过，真实DINO GPU接入、训练/整图评价入口、TCAP gate-fit统计、滑窗后精确回退、吞吐/磁盘测量尚待完成；正式队列未实现/启动。[B准备记录](../protocols/D23_B_IMPLEMENTATION_PREPARATION_20261001.md)。

立即工作：服务器CPU8项复验已PASS（1.732秒，结束时钟未提供）。scripts/probe_rebuild_v1_d23_gate.py已实现，3项本地准入检查PASS；下一步用户执行[单GPU训练crop短测](../protocols/D23_B_CROP_GPU_PROBE_20261001.md)。GPU尚未运行；crop probe不含正式增强流/整图评价，后续仍须完成单一入口、TCAP统计、整图测试、wall/job/显存/RSS/磁盘预算，才生成8组4000步命令。A只证明互补空间，不证明语义/频率/gate有效；收益/harm-rescue门槛不改。频率无独立增量撤回贡献，gate无收益关闭解法，不自动补seed/改半径。

旧Test6历史暴露，不具独立final资格，继续禁读。第一轮光学可用、已知DSM availability，未知缺失/光学全缺失及独立地区仍待检验。旧交接见固定[961c719](https://github.com/66322/remote_sensing_frequency/blob/961c7197d07a636c0d7d46bba7937e15395cf4f8/docs/current/HANDOFF.md)。

用户本轮明确授权GPU0和GPU1。下一命令将逐卡运行相同crop探针，每卡上限30分钟；正式双卡并行资源与整图预算仍待验收，不重复询问卡号权限。

目录规则：用户要求所有服务器实验记录保存在/home/jovyan/zzx下的对应实验目录。本次B代码快照、两卡结果、日志统一在项目records/research_d23_b_crop_probe_<timestamp>_<pid>/下的code/gpu0/gpu1；A归档仍在A目录。后续不使用/tmp执行快照，不自动移动旧记录。
