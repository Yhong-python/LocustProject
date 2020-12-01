

#!/usr/bin/env python
# encoding: utf-8
'''
@author: yanghong
@file: LocustDome.py
@time: 2020/12/1 10:57
@desc:
'''
import queue
import sys
import time

from locust import HttpUser, task, TaskSet, events, between


class UserBehavior(TaskSet):
    def on_start(self):
        username = self.user.user_que.get()
        print('运行压测前的前置条件,登录账号%s' % username)
        r = self.client.post("/wwwApi/admin/sys/login",
                             data={"username": username, "password": username[5:], "captcha": "1111"})
        print(r.json())

    def get_response(self, response):
        """
        获取返回
        :param response:请求返回对象
        :return:
        """
        start_time = int(time.time())
        if response.status_code == 200:
            events.request_success.fire(
                requests_type='recv',
                name=sys._getframe().f_code.co_name,
                response_time=int(time.time() - start_time) * 1000,
                response_length=0
            )
        else:
            events.request_failure.fire(
                request_type="recv",
                name=sys._getframe().f_code.co_name,
                response_time=int(time.time() - start_time) * 1000,
                response_length=0,
                exception="Response Code Error! Code:{}".format(response.content)
            )

    @task(1)
    def test_get(self):
        self.client.get("http://www.baidu.com", name="打开百度首页")


    @task(1)
    def test_post(self):
        """由于没有免费的post接口暂时使用百度搜索"""
        r=self.client.get("/wwwApi/admin/sys/loginfo", name="查询登录信息")
        print(r.json()['data']['realName'])


class WebUser(HttpUser):
    """性能测试配置 换算配置"""
    host = "http://testfdv2.gold-cloud.com:82"
    tasks = [UserBehavior]  # Testcase类
    wait_time = between(1, 5)
    user_que = queue.Queue()
    print('11111111')
    user_que.put('19999999999')
    user_que.put('19999999992')
