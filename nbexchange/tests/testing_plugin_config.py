from traitlets.config import get_config

c = get_config()

c.Exchange.max_buffer_size = 200000000  # 200M
