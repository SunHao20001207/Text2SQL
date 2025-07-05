# libreries

import warnings
warnings.filterwarnings('ignore')

import os                          
from dotenv import load_dotenv
from operator import itemgetter # 用于提取字典中的值
from sqlalchemy import create_engine, inspect # 连接数据库 + 获取表结构
from langchain import SQLDatabase # LangChain 的 SQL 数据库包装器
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder
from langchain.chains import create_sql_query_chain # SQL查询的链
from langchain_openai.chat_models import ChatOpenAI  
from langchain.schema import StrOutputParser
from langchain.schema.runnable import RunnableLambda, RunnablePassthrough
from langchain.memory import ConversationBufferWindowMemory
# 添加对话记忆 0.3.1 版后已移除，迁移到 from langchain_core.messages import trim_messages

from .prompts import sql_prompt_template, system_prompt_template, question_prompt_template
from tools import logger


_ = load_dotenv(override=True)

URI = os.getenv('URI')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
model = os.getenv('MODEL')


class Text2SQL:

    def __init__(self):

        logger.info('开始聊天') # 记录日志："开始聊天"

        # 获取数据库表名
        self.tables = inspect(create_engine(URI)).get_table_names()

        # 创建 LangChain 的 SQLDatabase 对象（用于执行 SQL）
        self.db = SQLDatabase.from_uri(URI, sample_rows_in_table_info=2, include_tables=self.tables)

        self.sql_query = None
        self.last_sql_query = None
        self.context = None

        # 记忆最近 4 轮对话
        self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)
    

    def create_sql_query(self, prompt: str) -> str:

        """
        用于创建 SQL 查询语句的方法，会更新 self.sql_query 属性。

        参数：
            prompt（str）：用户的查询请求。

        返回值：
            None（无返回值）
        """

        logger.info('正在生成查询...')

        input_model = ChatOpenAI(model=model, temperature=0)

        sql_prompt = PromptTemplate(template=sql_prompt_template)

        # k=None 返回所有可用的示例
        database_chain = create_sql_query_chain(input_model, self.db, prompt=sql_prompt, k=None)

        sql_query = database_chain.invoke({'question': prompt, 
                                           'last_query': self.last_sql_query, # 上一次查询（用于上下文）
                                           'table_names': self.tables})

        sql_query = sql_query.split('```sql')[1].replace('`', '')

        # 安全检查：禁止执行 DML 操作（如 INSERT, DELETE）
        DML = ['create', 'drop', 'delete', 'alter', 'insert', 'update']

        for clause in DML:
            if clause in sql_query.lower():
                self.sql_query = 'SELECT "充当一个助手，使用记忆功能"'
            else:
                self.sql_query = sql_query

        logger.info('查询生成成功！')
    

    def execute_and_check_query(self, prompt: str) -> None:

        """
        用于执行 SQL 查询的方法。

        参数：
            prompt（str）：用户的查询请求。

        返回值：
            None（无返回值），但会更新 contexto 属性。
        """

        logger.info('正在执行查询...')

        done = False
        counter = 0

        while not done:

            counter += 1

            # 最多重试 5 次
            if counter==5:
                logger.info('退出 SQL 执行')
                break

            #正常生成sql语句
            try:
                self.create_sql_query(prompt)
                logger.info(f'SQL 查询: {self.sql_query}')
                context = self.db.run(self.sql_query)


            # 如果是sql语句语法生成错误（没生成sql的正确语法语句），则重写一个提示词，重新交给create_sql_query链再次生成sql语句
            except Exception as e:
                logger.info(e)
                logger.info('无法获取结果，重新创建查询...')
                #context = ''
                self.create_sql_query(
                    f'''
                    原始需求: {prompt}
                    生成的错误SQL: {self.sql_query}
                    数据库返回的错误: {str(e)}
                    请修正这个SQL查询，确保语法正确且符合数据库结构
                    ''')
                context = self.db.run(self.sql_query)

            #因各种错误原因没有返回正确的context，则再次重写一个提示词，再次重新交给create_sql_query链生成sql语句
            if not context:
                logger.info('结果为空，正在重新创建查询...')
                self.create_sql_query(
                    f'''
                    这个提示 {prompt} 生成了查询 {self.sql_query}，但没有返回结果。
                    请重新设计并简化查询，使其能从数据库返回结果。
                    ''')
                context = self.db.run(self.sql_query) 
            
            else:
                done = True
        
        self.context = context

        logger.info('上下文生成成功')   # 经过这么多次的重试，生成的sql语句几乎不可能再有语法错误
    

    def chain_to_response(self) -> object:

        """
        用于创建 LangChain 链的方法。

        返回值：
            LangChain 链对象
        """

        #查询结果可能有很多条，这里的max_tokens设置为32768，确保能处理整个查询结果
        output_model = ChatOpenAI(model=model, streaming=True, max_retries=1, max_tokens=32768)

        final_prompt = ChatPromptTemplate.from_messages([('system', system_prompt_template),
                                                         
                                                         MessagesPlaceholder(variable_name='history'),
                                                         
                                                         ('human', question_prompt_template)])


        chain = (RunnablePassthrough.assign(history=RunnableLambda(self.memory.load_memory_variables) 
                                            | itemgetter('history'))) | final_prompt  | output_model | StrOutputParser()

        return chain
    

    def main(self, prompt: str):

        self.execute_and_check_query(prompt)  #流程：执行查询->创建sql查询->使用sql查询语句返回数据库查询结果->使用agent生成自然语言回复

        chain = self.chain_to_response()

        try:
            logger.info('正在生成回答...')
            response = ''

            # 流式返回回答（逐词生成）
            for chunk in chain.stream({
                'sql_query': self.sql_query,
                'context': self.context,
                'prompt': prompt
            }):
                # 流式返回
                yield(chunk)
                response += chunk

            # 保存对话到记忆
            self.memory.save_context({'question': prompt}, {'response': response})


        # 处理异常
        except Exception as e:
            try:
                logger.info(f'正在恢复内存...错误: {e}')
                #response = ''

                # 如果内存中有历史对话，重置记忆窗口，保存最后一组对话到内存
                if self.memory.load_memory_variables({})['history']:
                    last_messages = self.memory.load_memory_variables({})['history'][-2:]
                    self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)
                    self.memory.save_context({'question': last_messages[-2].content}, {'response': last_messages[-1].content})

                # 如果内存中没有历史对话，重新创建一个新的记忆窗口
                else:
                    self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)

                # 再次尝试生成响应并保存
                response = ''
                for chunk in chain.stream({'sql_query': self.sql_query, 
                                           'context': self.context,
                                           'prompt': prompt}):
                        
                    yield(chunk)
                    response += chunk
                self.memory.save_context({'question': prompt}, {'response': response})

            # 如果再次失败，返回默认的响应
            except Exception as e:
                logger.info(f'默认响应，上下文太大。错误： {e}')
                #response = ''
                # 完全重置记忆系统
                self.memory = ConversationBufferWindowMemory(k=4, return_messages=True)
                response = '上下文太广泛，请提出更具体的问题，以便我们回答您。'

                # 以流式方式返回错误信息
                for chunk in response:
                        
                    yield(chunk)
                    response += chunk
            # 保存这次失败的交互到记忆
            self.memory.save_context({'question': prompt}, {'response': response})

        self.last_sql_query = self.sql_query
        self.sql_query = None
        self.context = None
        logger.info('完成')
