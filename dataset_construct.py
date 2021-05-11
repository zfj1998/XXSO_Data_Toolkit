'''
构造数据集，主要包括两个函数
1. attr_extractor
主要用于过滤优质问题，输入输出都是xml文件
2. content_extractor
主要用于过滤不符合文本+代码、长度要求、和其它tag重复的内容，输入为xml，输出为json
'''
import xmltodict
import ipdb
import datetime
from collections import Counter, OrderedDict
from tqdm import tqdm
import html
import json
from html.parser import HTMLParser
from transformers import RobertaTokenizer
import time
import numpy as np
from matplotlib import pyplot as plt
from matplotlib.ticker import PercentFormatter

BATCH_SIZE = 1000
LANGUAGES = set(['<javascript>', '<go>', '<c#>', '<php>', '<ruby>', '<java>', '<python>'])

special_tokens_id = list(range(33, 48))
special_tokens_id += list(range(58, 65))
special_tokens_id += list(range(91, 97))
special_tokens_id += list(range(123, 127))
special_tokens = [chr(i) for i in special_tokens_id]

def convention_tokenize(text):
    '''
    针对特殊符号分词
    '''
    for st in special_tokens:
        text = f' {st} '.join(text.split(st)).strip()
    tokens = text.split()
    return tokens

def plot_histogram(x, distance):
    '''
    x is a list containing numbers
    distance is an int number indicating the x-axis distance
    '''
    d = distance
    plt.figure()
    min_x = int(min(x))
    max_x = int(max(x))
    range_by_d = range(min_x, max_x + d, d)
    plt.hist(x, range_by_d, weights=np.ones(len(x))/len(x))
    plt.xticks(range_by_d)
    plt.gca().yaxis.set_major_formatter(PercentFormatter(1))
    plt.grid()
    plt.show()

class OrderedCounter(Counter, OrderedDict):
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, OrderedDict(self))

def write_lines(lines, target):
    with open(target, 'a', encoding='utf-8') as f:
        f.writelines(lines)

def line_counter(source_path):
    '''
    简单统计文件行数
    '''
    count = 0
    with open(source_path, 'r', encoding='utf-8') as f:
        for line in tqdm(f):
            count += 1
    print(f'{source_path} total {count} lines')
    return count

def include_extractor(
        source_path, target_path,
        filters, total_line_count=None
    ):
    '''
    根据包含关系抽取数据行
    '''
    result = []
    target_line_count = 0
    if not total_line_count:
        total_line_count = line_counter(source_path)
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_line_count)
        for line in f:
            t.update(1)
            flag_to_keep = True
            for fltr in filters:
                if fltr not in line:
                    flag_to_keep = False
            if not flag_to_keep:
                continue
            result.append(line)
            target_line_count += 1
            if len(result) == BATCH_SIZE:
                write_lines(result, target_path)
                result.clear()
        t.close()
    if result:
        write_lines(result, target_path)
    print(f'{target_path} total line {target_line_count}')

def attr_counter(source_path, attr, total_line_count=None, condition_func=lambda x: True):
    '''
    根据属性统计数量特征
    '''
    counts = []
    if not total_line_count:
        total_line_count = line_counter(source_path)
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_line_count)
        for line in f:
            line_json = xmltodict.parse(line)
            if condition_func(line_json['row']):
                counts.append(line_json['row'][attr])
            t.update(1)
    t.close()
    count_result = Counter(counts).most_common()
    percentage_result = dict()
    accumulative_count = dict()
    # for item in count_result:
    #     percentage_result[item[0]] = round(item[1]/total_line_count, 2)
    for item in count_result:
        bigger_count = 0
        for comparable_item in count_result:
            if int(comparable_item[0]) >= int(item[0]):
                bigger_count += comparable_item[1]
        accumulative_count[item[0]] = bigger_count
    print(total_line_count)
    # print(count_result)
    # print(percentage_result)
    print(accumulative_count)
    return count_result, percentage_result, accumulative_count

def attr_extractor(
        source_path, target_path,
        condition_func, total_line_count=None
    ):
    '''
    按照属性条件进行抽取
    '''
    result = []
    if not total_line_count:
        total_line_count = line_counter(source_path)
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_line_count)
        for line in f:
            line_json = xmltodict.parse(line)
            if condition_func(line_json['row']):
                result.append(line)
            if len(result) == BATCH_SIZE:
                write_lines(result, target_path)
                result.clear()
            t.update(1)
        t.close()
    if result:
        write_lines(result, target_path)

