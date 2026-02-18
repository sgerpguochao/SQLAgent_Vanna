"""
真正的Multi-Agent系统 - 基于LangChain 1.0
使用LangChain 1.0新版Agent API实现多Agent协作工作流
"""
import logging
logger = logging.getLogger(__name__)
import os
from typing import Dict, Any, Optional, List, TypedDict, Annotated
import pandas as pd
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.tools import StructuredTool
from langchain.agents import create_agent
import operator
from .utils import pretty_print


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: Annotated[List[BaseMessage], operator.add]
    user_query: str
    selected_datasets: List[str]  # 选中的数据集
    dataset_schemas: Dict[str, Dict]  # 数据集schema信息
    generated_code: str  # 生成的代码
    execution_result: Any  # 执行结果
    final_answer: str  # 最终答案
    error: Optional[str]  # 错误信息


class SchemaAgent:
    """Schema分析Agent - 只读取CSV前几行获取结构信息"""
    
    def __init__(self, data_directory: str, sample_rows: int = 3):
        self.data_directory = data_directory
        self.sample_rows = sample_rows
        self._csv_files_cache = None
    
    def get_available_datasets(self) -> List[str]:
        """获取所有可用的CSV文件名"""
        if self._csv_files_cache is None:
            import glob
            csv_files = glob.glob(os.path.join(self.data_directory, "*.csv"))
            self._csv_files_cache = [os.path.splitext(os.path.basename(f))[0] for f in csv_files]
        return self._csv_files_cache
    
    def analyze_schema(self, dataset_name: str) -> Dict[str, Any]:
        """
        分析单个数据集的schema（只读取前几行）
        
        Returns:
            schema信息字典，包含列名、类型、样本数据
        """
        try:
            csv_path = os.path.join(self.data_directory, f"{dataset_name}.csv")
            
            # 只读取前几行来分析结构
            df_sample = pd.read_csv(csv_path, nrows=self.sample_rows, encoding='utf-8')
            
            # 获取完整行数（只读取文件统计，不加载全部数据）
            row_count = sum(1 for _ in open(csv_path, encoding='utf-8')) - 1  # 减去表头
            
            schema = {
                "name": dataset_name,
                "row_count": row_count,
                "columns": df_sample.columns.tolist(),
                "dtypes": {col: str(dtype) for col, dtype in df_sample.dtypes.items()},
                "sample_data": df_sample.to_dict('records')
            }
            
            return schema
        except Exception as e:
            return {"error": f"分析schema失败: {str(e)}"}


class RouterAgent:
    """路由Agent - 理解用户意图，选择相关数据集"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def route_query(self, user_query: str, available_datasets: List[str]) -> List[str]:
        """
        根据用户查询选择相关的数据集
        
        Returns:
            相关数据集名称列表
        """
        prompt = f"""分析用户查询，从可用数据集中选择相关的数据集。

可用数据集: {', '.join(available_datasets)}

用户查询: {user_query}

请只返回相关数据集的名称，用逗号分隔。如果需要多个数据集，就返回多个。
格式要求：数据集名1,数据集名2

