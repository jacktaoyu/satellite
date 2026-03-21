def remove_blank_lines(input_file, output_file=None):
    """
    删除文本文件中的空行
    
    Args:
        input_file (str): 输入文件路径
        output_file (str, optional): 输出文件路径。如果未指定，将覆盖原文件
    
    Returns:
        None
    """
    # 读取文件内容
    with open(input_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # 过滤掉空行
    non_blank_lines = [line for line in lines if line.strip()]
    
    # 确定输出文件路径
    if output_file is None:
        output_file = input_file
    
    # 写入文件
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(non_blank_lines)

if __name__ == '__main__':
    import sys
    
    # if len(sys.argv) < 2:
    #     print("使用方法: python blank_line.py <输入文件> [输出文件]")
    #     sys.exit(1)
    
    # input_file = sys.argv[1]
    # output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        remove_blank_lines(r"D:\Satellite\library\tlerr.txt")
        print("空行删除成功！")
    except Exception as e:
        print(f"发生错误: {str(e)}")
