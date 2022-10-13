import bisect
import glob
import itertools
import json
import re
import sys
from pathlib import Path
from argparse import ArgumentParser, FileType

def main():
    parser = ArgumentParser()
    parser.add_argument('query_file', metavar='QUERY_FILE', type=FileType('r', encoding='utf-8'))
    args = parser.parse_args()

    try:
        query_obj = json.load(args.query_file)
    except json.JSONDecodeError as e:
        print('Error decoding JSON from {}: {}'.format(args.query_file.name, e), file=sys.stderr)
        sys.exit(1)

    try:
        query = Query(query_obj)
    except QueryDeserializeError as e:
        print('Error deserializing query from {}: {}'.format(args.query_file.name, e), file=sys.stderr)
        sys.exit(1)

    print('[query] {}'.format(query))

    query.run()

    input('press <enter> to exit')

class QueryDeserializeError(Exception):
    pass

class Query:

    def __init__(self, obj):
        self.max_results_per_text = None

        def is_list_of_strings(x):
            return isinstance(x, list) and all(isinstance(s, str) for s in x)
        if 'directories' not in obj:
            raise QueryDeserializeError('missing "directories" key')
        if not is_list_of_strings(obj['directories']):
            raise QueryDeserializeError('"directories" must be a list of strings')
        if 'fragments' not in obj:
            raise QueryDeserializeError('missing "fragments" key')
        if not is_list_of_strings(obj['fragments']):
            raise QueryDeserializeError('"fragments" must be a list of strings')
        if 'options' in obj:
            options = obj['options']
            if not isinstance(options, dict):
                raise QueryDeserializeError('"options" must be an object')
            if 'max_results_per_text' in options:
                max_results_per_text = options['max_results_per_text']
                if not isinstance(max_results_per_text, int):
                    raise QueryDeserializeError('"options.max_results_per_text" must be an integer')
                self.max_results_per_text = max_results_per_text

        self.directories = list(map(Path, obj['directories']))
        self.fragments = obj['fragments']

        flags = re.IGNORECASE
        self.fragment_regexes = { fragment: re.compile(re.escape(fragment), flags) for fragment in self.fragments }

    def __str__(self):
        conjunction = ' | '.join(map(repr, self.fragments))
        scope = ', '.join(map(str, self.directories))
        return "[ {} ] in [ {} ]".format(conjunction, scope)

    def search_text_all(self, text):
        newline_index = NewlineIndex(text)
        for fragment, regex in self.fragment_regexes.items():
            for match in regex.finditer(text):
                yield fragment, newline_index.line_index(match.start())

    def search_text(self, text):
        it = self.search_text_all(text)
        if self.max_results_per_text is None:
            yield from it
        else:
            yield from itertools.islice(it, self.max_results_per_text)

    def run(self):
        num_matches = 0

        for directory in self.directories:
            if not directory.is_dir():
                print('Error: {} is not a directory'.format(directory), file=sys.stderr)
                sys.exit(1)
            text_paths = directory.glob('**/*.htm')
            for text_path in text_paths:
                with open(text_path, encoding='utf-8') as f:
                    text = f.read()
                for fragment_regex, line_index in self.search_text(text):
                    line_number = line_index + 1
                    print('[match] "{}" at {}:{}'.format(fragment_regex, text_path, line_number))
                    num_matches += 1

        print('[summary] {} matches'.format(num_matches))

class NewlineIndex:

    def __init__(self, text):
        lf_indices = []
        r = re.compile('\n')
        for match in r.finditer(text):
            lf_indices.append(match.start())
        self.lf_indices = lf_indices

    def line_index(self, char_index):
        return bisect.bisect_left(self.lf_indices, char_index)

if __name__ == '__main__':
    main()
