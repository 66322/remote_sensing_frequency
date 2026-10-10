# Post-N5交叉问题诊断执行协议（2026-10-06）

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run（准备执行包；服务器由用户执行）
- Verification Status: UNVERIFIED（新科学结果尚未运行；本地CPU17项与10文件语法已通过）
- Version Label: post_n5_cross_diagnostics_v1

## 本次范围
用户“按上述规划进行吧”授权落实[24—48小时条件规划](POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)。本包落实最先阶段：E3构成、N5后边界复查与E4-v2三因素分解；0次optimizer更新，不重启原N5/N2/诊断，不读取T/Test6/independent final/held4。R1/N3/S1须先接收诊断，按既有授权落实至多两个完整训练族；不是再次等待训练许可。本包没有虚构尚未实现的训练族为可运行任务。

最后服务器观测仍2026-10-06T21:16:59.632381+08:00 N5_COMPLETE_AWAITING_REVIEW。本包发布/CPU验证不代表服务器已登记、完成或有精度收益。

## 输入、源码与绑定
- 根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。
- 固定N5目录records/research_post_n5_20261006T114819_71934，执行2e565cca04d84d8605a96105d12fb6c0871e464d。
- 既有诊断目录records/research_post_n2_diagnostics_20261005T131434_3591073。
- E4固定模型N1-2、N2-0，N2-3预定旁证；只读各selected checkpoint，不新选模/训练。
- 执行快照继承原N5 code_manifest中全部文件，逐SHA验证；只添加本包文件，原科学源码不改。construct_model进一步核对各模型原源码、checkpoint/输入/配置绑定。N1-2固定SHA28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b。
- 已知Torch2.2.2+cu121环境、原DINO固定源码、Potsdam fit12/Val2=3_11、5_10，native512/stride256、推理batch8、FP32/TF32原口径。无新fit读取，本轮实际只读Val2与既有预测。
- 原U/H/L mask字节先验SHA核对，并与N5原mask解码内容逐像素相等；复制到本实验对应目录，不重新按结果生成掩码。

## E3与边界CPU阶段
A0/B1原E1、N5-0/N5-3内容评价既有candidate预测；U/H/L、RGB/DSM两方向、两tile，共16个构成结果文件。source complete/selected、case/预测/mask SHA与全tile NoBoundary CM独立重算匹配，才能进入后续。不从全局CM逆推像素分层。

类别0—4×边界/内部十层：边界为原Full真值4px带，正确率评价与权重使用NoBoundary有效fg5区域；缺失mask内每层支持至少100且三规则共同支持，权重为同一tile完整NoBoundary有效fg5类别×Full边界频率。记录全部原始CM/支持/正确数、共同支持、未覆盖权重与标准化正确率。它不是“校正后的mIoU”或因果结论，真值只在事后使用。

N5-0/N5-3 clean已有candidate+两个原固定anchor，分别两tile保存Full/NoBoundary边界、内部CM/joint与锚点正确并集harm/分母，先复算clean原CM。
N3门槛严格复用原E0：Full/4px，两侧正确并集边界/内部分母均≥100，两个单侧正确象限合计各≥100，每tile边界−内部harm≥1pp；两N5模型四项均过才保留N3问题。原E0历史结论不改判。

## E4-v2的8条路径
A输入清零×B中间特征支持×C局部输出硬回退，各0/1：
- A1：原报告mask清零。A0：保留接收到的物理输入；被真实遮挡的零值不会被恢复。
- B1：原N1三尺度投影与merge的valid_at相乘；N2另外保持relation中心与donor共同支持。B0：保留受损输入编码后的上下文特征，并让相应relation中心/donor参与；报告mask仍独立保留。没有读取遮前图/特征/标签。这个因素包含完整内部特征支持链，不能只说修改最后一层。
- C1：原逐像素单侧own-logit硬回退。C0：两模态均有可见像素的窗口局部保留raw融合。
- 若某512窗口一整模态被报告缺失，该样本所有A/B/C都走原输入清零、特征掩码和输出路径；这是一项明确的窗口级安全规则。两侧均不可见像素输出0，预测255。CPU验证含“整侧缺失＋另一侧局部缺失”组合。
- path=A1B1C1须与原E2已保存三种预测candidate/rgb/dsm逐像素完全一致；若不一致则HOLD，不能继续用新路径解释旧现象。
- 物理真实零块和完整物理输入误报两状态；报告缺失25%固定U，方向RGB/DSM，模型三个，tile两个：8×2×2×3×2=192新推理单元。每模型64，不复用原预测减少计数。
- 只保存三种uint8预测与原始计数；适配own分支joint是诊断，不能称不可变原anchor。
- 首个native512 padded batch保存收到输入、实际专家输入、报告mask、特征支持、relation支持、两侧feature、raw/result logits的shape/dtype/content SHA。它是首batch链路证据，不是整tile激活哈希；完整物理数组/报告mask另有全tile SHA。
- C开关上游hash一致、真实零块时A开关全部预测和首batch中间hash一致，作为工程负控制。检查所有case的物理/报告绑定跨路径一致。
- 原硬回退身份检查只对C1强制；C0主动改变局部输出，不误用旧infer保护断言。全缺失安全另外验证。

