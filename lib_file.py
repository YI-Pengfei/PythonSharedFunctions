"""
    2019.09.10  save/load dictionary to/as json
	2019.08.25  pickle save/load object.
	集成了常用的文件操作函数
"""
import os
import shutil
import pickle
import json
import lxml.etree as ET
import pandas as pd

def read_csv2dict(f,key,value):
    """ read CSV, 并指定两列作为键和值
    """
    df = read_file2df(f)
    return dict(zip(df[key], df[value]))


def read_file2df(f,encoding='utf-8'):
    """read CSV or EXCEL file
        有时会由于编码的问题无法工作
    """
    if f.endswith('.csv'):
        return pd.read_csv(f,encoding=encoding)
    elif f.endswith('.xls') or f.endswith('.xlsx'):
        return pd.read_excel(f,encoding=encoding)
    else:
        print('Unsupported file format!')
        return None

def read_XML2df(f,encoding='utf-8'):
    """ 针对欧洲铁路车站XML格式编的代码
    """
    tree = ET.parse(f)
    stations = tree.findall('station')
    temp = []
    for s in stations:    
        temp.append([s.attrib['name'],s.attrib['lon'],s.attrib['lat'], s.attrib['country'], s.attrib['UTC']])
    return pd.DataFrame(temp, columns=['name','lon','lat','country','time_zone'])
    
    
def get_LocIndex(df, key='name', lon='lon', lat='lat'):    
    """ 创建一个 name:[lon,lat] 的字典
    """
    dict_NameLocation = {}   # name:location
    temp_locs = df.set_index(key).T.to_dict()
    for name in temp_locs:
        if name in dict_NameLocation:
            print('Warning. Key is not unique!')
        dict_NameLocation[name] = (temp_locs[name][lon],temp_locs[name][lat])
    return dict_NameLocation

##############################################################################
def move_file(in_file,out_file):
    """
    剪切文件
    in_file：输入文件名（完整路径的）
    out_file：输出文件名（完整路径的）
    """
    s=out_file.split(os.sep)
    out_path = ""
    for i in s[:-1]:
        out_path+=i+os.sep
    if not os.path.exists(out_path):
        os.makedirs(out_path) 
    shutil.move(in_file,out_file)


def copy_file(in_file,out_file):
    """
    复制文件
    in_file：输入文件名（完整路径的）
    out_file：输出文件名（完整路径的）
    """
    s=out_file.split(os.sep)
    # 生成路径
    out_path = ""
    for i in s[:-1]:
        out_path+=i+os.sep
    if not os.path.exists(out_path):
        os.makedirs(out_path) 
    # 复制文件
    shutil.copy(in_file,out_file)


def list_all_files(rootdir, type=None):
    """
    列出该目录下的所有文件
    以列表形式输出所有文件
    """
    _files = []
    lst = os.listdir(rootdir) #列出文件夹下所有的目录与文件
    for i in range(0,len(lst)):
           path = os.path.join(rootdir,lst[i])
           if os.path.isdir(path):
              _files.extend(list_all_files(path))
           if os.path.isfile(path):
              _files.append(path)
    if type:
        _files = [f for f in _files if f.endswith(type)]
    return _files

def find_corresponding(f,files):
    """
    f: 输入的文件名（可以只是文件名，也可以是包含完整路径的文件名）
    files: 待查找的文件列表
    从文件列表中寻找文件f，输出找到的文件路径
    """
    short_name = f.split(os.sep)[-1]
    for f_new in files:
        if short_name in f_new.split(os.sep):
            return f_new
    print('No corresponding file:',f)
    return None

##########################  pickle  ##########################################
def pickle_save(obj,file):
    with open(file,'wb') as f:
        pickle.dump(obj,f)
        
def pickle_load(file):
    with open(file,'rb') as f:
        obj = pickle.load(f)
    return obj
######################### json ################################################
def json_save(test_dict, file,encoding='utf-8'):
    json_str = json.dumps(test_dict, indent=4,ensure_ascii =False)
    with open(file, 'w',encoding=encoding) as json_file:
        json_file.write(json_str)

def json_load(file,encoding='utf-8'):
    with open(file, 'r',encoding=encoding) as f:
        #print("Load str file from {}".format(file))
        str1 = f.read()
        r = json.loads(str1)
    return r

###########################  DataFrame与字典     ##########################################
def creat_dict_from_CSV(f,key,value):
    df = pd.read_csv(f)
    return dict(zip(df[key], df[value]))



