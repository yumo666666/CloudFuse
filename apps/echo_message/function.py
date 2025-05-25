def echo_message(message: str):
    """
    单参数示例函数，回显输入的消息
    
    Args:
        message (str): 要回显的消息
    
    Returns:
        dict: 包含原始消息和时间戳
    """
    from datetime import datetime
    return {
        "original_message": message,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    } 