## 固定筛选与结束输出
RGB U真实缺失、NoBoundary fg5，按整数CM先逐tile池化：
- R1问题：A1B1C0−A1B1C1；N1-2/N2-0各pooled≥0.5pp且各两tile严格正。
- S1问题：A1B0C0−A1B1C0；同两模型/阈值/两tile条件。
- N2-3与DSM固定全量报告，不替换失败主模型/方向；原E2 gate=False不改变。
- 全部192case的int64 6×6、derived metrics、joint边际、case/预测SHA、tile池化和complete绑定复核后输出cross_screen.json。
- 候选族按预先优先级R1→N3→S1选至多两个，不按最高观测收益选；最大9训练作业只是后续预算，当前optimizer更新0。
- 最终CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW；退出并等待原件接收/诊断分析，再冻结并实现所选训练协议。按规划科学阶段推进，不是把未实现的族直接派发。
- 两tile/seed42为开发证据，差值门槛不是显著性标准；不报告像素伪重复p值，不承诺正结果或论文贡献。

## 登记、队列与失败规则
入口scripts/enqueue_post_n5_cross.py --root ROOT --commit PINNED_COMMIT。
启动前核对旧N1/N2/诊断/N5完成、PID身份与锁释放；查询本类既有登记，有则只报告，不能重复启动。注册锁与共享successor lease防竞态。
新目录records/research_post_n5_cross_<timestamp>_<pid>，记录/代码/cache/temporary/log全部留在该目录。不修改工作树或原实验。运行器解释器沿用户已知plan python，不重复资源审计。

服务器登记前执行本包17项CPU检查（300秒），成功后才nohup控制器。CPU阶段GPU不可见，6小时正有限超时；E4每模型8小时正有限超时。两卡仅GPU0/1、每卡一worker，两波。仅核对GPU身份/占用以防碰撞，无资源容量重新审计。
控制器持有共享lease，CPU复查→E4三作业→独立summarize子进程→最终退出。模型CPU检查不能代替派发/汇总入口；本包同时检查两个lane、完成退出、失败禁止新派发、已有产物拒绝、terminate/kill及超时rc0也不能算成功、完整192case standalone汇总和六个独立入口import/--help。
技术故障停止新派发，已有另一worker允许结束；控制器意外退出可能留下detached worker，原目录保留、人工诊断后明确接管，不自动重试/续跑。不重复调用登记来恢复。硬超时terminate后60秒kill；不按loss/指标自动停。

暂估CPU/IO+E4约2—4小时；不是实测/完成承诺，本地CPU约60秒仅说明检查时间。R1/N3/S1的9—20小时族预算不计入当前诊断登记，也未启动一两天训练队列。

## 记录与上传
status_post_n5_cross.py只读，打印QUERY_OBSERVED及queue LAST_OBSERVED，分别标注，不能把旧快照当实时。
完成后用户调用upload_post_n5_cross_records.py，显式Git上传轻量JSON/日志/快照，含E3和E0_postN5；gzip-base64-exact-v1保原字节。不上传.npy/.npz/.pth，只留SHA/大小/服务器索引，512MiB轻量bundle上限；独立detached工作树位于本实验目录，非force推同一分支，冲突则保留停止。自动队列不保存/索取凭据、不自动推送。
接收后独立复算及结论/当前交接继续同步GitHub并回读。
