# 随机返回Excel文件中的一行数据

## 接口说明
请求方式：GET
接口地址：/function/get_random_xlsx_line
参数：
  - filename: Excel文件名称（必须位于xlsx_files目录下）

## 返回值
  - 单列Excel：返回随机一行的字符串
  - 多列Excel：返回随机一行的所有列值（数组格式）
