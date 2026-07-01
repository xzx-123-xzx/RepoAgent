import os

root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_file_path(relative_path):
    return os.path.join(root_dir, relative_path)


if __name__ == '__main__':
    print(root_dir)
    print(get_file_path("data/__001__qa_data/JP学科知识问答.csv"))