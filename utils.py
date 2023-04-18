import json
import os
import datetime
from asyncio import sleep

from config import admin_data_path, data_path, data_folder


def format_callback_data(callback_query):
    try:
        callback_query_data = json.loads(callback_query.data)
        if type(callback_query_data) != dict:
            raise "JSONDecodeError"
    except "JSONDecodeError":
        return False
    callback_type = callback_query_data['type']
    try:
        task_id = str(callback_query_data['task_id'])
    except KeyError:
        task_id = -1
    user_id = callback_query.from_user.id
    return {
        "callback_type": callback_type,
        "task_id": task_id,
        "user_id": user_id
    }


def convert_to_text(datas: list, callback_type):
    text = ""
    for data in datas[callback_type]:
        task_id = data['task_id']
        text += f"任务序号：{data['task_id']}\n" \
                f"发布时间：{timestamp_to_readable(data['timestamp'])}\n\n" \
                f"{data['task_details']}\n\n" \
                f"当前状态：{get_task_status(data['status'])}\n" \
                f"认领者：{'暂无' if not data['claimer'] else data['claimer']}\n" \
                f"[直达链接]({data['message_link']})\n\n\n"
    return text


def sort_by_status(data):
    published = []
    claimed = []
    task_scheduling = []
    TaskMaking = []

    for key in data:
        item = data[key]
        status = item["status"]
        if status == "published":
            published.append(item)
        elif status == "claimed":
            claimed.append(item)
        elif status == "task_scheduling":
            task_scheduling.append(item)
        elif status == "TaskMaking":
            TaskMaking.append(item)

    return {
        "published": published,
        "claimed": claimed,
        "task_scheduling": task_scheduling,
        "TaskMaking": TaskMaking
    }


def get_overview_text():
    data = read_json_file()
    stats_overview = stats_count(data)
    stats_text = f"当前数据库内共有 **{stats_overview['all']}** 条数据。其中：\n" \
                 f"    **待认领：** {stats_overview['published']}\n" \
                 f"    **已认领：** {stats_overview['claimed']}\n" \
                 f"    **排期中：** {stats_overview['task_scheduling']}\n" \
                 f"    **制作中：** {stats_overview['TaskMaking']}\n" \
                 f"    **已完成：** {stats_overview['task_finished']}"

    if stats_overview['top_claimer']['id'] != 0:
        top_user_id = stats_overview['top_claimer']['id']
        top_user_finished = stats_overview['top_claimer']['finished']
        stats_text += f"\n\n历史最多完成数 {top_user_finished}, 由 [此大佬保持](tg://user?id={top_user_id})"
    return stats_text


def stats_count(data) -> dict:
    task_finished_counts = {}
    status_counts = {
        "all": len(data),
        "published": 0,
        "claimed": 0,
        "task_scheduling": 0,
        "TaskMaking": 0,
        "task_finished": 0,
        "top_claimer": {
            "id": 0,
            "finished": 0
        }
    }
    if len(data) == 0:
        return status_counts
    else:
        # 数出各个状态的人数
        for task in data:
            status = data[task]['status']
            if status in status_counts:
                status_counts[status] += 1
        # 统计所有人的完成数
        for key, value in data.items():
            if value['status'] == 'task_finished':
                claimer_id = value['claimer_id']
                if claimer_id in task_finished_counts:
                    task_finished_counts[claimer_id] += 1
                else:
                    task_finished_counts[claimer_id] = 1
        # 得到完成数最高值
        max_count = 0
        max_claimer_id = 0
        if task_finished_counts:
            for claimer_id, count in task_finished_counts.items():
                if count > max_count:
                    max_count = count
                    max_claimer_id = claimer_id
        # 加入到结果中
        status_counts['top_claimer']['id'] = max_claimer_id
        status_counts['top_claimer']['finished'] = max_count
        return status_counts


def get_task_status(task_status: str) -> str:
    if task_status == "published":
        return "待认领"
    elif task_status == "claimed":
        return "已认领"
    elif task_status == "task_scheduling":
        return "排期中"
    elif task_status == "TaskMaking":
        return "制作中"
    elif task_status == "task_finished":
        return "已完成"
    elif task_status == "deleted":
        return "已删除"
    else:
        return "未知"


def contains_only_special_whitespace(string) -> bool:
    chars = "\u3164\u2060\ufe0f\u0020\u2063\u000a"
    return all(char in chars for char in string)


def write_admin_file(input_data: list):
    with open(admin_data_path, 'w') as f:
        json.dump(input_data, f, indent=4)


def read_admin_file() -> list:
    with open(admin_data_path, 'r') as f:
        data = json.load(f)
    return data


def write_json_file(input_data: dict):
    source_data = read_json_file()
    merged_data = {**source_data, **input_data}
    data = json.dumps(merged_data)
    with open(data_path, 'w') as f:
        json.dump(json.loads(data), f, indent=4)


def read_json_file() -> dict:
    with open(data_path, 'r') as f:
        data = json.load(f)
    return data


def timestamp_to_readable(timestamp: float) -> str:
    time_format = '%Y-%m-%d %H:%M:%S'
    dt_object = datetime.datetime.fromtimestamp(timestamp)
    readable_time = dt_object.strftime(time_format)
    return readable_time


def readable_to_timestamp(readable_time: str) -> int:
    time_format = '%Y-%m-%d %H:%M:%S'
    dt_object = datetime.datetime.strptime(readable_time, time_format)
    timestamp = dt_object.timestamp()
    return int(timestamp)


def get_task_id() -> int:
    tasks = read_json_file()
    try:
        max_index = max(int(i) for i in tasks.keys())
        return int(max_index) + 1
    except ValueError:
        return len(tasks) + 1


def initial_checks():
    if not os.path.exists(data_folder):
        os.makedirs(data_folder, exist_ok=True)
    if not os.path.exists(f"{data_path}"):
        with open(data_path, "w") as f:
            f.write('{}')
    if not os.path.exists(f"{admin_data_path}"):
        with open(admin_data_path, "w") as f:
            f.write('[]')


async def is_member_in_work_group(bot, chat_id, user_id):
    if not chat_id:
        return True
    async for m in bot.get_chat_members(chat_id):
        if m.user.id == user_id:
            return True
    return False


async def get_user_fullname(message):
    full_name = message.from_user.first_name
    full_name += f" {message.from_user.last_name}" if message.from_user.last_name else ""
    full_name = "空白字符组员" if contains_only_special_whitespace(full_name) else full_name
    return full_name


async def get_task_info(data, task_id):
    task = f"任务序号：{task_id}\n" \
           f"发布时间：{timestamp_to_readable(data[task_id]['timestamp'])}\n\n" \
           f"{data[task_id]['task_details']}\n\n" \
           f"当前状态：{get_task_status(data[task_id]['status'])}\n" \
           f"认领者：{'暂无' if not data[task_id]['claimer'] else data[task_id]['claimer']}"
    return task


async def sleep_and_delete_message(sleep_time, message):
    await sleep(int(sleep_time))
    try:
        await message.delete()
    except:
        pass
