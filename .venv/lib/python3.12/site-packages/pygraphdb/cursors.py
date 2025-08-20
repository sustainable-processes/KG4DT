# -*- coding: UTF-8 -*-
# @Time : 2021/11/15 下午6:04 
# @Author : 刘洪波
import requests


class Cursor(object):
    def __init__(self, query_url, update_url, authorization):
        self.query_url = query_url
        self.update_url = update_url
        self.authorization = authorization
        self.is_close = False

    def execute(self, sparql: str):
        """
        执行 sparql
        :param sparql: 例 "SELECT ?s ?p ?o WHERE {?s ?p ?o .} LIMIT 100"
        :return:
        """
        if self.is_close:
            raise Exception('Cursor is closed')
        use_type, params = self.check_key(sparql)
        if use_type == 'query':
            res = requests.get(self.query_url, headers={'Authorization': self.authorization}, params=params)
        else:
            res = requests.post(self.update_url, headers={'Authorization': self.authorization}, data=params)
        if str(res) == '<Response [200]>' and use_type == 'query':
            return res.text
        elif str(res) == '<Response [204]>' and use_type == 'update':
            return res.text
        else:
            print(res)
            raise ValueError(res.text)

    def download_data(self, file_path: str = None):
        """
        下载数据
        :param file_path: 文件路径  例：'./file.rdf' ，'./file.owl' 或 './file.json'
                          当文件路径为None时， 下载的时原始数据流，需自己保存至自己所需的格式。
                          下载的json格式数据不能用于导入图数据，rdf、owl 可以用于导入图数据
        :return:
        """
        if self.is_close:
            raise Exception('Cursor is closed')
        if file_path is None:
            params = {'Accept': 'application/rdf+xml'}
        elif '.rdf' in file_path or '.owl' in file_path:
            params = {'Accept': 'application/rdf+xml'}
        elif '.json' in file_path:
            params = {'Accept': 'application/rdf+json'}
        else:
            raise ValueError('file_path is error, Only RDF、OWL and JSON formats are supported')
        data = requests.get(self.update_url, headers={'Authorization': self.authorization}, params=params)
        if str(data) == '<Response [200]>':
            if file_path:
                with open(file_path, "wb") as fp:
                    itr = data.iter_content()
                    for content in itr:
                        fp.write(content)
                return 'Download successful'
            else:
                print('After downloading the original data successfully, you need to save the desired format yourself')
                return data
        else:
            print(data)
            raise ValueError(data.text)

    def upload_data(self, file_path: str = None):
        """
        上传数据
        :param file_path:
        :return:
        """
        if self.is_close:
            raise Exception('Cursor is closed')
        if '.rdf' not in file_path and '.owl' not in file_path:
            raise ValueError('file_path is error, Only RDF and OWL formats are supported')
        headers = {'Authorization': self.authorization, "Content-Type": "application/xml"}
        with open(file_path, 'rb') as f:
            res = requests.post(url=self.update_url, data=f.read(), headers=headers)
            if str(res) == '<Response [204]>':
                return 'Upload successful'
            else:
                print(res)
                raise ValueError(res.text)

    def delete_all_data(self):
        """
        删除全部的节点数据
        :return:
        """
        if self.is_close:
            raise Exception('Cursor is closed')
        self.execute('DELETE WHERE {?s ?r ?o}')
        return 'Delete successful'

    @staticmethod
    def check_key(sparql):
        """
        校验sparql里的关键字
        :param sparql:
        :return:
        """
        upper_sparql = sparql.upper()
        query = ['SELECT', 'CONSTRUCT', 'ASK', 'DESCRIBE']
        update = ['INSERT', 'DELETE']
        for q in query:
            if q in upper_sparql:
                params = {'query': sparql}
                return 'query', params
        for u in update:
            if u in upper_sparql:
                params = {'update': sparql, 'infer': True, 'sameAs': True}
                return 'update', params
        raise ValueError('sparql error, Keyword deletion')

    def close(self):
        self.query_url = None
        self.update_url = None
        self.authorization = None
        self.is_close = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
