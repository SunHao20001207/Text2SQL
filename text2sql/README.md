# Text2SQL
使用LangChain进行文本到SQL语句的转换，再利用LLM生成回复文本。

该代理由三个过程组成：
1. 根据用户查询意图和已知的数据库结构生成SQL查询语句。
2. 执行生成的SQL查询语句。
3. 将查询结果转换为自然语言，便于用户以对话形式与数据库交互。

## 示例图片
![示例图片](https://github.com/SunHao20001207/Text2SQL/blob/main/text2sql/example/%E7%A4%BA%E4%BE%8B.png?raw=true)

## 文件夹结构

```plaintext
📦 text2sql
├── 📁 chatbot                                          # Text-to-SQL 代码
│   ├── 📄 __init__.py                                  # 将目录设为 Python 包
│   ├── 📄 chatclass.py                                 # text2sql 代理类
│   └── 📄 prompts.py                                   # 系统提示词
│
├── 📁 example                                          # 使用代理示例
│
├── 📁 sakila_sql                                       # 数据库文件夹
│   └── 📁 datacsv                                      # 数据库中所有表的csv文件
│   └── 🖼️ erd.PNG                                      # 数据库文件结构图
│   └── 📄 sakila.sql                                   # 数据库文件
│
├── 📁 tools                                            # 工具文件夹
│   ├── 📄 __init__.py                                  # 将目录设为 Python 包
│   └── 📄 tools.py                                     # 工具（日志器）
│
├── ⚙️ .env                                             # .env 文件模板
├── 📄 chainlit.md                                      # chainlit的说明文档
├── 📄 README.md                                        # 项目主文档
├── 📄 requirements.txt                                 # 依赖项列表
├── 📄 text2sql_front.py                                # 前端脚本
配置
```

## 依赖项

1. **创建并激活虚拟环境**

    使用conda创建一个虚拟环境：

    ```bash
    conda create -n text2sql python=3.11
    ```

    激活虚拟环境：
     
     ```bash
    conda activate text2sql
    ```

2. **使用 pip 同步依赖项**：

    ```bash
    pip install -r requirements.txt
    ```
    
    此命令将在虚拟环境中安装 requirements.txt 文件中定义的依赖项。

## 环境变量

该项目需要一个 SQL 数据库（MySQL、PostGres、SQLServer）以及OpenAI的API Key. URI和API Key应写在.env文件中。

`URI = 'mysql+pymysql://user:password@localhost:3306/sakila'`

`OPENAI_API_KEY = 'sk-WrrN..................'`


## 安装和使用流程

1. 创建MySQL的sakila数据库。可以通过通过sql终端执行以下命令：
   ```bash
    mysql -u root -p 
    ```

    ```bash
    mysql -u root -p sakila < sakila_sql/sakila.sql
    ```

2. 通过以下命令启动 chainlit 前端：
    ```bash
    chainlit run front.py -w --port 8001
    ```
