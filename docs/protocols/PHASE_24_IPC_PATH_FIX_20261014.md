# Phase2.4登记期IPC路径修复（2026-10-14）

状态：**IPC_PATH_FIX_READY_AWAITING_SERVER_REGISTRATION_CHECKS**。这不是新科学配方或训练重试。

## 已观测事故

用户回传目录 research_phase24_protected_20261014T185408_2127460（目录登记时间18:54:08+08:00，不代表检查结束时间）的CPU日志：20项中18项数值/梯度/协议检查通过，test_cross_process_readonly 与 test_roundtrip_and_last_close 均为 OSError: AF_UNIX path too long；无launch.json，登记进程退出。没有启动控制器、正式GPU推理或训练，优化器更新0。来自[用户回传摘录](../../records/phase24_ipc_path_fix_20261014/user_cpu_log_excerpt.txt)，未宣称已逐byte接收服务器原log。

Python3.10 resource_sharer默认在TMPDIR下生成AF_UNIX文件socket；长实验目录叠加pymp/listener名称超出地址限制。所有记录必须保存在zzx对应实验目录，不能通过改到/tmp绕过这一规则。Windows初版跳过的两项正是服务器暴露此兼容性问题的检查。

## 修复范围和生命周期

Packet.descriptor先以现有resource_sharer锁初始化明确的、带进程authkey认证的Linux抽象AF_UNIX Listener。地址以NUL开头，短ASCII进程标识加系统随机token，不含实验路径，不创建文件socket。系统随机token只用于通信命名，不改变训练/采样seed。仍由CPython原resource_sharer持有claim缓存、发送/关闭dup fd、处理after-fork与进程结束清理；不替换其服务循环，不全局改arbitrary_address。已有文件socket或不匹配的私有字段明确报错，不静默fallback。

私有字段接口已核对[CPython3.10 resource_sharer](https://github.com/python/cpython/blob/3.10/Lib/multiprocessing/resource_sharer.py)与[connection](https://github.com/python/cpython/blob/3.10/Lib/multiprocessing/connection.py)；bytes抽象namespace和不unlink分支受支持。实际服务器26项检查仍须执行，不能用源码核对代替Linux验证。TMPDIR及其他临时/缓存/记录目录不改变。

数值、科学gate、split、退化、原专家/初始化/数据流/优化器、4k/8k口径均保持；最多4小头32k，0新专家/追加训练seed，GPU0/1，无Test6/held4/final及24h硬截止。另修复未生成queue_status时的状态查询，归档白名单增加technical_replacement.json。

## 单次显式技术替换

原目录原代码、seal、失败log保留；不热改冻结代码、不删除、不改成成功状态。用户在新固定提交的enqueue_phase24.py显式传入：

--replace-ipc-path-bug-directory /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_20261014T185408_2127460

仅接受这个已观测目录和原执行15fdfa4c完整版本。要求：plan/code/registration SHA一致、科学预算不变、原20项恰好18项ok且仅上述两项ERROR、两个路径错误栈、无launch/queue_status/成功smoke/科学产物/权重、无原目录存活进程，且没有其他Phase2.4登记。缺一拒绝替换。原失败log/manifest的真实SHA由服务器检查时记录到新plan与technical_replacement.json。

全局登记锁保护创建。生成新独立目录，并在原目录写单次replacement marker；此参数再次执行只查询已生成的替换目录，不再创建任务。新尝试若再次技术失败，仍hold，没有自动再替换。若GPU0/1忙，则不创建新目录或marker；释放资源后可以再次执行同一准入命令。

新的26项Linux CPU检查必须全部通过、无skip，然后才启动控制器；双卡CUDA梯度、12个原CM桥接和吞吐检查仍排在正式任务之前。无额外人工阶段派发。新的运行目录/日志由命令输出，不能沿用旧失败目录查看运行进度。

## 本地验证和下一观测

Windows/Python3.13.3/Torch2.7.1+cpu：26项中23通过、3个真实Linux运输检查跳过；14个Python文件编译通过。新增检查覆盖短地址/认证/幂等、拒绝文件socket/未知私有ABI、仅无科学启动的已知失败允许替换、拒绝改seed或其他失败；Linux额外检查强制get_temp_dir不可调用，测试通信不会退回长文件路径。[修复审计](../../records/phase24_ipc_path_fix_20261014/fix_audit.json)。

仍等待用户执行新固定SHA命令，接收实际新目录和全部Linux/CUDA检查记录。当前不存在已启动替换队列的证据；本文件的ready不表示实时GPU运行。研究主线和原C/L/原B1/B3决定不因工程登记错误改变。
