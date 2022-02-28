import sys
import re
import glob
import json
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

    print('query: {}'.format(query))

    query.run()

class QueryDeserializeError(Exception):
    pass

class Query:

    def __init__(self, obj):
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

        self.directories = list(map(Path, obj['directories']))
        self.fragments = obj['fragments']

        flags = re.IGNORECASE
        self.fragment_regexes = [ re.compile(re.escape(fragment), flags) for fragment in self.fragments ]

    def __str__(self):
        conjunction = ' & '.join(map(repr, self.fragments))
        scope = ', '.join(map(str, self.directories))
        return "[ {} ] in [ {} ]".format(conjunction, scope)

    def search_text(self, text):
        for regex in self.fragment_regexes:
            match = regex.search(text)
            if match is None:
                return False
        return True

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
                if self.search_text(text):
                    print('match: {}'.format(text_path))
                    num_matches += 1

        print('summary: {} matches'.format(num_matches))
    
if __name__ == '__main__':
    main()
