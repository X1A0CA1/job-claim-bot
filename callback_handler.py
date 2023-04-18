from time import time

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from utils import *


def stats_reply_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("待认领", callback_data=f'{{"type": "stats_get_published"}}'),
            InlineKeyboardButton("排期中", callback_data=f'{{"type": "stats_get_claimed"}}'),
            InlineKeyboardButton("制作中", callback_data=f'{{"type": "stats_get_TaskMaking"}}')
        ],
        [
            InlineKeyboardButton("本月完成", callback_data=f'{{"type": "stats_get_this_month"}}'),
            InlineKeyboardButton("上月完成", callback_data=f'{{"type": "stats_get_last_month"}}')
        ],
        [
            InlineKeyboardButton("查看目前总览", callback_data=f'{{"type": "stats_get_overview"}}'),
        ],
        [
            InlineKeyboardButton("删除此条消息", callback_data=f'{{"type": "stats_message_delete"}}'),
        ]
    ])


async def stats_message_delete(client, callback_query):
    await callback_query.message.delete()
    await client.answer_callback_query(callback_query.id, text="已删除")


async def edit_reply_markup(task, task_id, callback_query):
    await callback_query.message.edit(
        task,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("排期中", callback_data=f'{{"type": "task_scheduling", "task_id": {task_id}}}'),
                InlineKeyboardButton("制作中", callback_data=f'{{"type": "TaskMaking", "task_id": {task_id}}}'),
                InlineKeyboardButton("已完成", callback_data=f'{{"type": "task_finished", "task_id": {task_id}}}'),
            ],
            [
                InlineKeyboardButton("取消认领", callback_data=f'{{"type": "waive_task", "task_id": {task_id}}}'),
                InlineKeyboardButton("删除任务", callback_data=f'{{"type": "delete_task", "task_id": {task_id}}}')
            ],
            [
                InlineKeyboardButton("查看日志", callback_data=f'{{"type": "get_log", "task_id": {task_id}}}')
            ]]),
        disable_web_page_preview=True
    )


async def stats_get_overview_handler(client, callback_query, callback_type):
    stats_text = get_overview_text()
    await callback_query.message.edit(
        stats_text,
        reply_markup=stats_reply_markup(),
        disable_web_page_preview=True
    )
    await client.answer_callback_query(callback_query.id, text="已更新总览")


async def stats_get_published_handler(client, callback_query, callback_type):
    data = read_json_file()
    callback_type = callback_type.split("_")[-1]
    published_tasks = sort_by_status(data)[callback_type]
    if len(published_tasks) == 0:
        text = "**暂无任务详情**"
    else:
        text = "**当前任务详情\n\n**"

    text += convert_to_text(
        sort_by_status(read_json_file()),
        callback_type
    )

    await callback_query.message.edit(
        text,
        reply_markup=stats_reply_markup(),
        disable_web_page_preview=True
    )
    await client.answer_callback_query(callback_query.id, text="已更新任务详情")


async def claim_handler(client, callback_query, task_id):
    full_name = await get_user_fullname(callback_query)
    data = read_json_file()
    data[task_id]["claimer_id"] = callback_query.from_user.id
    data[task_id]["claimer_fullname"] = full_name
    data[task_id]["claimer"] = f"[{full_name}](tg://user?id={callback_query.from_user.id})"
    data[task_id]["status"] = "claimed"
    log_info = f"{timestamp_to_readable(int(time()))} " \
               f"已被 [{full_name}](tg://user?id={callback_query.from_user.id}) 认领"
    data[task_id]['logs'] = f"{data[task_id]['logs'] if data[task_id]['logs'] else ''} {log_info}\n"

    task = await get_task_info(data, task_id)
    await edit_reply_markup(task, task_id, callback_query)

    await client.answer_callback_query(callback_query.id, text="认领成功")
    write_json_file(data)


