import logging as log

class Logger:
    def __init__(self, name: str) -> None:
        """
        创建一个用于反馈的日志记录器。
        :param name: 字符串类型。日志记录器的名称。
        """

        # 创建一个日志记录器（logger），并设置它的名字（用于区分不同的logger）
        self.logger = log.getLogger(name)
        # 设置日志级别为DEBUG（最低级别，会记录所有级别的日志）
        self.logger.setLevel(log.DEBUG)

        # 创建一个控制台处理器（StreamHandler），用于在终端输出日志
        ch = log.StreamHandler()

        # 设置控制台处理器的日志级别（也是DEBUG，即所有日志都会输出）
        ch.setLevel(log.DEBUG)

        # 定义日志的格式
        formatter = log.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # 把格式应用到控制台处理器
        ch.setFormatter(formatter)

        # 把控制台处理器添加到logger，这样日志就能输出到终端了
        self.logger.addHandler(ch)