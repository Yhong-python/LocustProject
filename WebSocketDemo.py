#!/usr/bin/env python
# encoding: utf-8
'''
@author: yanghong
@file: WebSocketDemo.py
@time: 2020/12/1 14:38
@desc:
'''
import socket
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)  # 移除ssl警告
import requests
import random


# socket.setdefaulttimeout(20)
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
import json
import time
import websocket
from locust import TaskSet, task, between, events, HttpUser
import queue
from LocustProject.excelRead import Excel_read


# 实例化
# all_locusts_spawned = Semaphore()
# all_locusts_spawned.acquire()


# 创建等待方法
# def on_hatch_complete(**kwargs):
#     time.sleep(3)
#     print('所有用户已加载完成，开始执行测试')
# all_locusts_spawned.release()


# 当用户加载完成时触发前面的钩子函数解锁
# events.hatch_complete.add_listener(on_hatch_complete)


class WebSocketClient(object):
    def __init__(self, host="wss://server.qixiaosheng.cn"):
        self.host = host
        self.ws = websocket.WebSocket()
        self.ws.settimeout(150)


    def connect(self, burl="/yun/0"):
        start_time = time.time()
        try:
            self.conn = self.ws.connect(url=burl)
        except websocket.WebSocketTimeoutException as e:
            total_time = int((time.time() - start_time) * 1000)
            events.request_failure.fire(request_type="websockt", name=burl, response_time=total_time, exception=e)
        else:
            total_time = int((time.time() - start_time) * 1000)
            events.request_success.fire(request_type="websockt", name=burl, response_time=total_time, response_length=0)
        return self.conn


    def recv(self):
        start_time = time.time()
        msg = self.ws.recv()
        total_time = int((time.time() - start_time) * 1000)
        if json.loads(msg.decode())['sCmd'] == 1000:
            events.request_success.fire(request_type="websockt", name='sCmd:1000', response_time=total_time,
                                        response_length=0)
        elif json.loads(msg.decode())['sCmd'] == 1001:
            events.request_success.fire(request_type="websockt", name='sCmd:1001', response_time=total_time,
                                        response_length=0)
        elif json.loads(msg.decode())['sCmd'] == 1102:
            events.request_success.fire(request_type="websockt", name='sCmd:1102', response_time=total_time,
                                        response_length=0)
        elif json.loads(msg.decode())['sCmd'] == 1103:
            events.request_success.fire(request_type="websockt", name='sCmd:1103', response_time=total_time,
                                        response_length=0)
        return msg


    def send(self, msg):
        self.ws.send(msg)


    def close(self):
        return self.ws.close()



