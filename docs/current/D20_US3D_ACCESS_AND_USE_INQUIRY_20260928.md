# D20 US3D/DFC2019 Track 1：获取与使用条件待确认

## 已知状态

服务器尚无 RGB/AGL/CLS 三元组；GRSS 和 IEEE DataPort 在服务器代理下返回 403。官方 JHU/APL Track-1 torrent 元数据可达，数据包仍未下载。既有 Hugging Face 私有中转在技术上可行，但**未取得数据方对 DFC2019 原始包经第三方云中转的许可**。官方 [2019 DFC 条款](https://www.grss-ieee.org/community/technical-committees/2019-ieee-grss-data-fusion-contest/)禁止注册用户传播数据包，并要求使用数据发表论文时逐案获批；网页给出的论文审批邮箱为 `iadf_chairs@grss-ieee.org`。这不是对任何具体中转方式的许可判断。

## 需要官方明确回答的四项

1. 当前如何以研究用途注册、取得 `Train-Track1-RGB.zip` 和 `Train-Track1-Truth.zip`，以及竞赛结束后的非竞赛研究是否允许在论文审批前开展。
2. 服务器无法直连 DataPort 时，是否有官方直接下载或其他**不发生用户再分发**的路径。
3. 若只能由同一注册研究者从可访问网络下载，再经该研究者控制的私有 Hugging Face 仓库传到计算服务器，该具体做法是否获准；没有书面明确答复前不执行。
4. 论文使用审批应在何时申请、提交哪些材料；是否可公开源代码、模型产生的汇总整数指标、配置与原始文件哈希（不含原始影像、标签或权重）。

## 可发送的英文询问草稿（未发送）

Subject: DFC2019 Track 1 research access and permitted transfer route

Dear IEEE GRSS IADF TC,

Our research group is planning a study that compares optical-only and optical-plus-height semantic segmentation using the DFC2019 Track 1 training data. We would need only the Train-Track1-RGB and Train-Track1-Truth packages. Our compute server currently receives HTTP 403 responses when accessing the GRSS and IEEE DataPort pages.

Could you advise on the current registration and direct download procedure, and whether research use before a manuscript is submitted is permitted? If direct server download remains unavailable, is a transfer through a private Hugging Face repository controlled by the same registered researcher permitted under the data terms? We would not use that route without your explicit authorization. Please also advise when and how to request approval for a scientific publication, and whether code, configuration, file checksums and aggregate experimental metrics may be made public without sharing any source data.

Thank you for your guidance.

Sincerely,
[Researcher name, institution, contact email]

## 决策记录要求

发送者、日期、所获条款版本、完整回复与允许/禁止的具体路线应保存在服务器 `zzx` 项目记录下；GitHub 只记录许可结论、联系时间、审批状态和非敏感摘要。若官方确认 US3D 无法用于本研究，再按 D20 协议对 Houston 做一次来源准入；在此之前不重跑 Vaihingen seed42，也不补 seed17。
