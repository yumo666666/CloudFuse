# 云函数开发与接入指南

本说明文档介绍如何为 CloudFuse 云函数管理系统添加和开发新函数。

---

## 1. 函数目录结构

每个函数需独立一个目录，目录名即为函数名，结构如下：

```
function_name/
├── function.py      # 函数实现（必需，需有同名函数）
├── config.json      # 函数API配置（必需）
├── intro.md         # 简要介绍（必需）
├── requirements.txt # 依赖（可选，自动安装）
├── readme.md        # 详细文档（可选）
└── xlsx_files/      # Excel文件目录（可选）
```

---

## 2. 必需文件说明

### function.py
- 必须包含一个与目录同名的函数。
- 支持参数类型注解和默认值。

示例：
```python
def example_function(param1: str, param2: int = 0):
    """示例函数"""
    return {"result": f"处理 {param1} 和 {param2}"}
```

### config.json
- 定义API接口信息、参数类型、描述等。

示例：
```json
{
    "url": "/function/example_function",
    "method": "GET",
    "name": "示例函数的简要描述",
    "parameters": [
        {"name": "param1", "type": "string", "required": true, "description": "第一个参数", "default": ""},
        {"name": "param2", "type": "number", "required": false, "description": "第二个参数", "default": "0"}
    ]
}
```

### intro.md
- 简要介绍函数用途和特点。

---

## 3. 可选文件说明

- **requirements.txt**：列出依赖包，系统自动检测并安装。
- **readme.md**：详细文档，建议包含用法、参数、返回值、示例等。
- **xlsx_files/**：如需处理Excel文件可放于此。

---

## 4. 支持的参数类型
- string
- number
- boolean
- array
- object

---

## 5. 示例

### 简单回显函数
```python
def echo_message(message: str = "Hello World"):
    return {"message": message}
```

```json
{
    "url": "/function/echo_message",
    "method": "GET",
    "name": "函数中文名",
    "parameters": [
        {"name": "message", "type": "string", "required": true, "description": "要回显的消息内容", "default": "Hello World"}
    ]
}
```

### Excel处理函数
```python
import pandas as pd
import random
import os

def get_random_xlsx_line(filename: str):
    file_path = os.path.join('xlsx_files', filename)
    if not os.path.exists(file_path):
        return {"error": "文件不存在"}
    df = pd.read_excel(file_path)
    random_row = df.iloc[random.randint(0, len(df)-1)]
    return random_row.to_dict()
```

---

## 6. 开发与调试建议

- 本地先测试函数逻辑，确保可用。
- 检查必需文件和参数类型。
- 返回值必须可JSON序列化，建议用dict。
- 依赖请写入 requirements.txt，系统自动安装。
- 错误处理要明确，建议 try-except。
- 上传/保存后可在Web界面直接测试。

---

## 7. 上传与管理

- 推荐通过 Web 管理界面上传/新建函数，系统自动校验、安装依赖、刷新路由。
- 也可手动将函数目录放入 apps/，重启服务或点击刷新。

---

## 8. 常见问题

- **依赖未安装**：请检查 requirements.txt 格式和包名。
- **参数报错**：请检查 config.json 参数类型和函数签名。
- **函数不可用**：请确保函数名与目录名一致，且有 function.py。
- **返回值异常**：请确保返回值可被 JSON 序列化。

---

## 9. 最佳实践

- 遵循 PEP8 规范，适当注释
- 合理设计参数和默认值
- 明确错误处理和返回格式
- 文档齐全，便于协作和维护