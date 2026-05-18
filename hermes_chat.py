import os
import argparse
import concurrent.futures
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path


try:
    from run_agent import AIAgent
    HAS_HERMES = True
except ImportError:
    HAS_HERMES = False
    AIAgent = None


class HermesClient:
    DEFAULT_MODEL = "anthropic/claude-opus-4.6"
    DEFAULT_MAX_ITERATIONS = 90

    def __init__(
        self,
        model: str = None,
        api_key: str = None,
        base_url: str = None,
        quiet_mode: bool = True,
        enabled_toolsets: List[str] = None,
        disabled_toolsets: List[str] = None,
        save_trajectories: bool = False,
        ephemeral_system_prompt: str = None,
        max_iterations: int = DEFAULT_MAX_ITERATIONS,
        skip_context_files: bool = False,
        skip_memory: bool = False,
        platform: str = None,
    ) -> None:
        if not HAS_HERMES:
            raise ImportError(
                "Hermes agent not installed. Install with: "
                "pip install git+https://github.com/NousResearch/hermes-agent.git"
            )

        self.model = model or os.getenv("HERMES_MODEL", self.DEFAULT_MODEL)
        self.api_key = api_key
        self.base_url = base_url
        self.quiet_mode = quiet_mode
        self.enabled_toolsets = enabled_toolsets
        self.disabled_toolsets = disabled_toolsets
        self.save_trajectories = save_trajectories
        self.ephemeral_system_prompt = ephemeral_system_prompt
        self.max_iterations = max_iterations
        self.skip_context_files = skip_context_files
        self.skip_memory = skip_memory
        self.platform = platform
        self._agent = None

    def _create_agent(self, **kwargs) -> Any:
        init_kwargs = {
            "model": self.model,
            "quiet_mode": self.quiet_mode,
            "save_trajectories": self.save_trajectories,
            "max_iterations": self.max_iterations,
            "skip_context_files": self.skip_context_files,
            "skip_memory": self.skip_memory,
        }
        if self.enabled_toolsets:
            init_kwargs["enabled_toolsets"] = self.enabled_toolsets
        if self.disabled_toolsets:
            init_kwargs["disabled_toolsets"] = self.disabled_toolsets
        if self.ephemeral_system_prompt:
            init_kwargs["ephemeral_system_prompt"] = self.ephemeral_system_prompt
        if self.api_key:
            init_kwargs["api_key"] = self.api_key
        if self.base_url:
            init_kwargs["base_url"] = self.base_url
        if self.platform:
            init_kwargs["platform"] = self.platform
        init_kwargs.update(kwargs)
        return AIAgent(**init_kwargs)

    @property
    def agent(self) -> Any:
        if self._agent is None:
            self._agent = self._create_agent()
        return self._agent

    def chat(self, message: str) -> str:
        return self.agent.chat(message)

    def chat_with_system_prompt(
        self,
        message: str,
        system_prompt: str,
        task_id: str = None,
    ) -> str:
        kwargs = {
            "user_message": message,
            "system_message": system_prompt,
        }
        if task_id:
            kwargs["task_id"] = task_id
        result = self.agent.run_conversation(**kwargs)
        return result.get("final_response", "")

    def start_conversation(self) -> List[Dict[str, Any]]:
        return []

    def continue_conversation(
        self,
        message: str,
        history: List[Dict[str, Any]],
        task_id: str = None,
    ) -> Tuple[str, List[Dict[str, Any]]]:
        kwargs = {
            "user_message": message,
            "conversation_history": history,
        }
        if task_id:
            kwargs["task_id"] = task_id
        result = self.agent.run_conversation(**kwargs)
        messages = result.get("messages", [])
        if messages:
            history.extend(messages)
        return result.get("final_response", ""), history

    def run_conversation(
        self,
        message: str,
        system_prompt: str = None,
        task_id: str = None,
        conversation_history: List[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        kwargs = {
            "user_message": message,
        }
        if system_prompt:
            kwargs["system_message"] = system_prompt
        if task_id:
            kwargs["task_id"] = task_id
        if conversation_history:
            kwargs["conversation_history"] = conversation_history
        return self.agent.run_conversation(**kwargs)

    def batch_chat(
        self,
        prompts: List[str],
        max_workers: int = 3,
    ) -> Dict[str, str]:
        def _process_prompt(prompt: str) -> Tuple[str, str]:
            agent = self._create_agent(
                skip_memory=True,
                skip_context_files=True,
            )
            return prompt, agent.chat(prompt)

        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_prompt = {
                executor.submit(_process_prompt, prompt): prompt
                for prompt in prompts
            }
            for future in concurrent.futures.as_completed(future_to_prompt):
                prompt, response = future.result()
                results[prompt] = response
        return results


def create_client(
    model: str = None,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    system_prompt: str = None,
    no_tools: bool = False,
) -> HermesClient:
    client_kwargs = {
        "quiet_mode": True,
        "skip_context_files": True,
        "skip_memory": True,
    }
    if model:
        client_kwargs["model"] = model
    if no_tools:
        client_kwargs["enabled_toolsets"] = []
    else:
        if enabled_toolsets:
            client_kwargs["enabled_toolsets"] = enabled_toolsets
        if disabled_toolsets:
            client_kwargs["disabled_toolsets"] = disabled_toolsets
    if system_prompt:
        client_kwargs["ephemeral_system_prompt"] = system_prompt
    return HermesClient(**client_kwargs)


def single_message_mode(
    message: str,
    model: str = None,
    system_prompt: str = None,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    no_tools: bool = False,
) -> str:
    client = create_client(
        model=model,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
        system_prompt=system_prompt,
        no_tools=no_tools,
    )
    return client.chat(message)


def interactive_mode(
    model: str = None,
    system_prompt: str = None,
    enabled_toolsets: List[str] = None,
    disabled_toolsets: List[str] = None,
    no_tools: bool = False,
) -> None:
    client = create_client(
        model=model,
        enabled_toolsets=enabled_toolsets,
        disabled_toolsets=disabled_toolsets,
        system_prompt=system_prompt,
        no_tools=no_tools,
    )
    print("Hermes Chat - Interactive Mode")
    print("Type 'quit' or 'exit' to end the conversation.\n")
    history = []
    exit_commands = {"quit", "exit", "/quit", "/exit"}
    while True:
        try:
            user_input = input("You: ")
            if user_input.strip().lower() in exit_commands:
                print("Goodbye!")
                break
            if not user_input.strip():
                continue
            response, history = client.continue_conversation(user_input, history)
            print(f"Hermes: {response}\n")
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")
            break


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Hermes Agent Chat - Python program to chat with Hermes AI agent"
    )
    parser.add_argument(
        "-m", "--message",
        type=str,
        help="Single message to send to Hermes"
    )
    parser.add_argument(
        "-i", "--interactive",
        action="store_true",
        help="Run in interactive mode (continuous conversation)"
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model name in OpenRouter format (e.g., anthropic/claude-sonnet-4)"
    )
    parser.add_argument(
        "--system-prompt",
        type=str,
        help="Custom system prompt to guide the agent's behavior"
    )
    parser.add_argument(
        "--enable-tools",
        type=str,
        nargs="+",
        help="Enable specific toolsets (e.g., web search terminal)"
    )
    parser.add_argument(
        "--disable-tools",
        type=str,
        nargs="+",
        help="Disable specific toolsets (e.g., terminal browser)"
    )
    parser.add_argument(
        "--no-tools",
        action="store_true",
        help="Disable all tools (read-only chat only)"
    )
    return parser.parse_args()


def main() -> None:
    if not HAS_HERMES:
        print("Error: Hermes agent not installed.")
        print("Install with: pip install git+https://github.com/NousResearch/hermes-agent.git")
        print("")
        print("Required environment variables (at minimum):")
        print("  - OPENROUTER_API_KEY")
        print("  or")
        print("  - OPENAI_API_KEY / ANTHROPIC_API_KEY (direct provider access)")
        return

    args = parse_args()

    if args.message:
        response = single_message_mode(
            message=args.message,
            model=args.model,
            system_prompt=args.system_prompt,
            enabled_toolsets=args.enable_tools,
            disabled_toolsets=args.disable_tools,
            no_tools=args.no_tools,
        )
        print(response)
    elif args.interactive:
        interactive_mode(
            model=args.model,
            system_prompt=args.system_prompt,
            enabled_toolsets=args.enable_tools,
            disabled_toolsets=args.disable_tools,
            no_tools=args.no_tools,
        )
    else:
        print("Usage:")
        print("  Single message: python hermes_chat.py -m 'What is Python?'")
        print("  Interactive mode: python hermes_chat.py -i")
        print("")
        print("Examples:")
        print("  python hermes_chat.py -m 'Explain recursion'")
        print("  python hermes_chat.py -m 'Write a hello world' --no-tools")
        print("  python hermes_chat.py -i --model anthropic/claude-sonnet-4")
        print("  python hermes_chat.py -i --system-prompt 'You are a helpful assistant.'")
        print("  python hermes_chat.py -m 'Search for news' --enable-tools web search")


if __name__ == "__main__":
    main()