def time_counter(source_path, total_len):
    '''
    按年/月统计问题数量
    '''
    by_month = []
    by_year = []
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        for line in f:
            # line_json = xmltodict.parse(line)
            # time_str = line_json['row']['@CreationDate']
            line_json = json.loads(line.strip())
            time_str = line_json['@CreationDate']
            time_obj = datetime.datetime.strptime(time_str,'%Y-%m-%dT%H:%M:%S.%f')
            # by_month.append(time_obj.strftime('%Y-%m'))
            by_year.append(time_obj.strftime('%Y'))
            t.update(1)
    t.close()
    # print(OrderedCounter(by_month))
    print(OrderedCounter(by_year))

'''
解析post body中的html标签
'''
class BodyParser(HTMLParser):
    def __init__(self):
        super(BodyParser, self).__init__()
        self.result = []
        self.current_tag = None
        self.current_text = ''
        self.current_code = ''

    def simplify_tag(self, tag):
        if tag == 'code':
            return tag
        return 'text'

    def handle_starttag(self, tag, attrs):
        tag = self.simplify_tag(tag)
        if not self.current_tag:
            self.current_tag = tag
            return
        if tag == 'code' and tag != self.current_tag:
            self.result.append(('text', self.current_text))
            self.current_text = ''
        elif tag == 'text' and tag != self.current_tag:
            self.result.append(('code', self.current_code))
            self.current_code = ''
        self.current_tag = tag


    def handle_endtag(self, tag):
        tag = self.simplify_tag(tag)
        if tag == 'code': 
            self.result.append(('code', self.current_code))
            self.current_code = ''
            self.current_tag = 'text' # 因为<code>中不会有别的标签
        elif tag == 'text':
            self.result.append(('text', self.current_text))
            self.current_text = ''

    def handle_data(self, data):
        data = html.unescape(data).strip()
        if not data:
            return
        if self.current_tag == 'text':
            self.current_text += f'{data} '
        elif self.current_tag == 'code':
            self.current_code += f'{data} '
    
    def denoising(self, data):
        # 删去content中的特殊字符
        for char in ['\r\n', '\r', '\n']:
            data = data.replace(char, ' ')
        data = ''.join([i if ord(i) < 128 else ' ' for i in data])
        data = ' '.join(data.split())
        return data

    def get_result(self):
        '''
        返回空值：
        1. 该行解析结果为空
        2. 不同时包含code与text
        '''
        if not self.result:
            return []
        merged_result = []
        last_tag = self.result[0][0]
        current_content = self.result[0][1]
        for segment in self.result[1:]:
            tag, content = segment
            if (not content) or (not content.strip()):
                continue
            if tag != last_tag:
                merged_result.append((last_tag, current_content))
                last_tag = tag
                current_content = content
                continue
            current_content += content
        merged_result.append((last_tag, current_content))
        cleaned_result = []
        # 删去空白的内容
        for item in merged_result:
            if not item[1]:
                continue
            denoised_content = self.denoising(item[1])
            if denoised_content:
                cleaned_result.append((item[0], denoised_content))
        return cleaned_result

def content_counter(source_path, total_len, language):
    '''
    统计各类标签的总数
    '''
    tag_count = {
        'code': 0,
        'text': 0
    } # 统计包含各类标签的问题数
    lang_tags = set()
    other_language_tags = LANGUAGES - set([f'<{language}>'])
    repeated_question = 0
    blank_line = 0
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        for line in f:
            t.update(1)
            line_json = xmltodict.parse(line)
            body_str = line_json['row']['@Body']

            tags_raw = line_json['row']['@Tags']
            for lang_tag in other_language_tags:
                if lang_tag in tags_raw:
                    repeated_question += 1
                    break

            parser = BodyParser()
            parser.feed(body_str)
            content = parser.get_result()
            if not content:
                blank_line += 1
                continue
            tags = set()
            for segment in content:
                tag, tag_content = segment
                tags.add(tag)
            for tag in tags:
                # 统计包含该标签的问题数
                tag_count[tag] += 1 
        t.close()
    print(f'total: {total_len}')
    print(tag_count)
    print(blank_line)
    print(f'repeated_question {repeated_question}')

