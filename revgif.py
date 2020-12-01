from os import urandom
from PIL import Image, ImageSequence
import requests
import re
import os
from io import BytesIO

import nonebot
from hoshino import Service

sv = Service('revgif', help_="GIF倒放功能")

headers = {"User-Agent": "Mozilla/5.0 (Windows; U; Windows NT 5.1; zh-CN; rv:1.9.1.6) ",
           "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
           "Accept-Language": "zh-cn"
           }
fd = os.path.dirname(__file__)

@sv.on_keyword("倒放")
async def revgif(bot, ev):
    message_id = None
    # 情况1，用户对需要倒放的gif进行回复
    match = re.match(r"\[CQ:reply,id=(?P<id>.*)\]\[CQ:", str(ev.message))
    if match is not None:
        message_id = match.group("id")
        print(message_id)
        pre_message = await bot.get_msg(message_id=message_id)
        pre_raw_message = pre_message["message"]
        print(pre_message, "\nwwww",pre_raw_message)
        await match_revgif(bot, ev, custom=pre_raw_message)
    else:
        await match_revgif(bot, ev)


async def match_revgif(bot, ev, custom=None):
    if custom is not None:
        ev.message = str(custom)
    # 情况2，用户直接发送“倒放+GIF图片”
    match = re.match(r"(.*)\[CQ:image(.*?)url=(?P<url>.*)\]", str(ev.message))
    if match is not None:
        image_url = match.group("url")
        print(image_url)
        await do_revgif(bot, ev, image_url)
    else:
        print("CQ码内未找到图片信息")
        return


async def do_revgif(bot, ev, image_url):
    print("正在准备图片")
    response = requests.get(image_url, headers=headers)
    image = Image.open(BytesIO(response.content))

    sequence = []
    for f in ImageSequence.Iterator(image):
        sequence.append(f.copy())
    print(len(sequence))
    if len(sequence) == 1:
        print("并非GIF图片")
        return
    sequence.reverse()
    gif_path=os.path.join(fd,f"{ev.user_id}.gif")
    sequence[0].save(gif_path, save_all=True,
                     append_images=sequence[1:])
    
    if os.path.exists(gif_path):
        await bot.send(ev, f"[CQ:image,file=file:///{gif_path}]")
        os.remove(gif_path)
