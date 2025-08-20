# -*- coding: UTF-8 -*-
# @Time : 2022/4/28 下午3:34 
# @Author : 刘洪波
import requests
import json
from .graphdb_free_config import gf_config


class Management(object):
    def __init__(self, base_url, authorization):
        self.base_url = base_url
        self.authorization = authorization
        self.base_mge_url = base_url + '/rest/repositories'
        self.headers = {'Authorization': self.authorization}
        self.is_close = False

    def get_repository_list(self):
        """获取现有的repository列表"""
        if self.is_close:
            raise Exception('Manager is closed')
        res = requests.get(self.base_mge_url, headers=self.headers)
        if str(res) == '<Response [200]>':
            return res.text
        else:
            print(res)
            raise ValueError(res.text)

    def delete_repository(self, repository_id: str):
        """删除现有的repository"""
        if self.is_close:
            raise Exception('Manager is closed')
        if isinstance(repository_id, str):
            res = requests.delete(self.base_mge_url + '/' + repository_id, headers=self.headers)
            if str(res) == '<Response [200]>':
                return f'Delete {repository_id} repository successful'
            else:
                print(f'Delete {repository_id} repository failed, {str(res)}')
                raise ValueError(res.text)
        else:
            raise ValueError('type error: repository_id is not a string, repository_id must be a string')

    def create_repository_graphdb_free(self, repository_id: str, repository_description=None, other_params=None):
        """
        创建一个repository
        :param repository_id:
        :param repository_description:
        :param other_params: repository的详细配置，当为None时创建一个默认参数的repository
        :return:
        """
        if self.is_close:
            raise Exception('Manager is closed')
        if isinstance(repository_id, str):
            gf_config['id'] = repository_id
        else:
            raise ValueError('type error: repository_id is not a string, repository_id must be a string')
        if repository_description:
            if isinstance(repository_id, str):
                gf_config['title'] = repository_description
            else:
                raise ValueError('type error: repository_description is not a string or None, '
                                 'repository_description must be a string or None')
        if other_params:
            if isinstance(other_params, str):
                gf_config['params'] = other_params
            else:
                raise ValueError('type error: other_params is not a string or None, '
                                 'other_params must be a string or None')
        headers = self.headers.copy()
        headers['Accept'] = 'application/json'
        headers["content-type"] = "application/json;charset=UTF-8"
        res = requests.post(self.base_mge_url, headers=headers, data=json.dumps(gf_config))
        if str(res) == '<Response [201]>':
            return f'Create {repository_id} repository successful, repository type is graphdb free'
        else:
            print(f'Create {repository_id} repository failed, {str(res)}')
            raise ValueError(res.text)

    def restart_repository(self, repository_id: str):
        """重启现有的repository"""
        if self.is_close:
            raise Exception('Manager is closed')
        if isinstance(repository_id, str):
            res = requests.post(self.base_mge_url + '/' + repository_id + '/restart', headers=self.headers)
            if str(res) == '<Response [202]>':
                return f'Restart {repository_id} repository successful'
            else:
                print(f'Restart {repository_id} repository failed, {str(res)}')
                raise ValueError(res.text)
        else:
            raise ValueError('type error: repository_id is not a string, repository_id must be a string')

    def get_repository_size(self, repository_id: str):
        """获取现有的repository size"""
        if self.is_close:
            raise Exception('Manager is closed')
        if isinstance(repository_id, str):
            res = requests.get(self.base_mge_url + '/' + repository_id + '/size', headers=self.headers)
            if str(res) == '<Response [200]>':
                return res.text
            else:
                print(f'Get {repository_id} repository size failed, {str(res)}')
                raise ValueError(res.text)
        else:
            raise ValueError('type error: repository_id is not a string, repository_id must be a string')

    def close(self):
        self.base_url = None
        self.authorization = None
        self.base_mge_url = None
        self.headers = None
        self.is_close = True

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
