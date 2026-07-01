"""Custom exceptions and error codes."""


class RepoAgentError(Exception):
    def __init__(self, code: int, message: str, stage: str = "", recoverable: bool = False):
        self.code = code
        self.message = message
        self.stage = stage
        self.recoverable = recoverable
        super().__init__(message)


class InvalidUrlError(RepoAgentError):
    def __init__(
        self,
        message: str = "GitHub URL 格式不正确，请使用仓库地址：https://github.com/owner/repo",
    ):
        super().__init__(4001, message, stage="validate", recoverable=False)


class PrivateRepoError(RepoAgentError):
    def __init__(self, message: str = "仓库不存在或为私有仓库"):
        super().__init__(4002, message, stage="fetch_data", recoverable=False)


class TaskNotFoundError(RepoAgentError):
    def __init__(self, message: str = "任务不存在"):
        super().__init__(4003, message, recoverable=False)


class RateLimitError(RepoAgentError):
    def __init__(self, message: str = "请求频率超限"):
        super().__init__(4290, message, recoverable=True)


class GitHubApiError(RepoAgentError):
    def __init__(self, message: str = "GitHub API 调用失败"):
        super().__init__(5001, message, stage="fetch_data", recoverable=True)


class AgentTimeoutError(RepoAgentError):
    def __init__(self, message: str = "Agent 执行超时"):
        super().__init__(5002, message, recoverable=False)


class LLMError(RepoAgentError):
    def __init__(self, message: str = "LLM 调用失败"):
        super().__init__(5003, message, recoverable=True)


class TaskTimeoutError(RepoAgentError):
    def __init__(self, message: str = "分析任务超时"):
        super().__init__(5004, message, recoverable=False)
