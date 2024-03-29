import ipdb
import xmltodict
import html
import json
import linecache

from elasticsearch import Elasticsearch, helpers
from logging import config, getLogger
from tqdm import tqdm

from log_config import LOGGING_DIC
from file_helper import for_line_in, append_file
from other_utils import split_things, compare_str, convention_tokenize

config.dictConfig(LOGGING_DIC)
# logger = getLogger('production') # 生产环境使用的logger，输出内容到文件
logger = getLogger('console_info') # 测试使用的logger，输出内容到终端
# INDEX_NAME = 'so_posts_all' # elastic数据库名称
# INDEX_NAME = 'java_a1s1_lte1000' # elastic数据库名称
INDEX_NAME = 'python_match_gao_html_v2' # elastic数据库名称
# INDEX_NAME = 'python_a1s2_lte1000' # elastic数据库名称
DOC_TYPE = 'python' # elastic表名
FAILED_RECORD = 'failed.txt' # 上传失败的记录文件
BULK_SIZE = 100 # 批量上传的条数
# TOTAL_SIZE = 1597777 # 要上传的数据总量
TOTAL_SIZE = 34013 # 要上传的数据总量
HOST = '192.168.40.250' # elastic数据库ip地址

def get_connection():
    es = Elasticsearch(f"http://{HOST}:9200")
    logger.info("connected to elasticsearch")
    return es

def initialize(es):
    '''创建数据库，建表'''
    logger.info(f"creating index: {INDEX_NAME}")
    result = es.indices.create(index=INDEX_NAME, ignore=400)
    logger.info(result)

def upload_xml(lines, es):
    '''上传文档，单进程批量xml版'''
    bulk_actions = []
    for line in lines:
        line_json = xmltodict.parse(line)
        action = {
            '_index': INDEX_NAME,
            '_type': DOC_TYPE,
            '_id': int(line_json['row']['@Id']),
            '_source': {
                'title': line_json['row']['@Title'],
                'body': html.unescape(line_json['row']['@Body'])
            }
        }
        bulk_actions.append(action)
    result = helpers.bulk(es, bulk_actions, ignore=409)
    first_id = bulk_actions[0]['_id']
    last_id = bulk_actions[-1]['_id']
    logger.info(f'lines with identifiers from {first_id} to {last_id} have been successfully uploaded')

def upload_json(lines, es):
    '''上传文档，单进程批量json版'''
    bulk_actions = []
    for line in lines:
        line_json = json.loads(line.strip())
        title = ' '.join(split_things(line_json['@Title'], False, False))
        body = ' '.join(split_things(line_json['@Body'], False, False))
        action = {
            '_index': INDEX_NAME,
            '_type': DOC_TYPE,
            '_id': int(line_json['@Id']),
            '_source': {
                'title': title,
                'body': body
            }
        }
        bulk_actions.append(action)
    result = helpers.bulk(es, bulk_actions, ignore=409)
    first_id = bulk_actions[0]['_id']
    last_id = bulk_actions[-1]['_id']
    logger.info(f'lines with identifiers from {first_id} to {last_id} have been successfully uploaded')

def upload_match_gao(lines, line_no, es):
    '''上传match_gao json数据集，批量版'''
    bulk_actions = []
    for i, line in enumerate(lines):
        line_json = json.loads(line.strip())
        title = ' '.join(line_json['docstring_tokens'])
        body = ' '.join(line_json['code_tokens'])
        action = {
            '_index': INDEX_NAME,
            '_type': DOC_TYPE,
            '_source': {
                'title': title,
                'body': body
            }
        }
        bulk_actions.append(action)
    result = helpers.bulk(es, bulk_actions, ignore=409)

def delete_index(es):
    '''删除数据库'''
    result = es.indices.delete(index=INDEX_NAME, ignore=[400, 404])
    logger.info(result)

