import json
import re
import requests
import hashlib
import os
import time
from tqdm import tqdm
from jsonpath import jsonpath
from tabulate import tabulate

"""
似乎只有 Edge 浏览器才能完整听歌，所以抓包要在 Edge 浏览器上抓
逆向的时候，l.signature 那下断点后，会重复执行两次，第二次的 s 值才是真的
"""


# 获取当前脚本文件的绝对路径
file_path = os.path.abspath(__file__)
# 获取当前脚本文件所在的父级文件夹路径
parent_directory = os.path.dirname(file_path)
# 将当前工作目录更改为父级文件夹
os.chdir(parent_directory)

# config.json 一定要放在当前目录下！
# 格式如下：
# {
#     "path": ".\\",
#     "mid": "0376045b610cd30487f66855d296194b",
#     "uuid": "0376045b610cd30487f66855d296194b",
#     "dfid": "34cTSp3R2RvO1lnyUh353ByL",
#     "token": "2e145f0776574048ee733b73e0f5644e175dd8ba6cd97f85c3e3cb3b0e3f5d1e",
#     "userid": 954283296
# }
with open('./config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)
PATH = config['path']
print(f'保存路径：“{PATH}”')

MID = config['mid']
UUID = config['uuid']
DFID = config['dfid']
TOKEN = config['token']
USERID = config['userid']

SEARCH_PAGE_SIZE = config['search_page_size']

T = round(time.time() * 1000)



def md5_hash(string):
    # 创建一个md5对象
    md5 = hashlib.md5()
    # 将字符串转换为字节流并进行MD5加密
    md5.update(string.encode('utf-8'))
    # 获取加密后的十六进制结果
    encrypted_string = md5.hexdigest()
    return encrypted_string


class Audio:

    def __init__(self, id):
        self.id = id
        self.info_url = 'https://wwwapi.kugou.com/play/songinfo'

    def download(self):
        """
        :return: 音乐保存的路径
        """
        audio_url, title = self.audio_url_and_title
        full_path = PATH + title + '.mp3'
        with open(full_path, 'ab') as f:
            resp = requests.get(audio_url, stream=True)
            for chunk in tqdm(resp.iter_content(1024), desc='正在下载歌曲 ' + title, unit='kb'):
                f.write(chunk)
        return full_path

    @property
    def audio_url_and_title(self):
        """
        :return: (音频链接, 标题)
        """
        params = {
            "srcappid": 2919,
            "clientver": 20000,
            f"clienttime": T,
            "mid": MID,
            "uuid": UUID,
            "dfid": DFID,
            "appid": 1014,
            "platid": 4,
            "encode_album_audio_id": self.id,
            "token": TOKEN,
            "userid": USERID,
            "signature": self._signature(),
        }

        resp = requests.get(url=self.info_url, params=params)

        # with open('index.json', 'w', encoding='utf-8') as f:
        #     json.dump(resp.json(), f, indent=4, ensure_ascii=False)

        url = resp.json()['data']['play_url']
        author_name = resp.json()['data']['author_name']
        song_name = resp.json()['data']['song_name']
        return (url, author_name + '-' + song_name)

    def _signature(self):
        """
        解密 signature 参数
        这些参数，params中都有，初步猜测，请求提交到服务器时，
        会按顺序排列 params 中的参数为下面 p 的形状，
        用 md5 加密后再与 params 中的 signature 做对比
        """
        p = [
            "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt",
            "appid=1014",  #
            f"clienttime={T}",
            "clientver=20000",  #
            f"dfid={DFID}",
            f"encode_album_audio_id={self.id}",
            f"mid={MID}",
            "platid=4",  #
            "srcappid=2919",  #
            f"token={TOKEN}",
            f"userid={USERID}",
            f"uuid={UUID}",
            "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"
        ]

        signature = md5_hash(''.join(p))
        return signature


class Search:

    def __init__(self, keyword):
        self.url = 'https://complexsearch.kugou.com/v2/search/song'
        self.keyword = keyword
        self.page_size = SEARCH_PAGE_SIZE

    def get_info(self):
        params = {
            "callback": "callback123",
            "srcappid": 2919,
            "clientver": 1000,
            "clienttime": T,
            "mid": MID,
            "uuid": UUID,
            "dfid": DFID,
            "keyword": self.keyword,
            "page": 1,
            "pagesize": self.page_size,
            "bitrate": 0,
            "isfuzzy": 0,
            "inputtype": 0,
            "platform": "WebFilter",
            "userid": USERID,
            "iscorrection": 1,
            "privilege_filter": 0,
            "filter": 10,
            "token": TOKEN,
            "appid": 1014,
            "signature": self._signature(),
        }
        resp = requests.get(url=self.url, params=params)
        return self._extract(resp.text)

    def _extract(self, r):
        # json 信息被 "callback123()" 包裹起来了
        pattern = re.compile('^callback123\((.*?)\)$')
        json_info = json.loads(pattern.findall(r)[0])
        # with open('index.json', 'w', encoding='utf-8') as f:
        #     json.dump(json.loads(json_info), f, indent=4, ensure_ascii=False)
        id = jsonpath(json_info, '$..EMixSongID')
        singer_names = jsonpath(json_info, '$..SingerName')
        song_names = jsonpath(json_info, '$..SongName')
        album_names = jsonpath(json_info, '$..AlbumName')
        return zip(id, singer_names, song_names, album_names)

    def _signature(self):
        p = [
            "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt",
            "appid=1014",
            "bitrate=0",
            "callback=callback123",
            f"clienttime={T}",
            "clientver=1000",
            f"dfid={DFID}",
            "filter=10",
            "inputtype=0",
            "iscorrection=1",
            "isfuzzy=0",
            f"keyword={self.keyword}",
            f"mid={MID}",
            "page=1",
            f"pagesize={self.page_size}",
            "platform=WebFilter",
            "privilege_filter=0",
            "srcappid=2919",
            f"token={TOKEN}",
            f"userid={USERID}",
            f"uuid={UUID}",
            "NVPh5oo715z5DIWAeQlhMDsWXXQV4hwt"
        ]
        signature = md5_hash(''.join(p))
        return signature

def is_string_digit(s):
    """检查字符串是不是数字"""
    try:
        int(s)
        return True
    except ValueError:
        return False

def main():

    print()
    _ = input('关键词(搜索) >>>')
    s = Search(_)
    d = dict()
    l = list()
    for index, info in enumerate(s.get_info()):
        d[str(index)] = info[0]
        l_ = list(info)
        l_[0] = str(index)
        l.append(l_)
    # 表头
    headers = ['序号', '歌手', '歌曲名', '所属专辑']
    # 打印表格
    print(tabulate(l, headers=headers, tablefmt='grid'))
    while True:
        print('\n输入序号以下载对应歌曲（输入ALL下载全部）')
        _ = input('>>>')
        if is_string_digit(_):
            path = Audio(d[_]).download()
            print(f'歌曲已下载至 “{path}”')
        elif _ == 'ALL':
            for id in d.values():
                Audio(id).download()
        else:
            continue


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f'错误：{e}')
        input()

