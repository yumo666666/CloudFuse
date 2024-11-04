import pandas as pd

# 创建示例数据
data = {
    '名言': [
        '千里之行，始于足下',
        '学而不思则罔，思而不学则殆',
        '工欲善其事，必先利其器',
        '不积跬步，无以至千里',
        '读书破万卷，下笔如有神'
    ],
    '作者': [
        '老子',
        '孔子',
        '孔子',
        '荀子',
        '杜甫'
    ]
}

# 创建DataFrame并保存为Excel
df = pd.DataFrame(data)
df.to_excel('apps/get_random_xlsx_line/xlsx_files/famous_quotes.xlsx', index=False)
print("示例文件已创建完成！") 