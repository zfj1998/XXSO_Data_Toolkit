import ipdb
import xmltodict
import html
import json
from elasticsearch import Elasticsearch, helpers
from logging import config,getLogger

from log_config import LOGGING_DIC
from file_helper import for_line_in, append_file

config.dictConfig(LOGGING_DIC)
# logger = getLogger('production') # 生产环境使用的logger，输出内容到文件
logger = getLogger('console_info') # 测试使用的logger，输出内容到终端
INDEX_NAME = 'so_posts_all' # elastic数据库名称
DOC_TYPE = 'python' # elastic表名
FAILED_RECORD = 'failed.txt' # 上传失败的记录文件
BULK_SIZE = 100 # 批量上传的条数
TOTAL_SIZE = 1597777 # 要上传的数据总量
HOST = '192.168.0.105' # elastic数据库ip地址

def get_connection():
    es = Elasticsearch(f"http://{HOST}:9200")
    logger.info("connected to elasticsearch")
    return es

def initialize(es):
    '''创建数据库，建表'''
    logger.info(f"creating index: {INDEX_NAME}")
    result = es.indices.create(index=INDEX_NAME, ignore=400)
    logger.info(result)

def upload(lines, es):
    '''上传文档，单进程批量版'''
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

def delete_index(es):
    '''删除数据库'''
    result = es.indices.delete(index=INDEX_NAME, ignore=[400, 404])
    logger.info(result)

def query_index(es, field, support_str):
    '''
    根据特定field和文本查询，返回最接近的前三条结果field中的内容
    exact match 的分数从 10+ 到 50+ 不等，越长的文本分数越高
    '''
    data ={'query': {'match': {field: support_str }}}
    result = es.search(index=INDEX_NAME, doc_type=DOC_TYPE, body=data)
    top_three = result['hits']['hits'][:3]
    top_three_simple = \
        [{ 
            'id': hit['_id'],
            'score': hit['_score'],
            field: hit['_source'][field]
        } for hit in top_three]
    logger.info(top_three_simple)
    return top_three_simple

def query_file(es,read_file_path,write_file_path):
    """
    查询指定文件的所有标题，并把排名前三的结果写入json
    """
    with open(read_file_path, mode='r', encoding='utf-8') as fr:
        with open(write_file_path,mode="w",encoding="utf-8") as fw:
            for line in fr:
                line_dict = {} 
                line_dict["title"] = line
                line_dict["top_three_simple"] = query_index(es,"title",line)

                # 这里补充字符串转换操作，在字典里加相应的东西

                json.dump(line_dict,fw)


if __name__ == '__main__':
    es = get_connection()
    # initialize(es)
    query_file(es,"./raw_data/tgt-train.txt","./matcheddata/tgt-train.json")
    # query_index(es, 'title', 'how to format python string based on byte length ?')
    # for_line_in("data/xml-data/with_python_tag_all.xml", TOTAL_SIZE, BULK_SIZE, upload, es)

    


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