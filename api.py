import asyncio
import aiofiles
import aiohttp

base_url = 'https://2ch.hk/'

HEADERS = {
    'user-agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/45.0.2454.101 Safari/537.36'),
}


async def get_all_threads(board, threads):
    endpoint = '/threads.json'
    url = f'{board}/{endpoint}'
    print(f'Getting all threads from /{board}')
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS) as resp:
            data = await resp.json
    threads.extend([(thread['num']) for thread in threads['threads']])

async def get_thread(thread_num):
    pass

loop = asyncio.get_event_loop()
board = 'b'
threads = []
loop.run_until_complete(get_all_threads(board, threads))

'''
loop.run_until_complete(
    asyncio.gather(
        *(get_thread(*args) for args in threads)
    )
)
'''