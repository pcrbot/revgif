import asyncio
import os
import random
import re
from io import BytesIO

import requests
from PIL import Image, ImageSequence

from hoshino import Service, priv
from hoshino.typing import CommandSession, CQEvent, Message

sv_help = '''
- [倒放 + 图片 + 规则] 图片必须为gif图
- 规则列表：
    - [随机/左右/上下/顺90/逆90/180]
'''.strip()

sv = Service(
    name='GIF倒放',  # 功能名
    use_priv=priv.NORMAL,  # 使用权限
    manage_priv=priv.ADMIN,  # 管理权限
    visible=True,  # 是否可见
    enable_on_default=True,  # 是否默认启用
    bundle='通用',  # 属于哪一类
    help_=sv_help  # 帮助文本
)


@sv.on_fullmatch(["帮助GIF倒放"])
async def bangzhu(bot, ev):
    await bot.send(ev, sv_help, at_sender=True)


headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
fd = os.path.dirname(__file__)


@sv.on_keyword(("GIF倒放", "gif倒放", "gifrev"))
async def revgif(bot, ev: CQEvent):
    fmsg = ev.message[0]
    if fmsg.type == 'reply':  # 回复消息第一个消息段type一定是reply
        # 情况1，用户对需要倒放的gif进行回复
        pre_message = await bot.get_msg(message_id=fmsg.data['id'])
        msg = Message(pre_message["message"])
    else:
        # 情况2，直接命令带图
        msg = ev.message
    ifturn = None
    ifturn = judge_ifturn(event=ev, arg=ifturn)
    imgcount = 0
    for i in msg:
        if i.type == 'image':
            imgcount += 1
            asyncio.get_event_loop().create_task(
                do_revgif(bot, ev, i.data['url'], ifturn))
    if not imgcount:
        await bot.finish(ev, "未找到图片信息，请尝试重新发送图片")


def judge_ifturn(arg, event=None):
    if event is not None:
        if re.search(r"随机|(?i)random", event.raw_message):
            arg = random.choice(
                [Image.FLIP_LEFT_RIGHT,
                 Image.FLIP_TOP_BOTTOM,
                 Image.ROTATE_90,
                 Image.ROTATE_180,
                 Image.ROTATE_270,
                 Image.TRANSPOSE,
                 Image.TRANSVERSE])
        elif re.search(r"左右|(?i)lr", event.raw_message):
            arg = Image.FLIP_LEFT_RIGHT
        elif re.search(r"上下|(?i)ud", event.raw_message):
            arg = Image.FLIP_TOP_BOTTOM
        elif re.search(r"(逆|(?i)l)90", event.raw_message):
            arg = Image.ROTATE_90
        elif re.search(r"180", event.raw_message):
            arg = Image.ROTATE_180
        elif re.search(r"(顺|(?i)r)90", event.raw_message):
            arg = Image.ROTATE_270
        else:
            arg = None
    else:
        if re.search(r"随机|(?i)random", arg):
            arg = random.choice(
                [Image.FLIP_LEFT_RIGHT,
                 Image.FLIP_TOP_BOTTOM,
                 Image.ROTATE_90,
                 Image.ROTATE_180,
                 Image.ROTATE_270,
                 Image.TRANSPOSE,
                 Image.TRANSVERSE])
        elif re.search(r"左右|(?i)lr", arg):
            arg = Image.FLIP_LEFT_RIGHT
        elif re.search(r"上下|(?i)ud", arg):
            arg = Image.FLIP_TOP_BOTTOM
        elif re.search(r"(逆|(?i)l)90", arg):
            arg = Image.ROTATE_90
        elif re.search(r"180", arg):
            arg = Image.ROTATE_180
        elif re.search(r"(顺|(?i)r)90", arg):
            arg = Image.ROTATE_270
        else:
            arg = None
    return arg


img = {}
send_times = {}


@sv.on_command("rev", only_to_me=True, aliases=("倒放", "revgif"))
async def match_next(session: CommandSession):
    event = session.ctx
    uid = event['user_id']
    if uid not in img:
        img[uid] = []
    if uid not in send_times:
        send_times[uid] = 0
    msg = event.message
    rule = re.compile(r"^\[CQ:image.+$")

    if re.match(rule, str(msg)) and len(img[uid]) == 0:
        image_url = msg[0].data["url"]
        img[uid].append(image_url)
    elif len(img[uid]) == 1 and not re.match(rule, str(msg)):
        img[uid].extend(msg)
    else:
        send_times[uid] += 1
    if send_times[uid] >= 3:
        img[uid] = []
        send_times[uid] = 0
        await session.finish('过多次未发送图片，已自动停止')

    if len(img[uid]) == 0:
        session.pause('请发送图片')
    elif len(img[uid]) == 1:
        session.pause('请发送变换规则，随意输入代表不自定义变换')
    elif len(img[uid]) >= 2:
        pic = img[uid][0]
        ifturn = img[uid][1].data["text"]
        ifturn = judge_ifturn(arg=ifturn)
        await do_revgif(session.bot, session.event, pic, ifturn)
        img[uid] = []
        send_times[uid] = 0


async def do_revgif(bot, ev, image_url, ifturn=None):
    print("正在准备图片")
    response = requests.get(image_url, headers=headers)
    image = Image.open(BytesIO(response.content))
    print(f"frames:{image.n_frames}, mode:{image.mode}, info:{image.info}")

    if image.n_frames == 1:
        await bot.finish(ev, "并非GIF图片")
    if image.n_frames > 200:
        await bot.finish(ev, "GIF帧数太多了，懒得倒放[CQ:face,id=13]")

    sequence = []
    for f in ImageSequence.Iterator(image):
        sequence.append(f.copy())
    if len(sequence) > 30:
        await bot.send(ev, "ℹ正在翻转图片序列，请稍候")
    sequence = [f.transpose(ifturn).copy() if ifturn is not None else f.copy()
                for f in ImageSequence.Iterator(image)]
    sequence.reverse()
    gif_path = os.path.join(fd, f"{ev.user_id}.gif")
    sequence[0].save(gif_path, save_all=True,
                     append_images=sequence[1:], disposal=1, loop=0)

    if os.path.exists(gif_path):
        await bot.send(ev, f"[CQ:image,file=file:///{gif_path}]")
        os.remove(gif_path)
    else:
        await bot.finish(ev, "写入文件时发生未知错误")
