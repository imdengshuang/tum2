import os
import sys


def main():
    """
    处理参数
    python3 clean_empty_dir.py xxx
    xxx为文件夹绝对路径
    请重复运行至无文件夹可删除为止
    :return:
    """
    args = sys.argv
    if len(args) == 2:
        target_path = str(args[1])
    else:
        print('error path')
        return False

    print(target_path)
    if not os.path.isdir(target_path):
        print('error')
        return False
    clean_empty_dir(target_path)


def clean_empty_dir(target_path):
    """
    删除空文件夹
    文件夹有子文件夹,且子文件夹为空时,只删除子文件夹
    :param target_path:
    :return:
    """
    if not os.path.isdir(target_path):
        print('error')
        return False
    else:
        list_son_dir = os.listdir(target_path)
        if not list_son_dir:
            print('删除目录%s' % target_path)
            os.rmdir(target_path)
        elif list_son_dir == ['.DS_Store']:
            print('删除.DS_Store')
            os.remove(os.path.join(target_path, '.DS_Store'))
            print('删除目录%s' % target_path)
            os.rmdir(target_path)

        else:
            for dir_name in list_son_dir:
                son_dir_name = os.path.join(target_path, dir_name)
                if os.path.isdir(son_dir_name):
                    clean_empty_dir(son_dir_name)
                else:
                    continue
            # print('重新获取文件夹列表')
            list_son_dir = os.listdir(target_path)
            # print(list_son_dir)
            if not list_son_dir:
                print('删除目录%s' % target_path)
                os.rmdir(target_path)
            elif list_son_dir == ['.DS_Store']:
                print('删除.DS_Store')
                os.remove(os.path.join(target_path, '.DS_Store'))
                print('删除目录%s' % target_path)
                os.rmdir(target_path)

if __name__ == '__main__':
    main()
