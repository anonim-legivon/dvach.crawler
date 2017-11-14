import asyncio
import os
import re
from collections import defaultdict
from random import choice

import aiohttp
import async_timeout
import tqdm
from fake_useragent import UserAgent

# INIT
MIRRORS = ('2ch.hk', '2ch.pm', '2ch.re', '2ch.tf', '2ch.wf', '2ch.yt', '2-ch.so')  # 2ch mirrors
BASE_URL = 'https://{}'.format(choice(MIRRORS))
BOARD = 'b'
PATTERNS = ['webm', 'шебм', 'цуиь', 'fap', 'фап', 'афз', 'afg', ]  # Required substrings in OP post
ANTI_PATTERNS = ['black', 'рулет', ]  # Didn't required substrings in OP post
MIN_REPLIES = 2  # Minimum replies to match post
MAX_QUEUE_SIZE = 30  # Maximum download queues
CHUNK_SIZE = 1024 * 1024  # 1 MB. Use -1 (EOF) if you have good internet channel
ua = UserAgent()  # Pass cache=False if you don’t want cache database (increase init time)
HEADERS = {'user-agent': ua.random}


async def get_all_threads(board, threads):
    endpoint = '/threads.json'
    url = f'{BASE_URL}/{board}{endpoint}'
    print(f'Getting all threads from {board}')
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            data = await resp.json()
    threads.extend([{thread['num']: thread['comment']} for thread in data['threads']])


async def get_thread(thread_num, posts):
    endpoint = '/res/'
    url = f'{BASE_URL}/{BOARD}{endpoint}{thread_num}.json'
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            data = await resp.json()
    posts.extend(data['threads'][0]['posts'])


async def download_file(url, name, loop):
    with async_timeout.timeout(100):  # Optimal timeout. Less values increase chance to TimeoutError
        async with aiohttp.ClientSession(loop=loop) as session:
            async with session.get(url) as resp:
                assert resp.status == 200
                filename = f"{os.curdir}{os.sep}downloads{os.sep}{name}"
                with open(filename, 'wb') as f_handle:
                    while True:
                        chunk = await resp.content.read(
                            CHUNK_SIZE)  # Maybe less or high chunk size (-1 for read until EOF)?
                        if not chunk:
                            break
                        f_handle.write(chunk)
                return await resp.release()


async def produce(queue, file_list):
    for file in file_list:
        item = (BASE_URL + file['path'], file['fullname'])
        await queue.put(item)


async def consume(queue, loop, p_bar):
    while True:
        # wait for an item from the producer
        file = await queue.get()
        # process the item
        await download_file(file[0], file[1], loop)
        p_bar.update()
        # Notify the queue that the item has been processed
        queue.task_done()


async def run(n, file_list, loop):
    total = len(file_list)
    p_bar = tqdm.tqdm(total=total)
    queue = asyncio.Queue(maxsize=n)
    # schedule the consumer
    consumer = asyncio.ensure_future(consume(queue, loop, p_bar))
    # run the producer and wait for completion
    await produce(queue, file_list)
    # wait until the consumer has processed all items
    await queue.join()
    # the consumer is still awaiting for an item, cancel it
    consumer.cancel()


def main():
    loop = asyncio.get_event_loop()

    threads = []
    posts = []

    loop.run_until_complete(get_all_threads(BOARD, threads))

    print(f'Total {len(threads)} threads')

    matched_threads = []

    for thread in threads:
        for key, value in thread.items():
            if any(subs in value.lower() for subs in PATTERNS) and all(subs not in value.lower() for subs in
                                                                       ANTI_PATTERNS):
                matched_threads.append(key)
    print(f'Total {len(matched_threads)} webm threads')

    loop.run_until_complete(
        asyncio.gather(
            *(get_thread(arg, posts) for arg in matched_threads)
        )
    )

    posts = {post['num']: post for post in posts}
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
                pass

    path = f'{os.curdir}{os.sep}downloads'

    if not os.path.exists(path):
        os.makedirs(path)

    files_in_dir = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]
    download_list = []

    for each_file in file_list:
        if each_file['fullname'] not in files_in_dir:
            download_list.append(each_file)

    print(f'Found {len(file_list)} files. New files: {len(download_list)}')

    loop.run_until_complete(run(MAX_QUEUE_SIZE, download_list, loop))
    loop.close()


if __name__ == '__main__':
    main()
