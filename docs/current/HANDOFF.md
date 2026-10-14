# 当前交接：Phase2.4零更新登记失败的IPC技术替换（2026-10-14）

## 当前事实与唯一下一动作
**IPC_PATH_FIX_READY_AWAITING_SERVER_REGISTRATION_CHECKS**。用户回传原失败目录 research_phase24_protected_20261014T185408_2127460，执行15fdfa4c：20项中18数值检查ok、两项运输检查均OSError: AF_UNIX path too long；没有launch.json。0控制器、0正式GPU推理、0训练。18:54:08是目录登记时间，不是失败结束观测；用户未提供失败结束时间，不写成实时状态。

[修复协议](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)与[审计](../../records/phase24_ipc_path_fix_20261014/fix_audit.json)。用户使用修复提交的固定40位SHA，运行enqueue_phase24.py并显式指定--replace-ipc-path-bug-directory=<该原目录>。原代码/失败记录保留，不热改/删除；新独立目录先完整Linux CPU检查，成功才启动双卡smoke。当前尚无替换目录或smoke成功记录。

## 工程修复与验证边界
Python3.10默认文件socket的长TMPDIR路径超限，改为现有resource_sharer管理的短Linux抽象地址，带原process.authkey认证，保留FD claim/after-fork/关闭语义；无全局地址猴补丁、无/tmp回退、无新文件socket。未知ABI或已有文件listener明确hold。修复未登记状态查询和技术替换索引上传。

显式替换仅接受该目录/15f版本、原20测试18pass+两项路径错误、seal/code一致、预算相同且无任何launch/科学产物/存活worker或另一个队列。marker保证再运行只查询同一替换目录，不能再次启动失败科学配方。替换仍失败则hold，不自动继续。

本地26项：23通过、3项真实Linux运输待服务器；14文件编译通过。CPython3.10私有生命周期源码已核对，不能代替实际Linux验证；新注册必须26项全通过无skip。之后两卡真实梯度/原CM桥接/吞吐仍必须先验收。初版D0旧六差值复算一致仍有效；本轮没有新科学结果。

## 科学队列及资源不变
[原执行协议](../protocols/PHASE_24_EXECUTION_20261014.md)和[科学门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)：D0–D3、T0 clean8k、条件T1/T2各8k和再条件T3 8k；最多4小头32k，0新专家/训练seed，原B1/B3及L=False不重写。4k轨迹、8k固定主端点、不挑年龄或阈值。GPU0/1 ≥24h可续，无硬截止。

只读共享原9.792GB输入、每卡最多2匿名包/clean低logit缓存<1GiB/mask LRU8、source sample≤1GiB、CPU16/24/32按有效配额实测。临时产物用完回收，不恢复旧磁盘cache；计数复算后退役rolling/4k临时pth，必要8k及来源暂留待审。

## 研究决定、旧结果与交接
主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复旁支；当前识别DSM条件补救并保护强RGB。两重复Val2/seed42仅开发证据，跨tile源拟合不等于独立泛化。不以工程失败或oracle差否定整个互补问题，不加seed/专家凑时间，不用附属alignment参照作路线gate。

Phase2最后完成证据2026-10-14T00:39:03.210695+08:00，4核心训练48k、上传dc335e0d；原件/CM/汇总验收通过。[结果](../experiments/PHASE_2_RESULTS_20261014.md)。旧大缓存35910文件退役回执12:13:25.974504+08:00，必要权重/代码/原CM/输入/L坐标保留，不能再假设旧cache在线。服务器权重和L union仍限既有原件验收边界。

用户服务器执行，无SSH、Test6/held4/final或自动失败重跑。接收新登记打印的真实目录和最后观测后更新当前入口；成功结束用户显式运行upload_phase24.py，白名单轻量归档及GitHub回读，原失败记录不删。[修复前交接](../history/20261014_before_phase24_ipc_fix/HANDOFF.md)。