def query_index(es, field, support_str):
    '''
    根据特定field和文本查询，返回最接近的前三条结果field中的内容
    exact match 的分数从 10+ 到 50+ 不等，越长的文本分数越高
    '''
    # data ={'query': {'match': {field: {'query': support_str, "analyzer": "standard"} }}, 'sort':{'_score':{'order':'asc'}}}
    data ={'query': {'match': {field: {'query': support_str, "analyzer": "standard"} }}}
    result = es.search(index=INDEX_NAME, doc_type=DOC_TYPE, body=data, size=10)
    top_three = result['hits']['hits']
    top_three_simple = \
        [{ 
            'id': hit['_id'],
            'score': hit['_score'],
            # field: hit['_source'][field]
            'title': hit['_source']['title'],
            'body': hit['_source']['body']
        } for hit in top_three]
    # logger.info(top_three_simple)
    return top_three_simple

def query_file(es,read_file_path,write_file_path):
    """
    查询指定文件的所有标题，并把排名前三的结果写入json
    """
    with open(read_file_path, mode='r', encoding='utf-8') as fr:
        with open(write_file_path,mode="w",encoding="utf-8") as fw:
            for line in fr:
                line_dict = {}
                # line_dict["title"] = line
                line_dict["code"] = line
                # line_dict["top_three_simple"] = query_index(es,"title",line)
                line_dict["top_three_simple"] = query_index(es, "body", line)

                line_json = json.dumps(line_dict)
                fw.write(line_json + '\n')
            fw.close()

def query_jsonfile(es,read_file_path_json,read_file_path_code,write_file_path):
    '''
    读取json文件，并进行代码段匹配，把排名前三的写入json
    '''
    with open(read_file_path_json, mode='r', encoding='utf-8') as fr_json:
        with open(write_file_path,mode="w",encoding="utf-8") as fw:
            for line in fr_json:
                line_dict={} #用于生成json文件
                load_json = json.loads(line)
                line_index=load_json["linedex"]
                line_dict["code"] = linecache.getline(read_file_path_code, line_index)
                line_dict["top_three_simple"] = query_index(es,"body",line_dict["code"])
                line_dict["line_index"] = line_index

                line_json = json.dumps(line_dict)
                fw.write(line_json+"\n")


def match_and_write(es, source_path, target_path, length):
    '''
    查询数据库，把排名第一且token重复率超过99%的写入文件
    '''
    t = tqdm(total=length)
    with open(source_path, mode='r', encoding='utf-8') as r_f,\
        open(target_path, mode='w', encoding='utf-8') as w_f:
        line_no = 0
        existed_id = set()
        for line in r_f:
            # r_f为Gao的txt文件
            line_no += 1
            title = line.strip()
            top_1 = query_index(es, 'title', title)[0]
            t.update(1)
            line_dict = {}
            line_dict['score'] = top_1['score']
            line_dict['zfj-id'] = top_1['id']
            if line_dict['zfj-id'] in existed_id:
                continue
            existed_id.add(line_dict['zfj-id'])
            line_dict['gao-lino'] = line_no
            line_dict['gao-title'] = title
            line_dict['zfj-title'] = top_1['title']
            if not compare_str(line_dict['gao-title'], line_dict['zfj-title']):
                # n_f.write(f'{line_no}\n')
                continue
            w_f.write(json.dumps(line_dict, ensure_ascii=False)+'\n')
    t.close()

def match_similar_and_write(es, source_path, target_path, length):
    '''
    查询数据库，把排名第2的写入文件
    '''
    t = tqdm(total=length)
    with open(source_path, mode='r', encoding='utf-8') as r_f,\
        open(target_path, mode='w', encoding='utf-8') as w_f:
        line_no = 0
        for line in r_f:
            # r_f为match-gao的train json文件
            line_no += 1
            line = line.strip()
            # line_json = json.loads(line)
            # title = ' '.join(line_json['docstring_tokens'])
            title = line
            queryed = query_index(es, 'title', title)
            title_first = queryed[0]['title']
            if title_first == title:
                title_first = queryed[1]['title']
            w_f.write(f'{title_first}\n')
            t.update(1)
    t.close()