'''
解析post body中的html标签
'''
def content_extractor(source_path, target_path, total_len, language):
    '''
    把xml数据变为最终要用的json数据
    '''
    result = []
    other_language_tags = LANGUAGES - set([f'<{language}>'])
    # tokenizer = RobertaTokenizer.from_pretrained('microsoft/codebert-base', do_lower_case=False)
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        blank_lines = 0
        only_code = 0
        only_text = 0
        for line in f:
            t.update(1)
            line_json = xmltodict.parse(line)
            body_str = line_json['row']['@Body']
            parser = BodyParser()
            parser.feed(body_str)
            line_parsed = parser.get_result()
            # 移除和其他language重复的post
            language_tag_flag = False
            tags_raw = line_json['row']['@Tags']
            for lang_tag in other_language_tags:
                if lang_tag in tags_raw:
                    language_tag_flag = True
            if language_tag_flag:
                continue
            # 删去不同时包含text和code的内容
            if not line_parsed:
                blank_lines += 1
                continue
            tags = [item[0] for item in line_parsed]
            if ('code' in tags) and ('text' not in tags):
                only_code += 1
                continue
            elif ('text' in tags) and ('code' not in tags):
                only_text += 1
                continue
            line_json['row']['@Body'] = line_parsed
            # 删去分词后长度过短或过长的
            len_item = {
                'total': 0,
                'text': 0,
                'code': 0
            }
            for segment in line_json['row']['@Body']:
                if segment[0] == 'text':
                    len_item['text'] += len(convention_tokenize(segment[1]))
                else:
                    len_item['code'] += len(convention_tokenize(segment[1]))
            len_item['total'] = len_item['text'] + len_item['code']
            if len_item['total'] > 1000:
                continue
            raw_title = line_json['row']['@Title']
            line_json['row']['@Title'] = ''.join([i if ord(i) < 128 else ' ' for i in raw_title])
            line_json_str = json.dumps(line_json['row'])
            result.append(f'{line_json_str}\n')
            if len(result) == BATCH_SIZE:
                write_lines(result, target_path)
                result.clear()
        t.close()
        if result:
            write_lines(result, target_path)
        print(f'blank lines: {blank_lines}, only_code: {only_code}, only_text: {only_text}')

def use_attr_extractor():
    '''
    主要用于过滤优质问题，输入输出都是xml文件
    '''
    language_all_path = './data/dataset/all/{}-all.xml'
    # for language in ['go', 'javascript', 'python', 'c#', 'php', 'ruby', 'java']:
    #     '''按条件抽取并新建文件'''
    #     TAG = f'&lt;{language}&gt;'
    #     filters = [TAG]
        # include_extractor(source_path, language_all_path.format(language), filters, total_lines)
    for language, total_lines in [
        # ('go', 50355), ('python', 1597777), ('c#', 1450789), ('php', 1381587), ('ruby', 216776), ('java', 1735380), ('javascript', 2130667)
            ('java', 1735380)
        ]:
        '''统计语言文件的回答数分布'''
        print(f'------------{language}------------')
        condition = lambda x: int(x['@Score']) >= 1 and '@AcceptedAnswerId' in x and '@ClosedDate' not in x and int(x['@AnswerCount']) >= 1
        attr_extractor(language_all_path.format(language), './data/dataset/all/java-a1-s1.xml', condition, total_lines)
        # attr_counter(language_all_path.format(language), '@AnswerCount', total_lines, condition)
        # time_counter( './data/dataset/java-a3-s3-no-code.xml', 81123)

def use_content_extractor():
    '''
    主要用于过滤不符合文本+代码、长度要求、和其它tag重复的内容，输入为xml，输出为json
    '''
    # source_path = './data/dataset/all/python-a1-s2.xml'
    # target_path = './data/dataset/all/python-a1-s2-len-lte-1000-only-text.jsonl'
    # python_lines = 267717
    # content_extractor(source_path, target_path, python_lines, 'python')
    # 用于统计不包含代码的post数量随时间分布规律
    # time_counter(target_path, 27093)
    # content_counter(source_path, python_lines, 'python')
    source_path = './data/dataset/all/java-a1-s1.xml'
    target_path = './data/dataset/all/java-a1-s1-len-lte-1000.jsonl'
    java_lines = 462244
    content_extractor(source_path, target_path, java_lines, 'java')

def token_len_counter(source_path, total_len):
    '''
    统计每个post body的token长度，并分别计算text和code的长度
    最终生成分位数：总长度分位数、text长度分位数、code长度分位数
    '''
    # tokenizer = RobertaTokenizer.from_pretrained('microsoft/codebert-base', do_lower_case=False)
    result = []
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        for line in f:
            t.update(1)
            line_json = json.loads(line)
            body_content = line_json['@Body']
            len_item = {
                'total': 0,
                'text': 0,
                'code': 0
            }
            for segment in body_content:
                if segment[0] == 'text':
                    # len_item['text'] += len(tokenizer.tokenize(segment[1]))
                    len_item['text'] += len(convention_tokenize(segment[1]))
                else:
                    # len_item['code'] += len(tokenizer.tokenize(segment[1]))
                    len_item['code'] += len(convention_tokenize(segment[1]))
            len_item['total'] = len_item['text'] + len_item['code']
            result.append(len_item)
        t.close()
    total_lens = np.array([item['total'] for item in result])
    text_lens = np.array([item['text'] for item in result])
    code_lens = np.array([item['code'] for item in result])
    for label, x in [('total', total_lens)]:
    # for label, x in [('text', text_lens), ('code', code_lens), ('total', total_lens)]:
        print(label)
        for percent in [0, 2, 3, 5, 7, 9, 50, 85, 86, 87, 88, 89, 90, 95, 100]:
            print('{} percent - len {}'.format(percent, np.percentile(x, percent)))
        # plot_histogram(x, 50)

