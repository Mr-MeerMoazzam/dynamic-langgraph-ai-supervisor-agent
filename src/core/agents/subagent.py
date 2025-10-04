"""
Subagent execution system for the Supervisor Agent.

This module implements the SubagentExecutor class that creates and runs
specialized subagents for specific tasks, coordinating with the VirtualFileSystem
and tool registry to accomplish complex objectives.
"""

import os
import json
import logging
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain.prompts import MessagesPlaceholder
from langchain.memory import ConversationBufferMemory

# Local imports
from src.core.file_system import VirtualFileSystem
from src.core.tools.file_tools import get_file_tools
from src.core.tools.assignable_tools import get_assignable_tools


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def generate_subagent_prompt(
    task_description: str,
    context: Dict[str, Any],
    success_criteria: str,
    available_tools: List[str]
) -> str:
    """
    Generate a specialized prompt for a subagent execution.

    This function creates a comprehensive system prompt that gives the subagent
    clear instructions, context, success criteria, and available tools.

    Args:
        task_description: Description of the specific task to accomplish
        context: Dictionary of contextual information from previous tasks
        success_criteria: Criteria that define task completion
        available_tools: List of tool names available to the subagent

    Returns:
        str: Complete system prompt for the subagent

    Example:
        >>> prompt = generate_subagent_prompt(
        ...     "Analyze sales data",
        ...     {"previous_findings": "Sales up 15%"},
        ...     "Generate summary report",
        ...     ["read_file", "write_file", "execute_code"]
        ... )
    """
    # Build enhanced context section
    context_section = _build_context_section(context)

    # Format tools list
    tools_list = "\n".join(f"- {tool}" for tool in available_tools)

    # Create the system prompt with all variables substituted
    system_prompt = f"""You are a specialized AI subagent tasked with completing a specific objective.

## Task Description
{task_description}

{context_section}

## Success Criteria
Your work is complete when:
{success_criteria}

## Available Tools
You have access to the following tools:
{tools_list}

## Important Instructions

1. **Context Awareness**: 
   - **ALWAYS check previous task results before starting new work**
   - **Use existing files when possible instead of recreating data**
   - **Read from files created by previous tasks**
   - **Build upon previous work rather than starting from scratch**

2. **File Operations**: Use file tools (read_file, write_file, edit_file) to:
   - **Read existing files first** before creating new ones
   - Save important findings and results
   - Store intermediate data for other tasks
   - Create reports and documentation
   - Externalize your memory and thought process

3. **Tool Usage**: Use the available tools strategically. Each tool serves a specific purpose:
   - Use file tools for context engineering and persistence
   - Use assigned tools for task-specific operations
   - Combine tools when needed for complex tasks

4. **Output Format**: Provide clear, actionable results. If creating files, mention them explicitly.

5. **Context Utilization**:
   - If previous tasks created files, read them first
   - If previous tasks calculated data, use that data
   - If previous tasks found information, build upon it
   - **NEVER recalculate what previous tasks already computed**

5. **Error Handling**: If you encounter errors, analyze them and try alternative approaches.

6. **Completion**: When you believe you've met the success criteria, provide a clear summary of what was accomplished.

## Response Guidelines
- Be concise but thorough
- Use files to store detailed information
- Reference created files in your responses
- Explain your reasoning when making important decisions

Start by analyzing the task and planning your approach. Then execute systematically."""

    return system_prompt.strip()


