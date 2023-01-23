def get_file(file):
    with open(file, 'rb') as f:
        return f.read()

def get_data_file(file):
    return get_file('./data/' + file)