def construct_3_datasets(source_path, total_len):
    # 得到各类数据集的行号
    # test_size = total_len // 10
    total_size = 40000
    test_size = 2000
    np.random.seed(999)
    total_line_ids = np.arange(total_len)
    total_line_ids_new = np.random.choice(total_line_ids, total_size, replace=False)
    test_ids = np.random.choice(total_line_ids_new, test_size, replace=False)
    total_line_ids = np.setdiff1d(total_line_ids_new, test_ids)
    valid_ids = np.random.choice(total_line_ids, test_size, replace=False)
    # 数据写入
    train_path = source_path.replace('.jsonl', '.train.jsonl')
    test_path = source_path.replace('.jsonl', '.test.jsonl')
    valid_path = source_path.replace('.jsonl', '.valid.jsonl')

    test_len = 0
    valid_len = 0
    train_len = 0
    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        line_id = 0
        for line in f:
            write_path = None
            t.update(1)
            if line_id in test_ids:
                test_len += 1
                write_path = test_path
            elif line_id in valid_ids:
                valid_len += 1
                write_path = valid_path
            elif line_id in total_line_ids_new:
                train_len += 1
                write_path = train_path
            else:
                line_id += 1
                continue
            write_lines([line], write_path)
            line_id += 1
        t.close()
        print("expected: {}-{}".format(len(valid_ids), len(test_ids)))
        print("{}-{}-{}".format(test_len, valid_len, train_len))

def construct_3_datasets_by_date(source_path, total_len, start_line, end_line):
    # 数据写入，source_path是json文件
    train_path = source_path.replace('.jsonl', '.train.jsonl')
    test_path = source_path.replace('.jsonl', '.test.jsonl')
    valid_path = source_path.replace('.jsonl', '.valid.jsonl')

    test_len = 0
    valid_len = 0
    train_len = 0

    total_lines_for_test = end_line - start_line + 1
    test_size = total_lines_for_test // 2
    valid_size = total_lines_for_test - test_size
    total_line_ids = np.arange(start_line, end_line+1)
    test_ids = np.random.choice(total_line_ids, test_size, replace=False)
    total_line_ids = set(total_line_ids)
    test_ids = set(test_ids)
    valid_ids = total_line_ids - test_ids

    with open(source_path, 'r', encoding='utf-8') as f:
        t = tqdm(total=total_len)
        line_id = 1
        write_path = None
        for line in f:
            t.update(1)
            if line_id in test_ids:
                test_len += 1
                write_path = test_path
            elif line_id in valid_ids:
                valid_len += 1
                write_path = valid_path
            else:
                train_len += 1
                write_path = train_path
            write_lines([line], write_path)
            line_id += 1
        t.close()
        print("expected: {}-{}".format(len(valid_ids), len(test_ids)))
        print("{}-{}-{}".format(test_len, valid_len, train_len))


def attr_counter_2(source_path, condition_func):
    '''
    读取jsonl文件
    文件行数以及关心数据的行数
    '''
    total_count = 0
    condition_count = 0
    with open(source_path, 'r', encoding='utf-8') as f:
        for line in f:
            total_count += 1
            if condition_func(json.loads(line)):
                condition_count += 1
    print(f'{source_path} total {total_count} lines')
    print(f'{source_path} conditioned {condition_count} lines')

def interrogative_counter():
    source_path = './data/dataset/all/python-a3-s2-len-lte-1000.jsonl'
    def function(json_data):
        target = ['how', 'what', 'why', 'which', 'when']
        title = json_data['@Title'].lower()
        for i in target:
            if i in title:
                return True
        return False
    attr_counter_2(source_path, function)

if __name__ == '__main__':
    # use_content_extractor()
    # use_attr_extractor()
    source_path = './data/dataset/all/java-a1-s1-len-lte-1000-match-gao-code-only.jsonl'
    # source_path = './data/dataset/all/java-a1-s1-len-lte-1000-match-gao.jsonl'
    # java_lines = 63056
    # construct_3_datasets(source_path, 54289)
    # construct_3_datasets_by_date('./data/dataset/all/python-a1-s2-len-lte-1000.jsonl', 225906, 211537, 225906)
    source_path = './data/dataset/all/python-a3-s2-len-lte-1000.jsonl'
    python_lines = 66439
    # construct_3_datasets(source_path, python_lines)
    # token_len_counter(source_path, python_lines)
    # interrogative_counter()
    