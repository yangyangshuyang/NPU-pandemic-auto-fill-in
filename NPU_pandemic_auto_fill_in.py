import math
import sys
import requests
import json
import re
from bs4 import BeautifulSoup
from places import placesMap

# 调试模式，开启后使用本地的配置，而不使用参数读入
debug = False

# 网页url
yqtb_url = "https://yqtb.nwpu.edu.cn"
uis_login_url = "https://uis.nwpu.edu.cn/cas/login?service=https%3A%2F%2Fyqtb.nwpu.edu.cn%2F%2Fsso%2Flogin.jsp%3FtargetUrl%3Dbase64aHR0cHM6Ly95cXRiLm53cHUuZWR1LmNuLy93eC94Zy95ei1tb2JpbGUvaW5kZXguanNw"
yqtb_fillin_url = "https://yqtb.nwpu.edu.cn/wx/ry/" # 获取到签名和时间戳后拼接上去
yqtb_detail_url = "https://yqtb.nwpu.edu.cn/wx/ry/jrsb_xs.jsp"

# 疫情填报的会话ID
yqtb_cookie = ""
# 指示是否成功
flag = True
# 指示是否成功发送填报数据并获取返回值
filled = False
# 服务器返回的状态信息
state = "1"
# 服务器返回的错误信息
error = ""

if debug:
    from debug import *

else:
# 用户信息，通过参数读取
    studentId = sys.argv[1]
    password = sys.argv[2]
    webhook = ""
    try:
        webhook = sys.argv[3]
    except:
        webhook = ""

# 打印学生信息
print("西北工业大学 疫情自动填报Python脚本")
print("【免责声明】本脚本专为懒人准备，不代表校方观点。若填报失败、填报错误、被后台识别等，开发者不负任何责任。使用此脚本则表示你已阅读并同意以上免责声明。")
print("你的学号：" + studentId)
print("你的密码：" + "***")

