import hashlib
import os
import sys
import model.db as dbm
# 自有模块
import model.model as model


def main():
    args = sys.argv
    if len(args) == 2:
        target_path = str(args[1])
    else:
        print('error path')
        return False

    # print(target_path)
    if not os.path.isdir(target_path):
        print('error')
    list_son_dir = os.listdir(target_path)
    for dirname in list_son_dir:
        son_dir_name = os.path.join(target_path, dirname)
        if os.path.isdir(son_dir_name):
            fix_md5_by_path(son_dir_name)
        elif os.path.isfile(son_dir_name) and dirname != '.DS_Store':
            fix_md5_by_file(son_dir_name)


def fix_md5_by_file(filename):
    print('检查文件%s' % filename)
    if not os.path.isfile(filename):
        return False
    md5_val = get_file_md5(filename)
    # print(os.path.split(filename)[-1])
    id_int = int(os.path.split(filename)[-1].split('.')[0])
    # print(id_int)
    db = dbm.DbManager()
    exist_md5 = db.session.query(model.Item).filter(model.Item.id == int(id_int), model.Item.status == 3).first()
    if exist_md5:
        if not exist_md5.md5:
            exist_md5.md5 = md5_val
            db.session.add(exist_md5)
            db.session.commit()
            print('[%s] 修改md5' % exist_md5.id)
    db.session.close()


def fix_md5_by_path(target_path):
    print('检查目录%s' % target_path)
    if not os.path.isdir(target_path):
        print('error')
        return False
    list_son_dir = os.listdir(target_path)
    for dirname in list_son_dir:
        son_dir_name = os.path.join(target_path, dirname)
        # print(son_dir_name)
        if os.path.isfile(son_dir_name) and dirname != '.DS_Store':
            # print(son_dir_name)
            fix_md5_by_file(son_dir_name)
        elif os.path.isdir(son_dir_name):
            fix_md5_by_path(son_dir_name)


def get_file_md5(path):
    # print(path)
    m = hashlib.md5()
    if os.path.isfile(path):
        for chunk in read_in_chunks(path):
            m.update(chunk)

        md5_val = m.hexdigest()
        # print(md5_val)
        return md5_val


def read_in_chunks(filePath, chunk_size=1024 * 1024):
    """
    Lazy function (generator) to read a file piece by piece.
    Default chunk size: 1M
    You can set your own chunk size
    """
    file_object = open(filePath, 'rb')
    while True:
        chunk_data = file_object.read(chunk_size)
        if not chunk_data:
            break
        yield chunk_data


if __name__ == '__main__':
    # fix_md5_by_file('/Volumes/hhd/python_download/tum/download_2018-04-06/pic/atomicstua/post_2018-03-10/102275.png')
    main()