def match_similar_json_and_write(es, source_path, target_path, ref_path, length):
    '''
    查询数据库，把排名第2的写入文件
    '''
    t = tqdm(total=length)
    with open(source_path, mode='r', encoding='utf-8') as r_f,\
        open(target_path, mode='w', encoding='utf-8') as w_f,\
        open(ref_path, mode='w', encoding='utf-8') as e_f:
        line_no = 0
        for line in r_f:
            # r_f为match-gao的train json文件
            line_no += 1
            line = line.strip()
            line_json = json.loads(line)
            title = ' '.join(line_json['docstring_tokens'])
            body = ' '.join(line_json['code_tokens'])
            queryed = query_index(es, 'body', body)
            title_first = queryed[0]['title']
            # if title_first == title:
            #     title_first = queryed[1]['title']
            w_f.write(f'{title_first}\n')
            e_f.write(f'{title}\n')
            t.update(1)
    t.close()

if __name__ == '__main__':
    es = get_connection()
    # initialize(es)
    # query_file(es,"/home/zzm/sdb2_zzm/Code2Que-master/Code2Que-data/pydata/src-train.txt","/home/zzm/sdb2_zzm/Code2Que-master/Code2Que-data/pydata/src-train.json")
    # query_jsonfile(es,"notmatch-pytgt-train.json","/home/zzm/sdb2_zzm/Code2Que-master/Code2Que-data/pydata/src-train.txt","notmatch-pysrc-train.json")
    # for_line_in("data/dataset/Python/python-match-gao-html.train.jsonl", TOTAL_SIZE, BULK_SIZE, upload_match_gao, es)
    # match_and_write(es, "data/Gao/python/tgt-train-test.txt", "data/Gao/python/a1s2_matched_tgt_train.trust.jsonl", 189936)
    # match_and_write(es, "data/Gao/java/tgt-train-test.txt", "data/Gao/java/a1s1_matched_tgt_train.trust.with-repeat.jsonl", 253671)

    for i in range(100):
        line = linecache.getline('data/dataset/Python/python-match-gao-html.train.jsonl', i+300).strip()
        line_json = json.loads(line)
        body = ' '.join(line_json['code_tokens'])
        title = ' '.join(line_json['docstring_tokens'])

        top_three_simple = query_index(es, 'body', body)
        # top_three_simple = query_index(es, 'title', 'How to check for a button press while another tk . button function runs ?')
        print(title)
        print(body)
        ipdb.set_trace()
        print(top_three_simple)
        

    # match_similar_and_write(es, 'data/dataset/Python/codebert.python.a1s2.both.lte1000.match-gao.valid.jsonl', 'python-match-gao.train.retrieve.jsonl', 34013)
    # match_similar_json_and_write(es, 'data/dataset/Python/codebert.python.a1s2.both.lte1000.match-gao.valid.jsonl', 'python-match-gao.valid.bodyinbody-retrieve.jsonl',  'python-match-gao.valid.bodyinbody-gold.jsonl', 2000)

'''
查看所有索引 http://192.168.40.250:9200/_cat/indices?v

'''

# def upload_self_es(line):
#     '''废弃不用
#     上传文档，多进程版，无需传入连接对象
#     '''
#     try:
#         es = get_connection()
#         line_json = xmltodict.parse(line)
#         data = {
#             'title': line_json['row']['@Title'],
#             'body': html.unescape(line_json['row']['@Body'])
#         }
#         data_id = int(line_json['row']['@Id'])
#         result = es.create(index=INDEX_NAME, doc_type=DOC_TYPE, id=data_id, body=data, ignore=409)
#         logger.info(f'id:{data_id} success log: {result}')
#         return None
#     except Exception as e:
#         logger.error(f'id:{data_id} failed reason: {e}')
#         return (FAILED_RECORD, data_id)
# async_for_line_in("xml-data/python_over_3_answers.xml", TOTAL_SIZE, upload_self_es)