try:
    # 创建会话
    session = requests.Session()
    # 请求疫情填报页面
    response1 = session.get(yqtb_url)
    yqtb_cookie = session.cookies["JSESSIONID"] # 疫情填报的会话id
    print("会话ID：" + yqtb_cookie)

    # 登录所用的execution的值
    execution = re.findall('(?<=<input type="hidden" name="execution" value=").*?(?="/>)', response1.text)[0]

    # 登录翱翔门户post的数据
    loginData = {
        "username" : studentId,
        "password" : password,
        "currentMenu" : 1,
        "execution" : execution,
        "_eventId" : "submit",
        "geolocation" : "",
        "submit" : "稍等片刻……"
    }

    # 请求登录
    response2 = session.post(uis_login_url, data = loginData)

    # 填报所需要的header
    # 为减少被识别的风险，User-Agent用的是安卓浏览器
    fillinHeader = {
        "Host" : "yqtb.nwpu.edu.cn",
        "Connection" : "keep-alive",
        "sec-ch-ua" : '".Not/A)Brand";v="99", "Google Chrome";v="103", "Chromium";v="103"',
        "Accept" : "application/json, text/javascript, */*; q=0.01",
        "DNT" : "1",
        "sec-ch-ua-mobile" : "?1",
        "User-Agent" : "Mozilla/5.0 (Linux; Android 4.4.2; Nexus 4 Build/KOT49H) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/34.0.1847.114 Mobile Safari/537.36",
        "Content-Type" : "application/x-www-form-urlencoded",
        "Accept" : "application/json, text/javascript, */*; q=0.01",
        "X-Requested-With" : "XMLHttpRequest",
        "sec-ch-ua-platform" : '"Android"',
        "Origin" : yqtb_url,
        "Sec-Fetch-Site" : "same-origin",
        "Sec-Fetch-Mode" : "cors",
        "Sec-Fetch-Dest" : "empty",
        "Referer" : yqtb_detail_url,
        "Accept-Encoding" : "gzip, deflate, br",
        "Accept-Language" : "zh-CN,zh;q=0.9,en;q=0.8",
        "Cookie" : "JSESSIONID=" + yqtb_cookie
    }

    # 获取填报主页面
    response3 = session.get(yqtb_detail_url, headers = fillinHeader)

    soup = BeautifulSoup(response3.text, 'html.parser')
    # 判断已经填报的位置信息
    #  数值   位置   多选框的id（HTML）
    #   0    在学校     x11
    #   1    在西安     x12
    #   2    在国内     x13
    #   3    在国外     x14
    position = -1
    if "checked" in soup.select("#x11")[0].attrs:
        position = 0
    elif "checked" in soup.select("#x12")[0].attrs:
        position = 1
    elif "checked" in soup.select("#x13")[0].attrs:
        position = 2
    elif "checked" in soup.select("#x14")[0].attrs:
        position = 3

    # 未获取到位置信息，抛异常
    if position == -1:
        filled = True
        state = "[脚本错误]"
        error = "未获取到“当前所在位置”，请手动填一次再运行"
        raise

    # 从返回的js脚本中提取硬编码信息
    content = response3.content.decode("utf-8")

    # 提取姓名
    name = re.findall("(?<=userName:').*?(?=')", content)[0]
    # 提取userType
    userType = re.findall("(?<=userType:').*?(?=')", content)[0]
    # 提取qrlxzt（不明所以）
    qrlxzt = re.findall("(?<=qrlxzt:').*?(?=')", content)[0]
    # 提取bdzt（不明所以）
    bdzt = re.findall("(?<=bdzt:').*?(?=')", content)[0]
    # 提取所在学院
    college = re.findall("(?<=xymc:').*?(?=')", content)[0]
    # 提取手机号
    phoneNumber = re.findall("(?<=xssjhm:').*?(?=')", content)[0]
    # 提取地区编码
    place = re.findall('(?<=select\\(")[0-9]+(?="\\))', content)[0]
    # 提取签名和时间戳
    extract = re.findall("ry_util.jsp.*(?=')",content)[0]
    yqtb_fillin_url += extract

    # 共通填报信息，不含地区（神TM知道这些是啥）
    fillinData = {
        "hsjc" : 1,
        "sfczbcqca": "",
        "czbcqcasjd": "",
        "sfczbcfhyy": "",
        "czbcfhyysjd": "",
        "actionType" : "addRbxx",
        "userLoginId" : studentId,
        "userName": name,
        "sfjt": 0,
        "sfjtsm": "",
        "sfjcry": 0,
        "sfjcrysm": "",
        "sfjcqz": 0,
        "sfyzz" : 0,
        "sfqz" : 0,
        "ycqksm": "",
        "glqk": 0,
        "glksrq": "",
        "gljsrq": "",
        "tbly": "sso",
        "glyy": "",
        "qtqksm": "",
        "sfjcqzsm": "",
        "sfjkqk": 0,
        "jkqksm": "",
        "sfmtbg": "",
        "userType": userType,
        "qrlxzt": qrlxzt,
        "bdzt": bdzt,
        "xymc": college,
        "xssjhm": phoneNumber
    }

    if position == 0: # 在学校
        # 额外填报信息，即所在地区
        extraData = {
            "szcsbm": 1,
            "szcsmc": "在学校",
            "szcsmc1": "在学校"
        }

    elif position == 1: # 在西安
        # 详细居住信息
        detail = soup.select("#xaxxdz")[0].attrs["value"]
        district = placesMap[place]
        place = int(place)
        cityCode = format(math.floor(int(place/100))*100)
        city = placesMap[cityCode]
        provinceCode = format(math.floor(int(place/10000))*10000)
        province = placesMap[provinceCode]
        extraData = {
            "szcsbm": place,
            "szcsmc": province + city + district + detail,
            "szcsmc1": province + city + district
        }

    elif position == 2: # 在国内
        district = placesMap[place]
        place = int(place)
        cityCode = format(math.floor(int(place/100))*100)
        city = placesMap[cityCode]
        provinceCode = format(math.floor(int(place/10000))*10000)
        province = placesMap[provinceCode]
        extraData = {
            "szcsbm": place,
            "szcsmc": province + city + district,
            "szcsmc1": province + city + district
        }

    elif position == 3: # 在国外
        # 详细居住信息
        detail = soup.select("#xaxxdz")[0].attrs["value"]
        extraData = {
            "szcsbm": 4,
            "szcsmc": detail,
            "szcsmc1": detail
        }

    # 将地区信息拼接到填报信息中
    fillinData.update(extraData)

    # 提交填报信息
    response4 = session.post(yqtb_fillin_url, data = fillinData, headers = fillinHeader)
    message = response4.text.strip().replace("\n", "").replace("\r", "").replace("－", "-") # 草（请赏析草字的妙处，6分）
    dict = json.loads(message)
    filled = True
    state = dict["state"]

    if state != "1":
        flag = False
        if "err-msg" in dict:
            error = dict["err-msg"]
        elif "err_msg" in dict:
            error = dict["err_msg"]
        else:
            error = "[疫情自动填报]无法访问错误信息"

except:
    flag = False # 设置状态为失败

# 打印信息
if flag:
    print("填报成功")
else:
    print("填报失败")
    if filled:
        print("错误码：" + str(state))
        print("错误信息：" + error)

# 发送钉钉通知
if len(webhook) != 0:
    message = "【疫情自动填报】"
    if flag:
        message += "填报成功"
    elif filled:
        message += "填报失败\n错误码：" + str(state) + "\n错误信息：" + error
    else:
        message += "填报失败"
    if filled and len(yqtb_cookie) != 0:
        message += "\n会话ID：" + yqtb_cookie
    # 要发送的数据
    data = {
        "msgtype" : "text",
        "text" : {
            "content" : message
        },
        "at" : {
            "isAtAll" : not flag
        }
    }
    try:
        requests.post(webhook, data = json.dumps(data), headers = {"Content-Type": "application/json"})
    except:
        print("发送钉钉通知失败")
        sys.exit(1)

if not flag:
    sys.exit(1)