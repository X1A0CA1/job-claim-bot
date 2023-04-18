import pyromod
import re

from pyrogram import Client, filters, idle
from pyrogram.enums import ChatType, ParseMode
from pyrogram.types import BotCommand, ReplyKeyboardRemove, ReplyKeyboardMarkup
from pyrogram.raw.functions import Ping

from config import work_group, bot_name, api_id, api_hash, bot_token, super_admin
from callback_handler import *

admin_list = list(set(super_admin) | set(read_admin_file()))

bot = Client(
    bot_name,
    api_id=api_id,
    api_hash=api_hash,
    bot_token=bot_token
)

publish_template = "源片名：\n" \
                   "无种子视频 URL：\n" \
                   "中字所在平台："

stats_callback_regex = r"stats_get_published|stats_get_claimed|stats_get_TaskMaking|stats_get_this_month" \
                       r"|stats_get_last_month|stats_get_overview|stats_message_delete "
other_callback_regex = r"claim_task|task_scheduling|TaskMaking|task_finished|waive_task|delete_task|get_log" \
                       r"|confirm_delete_task|back_to_menu_task "


@bot.on_callback_query()
async def other_callback_handler(client, callback_query):
    if not await is_member_in_work_group(client, work_group, callback_query.from_user.id):
        return
    data = read_json_file()
    callback_query_data = format_callback_data(callback_query)
    if not callback_query_data:
        await client.answer_callback_query(callback_query.id, text="JSON 字符串出错", show_alert=True)
        return

    callback_type = callback_query_data['callback_type']
    task_id = str(callback_query_data['task_id'])
    user_id = callback_query_data['user_id']

    if callback_type in ["stats_get_published", "stats_get_claimed", "stats_get_TaskMaking"]:
        await stats_get_published_handler(client, callback_query, callback_type)

    elif callback_type == "stats_get_this_month":
        await client.answer_callback_query(callback_query.id, text="这里等后续写了", show_alert=True)

    elif callback_type == "stats_get_last_month":
        await client.answer_callback_query(callback_query.id, text="这里等后续写了", show_alert=True)

    elif callback_type == "stats_get_overview":
        await stats_get_overview_handler(client, callback_query, callback_type)

    elif callback_type == "stats_message_delete":
        await stats_message_delete(client, callback_query)

    elif callback_type == "claim_task":
        await claim_handler(client, callback_query, task_id)

    elif callback_type in ["task_scheduling", "TaskMaking", "task_finished"]:
        # 只有管理员和原始认领者才能改变进度
        if (user_id != int(data[task_id]['claimer_id'])) and (user_id not in admin_list):
            await client.answer_callback_query(callback_query.id, text="这不是你的认领，请勿点击。", show_alert=True)
        else:
            await task_update_progress_handler(client, callback_query, task_id, callback_type)

    elif callback_type == "waive_task":
        # 只有管理员和原始认领者才能改变认领状态
        if (user_id != int(data[task_id]['claimer_id'])) and (user_id not in admin_list):
            await client.answer_callback_query(callback_query.id, text="这不是你的认领，请勿点击。", show_alert=True)
        else:
            await waive_task_handler(client, callback_query, task_id)

    elif callback_type == "delete_task":
        # 这一步不需要权限检测
        await delete_handler(client, callback_query, task_id)

    elif callback_type == "get_log":
        # 这个也不写权限检测了，日志无所谓的，随便玩
        await get_log_handler(client, callback_query, task_id)

    elif callback_type == "confirm_delete_task":
        # 只有管理和原始发布者有权限删除
        if (user_id != int(data[task_id]['publisher_id'])) and (user_id not in admin_list):
            await client.answer_callback_query(callback_query.id, text="你好像没有删除权限", show_alert=True)
        else:
            await confirm_delete_handler(client, callback_query, task_id)

    elif callback_type == "back_to_menu_task":
        await back_to_menu_handler(client, callback_query, task_id)
    else:
        await client.answer_callback_query(callback_query.id, text="未知操作。", show_alert=True)


@bot.on_message(filters.command('publish'))
async def publish(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    chat_type = message.chat.type
    if (chat_type != ChatType.BOT) and (chat_type != ChatType.PRIVATE):
        message = await message.reply("请在与我的私聊中使用此命令。")
        await sleep_and_delete_message(10, message)
        return
    await message.reply("请在 5 分钟内填写任务并确认发送，否则将会超时。建议按照模板填写请求：")
    asking = await message.chat.ask(publish_template, timeout=300)
    task_id = get_task_id()
    data = {
        task_id: {
            "timestamp": int(time()),
            "task_details": asking.text,
            "status": "published",
            "publisher_id": asking.from_user.id,
            "claimer": None,
            "claimer_id": None,
            "claimer_fullname": None,
            "logs": None,
            "task_id": task_id
        }
    }

    task = f"任务序号：{task_id}\n" \
           f"发布时间：{timestamp_to_readable(data[task_id]['timestamp'])}\n\n" \
           f"{data[task_id]['task_details']}\n\n" \
           f"当前状态：{get_task_status(data[task_id]['status'])}\n" \
           f"认领者：{'暂无' if not data[task_id]['claimer'] else data[task_id]['claimer']}"

    confirmation = await message.chat.ask(
        task,
        reply_markup=ReplyKeyboardMarkup(
            [["确认", "取消"]],
            resize_keyboard=True
        ),
        timeout=300
    )
    if confirmation.text == "确认":
        task_message = await bot.send_message(
            work_group,
            task,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("删除此任务", callback_data=f'{{"type": "delete_task", "task_id": {task_id}}}'),
                    InlineKeyboardButton("认领", callback_data=f'{{"type": "claim_task", "task_id": {task_id}}}')
                ],
                [
                    InlineKeyboardButton("查看日志", callback_data=f'{{"type": "get_log", "task_id": {task_id}}}')
                ]
            ]),
            disable_web_page_preview=True
        )
        pin_message = await task_message.pin()
        data[task_id]["message_id"] = message.id
        data[task_id]["message_link"] = task_message.link
        write_json_file(data)
        await pin_message.delete()
        await bot.send_message(
            message.chat.id, f"确认，已成功推送到频道。\n"
                             f"[请点击这里查看]({task_message.link})",
            reply_markup=ReplyKeyboardRemove())

    elif confirmation.text == "取消":
        await bot.send_message(message.chat.id, "已取消，请重新开始。", reply_markup=ReplyKeyboardRemove())
        return
    else:
        await bot.send_message(message.chat.id, "未知命令，请重新开始。", reply_markup=ReplyKeyboardRemove())
        return


