import pandas as pd
import random
import os

def get_random_xlsx_line(filename: str):
    """
    从Excel文件中随机获取一行数据
    
    Args:
        filename (str): Excel文件名
    
    Returns:
        dict: 包含随机行数据的字典
    """
    try:
        file_path = os.path.join("apps", "get_random_xlsx_line", "xlsx_files", filename)
        df = pd.read_excel(file_path)
        
        if df.empty:
            return {"error": "Excel文件为空"}
            
        # 获取随机行
        random_row = df.iloc[random.randint(0, len(df)-1)]
        
        # 只返回题目内容（第一列）
        if len(df.columns) > 0:
            question = random_row[df.columns[0]]
            return {"data": question}
        else:
            return {"error": "Excel文件格式不正确"}
        
    except Exception as e:
        return {"error": str(e)}