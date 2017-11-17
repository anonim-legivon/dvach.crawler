import asyncio
import os
import re
import traceback  # TODO: Избавиться от этого
# import logging # TODO: Следует сделать логгирование
from collections import defaultdict

import aiohttp
import async_timeout
import tqdm
from fake_useragent import UserAgent

from config import *


# TODOs
# TODO: Может стоит грузить OP посты в отдельную папку и вообще сделать разные папки для картинок, gif и видео

# TODO: Сделать опциональную возможность делать реквесты через proxy. В сессию передавать параметр proxy='url'
async def get_async(url, *args):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={'user-agent': UserAgent().random}) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data, args
            else:
                return None


async def get_all(boards):
    async def filter_threads(data):  # Thread filter by PATTERNS and ANTI_PATTERNS lists
        matched_threads = []
        for t in [(thread['num'], thread['comment']) for thread in data['threads']]:
            if any(subs in t[1].lower() for subs in PATTERNS) and all(subs not in t[1].lower() for subs in
                                                                      ANTI_PATTERNS):
                matched_threads.append(t[0])
        return matched_threads

    async def filter_posts(posts):
        post_replies = defaultdict(int)
        for post in posts.values():
            replied = []
            for post_id in re.findall(r'>>>(\d+)', post['comment']):
                if post_id not in replied:
                    post_replies[int(post_id)] += 1
                    replied.append(post_id)

        file_list = []

        for post_id, reply_count in post_replies.items():
            if reply_count >= MIN_REPLIES:
                try:
                    file_list.extend(posts[post_id]['files'])
                except KeyError:
                    pass  # Ошибка возникает, если находится пост с реплаем в другой тред (DT), он нам не нужен.

        path = f'{os.curdir}{os.sep}downloads'

        if not os.path.exists(path):
            os.makedirs(path)

        files_in_dir = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
        filtered_download_list = []

        for each_file in file_list:
            if each_file['fullname'].split('.')[0] == '':
                each_file['fullname'] = each_file['name']
            n_condition = each_file['fullname'] not in files_in_dir  # TODO: Фильтр пустых имен. Проверь тут.
            f_ext = each_file['fullname'].split('.')[-1]  # Фильтр по расширениям
            ext_condition = f_ext in ALLOWED_EXT
            if n_condition and ext_condition:
                filtered_download_list.append(each_file)

        print(f'Найдено {len(file_list)} файлов. Новых: {len(filtered_download_list)}.')
        return filtered_download_list

    async def get_posts(board, matched_threads):
        result = []
        endpoint = '/res/'
        urls = [f'{BASE_URL}/{board}{endpoint}{thread_num}.json' for thread_num in matched_threads]
        futures = [get_async(url) for url in urls]
        done, _ = await asyncio.wait(futures)
        for future in done:
            try:
                f_res = future.result()
                result.extend(f_res[0]['threads'][0]['posts'])
            except:  # TODO: Тут все таки лучше явно указать тип отлавливаемых ошибок, надо тестировать
                print("Unexpected error: {}".format(traceback.format_exc()))
        return result

    async def main_async(boards_list):
        result = []
        endpoint = '/threads.json'
        urls = [(f'{BASE_URL}/{board}{endpoint}', board) for board in boards_list]
        futures = [get_async(url[0], url[1]) for url in urls]  # url[1] == board | pass board to exclude future parsing
        done, _ = await asyncio.wait(futures)
        for future in done:
            data, board = future.result()
            matched_threads = await filter_threads(data)
            print(f'Подходящих тредов в {board[0]}: {len(matched_threads)}.')
            if not len(matched_threads):
                continue
            posts = await get_posts(board[0], matched_threads)
            download_nums_list = await filter_posts({post['num']: post for post in posts})
            result.extend(download_nums_list)
        return result

    download_list = await main_async(boards)
    await run(MAX_QUEUE_SIZE, download_list)


# TODO: Сделать опциональную возможность загружать файлы через proxy. В сессию передавать параметр proxy='url'
async def download_file(url, name):
    with async_timeout.timeout(TIMEOUT):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={'user-agent': UserAgent().random}) as resp:
                assert resp.status == 200
                filename = f"{os.curdir}{os.sep}downloads{os.sep}{name}"
                with open(filename, 'wb') as f_handle:
                    while True:
                        chunk = await resp.content.read(CHUNK_SIZE)
                        if not chunk:
                            break
                        f_handle.write(chunk)
                return await resp.release()


async def produce(queue, file_list):
    for file in file_list:
        item = (BASE_URL + file['path'], file['fullname'])  # TODO: Фильтр пустых имен. И тут проверь.
        await queue.put(item)


async def consume(queue, p_bar):
    while True:
        # wait for an item from the producer
        file = await queue.get()
        # process the item
        await download_file(file[0], file[1])
        p_bar.update()
        # Notify the queue that the item has been processed
        queue.task_done()


async def run(n, file_list):
    total = len(file_list)
    print(f'\nВсего найдено новых файлов: {total}.\n')
    p_bar = tqdm.tqdm(total=total)
    queue = asyncio.Queue(maxsize=n)
    # schedule the consumer
    consumer = asyncio.ensure_future(consume(queue, p_bar))
    # run the producer and wait for completion
    await produce(queue, file_list)
    # wait until the consumer has processed all items
    await queue.join()
    # the consumer is still awaiting for an item, cancel it
    consumer.cancel()


def main():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(get_all(BOARDS))
    loop.close()


if __name__ == '__main__':
    main()
