'''
先都变为小写然后分词
'''

from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from rouge import Rouge
import ipdb

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

def get_word_maps_from_file(pred_file, gold_file, tokenize):
    '''
    如下行格式均可:
        {idx}\t{content}
        {content}
    分词方式可以自定义，只要保证content是一个字符串，由空格分隔的tokens组成
    return:
        hypotheses: dict{id: [str]}
        references: dict{id: [str]}
    '''
    prediction_map = {}
    gold_map = {}
    with open(pred_file, 'r', encoding='utf-8') as pf, \
        open(gold_file, 'r', encoding='utf-8') as gf:
        for row_no, row in enumerate(pf):
            cols = row.strip().split('\t')
            if len(cols) == 1:
                rid, pred = row_no, cols[0]
                if not pred:
                    pred = 'nothinggeneratedandscoreshouldbezero'
            else:
                rid, pred = cols[0], cols[1]
            prediction_map[rid] = [pred.strip().lower()]
            if tokenize:
                tokenized_pred = convention_tokenize(prediction_map[rid][0])
                prediction_map[rid] = [' '.join(tokenized_pred)]

        for row_no, row in enumerate(gf):
            cols = row.strip().split('\t')
            if len(cols) == 1:
                rid, gold = row_no, cols[0]
            else:
                rid, gold = cols[0], cols[1]
            gold_map[rid] = [(gold.strip().lower())]
            if tokenize:
                tokenized_gold = convention_tokenize(gold_map[rid][0])
                gold_map[rid] = [' '.join(tokenized_gold)]

        print(f'Total: {len(gold_map)}')
        return (prediction_map, gold_map)

def nltk_bleu(hypotheses, references):
    '''return float'''
    total_score = 0
    count = len(hypotheses)
    smoothing = SmoothingFunction().method3
    for key in list(hypotheses.keys()):
        hyp = hypotheses[key][0].split()
        ref = [r.split() for r in references[key]]
        score = sentence_bleu(ref, hyp, weights=(0.25, 0.25, 0.25, 0.25), smoothing_function=smoothing)
        # score = sentence_bleu(ref, hyp, weights=(0.25, 0.25, 0.25, 0.25))
        total_score += score
    avg_score = total_score / count
    return avg_score

def py_rouge(hypotheses, references):
    '''
    {'rouge-1': {'f':, 'p':, 'r':}, 'rouge-2', 'rouge-l'}
    '''
    rouge = Rouge()
    hyps = []
    refs = []
    for key in list(hypotheses.keys()):
        hyps.append(hypotheses[key][0])
        refs.append(references[key][0])
    scores = rouge.get_scores(hyps, refs, avg=True)
    return scores

def average_rouge(hypotheses, references):
    '''
    return the avg f score of rouge1, rouge2, rougeL
    '''
    scores = py_rouge(hypotheses, references)
    rouge1_f = scores['rouge-1']['f']
    rouge2_f = scores['rouge-2']['f']
    rougeL_f = scores['rouge-l']['f']
    avg_f = 0.2*rouge1_f + 0.3*rouge2_f + 0.5*rougeL_f
    return avg_f

def rouge_between_strings(gold, hypo):
    '''
    计算两个字符串的avg_rouge
    '''
    rouge = Rouge()
    scores = rouge.get_scores([hypo], [gold], avg=True)
    rouge1_f = scores['rouge-1']['f']
    rouge2_f = scores['rouge-2']['f']
    rougeL_f = scores['rouge-l']['f']
    avg_f = 0.2*rouge1_f + 0.3*rouge2_f + 0.5*rougeL_f
    return avg_f

def running_local():
    # onmt-both-trunc510-bs16
    # pred_path = 'train_results/beam-search-both-valid/hyp_beam.txt'
    # gold_path = 'train_results/beam-search-both-valid/ref_beam.txt'
    pred_path = 'train_results/gao-zfj/python/{}'
    gold_path = 'train_results/gao-zfj/python/{}'
    # pred_path = pred_path.format('pred.valid.v4.sharevocab.nocover.txt')
    # gold_path = gold_path.format('tgt.valid.python.a1s2.both.lte1000.match-gao.txt')
    pred_path = 'python-match-gao.valid.bodyinbody-retrieve.jsonl'
    gold_path = 'python-match-gao.valid.bodyinbody-gold.jsonl'
    hypotheses, references = get_word_maps_from_file(pred_path, gold_path, True)
    bleu = nltk_bleu(hypotheses, references)
    rouge_score = average_rouge(hypotheses, references)
    print(f'bleu:\n{bleu}')
    print(f'rouge:\n{rouge_score}')

if __name__ == '__main__':
    running_local()