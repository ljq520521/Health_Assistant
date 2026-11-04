# 随项目分发的公共参考目录

本目录仅包含从既有 v3 课程演示数据包构建的公开食品和菜谱，不是用户数据库。

保留 `food_catalog.db`、`catalog-release.json`、`SHA256SUMS.txt` 三个文件作为同一发布单元。数据库以只读方式打开；新克隆无需数据导入。

校验分为两层：发布数据库的文件 SHA256 必须与本目录两份清单一致；跨平台重建时比较规范化逻辑内容哈希、表结构和逐表完整记录（包含 NULL 与原始营养值）。SQLite 版本差异可能改变文件头和页布局，因此不要求不同平台重建文件的字节与发布文件相同。同一构建环境连续重建仍须字节一致。重建结果不能覆盖发布文件或擅自更新发布校验值，完整性、外键、来源及数量校验始终保留。

来源：U.S. Department of Agriculture, Agricultural Research Service. FoodData Central。
134 种食品的原始来源记录、FDC ID、营养值和来源 SHA256 均保留。12 道菜谱为团队自编、AI 辅助、未经实际试做，营养为投料估算。课程演示批准不代表医学、生产用途或过敏安全认证。

来源许可沿用 [v3 数据来源与许可](../seed_data/usda_v3_course_demo/LICENSE-SOURCES.md)，不另行扩张团队菜谱或中文整理内容的许可证。

完整架构、API、迁移及临时验收说明见 [PUBLIC-CATALOG.md](../docs/PUBLIC-CATALOG.md)。
