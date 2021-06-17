from tqdm import tqdm
from multiprocessing import Pool

def for_line_in(file_path, length, bulk_size, func, *args, **kwargs):
    '''
    批量处理独立不相关的数据行
    '''
    with open(file_path, mode='r', encoding='utf-8') as f:
        t = tqdm(total=length)
        line_no = 1
        lines = []
        for line in f:
            if len(lines) == bulk_size:
                func(lines, line_no, *args, **kwargs)
                t.update(bulk_size)
                lines = []
                line_no += bulk_size
            lines.append(line)
        if len(lines) != 0:
            func(lines, line_no, *args, **kwargs)
            t.update(len(lines))
        t.close()

def append_file(data):
    '''
    续写文档:
    data是一个元组：(file_path, content)
    content 是一个列表，其中的内容不包括换行符
    '''
    if not data:
        return
    file_path, content = data
    content_with_line_feed = [f'{line}\n' for line in content]
    with open(file_path, mode='a', encoding='utf-8') as f:
        f.writelines(content_with_line_feed)



# def async_for_line_in(file_path, length, func):
#     '''
#     废弃不用
#     多进程处理独立不相关的数据行
#     '''
#     pool = Pool(8)
#     with open(file_path, mode='r', encoding='utf-8') as f:
#         line_no = 1
#         for line in f:
#             pool.apply_async(func, args=(line, ), callback=append_file)
#             line_no += 1
#         pool.close()
#         pool.join()
