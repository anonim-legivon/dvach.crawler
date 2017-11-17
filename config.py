BASE_URL = 'https://2ch.hk'  # 2ch url, if .hk didn't work use other, e.g. .pm
BOARDS = ['b', 'vg']  # Список борд на которых искать
PATTERNS = ['webm', 'шебм', 'цуиь', 'fap', 'фап', 'афз', 'afg', ]  # Required substrings in OP post
ALLOWED_EXT = ['webm', 'mp4', ]  # Разрешенные расширения файлов
ANTI_PATTERNS = ['black', 'рулет', ]  # Didn't required substrings in OP post
MIN_REPLIES = 2  # Minimum replies to match post
MAX_QUEUE_SIZE = 30  # Maximum download queues
CHUNK_SIZE = 1024 * 1024  # Погулил - >=1 МБ норм, на чанах нету огромных файлов.
TIMEOUT = 100  # You can increase this value if you have TimeoutError. Or if you're using proxy
PROXY = None # HTTP/HTTPS only, example: "http//asdasd:asdasd@127.0.0.1:8080"
             # pip install proxybroker
             # proxybroker find --types HTTP HTTPS --countries RU --strict -l 10