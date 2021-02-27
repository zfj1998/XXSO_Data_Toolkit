# LABEL = '&lt;python&gt'
import xmltodict
import ipdb
import datetime
from collections import Counter, OrderedDict
from tqdm import tqdm
import html
from html.parser import HTMLParser

# DATA_DUMP = './xml-data/with_python_tag_all.xml'
DATA_DUMP = './xml-data/python_over_3_answers.xml'
TARGET = './xml-data/python_over_3_answers_beautified.xml'
BATCH_SIZE = 500
TOTAL_SIZE = 218558 # python over 3 answers
# TOTAL_SIZE = 1597777 # with_python_tag_all

class OrderedCounter(Counter, OrderedDict):
    def __repr__(self):
        return "%s(%r)" % (self.__class__.__name__, OrderedDict(self))

def write_lines(lines):
    with open(TARGET, 'a', encoding='utf-8') as f:
        f.writelines(lines)

def include_extractor():
    '''
    根据包含关系抽取数据行
    '''
    LABEL = 'AnswerCount='
    result = []
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        for line in f:
            if LABEL in line:
                result.append(line)
            if len(result) == BATCH_SIZE:
                write_lines(result)
                result.clear()
    if result:
        write_lines(result)

def line_counter():
    '''
    简单统计文件行数
    '''
    count = 0
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        for line in f:
            count += 1
    print(f'{DATA_DUMP} total lines: {count}')

def attr_extractor():
    '''
    按照属性值进行抽取
    '''
    result = []
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            answer_count = int(line_json['row']['@AnswerCount'])
            if answer_count > 2:
                result.append(line)
            if len(result) == BATCH_SIZE:
                write_lines(result)
                result.clear()
            t.update(1)
        t.close()
    if result:
        write_lines(result)

def average_len():
    '''
    统计Post的平均长度
    '''
    total_len = 0
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            total_len += len(html.unescape(line_json['row']['@Body']).split())
            t.update(1)
    t.close()
    print(total_len)
    print(round(total_len/TOTAL_SIZE, 2))

def answer_counter():
    '''
    统计回答数
    '''
    counts = []
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            counts.append(line_json['row']['@AnswerCount'])
            t.update(1)
    t.close()
    c = Counter(counts)
    print(c.most_common())

def time_counter():
    '''
    按年/月统计问题数量
    '''
    by_month = []
    by_year = []
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            time_str = line_json['row']['@CreationDate']
            time_obj = datetime.datetime.strptime(time_str,'%Y-%m-%dT%H:%M:%S.%f')
            by_month.append(time_obj.strftime('%Y-%m'))
            by_year.append(time_obj.strftime('%Y'))
            t.update(1)
    t.close()
    print(OrderedCounter(by_month))
    print(OrderedCounter(by_year))

'''
解析post body中的html标签
'''
class BodyParser(HTMLParser):
    def __init__(self):
        super(BodyParser, self).__init__()
        self.current_data_len = 0
        self.result = {}

    def handle_starttag(self, tag, attrs):
        pass

    def handle_endtag(self, tag):
        current_item = self.result.get(tag)
        if not current_item:
            self.result[tag] = {
                'count': 1,
                'len': self.current_data_len
            }
            return
        current_item['count'] += 1
        current_item['len'] += self.current_data_len
        self.result[tag] = current_item

    def handle_data(self, data):
        self.current_data_len = len(html.unescape(data).split())
    
    def get_result(self):
        return self.result

'''
解析post body中的html标签
'''
def content_parser():
    '''
    把原始数据修改为训练所用的数据
    '''
    result = []
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            body_str = line_json['row']['@Body']
            parser = BodyParser()
            parser.feed(body_str)
            line_json['row']['@Body'] = parser.get_result()
            handled_line = xmltodict.unparse(line_json, full_document=False)
            result.append(f'{handled_line}\n')
            if len(result) == BATCH_SIZE:
                write_lines(result)
                result.clear()
            t.update(1)
        t.close()
        if result:
            write_lines(result)

def content_counter():
    '''
    统计各类标签的总数以及总长度
    '''
    tag_amount = {} # 统计标签总数
    tag_count = {} # 统计包含各类标签的问题数
    with open(DATA_DUMP, 'r', encoding='utf-8') as f:
        t = tqdm(total=TOTAL_SIZE)
        for line in f:
            line_json = xmltodict.parse(line)
            body_str = line_json['row']['@Body']
            parser = BodyParser()
            parser.feed(body_str)
            tag_items = parser.get_result()
            for tag in tag_items.keys():
                tag_item = tag_items[tag]
                # 统计标签总数
                if tag_amount.get(tag):
                    tag_amount[tag]['count'] += tag_item['count']
                    tag_amount[tag]['len'] += tag_item['len']
                else:
                    tag_amount[tag] = tag_item
                # 统计包含该标签的问题数
                if tag_count.get(tag):
                    tag_count[tag]['count'] += 1
                else:
                    tag_count[tag] = {'count': 1}
            t.update(1)
        t.close()
    print(tag_amount)
    print(tag_count)

if __name__ == '__main__':
    average_len()
    # line_counter()
    # content_parser()
    # content_counter()