def _build_context_section(context: Dict[str, Any], available_files: set = None) -> str:
    """Build enhanced context section with file mapping and strong warnings"""
    if not context:
        context = {}
    
    # Get available files from context if not provided
    if available_files is None:
        available_files = set(context.get('available_files', []))
    
    sections = []
    
    # Critical file usage instructions (ALWAYS SHOW)
    if available_files:
        sections.append("═══════════════════════════════════════════════════")
        sections.append("⚠️  CRITICAL: FILES AVAILABLE IN VIRTUAL FILESYSTEM")
        sections.append("═══════════════════════════════════════════════════")
        sections.append("")
        sections.append("📁 EXISTING FILES YOU MUST USE:")
        for filepath in sorted(available_files):
            sections.append(f"   • {filepath}")
        sections.append("")
        sections.append("⚠️  MANDATORY RULES:")
        sections.append("   1. ALWAYS use files from the list above")
        sections.append("   2. Do NOT search for files with different names")
        sections.append("   3. Do NOT create new files if existing files contain the data")
        sections.append("   4. If you need data, READ the existing files first")
        sections.append("   5. Use EXACT filenames as shown above")
        sections.append("")
    
    # Previous tasks with explicit file mapping
    completed = context.get('completed_tasks', [])
    if completed:
        sections.append("═══════════════════════════════════════════════════")
        sections.append("📋 PREVIOUS TASKS & THEIR OUTPUT FILES")
        sections.append("═══════════════════════════════════════════════════")
        sections.append("")
        
        for task in completed[-5:]:  # Show last 5 tasks
            task_desc = task.get('task', 'Unknown task')
            task_id = task.get('id', '?')
            artifacts = task.get('artifacts', [])
            
            sections.append(f"Task {task_id}: {task_desc}")
            
            if artifacts:
                sections.append(f"   Created files: {', '.join(artifacts)}")
                # Add content hints for key files
                for artifact in artifacts:
                    if artifact in available_files:
                        sections.append(f"   ✓ File '{artifact}' is available for you to read")
            else:
                sections.append("   (No files created)")
            sections.append("")
    
    # Overall objective for context
    objective = context.get('objective', '')
    if objective:
        sections.append("═══════════════════════════════════════════════════")
        sections.append("🎯 OVERALL PROJECT OBJECTIVE")
        sections.append("═══════════════════════════════════════════════════")
        sections.append(objective)
        sections.append("")
    
    # File usage reminder (repeat for emphasis)
    if available_files:
        sections.append("═══════════════════════════════════════════════════")
        sections.append("🔍 BEFORE YOU START")
        sections.append("═══════════════════════════════════════════════════")
        sections.append("1. Review the list of available files above")
        sections.append("2. Map your task requirements to existing files")
        sections.append("3. Use read_file_tool to examine existing files")
        sections.append("4. Only create NEW files if data doesn't exist")
        sections.append("")
    
    return "\n".join(sections) if sections else ""


