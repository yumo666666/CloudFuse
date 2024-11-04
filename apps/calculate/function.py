def calculate(num1: float, num2: float, operation: str = "add"):
    """
    多参数示例函数，执行基本的数学运算
    
    Args:
        num1 (float): 第一个数字
        num2 (float): 第二个数字
        operation (str): 运算符(add/subtract/multiply/divide)
    
    Returns:
        dict: 包含计算结果和运算说明
    """
    operations = {
        "add": (lambda x, y: x + y, "加"),
        "subtract": (lambda x, y: x - y, "减"),
        "multiply": (lambda x, y: x * y, "乘"),
        "divide": (lambda x, y: x / y if y != 0 else "除数不能为0", "除")
    }
    
    try:
        if operation not in operations:
            return {"error": "不支持的运算符"}
            
        func, op_name = operations[operation]
        result = func(float(num1), float(num2))
        
        return {
            "result": result,
            "description": f"{num1} {op_name} {num2} = {result}"
        }
    except Exception as e:
        return {"error": str(e)} 