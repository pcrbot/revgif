import base64
import random
import asyncio
from io import BytesIO
from PIL import Image, ImageSequence

from hoshino import Service, aiorequests
from hoshino.typing import CQEvent, Message, MessageSegment as ms

sv = Service('revgif', help_="GIF倒放功能")

headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }


@sv.on_keyword("倒放")
async def revgif(bot, ev: CQEvent):
    fmsg = ev.message[0]
    if fmsg.type == 'reply':  # 回复消息第一个消息段type一定是reply
        # 情况1，用户对需要倒放的gif进行回复
        pre_message = await bot.get_msg(message_id=fmsg.data['id'])
        msg = Message(pre_message["message"])
    else:
        # 情况2，直接命令带图
        msg = ev.message
    ifturn = '翻转' in ev.raw_message
    imgcount = 0
    for i in msg:
        if i.type == 'image':
            imgcount += 1
            asyncio.get_event_loop().create_task(
                do_revgif(bot, ev, i.data['url'], ifturn))
    if not imgcount:
        await bot.finish(ev, "未找到图片信息，请尝试重新发送图片")


async def do_revgif(bot, ev, image_url, ifturn):
    print("正在准备图片")
    response = await aiorequests.get(image_url, headers=headers)
    image = Image.open(BytesIO(await response.content))
    info = image.info
    print(f"frames:{image.n_frames}, mode:{image.mode}, info:{image.info}")

    if image.n_frames == 1:
        await bot.finish(ev, "并非GIF图片")
    if image.n_frames > 200:
        await bot.finish(ev, "GIF帧数太多了，懒得倒放[CQ:face,id=13]")

    turnAround = random.randint(0, 6)
    sequence = [f.transpose(turnAround).copy() if ifturn else f.copy()
                for f in ImageSequence.Iterator(image)]
    if len(sequence) > 30:
        await bot.send(ev, "ℹ正在翻转图片序列，请稍候")
    sequence.reverse()

    buf = BytesIO()
    sequence[0].save(buf, format='GIF', save_all=True,
                     append_images=sequence[1:], disposal=2,
                     quality=80, **info)
    base64_str = base64.b64encode(buf.getvalue()).decode()
    await bot.send(ev, ms.image('base64://' + base64_str))