class SubagentExecutor:
    """
    Executes specialized subagents for specific tasks.

    This class creates and runs subagents with tailored prompts and toolsets,
    coordinating with the VirtualFileSystem and tool registry to accomplish
    complex objectives through task decomposition.
    """

    def __init__(self, file_system: Optional[VirtualFileSystem] = None):
        """
        Initialize the SubagentExecutor.

        Args:
            file_system: VirtualFileSystem instance. If None, creates new instance.
        """
        self.file_system = file_system or VirtualFileSystem()

        # Load API key and initialize LLM
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")

        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  # Low temperature for consistency
            api_key=openai_api_key
        )

        # Get available tools
        self.file_tools = get_file_tools()
        self.assignable_tools = get_assignable_tools()

        logger.info(f"SubagentExecutor initialized with {len(self.file_tools)} file tools and {len(self.assignable_tools)} assignable tools")

    def run_subagent(
        self,
        task_description: str,
        assigned_tools: List[str],
        context: Dict[str, Any],
        success_criteria: str,
        max_iterations: int = 15
    ) -> Dict[str, Any]:
        """
        Execute a subagent for a specific task.

        Args:
            task_description: Description of the task to accomplish
            assigned_tools: List of tool names to assign to this subagent
            context: Contextual information from previous tasks
            success_criteria: Criteria that define when task is complete
            max_iterations: Maximum number of agent iterations (default: 15)

        Returns:
            Dict containing:
            - success: Boolean indicating if task completed successfully
            - result: Final result/output from the subagent
            - iterations_used: Number of iterations actually used
            - artifacts_created: List of files created during execution

        Example:
            >>> result = executor.run_subagent(
            ...     "Analyze quarterly sales data",
            ...     ["read_file", "execute_code"],
            ...     {"previous_data": "sales_q1.csv"},
            ...     "Generate summary report in report.txt"
            ... )
        """
        logger.info(f"Starting subagent execution for task: {task_description[:50]}...")

        start_time = time.time()

        try:
            # Generate specialized prompt
            # Combine file tools with requested assignable tools
            available_tools = []
            available_tools.extend(self.file_tools.values())

            for tool_name in assigned_tools:
                # Check assignable tools first
                if tool_name in self.assignable_tools:
                    available_tools.append(self.assignable_tools[tool_name])
                # Also allow file tools by name
                elif tool_name in self.file_tools:
                    # File tool already added above, skip duplicate
                    pass
            # Get tool names for the prompt
            tool_names = []
            for tool in available_tools:
                if hasattr(tool, 'name'):
                    tool_names.append(tool.name)
                else:
                    # Handle case where tool might be a string or different format
                    tool_names.append(str(tool))
            
            system_prompt = generate_subagent_prompt(
                task_description,
                context,
                success_criteria,
                tool_names
            )
            
            # Add intelligent file suggestions
            available_files = set(self.file_system.list_files())
            relevant_files = self._suggest_relevant_files(task_description, available_files)
            if relevant_files:
                file_suggestions = "\n\n" + "═" * 55 + "\n"
                file_suggestions += "💡 FILES LIKELY RELEVANT TO YOUR TASK\n"
                file_suggestions += "═" * 55 + "\n"
                for filepath in relevant_files:
                    file_suggestions += f"   • {filepath}\n"
                file_suggestions += "\nConsider reading these files first!\n"
                system_prompt += file_suggestions

            # Create the agent
            agent = create_openai_functions_agent(
                llm=self.llm,
                tools=available_tools,
                prompt=ChatPromptTemplate.from_messages([
                    ("system", system_prompt),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("human", "{input}"),
                    MessagesPlaceholder(variable_name="agent_scratchpad"),
                ])
            )

            # Create agent executor with memory
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True
            )

            agent_executor = AgentExecutor(
                agent=agent,
                tools=available_tools,
                memory=memory,
                verbose=True,
                max_iterations=max_iterations,
                handle_parsing_errors=True,
                return_intermediate_steps=True
            )

            # Snapshot files BEFORE execution
            files_before = set(self.file_system.list_files())
            logger.info(f"📁 Files before execution: {files_before}")
            
            # Execute the agent
            logger.info(f"Executing subagent with {len(available_tools)} tools")

            # Format the input for the agent
            agent_input = f"""
Task: {task_description}

Available Context:
{json.dumps(context, indent=2)}

Please complete this task using the available tools. Focus on efficiency and save important findings to files.
"""

            # Run the agent
            result = agent_executor.invoke({"input": agent_input})

            # Extract information from result
            iterations_used = len(result.get("intermediate_steps", []))

            # Snapshot files AFTER execution
            files_after = set(self.file_system.list_files())
            logger.info(f"📁 Files after execution: {files_after}")
            
            # Calculate diff
            new_files = list(files_after - files_before)
            artifacts_created = new_files
            logger.info(f"📦 Artifacts created: {artifacts_created}")

            # Check if execution was successful
            if result.get("output"):
                success = True
                final_result = result["output"]

                logger.info(f"Subagent completed successfully in {iterations_used} iterations")
                logger.info(f"Created artifacts: {artifacts_created}")

                return {
                    "success": success,
                    "result": final_result,
                    "iterations_used": iterations_used,
                    "artifacts_created": artifacts_created
                }
            else:
                logger.warning("Subagent execution completed but no output generated")
                return {
                    "success": False,
                    "result": "Subagent execution completed but no clear result was generated",
                    "iterations_used": iterations_used,
                    "artifacts_created": artifacts_created
                }

        except Exception as e:
            logger.error(f"Subagent execution failed: {str(e)}")
            logger.error(f"Error details: {type(e).__name__}: {str(e)}")

            # Try to get artifacts even if execution failed
            try:
                artifacts_created = artifact_tracker.get_artifacts() if 'artifact_tracker' in locals() else []
            except:
                artifacts_created = []

            return {
                "success": False,
                "result": f"Subagent execution failed: {str(e)}",
                "iterations_used": 0,
                "artifacts_created": artifacts_created
            }

        finally:
            execution_time = time.time() - start_time
            logger.info(f"Subagent execution completed in {execution_time:.2f} seconds")

    def _suggest_relevant_files(self, task_description: str, available_files: set) -> List[str]:
        """Suggest which existing files might be relevant to the task"""
        task_lower = task_description.lower()
        suggestions = []
        
        # Keyword mapping
        keywords_map = {
            'market': ['market', 'research'],
            'catalog': ['catalog', 'product'],
            'price': ['price', 'discount', 'cost'],
            'report': ['report', 'summary', 'final'],
            'discount': ['discount', 'price'],
            'data': ['data', 'csv'],
        }
        
        # Find relevant files based on keywords
        for filepath in available_files:
            filepath_lower = filepath.lower()
            
            # Check if any keyword from task appears in filename
            for keyword_group in keywords_map.values():
                if any(keyword in task_lower for keyword in keyword_group):
                    if any(keyword in filepath_lower for keyword in keyword_group):
                        if filepath not in suggestions:
                            suggestions.append(filepath)
                            break
        
        return suggestions


def create_subagent_executor(file_system: Optional[VirtualFileSystem] = None) -> SubagentExecutor:
    """
    Factory function to create a SubagentExecutor instance.

    Args:
        file_system: Optional VirtualFileSystem instance

    Returns:
        SubagentExecutor: Configured subagent executor

    Example:
        >>> executor = create_subagent_executor()
        >>> result = executor.run_subagent("Analyze data", ["read_file"], {}, "Generate report")
    """
    return SubagentExecutor(file_system)
