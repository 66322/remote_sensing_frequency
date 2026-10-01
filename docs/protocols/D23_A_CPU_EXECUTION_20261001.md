# D23-A CPU诊断执行说明

日期2026-10-01。代码已实现，7项本地合成测试通过；真实服务器profile与计数尚未执行。D23-B gate没有实现/训练。用户明确由其在服务器终端执行。

## 范围与资源

只读取D21 Potsdam seed42 R0/M0：Val2 3_11/5_10 ×5条件，共20个已有预测；固定label-informed互补诊断不能部署，不是理论mIoU上界。FullGT及NoBoundary每tile原始混淆矩阵必须与D21摘要逐元素一致，输出truth×R0×M0 int64联合计数、缺失/有效区域、harm/rescue、逐类原始计数与同回退结果。原专家、预测和GT只读，不导入torch、不训练、不做新推理、不加载Test6/独立final。

复用NumPy、Pillow和Python标准库，不安装依赖。检查D21原训练/评价签名、固定checkpoint SHA，并读取权重字节重新hash；GT绑定原D21 input_manifest SHA及逐GT SHA；每npy绑定原预测SHA及tile JSON。NoBoundary黑色=255；类别无有效并集时按原代码nanmean；局部缺失沿d18_replication.availability的中央区域定义。

先profile一tile/clean，两scope与真实资源。每进程总时间保护1800秒、峰值RSS保护2GiB，输出预计<10MiB；检查在分块/hash/标签读后执行，是监测保护，不保证底层读调用瞬间不会超额。full必须读取同脚本、同root、同输入绑定的成功profile，并要求预计耗时≤1800秒。估计=本次绑定耗时+单pair耗时×10，是保守开发估计，不是实际工时保证。任一缺文件、错绑定、原计数不一致或超限保留failure.json，属于技术失败，不解释为研究负结论。

输出目录带时间戳和进程ID，子目录禁止覆盖；profile/full分开归档，保留日志和脚本临时副本。Git只fetch并提取已审核脚本，**不切分支或更新服务器工作副本**。采用D21 plan.json记录的Python路径，不猜测旧conda环境。不影响冻结D21源码。

## 可复制执行命令

脚本SHA256：04435db2bf0c21351e5684daa1588481c0cfdcd97a5a952585c2c7c89957b74d。若服务器branch还没有本次脚本，或Git提取后SHA不同，停止；不要忽略校验或自动替换环境。

```bash
set -e
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git fetch origin rebuild-v1-protocol-20260915
D23_REV=$(git rev-parse FETCH_HEAD)
D23_TMP=$(mktemp -d /tmp/d23-a-20261001.XXXXXX)
git show "$D23_REV:scripts/audit_rebuild_v1_d23_complementarity.py" > "$D23_TMP/audit_d23.py"
printf '%s  %s\n' '04435db2bf0c21351e5684daa1588481c0cfdcd97a5a952585c2c7c89957b74d' "$D23_TMP/audit_d23.py" | sha256sum -c -
D23_PY=$(python -c 'import json; print(json.load(open("records/rebuild_v1_d21_queue_20260928/plan.json"))["python"])')
test -x "$D23_PY"
D23_OUT="$PWD/records/research_d23_feasibility_20261001_$(date +%Y%m%dT%H%M%S)_$$"
mkdir "$D23_OUT"
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1
"$D23_PY" -B "$D23_TMP/audit_d23.py" --root "$PWD" --output "$D23_OUT/profile" --mode profile > "$D23_OUT/profile.log" 2>&1 || { cat "$D23_OUT/profile.log"; exit 1; }
cat "$D23_OUT/profile.log"
"$D23_PY" -B "$D23_TMP/audit_d23.py" --root "$PWD" --output "$D23_OUT/full" --mode full --profile "$D23_OUT/profile/profile.json" > "$D23_OUT/full.log" 2>&1 || { cat "$D23_OUT/full.log"; exit 1; }
cat "$D23_OUT/full.log"
printf 'D23_OUTPUT=%s\n' "$D23_OUT"
```

请回传profile.log最后几行、full.log中的D23_A_DECISION以及D23_OUTPUT路径；报错则回传failure.json与日志。无需传权重或所有预测。完整decision.json与10份tile-condition JSON应补归档再作研究判断。

## 结果判定

三available条件的不可部署诊断相对较强R0/同回退M0增益平均≥0.5pp，且rgb_down4增益>0，才eligible_to_prepare_B=true；该字段只允许准备B，不启动训练。没有空间就关闭此固定专家组合的gate方案，不扩大为DSM或可靠性问题无效。旧门槛不更改。

## 本地验证边界

7项测试覆盖随机像素与独立循环、uint8/uint64和跨chunk边界、完整缺失回退、无效预测类别（含GT忽略区）、六色/黑色/非法标签、缺类nanmean、profile→full端到端且拒绝覆盖、预测与checkpoint篡改拒绝。端到端fixture只有小型合成标签/预测和伪权重字节，测试中替换固定SHA；不是服务器真实数据审计或精度结果。