class TestChess(TaskSet):
    def on_start(self):
        pass
        # print('加载用户成功')
        # all_locusts_spawned.wait()


    # 获取登录的token
    def getLoginToken(self, username, eventCode):
        url = "https://server.qixiaosheng.cn/match/login"
        sendData = {
            "phoneNumber": str(username),
            "eventCode": str(eventCode),
            "vcode": "123456",
            "appId": "",
            "cpId": "",
            "chId": "",
            "netType": "",
            "sdkversion": 100020007,
            "system": "OSVersion",
            "model": "DeviceID",
            "brand": "DeviceBrand",
            "channelId": 200000,
            "uid": None
        }
        time.sleep(0.1)
        r = requests.post(url, json=sendData, verify=False)
        # print("http接口登录结果{}".format(r.json()))
        assert r.json()['code'] == 200, "登录失败"
        uid = r.json()['userInfo']['uid']
        yunToken = r.json()['yunToken']
        return uid, yunToken


    def runChess(self,userdata):
        host = "wss://server.qixiaosheng.cn"
        client = WebSocketClient(host)
        self.url = 'wss://server.qixiaosheng.cn/yun/0'
        userData = userdata  # 从队列中取登录信息
        client.connect(self.url)
        while True:  # 先登录,登录之后返回的信息中tabid数字小于0时，每隔5秒再次登录获取信息
            try:
                loginData = self.getLoginToken(username=userData[0], eventCode=userData[1])
                # loginData = self.getLoginToken(username="qxs001", eventCode="100001")
                self.url = 'wss://server.qixiaosheng.cn/yun/0'
                Logindata = {
                    "uid": int(loginData[0]),
                    "mCmd": "1",
                    "sCmd": "100",
                    "serverid": 0,
                    "payload": {
                        "uid": int(loginData[0]),
                        "skey": loginData[1],
                        "macaddr": "92:68:A8:BE"}
                }
                client.send(json.dumps(Logindata))
                time1 = time.time()
                recv = json.loads(client.recv().decode())
                serverid = recv['serverid']
                with open("time.txt", "a+") as fp:
                    fp.write("mCmd:1,sCmd:100的结果时间:" + str(time.time() - time1) + "\n")
                print("websocket接口登录结果{}".format(recv))
                if recv['sCmd'] == 1000 and int(recv['payload']['tabid']) <= 0:  # 小于登录0说明还没有比赛信息，没有桌子，需要一直登录获取比赛信息
                    time.sleep(5)
                    print('{}当前还没有比赛信息，重新登录'.format(userData[0]))
                    continue
                elif recv['sCmd'] == 1000 and int(recv['payload']['tabid']) > 0:  # 否则跳出循环后请求重新加入游戏的接口
                    tabid = int(recv['payload']['tabid'])
                    print("当前账号{}已有比赛信息,桌子id为{}".format(userData[0], tabid))
                    break
            except Exception as e:
                print('账号{}在获取登录信息中的tabid时超时,10秒后重试'.format(userData[0]))
                time.sleep(10)
                return False
                # continue


        joinGameData = {"uid": loginData[0], "mCmd": "2", "sCmd": "101", "serverid": serverid,
                        "payload": {"tabid": tabid, "macaddr": "C7:83:66:DF"}}
        client.send(json.dumps(joinGameData))
        msgList = []
        count = 0
        while count != 7:
            try:
                recv = json.loads(client.recv().decode())
            except Exception as e:
                print('账号{}在获取请求"mCmd": "2", "sCmd": "101"后返回的7个信息中时超时'.format(userData[0]))


                continue
            else:
                msgList.append(recv)
                count += 1


        for msg in msgList:
            if msg['sCmd'] == 1001:
                myCid = msg['payload']['cid']
                if myCid == 1:
                    print('当前账号：{}是黑方'.format(userData[0]))
                elif myCid == 2:
                    print('当前账号：{}是红方'.format(userData[0]))
                break
        else:
            while True:
                try:
                    recv = json.loads(client.recv().decode())
                    if recv['sCmd'] == 1001:
                        myCid = recv['payload']['cid']
                        if myCid == 1:
                            print('当前账号：{}是黑方'.format(userData[0]))
                        elif myCid == 2:
                            print('当前账号：{}是黑方'.format(userData[0]))
                        break
                except Exception as e:
                    print('账号{}在获取代码1001中返回的所属红/黑方时超时,10秒后重试'.format(userData[0]))
                    time.sleep(10)
                    # continue
                    return False
        # #等待游戏开始
        # 加入游戏后，等待棋局开始的1102命令
        for msg in msgList:
            if msg['sCmd'] == 1102:
                print('棋局开始')
                break
        else:
            while True:
                try:
                    # time1=time.time()
                    recv = json.loads(client.recv().decode())
                    # with open("time.txt", "a+") as fp:
                    #     fp.write(str(time.time()-time1)+"\n")
                    if recv['sCmd'] == 1102:
                        print('棋局开始')
                        break
                except Exception as e:
                    print('账号{}在开始棋局时超时,10秒后重试'.format(userData[0]))
                    time.sleep(10)
                    # continue
                    return False
        # cid=2#红方   cid=1黑方
        # 红方车向上走一格的坐标
        payload_BLACK_FORWARD = {"sx": 0, "sy": 0, "ex": 0, "ey": 1, "macaddr": "3E:93:7F:36"}  # 黑方的车往上走一步
        payload_BLACK_BACK = {"sx": 0, "sy": 1, "ex": 0, "ey": 0, "macaddr": "3E:93:7F:36"}  # 黑方的车往下走一步
        move1Data = {"uid": loginData[0], "mCmd": "2", "sCmd": "104", "serverid": 20021, "payload": None}
        move2Data = {"uid": loginData[0], "mCmd": "2", "sCmd": "104", "serverid": 20021, "payload": None}
        move3Data = {"uid": loginData[0], "mCmd": "2", "sCmd": "104", "serverid": 20021, "payload": None}


        payload_RED_pao_first = {"sx": 7, "sy": 7, "ex": 7, "ey": 5, "macaddr": "6D:20:71:4B"}  # 红方的炮，走第一步
        payload_RED_pao_second = {"sx": 7, "sy": 5, "ex": 4, "ey": 5, "macaddr": "6D:20:71:4B"}  # 红方的炮，走第二步
        payload_RED_pao_third = {"sx": 4, "sy": 5, "ex": 4, "ey": 0, "macaddr": "6D:20:71:4B"}  # 红方的炮，走第三步，吃将
        if myCid == 1:
            move1Data['payload'] = payload_BLACK_FORWARD  # 黑方车往前一步
            move2Data['payload'] = payload_BLACK_BACK  # 黑方车往后一步
            move3Data['payload'] = payload_BLACK_FORWARD  # 黑方车往前一步
        elif myCid == 2:
            move1Data['payload'] = payload_RED_pao_first  # 红方炮走前面
            move2Data['payload'] = payload_RED_pao_second  # 红方炮将军
            move3Data['payload'] = payload_RED_pao_third  # 红方吃将


        while True:
            try:
                recv = json.loads(client.recv().decode())
                if recv['sCmd'] == 1125 and recv['payload']['cid'] == myCid:
                    move1Data['serverid'] = recv['serverid']
                    sleeptime = random.randint(3, 10)
                    print('{},{}秒后下第一步'.format(userData[0], sleeptime))
                    time.sleep(sleeptime)
                    client.send(json.dumps(move1Data))
                    break
            except Exception as e:
                print('账号{}在下第一步棋时超时'.format(userData[0]))
                return False
        while True:
            try:
                recv = json.loads(client.recv().decode())
                if recv['sCmd'] == 1125 and recv['payload']['cid'] == myCid:
                    move2Data['serverid'] = recv['serverid']
                    sleeptime = random.randint(3, 10)
                    print('{},{}秒后下第二步'.format(userData[0], sleeptime))
                    time.sleep(sleeptime)
                    client.send(json.dumps(move2Data))
                    break
            except Exception as e:
                print('账号{}在下第二步棋时超时'.format(userData[0]))
                return False
        while True:
            try:
                recv = json.loads(client.recv().decode())
                if recv['sCmd'] == 1125 and recv['payload']['cid'] == myCid:
                    move3Data['serverid'] = recv['serverid']
                    sleeptime = random.randint(3, 10)
                    print('{},{}秒后下第三步'.format(userData[0], sleeptime))
                    time.sleep(sleeptime)
                    client.send(json.dumps(move3Data))
                    break
            except Exception as e:
                print('账号{}在下第三步棋时超时'.format(userData[0]))
                return False
        while True:
            try:
                recv = json.loads(client.recv().decode())
                if recv['sCmd'] == 1103 and recv['payload']['endType'] == '红方吃将':
                    print('{}正常结束棋局'.format(userData[0]))
                    with open("success.txt", "a+") as fp:
                        fp.write("账号:{},正常结束对局".format(userData[0]) + "\n")
                    break
            except:
                print('账号{}在接收下棋结果时超时'.format(userData[0]))
                return False
        client.ws.close()
        # with open("success.txt", "a+") as fp:
        #     fp.write("账号:{},正常结束对局".format(userData[0]) + "\n")
        return True


    @task
    def test(self):
        userData=self.user.queue.get()
        resultFlag = self.runChess(userData)
        retryCount = 0
        while not resultFlag:
            resultFlag = self.runChess(userData)
            retryCount += 1
            if retryCount == 2:
                print('错误重试2次都失败')
                break
        while True:
            print('===========')
            time.sleep(60)


class WebsocketLocust(HttpUser):
    def __init__(self, *args, **kwargs):
        super(WebsocketLocust, self).__init__(*args, **kwargs)


    allData = Excel_read('logindata.xlsx', 'Sheet1').getAllData()
    user100 = []
    for i in range(len(allData)):
        if i <= 799:
            user100.append(allData[i])
        else:
            continue
    queue = queue.Queue()
    for i in user100:
        queue.put(i)
    wait_time = between(1, 3)
    tasks = [TestChess]
    host = "wss://server.qixiaosheng.cn"
