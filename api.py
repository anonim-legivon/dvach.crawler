import asyncio
import os
import re
from collections import Counter

import aiohttp
import async_timeout
import tqdm

BASE_URL = 'https://2ch.hk'
BOARD = input('Choose board: ')
MIN_REPLIES = 3  # value less then 3 have 99.9% chance to produce aiohttp.ClientPayloadError. Help me fix this pls :c
if not BOARD:
    BOARD = 'b'
HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}


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


loop = asyncio.get_event_loop()
threads = []
posts = []
loop.run_until_complete(get_all_threads(BOARD, threads))
print(f'Total {len(threads)} threads')

webm_threads = []

for thread in threads:
    for key, value in thread.items():
        if any(subs in value.lower() for subs in
               ['webm', 'шебм', 'цуиь', 'fap', 'фап', 'афз']):  # remove fap and etc for disable fap threads
            webm_threads.append(key)
print(f'Total {len(webm_threads)} webm threads')

loop.run_until_complete(
    asyncio.gather(
        *(get_thread(arg, posts) for arg in webm_threads)
    )
)

pwr = []

for post in posts:
    result = re.search(r'#(\d*?)\"', post['comment'])
    if result:
        pwr.append(result.group(1))

nums = []
c = Counter(pwr)

for i in c:
    if c[i] >= MIN_REPLIES:
        nums.append(i)
files = []

for each_p in posts:
    if str(each_p['num']) in nums:
        if each_p['files']:
            files.append(each_p['files'])

download_list = []

for e in files:
    for file in e:
        download_list.append(file)


async def download_file(url, name):
    with async_timeout.timeout(100):  # Optimal timeout. Less increase chance to TimeoutError
        async with aiohttp.ClientSession(loop=loop) as session:
            async with session.get(url) as resp:
                assert resp.status == 200
                filename = f"{os.curdir}{os.sep}downloads{os.sep}{name}"
                with open(filename, 'wb') as f_handle:
                    while True:
                        chunk = await resp.content.read(4096)  # Maybe less or high chunk size?
                        if not chunk:
                            break
                        f_handle.write(chunk)
                return await resp.release()


path = f'{os.curdir}{os.sep}downloads'

if not os.path.exists(path):
    os.makedirs(path)

download_list_wo_dupes = []

files_in_dir = [f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f))]

for each_file in download_list:
    if each_file['fullname'] not in files_in_dir:
        download_list_wo_dupes.append(each_file)

print(f'Found {len(download_list)} files. New files: {len(download_list_wo_dupes)}')


async def progress(task):
    for f in tqdm.tqdm(asyncio.as_completed(task), total=len(task)):
        await f


loop.run_until_complete(
    progress([download_file(BASE_URL + file['path'], file['fullname']) for file in download_list_wo_dupes]))
loop.close()
