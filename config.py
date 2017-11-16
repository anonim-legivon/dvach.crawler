MIRROR = '2ch.hk'  # 2ch mirror, if .hk didn't work use other, e.g. .pm
BASE_URL = f'https://{MIRROR}'
BOARDS = ['b', 'vg', 'pr']  # Список борд на которых искать
PATTERNS = ['webm', 'шебм', 'цуиь', 'fap', 'фап', 'афз', 'afg', ]  # Required substrings in OP post
ANTI_PATTERNS = ['black', 'рулет', ]  # Didn't required substrings in OP post
MIN_REPLIES = 2  # Minimum replies to match post
MAX_QUEUE_SIZE = 30  # Maximum download queues
# TODO: Подобрать подходящий размер чанка. Сейчас 1 МБ.
CHUNK_SIZE = 1024 * 1024
TIMEOUT = 100  # You can increase this value if you have TimeoutError.
