from urllib import request, parse
import json
 
def fanyi(content):
    req_url = 'http://fanyi.youdao.com/translate'
    head_data = {}
    head_data['Referer'] = 'http://fanyi.youdao.com/'
    head_data['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36X-Requested-With: XMLHttpRequest'
    form_data = {}
    form_data['i'] = content
    form_data['doctype'] = 'json'
    data = parse.urlencode(form_data).encode('utf-8')
    req = request.Request(req_url, data, head_data)
    response = request.urlopen(req)
    html = response.read().decode('utf-8')
    translate_results = json.loads(html)
    translate_results = translate_results['translateResult'][0][0]['tgt']
#    print(translate_results.capitalize())
    return translate_results.capitalize()


def main():
    while True:
        content = input('请输入要翻译的文字：')
        if content == 'quit':
             break
        else:
            print(fanyi(content))
 
if __name__ == '__main__':
    main()
