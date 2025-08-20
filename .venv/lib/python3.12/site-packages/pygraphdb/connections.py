# -*- coding: UTF-8 -*-
# @Time : 2021/11/11 下午8:33 
# @Author : 刘洪波
from .cursors import Cursor
from .management import Management
import requests


class Connection(object):
    def __init__(self, host: str, port: str, user: str, password: str, db: str):
        """
        连接数据库
        :param host:
        :param port:
        :param db:
        :param user:
        :param password:
        :return:
        """
        login_url = f'http://{host}:{port}/rest/login/{user}'
        headers = {'X-GraphDB-Password': password}
        response = requests.post(login_url, headers=headers)
        if str(response) != '<Response [200]>':
            print(response, 'Connection error, GraphDB not connected')
            raise ValueError(response.text)
        self.authorization = response.headers.get('Authorization')
        self.base_url = f'http://{host}:{port}'
        self.db_name = db

    def cursor(self):
        """
        操作数据库
        :return:
        """
        if self.authorization is None:
            raise Exception('GraphDB not connected')
        query_url = self.base_url + f'/repositories/{self.db_name}?'
        update_url = self.base_url + f'/repositories/{self.db_name}/statements?'
        return Cursor(query_url, update_url, self.authorization)

    def manage_repository(self):
        """
        管理数据库
        :return:
        """
        if self.authorization is None:
            raise Exception('GraphDB not connected')
        return Management(self.base_url, self.authorization)

    def close(self):
        self.authorization = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
