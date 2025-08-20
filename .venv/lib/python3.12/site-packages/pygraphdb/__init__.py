# -*- coding: UTF-8 -*-
# @Time : 2021/11/11 下午8:16 
# @Author : 刘洪波


def connect(host, port, user, password, db=None):
    from .connections import Connection
    return Connection(host, port, user, password, db)




