'''
为分类任务构建数据集
包括数据计算、分析、筛选
'''
import json
from tqdm import tqdm
import pickle
import numpy as np
import time
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter
from multiprocessing.dummy import Pool as ThreadPool
from logging import config, getLogger
from log_config import LOGGING_DIC
import ipdb

from scorer import rouge_between_strings

config.dictConfig(LOGGING_DIC)
# logger = getLogger('production') # 生产环境使用的logger，输出内容到文件
logger = getLogger('production') # 测试使用的logger，输出内容到终端
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号
start_time = time.time()

def read_train_titles(train_path):
    '''读取codebert json文件'''
    titles = []
    with open(train_path, 'r', encoding='utf-8') as f:
        for line in f:
            js = json.loads(line.strip())
            title = ' '.join(js['docstring_tokens'])
            titles.append(title)
    return titles

def make_triplet_titles(titles):
    '''构造下三角样式的title列表，用于计算rouge分数'''
    lines = []
    t = tqdm(total=len(titles))
    for i, _ in enumerate(titles):
        line = titles[:(i+1)]
        lines.append(line)
    return lines

def plot_histogram(x, distance=0.05):
    '''
    x is a list containing numbers
    distance is an int number indicating the x-axis distance
    '''
    d = distance
    plt.figure(dpi=300)
    min_x = min(x)
    max_x = max(x)
    range_by_d = np.arange(min_x, max_x + d, d)
    plt.hist(x, range_by_d, weights=np.ones(len(x))/len(x))
    plt.xticks(range_by_d)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.grid()
    plt.savefig('plot.png')

def save_load_pickle(path, content=None):
    if not content:
        with open(path, 'rb') as f:
            content = pickle.load(f)
            return content
    with open(path, 'wb') as f:
        pickle.dump(content, f)


def calc_one_against_all(titles):
    gold_title = titles[-1]
    scores = []
    # t = tqdm(total=(len(titles)-1))
    for i in titles[:-1]:
        rouge_score = rouge_between_strings(gold_title, i)
        scores.append(rouge_score)
        # t.update(1)
    scores.append(0.99)
    end_time = time.time()
    logger.info(f'完成第{len(titles)}行，累计花费{round(end_time-start_time, 2)}秒')
    # t.close()
    return scores



def calc_rouge_all(tri_titles):
    pool = ThreadPool()
    results = pool.map(calc_one_against_all, tri_titles)
    pool.close()
    pool.join()
    return results


if __name__ == '__main__':
    train_path = 'data/dataset/Python/codebert.python.a1s2.both.lte1000.match-gao.train.jsonl'
    # titles = read_train_titles(train_path)
    # scores = calc_one_against_all(titles)
    # scores = save_load_pickle('scores.pkl')
    # plot_histogram(scores)
    # tri_titles = make_triplet_titles(titles)

    tri_titles = save_load_pickle('class_data/tri_titles.pkl')
    logger.info(f'加载tri_titles完毕')
    content = calc_rouge_all(tri_titles)
    save_load_pickle('class_data/tri_scores.pkl', content)

    # tri_scores = save_load_pickle('class_data/tri_scores.pkl')
    # ipdb.set_trace()
    # print()
    