async def delete_handler(client, callback_query, task_id):
    await client.answer_callback_query(callback_query.id, text="如果你确定的话，请再次点击删除。", show_alert=True)
    await callback_query.message.edit_reply_markup(InlineKeyboardMarkup([
        [
            InlineKeyboardButton("最后警告，删除请点这里",
                                 callback_data=f'{{"type": "confirm_delete_task", "task_id": {task_id}}}')
        ],
        [
            InlineKeyboardButton("取消", callback_data=f'{{"type": "back_to_menu_task", "task_id": {task_id}}}')
        ]
    ]))


async def confirm_delete_handler(client, callback_query, task_id):
    full_name = await get_user_fullname(callback_query)
    data = read_json_file()
    data[task_id]["status"] = "deleted"
    log_info = f"{timestamp_to_readable(int(time()))} 已被 [{full_name}](tg://user?id={callback_query.from_user.id}) 删除"
    data[task_id]['logs'] = f"{data[task_id]['logs'] if data[task_id]['logs'] else ''} {log_info}\n"
    await client.answer_callback_query(callback_query.id, text="已删除")
    await callback_query.message.delete()
    write_json_file(data)


async def back_to_menu_handler(client, callback_query, task_id):
    data = read_json_file()
    task = await get_task_info(data, task_id)
    if data[task_id]['status'] == "published":
        await callback_query.message.edit(
            task,
            reply_markup=InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("删除此任务", callback_data=f'{{"type": "delete_task", "task_id": {task_id}}}'),
                    InlineKeyboardButton("认领", callback_data=f'{{"type": "claim_task", "task_id": {task_id}}}')
                ],
                [
                    InlineKeyboardButton("查看日志", callback_data=f'{{"type": "get_log", "task_id": {task_id}}}')
                ]]),
            disable_web_page_preview=True
        )
    else:
        await edit_reply_markup(task, task_id, callback_query)
    await client.answer_callback_query(callback_query.id, text="已取消操作")


async def waive_task_handler(client, callback_query, task_id):
    full_name = await get_user_fullname(callback_query)
    data = read_json_file()
    data[task_id]["claimer"] = None
    data[task_id]["claimer_id"] = None
    data[task_id]["claimer_fullname"] = None
    data[task_id]["status"] = "published"
    log_info = f"{timestamp_to_readable(int(time()))} " \
               f"已被 [{full_name}](tg://user?id={callback_query.from_user.id}) 取消认领"
    data[task_id]['logs'] = f"{data[task_id]['logs'] if data[task_id]['logs'] else ''} {log_info}\n"

    task = await get_task_info(data, task_id)

    await callback_query.message.edit(
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
    await client.answer_callback_query(callback_query.id, text="已取消认领")
    write_json_file(data)


async def task_update_progress_handler(client, callback_query, task_id, callback_type):
    full_name = await get_user_fullname(callback_query)
    data = read_json_file()
    data[task_id]["status"] = callback_type
    task_status = get_task_status(callback_type)
    log_info = f"{timestamp_to_readable(int(time()))} " \
               f"已被 [{full_name}](tg://user?id={callback_query.from_user.id}) 标记为 {task_status}"
    data[task_id]['logs'] = f"{data[task_id]['logs'] if data[task_id]['logs'] else ''} {log_info}\n"

    task = await get_task_info(data, task_id)
    await edit_reply_markup(task, task_id, callback_query)

    await client.answer_callback_query(callback_query.id, text="已更新状态")
    write_json_file(data)

    if callback_type == "task_finished":
        await client.send_message(
            int(data[task_id]['publisher_id']),
            f"您所发布的任务：\n\n{data[task_id]['task_details']}\n\n已经被 {data[task_id]['claimer']} 标记完成了。"
            f"[请点击这里查看]({callback_query.message.link})",
            disable_web_page_preview=True
        )
        await callback_query.message.unpin()


async def get_log_handler(client, callback_query, task_id):
    data = read_json_file()
    task = await get_task_info(data, task_id)
    task += f"\n\n **日志信息：**\n{data[task_id]['logs']}"
    await callback_query.message.edit(
        task,
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("返回", callback_data=f'{{"type": "back_to_menu_task", "task_id": {task_id}}}')
            ]]),
        disable_web_page_preview=True
    )
    await client.answer_callback_query(callback_query.id, text="日志已打印")
