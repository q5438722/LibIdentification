import torch
import numpy as np
from torch.utils.data import DataLoader
from dataset import MDataset, createDataCSV

from model import LightXML

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('--dataset', type=str, required=False, default='eurlex4k')
parser.add_argument('--cp', type=str, required=False, default='vera_models')
args = parser.parse_args()

if __name__ == '__main__':
    df, label_map = createDataCSV(args.dataset)
    print(f'load {args.dataset} dataset with '
          f'{len(df[df.dataType =="train"])} train {len(df[df.dataType =="test"])} test with {len(label_map)} labels done')

    xmc_models = []
    predicts = []
    
    # Important!
    # You can list the transformer models used here
    # Currently we have tried:
    # bert-base, roberta, xlnet, docbert, longformer, and bigbird
    # berts = ['bert-base']
    berts = ['bert-base', 'roberta', 'xlnet']
    # berts = ['bert-base', 'longformer', 'bigbird']

    for index in range(len(berts)):
        model_name = [args.dataset, '' if berts[index] == 'bert-base' else berts[index]]
        model_name = '_'.join([i for i in model_name if i != ''])

        model = LightXML(n_labels=len(label_map), bert=berts[index])

        print(f'models/model-model_name.bin')
        model.load_state_dict(torch.load(f'{args.cp}/model-{model_name}.bin'))

        tokenizer = model.get_tokenizer()
        test_d = MDataset(df, 'test', tokenizer, label_map, 128 if args.dataset == 'amazoncat13k' and berts[index] == 'xlnent' else 512)
        testloader = DataLoader(test_d, batch_size=16, num_workers=0,
                                shuffle=False)

        model.cuda()
        predicts.append(torch.Tensor(model.one_epoch(0, testloader, None, mode='test')[0]))
        xmc_models.append(model)

    df = df[df.dataType == 'test']
    total = len(df)
    acc1 = [0 for i in range(len(berts) + 1)]
    acc2 = [0 for i in range(len(berts) + 1)]
    acc3 = [0 for i in range(len(berts) + 1)]
    acc5 = [0 for i in range(len(berts) + 1)]
    rec1 = [0 for i in range(len(berts) + 1)]
    rec2 = [0 for i in range(len(berts) + 1)]
    rec3 = [0 for i in range(len(berts) + 1)]
    
    print(df)
    for index, true_labels in enumerate(df.label.values):
        true_labels = set([label_map[i] for i in true_labels.split()])

        logits = [torch.sigmoid(predicts[i][index]) for i in range(len(berts))]
        logits.append(sum(logits))
        logits = [(-i).argsort()[:10].cpu().numpy() for i in logits]
        
        for i, logit in enumerate(logits):
            acc1[i] += len(set([logit[0]]) & true_labels) / min(len(true_labels), 1)
            acc2[i] += len(set(logit[:2]) & true_labels) / min(len(true_labels), 2)
            acc3[i] += len(set(logit[:3]) & true_labels) / min(len(true_labels), 3)
            acc5[i] += len(set(logit[:5]) & true_labels) / min(len(true_labels), 5)
            rec1[i] += len(set([logit[0]]) & true_labels) / len(true_labels)
            rec2[i] += len(set(logit[:2]) & true_labels) / len(true_labels)
            rec3[i] += len(set(logit[:3]) & true_labels) / len(true_labels)
    
    for i, name in enumerate(berts + ['all']):
        p1 = acc1[i] / total
        p2 = acc2[i] / total
        p3 = acc3[i] / total
        p5 = acc5[i] / total
        r1 = rec1[i] / total
        r2 = rec2[i] / total
        r3 = rec3[i] / total
        f1 = float(2 * p1 * r1) / (p1 + r1)
        f2 = float(2 * p2 * r2) / (p2 + r2)
        f3 = float(2 * p3 * r3) / (p3 + r3)

        print("\n\n\n")
        print("Bert model: " + name)
        print("K = 1")
        print("Precision = " + p1.__str__())
        print("Recall    = " + r1.__str__())
        print("F1        = " + f1.__str__())
        print()
        print("K = 2")
        print("Precision = " + p2.__str__())
        print("Recall    = " + r2.__str__())
        print("F1        = " + f2.__str__())
        print()
        print("K = 3")
        print("Precision = " + p3.__str__())
        print("Recall    = " + r3.__str__())
        print("F1        = " + f3.__str__())
        print()