只返回数据集名称，不要其他解释："""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # 解析返回的数据集名称
        selected = [ds.strip() for ds in response.content.split(',')]
        
        # 验证数据集是否存在
        valid_datasets = [ds for ds in selected if ds in available_datasets]
        
        # 如果没有匹配到，返回所有数据集（保险起见）
        if not valid_datasets:
            return available_datasets
        
        return valid_datasets


class CodeGeneratorAgent:
    """代码生成Agent - 根据schema生成pandas查询代码"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def generate_code(
        self,
        user_query: str,
        schemas: Dict[str, Dict]
    ) -> str:
        """
        根据用户查询和数据集schema生成pandas代码
        
        Returns:
            可执行的pandas代码字符串
        """
        # 构建schema描述
        schema_desc = []
        for name, schema in schemas.items():
            if 'error' in schema:
                continue
            
            desc = f"""
数据集: {name}
行数: {schema['row_count']}
列: {', '.join(schema['columns'])}
数据类型: {schema['dtypes']}
样本数据:
{pd.DataFrame(schema['sample_data']).to_string()}
"""
            schema_desc.append(desc)
        
        schema_text = "\n".join(schema_desc)
        
        prompt = f"""你是pandas代码生成专家。根据用户查询和数据集schema，生成可执行的pandas代码。

数据集信息:
{schema_text}

用户查询: {user_query}

重要规则:
1. 数据集已经加载为DataFrame，变量名为数据集的名称
2. 只生成纯Python代码，不要markdown代码块标记
3. 将最终结果赋值给变量 'result'
4. 如果需要多个数据集关联，使用pd.merge()
5. 代码要简洁高效
6. 列名使用schema中提供的准确名称（区分大小写）
7. 使用schema中显示的实际列名和数据类型

代码示例格式:
- 单表筛选: result = 数据集名[数据集名['列名'] == 值]
- 聚合计算: result = 数据集名.groupby('列名')['目标列'].聚合函数()
- 多表关联: merged = pd.merge(数据集1, 数据集2, on='关联列'); result = merged[条件]

现在请生成代码（只返回代码，不要解释）:"""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        
        # 清理代码（移除可能的markdown标记）
        code = response.content.strip()
        code = code.replace('```python', '').replace('```', '').strip()
        
        return code


class CodeExecutorAgent:
    """代码执行Agent - 安全执行生成的代码"""
    
    def __init__(self, data_directory: str):
        self.data_directory = data_directory
        self._dataframe_cache = {}
    
    def _load_dataframe(self, dataset_name: str) -> pd.DataFrame:
        """延迟加载DataFrame（只在需要时加载）"""
        if dataset_name not in self._dataframe_cache:
            csv_path = os.path.join(self.data_directory, f"{dataset_name}.csv")
            self._dataframe_cache[dataset_name] = pd.read_csv(csv_path, encoding='utf-8')
        return self._dataframe_cache[dataset_name]
    
    def execute_code(
        self,
        code: str,
        required_datasets: List[str]
    ) -> Dict[str, Any]:
        """
        执行pandas代码
        
        Returns:
            执行结果字典
        """
        try:
            # 准备执行环境（只加载需要的数据集）
            local_vars = {'pd': pd}
            
            for dataset_name in required_datasets:
                df = self._load_dataframe(dataset_name)
                local_vars[dataset_name] = df
            
            # 执行代码
            exec(code, {"__builtins__": __builtins__, "pd": pd}, local_vars)
            
            # 获取结果
            if 'result' not in local_vars:
                return {
                    "success": False,
                    "error": "代码未生成'result'变量"
                }
            
            result = local_vars['result']
            
            # 格式化结果
            if isinstance(result, pd.DataFrame):
                if len(result) > 20:
                    result_str = f"找到 {len(result)} 行结果。前20行:\n{result.head(20).to_string()}"
                else:
                    result_str = result.to_string()
            elif isinstance(result, pd.Series):
                if len(result) > 20:
                    result_str = f"找到 {len(result)} 项结果。前20项:\n{result.head(20).to_string()}"
                else:
                    result_str = result.to_string()
            else:
                result_str = str(result)
            
            return {
                "success": True,
                "result": result,
                "result_str": result_str
            }
            
        except Exception as e:
            import traceback
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }


class InterpreterAgent:
    """解释Agent - 解释执行结果并生成用户友好的回答"""
    
    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
    
    def interpret_result(
        self,
        user_query: str,
        code: str,
        execution_result: Dict[str, Any]
    ) -> str:
        """
        解释执行结果
        
        Returns:
            用户友好的答案
        """
        if not execution_result.get("success"):
            error = execution_result.get("error", "未知错误")
            return f"❌ 执行失败: {error}"
        
        result_str = execution_result.get("result_str", "")
        
        prompt = f"""用户提出了一个数据分析问题，我们执行了pandas代码并得到了结果。
请用自然语言解释这个结果，回答用户的问题。

用户问题: {user_query}

执行的代码:
{code}

执行结果:
{result_str}

请用简洁、专业的语言回答用户的问题（不要重复展示代码和原始结果）："""

        response = self.llm.invoke([HumanMessage(content=prompt)])
        return response.content


