import asyncio
import os
import logging
from collections import defaultdict
from random import choice
import re
import traceback
import aiohttp
import async_timeout
import tqdm
from fake_useragent import UserAgent

# TODO: Перенести в config.py
MIRRORS = ['2ch.hk', '2ch.pm', '2ch.re', '2ch.tf', '2ch.wf', '2ch.yt', '2-ch.so', ]  # 2ch mirrors
BASE_URL = 'https://{}'.format(choice(MIRRORS))
BOARDS = ['b', 'vg', 'pr']
PATTERNS = ['webm', 'шебм', 'цуиь', 'fap', 'фап', 'афз', 'afg', ]  # Required substrings in OP post
ANTI_PATTERNS = ['black', 'рулет', ]  # Didn't required substrings in OP post
MIN_REPLIES = 2  # Minimum replies to match post
MAX_QUEUE_SIZE = 30  # Maximum download queues
# TODO: Подобрать подходящий размер чанка. Сейчас 1 МБ.
CHUNK_SIZE = 1024 * 1024
TIMEOUT = 100  # You can increase this value if you have TimeoutError.


# TODO: Сделать опциональную возможность делать реквесты через proxy. В сессию передавать proxy=
async def get_async(url, *args):
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers={f'user-agent': UserAgent().random}) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data, args
            else:
                return None

async def get_all(boards):

    async def filter_threads(data): # Thread filter by PATTERNS and ANTI_PATTERNS lists
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
            for post_id in re.findall(r'>>>(\d+) ?', post['comment']):
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
        download_list = []

        for each_file in file_list:
            if each_file['fullname'] not in files_in_dir:
                download_list.append(each_file)
        print(f'Found {len(file_list)} files. New files: {len(download_list)}')
        return download_list


    async def get_posts(board, matched_threads):
        result = []
        endpoint = '/res/'
        urls = [f'{BASE_URL}/{board}{endpoint}{thread_num}.json' for thread_num in matched_threads]
        futures = [get_async(url) for url in urls]
        done, _ = await asyncio.wait(futures)
        for future in done:
            try:
                i = future.result()
                result.extend(i[0]['threads'][0]['posts'])
            except:
                print("Unexpected error: {}".format(traceback.format_exc()))            
        return result

    async def main_async(boards):
        result = []
        endpoint = '/threads.json'
        urls = [(f'{BASE_URL}/{board}{endpoint}', board) for board in boards]
        futures = [get_async(url[0], url[1]) for url in urls] # url[1] == board | pass board to exculde future parsing
        done, _ = await asyncio.wait(futures)
        for future in done:
            try:
                data, board = future.result()
                matched_threads = await filter_threads(data)
                print(f'Тредов {board[0]} подходит', len(matched_threads))

                posts = await get_posts(board[0], matched_threads)
                download_list = await filter_posts({post['num']: post for post in posts})
                result.extend(download_list)
                # result[board[0]].extend(matched_threads)
            except:
                print("Unexpected error: {}".format(traceback.format_exc()))
        return result

    download_list = await main_async(boards)
    await run(MAX_QUEUE_SIZE, download_list)
    
# TODO: Сделать опциональную возможность делать реквесты через proxy. В сессию передавать proxy=
async def download_file(url, name):
    with async_timeout.timeout(TIMEOUT):
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers={f'user-agent': UserAgent().random}) as resp:
                assert resp.status == 200
                filename = f"{os.curdir}{os.sep}downloads{os.sep}{name}"
                with open(filename, 'wb') as f_handle:
                    while True:
                        chunk = await resp.content.read(
                            CHUNK_SIZE)
                        if not chunk:
                            break
                        f_handle.write(chunk)
                return await resp.release()


async def produce(queue, file_list):
    for file in file_list:
        item = (BASE_URL + file['path'], file['fullname'])
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
    # TODO: По возможности упростить вакханалию ниже
    loop.run_until_complete(get_all(BOARDS))
    # loop.run_until_complete(run(MAX_QUEUE_SIZE, download_list, loop))
    loop.close()


if __name__ == '__main__':
    main()
