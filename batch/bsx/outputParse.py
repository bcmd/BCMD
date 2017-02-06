import argparse
import os.path
import pprint
import json


def float_or_str(s):
    try:
        return float(s)
    except ValueError:
        return s


def output_parse(fname):
    optim_data = {'Cortex': [],
                  'Subject': [],
                  'Max_Demand': [],
                  'Final_Distance': []}
    with open(fname) as f:
        for line in filter(None, (line.rstrip() for line in f)):
            li = line.lstrip()
            li = li.split()
            if li[0][:2] == '~~':
                input_file = os.path.splitext(os.path.split(
                    li[-1])[1])[0].split('_')
                optim_data['Cortex'].append(input_file[-1])
                optim_data['Subject'].append(input_file[1])
                optim_data['Max_Demand'].append(
                    float_or_str(input_file[-2]) / 10)
            if li[0][:2] == '^^':
                optim_data.setdefault(li[1][:-1],
                                      []).append(float_or_str(li[-1]))

            if li[0][:2] == '&&':
                optim_data['Final_Distance'].append(float_or_str(li[-1]))
    return optim_data


def data_writing(optim_data):
    with open('optimisation.json', 'w') as fp:
        json.dump(optim_data, fp)

    return print('Data printed to %s' % os.path.abspath('./optimisation.json'))


def cli_interface():
    ap = argparse.ArgumentParser(description='Process optim_demand output file')
    ap.add_argument('output_file', metavar='FILE',
                    help='the optim_demand output file')
    args = ap.parse_args()
    optim_data = output_parse(args.output_file)
    pprint.pprint(optim_data, depth=2)

    data_writing(optim_data)
    return optim_data


if __name__ == '__main__':
    cli_interface()