class MultiAgentSystem:
    """多Agent系统协调器 - 使用LangGraph ReAct模式"""
    
    def __init__(
        self,
        data_directory: str,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        api_base: Optional[str] = None,
        temperature: float = 0,
        sample_rows: int = 3
    ):
        # 获取配置（优先使用参数，其次环境变量，最后默认值）
        final_model_name = model_name or os.getenv("MODEL_NAME") or "gpt-3.5-turbo"
        final_api_key = api_key or os.getenv("OPENAI_API_KEY")
        final_api_base = api_base or os.getenv("OPENAI_API_BASE")
        
        # 验证必需参数
        if not final_api_key:
            raise ValueError("API密钥未设置。请设置OPENAI_API_KEY环境变量或传入api_key参数")
        
        # 配置LLM
        llm_config = {
            "model": final_model_name,
            "temperature": temperature,
            "api_key": final_api_key,
        }
        
        if final_api_base:
            llm_config["base_url"] = final_api_base
        
        self.llm = ChatOpenAI(**llm_config)
        self.data_directory = data_directory
        self.sample_rows = sample_rows
        
        # 初始化Schema Agent（用于获取可用数据集）
        self.schema_agent = SchemaAgent(data_directory, sample_rows)
        
        # 创建ReAct工具
        self.tools = self._create_react_tools()
        
        # 构建ReAct Agent
        self.react_agent = self._build_react_agent()
    
    def _create_react_tools(self) -> List[StructuredTool]:
        """创建ReAct模式的工具 - Agent可以多次调用这些工具"""
        tools = []
        
        # 工具1: 列出所有可用数据集
        def list_available_datasets(query: str = "") -> str:
            """列出所有可用的CSV数据集名称"""
            datasets = self.schema_agent.get_available_datasets()
            return f"可用的数据集: {', '.join(datasets)}"
        
        tools.append(StructuredTool.from_function(
            func=list_available_datasets,
            name="list_datasets",
            description="列出所有可用的CSV数据集名称。当你不确定有哪些数据集可用时使用此工具。"
        ))
        
        # 工具2: 查看数据集Schema
        def get_dataset_schema(dataset_name: str) -> str:
            """
            获取指定数据集的结构信息（列名、数据类型、前几行样本）
            
            Args:
                dataset_name: 数据集名称，从可用数据集列表中选择
            """
            # 验证数据集是否存在
            available = self.schema_agent.get_available_datasets()
            if dataset_name not in available:
                return f"""❌ 错误: 数据集 '{dataset_name}' 不存在。

📂 可用的数据集: {', '.join(available)}

请从上述列表中选择正确的数据集名称。"""
            
            schema = self.schema_agent.analyze_schema(dataset_name)
            
            if 'error' in schema:
                return f"错误: {schema['error']}"
            
            result = f"""
数据集: {schema['name']}
行数: {schema['row_count']}
列名: {', '.join(schema['columns'])}
数据类型: {schema['dtypes']}

样本数据（前{self.sample_rows}行）:
{pd.DataFrame(schema['sample_data']).to_string()}
"""
            return result
        
        tools.append(StructuredTool.from_function(
            func=get_dataset_schema,
            name="get_schema",
            description="获取指定数据集的结构信息，包括列名、数据类型和样本数据。在编写查询代码前必须先查看schema。"
        ))
        
        # 工具3: 执行pandas查询代码
        code_executor = CodeExecutorAgent(self.data_directory)
        
        def execute_pandas_query(code: str, datasets: str) -> str:
            """
            执行pandas查询代码并返回结果
            
            Args:
                code: pandas代码，必须将结果赋值给变量'result'。格式: result = 数据集名[筛选条件]
                datasets: 需要加载的数据集名称，用逗号分隔。格式: "数据集1,数据集2"
            """
            # 解析数据集列表
            dataset_list = [ds.strip() for ds in datasets.split(',')]
            
            # 执行代码
            exec_result = code_executor.execute_code(code, dataset_list)
            
            if not exec_result.get("success"):
                return f"执行失败: {exec_result.get('error', '未知错误')}"
            
            return f"执行成功！结果:\n{exec_result.get('result_str', '')}"
        
        tools.append(StructuredTool.from_function(
            func=execute_pandas_query,
            name="query_data",
            description="执行pandas查询代码。代码中必须将最终结果赋值给'result'变量。数据集变量名就是数据集的名称。"
        ))
        
        return tools
    
    def _build_react_agent(self):
        """构建LangChain 1.0 Agent"""
        # 获取可用数据集列表并直接放入 system prompt
        available_datasets = self.schema_agent.get_available_datasets()
        
        system_prompt = f"""你是一个专业的数据分析助手，可以使用工具来查询和分析CSV数据。

可用的数据集（完整列表）: {', '.join(available_datasets)}

工作流程（ReAct模式）:
1. 理解用户问题
2. 从上述可用数据集列表中选择相关的数据集（不要猜测或虚构数据集名称）
3. 使用 get_schema 工具查看需要的数据集结构
4. 使用 query_data 工具执行pandas代码查询数据
5. 如果需要更多信息，继续使用 get_schema 和 query_data 工具
6. 当获得足够信息后，用自然语言回答用户问题

重要规则:
- **严格要求：只能使用上述列表中的数据集名称，不要猜测或虚构**
- 在编写查询代码前，必须先使用 get_schema 查看需要的数据集结构
- 如果查询结果只返回了ID或编号等引用字段，应该继续查询相关数据集获取完整详细信息
- 列名必须使用schema中显示的准确名称（区分大小写）
- 代码中数据集变量名就是数据集的名称
- 将最终结果赋值给 'result' 变量
"""
        
        # 使用LangChain 1.0新版Agent API创建agent
        return create_agent(
            model=self.llm,
            tools=self.tools,
            system_prompt=system_prompt
        )
    

    
    def query(self, user_query: str, verbose: bool = True) -> Dict[str, Any]:
        """
        处理用户查询（使用ReAct Agent）
        
        Args:
            user_query: 用户查询
            verbose: 是否显示详细过程
            
        Returns:
            包含结果的字典
        """
        try:
            # 准备消息
            messages = [HumanMessage(content=user_query)]
            
            # 执行ReAct Agent，捕获中间步骤
            step_count = 0
            tool_calls_log = []
            all_messages = []
            
            # 流式执行Agent
            for event in self.react_agent.stream({"messages": messages}, stream_mode="values"):
                messages_in_event = event.get("messages", [])
                if messages_in_event:
                    last_msg = messages_in_event[-1]
                    all_messages.append(last_msg)
                    
                    # 统计工具调用次数
                    if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                        for tool_call in last_msg.tool_calls:
                            step_count += 1
                            tool_calls_log.append({
                                "tool": tool_call.get("name", "unknown"),
                                "args": tool_call.get("args", {})
                            })
                    
                    # 使用 LangChain 内置的 pretty_print 显示消息
                    if verbose:
                        if hasattr(last_msg, 'pretty_print'):
                            last_msg.pretty_print()
                        else:
                            # 降级到普通打印
                            msg_type = last_msg.__class__.__name__
                            content = getattr(last_msg, 'content', str(last_msg))
                            if len(str(content)) > 500:
                                logger.info(f"\n{msg_type}: {str(content)[:500]}...")
                            else:
                                logger.info(f"\n{msg_type}: {content}")
            
            # 获取最终结果
            final_result = self.react_agent.invoke({"messages": messages})
            final_messages = final_result.get("messages", [])
            
            if final_messages:
                last_message = final_messages[-1]
                answer = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                answer = "无响应"
            
            return {
                "success": True,
                "answer": answer,
                "step_count": step_count,
                "tool_calls": tool_calls_log,
                "messages": final_messages  # 始终返回完整消息链
            }
            
        except Exception as e:
            import traceback
            error_detail = traceback.format_exc()
            
            if verbose:
                pretty_print(f"执行失败: {str(e)}\n详细错误:\n{error_detail}", level="error")
            
            return {
                "success": False,
                "error": str(e),
                "error_detail": error_detail
            }
