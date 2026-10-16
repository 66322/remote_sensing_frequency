# D20 修订版 GAMUS 公开来源与地理索引案头核查

## 核查范围

本次仅查公开文档和仓库，不下载数据或访问 Test6。修订版数据固定 revision 为 `a3c0e2511f06d909612406f436cf8abb4da805f5`；服务器九文件 HDF5 属性审计见[结果](../experiments/D20_GAMUS_SAMPLE_METADATA_RESULTS_20260928.md)。以下“未找到”仅限所列材料，不代表原始发布者没有相应资料。

| 来源 | 可核对事实 | 尚缺证据 |
|---|---|---|
| [作者 GAMUS 仓库，`6ed44ba`](https://github.com/EarthNets/RSI-MMSegmentation/tree/6ed44ba87b59911144430ebc0ca02c1f7a1c62b4) | README 指向修订版 `XShadow/GAMUS`（现跳转 `earthflow/GAMUS`），说明已移除旧版 DFC2019 的 OMA/JAX；数据加载器按文件名配对 `image` 数组。 | README 和加载器没有三城逐模态原始数据 URL、文件 stem 到地理范围／CRS 的映射或上游权利清单。 |
| [固定 revision 数据仓库](https://huggingface.co/datasets/earthflow/GAMUS/tree/a3c0e2511f06d909612406f436cf8abb4da805f5) | 根目录为 `images/`、`heights/`、`classes/`、`.gitattributes` 和 131 字节 README；README 仅有 `cc-by-4.0` 标签和作者加载器链接。前次 Stage A 已核对文件名清单配对及三城小样本。 | 未见发布的坐标索引、逐城市处理说明或逐原始来源授权表。Hub 许可标签不能单独确定底层影像、LiDAR 与标签的权利。 |
| [旧版论文，§3.1](https://arxiv.org/html/2305.14914v1) | 概述 Data DC 和费城开放数据，以及 LiDAR 点云处理为 nDSM／部分标签的流程；论文描述的旧版包括已移除的 OMA/JAX。 | 没有逐文件绑定修订版 DC／PHL／NYC 的原始资产、年份、许可和地理范围；尤其不能由该段推断 NYC 的具体来源。 |
| [Dataset4EO GAMUS 导入代码，`db7983f`](https://github.com/EarthNets/Dataset4EO/blob/db7983f4273d2b2c10557bd824b6649efeae02c0/builtin_datasets/GAMUS/collect_data.py) | 将 HDF5 的 `image` 数组与 basename 转成流式样本；其 metadata 只列样本名、图像、类别、高度。 | 不补充原始地理范围、CRS、来源条款或跨 split 空间关系。 |
| [九文件服务器审计](../experiments/D20_GAMUS_SAMPLE_METADATA_RESULTS_20260928.md) | DC／PHL／NYC 各一组三元组的 HDF5 根节点和 `image` 数据集属性均为空，并与 Stage A SHA 绑定。 | 仅九个样本；不能推断全量文件的属性或地理关系。 |

## 决策边界

目前可确定三城小样本可读、文件名清单配对，但**来源准入仍待定**。不能把城市前缀、Hub 许可标签或旧版论文直接升级为修订版全量数据的地理与权利证明。若仅按城市整体划分，前缀可作为候选分组；冻结前仍需确认这些前缀确实对应互不重叠的地理区域，并明确作者是否允许相关学术使用。任何同城内部 fit/dev 划分还需要瓦片范围或等价空间索引。此时不下载全量数据、不启动 GPU、不访问 Test6。

## 未发送的作者询问稿

下面文本可发给数据作者或维护者；目前仅为草稿，**尚未发送**。不请求受限原始数据包。

> Subject: Provenance and geographic indexing for the revised GAMUS release
>
> Dear GAMUS team,
>
> We are assessing the revised GAMUS release linked from your RSI-MMSegmentation repository (`earthflow/GAMUS`, revision `a3c0e2511f06d909612406f436cf8abb4da805f5`) for an academic RGB–height segmentation study. Before defining geographically independent training, development and final evaluation areas, could you clarify:
>
> 1. For DC, PHL and NYC separately, which original RGB imagery, LiDAR/height and semantic-label datasets were used (publisher, dataset URL, acquisition year and applicable use or attribution terms)? Does the release's CC BY 4.0 label cover all derived files, and are there additional publication conditions?
> 2. Is there a file-stem-to-geographic-bounds/CRS or original tile-ID index, or a reproducible crop-grid rule, for the revised release? If not public, could you share the metadata alone?
> 3. Can patches from different original train/val/test folders overlap or be adjacent within the same city? Are any duplicate scenes present across those folders?
> 4. Did the revised release change the class mapping or data provenance beyond removing OMA/JAX? Is there a recommended citation for this specific release?
>
> We are only asking for provenance and indexing information, not for any restricted raw imagery or point clouds. Thank you.

收到答复后逐项链接原始来源、核对使用条件，并决定是否能冻结城市级或同城空间隔离划分。若作者无法提供映射，可考虑只用城市整体分组并清楚说明证据限制；其适用性仍需在训练前单独审查。
