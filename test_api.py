import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_api():
    # 测试获取所有函数列表
    print("\n1. 测试获取函数列表:")
    response = requests.get(f"{BASE_URL}/functions")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

    # 测试获取特定函数的帮助信息
    print("\n2. 测试获取函数帮助信息:")
    response = requests.get(f"{BASE_URL}/function/get_random_xlsx_line/help")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

    # 测试随机获取Excel行数据
    print("\n3. 测试随机获取Excel数据:")
    response = requests.get(f"{BASE_URL}/function/get_random_xlsx_line?filename=中国近现代史dan'xuan.xlsx")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_api() 