@bot.on_message(filters.command('stats'))
async def stats(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    stats_text = get_overview_text()
    await client.send_message(
        message.chat.id,
        stats_text,
        reply_markup=stats_reply_markup(),
        disable_web_page_preview=True
    )


@bot.on_message(filters.command('ping'))
async def ping(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    from datetime import datetime
    start = datetime.now()
    await bot.invoke(Ping(ping_id=0))
    end = datetime.now()
    ping_duration = (end - start).microseconds / 1000
    start = datetime.now()
    message = await message.reply("Poi~", disable_notification=True)
    end = datetime.now()
    msg_duration = (end - start).microseconds / 1000
    message = await message.edit(f"Pong! | 服务器延迟: {ping_duration}ms | 消息处理延迟: {msg_duration}ms")
    await sleep_and_delete_message(10, message)


@bot.on_message(filters.command('id'))
async def get_ids(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    text = f"本群群组 ID 为：`{message.chat.id}`\n发送消息的 ID 为：`{message.from_user.id}`"
    if message.reply_to_message:
        text += f"\n回复的人的 ID 为：`{message.reply_to_message.from_user.id}`"
    await client.send_message(message.chat.id, text)


@bot.on_message(filters.command('add_admin'))
async def add_admin(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    if message.from_user.id not in super_admin:
        message = await message.reply("只有超级管理员才可以使用这个命令")
        await sleep_and_delete_message(10, message)
        return
    global admin_list
    parameters = message.text.split(" ")[1:]
    if message.reply_to_message:
        admin_list.append(message.reply_to_message.from_user.id)
        write_admin_file(admin_list)
        message = await message.reply("已添加。")
        await sleep_and_delete_message(10, message)
    elif len(parameters) != 0:
        for parameter in parameters:
            if parameter.isdigit():
                admin_list.append(int(parameter))
        write_admin_file(admin_list)
        message = await message.reply("已添加。")
        await sleep_and_delete_message(10, message)
    else:
        message = await message.reply("参数错误。")
        await sleep_and_delete_message(10, message)


@bot.on_message(filters.command('del_admin'))
async def del_admin(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    if message.from_user.id not in super_admin:
        message = await message.reply("只有超级管理员才可以使用这个命令")
        await sleep_and_delete_message(10, message)
        return
    global admin_list
    parameters = message.text.split(" ")[1:]
    if message.reply_to_message:
        try:
            admin_list.remove(message.reply_to_message.from_user.id)
            write_admin_file(admin_list)
            message = await message.reply("已删除")
            await sleep_and_delete_message(10, message)
        except ValueError:
            message = await message.reply("此人原先并不是管理")
            await sleep_and_delete_message(10, message)
            return
    elif len(parameters) != 0:
        for parameter in parameters:
            if parameter.isdigit():
                try:
                    admin_list.remove(int(parameter))
                except ValueError:
                    pass
        write_admin_file(admin_list)
        message = await message.reply("已删除")
        await sleep_and_delete_message(10, message)
    else:
        message = await message.reply("参数错误")
        await sleep_and_delete_message(10, message)


@bot.on_message(filters.command('help'))
async def help_message(client, message):
    if not await is_member_in_work_group(client, work_group, message.from_user.id):
        return
    await message.delete()
    await message.reply(
        "**Powered By XiaoCai b0.1**\n\n"
        "/publish 用来发布任务，只可以在私聊 bot 的时候使用\n"
        "/stats 查看统计信息\n\n"
        "/add_admin 用来添加能够管理任务的管理员，需要对着一条消息回复，被回复者会成为管理员。"
        "或者直接发送带有用户 ID 的消息也可以添加管理员，如： `/add_admin 634873450`\n"
        "/del_admin 删除一位管理员，与 /add_admin 用法相同\n\n"
        "/id 查看发送者和被回复消息的人的数字 ID 与本群组的 ID\n"
        "/ping 用来检测机器人还是否在线\n"
        "/help 查看本消息"
    )


def startBot():
    bot.start()
    bot.set_parse_mode(ParseMode.DEFAULT)
    bot.set_bot_commands([
        BotCommand("publish", "发布任务"),
        BotCommand("stats", "查看统计信息"),
        BotCommand("add_admin", "添加一位机器人管理员"),
        BotCommand("del_admin", "删除一位机器人管理员"),
        BotCommand("id", "查看当前群组信息"),
        BotCommand("ping", "检查机器人是否存活"),
        BotCommand("help", "查看基础的帮助")
    ])
    idle()
    bot.stop()


if __name__ == "__main__":
    initial_checks()
    startBot()
