## 文件说明
- log_config.py 配置logging
- file_helper.py 文件相关操作
- statistic_tool.py 统计stackoverflow dump数据
- elastic_tool.py 封装elastic相关操作
- Statistics.md 数据统计结果
## 环境配置
```bash
pip install -r requirements.txt
```
- 视情况修改 log_config 中的 `logfile_name` 
- 视情况修改 elastic_tool 中的 `logger`, `HOST`, `INDEX_NAME`与`DOC_TYPE`
## 工作流
1. fork 为自己的仓库

2. 在自己的仓库修改代码

3. 提交pull request到zfj1998的仓库

## 待办
- [ ] 在 'so_posts_all.python' 数据库中检索出现在 'XXSO.python' 中的数据，得到对应的elastic_id
  - 质量需求：1. 可观的性能 2. 较高的可信度
  - 难点：1. 如何计算匹配度 2. 如何验证匹配的准确度